#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  SSH WebSocket Tunnel Installer (Ubuntu)${NC}"
echo -e "${BLUE}=========================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo).${NC}"
    exit 1
fi

# Install system packages (including certbot)
apt update
apt install -y python3 python3-pip curl git openssl iptables iptables-persistent certbot python3-certbot-dns-cloudflare

# Disable IPv6
echo -e "${YELLOW}Disabling IPv6...${NC}"
cat >> /etc/sysctl.conf <<EOF
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
EOF
sysctl -p
echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6
echo 1 > /proc/sys/net/ipv6/conf/default/disable_ipv6
echo 1 > /proc/sys/net/ipv6/conf/lo/disable_ipv6
cat >> /etc/default/grub <<EOF
GRUB_CMDLINE_LINUX="ipv6.disable=1"
EOF
update-grub

sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

pip3 install -r requirements.txt

# Certificate source
echo -e "${YELLOW}Select certificate source:${NC}"
echo "  1) Cloudflare Origin Certificate (you provide PEM and KEY files)"
echo "  2) ACME (Let's Encrypt) via Cloudflare DNS (automated)"
read -p "Enter choice [1-2]: " CERT_CHOICE

CERT_SOURCE=""
CERT_FILE=""
KEY_FILE=""
EMAIL=""
CF_TOKEN=""

if [ "$CERT_CHOICE" = "1" ]; then
    CERT_SOURCE="cloudflare"
    read -p "Path to certificate PEM file: " CERT_FILE
    read -p "Path to private key file: " KEY_FILE
    if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
        echo -e "${RED}Certificate or key file not found.${NC}"
        exit 1
    fi
else
    CERT_SOURCE="acme"
    read -p "Your Cloudflare account email: " EMAIL
    read -p "Your Cloudflare API Token: " CF_TOKEN
fi

read -p "Your domain (e.g., tunnel.example.com): " DOMAIN
read -p "WebSocket HTTP ports (comma-separated) [8080]: " WS_PORTS
WS_PORTS=${WS_PORTS:-8080}
read -p "WebSocket HTTPS ports (comma-separated) [8443]: " TLS_PORTS
TLS_PORTS=${TLS_PORTS:-8443}
read -p "SSH host [127.0.0.1]: " SSH_HOST
SSH_HOST=${SSH_HOST:-127.0.0.1}
read -p "SSH port [22]: " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

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
CERT_SOURCE=${CERT_SOURCE}
CERT_FILE=${CERT_FILE}
KEY_FILE=${KEY_FILE}
EOF

echo -e "${GREEN}Configuration saved to .env${NC}"

# iptables
echo -e "${YELLOW}Configuring iptables...${NC}"
IFS=',' read -ra WS_ARRAY <<< "$WS_PORTS"
IFS=',' read -ra TLS_ARRAY <<< "$TLS_PORTS"
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
for port in "${WS_ARRAY[@]}"; do
    iptables -A INPUT -p tcp --dport "$port" -j ACCEPT
done
for port in "${TLS_ARRAY[@]}"; do
    iptables -A INPUT -p tcp --dport "$port" -j ACCEPT
done
iptables -A FORWARD -j ACCEPT
netfilter-persistent save

# SSH
if grep -q "^AllowTcpForwarding" /etc/ssh/sshd_config; then
    sed -i 's/^AllowTcpForwarding.*/AllowTcpForwarding yes/' /etc/ssh/sshd_config
else
    echo "AllowTcpForwarding yes" >> /etc/ssh/sshd_config
fi
if ! grep -q "^GatewayPorts" /etc/ssh/sshd_config; then
    echo "GatewayPorts yes" >> /etc/ssh/sshd_config
fi
systemctl restart sshd

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

# Create kkmod with proper path resolution
mkdir -p scripts
cat > scripts/kkmod << 'KKMOD'
#!/bin/bash
SCRIPT_PATH="$(readlink -f "$0")"
cd "$(dirname "$SCRIPT_PATH")/.." || exit
python3 -c "from src.dashboard import main; main()"
KKMOD
chmod +x scripts/kkmod
ln -sf $(pwd)/scripts/kkmod /usr/local/bin/kkmod

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "Service status: ${YELLOW}systemctl status ssh-ws-tunnel${NC}"
echo -e "Dashboard: ${YELLOW}kkmod${NC}"
echo -e "IPv6 disabled – ${RED}reboot recommended.${NC}"
echo -e "${GREEN}=========================================${NC}"
