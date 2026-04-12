"""
easy_vpn Client 入口。

启动方式：
  python main.py --config config.yml

连接流程：
  1. 读取本地极简配置（server_url + token + client_id）
  2. 建立 WebSocket 连接，发送 register 消息
  3. 接收 Server 下发的规则（rules_push），保存到内存
  4. 进入消息循环，处理三类消息：
       - rules_push     → 更新本地规则缓存
       - http_request   → 调用 forwarder.forward_http()，回传 http_response
       - tcp_open       → 调用 forwarder.open_tcp()，建立本地 TCP 连接，
                          后续 tcp_data 双向转发，tcp_close 关闭连接
       - heartbeat      → 回复 heartbeat_ack
  5. 断线后指数退避重连（1s → 2s → 4s → ... → 最大 60s）
"""
import asyncio


async def run():
    pass


if __name__ == "__main__":
    asyncio.run(run())
