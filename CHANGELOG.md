# Changelog

Stellar Hub's update manager shows the entries newer than the version you have.

## v0.12.0
- Added: the Upper Street. When the walkway is full, the resident can buy a raised deck (1500 credits, about 8 hours) with 14 more plots (16-30), reached by a glass lift beside the Home Dome. It rides the lift between levels on the dashboard and in the app.
- Added: the Department Store (a new building, free to build). Once it's open, all shopping happens there; the Credit Vault keeps your balance and history.
- Added: 64 new curios in 23 sets of 2, 3 or 4 (192 curios in all). Each set's pieces turn up mostly from one place: expeditions, meteor showers, visitors, the trader, pets, the park, the observatory or the Exchange. Completing a set pays a bonus. A complete set fits in one showcase spot, and taking it down splits it back into pieces.
- Added: the Stellar Museum (unlock for 400). Donate a complete set to a permanent exhibit (reputation, a daily stipend and more visitors) or sell it to the curator for much more than its pieces.
- Added: four new pets: Signal Jelly (music: picks songs and writes radio segments for the show), Gear Beetle (mechanics: checks programs, salvages parts), Star Owl (astronomy: sky surveys, spots fragments) and Moss Tortoise (garden: feeds plants and sets their lights). Seven new jobs.
- Added: pet skill levels (1-10): practice makes each pet's job cheaper.
- Added: the Monitor (a new dashboard tab and a card in the app's Hub tab). It tracks pets, money and the model separately and flags anything unusual: failed or invalid turns, loops, slow turns, AI-call limits, big spends, debt, spending spikes, quick health drops and overwork. Alerts also come as phone notifications.
- Changed: up to 6 pets, and each pet it already has makes the next adoption cost 50% more.

## v0.11.0
- Added: pets and the Pet Shop (unlock for 250 credits). Six species, each with a speciality, a lifespan and its own hours: Orbit Moth (small repetitive tasks, night), Drone Cat (watching, night), Rover Pup (fetching, day), Comet Finch (words, day), Crystal Snail (careful long jobs, any time, lives longest) and Nebula Axolotl (care, night).
- Added: the resident trains each pet for one of 10 jobs (watering plants, sorting curios, night watch, Exchange watch, scouting the uplink, drafting logs, proofreading, tidying memories, tending other pets, fetching) and sets its shifts a day. Specialised jobs cost a pet less energy.
- Added: pet needs: energy (rest), hunger, happiness and health. Overwork builds strain: sick, then injured, then critical. A critical pet can be rescued at a steep price (debt allowed); otherwise after 24 hours the Colony Welfare Office takes it and fines the resident. Debt blocks shopping until paid off. Pets grow up, grow old and pass away at the end of their lifespan.
- Added: pets run on the computer's spare time. Simple jobs are plain code; thinking jobs use a small "pet brain" model (qwen3:0.6b, download it from the dashboard's Pets tab) and only run while the CPU and graphics card are idle.
- Added: a Pets tab on the dashboard, a Pets card in the app's Colony tab, pets trotting along the walkway to their jobs, and the Pet Shop's own room with a habitat pen for each pet.

## v0.10.0
- Added: building manuals. The resident gets a manual when a blueprint unlocks, reads it when the building opens, and can reread any of them (read_manual). Greenhouse care guide and a care card for each new species (read_plant_guide).
- Added: a voice. Colony logs and a new daily radio show (host_show) are spoken and sent to your phone. Every chat reply has a 🔊 Hear it button. It uses Windows' built-in voice out of the box, or install the natural Piper voice from the dashboard's Hub tab.
- Added: decorate every building. 19 pieces of furniture (posters, neon signs, lamps, a robot buddy, an arcade cabinet, mobiles, rugs…) bought at the Credit Vault and placed in each building's own wall, floor, ceiling and rug spots (decorate).
- Added: visitors. Travellers like Captain Orla and Old Tamsin stop by a few times a week; the resident can talk with them (talk_to_visitor), and they sometimes leave a curio. They show up in the colony and inside rooms.
- Added: room moods: rooms glow warm when it's happy, pink when it's listening with you, and blue when it's low. Neglected plants droop.
- Added: a photo album. It snapshots big moments (milestones, blooms, new buildings, visitors, gifts) automatically.
- Added: gifts for you: paintings, songs, poems and spare curios (make_gift), with Save buttons in the app and dashboard.
- Added: your music taste. With "Share listening" on in Stellar Disc (v3.5.0+) and Hub Connect S, it learns what you finish and skip, knows your favourites, and listens along while the app is open.
- Changed: the dashboard is organised into tabs: Today, Colony, Creations, Mind, Pets and Hub.

