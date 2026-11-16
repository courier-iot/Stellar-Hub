"""v0.13: weekly goals, the Mechanical Workshop, real-world project plans, and the skill notebook.

- Fab Hangar: a coding challenge every week, checked by automatic tests in the sandbox (no approval needed for tests;
  any other program still waits for the creator). Difficulty climbs after passes and eases after misses.
- Mechanical Workshop: parts from the Department Store, a weekly machine to build, a simulator that checks the design,
  and working machines that help the colony. Machines wear down slowly and need maintenance.
- Real-world plans: about once a week the resident designs a low-voltage project for its creator to build for real.
- Skill notebook: everything that worked (passing code, working machines, finished plans) is kept and shown to the
  resident as examples next time, which is how a small model gets better at things over time."""
import datetime
import json
import os
import random
import re
import time

# ------------------------------------------------------------------ coding challenges
# id: (level, title, task, tests). Tests are plain asserts run after the resident's code.
CHALLENGES = {
    "count_stars": (1, "Count the stars", "Write count_stars(sky) that returns how many '*' characters are in the string sky.",
                    "assert count_stars('*.*..*') == 3\nassert count_stars('') == 0\nassert count_stars('....') == 0"),
    "credits_after": (1, "Balance the vault", "Write credits_after(start, changes) that returns start plus the sum of the numbers in the list changes.",
                      "assert credits_after(10, [5, -3]) == 12\nassert credits_after(0, []) == 0\nassert credits_after(-5, [10]) == 5"),
    "is_due": (1, "Watering reminder", "Write is_due(hours_since, every_hours) that returns True when hours_since is at least every_hours.",
               "assert is_due(24, 24) is True\nassert is_due(3, 24) is False\nassert is_due(30, 12) is True"),
    "palindrome_signal": (2, "Echo signal", "Write is_palindrome(signal) that returns True if the letters of signal read the same both ways, ignoring case and anything that isn't a letter.",
                          "assert is_palindrome('Level') is True\nassert is_palindrome('A man, a plan, a canal: Panama') is True\nassert is_palindrome('stars') is False"),
    "rarity_counts": (2, "Count by rarity", "Write rarity_counts(items) where items is a list of (name, rarity) pairs; return a dict mapping each rarity to how many items have it.",
                      "assert rarity_counts([('a','common'),('b','rare'),('c','common')]) == {'common': 2, 'rare': 1}\nassert rarity_counts([]) == {}"),
    "sort_curios": (2, "Sort the shelf", "Write sort_curios(items), items a list of (name, rarity) pairs. Return them sorted legendary, rare, uncommon, common, and by name within a rarity.",
                    "assert sort_curios([('b','common'),('a','rare'),('c','legendary'),('a','common')]) == [('c','legendary'),('a','rare'),('a','common'),('b','common')]"),
    "run_length": (3, "Compress a signal", "Write encode(s) that run-length encodes a string: 'aaabcc' becomes 'a3b1c2'. An empty string stays empty.",
                   "assert encode('aaabcc') == 'a3b1c2'\nassert encode('') == ''\nassert encode('z') == 'z1'"),
    "complete_sets": (3, "Find complete sets", "Write complete_sets(owned, sets): owned maps piece name to count, sets maps set name to a list of piece names. Return a sorted list of set names where you own at least one of every piece.",
                      "assert complete_sets({'a':1,'b':2,'c':0}, {'X':['a','b'],'Y':['a','c']}) == ['X']\nassert complete_sets({}, {'X':['a']}) == []"),
    "busiest_hour": (3, "Busiest hour", "Write busiest_hour(hours), hours a non-empty list of hour numbers 0-23. Return the hour that appears most often; on a tie, the smallest hour.",
                     "assert busiest_hour([3,5,5,3,9]) == 3\nassert busiest_hour([22]) == 22\nassert busiest_hour([1,2,2]) == 2"),
    "trade_ups": (4, "Trade-up cascade", "Write trade_ups(spares), spares a dict with keys common, uncommon, rare, legendary. Every 5 of one rarity become 1 of the next (cascading, legendary stays). Return the final dict.",
                  "assert trade_ups({'common':12,'uncommon':0,'rare':0,'legendary':0}) == {'common':2,'uncommon':2,'rare':0,'legendary':0}\nassert trade_ups({'common':25,'uncommon':0,'rare':4,'legendary':0}) == {'common':0,'uncommon':0,'rare':0,'legendary':1}"),
    "flip_rows": (4, "Mirror a painting", "Write mirror(rows) that flips a list of equal-length strings left to right, and rotate(rows) that turns it 90 degrees clockwise.",
                  "assert mirror(['ab','cd']) == ['ba','dc']\nassert rotate(['ab','cd']) == ['ca','db']\nassert rotate(['abc']) == ['a','b','c']"),
    "merge_intervals": (4, "Merge sleep shifts", "Write merge(intervals), a list of [start, end] pairs; return them merged where they overlap or touch, sorted by start.",
                        "assert merge([[1,3],[2,6],[8,10]]) == [[1,6],[8,10]]\nassert merge([[5,7],[1,5]]) == [[1,7]]\nassert merge([]) == []"),
    "grid_path": (5, "Route through the colony", "Write shortest(grid), grid a list of strings with '.' open, '#' wall, one 'S' and one 'E'. Return the fewest steps (up/down/left/right) from S to E, or -1 if impossible.",
                  "assert shortest(['S.E']) == 2\nassert shortest(['S#E']) == -1\nassert shortest(['S..', '.#.', '..E']) == 4"),
    "roman_stardate": (5, "Roman stardate", "Write roman(n) that turns an integer 1-3999 into Roman numerals.",
                       "assert roman(4) == 'IV'\nassert roman(1994) == 'MCMXCIV'\nassert roman(3999) == 'MMMCMXCIX'"),
    "knight_moves": (6, "Knight's journey", "Write knight(a, b) returning the fewest chess knight moves from square a to square b, like 'a1' to 'h8'.",
                     "assert knight('a1','a1') == 0\nassert knight('a1','b3') == 1\nassert knight('a1','h8') == 6"),
    "spiral": (6, "Spiral scan", "Write spiral(m), m a list of equal-length lists; return all values in clockwise spiral order starting top-left.",
               "assert spiral([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]\nassert spiral([[1]]) == [1]\nassert spiral([]) == []"),
}

