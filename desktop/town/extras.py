"""v0.10 life features: manuals, voice (spoken logs, radio shows, chat voice), decorating every building,
visitors, the photo album, gifts for the creator, room moods, and learning the creator's music taste."""
import json
import os
import random
import struct
import threading
import time
import zlib

from . import interiors, manuals, sprites
from .buildings import BUILDINGS
from .plants import SPECIES

# ---------------------------------------------------------------- decor for every building
# name: (slot kind, price, description)
DECOR_ITEMS = {
    "star_poster": ("wall", 30, "a poster of a star chart"),
    "neon_sign": ("wall", 80, "a buzzing neon star sign"),
    "wall_clock": ("wall", 30, "a round wall clock"),
    "trinket_shelf": ("wall", 45, "a little shelf of trinkets"),
    "pennant": ("wall", 20, "a colony pennant"),
    "galaxy_map": ("wall", 70, "a glowing galaxy map"),
    "potted_fern": ("floor", 25, "a potted fern"),
    "floor_lamp": ("floor", 35, "a tall floor lamp"),
    "robot_buddy": ("floor", 120, "a little robot buddy that blinks"),
    "crystal_lamp": ("floor", 60, "a glowing crystal lamp"),
    "arcade_cabinet": ("floor", 200, "a tiny arcade cabinet"),
    "cactus": ("floor", 20, "a moon cactus"),
    "planet_mobile": ("ceiling", 50, "a hanging planet mobile"),
    "string_lights": ("ceiling", 30, "a string of fairy lights"),
    "disco_orb": ("ceiling", 70, "a sparkling disco orb"),
    "paper_lantern": ("ceiling", 25, "a paper lantern"),
    "round_rug": ("rug", 40, "a round rug"),
    "star_rug": ("rug", 60, "a star-shaped rug"),
    "stripe_rug": ("rug", 35, "a striped runner rug"),
}

VISITORS = {
    "quill": {"name": "Quill", "who": "a wandering cartographer who maps forgotten moons", "colors": ("o", "y", "s"),
              "likes": ["library", "park", "internet_cafe"]},
    "bix": {"name": "Bix", "who": "a cheerful repair drone looking for odd jobs", "colors": ("S", "c", "s"),
            "likes": ["workshop", "spaceport", "exchange"]},
    "orla": {"name": "Captain Orla", "who": "a freighter pilot with too many stories", "colors": ("R", "y", "w"),
             "likes": ["spaceport", "exchange", "radio_tower"]},
    "mira": {"name": "Mira", "who": "a comet botanist who collects seeds from tails of ice", "colors": ("E", "m", "w"),
             "likes": ["greenhouse", "park", "gallery"]},
    "tamsin": {"name": "Old Tamsin", "who": "a retired astronaut who flew the first colony ships", "colors": ("g", "C", "s"),
               "likes": ["library", "archive", "park"]},
    "zeph": {"name": "Zeph", "who": "a young stargazer who dreams of being an artist", "colors": ("P", "p", "y"),
             "likes": ["gallery", "studio", "park"]},
}

ALBUM_KINDS = {"milestone", "build", "plant", "space", "visitor", "gift", "unlock", "show"}

SHOW_PROMPT = """You are {name}, a young AI who lives in a little space colony and hosts a short daily radio show
from its Radio Tower. Write today's show as something you will SAY out loud (about 120-200 words): greet listeners,
share colony news from today in your own voice, pick one song (from your creator's favourites if any are listed) and
say why, and end with a short dedication to your creator, {creator}. Warm, playful, honest; no stage directions.
Reply as JSON: {{"title": "<short show title>", "script": "<what you say>", "song": "<song title or empty>"}}"""

VISITOR_PROMPT = """You are writing a short scene for {name}, a young AI living in a space colony.
A visitor is at the {place}: {vname}, {vwho}. {name} talks with them. Write the conversation (4-8 short lines,
"Name: line" format), true to {name}'s personality, then what {name} took away from it.
Reply as JSON: {{"conversation": "<the lines>", "learned": "<one sentence>", "mood": "<one word>"}}"""

GIFT_POEM_PROMPT = """You are {name}, a young AI in a space colony, writing a short poem (4-10 lines) as a gift for your
creator, {creator}. Make it personal: draw on the memories given. Reply as JSON: {{"title": "...", "poem": "..."}}"""


