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
        self._tcp_open_waiters: dict[str, asyncio.Future] = {} # channel_id → Future
        self._channel_owner: dict[str, str] = {}              # channel_id → client_id
        self._lock = asyncio.Lock()
        # 流量统计：内存增量，定期 flush 到 SQLite
        self._pending_traffic: dict[str, dict] = {}           # client_id → delta dict

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
                "send_lock": asyncio.Lock(),
                "connected_at": time.time(),
                "last_heartbeat": time.time(),
            }
        logger.info(f"Client connected: {client_id}")

        from rules import rules_manager
        rules = rules_manager.get_by_client(client_id)
        await self._send(client_id, encode(MsgType.RULES_PUSH, payload={"rules": rules}))

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
            open_waiter = self._tcp_open_waiters.pop(cid, None)
            if open_waiter and not open_waiter.done():
                open_waiter.set_exception(ConnectionError(f"Client {client_id} disconnected"))
            queue = self._tcp_queues.pop(cid, None)
            if queue:
                await queue.put(None)
            self._channel_owner.pop(cid, None)

        asyncio.create_task(self._flush_traffic())
        logger.info(f"Client disconnected: {client_id}")

    def is_online(self, client_id: str) -> bool:
        return client_id in self._clients

    def count_online(self) -> int:
        return len(self._clients)

    async def get_online_clients(self) -> list:
        from rules import rules_manager
        traffic_map = await self._get_traffic_merged()
        empty = {"bytes_in": 0, "bytes_out": 0, "http_requests": 0, "tcp_connections": 0}
        now = time.time()
        return [
            {
                "client_id": cid,
                "connected_at": info["connected_at"],
                "online_seconds": int(now - info["connected_at"]),
                "rules": rules_manager.get_by_client(cid),
                "traffic": traffic_map.get(cid, empty),
            }
            for cid, info in self._clients.items()
        ]

    # ------------------------------------------------------------------ 流量统计

    def record_traffic(self, client_id: str, *,
                       bytes_in: int = 0, bytes_out: int = 0,
                       http_req: int = 0, tcp_conn: int = 0) -> None:
        """内存累加，不阻塞事件循环。由 traffic_flush_loop 定期写入 SQLite。"""
        if not client_id:
            return
        d = self._pending_traffic.setdefault(client_id, {
            "bytes_in": 0, "bytes_out": 0,
            "http_requests": 0, "tcp_connections": 0,
            "last_active": 0,
        })
        d["bytes_in"]        += bytes_in
        d["bytes_out"]       += bytes_out
        d["http_requests"]   += http_req
        d["tcp_connections"] += tcp_conn
        d["last_active"]      = time.time()

    async def _flush_traffic(self) -> None:
        """将内存增量写入 SQLite，然后清空内存。"""
        from traffic_db import flush_to_db
        if not self._pending_traffic:
            return
        pending, self._pending_traffic = self._pending_traffic, {}
        await flush_to_db(pending)

    async def traffic_flush_loop(self) -> None:
        """每 30 秒定期将流量增量写入数据库。"""
        while True:
            await asyncio.sleep(30)
            try:
                await self._flush_traffic()
            except Exception as e:
                logger.error(f"Traffic flush error: {e}")

    async def _get_traffic_merged(self) -> dict[str, dict]:
        """返回 DB 历史 + 内存增量的合并结果。"""
        from traffic_db import query_all
        db_map = {r["client_id"]: dict(r) for r in await query_all()}
        for cid, d in self._pending_traffic.items():
            if cid in db_map:
                for k in ("bytes_in", "bytes_out", "http_requests", "tcp_connections"):
                    db_map[cid][k] += d.get(k, 0)
                db_map[cid]["last_active"] = max(
                    db_map[cid]["last_active"], d.get("last_active", 0)
                )
            else:
                db_map[cid] = dict(d)
        return db_map

    async def get_all_traffic(self) -> list[dict]:
        """返回所有设备流量列表（含离线历史）。"""
        merged = await self._get_traffic_merged()
        return list(merged.values())

    # ------------------------------------------------------------------ 发送（加锁防并发）

    async def _send(self, client_id: str, text: str) -> None:
        """所有向 client 发送的入口，保证串行，避免并发 send_text 崩溃。"""
        client = self._clients.get(client_id)
        if not client:
            return
        async with client["send_lock"]:
            await client["ws"].send_text(text)

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
            await self._send(client_id, encode(MsgType.HEARTBEAT_ACK))

        elif msg_type == MsgType.HTTP_RESPONSE:
            future = self._http_channels.pop(channel_id, None)
            self._channel_owner.pop(channel_id, None)
            if future and not future.done():
                future.set_result(msg.get("payload", {}))

        elif msg_type == MsgType.TCP_OPENED:
            open_waiter = self._tcp_open_waiters.pop(channel_id, None)
            if open_waiter and not open_waiter.done():
                open_waiter.set_result(True)

        elif msg_type == MsgType.TCP_DATA:
            queue = self._tcp_queues.get(channel_id)
            if queue and msg.get("data"):
                raw = decode_data(msg["data"])
                self.record_traffic(self._channel_owner.get(channel_id, ""), bytes_out=len(raw))
                await queue.put(raw)

        elif msg_type == MsgType.TCP_CLOSE:
            open_waiter = self._tcp_open_waiters.pop(channel_id, None)
            if open_waiter and not open_waiter.done():
                open_waiter.set_exception(ConnectionError(f"TCP channel {channel_id[:8]} failed to open"))
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

        await self._send(client_id, encode(MsgType.HTTP_REQUEST, channel_id=channel_id, payload=request_data))

        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            # 统计 HTTP 流量
            req_bytes  = len(request_data.get("body", "").encode("latin-1"))
            resp_bytes = len(result.get("body", "").encode("latin-1"))
            self.record_traffic(client_id, bytes_in=req_bytes, bytes_out=resp_bytes, http_req=1)
            return result
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
        open_waiter: asyncio.Future = asyncio.get_running_loop().create_future()
        self._tcp_queues[channel_id] = queue
        self._tcp_open_waiters[channel_id] = open_waiter
        self._channel_owner[channel_id] = client_id

        self.record_traffic(client_id, tcp_conn=1)
        await self._send(client_id, encode(
            MsgType.TCP_OPEN, channel_id=channel_id,
            payload={"local_host": local_host, "local_port": local_port}
        ))
        return queue

    async def wait_tcp_ready(self, channel_id: str, timeout: float = 0.5) -> bool:
        """
        等待客户端确认本地 TCP 已连通。
        - 新客户端会显式发送 TCP_OPENED。
        - 旧客户端没有该握手，超时后继续，以兼容现网。
        """
        open_waiter = self._tcp_open_waiters.get(channel_id)
        if not open_waiter:
            return True
        try:
            await asyncio.wait_for(asyncio.shield(open_waiter), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def send_tcp_data(self, client_id: str, channel_id: str, data: bytes) -> None:
        self.record_traffic(client_id, bytes_in=len(data))
        await self._send(client_id, encode(MsgType.TCP_DATA, channel_id=channel_id, data=data))

    async def close_tcp_channel(self, client_id: str, channel_id: str) -> None:
        self._tcp_open_waiters.pop(channel_id, None)
        queue = self._tcp_queues.pop(channel_id, None)
        self._channel_owner.pop(channel_id, None)
        if queue:
            await queue.put(None)  # 唤醒 pipe_out，使其正常退出并关闭 writer
        await self._send(client_id, encode(MsgType.TCP_CLOSE, channel_id=channel_id))

    # ------------------------------------------------------------------ 规则推送

    async def push_rules(self, client_id: str, rules: list) -> None:
        await self._send(client_id, encode(MsgType.RULES_PUSH, payload={"rules": rules}))
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
                        await self._send(client_id, encode(MsgType.HEARTBEAT))
                    except Exception:
                        dead.append(client_id)
            for client_id in dead:
                await self.disconnect(client_id)


tunnel_manager = TunnelManager()
