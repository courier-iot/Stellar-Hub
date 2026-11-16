"""v0.13.3: the money tracker, for the resident and its creator.

Every ledger line is sorted into a category from its reason, then totalled by day, week and month. The resident sees a
short weekly money note in its news; the dashboard and app show the full picture with warnings when things drift."""
import datetime
import time

CATEGORIES = [   # (category, words in the ledger reason that put a line in it). First match wins.
    ("pets", ("pet", "adopted", "rescue", "fine", "vet", "treat", "feeder", "salvage")),
    ("workshop", ("bought a frame", "bought a wheel", "bought a gear", "bought a motor", "bought a sensor", "bought a circuit",
                  "bought a pump", "bought a arm", "bought an arm", "bought a lens", "bought a speaker", "bought a battery",
                  "bought a solar", "goal", "challenge")),
    ("machines", ("music box", "cleaning drone", "solar array", "machine")),
    ("museum & curios", ("museum", "set", "curio", "exchange", "auction", "trade", "sold", "donat")),
    ("building", ("built", "build", "construction", "unlock", "upper street", "plot")),
    ("style & decor", ("crown", "beanie", "scarf", "helmet", "antenna", "comet trail", "painted", "paint", "decor",
                       "furniture", "rug", "lamp", "poster")),
    ("shopping", ("bought", "seeds", "store", "shop")),
    ("garden", ("plant", "harvest", "flower", "greenhouse")),
    ("rewards", ("milestone", "skill reached", "level", "bonus", "gift from", "stipend", "routine", "stardust")),
]


def category(reason):
    r = (reason or "").lower()
    for cat, keys in CATEGORIES:
        if any(k in r for k in keys):
            return cat
    return "other"


def _day(ts):
    return datetime.date.fromtimestamp(ts).isoformat()


class EconomyMixin:
    def economy(self, days=30):
        now = time.time()
        rows = self.db.q("SELECT ts, amount, reason FROM ledger WHERE ts > ? ORDER BY ts", (now - days * 86400,))
        bal = self.credits()
        daily = {}
        for d in range(days - 1, -1, -1):
            daily[_day(now - d * 86400)] = {"in": 0, "out": 0}
        cats = {}
        week_in = week_out = 0
        week_cats = {}
        for r in rows:
            day = _day(r["ts"])
            if day in daily:
                daily[day]["in" if r["amount"] > 0 else "out"] += abs(r["amount"])
            c = category(r["reason"])
            e = cats.setdefault(c, {"in": 0, "out": 0})
            e["in" if r["amount"] > 0 else "out"] += abs(r["amount"])
            if r["ts"] > now - 7 * 86400:
                if r["amount"] > 0:
                    week_in += r["amount"]
                else:
                    week_out -= r["amount"]
                w = week_cats.setdefault(c, {"in": 0, "out": 0})
                w["in" if r["amount"] > 0 else "out"] += abs(r["amount"])
        # walk back from today's balance to get the balance at the end of each day
        series, b = [], bal
        for day in reversed(list(daily)):
            series.append({"day": day, "in": daily[day]["in"], "out": daily[day]["out"], "balance": b})
            b -= daily[day]["in"] - daily[day]["out"]
        series.reverse()
        big = [dict(r, category=category(r["reason"])) for r in
               self.db.q("SELECT ts, amount, reason FROM ledger WHERE ts > ? ORDER BY ABS(amount) DESC LIMIT 8", (now - 7 * 86400,))]
        warnings = []
        if bal < 0:
            warnings.append(f"In debt: {bal} credits.")
        weeks_down = 0
        for k in range(4):
            seg = series[max(0, len(series) - 7 * (k + 1)):len(series) - 7 * k]
            if seg and sum(x["in"] for x in seg) < sum(x["out"] for x in seg):
                weeks_down += 1
            else:
                break
        if weeks_down >= 2:
            warnings.append(f"Spending more than it earns for {weeks_down} weeks in a row.")
        if week_cats:
            top_out = max(week_cats.items(), key=lambda kv: kv[1]["out"])
            if week_out and top_out[1]["out"] > 0.6 * week_out and week_out > 100:
                warnings.append(f"Most of this week's spending ({top_out[1]['out']} of {week_out}) went on {top_out[0]}.")
        if len(series) >= 14 and series[-1]["balance"] > 4 * max(1, series[-14]["balance"]) and series[-1]["balance"] > 3000:
            warnings.append("Credits are piling up fast: rewards may be too generous.")
        return {"balance": bal, "days": series, "categories": cats, "week": {"in": week_in, "out": week_out, "categories": week_cats},
                "biggest": big, "warnings": warnings}

    def money_news(self):
        """A short weekly note for the resident (and a line any time it's in debt)."""
        out = []
        today = datetime.date.today()
        e = None
        if today.weekday() == 0 or self.credits() < 0:
            e = self.economy(14)
        if e and today.weekday() == 0:
            w = e["week"]
            top = sorted(w["categories"].items(), key=lambda kv: -kv[1]["out"])[:2]
            out.append(f"MONEY THIS PAST WEEK: earned {w['in']}, spent {w['out']}" +
                       (f" (mostly on {', '.join(c for c, _ in top if _['out'])})" if top else "") +
                       f". Balance {e['balance']}. " + " ".join(e["warnings"]))
        elif e and e["balance"] < 0:
            out.append(f"MONEY: you're {-e['balance']} credits in debt. Earn before you spend.")
        return out
