# Changelog

Stellar Hub's update manager shows the entries newer than the version you have.

## v0.15.0
- Added: a before-and-after report for every training run: the same five questions answered by the old model and the new one, side by side in the Training tab (kept for runs that didn't go live too).
- Added: festivals. Every season in every world has one (the 12th-14th): Seedling Day, Sunfire Fair, Harvest Moon and Long Night Lights on the Moon; the Blossom Dance, Firefly Night, Lantern Festival and Frostlight Vigil in the forest; the Shell Gathering, Summer Regatta, Harvest of the Tides and Beacon Night on the ocean. Each special season ends with a 4-day finale (the 20th-23rd: The Great Starfall, Night of a Thousand Wisps, The Great Tide) with twice the events. Decorations go up across the town (bunting, lanterns, fairy lights, petals or sparkles), a visitor and the festival's signature event arrive, and the resident can celebrate once a day for credits and keepsakes.
- Added: life projects. After a personality review, one of its hopes becomes a project of 2-7 stages (a book, a machine, a study, a painting series...). It works on one stage a day at the place that fits, and finishing pays 100 credits, keeps the finished work in its writings and earns a milestone. Projects left alone for three weeks are set aside. See them on the Mind tab.
- Added: visitors who remember. Each visitor builds up how they feel about the resident, calls back to earlier visits, brings news from their travels, gives gifts more often the fonder they are, and comes back more often.
- Added: a spoken goodnight log each night (voice.goodnight_log in config.json), and speech paced by mood: a little faster when it's excited, slower when it's calm or sleepy.
- Added: forest and ocean insides. Every room in both worlds is redrawn: cosy treehouse rooms in the forest (plank walls, vines, hanging lanterns, arched doors, windows on to the night woods) and ship's cabins on the ocean (painted planks, brass rivets, rope rails, ship's lamps, hatch doors, portholes looking underwater). The park becomes a glade under the canopy or a sandy lagoon, and the launch bay becomes the Whisper Woods trailhead or a moon pool with a submarine. Each room keeps its furniture and what happens there.
- Added: 20 new pets: Luna Moth, Starry Cat, Ivy Pup, Puffball Finch, Waxcap Snail, Coontail Axolotl, Lotus Jelly, Crystal Beetle, Vine Owl and Mossy Tortoise in the forest; Sea Moth, Lantern Cat, Seal Pup, Puffin Chick, Pearl Snail, Reef Axolotl, Moon Jelly, Hermit Crab, Sea Owl and Sea Turtle on the ocean. Same jobs and care as before, new drawings.
- Added: Hub health on the Monitor tab: model reply time, AI calls per day against the limit, slow or failed calls, disk use by folder, and a chart of training runs.

