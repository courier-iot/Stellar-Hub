"""Start Stellar Hub:  python3 run.py   (Windows: Stellar Hub in the Start menu)
Options:
  --once             take one turn and exit (good for testing)
  --no-server        run without the dashboard
  --open             open the dashboard in your browser once it's ready
  --new-pair-code    make a new pair code (phones using the old one get logged out)
"""
import json
import os
import sys
import threading
import time
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # needed by the bundled Python on Windows

import town.osutil  # noqa: F401  (sets up certificates before any network use)
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
    from town.config import load_config as _load
    return _load(ROOT)


LOG_FILE = None


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass   # no console (started in the background)
    if LOG_FILE:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d ") + line + "\n")
        except OSError:
            pass


def main():
    cfg = load_config()
    global LOG_FILE
    data_dir = os.path.join(ROOT, cfg.get("data_dir", "data"))
    os.makedirs(data_dir, exist_ok=True)
    LOG_FILE = os.path.join(data_dir, "hub.log")
    try:   # keep the log from growing forever
        if os.path.getsize(LOG_FILE) > 2_000_000:
            os.replace(LOG_FILE, LOG_FILE + ".old")
    except OSError:
        pass
    db = DB(os.path.join(data_dir, "town.db"))
    if cfg.get("provider") == "mock":
        llm = MockLLM()
    else:
        o = cfg["ollama"]
        llm = OllamaLLM(o["url"], o["model"], o.get("temperature", 0.8), num_ctx=o.get("num_ctx", 8192))
    agent = Agent(cfg, db, llm, data_dir)
    from town.updater import Updater
    agent.updater = Updater(ROOT, cfg, db, agent)

    log(f"Stellar Hub v{VERSION}")
    agent.ensure_model(force=True)
    st = agent.model_status
    if st and st.get("note"):
        log("WARNING: " + st["note"])
    elif st:
        log(f"AI model: {st['model']}")

    if "--once" in sys.argv:
        log(json.dumps(agent.take_turn(), indent=2))
        return

    if "--no-server" not in sys.argv:
        port = cfg.get("port", 8080)
        code = load_pair_code(data_dir, reset="--new-pair-code" in sys.argv)
        try:
            srv = None
            for attempt in range(15 if os.environ.get("STELLAR_RESTARTING") else 1):
                try:
                    srv = make_server(agent, "127.0.0.1", port, code)
                    break
                except OSError:
                    if attempt < 14 and os.environ.get("STELLAR_RESTARTING"):
                        time.sleep(1)   # the old copy is still shutting down after an update
                    else:
                        raise
        except OSError:
            # Port already taken: most likely Stellar Hub is already running in the background.
            log(f"Stellar Hub is already running. Opening the dashboard: http://localhost:{port}")
            if "--open" in sys.argv:
                webbrowser.open(f"http://localhost:{port}")
            return
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log(f"Dashboard + town viewer: http://localhost:{port}")
        if "--open" in sys.argv:
            threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
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
    def pet_loop():      # pets live on their own clock, using the computer's spare time
        while True:
            try:
                agent.pet_tick()
            except Exception as e:
                log(f"Pet problem: {e}")
            time.sleep(max(60, int(cfg.get("pets", {}).get("tick_minutes", 5)) * 60))

    try:
        threading.Thread(target=lambda: agent.updater.check(), daemon=True).start()
        threading.Thread(target=pet_loop, daemon=True).start()
        while True:
            if time.time() - (db.get("update") or {}).get("checked", 0) > 12 * 3600:
                threading.Thread(target=lambda: agent.updater.check(), daemon=True).start()
            # nightly backup, once a day after 04:00
            if cfg.get("backups", {}).get("enabled", True) and time.localtime().tm_hour >= 4 \
                    and (db.get("last_backup") or {}).get("day") != time.strftime("%Y-%m-%d"):
                try:
                    path = agent.backup_now()
                    db.set("last_backup", {**db.get("last_backup"), "day": time.strftime("%Y-%m-%d")})
                    log(f"Backed up to {path}")
                except Exception as e:
                    db.set("last_backup", {"ts": time.time(), "error": str(e), "day": time.strftime("%Y-%m-%d")})
                    log(f"Backup failed: {e}")
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
