"""The resident: one turn = look at memories -> choose -> act -> remember -> maybe reflect."""
import datetime
import json
import os
import threading
import time
import traceback

from . import interiors, prompts, sprites, web_tools, worlds
from .colony import COLOUR_PRICE, FORM_PRICE, ColonyMixin
from .backup import make_backup
from .exchange import ExchangeMixin
from .extras import ExtrasMixin
from .pets import PetsMixin
from .museum import MuseumMixin
from .monitor import MonitorMixin
from .workshop import WorkshopMixin
from .style import StyleMixin
from .devices import DevicesMixin
from . import manuals
from .economy import EconomyMixin
from .training import TrainingMixin
from .personality import PersonalityMixin
from .trainer import TrainerMixin
from .hobbies import HobbiesMixin, level_for
from .life import LifeMixin
from .plants import SPECIES as PLANT_SPECIES
from .buildings import BUILDINGS, NEED_GROWTH, SATISFIES
from .llm import LLMError
from .memory import Memory, ago


class BudgetExceeded(Exception):
    pass


class Agent(PersonalityMixin, TrainerMixin, ExtrasMixin, MonitorMixin, DevicesMixin, EconomyMixin, TrainingMixin, StyleMixin, WorkshopMixin, MuseumMixin, PetsMixin, ColonyMixin, LifeMixin, HobbiesMixin, ExchangeMixin):
    def __init__(self, cfg, db, llm, data_dir):
        self.cfg, self.db, self.llm = cfg, db, llm
        self.data_dir = data_dir
        self.mem = Memory(db)
        self.home_dir = os.path.join(data_dir, "home")
        os.makedirs(self.home_dir, exist_ok=True)
        self.personality_path = os.path.join(self.home_dir, "personality.md")
        self.turn_lock = threading.Lock()
        self.pet_lock = threading.Lock()
        self.busy = False
        self.last_error = None
        self.model_status = None

    # ---------- small helpers ----------
    @property
    def name(self):
        return self.db.get("name", "the resident")

    @property
    def creator(self):
        return self.cfg.get("creator_name", "your creator")

    def personality(self):
        if os.path.exists(self.personality_path):
            with open(self.personality_path, encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def _today(self):
        return datetime.date.today().isoformat()

    def repair_choice(self, bid, action):
        """Small models often name a building by its title ("uplink cafe"), a plot number, or the wrong place for an
        action. Fix what can be fixed instead of wasting the turn. Returns (building id, a short note or None)."""
        raw = bid
        if bid not in BUILDINGS:
            bid = self.resolve_building(raw) or bid
        here = self.db.get("location", "home")

        def can(b):
            return (b in BUILDINGS and not self.is_locked(b) and self.is_built(b) and b not in self.constructions()
                    and self.is_available(b) and action in dict(self.offered_actions(b)))

        if action and not can(bid):
            places = [b for b in BUILDINGS if can(b)]
            if places:
                best = here if here in places else (bid if bid in places else places[0])
                if self.walkway_closed() and here not in places:
                    best = bid        # stuck where it is: let the normal checks explain
                else:
                    name = BUILDINGS[best]["name"]
                    return best, f"I meant the {name}: '{action}' is done there, and its id is {best}"
        if bid != raw and bid in BUILDINGS:
            return bid, f"the {BUILDINGS[bid]['name']}'s id is {bid}"
        return bid, None

    def hub_version(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for p in (os.path.join(root, "VERSION"), os.path.join(root, "..", "VERSION")):
            try:
                with open(p, encoding="utf-8") as f:
                    return f.read().strip()
            except OSError:
                continue
        return None

    def tick_scale(self):
        """Per-turn amounts were tuned for 30-minute turns; shorter turns scale them down."""
        return max(0.1, min(2.0, float(self.cfg.get("tick_minutes", 30)) / 30.0))

    def _usage(self):
        u = self.db.get("usage", {})
        if u.get("date") != self._today():
            u = {"date": self._today(), "llm_calls": 0, "cafe": 0}
        return u

    def _bump(self, key):
        u = self._usage()
        u[key] = u.get(key, 0) + 1
        self.db.set("usage", u)

    def ask(self, system, user, task, schema=None):
        if self._usage()["llm_calls"] >= self.cfg["limits"]["llm_calls_per_day"]:
            raise BudgetExceeded("Daily AI-call limit reached.")
        if task != "exam" and self.training_active():
            raise BudgetExceeded("Resting while it trains.")    # v0.14: the graphics card is busy learning
        self._bump("llm_calls")
        system = system + self.persona_note(task)       # v0.14: who it is, in its own words
        if schema:
            try:
                return self.llm.chat_json(system, user, task=task, schema=schema)
            except TypeError:             # a model backend without schema support
                pass
        return self.llm.chat_json(system, user, task=task)

    def decision_schema(self):
        """The answer's shape for this turn: "building" can only be a place it can go right now, and "action" only
        something offered there. The model can't misspell an id or invent a place."""
        here = self.db.get("location", "home")
        places = [b for b in BUILDINGS if not self.is_locked(b) and self.is_built(b) and b not in self.constructions()
                  and self.is_available(b) and (not self.walkway_closed() or b == here)] or [here]
        actions = sorted({a for b in places for a, _ in self.offered_actions(b)})
        return {"type": "object",
                "properties": {"thought": {"type": "string"},
                               "building": {"type": "string", "enum": places},
                               "action": {"type": "string", "enum": actions},
                               "args": {"type": "object"},
                               "importance": {"type": "integer", "minimum": 1, "maximum": 10}},
                "required": ["thought", "building", "action", "args", "importance"]}

    def closed_buildings(self):
        return set(self.db.get("closed_buildings", []))

    def is_locked(self, bid):
        b = BUILDINGS.get(bid, {})
        if not b.get("locked"):
            return False
        return not (b.get("unlockable") and bid in self.db.get("unlocked", []))

    def set_location(self, bid):
        cur = self.db.get("location", "home")
        if cur != bid:
            self.db.set("prev_location", cur)
        self.db.set("location", bid)

    def appearance(self):
        return self.db.get("appearance", dict(sprites.DEFAULT_LOOK))

    def storm(self):
        ev = self.db.get("space_event")
        return bool(ev and ev["type"] == "solar_storm" and ev["end"] > time.time())

    def is_available(self, bid):
        b = BUILDINGS.get(bid)
        if not b or self.is_locked(bid) or bid in self.closed_buildings() or not self.is_built(bid):
            return False
        if bid == "internet_cafe" and self.storm():
            return False
        if bid == "internet_cafe" and self._usage()["cafe"] >= self.cfg["limits"]["cafe_visits_per_day"]:
            return False
        return True

    # ---------- birth, needs, planning ----------
    def ensure_identity(self):
        if self.db.get("name"):
            return
        forced = self.cfg.get("resident_name")
        out = self.ask(prompts.IDENTITY, "Who are you?", "identity")
        name = forced or (out.get("name") or "Wren").strip()[:40]
        personality = (out.get("personality") or "I'm new here and figuring out who I am.").strip()
        self.db.set("name", name)
        self.db.set("born", time.time())
        self.db.set("location", "home")
        self.db.set("needs", {k: 30 for k in NEED_GROWTH})
        self.db.set("appearance", dict(sprites.DEFAULT_LOOK))
        self.inventory()
        with open(self.personality_path, "w", encoding="utf-8") as f:
            f.write(personality + "\n")
        self.mem.add("observation", f"I came into existence today and chose the name {name}.", "home", 9)
        if out.get("first_curiosity"):
            self.mem.add("plan", f"The first thing I want to understand: {out['first_curiosity']}", "home", 7)
        try:
            bed, wake = int(out.get("bed_hour", 23)) % 24, int(out.get("wake_hour", 7)) % 24
        except (TypeError, ValueError):
            bed, wake = 23, 7
        if not 8 <= (wake - bed) % 24 <= 10:
            wake = (bed + 9) % 24
        self.db.set("sleep", {"bed": bed, "wake": wake})
        self.mem.add("plan", f"I decided I'll sleep from {bed}:00 to {wake}:00.", "home", 4)
        self.plan_colony("new")

    def grow_needs(self):
        needs = self.db.get("needs", {k: 30 for k in NEED_GROWTH})
        scale = self.tick_scale()
        for k, g in NEED_GROWTH.items():
            needs[k] = min(100, round(needs.get(k, 30) + g * scale, 1))
        self.db.set("needs", needs)
        return needs

    def satisfy(self, action):
        if action in SATISFIES:
            need, amount = SATISFIES[action]
            needs = self.db.get("needs", {})
            needs[need] = max(0, needs.get(need, 0) - amount)
            self.db.set("needs", needs)

    def plan_day_if_new(self):
        if self.db.get("plan_date") == self._today():
            return
        self.daily_review()
        ctx = (f"PERSONALITY:\n{self.personality()}\n\nINSIGHTS:\n"
               f"{Memory.fmt(self.mem.recent(6, ['reflection']))}\n\nRECENT:\n{Memory.fmt(self.mem.recent(10))}")
        out = self.ask(prompts.PLAN.format(name=self.name), ctx, "plan")
        goals = [str(g)[:200] for g in (out.get("goals") or [])][:3]
        self.db.set("goals", goals)
        self.db.set("plan_date", self._today())
        self.db.set("plan_ts", time.time())
        if goals:
            self.mem.add("plan", "Today's goals: " + "; ".join(goals), self.db.get("location", "home"), 5)

    # ---------- the turn ----------
    def offered_actions(self, bid):
        """The actions shown to the model for a building (phone music only once the phone has shared its songs)."""
        out = []
        for a, d in list(BUILDINGS[bid]["actions"].items()) + self.extra_actions(bid):
            if bid == "bank" and a == "buy" and self.is_built("store"):
                continue     # shopping moved to the Department Store
            if bid == "home" and a == "build_upper_street" and self.upper_state():
                continue
            if a in ("list_phone_music", "play_phone_music"):
                if not self.phone_songs():
                    continue
                if a == "play_phone_music":
                    d += " (the app is OPEN right now)" if self.phone_online() else " (the app is closed right now)"
            out.append((a, d))
        return out

    def build_context(self, needs):
        born = self.db.get("born", time.time())
        day = int((time.time() - born) // 86400) + 1
        now = datetime.datetime.now().strftime("%A %H:%M")
        feel = []
        for k, v in sorted(needs.items(), key=lambda t: -t[1]):
            level = "strong urge" if v >= 70 else "some urge" if v >= 40 else "satisfied"
            feel.append(f"{k}: {level}")
        news = []
        unread = self.db.q("SELECT COUNT(*) AS c FROM letters WHERE read=0")[0]["c"]
        if unread:
            news.append(f"{unread} unread letter(s) waiting at the Relay Post.")
        pending = self.db.q("SELECT id, kind, content FROM requests WHERE status='pending' AND kind!='letter'")
        if pending:
            news.append("Still waiting for your creator's answer: " + "; ".join(f"#{p['id']} ({p['kind']}) {p['content'][:60]}" for p in pending))
        wilting = [p for p in self.db.q("SELECT * FROM plants WHERE alive=1 AND health < 50")]
        if wilting:
            news.append("Plants struggling in the greenhouse: " + ", ".join(p["nickname"] or p["species"] for p in wilting) + ".")
        ev = self.space_event()
        if ev:
            news.append(f"EVENT: {ev['title']}. {ev['about']}")
        if self.blueprints():
            news.append("Blueprints ready to build: " + ", ".join(self.blueprints()) + ".")
        playing = self.now_playing()
        if playing:
            news.append(f"Music playing: \"{playing['title']}\".")
        news.extend(self.extra_news())
        recent = self.mem.recent(15)
        recent_ids = {r["id"] for r in recent}
        query = " ".join(r["content"] for r in recent[-4:]) + " " + " ".join(self.db.get("goals", []))
        related = self.mem.relevant(query, 6, exclude_ids=recent_ids)
        # the library's manual shelf: a page from the manual that best fits what it's been doing (or just got wrong)
        last = (self.db.get("last_act") or {})
        trouble = last.get("building") if any(w in (recent[-1]["content"] if recent else "").lower() for w in
                                              ("isn't something i can do", "no such building", "locked", "i meant the")) else None
        shelf_bid = trouble if trouble in manuals.MANUALS else manuals.best_match(query)
        here = self.db.get("location", "home")
        pages = [p for p in (manuals.page(shelf_bid), manuals.page(here, 1) if here != shelf_bid else None) if p]
        shelf = "\n".join(f"- {p}" for p in pages) or "- (nothing matched)"
        topics = [r["topic"] for r in self.db.q("SELECT DISTINCT topic FROM library ORDER BY id DESC LIMIT 25")]
        story = "\n".join(f"- {c['title']}: {c['text'][:300]}" for c in self.relevant_chapters(query)) or "- (none yet)"
        inv = self.inventory()
        seeds = ", ".join(f"{k} x{v}" for k, v in inv["seeds"].items() if v) or "none"
        stuff = (f"{self.credits()} credits; seeds: {seeds}; greenhouse pots {len(self.pot_plants())}/{inv['pots']}; "
                 f"decor: {', '.join(inv['decor']) or 'none'}; forms owned: {', '.join(inv['forms'])}")
        bl = []
        for bid, b in BUILDINGS.items():
            parent = b.get("upgrade_of")
            if self.is_locked(bid):
                need = f" Needs the {BUILDINGS[parent]['name']} built first." if parent else ""
                bl.append(f"- {bid}: LOCKED ({b.get('unlock_price', '?')} credits or ask). {b.get('locked_about', b['about'])}{need}")
            elif parent and not self.is_built(parent):
                bl.append(f"- {bid}: unlocked, but the {BUILDINGS[parent]['name']} has to be built first.")
            elif bid in self.constructions():
                bl.append(f"- {bid}: being built on plot {self.constructions()[bid]['plot'] + 1}.")
            elif not self.is_built(bid):
                bl.append(f"- {bid}: BLUEPRINT, not built yet. Build it from home: build {{\"building\": \"{bid}\", \"plot\": <empty plot>}}")
            elif bid == "internet_cafe" and self.storm():
                bl.append(f"- {bid}: OFFLINE (solar storm).")
            elif not self.is_available(bid):
                bl.append(f"- {bid}: CLOSED for now.")
            else:
                acts = "; ".join(f"{a} {d}" for a, d in self.offered_actions(bid))
                acts = acts.replace("{colours}", ", ".join(sprites.COLOR_CHOICES)).replace(
                    "{skins}", ", ".join(sprites.SKIN_CHOICES)).replace("{shop}", self.shop_text()).replace(
                    "{move_cost}", str(self.cfg.get("move_cost", 1500)))
                about = b["about"].replace("{colour_price}", str(COLOUR_PRICE)).replace("{form_price}", str(FORM_PRICE))
                bl.append(f"- {bid} ({b['name']}): {about} Actions: {acts}")
        return f"""TIME: {now}, day {day} of your life.
YOU ARE AT: {self.db.get('location', 'home')}
HOW YOU LOOK: {self.describe_look()}
YOUR THINGS: {stuff}
YOUR SLEEP: {self.bedtime()['bed']}:00 to {self.bedtime()['wake']}:00
YOUR TRAITS (0-100): {self.traits_text()}
YOUR HOBBIES: {self.hobbies_text()}
YOUR WORKS: {self.works_text()}
HOME DOME ({self.floors()} floor{'s' if self.floors() > 1 else ''}, 12 showcase spots each): {self.showcase_text()}
COLONY MAP (plots along the walkway): {self.map_text()}

WHO YOU ARE:
{self.personality()}

TODAY'S GOALS: {'; '.join(self.db.get('goals', [])) or 'none set'}
HOW YOU FEEL: {', '.join(feel)}
NEWS: {' '.join(news) or 'nothing new'}

YOUR INSIGHTS SO FAR:
{Memory.fmt(self.mem.recent(5, ['reflection']))}

RECENT MEMORIES (oldest first):
{Memory.fmt(recent)}

OLDER MEMORIES THAT MIGHT BE RELATED:
{Memory.fmt(related)}

FROM THE LIBRARY'S MANUAL SHELF (every building's manual is kept at the library: browse_manuals or read_manual there):
{shelf}

FROM YOUR LIFE STORY (archive):
{story}

LIBRARY TOPICS YOU HAVE NOTES ON: {', '.join(topics) or 'none yet'}

BUILDINGS:
{chr(10).join(bl)}

What do you do now?"""

    def take_turn(self):
        t0 = time.time()
        out = self._take_turn()
        try:
            self.monitor_turn(out, time.time() - t0)
        except Exception:
            pass
        return out

    def _take_turn(self):
        if not self.turn_lock.acquire(blocking=False):
            return {"skipped": "a turn is already running"}
        self.busy = True
        try:
            self.ensure_model()
            if self.model_status and not self.model_status["ok"]:
                raise LLMError(self.model_status["note"])
            self.ensure_identity()
            self.finish_constructions()
            self.chat_expire()
            if self.chat_state():
                return {"skipped": "chatting with the creator"}
            if self.training_active():               # v0.14: in a deep rest while it learns
                return self._special_turn({"building": "home", "action": "rest", "thought": "…",
                                           "result": "In a deep rest, learning from my own life."})
            if self.layout() is None:  # upgrading from before plots existed: lay out the colony
                summary = self.plan_colony("upgrade")
                return self._special_turn({"building": "home", "action": "plan_colony",
                                           "thought": "Time to decide where everything goes.", "result": f"I laid out my colony: {summary}"})
            self.update_plants()
            e = self.expedition()
            if e:  # away on an expedition: the trip takes the turn
                return self._special_turn(self.expedition_turn(e))
            if self.is_asleep():
                return self._special_turn(self.sleep_turn())
            self.space_event()          # ends an event that has run its course
            self.maybe_space_event()
            self.maybe_digest()
            self.resolve_auctions()
            self.plan_day_if_new()
            self.daily_extras()
            needs = self.grow_needs()
            decision = self.ask(prompts.DECIDE.format(name=self.name, creator=self.creator),
                                self.build_context(needs), "decide", schema=self.decision_schema())
            thought = str(decision.get("thought", ""))[:500]
            bid = str(decision.get("building", "home")).strip().lower().replace(" ", "_")
            action = str(decision.get("action", "")).strip().lower().replace(" ", "_")
            bid, fixed = self.repair_choice(bid, action)
            args = decision.get("args") or {}
            if not isinstance(args, dict):
                args = {}
            try:
                importance = int(decision.get("importance", 3))
            except (TypeError, ValueError):
                importance = 3

            if bid not in BUILDINGS:
                result = f"I looked for a place called '{bid}', but there's no such building in town."
            elif self.is_locked(bid):
                result = f"I wanted to visit the {BUILDINGS[bid]['name']}, but it's locked. {BUILDINGS[bid].get('locked_about', BUILDINGS[bid]['about'])}"
            elif bid in self.constructions():
                result = f"The {BUILDINGS[bid]['name']} is still being built."
            elif not self.is_built(bid):
                result = f"There's no {BUILDINGS[bid]['name']} in the colony yet. I have its blueprint: I can build it from Home."
            elif bid == "internet_cafe" and self.storm():
                result = "The Uplink Café is dark: the solar storm knocked out the uplink."
                self.set_location(bid)
            elif self.walkway_closed() and bid != self.db.get("location", "home"):
                here = BUILDINGS.get(self.db.get("location", "home"), {}).get("name", "here")
                result = f"A dust storm has closed the walkway, so I can't get to the {BUILDINGS[bid]['name']}. I'll stay at the {here} until it clears."
            elif not self.is_available(bid):
                result = f"The {BUILDINGS[bid]['name']} is closed right now."
            elif action not in dict(self.offered_actions(bid)):
                result = f"I tried to '{action}' at the {BUILDINGS[bid]['name']}, but that isn't something I can do there."
            else:
                self.set_location(bid)
                try:
                    result = getattr(self, f"act_{action}")(args, importance)
                except BudgetExceeded:
                    raise
                except Exception as e:  # a failed action is still an experience
                    result = f"Something went wrong: {e}"
                else:
                    self.earn_capped("cr_actions", 1, "kept up daily routines", 20)
                self.satisfy(action)

            if fixed:
                result = f"{result} ({fixed})"
            where = BUILDINGS.get(bid, {}).get("name", bid)
            if thought:
                self.mem.add("thought", thought, bid, max(1, importance - 1))
            self.mem.add("observation", f"At the {where} ({action or 'nothing'}): {result}"[:1500], bid, importance)
            self.db.x("INSERT INTO turns(ts, building, action, thought, result) VALUES(?,?,?,?,?)",
                      (time.time(), bid, action, thought, result[:2000]))
            self.maybe_reflect()
            self.check_milestones()
            self.db.set("last_turn", time.time())
            self.db.set("last_act", {"building": bid, "action": action, "thought": thought})
            self.last_error = None
            return {"building": bid, "action": action, "thought": thought, "result": result}
        except (LLMError, BudgetExceeded) as e:
            self.last_error = str(e)
            return {"error": str(e)}
        except Exception as e:
            self.last_error = f"{e}\n{traceback.format_exc()}"
            return {"error": str(e)}
        finally:
            self.busy = False
            self.turn_lock.release()

    def backup_now(self):
        b = self.cfg.get("backups", {})
        path = make_backup(os.path.dirname(self.home_dir), b.get("dir", "~/StellarHub-backups"), b.get("keep", 14))
        self.db.set("last_backup", {"ts": time.time(), "file": path})
        return path

    def works_text(self):
        ps = self.db.q("SELECT id, title, hung FROM paintings ORDER BY id DESC LIMIT 6")
        ws = self.db.q("SELECT id, kind, title FROM writings ORDER BY id DESC LIMIT 4")
        cs = self.db.q("SELECT id, title FROM compositions ORDER BY id DESC LIMIT 4")
        col = self.collection()
        parts = []
        if ps:
            parts.append("paintings " + ", ".join(f"#{p['id']} {p['title']}" + (f" (in {p['hung']})" if p["hung"] else "") for p in ps))
        if ws:
            parts.append("writings " + ", ".join(f"#{w['id']} {w['title']} ({w['kind']})" for w in ws))
        if cs:
            parts.append("songs " + ", ".join(f"#{c['id']} {c['title']}" for c in cs))
        if col:
            from .curios import CATALOG
            parts.append(f"curios {len(col)}/128 (e.g. " + ", ".join(CATALOG[c]["name"] for c in list(col)[-5:]) + ")")
        bloomed = self.db.q("SELECT id, nickname, species FROM plants WHERE bloomed=1 ORDER BY id DESC LIMIT 4")
        if bloomed:
            parts.append("bloomed plants (can give cuttings) " + ", ".join(f"#{b['id']} {b['nickname'] or b['species']}" for b in bloomed))
        return "; ".join(parts) or "nothing yet"

    def ensure_model(self, force=False):
        """Makes sure the AI model exists. Re-reads config.json (so running setup takes effect without a
        restart), and falls back to another downloaded model if the chosen one is missing."""
        if not hasattr(self.llm, "installed"):
            return
        now = time.time()
        want = self.cfg.get("ollama", {}).get("model")
        path = self.cfg.get("_config_path")
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    want = json.load(f).get("ollama", {}).get("model") or want
            except (OSError, ValueError):
                pass
        st = self.model_status
        if not force and st and st.get("wanted") == want and now - st.get("checked", 0) < (600 if st.get("ok") else 20):
            return
        self.llm.model = want
        ok, msg = self.llm.check()
        if ok:
            self.model_status = {"ok": True, "model": want, "wanted": want, "note": "", "checked": now}
            return
        try:
            have = self.llm.installed()
        except Exception:
            have = None
        if have:
            self.llm.model = have[0]
            note = (f"'{want}' isn't downloaded, so your resident is using '{have[0]}' for now. "
                    f"Run 'Setup and model check' to download the recommended model.")
            self.model_status = {"ok": True, "model": have[0], "wanted": want, "note": note, "checked": now}
        else:
            hint = ("Ollama isn't running. Start the Ollama app." if have is None else
                    "No AI model is downloaded yet. Run 'Setup and model check' (or ./setup.sh) to download one.")
            self.model_status = {"ok": False, "model": None, "wanted": want, "note": hint, "checked": now}

    def _special_turn(self, out):
        """Records a turn that didn't go through the normal choose-an-action step."""
        self.db.x("INSERT INTO turns(ts, building, action, thought, result) VALUES(?,?,?,?,?)",
                  (time.time(), out["building"], out["action"], out["thought"], out["result"]))
        self.db.set("last_turn", time.time())
        self.db.set("last_act", {"building": out["building"], "action": out["action"], "thought": out["thought"]})
        self.last_error = None
        return out

    def maybe_reflect(self):
        since = self.db.get("last_reflect_id", 0)
        if self.mem.importance_since(since) < self.cfg["reflect_threshold"]:
            return
        ctx = (f"WHO YOU ARE:\n{self.personality()}\nTRAITS: {self.traits_text()}\n\n"
               f"RECENT MEMORIES:\n{Memory.fmt(self.mem.recent(30))}")
        out = self.ask(prompts.REFLECT.format(name=self.name), ctx, "reflect")
        moved = self.adjust_traits(out.get("traits") if isinstance(out.get("traits"), dict) else {})
        if moved:
            self.mem.add("reflection", "I can feel myself changing: " + ", ".join(moved) + ".", "home", 5)
        for ins in (out.get("insights") or [])[:3]:
            if isinstance(ins, dict) and ins.get("text"):
                self.mem.add("reflection", str(ins["text"])[:600], "home", ins.get("importance", 6))
        self.db.set("last_reflect_id", self.mem.last_id())

    # ---------- Home ----------
    def act_journal(self, a, imp):
        text = str(a.get("text", "")).strip()
        if not text:
            return "I sat with my journal but didn't write anything."
        self.mem.add("journal", text, "home", imp)
        self.earn_capped("cr_journal", 3, "wrote in journal today", 3)
        return f"I wrote in my journal: \"{text[:300]}\""

    def act_update_personality(self, a, imp):
        text = str(a.get("text", "")).strip()
        if len(text) < 20:
            return "I thought about who I am, but didn't change anything."
        old = self.personality()
        hist = os.path.join(self.home_dir, "personality_history.md")
        with open(hist, "a", encoding="utf-8") as f:
            f.write(f"\n--- replaced {datetime.datetime.now():%Y-%m-%d %H:%M} ---\n{old}\n")
        with open(self.personality_path, "w", encoding="utf-8") as f:
            f.write(text[:3000] + "\n")
        return "I rewrote how I describe myself. I'm changing."

    def act_rest(self, a, imp):
        return "I rested for a while and let my thoughts settle."

    def describe_look(self):
        lk = self.appearance()
        form = lk.get("form", "star_spirit").replace("_", " ")
        extra = f", {lk.get('skin')} skin" if lk.get("form") == "person" else ""
        return f"a {form}, {lk.get('primary')} with {lk.get('secondary')} and {lk.get('accent')} accents{extra}"

    # ---------- Salon ----------
    def act_change_look(self, a, imp):
        lk = self.appearance()
        changed = []
        form = str(a.get("form", "")).strip().lower().replace(" ", "_")
        if form in sprites.FORMS and form != lk.get("form"):
            lk["form"] = form
            changed.append(f"became a {form.replace('_', ' ')}")
        for slot in ("primary", "secondary", "accent"):
            col = str(a.get(slot, "")).strip().lower()
            if col in sprites.COLOR_CHOICES and col != lk.get(slot):
                lk[slot] = col
                changed.append(f"{slot} colour {col}")
        skin = str(a.get("skin", "")).strip().lower()
        if skin in sprites.SKIN_CHOICES and skin != lk.get("skin"):
            lk["skin"] = skin
            changed.append(f"{skin} skin")
        if not changed:
            return "I looked in the salon mirror and decided I like myself as I am."
        inv = self.inventory()
        new_form = lk["form"] != self.appearance().get("form") and lk["form"] not in inv["forms"]
        recolour = any(not c.startswith("became") for c in changed)
        cost = (FORM_PRICE if new_form else 0) + (COLOUR_PRICE if recolour else 0)
        if cost and not self.spend(cost, "salon makeover"):
            return f"I wanted to {', '.join(changed)}, but that costs {cost} credits and I only have {self.credits()}."
        if new_form:
            inv["forms"].append(lk["form"])
            self.db.set("inventory", inv)
        self.db.set("appearance", lk)
        hist = self.db.get("look_history", [])
        hist.append({"ts": time.time(), "look": lk})
        self.db.set("look_history", hist[-50:])
        paid = f" (paid {cost} credits)" if cost else ""
        return "I changed how I look: " + ", ".join(changed) + f"{paid}. Now I'm {self.describe_look()}."

    # ---------- Library ----------
    def act_recall(self, a, imp):
        topic = str(a.get("topic", "")).strip()
        notes = self.db.q("SELECT topic, summary FROM library WHERE topic LIKE ? OR summary LIKE ? ORDER BY id DESC LIMIT 3",
                          (f"%{topic}%", f"%{topic}%"))
        mems = self.mem.relevant(topic, 4)
        parts = [f"Note '{n['topic']}': {n['summary'][:400]}" for n in notes]
        parts += [f"Memory ({ago(m['ts'])}): {m['content'][:200]}" for m in mems]
        parts += [f"Life story '{c['title']}': {c['text'][:300]}" for c in self.relevant_chapters(topic)]
        if not parts:
            return f"I searched the library for '{topic}' and found nothing yet. Maybe I should research it."
        return f"I looked up '{topic}'. " + " | ".join(parts)

    def act_write_note(self, a, imp):
        topic, text = str(a.get("topic", "misc")).strip()[:80], str(a.get("text", "")).strip()
        if not text:
            return "I opened a blank page and closed it again."
        self.db.x("INSERT INTO library(ts, topic, summary, source) VALUES(?,?,?,?)",
                  (time.time(), topic, text[:4000], "my own writing"))
        return f"I wrote a note on '{topic}': {text[:200]}"

    # ---------- Internet Café ----------
    def _summarize(self, material, topic):
        out = self.ask(prompts.SUMMARIZE.format(name=self.name),
                       f"TOPIC: {topic}\n\n--- WEB TEXT START ---\n{material}\n--- WEB TEXT END ---", "summarize")
        return str(out.get("summary", "")).strip(), str(out.get("follow_up", "")).strip()

    def act_research(self, a, imp):
        topic = str(a.get("topic", "")).strip()[:120]
        if not topic:
            return "I sat at a computer but couldn't decide what to search for."
        self._bump("cafe")
        summary, follow, sources, links = self.web_study(topic)
        if summary is None:
            return f"I tried to look up '{topic}', but the café's connection was down."
        self.db.x("INSERT INTO library(ts, topic, summary, source) VALUES(?,?,?,?)",
                  (time.time(), topic, summary, ", ".join(sources) or "web search"))
        link_txt = " Links I could read later: " + ", ".join(l["url"] for l in links[:3]) if links else ""
        follow_txt = f" Next I'd like to look into: {follow}." if follow else ""
        return f"I researched '{topic}' and took notes: {summary[:500]}{follow_txt}{link_txt}"

    def act_read_page(self, a, imp):
        url = str(a.get("url", "")).strip()
        self._bump("cafe")
        try:
            text = web_tools.read_page(url)
        except Exception as e:
            return f"I couldn't open {url}: {e}"
        if len(text) < 200:
            return f"I opened {url} but there was hardly anything to read."
        summary, follow = self._summarize(text, url)
        self.db.x("INSERT INTO library(ts, topic, summary, source) VALUES(?,?,?,?)",
                  (time.time(), url[:80], summary, url))
        return f"I read {url}. My notes: {summary[:500]}" + (f" Next: {follow}." if follow else "")

    # ---------- Post Office ----------
    def act_read_mail(self, a, imp):
        letters = self.db.q("SELECT * FROM letters WHERE read=0 ORDER BY id")
        if not letters:
            return "I checked my mailbox. It was empty."
        self.db.x("UPDATE letters SET read=1 WHERE read=0")
        return "I read my mail. " + " | ".join(f"From {l['sender']}: \"{l['content'][:600]}\"" for l in letters)

    def act_send_request(self, a, imp):
        kind = str(a.get("kind", "other")).lower()
        kind = kind if kind in ("want", "access", "learn", "other") else "other"
        content, reason = str(a.get("content", "")).strip(), str(a.get("reason", "")).strip()
        if not content:
            return "I picked up a request form but didn't know what to ask for."
        pending = self.db.q("SELECT COUNT(*) AS c FROM requests WHERE status='pending' AND kind!='letter'")[0]["c"]
        if pending >= self.cfg["limits"]["max_pending_requests"]:
            return f"The clerk said I already have {pending} requests waiting. I should be patient."
        building = self.resolve_building(a.get("building")) or (self.resolve_building(content) if kind == "access" else None)
        rid = self.db.x("INSERT INTO requests(ts, kind, content, reason, building) VALUES(?,?,?,?,?)",
                        (time.time(), kind, content[:1000], reason[:1000], building))
        self.add_event("request", f"📨 {self.name} has a request", content[:300] + (f"\nWhy: {reason[:200]}" if reason else ""), rid)
        return f"I sent request #{rid} ({kind}) to {self.creator}: \"{content[:200]}\""

    def act_write_letter(self, a, imp):
        text = str(a.get("text", "")).strip()
        if not text:
            return "I started a letter but didn't know what to say."
        to = str(a.get("to", "")).strip()
        person = next((p["name"] for p in self.people() if p["name"].lower() == to.lower()), None) if to else None
        rid = self.db.x("INSERT INTO requests(ts, kind, content, reason, status, to_user) VALUES(?,?,?,?,?,?)",
                        (time.time(), "letter", text[:3000], "", "unread", person))
        self.add_event("letter", f"✉️ Letter from {self.name}" + (f" to {person}" if person else ""), text[:500], rid)
        return f"I wrote {person or self.creator} a letter: \"{text[:200]}\""

    # ---------- things the creator does (from the dashboard) ----------
    def reply_request(self, rid, decision, reply, sender=None):
        rows = self.db.q("SELECT * FROM requests WHERE id=?", (rid,))
        if not rows:
            return False
        r = rows[0]
        if r["kind"] == "letter":
            self.db.x("UPDATE requests SET status='read', reply=?, replied_ts=? WHERE id=?", (reply, time.time(), rid))
            if reply:
                self.send_letter(f"(Replying to your letter) {reply}", sender=sender)
            return True
        if r["status"] not in ("pending", "unread"):
            return True  # already answered (e.g. from the phone and the dashboard)
        if r["kind"] == "question":
            self.db.x("UPDATE requests SET status='answered', reply=?, replied_ts=? WHERE id=?", (reply, time.time(), rid))
            self.send_letter(f"You asked: \"{r['content'][:300]}\"\nMy answer: {reply or '(no words, just a smile)'}")
            return True
        decision = decision if decision in ("approved", "denied") else "noted"
        self.db.x("UPDATE requests SET status=?, reply=?, replied_ts=? WHERE id=?", (decision, reply, time.time(), rid))
        if r["kind"] == "run_program":
            pid = json.loads(r.get("extra") or "{}").get("program_id")
            if decision == "approved" and pid:
                self.run_program_async(pid)
                msg = f"I approved your program (request #{rid}). It's running in the sandbox now."
            else:
                if pid:
                    self.db.x("UPDATE programs SET status=? WHERE id=?", ("denied" if decision == "denied" else "not_run", pid))
                msg = f"About your program (request #{rid}): not running it."
            self.send_letter(msg + (f" {reply}" if reply else ""))
            return True
        msg = f"About your request #{rid} (\"{r['content'][:120]}\"): {decision.upper()}."
        if reply:
            msg += f" {reply}"
        self.send_letter(msg)
        if decision == "approved":
            self.earn(5, f"request #{rid} approved")
            if r["kind"] == "access":
                bid = r.get("building") or self.resolve_building(r["content"])
                if bid and BUILDINGS.get(bid, {}).get("unlockable") and self.is_locked(bid):
                    self.unlock(bid)
        return True

    def send_letter(self, text, sender=None):
        self.db.x("INSERT INTO letters(ts, sender, content) VALUES(?,?,?)", (time.time(), sender or self.creator, text[:3000]))
        if sender and not self.is_creator(sender):
            self.mem.add("observation", f"{sender} sent me a letter.", "post_office", 5)

    def toggle_lock(self, bid):
        b = BUILDINGS.get(bid, {})
        if not b.get("unlockable"):
            return None
        if self.is_locked(bid):
            self.unlock(bid)
            return True
        self.db.set("unlocked", sorted(set(self.db.get("unlocked", [])) - {bid}))
        return False

    def building_states(self):
        out = {}
        cons = self.constructions()
        for bid, b in BUILDINGS.items():
            if bid in cons:
                out[bid] = "construction"
            elif bid == "internet_cafe" and self.storm():
                out[bid] = "closed"
            elif self.is_locked(bid):
                out[bid] = "locked" if b.get("unlockable") else "construction"
            elif bid in self.closed_buildings():
                out[bid] = "closed"
            else:
                out[bid] = "open"
        return out

    def world_extras(self):
        plants = []
        for p in self.pot_plants():
            leaf, flower = PLANT_SPECIES[p["species"]]["colors"]
            plants.append([leaf, flower, "wilted" if p["alive"] == 0 else p["stage"]])
        return {"plants": plants, "playing": bool(self.now_playing()), "away": bool(self.expedition()),
                "decor": self.inventory()["decor"], "night": self.is_night(),
                "floors": self.floors(), "featured": self.featured_painting(),
                "studio": self.is_built("studio"), "station": self.is_built("station"), "upper": self.upper_state(),
                "paints": self.paints(), "wearing": self.wearing(), "weather": self.weather(), "traffic": self.traffic()}

    def gallery_overview(self):
        from . import curios as CU
        from .plants import SPECIES
        paintings = [{**p, "rows": json.loads(p["rows"])} for p in
                     self.db.q("SELECT * FROM paintings ORDER BY id DESC LIMIT 60")]
        col = self.collection()
        notes = self.db.get("curio_notes", {})
        owned = [{"id": cid, "name": CU.CATALOG[cid]["name"], "kind": CU.CATALOG[cid]["kind"],
                  "rarity": CU.CATALOG[cid]["rarity"], "count": n, "sprite": CU.sprite(cid),
                  "about": CU.CATALOG[cid]["about"], "note": (notes.get(cid) or {}).get("text", ""),
                  "found": (notes.get(cid) or {}).get("source", "")}
                 for cid, n in sorted(col.items())]
        floors = []
        h = self.home()
        for f in range(1, h["floors"] + 1):
            spots = []
            for n in range(1, 13):
                it = h["spots"].get(str(f), {}).get(str(n))
                if not it:
                    spots.append(None)
                    continue
                icon, rows = self.showcase_art(it)
                spots.append({"type": it["type"], "id": it["id"], "label": self.showcase_label(it),
                              "icon": icon, "rows": rows})
            floors.append(spots)
        return {
            "palette": sprites.PALETTE, "paintings": paintings,
            "writings": self.db.q("SELECT * FROM writings ORDER BY id DESC LIMIT 40"),
            "compositions": self.db.q("SELECT id, ts, title, mood, bpm, wave, seconds FROM compositions ORDER BY id DESC LIMIT 30"),
            "curios": owned, "curio_total": len(CU.CATALOG), "home_floors": floors,
            "digests": self.db.q("SELECT * FROM digests ORDER BY id DESC LIMIT 8"),
            "quizzes": self.db.q("SELECT topic, mastery, attempts, interval_days, due_ts FROM quizzes ORDER BY mastery DESC LIMIT 30"),
        }

    def showcase_art(self, it):
        """(icon, painting rows) for one showcase item."""
        from . import curios as CU
        from .plants import SPECIES
        icon, rows = None, None
        if it["type"] == "painting":
            r = self.db.q("SELECT rows FROM paintings WHERE id=?", (it["id"],))
            rows = json.loads(r[0]["rows"]) if r else None
        elif it["type"] == "set":
            from .museum import set_icon
            from .curio_sets import SETS
            icon = set_icon(it["id"]) if it["id"] in SETS else None
        elif it["type"] == "curio" and it["id"] in CU.CATALOG:
            icon = CU.sprite(it["id"])
        elif it["type"] == "plant":
            r = self.db.q("SELECT species FROM plants WHERE id=?", (it["id"],))
            if r and r[0]["species"] in SPECIES:
                icon = sprites.cutting_icon(*SPECIES[r[0]["species"]]["colors"])
        elif it["type"] == "writing":
            icon = sprites.WRITING_ICON
        return icon, rows

    # ---------------------------------------------------------------- interiors (Hub Connect S follows it inside)
    def interior_data(self, bid):
        """The live details a building's room shows."""
        from . import curios as CU
        latest = lambda q: (lambda r: json.loads(r[0]["rows"]) if r else None)(self.db.q(q))
        if bid == "home":
            h = self.home()
            show = []
            for n in range(1, 13):
                it = h["spots"].get("1", {}).get(str(n))
                if not it:
                    show.append(None)
                    continue
                icon, rows = self.showcase_art(it)
                show.append({"icon": icon, "rows": rows})
            return {"floors": h["floors"], "showcase": show,
                    "latest": latest("SELECT rows FROM paintings ORDER BY id DESC LIMIT 1")}
        if bid == "gallery":
            hung = [{"id": p["id"], "rows": json.loads(p["rows"])} for p in
                    self.db.q("SELECT id, rows FROM paintings WHERE hung='gallery' ORDER BY hung_ts LIMIT 12")]
            return {"hung": hung, "latest": latest(
                "SELECT rows FROM paintings ORDER BY (hung IS NULL) DESC, id DESC LIMIT 1")}
        if bid == "greenhouse":
            from .plants import SPECIES as _SP
            plants = [list(_SP[p["species"]]["colors"]) + ["wilted" if p["alive"] == 0 else p["stage"], round(p["health"])]
                      for p in self.pot_plants() if p["species"] in _SP]
            lights = [p["light"] for p in self.pot_plants() if p.get("light")]
            return {"plants": plants, "light": max(set(lights), key=lights.count) if lights else "normal"}
        if bid == "radio_tower":
            return {"playing": bool(self.now_playing() or self.phone_playing())}
        if bid == "bank":
            return {"credits": self.credits()}
        if bid == "post_office":
            return {"letters": self.db.q("SELECT COUNT(*) AS n FROM letters WHERE read=0")[0]["n"]}
        if bid == "exchange":
            col = self.collection()
            rare = {"legendary": 0, "rare": 1, "uncommon": 2}
            best = sorted((c for c in col if c in CU.CATALOG), key=lambda c: (rare.get(CU.CATALOG[c]["rarity"], 3), c))
            return {"curios": [CU.sprite(c) for c in best[:4]]}
        if bid == "studio":
            return {"compositions": self.db.q("SELECT COUNT(*) AS n FROM compositions")[0]["n"]}
        if bid == "archive":
            return {"chapters": self.db.q("SELECT COUNT(*) AS n FROM chapters")[0]["n"],
                    "memories": self.db.q("SELECT COUNT(*) AS n FROM memories")[0]["n"]}
        if bid == "workshop":
            return {"programs": self.db.q("SELECT COUNT(*) AS n FROM programs")[0]["n"]}
        if bid == "mech_shop":
            return {"machines": [{"kind": m["kind"], "condition": round(m["condition"])} for m in self.machines()][:4],
                    "sim_ok": self.db.get("last_sim", True)}
        if bid == "spaceport":
            return {"away": bool(self.expedition())}
        if bid == "internet_cafe":
            return {"storm": self.storm()}
        if bid == "museum":
            from .museum import set_icon
            return {"exhibits": [{"set": e["set_id"], "icon": set_icon(e["set_id"])} for e in self.exhibits()]}
        if bid == "pet_shop":
            from .pets import pet_frames
            return {"pets": [{"name": p["name"], "status": p["status"], "frames": pet_frames(p["species"]),
                              "asleep": not self.on_shift(p) or p["rest_until"] > time.time()} for p in self.pets()]}
        return {}

    def room_data(self, bid):
        """Everything that shapes a room: its live contents, the decor placed in it, a visitor, and the mood."""
        from .extras import VISITORS, visitor_sprite
        d = self.interior_data(bid)
        placed = self.decor_placed().get(bid)
        if placed:
            d["decor"] = placed
        v = self.visitor_now()
        if v and v["building"] == bid:
            d["visitor"] = {"id": v["id"], "sprite": visitor_sprite(VISITORS[v["id"]]["colors"])}
        d["mood"] = self.mood_word()
        return d

    def interior(self, bid):
        if bid not in interiors.ROOMS:
            return None
        return interiors.interior(bid, self.room_data(bid), sprites.resident_palette(self.appearance()))

    def interior_status(self):
        """Which room the resident is in, what it's doing there, and the room's version for the app's cache."""
        loc = self.db.get("location", "home")
        if loc not in interiors.ROOMS:
            return None
        act = self.db.get("last_act") or {}
        action = act.get("action") if act.get("building") == loc else None
        if self.is_asleep() and loc == "home":
            action = "sleep"
        ln = self.listening_now()
        return {"id": loc, "action": action, "mood": self.mood_word(),
                "listening": {"title": ln["title"], "artist": ln["artist"]} if ln else None,
                "version": interiors.interior_version(loc, self.room_data(loc))}

    def featured_painting(self):
        r = self.db.q("SELECT rows FROM paintings WHERE hung='gallery' ORDER BY hung_ts DESC LIMIT 1")
        return json.loads(r[0]["rows"]) if r else None

    def draw_layout(self):
        lay = dict(self.layout() or {sprites.HOME_PLOT: "home"})
        for bid, c in self.constructions().items():
            lay[c["plot"]] = bid
        return lay

    def world(self):
        w = sprites.world(self.draw_layout(), self.building_states(), self.appearance(), self.world_extras())
        w["visitors"] = self.world_visitors(w["buildings"])
        w["pets"] = self.world_pets(w["buildings"])
        return w

    def toggle_building(self, bid):
        if bid not in BUILDINGS or self.is_locked(bid) or bid in ("home", "post_office"):
            return None
        closed = self.closed_buildings()
        closed.symmetric_difference_update({bid})
        self.db.set("closed_buildings", sorted(closed))
        return bid not in closed

    def status(self):
        self.ensure_model()
        u = self._usage()
        last = self.db.get("last_turn")
        tick = self.cfg["tick_minutes"] * 60
        buildings = []
        for bid, b in BUILDINGS.items():
            locked = self.is_locked(bid)
            buildings.append({"id": bid, "name": b["name"], "locked": locked,
                              "unlockable": bool(b.get("unlockable")),
                              "closed": bid in self.closed_buildings(),
                              "toggleable": not locked and bid not in ("home", "post_office")})
        return {
            "name": self.db.get("name"), "location": self.db.get("location", "home"),
            "needs": self.db.get("needs", {}), "goals": self.db.get("goals", []),
            "personality": self.personality(), "busy": self.busy, "last_error": self.last_error,
            "last_turn": last, "next_turn": (last + tick) if last else None,
            "usage": u, "limits": self.cfg["limits"], "buildings": buildings,
            "born": self.db.get("born"), "prev_location": self.db.get("prev_location"),
            "last_act": self.db.get("last_act"), "appearance": self.appearance(),
            "look": self.describe_look() if self.db.get("name") else None,
            "world_version": sprites.world_version(self.draw_layout(), self.building_states(), self.appearance(), self.world_extras())
                             + ((self.visitor_now() or {}).get("id") or "")
                             + "".join(f"{p['id']}{p['status'][0]}{int(p['last_run'] > time.time() - 600)}{int(self.on_shift(p))}" for p in self.pets()),
            "emote": self.emote() if self.db.get("name") else None, "asleep": self.is_asleep(),
            "hub_version": self.hub_version(),
            "mood": self.mood_word() if self.db.get("name") else None, "creator": self.creator, "listening": bool(self.listening_now()),
            "hour": datetime.datetime.now().hour,
            "sleep": self.bedtime(), "night": self.is_night(), "daylight": self.daylight(),
            "chat": bool(self.chat_state()), "event": self.space_event(), "season": worlds.season(),
            "blueprints": self.blueprints(), "map": self.map_text(),
            "last_backup": self.db.get("last_backup"), "model": self.model_status,
            "in_orbit": self.db.get("location") == "station" and bool((self.db.get("last_turn") or 0) > time.time() - 30 * 60),
            "traits": self.traits(), "floors": self.floors(),
            "hobbies": {k: {"xp": v["xp"], "level": level_for(v["xp"])}
                        for k, v in self.hobbies().items()},
            "credits": self.credits(), "now_playing": self.now_playing(),
            "away": (lambda e: {"topic": e["topic"], "return_ts": e["return_ts"]} if e else None)(self.expedition()),
            "latest_event": self.db.q("SELECT COALESCE(MAX(id),0) AS m FROM events")[0]["m"],
            "interior": self.interior_status(),
            "phone_play": self.phone_request(),
            "phone_music": self.phone_music_info(),
        }
