"""Stellar Hub setup: checks your hardware and drivers, picks a model that fits, and gets everything ready.

Run it with ./setup.sh on Linux, or "Setup and model check" in the Start menu on Windows.
Options: --yes to accept every suggestion, --check to only report.
Nothing that needs your password (or admin rights) happens without asking first.
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from town.osutil import IS_WIN, find_exe, run_quiet  # noqa: E402

CONFIG = os.path.join(ROOT, "config.json")
YES = "--yes" in sys.argv
CHECK_ONLY = "--check" in sys.argv
PAUSE = "--pause" in sys.argv
if IS_WIN:
    os.system("")   # turns on colours in the Windows console

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
    return run_quiet(cmd, timeout)


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
    if IS_WIN:
        return f"Windows {platform.release()} ({platform.version()})", "windows"
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
    if IS_WIN:
        return "winget" if shutil.which("winget") else None
    for pm in ("apt", "dnf", "pacman", "zypper"):
        if shutil.which(pm):
            return pm
    return None


def install_cmd(pm, pkgs):
    if pm == "winget":
        return " && ".join(f"winget install -e --id {p} --accept-source-agreements --accept-package-agreements"
                           for p in pkgs.split())
    return {"apt": f"sudo apt install -y {pkgs}", "dnf": f"sudo dnf install -y {pkgs}",
            "pacman": f"sudo pacman -S --needed {pkgs}", "zypper": f"sudo zypper install -y {pkgs}"}.get(pm)


def ram_gb():
    if IS_WIN:
        import ctypes

        class MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MemStatus()
        m.dwLength = ctypes.sizeof(MemStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullTotalPhys / 1024 ** 3
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 0


def cpu_name():
    if IS_WIN:
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        except OSError:
            return platform.processor() or "unknown CPU"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown CPU"


def gpus_windows():
    """Reads graphics cards from the Windows registry (accurate memory sizes, unlike most tools)."""
    import winreg
    found = []
    base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
    except OSError:
        return found
    i = 0
    while True:
        try:
            sub = winreg.EnumKey(root, i)
        except OSError:
            break
        i += 1
        if not sub.isdigit():
            continue
        try:
            k = winreg.OpenKey(root, sub)
        except OSError:
            continue

        def val(name):
            try:
                return winreg.QueryValueEx(k, name)[0]
            except OSError:
                return None
        desc = val("DriverDesc") or ""
        dev = (val("MatchingDeviceId") or "").lower()
        provider = (val("ProviderName") or "").lower()
        mem = val("HardwareInformation.qwMemorySize")
        if mem is None:
            mem = val("HardwareInformation.MemorySize")
            if isinstance(mem, bytes):
                mem = int.from_bytes(mem[:8], "little")
        low = desc.lower()
        if "ven_10de" in dev or "nvidia" in low:
            vendor = "nvidia"
        elif "ven_1002" in dev or "radeon" in low or "amd" in low:
            vendor = "amd"
        elif "ven_8086" in dev or "intel" in low:
            vendor = "intel"
        elif "basic display" in low or "basic render" in low:
            vendor = "basic"
        else:
            continue
        g = {"vendor": vendor, "name": desc, "vram_gb": (mem or 0) / 1024 ** 3, "driver_ok": False, "note": "", "slot": sub}
        if vendor == "nvidia":
            smi = find_exe("nvidia-smi")
            code, out = run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]) if smi else (1, "")
            if code == 0 and out:
                name, m = out.splitlines()[0].rsplit(",", 1)
                g.update(name=name.strip(), vram_gb=int(m) / 1024, driver_ok=True)
            else:
                g["note"] = "NVIDIA driver missing or not working"
        elif vendor == "amd":
            g["driver_ok"] = "advanced micro devices" in provider and g["vram_gb"] >= 2
            if g["vram_gb"] < 2:
                g["note"] = "integrated graphics (uses system RAM)"
            elif not g["driver_ok"]:
                g["note"] = "AMD driver missing"
        elif vendor == "intel":
            g["note"] = "Intel graphics: the model will run on the CPU"
        else:
            g["note"] = "Windows is using its basic display driver (no graphics driver installed)"
        found.append(g)
    return found


def gpus():
    """Returns a list of {vendor, name, vram_gb, driver_ok, note}."""
    if IS_WIN:
        return gpus_windows()
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
    if IS_WIN:
        return {
            "nvidia": "Install the latest driver from nvidia.com/drivers (or the NVIDIA App), then restart.",
            "amd": ("Install AMD Software: Adrenalin Edition from amd.com/support, then restart. "
                    "Older Radeon cards may not be supported for AI and will use the CPU instead."),
            "basic": ("Install your graphics card's driver: NVIDIA (nvidia.com/drivers), AMD (amd.com/support) "
                      "or Intel (intel.com/support), then restart and run setup again."),
        }.get(g["vendor"], ""), False
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


def wait_for_ollama(seconds=90):
    """Ollama can take a while to start, especially right after installing. Wait for it, and on
    Windows start the Ollama app ourselves if it hasn't started on its own."""
    have = ollama_up()
    if have is not None:
        return have
    say("\nWaiting for Ollama to start…", "c")
    started = False
    for i in range(seconds // 3):
        if i == 3 and not started:
            started = True
            try:
                app = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama app.exe") if IS_WIN else ""
                if IS_WIN and os.path.exists(app):
                    subprocess.Popen([app], close_fds=True)
                elif find_exe("ollama"):
                    subprocess.Popen([find_exe("ollama"), "serve"], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, close_fds=True,
                                     creationflags=0x08000000 if IS_WIN else 0)
            except OSError:
                pass
        time.sleep(3)
        have = ollama_up()
        if have is not None:
            return have
    return None


def pull(model):
    say(f"\nDownloading {model} (this can take a while)…", "c")
    return subprocess.run([find_exe("ollama") or "ollama", "pull", model]).returncode == 0


def set_model(model):
    from town.config import load_config
    load_config(ROOT)                     # makes sure config.json exists
    with open(CONFIG, encoding="utf-8") as f:
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
                    say("  Reboot, then run setup again.", "y")
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
    if not find_exe("ollama"):
        say("\nOllama isn't installed.", "y")
        if IS_WIN:
            if pm and ask("Install Ollama now? (uses winget, Windows' official installer)"):
                subprocess.run(install_cmd("winget", "Ollama.Ollama"), shell=True)
            if not find_exe("ollama"):
                say("Install it from ollama.com/download, then run setup again.", "d")
                return 0
            if IS_WIN:
                say("Ollama may open its own chat window. You can close it: it keeps running in the background.", "d")
        else:
            if ask("Install Ollama now? (runs the official installer from ollama.com, needs your password)"):
                subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True)
            if not find_exe("ollama"):
                say("Install it later with:  curl -fsSL https://ollama.com/install.sh | sh", "d")
                return 0
    have = wait_for_ollama()
    if have is None:
        say("\nOllama is installed but didn't start. " + ("Open Ollama from the Start menu, then run setup again."
            if IS_WIN else "Start it with:  sudo systemctl start ollama   (or: ollama serve)"), "y")
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
    if IS_WIN:
        extras = [("docker", "Docker.DockerDesktop", "the Fabrication Hangar's safe sandbox for running its programs")]
        say("  ✓ music: Windows' own media player (VLC or mpv also work if installed)", "g")
    else:
        extras = [("bwrap", "bubblewrap", "the Fabrication Hangar's safe sandbox for running its programs"),
                  ("mpv", "mpv", "the Radio Tower, to play music out loud")]
    missing = []
    for exe, pkg, why in extras:
        if find_exe(exe):
            say(f"  ✓ {exe}: {why}", "g")
            if exe == "docker" and ask("  Download the sandbox's Python image now (about 50 MB)?"):
                subprocess.run([find_exe("docker"), "pull", "python:3.12-slim"])
        else:
            say(f"  ✗ {exe}: needed for {why}", "y")
            missing.append(pkg)
    if missing and pm:
        cmd = install_cmd(pm, " ".join(missing))
        say(f"  Install with: {cmd}", "d")
        if ask("  Install now?" + ("" if IS_WIN else " (needs your password)")):
            subprocess.run(cmd, shell=True)
    ts = find_exe("tailscale")
    if ts:
        code, ip = run([ts, "ip", "-4"])
        if code == 0 and ip:
            say(f"  ✓ tailscale: phone access at {ip.splitlines()[0]}:8080", "g")
            if IS_WIN:
                windows_firewall()
        else:
            say("  ✗ tailscale is installed but not connected. " +
                ("Open Tailscale and sign in." if IS_WIN else "Run: sudo tailscale up"), "y")
    else:
        say("  ✗ tailscale: needed for Hub Connect S. Install: " +
            ("winget install -e --id tailscale.tailscale" if IS_WIN else "curl -fsSL https://tailscale.com/install.sh | sh"), "y")

    from town.config import load_config
    music = os.path.expanduser(load_config(ROOT).get("radio", {}).get("music_dir", "~/Music"))
    if os.path.isdir(music):
        say(f"  ✓ music folder: {music}", "g")
    else:
        say(f"  ✗ music folder {music} not found. Set radio.music_dir in config.json", "y")

    if IS_WIN:
        return windows_autostart()
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