## v0.14.0
- Added: real training. The resident learns from its own life: a small LoRA adapter is trained on your graphics card from its corrections, exam answers and reviewed writing (Training tab → Train now, or by itself at night at most once a week). Each run starts from the plain base model, so mistakes can't pile up across versions. A new version (stellar-<name>:vN in Ollama) only goes live if it reaches the exam's pass mark and doesn't score much worse than before; otherwise it's thrown away automatically. Switch to any kept version, or back to the plain model, any time.
- Added: a one-click training toolkit (PyTorch, Transformers, PEFT and llama.cpp's converter, about 4-6 GB) installed into the Stellar Hub folder with uv, so the hub's own Python and your system aren't touched. The base model's original files come from Hugging Face (no account needed). Trainable models: Qwen 2.5 (1.5B-14B), Qwen 3 (0.6B-14B), Llama 3.2 (1B, 3B) and Llama 3.1 8B; the Training tab says what fits your graphics card.
- Added: a developing personality. Every few nights while it sleeps, it looks back and grows: a "who I am" statement it only rewrites with a reason, favourites and dislikes with reasons, up to 7 core memories that shaped it (set personality.max_core in config.json, 3-15; ones it lets go of move to a "once core" archive on the Mind tab and can come back), bonds with you, its pets and visitors (trust, fondness, in-jokes), quirks it notices in itself, hopes and a fear it's facing, and a self-check that pulls it back if it drifts. All of it guides every decision and chat.
- Added: Mind tab → "Who it's becoming" and "How it has changed" (a timeline), with a "Think about it now" button.
- Changed: while it trains, the resident is in a deep rest: turns and chat pause so the graphics card is free. A run cut off by a restart is cleared automatically.
- Changed: Start over keeps the training toolkit and downloads, and the new resident goes back to the plain, untrained model.

## v0.13.6
- Added: each world now colours how the resident talks and what it notices. In the forest it speaks with a gentle storybook warmth and treats the wisps and fireflies as neighbours; on the ocean it plans around the tides and weather and uses the odd sailor's phrase; on the Moon it notices the ringed planet, the stars and the quiet. Its personality stays its own.
- Added: five seasons in every world, each lasting one calendar month: 🌱 Spring, ☀️ Summer, 🍂 Autumn, ❄️ Winter, then a special season with far more events (☄️ Starfall on the Moon, ✨ Wild Magic in the forest, 🌀 Storm Season on the ocean). December 2026 is Winter. Each season recolours the world (autumn leaves, winter snow and frost, magic glow), shifts which events happen and how often (fewer in winter, 2.5x in the special season), and the resident knows the season and lets it shape what it does.
- Added: a 4-day transition at the end of every month: colours, events and the resident's mood blend gradually into the next season ("Autumn turning to Winter").
- Changed: the season shows on the dashboard (under the town and in Hub tab → World) and as an emoji next to your credits in Hub Connect S.

## v0.13.5
- Added: world types. Choose where the colony lives when you first install: the 🌙 Moon colony (the original), the 🌲 Enchanted Forest (a glowing night forest with lanterns, luminous mushrooms, fireflies and a stream) or the 🌊 Ocean world (a boardwalk colony on a moonlit sea, with coral, kelp and a lighthouse). Each world has its own backdrop and colours, its own drawing of every building (a treehouse home, a moon-window library tower, a burrow gallery, a willow-pond park, a wizard-tower trade hall, a fallen-log pet shop, a cherry-tree salon, a toadstool market and a wishing well in the forest; a coral cottage, a lighthouse library, a shipwreck museum and a submarine dock on the ocean), its own name for every building and pet, its own descriptions, and its own mix of events (fireflies, pollen and thunderstorms in the forest; sea glass, high tides and magnetic storms on the ocean).
- Added: switch worlds any time on the dashboard (Hub tab → World). Nothing is lost: the resident, its memories, buildings, credits and pets all move with it, and old memories read with the new names.
- Added: Start over (Hub tab, on the hub computer only). Resets the whole project with a brand-new resident in the world you pick. Type RESET to confirm. Nothing is deleted: the old resident is moved to the resets folder. Your settings, AI model and paired phones are kept.
- Changed: Hub Connect S shows building names from the hub, so they match your world.
- Changed: updating never asks about the world; existing colonies stay on the Moon until you switch.

## v0.13.4
- Fixed: installing an update by hand (downloading the installer) stopped the hub and didn't start it again, and could stop halfway. The installer now stops the hub properly before replacing files, "Start Stellar Hub now" is ticked and runs first, and the hardware check is no longer forced on every update (it's unticked on updates and still in the Start menu).
- Changed: the resident can only answer with buildings it can actually go to right now and actions that exist there. Ollama holds its answer to that list (Ollama 0.5 or newer), so misspelled ids and made-up places ("observatory_library", "10") can't happen. With an older Ollama the hub falls back to correcting mistakes like before.
- Changed: the app tells you when the hub is behind it ("Your hub (v0.13.2) is behind this app (v0.13.4)"), and a page the older hub doesn't have yet no longer shows as "Can't reach Stellar Hub". The Colony tab's economy card says to update the hub instead.

