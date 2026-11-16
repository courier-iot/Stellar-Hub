"""Curio sets and the Museum.

A complete set (one of each piece) pays a bonus the first time, fits in one showcase spot, and can be split again
just by taking it off display. At the Museum the resident can donate a set to a permanent exhibit (reputation, a daily
stipend and more visitors) or sell it to the curator for a big one-off price."""
import random
import time

from . import curios as CU
from .curio_sets import RARITY_MULT, SET_BONUS, SETS, piece_ids, set_of, source_for

BASE_PRICE = {"common": 6, "uncommon": 15, "rare": 40, "legendary": 120}


def set_title(sid):
    """The set's name without a leading 'The', for sentences like 'the Twin Moons set'."""
    n = SETS[sid][0]
    return n[4:] if n.startswith("The ") else n


def set_value(sid):
    n = len(SETS[sid][5])
    return int(SET_BONUS[n] * RARITY_MULT[SETS[sid][1]])


def set_icon(sid):
    """A 10x10 icon made of the set's pieces in miniature, on a gold-framed plinth."""
    pieces = [CU.sprite(c) for c in piece_ids(sid)]
    g = [["." for _ in range(10)] for _ in range(10)]
    slots = {2: [(0, 2), (5, 2)], 3: [(0, 0), (5, 0), (2, 5)], 4: [(0, 0), (5, 0), (0, 5), (5, 5)]}[len(pieces)]
    for spr, (ox, oy) in zip(pieces, slots):
        for y in range(5):
            for x in range(5):
                ch = spr[y * 2 + 1][x * 2 + 1] if spr[y * 2 + 1][x * 2 + 1] != "." else spr[y * 2][x * 2]
                if ch != ".":
                    g[oy + y][ox + x] = ch
    for x in range(10):
        if g[9][x] == ".":
            g[9][x] = "y"
    return ["".join(r) for r in g]


