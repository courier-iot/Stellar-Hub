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
    """v0.13.3: every memory's keywords go into an index (memory_words), so recall reaches back through its whole life,
    not just the newest 1,500 memories."""
    PER_WORD = 400        # newest matches looked at for each keyword
    BACKFILL = 5000       # older memories indexed per start-up / turn until the whole history is covered

    def __init__(self, db):
        self.db = db
        self.backfill()

    def _index(self, mid, content):
        ws = words(content)
        if ws:
            self.db.many("INSERT OR IGNORE INTO memory_words(word, mid) VALUES(?,?)", [(w, mid) for w in ws])

    def backfill(self):
        """Indexes memories from before v0.13.3, newest first, a batch at a time."""
        upto = self.db.get("memidx_below")
        if upto is None:
            upto = self.last_id() + 1
        if upto <= 1:
            return 0
        rows = self.db.q("SELECT id, content FROM memories WHERE id < ? ORDER BY id DESC LIMIT ?", (upto, self.BACKFILL))
        pairs = [(w, r["id"]) for r in rows for w in words(r["content"])]
        if pairs:
            self.db.many("INSERT OR IGNORE INTO memory_words(word, mid) VALUES(?,?)", pairs)
        self.db.set("memidx_below", rows[-1]["id"] if rows else 0)
        return len(rows)

    def add(self, kind, content, building="", importance=3):
        importance = max(1, min(10, int(importance or 3)))
        mid = self.db.x(
            "INSERT INTO memories(ts, kind, building, content, importance) VALUES(?,?,?,?,?)",
            (time.time(), kind, building, content.strip(), importance),
        )
        if self.db.get("memidx_below") is None:      # first ever memory on a new install: nothing older to index
            self.db.set("memidx_below", mid)
        self._index(mid, content)
        return mid

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
        weight, ids = {}, set()
        for w in list(q)[:24]:
            hits = [r["mid"] for r in self.db.q("SELECT mid FROM memory_words WHERE word=? ORDER BY mid DESC LIMIT ?",
                                                 (w, self.PER_WORD))]
            if not hits:
                continue
            # rarer words count for more (a full page of hits means a common word)
            weight[w] = 1.0 + (1.5 if len(hits) < 40 else 0.6 if len(hits) < self.PER_WORD else 0.0)
            ids.update(hits)
        ids.update(r["id"] for r in self.db.q("SELECT id FROM memories ORDER BY id DESC LIMIT 300"))
        rows = []
        idl = sorted(ids)
        for i in range(0, len(idl), 500):
            chunk = idl[i:i + 500]
            rows += self.db.q(f"SELECT * FROM memories WHERE id IN ({','.join('?' * len(chunk))})", chunk)
        scored = []
        for r in rows:
            if r["id"] in exclude_ids or r.get("archived"):
                continue
            shared = q & words(r["content"])
            if not shared:
                continue
            overlap = sum(weight.get(w, 1.0) for w in shared)
            hours = (now - r["ts"]) / 3600
            recency = math.exp(-hours / 72)  # fades over ~3 days, but old memories still come up when they match well
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
