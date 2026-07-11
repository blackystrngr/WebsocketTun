import asyncio
import logging
import ssl
from .utils import print_success, print_info, print_error

class SSHWebSocketProxy:
    """Simple TCP proxy that does the HTTP Upgrade trick (no real WebSocket)."""
    
    def __init__(self, ws_ports, tls_ports, ssh_host, ssh_port, ssl_cert=None, ssl_key=None):
        self.ws_ports = ws_ports if isinstance(ws_ports, list) else [ws_ports]
        self.tls_ports = tls_ports if isinstance(tls_ports, list) else [tls_ports]
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _handle_client(self, reader, writer):
        client_addr = writer.get_extra_info('peername')
        self.logger.info(f"New connection from {client_addr}")

        try:
            # 1. Read the HTTP request line and headers
            request_line = await reader.readline()
            if not request_line:
                self.logger.warning("Empty request, closing.")
                writer.close()
                await writer.wait_closed()
                return

            self.logger.info(f"Request: {request_line.decode().strip()}")

            headers = {}
            while True:
                line = await reader.readline()
                if line == b'\r\n' or line == b'\n' or not line:
                    break
                decoded = line.decode('utf-8', errors='ignore').strip()
                if ': ' in decoded:
                    key, value = decoded.split(': ', 1)
                    headers[key.lower()] = value

            # 2. Check Upgrade header
            upgrade = headers.get('upgrade', '').lower()
            if 'websocket' not in upgrade:
                self.logger.warning("No Upgrade: websocket header, closing.")
                writer.write(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return

            # 3. Send 101 Switching Protocols
            response = (
                b'HTTP/1.1 101 Switching Protocols\r\n'
                b'Upgrade: websocket\r\n'
                b'Connection: Upgrade\r\n'
                b'\r\n'
            )
            writer.write(response)
            await writer.drain()
            self.logger.info("Sent 101 Switching Protocols")

            # 4. Connect to SSH
            self.logger.info(f"Connecting to SSH {self.ssh_host}:{self.ssh_port}")
            try:
                ssh_reader, ssh_writer = await asyncio.open_connection(
                    self.ssh_host, self.ssh_port,
                    limit=65536
                )
            except Exception as e:
                self.logger.error(f"Failed to connect to SSH: {e}")
                writer.close()
                await writer.wait_closed()
                return

            self.logger.info("Connected to SSH")

            # 5. Pipe data both ways (raw bytes – no WebSocket framing)
            async def pipe(src, dst):
                try:
                    while True:
                        data = await src.read(4096)
                        if not data:
                            break
                        dst.write(data)
                        await dst.drain()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.logger.error(f"Pipe error: {e}")
                finally:
                    try:
                        dst.close()
                        await dst.wait_closed()
                    except Exception:
                        pass

            # Run both directions concurrently
            await asyncio.gather(
                pipe(reader, ssh_writer),
                pipe(ssh_reader, writer)
            )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            self.logger.info(f"Connection from {client_addr} closed.")

    async def start(self):
        servers = []
        for port in self.ws_ports:
            server = await asyncio.start_server(
                self._handle_client,
                "0.0.0.0",
                port,
                limit=65536
            )
            servers.append(server)
            print_success(f"WS (HTTP Upgrade) server listening on port {port}")

        if self.ssl_cert and self.ssl_key:
            try:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(self.ssl_cert, self.ssl_key)
                for port in self.tls_ports:
                    server = await asyncio.start_server(
                        self._handle_client,
                        "0.0.0.0",
                        port,
                        ssl=ssl_context,
                        limit=65536
                    )
                    servers.append(server)
                    print_success(f"WSS (TLS) server listening on port {port}")
            except Exception as e:
                print_error(f"SSL setup failed: {e}")
        else:
            print_info("WSS disabled: no certificates provided.")

        if not servers:
            print_error("No servers to start!")
            return

        await asyncio.gather(*[server.serve_forever() for server in servers])
