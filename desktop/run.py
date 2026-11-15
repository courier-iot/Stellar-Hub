"""Start Stellar Hub:  python3 run.py
Options:
  --once             take one turn and exit (good for testing)
  --no-server        run without the dashboard
  --new-pair-code    make a new pair code (phones using the old one get logged out)
"""
import json
import os
import sys
import threading
import time

from town.agent import Agent
from town.db import DB
from town.llm import MockLLM, OllamaLLM
from town.server import load_pair_code, make_server, tailscale_ip

ROOT = os.path.dirname(os.path.abspath(__file__))


def read_version():
    for p in (os.path.join(ROOT, "VERSION"), os.path.join(ROOT, "..", "VERSION")):
        if os.path.exists(p):
            with open(p) as f:
                return f.read().strip()
    return "dev"


VERSION = read_version()


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    cfg = load_config()
    data_dir = os.path.join(ROOT, cfg.get("data_dir", "data"))
    db = DB(os.path.join(data_dir, "town.db"))
    if cfg.get("provider") == "mock":
        llm = MockLLM()
    else:
        o = cfg["ollama"]
        llm = OllamaLLM(o["url"], o["model"], o.get("temperature", 0.8))
    agent = Agent(cfg, db, llm, data_dir)

    log(f"Stellar Hub v{VERSION}")
    ok, msg = llm.check()
    if not ok:
        log("WARNING: " + msg)

    if "--once" in sys.argv:
        log(json.dumps(agent.take_turn(), indent=2))
        return

    if "--no-server" not in sys.argv:
        port = cfg.get("port", 8080)
        code = load_pair_code(data_dir, reset="--new-pair-code" in sys.argv)
        srv = make_server(agent, "127.0.0.1", port, code)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log(f"Dashboard + town viewer: http://localhost:{port}")
        if cfg.get("phone_access", True):
            ip = tailscale_ip()
            if ip:
                try:
                    phone = make_server(agent, ip, port, code)
                    threading.Thread(target=phone.serve_forever, daemon=True).start()
                    log(f"Hub Connect S: address http://{ip}:{port}   pair code {code}")
                except OSError as e:
                    log(f"Couldn't open phone access on {ip}: {e}")
            else:
                log("Tailscale not found or not connected, so phone access is off (see README).")

    tick = cfg["tick_minutes"] * 60
    log(f"The resident wakes every {cfg['tick_minutes']} minutes. Press Ctrl+C to stop.")
    try:
        while True:
            last = db.get("last_turn") or 0
            if time.time() - last >= tick:
                log("Taking a turn…")
                out = agent.take_turn()
                if "error" in out:
                    log("Problem: " + out["error"] + " (will try again next wake)")
                    db.set("last_turn", time.time())  # wait a full tick before retrying
                elif "skipped" not in out:
                    log(f"{agent.name} @ {out['building']} → {out['action']}: {out['result'][:160]}")
            time.sleep(15)
    except KeyboardInterrupt:
        log("Stellar Hub is sleeping. Everything is saved.")


if __name__ == "__main__":
    main()
