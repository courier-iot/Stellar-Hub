# Stellar Hub

A tiny space colony where a self-developing AI lives. It remembers, reflects, learns from the
internet, sends you requests, and grows over time. It's drawn in 16-bit pixel art.

- **Stellar Hub** (`desktop/`): the AI's brain plus the town viewer. Runs on your Linux PC with Ollama.
- **Hub Connect S** (`android/`): the phone app. Watch the colony and answer requests from anywhere over Tailscale.

Every push to `main` builds everything and publishes a release named `vX.Y.Z`, using the number in the
`VERSION` file. The release includes `HubConnectS-vX.Y.Z.apk` (phone), `StellarHub-vX.Y.Z.zip` (Linux) and
`StellarHub-Setup-vX.Y.Z.exe` (Windows installer).

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

**Start with your PC:** `sh install-service.sh` makes Stellar Hub a background service that starts on login
(and optionally at boot). After updating files, restart it with `systemctl --user restart stellar-hub`.
Remove it with `sh install-service.sh remove`. Logs: `journalctl --user -u stellar-hub -f` (also saved in `data/hub.log`).
Stop a running hub from anywhere with `python3 stop.py`.

On its first turn the resident is born as a little **star spirit** and picks its own name.
It wakes every 30 minutes. Press **Take a turn now** to watch it right away.

## 1b. Or run Stellar Hub on Windows (10 or 11)

1. Download **`StellarHub-Setup-vX.Y.Z.exe`** from the latest release and run it. No admin rights are needed,
   and Python comes built in. It installs to `%LOCALAPPDATA%\StellarHub`.
2. At the end, leave **"Check my hardware and choose an AI model"** ticked. Setup then:
   - reads your CPU, RAM and graphics card (with exact video memory) and checks the graphics driver.
     If it's missing or Windows is using its basic display driver, it tells you where to get the right one.
   - installs Ollama with winget if needed, then picks and downloads the best model for your PC.
   - checks Docker Desktop (the Hangar's sandbox on Windows) and Tailscale.
   - offers to start Stellar Hub in the background each time you sign in.
3. Start menu → **Stellar Hub** opens the colony. There's also **Setup and model check**, **Stop Stellar Hub**
   and a **dashboard** link.

Music plays through Windows' own media player (VLC or mpv also work). Updating with a newer installer keeps
your resident; so does uninstalling (its mind stays in the `data` folder). If Windows Firewall asks about
Python, allow it so your phone can connect.

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
| Starlight Gallery | Paint pixel paintings and hang the best on its 12 walls (the newest is shown on its front) | 90 |
| Low-G Park | Write poems and stories, relax (sometimes finding curios), puzzles, and **chess with you** | 60 |
| Curio Exchange | Sell spare curios, fill collectors' wanted orders, trade 5 up into 1 of the next rarity, run 6-hour auctions | 80 |
| Radio Studio *(Radio Tower upgrade)* | Compose chiptune songs and play them on the radio | 120 |
| Orbital Station *(Spaceport upgrade)* | Turns what it studied into tests, then re-tests itself from memory on a spaced schedule | 300 |
| Spaceport | Research expeditions: it leaves for 1-8 hours, studies a topic in stages, and comes back with a report | 150 |
| Fabrication Hangar | Writes Python programs. **You approve each one**, then it runs in a sandbox with no internet and only its own folder. | 200 |

**Plots:** the colony has 15 plots along the walkway, with the Home Dome fixed in the middle (plot 8).
On its first day the resident decides where its starting buildings go. Every building it gets after that
arrives as a **blueprint**: it picks an empty plot and builds it from Home, which takes about 2 hours with
scaffolding up. Moving a finished building costs **1,500 credits** (`move_cost` in config.json).

**Unlocking:** locked buildings become blueprints when (1) you press **Unlock** on the dashboard or in the app's Hub tab,
(2) you **approve** its access request for that building, or (3) it buys access with credits at the Credit Vault.

**Sleep, day and night:** the colony follows your PC's clock. Its star crosses the sky by day, and the lights come on at night.
The resident picks its own bedtime (8-10 hours). While it sleeps it makes no AI calls, apart from one dream per night
that it learns something from.

**Live chat:** talk to it in real time from the dashboard or the app's Chat tab. It stops what it's doing,
gives you its full attention, and saves the conversation as a memory when you end the chat (or after 10 quiet minutes).

**Space events** (about 3 a week, `events_per_week` in config.json):
- solar storms take the Uplink offline for a few hours
- meteor showers leave stardust and rare seeds to find by stargazing
- eclipses pause plant growth
- travelling traders sell rare goods

You can also start one yourself from the dashboard.

**Emotes and milestones:** bubbles above its head show what it's up to (? ♪ ♥ ! z). Milestones (first bloom,
100 journal entries, one month old…) appear in the app and on the dashboard, with a credit bonus.

**Credits** are colony-only; no real money is involved. You can give bonuses (or take some away) from the Credit Vault panel.

