"""Stellar Hub setup: checks your hardware and drivers, picks a model that fits, and gets everything ready.

Run it with ./setup.sh   (options: --yes to accept every suggestion, --check to only report)
Nothing that needs your password happens without asking first.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "config.json")
YES = "--yes" in sys.argv
CHECK_ONLY = "--check" in sys.argv

# Model picks per memory size, best first. If a download fails (renamed or retired model),
# the next one is tried. The last entries in each list are long-established models.
# Picks checked against ollama.com guides in November 2026.
TIERS = [
    (22, "24 GB+ graphics card", ["qwen3.8:27b", "gemma4:31b", "qwen3:32b", "qwen2.5:32b"]),
    (14, "16 GB graphics card", ["gemma4:12b", "qwen3:14b", "qwen2.5:14b"]),
    (9, "10-12 GB graphics card", ["gemma4:12b", "qwen3:8b", "llama3.1:8b"]),
    (5.5, "6-8 GB graphics card", ["qwen3:8b", "llama3.1:8b", "qwen2.5:7b"]),
]
CPU_TIERS = [
    (15, "no usable graphics card, 16 GB+ RAM", ["qwen3.5:4b", "qwen3:4b", "llama3.2:3b"]),
    (7, "no usable graphics card, 8 GB RAM", ["llama3.2:3b", "qwen2.5:3b", "qwen3:1.7b"]),
    (0, "no usable graphics card, under 8 GB RAM", ["llama3.2:1b", "qwen2.5:1.5b"]),
]

C = {"b": "\033[1m", "c": "\033[96m", "g": "\033[92m", "y": "\033[93m", "r": "\033[91m", "d": "\033[2m", "x": "\033[0m"}


def say(msg, color="x"):
    print(f"{C[color]}{msg}{C['x']}")


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def ask(question):
    if CHECK_ONLY:
        return False
    if YES:
        print(f"{question} [y/N] y (--yes)")
        return True
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


# ------------------------------------------------------------------ detection
def distro():
    info = {}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                info[k] = v.strip('"')
    except OSError:
        pass
    ids = (info.get("ID", "") + " " + info.get("ID_LIKE", "")).lower()
    return info.get("PRETTY_NAME", "Linux"), ids


def pkg_manager():
    for pm in ("apt", "dnf", "pacman", "zypper"):
        if shutil.which(pm):
            return pm
    return None


def install_cmd(pm, pkgs):
    return {"apt": f"sudo apt install -y {pkgs}", "dnf": f"sudo dnf install -y {pkgs}",
            "pacman": f"sudo pacman -S --needed {pkgs}", "zypper": f"sudo zypper install -y {pkgs}"}.get(pm)


def ram_gb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 0


def cpu_name():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown CPU"


def gpus():
    """Returns a list of {vendor, name, vram_gb, driver_ok, note}."""
    found = []
    vendors = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}
    seen = set()
    for card in sorted(os.listdir("/sys/class/drm")) if os.path.isdir("/sys/class/drm") else []:
        if not re.fullmatch(r"card\d+", card):
            continue
        dev = f"/sys/class/drm/{card}/device"
        try:
            vendor = open(f"{dev}/vendor").read().strip()
            slot = os.path.basename(os.path.realpath(dev))
        except OSError:
            continue
        if slot in seen or vendor not in vendors:
            continue
        seen.add(slot)
        g = {"vendor": vendors[vendor], "name": "", "vram_gb": 0.0, "driver_ok": False, "note": "", "slot": slot}
        try:
            g["vram_gb"] = int(open(f"{dev}/mem_info_vram_total").read()) / 1024 ** 3
        except (OSError, ValueError):
            pass
        found.append(g)
    # names from lspci when available
    if shutil.which("lspci"):
        _, out = run(["lspci", "-D"])
        for line in out.splitlines():
            if not re.search(r"VGA|3D|Display", line):
                continue
            slot = line.split()[0]
            match = [g for g in found if g["slot"] == slot]
            if match:
                match[0]["name"] = line.split(": ", 1)[-1]
            elif re.search(r"NVIDIA|AMD|ATI", line):   # card with no driver loaded at all
                found.append({"vendor": "nvidia" if "NVIDIA" in line else "amd", "name": line.split(": ", 1)[-1],
                              "vram_gb": 0.0, "driver_ok": False, "note": "", "slot": slot})
    for g in found:
        if g["vendor"] == "nvidia":
            code, out = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
            if code == 0 and out:
                name, mem = out.splitlines()[0].rsplit(",", 1)
                g.update(name=name.strip(), vram_gb=int(mem) / 1024, driver_ok=True)
            else:
                g["note"] = "NVIDIA driver not working (nvidia-smi failed)"
        elif g["vendor"] == "amd":
            drv = os.path.basename(os.path.realpath(f"/sys/bus/pci/devices/{g['slot']}/driver")) \
                if os.path.exists(f"/sys/bus/pci/devices/{g['slot']}/driver") else ""
            g["driver_ok"] = drv == "amdgpu" and os.path.exists("/dev/kfd")
            if drv != "amdgpu":
                g["note"] = "amdgpu driver not loaded"
            elif not os.path.exists("/dev/kfd"):
                g["note"] = "/dev/kfd missing (compute support not enabled)"
            if g["vram_gb"] < 2:          # integrated AMD graphics share system RAM
                g["note"] = g["note"] or "integrated graphics (uses system RAM)"
                g["driver_ok"] = False
        else:
            g["note"] = "Intel graphics: the model will run on the CPU"
    return found


def driver_help(g, ids, pm):
    if g["vendor"] == "nvidia":
        if "ubuntu" in ids or "pop" in ids or "mint" in ids:
            return "sudo ubuntu-drivers install", True
        if "fedora" in ids:
            return ("Enable RPM Fusion (rpmfusion.org/Configuration), then: "
                    "sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda   (reboot after)"), False
        if "arch" in ids or "manjaro" in ids or "endeavour" in ids:
            return "sudo pacman -S nvidia-open nvidia-utils   (or 'nvidia' for older cards; reboot after)", False
        if "debian" in ids:
            return "Enable 'non-free' in /etc/apt/sources.list, then: sudo apt install nvidia-driver firmware-misc-nonfree", False
        if "suse" in ids:
            return "sudo zypper install openSUSE-repos-NVIDIA && sudo zypper install-new-recommends", False
        return "Install your distro's proprietary NVIDIA driver, then reboot.", False
    if g["vendor"] == "amd":
        return ("Your kernel's amdgpu driver should handle this. Update your system and make sure your user is in "
                "the 'render' and 'video' groups:  sudo usermod -aG render,video $USER   (log out and back in). "
                "Some older AMD cards aren't supported for AI and will use the CPU instead."), False
    return "", False


# ------------------------------------------------------------------ ollama
def ollama_up():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=4) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return None


def pull(model):
    say(f"\nDownloading {model} (this can take a while)…", "c")
    return subprocess.run(["ollama", "pull", model]).returncode == 0


def set_model(model):
    with open(CONFIG) as f:
        cfg = json.load(f)
    cfg.setdefault("ollama", {})["model"] = model
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


# ------------------------------------------------------------------ main
def main():
    say("\n★ STELLAR HUB SETUP ★\n", "b")
    name, ids = distro()
    pm = pkg_manager()
    ram = ram_gb()
    say(f"System:  {name}")
    say(f"CPU:     {cpu_name()} ({os.cpu_count()} threads)")
    say(f"Memory:  {ram:.1f} GB RAM")
    if sys.version_info < (3, 10):
        say(f"Python {sys.version.split()[0]} is too old. Stellar Hub needs Python 3.10 or newer.", "r")
        return 1

    # ---- graphics
    cards = gpus()
    best = None
    if not cards:
        say("Graphics: none detected, so the model will run on the CPU.", "y")
    for g in cards:
        label = g["name"] or g["vendor"].upper()
        vram = f", {g['vram_gb']:.0f} GB" if g["vram_gb"] >= 1 else ""
        if g["driver_ok"]:
            say(f"Graphics: {label}{vram} ✓ driver working", "g")
            if not best or g["vram_gb"] > best["vram_gb"]:
                best = g
        else:
            say(f"Graphics: {label}{vram}: {g['note']}", "y")
            fix, can_run = driver_help(g, ids, pm)
            if fix:
                say(f"  Fix: {fix}", "d")
                if can_run and ask("  Run the driver installer now? (needs your password, reboot after)"):
                    subprocess.run(fix, shell=True)
                    say("  Reboot, then run ./setup.sh again.", "y")
                    return 0

    # ---- pick a model tier
    if best:
        tier = next(((label, models) for need, label, models in TIERS if best["vram_gb"] >= need), None)
    else:
        tier = None
    if not tier:
        tier = next((label, models) for need, label, models in CPU_TIERS if ram >= need)
    label, candidates = tier
    say(f"\nBest fit: {label} → {candidates[0]}", "c")
    if not best:
        say("  Running on the CPU is slower, but fine here: your resident only thinks every 30 minutes.", "d")

    # ---- ollama
    if not shutil.which("ollama"):
        say("\nOllama isn't installed.", "y")
        if ask("Install Ollama now? (runs the official installer from ollama.com, needs your password)"):
            subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True)
        if not shutil.which("ollama"):
            say("Install it later with:  curl -fsSL https://ollama.com/install.sh | sh", "d")
            return 0
    have = ollama_up()
    if have is None:
        say("\nOllama is installed but not running. Start it with:  sudo systemctl start ollama   (or: ollama serve)", "y")
        if not CHECK_ONLY:
            return 0
    else:
        say(f"\nOllama is running ✓  Models you have: {', '.join(have) or 'none yet'}", "g")
        chosen = next((m for m in candidates if m in have or m + ":latest" in have), None)
        if chosen:
            say(f"You already have {chosen}.", "g")
        elif ask(f"Download {candidates[0]} now?"):
            for m in candidates:
                if pull(m):
                    chosen = m
                    break
                say(f"Couldn't download {m}, trying the next option…", "y")
        if chosen:
            set_model(chosen)
            say(f"✓ Stellar Hub will use {chosen} (saved in config.json)", "g")

    # ---- optional tools
    say("\nOptional extras:", "b")
    extras = [
        ("bwrap", "bubblewrap", "the Fabrication Hangar's safe sandbox for running its programs"),
        ("mpv", "mpv", "the Radio Tower, to play music out loud"),
    ]
    missing = []
    for exe, pkg, why in extras:
        if shutil.which(exe):
            say(f"  ✓ {exe}: {why}", "g")
        else:
            say(f"  ✗ {exe}: needed for {why}", "y")
            missing.append(pkg)
    if missing and pm:
        cmd = install_cmd(pm, " ".join(missing))
        say(f"  Install with: {cmd}", "d")
        if ask("  Install them now? (needs your password)"):
            subprocess.run(cmd, shell=True)
    if shutil.which("tailscale"):
        code, ip = run(["tailscale", "ip", "-4"])
        say(f"  ✓ tailscale: phone access at {ip.splitlines()[0]}:8080" if code == 0 and ip
            else "  ✗ tailscale is installed but not connected. Run: sudo tailscale up", "g" if code == 0 and ip else "y")
    else:
        say("  ✗ tailscale: needed for Hub Connect S. Install: curl -fsSL https://tailscale.com/install.sh | sh", "y")

    with open(CONFIG) as f:
        music = os.path.expanduser(json.load(f).get("radio", {}).get("music_dir", "~/Music"))
    if os.path.isdir(music):
        say(f"  ✓ music folder: {music}", "g")
    else:
        say(f"  ✗ music folder {music} not found. Set radio.music_dir in config.json", "y")

    unit = os.path.expanduser("~/.config/systemd/user/stellar-hub.service")
    if os.path.exists(unit):
        say("  ✓ starts automatically with your PC", "g")
        say("\nAll set. Restart it after updates with:  systemctl --user restart stellar-hub\n", "b")
        return 0
    if shutil.which("systemctl") and ask("\nStart Stellar Hub automatically with your PC?"):
        subprocess.run(["sh", os.path.join(ROOT, "install-service.sh")])
        return 0
    say("\nAll set. Start Stellar Hub with ./start.sh   (or make it start with your PC: sh install-service.sh)\n", "b")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(1)
