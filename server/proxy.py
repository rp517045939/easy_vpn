"""
HTTP 反向代理层。

职责：
- 接收 Nginx 转发过来的外部 HTTP 请求
- 根据 Host 头（如 nas.ruanpengpeng.cn）匹配对应的 Client
- 通过 TunnelManager 将请求转发给 Client，返回响应
"""
from fastapi import Request, Response


async def proxy_handler(request: Request) -> Response:
    """所有穿透流量的统一入口"""
    pass
