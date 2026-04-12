"""
本地流量转发器。

职责：
- 接收从隧道传来的 HTTP 请求数据
- 转发到本地配置的端口（如 NAS 的 :5000）
- 将本地服务的响应回传给隧道
"""


async def forward_to_local(host: str, port: int, request_data: dict) -> dict:
    """将请求转发到本地服务，返回响应"""
    pass
