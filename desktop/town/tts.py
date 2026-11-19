"""The resident's voice: turns text into a WAV file.

Uses the best voice this computer has:
  1. Piper (natural, offline): installed from the dashboard's Voice section into data/piper/
  2. Windows' built-in voice (System.Speech), always there on Windows
  3. espeak-ng on Linux, if installed
Nothing is sent anywhere: speech is made on this computer."""
import glob
import os
import shutil
import subprocess
import tarfile
import threading
import urllib.request
import zipfile

from .osutil import IS_WIN, NO_WINDOW

PIPER_RELEASE = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/"
PIPER_ZIP = "piper_windows_amd64.zip" if IS_WIN else "piper_linux_x86_64.tar.gz"
VOICES = {   # name: Hugging Face path under rhasspy/piper-voices
    "amy": "en/en_US/amy/medium/en_US-amy-medium",
    "ryan": "en/en_US/ryan/medium/en_US-ryan-medium",
    "lessac": "en/en_US/lessac/medium/en_US-lessac-medium",
    "joe": "en/en_US/joe/medium/en_US-joe-medium",
    "alba": "en/en_GB/alba/medium/en_GB-alba-medium",
    "cori": "en/en_GB/cori/medium/en_GB-cori-medium",
    "jenny": "en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium",
    "northern": "en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium",
}
VOICE_ABOUT = {"amy": "American, warm (female)", "ryan": "American, clear (male)", "lessac": "American, bright (female)",
               "joe": "American, relaxed (male)", "alba": "Scottish (female)", "cori": "English, soft (female)",
               "jenny": "English, cheerful (female)", "northern": "Northern English (male)"}
SAMPLE_BASE = "https://rhasspy.github.io/piper-samples/samples/"   # short recordings of each voice, to hear before downloading
VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"

SAPI_PS = r"""[Console]::InputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$v = $env:STELLAR_VOICE
if ($v) { try { $s.SelectVoice($v) } catch {} }
$r = 0; if ($env:STELLAR_RATE) { $r = [int]$env:STELLAR_RATE }
$s.Rate = $r
$s.SetOutputToWaveFile($env:STELLAR_OUT)
$s.Speak([Console]::In.ReadToEnd())
$s.Dispose()
"""


