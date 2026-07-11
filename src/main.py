#!/usr/bin/env python3
import asyncio
import sys
from .cli import CLIHandler
from .cert_manager import CloudflareCertManager
from .proxy_server import SSHWebSocketProxy
from .utils import setup_logging, load_config
from .auto_updater import GitAutoUpdater

async def run():
    config = load_config()
    setup_logging(config.get("debug", False))

    cert_path = key_path = None
    if not config.get("no_cert", False):
        cert_mgr = CloudflareCertManager(
            domain=config["domain"],
            email=config["email"],
            api_token=config["token"]
        )
        if not cert_mgr.request_certificate():
            print("Certificate issuance failed. Exiting.")
            sys.exit(1)
        cert_path, key_path, _ = cert_mgr.get_certificate_paths()
        if not cert_path or not key_path:
            print("Could not locate certificate files. Exiting.")
            sys.exit(1)

    proxy = SSHWebSocketProxy(
        ws_port=config.get("ws_port", 8080),
        tls_port=config.get("tls_port", 8443),
        ssh_host=config.get("ssh_host", "127.0.0.1"),
        ssh_port=config.get("ssh_port", 22),
        ssl_cert=cert_path,
        ssl_key=key_path,
    )

    # Start auto-updater (if git repo exists)
    updater = GitAutoUpdater(interval=30)
    proxy_task = asyncio.create_task(proxy.start())
    updater_task = asyncio.create_task(updater.run())

    try:
        await asyncio.gather(proxy_task, updater_task)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