class MuseumMixin:
    # ------------------------------------------------------------ sets
    def set_progress(self):
        col = self.collection()
        out = {}
        for sid in SETS:
            ids = piece_ids(sid)
            have = [c for c in ids if col.get(c, 0) > 0]
            out[sid] = {"have": len(have), "need": len(ids), "complete": len(have) == len(ids)}
        return out

    def check_sets(self):
        done = set(self.db.get("sets_completed") or [])
        new = [sid for sid, p in self.set_progress().items() if p["complete"] and sid not in done]
        for sid in new:
            done.add(sid)
            bonus = set_value(sid)
            self.earn(bonus, f"completed the {set_title(sid)} set")
            self.gain_xp("collecting", 10 + len(SETS[sid][5]) * 3, "completed a set")
            self.mem.add("observation", f"I completed the {set_title(sid)} set! Bonus: {bonus} credits. I could display it "
                                        f"as one piece, or take it to the Museum.", "home", 8)
            self.add_event("set", f"🧩 {self.name} completed the {set_title(sid)} set", f"+{bonus} credits")
            self.check_milestone("first_set", "Completed its first curio set", 20)
        if new:
            self.db.set("sets_completed", sorted(done))
            if len(done) >= 10:
                self.check_milestone("ten_sets", "Completed ten curio sets", 100)

    def find_curio(self, source, boost=0, cid=None):
        """Set pieces turn up mostly from their own place: expeditions, meteors, visitors, pets…"""
        if cid is None:
            key = source_for(source)
            if key and random.random() < 0.3:
                pool = [c for c, v in CU.CATALOG.items() if v.get("source") == key]
                if pool:
                    w = [{"common": 60, "uncommon": 25, "rare": 10, "legendary": 3}[CU.CATALOG[c]["rarity"]] for c in pool]
                    cid = random.choices(pool, w)[0]
        label = super().find_curio(source, boost, cid)
        self.check_sets()
        return label

    def sets_text(self):
        prog = self.set_progress()
        started = [f"{SETS[s][0]} {p['have']}/{p['need']}" for s, p in prog.items() if p["have"]]
        return ", ".join(started) or "none started"

    def _set_arg(self, a):
        raw = str(a.get("set", "") or a.get("id", "")).strip()
        q = raw.lower().replace(" ", "_")
        if q in SETS:
            return q
        return next((k for k, v in SETS.items() if v[0].lower() == raw.lower() or raw.lower() in v[0].lower()), None) if raw else None

    def _set_free(self, sid):
        """All pieces can leave: none of them on display (the set or a piece) or at auction."""
        return all(self.spares(c) > 0 for c in piece_ids(sid))

    # ------------------------------------------------------------ the Museum
    def exhibits(self):
        return [dict(r) for r in self.db.q("SELECT * FROM museum ORDER BY id")]

    def reputation(self):
        return sum(set_value(e["set_id"]) for e in self.exhibits() if e["set_id"] in SETS)

    def museum_stipend(self):
        if not self.is_built("museum") or self.db.get("stipend_day") == self._today():
            return
        self.db.set("stipend_day", self._today())
        rep = self.reputation()
        if rep:
            amt = max(1, round(rep * 0.03))
            self.earn(amt, "Museum stipend (exhibit reputation)")

    def act_view_museum(self, a, imp):
        ex = self.exhibits()
        prog = self.set_progress()
        ready = [f"{SETS[s][0]} ({s})" for s, p in prog.items() if p["complete"]]
        hall = ", ".join(SETS[e["set_id"]][0] for e in ex if e["set_id"] in SETS) or "empty halls"
        offers = "; ".join(f"{SETS[s][0]}: sells for {self.set_sale_price(s)}, or donate for +{set_value(s)} reputation"
                           for s, p in prog.items() if p["complete"])
        return (f"Museum reputation {self.reputation()} (daily stipend {max(1, round(self.reputation() * 0.03)) if ex else 0}). "
                f"Exhibits: {hall}. Complete sets I own: {', '.join(ready) or 'none'}. {offers} "
                f"Sets in progress: {self.sets_text()}.")

    def set_sale_price(self, sid):
        return int(sum(BASE_PRICE[CU.CATALOG[c]["rarity"]] for c in piece_ids(sid)) * 2.5 + set_value(sid))

    def act_donate_set(self, a, imp):
        sid = self._set_arg(a)
        if not sid or not self.set_progress()[sid]["complete"]:
            return "I don't have a complete set like that to donate."
        if not self._set_free(sid):
            return f"Part of the {set_title(sid)} is on display or at auction. I'd take it down first."
        if any(e["set_id"] == sid for e in self.exhibits()):
            return f"The Museum already has the {set_title(sid)}. The curator would rather buy this one."
        for c in piece_ids(sid):
            self._take(c)
        self.db.x("INSERT INTO museum(ts, set_id) VALUES(?,?)", (time.time(), sid))
        self.add_event("museum", f"🏛 {self.name} donated the {set_title(sid)}", f"Museum reputation is now {self.reputation()}.")
        self.check_milestone("first_exhibit", "Opened its first Museum exhibit", 25)
        return (f"I donated the {set_title(sid)} to the Museum. It's on permanent display now. Reputation +{set_value(sid)} "
                f"(now {self.reputation()}), so the daily stipend grows and more visitors will come.")

    def act_sell_set(self, a, imp):
        sid = self._set_arg(a)
        if not sid or not self.set_progress()[sid]["complete"]:
            return "I don't have a complete set like that to sell."
        if not self._set_free(sid):
            return f"Part of the {set_title(sid)} is on display or at auction. I'd take it down first."
        price = self.set_sale_price(sid)
        for c in piece_ids(sid):
            self._take(c)
        self.earn(price, f"sold the {set_title(sid)} set to the Museum curator")
        self.db.x("INSERT INTO trades(ts, kind, detail, credits) VALUES(?,?,?,?)", (time.time(), "set_sale", SETS[sid][0], price))
        self.add_event("museum", f"💰 {self.name} sold the {set_title(sid)}", f"+{price} credits")
        return f"I sold the {set_title(sid)} set to the curator for {price} credits."

    def museum_overview(self):
        prog = self.set_progress()
        return {"reputation": self.reputation(), "stipend": max(1, round(self.reputation() * 0.03)) if self.exhibits() else 0,
                "exhibits": [{"set": e["set_id"], "name": SETS[e["set_id"]][0], "ts": e["ts"], "icon": set_icon(e["set_id"])}
                             for e in self.exhibits() if e["set_id"] in SETS],
                "sets": [{"id": s, "name": v[0], "rarity": v[1], "source": v[4], "have": prog[s]["have"], "need": prog[s]["need"],
                          "value": set_value(s), "sale": self.set_sale_price(s),
                          "pieces": [{"id": c, "name": CU.CATALOG[c]["name"], "owned": self.collection().get(c, 0),
                                      "icon": CU.sprite(c)} for c in piece_ids(s)]}
                         for s, v in SETS.items()]}