FW_RULE = "Stellar Hub (Tailscale phone access)"


def windows_firewall():
    """Lets Hub Connect S reach the hub through Windows Firewall, but only from Tailscale addresses
    (100.64.0.0/10), never from the rest of your network or the internet."""
    code, out = run(["netsh", "advfirewall", "firewall", "show", "rule", f"name={FW_RULE}"])
    if code == 0 and FW_RULE in out:
        say("  ✓ Windows Firewall lets your phone in over Tailscale", "g")
        return
    say("  ✗ Windows Firewall may block your phone (that's the usual cause of the app saying 'Connecting…')", "y")
    if not ask("  Add a firewall rule for Stellar Hub, allowing Tailscale addresses only? (Windows will ask for permission)"):
        say("    You can add it later by running setup again.", "d")
        return
    from town.config import load_config
    port = int(load_config(ROOT).get("port", 8080))
    args = (f'advfirewall firewall add rule name="{FW_RULE}" dir=in action=allow protocol=TCP '
            f'localport={port} remoteip=100.64.0.0/10 profile=any')
    ps = f"Start-Process netsh -ArgumentList '{args}' -Verb RunAs -Wait"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps])
    code, out = run(["netsh", "advfirewall", "firewall", "show", "rule", f"name={FW_RULE}"])
    say("  ✓ Firewall rule added" if code == 0 and FW_RULE in out else "  ✗ The rule wasn't added (permission declined?)",
        "g" if code == 0 and FW_RULE in out else "y")


def windows_autostart():
    startup = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    vbs = os.path.join(startup, "Stellar Hub.vbs")
    if os.path.exists(vbs):
        say("  ✓ starts automatically when you sign in to Windows", "g")
        say("\nAll set. Open Stellar Hub from the Start menu.\n", "b")
        return 0
    if os.path.isdir(startup) and ask("\nStart Stellar Hub automatically (in the background) when you sign in?"):
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = sys.executable
        run_py = os.path.join(ROOT, "run.py")
        with open(vbs, "w", encoding="utf-8") as f:
            f.write('Set sh = CreateObject("WScript.Shell")\r\n'
                    f'sh.CurrentDirectory = "{ROOT}"\r\n'
                    f'sh.Run """{pyw}"" ""{run_py}""", 0, False\r\n')
        say("  ✓ It will start in the background each time you sign in. Dashboard: http://localhost:8080", "g")
        say("    (To turn this off, delete 'Stellar Hub.vbs' from your Startup folder: Win+R → shell:startup)", "d")
    say("\nAll set. Open Stellar Hub from the Start menu.\n", "b")
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except KeyboardInterrupt:
        print()
    if PAUSE:
        try:
            input("Press Enter to close…")
        except EOFError:
            pass
    sys.exit(code)
