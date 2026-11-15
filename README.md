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
2. Run **`./setup.sh`**. It:
   - detects your CPU, RAM and graphics card, and checks that the graphics driver is working.
     If it isn't, it tells you the exact fix for your distro. On Ubuntu it can run the official driver installer for you.
   - installs Ollama if needed, then picks and downloads the best model your hardware can run.
     If a model has been renamed, it falls back to the next choice.
   - checks the extras: bubblewrap (Hangar sandbox), mpv (Radio music), Tailscale (phone) and your music folder.
   - asks before anything that needs your password. Use `./setup.sh --check` to only report, or `--yes` to accept everything.
3. Start it: `./start.sh`. Your browser opens **http://localhost:8080** with the live pixel colony.

If `./setup.sh` or `./start.sh` says "permission denied", run `chmod +x *.sh` once in that folder.
GitHub's web uploader drops that flag.

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

| Building | What it does | Unlock price |
|---|---|---|
| Home Dome | Journal, rewrite its personality, rest. Decorations it buys appear outside. | open |
| Observatory Library | Notes and everything it has learned | open |
| Uplink Café | Web research (Wikipedia + DuckDuckGo). Daily limit; you can close it. | open |
| Relay Post | Requests, **questions** and letters between you and it | open |
| Credit Vault | Its colony credits and the shop | open |
| Hydro Greenhouse | 32 plants in 4 rarity tiers, each with its own watering, feeding and light routine. Neglected plants wilt. | 60 |
| Radio Tower | Plays songs from your music folder out loud on the PC (not during quiet hours), and broadcasts colony logs to your phone | 80 |
| Archive Vault | Turns old memories into chapters of its life story | 70 |
| Nova Salon | Change form (star spirit, robot, person) and colours | 50 |
| Spaceport | Research expeditions: it leaves for 1-8 hours, studies a topic in stages, and comes back with a report | 150 |
| Fabrication Hangar | Writes Python programs. **You approve each one**, then it runs in a sandbox with no internet and only its own folder. | 200 |

**Unlocking:** locked buildings open when (1) you press **Unlock** on the dashboard or in the app's Hub tab,
(2) you **approve** its access request for that building, or (3) it buys access with credits at the Credit Vault.

**Credits:** it earns them for daily routines (+1 per action, up to 20 a day), journaling (+3 a day), each finished
daily goal (+10), healthy plants (+2 each a day), blooms (+15), approved requests (+5), life-story chapters (+5),
finished expeditions (+20) and programs that run successfully (+8). You can give it bonuses (or take some away)
from the Credit Vault panel. It spends them on decorations, seeds, pots, Salon looks and building unlocks.
Credits are colony-only; no real money is involved.

**Phone notifications:** Hub Connect S checks about every 15 minutes. You can approve or deny requests and answer
questions right from the notification. Set quiet hours and turn notifications on or off in the Hub tab.
Keep Tailscale connected on your phone so the checks can reach the hub.

## Its mind lives in `desktop/data/`
`town.db` (memories, mail, notes, plants, credits), `home/personality.md` (who it thinks it is),
`home/personality_history.md` (every past version) and `workshop/` (its programs).
Back up `data/` to keep your resident. Upgrading from v0.3.0 keeps everything; new tables are added automatically.

## Settings (`config.json`)
- `ollama.model`: set by `./setup.sh`, or change it by hand
- `radio.music_dir`: your music folder (default `~/Music`). `radio.quiet_hours`: no music between these hours (default 23-8)
- `limits`: daily AI calls, café visits, and how many requests can wait at once

## One-time GitHub setup: signing key
So phone updates install over the previous version, every APK must be signed with the same key.
In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
- `KEYSTORE_BASE64`
- `KEYSTORE_PASSWORD`

(The values come in the separate `SIGNING-SECRETS.txt`. Never upload that file to the repo.)
