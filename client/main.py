"""
easy_vpn Client

用法：
  python main.py --config config.yml
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

import yaml
import websockets
import websockets.exceptions

from protocol import MsgType, encode, decode, decode_data
from forwarder import forward_http, open_tcp, write_tcp, close_tcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("easy_vpn_client")


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


async def run(config: dict):
    server_url  = config["server"]["url"]
    token       = config["server"]["token"]
    client_id   = config["client"]["id"]

    retry_delay = 1

    while True:
        try:
            logger.info(f"Connecting to {server_url} as [{client_id}]...")
            async with websockets.connect(server_url, ping_interval=None) as ws:
                retry_delay = 1

                # 注册
                await ws.send(encode(MsgType.REGISTER, payload={
                    "token": token, "client_id": client_id
                }))
                logger.info("Registered, waiting for rules...")

                rules: list = []

                # ── 向 Server 发送 TCP 数据 ──
                async def send_tcp_data(channel_id: str, data: bytes):
                    await ws.send(encode(MsgType.TCP_DATA, channel_id=channel_id, data=data))

                async def send_tcp_close(channel_id: str):
                    await ws.send(encode(MsgType.TCP_CLOSE, channel_id=channel_id))

                # ── 消息循环 ──
                async for raw in ws:
                    msg = decode(raw)
                    msg_type   = msg.get("type")
                    channel_id = msg.get("channel_id")

                    if msg_type == MsgType.RULES_PUSH:
                        rules = msg["payload"]["rules"]
                        logger.info(f"Rules updated: {len(rules)} rule(s)")
                        for r in rules:
                            logger.info(f"  [{r['type']}] {r.get('subdomain') or r.get('server_port')} "
                                        f"-> {r['local_host']}:{r['local_port']}")

                    elif msg_type == MsgType.HEARTBEAT:
                        await ws.send(encode(MsgType.HEARTBEAT_ACK))

                    elif msg_type == MsgType.HTTP_REQUEST:
                        asyncio.create_task(
                            _handle_http(ws, channel_id, msg["payload"], rules)
                        )

                    elif msg_type == MsgType.TCP_OPEN:
                        payload = msg["payload"]
                        asyncio.create_task(
                            open_tcp(
                                payload["local_host"], payload["local_port"],
                                channel_id, send_tcp_data, send_tcp_close
                            )
                        )

                    elif msg_type == MsgType.TCP_DATA:
                        data = decode_data(msg["data"])
                        await write_tcp(channel_id, data)

                    elif msg_type == MsgType.TCP_CLOSE:
                        await close_tcp(channel_id)

        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"Connection closed: {e}")
        except OSError as e:
            logger.error(f"Connection failed: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")

        logger.info(f"Reconnecting in {retry_delay}s...")
        await asyncio.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 60)


async def _handle_http(ws, channel_id: str, request_data: dict, rules: list):
    # 通过 Host header 匹配规则
    host = request_data.get("headers", {}).get("host", "").split(":")[0]
    rule = next(
        (r for r in rules if r["type"] == "http" and r["subdomain"] == host),
        None
    )
    if rule:
        response = await forward_http(rule["local_host"], rule["local_port"], request_data)
    else:
        response = {"status_code": 404, "headers": {}, "body": f"No rule for host: {host}"}

    await ws.send(encode(MsgType.HTTP_RESPONSE, channel_id=channel_id, payload=response))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="easy_vpn client")
    parser.add_argument("--config", default="config.yml", help="config file path")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(str(config_path))
    asyncio.run(run(config))
