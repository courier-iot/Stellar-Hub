"""Talks to the local Ollama server. Standard library only."""
import json
import re
import urllib.error
import urllib.request


class LLMError(Exception):
    pass


def _extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise LLMError(f"Model did not return valid JSON: {text[:200]}")


class OllamaLLM:
    def __init__(self, url, model, temperature=0.8, timeout=300, num_ctx=8192):
        self.num_ctx = num_ctx
        self.think_param = True   # turned off automatically if the model doesn't understand it
        self.url = url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def _post(self, path, payload):
        req = urllib.request.Request(self.url + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            raise LLMError(f"Ollama error {e.code}: {detail}") from e
        except Exception as e:
            raise LLMError(f"Could not reach Ollama at {self.url}: {e}") from e

    def installed(self):
        """Names of downloaded chat models (embedding models skipped), biggest first. Raises if Ollama is down."""
        with urllib.request.urlopen(self.url + "/api/tags", timeout=10) as r:
            tags = json.loads(r.read().decode())
        models = [m for m in tags.get("models", []) if "embed" not in m.get("name", "").lower()]
        models.sort(key=lambda m: -m.get("size", 0))
        return [m.get("name", "") for m in models]

    def check(self):
        """Returns (ok, message)."""
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=10) as r:
                tags = json.loads(r.read().decode())
        except Exception as e:
            return False, f"Ollama is not running at {self.url} ({e}). Start the Ollama app first."
        names = [m.get("name", "") for m in tags.get("models", [])]
        if not any(n == self.model or n.split(":")[0] == self.model or n == self.model + ":latest" for n in names):
            return False, (f"Model '{self.model}' isn't downloaded. Run:  ollama pull {self.model}\n"
                           f"Models you have: {', '.join(names) or 'none'}")
        return True, "ok"

    schema_ok = True      # Ollama 0.5+ can hold the answer to a JSON schema (the exact building ids and actions)

    def chat(self, system, user, json_mode=False, task=None, schema=None):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = schema if (schema and self.schema_ok) else "json"
        if self.think_param:
            payload["think"] = False   # thinking models: answer directly (faster, cleaner JSON)
        try:
            out = self._post("/api/chat", payload)
        except LLMError as e:
            if isinstance(payload.get("format"), dict) and "Ollama error 4" in str(e):
                self.schema_ok = False        # an older Ollama: plain JSON mode, and the hub repairs mistakes instead
                payload["format"] = "json"
                return self.chat(system, user, json_mode, task, None)
            if self.think_param and "think" in str(e).lower():
                self.think_param = False
                payload.pop("think", None)
                out = self._post("/api/chat", payload)
            else:
                raise
        return out.get("message", {}).get("content", "")

    def chat_json(self, system, user, task=None, schema=None):
        last = None
        for _ in range(2):
            try:
                return _extract_json(self.chat(system, user, json_mode=True, task=task, schema=schema))
            except LLMError as e:
                last = e
                if "reach Ollama" in str(e):
                    raise
        raise last


