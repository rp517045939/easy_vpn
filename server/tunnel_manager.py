import asyncio
import logging
import time
from protocol import MsgType, encode, decode, decode_data, new_channel_id
from config import settings

logger = logging.getLogger(__name__)


class TunnelManager:

    def __init__(self):
        self._clients: dict[str, dict] = {}          # client_id → {ws, connected_at, last_heartbeat}
        self._http_channels: dict[str, asyncio.Future] = {}   # channel_id → Future
        self._tcp_queues: dict[str, asyncio.Queue] = {}       # channel_id → Queue
        self._channel_owner: dict[str, str] = {}              # channel_id → client_id
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ 连接管理

    async def connect(self, client_id: str, websocket) -> None:
        async with self._lock:
            # 如果已有同 client_id 的旧连接，主动关闭它（避免旧 handler 的 finally 误清理新连接）
            existing = self._clients.get(client_id)
            if existing and existing["ws"] is not websocket:
                logger.warning(f"Client {client_id} reconnected, closing old connection")
                try:
                    await existing["ws"].close()
                except Exception:
                    pass
            self._clients[client_id] = {
                "ws": websocket,
                "connected_at": time.time(),
                "last_heartbeat": time.time(),
            }
        logger.info(f"Client connected: {client_id}")

        from rules import rules_manager
        rules = rules_manager.get_by_client(client_id)
        await websocket.send_text(encode(MsgType.RULES_PUSH, payload={"rules": rules}))

    async def disconnect(self, client_id: str, websocket=None) -> None:
        async with self._lock:
            existing = self._clients.get(client_id)
            if existing is None:
                return
            # 只清理调用方自己的连接：如果已被新连接替换，则跳过
            if websocket is not None and existing["ws"] is not websocket:
                logger.info(f"Skipping disconnect for {client_id}: already replaced by new connection")
                return
            self._clients.pop(client_id, None)

        # 取消该 client 所有待处理的 HTTP channel
        dead_channels = [cid for cid, owner in self._channel_owner.items() if owner == client_id]
        for cid in dead_channels:
            future = self._http_channels.pop(cid, None)
            if future and not future.done():
                future.set_exception(ConnectionError(f"Client {client_id} disconnected"))
            queue = self._tcp_queues.pop(cid, None)
            if queue:
                await queue.put(None)
            self._channel_owner.pop(cid, None)

        logger.info(f"Client disconnected: {client_id}")

    def is_online(self, client_id: str) -> bool:
        return client_id in self._clients

    def get_online_clients(self) -> list:
        from rules import rules_manager
        now = time.time()
        return [
            {
                "client_id": cid,
                "connected_at": info["connected_at"],
                "online_seconds": int(now - info["connected_at"]),
                "rules": rules_manager.get_by_client(cid),
            }
            for cid, info in self._clients.items()
        ]

    # ------------------------------------------------------------------ 消息分发

    async def dispatch(self, client_id: str, raw: str) -> None:
        msg = decode(raw)
        msg_type = msg.get("type")
        channel_id = msg.get("channel_id")

        if msg_type == MsgType.HEARTBEAT_ACK:
            # 服务端发 HEARTBEAT，客户端回 HEARTBEAT_ACK → 更新心跳时间
            async with self._lock:
                if client_id in self._clients:
                    self._clients[client_id]["last_heartbeat"] = time.time()

        elif msg_type == MsgType.HEARTBEAT:
            # 兼容客户端主动发心跳的场景
            async with self._lock:
                if client_id in self._clients:
                    self._clients[client_id]["last_heartbeat"] = time.time()
            client = self._clients.get(client_id)
            if client:
                await client["ws"].send_text(encode(MsgType.HEARTBEAT_ACK))

        elif msg_type == MsgType.HTTP_RESPONSE:
            future = self._http_channels.pop(channel_id, None)
            self._channel_owner.pop(channel_id, None)
            if future and not future.done():
                future.set_result(msg.get("payload", {}))

        elif msg_type == MsgType.TCP_DATA:
            queue = self._tcp_queues.get(channel_id)
            if queue and msg.get("data"):
                await queue.put(decode_data(msg["data"]))

        elif msg_type == MsgType.TCP_CLOSE:
            queue = self._tcp_queues.pop(channel_id, None)
            self._channel_owner.pop(channel_id, None)
            if queue:
                await queue.put(None)  # sentinel

    # ------------------------------------------------------------------ HTTP 隧道

    async def forward_http(self, client_id: str, request_data: dict) -> dict:
        client = self._clients.get(client_id)
        if not client:
            raise ConnectionError(f"Client {client_id} is not online")

        channel_id = new_channel_id()
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        self._http_channels[channel_id] = future
        self._channel_owner[channel_id] = client_id

        await client["ws"].send_text(encode(MsgType.HTTP_REQUEST, channel_id=channel_id, payload=request_data))

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._http_channels.pop(channel_id, None)
            self._channel_owner.pop(channel_id, None)
            raise TimeoutError(f"Client {client_id} did not respond in time")

    # ------------------------------------------------------------------ TCP 隧道

    async def open_tcp_channel(self, client_id: str, channel_id: str,
                                local_host: str, local_port: int) -> asyncio.Queue:
        client = self._clients.get(client_id)
        if not client:
            raise ConnectionError(f"Client {client_id} is not online")

        queue: asyncio.Queue = asyncio.Queue()
        self._tcp_queues[channel_id] = queue
        self._channel_owner[channel_id] = client_id

        await client["ws"].send_text(encode(
            MsgType.TCP_OPEN, channel_id=channel_id,
            payload={"local_host": local_host, "local_port": local_port}
        ))
        return queue

    async def send_tcp_data(self, client_id: str, channel_id: str, data: bytes) -> None:
        client = self._clients.get(client_id)
        if client:
            await client["ws"].send_text(encode(MsgType.TCP_DATA, channel_id=channel_id, data=data))

    async def close_tcp_channel(self, client_id: str, channel_id: str) -> None:
        client = self._clients.get(client_id)
        if client:
            await client["ws"].send_text(encode(MsgType.TCP_CLOSE, channel_id=channel_id))
        self._tcp_queues.pop(channel_id, None)
        self._channel_owner.pop(channel_id, None)

    # ------------------------------------------------------------------ 规则推送

    async def push_rules(self, client_id: str, rules: list) -> None:
        client = self._clients.get(client_id)
        if client:
            await client["ws"].send_text(encode(MsgType.RULES_PUSH, payload={"rules": rules}))
            logger.info(f"Rules pushed to {client_id}: {len(rules)} rules")

    # ------------------------------------------------------------------ 心跳检测

    async def heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(settings.heartbeat_interval)
            now = time.time()
            dead = []
            for client_id, info in list(self._clients.items()):
                if now - info["last_heartbeat"] > settings.heartbeat_timeout:
                    logger.warning(f"Client {client_id} heartbeat timeout, marking offline")
                    dead.append(client_id)
                else:
                    try:
                        await info["ws"].send_text(encode(MsgType.HEARTBEAT))
                    except Exception:
                        dead.append(client_id)
            for client_id in dead:
                await self.disconnect(client_id)


tunnel_manager = TunnelManager()
