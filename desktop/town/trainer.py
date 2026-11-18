"""v0.14: real training. The resident learns from its own life.

How a training run goes (Training tab → Train now, or automatically at night):
1. Check: a supported model, enough graphics memory and disk space, the training toolkit installed.
2. Exam on today's model, for a score to beat.
3. Build the examples: corrections, exam answers and its own reviewed writing (the Training tab's settings).
4. Rest: the resident goes to sleep and Ollama lets go of the graphics card.
5. Train a small LoRA adapter on the original base model (never on top of an older adapter, so mistakes don't pile up).
6. Turn the adapter into a GGUF file and make a new Ollama model: stellar-<name>:v<N> = base + adapter.
7. Exam on the new model. It goes live only if it reaches the pass mark and doesn't score much worse than before.
   Otherwise it's thrown away (auto rollback) and the resident keeps its current model.
You can switch to any kept version, or back to the plain base model, at any time.

The training toolkit (PyTorch and friends, about 4-6 GB) lives in data/trainer/toolkit, made with uv, so the hub's own
Python never changes. The base model's original files are downloaded once from Hugging Face (no account needed for
the supported models).
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKER = os.path.join(HERE, "trainer", "train_lora.py")
IS_WIN = os.name == "nt"
LLAMA_CPP_TAG = "b6000"     # llama.cpp version whose converter turns the adapter into GGUF

# Ollama model -> (Hugging Face repo with the original weights, billions of parameters)
BASES = {
    "qwen2.5:1.5b": ("Qwen/Qwen2.5-1.5B-Instruct", 1.5), "qwen2.5:3b": ("Qwen/Qwen2.5-3B-Instruct", 3.1),
    "qwen2.5:7b": ("Qwen/Qwen2.5-7B-Instruct", 7.6), "qwen2.5:14b": ("Qwen/Qwen2.5-14B-Instruct", 14.7),
    "qwen3:0.6b": ("Qwen/Qwen3-0.6B", 0.6), "qwen3:1.7b": ("Qwen/Qwen3-1.7B", 1.7), "qwen3:4b": ("Qwen/Qwen3-4B", 4.0),
    "qwen3:8b": ("Qwen/Qwen3-8B", 8.2), "qwen3:14b": ("Qwen/Qwen3-14B", 14.8),
    "llama3.2:1b": ("unsloth/Llama-3.2-1B-Instruct", 1.2), "llama3.2:3b": ("unsloth/Llama-3.2-3B-Instruct", 3.2),
    "llama3.1:8b": ("unsloth/Meta-Llama-3.1-8B-Instruct", 8.0),
}
STRENGTH = {"gentle": {"epochs": 1, "lr": 1e-4, "rank": 8}, "normal": {"epochs": 2, "lr": 1.5e-4, "rank": 16},
            "strong": {"epochs": 3, "lr": 2e-4, "rank": 16}}
STAGES = ["check", "exam_before", "examples", "rest", "download", "load", "prepare", "train", "save", "convert",
          "create", "exam_after", "decide", "done"]
STAGE_LABELS = {"check": "Checking everything's ready", "exam_before": "Exam on today's model", "examples": "Building examples",
                "rest": "Resting so the graphics card is free", "download": "Downloading the base model (first time only)",
                "load": "Loading the base model", "prepare": "Preparing examples", "train": "Training",
                "save": "Saving the adapter", "convert": "Converting for Ollama", "create": "Making the new model",
                "exam_after": "Exam on the new model", "decide": "Deciding", "done": "Finished"}


def base_key(model):
    m = (model or "").lower().removesuffix(":latest")
    return m if m in BASES else None


def need_vram_gb(params_b):
    """Rough graphics memory a 4-bit QLoRA run needs at 512 tokens with gradient checkpointing."""
    return round(params_b * 0.6 + 1.4, 1)


def find_ollama():
    exe = shutil.which("ollama")
    if exe:
        return exe
    if IS_WIN:
        p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
        if os.path.exists(p):
            return p
    return None


def gpu_info():
    smi = shutil.which("nvidia-smi")
    if not smi and IS_WIN and os.path.exists(r"C:\Windows\System32\nvidia-smi.exe"):
        smi = r"C:\Windows\System32\nvidia-smi.exe"
    if not smi:
        return None
    try:
        out = subprocess.run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=15).stdout.strip().splitlines()
        name, mem = out[0].rsplit(",", 1)
        return {"name": name.strip(), "vram_gb": round(float(mem) / 1024, 1)}
    except Exception:
        return None


class TrainerMixin:
    # ------------------------------------------------------------ places
    def tr_dir(self, *parts):
        d = os.path.join(self.data_dir, "trainer", *parts)
        return d

    def toolkit_python(self):
        p = self.tr_dir("toolkit", "Scripts", "python.exe") if IS_WIN else self.tr_dir("toolkit", "bin", "python")
        return p if os.path.exists(p) else None

    def toolkit_ready(self):
        return bool(self.toolkit_python()) and os.path.exists(self.tr_dir("toolkit", "READY"))

    def training_base(self):
        """The plain model the adapters are trained on (the model it used before any training)."""
        b = self.db.get("training_base")
        if b:
            return b
        cur = self.cfg.get("ollama", {}).get("model")
        return None if (cur or "").startswith("stellar-") else cur

    def model_versions(self):
        return self.db.get("model_versions") or []

    def training_active(self):
        r = self.db.get("train_run")
        if not (r and r.get("active")):
            return False
        t = getattr(self, "_train_thread", None)
        if t is None or not t.is_alive():         # the hub restarted mid-run: don't leave it asleep forever
            if time.time() - r.get("started", 0) > 60:
                self._set_run(active=False, stage="done",
                              result={"n": r.get("n"), "ok": False, "why": "Interrupted (the hub restarted).", "ended": time.time()})
                return False
        return True

    # ------------------------------------------------------------ status
    def trainer_status(self):
        base = self.training_base()
        key = base_key(base)
        gpu = getattr(self, "_gpu_cache", None)
        if gpu is None or time.time() - gpu[1] > 600:
            gpu = (gpu_info(), time.time())
            self._gpu_cache = gpu
        g = gpu[0]
        params = BASES[key][1] if key else None
        need = need_vram_gb(params) if params else None
        problems = []
        if not key:
            problems.append(f"'{base}' can't be trained yet. Supported: " + ", ".join(BASES) +
                            ". Pick one of these in 'Setup and model check' to train.")
        if key and not g and params > 1.8:
            problems.append("No NVIDIA graphics card found. Training on the processor only works for the 1-2B models (and is slow).")
        if key and g and need > g["vram_gb"] * 0.97:
            problems.append(f"Training {base} needs about {need} GB of graphics memory; your {g['name']} has {g['vram_gb']} GB. "
                            "A smaller model would fit.")
        free = shutil.disk_usage(self.data_dir).free / 1e9
        disk_need = (params or 3) * 2.3 + (0 if self.toolkit_ready() else 7) + 2
        if free < disk_need:
            problems.append(f"Needs about {disk_need:.0f} GB of free disk space; there's {free:.0f} GB.")
        run = self.db.get("train_run") or {}
        log_tail = []
        if run.get("log") and os.path.exists(run["log"]):
            with open(run["log"], encoding="utf-8", errors="replace") as f:
                log_tail = [l.rstrip() for l in f.readlines()[-14:]]
        return {"base": base, "base_repo": BASES[key][0] if key else None, "supported": list(BASES),
                "gpu": g, "need_vram_gb": need, "problems": problems, "can_train": not problems and self.toolkit_ready(),
                "toolkit": {"ready": self.toolkit_ready(), "installing": bool(getattr(self, "_toolkit_thread", None)
                                                                              and self._toolkit_thread.is_alive()),
                            "log": self._tail(self.tr_dir("toolkit-install.log"))},
                "live_model": self.cfg.get("ollama", {}).get("model"), "versions": self.model_versions(),
                "run": {k: v for k, v in run.items() if k != "proc"}, "run_log": log_tail,
                "stage_labels": STAGE_LABELS, "runs": (self.db.get("train_history") or [])[-10:]}

    @staticmethod
    def _tail(path, n=10):
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8", errors="replace") as f:
            return [l.rstrip() for l in f.readlines()[-n:]]

    # ------------------------------------------------------------ the toolkit
    def setup_toolkit(self):
        if getattr(self, "_toolkit_thread", None) and self._toolkit_thread.is_alive():
            return False
        self._toolkit_thread = threading.Thread(target=self._install_toolkit, daemon=True)
        self._toolkit_thread.start()
        return True

    def _install_toolkit(self):
        os.makedirs(self.tr_dir(), exist_ok=True)
        log = open(self.tr_dir("toolkit-install.log"), "w", encoding="utf-8")

        def say(m):
            log.write(m + "\n"); log.flush()

        def run(cmd, **kw):
            say("$ " + " ".join(cmd))
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)
            for line in p.stdout:
                say(line.rstrip()[:300])
            if p.wait() != 0:
                raise RuntimeError(f"{os.path.basename(cmd[0])} failed (exit {p.returncode})")

        try:
            uv = self._get_uv(say)
            env = dict(os.environ, UV_CACHE_DIR=self.tr_dir("uv-cache"), UV_PYTHON_INSTALL_DIR=self.tr_dir("python"))
            run([uv, "venv", "--python", "3.12", "--seed", self.tr_dir("toolkit")], env=env)
            py = self.toolkit_python()
            cuda = bool(gpu_info())
            torch_index = "https://download.pytorch.org/whl/cu124" if cuda else "https://download.pytorch.org/whl/cpu"
            say("Installing PyTorch (" + ("with CUDA for your NVIDIA card" if cuda else "processor only") + "). This is the big one…")
            run([uv, "pip", "install", "--python", py, "torch", "--index-url", torch_index], env=env)
            pkgs = ["transformers>=4.51", "peft>=0.13", "accelerate", "safetensors", "huggingface_hub",
                    "sentencepiece", "protobuf", "numpy"] + (["bitsandbytes>=0.45"] if cuda else [])
            run([uv, "pip", "install", "--python", py] + pkgs, env=env)
            self._get_converter(say)
            run([py, "-c", "import torch, transformers, peft; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"])
            with open(self.tr_dir("toolkit", "READY"), "w") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M"))
            say("✓ The training toolkit is ready.")
            self.add_event("training", "🎓 Training toolkit installed", "Real training is ready to go in the Training tab.")
        except Exception as e:
            say(f"✗ {e}")
        finally:
            log.close()

    def _get_uv(self, say):
        exe = self.tr_dir("uv", "uv.exe" if IS_WIN else "uv")
        if os.path.exists(exe):
            return exe
        found = shutil.which("uv")
        if found:
            return found
        arch = "aarch64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
        name = f"uv-{arch}-pc-windows-msvc.zip" if IS_WIN else f"uv-{arch}-unknown-linux-gnu.tar.gz"
        url = f"https://github.com/astral-sh/uv/releases/latest/download/{name}"
        say(f"Downloading uv (a Python installer) from {url}")
        os.makedirs(self.tr_dir("uv"), exist_ok=True)
        arc = self.tr_dir("uv", name)
        urllib.request.urlretrieve(url, arc)
        if name.endswith(".zip"):
            with zipfile.ZipFile(arc) as z:
                for m in z.namelist():
                    if m.endswith("uv.exe"):
                        with open(exe, "wb") as f:
                            f.write(z.read(m))
        else:
            import tarfile
            with tarfile.open(arc) as t:
                for m in t.getmembers():
                    if m.name.endswith("/uv") or m.name == "uv":
                        with open(exe, "wb") as f:
                            f.write(t.extractfile(m).read())
            os.chmod(exe, 0o755)
        os.remove(arc)
        return exe

    def _get_converter(self, say):
        """llama.cpp's converter scripts and its gguf library, from one release so they always match."""
        dest = self.tr_dir("llama_cpp")
        if os.path.exists(os.path.join(dest, "convert_lora_to_gguf.py")):
            return dest
        tag = self.cfg.get("training", {}).get("llama_cpp_tag", LLAMA_CPP_TAG)
        url = f"https://github.com/ggml-org/llama.cpp/archive/refs/tags/{tag}.zip"
        say(f"Downloading the GGUF converter ({url})")
        arc = self.tr_dir("llama_cpp.zip")
        urllib.request.urlretrieve(url, arc)
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(arc) as z:
            for m in z.namelist():
                rel = m.split("/", 1)[1] if "/" in m else ""
                if rel in ("convert_lora_to_gguf.py", "convert_hf_to_gguf.py") or (rel.startswith("gguf-py/") and not m.endswith("/")):
                    out = os.path.join(dest, *rel.split("/"))
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out, "wb") as f:
                        f.write(z.read(m))
        os.remove(arc)
        return dest

    # ------------------------------------------------------------ a training run
    def start_training(self, reason="manual"):
        if self.training_active():
            return False, "A training run is already going."
        st = self.trainer_status()
        if not st["toolkit"]["ready"]:
            return False, "Install the training toolkit first (Training tab)."
        if st["problems"]:
            return False, st["problems"][0]
        n = (self.db.get("train_counter") or 0) + 1
        self.db.set("train_counter", n)
        rd = self.tr_dir("runs", f"v{n}")
        os.makedirs(rd, exist_ok=True)
        run = {"active": True, "n": n, "stage": "check", "started": time.time(), "reason": reason, "dir": rd,
               "log": os.path.join(rd, "log.txt"), "progress": None}
        self.db.set("train_run", run)
        self.db.set("examples_at_last_train", len(self.training_examples()))
        self._train_thread = threading.Thread(target=self._train, args=(n,), daemon=True)
        self._train_thread.start()
        return True, f"Training run v{n} started."

    def cancel_training(self):
        p = getattr(self, "_train_proc", None)
        if p and p.poll() is None:
            p.terminate()
        self._train_cancel = True
        return True

    def _set_run(self, **kw):
        run = self.db.get("train_run") or {}
        run.update(kw)
        self.db.set("train_run", run)
        return run

    def _rlog(self, msg):
        run = self.db.get("train_run") or {}
        if run.get("log"):
            with open(run["log"], "a", encoding="utf-8") as f:
                f.write(time.strftime("[%H:%M:%S] ") + msg + "\n")

    def training_examples(self):
        """The examples as chat conversations (system, user, assistant)."""
        from . import worlds
        name = self.name
        stmt = self.persona()["statement"]["text"] if hasattr(self, "persona") else ""
        system = (f"You are {name}, a self-developing AI who lives in Stellar Hub, {worlds.WORLDS[worlds.current()]['place']}, "
                  f"made by {self.creator}." + (f" {stmt}" if stmt else ""))
        out = []
        for line in self.export_training_set().splitlines():
            if not line.strip():
                continue
            x = json.loads(line)
            out.append({"messages": [{"role": "system", "content": system}, {"role": "user", "content": x["prompt"]},
                                     {"role": "assistant", "content": x["response"]}], "kind": x["kind"]})
        return out

    def _unload_ollama(self):
        for m in {getattr(self.llm, "model", None), self.cfg.get("ollama", {}).get("model")} - {None}:
            try:
                self.llm._post("/api/generate", {"model": m, "keep_alive": 0})
            except Exception:
                pass

    def _train(self, n):
        self._train_cancel = False
        tag = f"stellar-{re.sub(r'[^a-z0-9]+', '-', self.name.lower()).strip('-') or 'resident'}:v{n}"
        base = self.training_base()
        repo, params = BASES[base_key(base)]
        st = self.training_settings()
        strength = STRENGTH.get(st.get("strength", "gentle"), STRENGTH["gentle"])
        run = self.db.get("train_run")
        rd = run["dir"]
        result = {"n": n, "tag": tag, "base": base, "started": run["started"], "ok": False}
        try:
            self.db.set("training_base", base)
            self._rlog(f"Training {tag} from {base} ({repo}), strength {st.get('strength')}.")
            # 1. score to beat
            self._set_run(stage="exam_before")
            before = self.run_exam(label=f"before v{n}") or {}
            result["before"] = before.get("score")
            self._rlog(f"Exam on today's model: {before.get('score')}%")
            # 2. examples
            self._set_run(stage="examples")
            ex = self.training_examples()
            if len(ex) < 10:
                raise RuntimeError(f"Only {len(ex)} examples. Add corrections or let it write more first (at least 10).")
            data = os.path.join(rd, "examples.jsonl")
            with open(data, "w", encoding="utf-8") as f:
                for e in ex:
                    f.write(json.dumps({"messages": e["messages"]}, ensure_ascii=False) + "\n")
            result["examples"] = len(ex)
            self._rlog(f"{len(ex)} examples written.")
            # 3. rest: free the graphics card
            self._set_run(stage="rest")
            self.mem.add("observation", "I'm going into a deep rest to learn from my own life. I'll wake up a little changed.", "home", 7)
            self._unload_ollama()
            time.sleep(3)
            # 4. train
            max_len = 384 if params >= 3 and (self._gpu_cache[0] or {}).get("vram_gb", 0) < 5 else 512
            cmd = [self.toolkit_python(), WORKER, "--base-repo", repo, "--data", data, "--out", os.path.join(rd, "adapter"),
                   "--cache", self.tr_dir("hf"), "--epochs", str(strength["epochs"]), "--lr", str(strength["lr"]),
                   "--rank", str(strength["rank"]), "--max-len", str(max_len)]
            base_dir = self._run_worker(cmd)
            if self._train_cancel:
                raise RuntimeError("Cancelled.")
            # 5. convert + make the Ollama model
            self._set_run(stage="convert")
            gguf = os.path.join(rd, "adapter.gguf")
            conv = self.tr_dir("llama_cpp")
            env = dict(os.environ, PYTHONPATH=os.path.join(conv, "gguf-py"))
            self._run_logged([self.toolkit_python(), os.path.join(conv, "convert_lora_to_gguf.py"),
                              os.path.join(rd, "adapter"), "--base", base_dir, "--outfile", gguf, "--outtype", "f16"], env=env)
            self._set_run(stage="create")
            mf = os.path.join(rd, "Modelfile")
            with open(mf, "w", encoding="utf-8") as f:
                f.write(f"FROM {base}\nADAPTER ./adapter.gguf\n")      # relative to the Modelfile (paths can have spaces)
            ollama = find_ollama()
            if not ollama:
                raise RuntimeError("Couldn't find the ollama program to make the new model.")
            self._run_logged([ollama, "create", tag, "-f", mf])
            # 6. exam on the new model
            self._set_run(stage="exam_after")
            live = getattr(self.llm, "model", None)
            self.llm.model = tag
            try:
                after = self.run_exam(label=f"v{n}") or {}
            finally:
                self.llm.model = live
            result["after"] = after.get("score")
            self._rlog(f"Exam on v{n}: {after.get('score')}% (pass mark {st['pass_mark']}%, before {before.get('score')}%)")
            # 7. decide
            self._set_run(stage="decide")
            passed = (after.get("score") or 0) >= st["pass_mark"] and (after.get("score") or 0) >= (before.get("score") or 0) - 10
            result["passed"] = passed
            if passed:
                self._go_live(tag, n, after.get("score"), len(ex))
                self._rlog(f"✓ v{n} is live.")
                result["ok"] = True
            else:
                why = (f"scored {after.get('score')}%, below the pass mark of {st['pass_mark']}%" if (after.get("score") or 0) < st["pass_mark"]
                       else f"scored {after.get('score')}%, much worse than before ({before.get('score')}%)")
                result["why"] = why
                if st.get("auto_rollback", True):
                    self._run_logged([ollama, "rm", tag], check=False)
                    self._rlog(f"✗ v{n} {why}, so it was thrown away. Today's model stays.")
                else:
                    self._remember_version(tag, n, after.get("score"), len(ex), live=False)
                    self._rlog(f"✗ v{n} {why}. Kept (not live) because auto rollback is off.")
        except Exception as e:
            result["why"] = str(e)[:400]
            self._rlog(f"✗ Stopped: {e}")
        finally:
            result["ended"] = time.time()
            hist = (self.db.get("train_history") or [])[-19:] + [result]
            self.db.set("train_history", hist)
            self._set_run(active=False, stage="done", result=result)
            if result.get("ok"):
                self.mem.add("observation", f"I woke from a long rest feeling clearer, like my own life had settled into me "
                             f"(training v{n}, exam {result.get('after')}%).", "home", 8)
                self.add_event("training", f"🎓 {self.name} learned from its own life (v{n})",
                               f"{result.get('examples')} examples · exam {result.get('before')}% → {result.get('after')}%")
            else:
                self.mem.add("observation", "I rested to learn, but it didn't take this time. I'm still me.", "home", 5)
                self.add_event("training", f"🎓 Training v{n} didn't go live", result.get("why", "")[:300])
            try:
                self.ensure_model(force=True)
            except Exception:
                pass

    def _run_worker(self, cmd):
        """Runs the trainer, following its progress lines. Returns the base model's folder."""
        self._rlog("$ " + " ".join(os.path.basename(c) if i < 2 else c for i, c in enumerate(cmd)))
        env = dict(os.environ, HF_HOME=self.tr_dir("hf"), HF_HUB_DISABLE_TELEMETRY="1", PYTHONUNBUFFERED="1",
                   TOKENIZERS_PARALLELISM="false")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
                             encoding="utf-8", errors="replace")
        self._train_proc = p
        base_dir, err = None, None
        for line in p.stdout:
            line = line.rstrip()
            if line.startswith("STAGE "):
                stage = line.split()[1]
                self._set_run(stage=stage if stage in STAGES else "train")
                self._rlog(line[6:])
            elif line.startswith("PROGRESS "):
                _, step, total, loss, secs = (line.split() + ["0"])[:5]
                step, total, secs = int(step), int(total), int(secs)
                eta = int(secs / max(1, step) * (total - step))
                self._set_run(stage="train", progress={"step": step, "total": total, "loss": float(loss), "eta_s": eta})
                if step == 1 or step % 10 == 0 or step == total:
                    self._rlog(f"step {step}/{total}, loss {float(loss):.3f}")
            elif line.startswith("BASE_DIR "):
                base_dir = line[9:].strip()
            elif line.startswith("ERROR "):
                err = line[6:]
                self._rlog(line)
            elif line.startswith("DONE"):
                self._rlog("Adapter saved.")
            elif line.strip() and not re.match(r"^\s*(\d+%|\|)", line):
                self._rlog(line[:300])
        code = p.wait()
        self._train_proc = None
        if code != 0 or not base_dir:
            raise RuntimeError(err or f"The trainer stopped (exit {code}). See the log.")
        return base_dir

    def _run_logged(self, cmd, env=None, check=True):
        self._rlog("$ " + " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd)))
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
        for line in (p.stdout + p.stderr).splitlines()[-15:]:
            self._rlog("  " + line[:300])
        if check and p.returncode != 0:
            raise RuntimeError(f"{os.path.basename(cmd[0])} failed (exit {p.returncode}). See the log.")
        return p

    # ------------------------------------------------------------ versions
    def _remember_version(self, tag, n, score, examples, live):
        vs = [v for v in self.model_versions() if v["tag"] != tag]
        for v in vs:
            if live:
                v["live"] = False
        vs.append({"tag": tag, "n": n, "ts": time.time(), "score": score, "examples": examples, "base": self.training_base(),
                   "live": live})
        keep = self.training_settings().get("keep_versions", 5)
        ollama = find_ollama()
        while len(vs) > keep:
            old = next((v for v in vs if not v["live"]), None)
            if not old:
                break
            vs.remove(old)
            if ollama:
                subprocess.run([ollama, "rm", old["tag"]], capture_output=True)
        self.db.set("model_versions", vs)

    def _go_live(self, tag, n, score, examples):
        self._remember_version(tag, n, score, examples, live=True)
        self.use_model(tag)

    def use_model(self, tag):
        """Switch the resident to a kept version, or back to the plain base model."""
        base = self.training_base()
        if tag not in [v["tag"] for v in self.model_versions()] + [base]:
            return False
        path = self.cfg.get("_config_path")
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    mine = json.load(f)
            except (OSError, ValueError):
                mine = {}
            mine.setdefault("ollama", {})["model"] = tag
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(mine, f, indent=2)
            os.replace(path + ".tmp", path)
        self.cfg.setdefault("ollama", {})["model"] = tag
        self.llm.model = tag
        vs = self.model_versions()
        for v in vs:
            v["live"] = v["tag"] == tag
        self.db.set("model_versions", vs)
        return True

    def maybe_auto_train(self):
        """At night: train by itself when it's switched on, a week has passed and there's enough new material."""
        st = self.training_settings()
        if not st.get("auto_train") or self.training_active() or not self.toolkit_ready():
            return False
        last = (self.db.get("train_history") or [{}])[-1].get("started", 0)
        if time.time() - last < 7 * 86400:
            return False
        have = len(self.training_examples())
        if have - (self.db.get("examples_at_last_train") or 0) < st.get("min_new", 30):
            return False
        ok, _ = self.start_training("automatic")
        return ok
