#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  SSH WebSocket Tunnel Installer${NC}"
echo -e "${BLUE}=========================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo).${NC}"
    exit 1
fi

# Install system dependencies
apt update
apt install -y python3 python3-pip curl git openssl

# Install Python dependencies
pip3 install -r requirements.txt

echo -e "${YELLOW}Please provide the following configuration:${NC}"

read -p "Your domain (e.g., tunnel.example.com): " DOMAIN
read -p "Your Cloudflare account email: " EMAIL
read -p "Your Cloudflare API Token: " CF_TOKEN
read -p "WebSocket HTTP ports (comma-separated, e.g., 8080,8081) [8080]: " WS_PORTS
WS_PORTS=${WS_PORTS:-8080}
read -p "WebSocket HTTPS ports (comma-separated, e.g., 8443,8444) [8443]: " TLS_PORTS
TLS_PORTS=${TLS_PORTS:-8443}
read -p "SSH host [127.0.0.1]: " SSH_HOST
SSH_HOST=${SSH_HOST:-127.0.0.1}
read -p "SSH port [22]: " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

# Write .env
cat > .env <<EOF
DOMAIN=${DOMAIN}
EMAIL=${EMAIL}
CF_API_TOKEN=${CF_TOKEN}
WS_PORTS=${WS_PORTS}
TLS_PORTS=${TLS_PORTS}
SSH_HOST=${SSH_HOST}
SSH_PORT=${SSH_PORT}
NO_CERT=false
DEBUG=false
EOF

echo -e "${GREEN}Configuration saved to .env${NC}"

# Systemd service
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

ln -sf $(pwd)/scripts/kkmod /usr/local/bin/kkmod
chmod +x /usr/local/bin/kkmod

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "Service status: ${YELLOW}systemctl status ssh-ws-tunnel${NC}"
echo -e "Dashboard: ${YELLOW}kkmod${NC}"
echo -e "${GREEN}=========================================${NC}"
