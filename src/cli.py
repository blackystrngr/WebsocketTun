import argparse

class CLIHandler:
    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(description="SSH WebSocket Tunnel")
        parser.add_argument("-d", "--domain", help="Domain name")
        parser.add_argument("-e", "--email", help="Cloudflare email")
        parser.add_argument("-t", "--token", help="Cloudflare API token")
        parser.add_argument("--ws-ports", help="Comma‑separated WS ports")
        parser.add_argument("--tls-ports", help="Comma‑separated WSS ports")
        parser.add_argument("--ssh-host", default="127.0.0.1")
        parser.add_argument("--ssh-port", type=int, default=22)
        parser.add_argument("--no-cert", action="store_true")
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("-c", "--config", help="YAML config file")
        return parser.parse_args()
