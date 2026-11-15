"""Colony systems mixed into the Agent: events (phone notifications), credits and shop,
greenhouse, radio tower, archive vault, spaceport expeditions and the fabrication hangar."""
import datetime
import json
import os
import re
import shutil
import subprocess
import threading
import time

from . import plants as P
from . import prompts, sprites, web_tools
from .buildings import BUILDINGS
from .memory import words
from .osutil import IS_WIN, NO_WINDOW, WIN_PLAYER_PS, find_exe, run_quiet

try:
    import resource          # Linux/macOS only: CPU and file-size limits for sandboxed programs
except ImportError:
    resource = None

AUDIO_EXT = {".mp3", ".flac", ".ogg", ".opus", ".wav", ".m4a", ".aac"}
PLAYERS = [
    ("mpv", ["mpv", "--no-video", "--really-quiet", "--volume={volume}"]),
    ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", "{volume}"]),
    ("cvlc", ["cvlc", "--play-and-exit", "--quiet"]),
    ("mpg123", ["mpg123", "-q"]),
    ("paplay", ["paplay"]),
]
DEFAULT_INVENTORY = {"seeds": {"moon_moss": 2, "comet_clover": 2, "solar_sprout": 2},
                     "decor": [], "pots": 6, "forms": ["star_spirit"]}
COLOUR_PRICE, FORM_PRICE, POTS_PRICE, MAX_POTS = 10, 40, 30, 12


