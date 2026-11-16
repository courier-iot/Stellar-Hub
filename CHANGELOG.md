# Changelog

Stellar Hub's update manager shows the entries newer than the version you have.

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
