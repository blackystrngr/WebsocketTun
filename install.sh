#!/bin/bash
set -e

echo "========================================="
echo "  SSH WebSocket Tunnel Installer"
echo "========================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)."
    exit 1
fi

# Install system dependencies
apt update
apt install -y python3 python3-pip curl git

# Install Python dependencies
pip3 install -r requirements.txt

# --- Interactive configuration ---
echo ""
echo "Please provide the following configuration:"

read -p "Your domain (e.g., tunnel.example.com): " DOMAIN
read -p "Your Cloudflare account email: " EMAIL
read -p "Your Cloudflare API Token: " CF_TOKEN
read -p "WebSocket HTTP port [8080]: " WS_PORT
WS_PORT=${WS_PORT:-8080}
read -p "WebSocket HTTPS port [8443]: " TLS_PORT
TLS_PORT=${TLS_PORT:-8443}
read -p "SSH host [127.0.0.1]: " SSH_HOST
SSH_HOST=${SSH_HOST:-127.0.0.1}
read -p "SSH port [22]: " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

# Write .env file
cat > .env <<EOF
DOMAIN=${DOMAIN}
EMAIL=${EMAIL}
CF_API_TOKEN=${CF_TOKEN}
WS_PORT=${WS_PORT}
TLS_PORT=${TLS_PORT}
SSH_HOST=${SSH_HOST}
SSH_PORT=${SSH_PORT}
NO_CERT=false
DEBUG=false
EOF

echo ""
echo "Configuration saved to .env"

# Install as a systemd service
cat > /etc/systemd/system/ssh-ws-tunnel.service <<EOF
[Unit]
Description=SSH WebSocket Tunnel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ssh-ws-tunnel.service
systemctl start ssh-ws-tunnel.service

# Create the kkmod command
mkdir -p /usr/local/bin
ln -sf $(pwd)/scripts/kkmod /usr/local/bin/kkmod
chmod +x /usr/local/bin/kkmod

echo "========================================="
echo "Installation complete!"
echo "Service status: systemctl status ssh-ws-tunnel"
echo "Dashboard: kkmod"
echo "========================================="
