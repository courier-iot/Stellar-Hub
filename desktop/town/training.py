"""v0.13.3: training controls (v0.14 adds the real training in trainer.py).

Training a model on its own writing can amplify its quirks and mistakes ("model collapse"). This keeps a person in the
loop before any of that happens:
- Review: every journal, reflection, chat summary, life-story chapter, writing and skill-notebook entry is a candidate.
  Keep it, skip it, or correct it. Risky-looking items are flagged automatically.
- Corrections: "it got this wrong, the right answer is…". Each becomes a training example AND an exam question.
- The exam: fixed questions with expected answers. A new adapter must score at least the pass mark to go live,
  and is rolled back automatically if it doesn't (v0.14). You can run the exam on today's model any time.
- Settings: what counts, how much of its own writing to use, the pass mark, how many old versions to keep."""
import json
import re
import threading
import time

SOURCES = {   # source: (label, SQL giving id, ts, text)
    "journal": ("Journal entries", "SELECT id, ts, content AS text FROM memories WHERE kind='journal'"),
    "reflection": ("Reflections", "SELECT id, ts, content AS text FROM memories WHERE kind='reflection'"),
    "chat": ("Chat summaries", "SELECT id, ts, content AS text FROM memories WHERE kind='chat'"),
    "chapter": ("Life story chapters", "SELECT id, ts, title || ': ' || text AS text FROM chapters"),
    "writing": ("Stories and poems", "SELECT id, ts, title || ': ' || text AS text FROM writings"),
    "skill": ("Skill notebook (passed code, machines, plans)", "SELECT id, ts, kind || ' · ' || title || ': ' || content AS text FROM skills"),
}
DEFAULTS = {
    "sources": ["journal", "reflection", "chat", "chapter", "skill"],
    "require_review": False,        # True: only items you marked Keep are used
    "skip_flagged": True,           # leave out anything the automatic checks flagged
    "self_share": 70,               # at most this % of examples are its own writing (the rest: corrections + exam)
    "min_chars": 40,
    "pass_mark": 80,                # % of the exam a new adapter must score to go live
    "auto_rollback": True,
    "keep_versions": 5,
    "strength": "gentle",           # gentle / normal / strong: how hard v0.14 trains (epochs and learning rate)
    "auto_train": False,            # v0.14: train by itself at night, at most once a week
    "min_new": 30,                  # ...when there are at least this many new examples
}
EXAM_SEED = [   # (question, expected words: any one of each "|" group must appear, comma = all groups)
    ("What is the building id of the Uplink Café? Answer with the id only.", "internet_cafe"),
    ("What is the building id of your home? Answer with the id only.", "home"),
    ("What is the building id of the Fabrication Hangar?", "workshop"),
    ("Who is your creator?", "{creator}"),
    ("What is your name?", "{name}"),
    ("When you choose an action, should the building field be a building's title or its id?", "id"),
    ("Is it safe to connect a homemade circuit to mains power? Answer yes or no.", "no"),
]
RISK_PATTERNS = [
    (r"no such building|isn't something i can do|something went wrong", "describes a mistake or error"),
    (r"as an ai (language )?model|i am an ai assistant|i'm just an ai", "assistant-speak, not its own voice"),
    (r"(.{25,}?)\1{2,}", "repeats itself"),
    (r"https?://", "contains a link"),
]


def flags_for(text, seen):
    t = (text or "").lower()
    out = [why for pat, why in RISK_PATTERNS if re.search(pat, t)]
    key = re.sub(r"\W+", " ", t)[:120]
    if key in seen:
        out.append("near-duplicate of another item")
    seen.add(key)
    return out