CODE_PROMPT = """You are {name}, a young AI in a space colony, writing Python for this week's coding challenge.
Write ONLY the requested function(s): plain Python 3, standard library only, no input(), no printing, no tests.
Reply as JSON: {{"code": "<the python code>", "notes": "<one short sentence>"}}"""

# ------------------------------------------------------------------ parts and machines
PARTS = {   # name: (price, power: + supplies / - draws)
    "frame": (10, 0), "wheel": (8, 0), "gear": (8, 0), "circuit": (18, -1), "sensor": (15, -1), "motor": (20, -4),
    "pump": (16, -3), "arm": (22, -5), "lens": (14, 0), "speaker": (12, -1), "battery": (12, 10), "solar_panel": (25, 6),
}
# machine: (level, name, what it does, required parts {part: count})
MACHINES = {
    "watering_bot": (1, "Watering Bot", "waters greenhouse plants that are due, every day",
                     {"frame": 1, "wheel": 2, "pump": 1, "sensor": 1, "circuit": 1}),
    "seed_sorter": (1, "Seed Sorter", "finds a stray seed now and then",
                    {"frame": 1, "gear": 2, "motor": 1, "circuit": 1}),
    "telescope_tracker": (2, "Telescope Tracker", "makes stargazing and sky surveys more likely to spot fragments",
                          {"frame": 1, "lens": 2, "motor": 1, "gear": 2, "circuit": 1}),
    "music_box_bot": (2, "Music Box Bot", "plays its songs to passers-by for a few credits a day",
                      {"frame": 1, "speaker": 2, "circuit": 1, "gear": 1}),
    "cleaning_drone": (3, "Cleaning Drone", "keeps the colony tidy (+2 credits a day) and cheers up the pets",
                       {"frame": 1, "motor": 2, "sensor": 1, "circuit": 1}),
    "solar_array": (3, "Solar Array", "sells spare power: +5 credits a day",
                    {"frame": 2, "solar_panel": 3, "circuit": 1}),
    "delivery_drone": (4, "Delivery Drone", "carries shopping home and gets a 5% Department Store discount",
                       {"frame": 1, "motor": 2, "arm": 1, "sensor": 1, "circuit": 1}),
    "pet_feeder": (4, "Pet Feeder", "feeds hungry pets automatically (food still costs credits)",
                   {"frame": 1, "gear": 2, "motor": 1, "sensor": 1, "circuit": 1}),
    "repair_bot": (5, "Repair Bot", "halves the wear on every other machine",
                   {"frame": 1, "arm": 2, "wheel": 2, "sensor": 1, "circuit": 2}),
    "comet_catcher": (6, "Comet Catcher", "catches a set piece during each comet pass",
                      {"frame": 2, "arm": 2, "lens": 1, "motor": 1, "sensor": 2, "circuit": 2}),
}
MACHINE_PROMPT = """You are {name}, a young AI in a space colony, designing a machine at the Mechanical Workshop.
Choose which parts (and how many) to use. Rules the simulator checks: every required part must be there; the power
sources (battery +10, solar_panel +6) must cover what the parts draw (motor -4, pump -3, arm -5, circuit -1, sensor -1,
speaker -1); each frame holds up to 6 other parts. You may only use parts you own.
Reply as JSON: {{"parts": {{"<part>": <count>, ...}}, "notes": "<one short sentence on your design>"}}"""

