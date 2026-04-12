"""
TCP 隧道监听器。

职责：
- 在配置的端口上监听原始 TCP 连接（如 :2222 用于 SSH）
- 每个新 TCP 连接分配一个 channel_id
- 通过 TunnelManager 向对应 Client 发送 tcp_open 消息
- 将 TCP 数据双向转发：
    外部 TCP → channel → Client → 本地服务（如 Mac:22）
    本地服务  → Client → channel → 外部 TCP
- 连接断开时发送 tcp_close 消息

端口范围：2200-2299（在 docker-compose 中统一开放）
每条 TCP 规则占用一个端口，由管理面板分配。

示例规则：
  server_port: 2222
  client_id:   mac
  local_host:  127.0.0.1
  local_port:  22
  label:       Mac SSH
"""
import asyncio


class TcpListener:

    def __init__(self, tunnel_manager):
        self.tunnel_manager = tunnel_manager
        self._servers: dict[int, asyncio.Server] = {}  # port → asyncio.Server

    async def start(self, server_port: int, client_id: str,
                    local_host: str, local_port: int) -> None:
        """在 server_port 上启动 TCP 监听，关联到指定 Client 的本地端口"""
        pass

    async def stop(self, server_port: int) -> None:
        """停止指定端口的监听（规则删除时调用）"""
        pass

    async def stop_all(self) -> None:
        """停止所有 TCP 监听"""
        pass

    async def _handle_connection(self, reader: asyncio.StreamReader,
                                  writer: asyncio.StreamWriter,
                                  client_id: str,
                                  local_host: str, local_port: int) -> None:
        """处理一个新 TCP 连接：分配 channel_id，通知 Client，双向转发数据"""
        pass


tcp_listener = TcpListener(None)  # tunnel_manager 在 main.py 中注入
