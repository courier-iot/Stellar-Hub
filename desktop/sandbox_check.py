"""Checks the coding sandbox the Fab Hangar uses, and gets it ready.

Windows: Docker Desktop must be installed and running; this downloads the small Python image the sandbox runs code in.
Linux: bubblewrap (bwrap) is used if it's installed, otherwise Docker.

Run it any time:  python sandbox_check.py --pause"""
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from town.osutil import IS_WIN, NO_WINDOW, find_exe  # noqa: E402

IMAGE = "python:3.12-slim"


def run(cmd, timeout):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=NO_WINDOW)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def main():
    print("Stellar Hub · coding sandbox check\n")
    if not IS_WIN and shutil.which("bwrap"):
        print("✓ bubblewrap is installed. The sandbox is ready.")
        return 0
    docker = find_exe("docker")
    if not docker:
        print("✗ Docker wasn't found.")
        print("  Weekly coding challenges and programs need it. Install Docker Desktop from")
        print("  https://www.docker.com/products/docker-desktop/ , start it once, then run this check again.")
        return 1
    print(f"✓ Docker found: {docker}")
    rc, out = run([docker, "info", "--format", "{{.ServerVersion}}"], 30)
    if rc != 0 and IS_WIN:
        desk = os.path.expandvars(r"%ProgramFiles%\Docker\Docker\Docker Desktop.exe")
        if os.path.isfile(desk):
            print("… Docker Desktop isn't running. Starting it (this can take a minute)…")
            subprocess.Popen([desk], creationflags=NO_WINDOW)
            for _ in range(36):
                time.sleep(5)
                rc, out = run([docker, "info", "--format", "{{.ServerVersion}}"], 30)
                if rc == 0:
                    break
    if rc != 0:
        print("✗ Docker is installed but not running. Start Docker Desktop, then run this check again.")
        return 1
    print(f"✓ Docker is running (engine {out.splitlines()[0] if out else '?'}).")
    rc, _ = run([docker, "image", "inspect", IMAGE], 30)
    if rc != 0:
        print(f"… Downloading the sandbox's Python image ({IMAGE}, about 50 MB)…")
        rc, out = run([docker, "pull", IMAGE], 1800)
        if rc != 0:
            print(f"✗ Couldn't download it: {out[-300:]}")
            return 1
    print(f"✓ Sandbox image ready ({IMAGE}).")
    rc, out = run([docker, "run", "--rm", "--network", "none", IMAGE, "python", "-c", "print(6*7)"], 120)
    if rc == 0 and out.strip().endswith("42"):
        print("✓ Test run worked. Coding challenges are good to go.")
        return 0
    print(f"✗ The test run failed: {out[-300:]}")
    return 1


if __name__ == "__main__":
    code = main()
    if "--pause" in sys.argv:
        input("\nPress Enter to close…")
    sys.exit(code)
