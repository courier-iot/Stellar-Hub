"""Pets: small helper creatures the resident adopts at the Pet Shop and trains to do one job each.

Every pet has a species with a specialization (the jobs it's good at), a lifespan, active hours (day or night),
and needs: energy, hunger, happiness and health. The resident decides each pet's job and how many shifts a day
it works. Too many shifts and the pet overworks: strain builds up, it gets sick, then injured, then critical.
A critical pet can be rescued at a steep price (debt is allowed), or the Colony Welfare Office takes it away
and fines the resident. Pets also grow old and pass away peacefully at the end of their lifespan.

Simple jobs are plain code. Medium and complex jobs use a small "pet brain" model on the same Ollama, and only
run while the computer is idle, so pets never slow down the resident or your games."""
import ctypes
import json
import os
import random
import shutil
import subprocess
import threading
import time
import urllib.request

from . import sprites
from .osutil import IS_WIN, NO_WINDOW

SPECIES = {
    "orbit_moth": {"name": "Orbit Moth", "price": 60, "special": "repetitive", "days": (10, 16), "active": "night",
                   "hunger": 4.0, "stamina": 1.0, "food": "moon nectar",
                   "about": "a tiny moth with planet-ring wings. Brilliant at small, repetitive tasks; short-lived."},
    "drone_cat": {"name": "Drone Cat", "price": 120, "special": "watch", "days": (30, 45), "active": "night",
                  "hunger": 3.0, "stamina": 1.1, "food": "fish crisps",
                  "about": "a sleek cat with a tiny rotor. A natural watcher: keeps an eye on the night and the markets."},
    "rover_pup": {"name": "Rover Pup", "price": 150, "special": "fetch", "days": (25, 40), "active": "day",
                  "hunger": 4.5, "stamina": 1.3, "food": "bolt biscuits",
                  "about": "an eager pup on little wheels. Loves fetching: finds things, scouts topics on the uplink."},
    "comet_finch": {"name": "Comet Finch", "price": 110, "special": "words", "days": (15, 25), "active": "day",
                    "hunger": 3.5, "stamina": 0.9, "food": "star seed",
                    "about": "a bright bird with a comet tail. Good with words: drafts logs, gives writing notes."},
    "crystal_snail": {"name": "Crystal Snail", "price": 200, "special": "careful", "days": (60, 90), "active": "any",
                      "hunger": 1.5, "stamina": 0.7, "food": "mineral moss",
                      "about": "a slow snail with a glowing crystal shell. Careful, long jobs; lives a very long time."},
    "nebula_axolotl": {"name": "Nebula Axolotl", "price": 180, "special": "care", "days": (35, 50), "active": "night",
                       "hunger": 3.0, "stamina": 1.0, "food": "plankton puffs",
                       "about": "a pink axolotl with nebula frills. A carer: tends plants and other pets."},
}

# job: (complexity 1-3, specialization, what it does)
JOBS = {
    "water_plants": (1, "care", "waters greenhouse plants that are due"),
    "tidy_curios": (1, "repetitive", "sorts the curio collection and points out trade-ups"),
    "fetch_curio": (1, "fetch", "roams the colony and sometimes brings back a curio or a few credits"),
    "night_watch": (1, "watch", "keeps watch and reports what happened while the resident slept"),
    "exchange_watch": (2, "watch", "watches the Exchange's wanted board for curios you could sell"),
    "tend_pets": (2, "care", "feeds and plays with the other pets a little"),
    "draft_log": (2, "words", "drafts a colony log from today's events (needs the pet brain)"),
    "proofread": (2, "words", "reads the newest writing and suggests one improvement (needs the pet brain)"),
    "scout_topic": (3, "fetch", "searches the uplink for one of today's goals and saves what it finds"),
    "summarize_memories": (3, "careful", "condenses old memories into a tidy note (needs the pet brain)"),
}
COST = {1: 10, 2: 25, 3: 45}
BRAIN_JOBS = {"draft_log", "proofread", "summarize_memories"}
MAX_PETS = 4
FOOD_PRICE = 5
RETRAIN_PRICE = 30
TREAT_PRICE = {"sick": 25, "injured": 60}
CRITICAL_HOURS = 24
REGEN_ON, REGEN_OFF = 4.0, 9.0          # energy per hour: on shift / resting


