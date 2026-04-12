"""
本地流量转发器。

处理两类转发：

  HTTP 转发：
    接收 http_request 消息 → 连接本地 HTTP 服务 → 返回 http_response
    适用于：NAS Web UI、Mac 上的 Web 服务等

  TCP 转发：
    接收 tcp_open 消息 → 连接本地 TCP 服务（如 sshd:22）→ 建立双向数据管道
    tcp_data：将数据写入本地 TCP 连接 / 从本地 TCP 读取数据回传 Server
    tcp_close：关闭本地 TCP 连接
    适用于：SSH、数据库、任意 TCP 服务
"""
import asyncio


async def forward_http(local_host: str, local_port: int,
                        request_data: dict) -> dict:
    """
    将 HTTP 请求转发到本地服务，返回响应。
    由 main.py 在收到 http_request 消息时调用。
    """
    pass


async def open_tcp(local_host: str, local_port: int,
                    channel_id: str, send_fn) -> None:
    """
    连接本地 TCP 服务，建立双向数据管道。
    - send_fn：回调函数，用于将本地读取到的数据通过 WebSocket 发回 Server
    - 持续运行直到本地连接断开或收到 tcp_close 消息
    由 main.py 在收到 tcp_open 消息时调用（以 asyncio.create_task 运行）。
    """
    pass


async def write_tcp(channel_id: str, data: bytes) -> None:
    """
    将 Server 发来的 tcp_data 写入对应的本地 TCP 连接。
    由 main.py 在收到 tcp_data 消息时调用。
    """
    pass


async def close_tcp(channel_id: str) -> None:
    """
    关闭指定 channel 的本地 TCP 连接。
    由 main.py 在收到 tcp_close 消息时调用。
    """
    pass
