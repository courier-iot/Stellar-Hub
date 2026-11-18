"""Stellar Hub dashboard + JSON API. Hub Connect S (the phone app) uses this same API.

Requests from this computer (localhost) are allowed without the pair code, with two safety checks so that
websites open in your browser can't control the hub: the Host header must be localhost (stops "DNS
rebinding"), and changes (POST) must carry the dashboard's own header, which other sites can't send.
Requests from anywhere else (phones over Tailscale) need a device key, sent as the X-Hub-Token header or
?token=... in the URL. A phone gets its key by joining with the pair code and a username (POST /api/join); the key
only works once the owner approves the device. Each device has a role: owner, member or viewer (see devices.py). Too many wrong pair codes from one address get it blocked for 5 minutes.
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

from . import interiors
from urllib.parse import parse_qs, urlparse

from .osutil import find_exe, run_quiet
from . import worlds
from .devices import MEMBER_POSTS, OWNER_ONLY_GETS, PRIVATE_EVENTS

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

        who = None     # the signed-in device for this request (the hub computer counts as the owner)

        def _identity(self, qs):
            if self._local():
                return {"id": 0, "name": None, "role": "owner", "status": "active", "local": True}
            ip = self.client_address[0]
            if _blocked(ip):
                return None
            given = (self.headers.get("X-Hub-Token") or (qs.get("token") or [""])[0]).strip()
            d = agent.device_for(given) if given else None
            if not d or d["status"] == "removed":
                _failed(ip)
                return None
            return dict(d)

        def _gate(self, qs):
            """Signs the request in. Returns True when it may go on; otherwise it has already answered."""
            self.who = self._identity(qs)
            if self.who is None:
                if _blocked(self.client_address[0]):
                    self._json({"error": "too many wrong keys, try again in 5 minutes"}, 429)
                else:
                    self._json({"error": "not signed in", "join": True}, 401)
                return False
            if self.who["status"] == "pending":
                self._json({"error": "waiting for the owner to approve this device", "pending": True,
                            "name": self.who["name"]}, 403)
                return False
            return True

        @property
        def role(self):
            return (self.who or {}).get("role", "viewer")

        @property
        def person(self):
            """The speaker's name for the resident, or None when it's the creator (the owner)."""
            return None if self.role == "owner" else (self.who or {}).get("name")

        def _join(self, body):
            ip = self.client_address[0]
            if _blocked(ip):
                return self._json({"ok": False, "error": "too many wrong pair codes, try again in 5 minutes"}, 429)
            code = str(body.get("code", "")).strip().upper()
            if not hmac.compare_digest(code.encode(), pair_code.encode()):
                _failed(ip)
                return self._json({"ok": False, "error": "Wrong pair code. Check it on the Stellar Hub dashboard."}, 401)
            another = bool(body.get("another_device"))
            if body.get("check_only"):
                problem = agent.username_problem(body.get("name"), another)
                return self._json({"ok": problem is None, "error": problem})
            out, problem = agent.join_device(body.get("name"), str(body.get("platform", ""))[:60], another)
            if problem:
                return self._json({"ok": False, "error": problem}, 400)
            return self._json({"ok": True, **out})

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

        def handle_one_request(self):
            try:
                super().handle_one_request()
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                self.close_connection = True   # the browser or phone closed the page mid-reply: nothing to do

        def _json(self, obj, code=200):
            self._send(json.dumps(worlds.reword_obj(obj)), code=code)     # v0.13.5: names in the current world

        def _body(self, limit=100_000):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return {}
            if not n or n > limit:
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
                    return self._send(worlds.reword(f.read()), "text/html")
            if u.path == "/api/me":
                self.who = self._identity(qs)
                if self.who is None:
                    return self._json({"error": "not signed in", "join": True}, 401)
                return self._json({**{k: self.who.get(k) for k in ("id", "name", "role", "status")},
                                   "creator": agent.creator, "resident": agent.db.get("name")})
            if not self._gate(qs):
                return None
            if u.path in OWNER_ONLY_GETS and self.role != "owner":
                return self._json({"error": "only the owner can see this"}, 403)
            if u.path == "/api/devices":
                return self._json({"devices": agent.devices_list()})
            if self.headers.get("X-Hub-App") == "open" and self.role == "owner":
                agent.phone_here()
            try:
                limit = max(1, min(500, int((qs.get("limit") or ["60"])[0])))
            except ValueError:
                limit = 60
            if u.path == "/api/ping":
                return self._json({"ok": True, "app": "Stellar Hub", "name": agent.db.get("name")})
            if u.path == "/api/status":
                return self._json(agent.status())
            m = re.fullmatch(r"/api/interior/(\w+)", u.path)
            if m:
                room = agent.interior(m.group(1))
                return self._json(room) if room else self._json({"error": "no such room"}, 404)
            if u.path == "/api/world":
                return self._json(agent.world())
            if u.path == "/api/worlds":
                from .life import EVENT_TYPES
                return self._json({"current": worlds.current(), "choices": worlds.choices(),
                                   "events": {k: v["title"] for k, v in EVENT_TYPES.items()},
                                   "season": worlds.season(),
                                   "can_reset": self._local() and self.role == "owner"})
            if u.path == "/api/pairing":
                if not self._local():
                    return self._json({"error": "only available on the hub computer"}, 403)
                return self._json({"code": pair_code, "tailscale_ip": tailscale_ip(), "port": port, "windows": os.name == "nt"})
            if u.path == "/api/feed":
                return self._json(db.q("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)))
            if u.path == "/api/inbox":
                if self.role != "owner":    # other people see the letters the resident wrote to them
                    return self._json(db.q("SELECT * FROM requests WHERE kind='letter' AND lower(to_user)=? "
                                           "ORDER BY CASE WHEN status='unread' THEN 0 ELSE 1 END, id DESC LIMIT ?",
                                           (str(self.who.get("name") or "").lower(), limit)))
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
                me = str((self.who or {}).get("name") or "").lower()
                keep = []
                for e in ev:
                    if e["kind"] in ("request", "question", "letter"):
                        r = db.q("SELECT status, kind, to_user FROM requests WHERE id=?", (e["ref_id"],))
                        e["open"] = bool(r and r[0]["status"] in ("pending", "unread"))
                        e["request_kind"] = r[0]["kind"] if r else None
                        if self.role != "owner" and e["kind"] == "letter" and not (r and str(r[0]["to_user"] or "").lower() == me):
                            continue
                    if self.role != "owner" and e["kind"] in PRIVATE_EVENTS:
                        continue
                    keep.append(e)
                return self._json({"latest": latest, "events": keep})
            m = re.fullmatch(r"/api/(audio|chat/voice|album|gifts)/(\d+)\.(wav|png)", u.path)
            if m:
                kind, n = m.group(1), int(m.group(2))
                data, ctype = None, "audio/wav"
                if kind == "audio":
                    path = agent.audio_file(n)
                elif kind == "chat/voice":
                    path = agent.chat_voice(n)
                elif kind == "album":
                    path, ctype = os.path.join(agent.data_root(), "album", f"{n}.png"), "image/png"
                else:
                    path, ctype, data = None, "image/png", agent.gift_png(n)
                if data is None and path and os.path.exists(path):
                    with open(path, "rb") as f:
                        data = f.read()
                if data is None:
                    return self._json({"error": "not found"}, 404)
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return None
            simple = {"/api/audio": lambda: {"audio": agent.audio_list()},
                      "/api/album": lambda: {"album": agent.album_list()},
                      "/api/gifts": lambda: {"gifts": agent.gifts_list()},
                      "/api/taste": agent.taste_overview,
                      "/api/voice": lambda: agent.voice().status(),
                      "/api/decor": lambda: {"owned": agent.decor_inventory(), "placed": agent.decor_placed(),
                                             "slots": {b: {k: (v if isinstance(v, int) else list(v)) for k, v in s.items()}
                                                       for b, s in interiors.DECOR_SLOTS.items()}},
                      "/api/visitors": agent.visitors_overview,
                      "/api/pets": agent.pets_overview,
                      "/api/museum": agent.museum_overview,
                      "/api/workshop": agent.workshop_overview,
                      "/api/economy": agent.economy,
                      "/api/training": agent.training_summary,
                      "/api/training/exam": lambda: {"questions": agent.exam(), "runs": (agent.db.get("exam_runs") or [])[-5:],
                                                     "running": getattr(agent, "_exam_running", False)},
                      "/api/training/corrections": lambda: {"corrections": agent.corrections()},
                      "/api/sandbox": lambda: {"status": agent.sandbox_status(), "problem": agent.sandbox_problem()},
                      "/api/monitor": lambda: agent.monitor_overview((qs.get("track") or [None])[0])}
            if u.path in simple:
                return self._json(simple[u.path]())
            if u.path in ("/api/training/items", "/api/training/export.jsonl") and self.role != "owner":
                return self._json({"error": "only the owner can see this"}, 403)
            if u.path == "/api/training/items":
                return self._json({"items": agent.training_items((qs.get("src") or [None])[0], (qs.get("status") or [None])[0],
                                                                 min(200, int((qs.get("limit") or ["60"])[0])),
                                                                 int((qs.get("offset") or ["0"])[0]))})
            if u.path == "/api/training/export.jsonl":
                body = agent.export_training_set().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="stellar_training_preview.jsonl"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return None
            m = re.fullmatch(r"/api/plans/(\d+)\.(md|code|scad)", u.path)
            if m:
                pid, part = int(m.group(1)), m.group(2)
                plan = next((p for p in agent.plans_list() if p["id"] == pid), None)
                if not plan:
                    return self._json({"error": "not found"}, 404)
                slug = re.sub(r"[^a-z0-9]+", "_", plan["title"].lower()).strip("_")[:40] or f"plan_{pid}"
                if part == "md":
                    data, fname = agent.plan_markdown(pid), f"{slug}.md"
                elif part == "scad":
                    data, fname = plan["plan"].get("scad") or "", f"{slug}.scad"
                else:
                    data = plan["plan"].get("code") or ""
                    fname = f"{slug}.ino" if "void setup" in data or "#include" in data else f"{slug}.py"
                if not data:
                    return self._json({"error": "this plan has no such file"}, 404)
                body = data.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return None
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
            path = u.path
            body = self._body(2_000_000 if path == "/api/phone/music" else 100_000)
            if path == "/api/join":
                return self._join(body)
            if not self._gate(parse_qs(u.query)):
                return None
            if self.role != "owner":
                letter_reply = re.fullmatch(r"/api/requests/(\d+)/reply", path)
                mine = letter_reply and db.q("SELECT id FROM requests WHERE id=? AND kind='letter' AND lower(to_user)=?",
                                             (int(letter_reply.group(1)), str(self.who.get("name") or "").lower()))
                if self.role == "viewer" or not (path in MEMBER_POSTS or mine):
                    return self._json({"error": f"your account ({self.role}) can't do that. Ask the owner."}, 403)
            if self.headers.get("X-Hub-App") == "open" and self.role == "owner":
                agent.phone_here()
            if path == "/api/world":                       # owner only (non-owners are stopped above)
                w = str(body.get("world", ""))
                if not worlds.valid(w):
                    return self._json({"ok": False, "error": "unknown world"}, 400)
                if w != worlds.current():
                    from .config import save_top
                    save_top(agent.cfg, "world", w)
                    worlds.set_current(w)
                    agent.add_event("world", f"🗺️ The colony moved to: {worlds.WORLDS[w]['title']}",
                                    "Same resident, same memories and buildings, new surroundings and names.")
                return self._json({"ok": True, "current": worlds.current()})
            if path == "/api/reset":
                if not self._local():
                    return self._json({"ok": False, "error": "a reset can only be started on the hub computer"}, 403)
                if str(body.get("confirm", "")).strip() != "RESET":
                    return self._json({"ok": False, "error": "type RESET to confirm"}, 400)
                w = str(body.get("world") or worlds.current())
                if not worlds.valid(w):
                    return self._json({"ok": False, "error": "unknown world"}, 400)
                from . import reset
                up = getattr(agent, "updater", None)
                if not up:
                    return self._json({"ok": False, "error": "restart isn't available here"}, 500)
                reset.request(agent.data_dir, w)
                up._exit_soon(restart=True)
                return self._json({"ok": True})
            m = re.fullmatch(r"/api/devices/(\d+)", path)
            if m:
                ok = agent.update_device(int(m.group(1)), body.get("role"), body.get("status"), body.get("name"))
                return self._json({"ok": ok, "devices": agent.devices_list()})
            if path == "/api/phone/music":
                tracks = body.get("tracks")
                if not isinstance(tracks, list):
                    return self._json({"ok": False, "error": "tracks must be a list"}, 400)
                return self._json({"ok": True, "songs": agent.set_phone_library(tracks)})
            if path == "/api/phone/listening":
                evs = body.get("events")
                if not isinstance(evs, list):
                    return self._json({"ok": False}, 400)
                return self._json({"ok": True, "songs": agent.listen_events(evs)})
            if path in ("/api/voice/install", "/api/voice/test", "/api/voice/settings"):
                if not self._local():
                    return self._json({"error": "only from the hub computer"}, 403)
                if path.endswith("install"):
                    return self._json(agent.voice().install_piper())
                if path.endswith("test"):
                    aid = agent.speak_async("test", "🔊 Voice test", f"Hello, {agent.creator}. This is {agent.name}, "
                                            "testing the radio. Can you hear me?")
                    return self._json({"ok": bool(aid), "id": aid})
                from .config import save_setting
                for k in ("enabled", "piper_voice"):
                    if k in body:
                        save_setting(agent.cfg, "voice", k, body[k])
                return self._json(agent.voice().status())
            if path == "/api/training/settings":
                return self._json({"settings": agent.set_training_settings(body)})
            if path == "/api/training/review":
                return self._json({"ok": agent.review_item(str(body.get("src")), int(body.get("ref") or 0), str(body.get("status")),
                                                            body.get("corrected"), body.get("note"))})
            if path == "/api/training/correction":
                cid = agent.add_correction(body.get("wrong"), body.get("right"), body.get("question"))
                return self._json({"ok": bool(cid), "id": cid})
            if path == "/api/training/exam/add":
                return self._json({"ok": bool(agent.add_exam_question(body.get("question", ""), body.get("expect", "")))})
            if path == "/api/training/exam/remove":
                agent.remove_exam_question(int(body.get("id") or 0))
                return self._json({"ok": True})
            if path == "/api/training/exam/run":
                agent.run_exam_async()
                return self._json({"ok": True})
            if path == "/api/sandbox/check":
                return self._json({"status": agent.sandbox_status(fresh=True), "problem": agent.sandbox_problem()})
            if path == "/api/goals":
                title, text = str(body.get("title", "")).strip(), str(body.get("text", "")).strip()
                if not title or not text:
                    return self._json({"ok": False, "error": "a goal needs a title and a description"}, 400)
                gid = agent.add_creator_goal(body.get("kind", "code"), title, text, body.get("tests") or None, by=self.person)
                return self._json({"ok": True, "id": gid})
            if path == "/api/goals/review":
                try:
                    gid = int(body.get("id"))
                except (TypeError, ValueError):
                    return self._json({"ok": False}, 400)
                if self.role != "owner" and not db.q("SELECT id FROM goals WHERE id=? AND lower(by_user)=?",
                                                     (gid, str(self.who.get("name") or "").lower())):
                    return self._json({"ok": False, "error": "only the person who set this goal (or the owner) can review it"}, 403)
                return self._json({"ok": agent.review_goal(gid, bool(body.get("passed")), str(body.get("note", ""))[:500])})
            if path == "/api/goals/cancel":
                try:
                    gid = int(body.get("id"))
                except (TypeError, ValueError):
                    return self._json({"ok": False}, 400)
                if self.role == "owner":
                    agent.db.x("UPDATE goals SET status='cancelled' WHERE id=? AND source='creator' AND status IN ('open','review')", (gid,))
                else:
                    agent.db.x("UPDATE goals SET status='cancelled' WHERE id=? AND source='creator' AND lower(by_user)=? "
                               "AND status IN ('open','review')", (gid, str(self.who.get("name") or "").lower()))
                return self._json({"ok": True})
            if path == "/api/pets/brain":
                if not self._local():
                    return self._json({"error": "only from the hub computer"}, 403)
                return self._json(agent.pull_pet_brain())
            if path == "/api/phone/forget":
                agent.db.set("phone_music", None)
                return self._json({"ok": True})
            if path == "/api/phone/played":
                try:
                    rid = int(body.get("id"))
                except (TypeError, ValueError):
                    return self._json({"ok": False}, 400)
                ok = agent.phone_played(rid, bool(body.get("ok")), str(body.get("note", ""))[:200])
                return self._json({"ok": ok})
            m = re.fullmatch(r"/api/requests/(\d+)/reply", path)
            if m:
                ok = agent.reply_request(int(m.group(1)), body.get("decision", ""), str(body.get("reply", ""))[:3000], sender=self.person)
                return self._json({"ok": ok}, 200 if ok else 404)
            if path == "/api/letter":
                text = str(body.get("text", "")).strip()
                if not text:
                    return self._json({"ok": False, "error": "empty letter"}, 400)
                agent.send_letter(text[:3000], sender=self.person)
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
                    return self._json({"reply": agent.chat_say(text, who=self.person), "chat": agent.chat_state()})
                except Exception as e:
                    return self._json({"error": f"{agent.name} couldn't answer: {e}"}, 503)
            if path == "/api/chat/end":
                return self._json({"summary": agent.chat_end()})
            if path == "/api/space_event/stop":
                ev = agent.space_event()
                if ev:
                    agent.end_space_event(ev)
                return self._json({"ok": True, "stopped": bool(ev)})
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
