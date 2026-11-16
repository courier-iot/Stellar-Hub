"""The Curio Exchange (auction house), mixed into the Agent: sell spare curios, fill collectors'
wanted orders, trade 5 of a rarity up into 1 of the next, and run timed auctions."""
import datetime
import random
import time

from . import curios

BASE_PRICE = {"common": 6, "uncommon": 15, "rare": 40, "legendary": 120}
NEXT_RARITY = {"common": "uncommon", "uncommon": "rare", "rare": "legendary"}
TRADE_UP_COUNT = 5
AUCTION_HOURS = 6
MAX_AUCTIONS = 3


class ExchangeMixin:
    # ------------------------------------------------------------ helpers
    def displayed_curios(self):
        out = set()
        for spots in self.home()["spots"].values():
            for it in spots.values():
                if it["type"] == "curio":
                    out.add(it["id"])
                elif it["type"] == "set":
                    from .curio_sets import piece_ids, SETS
                    if it["id"] in SETS:
                        out.update(piece_ids(it["id"]))
        return out

    def spares(self, cid):
        """Copies it can part with: everything except the one on display."""
        n = self.collection().get(cid, 0)
        listed = sum(1 for a in self.db.q("SELECT curio FROM auctions WHERE status='open'") if a["curio"] == cid)
        return max(0, n - (1 if cid in self.displayed_curios() else 0) - listed)

    def _take(self, cid, n=1):
        col = self.collection()
        col[cid] = col.get(cid, 0) - n
        if col[cid] <= 0:
            del col[cid]
        self.db.set("curios", col)

    def _give(self, cid):
        col = self.collection()
        first = cid not in col
        col[cid] = col.get(cid, 0) + 1
        self.db.set("curios", col)
        return first

    def _resolve_curio(self, q):
        q = str(q or "").strip().lower()
        col = self.collection()
        return next((c for c in col if c == q or curios.CATALOG[c]["name"].lower() == q), None) or \
            next((c for c in col if q and q in curios.CATALOG[c]["name"].lower()), None)

    # ------------------------------------------------------------ wanted board
    def wanted_board(self):
        today = datetime.date.today().isoformat()
        board = self.db.get("wanted")
        if board and board.get("day") == today:
            return board
        rnd = random.Random()
        owned_spares = [c for c in self.collection() if self.spares(c) > 0]
        picks = set()
        if owned_spares and rnd.random() < 0.7:   # usually one request it can actually fill
            picks.add(rnd.choice(owned_spares))
        while len(picks) < 3:
            picks.add(curios.random_find(rnd, boost=1))
        orders = []
        for cid in picks:
            base = BASE_PRICE[curios.CATALOG[cid]["rarity"]]
            orders.append({"curio": cid, "price": int(base * rnd.uniform(1.6, 2.5)),
                           "collector": rnd.choice(["Old Vega", "Captain Ilo", "The Miner Twins", "Professor Quill",
                                                    "Wren of Ceres", "A quiet stranger", "Dr. Halley", "Pip the Trader"])})
        board = {"day": today, "orders": orders}
        self.db.set("wanted", board)
        return board

    # ------------------------------------------------------------ actions
    def act_check_exchange(self, a, imp):
        self.resolve_auctions()
        board = self.wanted_board()
        wanted = "; ".join(f"{o['collector']} wants {curios.CATALOG[o['curio']]['name']} ({o['curio']}) for {o['price']}"
                           + (" (you have a spare!)" if self.spares(o["curio"]) else "") for o in board["orders"]) or "nothing today"
        auctions = self.db.q("SELECT * FROM auctions WHERE status='open'")
        mine = "; ".join(f"{curios.CATALOG[x['curio']]['name']} (reserve {x['reserve']})" for x in auctions) or "none"
        spare = [(c, self.spares(c)) for c in self.collection()]
        spare = [f"{curios.CATALOG[c]['name']} x{n} ({curios.CATALOG[c]['rarity']})" for c, n in spare if n > 0]
        prices = ", ".join(f"{r} {p}" for r, p in BASE_PRICE.items())
        return (f"Exchange prices: {prices}. Wanted board: {wanted}. My open auctions: {mine}. "
                f"My spares: {', '.join(spare) or 'none'}.")

    def act_sell_curio(self, a, imp):
        cid = self._resolve_curio(a.get("curio"))
        if not cid:
            return "I don't have that curio."
        try:
            n = max(1, min(20, int(a.get("count", 1) or 1)))
        except (TypeError, ValueError):
            n = 1
        have = self.spares(cid)
        name = curios.CATALOG[cid]["name"]
        if have <= 0:
            return f"My only {name} is on display (or up for auction). I'd have to take it down first."
        n = min(n, have)
        board = self.wanted_board()
        order = next((o for o in board["orders"] if o["curio"] == cid), None)
        total, notes = 0, []
        for _ in range(n):
            if order:
                total += order["price"]
                notes.append(f"{order['collector']} paid {order['price']}")
                board["orders"].remove(order)
                self.db.set("wanted", board)
                order = None
            else:
                total += BASE_PRICE[curios.CATALOG[cid]["rarity"]]
        self._take(cid, n)
        self.earn(total, f"sold {n}x {name}")
        self.db.x("INSERT INTO trades(ts, kind, detail, credits) VALUES(?,?,?,?)", (time.time(), "sell", f"{n}x {name}", total))
        self.gain_xp("collecting", n)
        return f"I sold {n}x {name} for {total} credits" + (f" ({'; '.join(notes)})" if notes else "") + "."

    def act_trade_up(self, a, imp):
        rarity = str(a.get("rarity", "common")).lower()
        if rarity not in NEXT_RARITY:
            return "I can trade up common, uncommon or rare curios (5 of one rarity become 1 of the next)."
        kind = str(a.get("kind", "") or "").lower() or None
        pool = []
        for cid in sorted(self.collection(), key=lambda c: -self.spares(c)):   # most-duplicated first
            item = curios.CATALOG[cid]
            if item["rarity"] == rarity and (not kind or item["kind"] == kind):
                pool += [cid] * self.spares(cid)
        if len(pool) < TRADE_UP_COUNT:
            return f"I need {TRADE_UP_COUNT} spare {rarity} curios{' of that kind' if kind else ''} to trade up. I have {len(pool)}."
        used = pool[:TRADE_UP_COUNT]
        for cid in used:
            self._take(cid)
        target = NEXT_RARITY[rarity]
        kinds = {curios.CATALOG[c]["kind"] for c in used}
        options = [c for c in curios.CATALOG.values() if c["rarity"] == target and (len(kinds) > 1 or c["kind"] in kinds)]
        missing = [c for c in options if c["id"] not in self.collection()]
        pick = random.choice(missing if missing and random.random() < 0.65 else options)["id"]
        first = self._give(pick)
        if first:
            self.note_curio(pick, "a trade-up at the Curio Exchange")
        names = ", ".join(curios.CATALOG[c]["name"] for c in used)
        result = curios.CATALOG[pick]["name"]
        self.db.x("INSERT INTO trades(ts, kind, detail, credits) VALUES(?,?,?,?)",
                  (time.time(), "trade_up", f"{names} -> {result}", 0))
        self.gain_xp("collecting", 6 + 4 * list(NEXT_RARITY).index(rarity))
        if target in ("rare", "legendary"):
            self.add_event("curio", f"✨ {self.name} traded up for a {target} curio", result)
        art = "an" if target[0] in "aeiou" else "a"
        return (f"I traded {names} at the Exchange and got {art} {target} {result}"
                + (" (new to my collection!)" if first else "") + ".")

    def act_auction_curio(self, a, imp):
        cid = self._resolve_curio(a.get("curio"))
        if not cid:
            return "I don't have that curio."
        if self.spares(cid) <= 0:
            return "That one is on display or already up for auction."
        if len(self.db.q("SELECT id FROM auctions WHERE status='open'")) >= MAX_AUCTIONS:
            return f"I already have {MAX_AUCTIONS} auctions running."
        base = BASE_PRICE[curios.CATALOG[cid]["rarity"]]
        try:
            reserve = max(1, int(a.get("reserve", base)))
        except (TypeError, ValueError):
            reserve = base
        self.db.x("INSERT INTO auctions(ts, curio, reserve, end_ts, status) VALUES(?,?,?,?, 'open')",
                  (time.time(), cid, reserve, time.time() + AUCTION_HOURS * 3600))
        return (f"I put my {curios.CATALOG[cid]['name']} up for auction with a reserve of {reserve} credits. "
                f"Bidding closes in {AUCTION_HOURS} hours.")

    def resolve_auctions(self):
        for au in self.db.q("SELECT * FROM auctions WHERE status='open' AND end_ts <= ?", (time.time(),)):
            item = curios.CATALOG[au["curio"]]
            base = BASE_PRICE[item["rarity"]]
            spread = {"common": (0.5, 1.8), "uncommon": (0.6, 2.0), "rare": (0.6, 2.3), "legendary": (0.7, 2.6)}[item["rarity"]]
            bidders = random.randint(0, 6)
            best = int(max(base * random.uniform(*spread) for _ in range(bidders))) if bidders else 0
            if best >= au["reserve"]:
                self._take(au["curio"])
                self.earn(best, f"auctioned {item['name']}")
                self.db.x("UPDATE auctions SET status='sold', best_bid=? WHERE id=?", (best, au["id"]))
                self.db.x("INSERT INTO trades(ts, kind, detail, credits) VALUES(?,?,?,?)",
                          (time.time(), "auction", item["name"], best))
                self.mem.add("observation", f"My {item['name']} sold at auction for {best} credits ({bidders} bidders).",
                             "exchange", 6)
                self.add_event("auction", f"🔨 {item['name']} sold for {best} credits", f"{bidders} collectors bid.")
                self.gain_xp("collecting", 3)
            else:
                self.db.x("UPDATE auctions SET status='unsold', best_bid=? WHERE id=?", (best, au["id"]))
                self.mem.add("observation", f"Nobody met my reserve for the {item['name']} at auction "
                                            f"(best bid {best or 'none'}). It came back to me.", "exchange", 4)

    def exchange_overview(self):
        self.resolve_auctions()
        board = self.wanted_board()
        return {
            "prices": BASE_PRICE,
            "wanted": [{**o, "name": curios.CATALOG[o["curio"]]["name"], "rarity": curios.CATALOG[o["curio"]]["rarity"],
                        "spare": self.spares(o["curio"]) > 0} for o in board["orders"]],
            "auctions": [{**x, "name": curios.CATALOG[x["curio"]]["name"]}
                         for x in self.db.q("SELECT * FROM auctions ORDER BY id DESC LIMIT 12")],
            "trades": self.db.q("SELECT * FROM trades ORDER BY id DESC LIMIT 15"),
        }
