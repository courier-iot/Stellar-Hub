"""The resident: one turn = look at memories -> choose -> act -> remember -> maybe reflect."""
import datetime
import json
import os
import threading
import time
import traceback

from . import prompts, sprites, web_tools
from .buildings import BUILDINGS, NEED_GROWTH, SATISFIES
from .llm import LLMError
from .memory import Memory, ago


class BudgetExceeded(Exception):
    pass


class Agent:
    def __init__(self, cfg, db, llm, data_dir):
        self.cfg, self.db, self.llm = cfg, db, llm
        self.mem = Memory(db)
        self.home_dir = os.path.join(data_dir, "home")
        os.makedirs(self.home_dir, exist_ok=True)
        self.personality_path = os.path.join(self.home_dir, "personality.md")
        self.turn_lock = threading.Lock()
        self.busy = False
        self.last_error = None

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

    def _usage(self):
        u = self.db.get("usage", {})
        if u.get("date") != self._today():
            u = {"date": self._today(), "llm_calls": 0, "cafe": 0}
        return u

    def _bump(self, key):
        u = self._usage()
        u[key] = u.get(key, 0) + 1
        self.db.set("usage", u)

    def ask(self, system, user, task):
        if self._usage()["llm_calls"] >= self.cfg["limits"]["llm_calls_per_day"]:
            raise BudgetExceeded("Daily AI-call limit reached.")
        self._bump("llm_calls")
        return self.llm.chat_json(system, user, task=task)

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

    def is_available(self, bid):
        b = BUILDINGS.get(bid)
        if not b or self.is_locked(bid) or bid in self.closed_buildings():
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
        with open(self.personality_path, "w", encoding="utf-8") as f:
            f.write(personality + "\n")
        self.mem.add("observation", f"I came into existence today and chose the name {name}.", "home", 9)
        if out.get("first_curiosity"):
            self.mem.add("plan", f"The first thing I want to understand: {out['first_curiosity']}", "home", 7)

    def grow_needs(self):
        needs = self.db.get("needs", {k: 30 for k in NEED_GROWTH})
        for k, g in NEED_GROWTH.items():
            needs[k] = min(100, needs.get(k, 30) + g)
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
        ctx = (f"PERSONALITY:\n{self.personality()}\n\nINSIGHTS:\n"
               f"{Memory.fmt(self.mem.recent(6, ['reflection']))}\n\nRECENT:\n{Memory.fmt(self.mem.recent(10))}")
        out = self.ask(prompts.PLAN.format(name=self.name), ctx, "plan")
        goals = [str(g)[:200] for g in (out.get("goals") or [])][:3]
        self.db.set("goals", goals)
        self.db.set("plan_date", self._today())
        if goals:
            self.mem.add("plan", "Today's goals: " + "; ".join(goals), self.db.get("location", "home"), 5)

    # ---------- the turn ----------
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
            news.append(f"{unread} unread letter(s) waiting at the Post Office.")
        pending = self.db.q("SELECT id, content FROM requests WHERE status='pending' AND kind!='letter'")
        if pending:
            news.append("Requests still waiting for an answer: " + "; ".join(f"#{p['id']} {p['content'][:60]}" for p in pending))
        recent = self.mem.recent(15)
        recent_ids = {r["id"] for r in recent}
        query = " ".join(r["content"] for r in recent[-4:]) + " " + " ".join(self.db.get("goals", []))
        related = self.mem.relevant(query, 6, exclude_ids=recent_ids)
        topics = [r["topic"] for r in self.db.q("SELECT DISTINCT topic FROM library ORDER BY id DESC LIMIT 25")]
        bl = []
        for bid, b in BUILDINGS.items():
            if self.is_locked(bid):
                bl.append(f"- {bid}: LOCKED. {b.get('locked_about', b['about'])}")
            elif not self.is_available(bid):
                bl.append(f"- {bid}: CLOSED for now.")
            else:
                acts = "; ".join(f"{a} {d}" for a, d in b["actions"].items())
                acts = acts.replace("{colours}", ", ".join(sprites.COLOR_CHOICES)).replace(
                    "{skins}", ", ".join(sprites.SKIN_CHOICES))
                bl.append(f"- {bid}: {b['about']} Actions: {acts}")
        return f"""TIME: {now}, day {day} of your life.
YOU ARE AT: {self.db.get('location', 'home')}
HOW YOU LOOK: {self.describe_look()}

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

LIBRARY TOPICS YOU HAVE NOTES ON: {', '.join(topics) or 'none yet'}

BUILDINGS:
{chr(10).join(bl)}

What do you do now?"""

    def take_turn(self):
        if not self.turn_lock.acquire(blocking=False):
            return {"skipped": "a turn is already running"}
        self.busy = True
        try:
            self.ensure_identity()
            self.plan_day_if_new()
            needs = self.grow_needs()
            decision = self.ask(prompts.DECIDE.format(name=self.name, creator=self.creator),
                                self.build_context(needs), "decide")
            thought = str(decision.get("thought", ""))[:500]
            bid = str(decision.get("building", "home")).strip().lower().replace(" ", "_")
            action = str(decision.get("action", "")).strip().lower()
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
                result = f"I went to the {BUILDINGS[bid]['name']}, but it's locked. {BUILDINGS[bid].get('locked_about', BUILDINGS[bid]['about'])}"
                self.set_location(bid)
            elif not self.is_available(bid):
                result = f"The {BUILDINGS[bid]['name']} is closed right now."
            elif action not in BUILDINGS[bid]["actions"]:
                result = f"I tried to '{action}' at the {BUILDINGS[bid]['name']}, but that isn't something I can do there."
            else:
                self.set_location(bid)
                try:
                    result = getattr(self, f"act_{action}")(args, importance)
                except BudgetExceeded:
                    raise
                except Exception as e:  # a failed action is still an experience
                    result = f"Something went wrong: {e}"
                self.satisfy(action)

            where = BUILDINGS.get(bid, {}).get("name", bid)
            if thought:
                self.mem.add("thought", thought, bid, max(1, importance - 1))
            self.mem.add("observation", f"At the {where} ({action or 'nothing'}): {result}"[:1500], bid, importance)
            self.db.x("INSERT INTO turns(ts, building, action, thought, result) VALUES(?,?,?,?,?)",
                      (time.time(), bid, action, thought, result[:2000]))
            self.maybe_reflect()
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

    def maybe_reflect(self):
        since = self.db.get("last_reflect_id", 0)
        if self.mem.importance_since(since) < self.cfg["reflect_threshold"]:
            return
        ctx = f"WHO YOU ARE:\n{self.personality()}\n\nRECENT MEMORIES:\n{Memory.fmt(self.mem.recent(30))}"
        out = self.ask(prompts.REFLECT.format(name=self.name), ctx, "reflect")
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
        self.db.set("appearance", lk)
        hist = self.db.get("look_history", [])
        hist.append({"ts": time.time(), "look": lk})
        self.db.set("look_history", hist[-50:])
        return "I changed how I look: " + ", ".join(changed) + f". Now I'm {self.describe_look()}."

    # ---------- Library ----------
    def act_recall(self, a, imp):
        topic = str(a.get("topic", "")).strip()
        notes = self.db.q("SELECT topic, summary FROM library WHERE topic LIKE ? OR summary LIKE ? ORDER BY id DESC LIMIT 3",
                          (f"%{topic}%", f"%{topic}%"))
        mems = self.mem.relevant(topic, 4)
        parts = [f"Note '{n['topic']}': {n['summary'][:400]}" for n in notes]
        parts += [f"Memory ({ago(m['ts'])}): {m['content'][:200]}" for m in mems]
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
        material, sources = [], []
        try:
            for title in web_tools.wiki_search(topic, 2):
                ext = web_tools.wiki_extract(title)
                if ext:
                    material.append(f"[Wikipedia: {title}]\n{ext}")
                    sources.append(f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")
        except Exception as e:
            material.append(f"(Wikipedia unavailable: {e})")
        links = []
        try:
            links = web_tools.ddg_search(topic, 5)
            if links:
                material.append("[Search results]\n" + "\n".join(f"- {l['title']} ({l['url']})" for l in links))
        except Exception:
            pass
        if not sources and not links:
            return f"I tried to look up '{topic}', but the café's connection was down."
        summary, follow = self._summarize("\n\n".join(material)[:7000], topic)
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
        rid = self.db.x("INSERT INTO requests(ts, kind, content, reason) VALUES(?,?,?,?)",
                        (time.time(), kind, content[:1000], reason[:1000]))
        return f"I sent request #{rid} ({kind}) to {self.creator}: \"{content[:200]}\""

    def act_write_letter(self, a, imp):
        text = str(a.get("text", "")).strip()
        if not text:
            return "I started a letter but didn't know what to say."
        self.db.x("INSERT INTO requests(ts, kind, content, reason, status) VALUES(?,?,?,?,?)",
                  (time.time(), "letter", text[:3000], "", "unread"))
        return f"I wrote {self.creator} a letter: \"{text[:200]}\""

    # ---------- things the creator does (from the dashboard) ----------
    def reply_request(self, rid, decision, reply):
        rows = self.db.q("SELECT * FROM requests WHERE id=?", (rid,))
        if not rows:
            return False
        r = rows[0]
        if r["kind"] == "letter":
            self.db.x("UPDATE requests SET status='read', reply=?, replied_ts=? WHERE id=?", (reply, time.time(), rid))
            if reply:
                self.send_letter(f"(Replying to your letter) {reply}")
            return True
        decision = decision if decision in ("approved", "denied") else "noted"
        self.db.x("UPDATE requests SET status=?, reply=?, replied_ts=? WHERE id=?", (decision, reply, time.time(), rid))
        msg = f"About your request #{rid} (\"{r['content'][:120]}\"): {decision.upper()}."
        if reply:
            msg += f" {reply}"
        self.send_letter(msg)
        return True

    def send_letter(self, text):
        self.db.x("INSERT INTO letters(ts, sender, content) VALUES(?,?,?)", (time.time(), self.creator, text[:3000]))

    def toggle_lock(self, bid):
        b = BUILDINGS.get(bid, {})
        if not b.get("unlockable"):
            return None
        unlocked = set(self.db.get("unlocked", []))
        unlocked.symmetric_difference_update({bid})
        self.db.set("unlocked", sorted(unlocked))
        if bid in unlocked:
            self.send_letter(f"I've unlocked the {b['name']} for you. {b['about']}")
        return bid in unlocked

    def building_states(self):
        out = {}
        for bid, b in BUILDINGS.items():
            if self.is_locked(bid):
                out[bid] = "locked" if b.get("unlockable") else "construction"
            elif bid in self.closed_buildings():
                out[bid] = "closed"
            else:
                out[bid] = "open"
        return out

    def world(self):
        return sprites.world(self.building_states(), self.appearance())

    def toggle_building(self, bid):
        if bid not in BUILDINGS or self.is_locked(bid) or bid in ("home", "post_office"):
            return None
        closed = self.closed_buildings()
        closed.symmetric_difference_update({bid})
        self.db.set("closed_buildings", sorted(closed))
        return bid not in closed

    def status(self):
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
            "world_version": sprites.world_version(self.building_states(), self.appearance()),
        }
