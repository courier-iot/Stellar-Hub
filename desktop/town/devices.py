"""v0.13.2: people and their devices.

Each phone joins with the pair code and a user name, then waits until the owner approves it. Approved devices get their
own secret key (the pair code is only an invitation). Roles:
  owner  - everything (approving requests and programs, settings, devices)
  member - watch, chat, give goals, write letters, take a turn, play chess
  viewer - watch only
The hub computer itself always counts as the owner."""
import hashlib
import re
import secrets
import time

ROLES = ("owner", "member", "viewer")
MEMBER_POSTS = {"/api/goals/review", "/api/chat/start", "/api/chat/say", "/api/chat/end", "/api/goals", "/api/goals/cancel", "/api/letter",
                "/api/turn", "/api/search", "/api/chess/new", "/api/chess/move"}
OWNER_ONLY_GETS = {"/api/devices", "/api/training", "/api/training/exam", "/api/training/corrections", "/api/trainer"}
PRIVATE_EVENTS = {"request", "question", "device", "monitor", "program"}


def _hash(token):
    return hashlib.sha256(token.strip().upper().encode()).hexdigest()


def clean_name(name):
    name = re.sub(r"[^\w .'\-]", "", str(name or ""), flags=re.UNICODE).strip()[:20]
    return re.sub(r"\s+", " ", name)


RESERVED = {"owner", "admin", "creator", "resident", "hub", "stellar hub", "system", "everyone"}


class DevicesMixin:
    # ------------------------------------------------------------ joining and keys
    def username_problem(self, name, another_device=False):
        """Why a new username can't be used (None if it's fine)."""
        raw = str(name or "").strip()
        n = clean_name(raw)
        if len(n) < 3:
            return "Usernames need at least 3 characters."
        if n != raw:
            return "Usernames can use letters, numbers, spaces and . ' - _ only (up to 20)."
        if n.lower() in RESERVED or n.lower() == str(self.db.get("name") or "").lower():
            return f"'{n}' is reserved. Please pick another username."
        taken = self.db.q("SELECT id FROM devices WHERE lower(name)=? AND status != 'removed'", (n.lower(),))
        if taken and not another_device:
            return f"'{n}' is already taken. If it's yours and this is another of your devices, choose 'This is another device of mine'."
        if another_device and not taken:
            return f"There's no user called '{n}' yet. Create it as a new username instead."
        return None

    def join_device(self, name, platform="", another_device=False):
        problem = self.username_problem(name, another_device)
        if problem:
            return None, problem
        name = clean_name(name)
        token = secrets.token_hex(16).upper()
        did = self.db.x("INSERT INTO devices(name, token_hash, role, status, created, last_seen, platform) VALUES(?,?,?,?,?,?,?)",
                        (name, _hash(token), "member", "pending", time.time(), time.time(), str(platform)[:60]))
        self.add_event("device", f"📱 {name} wants to connect" + (" (another device)" if another_device else ""),
                       f"A new device ({platform or 'phone'}) is waiting for you to approve it.", did)
        return {"token": token, "id": did, "name": name, "status": "pending"}, None

    def device_for(self, token):
        if not token:
            return None
        r = self.db.q("SELECT * FROM devices WHERE token_hash=?", (_hash(token),))
        if not r:
            return None
        d = r[0]
        if d["status"] == "active" and time.time() - (d["last_seen"] or 0) > 60:
            self.db.x("UPDATE devices SET last_seen=? WHERE id=?", (time.time(), d["id"]))
        return d

    def devices_list(self):
        return [{k: d[k] for k in ("id", "name", "role", "status", "created", "last_seen", "platform")}
                for d in self.db.q("SELECT * FROM devices WHERE status != 'removed' ORDER BY status='pending' DESC, id")]

    def update_device(self, did, role=None, status=None, name=None):
        r = self.db.q("SELECT * FROM devices WHERE id=?", (did,))
        if not r:
            return False
        d = r[0]
        if role in ROLES:
            self.db.x("UPDATE devices SET role=? WHERE id=?", (role, did))
        if name and clean_name(name):
            self.db.x("UPDATE devices SET name=? WHERE id=?", (clean_name(name), did))
        if status in ("active", "removed"):
            self.db.x("UPDATE devices SET status=? WHERE id=?", (status, did))
            nm = clean_name(name) or d["name"]
            if status == "active" and d["status"] == "pending":
                self.meet_person(nm, role or d["role"])
            if status == "removed":
                self.mem.add("observation", f"{nm} doesn't visit the colony any more.", "post_office", 4)
        return True

    # ------------------------------------------------------------ people the resident knows
    def people(self):
        """Everyone with an approved device, other than its creator."""
        out = {}
        owners = {d["name"].lower() for d in self.db.q("SELECT name FROM devices WHERE status='active' AND role='owner'")}
        for d in self.db.q("SELECT name, role, last_seen FROM devices WHERE status='active'"):
            if d["name"].lower() == self.creator.lower() or d["name"].lower() in owners:
                continue
            p = out.setdefault(d["name"], {"name": d["name"], "role": d["role"], "last_seen": d["last_seen"] or 0})
            if ROLES.index(d["role"]) < ROLES.index(p["role"]):
                p["role"] = d["role"]
            p["last_seen"] = max(p["last_seen"], d["last_seen"] or 0)
        return list(out.values())

    def is_creator(self, who):
        if not who or who.lower() == self.creator.lower():
            return True
        return bool(self.db.q("SELECT id FROM devices WHERE lower(name)=? AND role='owner' AND status='active'", (who.lower(),)))

    def meet_person(self, name, role):
        if self.is_creator(name):
            return
        met = self.db.get("people_met") or {}
        if name in met:
            return
        met[name] = time.time()
        self.db.set("people_met", met)
        what = "can chat with me and give me goals" if role in ("owner", "member") else "can watch the colony"
        self.mem.add("observation", f"{self.creator} let {name} into the colony through Hub Connect S. {name} {what}.", "post_office", 7)
        self.add_event("people", f"👋 {self.name} met {name}", f"{name} can now connect from their phone.")

    def people_news(self):
        ps = self.people()
        if not ps:
            return []
        return ["PEOPLE who visit the colony through their phones (besides your creator): "
                + ", ".join(f"{p['name']} ({'can chat and give goals' if p['role'] != 'viewer' else 'watches'})" for p in ps)
                + ". You can write one of them a letter with write_letter and \"to\": \"<their name>\"."]
