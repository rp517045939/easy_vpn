import asyncio
import logging
import time
from dataclasses import dataclass

from protocol import new_channel_id

logger = logging.getLogger(__name__)

UDP_SESSION_IDLE_SECONDS = 120
UDP_CLEANUP_INTERVAL = 30


@dataclass
class UdpSession:
    port: int
    peer: tuple[str, int]
    channel_id: str
    client_id: str
    local_host: str
    local_port: int
    last_seen: float


class _PortProtocol(asyncio.DatagramProtocol):
    def __init__(self, listener: "UdpListener", port: int,
                 client_id: str, local_host: str, local_port: int):
        self.listener = listener
        self.port = port
        self.client_id = client_id
        self.local_host = local_host
        self.local_port = local_port
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, peer):
        asyncio.create_task(
            self.listener.handle_datagram(
                self.port, peer, data,
                self.client_id, self.local_host, self.local_port,
            )
        )

    def error_received(self, exc):
        logger.debug(f"UDP listener :{self.port} error: {exc}")


class UdpListener:
    def __init__(self):
        self._tunnel_manager = None
        self._transports: dict[int, asyncio.DatagramTransport] = {}
        self._protocols: dict[int, _PortProtocol] = {}
        self._sessions_by_peer: dict[tuple[int, tuple[str, int]], UdpSession] = {}
        self._sessions_by_channel: dict[str, UdpSession] = {}
        self._cleanup_task: asyncio.Task | None = None

    def set_tunnel_manager(self, tm) -> None:
        self._tunnel_manager = tm

    async def start(self, server_port: int, client_id: str,
                    local_host: str, local_port: int) -> None:
        if server_port in self._transports:
            logger.warning(f"UDP port {server_port} already listening, skipping")
            return

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: _PortProtocol(self, server_port, client_id, local_host, local_port),
            local_addr=("0.0.0.0", server_port),
        )
        self._transports[server_port] = transport
        self._protocols[server_port] = protocol
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"UDP listener :{server_port} -> {client_id} -> {local_host}:{local_port}")

    async def stop(self, server_port: int) -> None:
        transport = self._transports.pop(server_port, None)
        self._protocols.pop(server_port, None)
        if transport:
            transport.close()

        sessions = [
            session for session in self._sessions_by_channel.values()
            if session.port == server_port
        ]
        for session in sessions:
            await self._remove_session(session, notify_client=True)
        logger.info(f"UDP listener stopped: :{server_port}")

    async def stop_all(self) -> None:
        for port in list(self._transports.keys()):
            await self.stop(port)
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def handle_datagram(self, server_port: int, peer: tuple[str, int], data: bytes,
                              client_id: str, local_host: str, local_port: int) -> None:
        key = (server_port, peer)
        session = self._sessions_by_peer.get(key)
        if session is None:
            channel_id = new_channel_id()
            session = UdpSession(
                port=server_port,
                peer=peer,
                channel_id=channel_id,
                client_id=client_id,
                local_host=local_host,
                local_port=local_port,
                last_seen=time.time(),
            )
            self._sessions_by_peer[key] = session
            self._sessions_by_channel[channel_id] = session
            try:
                await self._tunnel_manager.open_udp_channel(
                    client_id, channel_id, local_host, local_port
                )
            except ConnectionError as e:
                logger.warning(f"Cannot open UDP channel: {e}")
                await self._remove_session(session, notify_client=False)
                return
            logger.info(
                f"UDP session {peer} -> channel {channel_id[:8]} -> {client_id}:{local_port}"
            )

        session.last_seen = time.time()
        await self._tunnel_manager.send_udp_data(client_id, session.channel_id, data)

    async def send_to_peer(self, channel_id: str, data: bytes) -> None:
        session = self._sessions_by_channel.get(channel_id)
        if not session:
            return
        transport = self._transports.get(session.port)
        if not transport:
            await self._remove_session(session, notify_client=True)
            return
        session.last_seen = time.time()
        transport.sendto(data, session.peer)

    async def close_channel(self, channel_id: str, notify_client: bool = False) -> None:
        session = self._sessions_by_channel.get(channel_id)
        if session:
            await self._remove_session(session, notify_client=notify_client)

    async def _remove_session(self, session: UdpSession, notify_client: bool) -> None:
        self._sessions_by_peer.pop((session.port, session.peer), None)
        self._sessions_by_channel.pop(session.channel_id, None)
        if notify_client and self._tunnel_manager:
            await self._tunnel_manager.close_udp_channel(session.client_id, session.channel_id)

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(UDP_CLEANUP_INTERVAL)
            now = time.time()
            stale = [
                session for session in list(self._sessions_by_channel.values())
                if now - session.last_seen > UDP_SESSION_IDLE_SECONDS
            ]
            for session in stale:
                logger.info(f"UDP session {session.channel_id[:8]} idle timeout")
                await self._remove_session(session, notify_client=True)


udp_listener = UdpListener()