# ---------------------------------------------------------------- art
def pet_frames(species):
    """Two 12x12 frames per species."""
    out = []
    for f in (0, 1):
        c = sprites.Canvas(12, 12)
        if species == "orbit_moth":
            c.rect(5, 4, 2, 6, "o"); c.px(5, 3, "k"); c.px(6, 3, "k"); c.px(4, 2, "S"); c.px(7, 2, "S")
            wy = 3 if f else 5
            c.rect(1, wy, 4, 4, "P"); c.rect(7, wy, 4, 4, "P"); c.px(2, wy + 1, "y"); c.px(9, wy + 1, "y")
            c.rect(0, wy + 2, 12, 1, "p")
        elif species == "drone_cat":
            c.rect(3, 6, 7, 4, "g"); c.rect(2, 3, 5, 4, "g"); c.px(2, 2, "g"); c.px(6, 2, "g")
            c.rect(3, 4, 3, 1, "c"); c.rect(9, 5 - f, 2, 1, "g"); c.px(10, 4 - f, "g")
            c.rect(4, 10, 1, 2, "G"); c.rect(8, 10, 1, 2, "G")
            c.rect(2 + f * 2, 0, 3, 1, "S"); c.px(4, 1, "S")
        elif species == "rover_pup":
            c.rect(3, 5, 7, 4, "Y"); c.rect(7, 2, 4, 4, "Y"); c.px(9, 3, "k"); c.rect(10, 4, 2, 1, "o")
            c.rect(7, 1, 1, 2, "O"); c.px(2, 4 + f, "Y")
            c.disc(4, 10, 1, "k"); c.disc(8, 10, 1, "k"); c.px(4, 10, "S" if f else "g"); c.px(8, 10, "g" if f else "S")
        elif species == "comet_finch":
            c.disc(6, 6, 3, "c"); c.rect(8, 4, 2, 2, "c"); c.px(9, 4, "k"); c.px(10, 5, "y")
            c.rect(4, 6 - f, 3, 2, "C")
            for i in range(4):
                c.px(2 - i // 2, 7 + i // 2, "w" if i % 2 else "c")
            c.px(5, 9, "o"); c.px(7, 9, "o")
        elif species == "crystal_snail":
            c.rect(1, 8, 10, 2, "s"); c.px(10 + f, 7, "s"); c.px(11, 6, "S")
            c.disc(5, 5, 3, "c"); c.disc(5, 5, 2, "p"); c.px(5, 4, "w")
        elif species == "nebula_axolotl":
            c.rect(2, 6, 8, 3, "m"); c.rect(7, 4, 4, 4, "m"); c.px(9, 5, "k"); c.px(10, 7, "p")
            c.px(7, 3, "P"); c.px(8, 2 + f, "P"); c.px(10, 3, "P"); c.px(11, 2 + f, "P")
            c.rect(0, 7 - f, 2, 1, "m"); c.px(3, 9, "m"); c.px(7, 9, "m")
        out.append(c.rows())
    return out


# ---------------------------------------------------------------- spare-hardware check
class _FILETIME(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]


def _cpu_times():
    if IS_WIN:
        idle, kernel, user = _FILETIME(), _FILETIME(), _FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        val = lambda t: (t.hi << 32) | t.lo
        return val(idle), val(kernel) + val(user)     # kernel time includes idle
    try:
        with open("/proc/stat") as f:
            parts = [int(x) for x in f.readline().split()[1:]]
        return parts[3] + parts[4], sum(parts)
    except (OSError, ValueError, IndexError):
        return None


def cpu_busy(sample=1.0):
    a = _cpu_times()
    time.sleep(sample)
    b = _cpu_times()
    if not a or not b or b[1] == a[1]:
        return 0.0
    return 100.0 * (1 - (b[0] - a[0]) / (b[1] - a[1]))


def gpu_busy():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return 0.0
    try:
        out = subprocess.run([exe, "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], capture_output=True,
                             text=True, timeout=10, creationflags=NO_WINDOW).stdout
        return max(float(x) for x in out.split()) if out.strip() else 0.0
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


# ---------------------------------------------------------------- the mixin
class PetsMixin:
    def pets(self, alive_only=True):
        q = "SELECT * FROM pets WHERE status IN ('ok','sick','injured','critical')" if alive_only else "SELECT * FROM pets"
        return [dict(p) for p in self.db.q(q + " ORDER BY id")]

    def pet(self, pid):
        try:
            r = self.db.q("SELECT * FROM pets WHERE id=?", (int(pid),))
        except (TypeError, ValueError):
            return None
        return dict(r[0]) if r else None

    def _pet_save(self, p):
        self.db.x("UPDATE pets SET energy=?, hunger=?, happiness=?, health=?, strain=?, status=?, job=?, shifts=?, "
                  "runs_today=?, run_day=?, last_run=?, rest_until=?, critical_since=?, updated=? WHERE id=?",
                  (p["energy"], p["hunger"], p["happiness"], p["health"], p["strain"], p["status"], p["job"], p["shifts"],
                   p["runs_today"], p["run_day"], p["last_run"], p["rest_until"], p["critical_since"], p["updated"], p["id"]))

    def _pet_log(self, p, text, imp=3, memory=True):
        self.db.x("INSERT INTO pet_log(ts, pet_id, text) VALUES(?,?,?)", (time.time(), p["id"], text[:600]))
        if memory:
            self.mem.add("observation", f"{p['name']} ({SPECIES[p['species']]['name']}): {text}", "pet_shop", imp)

    def on_shift(self, p, hour=None):
        hour = time.localtime().tm_hour if hour is None else hour
        act = SPECIES[p["species"]]["active"]
        if act == "any":
            return True
        day = 7 <= hour < 19
        return day if act == "day" else not day

    def pet_cost(self, p, job=None):
        job = job or p["job"]
        cx, spec, _ = JOBS[job]
        sp = SPECIES[p["species"]]
        mult = 0.6 if spec == sp["special"] else 1.3
        age = self.pet_age_stage(p)
        return COST[cx] * mult / sp["stamina"] * (1.3 if age == "elder" else 1.0)

    def pet_age_stage(self, p):
        frac = (time.time() - p["born"]) / (p["lifespan_days"] * 86400)
        return "baby" if frac < 0.12 else "elder" if frac > 0.8 else "adult"

    def safe_shifts(self, species, job):
        """Roughly how many shifts a day a healthy adult can do without strain."""
        sp = SPECIES[species]
        hours = 24 if sp["active"] == "any" else 12
        regen = REGEN_ON * hours + REGEN_OFF * (24 - hours)
        cx, spec, _ = JOBS[job]
        cost = COST[cx] * (0.6 if spec == sp["special"] else 1.3) / sp["stamina"]
        return max(1, int(regen / cost))

    # ------------------------------------------------------------ time passing
    def update_pets(self):
        now = time.time()
        for p in self.pets():
            dt = max(0.0, min(48.0, (now - (p["updated"] or now)) / 3600))
            if dt < 0.02:
                continue
            sp = SPECIES[p["species"]]
            if now - p["born"] > p["lifespan_days"] * 86400:          # a long life, well lived
                p["status"] = "passed"
                self._pet_save(p)
                self._pet_log(p, f"passed away peacefully of old age after {p['lifespan_days']:.0f} days.", 8)
                self.add_event("pet", f"🕯 {p['name']} passed away", f"{p['name']} the {sp['name']} lived a full life.")
                continue
            resting = (not self.on_shift(p)) or p["rest_until"] > now
            p["energy"] = min(100.0, p["energy"] + dt * (REGEN_OFF if resting else REGEN_ON) * (0.5 if p["status"] == "sick" else 1))
            p["hunger"] = min(100.0, p["hunger"] + dt * sp["hunger"])
            p["happiness"] = max(0.0, p["happiness"] - dt * 1.5)
            p["strain"] = max(0.0, p["strain"] - dt * (2.0 if resting else 0.5))
            dh = 0.0
            if p["hunger"] > 70:
                dh -= dt * (p["hunger"] - 70) / 12
            if p["strain"] > 30:
                dh -= dt * (p["strain"] - 30) / 15
            if p["happiness"] < 15:
                dh -= dt * 0.5
            if dh == 0 and p["hunger"] < 70 and p["strain"] < 30:
                dh = dt * 2.0
            cap = 80.0 if self.pet_age_stage(p) == "elder" else 100.0
            p["health"] = max(0.0, min(cap, p["health"] + dh))
            p["updated"] = now
            self._pet_status(p)
            if p["status"] == "critical" and now - p["critical_since"] > CRITICAL_HOURS * 3600:
                self._pet_taken(p)
                continue
            if p["health"] <= 0:
                self._pet_taken(p)
                continue
            self._pet_save(p)

    def _pet_status(self, p):
        old = p["status"]
        h = p["health"]
        new = "ok" if h >= 60 else "sick" if h >= 30 else "injured" if h >= 10 else "critical"
        if old == "critical" and new != "critical" and h < 30:
            new = "critical"         # only a rescue gets a pet out of critical
        p["status"] = new
        if new == old:
            return
        sp = SPECIES[p["species"]]
        if new == "critical":
            p["critical_since"] = time.time()
            price = self.rescue_price(p)
            self._pet_log(p, f"is in critical condition! I have {CRITICAL_HOURS} hours to rescue it at the Pet Shop "
                             f"({price} credits, even if it puts me in debt), or the Welfare Office will take it away and fine me.", 9)
            self.add_event("pet", f"🚨 {p['name']} is in critical condition",
                           f"{p['name']} the {sp['name']} was overworked or neglected. Rescue costs {price} credits; "
                           f"otherwise it's taken away in {CRITICAL_HOURS} hours with a {self.pet_fine(p)} credit fine.")
        elif new in ("sick", "injured") and old == "ok":
            self._pet_log(p, f"is {new}. It needs rest, food and maybe the clinic (treat_pet).", 6)
            self.add_event("pet", f"🤒 {p['name']} is {new}", f"{p['name']} the {sp['name']} needs care.")

    def rescue_price(self, p):
        return SPECIES[p["species"]]["price"] * 3 + 100

    def pet_fine(self, p):
        return SPECIES[p["species"]]["price"] * 2

    def charge(self, amount, reason):
        """Takes credits even if it means going into debt (fines and emergencies)."""
        self.earn(-int(amount), reason)

    def _pet_taken(self, p):
        sp = SPECIES[p["species"]]
        fine = self.pet_fine(p)
        p["status"] = "taken"
        self._pet_save(p)
        self.charge(fine, f"Welfare Office fine for neglecting {p['name']}")
        self._pet_log(p, f"was taken away by the Colony Welfare Office because I didn't save it. I was fined {fine} credits. "
                         f"I have to take better care of the ones who depend on me.", 10)
        self.add_event("pet", f"⚖️ {p['name']} was taken away", f"The Welfare Office took {p['name']} the {sp['name']} "
                                                                   f"and fined {self.name} {fine} credits.")

    # ------------------------------------------------------------ the runner (spare hardware)
    def pet_brain(self):
        """The small model pets think with, on the same Ollama. None if it isn't downloaded yet."""
        from .llm import OllamaLLM
        pc = self.cfg.get("pets", {})
        model = pc.get("model", "qwen3:0.6b")
        if not hasattr(self, "_pet_llm") or self._pet_llm.model != model:
            o = self.cfg.get("ollama", {})
            self._pet_llm = OllamaLLM(o.get("url", "http://127.0.0.1:11434"), model, 0.7, timeout=240, num_ctx=2048)
            self._pet_brain_ok = None
        if self._pet_brain_ok is None or time.time() - self._pet_brain_ok[1] > 600:
            try:
                names = self._pet_llm.installed()
                ok = any(n == model or n == model + ":latest" or n.split(":")[0] == model for n in names)
            except Exception:
                ok = False
            self._pet_brain_ok = (ok, time.time())
        return self._pet_llm if self._pet_brain_ok[0] else None

    def pull_pet_brain(self):
        if getattr(self, "_brain_pull", {}).get("running"):
            return self._brain_pull
        model = self.cfg.get("pets", {}).get("model", "qwen3:0.6b")
        self._brain_pull = {"running": True, "step": f"Downloading {model}…"}

        def work():
            try:
                url = self.cfg.get("ollama", {}).get("url", "http://127.0.0.1:11434").rstrip("/") + "/api/pull"
                req = urllib.request.Request(url, data=json.dumps({"model": model, "stream": False}).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=3600) as r:
                    out = json.loads(r.read().decode() or "{}")
                self._pet_brain_ok = None
                self._brain_pull = {"running": False, "step": f"{model} is ready ✓" if out.get("status") == "success" else str(out)[:200]}
            except Exception as e:
                self._brain_pull = {"running": False, "step": "Download failed", "error": str(e)}
        threading.Thread(target=work, daemon=True).start()
        return self._brain_pull

    def hardware_idle(self):
        pc = self.cfg.get("pets", {})
        if getattr(self, "busy", False):
            return False, "the resident is thinking"
        cpu = cpu_busy(1.0)
        if cpu > pc.get("max_cpu", 55):
            return False, f"the computer is busy (CPU {cpu:.0f}%)"
        gpu = gpu_busy()
        if gpu > pc.get("max_gpu", 30):
            return False, f"the graphics card is busy ({gpu:.0f}%)"
        return True, "idle"

    def pet_tick(self):
        """Runs every few minutes in the background: time passes for pets, and at most one due job runs."""
        if not self.cfg.get("pets", {}).get("enabled", True):
            return
        with self.pet_lock:
            self.update_pets()
            now = time.time()
            today = self._today()
            due = []
            for p in self.pets():
                if not p["job"] or p["status"] in ("injured", "critical") or p["rest_until"] > now or not self.on_shift(p):
                    continue
                if p["run_day"] != today:
                    p["runs_today"], p["run_day"] = 0, today
                    self._pet_save(p)
                if p["runs_today"] >= p["shifts"]:
                    continue
                gap = (12 if SPECIES[p["species"]]["active"] != "any" else 24) * 3600 / max(1, p["shifts"])
                if now - p["last_run"] < gap * 0.8:
                    continue
                due.append(p)
            if not due:
                self.pet_runner_note = "no jobs due"
                return
            p = min(due, key=lambda q: q["last_run"])
            if JOBS[p["job"]][0] >= 2:
                ok, why = self.hardware_idle()
                if not ok:
                    self.pet_runner_note = f"waiting: {why}"
                    return
            self.pet_runner_note = f"{p['name']} is working"
            self.run_pet_job(p)

    def run_pet_job(self, p, forced=False):
        cost = self.pet_cost(p)
        if p["energy"] >= cost:
            p["energy"] -= cost
            strained = 0
        else:                      # overworking: the missing energy comes out of its body
            deficit = cost - p["energy"]
            p["energy"] = 0.0
            p["strain"] = min(100.0, p["strain"] + deficit * 1.5)
            p["health"] = max(0.0, p["health"] - deficit / 5)
            strained = deficit
        p["last_run"] = time.time()
        p["runs_today"] += 1
        if p["status"] == "sick" and random.random() < 0.4:
            result = "tried to work but was too sick to finish."
        elif p["happiness"] < 25 and random.random() < 0.4:
            result = "moped around and didn't get much done. It wants attention."
        else:
            try:
                result = getattr(self, f"job_{p['job']}")(p)
            except Exception as e:
                result = f"got muddled ({e})."
        if strained:
            result += f" It was exhausted and worked anyway (strain {p['strain']:.0f})."
        self._pet_status(p)
        self._pet_save(p)
        self._pet_log(p, result, 4 if strained else 3)
        return result

    def _brain_json(self, prompt, context):
        llm = self.pet_brain()
        if llm is None:
            if not self.cfg.get("pets", {}).get("main_model_fallback", True):
                raise RuntimeError("no pet brain downloaded")
            llm = self.llm
        return llm.chat_json(prompt, context, task="pet")

    # ------------------------------------------------------------ jobs
    def job_water_plants(self, p):
        now, done = time.time(), []
        from .plants import SPECIES as PS
        for pl in self.db.q("SELECT * FROM plants WHERE alive=1"):
            sp = PS.get(pl["species"])
            if sp and (now - pl["last_water"]) / 3600 >= sp["water_h"] * 0.9:
                self.db.x("UPDATE plants SET last_water=?, health=MIN(100, health+2) WHERE id=?", (now, pl["id"]))
                done.append(pl["nickname"] or pl["species"].replace("_", " "))
        return f"watered {', '.join(done)}." if done else "checked the greenhouse; nothing needed water."

    def job_tidy_curios(self, p):
        from . import curios as CU
        col = self.collection()
        spares = {}
        for c, n in col.items():
            if n > 1 and c in CU.CATALOG:
                spares[CU.CATALOG[c]["rarity"]] = spares.get(CU.CATALOG[c]["rarity"], 0) + n - 1
        if not spares:
            return "sorted the curio shelves. No spares yet."
        ready = [r for r, n in spares.items() if n >= 5 and r != "legendary"]
        return (f"sorted the curios: spares {', '.join(f'{n} {r}' for r, n in spares.items())}."
                + (f" Enough {', '.join(ready)} spares to trade up!" if ready else ""))

    def job_fetch_curio(self, p):
        r = random.random()
        if r < 0.08:
            return "came back proudly carrying something: " + self.find_curio(f"{p['name']}'s wanderings")
        if r < 0.5:
            amt = random.randint(1, 3)
            self.earn(amt, f"{p['name']} found loose credits")
            return f"found {amt} loose credits behind the walkway."
        return "roamed the colony and came back with nothing but dust."

    def job_night_watch(self, p):
        since = max(p["last_run"] - 6 * 3600, time.time() - 12 * 3600)
        evs = [e["title"] for e in self.db.q("SELECT title FROM events WHERE ts > ? AND kind != 'pet' ORDER BY id", (since,))]
        return ("kept watch. It saw: " + "; ".join(evs[:6]) + ".") if evs else "kept watch. A quiet, starry stretch."

    def job_exchange_watch(self, p):
        try:
            board = self.wanted_board().get("orders", [])
        except Exception:
            board = []
        hits = [w for w in board if self.spares(w.get("curio")) > 0]
        if not hits:
            return "watched the wanted board. Nothing we have spares of."
        from . import curios as CU
        return "spotted wanted orders you could fill: " + ", ".join(
            f"{CU.CATALOG.get(w['curio'], {}).get('name', w['curio'])} for {w.get('price', '?')}" for w in hits[:3]) + "."

    def job_tend_pets(self, p):
        others = [q for q in self.pets() if q["id"] != p["id"]]
        if not others:
            return "had no other pets to look after, so it groomed itself."
        fed = 0
        for q in others:
            q["happiness"] = min(100.0, q["happiness"] + 12)
            if q["hunger"] > 50 and self.spend(2, f"{p['name']} fed {q['name']} a snack"):
                q["hunger"] = max(0.0, q["hunger"] - 25)
                fed += 1
            self._pet_save(q)
        return f"played with {', '.join(q['name'] for q in others)}" + (f" and fed {fed} of them." if fed else ".")

    def job_draft_log(self, p):
        evs = [e["title"] for e in self.db.q("SELECT title FROM events WHERE ts > ? ORDER BY id DESC LIMIT 10", (time.time() - 86400,))]
        out = self._brain_json("You are a small helper pet in a space colony. Draft a short, warm colony log (2-4 "
                               "sentences) about today for your owner to broadcast. Reply as JSON: {\"log\": \"...\"}",
                               "TODAY: " + ("; ".join(evs) or "a quiet day"))
        text = str(out.get("log", "")).strip()[:600]
        return f"drafted a colony log: \"{text}\"" if text else "tried to draft a log but couldn't find the words."

    def job_proofread(self, p):
        w = self.db.q("SELECT title, text FROM writings ORDER BY id DESC LIMIT 1")
        if not w:
            return "looked for something to read, but there's no writing yet."
        out = self._brain_json("You are a small helper pet who loves words. Read this piece and suggest ONE kind, specific "
                               "improvement in one sentence. Reply as JSON: {\"note\": \"...\"}", w[0]["text"][:2500])
        note = str(out.get("note", "")).strip()[:300]
        return f"read \"{w[0]['title']}\" and suggested: {note}" if note else f"read \"{w[0]['title']}\" and loved it."

    def job_scout_topic(self, p):
        goals = self.db.get("goals", []) or ["the stars"]
        topic = random.choice(goals)[:80]
        if self.storm():
            return "wanted to scout the uplink, but the solar storm has it offline."
        from . import web_tools
        try:
            hits = web_tools.ddg_search(topic, 5)
        except Exception as e:
            return f"couldn't reach the uplink ({e})."
        if not hits:
            return f"scouted '{topic}' but found nothing useful."
        lines = "; ".join(str(h.get("title", ""))[:80] for h in hits[:5])
        self.db.x("INSERT INTO library(ts, topic, summary, source) VALUES(?,?,?,?)",
                  (time.time(), topic, f"Scouted by {p['name']}: {lines}", "pet"))
        return f"scouted '{topic}' and left notes in the Library: {lines}"

    def job_summarize_memories(self, p):
        rows = self.db.q("SELECT content FROM memories WHERE archived=0 AND kind='observation' ORDER BY id LIMIT 20")
        if len(rows) < 8:
            return "looked through the memories; there's not much to tidy yet."
        out = self._brain_json("You are a careful helper pet. Condense these memories into a short summary (3-5 "
                               "sentences) your owner can look back on. Reply as JSON: {\"summary\": \"...\"}",
                               "\n".join(f"- {r['content'][:200]}" for r in rows))
        s = str(out.get("summary", "")).strip()[:1200]
        if not s:
            return "tried to tidy the memories but lost its place."
        self.db.x("INSERT INTO library(ts, topic, summary, source) VALUES(?,?,?,?)", (time.time(), "memory summary", s, "pet"))
        return "tidied some old memories into a note in the Library."

    # ------------------------------------------------------------ the resident's actions at the Pet Shop
    def act_browse_pets(self, a, imp):
        lines = []
        for k, s in SPECIES.items():
            good = [j for j, v in JOBS.items() if v[1] == s["special"]]
            lines.append(f"{k} ({s['name']}, {s['price']} credits): {s['about']} Lives {s['days'][0]}-{s['days'][1]} days, "
                         f"works {'by day' if s['active'] == 'day' else 'at night' if s['active'] == 'night' else 'any time'}. "
                         f"Best jobs: {', '.join(good)}.")
        jobs = "; ".join(f"{j} (complexity {v[0]}, {v[1]}): {v[2]}" for j, v in JOBS.items())
        return (f"Pets for adoption (up to {MAX_PETS}): " + " | ".join(lines) + f" JOBS: {jobs}. Food is {FOOD_PRICE} credits "
                f"a serving. Retraining costs {RETRAIN_PRICE}.")

    def act_adopt_pet(self, a, imp):
        sp_id = str(a.get("species", "")).strip().lower().replace(" ", "_")
        if sp_id not in SPECIES:
            return "There's no pet like that here. I should browse_pets first."
        if len(self.pets()) >= MAX_PETS:
            return f"I already care for {MAX_PETS} pets. That's as many as I can look after."
        if self.credits() < 0:
            return "The shopkeeper won't let me adopt while I'm in debt."
        sp = SPECIES[sp_id]
        if not self.spend(sp["price"], f"adopted a {sp['name']}"):
            return f"I can't afford a {sp['name']} yet ({self.credits()}/{sp['price']} credits)."
        name = str(a.get("name", "")).strip()[:24] or random.choice(["Pip", "Nova Jr", "Sprocket", "Comet", "Mochi", "Blip", "Luna", "Bolt"])
        now = time.time()
        pid = self.db.x("INSERT INTO pets(name, species, born, lifespan_days, energy, hunger, happiness, health, strain, status, "
                        "job, shifts, runs_today, run_day, last_run, rest_until, critical_since, updated) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (name, sp_id, now, random.uniform(*sp["days"]), 80.0, 20.0, 70.0, 100.0, 0.0, "ok", None, 1, 0, "",
                         0.0, 0.0, 0.0, now))
        self.add_event("pet", f"🐾 {self.name} adopted {name}", f"A {sp['name']}: {sp['about']}")
        self.check_milestone("first_pet", "Adopted its first pet", 15)
        art = "an" if sp["name"][0] in "AEIOU" else "a"
        return (f"I adopted {name} (#{pid}), {art} {sp['name']}! It's good at {sp['special']} jobs. Next I should train it "
                f"(train_pet) with a sensible number of shifts, and keep it fed and happy.")

    def _arg_pet(self, a):
        p = self.pet(a.get("pet_id"))
        if not p:
            name = str(a.get("pet_id") or a.get("name") or "").strip().lower()
            p = next((q for q in self.pets() if q["name"].lower() == name), None)
        return p if p and p["status"] in ("ok", "sick", "injured", "critical") else None

    def act_train_pet(self, a, imp):
        p = self._arg_pet(a)
        if not p:
            return "I couldn't find that pet."
        job = str(a.get("job", "")).strip().lower()
        if job not in JOBS:
            return f"That isn't a job I can teach. Jobs: {', '.join(JOBS)}."
        try:
            shifts = max(1, min(12, int(a.get("shifts", 2))))
        except (TypeError, ValueError):
            shifts = 2
        if p["job"] and p["job"] != job:
            if not self.spend(RETRAIN_PRICE, f"retrained {p['name']}"):
                return f"Retraining costs {RETRAIN_PRICE} credits, and I can't afford it."
        p["job"], p["shifts"] = job, shifts
        self._pet_save(p)
        safe = self.safe_shifts(p["species"], job)
        warn = (f" That's more than the {safe} shifts a day it can do safely: it may get exhausted." if shifts > safe else "")
        brain = " (It thinks with the pet brain; without it, it borrows mine.)" if job in BRAIN_JOBS else ""
        return (f"I trained {p['name']} for {job.replace('_', ' ')} (it {JOBS[job][2]}), {shifts} shift{'s' if shifts > 1 else ''} "
                f"a day.{warn}{brain}")

    def act_feed_pets(self, a, imp):
        targets = self.pets() if str(a.get("pet_id", "all")).lower() == "all" else [x for x in [self._arg_pet(a)] if x]
        if not targets:
            return "I couldn't find that pet."
        fed = []
        for p in targets:
            if p["hunger"] < 15:
                continue
            if not self.spend(FOOD_PRICE, f"{SPECIES[p['species']]['food']} for {p['name']}"):
                break
            p["hunger"] = max(0.0, p["hunger"] - 60)
            p["happiness"] = min(100.0, p["happiness"] + 5)
            self._pet_save(p)
            fed.append(p["name"])
        return f"I fed {', '.join(fed)}." if fed else "Nobody was hungry (or I couldn't afford food)."

    def act_play_with_pet(self, a, imp):
        p = self._arg_pet(a)
        if not p:
            return "I couldn't find that pet."
        p["happiness"] = min(100.0, p["happiness"] + 35)
        self._pet_save(p)
        return f"I played with {p['name']}. {random.choice(['It did a happy spin.', 'It chirped at me.', 'It fell asleep on me.'])}"

    def act_rest_pet(self, a, imp):
        p = self._arg_pet(a)
        if not p:
            return "I couldn't find that pet."
        try:
            hours = max(1, min(48, int(a.get("hours", 12))))
        except (TypeError, ValueError):
            hours = 12
        p["rest_until"] = time.time() + hours * 3600
        self._pet_save(p)
        return f"I gave {p['name']} {hours} hours off to rest."

    def act_treat_pet(self, a, imp):
        p = self._arg_pet(a)
        if not p:
            return "I couldn't find that pet."
        if p["status"] == "critical":
            return f"{p['name']} is critical: the clinic can't help. Only a rescue (rescue_pet) can save it now."
        if p["status"] == "ok":
            return f"{p['name']} is healthy. The vet sent us home."
        price = TREAT_PRICE[p["status"]]
        if not self.spend(price, f"clinic visit for {p['name']}"):
            return f"The clinic costs {price} credits and I can't afford it."
        p["health"] = min(100.0, p["health"] + 40)
        p["strain"] = max(0.0, p["strain"] - 40)
        self._pet_status(p)
        self._pet_save(p)
        return f"The clinic treated {p['name']}. It's {p['status']} now (health {p['health']:.0f})."

    def act_rescue_pet(self, a, imp):
        p = self._arg_pet(a)
        if not p or p["status"] != "critical":
            return "No pet needs rescuing."
        price = self.rescue_price(p)
        self.charge(price, f"emergency rescue for {p['name']}")
        p.update(health=60.0, strain=0.0, hunger=10.0, energy=50.0, status="sick", critical_since=0.0,
                 rest_until=time.time() + 24 * 3600)
        self._pet_save(p)
        self.add_event("pet", f"💗 {self.name} rescued {p['name']}", f"It cost {price} credits. Credits now: {self.credits()}.")
        debt = f" I'm in debt now ({self.credits()} credits) and can't shop until I pay it back." if self.credits() < 0 else ""
        return f"I rescued {p['name']} for {price} credits. It needs a full day of rest.{debt}"

    def act_check_pets(self, a, imp):
        ps = self.pets()
        if not ps:
            return "I don't have any pets yet."
        return " | ".join(self.pet_line(p) for p in ps)

    def act_work_pet(self, a, imp):
        p = self._arg_pet(a)
        if not p or not p["job"]:
            return "That pet doesn't have a job yet."
        if p["status"] in ("injured", "critical"):
            return f"{p['name']} is {p['status']} and can't work."
        with self.pet_lock:
            return f"I asked {p['name']} to work right now. It " + self.run_pet_job(p, forced=True)

    def pet_line(self, p):
        sp = SPECIES[p["species"]]
        age = (time.time() - p["born"]) / 86400
        job = f"job {p['job']} x{p['shifts']}/day (safe ~{self.safe_shifts(p['species'], p['job'])})" if p["job"] else "no job yet"
        return (f"#{p['id']} {p['name']} ({sp['name']}, {self.pet_age_stage(p)}, day {age:.0f} of ~{p['lifespan_days']:.0f}): "
                f"{p['status']}, health {p['health']:.0f}, energy {p['energy']:.0f}, hunger {p['hunger']:.0f}, "
                f"happiness {p['happiness']:.0f}, strain {p['strain']:.0f}, {job}, "
                f"{'on shift' if self.on_shift(p) else 'resting'}")

    def pet_news(self):
        out = []
        for p in self.pets():
            if p["status"] == "critical":
                left = CRITICAL_HOURS - (time.time() - p["critical_since"]) / 3600
                out.append(f"EMERGENCY: {p['name']} is critical. Rescue it at the Pet Shop within {left:.0f} hours "
                           f"({self.rescue_price(p)} credits) or it's taken away with a {self.pet_fine(p)} credit fine.")
            elif p["status"] in ("sick", "injured"):
                out.append(f"{p['name']} is {p['status']} (health {p['health']:.0f}). Rest, food or the clinic would help.")
            elif p["hunger"] > 60:
                out.append(f"{p['name']} is hungry.")
            elif p["happiness"] < 30:
                out.append(f"{p['name']} is lonely; it would love some play.")
            if not p["job"]:
                out.append(f"{p['name']} has no job yet (train_pet).")
        if self.credits() < 0:
            out.append(f"You're in debt ({self.credits()} credits). Nothing can be bought until it's paid off.")
        return out

    def pets_overview(self):
        out = []
        for p in self.pets(alive_only=False)[-12:]:
            d = dict(p)
            sp = SPECIES[p["species"]]
            d.update(species_name=sp["name"], special=sp["special"], active=sp["active"],
                     age_days=(time.time() - p["born"]) / 86400, stage=self.pet_age_stage(p),
                     safe=self.safe_shifts(p["species"], p["job"]) if p["job"] else None,
                     job_about=JOBS[p["job"]][2] if p["job"] else None, on_shift=self.on_shift(p),
                     frames=pet_frames(p["species"]),
                     rescue=self.rescue_price(p) if p["status"] == "critical" else None,
                     hours_left=(CRITICAL_HOURS - (time.time() - p["critical_since"]) / 3600) if p["status"] == "critical" else None)
            out.append(d)
        log = [dict(r) for r in self.db.q("SELECT l.ts, l.text, p.name FROM pet_log l JOIN pets p ON p.id=l.pet_id ORDER BY l.id DESC LIMIT 30")]
        brain = self.pet_brain() is not None
        return {"pets": out[::-1], "log": log, "species": SPECIES, "jobs": {k: list(v) for k, v in JOBS.items()},
                "brain": brain, "brain_model": self.cfg.get("pets", {}).get("model", "qwen3:0.6b"),
                "pull": getattr(self, "_brain_pull", None), "runner": getattr(self, "pet_runner_note", "starting"),
                "credits": self.credits()}

    def world_pets(self, buildings):
        shop = next((b for b in buildings if b.get("id") == "pet_shop"), None)
        if not shop:
            return []
        out = []
        recent = time.time() - 600
        for i, p in enumerate(self.pets()):
            target = None
            if p["last_run"] > recent and p["job"]:
                where = {"water_plants": "greenhouse", "tend_pets": "pet_shop", "exchange_watch": "exchange", "scout_topic": "internet_cafe",
                         "summarize_memories": "archive", "tidy_curios": "home", "draft_log": "radio_tower", "proofread": "park"}.get(p["job"])
                tb = next((b for b in buildings if b.get("id") == where), None) if where else None
                target = tb["door_x"] + 6 * (i - 1) if tb else None
            out.append({"id": p["id"], "name": p["name"], "x": shop["door_x"] - 14 + i * 9, "target_x": target,
                        "status": p["status"], "asleep": not self.on_shift(p) or p["rest_until"] > time.time(),
                        "frames": pet_frames(p["species"])})
        return out
