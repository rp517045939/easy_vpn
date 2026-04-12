"""
easy_vpn Client 入口。

启动方式：
  python main.py --config config.yml

流程：
1. 读取本地极简配置（server地址 + token + client_id）
2. 向 Server 建立 WebSocket 连接并完成认证
3. 从 Server 接收下发的隧道规则（无需本地配置）
4. 维持心跳，断线后自动重连（指数退避）
5. 收到转发请求后，调用 forwarder.py 处理并回传响应
"""
import asyncio


async def run():
    pass


if __name__ == "__main__":
    asyncio.run(run())
