#!/bin/sh
# Start Stellar Hub and open the town viewer.
cd "$(dirname "$0")"
( sleep 2; command -v xdg-open >/dev/null && xdg-open http://localhost:8080 >/dev/null 2>&1 ) &
exec python3 run.py "$@"