class Voice:
    def __init__(self, data_dir, cfg):
        self.dir = os.path.join(data_dir, "piper")
        self.cfg = cfg
        self.install_state = None
        self.last_error = None
        self.lock = threading.Lock()

    # ------------------------------------------------------------ which voice
    def piper(self):
        exe = self.cfg.get("piper_path") or ""
        if not exe:
            for p in (os.path.join(self.dir, "piper", "piper.exe" if IS_WIN else "piper"), shutil.which("piper") or ""):
                if p and os.path.exists(p):
                    exe = p
                    break
        want = os.path.basename(VOICES.get(self.cfg.get("piper_voice", "amy"), "amy"))
        models = sorted(glob.glob(os.path.join(self.dir, "*.onnx")))
        model = next((m for m in models if os.path.basename(m) == want + ".onnx"),
                     next((m for m in models if want in os.path.basename(m)), models[0] if models else None))
        return (exe, model) if exe and model else (None, None)

    def backend(self):
        if not self.cfg.get("enabled", True):
            return None
        if self.piper()[0]:
            return "piper"
        if IS_WIN:
            return "windows"
        if shutil.which("espeak-ng"):
            return "espeak"
        return None

    def status(self):
        b = self.backend()
        names = {"piper": "Piper (natural voice)", "windows": "Windows built-in voice", "espeak": "espeak-ng", None: "none"}
        exe, model = self.piper()
        have = self.installed_voices()
        if b == "piper" and model:
            names["piper"] = f"Piper: {next((v for v, p in VOICES.items() if os.path.basename(p) in model), 'custom')}"
        return {"backend": b, "name": names[b], "enabled": self.cfg.get("enabled", True),
                "piper_installed": bool(exe), "install": self.install_state,
                "voices": [{"id": v, "about": VOICE_ABOUT.get(v, ""), "installed": v in have,
                            "sample": SAMPLE_BASE + p.rsplit("/", 1)[0] + "/speaker_0.mp3"} for v, p in VOICES.items()],
                "voice": self.cfg.get("piper_voice", "amy"), "last_error": self.last_error}

    def installed_voices(self):
        files = {os.path.basename(m) for m in glob.glob(os.path.join(self.dir, "*.onnx"))}
        return [v for v, p in VOICES.items() if os.path.basename(p) + ".onnx" in files]

    def install_voice(self, voice):
        """v0.15: download another voice for an installed Piper (no need to reinstall Piper)."""
        if voice not in VOICES or voice in self.installed_voices():
            return self.install_state
        if self.install_state and self.install_state.get("running"):
            return self.install_state
        self.install_state = {"running": True, "step": f"Downloading the {voice} voice…"}

        def go():
            try:
                os.makedirs(self.dir, exist_ok=True)
                path = VOICES[voice]
                name = os.path.basename(path)
                self._download(VOICE_BASE + path + ".onnx", os.path.join(self.dir, name + ".onnx"))
                self._download(VOICE_BASE + path + ".onnx.json", os.path.join(self.dir, name + ".onnx.json"))
                self.install_state = {"running": False, "step": f"The {voice} voice is ready ✓", "ok": True}
            except Exception as e:
                self.install_state = {"running": False, "step": f"Couldn't download the {voice} voice", "error": str(e)}
        threading.Thread(target=go, daemon=True).start()
        return self.install_state

    # ------------------------------------------------------------ speaking
    @staticmethod
    def pace(mood):
        """v0.14.1: speaking speed from its mood: 1.0 normal, above 1 slower, below 1 faster."""
        m = (mood or "").lower()
        if any(w in m for w in ("excited", "thrilled", "joy", "elated", "giddy", "eager", "playful", "festive")):
            return 0.9
        if any(w in m for w in ("sleepy", "tired", "calm", "sad", "wistful", "peaceful", "quiet", "melancholy", "drowsy")):
            return 1.15
        return 1.0

    def speak(self, text, out_path, mood=None):
        """Writes text as speech to out_path (WAV), paced by mood. Returns the backend used, or None."""
        pace = self.pace(mood)
        text = " ".join(str(text).split())[:4000]
        if not text:
            return None
        b = self.backend()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with self.lock:
            try:
                if b == "piper":
                    exe, model = self.piper()
                    r = subprocess.run([exe, "--model", model, "--output_file", out_path, "--length_scale", str(pace)],
                                       input=text.encode("utf-8"),
                                       capture_output=True, timeout=180, creationflags=NO_WINDOW)
                    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                        self.last_error = None
                    else:                         # v0.15: say why, and fall back to the built-in voice for now
                        err = (r.stderr or b"").decode("utf-8", "replace").strip().splitlines()
                        self.last_error = "Piper couldn't speak: " + (err[-1][:200] if err else f"exit {r.returncode}")
                        b = "windows" if IS_WIN else ("espeak" if shutil.which("espeak-ng") else None)
                if b == "windows":
                    env = dict(os.environ, STELLAR_OUT=out_path, STELLAR_VOICE=self.cfg.get("windows_voice", ""),
                               STELLAR_RATE=str(round((1 - pace) * 10)))
                    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", SAPI_PS],
                                   input=text.encode("utf-8"), capture_output=True, timeout=180, env=env,
                                   creationflags=NO_WINDOW)
                elif b == "espeak":
                    subprocess.run(["espeak-ng", "-w", out_path, "-s", str(int(165 / pace)), "--stdin"], input=text.encode("utf-8"),
                                   capture_output=True, timeout=180)
                else:
                    return None
            except (OSError, subprocess.SubprocessError):
                return None
        return b if os.path.exists(out_path) and os.path.getsize(out_path) > 100 else None

    # ------------------------------------------------------------ installing Piper
    def install_piper(self):
        if self.install_state and self.install_state.get("running"):
            return self.install_state
        self.install_state = {"running": True, "step": "Starting…"}
        threading.Thread(target=self._install, daemon=True).start()
        return self.install_state

    def _download(self, url, path):
        req = urllib.request.Request(url, headers={"User-Agent": "StellarHub"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path + ".part", "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(path + ".part", path)

    def _install(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            archive = os.path.join(self.dir, PIPER_ZIP)
            self.install_state["step"] = "Downloading Piper…"
            self._download(PIPER_RELEASE + PIPER_ZIP, archive)
            self.install_state["step"] = "Unpacking…"
            root = os.path.realpath(self.dir)
            if archive.endswith(".zip"):
                with zipfile.ZipFile(archive) as z:
                    for n in z.namelist():
                        if not os.path.realpath(os.path.join(root, n)).startswith(root + os.sep):
                            raise ValueError("unsafe file in the Piper download")
                    z.extractall(root)
            else:
                with tarfile.open(archive) as t:
                    for m in t.getmembers():
                        if not os.path.realpath(os.path.join(root, m.name)).startswith(root + os.sep) or m.issym() or m.islnk():
                            raise ValueError("unsafe file in the Piper download")
                    t.extractall(root)
            os.remove(archive)
            voice = self.cfg.get("piper_voice", "amy")
            path = VOICES.get(voice, VOICES["amy"])
            name = os.path.basename(path)
            self.install_state["step"] = f"Downloading the {voice} voice…"
            self._download(VOICE_BASE + path + ".onnx", os.path.join(self.dir, name + ".onnx"))
            self._download(VOICE_BASE + path + ".onnx.json", os.path.join(self.dir, name + ".onnx.json"))
            if not IS_WIN:
                exe = os.path.join(self.dir, "piper", "piper")
                if os.path.exists(exe):
                    os.chmod(exe, 0o755)
            self.install_state = {"running": False, "step": "Piper is installed ✓", "ok": True}
        except Exception as e:
            self.install_state = {"running": False, "step": "Install failed", "error": str(e)}
