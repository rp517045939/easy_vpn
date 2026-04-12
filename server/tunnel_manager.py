"""
管理所有 Client 的 WebSocket 连接，承载 HTTP 和 TCP 两类隧道流量。

一条 WebSocket 连接通过 channel_id 多路复用：
  - HTTP 请求/响应各占一个 channel（短生命周期）
  - TCP 流（如 SSH）占一个 channel（长生命周期，直到连接关闭）

职责：
- 维护在线 Client 列表（client_id → websocket）
- Client 连接时下发规则（rules_push）
- 接收 Client 消息，按 channel_id 路由到等待中的 Future 或 TCP 流
- 提供 forward_http() 和 forward_tcp_data() 接口供 proxy.py 和 tcp_listener.py 调用
- 心跳检测，超时标记 Client 离线
"""
import asyncio


class TunnelManager:

    def __init__(self):
        # client_id → websocket
        self._clients: dict[str, object] = {}
        # channel_id → asyncio.Future（HTTP 请求等待响应）
        self._http_channels: dict[str, asyncio.Future] = {}
        # channel_id → asyncio.Queue（TCP 流数据队列）
        self._tcp_channels: dict[str, asyncio.Queue] = {}

    async def connect(self, client_id: str, websocket) -> None:
        """Client 建立 WebSocket 连接，下发当前规则"""
        pass

    async def disconnect(self, client_id: str) -> None:
        """Client 断开，清理所有关联的 HTTP channel 和 TCP channel"""
        pass

    async def dispatch(self, client_id: str, message: dict) -> None:
        """
        接收 Client 发来的消息，按类型路由：
          - http_response → 唤醒对应 Future
          - tcp_data      → 放入对应 Queue
          - tcp_close     → 关闭对应 Queue
          - heartbeat     → 回复 heartbeat_ack
        """
        pass

    async def forward_http(self, client_id: str, request_data: dict) -> dict:
        """
        向指定 Client 发送 HTTP 请求，等待响应。
        由 proxy.py 调用。
        """
        pass

    async def open_tcp_channel(self, client_id: str, channel_id: str,
                                local_host: str, local_port: int) -> asyncio.Queue:
        """
        通知 Client 打开一个 TCP 本地连接，返回数据 Queue。
        由 tcp_listener.py 调用。
        """
        pass

    async def send_tcp_data(self, client_id: str, channel_id: str,
                             data: bytes) -> None:
        """向 Client 发送 TCP 数据帧。由 tcp_listener.py 调用。"""
        pass

    async def close_tcp_channel(self, client_id: str, channel_id: str) -> None:
        """通知 Client 关闭 TCP 连接。由 tcp_listener.py 调用。"""
        pass

    def get_online_clients(self) -> list:
        """返回当前在线的 Client 列表，含各自的规则信息"""
        pass


tunnel_manager = TunnelManager()