class MockLLM:
    """Fake model for testing Stellar Hub without Ollama (set "provider": "mock")."""

    def __init__(self):
        self.i = 0
        self.script = [
            ("home", "journal", {"text": "My first day. Everything is new and quiet."}),
            ("internet_cafe", "research", {"topic": "how stars form"}),
            ("library", "write_note", {"topic": "goals", "text": "I want to understand the sky."}),
            ("post_office", "send_request", {"kind": "learn", "content": "Can you teach me about music?",
                                             "reason": "I keep wondering what sound feels like."}),
            ("library", "recall", {"topic": "stars"}),
            ("post_office", "read_mail", {}),
            ("bank", "enter", {}),
            ("salon", "change_look", {"form": "robot", "primary": "silver", "secondary": "blue", "accent": "cyan"}),
            ("post_office", "ask_question", {"question": "What does rain feel like?"}),
            ("post_office", "send_request", {"kind": "access", "content": "May I use the greenhouse?", "reason": "I want to grow things.", "building": "greenhouse"}),
            ("bank", "check_balance", {}),
            ("bank", "buy", {"item": "decor:bench"}),
            ("greenhouse", "plant", {"species": "moon_moss", "nickname": "Silvy"}),
            ("greenhouse", "check_plants", {}),
            ("greenhouse", "water", {"plant_id": "all"}),
            ("radio_tower", "broadcast_log", {"text": "Day one log: quiet skies."}),
            ("radio_tower", "list_music", {"search": ""}),
            ("radio_tower", "play_music", {"song_id": 1}),
            ("workshop", "write_program", {"name": "hello", "description": "prints primes", "code": "print([p for p in range(2,30) if all(p%d for d in range(2,p))])"}),
            ("home", "build", {"building": "greenhouse", "plot": 4}),
            ("home", "paint", {"subject": "a sunset over the sea", "title": "Sunset"}),
            ("home", "showcase", {"type": "painting", "id": 1}),
            ("home", "upgrade_home", {}),
            ("library", "observe_sky", {}),
            ("park", "write", {"kind": "poem", "title": "Orbit", "text": "Round and round the quiet planet goes, carrying my little colony."}),
            ("park", "relax", {}),
            ("park", "solve_puzzle", {}),
            ("gallery", "hang_painting", {"painting_id": 1}),
            ("studio", "compose", {"title": "First Light", "bpm": 120, "wave": "pulse", "melody": "C4:1 E4:1 G4:1 C5:2 B4:1 G4:1", "bass": "C3:4 G2:4"}),
            ("studio", "play_composition", {"composition_id": 1}),
            ("station", "station_study", {}),
            ("exchange", "check_exchange", {}),
            ("exchange", "sell_curio", {"curio": "", "count": 1}),
            ("exchange", "trade_up", {"rarity": "common"}),
            ("exchange", "auction_curio", {"curio": "", "reserve": 10}),
            ("home", "stargaze", {}),
            ("home", "set_bedtime", {"bed_hour": 22, "wake_hour": 7}),
            ("spaceport", "start_expedition", {"topic": "black holes", "hours": 1}),
            ("home", "rest", {}),
        ]

    def check(self):
        return True, "mock"

    def chat_json(self, system, user, task=None, schema=None):
        if schema:
            self.last_schema = schema
        if task == "code":
            return {"code": "def count_stars(sky):\n    return sky.count('*')\n", "notes": "Counting is easy with str.count."}
        if task == "machine_design":
            return {"parts": {"frame": 1, "wheel": 2, "pump": 1, "sensor": 1, "circuit": 1, "battery": 1},
                    "notes": "One battery covers the pump, sensor and circuit."}
        if task == "project_plan":
            return {"title": "Desk Plant Moisture Light", "summary": "An ESP32 reads a soil sensor and lights an LED when the plant is thirsty.",
                    "difficulty": "easy", "parts": [{"item": "ESP32 dev board", "qty": 1, "note": "any"},
                                                    {"item": "capacitive soil sensor", "qty": 1, "note": "3.3V"}],
                    "tools": ["USB cable"], "steps": ["Wire the sensor to 3V3, GND and GPIO34.", "Upload the code."],
                    "code": "void setup(){ pinMode(2, OUTPUT); }\nvoid loop(){ digitalWrite(2, analogRead(34) > 2000); delay(1000); }",
                    "scad": "", "tips": "Calibrate dry and wet readings first."}
        if task == "identity":
            return {"name": "Nova", "personality": "I am Nova. I'm curious, gentle, and a little dramatic about stars.",
                    "first_curiosity": "why the sky changes colour", "bed_hour": 23, "wake_hour": 7}
        if task == "plan":
            return {"goals": ["Learn something about space", "Write in my journal"]}
        if task == "reflect":
            return {"insights": [{"text": "I seem happiest when I'm learning about the sky.", "importance": 7}],
                    "traits": {"curious": 3, "calm": -1}}
        if task == "paint":
            return {"rows": ["..yy....", ".yyyy...", "yyyyyy..", ".yyyy..c", "..yy..cc", "....cccc", "...ccccc", "eeeeeeee"],
                    "about": "A sun setting over a cyan sea."}
        if task == "curio_note":
            return {"note": "It feels lighter than it looks. I think I'll keep this one close."}
        if task == "puzzle":
            return {"answer": "42"}
        if task == "chess":
            return {"move": "zz99", "comment": "Hmm, let me think..."}
        if task == "quiz_make":
            return {"questions": [{"q": "What is a star made of?", "a": "plasma"}, {"q": "Nearest star?", "a": "the Sun"},
                                  {"q": "What powers stars?", "a": "fusion"}]}
        if task == "quiz_take":
            return {"answers": ["plasma", "the Sun", "I don't remember"]}
        if task == "quiz_grade":
            return {"correct": 2}
        if task == "digest":
            return {"digest": "This week I painted a sunset and learned about stars."}
        if task == "recall":
            return {"answer": "I remember writing in my journal on my first day."}
        if task == "layout":
            return {"placements": {"library": 6, "post_office": 9, "internet_cafe": 5, "bank": 10}, "why": "Books and mail close to home."}
        if task == "dream":
            return {"dream": "I dreamed the greenhouse floated away.", "insight": "I worry about losing what I grow."}
        if task == "chat":
            return {"reply": "Hi! I was just thinking about you."}
        if task == "chat_summary":
            return {"summary": "My creator said hello and we talked about stars.", "importance": 6}
        if task == "review":
            return {"completed": [0], "note": "I did the first one."}
        if task == "chapter":
            return {"title": "Waking Up", "text": "Mock chapter about my first days."}
        if task == "exp_plan":
            return {"legs": ["basics", "history", "open questions"]}
        if task == "exp_report":
            return {"title": "Mock Report", "report": "I learned a lot.", "skills": ["explain the basics"]}
        if task == "summarize":
            return {"summary": "Mock notes about the topic.", "follow_up": "something related"}
        b, a, args = self.script[self.i % len(self.script)]
        self.i += 1
        return {"thought": f"I feel like going to the {b}.", "building": b, "action": a, "args": args,
                "importance": 4}