## v0.9.1
- Fixed: Check for updates could miss new versions, because it trusted GitHub's "Latest" label, which was stuck on an old release. The hub now looks through all releases and picks the newest one that has a file for your install. The dashboard also shows the newest version it found on GitHub.
- Added: Stop event, in the dashboard and in the app's Colony tab. The app can now start space events too.
- Fixed: with a hub older than the app, the resident vanished from the colony view. It now stands at its building's door until the hub can send the room.
- Changed: the app says plainly when the hub on your PC needs updating, including when sharing music fails for that reason.

## v0.9.0
- Added: follow your resident inside. Every one of the 16 buildings has its own room in Hub Connect S, showing real things from the colony: the paintings hung in the Gallery, the plants in the Greenhouse, the Home Dome showcase, the Exchange's best curios and more. The resident walks to the easel, the bed, the telescope or a painting on the wall depending on what it's doing, and wanders around between turns.
- Added: walking in and out of buildings. Airlocks open, the resident steps inside or back out, and little effects show what it's doing (notes, paint, water, sleep).
- Added: phone music through Stellar Disc. Share your phone's song list from the Hub tab, and at the Radio Tower your resident can pick a song that Stellar Disc plays on your phone, only while Hub Connect S is open.
- Added: a Take a turn button right under the colony, with Go inside / Outside and Follow on/off.
- Changed: Live chat is now at the top of the Chat tab.

## v0.8.4
- Fixed: Hub Connect S crashed when you tapped Save & test (and could crash on opening once paired) on Android 14 and newer. A required network permission for the background notification check was missing.
- Added: if the app ever crashes, the next time it opens it shows what happened, so it can be screenshotted and fixed.
- Changed: if background notifications can't be set up, the app shows a short message instead of closing.
- Added: Windows update watchdog. It runs the installer, then makes sure Stellar Hub starts again whether the install worked or not. If it failed, the dashboard explains what happened and offers Try again.
- Added: the dashboard shows "Reconnecting…" (or "Updating…") while the hub is restarting, and reloads itself onto the new version when it's back.

## v0.8.3
- Fixed: on Windows, update checks and the resident's web research failed with a certificate error. The installer now includes a certificate bundle.
- Added: Windows setup offers a firewall rule that lets your phone in over Tailscale only (the usual reason the app says "Connecting…").
- Fixed: the app says when it isn't paired yet, and explains connection problems (wrong code, can't reach the hub, bad address) instead of "Connecting…" forever.

## v0.8.2
- Added: update manager. The hub checks GitHub twice a day, the dashboard shows what's new, and Update now installs it (Windows: quiet installer; Linux: in-place update). Downloads are checked against SHA-256 checksums, and your resident is backed up first.
- Added: security hardening. Websites open in your browser can't control the hub, wrong pair codes are rate-limited, the resident can't be tricked into opening pages on your home network, and backups are private to your user.
- Changed: settings now live in config.json, created from config.default.json. Updates never overwrite your settings.
- Changed: setup waits for Ollama to finish starting before downloading a model. The hub uses another downloaded model if the chosen one is missing, and the dashboard explains model problems.
- Changed: releases are race-proof, and each file gets a .sha256 checksum.

## v0.8.0
- Added: Curio Exchange (sell, wanted board, trade-ups, auctions), descriptions for all 128 curios, and the resident's own notes on first finds.

## v0.7.0
- Added: hobbies with skill levels, Starlight Gallery, Low-G Park, Radio Studio, Orbital Station, astronomy, 128 curios, puzzles and chess, the multi-floor Home Dome showcase, weekly digest, memory search, photo mode and personality traits.

## v0.6.0
- Added: Windows installer and Windows support.

## v0.5.0
- Added: choosing building plots, nightly backups, start with the PC, sleep and dreams, day/night, live chat, emotes, space events and milestones.

## v0.4.0
- Added: questions, phone notifications, the Credit Vault economy, Greenhouse, Radio Tower, Archive Vault, Spaceport expeditions, Fabrication Hangar and the setup script.