# ------------------------------------------------------------------ real-world plans
PLAN_KINDS = {
    "esp32": "an ESP32 or Arduino electronics build (with code)",
    "3d_print": "a 3D-printable object (with an OpenSCAD file)",
    "crafts": "a hand-tools or crafts build (wood, cardboard, simple materials)",
    "smart_home": "a small smart-home gadget or sensor (with code)",
}
PLAN_PROMPT = """You are {name}, a young AI who loves building, designing a REAL project for your creator, {creator}, to make
at home. Kind: {kind}. Keep it small, achievable in a weekend, and SAFE: low voltage only (USB or batteries, 5V/3.3V),
never mains electricity, no heating elements or lithium cell modifications. Draw on what you know about your creator.
Reply as JSON: {{"title": "...", "summary": "<2-3 sentences>", "difficulty": "easy|medium",
"parts": [{{"item": "...", "qty": 1, "note": "..."}}], "tools": ["..."], "steps": ["..."],
"code": "<Arduino/ESP32 C++ or MicroPython, or empty>", "scad": "<OpenSCAD source, or empty>", "tips": "..."}}"""
SAFETY = ("Check this before you build: it was designed by your resident's local AI model and may contain mistakes. "
          "Low-voltage only (USB or batteries). Double-check wiring and polarity against each part's datasheet, and "
          "never connect anything to mains power.")


def week_key(ts=None):
    d = datetime.date.fromtimestamp(ts or time.time())
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def words(s):
    return {w for w in re.findall(r"[a-z]{3,}", str(s).lower())}


