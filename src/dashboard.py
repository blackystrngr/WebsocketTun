import os
import sys
from .service_manager import ServiceManager
from .utils import load_config, print_header, print_success, print_error, print_info

def show_dashboard():
    config = load_config()
    print_header("SSH WebSocket Tunnel Dashboard (kkmod)")
    status = ServiceManager.status()
    if status == "active":
        print_success(f"Service Status: {status.upper()}")
    else:
        print_error(f"Service Status: {status.upper()}")

    ws_ports = config.get("ws_ports", [8080])
    tls_ports = config.get("tls_ports", [8443])
    print_info(f"WebSocket (HTTP) ports:  {', '.join(map(str, ws_ports))}")
    print_info(f"WebSocket (HTTPS) ports: {', '.join(map(str, tls_ports))}")
    print_info(f"Domain: {config.get('domain', 'N/A')}")

    print("\n[1] Show recent logs")
    print("[2] Restart service")
    print("[3] Stop service")
    print("[4] Edit configuration (will restart)")
    print("[0] Exit")

    choice = input("\nSelect option: ").strip()
    if choice == "1":
        print(ServiceManager.logs())
        input("Press Enter to continue...")
    elif choice == "2":
        ServiceManager.restart()
        print_success("Service restarted.")
    elif choice == "3":
        ServiceManager.stop()
        print_info("Service stopped.")
    elif choice == "4":
        editor = os.environ.get("EDITOR", "nano")
        config_file = ".env" if os.path.exists(".env") else "config.yaml"
        os.system(f"{editor} {config_file}")
        ServiceManager.restart()
        print_success("Configuration updated and service restarted.")

def main():
    while True:
        show_dashboard()

if __name__ == "__main__":
    main()
