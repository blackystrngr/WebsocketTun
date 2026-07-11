import argparse

class CLIHandler:
    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(description="SSH WebSocket Tunnel")
        parser.add_argument("-d", "--domain", help="Domain name")
        parser.add_argument("-e", "--email", help="Cloudflare email")
        parser.add_argument("-t", "--token", help="Cloudflare API token")
        parser.add_argument("--ws-port", type=int, help="Plain WebSocket port")
        parser.add_argument("--tls-port", type=int, help="TLS WebSocket port")
        parser.add_argument("--ssh-host", default="127.0.0.1", help="SSH host")
        parser.add_argument("--ssh-port", type=int, default=22, help="SSH port")
        parser.add_argument("--no-cert", action="store_true", help="Skip cert issuance")
        parser.add_argument("--debug", action="store_true", help="Debug logging")
        parser.add_argument("-c", "--config", help="Path to YAML config file")
        return parser.parse_args()
