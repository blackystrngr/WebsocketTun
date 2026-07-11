#!/bin/bash
set -e
echo "========================================="
echo "  SSH WebSocket Tunnel Uninstaller"
echo "========================================="
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)."
    exit 1
fi
systemctl stop ssh-ws-tunnel.service 2>/dev/null || true
systemctl disable ssh-ws-tunnel.service 2>/dev/null || true
rm -f /etc/systemd/system/ssh-ws-tunnel.service
systemctl daemon-reload
rm -f /usr/local/bin/kkmod
echo "Uninstall complete."
