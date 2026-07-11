import subprocess
import logging

class ServiceManager:
    @staticmethod
    def status():
        try:
            result = subprocess.run(["systemctl", "is-active", "ssh-ws-tunnel"],
                                    capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return "unknown"

    @staticmethod
    def restart():
        subprocess.run(["systemctl", "restart", "ssh-ws-tunnel"], check=True)

    @staticmethod
    def stop():
        subprocess.run(["systemctl", "stop", "ssh-ws-tunnel"], check=True)

    @staticmethod
    def logs(tail=50):
        try:
            result = subprocess.run(
                ["journalctl", "-u", "ssh-ws-tunnel", "-n", str(tail), "--no-pager"],
                capture_output=True, text=True
            )
            return result.stdout
        except Exception as e:
            return f"Error: {e}"
