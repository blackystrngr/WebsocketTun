#!/bin/bash
set -e

# ============================================
# Colors
# ============================================
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

# ============================================
# 1. System updates & base packages
# ============================================
apt update
apt install -y python3 python3-pip curl git openssl iptables iptables-persistent

# ============================================
# 2. Disable IPv6 system-wide (persistent)
# ============================================
echo -e "${YELLOW}Disabling IPv6...${NC}"
cat >> /etc/sysctl.conf <<EOF
# Disable IPv6
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
EOF
sysctl -p

# Also disable for current session
echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6
echo 1 > /proc/sys/net/ipv6/conf/default/disable_ipv6
echo 1 > /proc/sys/net/ipv6/conf/lo/disable_ipv6

# Blacklist IPv6 modules (optional, but thorough)
cat >> /etc/default/grub <<EOF
GRUB_CMDLINE_LINUX="ipv6.disable=1"
EOF
update-grub

echo -e "${GREEN}IPv6 disabled. Reboot recommended after installation.${NC}"

# ============================================
# 3. Enable IP forwarding (for NAT/gateway)
# ============================================
echo -e "${YELLOW}Enabling IP forwarding...${NC}"
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

# ============================================
# 4. Python dependencies
# ============================================
pip3 install -r requirements.txt

# ============================================
# 5. Interactive configuration
# ============================================
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

# ============================================
# 6. Write .env file
# ============================================
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

# ============================================
# 7. Configure iptables (allow chosen ports + SSH)
# ============================================
echo -e "${YELLOW}Configuring iptables...${NC}"

# Convert comma lists to individual ports
IFS=',' read -ra WS_ARRAY <<< "$WS_PORTS"
IFS=',' read -ra TLS_ARRAY <<< "$TLS_PORTS"

# Flush existing rules (be careful – you may want to backup)
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow SSH (port 22) – so you don't lose access
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow WebSocket ports (HTTP and HTTPS)
for port in "${WS_ARRAY[@]}"; do
    iptables -A INPUT -p tcp --dport "$port" -j ACCEPT
done
for port in "${TLS_ARRAY[@]}"; do
    iptables -A INPUT -p tcp --dport "$port" -j ACCEPT
done

# Allow forwarding (if you want to use as a gateway)
iptables -A FORWARD -j ACCEPT   # or more restrictive rules

# Save iptables rules (persist after reboot)
netfilter-persistent save
echo -e "${GREEN}iptables rules saved.${NC}"

# ============================================
# 8. Adjust SSH to allow tunneling
# ============================================
echo -e "${YELLOW}Ensuring SSH allows tunneling...${NC}"
if grep -q "^AllowTcpForwarding" /etc/ssh/sshd_config; then
    sed -i 's/^AllowTcpForwarding.*/AllowTcpForwarding yes/' /etc/ssh/sshd_config
else
    echo "AllowTcpForwarding yes" >> /etc/ssh/sshd_config
fi

# Also ensure GatewayPorts if needed
if ! grep -q "^GatewayPorts" /etc/ssh/sshd_config; then
    echo "GatewayPorts yes" >> /etc/ssh/sshd_config
fi

systemctl restart sshd

# ============================================
# 9. Setup systemd service
# ============================================
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

# ============================================
# 10. Create kkmod command
# ============================================
ln -sf $(pwd)/scripts/kkmod /usr/local/bin/kkmod
chmod +x /usr/local/bin/kkmod

# ============================================
# 11. Final message
# ============================================
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "Service status: ${YELLOW}systemctl status ssh-ws-tunnel${NC}"
echo -e "Dashboard: ${YELLOW}kkmod${NC}"
echo -e "IPv6 has been disabled – a ${RED}reboot${NC} is recommended."
echo -e "Your firewall is now active. Ensure your Cloudflare DNS points to this server."
echo -e "${GREEN}=========================================${NC}"
