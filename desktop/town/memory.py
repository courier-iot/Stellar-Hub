"""Memory stream: observations, reflections and plans, with simple retrieval.

Retrieval scores each memory by keyword overlap + importance + recency,
the same idea as the "Generative Agents" research, without needing embeddings.
"""
import math
import re
import time

STOP = set("""a an the and or but if of to in on at for with is are was were be been i me my
you your it its this that these those as by from so do did not no yes can will just about
what which who how when where why there here have has had they them their we our""".split())


def words(text):
    return {w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if w not in STOP and len(w) > 2}


def ago(ts):
    s = max(0, time.time() - ts)
    if s < 90:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)}m ago"
    if s < 86400:
        return f"{int(s // 3600)}h ago"
    return f"{int(s // 86400)}d ago"


class Memory:
    def __init__(self, db):
        self.db = db

    def add(self, kind, content, building="", importance=3):
        importance = max(1, min(10, int(importance or 3)))
        return self.db.x(
            "INSERT INTO memories(ts, kind, building, content, importance) VALUES(?,?,?,?,?)",
            (time.time(), kind, building, content.strip(), importance),
        )

    def recent(self, n=15, kinds=None):
        if kinds:
            marks = ",".join("?" * len(kinds))
            rows = self.db.q(f"SELECT * FROM memories WHERE kind IN ({marks}) ORDER BY id DESC LIMIT ?",
                             (*kinds, n))
        else:
            rows = self.db.q("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (n,))
        return list(reversed(rows))

    def relevant(self, query, n=8, exclude_ids=()):
        q = words(query)
        if not q:
            return []
        now = time.time()
        rows = self.db.q("SELECT * FROM memories ORDER BY id DESC LIMIT 1500")
        scored = []
        for r in rows:
            if r["id"] in exclude_ids:
                continue
            overlap = len(q & words(r["content"]))
            if not overlap:
                continue
            hours = (now - r["ts"]) / 3600
            recency = math.exp(-hours / 72)  # fades over ~3 days
            score = overlap * 1.0 + r["importance"] * 0.3 + recency * 1.5
            scored.append((score, r))
        scored.sort(key=lambda t: -t[0])
        return [r for _, r in scored[:n]]

    def importance_since(self, memory_id):
        rows = self.db.q("SELECT COALESCE(SUM(importance),0) AS s FROM memories WHERE id > ? AND kind != 'reflection'",
                         (memory_id,))
        return rows[0]["s"]

    def last_id(self):
        rows = self.db.q("SELECT COALESCE(MAX(id),0) AS m FROM memories")
        return rows[0]["m"]

    @staticmethod
    def fmt(rows):
        return "\n".join(f"- [{ago(r['ts'])}] ({r['kind']}) {r['content']}" for r in rows) or "- (nothing yet)"
