#!/bin/sh
# Stellar Hub setup: detects your hardware and drivers, picks and downloads a model,
# and checks the optional extras. Options: --yes (accept all), --check (report only)
cd "$(dirname "$0")"
exec python3 setup_hub.py "$@"
