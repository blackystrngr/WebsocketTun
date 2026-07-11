import asyncio
import logging
import subprocess
import os
from pathlib import Path

class GitAutoUpdater:
    def __init__(self, repo_path=".", interval=30):
        self.repo_path = Path(repo_path).absolute()
        self.interval = interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_commit = self._get_current_commit()

    def _get_current_commit(self):
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except Exception:
            return None

    def _git_pull(self):
        try:
            subprocess.run(["git", "-C", str(self.repo_path), "pull"], check=True)
            self.logger.info("Git pull successful.")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git pull failed: {e}")
            return False

    def _restart_service(self):
        try:
            subprocess.run(["systemctl", "restart", "ssh-ws-tunnel"], check=True)
            self.logger.info("Service restarted after update.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Service restart failed: {e}")

    async def run(self):
        self.logger.info(f"Auto‑updater started, interval={self.interval}s")
        while True:
            await asyncio.sleep(self.interval)
            current = self._get_current_commit()
            if current and current != self.last_commit:
                self.logger.info(f"New commit detected: {current[:8]} (was {self.last_commit[:8]})")
                if self._git_pull():
                    self._restart_service()
                    self.last_commit = current
                else:
                    self.logger.warning("Pull failed, skipping restart.")
