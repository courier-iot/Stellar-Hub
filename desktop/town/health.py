"""v0.14.1: hub health. How fast the model answers, how many AI calls it makes, what's using the disk, and how
training has gone over time. Shown on the Monitor tab."""
import os
import time

DAYS = 14


def folder_size(path, limit_s=4.0):
    total, t0 = 0, time.time()
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
        if time.time() - t0 > limit_s:
            break
    return total


class HealthMixin:
    def note_call(self, task, seconds, ok):
        """Records one AI call: per day, and the last 50 for a rolling average."""
        try:
            st = self.db.get("llm_stats") or {"days": {}, "recent": []}
            day = time.strftime("%Y-%m-%d")
            d = st["days"].setdefault(day, {"calls": 0, "secs": 0.0, "slow": 0, "errors": 0, "slowest": 0.0})
            d["calls"] += 1
            d["secs"] = round(d["secs"] + seconds, 2)
            d["slowest"] = round(max(d["slowest"], seconds), 1)
            d["slow"] += seconds > 60
            d["errors"] += not ok
            st["recent"] = (st["recent"] + [[round(time.time()), task, round(seconds, 2), ok]])[-50:]
            for k in sorted(st["days"])[:-DAYS]:
                del st["days"][k]
            self.db.set("llm_stats", st)
        except Exception:
            pass

    def disk_use(self):
        cache = getattr(self, "_disk_cache", None)
        if cache and time.time() - cache[0] < 600:
            return cache[1]
        root = self.data_dir
        parts = {"Training (toolkit, base model, runs)": os.path.join(root, "trainer"),
                 "Audio (logs, shows, chats)": os.path.join(root, "audio"),
                 "Voice (Piper)": os.path.join(root, "piper")}
        out = [{"label": k, "bytes": folder_size(v)} for k, v in parts.items() if os.path.exists(v)]
        db_path = os.path.join(root, "town.db")
        if os.path.exists(db_path):
            out.append({"label": "Memories and colony (database)", "bytes": os.path.getsize(db_path)})
        everything = folder_size(root, 8.0)
        out.append({"label": "Everything else", "bytes": max(0, everything - sum(x["bytes"] for x in out))})
        try:
            import shutil
            free = shutil.disk_usage(root).free
        except OSError:
            free = None
        res = {"parts": sorted(out, key=lambda x: -x["bytes"]), "total": everything, "free": free}
        self._disk_cache = (time.time(), res)
        return res

    def health_overview(self):
        st = self.db.get("llm_stats") or {"days": {}, "recent": []}
        days = []
        for i in range(DAYS - 1, -1, -1):
            day = time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400))
            d = st["days"].get(day, {})
            days.append({"day": day, "calls": d.get("calls", 0), "avg_s": round(d.get("secs", 0) / d["calls"], 1) if d.get("calls") else None,
                         "slow": d.get("slow", 0), "errors": d.get("errors", 0), "slowest": d.get("slowest")})
        recent = st["recent"]
        avg = round(sum(r[2] for r in recent) / len(recent), 1) if recent else None
        by_task = {}
        for r in recent:
            by_task.setdefault(r[1] or "other", []).append(r[2])
        history = [{"n": h.get("n"), "ts": h.get("ended") or h.get("started"), "before": h.get("before"), "after": h.get("after"),
                    "ok": h.get("ok"), "examples": h.get("examples")} for h in (self.db.get("train_history") or [])]
        return {"model": getattr(self.llm, "model", None), "model_status": self.model_status,
                "avg_s": avg, "by_task": {k: round(sum(v) / len(v), 1) for k, v in sorted(by_task.items(), key=lambda t: -len(t[1]))[:8]},
                "today": self._usage().get("llm_calls", 0), "limit": self.cfg["limits"]["llm_calls_per_day"],
                "days": days, "disk": self.disk_use(), "training": history[-20:]}
