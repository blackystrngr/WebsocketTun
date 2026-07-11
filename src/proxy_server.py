import asyncio
import logging
import ssl
from websockets.server import serve
from .utils import print_success, print_info, print_error

class SSHWebSocketProxy:
    def __init__(self, ws_ports, tls_ports, ssh_host, ssh_port, ssl_cert=None, ssl_key=None):
        self.ws_ports = ws_ports if isinstance(ws_ports, list) else [ws_ports]
        self.tls_ports = tls_ports if isinstance(tls_ports, list) else [tls_ports]
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
                    self.logger.debug(f"ws->ssh: {e}")
            async def ssh_to_ws():
                try:
                    while True:
                        data = await ssh_reader.read(4096)
                        if not data:
                            break
                        await websocket.send(data)
                except Exception as e:
                    self.logger.debug(f"ssh->ws: {e}")
            await asyncio.gather(ws_to_ssh(), ssh_to_ws())
        except ConnectionRefusedError:
            self.logger.error("SSH service not reachable. Is sshd running?")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            if ssh_writer:
                ssh_writer.close()
                await ssh_writer.wait_closed()
            self.logger.info("Connection closed")

    async def _process_request(self, path, request_headers):
        """Accept any WebSocket upgrade, regardless of HTTP method."""
        # This is called before the WebSocket handshake.
        # Return None to continue handshake, or a tuple (status, headers, body) to respond.
        # We just allow all – websockets library will handle the upgrade.
        return None

    async def start(self):
        servers = []
        for port in self.ws_ports:
            server = serve(
                self._handle_connection,
                "0.0.0.0",
                port,
                process_request=self._process_request  # accept any method
            )
            servers.append(server)
            print_success(f"WS server listening on port {port}")

        if self.ssl_cert and self.ssl_key:
            try:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(self.ssl_cert, self.ssl_key)
                for port in self.tls_ports:
                    server = serve(
                        self._handle_connection,
                        "0.0.0.0",
                        port,
                        ssl=ssl_context,
                        process_request=self._process_request
                    )
                    servers.append(server)
                    print_success(f"WSS server listening on port {port}")
            except Exception as e:
                print_error(f"SSL setup failed: {e}")
        else:
            print_info("WSS disabled: no certificates provided.")

        if not servers:
            print_error("No servers to start!")
            return

        await asyncio.gather(*servers)
