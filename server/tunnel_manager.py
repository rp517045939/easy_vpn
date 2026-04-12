"""
管理所有 Client 的 WebSocket 连接。

职责：
- 维护在线 Client 列表（client_id → websocket）
- 处理 Client 注册、心跳、断线
- 提供「向指定 Client 发送请求」的接口，供 proxy.py 调用
"""


class TunnelManager:

    async def connect(self, client_id: str, websocket) -> None:
        """Client 建立连接，注册到管理器"""
        pass

    async def disconnect(self, client_id: str) -> None:
        """Client 断开连接，从管理器移除"""
        pass

    async def forward(self, client_id: str, request_data: dict) -> dict:
        """将 HTTP 请求通过隧道转发给指定 Client，返回响应"""
        pass

    def get_online_clients(self) -> list:
        """返回当前在线的 Client 列表"""
        pass


tunnel_manager = TunnelManager()