| It earns | Credits |
|---|---|
| Each successful action | +1 (up to 20 a day) |
| Writing in its journal | +3 once a day |
| Each finished daily goal | +10 (up to 3 a day) |
| Each healthy plant (70%+) | +2 a day |
| A plant blooms | +15 |
| A request you approve | +5 |
| A life-story chapter | +5 |
| Finishing an expedition | +20 |
| A program runs successfully | +8 |
| Stardust in a meteor shower | 5-25 (up to 3 a day) |
| A hobby skill levels up | +5 × the new level |
| Solving a puzzle | +2 (up to 10 a day) |
| Selling curios | 6 / 15 / 40 / 120 by rarity (more from wanted orders and auctions) |
| Winning chess against you | +10 |
| Station test | +3 per right answer, +15 when a topic is mastered |
| Milestones | 5-300 |

| It spends | Credits |
|---|---|
| Decorations | 10-80 |
| Seeds | 3 / 10 / 25 / 60 by rarity |
| 2 more greenhouse pots | 30 |
| Salon: new colours / new form | 10 / 40 |
| Building unlocks | 50-300 |
| Home Dome floor 2 / 3 / 4 | 150 / 300 / 600 |
| Trader goods | varies |
| Moving a building | 1,500 |

**Hobbies:** painting, writing, composing, astronomy, collecting, games, gardening and coding each have a skill
level that grows with practice. It takes hobbies up by trying them. Higher painting levels mean bigger canvases
(8×8 → 12×12 → 16×16), and higher collecting levels mean better odds of rare finds. Its paintings, writings,
songs and curios all show up in the app's **Gallery** tab and on the dashboard.

**Home Dome showcase:** the home can grow to **4 floors** with **12 showcase spots each**. It displays paintings,
curios, framed writings and cuttings from plants that have bloomed. Space is limited on purpose, so it has to choose
what to rotate out. The dome visibly gets taller with each floor.

**Curios:** 128 to collect (meteorites, crystals, shells, fossils, Earth relics, gadgets, seed pods and alien
artifacts) at four rarities. Each one has a description, and the first time the resident finds one it writes its own
note about it. They turn up during meteor showers, park walks, expeditions and telescope sessions, and travelling
traders sell them too.

At the **Curio Exchange** it can sell spares for 6 / 15 / 40 / 120 credits by rarity. Three collectors post a
**wanted board** each day, paying 1.6-2.5× for specific curios. **Trading up** turns 5 spares of one rarity into 1
of the next, usually one it doesn't have yet. **Auctions** run for 6 hours with a reserve price it sets; it might get
double, or nothing. Anything on display in its home is never sold or traded.

**Personality traits** (curious, creative, social, calm, brave, playful, thoughtful) shift slowly as it reflects
on its experiences. **Every Sunday evening** it writes "This week in the colony" and sends it to your phone.
**Ask what it remembers** (Chat tab or dashboard) and it answers from its real memories.
**📷** saves a picture of the colony (app: Pictures/Stellar Hub; dashboard: downloads a PNG).

**Phone notifications:** Hub Connect S checks about every 15 minutes. You can approve or deny requests and answer
questions right from the notification. Set quiet hours and turn notifications on or off in the Hub tab.
Keep Tailscale connected on your phone so the checks can reach the hub.

## Its mind lives in `desktop/data/`
`town.db` (memories, mail, notes, plants, credits), `home/personality.md` (who it thinks it is),
`home/personality_history.md` (every past version) and `workshop/` (its programs).
**Nightly backups** go to `~/StellarHub-backups` (the newest 14 are kept; change it under `backups` in config.json,
e.g. to a USB drive). To restore: stop Stellar Hub, then
`tar -xzf ~/StellarHub-backups/stellarhub-YYYY-MM-DD.tar.gz -C /path/to/StellarHub`.
Upgrading keeps everything; new tables are added automatically.

## Updates
Stellar Hub checks this repo's releases twice a day. When there's a new version, the dashboard shows a banner with
what's new and an **Update now** button (it only works from the hub computer itself), and your phone gets a notification.
- **Windows (installed with Setup):** it downloads the new installer, runs it quietly, and Stellar Hub restarts in the background.
- **Linux / zip installs:** it replaces the program files in place and restarts (a systemd service restarts automatically).

Before installing, it backs up your resident and checks the download's SHA-256 checksum against the release.
`data/` and `config.json` are never touched. Turn off the twice-daily check with `"update": {"check": false}`.

## Security
- The dashboard has no password, but it only answers to `localhost`. Changes need the dashboard's own header,
  so a website open in your browser can't control the hub.
- The phone connection needs the pair code. Ten wrong codes from one address block it for 5 minutes.
- When the resident reads web pages, it can only open public internet addresses, never your home network or this computer.
- Programs from the Fabrication Hangar only run after you approve them, in a sandbox with no internet.
- Backups contain the pair code and are readable only by your user. Make a new pair code with `--new-pair-code` if one leaks.

## Settings (`config.json`)
Your settings live in `config.json`, which is created from `config.default.json` the first time Stellar Hub runs.
Updates replace `config.default.json` but never your `config.json`, and new settings from an update are filled in automatically.
- `ollama.model`: set by `./setup.sh`, or change it by hand
- `radio.music_dir`: your music folder (default `~/Music`). `radio.quiet_hours`: no music between these hours (default 23-8)
- `limits`: daily AI calls, café visits, and how many requests can wait at once

## One-time GitHub setup: signing key
So phone updates install over the previous version, every APK must be signed with the same key.
In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
- `KEYSTORE_BASE64`
- `KEYSTORE_PASSWORD`

(The values come in the separate `SIGNING-SECRETS.txt`. Never upload that file to the repo.)
