"""Hobbies and skills, mixed into the Agent: painting, writing, composing, astronomy, collecting,
games (puzzles + chess with the creator), plus the Space Station's study-and-test loop, personality
traits, the weekly digest and memory search."""
import datetime
import json
import math
import os
import random
import time
import urllib.request

from . import chess, curios, prompts, synth
from .memory import Memory, words

HOBBIES = {
    "painting": "🎨", "writing": "✍️", "composing": "🎼", "astronomy": "🔭",
    "collecting": "🧺", "games": "♟️", "gardening": "🌱", "coding": "🛠",
}
LEVELS = [0, 10, 30, 60, 100, 150, 210, 280, 360, 450, 550]   # xp needed for level 1..11
PAINT_PALETTE = {"k": "black", "w": "white", "s": "silver", "S": "grey", "n": "navy", "N": "dusk blue",
                 "c": "cyan", "C": "teal", "p": "lilac", "P": "purple", "m": "pink", "M": "plum",
                 "r": "red", "R": "maroon", "y": "yellow", "Y": "orange", "e": "green", "E": "forest green",
                 "o": "brown", "t": "cream"}
GALLERY_WALL = 12
SPOTS_PER_FLOOR, MAX_FLOORS = 12, 4
FLOOR_PRICES = {2: 150, 3: 300, 4: 600}
SHOWCASE_TYPES = ("painting", "curio", "plant", "writing")
SPACE_WORDS = ["comet", "nebula", "orbit", "galaxy", "quasar", "meteor", "eclipse", "rocket", "planet", "aurora",
               "gravity", "station", "cosmos", "stardust", "satellite", "telescope", "asteroid", "pulsar", "lunar", "photon"]
TRAITS = ["curious", "creative", "social", "calm", "brave", "playful", "thoughtful"]


def level_for(xp):
    lvl = 0
    for i, need in enumerate(LEVELS):
        if xp >= need:
            lvl = i + 1
    return lvl


