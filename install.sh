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

# Create config if missing
if [ ! -f .env ] && [ ! -f config.yaml ]; then
    cp .env.example .env
    echo "Please edit .env with your domain, email, and Cloudflare API token."
    echo "Then run the installer again or start manually."
    exit 1
fi

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
