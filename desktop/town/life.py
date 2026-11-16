"""Life in the colony, mixed into the Agent: choosing building plots, sleeping and dreaming,
live chat with the creator, emotes, space events and milestones."""
import datetime
import json
import random
import time

from . import plants as P
from . import curios, prompts, sprites
from .buildings import BUILDINGS
from .memory import Memory

STARTERS = ["library", "internet_cafe", "post_office", "bank"]
BUILD_HOURS = 2
CHAT_IDLE_MIN = 10

EVENT_TYPES = {
    "solar_storm": {"title": "☀️ Solar storm", "hours": (3, 6), "weight": 3,
                    "about": "A solar storm is battering the colony. The Uplink Café and the Spaceport's uplink are offline until it passes."},
    "meteor_shower": {"title": "☄️ Meteor shower", "hours": (2, 3), "weight": 3,
                      "about": "A meteor shower is streaking over the colony! Stargazing from Home now might turn up stardust or a rare seed."},
    "eclipse": {"title": "🌑 Eclipse", "hours": (1, 2), "weight": 2,
                "about": "The planet is passing in front of the star. The greenhouse lamps flicker and plants pause their growth."},
    "stardust": {"title": "✨ Stardust drift", "hours": (3, 6), "weight": 5,
                 "about": "Glittering stardust is drifting over the colony. Now and then a little can be swept up and sold."},
    "dust_storm": {"title": "🌪️ Dust storm", "hours": (2, 4), "weight": 2,
                   "about": "A dust storm has closed the walkway. Everyone stays where they are until it clears."},
    "comet": {"title": "☄️ Comet pass", "hours": (5, 9), "weight": 1,
              "about": "A comet is sliding slowly across the sky. Its tail sometimes drops curio set pieces."},
    "trader": {"title": "🛸 Visiting trader", "hours": (5, 8), "weight": 2,
               "about": "A travelling trader has landed in the colony with rare goods. Buy with buy {\"item\": \"trader:<item>\"} at the Credit Vault."},
}

MILESTONES = [
    ("journal_10", "Wrote 10 journal entries", 10, "SELECT COUNT(*) AS c FROM memories WHERE kind='journal'", 10),
    ("journal_50", "Wrote 50 journal entries", 25, "SELECT COUNT(*) AS c FROM memories WHERE kind='journal'", 50),
    ("journal_100", "Wrote 100 journal entries", 50, "SELECT COUNT(*) AS c FROM memories WHERE kind='journal'", 100),
    ("first_question", "Asked its first question", 10, "SELECT COUNT(*) AS c FROM requests WHERE kind='question'", 1),
    ("first_note", "Wrote its first library note", 5, "SELECT COUNT(*) AS c FROM library WHERE source='my own writing'", 1),
    ("research_10", "Researched 10 topics", 15, "SELECT COUNT(*) AS c FROM library WHERE source!='my own writing'", 10),
    ("first_plant", "Planted its first seed", 5, "SELECT COUNT(*) AS c FROM plants", 1),
    ("first_bloom", "Grew its first bloom", 20, "SELECT COUNT(*) AS c FROM plants WHERE bloomed=1", 1),
    ("bloom_10", "Grew 10 blooms", 50, "SELECT COUNT(*) AS c FROM plants WHERE bloomed=1", 10),
    ("first_log", "Broadcast its first colony log", 5, "SELECT COUNT(*) AS c FROM broadcasts", 1),
    ("first_chapter", "Wrote the first chapter of its life story", 15, "SELECT COUNT(*) AS c FROM chapters", 1),
    ("first_expedition", "Came home from its first expedition", 20, "SELECT COUNT(*) AS c FROM expeditions WHERE status='returned'", 1),
    ("first_program", "Ran its first program", 20, "SELECT COUNT(*) AS c FROM programs WHERE status='done'", 1),
    ("first_dream", "Had its first dream", 5, "SELECT COUNT(*) AS c FROM memories WHERE kind='dream'", 1),
    ("first_chat", "Had its first live chat with you", 10, "SELECT COUNT(*) AS c FROM memories WHERE kind='chat'", 1),
    ("reflections_25", "Reached 25 insights about itself", 25, "SELECT COUNT(*) AS c FROM memories WHERE kind='reflection'", 25),
]
DAY_MILESTONES = [(7, "One week old", 15), (30, "One month old", 40), (100, "100 days old", 100), (365, "One year old", 300)]
CREDIT_MILESTONES = [(100, "Saved 100 credits", 10), (500, "Saved 500 credits", 25), (1500, "Saved 1,500 credits", 50)]


