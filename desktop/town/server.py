"""Stellar Hub dashboard + JSON API. Hub Connect S (the phone app) uses this same API.

Requests from this computer (localhost) are always allowed.
Requests from anywhere else (your phone over Tailscale) need the pair code,
sent as the X-Hub-Token header or ?token=... in the URL.
"""
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def load_pair_code(data_dir, reset=False):
    path = os.path.join(data_dir, "pair_code.txt")
    if not reset and os.path.exists(path):
        with open(path) as f:
            code = f.read().strip()
            if code:
                return code
    code = "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(3))
    os.makedirs(data_dir, exist_ok=True)
    with open(path, "w") as f:
        f.write(code)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return code


def tailscale_ip():
    exe = shutil.which("tailscale")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=5).stdout.strip()
        return out.splitlines()[0] if out else None
    except Exception:
        return None


def make_server(agent, host, port, pair_code):
    db = agent.db

    class Handler(BaseHTTPRequestHandler):
        server_version = "StellarHub"

        def log_message(self, *args):
            pass

        def _local(self):
            return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

        def _authed(self, qs):
            if self._local():
                return True
            given = self.headers.get("X-Hub-Token") or (qs.get("token") or [""])[0]
            return hmac.compare_digest(given.strip().upper(), pair_code)

        def _send(self, body, ctype="application/json", code=200):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, code=200):
            self._send(json.dumps(obj), code=code)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n or n > 100_000:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}

        def do_GET(self):
            u = urlparse(self.path)
            qs = parse_qs(u.query)
            if u.path in ("/", "/index.html"):
                if not self._local():
                    return self._send("Open the dashboard on the Stellar Hub computer, or use Hub Connect S.",
                                      "text/plain", 403)
                with open(os.path.join(HERE, "dashboard.html"), encoding="utf-8") as f:
                    return self._send(f.read(), "text/html")
            if not self._authed(qs):
                return self._json({"error": "wrong or missing pair code"}, 401)
            try:
                limit = max(1, min(500, int((qs.get("limit") or ["60"])[0])))
            except ValueError:
                limit = 60
            if u.path == "/api/ping":
                return self._json({"ok": True, "app": "Stellar Hub", "name": agent.db.get("name")})
            if u.path == "/api/status":
                return self._json(agent.status())
            if u.path == "/api/world":
                return self._json(agent.world())
            if u.path == "/api/pairing":
                if not self._local():
                    return self._json({"error": "only available on the hub computer"}, 403)
                return self._json({"code": pair_code, "tailscale_ip": tailscale_ip(), "port": port})
            if u.path == "/api/feed":
                return self._json(db.q("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)))
            if u.path == "/api/inbox":
                return self._json(db.q(
                    "SELECT * FROM requests ORDER BY CASE WHEN status IN ('pending','unread') THEN 0 ELSE 1 END, id DESC LIMIT ?",
                    (limit,)))
            if u.path == "/api/library":
                return self._json(db.q("SELECT * FROM library ORDER BY id DESC LIMIT ?", (limit,)))
            if u.path == "/api/events":
                try:
                    after = int((qs.get("after") or ["0"])[0])
                except ValueError:
                    after = 0
                latest = db.q("SELECT COALESCE(MAX(id),0) AS m FROM events")[0]["m"]
                if after < 0:  # phone asking only "where are we?" when it first pairs
                    return self._json({"latest": latest, "events": []})
                ev = db.q("SELECT * FROM events WHERE id > ? ORDER BY id LIMIT 50", (after,))
                for e in ev:
                    if e["kind"] in ("request", "question", "letter"):
                        r = db.q("SELECT status, kind FROM requests WHERE id=?", (e["ref_id"],))
                        e["open"] = bool(r and r[0]["status"] in ("pending", "unread"))
                        e["request_kind"] = r[0]["kind"] if r else None
                return self._json({"latest": latest, "events": ev})
            if u.path == "/api/colony":
                return self._json(agent.colony_overview())
            if u.path == "/api/letters":
                return self._json(db.q("SELECT * FROM letters ORDER BY id DESC LIMIT ?", (limit,)))
            return self._json({"error": "not found"}, 404)

        def do_POST(self):
            u = urlparse(self.path)
            if not self._authed(parse_qs(u.query)):
                return self._json({"error": "wrong or missing pair code"}, 401)
            path, body = u.path, self._body()
            m = re.fullmatch(r"/api/requests/(\d+)/reply", path)
            if m:
                ok = agent.reply_request(int(m.group(1)), body.get("decision", ""), str(body.get("reply", ""))[:3000])
                return self._json({"ok": ok}, 200 if ok else 404)
            if path == "/api/letter":
                text = str(body.get("text", "")).strip()
                if not text:
                    return self._json({"ok": False, "error": "empty letter"}, 400)
                agent.send_letter(text[:3000])
                return self._json({"ok": True})
            if path == "/api/turn":
                threading.Thread(target=agent.take_turn, daemon=True).start()
                return self._json({"started": True})
            m = re.fullmatch(r"/api/buildings/(\w+)/toggle", path)
            if m:
                open_now = agent.toggle_building(m.group(1))
                return self._json({"ok": open_now is not None, "open": open_now})
            if path == "/api/credits/bonus":
                try:
                    amount = max(-1000, min(1000, int(body.get("amount", 0))))
                except (TypeError, ValueError):
                    amount = 0
                if not amount:
                    return self._json({"ok": False, "error": "amount needed"}, 400)
                note = str(body.get("note", "")).strip()[:150] or "a gift"
                agent.earn(amount, f"from {agent.creator}: {note}")
                agent.send_letter(f"I gave you {amount} credits: {note}" if amount > 0 else f"I took {-amount} credits: {note}")
                return self._json({"ok": True, "credits": agent.credits()})
            if path == "/api/radio/stop":
                return self._json({"ok": True, "result": agent.act_stop_music({}, 0)})
            m = re.fullmatch(r"/api/buildings/(\w+)/lock", path)
            if m:
                unlocked = agent.toggle_lock(m.group(1))
                return self._json({"ok": unlocked is not None, "unlocked": unlocked})
            return self._json({"error": "not found"}, 404)

    return ThreadingHTTPServer((host, port), Handler)
