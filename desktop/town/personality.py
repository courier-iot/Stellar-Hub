"""v0.14: a personality that develops.

Traits are numbers; this gives the resident a character to go with them:
1. "Who I am": a short statement of its values. It can rewrite it, but only with a reason ("I used to think…").
2. Tastes: favourites and dislikes, each with a reason, that strengthen or fade over time.
3. Core memories: up to 7 formative moments it pins (personality.max_core in config.json). They're shown to it
   whenever it decides what to do. Ones it lets go of are kept in a "once core" archive, and can come back.
4. Bonds: how it feels about its creator, each pet and the regular visitors (trust, fondness, in-jokes).
5. Quirks: habits and phrases it notices in its own behaviour and keeps (or drops).
6. Hopes and a fear: what it's working towards, and something it's nervous about and slowly facing.
7. A timeline of how it has changed, shown on the dashboard.
8. A self-check: "did I act like myself?" If it's drifting, it's reminded who it is.

It all changes in one "personality review" every few nights while it sleeps (one AI call), so it grows slowly
and steadily, like a person, instead of lurching from turn to turn.
"""
import json
import time

MAX_TASTES, MAX_CORE, MAX_QUIRKS, MAX_HOPES = 12, 7, 6, 3
NO_PERSONA = {"exam", "grade", "quiz_grade", "code", "machine_design", "project_plan", "persona_review", "pet",
              "identity", "summarize_chat"}

REVIEW = """You are {name}, looking back over the last few days to understand yourself a little better.
Change things slowly and only for real reasons drawn from what actually happened. Keep what still fits.
Reply ONLY with JSON:
{{"statement": {{"text": "who you are and what you value, first person, 3-5 sentences, or the same as now", "reason": "why it changed, or empty"}},
 "tastes": [{{"thing": "...", "kind": "favourite|dislike", "about": "music|book|food|place|plant|season|activity|other", "why": "...", "strength": 1-10}}],
 "core_memories": [{{"id": <memory id from the recent or once-core lists>, "why": "why this moment shaped you"}}],
 "let_go": [{{"id": <a current core memory id you no longer keep at the centre>, "why": "why it matters less now"}}],
 "bonds": [{{"who": "<a name from the list>", "trust": -2 to 2, "fondness": -2 to 2, "note": "how you feel now, short", "in_joke": "optional"}}],
 "quirks": ["a habit or phrase you've noticed in yourself"],
 "hopes": [{{"hope": "...", "progress": "what you did towards it lately"}}],
 "fear": {{"fear": "...", "facing": "how you're facing it, or empty"}},
 "self_check": {{"like_myself": true, "note": "did you act like yourself? if not, what pulled you off course"}},
 "changes": ["each real change in one short line, for your timeline, e.g. 'Grew fonder of Moss the tortoise after the storm'"]}}
Rules: tastes are the full updated list (at most 12); core_memories is the full list, at most {max_core}, only ids from
the lists (you may bring back a once-core memory); quirks at most 6;
hopes at most 3. Write the statement in your own voice."""


def _int(v, default):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


