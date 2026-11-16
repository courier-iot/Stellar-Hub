"""Checks GitHub for new Stellar Hub releases and installs them when you press Update.

- Windows (installed with the Setup .exe): downloads the new installer, checks its SHA-256, runs it
  silently, and the installer starts Stellar Hub again in the background.
- Linux (or the zip version anywhere): backs up the resident, downloads the release zip, checks its
  SHA-256, replaces the program files (never data/ or config.json), then restarts.
Nothing is installed without you pressing Update.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile

from .osutil import IS_WIN, NO_WINDOW

UA = {"User-Agent": "StellarHub-Updater", "Accept": "application/vnd.github+json"}
CHECK_EVERY = 12 * 3600
KEEP = {"data", "config.json"}          # never replaced by an update


def parse_version(v):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(v or ""))
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Updater:
    def __init__(self, root, cfg, db, agent):
        self.root, self.cfg, self.db, self.agent = root, cfg, db, agent
        self.lock = threading.Lock()
        self.read_watchdog_result()

    @property
    def result_path(self):
        return os.path.join(self.root, "data", "update_result.json")

    def read_watchdog_result(self):
        """After a Windows update, the watchdog leaves a note saying whether the installer succeeded."""
        prog = self.db.get("update_progress") or {}
        if str(prog.get("stage", "")).startswith("Installing") and not os.path.exists(self.result_path):
            self._progress("The last update didn't finish", "Stellar Hub restarted on v" + self.current() + ". You can try "
                           "again, or run the installer from the latest release yourself (your resident and settings are kept).")
        try:
            with open(self.result_path, encoding="utf-8-sig") as f:
                r = json.load(f)
            os.remove(self.result_path)
        except (OSError, ValueError):
            return
        cur = self.current()
        if r.get("code") == 0 and parse_version(cur) >= parse_version(r.get("version")):
            self._progress(f"Updated to v{cur} ✓")
            self.agent.add_event("update", f"⬆️ Stellar Hub updated to v{cur}", "The hub restarted on the new version.")
        else:
            self._progress("Update failed", f"The installer for v{r.get('version')} stopped (code {r.get('code')}), so "
                                            f"Stellar Hub restarted on v{cur}. Details: data/updates/install.log. "
                                            f"You can try again, or run the new installer from the release page.")

    def _windows_watchdog(self, exe, version):
        """A small hidden PowerShell helper that outlives the hub: it waits for the hub to close, runs the
        installer, records the result, and makes sure Stellar Hub is running afterwards no matter what."""
        port = int(self.cfg.get("port", 8080))
        logs = os.path.join(self.root, "data", "updates")
        os.makedirs(logs, exist_ok=True)
        q = lambda s: str(s).replace("'", "''")   # PowerShell single-quote escaping
        pyw = os.path.join(self.root, "python", "pythonw.exe")
        script = f"""$ErrorActionPreference = 'SilentlyContinue'
