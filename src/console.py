import asyncio
import sys
import logging
from .service_manager import ServiceManager
from .utils import print_success, print_error, print_info

class ConsoleHandler:
    def __init__(self, shutdown_callback=None):
        self.shutdown_callback = shutdown_callback
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = True

    async def run(self):
        loop = asyncio.get_running_loop()
        print_info("\nConsole ready. Type 'help' for commands.\n")
        while self.running:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                await self.process_command(line)
            except Exception as e:
                self.logger.error(f"Console error: {e}")

    async def process_command(self, cmd):
        if cmd == "status":
            status = ServiceManager.status()
            print_success(f"Service status: {status}")
        elif cmd == "restart":
            ServiceManager.restart()
            print_success("Service restarted.")
        elif cmd == "stop":
            ServiceManager.stop()
            print_info("Service stopped.")
        elif cmd == "logs":
            logs = ServiceManager.logs()
            print(logs)
        elif cmd == "exit" or cmd == "quit":
            print_info("Shutting down...")
            if self.shutdown_callback:
                await self.shutdown_callback()
            self.running = False
        elif cmd == "help":
            print_info("Commands: status, restart, stop, logs, exit, help")
        else:
            print_error(f"Unknown command: {cmd}")
