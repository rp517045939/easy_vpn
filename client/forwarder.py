"""
本地流量转发器。

职责：
- 接收从隧道传来的 HTTP 请求数据
- 根据 Server 下发的规则，找到对应的本地 host:port
- 将请求转发到本地服务，将响应回传给隧道
"""


async def forward_to_local(local_host: str, local_port: int, request_data: dict) -> dict:
    """将请求转发到本地服务，返回响应"""
    pass