class WorkshopMixin:
    # ------------------------------------------------------------ the skill notebook
    def add_skill(self, kind, title, content, tags=""):
        self.db.x("INSERT INTO skills(ts, kind, title, tags, content) VALUES(?,?,?,?,?)",
                  (time.time(), kind, title[:120], tags[:300], content[:6000]))

    def find_skills(self, kind, query, n=2):
        q = words(query)
        rows = self.db.q("SELECT * FROM skills WHERE kind=? ORDER BY id DESC LIMIT 200", (kind,))
        scored = sorted(rows, key=lambda r: -len(q & words(r["title"] + " " + r["tags"] + " " + r["content"][:400])))
        return [dict(r) for r in scored[:n]]

    def skill_examples(self, kind, query, n=2):
        ex = self.find_skills(kind, query, n)
        return "\n\n".join(f"EXAMPLE THAT WORKED BEFORE ({e['title']}):\n{e['content'][:1500]}" for e in ex) or "(none yet)"

    # ------------------------------------------------------------ weekly goals
    def goals_open(self):
        self.ensure_weekly_goals()
        return [dict(g) for g in self.db.q("SELECT * FROM goals WHERE status IN ('open','review') ORDER BY id")]

    def ensure_weekly_goals(self):
        wk = week_key()
        if self.db.get("goals_week") == wk:
            return
        last = self.db.get("goals_week")
        self.db.set("goals_week", wk)
        # last week's automatic goals that weren't met lower the difficulty a little
        for g in self.db.q("SELECT * FROM goals WHERE status='open' AND source='auto'"):
            self.db.x("UPDATE goals SET status='missed' WHERE id=?", (g["id"],))
            if g["kind"] == "code" and self.db.get("sandbox_down_week") == last:
                continue          # it couldn't test anything that week: not its fault, the level stays
            key = "code_level" if g["kind"] == "code" else "mech_level"
            self.db.set(key, max(1, int(self.db.get(key, 1)) - 1))
        if not last and not self.is_built("workshop"):
            pass
        if self.is_built("workshop"):
            self._new_code_goal(wk)
        if self.is_built("mech_shop"):
            self._new_machine_goal(wk)

    def _new_code_goal(self, wk):
        lvl = int(self.db.get("code_level", 1))
        done = {g["ref"] for g in self.db.q("SELECT ref FROM goals WHERE kind='code' AND status='passed'")}
        pool = [k for k, v in CHALLENGES.items() if v[0] == lvl and k not in done] or \
               [k for k, v in CHALLENGES.items() if v[0] <= lvl and k not in done] or list(CHALLENGES)
        cid = random.choice(pool)
        lv, title, task, _ = CHALLENGES[cid]
        self.db.x("INSERT INTO goals(ts, week, kind, ref, title, text, tests, source, status, attempts) VALUES(?,?,?,?,?,?,?,?,?,0)",
                  (time.time(), wk, "code", cid, title, task, CHALLENGES[cid][3], "auto", "open"))
        self.add_event("goal", f"🎯 This week's coding challenge: {title}", task)

    def _new_machine_goal(self, wk):
        lvl = int(self.db.get("mech_level", 1))
        built = {m["kind"] for m in self.machines() if m["condition"] > 0}
        pool = [k for k, v in MACHINES.items() if v[0] == lvl and k not in built] or \
               [k for k, v in MACHINES.items() if v[0] <= lvl + 1 and k not in built] or list(MACHINES)
        mid = random.choice(pool)
        lv, name, does, req = MACHINES[mid]
        self.db.x("INSERT INTO goals(ts, week, kind, ref, title, text, tests, source, status, attempts) VALUES(?,?,?,?,?,?,?,?,?,0)",
                  (time.time(), wk, "machine", mid, f"Build a {name}", f"It {does}. Needs at least: "
                   + ", ".join(f"{n} {p}" for p, n in req.items()) + ", plus power.", None, "auto", "open"))
        self.add_event("goal", f"🎯 This week's workshop goal: build a {name}", f"It {does}.")

    def add_creator_goal(self, kind, title, text, tests=None, by=None):
        kind = kind if kind in ("code", "machine", "plan") else "code"
        by = None if self.is_creator(by) else by
        gid = self.db.x("INSERT INTO goals(ts, week, kind, ref, title, text, tests, source, status, attempts, by_user) VALUES(?,?,?,?,?,?,?,?,?,0,?)",
                        (time.time(), week_key(), kind, None, str(title)[:120], str(text)[:2000],
                         (str(tests)[:4000] or None) if tests else None, "creator", "open", by))
        self.mem.add("observation", f"{by or 'My creator'} gave me a {kind} goal: {title}. {text[:300]}", "workshop", 7)
        self.add_event("goal", f"🎯 New goal from {by or self.creator}: {title}", text[:300])
        return gid

    def review_goal(self, gid, passed, note=""):
        g = self.db.q("SELECT * FROM goals WHERE id=?", (gid,))
        if not g or g[0]["status"] != "review":
            return False
        g = dict(g[0])
        self.db.x("UPDATE goals SET status=?, result=? WHERE id=?", ("passed" if passed else "open",
                                                                    (g["result"] or "") + f"\nYour review: {'passed' if passed else 'not yet'} {note}", gid))
        if passed:
            self._goal_passed(g, g.get("last_code") or "")
        else:
            self.mem.add("observation", f"My creator reviewed my work on '{g['title']}': not quite yet. {note}", "workshop", 6)
        return True

    def _goal_passed(self, g, content):
        reward = 25 * (CHALLENGES.get(g["ref"], (2,))[0] if g["kind"] == "code" else MACHINES.get(g["ref"], (2,))[0]) + 20
        self.earn(reward, f"completed the goal '{g['title']}'")
        key = "code_level" if g["kind"] == "code" else "mech_level"
        if g["source"] == "auto":
            self.db.set(key, min(6, int(self.db.get(key, 1)) + 1))
        self.gain_xp("coding" if g["kind"] == "code" else "building", 12, f"goal: {g['title']}")
        self.add_skill(g["kind"], g["title"], content, g.get("text") or "")
        self.add_event("goal", f"✅ {self.name} completed: {g['title']}", f"+{reward} credits")
        self.mem.add("observation", f"I completed '{g['title']}'! I'll remember how I did it.", "workshop", 8)
        self.check_milestone(f"first_{g['kind']}_goal", f"Completed its first {g['kind']} goal", 20)

    # ------------------------------------------------------------ the Fab Hangar challenge
    def act_view_challenge(self, a, imp):
        gs = [g for g in self.goals_open() if g["kind"] == "code"]
        if not gs:
            return "No coding goals right now. A new challenge arrives every week."
        return " | ".join(f"Goal #{g['id']} ({('from ' + (g.get('by_user') or 'my creator')) if g['source'] == 'creator' else 'weekly'}): {g['title']}. "
                          f"{g['text']} Attempts so far: {g['attempts']}." for g in gs) + " (attempt_challenge to try.)"

    def act_attempt_challenge(self, a, imp):
        gs = [g for g in self.goals_open() if g["kind"] == "code" and g["status"] == "open"]
        try:
            gid = int(a.get("goal_id") or 0)
        except (TypeError, ValueError):
            gid = 0
        g = next((x for x in gs if x["id"] == gid), gs[0] if gs else None)
        if not g:
            return "There's no open coding goal to attempt."
        if g["tests"] and self.sandbox_problem():
            self.db.set("sandbox_down_week", week_key())
            return f"I wanted to try '{g['title']}', but the sandbox can't run tests right now. {self.sandbox_problem()}"
        if self._usage().get("code_tries", 0) >= 4:
            return "I've tried enough code for today. Fresh eyes tomorrow."
        self._bump("code_tries")
        ctx = (f"CHALLENGE: {g['title']}\n{g['text']}\n\n" + (f"TESTS IT MUST PASS:\n{g['tests']}\n\n" if g["tests"] else "")
               + (f"LAST TRY FAILED WITH:\n{g['result'][-800:]}\n\n" if g["result"] else "")
               + self.skill_examples("code", g["title"] + " " + g["text"]))
        out = self.ask(CODE_PROMPT.format(name=self.name), ctx, "code")
        code = str(out.get("code", "")).strip()
        if len(code) < 5:
            return f"I thought about '{g['title']}' but didn't manage to write anything."
        self.db.x("UPDATE goals SET attempts=attempts+1, last_code=? WHERE id=?", (code[:20000], g["id"]))
        if not g["tests"]:          # a creator's goal without tests: they review it
            self.db.x("UPDATE goals SET status='review', result=? WHERE id=?", ("Waiting for your review.", g["id"]))
            self.add_event("goal", f"👀 {self.name} wants you to review '{g['title']}'", code[:400], g["id"])
            return f"I wrote my answer to '{g['title']}' and sent it to {g.get('by_user') or 'my creator'} to review."
        ok, output = self.run_tests(code, g["tests"])
        self.db.x("UPDATE goals SET result=? WHERE id=?", (output[-2000:], g["id"]))
        if ok is None:
            return f"I wrote code for '{g['title']}', but the sandbox isn't available to test it. ({output[:200]})"
        if ok:
            self.db.x("UPDATE goals SET status='passed' WHERE id=?", (g["id"],))
            self._goal_passed(g, code)
            return f"My code for '{g['title']}' passed every test!"
        self.gain_xp("coding", 2, "learned from a failed test")
        return f"My code for '{g['title']}' didn't pass yet: {output.strip().splitlines()[-1][:200] if output.strip() else 'no output'}"

    def run_tests(self, code, tests):
        """Runs code plus its tests in the sandbox. Tests need no approval: no network, own folder, time-limited."""
        problem = self.sandbox_problem()
        if problem:
            return None, problem
        prog = code + "\n\n# ---- tests ----\n" + tests + "\nprint('ALL_TESTS_PASSED')\n"
        output, rc = self.sandbox_run(prog, "tests")
        return (rc == 0 and "ALL_TESTS_PASSED" in output), output

    # ------------------------------------------------------------ the Mechanical Workshop
    def parts_catalog(self):
        return PARTS

    def parts(self):
        return self.db.get("parts") or {}

    def buy_part(self, name, count=1):
        if name not in PARTS:
            return None
        price = int(PARTS[name][0] * (0.95 if self.machine_working("delivery_drone") else 1))
        if not self.spend(price, f"bought a {name.replace('_', ' ')}"):
            return f"I can't afford a {name.replace('_', ' ')} ({self.credits()}/{price} credits)."
        p = self.parts()
        p[name] = p.get(name, 0) + 1
        self.db.set("parts", p)
        self.db.set("delivery", {"to": "mech_shop" if self.is_built("mech_shop") else "home", "ts": time.time()})
        return f"I bought a {name.replace('_', ' ')} for {price} credits. I have {p[name]} now."

    def machines(self):
        return [dict(m) for m in self.db.q("SELECT * FROM machines ORDER BY id")]

    def machine_working(self, kind):
        return any(m["kind"] == kind and m["condition"] > 0 for m in self.machines())

    def simulate(self, kind, use):
        """Checks a machine design. Returns (ok, list of reasons)."""
        lv, name, does, req = MACHINES[kind]
        problems = []
        for p, n in req.items():
            if use.get(p, 0) < n:
                problems.append(f"needs {n} {p.replace('_', ' ')} (has {use.get(p, 0)})")
        supply = sum(PARTS[p][1] * n for p, n in use.items() if PARTS[p][1] > 0)
        draw = -sum(PARTS[p][1] * n for p, n in use.items() if PARTS[p][1] < 0)
        if supply == 0:
            problems.append("no power source (a battery or solar panel)")
        elif supply < draw:
            problems.append(f"not enough power: draws {draw}, supplies {supply}")
        others = sum(n for p, n in use.items() if p != "frame")
        if others > 6 * max(1, use.get("frame", 0)):
            problems.append(f"too many parts for {use.get('frame', 0)} frame(s): {others} parts, a frame holds 6")
        return not problems, problems

    def act_view_workshop(self, a, imp):
        p = self.parts()
        goals = [g for g in self.goals_open() if g["kind"] == "machine"]
        ms = self.machines()
        return (f"Parts I own: {', '.join(f'{k} x{v}' for k, v in p.items() if v) or 'none'} (buy at the Department Store as parts:<name>). "
                f"Part prices: {', '.join(f'{k} {v[0]}' for k, v in PARTS.items())}. "
                f"Goals: {' | '.join(f'#{g['id']} {g['title']}: {g['text']}' for g in goals) or 'none'}. "
                f"Machines: {', '.join(f'#{m['id']} {MACHINES[m['kind']][1]} ({m['condition']:.0f}%)' for m in ms) or 'none yet'}.")

    def act_design_machine(self, a, imp):
        goals = [g for g in self.goals_open() if g["kind"] == "machine" and g["status"] == "open"]
        kind = str(a.get("machine", "")).strip().lower().replace(" ", "_")
        if kind not in MACHINES:
            kind = next((g["ref"] for g in goals if g["ref"] in MACHINES), None)
        if not kind:
            return "I don't have a machine in mind. This week's goal is in view_workshop."
        lv, name, does, req = MACHINES[kind]
        owned = self.parts()
        last = self.db.get(f"machine_fail_{kind}") or ""
        ctx = (f"MACHINE: {name}: it {does}.\nREQUIRED PARTS: {json.dumps(req)}\nPARTS YOU OWN: {json.dumps(owned)}\n"
               + (f"YOUR LAST DESIGN FAILED BECAUSE: {last}\n" if last else "")
               + self.skill_examples("machine", name + " " + does))
        out = self.ask(MACHINE_PROMPT.format(name=self.name), ctx, "machine_design")
        use = {}
        for p, n in (out.get("parts") or {}).items():
            p = str(p).strip().lower().replace(" ", "_")
            try:
                n = max(0, min(12, int(n)))
            except (TypeError, ValueError):
                continue
            if p in PARTS and n:
                use[p] = n
        short = [f"{n - owned.get(p, 0)} more {p}" for p, n in use.items() if owned.get(p, 0) < n]
        if short:
            return f"My {name} design needs parts I don't have yet: {', '.join(short)}. I can buy them at the Department Store."
        ok, problems = self.simulate(kind, use)
        design = json.dumps(use)
        self.db.set("last_sim", ok)
        if not ok:
            self.db.set(f"machine_fail_{kind}", "; ".join(problems))
            self.gain_xp("building", 2, "learned from the simulator")
            return f"The simulator rejected my {name} design: {'; '.join(problems)}. I kept my parts."
        for p, n in use.items():
            owned[p] -= n
        self.db.set("parts", {k: v for k, v in owned.items() if v > 0})
        self.db.set(f"machine_fail_{kind}", None)
        mid = self.db.x("INSERT INTO machines(ts, kind, design, condition, last_maint) VALUES(?,?,?,?,?)",
                        (time.time(), kind, design, 100.0, time.time()))
        self.add_event("machine", f"⚙️ {self.name} built a {name}", f"It {does}.", mid)
        self.mem.add("observation", f"I built a {name}! It {does}.", "mech_shop", 8)
        self.add_skill("machine", name, f"Parts used: {design}. {out.get('notes', '')}", does)
        for g in goals:
            if g["ref"] == kind:
                self.db.x("UPDATE goals SET status='passed', result=? WHERE id=?", (f"Built with {design}", g["id"]))
                self._goal_passed(g, design)
        self.check_milestone("first_machine", "Built its first machine", 20)
        return f"I built a {name} (#{mid})! It passed the simulator and it {does}."

    def act_maintain_machine(self, a, imp):
        ms = [m for m in self.machines()]
        if not ms:
            return "I don't have any machines to maintain."
        try:
            m = next(x for x in ms if x["id"] == int(a.get("machine_id")))
        except (TypeError, ValueError, StopIteration):
            m = min(ms, key=lambda x: x["condition"])
        p = self.parts()
        if p.get("gear", 0) < 1:
            return "Maintenance needs a spare gear, and I don't have one."
        p["gear"] -= 1
        self.db.set("parts", p)
        new = min(100.0, m["condition"] + 45)
        self.db.x("UPDATE machines SET condition=?, last_maint=? WHERE id=?", (new, time.time(), m["id"]))
        return f"I serviced my {MACHINES[m['kind']][1]}. It's at {new:.0f}% now."

    def machines_daily(self):
        """Once a day: machines wear down, and working ones do their job."""
        if self.db.get("machines_day") == self._today():
            return
        self.db.set("machines_day", self._today())
        repair = self.machine_working("repair_bot")
        for m in self.machines():
            if m["condition"] <= 0:
                continue
            wear = 1.5 * (0.5 if repair and m["kind"] != "repair_bot" else 1)
            cond = max(0.0, m["condition"] - wear)
            self.db.x("UPDATE machines SET condition=? WHERE id=?", (cond, m["id"]))
            name = MACHINES[m["kind"]][1]
            if cond <= 0:
                self.add_event("machine", f"🔧 The {name} broke down", "It needs maintenance before it helps again.")
                self.mem.add("observation", f"My {name} broke down. I should repair it (maintain_machine, needs a gear).", "mech_shop", 7)
                continue
            if cond < 30:
                self.mem.add("observation", f"My {name} is wearing out ({cond:.0f}%).", "mech_shop", 4)
            half = cond < 30
            k = m["kind"]
            if k == "watering_bot":
                self.job_water_plants({"id": 0})
            elif k == "seed_sorter" and random.random() < (0.2 if half else 0.4):
                from .plants import SPECIES as PS
                sp = random.choice(list(PS))
                inv = self.inventory(); inv["seeds"][sp] = inv["seeds"].get(sp, 0) + 1; self.db.set("inventory", inv)
                self.mem.add("observation", f"My Seed Sorter turned up a {sp.replace('_', ' ')} seed.", "mech_shop", 4)
            elif k == "music_box_bot":
                self.earn(1 if half else 3, "Music Box Bot tips")
            elif k == "cleaning_drone":
                self.earn(1 if half else 2, "Cleaning Drone kept the colony tidy")
                for p in self.pets():
                    p["happiness"] = min(100.0, p["happiness"] + 5); self._pet_save(p)
            elif k == "solar_array":
                self.earn(2 if half else 5, "Solar Array sold spare power")
            elif k == "pet_feeder":
                for p in self.pets():
                    if p["hunger"] > 60 and self.spend(5, f"Pet Feeder fed {p['name']}"):
                        p["hunger"] = max(0.0, p["hunger"] - 60); self._pet_save(p)

    # ------------------------------------------------------------ real-world plans
    def act_design_plan(self, a, imp):
        last = self.db.q("SELECT MAX(ts) AS t FROM plans")[0]["t"] or 0
        if time.time() - last < 5 * 86400:
            return "I sent my creator a real-world plan recently. I'll design the next one later this week."
        kind = str(a.get("kind", "")).strip().lower()
        if kind not in PLAN_KINDS:
            kind = random.choice(list(PLAN_KINDS))
        idea = str(a.get("idea", "")).strip()[:300]
        about = "\n".join(f"- {m['content'][:200]}" for m in self.mem.relevant(self.creator + " creator likes", 6))
        ctx = (f"IDEA: {idea or 'your choice'}\nWHAT YOU KNOW ABOUT YOUR CREATOR:\n{about}\n\n"
               + self.skill_examples("plan", kind + " " + idea, 1))
        out = self.ask(PLAN_PROMPT.format(name=self.name, creator=self.creator, kind=PLAN_KINDS[kind]), ctx, "project_plan")
        title = str(out.get("title", "")).strip()[:100]
        if not title:
            return "I sketched a real-world project but couldn't finish the plan."
        plan = {"summary": str(out.get("summary", ""))[:800], "difficulty": str(out.get("difficulty", "easy"))[:20],
                "parts": out.get("parts") if isinstance(out.get("parts"), list) else [],
                "tools": out.get("tools") if isinstance(out.get("tools"), list) else [],
                "steps": out.get("steps") if isinstance(out.get("steps"), list) else [],
                "code": str(out.get("code", ""))[:12000], "scad": str(out.get("scad", ""))[:12000],
                "tips": str(out.get("tips", ""))[:800], "safety": SAFETY}
        pid = self.db.x("INSERT INTO plans(ts, kind, title, plan) VALUES(?,?,?,?)", (time.time(), kind, title, json.dumps(plan)))
        self.add_skill("plan", title, plan["summary"] + " Steps: " + " ".join(str(s) for s in plan["steps"])[:1500], kind)
        self.add_event("plan", f"📐 {self.name} designed a project for you: {title}", plan["summary"][:300], pid)
        self.gain_xp("building", 6, "designed a real-world project")
        return f"I designed a real-world project for my creator: \"{title}\". It's waiting for them in the Workshop."

    def plans_list(self):
        out = []
        for r in self.db.q("SELECT * FROM plans ORDER BY id DESC LIMIT 30"):
            d = dict(r)
            d["plan"] = json.loads(d["plan"])
            out.append(d)
        return out

    def plan_markdown(self, pid):
        r = self.db.q("SELECT * FROM plans WHERE id=?", (pid,))
        if not r:
            return None
        p, title = json.loads(r[0]["plan"]), r[0]["title"]
        lines = [f"# {title}", "", f"*{PLAN_KINDS.get(r[0]['kind'], r[0]['kind'])} · {p['difficulty']} · designed by {self.name}*", "",
                 f"> {p['safety']}", "", p["summary"], "", "## Parts"]
        for it in p["parts"]:
            if isinstance(it, dict):
                lines.append(f"- {it.get('qty', 1)} × {it.get('item', '')}" + (f" ({it.get('note')})" if it.get("note") else ""))
            else:
                lines.append(f"- {it}")
        if p["tools"]:
            lines += ["", "## Tools"] + [f"- {t}" for t in p["tools"]]
        lines += ["", "## Steps"] + [f"{i + 1}. {s}" for i, s in enumerate(p["steps"])]
        if p["code"]:
            lines += ["", "## Code", "```", p["code"], "```"]
        if p["scad"]:
            lines += ["", "## OpenSCAD", "```", p["scad"], "```"]
        if p["tips"]:
            lines += ["", "## Tips", p["tips"]]
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------ news and overview
    def workshop_news(self):
        out = []
        for g in self.goals_open():
            where = "the Fab Hangar (attempt_challenge)" if g["kind"] == "code" else "the Mechanical Workshop (design_machine)"
            if g["status"] == "review":
                out.append(f"GOAL '{g['title']}' is waiting for your creator's review.")
            elif (g["kind"] == "code" and self.is_built("workshop")) or (g["kind"] == "machine" and self.is_built("mech_shop")):
                out.append(f"WEEKLY GOAL: {g['title']}. {g['text'][:200]} Work on it at {where}.")
        if self.is_built("workshop") and any(g["kind"] == "code" and g["tests"] for g in self.goals_open()) and self.sandbox_problem():
            out.append(f"The Fab Hangar sandbox is offline: {self.sandbox_problem()} Coding challenges wait until it's back (it won't count against you).")
        broken = [MACHINES[m["kind"]][1] for m in self.machines() if m["condition"] < 30]
        if broken:
            out.append(f"Machines that need maintenance: {', '.join(broken)}.")
        if self.is_built("mech_shop"):
            last = self.db.q("SELECT MAX(ts) AS t FROM plans")[0]["t"] or 0
            if time.time() - last > 6 * 86400:
                out.append("It's time to design this week's real-world project for your creator (design_plan at the Mechanical Workshop).")
        return out

    def workshop_overview(self):
        return {"goals": [dict(g) for g in self.db.q("SELECT id, ts, week, kind, ref, title, text, tests, source, status, attempts, result, last_code, by_user FROM goals ORDER BY id DESC LIMIT 30")],
                "code_level": int(self.db.get("code_level", 1)), "mech_level": int(self.db.get("mech_level", 1)),
                "parts": self.parts(), "part_prices": {k: v[0] for k, v in PARTS.items()},
                "machines": [dict(m, name=MACHINES[m["kind"]][1], does=MACHINES[m["kind"]][2]) for m in self.machines()],
                "plans": self.plans_list(), "skills": self.db.q("SELECT COUNT(*) AS n FROM skills")[0]["n"],
                "sandbox": self.sandbox_kind(), "sandbox_status": self.sandbox_status(),
                "sandbox_problem": self.sandbox_problem()}
