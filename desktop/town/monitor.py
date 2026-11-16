"""The monitor: watches three tracks (pets, money and the model) and flags anything unusual, so problems are easy to
spot while testing. Levels: info (worth knowing), warn (looks odd), alert (something's wrong; also sent to the phone)."""
import time

INVALID = ("isn't something I can do", "no such building", "but it's locked", "isn't free", "don't have a blueprint",
           "couldn't find that", "Something went wrong")


class MonitorMixin:
    def monitor(self, track, level, title, detail=""):
        recent = self.db.q("SELECT 1 FROM monitor WHERE track=? AND title=? AND ts > ?", (track, title[:200], time.time() - 3600))
        if recent:
            return
        self.db.x("INSERT INTO monitor(ts, track, level, title, detail) VALUES(?,?,?,?,?)",
                  (time.time(), track, level, title[:200], str(detail)[:1000]))
        if level == "alert":
            super().add_event("monitor", f"🩺 {title}", str(detail)[:300])

    # ------------------------------------------------------------ model
    def monitor_turn(self, out, seconds):
        if not isinstance(out, dict) or out.get("skipped"):
            return
        if out.get("error"):
            self.monitor("model", "alert", "A turn failed", out["error"])
            return
        res = str(out.get("result", ""))
        hist = self.db.get("monitor_turns") or []
        hist = (hist + [{"b": out.get("building"), "a": out.get("action"), "bad": any(w in res for w in INVALID),
                         "s": round(seconds, 1)}])[-12:]
        self.db.set("monitor_turns", hist)
        if hist[-1]["bad"]:
            self.monitor("model", "warn", f"Invalid choice: {out.get('action')} at {out.get('building')}", res[:300])
        if sum(1 for h in hist[-10:] if h["bad"]) >= 4:
            self.monitor("model", "alert", "Many invalid choices lately",
                         f"{sum(1 for h in hist[-10:] if h['bad'])} of the last 10 turns picked something that couldn't happen. "
                         "The model may be too small or confused by the prompt.")
        last5 = [(h["b"], h["a"]) for h in hist[-5:]]
        if len(last5) == 5 and len(set(last5)) == 1:
            self.monitor("model", "warn", f"Stuck repeating {last5[0][1]} at {last5[0][0]}", "Five turns in a row did the same thing.")
        if seconds > 240:
            self.monitor("model", "warn", "Slow turn", f"A turn took {seconds:.0f} seconds.")
        lim = self.cfg["limits"]["llm_calls_per_day"]
        used = self._usage().get("llm_calls", 0)
        if used >= lim * 0.9:
            self.monitor("model", "warn", "Close to the daily AI-call limit", f"{used} of {lim} calls used today.")

    # ------------------------------------------------------------ money
    def earn(self, amount, reason):
        before = self.credits()
        super().earn(amount, reason)
        amount = int(amount)
        if not amount:
            return
        after = self.credits()
        if amount < 0 and -amount >= max(150, 0.4 * max(before, 1)):
            self.monitor("money", "warn", f"Big spend: {-amount} credits", f"{reason}. Balance {before} → {after}.")
        if after < 0 <= before:
            self.monitor("money", "alert", f"Went into debt ({after} credits)", reason)
        if amount >= 300:
            self.monitor("money", "info", f"Big income: +{amount}", reason)

    def money_daily_check(self):
        day = self._today()
        if self.db.get("monitor_money_day") == day:
            return
        self.db.set("monitor_money_day", day)
        now = time.time()
        rows = self.db.q("SELECT ts, amount FROM ledger WHERE ts > ?", (now - 8 * 86400,))
        y_in = sum(r["amount"] for r in rows if r["amount"] > 0 and now - r["ts"] < 86400)
        y_out = -sum(r["amount"] for r in rows if r["amount"] < 0 and now - r["ts"] < 86400)
        old = [r for r in rows if now - r["ts"] >= 86400]
        avg_out = -sum(r["amount"] for r in old if r["amount"] < 0) / 7
        avg_in = sum(r["amount"] for r in old if r["amount"] > 0) / 7
        self.monitor("money", "info", f"Daily money: +{y_in} / -{y_out}", f"Balance {self.credits()}. 7-day average +{avg_in:.0f} / -{avg_out:.0f}.")
        if y_out > 100 and avg_out and y_out > 3 * avg_out:
            self.monitor("money", "warn", "Spending spike", f"Spent {y_out} in the last day, about {y_out / avg_out:.1f}× its usual.")
        if y_in > 100 and avg_in and y_in > 3 * avg_in:
            self.monitor("money", "warn", "Earnings spike", f"Earned {y_in} in the last day, about {y_in / avg_in:.1f}× its usual.")

    # ------------------------------------------------------------ pets
    def monitor_pets(self):
        last = self.db.get("monitor_pet_health") or {}
        now = {}
        for p in self.pets():
            now[str(p["id"])] = p["health"]
            prev = last.get(str(p["id"]))
            if prev is not None and prev - p["health"] >= 15:
                self.monitor("pets", "warn", f"{p['name']} lost {prev - p['health']:.0f} health quickly",
                             f"Strain {p['strain']:.0f}, hunger {p['hunger']:.0f}, energy {p['energy']:.0f}, "
                             f"{p['shifts']} shifts a day (safe ~{self.safe_shifts(p['species'], p['job']) if p['job'] else '?'}).")
            if p["job"] and p["shifts"] > self.safe_shifts(p["species"], p["job"]) * 1.5:
                self.monitor("pets", "info", f"{p['name']} is scheduled well past its safe shifts",
                             f"{p['shifts']} shifts a day; about {self.safe_shifts(p['species'], p['job'])} is safe.")
        self.db.set("monitor_pet_health", now)

    def monitor_overview(self, track=None, limit=150):
        q, args = "SELECT * FROM monitor", []
        if track in ("pets", "money", "model"):
            q += " WHERE track=?"
            args.append(track)
        rows = [dict(r) for r in self.db.q(q + " ORDER BY id DESC LIMIT ?", tuple(args + [limit]))]
        day = time.time() - 86400
        counts = {}
        for r in self.db.q("SELECT track, level, COUNT(*) AS n FROM monitor WHERE ts > ? GROUP BY track, level", (day,)):
            counts.setdefault(r["track"], {})[r["level"]] = r["n"]
        hist = self.db.get("monitor_turns") or []
        return {"entries": rows, "counts": counts,
                "model": {"recent_turns": hist, "calls_today": self._usage().get("llm_calls", 0),
                          "call_limit": self.cfg["limits"]["llm_calls_per_day"],
                          "avg_turn_seconds": round(sum(h["s"] for h in hist) / len(hist), 1) if hist else None,
                          "model": self.cfg.get("ollama", {}).get("model")}}
