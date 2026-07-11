#!/usr/bin/env python3
import asyncio
import sys
from .cli import CLIHandler
from .cert_manager import CloudflareCertManager
from .proxy_server import SSHWebSocketProxy
from .utils import setup_logging, load_config, print_header, print_success, print_error, print_info
from .auto_updater import GitAutoUpdater
from .console import ConsoleHandler

async def run():
    print_header("SSH WebSocket Tunnel")
    config = load_config()
    setup_logging(config.get("debug", False))

    cert_path = key_path = None
    ssl_enabled = False

    if not config.get("no_cert", False):
        cert_mgr = CloudflareCertManager(
            domain=config["domain"],
            email=config.get("email", ""),          # may be empty
            api_token=config["token"],
            cert_source=config.get("cert_source", "acme"),
            cert_file=config.get("cert_file"),
            key_file=config.get("key_file")
        )
        if cert_mgr.request_certificate():
            cert_path, key_path, ca_path = cert_mgr.get_certificate_paths()
            if cert_path and key_path:
                # Validate the certificate
                if cert_mgr.validate_certificate(cert_path, key_path, ca_path):
                    ssl_enabled = True
                    print_success("SSL will be enabled with the valid certificate.")
                else:
                    print_error("Certificate validation failed – we will continue WITHOUT SSL.")
                    ssl_enabled = False
            else:
                print_error("Could not locate certificate files – continuing WITHOUT SSL.")
                ssl_enabled = False
        else:
            print_error("Certificate issuance failed – continuing WITHOUT SSL.")
            ssl_enabled = False
    else:
        print_info("Certificate skipped (NO_CERT=true) – SSL disabled.")

    # If SSL is not enabled, we force cert_path and key_path to None
    if not ssl_enabled:
        cert_path = key_path = None
        print_info("WSS (TLS) will be disabled. Only plain WS will work.")

    proxy = SSHWebSocketProxy(
        ws_ports=config.get("ws_ports", [8080]),
        tls_ports=config.get("tls_ports", [8443]),
        ssh_host=config.get("ssh_host", "127.0.0.1"),
        ssh_port=config.get("ssh_port", 22),
        ssl_cert=cert_path,
        ssl_key=key_path,
    )

    updater = GitAutoUpdater(interval=30)
    proxy_task = asyncio.create_task(proxy.start())
    updater_task = asyncio.create_task(updater.run())

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
        print_info("No TTY – console disabled.")

    tasks = [proxy_task, updater_task]
    if console_task:
        tasks.append(console_task)

    try:
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
        print_success("Goodbye.")

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
