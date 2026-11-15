#!/bin/sh
# Makes Stellar Hub start automatically with your PC (a systemd user service).
#   sh install-service.sh            install and start it
#   sh install-service.sh remove     stop and remove it
# Logs:  journalctl --user -u stellar-hub -f
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
UNIT="$HOME/.config/systemd/user/stellar-hub.service"

if [ "$1" = "remove" ]; then
    systemctl --user disable --now stellar-hub.service 2>/dev/null || true
    rm -f "$UNIT"
    systemctl --user daemon-reload
    echo "Stellar Hub service removed. Start it by hand with ./start.sh"
    exit 0
fi

command -v systemctl >/dev/null || { echo "This needs systemd (most distros have it)."; exit 1; }
mkdir -p "$(dirname "$UNIT")"
cat > "$UNIT" <<UNIT_EOF
[Unit]
Description=Stellar Hub - AI colony
After=network-online.target ollama.service
Wants=network-online.target

[Service]
WorkingDirectory=$DIR
ExecStart=$(command -v python3) $DIR/run.py
Restart=on-failure
RestartSec=20

[Install]
WantedBy=default.target
UNIT_EOF

systemctl --user daemon-reload
systemctl --user enable --now stellar-hub.service
echo "✓ Stellar Hub is running as a service and will start whenever you log in."
echo "  Dashboard: http://localhost:8080    Logs: journalctl --user -u stellar-hub -f"

if [ "$(loginctl show-user "$USER" -p Linger 2>/dev/null | cut -d= -f2)" != "yes" ]; then
    echo
    printf "Also start it at boot, before you log in? (needs your password) [y/N] "
    read -r ans
    case "$ans" in
        y|Y|yes) sudo loginctl enable-linger "$USER" && echo "✓ It will now start at boot." ;;
        *) echo "OK, it starts when you log in." ;;
    esac
fi
