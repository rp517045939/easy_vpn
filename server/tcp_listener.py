import asyncio
import logging
from protocol import new_channel_id

logger = logging.getLogger(__name__)


class TcpListener:

    def __init__(self):
        self._tunnel_manager = None
        self._servers: dict[int, asyncio.Server] = {}

    def set_tunnel_manager(self, tm) -> None:
        self._tunnel_manager = tm

    async def start(self, server_port: int, client_id: str,
                    local_host: str, local_port: int) -> None:
        if server_port in self._servers:
            logger.warning(f"Port {server_port} already listening, skipping")
            return

        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            await self._handle_connection(reader, writer, client_id, local_host, local_port)

        server = await asyncio.start_server(handle, "0.0.0.0", server_port)
        self._servers[server_port] = server
        asyncio.create_task(server.serve_forever())
        logger.info(f"TCP listener :{server_port} -> {client_id} -> {local_host}:{local_port}")

    async def stop(self, server_port: int) -> None:
        server = self._servers.pop(server_port, None)
        if server:
            server.close()
            await server.wait_closed()
            logger.info(f"TCP listener stopped: :{server_port}")

    async def stop_all(self) -> None:
        for port in list(self._servers.keys()):
            await self.stop(port)

    async def _handle_connection(self, reader: asyncio.StreamReader,
                                  writer: asyncio.StreamWriter,
                                  client_id: str,
                                  local_host: str, local_port: int) -> None:
        channel_id = new_channel_id()
        peer = writer.get_extra_info("peername")
        logger.info(f"TCP connection {peer} -> channel {channel_id[:8]} -> {client_id}:{local_port}")
        tm = self._tunnel_manager

        try:
            queue = await tm.open_tcp_channel(client_id, channel_id, local_host, local_port)
        except ConnectionError as e:
            logger.warning(f"Cannot open TCP channel: {e}")
            writer.close()
            return

        if not await tm.wait_tcp_ready(channel_id, timeout=0.5):
            logger.debug(f"TCP channel {channel_id[:8]} proceeding without explicit ready ack")

        async def pipe_in():
            """外部 TCP → WebSocket → Client"""
            try:
                while True:
                    data = await reader.read(65536)
                    if not data:
                        break
                    await tm.send_tcp_data(client_id, channel_id, data)
            except Exception as e:
                logger.debug(f"pipe_in error {channel_id[:8]}: {e}")
            finally:
                try:
                    await tm.close_tcp_channel(client_id, channel_id)
                except Exception as e:
                    logger.debug(f"close_tcp_channel error {channel_id[:8]}: {e}")

        async def pipe_out():
            """Client → WebSocket → 外部 TCP"""
            try:
                while True:
                    data = await queue.get()
                    if data is None:
                        break
                    writer.write(data)
                    await writer.drain()
            except Exception as e:
                logger.debug(f"pipe_out error {channel_id[:8]}: {e}")
            finally:
                try:
                    writer.close()
                except Exception:
                    pass

        await asyncio.gather(pipe_in(), pipe_out())
        logger.info(f"TCP channel {channel_id[:8]} closed")


tcp_listener = TcpListener()