def moon_phase(now=None):
    """Returns (fraction 0..1 through the cycle, name)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    known_new = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc)
    f = ((now - known_new).total_seconds() / 86400 / 29.530588853) % 1
    names = ["new moon", "waxing crescent", "first quarter", "waxing gibbous", "full moon",
             "waning gibbous", "last quarter", "waning crescent"]
    return f, names[int((f * 8) + 0.5) % 8]


class HobbiesMixin:
    # ================================================================ skills
    def hobbies(self):
        return self.db.get("hobbies", {})

    def gain_xp(self, hobby, amount, why=""):
        hs = self.hobbies()
        h = hs.get(hobby)
        if h is None:
            h = {"xp": 0, "since": time.time()}
            self.mem.add("observation", f"I took up a new hobby: {hobby}.", self.db.get("location", "home"), 6)
            self.add_event("hobby", f"{HOBBIES.get(hobby, '')} {self.name} took up {hobby}", why[:200])
        before = level_for(h["xp"])
        h["xp"] += int(amount)
        hs[hobby] = h
        self.db.set("hobbies", hs)
        after = level_for(h["xp"])
        if after > before and before > 0:
            self.earn(5 * after, f"{hobby} skill reached level {after}")
            self.mem.add("observation", f"My {hobby} skill reached level {after}!", self.db.get("location", "home"), 7)
            self.add_event("hobby", f"{HOBBIES.get(hobby, '')} {self.name}: {hobby} level {after}", f"+{5 * after} credits")
        return after

    def hobby_level(self, hobby):
        return level_for(self.hobbies().get(hobby, {}).get("xp", 0)) or 1

    def hobbies_text(self):
        hs = self.hobbies()
        mine = ", ".join(f"{k} lv{level_for(v['xp'])}" for k, v in sorted(hs.items(), key=lambda kv: -kv[1]["xp"]))
        untried = [k for k in HOBBIES if k not in hs]
        return (mine or "none yet") + (f". Hobbies you haven't tried: {', '.join(untried)}" if untried else "")

    # ================================================================ painting
    def canvas_size(self):
        lvl = self.hobby_level("painting")
        return 8 if lvl <= 2 else 12 if lvl <= 4 else 16

    def act_paint(self, a, imp):
        subject = str(a.get("subject", "")).strip()[:200] or "something I love"
        title = str(a.get("title", "")).strip()[:80] or subject[:40]
        size = self.canvas_size()
        legend = ", ".join(f"{k}={v}" for k, v in PAINT_PALETTE.items())
        out = self.ask(prompts.PAINT.format(name=self.name, size=size),
                       f"SUBJECT: {subject}\nTITLE: {title}\nCOLOURS (one letter per pixel): {legend}\n"
                       f"Use '.' for empty background.", "paint")
        rows = out.get("rows") or []
        if not isinstance(rows, list):
            rows = []
        clean = []
        for r in rows[:size]:
            r = "".join(ch if ch in PAINT_PALETTE or ch == "." else "." for ch in str(r))[:size]
            clean.append(r.ljust(size, "."))
        while len(clean) < size:
            clean.append("." * size)
        if sum(ch != "." for row in clean for ch in row) < size:
            return "I stared at the blank canvas for a long time but nothing came out."
        about = str(out.get("about", "")).strip()[:400]
        pid = self.db.x("INSERT INTO paintings(ts, title, about, size, rows, hung) VALUES(?,?,?,?,?,NULL)",
                        (time.time(), title, about, size, json.dumps(clean)))
        self.gain_xp("painting", 6 + size // 4, f"painted \"{title}\"")
        return f"I painted #{pid} \"{title}\" ({size}x{size}). {about}"

    def act_hang_painting(self, a, imp):
        """Gallery walls: 12 paintings. (At home, paintings go in the showcase instead.)"""
        if self.db.get("location") != "gallery":
            return self.act_showcase({"type": "painting", "id": a.get("painting_id"), "floor": a.get("floor"),
                                      "spot": a.get("spot")}, imp)
        try:
            pid = int(a.get("painting_id"))
        except (TypeError, ValueError):
            return "I picked up a frame but didn't choose a painting."
        rows = self.db.q("SELECT * FROM paintings WHERE id=?", (pid,))
        if not rows:
            return "I couldn't find that painting."
        hung = self.db.q("SELECT id, title FROM paintings WHERE hung='gallery' ORDER BY hung_ts")
        replace = a.get("replace_id")
        note = ""
        if len(hung) >= GALLERY_WALL:
            if not replace:
                return ("Every gallery wall is full. I need to choose one to take down (replace_id): " +
                        ", ".join(f"#{h['id']} {h['title']}" for h in hung))
            self.db.x("UPDATE paintings SET hung=NULL WHERE id=? AND hung='gallery'", (int(replace),))
            note = f" in place of #{replace}"
        self.db.x("UPDATE paintings SET hung='gallery', hung_ts=? WHERE id=?", (time.time(), pid))
        return f"I hung \"{rows[0]['title']}\" in the Gallery{note}."

    # ================================================================ home showcase (floors x 12 spots)
    def home(self):
        h = self.db.get("home_showcase")
        if not h:
            h = {"floors": 1, "spots": {}}
        return h

    def floors(self):
        return self.home()["floors"]

    def showcase_label(self, item):
        t, i = item["type"], item["id"]
        try:
            if t == "painting":
                return "painting \"" + self.db.q("SELECT title FROM paintings WHERE id=?", (int(i),))[0]["title"] + "\""
            if t == "curio":
                return curios.CATALOG[i]["name"]
            if t == "plant":
                p = self.db.q("SELECT nickname, species FROM plants WHERE id=?", (int(i),))[0]
                return f"cutting of {p['nickname'] or p['species'].replace('_', ' ')}"
            if t == "writing":
                return "framed " + self.db.q("SELECT kind, title FROM writings WHERE id=?", (int(i),))[0]["title"]
        except (IndexError, KeyError, ValueError, TypeError):
            pass
        return f"{t} {i}"

    def showcase_text(self):
        h = self.home()
        parts = []
        for f in range(1, h["floors"] + 1):
            spots = h["spots"].get(str(f), {})
            items = "; ".join(f"spot {s}: {self.showcase_label(it)}" for s, it in sorted(spots.items(), key=lambda kv: int(kv[0])))
            parts.append(f"floor {f} ({len(spots)}/{SPOTS_PER_FLOOR}): {items or 'empty'}")
        return " | ".join(parts)

    def _owns(self, t, i):
        if t == "painting":
            return bool(self.db.q("SELECT 1 FROM paintings WHERE id=?", (i,)))
        if t == "curio":
            return i in self.collection()
        if t == "plant":
            return bool(self.db.q("SELECT 1 FROM plants WHERE id=? AND bloomed=1", (i,)))
        if t == "writing":
            return bool(self.db.q("SELECT 1 FROM writings WHERE id=?", (i,)))
        return False

    def act_showcase(self, a, imp):
        t = str(a.get("type", "")).lower()
        if t not in SHOWCASE_TYPES:
            return f"I can showcase: {', '.join(SHOWCASE_TYPES)}."
        raw = a.get("id")
        if t == "curio":
            q = str(raw or "").strip().lower()
            col = self.collection()
            i = next((c for c in col if c == q or curios.CATALOG[c]["name"].lower() == q), None) or \
                next((c for c in col if q and q in curios.CATALOG[c]["name"].lower()), None)
        else:
            try:
                i = int(raw)
            except (TypeError, ValueError):
                i = None
        if i is None or not self._owns(t, i):
            return ("I don't have that to display." + (" (Only plants that have bloomed can give a cutting.)" if t == "plant" else ""))
        h = self.home()
        for f, spots in h["spots"].items():
            for s, it in spots.items():
                if it["type"] == t and it["id"] == i:
                    return f"That's already on display (floor {f}, spot {s})."
        try:
            floor = max(1, min(h["floors"], int(a.get("floor") or 1)))
        except (TypeError, ValueError):
            floor = 1
        spots = h["spots"].setdefault(str(floor), {})
        spot = a.get("spot")
        note = ""
        if spot not in (None, ""):
            try:
                spot = int(spot)
            except (TypeError, ValueError):
                return "That isn't a spot number."
            if not 1 <= spot <= SPOTS_PER_FLOOR:
                return f"Each floor has spots 1 to {SPOTS_PER_FLOOR}."
            if str(spot) in spots:
                note = f", rotating out the {self.showcase_label(spots[str(spot)])}"
        else:
            free = [n for n in range(1, SPOTS_PER_FLOOR + 1) if str(n) not in spots]
            if not free:
                return (f"Floor {floor} is full. I need to choose a spot to rotate out: " +
                        "; ".join(f"spot {s}: {self.showcase_label(it)}" for s, it in sorted(spots.items(), key=lambda kv: int(kv[0]))))
            spot = free[0]
        spots[str(spot)] = {"type": t, "id": i, "ts": time.time()}
        self.db.set("home_showcase", h)
        if t == "curio":
            self.gain_xp("collecting", 1)
        return f"I put the {self.showcase_label(spots[str(spot)])} on floor {floor}, spot {spot}{note}."

    def act_remove_showcase(self, a, imp):
        h = self.home()
        try:
            f, s = str(int(a.get("floor", 1))), str(int(a.get("spot")))
        except (TypeError, ValueError):
            return "I need a floor and spot number."
        it = h["spots"].get(f, {}).pop(s, None)
        if not it:
            return "That spot is already empty."
        self.db.set("home_showcase", h)
        return f"I took the {self.showcase_label(it)} down and put it away."

    def act_upgrade_home(self, a, imp):
        h = self.home()
        nxt = h["floors"] + 1
        if nxt > MAX_FLOORS:
            return f"My Home Dome already has all {MAX_FLOORS} floors."
        price = FLOOR_PRICES[nxt]
        if not self.spend(price, f"built home floor {nxt}"):
            return f"Adding floor {nxt} costs {price} credits. I have {self.credits()}."
        h["floors"] = nxt
        self.db.set("home_showcase", h)
        self.add_event("build", f"🏠 {self.name} added floor {nxt} to the Home Dome", f"{SPOTS_PER_FLOOR} more showcase spots.")
        return f"I paid {price} credits and my Home Dome grew a floor! Now it has {nxt} floors and {nxt * SPOTS_PER_FLOOR} showcase spots."

    # ================================================================ writing + park
    def act_write(self, a, imp):
        kind = str(a.get("kind", "poem")).lower()
        kind = kind if kind in ("poem", "story", "myth", "essay", "song lyrics", "letter to the future") else "poem"
        title = str(a.get("title", "")).strip()[:100] or f"Untitled {kind}"
        text = str(a.get("text", "")).strip()[:6000]
        if len(text) < 20:
            return "I sat on a bench with my notebook, but the words didn't come today."
        wid = self.db.x("INSERT INTO writings(ts, kind, title, text) VALUES(?,?,?,?)", (time.time(), kind, title, text))
        self.gain_xp("writing", 4 + min(10, len(text) // 300), f"wrote \"{title}\"")
        return f"I wrote a {kind}, #{wid} \"{title}\": {text[:200]}"

    def act_relax(self, a, imp):
        if random.random() < 0.08:
            return "I wandered the park paths and found something half-buried: " + self.find_curio("a walk in the park")
        return random.choice(["I lay in the low-gravity grass and watched the planet turn.",
                              "I listened to the air recyclers hum like wind in trees.",
                              "I sat by the park fountain and let my thoughts drift."])

    # ================================================================ composing (Radio Tower studio)
    @property
    def studio_dir(self):
        d = os.path.join(os.path.dirname(self.home_dir), "studio")
        os.makedirs(d, exist_ok=True)
        return d

    def act_compose(self, a, imp):
        title = str(a.get("title", "")).strip()[:80] or "Untitled tune"
        melody = str(a.get("melody", ""))[:2000]
        bass = str(a.get("bass", ""))[:1200]
        if len(synth.parse(melody)) < 4:
            return ("I hummed at the keyboard but didn't write enough notes. "
                    "(Format: \"C4:1 E4:1 G4:2 R:1\", a note and octave, then beats.)")
        cid = self.db.x("INSERT INTO compositions(ts, title, mood, melody, bass, bpm, wave) VALUES(?,?,?,?,?,?,?)",
                        (time.time(), title, str(a.get("mood", ""))[:60], melody, bass,
                         int(a.get("bpm", 110) or 110), str(a.get("wave", "square"))))
        path = os.path.join(self.studio_dir, f"{cid}.wav")
        try:
            secs = synth.render_wav(path, melody, bass, a.get("bpm", 110), a.get("wave", "square"))
        except Exception as e:
            self.db.x("DELETE FROM compositions WHERE id=?", (cid,))
            return f"The studio couldn't record it: {e}"
        self.db.x("UPDATE compositions SET seconds=? WHERE id=?", (secs, cid))
        self.gain_xp("composing", 6 + min(8, int(secs // 8)), f"composed \"{title}\"")
        return f"I composed #{cid} \"{title}\" ({secs:.0f} seconds). I can play it on the radio."

    def act_play_composition(self, a, imp):
        try:
            c = self.db.q("SELECT * FROM compositions WHERE id=?", (int(a.get("composition_id")),))[0]
        except (TypeError, ValueError, IndexError):
            return "I couldn't find that recording."
        path = os.path.join(self.studio_dir, f"{c['id']}.wav")
        return self.play_file(path, c["title"], self.name).replace("I put on", "I played my own")

    # ================================================================ astronomy
    def apod(self):
        cache = self.db.get("apod")
        today = datetime.date.today().isoformat()
        if cache and cache.get("day") == today:
            return cache
        key = self.cfg.get("astronomy", {}).get("nasa_key", "DEMO_KEY")
        try:
            with urllib.request.urlopen(f"https://api.nasa.gov/planetary/apod?api_key={key}", timeout=15) as r:
                d = json.loads(r.read().decode())
            cache = {"day": today, "title": d.get("title", ""), "text": d.get("explanation", "")[:1500],
                     "url": d.get("url", ""), "date": d.get("date", "")}
        except Exception:
            cache = {"day": today, "title": "", "text": "", "url": ""}
        self.db.set("apod", cache)
        return cache

    def act_observe_sky(self, a, imp):
        f, phase = moon_phase()
        parts = [f"Through the telescope: Earth's moon is a {phase} ({f * 100:.0f}% through its cycle)."]
        ev = self.db.get("space_event")
        if ev and ev.get("end", 0) > time.time():
            parts.append(f"I logged the {ev['title'].split(' ', 1)[-1].lower()} in my observation book.")
        if not self.storm() and "internet_cafe" not in self.closed_buildings():
            ap = self.apod()
            if ap.get("title"):
                parts.append(f"Today's sky picture from NASA is \"{ap['title']}\": {ap['text'][:350]}")
        if random.random() < 0.05:
            parts.append("Something glinted on the observatory deck: " + self.find_curio("the observatory deck"))
        self.gain_xp("astronomy", 5, "observed the sky")
        return " ".join(parts)

    # ================================================================ collecting
    def collection(self):
        return self.db.get("curios", {})

    def find_curio(self, source, boost=0):
        cid = curios.random_find(boost=boost)
        col = self.collection()
        first = cid not in col
        col[cid] = col.get(cid, 0) + 1
        self.db.set("curios", col)
        item = curios.CATALOG[cid]
        self.gain_xp("collecting", 3 + {"common": 0, "uncommon": 2, "rare": 6, "legendary": 15}[item["rarity"]], source)
        label = f"a {item['rarity']} {item['name']}" + (" (new to my collection!)" if first else "")
        self.mem.add("observation", f"I found {label} from {source}.", self.db.get("location", "home"), 5 if item["rarity"] == "common" else 8)
        if item["rarity"] in ("rare", "legendary"):
            self.add_event("curio", f"✨ {self.name} found a {item['rarity']} curio", f"{item['name']} ({source})")
        return label

    def act_display_curio(self, a, imp):
        return self.act_showcase({"type": "curio", "id": a.get("curio"), "floor": a.get("floor"), "spot": a.get("spot")}, imp)

    def act_view_collection(self, a, imp):
        col = self.collection()
        if not col:
            return "My collection box is empty. Meteor showers, park walks, expeditions and traders might turn things up."
        by = {}
        for cid in col:
            by.setdefault(curios.CATALOG[cid]["kind"], []).append(curios.CATALOG[cid]["name"])
        return (f"I have {len(col)} of 128 curios. " +
                "; ".join(f"{k.replace('_', ' ')}: {', '.join(v)}" for k, v in by.items()))

    # ================================================================ games: puzzles
    def make_puzzle(self, level):
        kind = random.choice(["sequence", "scramble", "sum"])
        if kind == "sequence":
            a, d = random.randint(1, 9), random.randint(2, 4 + level)
            if level >= 4 and random.random() < .5:
                seq = [a * (2 ** i) for i in range(5)]
            else:
                seq = [a + d * i for i in range(5)]
            return f"What number comes next: {', '.join(map(str, seq[:4]))}, ?", str(seq[4])
        if kind == "scramble":
            w = random.choice([w for w in SPACE_WORDS if len(w) <= 5 + level])
            letters = list(w)
            while "".join(letters) == w:
                random.shuffle(letters)
            return f"Unscramble this space word: {''.join(letters).upper()}", w
        x, y = random.randint(2, 6 + level * 3), random.randint(2, 6 + level * 3)
        return f"A rover drives {x} km out and {y} km back, twice. How many km in total?", str(2 * (x + y))

    def act_solve_puzzle(self, a, imp):
        lvl = self.hobby_level("games")
        q, answer = self.make_puzzle(lvl)
        out = self.ask(prompts.PUZZLE.format(name=self.name), q, "puzzle")
        guess = str(out.get("answer", "")).strip().lower()
        if guess == answer:
            self.gain_xp("games", 4 + lvl)
            self.earn_capped("cr_puzzles", 2, "solved a puzzle", 10)
            return f"Puzzle: {q} I answered {guess}, correct!"
        self.gain_xp("games", 1)
        return f"Puzzle: {q} I said \"{guess}\", but it was {answer}. Next time."

    # ================================================================ games: chess with the creator
    def chess_state(self):
        return self.db.get("chess")

    def chess_new(self, creator_color="w"):
        g = chess.new_game()
        g["creator"] = "w" if creator_color in ("w", "white") else "b"
        g["comments"] = []
        self.db.set("chess", g)
        if g["creator"] == "b":
            g = self.chess_resident_move(g)
        return g

    def chess_creator_move(self, uci):
        g = self.chess_state()
        if not g or g.get("result"):
            raise ValueError("no game in progress")
        if g["turn"] != g["creator"]:
            raise ValueError(f"it's {self.name}'s turn")
        extra = {k: g[k] for k in ("creator", "comments")}
        g = chess.play(g, uci)
        g.update(extra)
        self.db.set("chess", g)
        if not g["result"]:
            g = self.chess_resident_move(g)
        if g["result"]:
            self.chess_finished(g)
        return g

    def chess_resident_move(self, g):
        legal = chess.legal_moves(g)
        if not legal:
            return g
        color = "white" if g["turn"] == "w" else "black"
        ctx = (f"You play {color} (uppercase = white, lowercase = black).\nBOARD:\n{chess.describe(g)}\n"
               f"MOVES SO FAR: {' '.join(g['moves'][-30:]) or 'none'}\n"
               f"{'You are in check! ' if chess.in_check(g) else ''}LEGAL MOVES (pick exactly one): {' '.join(legal)}")
        move, comment = None, ""
        try:
            out = self.ask(prompts.CHESS.format(name=self.name, creator=self.creator), ctx, "chess")
            move = str(out.get("move", "")).strip().lower()
            comment = str(out.get("comment", "")).strip()[:200]
        except Exception:
            pass
        if move not in legal:   # fall back to a sensible move: prefer captures
            caps = [m for m in legal if g["board"][chess.sq(m[2:4])] != "."]
            move = random.choice(caps or legal)
        extra = {k: g[k] for k in ("creator", "comments")}
        g = chess.play(g, move)
        g.update(extra)
        g["comments"] = (g.get("comments") or [])[-20:] + [{"move": move, "text": comment}]
        self.db.set("chess", g)
        if g["result"]:
            self.chess_finished(g)
        return g

    def chess_view(self):
        g = self.chess_state()
        if not g:
            return {"game": None}
        legal = chess.legal_moves(g) if not g.get("result") and g["turn"] == g.get("creator") else []
        return {"game": {"board": g["board"], "turn": g["turn"], "creator": g.get("creator", "w"), "moves": g["moves"],
                         "result": g.get("result"), "check": chess.in_check(g), "legal": legal,
                         "comments": (g.get("comments") or [])[-5:], "last": g["moves"][-1] if g["moves"] else None}}

    def chess_finished(self, g):
        if g.get("recorded"):
            return
        g["recorded"] = True
        self.db.set("chess", g)
        mine = "b" if g["creator"] == "w" else "w"
        if g["result"] == "1/2-1/2":
            outcome, xp = "a draw", 12
        elif (g["result"] == "1-0") == (mine == "w"):
            outcome, xp = "a win for me", 20
            self.earn(10, "won a chess game")
        else:
            outcome, xp = f"a win for {self.creator}", 10
        self.gain_xp("games", xp, "played chess")
        self.mem.add("observation", f"I finished a chess game with {self.creator} at the park: {outcome} "
                                    f"after {len(g['moves'])} moves.", "park", 7)
        self.add_event("game", f"♟️ Chess with {self.name}: {outcome}", f"{len(g['moves'])} moves")

    # ================================================================ space station (testing)
    def act_station_study(self, a, imp):
        now = time.time()
        due = self.db.q("SELECT * FROM quizzes WHERE due_ts <= ? ORDER BY due_ts LIMIT 1", (now,))
        if due:
            return self._take_quiz(due[0])
        studied = {r["note_id"] for r in self.db.q("SELECT note_id FROM quizzes")}
        notes = [n for n in self.db.q("SELECT * FROM library WHERE source != 'my own writing' ORDER BY id DESC LIMIT 40")
                 if n["id"] not in studied and len(n["summary"]) > 120]
        if not notes:
            upcoming = self.db.q("SELECT topic, due_ts FROM quizzes ORDER BY due_ts LIMIT 1")
            when = f" My next test, on {upcoming[0]['topic']}, is due later." if upcoming else ""
            return "There's nothing new to study up here. I should research more topics first." + when
        n = notes[0]
        out = self.ask(prompts.QUIZ_MAKE.format(name=self.name), f"TOPIC: {n['topic']}\nNOTES:\n{n['summary'][:3000]}", "quiz_make")
        qs = [q for q in (out.get("questions") or []) if isinstance(q, dict) and q.get("q") and q.get("a")][:3]
        if not qs:
            return "I tried to write test questions but couldn't settle on good ones."
        self.db.x("INSERT INTO quizzes(ts, topic, note_id, questions, interval_days, due_ts, mastery, attempts) "
                  "VALUES(?,?,?,?,?,?,0,0)", (now, n["topic"][:120], n["id"], json.dumps(qs), 0.5, now + 12 * 3600))
        return (f"In the station's study pod I wrote {len(qs)} test questions about \"{n['topic']}\". "
                f"I'll test myself in about 12 hours, from memory only.")

    def _take_quiz(self, z):
        qs = json.loads(z["questions"])
        related = Memory.fmt(self.mem.relevant(z["topic"], 6))
        ctx = (f"TOPIC: {z['topic']}\nWHAT YOU REMEMBER:\n{related}\n\nQUESTIONS:\n" +
               "\n".join(f"{i + 1}. {q['q']}" for i, q in enumerate(qs)))
        ans = self.ask(prompts.QUIZ_TAKE.format(name=self.name), ctx, "quiz_take").get("answers") or []
        key = "\n".join(f"{i + 1}. Q: {q['q']}\n   Correct: {q['a']}\n   Given: {ans[i] if i < len(ans) else '(no answer)'}"
                        for i, q in enumerate(qs))
        grade = self.ask(prompts.QUIZ_GRADE, key, "quiz_grade")
        try:
            score = max(0, min(len(qs), int(grade.get("correct", 0))))
        except (TypeError, ValueError):
            score = 0
        ratio = score / len(qs)
        interval = z["interval_days"] * 2.5 if ratio >= 0.66 else 0.5
        mastery = min(100, int(z["mastery"] * 0.5 + ratio * 60 + (20 if interval >= 7 else 0)))
        self.db.x("UPDATE quizzes SET interval_days=?, due_ts=?, mastery=?, attempts=attempts+1 WHERE id=?",
                  (interval, time.time() + interval * 86400, mastery, z["id"]))
        self.earn(3 * score, f"answered {score}/{len(qs)} on {z['topic'][:40]}") if score else None
        if mastery >= 80 and z["mastery"] < 80:
            self.earn(15, f"mastered {z['topic'][:50]}")
            self.add_event("study", f"🛰 {self.name} mastered a topic", z["topic"])
        return (f"I tested myself on \"{z['topic']}\" from memory: {score}/{len(qs)} correct. "
                f"Mastery {mastery}%. Next test in {interval:.1f} days.")

    # ================================================================ personality traits
    def traits(self):
        t = self.db.get("traits")
        if not t:
            t = {k: 50 for k in TRAITS}
        return t

    def adjust_traits(self, changes):
        t = self.traits()
        moved = []
        for k, v in (changes or {}).items():
            if k in t:
                try:
                    d = max(-5, min(5, int(v)))
                except (TypeError, ValueError):
                    continue
                if d:
                    t[k] = max(0, min(100, t[k] + d))
                    moved.append(f"{k} {'+' if d > 0 else ''}{d}")
        self.db.set("traits", t)
        return moved

    def traits_text(self):
        return ", ".join(f"{k} {v}" for k, v in self.traits().items())

    # ================================================================ weekly digest
    def maybe_digest(self):
        now = datetime.datetime.now()
        week = now.strftime("%G-W%V")
        if now.weekday() != 6 or now.hour < 18 or self.db.get("digest_week") == week:
            return
        self.db.set("digest_week", week)
        mems = self.db.q("SELECT kind, content FROM memories WHERE ts > ? AND kind IN "
                         "('observation','reflection','journal','dream','chat','plan') ORDER BY importance DESC, id DESC LIMIT 60",
                         (time.time() - 7 * 86400,))
        if not mems:
            return
        try:
            out = self.ask(prompts.DIGEST.format(name=self.name, creator=self.creator),
                           "\n".join(f"- ({m['kind']}) {m['content'][:220]}" for m in mems), "digest")
            text = str(out.get("digest", "")).strip()[:3000]
        except Exception:
            return
        if text:
            did = self.db.x("INSERT INTO digests(ts, week, text) VALUES(?,?,?)", (time.time(), week, text))
            self.add_event("digest", f"📰 This week in {self.name}'s colony", text[:700], did)

    # ================================================================ memory search
    def search_memories(self, question):
        mems = self.mem.relevant(question, 8)
        chapters = self.relevant_chapters(question, 2)
        q = words(question)
        notes = [n for n in self.db.q("SELECT topic, summary FROM library ORDER BY id DESC LIMIT 300")
                 if q & words(n["topic"] + " " + n["summary"])][:3]
        found = [{"kind": m["kind"], "ts": m["ts"], "text": m["content"]} for m in mems]
        ctx = (f"WHO YOU ARE:\n{self.personality()}\n\nMEMORIES:\n{Memory.fmt(mems) if mems else '- (none match)'}\n\n"
               f"LIFE STORY:\n" + ("\n".join(f"- {c['title']}: {c['text'][:400]}" for c in chapters) or "- (none)") +
               "\n\nNOTES:\n" + ("\n".join(f"- {n['topic']}: {n['summary'][:300]}" for n in notes) or "- (none)") +
               f"\n\n{self.creator} asks: {question}")
        try:
            answer = str(self.ask(prompts.RECALL.format(name=self.name, creator=self.creator), ctx, "recall").get("answer", ""))
        except Exception as e:
            answer = f"(couldn't think right now: {e})"
        return {"answer": answer.strip()[:2000], "memories": found}
