# SSH WebSocket Tunnel with Cloudflare SSL, Auto‑Update & Colored Console

A secure SSH‑over‑WebSocket proxy that automatically obtains SSL certificates via Cloudflare DNS, validates them against the CA, and provides a colorful interactive console.

## Features
- 🔐 Automatic SSL (Let's Encrypt + Cloudflare DNS‑01) with **real‑time CA validation**
- 🌈 **Colored** headers, status messages, and logs
- 🌐 Cloudflare CDN ready (supports multiple WS and WSS ports)
- 🔄 Git auto‑sync & restart every 30 seconds
- 📊 Dashboard command `kkmod` (colored)
- 🧹 Clean uninstaller
- 🚀 One‑click installer

## Quick Start
1. Clone this repo or copy the files.
2. Run `sudo ./install.sh` and answer the prompts.
3. Monitor with `kkmod`.

## Client Connection
- WS: `ws://your-domain:8080` (or custom HTTP port)
- WSS: `wss://your-domain:8443` (or custom HTTPS port)

## Uninstall
`sudo ./uninstall.sh`