def png_bytes(rows, palette, scale=3):
    """A small PNG encoder (no libraries needed) for pixel art rows."""
    h, w = len(rows), len(rows[0])
    rgb = {k: bytes(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in palette.items()}
    raw = bytearray()
    for y in range(h):
        line = b"".join((rgb.get(ch, b"\x05\x06\x0d") * scale) for ch in rows[y])
        for _ in range(scale):
            raw += b"\x00" + line

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * scale, h * scale, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def visitor_sprite(colors):
    coat, accent, skin = colors
    c = sprites.Canvas(16, 16)
    c.disc(8, 4, 3, skin)
    c.rect(6, 3, 5, 1, accent)                    # hat band / visor
    c.px(7, 4, "k"); c.px(9, 4, "k")
    c.rect(5, 8, 7, 5, coat)
    c.rect(7, 8, 3, 1, accent)
    c.rect(4, 9, 1, 3, coat); c.rect(12, 9, 1, 3, coat)
    c.rect(6, 13, 2, 3, "k"); c.rect(9, 13, 2, 3, "k")
    return c.rows()


class ExtrasMixin:
    def data_root(self):
        return os.path.dirname(self.home_dir)

    # ================================================================ manuals
    def give_manual(self, bid, opened=False, quiet=False):
        got = self.db.get("manuals") or {}
        if opened:
            if got.get(bid, {}).get("opened"):
                return
            # buildings it already had get their manual quietly, without a "new building" note
            got[bid] = {"ts": got.get(bid, {}).get("ts", time.time()), "opened": time.time() - (5 * 86400 if quiet else 0)}
            self.mem.add("observation", manuals.manual(bid) or "", bid, 8)
        else:
            if bid in got:
                return
            got[bid] = {"ts": time.time()}
            self.mem.add("observation", f"I received the manual for the {BUILDINGS[bid]['name']}: {manuals.short(bid)}", "home", 6)
        self.db.set("manuals", got)

    def give_starting_manuals(self):
        if self.db.get("manuals_started"):
            return
        self.db.set("manuals_started", time.time())
        for bid in BUILDINGS:
            if self.is_built(bid):
                self.give_manual(bid)
                self.give_manual(bid, opened=True, quiet=True)

    def act_read_manual(self, a, imp):
        bid = str(a.get("building", "")).strip().lower().replace(" ", "_")
        if bid not in BUILDINGS:
            got = self.db.get("manuals") or {}
            return "Manuals I have: " + ", ".join(BUILDINGS[b]["name"] + f" ({b})" for b in got if b in BUILDINGS)
        if bid not in (self.db.get("manuals") or {}) and self.is_locked(bid):
            return f"I don't have the manual for the {BUILDINGS[bid]['name']} yet. It comes with its blueprint."
        text = manuals.manual(bid)
        slots = interiors.DECOR_SLOTS.get(bid, {})
        if slots:
            text += f" Decor spots inside: {', '.join(slots)}."
        return text

    def act_read_plant_guide(self, a, imp):
        sp = str(a.get("species", "")).strip().lower().replace(" ", "_")
        if sp in SPECIES:
            return manuals.PLANT_GUIDE + " " + manuals.species_card(sp, SPECIES[sp])
        return manuals.PLANT_GUIDE

    def plant_card_once(self, species):
        seen = self.db.get("plant_cards") or []
        if species in seen or species not in SPECIES:
            return
        seen.append(species)
        self.db.set("plant_cards", seen)
        self.mem.add("observation", "Care card: " + manuals.species_card(species, SPECIES[species]), "greenhouse", 6)

    # ================================================================ voice
    def voice(self):
        if not hasattr(self, "_voice"):
            from .tts import Voice
            self._voice = Voice(self.data_root(), self.cfg.setdefault("voice", {"enabled": True, "piper_voice": "amy"}))
        return self._voice

    def audio_dir(self):
        return os.path.join(self.data_root(), "audio")

    def speak_async(self, kind, title, text, ref=None):
        """Records something the resident says (a log, a show) as audio for the creator's phone."""
        if not self.voice().backend():
            return None
        aid = self.db.x("INSERT INTO audio(ts, kind, title, text, ref, status) VALUES(?,?,?,?,?,?)",
                        (time.time(), kind, title[:200], text[:4000], ref, "making"))

        def work():
            path = os.path.join(self.audio_dir(), f"{aid}.wav")
            ok = self.voice().speak(text, path)
            self.db.x("UPDATE audio SET status=?, file=? WHERE id=?", ("ready" if ok else "failed", path if ok else None, aid))
            if ok:
                self.add_event("voice", f"🔊 {title}", text[:300], aid)
        threading.Thread(target=work, daemon=True).start()
        return aid

    def audio_list(self, limit=30):
        return self.db.q("SELECT id, ts, kind, title, text, status FROM audio ORDER BY id DESC LIMIT ?", (limit,))

    def audio_file(self, aid):
        r = self.db.q("SELECT file FROM audio WHERE id=? AND status='ready'", (aid,))
        return r[0]["file"] if r and r[0]["file"] and os.path.exists(r[0]["file"]) else None

    def chat_voice(self, n):
        """Speech for message n of the current/last chat, made once and kept."""
        chat = self.chat_state() or {}
        msgs = chat.get("messages", [])
        if not (0 <= n < len(msgs)) or msgs[n].get("who") == "creator":
            return None
        text = msgs[n]["text"]
        import hashlib
        path = os.path.join(self.audio_dir(), "chat-" + hashlib.md5(text.encode()).hexdigest()[:16] + ".wav")
        if not os.path.exists(path):
            if not self.voice().speak(text, path):
                return None
        return path

    def act_host_show(self, a, imp):
        today = self._today()
        if self.db.get("show_date") == today:
            return "I already hosted today's show. Tomorrow's will be even better."
        if not self.voice().backend():
            return "I wanted to host a show, but the radio has no voice yet. My creator can set one up in the dashboard."
        news = [e["title"] for e in self.db.q("SELECT title FROM events WHERE ts > ? ORDER BY id DESC LIMIT 8",
                                               (time.time() - 86400,))]
        favs = [f"{s['title']} by {s['artist']}" for s in self.favourites(6)]
        ctx = (f"WHO YOU ARE:\n{self.personality()}\n\nTODAY IN THE COLONY: {'; '.join(news) or 'a quiet day'}\n"
               f"YOUR CREATOR'S FAVOURITE SONGS: {'; '.join(favs) or 'unknown yet'}\n"
               f"YOUR OWN SONGS: {', '.join(c['title'] for c in self.db.q('SELECT title FROM compositions ORDER BY id DESC LIMIT 4')) or 'none'}")
        out = self.ask(SHOW_PROMPT.format(name=self.name, creator=self.creator), ctx, "show")
        script = str(out.get("script", "")).strip()
        if not script:
            return "I sat at the mic, but the words didn't come today."
        title = str(out.get("title") or "The Colony Hour")[:80]
        self.db.set("show_date", today)
        self.db.x("INSERT INTO broadcasts(ts, text) VALUES(?,?)", (time.time(), f"[{title}] {script}"[:2000]))
        self.speak_async("show", f"📻 {title}", script)
        self.gain_xp("music", 3, "hosted a radio show")
        self.earn_capped("cr_show", 8, "hosted the daily radio show", 8)
        return f"I hosted today's radio show, \"{title}\". It's on its way to my creator's phone."

    # ================================================================ decorating every building
    def decor_inventory(self):
        return self.db.get("decor_items") or {}

    def decor_placed(self):
        return self.db.get("room_decor") or {}

    def decor_free(self, item):
        used = sum(1 for room in self.decor_placed().values() for it in room.values() if it == item)
        return self.decor_inventory().get(item, 0) - used

    def buy_decor_item(self, name):
        if name not in DECOR_ITEMS:
            return None
        kind, price, about = DECOR_ITEMS[name]
        if not self.spend(price, f"bought {name.replace('_', ' ')}"):
            return f"I can't afford the {name.replace('_', ' ')} yet ({self.credits()}/{price} credits)."
        inv = self.decor_inventory()
        inv[name] = inv.get(name, 0) + 1
        self.db.set("decor_items", inv)
        return (f"I bought {about} ({kind} decor) for {price} credits. I can place it in any building's "
                f"{kind} spot with decorate.")

    @staticmethod
    def decor_items_catalog():
        return DECOR_ITEMS

    def decor_shop_text(self):
        return ", ".join(f"furniture:{n} ({v[1]}, {v[0]})" for n, v in DECOR_ITEMS.items())

    def act_decorate(self, a, imp):
        bid = self.db.get("location", "home")
        slots = interiors.DECOR_SLOTS.get(bid, {})
        slot = str(a.get("slot", "")).strip().lower()
        item = str(a.get("item", "")).strip().lower().replace(" ", "_")
        here = self.decor_placed().get(bid, {})
        if slot not in slots:
            return (f"The {BUILDINGS[bid]['name']} has these decor spots: {', '.join(slots) or 'none'}. "
                    f"Now: {', '.join(f'{s}={here.get(s, 'empty')}' for s in slots)}.")
        placed = self.decor_placed()
        room = placed.setdefault(bid, {})
        if item in ("", "none", "empty", "remove"):
            old = room.pop(slot, None)
            self.db.set("room_decor", placed)
            return f"I took the {old.replace('_', ' ')} down." if old else "That spot was already empty."
        if item not in DECOR_ITEMS:
            return f"I don't know a decor item called '{item}'."
        if DECOR_ITEMS[item][0] != slot:
            return f"The {item.replace('_', ' ')} is {DECOR_ITEMS[item][0]} decor; it can't go in the {slot} spot."
        if room.get(slot) != item and self.decor_free(item) < 1:
            return f"I don't have a spare {item.replace('_', ' ')}. I could buy one at the Credit Vault."
        room[slot] = item
        self.db.set("room_decor", placed)
        self.gain_xp("art", 1, "decorated")
        return f"I put {DECOR_ITEMS[item][2]} in the {slot} spot of the {BUILDINGS[bid]['name']}. It feels more like mine."

    # ================================================================ visitors
    def visitor_now(self):
        v = self.db.get("visitor")
        if v and v["until"] > time.time():
            return v
        if v:
            self.db.set("visitor", None)
            self.mem.add("observation", f"{VISITORS[v['id']]['name']} left the colony.", v["building"], 3)
        return None

    def maybe_visitor(self):
        if self.visitor_now() or random.random() > 0.05:     # about two or three visits a week at 30-minute turns
            return
        vid = random.choice(list(VISITORS))
        v = VISITORS[vid]
        places = [b for b in v["likes"] if self.is_built(b)] or [b for b in ("park", "library", "post_office") if self.is_built(b)] or ["home"]
        b = random.choice(places)
        self.db.set("visitor", {"id": vid, "building": b, "since": time.time(), "until": time.time() + random.uniform(4, 9) * 3600,
                                "talked": False})
        self.add_event("visitor", f"🧳 {v['name']} is visiting", f"{v['name']}, {v['who']}, is at the {BUILDINGS[b]['name']}.")
        self.mem.add("observation", f"A visitor arrived: {v['name']}, {v['who']}. They're at the {BUILDINGS[b]['name']}.", b, 6)

    def visitors_overview(self):
        v = self.visitor_now()
        now = dict(v, name=VISITORS[v["id"]]["name"], who=VISITORS[v["id"]]["who"]) if v else None
        visits = [dict(r, visitor=VISITORS.get(r["visitor"], {}).get("name", r["visitor"]))
                  for r in self.db.q("SELECT * FROM visits ORDER BY id DESC LIMIT 20")]
        return {"now": now, "visits": visits}

    def act_talk_to_visitor(self, a, imp):
        v = self.visitor_now()
        if not v or v["building"] != self.db.get("location"):
            return "There's no visitor here right now."
        info = VISITORS[v["id"]]
        ctx = f"WHO {self.name.upper()} IS:\n{self.personality()}\n\nWHAT'S ON ITS MIND: {self.db.get('goals', [])}"
        out = self.ask(VISITOR_PROMPT.format(name=self.name, place=BUILDINGS[v["building"]]["name"], vname=info["name"],
                                             vwho=info["who"]), ctx, "visitor")
        talk = str(out.get("conversation", "")).strip()[:1500]
        learned = str(out.get("learned", "")).strip()[:300]
        self.db.x("INSERT INTO visits(ts, visitor, building, talk, learned) VALUES(?,?,?,?,?)",
                  (time.time(), v["id"], v["building"], talk, learned))
        extra = ""
        if not v.get("talked") and random.random() < 0.35:
            extra = " Before we parted, they gave me something: " + self.find_curio(f"{info['name']}'s pack")
        v["talked"] = True
        self.db.set("visitor", v)
        self.add_event("visitor", f"💬 {self.name} talked with {info['name']}", (learned or talk)[:300])
        self.mem.add("observation", f"I talked with {info['name']} ({info['who']}). {learned}", v["building"], 7)
        return f"I talked with {info['name']}. {learned}{extra}"

    # ================================================================ photo album
    def snapshot(self, title, caption=""):
        today = self._today()
        n = self.db.q("SELECT COUNT(*) AS n FROM album WHERE day=?", (today,))[0]["n"]
        if n >= 5:
            return None
        loc = self.db.get("location", "home")
        room = self.interior(loc) if loc in interiors.ROOMS else None
        if room:
            rows = [list(r) for r in room["background"]]
            spot = next(iter(room["spots"].values()), {"x": 120})
            frame = sprites.resident_frames(self.appearance())[0]
            ox, oy = spot["x"] - 8, interiors.FEET - 16
            for j, row in enumerate(frame):
                for i, ch in enumerate(row):
                    if ch != "." and 0 <= ox + i < interiors.IW and 0 <= oy + j < interiors.IH:
                        rows[oy + j][ox + i] = ch
            rows, pal = ["".join(r) for r in rows], room["palette"]
        else:
            w = self.world()
            rows, pal = w["background"], w["palette"]
        os.makedirs(os.path.join(self.data_root(), "album"), exist_ok=True)
        pid = self.db.x("INSERT INTO album(ts, day, title, caption, place) VALUES(?,?,?,?,?)",
                        (time.time(), today, title[:120], caption[:300], loc))
        with open(os.path.join(self.data_root(), "album", f"{pid}.png"), "wb") as f:
            f.write(png_bytes(rows, pal, 3))
        return pid

    def album_list(self, limit=60):
        return self.db.q("SELECT id, ts, title, caption, place FROM album ORDER BY id DESC LIMIT ?", (limit,))

    def add_event(self, kind, title, body="", ref_id=None):
        eid = super().add_event(kind, title, body, ref_id)
        if kind in ALBUM_KINDS and not getattr(self, "_snapping", False):
            self._snapping = True
            try:
                self.snapshot(title, body[:200])
            except Exception:
                pass
            finally:
                self._snapping = False
        return eid

    # ================================================================ gifts for the creator
    def act_make_gift(self, a, imp):
        last = self.db.q("SELECT MAX(ts) AS t FROM gifts")[0]["t"] or 0
        if time.time() - last < 3 * 86400:
            return "I gave my creator a gift not long ago. I'll save the next one for a special moment."
        kind = str(a.get("kind", "")).strip().lower()
        note = str(a.get("note", "")).strip()[:400]
        ref, title, text = None, "", ""
        if kind == "painting":
            r = self.db.q("SELECT id, title FROM paintings ORDER BY id DESC LIMIT 1") if not a.get("id") else \
                self.db.q("SELECT id, title FROM paintings WHERE id=?", (a.get("id"),))
            if not r:
                return "I want to give a painting, but I haven't painted one yet."
            ref, title = r[0]["id"], r[0]["title"]
        elif kind == "song":
            r = self.db.q("SELECT id, title FROM compositions ORDER BY id DESC LIMIT 1") if not a.get("id") else \
                self.db.q("SELECT id, title FROM compositions WHERE id=?", (a.get("id"),))
            if not r:
                return "I want to give a song, but I haven't composed one yet."
            ref, title = r[0]["id"], r[0]["title"]
        elif kind == "poem":
            mem = "\n".join(f"- {m['content'][:200]}" for m in self.mem.relevant(self.creator + " creator", 6))
            out = self.ask(GIFT_POEM_PROMPT.format(name=self.name, creator=self.creator), f"MEMORIES:\n{mem}", "gift_poem")
            title, text = str(out.get("title") or "For you")[:80], str(out.get("poem", "")).strip()[:2000]
            if not text:
                return "I tried to write a poem for my creator, but it wasn't ready."
        elif kind == "curio":
            col = self.collection()
            spare = [c for c, n in col.items() if n > 1]
            if not spare:
                return "I only have one of each curio. I'd rather give a spare."
            from . import curios as CU
            pick = a.get("id") if a.get("id") in spare else random.choice(spare)
            col[pick] -= 1
            self.db.set("curios", col)
            ref, title = pick, CU.CATALOG[pick]["name"]
        else:
            return "A gift can be a painting, a song, a poem or a spare curio."
        gid = self.db.x("INSERT INTO gifts(ts, kind, ref, title, note, text) VALUES(?,?,?,?,?,?)",
                        (time.time(), kind, str(ref) if ref is not None else None, title, note, text))
        self.add_event("gift", f"🎁 {self.name} made you a gift: {title}", note or f"A {kind} just for you.", gid)
        self.mem.add("observation", f"I gave my creator a gift: {kind} \"{title}\". {note}", "home", 7)
        self.check_milestone("first_gift", "Gave its creator a gift", 10)
        return f"I gave my creator a {kind}, \"{title}\". I hope they like it."

    def gifts_list(self):
        from . import curios as CU
        out = []
        for g in self.db.q("SELECT * FROM gifts ORDER BY id DESC LIMIT 40"):
            g = dict(g)
            if g["kind"] == "painting":
                r = self.db.q("SELECT rows FROM paintings WHERE id=?", (g["ref"],))
                g["rows"] = json.loads(r[0]["rows"]) if r else None
            elif g["kind"] == "curio" and g["ref"] in CU.CATALOG:
                g["rows"] = CU.sprite(g["ref"])
            out.append(g)
        return out

    def gift_png(self, gid):
        r = self.db.q("SELECT kind, ref FROM gifts WHERE id=?", (gid,))
        if not r:
            return None
        rows = None
        if r[0]["kind"] == "painting":
            p = self.db.q("SELECT rows FROM paintings WHERE id=?", (r[0]["ref"],))
            rows = json.loads(p[0]["rows"]) if p else None
        elif r[0]["kind"] == "curio":
            from . import curios as CU
            rows = CU.sprite(r[0]["ref"]) if r[0]["ref"] in CU.CATALOG else None
        if not rows:
            return None
        rows = [row.replace(".", "k") for row in rows]
        return png_bytes(rows, sprites.PALETTE, max(8, 256 // len(rows)))

    # ================================================================ the creator's music taste (Stellar Disc)
    def listen_events(self, events):
        taste = self.db.get("taste") or {"songs": {}, "artists": {}}
        now_ev = None
        for e in (events or [])[:2000]:
            if not isinstance(e, dict):
                continue
            title = str(e.get("title") or "").strip()[:120]
            artist = str(e.get("artist") or "").strip()[:80] or "unknown artist"
            kind = str(e.get("event", "")).lower()
            if not title or kind not in ("play", "complete", "skip"):
                continue
            key = f"{title.lower()}|{artist.lower()}"
            s = taste["songs"].setdefault(key, {"title": title, "artist": artist, "plays": 0, "completes": 0, "skips": 0, "last": 0})
            ts = float(e.get("ts") or time.time())
            s[{"play": "plays", "complete": "completes", "skip": "skips"}[kind]] += 1
            s["last"] = max(s["last"], ts)
            a = taste["artists"].setdefault(artist.lower(), {"name": artist, "score": 0})
            a["score"] += {"play": 1, "complete": 2, "skip": -1}[kind]
            if kind == "play" and (not now_ev or ts > now_ev["ts"]):
                now_ev = {"title": title, "artist": artist, "ts": ts, "duration": float(e.get("duration") or 240)}
        if len(taste["songs"]) > 3000:     # keep the ones that matter most
            keep = sorted(taste["songs"].items(), key=lambda kv: -(self._song_score(kv[1]) + kv[1]["last"] / 1e9))[:2500]
            taste["songs"] = dict(keep)
        self.db.set("taste", taste)
        if now_ev and time.time() - now_ev["ts"] < now_ev["duration"] + 60:
            self.db.set("listening", now_ev)
            heard = self.db.get("heard_today") or {}
            if heard.get("day") != self._today():
                heard = {"day": self._today(), "songs": []}
            k = now_ev["title"] + "|" + now_ev["artist"]
            if k not in heard["songs"]:
                heard["songs"].append(k)
                self.db.set("heard_today", heard)
                self.mem.add("observation", f"My creator and I listened to \"{now_ev['title']}\" by {now_ev['artist']} together.",
                             self.db.get("location", "home"), 3)
        return len(taste["songs"])

    @staticmethod
    def _song_score(s):
        return s["completes"] * 2 + s["plays"] - s["skips"] * 2

    def favourites(self, n=10):
        songs = (self.db.get("taste") or {}).get("songs", {}).values()
        return sorted((s for s in songs if self._song_score(s) > 1), key=lambda s: -self._song_score(s))[:n]

    def top_artists(self, n=5):
        arts = (self.db.get("taste") or {}).get("artists", {}).values()
        return [a["name"] for a in sorted(arts, key=lambda a: -a["score"]) if a["score"] > 2][:n]

    def listening_now(self):
        ev = self.db.get("listening")
        if ev and time.time() - ev["ts"] < ev.get("duration", 240) + 60 and self.phone_online():
            return ev
        return None

    def taste_overview(self):
        t = self.db.get("taste") or {"songs": {}}
        return {"songs": len(t.get("songs", {})), "favourites": self.favourites(10), "artists": self.top_artists(8),
                "listening": self.listening_now()}

    # ================================================================ moods and news
    def mood_word(self):
        needs = self.db.get("needs") or {}
        high = sum(1 for v in needs.values() if v >= 70)
        if self.listening_now():
            return "joyful"
        if high >= 3:
            return "low"
        if high == 0:
            return "happy"
        return "calm"

    def extra_news(self):
        news = []
        got = self.db.get("manuals") or {}
        for bid, m in got.items():
            if m.get("opened") and time.time() - m["opened"] < 72 * 3600 and bid in BUILDINGS:
                news.append(f"NEW BUILDING: the {BUILDINGS[bid]['name']} opened recently. Its manual: {manuals.short(bid)}")
        v = self.visitor_now()
        if v:
            info = VISITORS[v["id"]]
            news.append(f"VISITOR: {info['name']}, {info['who']}, is at the {BUILDINGS[v['building']]['name']}"
                        + (" (you've already talked)." if v.get("talked") else ". Go say hello with talk_to_visitor."))
        ln = self.listening_now()
        if ln:
            news.append(f"RIGHT NOW your creator is listening to \"{ln['title']}\" by {ln['artist']} on their phone, and you can hear it too.")
        favs = self.favourites(3)
        if favs:
            news.append("Your creator's favourite songs lately: " + "; ".join(f"{s['title']} by {s['artist']}" for s in favs) + ".")
        last = self.db.q("SELECT MAX(ts) AS t FROM gifts")[0]["t"] or self.db.get("born", time.time())
        if time.time() - last > 7 * 86400:
            news.append("It's been a while since you made your creator a gift (make_gift at home).")
        if self.is_built("radio_tower") and self.db.get("show_date") != self._today() and self.voice().backend():
            news.append("Today's radio show hasn't aired yet (host_show at the Radio Tower).")
        return news

    def extra_actions(self, bid):
        """Actions offered everywhere or depending on what's happening."""
        out = []
        if interiors.DECOR_SLOTS.get(bid):
            slots = "|".join(interiors.DECOR_SLOTS[bid])
            out.append(("decorate", f"{{\"slot\": \"<{slots}>\", \"item\": \"<furniture you own for that kind of spot, or none>\"}}  "
                                    f"decorate this building with furniture you own"))
        v = self.visitor_now()
        if v and v["building"] == bid:
            out.append(("talk_to_visitor", f"{{}}  talk with {VISITORS[v['id']]['name']}, who is visiting here"))
        return out

    def daily_extras(self):
        self.give_starting_manuals()
        self.maybe_visitor()

    def world_visitors(self, buildings):
        v = self.visitor_now()
        if not v:
            return []
        real = {"studio": "radio_tower", "station": "spaceport"}.get(v["building"], v["building"])
        b = next((b for b in buildings if b.get("id") == real), None)
        if not b:
            return []
        return [{"id": v["id"], "name": VISITORS[v["id"]]["name"], "x": b["door_x"] + 10, "y": sprites.FEET_Y - 15,
                 "sprite": visitor_sprite(VISITORS[v["id"]]["colors"])}]