class PersonalityMixin:
    # ------------------------------------------------------------ state
    def persona(self):
        p = self.db.get("persona") or {}
        p.setdefault("statement", {"text": "", "ts": None, "history": []})
        for k, d in (("tastes", []), ("core", []), ("core_archive", []), ("bonds", {}), ("quirks", []), ("hopes", []), ("fear", {}),
                     ("checks", []), ("timeline", [])):
            p.setdefault(k, d)
        return p

    def _save_persona(self, p):
        p["timeline"] = p["timeline"][-300:]
        p["checks"] = p["checks"][-30:]
        p["core_archive"] = p["core_archive"][-100:]
        p["statement"]["history"] = p["statement"]["history"][-20:]
        self.db.set("persona", p)

    def persona_log(self, text, kind="change"):
        p = self.persona()
        p["timeline"].append({"ts": time.time(), "kind": kind, "text": str(text)[:300]})
        self._save_persona(p)

    # ------------------------------------------------------------ what it's shown
    def persona_note(self, task=None):
        """A compact WHO YOU ARE block added to its prompts."""
        if task in NO_PERSONA or not self.db.get("name"):
            return ""
        p = self.persona()
        lines = []
        if p["statement"]["text"]:
            lines.append(f"Who you are, in your words: {p['statement']['text']}")
        if p["tastes"]:
            fav = [t for t in p["tastes"] if t.get("kind") == "favourite"]
            bad = [t for t in p["tastes"] if t.get("kind") == "dislike"]
            if fav:
                lines.append("You love: " + "; ".join(f"{t['thing']} ({t.get('why', '')[:60]})" for t in fav[:6]))
            if bad:
                lines.append("You dislike: " + "; ".join(f"{t['thing']}" for t in bad[:4]))
        if p["core"]:
            lines.append("Moments that shaped you: " + " | ".join(f"{c['text'][:110]} ({c['why'][:60]})" for c in p["core"]))
        if p["bonds"]:
            lines.append("How you feel about others: " + "; ".join(
                f"{who}: {b.get('note', '')[:70]}" + (f" (in-joke: {b['in_jokes'][-1][:40]})" if b.get("in_jokes") else "")
                for who, b in list(p["bonds"].items())[:6]))
        if p["quirks"]:
            lines.append("Your quirks: " + "; ".join(p["quirks"]))
        if p["hopes"]:
            lines.append("You hope to: " + "; ".join(h["hope"] for h in p["hopes"]))
        if p["fear"].get("fear"):
            lines.append(f"You're nervous about: {p['fear']['fear']}" + (f" (facing it by: {p['fear']['facing']})" if p["fear"].get("facing") else ""))
        last = p["checks"][-1] if p["checks"] else None
        if last and not last.get("like_myself", True):
            lines.append(f"Lately you drifted from yourself ({last.get('note', '')[:120]}). Come back to who you are.")
        if not lines:
            return ""
        return "\n\nWHO YOU ARE (let this guide you, naturally):\n- " + "\n- ".join(lines)

    # ------------------------------------------------------------ the review
    def max_core(self):
        try:
            n = int(self.cfg.get("personality", {}).get("max_core", MAX_CORE))
        except (TypeError, ValueError):
            n = MAX_CORE
        return max(3, min(15, n))

    def personality_due(self):
        days = float(self.cfg.get("personality", {}).get("review_days", 3))
        last = self.persona().get("last_review") or 0
        return time.time() - last >= days * 86400

    def _review_context(self):
        p = self.persona()
        since = max((p.get("last_review") or 0), time.time() - 7 * 86400)
        mems = self.db.q("SELECT id, kind, content, importance FROM memories WHERE ts > ? AND kind != 'dream' "
                         "ORDER BY importance DESC, id DESC LIMIT 45", (since,))
        acts = self.db.q("SELECT action, building, COUNT(*) AS n FROM turns WHERE ts > ? GROUP BY action, building "
                         "ORDER BY n DESC LIMIT 10", (time.time() - 14 * 86400,))
        others = [self.creator] + [f"{x['name']} (your {x['species'].replace('_', ' ')})" for x in self.pets()]
        try:
            from .extras import VISITORS
            met = {r["visitor"] for r in self.db.q("SELECT DISTINCT visitor FROM visits")}
            others += [VISITORS[v]["name"] + " (a visitor)" for v in met if v in VISITORS]
        except Exception:
            pass
        cur = {k: p[k] for k in ("tastes", "quirks", "hopes", "fear")}
        cur["statement"] = p["statement"]["text"]
        cur["core_memories"] = [{"id": c["id"], "why": c["why"]} for c in p["core"]]
        cur["once_core"] = [{"id": c["id"], "text": c["text"][:140], "let_go_because": c.get("retire_why", "")}
                            for c in p["core_archive"][-10:]]
        cur["bonds"] = {k: {"trust": v.get("trust"), "fondness": v.get("fondness"), "note": v.get("note")} for k, v in p["bonds"].items()}
        return (f"YOUR PERSONALITY FILE:\n{self.personality()[:1500]}\n\nTRAITS (0-100): {self.traits_text()}\n\n"
                f"HOW YOU SEE YOURSELF NOW:\n{json.dumps(cur, ensure_ascii=False)[:3500]}\n\n"
                "WHAT YOU'VE DONE MOST (last 2 weeks): " + "; ".join(f"{a['action']} at {a['building']} x{a['n']}" for a in acts) +
                "\n\nPEOPLE AND CREATURES IN YOUR LIFE: " + ", ".join(others) +
                "\n\nRECENT MEMORIES (id: text):\n" + "\n".join(f"{m['id']}: [{m['kind']}] {m['content'][:220]}" for m in mems))

    def personality_review(self, force=False):
        """Grows the personality a little. Returns the timeline lines it added (or None if it wasn't due)."""
        if not force and not self.personality_due():
            return None
        out = self.ask(REVIEW.format(name=self.name, max_core=self.max_core()), self._review_context(), "persona_review")
        return self.apply_review(out if isinstance(out, dict) else {})

    def apply_review(self, out):
        p = self.persona()
        now = time.time()
        added = []
        st = out.get("statement") if isinstance(out.get("statement"), dict) else {}
        text = str(st.get("text", "")).strip()[:900]
        if text and text != p["statement"]["text"]:
            if p["statement"]["text"]:
                p["statement"]["history"].append({"ts": p["statement"]["ts"], "text": p["statement"]["text"],
                                                  "reason": str(st.get("reason", ""))[:300]})
                added.append("Rewrote who I am" + (f": {st.get('reason')}" if st.get("reason") else ""))
            else:
                added.append("Wrote down who I am for the first time")
            p["statement"].update({"text": text, "ts": now})
        if isinstance(out.get("tastes"), list):
            old = {t["thing"].lower() for t in p["tastes"]}
            tastes = []
            for t in out["tastes"][:MAX_TASTES]:
                if isinstance(t, dict) and str(t.get("thing", "")).strip():
                    tastes.append({"thing": str(t["thing"]).strip()[:80],
                                   "kind": "dislike" if t.get("kind") == "dislike" else "favourite",
                                   "about": str(t.get("about", "other"))[:20], "why": str(t.get("why", ""))[:200],
                                   "strength": max(1, min(10, _int(t.get("strength"), 5))),
                                   "since": next((x.get("since") for x in p["tastes"] if x["thing"].lower() == str(t["thing"]).strip().lower()), now)})
            new = [t for t in tastes if t["thing"].lower() not in old]
            for t in new[:3]:
                added.append(f"Found a new {'favourite' if t['kind'] == 'favourite' else 'dislike'}: {t['thing']}")
            p["tastes"] = tastes
        if isinstance(out.get("core_memories"), list):
            core = []
            limit = self.max_core()
            for c in out["core_memories"][:limit]:
                try:
                    mid = int(c.get("id"))
                except (TypeError, ValueError, AttributeError):
                    continue
                row = self.db.q("SELECT content FROM memories WHERE id=?", (mid,))
                if row and mid not in {x["id"] for x in core}:
                    core.append({"id": mid, "text": row[0]["content"][:300], "why": str(c.get("why", ""))[:200],
                                 "since": next((x["since"] for x in p["core"] if x["id"] == mid), now)})
            reasons = {}
            for g in (out.get("let_go") or []):
                if isinstance(g, dict):
                    reasons[_int(g.get("id"), -1)] = str(g.get("why", ""))[:200]
            archived = {x["id"] for x in p["core_archive"]}
            for c in [c for c in core if c["id"] not in {x["id"] for x in p["core"]}][:3]:
                added.append(("Remembered again: " if c["id"] in archived else "A moment became part of me: ") + c["text"][:90])
            kept = {c["id"] for c in core}
            p["core_archive"] = [x for x in p["core_archive"] if x["id"] not in kept]       # brought back
            for old in p["core"]:
                if old["id"] not in kept:                                                  # let go: archived, not lost
                    p["core_archive"].append({**old, "retired": now, "retire_why": reasons.get(old["id"], "")})
                    added.append(f"Let go of a core memory: {old['text'][:80]}")
            p["core"] = core
        if isinstance(out.get("bonds"), list):
            for b in out["bonds"][:10]:
                if not isinstance(b, dict) or not str(b.get("who", "")).strip():
                    continue
                who = str(b["who"]).split(" (")[0].strip()[:40]
                cur = p["bonds"].get(who, {"trust": 50, "fondness": 50, "note": "", "in_jokes": []})
                for k in ("trust", "fondness"):
                    d = max(-2, min(2, _int(b.get(k), 0))) * 3
                    cur[k] = max(0, min(100, cur.get(k, 50) + d))
                    if abs(d) >= 6:
                        added.append(f"{'Grew' if d > 0 else 'Lost some'} {'trust in' if k == 'trust' else 'fondness for'} {who}")
                if b.get("note"):
                    cur["note"] = str(b["note"])[:200]
                if b.get("in_joke") and str(b["in_joke"]) not in cur.get("in_jokes", []):
                    cur.setdefault("in_jokes", []).append(str(b["in_joke"])[:120])
                    cur["in_jokes"] = cur["in_jokes"][-5:]
                    added.append(f"A new in-joke with {who}")
                p["bonds"][who] = cur
        if isinstance(out.get("quirks"), list):
            q = [str(x).strip()[:120] for x in out["quirks"] if str(x).strip()][:MAX_QUIRKS]
            for x in [x for x in q if x not in p["quirks"]][:2]:
                added.append(f"Noticed a quirk: {x}")
            p["quirks"] = q
        if isinstance(out.get("hopes"), list):
            p["hopes"] = [{"hope": str(h.get("hope", ""))[:160], "progress": str(h.get("progress", ""))[:200]}
                          for h in out["hopes"][:MAX_HOPES] if isinstance(h, dict) and h.get("hope")]
        if isinstance(out.get("fear"), dict) and out["fear"].get("fear"):
            if out["fear"]["fear"] != p["fear"].get("fear") and p["fear"].get("fear"):
                added.append(f"No longer as afraid of {p['fear']['fear'][:60]}")
            p["fear"] = {"fear": str(out["fear"]["fear"])[:160], "facing": str(out["fear"].get("facing", ""))[:200]}
        chk = out.get("self_check") if isinstance(out.get("self_check"), dict) else None
        if chk:
            p["checks"].append({"ts": now, "like_myself": bool(chk.get("like_myself", True)), "note": str(chk.get("note", ""))[:300]})
            if not chk.get("like_myself", True):
                added.append("Felt I wasn't quite myself: " + str(chk.get("note", ""))[:120])
        for c in (out.get("changes") or [])[:6]:
            if isinstance(c, str) and c.strip() and c.strip() not in added:
                added.append(c.strip()[:200])
        p["last_review"] = now
        for a in added:
            p["timeline"].append({"ts": now, "kind": "change", "text": a})
        self._save_persona(p)
        if added:
            self.mem.add("reflection", "Thinking about who I'm becoming: " + "; ".join(added[:4]), "home", 6)
            self.add_event("persona", f"🌱 {self.name} grew a little", "; ".join(added[:3])[:300])
        return added

    def persona_view(self):
        p = self.persona()
        return {"statement": p["statement"], "tastes": p["tastes"], "core": p["core"], "max_core": self.max_core(),
                "core_archive": list(reversed(p["core_archive"][-30:])), "bonds": p["bonds"],
                "quirks": p["quirks"], "hopes": p["hopes"], "fear": p["fear"], "checks": p["checks"][-5:],
                "timeline": list(reversed(p["timeline"][-80:])), "last_review": p.get("last_review"),
                "review_days": self.cfg.get("personality", {}).get("review_days", 3)}
