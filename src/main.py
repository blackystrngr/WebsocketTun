#!/usr/bin/env python3
import asyncio
import sys
import os
from .cli import CLIHandler
from .cert_manager import CloudflareCertManager
from .proxy_server import SSHWebSocketProxy
from .utils import setup_logging, load_config
from .auto_updater import GitAutoUpdater
from .console import ConsoleHandler

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
        ws_ports=config.get("ws_ports", [8080]),
        tls_ports=config.get("tls_ports", [8443]),
        ssh_host=config.get("ssh_host", "127.0.0.1"),
        ssh_port=config.get("ssh_port", 22),
        ssl_cert=cert_path,
        ssl_key=key_path,
    )

    # Start auto-updater (if git repo exists)
    updater = GitAutoUpdater(interval=30)
    
    # Create tasks
    proxy_task = asyncio.create_task(proxy.start())
    updater_task = asyncio.create_task(updater.run())

    # Console handler – only if stdin is a TTY (i.e., not running as a service)
    console_task = None
    if sys.stdin.isatty():
        async def shutdown():
            proxy_task.cancel()
            updater_task.cancel()
            if console_task:
                console_task.cancel()
        console = ConsoleHandler(shutdown_callback=shutdown)
        console_task = asyncio.create_task(console.run())
    else:
        print("No TTY detected – console disabled. (Running as service?)")

    try:
        tasks = [proxy_task, updater_task]
        if console_task:
            tasks.append(console_task)
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        print("\nInterrupted. Shutting down...")
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("Goodbye.")

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
