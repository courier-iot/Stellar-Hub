"""Stellar Hub dashboard + JSON API. Hub Connect S (the phone app) uses this same API.

Requests from this computer (localhost) are allowed without the pair code, with two safety checks so that
websites open in your browser can't control the hub: the Host header must be localhost (stops "DNS
rebinding"), and changes (POST) must carry the dashboard's own header, which other sites can't send.
Requests from anywhere else (your phone over Tailscale) need the pair code, sent as the X-Hub-Token header
or ?token=... in the URL. Too many wrong pair codes from one address get it blocked for 5 minutes.
"""
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .osutil import find_exe, run_quiet

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
    exe = find_exe("tailscale")
    if not exe:
        return None
    code, out = run_quiet([exe, "ip", "-4"], timeout=5)
    return out.splitlines()[0] if code == 0 and out else None


LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}
_FAILS = {}            # ip -> recent failed pair-code attempts
_FAILS_LOCK = threading.Lock()


def _blocked(ip):
    with _FAILS_LOCK:
        recent = [t for t in _FAILS.get(ip, []) if time.time() - t < 300]
        _FAILS[ip] = recent
        return len(recent) >= 10


def _failed(ip):
    with _FAILS_LOCK:
        _FAILS.setdefault(ip, []).append(time.time())


def make_server(agent, host, port, pair_code):
    db = agent.db
    local_server = host in ("127.0.0.1", "localhost")

    class Handler(BaseHTTPRequestHandler):
        server_version = "StellarHub"

        def log_message(self, *args):
            pass

        def _local(self):
            return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

        def _host_ok(self):
            """On the localhost server, only accept requests addressed to localhost (blocks DNS rebinding)."""
            if not local_server:
                return True
            h = (self.headers.get("Host") or "").strip().lower()
            name = h.rsplit(":", 1)[0] if not h.startswith("[") else h.split("]")[0] + "]"
            return name in LOCAL_HOSTS

        def _origin_ok(self):
            origin = (self.headers.get("Origin") or "").lower()
            if not origin:
                return True
            return origin in (f"http://localhost:{port}", f"http://127.0.0.1:{port}") or not self._local()

        def _authed(self, qs):
            ip = self.client_address[0]
            if self._local():
                return True
            if _blocked(ip):
                return False
            given = self.headers.get("X-Hub-Token") or (qs.get("token") or [""])[0]
            ok = hmac.compare_digest(given.strip().upper().encode(), pair_code.encode())
            if not ok:
                _failed(ip)
            return ok

        def _send(self, body, ctype="application/json", code=200):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, code=200):
            self._send(json.dumps(obj), code=code)

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return {}
            if not n or n > 100_000:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}

        def do_GET(self):
            if not self._host_ok():
                return self._json({"error": "bad host"}, 403)
            u = urlparse(self.path)
            qs = parse_qs(u.query)
            if u.path in ("/", "/index.html"):
                if not self._local():
                    return self._send("Open the dashboard on the Stellar Hub computer, or use Hub Connect S.",
                                      "text/plain", 403)
                with open(os.path.join(HERE, "dashboard.html"), encoding="utf-8") as f:
                    return self._send(f.read(), "text/html")
            if not self._authed(qs):
                if _blocked(self.client_address[0]):
                    return self._json({"error": "too many wrong pair codes, try again in 5 minutes"}, 429)
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
                return self._json({"code": pair_code, "tailscale_ip": tailscale_ip(), "port": port, "windows": os.name == "nt"})
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
            m = re.fullmatch(r"/api/compositions/(\d+)\.wav", u.path)
            if m:
                path = os.path.join(agent.studio_dir, f"{int(m.group(1))}.wav")
                if not os.path.exists(path):
                    return self._json({"error": "not found"}, 404)
                with open(path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return None
            if u.path == "/api/update":
                up = getattr(agent, "updater", None)
                return self._json(up.state() if up else {"available": False})
            if u.path == "/api/exchange":
                return self._json(agent.exchange_overview())
            if u.path == "/api/gallery":
                return self._json(agent.gallery_overview())
            if u.path == "/api/chess":
                return self._json(agent.chess_view())
            if u.path == "/api/chat":
                return self._json(agent.chat_state() or {"messages": []})
            if u.path == "/api/milestones":
                return self._json(db.q("SELECT * FROM milestones ORDER BY ts DESC"))
            if u.path == "/api/colony":
                return self._json(agent.colony_overview())
            if u.path == "/api/letters":
                return self._json(db.q("SELECT * FROM letters ORDER BY id DESC LIMIT ?", (limit,)))
            return self._json({"error": "not found"}, 404)

        def do_POST(self):
            if not self._host_ok() or not self._origin_ok():
                return self._json({"error": "not allowed"}, 403)
            # Browsers won't let other websites add custom headers, so this stops cross-site requests.
            if self._local() and not (self.headers.get("X-Stellar-Hub") or self.headers.get("X-Hub-Token")):
                return self._json({"error": "missing X-Stellar-Hub header"}, 403)
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
            if path == "/api/chess/new":
                agent.chess_new("b" if str(body.get("color", "white")).lower().startswith("b") else "w")
                return self._json(agent.chess_view())
            if path == "/api/chess/move":
                try:
                    agent.chess_creator_move(str(body.get("move", "")))
                except ValueError as e:
                    return self._json({"error": str(e), **agent.chess_view()}, 400)
                return self._json(agent.chess_view())
            if path == "/api/search":
                q = str(body.get("q", "")).strip()[:300]
                if not q:
                    return self._json({"error": "ask something"}, 400)
                return self._json(agent.search_memories(q))
            if path == "/api/chat/start":
                return self._json(agent.chat_start())
            if path == "/api/chat/say":
                text = str(body.get("text", "")).strip()
                if not text:
                    return self._json({"error": "say something"}, 400)
                try:
                    return self._json({"reply": agent.chat_say(text), "chat": agent.chat_state()})
                except Exception as e:
                    return self._json({"error": f"{agent.name} couldn't answer: {e}"}, 503)
            if path == "/api/chat/end":
                return self._json({"summary": agent.chat_end()})
            if path == "/api/space_event":
                ev = agent.start_space_event(str(body.get("type", "")))
                return self._json({"ok": ev is not None, "event": ev})
            if path == "/api/backup":
                try:
                    return self._json({"ok": True, "file": agent.backup_now()})
                except Exception as e:
                    return self._json({"ok": False, "error": str(e)}, 500)
            if path in ("/api/update/check", "/api/update/apply"):
                up = getattr(agent, "updater", None)
                if not up:
                    return self._json({"error": "updates unavailable"}, 404)
                if path.endswith("check"):
                    return self._json(up.check(force=True))
                if not self._local():
                    return self._json({"error": "updates can only be installed from the hub computer"}, 403)
                return self._json(up.apply())
            if path == "/api/shutdown":
                if not self._local():
                    return self._json({"error": "only from the hub computer"}, 403)
                agent.act_stop_music({}, 0)
                self._json({"ok": True})
                threading.Timer(0.5, lambda: os._exit(0)).start()
                return None
            if path == "/api/radio/stop":
                return self._json({"ok": True, "result": agent.act_stop_music({}, 0)})
            m = re.fullmatch(r"/api/buildings/(\w+)/lock", path)
            if m:
                unlocked = agent.toggle_lock(m.group(1))
                return self._json({"ok": unlocked is not None, "unlocked": unlocked})
            return self._json({"error": "not found"}, 404)

    return ThreadingHTTPServer((host, port), Handler)
