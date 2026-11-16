"""Shared setup for the hub's tests: a throwaway colony with the stand-in model (no Ollama, no network)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from town.agent import Agent  # noqa: E402
from town.config import load_config  # noqa: E402
from town.db import DB  # noqa: E402
from town.llm import MockLLM  # noqa: E402


def make_agent(credits=5000):
    tmp = tempfile.mkdtemp(prefix="stellar_test_")
    cfg = load_config(ROOT)
    cfg["data_dir"] = tmp
    cfg["creator_name"] = "Courier"
    a = Agent(cfg, DB(os.path.join(tmp, "town.db")), MockLLM(), tmp)
    a.model_status = {"ok": True}
    a.is_asleep = lambda: False
    if credits:
        a.earn(credits, "test money")
    return a


def finish_building(a, bid, plot):
    if a.is_locked(bid):
        a.unlock(bid)
    a.act_build({"building": bid, "plot": plot}, 1)
    c = a.constructions()
    for k in c:
        c[k]["done"] = time.time() - 1
    a.db.set("construction", c)
    a.finish_constructions()


def local_sandbox(a):
    """Runs sandboxed code with plain Python instead of Docker/bubblewrap (test machines have neither)."""
    def run(code, folder="sandbox"):
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=30)
        return (r.stdout + r.stderr).strip() or "(no output)", r.returncode
    a.sandbox_kind = lambda: "bwrap"
    a.sandbox_status = lambda fresh=False: "ready"
    a.sandbox_problem = lambda: None
    a.sandbox_run = run


def call(port, path, body=None, token=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"X-Hub-Token": token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