class LifeMixin:
    # ================================================================ plots
    def layout(self):
        raw = self.db.get("layout")
        return None if raw is None else {int(k): v for k, v in raw.items()}

    def save_layout(self, lay):
        self.db.set("layout", {str(k): v for k, v in lay.items()})

    def constructions(self):
        return self.db.get("construction", {})

    def plot_of(self, bid):
        for k, v in (self.layout() or {}).items():
            if v == bid:
                return k
        return None

    def is_built(self, bid):
        parent = BUILDINGS.get(bid, {}).get("upgrade_of")
        if parent:   # upgrades (Studio, Station) need no plot: they exist once unlocked and their parent is built
            return not self.is_locked(bid) and self.is_built(parent)
        return bid == "home" or (bid in (self.layout() or {}).values() and bid not in self.constructions())

    def available_buildings(self):
        """Plot buildings it's allowed to have (open by default, or unlocked). Upgrades aren't placed on plots."""
        return [bid for bid in BUILDINGS if bid != "home" and not self.is_locked(bid)
                and not BUILDINGS[bid].get("upgrade_of")]

    def blueprints(self):
        placed = set((self.layout() or {}).values()) | set(self.constructions())
        return [bid for bid in self.available_buildings() if bid not in placed]

    def upper_state(self):
        u = self.db.get("upper_street")
        if not u:
            return None
        return "open" if u["done"] <= time.time() else "construction"

    def plot_ids(self):
        return list(range(sprites.PLOTS)) + (sprites.upper_plots() if self.upper_state() == "open" else [])

    def empty_plots(self):
        lay = self.layout() or {}
        used = set(lay) | {c["plot"] for c in self.constructions().values()}
        return [i for i in self.plot_ids() if i not in used]

    def act_build_upper_street(self, a, imp):
        cost = self.cfg.get("upper_street_cost", 1500)
        if self.upper_state():
            return "The Upper Street is already " + ("open." if self.upper_state() == "open" else "being built.")
        if not self.spend(cost, "built the Upper Street"):
            return f"The Upper Street costs {cost} credits. I have {self.credits()}."
        self.db.set("upper_street", {"done": time.time() + 8 * 3600, "announced": False})
        self.add_event("build", f"🏗 {self.name} is building the Upper Street", "An elevated deck with 14 new plots, about 8 hours.")
        return f"I paid {cost} credits for the Upper Street: a raised deck with 14 more plots (16 to 30). It takes about 8 hours to build."

    def map_text(self):
        lay = self.layout() or {}
        cons = {c["plot"]: bid for bid, c in self.constructions().items()}
        parts = []
        for i in self.plot_ids():
            if i == sprites.UPPER_BASE:
                parts.append("UPPER STREET (reached by the lift beside the Home Dome):")
            if i in cons:
                parts.append(f"{i + 1}: {BUILDINGS[cons[i]]['name']} (being built)")
            elif i in lay:
                parts.append(f"{i + 1}: {BUILDINGS[lay[i]]['name']}")
            else:
                parts.append(f"{i + 1}: empty")
        return "; ".join(parts)

    def finish_constructions(self):
        u = self.db.get("upper_street")
        if u and u["done"] <= time.time() and not u.get("announced"):
            u["announced"] = True
            self.db.set("upper_street", u)
            self.mem.add("observation", "The Upper Street is finished! 14 new plots (16 to 30) up on the deck, reached by the lift.", "home", 8)
            self.add_event("build", "🌉 The Upper Street is open", "14 new plots up on the deck.")
        cons = self.constructions()
        if not cons:
            return
        now, lay, changed = time.time(), self.layout() or {}, False
        for bid, c in list(cons.items()):
            if c["done"] <= now:
                lay[c["plot"]] = bid
                del cons[bid]
                changed = True
                name = BUILDINGS[bid]["name"]
                self.mem.add("observation", f"The {name} is finished on plot {c['plot'] + 1}. It's open now!", bid, 7)
                self.give_manual(bid)
                self.give_manual(bid, opened=True)
                self.add_event("build", f"🏗 {name} is built", f"{self.name} built it on plot {c['plot'] + 1}.")
        if changed:
            self.save_layout(lay)
            self.db.set("construction", cons)
            self.check_milestone("first_build", "Built its first building", 10)

    def _plot_arg(self, a):
        try:
            p = int(a.get("plot")) - 1
        except (TypeError, ValueError):
            return None
        return p if p in self.plot_ids() else None

    def plan_colony(self, situation):
        """Lets the resident lay out its colony in one go (first day, or after an upgrade)."""
        lay = self.layout() or {}
        lay[sprites.HOME_PLOT] = "home"
        to_place = [b for b in (STARTERS if situation == "new" else self.available_buildings()) if b not in lay.values()]
        if not to_place:
            self.save_layout(lay)
            return "Nothing to place."
        names = "\n".join(f"- {b}: {BUILDINGS[b]['name']}: {BUILDINGS[b]['about'][:90]}" for b in to_place)
        ctx = (f"WHO YOU ARE:\n{self.personality()}\n\nThe colony has plots 1 to {sprites.PLOTS} in a row along one walkway. "
               f"Your Home Dome is on plot {sprites.HOME_PLOT + 1}, in the middle. Lower numbers are to the left, higher to the right.\n"
               f"BUILDINGS TO PLACE:\n{names}\n\nMore buildings may come later, so think about leaving room.")
        why, placements = "", {}
        try:
            out = self.ask(prompts.PLAN_LAYOUT.format(name=self.name), ctx, "layout")
            placements = out.get("placements") or {}
            why = str(out.get("why", ""))[:600]
        except Exception:
            pass
        used = set(lay)
        for bid in to_place:
            try:
                p = int(placements.get(bid)) - 1
            except (TypeError, ValueError):
                p = -1
            if p not in self.plot_ids() or p in used:
                free = [i for i in self.plot_ids() if i not in used]
                p = min(free, key=lambda i: abs(i - sprites.HOME_PLOT))
            lay[p] = bid
            used.add(p)
        self.save_layout(lay)
        summary = ", ".join(f"{BUILDINGS[b]['name']} on plot {p + 1}" for p, b in sorted(lay.items()) if b != "home")
        self.mem.add("plan", f"I laid out my colony: {summary}." + (f" Why: {why}" if why else ""), "home", 8)
        self.add_event("build", f"🗺 {self.name} planned the colony", why or summary)
        return summary

    def act_build(self, a, imp):
        bid = self.resolve_building(a.get("building"))
        if not bid or bid not in self.blueprints():
            bp = ", ".join(self.blueprints()) or "none"
            return f"I don't have a blueprint for that. Blueprints I can build: {bp}."
        p = self._plot_arg(a)
        if p is None or p not in self.empty_plots():
            return f"Plot {a.get('plot')} isn't free. Empty plots: {', '.join(str(i + 1) for i in self.empty_plots())}."
        cons = self.constructions()
        cons[bid] = {"plot": p, "done": time.time() + BUILD_HOURS * 3600}
        self.db.set("construction", cons)
        name = BUILDINGS[bid]["name"]
        self.add_event("build", f"🏗 {self.name} started building the {name}", f"On plot {p + 1}, about {BUILD_HOURS} hours.")
        return f"I chose plot {p + 1} for the {name}. Construction has started and takes about {BUILD_HOURS} hours."

    def act_move_building(self, a, imp):
        bid = self.resolve_building(a.get("building"))
        cost = self.cfg.get("move_cost", 1500)
        if not bid or bid == "home" or not self.is_built(bid):
            return "I can only move a finished building (and never my Home Dome)."
        p = self._plot_arg(a)
        if p is None or p not in self.empty_plots():
            return f"That plot isn't free. Empty plots: {', '.join(str(i + 1) for i in self.empty_plots())}."
        if not self.spend(cost, f"moved the {BUILDINGS[bid]['name']}"):
            return f"Moving a building costs {cost} credits. I have {self.credits()}."
        lay = self.layout()
        old = self.plot_of(bid)
        del lay[old]
        self.save_layout(lay)
        cons = self.constructions()
        cons[bid] = {"plot": p, "done": time.time() + BUILD_HOURS * 3600}
        self.db.set("construction", cons)
        return f"I paid {cost} credits to move the {BUILDINGS[bid]['name']} from plot {old + 1} to plot {p + 1}. Rebuilding takes {BUILD_HOURS} hours."

    # ================================================================ sleep and day/night
    def bedtime(self):
        return self.db.get("sleep", {"bed": 23, "wake": 7})

    @staticmethod
    def _in_window(h, start, end):
        return (h >= start or h < end) if start > end else (start <= h < end)

    def is_asleep(self):
        s = self.bedtime()
        return self._in_window(datetime.datetime.now().hour, s["bed"], s["wake"])

    @staticmethod
    def is_night():
        return LifeMixin._in_window(datetime.datetime.now().hour, 19, 6)

    @staticmethod
    def daylight():
        """0.0 at sunrise (6:00) to 1.0 at sunset (19:00); None at night."""
        now = datetime.datetime.now()
        h = now.hour + now.minute / 60
        return None if (h < 6 or h >= 19) else round((h - 6) / 13, 3)

    def act_set_bedtime(self, a, imp):
        try:
            bed, wake = int(a.get("bed_hour")) % 24, int(a.get("wake_hour")) % 24
        except (TypeError, ValueError):
            return "I thought about my sleep schedule but didn't change it."
        length = (wake - bed) % 24
        if not 8 <= length <= 10:
            return f"That would be {length} hours of sleep. I need between 8 and 10."
        self.db.set("sleep", {"bed": bed, "wake": wake})
        return f"I'll sleep from {bed}:00 to {wake}:00 from now on."

    def sleep_turn(self):
        night_key = (datetime.datetime.now() - datetime.timedelta(hours=12)).date().isoformat()
        self.set_location("home")
        if self.db.get("dreamed") == night_key:
            return {"building": "home", "action": "sleep", "thought": "", "result": "Asleep."}
        self.db.set("dreamed", night_key)
        mems = self.db.q("SELECT kind, content FROM memories WHERE ts > ? AND kind != 'dream' ORDER BY id DESC LIMIT 40",
                         (time.time() - 86400,))
        ctx = f"WHO YOU ARE:\n{self.personality()}\n\nYOUR DAY:\n" + "\n".join(f"- {m['content'][:200]}" for m in reversed(mems))
        try:
            out = self.ask(prompts.DREAM.format(name=self.name), ctx, "dream")
            dream = str(out.get("dream", "")).strip()[:1500]
            insight = str(out.get("insight", "")).strip()[:500]
        except Exception:
            dream, insight = "", ""
        if dream:
            self.mem.add("dream", dream, "home", 6)
        if insight:
            self.mem.add("reflection", insight, "home", 6)
        return {"building": "home", "action": "sleep", "thought": "zzz", "result": "Fell asleep and dreamed." if dream else "Asleep."}

    # ================================================================ live chat
    def chat_state(self):
        return self.db.get("chat")

    def chat_start(self):
        st = self.chat_state()
        if st:
            return st
        st = {"started": time.time(), "last": time.time(), "messages": []}
        self.db.set("chat", st)
        if not self.expedition():
            self.set_location("post_office")
        return st

    def chat_say(self, text):
        st = self.chat_state() or self.chat_start()
        text = text.strip()[:1500]
        st["messages"].append({"who": "creator", "text": text, "ts": time.time()})
        st["last"] = time.time()
        self.db.set("chat", st)
        history = "\n".join(f"{self.creator if m['who'] == 'creator' else self.name}: {m['text']}" for m in st["messages"][-16:])
        recent = Memory.fmt(self.mem.recent(10))
        related = Memory.fmt(self.mem.relevant(text, 5))
        where = "on an expedition, talking over the long-range radio" if self.expedition() else \
                ("half asleep" if self.is_asleep() else "at the Relay Post")
        ctx = (f"WHO YOU ARE:\n{self.personality()}\nYou are {where}.\n\nRECENT MEMORIES:\n{recent}\n\n"
               f"MEMORIES THAT MIGHT BE RELATED:\n{related}\n\nCONVERSATION SO FAR:\n{history}\n\n{self.name}:")
        out = self.ask(prompts.CHAT.format(name=self.name, creator=self.creator), ctx, "chat")
        reply = str(out.get("reply", "")).strip()[:2000] or "…"
        st = self.chat_state() or st
        st["messages"].append({"who": "resident", "text": reply, "ts": time.time()})
        st["messages"] = st["messages"][-40:]
        st["last"] = time.time()
        self.db.set("chat", st)
        return reply

    def chat_end(self):
        st = self.chat_state()
        if not st:
            return None
        self.db.set("chat", None)
        msgs = st.get("messages", [])
        if not msgs:
            return None
        transcript = "\n".join(f"{self.creator if m['who'] == 'creator' else self.name}: {m['text']}" for m in msgs)
        try:
            out = self.ask(prompts.CHAT_SUMMARY.format(name=self.name, creator=self.creator), transcript[:6000], "chat_summary")
            summary = str(out.get("summary", "")).strip()[:1200]
            imp = int(out.get("importance", 6))
        except Exception:
            summary, imp = f"I had a live chat with {self.creator} ({len(msgs)} messages).", 6
        self.mem.add("chat", summary or f"I chatted with {self.creator}.", "post_office", imp)
        self.check_milestones()
        return summary

    def chat_expire(self):
        st = self.chat_state()
        if st and time.time() - st.get("last", 0) > CHAT_IDLE_MIN * 60:
            self.chat_end()

    # ================================================================ emotes
    def emote(self):
        if self.is_asleep() and not self.chat_state():
            return "z"
        if self.chat_state():
            return "chat"
        if self.now_playing():
            return "note"
        act = (self.db.get("last_act") or {}).get("action", "")
        last_turn = self.db.get("last_turn") or 0
        recent = time.time() - last_turn < 20 * 60
        needs = self.db.get("needs", {})
        if recent and act in ("research", "read_page", "ask_question", "recall", "start_expedition"):
            return "?"
        if recent and act in ("change_look", "plant", "build", "write_letter"):
            return "heart"
        if recent and act in ("write_program", "write_note", "archive_memories", "journal"):
            return "idea"
        if any(v >= 85 for v in needs.values()):
            return "!"
        return None

    # ================================================================ space events
    def space_event(self):
        ev = self.db.get("space_event")
        if ev and ev["end"] <= time.time():
            self.end_space_event(ev)
            return None
        return ev

    def maybe_space_event(self):
        if self.space_event():
            return
        per_week = self.cfg.get("events_per_week", 4)
        turns_per_week = 7 * 16 * 60 / max(5, self.cfg["tick_minutes"])
        if random.random() < per_week / turns_per_week:
            self.start_space_event(random.choices(list(EVENT_TYPES), [e["weight"] for e in EVENT_TYPES.values()])[0])

    def start_space_event(self, kind):
        if kind not in EVENT_TYPES or self.db.get("space_event"):
            return None
        info = EVENT_TYPES[kind]
        hours = random.uniform(*info["hours"])
        ev = {"type": kind, "title": info["title"], "about": info["about"], "start": time.time(), "end": time.time() + hours * 3600}
        if kind == "trader":
            rare = [n for n, s in P.SPECIES.items() if s["tier"] in ("rare", "legendary")]
            stock = {f"seeds:{n}": int(P.TIER_PRICE[P.SPECIES[n]["tier"]] * 0.7) for n in random.sample(rare, 3)}
            deco = random.choice(list(sprites.DECOR_PRICES))
            stock[f"decor:{deco}"] = int(sprites.DECOR_PRICES[deco] * 0.7)
            pick = curios.random_find(boost=2)
            stock[f"curio:{pick}"] = {"common": 15, "uncommon": 30, "rare": 60, "legendary": 150}[curios.CATALOG[pick]["rarity"]]
            ev["stock"] = stock
            ev["about"] += " Today's goods: " + ", ".join(
                f"trader:{k.split(':')[1]} ({curios.CATALOG[k.split(':')[1]]['name'] + ', ' if k.startswith('curio:') else ''}{v} credits)"
                for k, v in stock.items())
        self.db.set("space_event", ev)
        self.mem.add("observation", f"{info['title']}! {ev['about']}", self.db.get("location", "home"), 7)
        self.add_event("space", f"{info['title']} over the colony", ev["about"][:300])
        return ev

    def end_space_event(self, ev):
        self.db.set("space_event", None)
        self.mem.add("observation", f"The {ev['title'].split(' ', 1)[-1].lower()} has passed.", self.db.get("location", "home"), 3)

    def act_stargaze(self, a, imp):
        ev = self.space_event()
        if ev and ev["type"] == "meteor_shower":
            if self._usage().get("stardust", 0) >= 3:
                return "I watched the meteors streak by. I've collected all the stardust I can carry tonight."
            self._bump("stardust")
            if random.random() < 0.3:
                return "A fragment fell nearby and I ran to it: " + self.find_curio("the meteor shower", boost=1)
            if random.random() < 0.2:
                pick = random.choice([n for n, s in P.SPECIES.items() if s["tier"] in ("rare", "legendary")])
                inv = self.inventory()
                inv["seeds"][pick] = inv["seeds"].get(pick, 0) + 1
                self.db.set("inventory", inv)
                return f"A glowing fragment landed near me. Inside was a {pick.replace('_', ' ')} seed!"
            amount = random.randint(5, 25)
            self.earn(amount, "stardust from the meteor shower")
            return f"I gathered stardust from the meteor shower, worth {amount} credits."
        if ev and ev["type"] == "eclipse":
            return "I watched the eclipse swallow the light. Everything went quiet and strange."
        return "I lay back and watched the stars wheel over the colony."

    # ================================================================ milestones
    def check_milestone(self, key, title, reward):
        if self.db.q("SELECT 1 FROM milestones WHERE key=?", (key,)):
            return
        self.db.x("INSERT INTO milestones(key, ts, title, reward) VALUES(?,?,?,?)", (key, time.time(), title, reward))
        if reward:
            self.earn(reward, f"milestone: {title}")
        self.mem.add("observation", f"Milestone reached: {title}.", self.db.get("location", "home"), 6)
        self.add_event("milestone", f"🏆 {self.name}: {title}", f"+{reward} credits" if reward else "")

    def check_milestones(self):
        for key, title, reward, sql, need in MILESTONES:
            if self.db.q(sql)[0]["c"] >= need:
                self.check_milestone(key, title, reward)
        born = self.db.get("born")
        if born:
            days = (time.time() - born) / 86400
            for d, title, reward in DAY_MILESTONES:
                if days >= d:
                    self.check_milestone(f"days_{d}", title, reward)
        for c, title, reward in CREDIT_MILESTONES:
            if self.credits() >= c:
                self.check_milestone(f"credits_{c}", title, reward)
        if not self.blueprints() and not self.constructions() and \
                all(not self.is_locked(b) for b in BUILDINGS) and self.layout():
            self.check_milestone("all_built", "Built every building in the colony", 100)