## v0.13.3
- Added: memory that reaches back through its whole life. Every memory's keywords now go into an index, so recall finds a fitting memory from months ago instead of only the newest 1,500 (about five days at the old pace). Memories from before this update are indexed automatically in the background.
- Added: the library's manual shelf. It holds every building's manual, even for places not unlocked yet (browse_manuals, then read_manual). Each turn, a short page from the manual that best fits what it's doing, or just got wrong, appears next to its memories.
- Added: a Docker check. The installer looks for Docker Desktop (and offers the download page if it's missing), then can check Docker is running and download the sandbox's Python image. The hub checks again at start-up and before each coding test, and the Workshop tab shows the sandbox's status with a "Check again" button.
- Added: the colony economy tracker, for you and the resident. The Monitor tab has a 30-day chart (earned, spent, balance), totals by category, the biggest items this week, and warnings (debt, weeks of overspending, one thing eating most of the budget, credits piling up). The app's Colony tab has a short version, and the resident gets a money note every Monday.
- Added: training controls, ready for v0.14 (new Training tab). Review what it would learn from (keep, skip or correct each item; risky ones are flagged automatically), teach corrections, set what it learns from and how much of its own writing to use, the pass mark, how many old versions to keep, and how strongly to train. The exam is a fixed set of questions with expected answers that a new version must pass (or it's rolled back); you can run it on today's model now. "Preview the training set" downloads exactly what it would train on.
- Added: automatic tests (22 of them, covering turns, memory, the workshop, devices and roles, money, training, pictures and updates). GitHub runs them before every build; if one fails, nothing is released.
- Changed: turns every 20 minutes. If your setting was 12 or 30 (the old automatic values), it moves to 20 once; anything else you set stays.
- Changed: when the resident names a building by its title ("uplink_cafe") or a plot number ("10"), or picks an action that's done somewhere else, the hub works out what it meant and does it, and tells it the right id. The building list shows each id next to its name.
- Changed: if the sandbox is offline, coding challenges wait, and a missed week doesn't lower its level.
- Fixed: building names with accents (Uplink Café) didn't match when written without them, and "adopted a Orbit Moth" now reads "an".

## v0.13.2
- Added: more than one phone, each with its own username. In Hub Connect S you enter the address and pair code, create a username (3-20 characters, unique; "This is another device of mine" adds a second phone to your name), then wait for the owner to approve it.
- Added: roles. Owner: everything. Member: watch, chat, give goals, write letters, take a turn, play chess. Viewer: watch only. Approve, change or remove devices on the dashboard (Hub tab → People & devices) or in the owner's app (Hub tab).
- Added: the resident knows each person by name. Chats show who's talking (several people can join one chat), goals and letters say who they're from, it remembers meeting new people, and it can write letters to them (they appear in that person's inbox).
- Changed: the pair code is now only an invitation. Each approved phone gets its own key, so removing a phone locks it out without changing anyone else's. Members and viewers only see their own letters and don't get request, program or monitor notifications.
- Changed: after updating, every phone (yours too) joins once with a username. Approve your own phone on the dashboard as Owner.

## v0.13.1
- Fixed: Hub Connect S crashed when opening the new Build tab.

## v0.13.0
- Added: the Mechanical Workshop (unlock for 300). The resident buys parts at the Department Store (frames, wheels, gears, motors, sensors, circuits, batteries, solar panels…), designs machines, and a simulator checks every design: required parts, power and frame space. Parts are only used when it passes.
- Added: 10 machines with daily colony bonuses: Watering Bot, Seed Sorter, Telescope Tracker, Music Box Bot, Cleaning Drone, Solar Array, Delivery Drone (5% store discount), Pet Feeder, Repair Bot (halves wear) and Comet Catcher. Machines wear down slowly; a broken machine does nothing until it's serviced (maintain_machine, one spare gear).
- Added: weekly goals. A coding challenge at the Fab Hangar every week (16 challenges in 6 levels), checked by automatic tests that run in the sandbox straight away with no approval needed. Any other program still waits for you. A machine to build at the Mechanical Workshop every week. Passing makes the next goal harder; missing a week makes it easier.
- Added: your own goals, from the dashboard's new Workshop tab or the app's new Build tab. Coding goals with tests are checked automatically; anything else comes back to you to review.
- Added: real-world project plans, about once a week: ESP32/Arduino builds, 3D prints (OpenSCAD), hand-tools and crafts, and smart-home gadgets. Each has a parts list, tools, steps and code or files, downloadable from the dashboard and the app. Electronics stay low-voltage (USB or batteries), and every plan carries a "Check this before you build" note.
- Added: the skill notebook. Passing code, working machines and finished plans are saved, and the best matching examples go into the resident's prompt next time, so it gets better at things over time. A new "building" skill joins coding.
- Added: space weather with light gameplay effects: stardust drift (common; a few credits swept up), dust storms (the walkway closes for a few hours, so it stays where it is) and comet passes (rare and slow; the tail drops set pieces, more with a Comet Catcher). All three can be started from the Hub tab too.
- Added: idle animations on the dashboard and in the app: looking around, stretching, yawning and dozing, waving when you open it, sitting and reading, and dancing while you listen together. They're picked by mood, time of day and place.
- Added: colony traffic that grows with the colony (maintenance bots, delivery drones from the store to whoever just shopped, a cargo shuttle once the Spaceport is built, and the lift car), plus building life: windows switching on and off at night and blinking roof beacons.
- Added: customization the resident chooses itself: six accessories (antenna cap, beanie, crown, bubble helmet, scarf, comet trail) and building paint jobs (8 colours) with roof lights (6 colours), all from the Department Store.
- Added: the Gear Beetle's new job, maintain_machines (services the most worn machine), and its salvage now turns up spare parts.
- Changed: turns every 12 minutes instead of 30. If your settings still had the old defaults, they move to 12 minutes and 500 AI calls a day once (anything you set yourself is kept). Needs and visitors are scaled so a day feels the same.
- Changed: when a pet slot opens up (a pet passes away or is taken), the adoption price goes back to the base price.
- Fixed: "The last update didn't finish" showed after an update that had worked, or after running the installer yourself. If the hub is already on the version it was updating to, it now shows "Updated ✓".

## v0.12.1
- Fixed: on Windows an update could get stuck on "Installing": the helper waited for the restarted Stellar Hub as well as the installer. It now waits for the installer only (at most 10 minutes) and closes any other copy of Stellar Hub that would block it.
- Fixed: "ConnectionAbortedError" tracebacks in the console when a page or the phone closed mid-reply.
- Changed: the dashboard suggests running the installer yourself if an update takes too long, and says so after a restart if the last update didn't finish.

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