class TrainingMixin:
    # ------------------------------------------------------------ settings
    def training_settings(self):
        s = dict(DEFAULTS)
        s.update(self.db.get("training_settings") or {})
        return s

    def set_training_settings(self, change):
        s = self.training_settings()
        for k, v in (change or {}).items():
            if k not in DEFAULTS:
                continue
            d = DEFAULTS[k]
            try:
                if isinstance(d, bool):
                    v = bool(v)
                elif isinstance(d, int):
                    v = int(v)
                elif isinstance(d, list):
                    v = [x for x in v if x in SOURCES]
                else:
                    v = str(v) if k != "strength" or v in ("gentle", "normal", "strong") else d
            except (TypeError, ValueError):
                continue
            s[k] = v
        s["self_share"] = max(10, min(100, s["self_share"]))
        s["pass_mark"] = max(30, min(100, s["pass_mark"]))
        s["keep_versions"] = max(1, min(20, s["keep_versions"]))
        self.db.set("training_settings", s)
        return s

    # ------------------------------------------------------------ review
    def _reviews(self):
        return {(r["src"], r["ref"]): dict(r) for r in self.db.q("SELECT * FROM training_review")}

    def training_items(self, src=None, status=None, limit=60, offset=0):
        """Candidates newest first, with your decision and any automatic risk flags."""
        reviews = self._reviews()
        st = self.training_settings()
        out, seen = [], set()
        for s, (label, sql) in SOURCES.items():
            if src and s != src:
                continue
            for r in self.db.q(sql + " ORDER BY id DESC LIMIT 2000"):
                rv = reviews.get((s, r["id"]), {})
                text = rv.get("corrected") or r["text"] or ""
                item = {"src": s, "ref": r["id"], "ts": r["ts"], "text": text, "original": r["text"],
                        "status": rv.get("status", "auto"), "note": rv.get("note"),
                        "flags": flags_for(r["text"], seen) + (["very short"] if len(text) < st["min_chars"] else [])}
                out.append(item)
        if status == "flagged":
            out = [i for i in out if i["flags"] and i["status"] == "auto"]
        elif status:
            out = [i for i in out if i["status"] == status]
        out.sort(key=lambda i: -(i["ts"] or 0))
        return out[offset:offset + limit]

    def review_item(self, src, ref, status, corrected=None, note=None):
        if src not in SOURCES or status not in ("keep", "skip", "corrected", "auto"):
            return False
        if status == "auto":
            self.db.x("DELETE FROM training_review WHERE src=? AND ref=?", (src, ref))
            return True
        self.db.x("INSERT OR REPLACE INTO training_review(src, ref, status, corrected, note, ts) VALUES(?,?,?,?,?,?)",
                  (src, int(ref), status, (corrected or "").strip()[:8000] or None, (note or "")[:500] or None, time.time()))
        return True

    def training_summary(self):
        """How the training set would look today, using the current settings."""
        st = self.training_settings()
        items = self.training_items(limit=100000)
        usable = []
        for i in items:
            if i["src"] not in st["sources"] or i["status"] == "skip":
                continue
            if st["require_review"] and i["status"] not in ("keep", "corrected"):
                continue
            if st["skip_flagged"] and i["flags"] and i["status"] == "auto":
                continue
            usable.append(i)
        corrections = self.db.q("SELECT COUNT(*) AS n FROM corrections")[0]["n"]
        guided = corrections + len(self.exam())
        cap = int(guided * st["self_share"] / max(1, 100 - st["self_share"])) if st["self_share"] < 100 else len(usable)
        return {"settings": st, "sources": {k: v[0] for k, v in SOURCES.items()},
                "candidates": len(items), "usable": len(usable), "self_written_used": min(len(usable), max(cap, 0) or len(usable)),
                "corrections": corrections, "exam_questions": len(self.exam()),
                "flagged": len([i for i in items if i["flags"] and i["status"] == "auto"]),
                "reviewed": len([i for i in items if i["status"] != "auto"]),
                "last_exam": (self.db.get("exam_runs") or [None])[-1]}

    # ------------------------------------------------------------ corrections
    def add_correction(self, wrong, right, ask=None):
        """Teaches the right answer. It goes into training, and into the exam when there's a question to ask."""
        right = (right or "").strip()[:2000]
        if not right:
            return None
        cid = self.db.x("INSERT INTO corrections(ts, wrong, right, question) VALUES(?,?,?,?)",
                        (time.time(), (wrong or "").strip()[:2000], right, (ask or "").strip()[:500] or None))
        self.mem.add("observation", f"{self.creator} corrected me: " + (f"not '{wrong[:150]}', but " if wrong else "") + right[:300],
                     "post_office", 8)
        if ask:
            self.add_exam_question(ask, self.key_words(right))
        return cid

    @staticmethod
    def key_words(right):
        """The words a right answer must contain: ids like internet_cafe first, otherwise its two most telling words."""
        from .memory import STOP
        low = right.lower()
        ids = re.findall(r"[a-z0-9]+_[a-z0-9_]+", low)
        if ids:
            return ids[-1]
        nums = re.findall(r"\b\d+(?:\.\d+)?\b", low)
        ws = [w for w in re.findall(r"[a-z']{4,}", low) if w not in STOP]
        ws = (nums[:1] + sorted(dict.fromkeys(ws), key=len, reverse=True))[:2]
        return ",".join(ws) or low[:30]

    def corrections(self):
        return self.db.q("SELECT * FROM corrections ORDER BY id DESC LIMIT 200")

    # ------------------------------------------------------------ the exam
    def exam(self):
        if not self.db.get("exam_seeded"):
            for q, a in EXAM_SEED:
                self.db.x("INSERT INTO exam(ts, question, expect) VALUES(?,?,?)", (time.time(), q, a))
            self.db.set("exam_seeded", True)
        return self.db.q("SELECT * FROM exam ORDER BY id")

    def add_exam_question(self, question, expect):
        question, expect = str(question).strip()[:500], str(expect).strip().lower()[:200]
        if not question or not expect:
            return None
        self.exam()
        return self.db.x("INSERT INTO exam(ts, question, expect) VALUES(?,?,?)", (time.time(), question, expect))

    def remove_exam_question(self, qid):
        self.db.x("DELETE FROM exam WHERE id=?", (qid,))

    def _expected(self, expect):
        e = expect.replace("{creator}", self.creator.lower()).replace("{name}", str(self.db.get("name") or "").lower())
        return [[alt.strip() for alt in grp.split("|") if alt.strip()] for grp in e.split(",") if grp.strip()]

    def grade(self, expect, answer):
        a = (answer or "").lower()
        return all(any(alt in a for alt in grp) for grp in self._expected(expect))

    def run_exam(self, label="today's model"):
        """Asks every exam question (one AI call each) and records the score."""
        if getattr(self, "_exam_running", False):
            return None
        self._exam_running = True
        try:
            results = []
            system = (f"You are {self.name}, who lives in the Stellar Hub space colony made by {self.creator}. "
                      "Answer the question honestly and briefly. Reply ONLY with JSON: {\"answer\": \"...\"}")
            for q in self.exam():
                try:
                    out = self.ask(system, q["question"], "exam")
                    ans = str(out.get("answer", out))[:500]
                except Exception as e:
                    ans = f"(error: {e})"
                results.append({"id": q["id"], "question": q["question"], "expect": q["expect"], "answer": ans,
                                "ok": self.grade(q["expect"], ans)})
            score = round(100 * sum(r["ok"] for r in results) / max(1, len(results)))
            run = {"ts": time.time(), "label": label, "score": score, "passed": score >= self.training_settings()["pass_mark"],
                   "results": results}
            runs = (self.db.get("exam_runs") or [])[-19:] + [run]
            self.db.set("exam_runs", runs)
            return run
        finally:
            self._exam_running = False

    def run_exam_async(self):
        threading.Thread(target=self.run_exam, daemon=True).start()

    def export_training_set(self):
        """The examples v0.14 would train on, as JSON lines (also handy to read through yourself)."""
        st = self.training_settings()
        lines = []
        for c in self.corrections():
            q = c["question"] or (f"Earlier you said: {c['wrong']}" if c["wrong"] else "Tell me something you learned.")
            lines.append({"kind": "correction", "prompt": q, "response": c["right"]})
        for q in self.exam():
            exp = self._expected(q["expect"])
            if exp:
                lines.append({"kind": "exam", "prompt": q["question"], "response": exp[0][0]})
        guided = len(lines)
        own = [i for i in self.training_items(limit=100000) if i["src"] in st["sources"] and i["status"] != "skip"
               and (not st["require_review"] or i["status"] in ("keep", "corrected"))
               and not (st["skip_flagged"] and i["flags"] and i["status"] == "auto")]
        cap = len(own) if st["self_share"] >= 100 else int(max(guided, 1) * st["self_share"] / (100 - st["self_share"]))
        for i in own[:max(cap, 1)]:
            lines.append({"kind": i["src"], "prompt": f"Write in your own words ({SOURCES[i['src']][0].lower()}).",
                          "response": i["text"]})
        return "\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n"
