"""
easy_vpn Client 入口。

启动方式：
  python main.py --config config.yml

职责：
- 读取配置，向 Server 发起 WebSocket 连接并注册隧道规则
- 维持心跳，断线后自动重连（指数退避）
- 收到转发请求后，调用 forwarder.py 处理并回传响应
"""
import asyncio


async def run():
    pass


if __name__ == "__main__":
    asyncio.run(run())
