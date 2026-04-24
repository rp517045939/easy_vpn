"""
Client 共享状态 + 自定义日志 handler，供 web_ui.py 读取。
"""
import logging
import asyncio
from collections import deque
from datetime import datetime

MAX_LOG_LINES = 500


class ClientState:
    def __init__(self):
        self.status: str = "disconnected"   # connecting | connected | disconnected
        self.server_url: str = ""
        self.client_id: str = ""
        self.connected_at: float | None = None
        self.rules: list = []
        self.retry_delay: int = 0
        self.config_path: str = "config.yml"
        self.ui_host: str = "127.0.0.1"
        self.ui_port: int = 7070
        self.ui_password: str = ""

        self.reload_event: asyncio.Event | None = None  # 由 main.py 注入

        # 流量统计（本次会话累计，断连重置）
        self.bytes_sent: int = 0      # 发给 server 的字节（HTTP 响应 + TCP 上行）
        self.bytes_recv: int = 0      # 从 server 收到的字节（HTTP 请求 + TCP 下行）
        self.http_requests: int = 0
        self.tcp_connections: int = 0

        self._log_buffer: deque = deque(maxlen=MAX_LOG_LINES)
        self._log_queues: list[asyncio.Queue] = []   # SSE 订阅者

    def record_traffic(self, *, sent: int = 0, recv: int = 0,
                       http_req: int = 0, tcp_conn: int = 0) -> None:
        self.bytes_sent      += sent
        self.bytes_recv      += recv
        self.http_requests   += http_req
        self.tcp_connections += tcp_conn

    def reset_traffic(self) -> None:
        self.bytes_sent = self.bytes_recv = self.http_requests = self.tcp_connections = 0

    # ------------------------------------------------------------------ 日志

    def add_log(self, record: str):
        self._log_buffer.append(record)
        for q in list(self._log_queues):
            try:
                q.put_nowait(record)
            except asyncio.QueueFull:
                pass

    def get_log_buffer(self) -> list[str]:
        return list(self._log_buffer)

    def subscribe_logs(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._log_queues.append(q)
        return q

    def unsubscribe_logs(self, q: asyncio.Queue):
        try:
            self._log_queues.remove(q)
        except ValueError:
            pass

    # ------------------------------------------------------------------ 快照

    def snapshot(self) -> dict:
        import time
        uptime = int(time.time() - self.connected_at) if self.connected_at else 0
        return {
            "status":          self.status,
            "server_url":      self.server_url,
            "client_id":       self.client_id,
            "uptime_seconds":  uptime,
            "retry_delay":     self.retry_delay,
            "rules":           self.rules,
            "traffic": {
                "bytes_sent":      self.bytes_sent,
                "bytes_recv":      self.bytes_recv,
                "http_requests":   self.http_requests,
                "tcp_connections": self.tcp_connections,
            },
        }


# 全局单例
client_state = ClientState()


class StateLogHandler(logging.Handler):
    """把日志记录写入 client_state，供 web UI 订阅。"""

    def emit(self, record: logging.LogRecord):
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        line = f"[{ts}] {record.levelname:<7} {record.name}: {record.getMessage()}"
        client_state.add_log(line)