class ColonyMixin:
    # ================================================================ events
    def add_event(self, kind, title, body="", ref_id=None):
        return self.db.x("INSERT INTO events(ts, kind, ref_id, title, body) VALUES(?,?,?,?,?)",
                         (time.time(), kind, ref_id, title[:200], (body or "")[:1000]))

    # ================================================================ credits
    def credits(self):
        return int(self.db.get("credits", 0))

    def earn(self, amount, reason):
        amount = int(amount)
        if not amount:
            return
        self.db.set("credits", self.credits() + amount)
        self.db.x("INSERT INTO ledger(ts, amount, reason) VALUES(?,?,?)", (time.time(), amount, reason[:200]))

    def spend(self, amount, reason):
        if self.credits() < amount:
            return False
        self.earn(-amount, reason)
        return True

    def earn_capped(self, key, amount, reason, cap):
        """Earn at most `cap` credits per day from one kind of thing."""
        u = self._usage()
        got = u.get(key, 0)
        give = min(amount, cap - got)
        if give <= 0:
            return
        u[key] = got + give
        self.db.set("usage", u)
        self.earn(give, reason)

    def inventory(self):
        inv = self.db.get("inventory")
        if not inv:
            inv = json.loads(json.dumps(DEFAULT_INVENTORY))
            self.db.set("inventory", inv)
        return inv

    def shop_text(self):
        decor = ", ".join(f"decor:{n} ({p})" for n, p in sprites.DECOR_PRICES.items())
        unlocks = ", ".join(f"unlock:{bid} ({b['unlock_price']})" for bid, b in BUILDINGS.items()
                            if b.get("unlockable") and self.is_locked(bid))
        return (f"{decor}; seeds:<species> by tier (common 3, uncommon 10, rare 25, legendary 60); "
                f"pots (+2 pots, {POTS_PRICE}){'; ' + unlocks if unlocks else ''}")

    def act_check_balance(self, a, imp):
        rows = self.db.q("SELECT amount, reason FROM ledger ORDER BY id DESC LIMIT 6")
        recent = "; ".join(f"{'+' if r['amount'] > 0 else ''}{r['amount']} {r['reason']}" for r in rows)
        return f"I have {self.credits()} credits. Recent: {recent or 'nothing yet'}."

    def act_buy(self, a, imp):
        item = str(a.get("item", "")).strip().lower().replace(" ", "_")
        kind, _, name = item.partition(":")
        if not name:
            kind, name = "", kind
        inv = self.inventory()
        have = self.credits()
        if kind == "trader":
            ev = self.db.get("space_event") or {}
            stock = ev.get("stock") if ev.get("type") == "trader" else None
            key = next((k for k in (stock or {}) if k.split(":", 1)[1] == name), None)
            if not key:
                return "The trader doesn't have that (or has already left)."
            price = stock[key]
            if not self.spend(price, f"bought {name.replace('_', ' ')} from the trader"):
                return f"I can't afford the trader's {name.replace('_', ' ')} ({have}/{price} credits)."
            if key.startswith("seeds:"):
                inv["seeds"][name] = inv["seeds"].get(name, 0) + 1
            else:
                inv["decor"].append(name)
            self.db.set("inventory", inv)
            del stock[key]
            self.db.set("space_event", ev)
            return f"I bought {name.replace('_', ' ')} from the travelling trader for {price} credits!"
        if kind == "decor" or (not kind and name in sprites.DECOR_PRICES):
            price = sprites.DECOR_PRICES.get(name)
            if price is None:
                return f"The vault clerk doesn't sell '{name}'."
            if not self.spend(price, f"bought {name.replace('_', ' ')}"):
                return f"I can't afford the {name.replace('_', ' ')} yet ({have}/{price} credits)."
            inv["decor"].append(name)
            self.db.set("inventory", inv)
            return f"I bought a {name.replace('_', ' ')} for {price} credits. It's outside my Home Dome now."
        if kind == "seeds" or (not kind and name in P.SPECIES):
            sp = P.SPECIES.get(name)
            if not sp:
                return f"There are no seeds called '{name}'."
            price = P.TIER_PRICE[sp["tier"]]
            if not self.spend(price, f"bought {name.replace('_', ' ')} seed"):
                return f"I can't afford {name.replace('_', ' ')} seeds yet ({have}/{price} credits)."
            inv["seeds"][name] = inv["seeds"].get(name, 0) + 1
            self.db.set("inventory", inv)
            art = "an" if sp["tier"][0] in "aeiou" else "a"
            return f"I bought {art} {sp['tier']} {name.replace('_', ' ')} seed for {price} credits."
        if name in ("pots", "pot"):
            if inv["pots"] >= MAX_POTS:
                return "The greenhouse has no room for more pots."
            if not self.spend(POTS_PRICE, "bought 2 greenhouse pots"):
                return f"I can't afford more pots yet ({have}/{POTS_PRICE} credits)."
            inv["pots"] = min(MAX_POTS, inv["pots"] + 2)
            self.db.set("inventory", inv)
            return f"I bought 2 more pots. The greenhouse holds {inv['pots']} plants now."
        if kind == "unlock" or name in BUILDINGS:
            bid = self.resolve_building(name)
            b = BUILDINGS.get(bid or "", {})
            if not bid or not b.get("unlockable"):
                return f"'{name}' isn't something I can unlock."
            if not self.is_locked(bid):
                return f"The {b['name']} is already open to me."
            price = b["unlock_price"]
            if not self.spend(price, f"unlocked {b['name']}"):
                return f"I can't afford the {b['name']} yet ({have}/{price} credits)."
            self.unlock(bid, by="credits")
            return f"I paid {price} credits and got the blueprint for the {b['name']}! Now I need to choose a plot and build it."
        return f"The vault clerk didn't understand '{item}'."

    def daily_review(self):
        """Once a day: reward finished goals and healthy plants."""
        today = self._today()
        if self.db.get("review_date") == today:
            return
        self.db.set("review_date", today)
        goals = self.db.get("goals", [])
        since = self.db.get("plan_ts")
        if goals and since and self.db.get("plan_date") != today:
            mems = self.db.q("SELECT kind, content FROM memories WHERE ts >= ? ORDER BY id LIMIT 120", (since,))
            log = "\n".join(f"- ({m['kind']}) {m['content'][:200]}" for m in mems)
            try:
                out = self.ask(prompts.REVIEW, "GOALS:\n" + "\n".join(f"{i}. {g}" for i, g in enumerate(goals))
                               + f"\n\nWHAT HAPPENED:\n{log}", "review")
                done = [int(i) for i in (out.get("completed") or []) if str(i).isdigit() and int(i) < len(goals)]
                for i in sorted(set(done))[:3]:
                    self.earn(10, f"finished goal: {goals[i][:80]}")
                if done:
                    self.mem.add("observation", f"I finished {len(set(done))} of yesterday's goals and earned credits.", "bank", 5)
            except Exception:
                pass
        for p in self.db.q("SELECT * FROM plants WHERE alive=1 AND health >= 70"):
            self.earn(2, f"healthy plant: {p['nickname'] or p['species']}")

    # ================================================================ buildings / unlocking
    def resolve_building(self, text):
        t = str(text or "").lower().replace("_", " ")
        if not t:
            return None
        for bid, b in BUILDINGS.items():
            if t == bid.replace("_", " ") or t == b["name"].lower():
                return bid
        for bid, b in BUILDINGS.items():
            if bid.replace("_", " ") in t or b["name"].lower() in t:
                return bid
        aliases = {"salon": "salon", "greenhouse": "greenhouse", "garden": "greenhouse", "radio": "radio_tower",
                   "archive": "archive", "spaceport": "spaceport", "rocket": "spaceport", "hangar": "workshop",
                   "workshop": "workshop", "fabrication": "workshop", "vault": "bank", "bank": "bank"}
        for word, bid in aliases.items():
            if re.search(rf"\b{word}\b", t):
                return bid
        return None

    def unlock(self, bid, by="creator"):
        unlocked = set(self.db.get("unlocked", []))
        unlocked.add(bid)
        self.db.set("unlocked", sorted(unlocked))
        b = BUILDINGS[bid]
        if by == "creator":
            self.send_letter(f"I've unlocked the {b['name']} for you. {b['about'].split('.')[0]}. "
                             f"You have its blueprint now: pick a plot and build it from your Home Dome.")
        self.add_event("unlock", f"🔓 {b['name']} unlocked", f"Unlocked by {by}.")

    # ================================================================ greenhouse
    def pot_plants(self):
        return self.db.q("SELECT * FROM plants WHERE alive >= 0 ORDER BY id")

    def update_plants(self, force=False):
        now = time.time()
        for p in self.db.q("SELECT * FROM plants WHERE alive=1"):
            sp = P.SPECIES.get(p["species"])
            if not sp:
                continue
            dt = (now - (p["updated_ts"] or now)) / 3600
            if dt < 0.05 and not force:
                continue
            water_over = (now - p["last_water"]) / 3600 - sp["water_h"]
            feed_over = (now - p["last_feed"]) / 3600 - sp["feed_h"]
            delta = 0.0
            if water_over > 0:
                delta -= min(dt, water_over) * 3
            if feed_over > 0:
                delta -= min(dt, feed_over) * 1.5
            if p["light"] != sp["light"]:
                delta -= dt * 0.8
            if water_over <= 0 and feed_over <= 0 and p["light"] == sp["light"]:
                delta += dt * 2
            health = max(0.0, min(100.0, p["health"] + delta))
            paused = (self.db.get("space_event") or {}).get("type") == "eclipse"
            growth = p["growth"] + (0 if paused else (dt / 24 / sp["days"]) * (health / 100 if health > 40 else 0))
            stage = P.stage_for(min(growth, 1.0))
            name = p["nickname"] or p["species"].replace("_", " ")
            bloomed = p["bloomed"]
            if growth >= 1 and not bloomed:
                bloomed = 1
                self.earn(15, f"{name} bloomed")
                self.mem.add("observation", f"My {name} ({p['species'].replace('_', ' ')}) bloomed in the greenhouse!", "greenhouse", 8)
                self.add_event("plant", f"🌸 {name} bloomed", f"{self.name}'s {p['species'].replace('_', ' ')} is in full bloom.")
            alive = 1
            if health <= 0:
                alive, stage = 0, "wilted"
                self.mem.add("observation", f"My {name} wilted. I didn't take care of it well enough.", "greenhouse", 7)
                self.add_event("plant", f"🥀 {name} wilted", "A plant in the greenhouse died from neglect.")
            self.db.x("UPDATE plants SET health=?, growth=?, stage=?, alive=?, updated_ts=?, bloomed=? WHERE id=?",
                      (health, growth, stage, alive, now, bloomed, p["id"]))

    def plant_line(self, p):
        sp = P.SPECIES[p["species"]]
        name = p["nickname"] or p["species"].replace("_", " ")
        if p["alive"] == 0:
            return f"#{p['id']} {name}: WILTED (remove it to free the pot)"
        now = time.time()

        def due(last, every):
            left = every - (now - last) / 3600
            return f"due in {left:.0f}h" if left > 0 else f"OVERDUE by {-left:.0f}h"
        light = p["light"] if p["light"] == sp["light"] else f"{p['light']} (wants {sp['light']})"
        return (f"#{p['id']} {name} ({p['species']}, {sp['tier']}): {p['stage']}, health {p['health']:.0f}%, "
                f"water {due(p['last_water'], sp['water_h'])} (every {sp['water_h']}h), "
                f"food {due(p['last_feed'], sp['feed_h'])} (every {sp['feed_h']}h), light {light}")

    def act_check_plants(self, a, imp):
        self.update_plants(force=True)
        inv = self.inventory()
        pots = self.pot_plants()
        seeds = ", ".join(f"{k} x{v}" for k, v in inv["seeds"].items() if v) or "none"
        lines = [self.plant_line(p) for p in pots] or ["(no plants yet)"]
        return f"Pots used {len(pots)}/{inv['pots']}. Seeds: {seeds}. " + " | ".join(lines)

    def _plant_targets(self, a):
        pid = a.get("plant_id", "")
        if str(pid).lower() == "all":
            return self.db.q("SELECT * FROM plants WHERE alive=1")
        try:
            return self.db.q("SELECT * FROM plants WHERE id=? AND alive=1", (int(pid),))
        except (TypeError, ValueError):
            return []

    def act_plant(self, a, imp):
        species = str(a.get("species", "")).strip().lower().replace(" ", "_")
        inv = self.inventory()
        if species not in P.SPECIES:
            return f"I don't know a plant called '{species}'."
        if inv["seeds"].get(species, 0) < 1:
            return f"I don't have any {species.replace('_', ' ')} seeds. I could buy some at the Credit Vault."
        if len(self.pot_plants()) >= inv["pots"]:
            return "Every pot is full."
        nick = str(a.get("nickname", "")).strip()[:30]
        inv["seeds"][species] -= 1
        self.db.set("inventory", inv)
        now = time.time()
        pid = self.db.x("INSERT INTO plants(species, nickname, planted_ts, last_water, last_feed, light, updated_ts) "
                        "VALUES(?,?,?,?,?,?,?)", (species, nick, now, now, now, "medium", now))
        sp = P.SPECIES[species]
        return (f"I planted a {species.replace('_', ' ')} (#{pid}{', ' + nick if nick else ''}): {sp['about']}. "
                f"Care: water every {sp['water_h']}h, feed every {sp['feed_h']}h, {sp['light']} light.")

    def _care(self, a, field, verb, past, bad):
        plants = self._plant_targets(a)
        if not plants:
            return f"I couldn't find that plant to {verb}."
        now, out = time.time(), []
        hours_key = "water_h" if field == "last_water" else "feed_h"
        for p in plants:
            sp = P.SPECIES[p["species"]]
            name = p["nickname"] or p["species"].replace("_", " ")
            since = (now - p[field]) / 3600
            if since < sp[hours_key] * 0.4:
                self.db.x("UPDATE plants SET health=MAX(0, health-?) WHERE id=?", (bad, p["id"]))
                out.append(f"{name}: too soon, that hurt it")
            else:
                self.db.x(f"UPDATE plants SET {field}=?, health=MIN(100, health+3) WHERE id=?", (now, p["id"]))
                out.append(f"{name}: done")
        return f"I {past}: " + "; ".join(out)

    def act_water(self, a, imp):
        return self._care(a, "last_water", "water", "watered", 8)

    def act_feed(self, a, imp):
        return self._care(a, "last_feed", "feed", "fed", 6)

    def act_set_light(self, a, imp):
        level = str(a.get("level", "")).lower()
        plants = self._plant_targets(a)
        if level not in P.LIGHTS or not plants:
            return "I fiddled with the grow lamps but didn't change anything."
        for p in plants:
            self.db.x("UPDATE plants SET light=? WHERE id=?", (level, p["id"]))
        return f"I set the grow lamp to {level} for " + ", ".join(p["nickname"] or p["species"] for p in plants) + "."

    def act_remove(self, a, imp):
        try:
            rows = self.db.q("SELECT * FROM plants WHERE id=? AND alive>=0", (int(a.get("plant_id")),))
        except (TypeError, ValueError):
            rows = []
        if not rows:
            return "There's no plant in that pot."
        self.db.x("UPDATE plants SET alive=-1 WHERE id=?", (rows[0]["id"],))
        return f"I cleared {rows[0]['nickname'] or rows[0]['species']} from its pot."

    # ================================================================ radio tower
    def music_library(self):
        cache = getattr(self, "_music", None)
        if cache and time.time() - cache[0] < 3600:
            return cache[1]
        root = os.path.expanduser(self.cfg.get("radio", {}).get("music_dir", "~/Music"))
        songs = []
        if os.path.isdir(root):
            for dirpath, dirs, files in os.walk(root):
                dirs.sort()
                for f in sorted(files):
                    stem, ext = os.path.splitext(f)
                    if ext.lower() not in AUDIO_EXT:
                        continue
                    stem = re.sub(r"^\d+[\s._-]+", "", stem)
                    if " - " in stem:
                        artist, title = stem.split(" - ", 1)
                    else:
                        artist = os.path.basename(dirpath) if dirpath != root else "unknown artist"
                        title = stem
                    songs.append({"id": len(songs) + 1, "path": os.path.join(dirpath, f), "title": title.strip(),
                                  "artist": artist.strip(), "album": os.path.basename(dirpath)})
                if len(songs) >= 5000:
                    break
        self._music = (time.time(), songs)
        return songs

    def player_cmd(self):
        vol = str(self.cfg.get("radio", {}).get("volume", 60))
        for exe, cmd in PLAYERS:
            path = find_exe(exe)
            if path:
                return [path] + [c.replace("{volume}", vol) for c in cmd[1:]]
        if IS_WIN:   # Windows always has its own media player, reached through PowerShell
            return ["powershell", "-NoProfile", "-NonInteractive", "-Command", WIN_PLAYER_PS]
        return None

    def quiet_now(self):
        q = self.cfg.get("radio", {}).get("quiet_hours", [23, 8])
        h = datetime.datetime.now().hour
        start, end = q
        return (start <= h or h < end) if start > end else (start <= h < end)

    def now_playing(self):
        proc = getattr(self, "_proc", None)
        if proc and proc.poll() is None:
            return getattr(self, "_now", None)
        return None

    def act_list_music(self, a, imp):
        songs = self.music_library()
        if not songs:
            return "The radio's music shelf is empty. My creator hasn't added a music folder yet."
        q = words(str(a.get("search", "")))
        if q:
            hits = [s for s in songs if q & words(f"{s['title']} {s['artist']} {s['album']}")][:10]
        else:
            import random
            hits = random.sample(songs, min(10, len(songs)))
        if not hits:
            return f"No songs matched. There are {len(songs)} songs in the collection."
        return f"{len(songs)} songs in the collection. Found: " + "; ".join(
            f"#{s['id']} {s['title']} by {s['artist']}" for s in hits)

    def act_play_music(self, a, imp):
        songs = self.music_library()
        try:
            song = songs[int(a.get("song_id")) - 1]
        except (TypeError, ValueError, IndexError):
            return "I couldn't find that song on the shelf. I should list the music first."
        label = f"\"{song['title']}\" by {song['artist']}"
        if self.quiet_now():
            return f"It's quiet hours, so I listened to {label} softly in my head instead of out loud."
        if self._usage().get("plays", 0) >= self.cfg.get("radio", {}).get("plays_per_day", 12):
            return "I've played a lot of music today. The radio needs a rest."
        cmd = self.player_cmd()
        if not cmd:
            return f"I wanted to play {label}, but the radio has no player installed (my creator could install mpv)."
        self.act_stop_music({}, 0)
        env = dict(os.environ)
        if cmd[0] == "powershell":
            env["STELLAR_SONG"] = song["path"]
            env["STELLAR_VOLUME"] = str(self.cfg.get("radio", {}).get("volume", 60) / 100)
            full = cmd
        else:
            full = cmd + [song["path"]]
        try:
            self._proc = subprocess.Popen(full, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL, env=env, creationflags=NO_WINDOW)
        except OSError as e:
            return f"The radio crackled and failed: {e}"
        self._now = {"title": song["title"], "artist": song["artist"], "started": time.time()}
        self._bump("plays")
        return f"I put on {label}. The colony fills with sound."

    def act_stop_music(self, a, imp):
        proc = getattr(self, "_proc", None)
        if proc and proc.poll() is None:
            proc.terminate()
            return "I turned the music off."
        return "Nothing was playing."

    def act_broadcast_log(self, a, imp):
        text = str(a.get("text", "")).strip()
        if not text:
            return "I keyed the mic but said nothing."
        if self._usage().get("logs", 0) >= 4:
            return "I've already broadcast enough logs today."
        self._bump("logs")
        bid = self.db.x("INSERT INTO broadcasts(ts, text) VALUES(?,?)", (time.time(), text[:2000]))
        self.add_event("log", f"📡 {self.name}'s colony log", text, bid)
        return f"I broadcast a colony log: \"{text[:200]}\""

    # ================================================================ archive vault
    def act_archive_memories(self, a, imp):
        cutoff = time.time() - 2 * 86400
        rows = self.db.q("SELECT * FROM memories WHERE archived=0 AND kind!='reflection' AND ts < ? ORDER BY id LIMIT 40",
                         (cutoff,))
        if len(rows) < 12:
            return "There aren't enough older memories to make a chapter yet. Life needs to happen first."
        n = self.db.q("SELECT COUNT(*) AS c FROM chapters")[0]["c"] + 1
        text = "\n".join(f"- ({r['kind']}) {r['content'][:250]}" for r in rows)
        out = self.ask(prompts.CHAPTER.format(name=self.name, n=n),
                       f"WHO YOU ARE:\n{self.personality()}\n\nMEMORIES:\n{text}", "chapter")
        title = str(out.get("title", f"Chapter {n}"))[:120]
        body = str(out.get("text", "")).strip()[:6000]
        if not body:
            return "I sat in the archive but couldn't find the words for this chapter."
        self.db.x("INSERT INTO chapters(ts, title, text, from_ts, to_ts) VALUES(?,?,?,?,?)",
                  (time.time(), title, body, rows[0]["ts"], rows[-1]["ts"]))
        ids = [r["id"] for r in rows]
        self.db.x(f"UPDATE memories SET archived=1 WHERE id IN ({','.join('?' * len(ids))})", ids)
        self.earn(5, f"wrote life chapter {n}")
        return f"I wrote chapter {n} of my life story, \"{title}\": {body[:300]}"

    def act_read_chapter(self, a, imp):
        rows = self.db.q("SELECT * FROM chapters ORDER BY id")
        if not rows:
            return "My life story has no chapters yet."
        try:
            i = max(1, min(len(rows), int(a.get("number", len(rows)))))
        except (TypeError, ValueError):
            i = len(rows)
        c = rows[i - 1]
        return f"Chapter {i}, \"{c['title']}\": {c['text'][:900]}"

    def relevant_chapters(self, query, n=2):
        q = words(query)
        if not q:
            return []
        rows = self.db.q("SELECT id, title, text FROM chapters ORDER BY id DESC LIMIT 200")
        scored = sorted(((len(q & words(r["title"] + " " + r["text"])), r) for r in rows), key=lambda t: -t[0])
        return [r for s, r in scored[:n] if s > 0]

    # ================================================================ spaceport
    def expedition(self):
        eid = self.db.get("away")
        if not eid:
            return None
        rows = self.db.q("SELECT * FROM expeditions WHERE id=?", (eid,))
        return rows[0] if rows else None

    def web_study(self, topic, max_chars=7000):
        material, sources, links = [], [], []
        if "internet_cafe" in self.closed_buildings() or self.storm():
            return None, None, [], []
        try:
            for title in web_tools.wiki_search(topic, 2):
                ext = web_tools.wiki_extract(title)
                if ext:
                    material.append(f"[Wikipedia: {title}]\n{ext}")
                    sources.append(f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")
        except Exception as e:
            material.append(f"(Wikipedia unavailable: {e})")
        try:
            links = web_tools.ddg_search(topic, 5)
            if links:
                material.append("[Search results]\n" + "\n".join(f"- {l['title']} ({l['url']})" for l in links))
        except Exception:
            pass
        if not sources and not links:
            return None, None, [], []
        summary, follow = self._summarize("\n\n".join(material)[:max_chars], topic)
        return summary, follow, sources, links

    def act_start_expedition(self, a, imp):
        if self.expedition():
            return "I'm already on an expedition."
        topic = str(a.get("topic", "")).strip()[:120]
        if not topic:
            return "I stood on the launch pad but couldn't decide where to go."
        try:
            hours = max(1.0, min(8.0, float(a.get("hours", 2))))
        except (TypeError, ValueError):
            hours = 2.0
        n = int(min(8, max(2, hours * 1.5)))
        out = self.ask(prompts.EXPEDITION_PLAN.format(name=self.name, n=n), f"TOPIC: {topic}", "exp_plan")
        legs = [str(x)[:120] for x in (out.get("legs") or []) if str(x).strip()][:n] or [topic]
        eid = self.db.x("INSERT INTO expeditions(ts, topic, hours, return_ts, legs) VALUES(?,?,?,?,?)",
                        (time.time(), topic, hours, time.time() + hours * 3600, json.dumps(legs)))
        self.db.set("away", eid)
        self.db.set("exp_leg", 0)
        self.add_event("expedition", f"🚀 {self.name} launched an expedition",
                       f"Studying \"{topic}\" for about {hours:g} hours.", eid)
        return (f"I launched an expedition to study \"{topic}\" for {hours:g} hour{'s' if hours != 1 else ''}. "
                f"Stops: " + "; ".join(legs))

    def expedition_turn(self, e):
        legs = json.loads(e["legs"] or "[]")
        i = self.db.get("exp_leg", 0)
        if i < len(legs):
            leg = legs[i]
            summary, follow, sources, links = self.web_study(f"{e['topic']} {leg}" if e["topic"].lower() not in leg.lower() else leg)
            if summary is None:
                out = self.ask(prompts.SUMMARIZE.format(name=self.name),
                               f"TOPIC: {leg}\n\n--- WEB TEXT START ---\n(No uplink out here. Think through what you already know.)\n--- WEB TEXT END ---",
                               "summarize")
                summary = str(out.get("summary", "")).strip()
            note = f"\n## {leg}\n{summary}\n" + (f"Sources: {', '.join(sources)}\n" if sources else "")
            self.db.x("UPDATE expeditions SET notes = notes || ? WHERE id=?", (note, e["id"]))
            self.db.set("exp_leg", i + 1)
            self.mem.add("observation", f"Expedition stop {i + 1}/{len(legs)} ({leg}): {summary[:300]}", "spaceport", 4)
            return {"building": "spaceport", "action": "expedition", "thought": f"Exploring {leg}",
                    "result": f"Expedition stop {i + 1}: {leg}"}
        if time.time() < e["return_ts"]:
            return {"building": "spaceport", "action": "expedition", "thought": "Drifting between the stars, thinking.",
                    "result": "Still travelling."}
        notes = self.db.q("SELECT notes FROM expeditions WHERE id=?", (e["id"],))[0]["notes"]
        out = self.ask(prompts.EXPEDITION_REPORT.format(name=self.name),
                       f"TOPIC: {e['topic']}\n\nFIELD NOTES:\n{notes[:9000]}", "exp_report")
        title = str(out.get("title", e["topic"]))[:120]
        report = str(out.get("report", "")).strip()[:8000]
        skills = [str(s)[:150] for s in (out.get("skills") or [])][:5]
        if skills:
            report += "\n\nWhat I can do now: " + "; ".join(skills)
        self.db.x("UPDATE expeditions SET report=?, status='returned' WHERE id=?", (report, e["id"]))
        self.db.x("INSERT INTO library(ts, topic, summary, source) VALUES(?,?,?,?)",
                  (time.time(), f"Expedition: {title}", report, "my expedition"))
        self.db.set("away", None)
        self.mem.add("observation", f"I came home from my expedition on \"{e['topic']}\". {report[:400]}", "spaceport", 8)
        self.earn(20, f"completed expedition: {e['topic'][:60]}")
        self.add_event("expedition", f"🛬 {self.name} is back: {title}", report[:600], e["id"])
        return {"building": "spaceport", "action": "expedition_return", "thought": "Home again!",
                "result": f"Returned with a report: {title}"}

    def act_read_reports(self, a, imp):
        rows = self.db.q("SELECT topic, report FROM expeditions WHERE status='returned' ORDER BY id DESC LIMIT 3")
        if not rows:
            return "I haven't been on any expeditions yet."
        return " | ".join(f"\"{r['topic']}\": {(r['report'] or '')[:350]}" for r in rows)

    # ================================================================ fabrication hangar
    @property
    def workshop_dir(self):
        d = os.path.join(os.path.dirname(self.home_dir), "workshop")
        os.makedirs(os.path.join(d, "programs"), exist_ok=True)
        os.makedirs(os.path.join(d, "sandbox"), exist_ok=True)
        return d

    def act_write_program(self, a, imp):
        name = re.sub(r"[^a-z0-9_]+", "_", str(a.get("name", "program")).lower()).strip("_")[:40] or "program"
        desc = str(a.get("description", "")).strip()[:600]
        code = str(a.get("code", ""))
        if len(code.strip()) < 5:
            return "I sketched a program but didn't write any code."
        if len(code) > 20000:
            return "That program is too big for the hangar (keep it under 20,000 characters)."
        waiting = self.db.q("SELECT COUNT(*) AS c FROM programs WHERE status='awaiting_approval'")[0]["c"]
        if waiting >= 3:
            return "Three programs are already waiting for approval. I'll wait."
        pid = self.db.x("INSERT INTO programs(ts, name, description, code) VALUES(?,?,?,?)",
                        (time.time(), name, desc, code))
        with open(os.path.join(self.workshop_dir, "programs", f"{pid}_{name}.py"), "w", encoding="utf-8") as f:
            f.write(code)
        rid = self.db.x("INSERT INTO requests(ts, kind, content, reason, extra) VALUES(?,?,?,?,?)",
                        (time.time(), "run_program", f"Run my program '{name}': {desc}", "", json.dumps({"program_id": pid})))
        self.db.x("UPDATE programs SET request_id=? WHERE id=?", (rid, pid))
        self.add_event("request", f"🛠 {self.name} wants to run '{name}'", desc, rid)
        return f"I wrote a program called '{name}' and asked {self.creator} to approve running it."

    def act_list_programs(self, a, imp):
        rows = self.db.q("SELECT * FROM programs ORDER BY id DESC LIMIT 5")
        if not rows:
            return "I haven't built any programs yet."
        return " | ".join(f"#{r['id']} {r['name']}: {r['status']}" + (f", output: {(r['output'] or '')[:200]}" if r["output"] else "")
                          for r in rows)

    def sandbox_kind(self):
        """bubblewrap on Linux; Docker on Windows (or on Linux without bubblewrap)."""
        if not IS_WIN and shutil.which("bwrap"):
            return "bwrap"
        if find_exe("docker"):
            return "docker"
        return None

    def sandbox_available(self):
        return self.sandbox_kind() is not None

    def _bwrap_cmd(self, work):
        bw = shutil.which("bwrap")
        py = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else (shutil.which("python3") or "python3")
        cmd = [bw, "--unshare-all", "--die-with-parent", "--new-session", "--ro-bind", "/usr", "/usr"]
        for d in ("/bin", "/lib", "/lib64", "/lib32", "/sbin"):
            if os.path.islink(d):
                cmd += ["--symlink", os.readlink(d), d]
            elif os.path.isdir(d):
                cmd += ["--ro-bind", d, d]
        for d in ("/etc/alternatives", "/etc/ssl", "/etc/localtime"):
            cmd += ["--ro-bind-try", d, d]
        return cmd + ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--bind", work, "/work", "--chdir", "/work",
                      "--setenv", "HOME", "/work", py, "-I", "/work/program.py"]

    def _docker_cmd(self, work):
        return [find_exe("docker"), "run", "--rm", "--network", "none", "--memory", "512m", "--cpus", "1",
                "--pids-limit", "64", "--read-only", "--tmpfs", "/tmp", "-v", f"{os.path.abspath(work)}:/work",
                "-w", "/work", "-e", "HOME=/work", "python:3.12-slim", "python", "-I", "/work/program.py"]

    def run_program(self, pid):
        rows = self.db.q("SELECT * FROM programs WHERE id=?", (pid,))
        if not rows:
            return
        prog = rows[0]
        kind = self.sandbox_kind()
        if not kind:
            self.db.x("UPDATE programs SET status='needs_sandbox' WHERE id=?", (pid,))
            how = "Docker Desktop" if IS_WIN else "bubblewrap"
            self.send_letter(f"I approved '{prog['name']}', but the safe sandbox ({how}) isn't installed on the hub yet, "
                             f"so it can't run. I'll install it.")
            return
        self.db.x("UPDATE programs SET status='running' WHERE id=?", (pid,))
        work = os.path.join(self.workshop_dir, "sandbox")
        with open(os.path.join(work, "program.py"), "w", encoding="utf-8") as f:
            f.write(prog["code"])
        cmd = self._bwrap_cmd(work) if kind == "bwrap" else self._docker_cmd(work)

        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
            resource.setrlimit(resource.RLIMIT_FSIZE, (20_000_000, 20_000_000))

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=45 if kind == "bwrap" else 120,
                               preexec_fn=limits if (kind == "bwrap" and resource) else None, creationflags=NO_WINDOW)
            output, code = (r.stdout + ("\n[errors]\n" + r.stderr if r.stderr.strip() else "")).strip(), r.returncode
        except subprocess.TimeoutExpired:
            output, code = "(stopped: took too long)", -1
        except Exception as e:
            output, code = f"(sandbox error: {e})", -1
        output = output[-4000:] or "(no output)"
        status = "done" if code == 0 else "failed"
        self.db.x("UPDATE programs SET status=?, output=?, exit_code=? WHERE id=?", (status, output, code, pid))
        if code == 0:
            self.earn(8, f"program '{prog['name']}' ran successfully")
        self.db.x("INSERT INTO letters(ts, sender, content) VALUES(?,?,?)",
                  (time.time(), "Fabrication Hangar", f"Your program '{prog['name']}' {'finished' if code == 0 else 'failed'} "
                                                     f"(exit {code}). Output:\n{output[:1500]}"))
        self.add_event("program", f"🛠 '{prog['name']}' {'finished' if code == 0 else 'failed'}", output[:500], pid)

    def run_program_async(self, pid):
        threading.Thread(target=self.run_program, args=(pid,), daemon=True).start()

    # ================================================================ questions
    def act_ask_question(self, a, imp):
        q = str(a.get("question", "")).strip()
        if not q:
            return "I started to ask something but lost the thought."
        pending = self.db.q("SELECT COUNT(*) AS c FROM requests WHERE status='pending' AND kind NOT IN ('letter')")[0]["c"]
        if pending >= self.cfg["limits"]["max_pending_requests"]:
            return f"I already have {pending} things waiting for an answer. I'll be patient."
        rid = self.db.x("INSERT INTO requests(ts, kind, content, reason) VALUES(?,?,?,?)", (time.time(), "question", q[:1500], ""))
        self.add_event("question", f"❓ {self.name} asks", q, rid)
        return f"I asked {self.creator}: \"{q[:200]}\""

    # ================================================================ overview for dashboard + phone
    def colony_overview(self):
        self.update_plants()
        inv = self.inventory()
        plants = []
        for p in self.pot_plants():
            sp = P.SPECIES.get(p["species"], {})
            plants.append({"id": p["id"], "name": p["nickname"] or p["species"].replace("_", " "),
                           "species": p["species"], "tier": sp.get("tier"), "stage": p["stage"],
                           "health": round(p["health"]), "alive": p["alive"], "line": self.plant_line(p)})
        e = self.expedition()
        legs = json.loads(e["legs"]) if e else []
        return {
            "credits": self.credits(),
            "ledger": self.db.q("SELECT * FROM ledger ORDER BY id DESC LIMIT 25"),
            "inventory": inv, "plants": plants,
            "now_playing": self.now_playing(), "music_count": len(self.music_library()),
            "player": ("Windows media player" if (self.player_cmd() or [""])[0] == "powershell"
                       else os.path.basename((self.player_cmd() or [""])[0]) or None), "quiet_now": self.quiet_now(),
            "player_hint": "Install VLC or mpv" if IS_WIN else "sudo apt install mpv",
            "sandbox_hint": ("Install Docker Desktop (winget install Docker.DockerDesktop) and start it"
                             if IS_WIN else "sudo apt install bubblewrap"),
            "broadcasts": self.db.q("SELECT * FROM broadcasts ORDER BY id DESC LIMIT 10"),
            "chapters": self.db.q("SELECT id, ts, title, text FROM chapters ORDER BY id DESC LIMIT 20"),
            "expedition": ({"topic": e["topic"], "return_ts": e["return_ts"], "legs": legs,
                            "done": self.db.get("exp_leg", 0)} if e else None),
            "reports": self.db.q("SELECT id, ts, topic, report FROM expeditions WHERE status='returned' ORDER BY id DESC LIMIT 5"),
            "programs": self.db.q("SELECT id, ts, name, description, code, status, output, exit_code FROM programs ORDER BY id DESC LIMIT 10"),
            "sandbox": self.sandbox_available(),
        }
