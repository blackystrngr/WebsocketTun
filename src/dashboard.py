import os
import sys
from .service_manager import ServiceManager
from .utils import load_config

def show_dashboard():
    config = load_config()
    print("\n" + "="*50)
    print("  SSH WebSocket Tunnel Dashboard (kkmod)")
    print("="*50)
    status = ServiceManager.status()
    print(f"Service Status: {status.upper()}")
    ws_port = config.get("ws_port", 8080)
    tls_port = config.get("tls_port", 8443)
    print(f"WebSocket (HTTP) port:  {ws_port}")
    print(f"WebSocket (HTTPS) port: {tls_port}")
    print(f"Domain: {config.get('domain', 'N/A')}")
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
        print("Service restarted.")
    elif choice == "3":
        ServiceManager.stop()
        print("Service stopped.")
    elif choice == "4":
        editor = os.environ.get("EDITOR", "nano")
        config_file = ".env" if os.path.exists(".env") else "config.yaml"
        os.system(f"{editor} {config_file}")
        ServiceManager.restart()

def main():
    while True:
        show_dashboard()
        # re-loop; user can exit with 0 (or Ctrl+C)

if __name__ == "__main__":
    main()
