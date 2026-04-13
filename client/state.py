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

        self.reload_event: asyncio.Event | None = None  # 由 main.py 注入

        self._log_buffer: deque = deque(maxlen=MAX_LOG_LINES)
        self._log_queues: list[asyncio.Queue] = []   # SSE 订阅者

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
            "status": self.status,
            "server_url": self.server_url,
            "client_id": self.client_id,
            "uptime_seconds": uptime,
            "retry_delay": self.retry_delay,
            "rules": self.rules,
        }


# 全局单例
client_state = ClientState()


class StateLogHandler(logging.Handler):
    """把日志记录写入 client_state，供 web UI 订阅。"""

    def emit(self, record: logging.LogRecord):
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        line = f"[{ts}] {record.levelname:<7} {record.name}: {record.getMessage()}"
        client_state.add_log(line)
