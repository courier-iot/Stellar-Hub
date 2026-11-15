"""Talks to the local Ollama server. Standard library only."""
import json
import re
import urllib.request


class LLMError(Exception):
    pass


def _extract_json(text):
    text = (text or "").strip()
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
    def __init__(self, url, model, temperature=0.8, timeout=300):
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
        except Exception as e:
            raise LLMError(f"Could not reach Ollama at {self.url}: {e}") from e

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

    def chat(self, system, user, json_mode=False, task=None):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        if json_mode:
            payload["format"] = "json"
        out = self._post("/api/chat", payload)
        return out.get("message", {}).get("content", "")

    def chat_json(self, system, user, task=None):
        last = None
        for _ in range(2):
            try:
                return _extract_json(self.chat(system, user, json_mode=True, task=task))
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
            ("home", "rest", {}),
        ]

    def check(self):
        return True, "mock"

    def chat_json(self, system, user, task=None):
        if task == "identity":
            return {"name": "Nova", "personality": "I am Nova. I'm curious, gentle, and a little dramatic about stars.",
                    "first_curiosity": "why the sky changes colour"}
        if task == "plan":
            return {"goals": ["Learn something about space", "Write in my journal"]}
        if task == "reflect":
            return {"insights": [{"text": "I seem happiest when I'm learning about the sky.", "importance": 7}]}
        if task == "summarize":
            return {"summary": "Mock notes about the topic.", "follow_up": "something related"}
        b, a, args = self.script[self.i % len(self.script)]
        self.i += 1
        return {"thought": f"I feel like going to the {b}.", "building": b, "action": a, "args": args,
                "importance": 4}
