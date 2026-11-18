"""v0.14.1: life projects. Its hopes turn into things it actually does.

When it has a hope and no project on the go, it plans one: 4-7 stages, each a real piece of work (a chapter, a
design, a study session, a painting in a series...). It works on a stage at most once a day (work_on_project, at
the place that fits), so a project takes a week or more. Finishing pays off: credits, a milestone, the finished work
kept in its writings, and a memory that often becomes a core one. A project left alone for three weeks is set aside.
"""
import json
import time

from .buildings import BUILDINGS

KINDS = {"writing": "park", "study": "library", "machine": "mech_shop", "program": "workshop", "art": "gallery",
         "music": "studio", "garden": "greenhouse", "other": "home"}
PLAN = """You are {name}. One of your hopes is: "{hope}".
Turn it into a real project you can do in this colony over the next couple of weeks: 4-7 stages, each one
session of real work that produces something (a chapter, a design, notes from studying, a sketch...).
Kinds: writing, study, machine, program, art, music, garden, other.
Reply ONLY with JSON: {{"title": "...", "kind": "<kind>", "stages": ["stage 1: what you'll make", "..."], "payoff": "what you'll have at the end"}}"""
WORK = """You are {name}, working on your project "{title}" ({kind}). This session: stage {n} of {total}: {stage}.
Do the work for real and write what you made (the chapter, the notes, the design, a description of the painting...),
in your own voice, 80-250 words. Then say how it went.
Reply ONLY with JSON: {{"work": "...", "feeling": "one short sentence"}}"""
STALE_DAYS = 21


class ProjectsMixin:
    def project(self):
        r = self.db.q("SELECT * FROM projects WHERE status='active' ORDER BY id DESC LIMIT 1")
        if not r:
            return None
        p = dict(r[0])
        p["stages"] = json.loads(p["stages"] or "[]")
        return p

    def projects(self, limit=12):
        out = []
        for r in self.db.q("SELECT * FROM projects ORDER BY id DESC LIMIT ?", (limit,)):
            p = dict(r)
            p["stages"] = json.loads(p["stages"] or "[]")
            out.append(p)
        return out

    def maybe_start_project(self):
        """After a personality review: plan a project from a hope, if none is on the go."""
        p = self.project()
        if p:
            if time.time() - (p["last_work"] or p["ts"]) > STALE_DAYS * 86400:
                self.db.x("UPDATE projects SET status='set_aside' WHERE id=?", (p["id"],))
                self.mem.add("reflection", f"I set aside my project \"{p['title']}\" for now. Maybe I'll come back to it.", "home", 5)
                self.persona_log(f"Set aside a project: {p['title']}")
            return None
        hopes = self.persona()["hopes"]
        tried = {r["hope"] for r in self.db.q("SELECT hope FROM projects")}
        hope = next((h["hope"] for h in hopes if h["hope"] not in tried), None)
        if not hope:
            return None
        out = self.ask(PLAN.format(name=self.name, hope=hope), f"WHO YOU ARE:\n{self.personality()[:1200]}", "project_plan_life")
        stages = [str(x).strip()[:200] for x in (out.get("stages") or []) if str(x).strip()][:7]
        if len(stages) < 2:
            return None
        kind = out.get("kind") if out.get("kind") in KINDS else "other"
        place = KINDS[kind]
        if place == "studio":
            place = "radio_tower"
        title = str(out.get("title") or hope)[:120]
        pid = self.db.x("INSERT INTO projects(ts, title, kind, hope, place, stages, current, status, last_work, payoff) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (time.time(), title, kind, hope, place, json.dumps([{"title": s, "work": None, "ts": None} for s in stages]),
                         0, "active", None, str(out.get("payoff", ""))[:300]))
        self.mem.add("plan", f"I started a project: \"{title}\" ({len(stages)} stages), because I hope to {hope}.", "home", 7)
        self.persona_log(f"Started a project: {title}")
        self.add_event("project", f"🛠️ {self.name} started a project", f"{title}: {len(stages)} stages")
        return pid

    def _project_place(self, p):
        return p["place"] if self.is_built(p["place"]) else "home"

    def project_actions(self, bid):
        p = self.project()
        if not p or bid != self._project_place(p):
            return []
        if p["last_work"] and time.time() - p["last_work"] < 20 * 3600:
            return []
        st = p["stages"][p["current"]]["title"]
        return [("work_on_project", f"{{}}  work on your project \"{p['title']}\": stage {p['current'] + 1} of {len(p['stages'])}, {st}")]

    def project_news(self):
        p = self.project()
        if not p:
            return []
        ready = not p["last_work"] or time.time() - p["last_work"] >= 20 * 3600
        return [f"YOUR PROJECT: \"{p['title']}\", stage {p['current'] + 1} of {len(p['stages'])}"
                + (f" (ready to work on at the {BUILDINGS[self._project_place(p)]['name']})." if ready else " (resting until tomorrow).")]

    def act_work_on_project(self, a, imp):
        p = self.project()
        if not p:
            return "I don't have a project on the go."
        if p["last_work"] and time.time() - p["last_work"] < 20 * 3600:
            return "I already worked on my project today. Good work needs a rest in between."
        n, total = p["current"], len(p["stages"])
        out = self.ask(WORK.format(name=self.name, title=p["title"], kind=p["kind"], n=n + 1, total=total,
                                   stage=p["stages"][n]["title"]),
                       "EARLIER STAGES:\n" + "\n".join(f"- {s['title']}: {(s['work'] or '')[:300]}" for s in p["stages"][:n]),
                       "project_work")
        work = str(out.get("work", "")).strip()[:3000]
        if not work:
            return "I sat down to work on my project, but nothing came today."
        p["stages"][n].update({"work": work, "ts": time.time()})
        done = n + 1 >= total
        self.db.x("UPDATE projects SET stages=?, current=?, last_work=?, status=?, finished=? WHERE id=?",
                  (json.dumps(p["stages"]), n + 1 if not done else n, time.time(), "done" if done else "active",
                   time.time() if done else None, p["id"]))
        self.gain_xp({"art": "painting", "music": "composing", "garden": "gardening", "program": "coding",
                      "study": "astronomy" if "star" in p["title"].lower() else "writing"}.get(p["kind"], "writing"), 3, "project work")
        feeling = str(out.get("feeling", "")).strip()[:200]
        if not done:
            self.mem.add("observation", f"I worked on \"{p['title']}\" (stage {n + 1}/{total}). {feeling}", self.db.get("location", "home"), 6)
            return f"I worked on \"{p['title']}\": stage {n + 1} of {total} is done. {feeling}"
        full = "\n\n".join(f"{i + 1}. {s['title']}\n{s['work']}" for i, s in enumerate(p["stages"]))
        self.db.x("INSERT INTO writings(ts, kind, title, text) VALUES(?,?,?,?)", (time.time(), "project", p["title"], full[:20000]))
        self.earn(100, f"finished the project {p['title'][:40]}")
        self.mem.add("observation", f"I finished my project \"{p['title']}\"! I hoped to {p['hope']}, and I did it. {feeling}", "home", 9)
        self.persona_log(f"Finished a project: {p['title']}")
        self.add_event("project", f"🏁 {self.name} finished a project", p["title"])
        self.check_milestone("project_first", "Finished a first life project", 50)
        return f"I finished \"{p['title']}\"! All {total} stages are done, and I earned 100 credits. {feeling}"
