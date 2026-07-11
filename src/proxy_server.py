import asyncio
import logging
import ssl
from websockets.server import serve

class SSHWebSocketProxy:
    def __init__(self, ws_port, tls_port, ssh_host, ssh_port, ssl_cert=None, ssl_key=None):
        self.ws_port = ws_port
        self.tls_port = tls_port
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _handle_connection(self, websocket, path):
        self.logger.info(f"New connection from {websocket.remote_address}")
        ssh_reader = ssh_writer = None
        try:
            ssh_reader, ssh_writer = await asyncio.open_connection(self.ssh_host, self.ssh_port)
            async def ws_to_ssh():
                try:
                    async for msg in websocket:
                        if isinstance(msg, bytes):
                            ssh_writer.write(msg)
                            await ssh_writer.drain()
                except Exception as e:
                    self.logger.debug(f"ws->ssh error: {e}")
            async def ssh_to_ws():
                try:
                    while True:
                        data = await ssh_reader.read(4096)
                        if not data:
                            break
                        await websocket.send(data)
                except Exception as e:
                    self.logger.debug(f"ssh->ws error: {e}")
            await asyncio.gather(ws_to_ssh(), ssh_to_ws())
        except ConnectionRefusedError:
            self.logger.error("SSH service not reachable.")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            if ssh_writer:
                ssh_writer.close()
                await ssh_writer.wait_closed()
            self.logger.info("Connection closed")

    async def start(self):
        ws_server = serve(self._handle_connection, "0.0.0.0", self.ws_port)
        wss_server = None
        if self.ssl_cert and self.ssl_key:
            try:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(self.ssl_cert, self.ssl_key)
                wss_server = serve(self._handle_connection, "0.0.0.0", self.tls_port, ssl=ssl_context)
                self.logger.info(f"WSS on port {self.tls_port}")
            except Exception as e:
                self.logger.error(f"WSS failed: {e}")
        self.logger.info(f"WS on port {self.ws_port}")
        servers = [ws_server]
        if wss_server:
            servers.append(wss_server)
        await asyncio.gather(*servers)
