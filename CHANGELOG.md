# Changelog

Stellar Hub's update manager shows the entries newer than the version you have.

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
