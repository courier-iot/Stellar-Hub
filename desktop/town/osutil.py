"""Small helpers so Stellar Hub runs the same on Linux and Windows."""
import os
import shutil
import subprocess

IS_WIN = os.name == "nt"
# On Windows, keep helper programs (players, tailscale, docker) from flashing console windows.
NO_WINDOW = 0x08000000 if IS_WIN else 0

_KNOWN = {
    "tailscale": [r"%ProgramFiles%\Tailscale\tailscale.exe"],
    "ollama": [r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"],
    "vlc": [r"%ProgramFiles%\VideoLAN\VLC\vlc.exe", r"%ProgramFiles(x86)%\VideoLAN\VLC\vlc.exe"],
    "mpv": [r"%LOCALAPPDATA%\Programs\mpv\mpv.exe"],
    "docker": [r"%ProgramFiles%\Docker\Docker\resources\bin\docker.exe"],
    "nvidia-smi": [r"%SystemRoot%\System32\nvidia-smi.exe"],
}


def find_exe(name):
    """Finds a program on PATH, or in its usual install folder on Windows."""
    found = shutil.which(name)
    if found:
        return found
    if IS_WIN:
        for p in _KNOWN.get(name, []):
            p = os.path.expandvars(p)
            if os.path.isfile(p):
                return p
    return None


def run_quiet(cmd, timeout=15):
    """Runs a command and returns (exit code, stdout), never raising."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=NO_WINDOW)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


# Plays one audio file with Windows' built-in media player (no install needed). The path comes in
# through an environment variable so song names with quotes or symbols are safe.
WIN_PLAYER_PS = r"""
Add-Type -AssemblyName PresentationCore
$p = New-Object System.Windows.Media.MediaPlayer
$p.Volume = [double]$env:STELLAR_VOLUME
$p.Open([Uri]$env:STELLAR_SONG)
$t = 0
while (-not $p.NaturalDuration.HasTimeSpan -and $t -lt 50) { Start-Sleep -Milliseconds 200; $t++ }
$p.Play()
if ($p.NaturalDuration.HasTimeSpan) { Start-Sleep -Seconds ([math]::Ceiling($p.NaturalDuration.TimeSpan.TotalSeconds) + 1) }
"""