$hubPid = {os.getpid()}
for ($i = 0; $i -lt 120 -and (Get-Process -Id $hubPid -ErrorAction SilentlyContinue); $i++) {{ Start-Sleep -Milliseconds 500 }}
# any other copy of Stellar Hub still running from this folder would block the install: close it
$appDir = '{q(self.root)}'
Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -and $_.Path.StartsWith($appDir, [StringComparison]::OrdinalIgnoreCase) }} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$code = 1
try {{
  $p = Start-Process -FilePath '{q(exe)}' -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LOG="{q(os.path.join(logs, "install.log"))}"' -PassThru
  # wait for the installer itself only (not the Stellar Hub it starts afterwards), at most 10 minutes
  if ($p.WaitForExit(600000)) {{ $code = $p.ExitCode }} else {{ $code = 98; try {{ $p.Kill() }} catch {{ }} }}
}} catch {{ $code = 99 }}
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Set-Content -Path '{q(self.result_path)}' -Value ('{{"version": "{q(version)}", "code": ' + $code + ', "ts": ' + $ts + '}}') -Encoding UTF8
for ($i = 0; $i -lt 25; $i++) {{
  try {{ $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', {port}); $c.Close(); exit 0 }} catch {{ }}
  Start-Sleep -Seconds 1
}}
Start-Process -FilePath '{q(pyw)}' -ArgumentList '"{q(os.path.join(self.root, "run.py"))}"' -WorkingDirectory '{q(self.root)}'
"""
        path = os.path.join(logs, "watchdog.ps1")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(script)
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", path],
                         close_fds=True, creationflags=0x00000008 | NO_WINDOW)   # DETACHED_PROCESS

    @property
    def repo(self):
        return self.cfg.get("update", {}).get("repo", "courier-iot/Stellar-Hub")

    def current(self):
        for p in (os.path.join(self.root, "VERSION"), os.path.join(self.root, "..", "VERSION")):
            if os.path.exists(p):
                with open(p) as f:
                    return f.read().strip()
        return "0.0.0"

    def install_kind(self):
        return "installer" if IS_WIN and os.path.isdir(os.path.join(self.root, "python")) else "zip"

    def state(self):
        st = dict(self.db.get("update") or {})
        st["current"] = self.current()
        st["kind"] = self.install_kind()
        st["repo"] = self.repo
        st["progress"] = self.db.get("update_progress")
        st["available"] = parse_version(st.get("latest")) > parse_version(st["current"])
        return st

    # ------------------------------------------------------------ checking
    def check(self, force=False):
        if getattr(self, "_checking", False):
            return self.state()
        self._checking = True
        try:
            return self._check(force)
        finally:
            self._checking = False

    def _check(self, force=False):
        st = self.db.get("update") or {}
        if not force and time.time() - st.get("checked", 0) < CHECK_EVERY:
            return self.state()
        if not self.cfg.get("update", {}).get("check", True) and not force:
            return self.state()
        try:
            rel = self._newest_release()
            tag = rel.get("tag_name", "")
            assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
            st = {"checked": time.time(), "latest": tag.lstrip("v"), "tag": tag, "assets": assets,
                  "url": rel.get("html_url", ""), "error": None}
            if parse_version(tag) > parse_version(self.current()):
                st["changelog"] = self._changelog(tag)
                if (self.db.get("update") or {}).get("notified") != tag:
                    self.agent.add_event("update", f"⬆️ Stellar Hub {tag} is available",
                                         "Open the dashboard on the hub computer and press Update.")
                st["notified"] = tag
        except Exception as e:
            st = {**st, "checked": time.time(), "error": f"Couldn't check for updates: {e}"}
        self.db.set("update", st)
        return self.state()

    def _newest_release(self):
        """The highest version on GitHub. Doesn't trust the "Latest" label, which GitHub can leave on an old release."""
        rels = json.loads(_get(f"https://api.github.com/repos/{self.repo}/releases?per_page=30").decode())
        if not isinstance(rels, list):
            raise ValueError(f"GitHub answered: {str(rels)[:200]}")
        want = ".exe" if self.install_kind() == "installer" else ".zip"
        good = [r for r in rels if not r.get("draft") and not r.get("prerelease") and parse_version(r.get("tag_name")) > (0, 0, 0)
                and any(a.get("name", "").endswith(want) for a in r.get("assets", []))]
        if not good:
            raise ValueError(f"no finished release with a {want} file found on GitHub yet")
        return max(good, key=lambda r: parse_version(r.get("tag_name")))

    def _changelog(self, tag):
        """The CHANGELOG.md entries newer than the running version."""
        try:
            text = _get(f"https://raw.githubusercontent.com/{self.repo}/{tag}/CHANGELOG.md").decode("utf-8", "replace")
        except Exception:
            return ""
        cur = parse_version(self.current())
        out, keep = [], False
        for line in text.splitlines():
            if line.startswith("## "):
                keep = parse_version(line) > cur
            if keep:
                out.append(line)
        return "\n".join(out).strip()[:6000]

    # ------------------------------------------------------------ installing
    def apply(self):
        if not self.lock.acquire(blocking=False):
            return {"ok": False, "message": "An update is already running."}
        st = self.check(force=True)
        if not st.get("available"):
            self.lock.release()
            return {"ok": False, "message": st.get("error") or "Stellar Hub is already up to date."}
        threading.Thread(target=self._apply, args=(st,), daemon=True).start()
        return {"ok": True, "message": f"Updating to v{st['latest']}…"}

    def _progress(self, stage, error=None):
        self.db.set("update_progress", {"stage": stage, "error": error, "ts": time.time()})

    def _download_verified(self, name, assets, folder):
        if name not in assets:
            raise RuntimeError(f"The release has no {name}")
        sums = assets.get(name + ".sha256")
        if not sums:
            raise RuntimeError(f"The release has no checksum for {name}, so it can't be verified")
        expected = _get(sums).decode().split()[0].strip().lower()
        path = os.path.join(folder, name)
        h = hashlib.sha256()
        req = urllib.request.Request(assets[name], headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
        if h.hexdigest() != expected:
            raise RuntimeError(f"{name} failed its checksum check (download damaged or tampered with)")
        return path

    def _apply(self, st):
        tag, version, assets = st["tag"], st["latest"], st.get("assets", {})
        work = tempfile.mkdtemp(prefix="stellarhub-update-")
        try:
            self._progress("Backing up your resident…")
            self.agent.backup_now()
            if self.install_kind() == "installer":
                self._progress("Downloading the installer…")
                exe = self._download_verified(f"StellarHub-Setup-v{version}.exe", assets, work)
                self._progress("Installing. Stellar Hub will restart by itself in a minute.")
                self.agent.mem.add("observation", f"The colony is being upgraded to {tag}.", "home", 6)
                self._windows_watchdog(exe, version)
                self._exit_soon(restart=False)
                return
            self._progress("Downloading the update…")
            z = self._download_verified(f"StellarHub-v{version}.zip", assets, work)
            self._progress("Installing the new files…")
            self._install_zip(z, work)
            self._progress(f"Updated to {tag} ✓ Restarting…")
            self.agent.mem.add("observation", f"The colony was upgraded to {tag}.", "home", 6)
            self._exit_soon(restart=True)
        except Exception as e:
            self._progress("Update failed", str(e))
            self.lock.release()
        finally:
            if self.install_kind() != "installer":
                shutil.rmtree(work, ignore_errors=True)

    def _install_zip(self, z, work):
        out = os.path.join(work, "x")
        with zipfile.ZipFile(z) as zf:
            for m in zf.infolist():                          # refuse anything that escapes the folder
                target = os.path.realpath(os.path.join(out, m.filename))
                if not target.startswith(os.path.realpath(out) + os.sep):
                    raise RuntimeError(f"Unsafe path in update: {m.filename}")
            zf.extractall(out)
        src = os.path.join(out, "StellarHub")
        if not os.path.isfile(os.path.join(src, "run.py")):
            raise RuntimeError("The update zip doesn't look like Stellar Hub")
        for name in os.listdir(src):
            if name in KEEP:
                continue
            s, d = os.path.join(src, name), os.path.join(self.root, name)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        for sh in ("start.sh", "setup.sh", "install-service.sh"):
            p = os.path.join(self.root, sh)
            if os.path.exists(p) and not IS_WIN:
                os.chmod(p, 0o755)

    def _exit_soon(self, restart):
        def go():
            time.sleep(2)
            try:
                self.agent.act_stop_music({}, 0)
            except Exception:
                pass
            if restart:
                if os.environ.get("INVOCATION_ID"):          # running as a systemd service: it restarts us
                    os._exit(75)
                env = dict(os.environ, STELLAR_RESTARTING="1")
                subprocess.Popen([sys.executable] + sys.argv, cwd=self.root, env=env, close_fds=True,
                                 creationflags=NO_WINDOW)
            os._exit(0)
        threading.Thread(target=go, daemon=True).start()
