# Stellar Hub

A tiny space colony where a self-developing AI lives. It remembers, reflects, learns from the
internet, sends you requests, and grows over time. It's drawn in 16-bit pixel art.

- **Stellar Hub** (`desktop/`): the AI's brain plus the town viewer. Runs on your Linux PC with Ollama.
- **Hub Connect S** (`android/`): the phone app. Watch the colony and answer requests from anywhere over Tailscale.

Every push to `main` builds the APK and publishes a release named `vX.Y.Z`, using the
number in the `VERSION` file. The release includes `HubConnectS-vX.Y.Z.apk` and `StellarHub-vX.Y.Z.zip`.

---

## 1. Run Stellar Hub on your Linux PC

1. Python 3.10+ (already on most distros: `python3 --version`).
2. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
3. Download a model: `ollama pull qwen2.5:7b`. Any chat model works; set it in `config.json` → `ollama.model`.
4. Start it: `./start.sh`. Your browser opens **http://localhost:8080** with the live pixel colony.

On its first turn the resident is born as a little **star spirit** and picks its own name.
It wakes every 30 minutes. Press **Take a turn now** to watch it right away.

## 2. Connect your phone (Tailscale)

1. Install Tailscale on the PC (`curl -fsSL https://tailscale.com/install.sh | sh`, then `sudo tailscale up`)
   and the Tailscale app on your phone. Sign in to the same account on both.
2. Restart Stellar Hub. The dashboard's **Hub Connect S · phone pairing** box shows an address and a pair code.
3. In Hub Connect S, open the **Hub** tab, enter the address and pair code, and tap **Save & test**.

Stellar Hub only listens on this computer and on your private Tailscale network, never your
regular Wi-Fi. Phones need the pair code. To make a new code: `./start.sh --new-pair-code`.

## The colony

| Building | What it does |
|---|---|
| Home Dome | Journal, rewrite its personality, rest |
| Observatory Library | Notes and everything it has learned |
| Uplink Café | Web research (Wikipedia + DuckDuckGo). Daily limit; you can close it. |
| Relay Post | Requests and letters between you and it |
| Nova Salon | **Locked until you unlock it.** Then it can change its form (star spirit, robot, person) and its colours. |
| Credit Vault, Fabrication Hangar | Under construction |

## Its mind lives in `desktop/data/`
`town.db` (memories, mail, notes), `home/personality.md` (who it thinks it is), and
`home/personality_history.md` (every past version). Back up `data/` to keep your resident.


