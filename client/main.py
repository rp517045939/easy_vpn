"""
easy_vpn Client

用法：
  python main.py --config config.yml [--ui-port 7070]
"""
import asyncio
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
import sys
import time
from pathlib import Path

import yaml
import websockets
import websockets.exceptions

from protocol import MsgType, encode, decode, decode_data
from forwarder import forward_http, open_tcp, write_tcp, close_tcp
from state import client_state, StateLogHandler

logger = logging.getLogger("easy_vpn_client")

LOG_RETENTION_DAYS = 7
LOG_TOTAL_SIZE_LIMIT = 10 * 1024 * 1024 * 1024  # 10 GiB
LOG_ROTATE_MAX_BYTES = 100 * 1024 * 1024        # 100 MiB / file
LOG_ROTATE_BACKUP_COUNT = 120
LOG_CLEANUP_INTERVAL = 3600                     # 1 hour


def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "easy_vpn_client.log"
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    state_handler = StateLogHandler()

    # Windows 文件锁会导致日志轮转时 PermissionError；
    # delay=True 让 handler 懒打开文件，降低冲突窗口。
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_ROTATE_MAX_BYTES,
        backupCount=LOG_ROTATE_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setFormatter(formatter)

    # Windows 上，RotatingFileHandler.doRollover() 调用 os.rename()
    # 时可能遭遇短暂文件锁，用重试包裹 emit 消除 PermissionError。
    if sys.platform == "win32":
        _original_emit = file_handler.emit

        def _safe_emit(record: logging.LogRecord) -> None:
            for _ in range(5):
                try:
                    _original_emit(record)
                    return
                except PermissionError:
                    time.sleep(0.05)

        file_handler.emit = _safe_emit  # type: ignore[method-assign]

    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, state_handler, file_handler],
        force=True,
    )


def _list_log_files(log_dir: Path) -> list[Path]:
    return sorted(
        [p for p in log_dir.glob("easy_vpn_client.log*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
    )


def cleanup_log_dir(log_dir: Path) -> list[str]:
    if not log_dir.exists():
        return []

    actions: list[str] = []
    now = time.time()
    expire_before = now - LOG_RETENTION_DAYS * 24 * 3600
    files = _list_log_files(log_dir)

    for path in files:
        try:
            if path.stat().st_mtime < expire_before:
                size_mb = path.stat().st_size / (1024 * 1024)
                path.unlink(missing_ok=True)
                actions.append(f"deleted expired log: {path.name} ({size_mb:.1f} MiB)")
        except FileNotFoundError:
            continue
        except Exception as e:
            actions.append(f"failed to delete expired log {path.name}: {e}")

    files = _list_log_files(log_dir)
    total_size = sum(path.stat().st_size for path in files)
    if total_size <= LOG_TOTAL_SIZE_LIMIT:
        return actions

    for path in files:
        if total_size <= LOG_TOTAL_SIZE_LIMIT:
            break
        try:
            size = path.stat().st_size
            size_mb = size / (1024 * 1024)
            path.unlink(missing_ok=True)
            total_size -= size
            actions.append(f"deleted oversized log: {path.name} ({size_mb:.1f} MiB)")
        except FileNotFoundError:
            continue
        except Exception as e:
            actions.append(f"failed to delete oversized log {path.name}: {e}")

    return actions


async def log_cleanup_loop(log_dir: Path) -> None:
    while True:
        try:
            for action in cleanup_log_dir(log_dir):
                logger.info(action)
        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
        await asyncio.sleep(LOG_CLEANUP_INTERVAL)


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


async def run_once(config: dict):
    """单次连接会话，返回后由外层重试。"""
    server_url = config["server"]["url"]
    token      = config["server"]["token"]
    client_id  = config["client"]["id"]

    client_state.server_url = server_url
    client_state.client_id  = client_id
    client_state.status     = "connecting"
    client_state.rules      = []

    logger.info(f"Connecting to {server_url} as [{client_id}]...")
    async with websockets.connect(server_url, ping_interval=None) as ws:
        client_state.status       = "connected"
        client_state.connected_at = time.time()
        logger.info("Connected")

        # 多个并发 TCP channel 的 asyncio.Task 会同时调用 ws.send()，
        # 必须加锁串行化，否则 WebSocket 帧会损坏导致数据混乱。
        _ws_lock = asyncio.Lock()

        async def ws_send(text: str) -> None:
            async with _ws_lock:
                await ws.send(text)

        # 注册
        await ws_send(encode(MsgType.REGISTER, payload={
            "token": token, "client_id": client_id
        }))
        logger.info("Registered, waiting for rules...")

        async def send_tcp_data(channel_id: str, data: bytes):
            await ws_send(encode(MsgType.TCP_DATA, channel_id=channel_id, data=data))

        async def send_tcp_opened(channel_id: str):
            await ws_send(encode(MsgType.TCP_OPENED, channel_id=channel_id))

        async def send_tcp_close(channel_id: str):
            await ws_send(encode(MsgType.TCP_CLOSE, channel_id=channel_id))

        async def send_http_response(channel_id: str, response: dict):
            await ws_send(encode(MsgType.HTTP_RESPONSE, channel_id=channel_id, payload=response))

        async for raw in ws:
            msg        = decode(raw)
            msg_type   = msg.get("type")
            channel_id = msg.get("channel_id")

            if msg_type == MsgType.RULES_PUSH:
                rules = msg["payload"]["rules"]
                client_state.rules = rules
                logger.info(f"Rules updated: {len(rules)} rule(s)")
                for r in rules:
                    logger.info(f"  [{r['type']}] {r.get('subdomain') or r.get('server_port')} "
                                f"-> {r['local_host']}:{r['local_port']}")

            elif msg_type == MsgType.HEARTBEAT:
                await ws_send(encode(MsgType.HEARTBEAT_ACK))

            elif msg_type == MsgType.HTTP_REQUEST:
                asyncio.create_task(
                    _handle_http(send_http_response, channel_id, msg["payload"], client_state.rules)
                )

            elif msg_type == MsgType.TCP_OPEN:
                payload = msg["payload"]
                asyncio.create_task(
                    open_tcp(
                        payload["local_host"], payload["local_port"],
                        channel_id, send_tcp_opened, send_tcp_data, send_tcp_close
                    )
                )

            elif msg_type == MsgType.TCP_DATA:
                data = decode_data(msg["data"])
                await write_tcp(channel_id, data)

            elif msg_type == MsgType.TCP_CLOSE:
                await close_tcp(channel_id)


async def run(config_path: str):
    """外层重试循环，支持配置热重载。"""
    reload_event = asyncio.Event()
    client_state.reload_event = reload_event
    client_state.config_path  = config_path

    retry_delay = 1

    while True:
        # 检查是否需要热重载配置
        if reload_event.is_set():
            reload_event.clear()
            logger.info("Config reloaded, reconnecting...")
            retry_delay = 1

        config = load_config(config_path)
        client_state.retry_delay = retry_delay

        try:
            await run_once(config)
            retry_delay = 1   # 正常断开重置
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"Connection closed: {e}")
        except OSError as e:
            logger.error(f"Connection failed: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
        finally:
            client_state.status       = "disconnected"
            client_state.connected_at = None
            client_state.reset_traffic()

        # 等待重试或配置变更
        logger.info(f"Reconnecting in {retry_delay}s...")
        try:
            await asyncio.wait_for(reload_event.wait(), timeout=retry_delay)
        except asyncio.TimeoutError:
            pass

        retry_delay = min(retry_delay * 2, 60)


async def _handle_http(send_http_response, channel_id: str, request_data: dict, rules: list):
    host = request_data.get("headers", {}).get("host", "").split(":")[0]
    try:
        rule = next(
            (r for r in rules if r["type"] == "http" and r["subdomain"] == host),
            None
        )
        if rule:
            response = await forward_http(rule["local_host"], rule["local_port"], request_data)
        else:
            response = {"status_code": 404, "headers": {}, "body": f"No rule for host: {host}"}

        await send_http_response(channel_id, response)
    except Exception as e:
        logger.exception(f"HTTP handler failed [{channel_id[:8]}] host={host}: {e}")


if __name__ == "__main__":
    # aiohttp 在 Windows 上要求 SelectorEventLoop；Python 3.8+ 默认是
    # ProactorEventLoop，需在 asyncio.run() 之前切换。
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(description="easy_vpn client")
    parser.add_argument("--config",   default="config.yml",  help="config file path")
    parser.add_argument("--ui-host",  default="127.0.0.1",   help="Web UI listen host (default: 127.0.0.1)")
    parser.add_argument("--ui-port",  type=int, default=7070, help="Web UI port (default: 7070)")
    parser.add_argument("--no-ui",    action="store_true",    help="disable Web UI")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    log_dir = config_path.resolve().parent / "logs"
    configure_logging(log_dir)
    for action in cleanup_log_dir(log_dir):
        logger.info(action)
    logger.info(f"File logging enabled: {log_dir / 'easy_vpn_client.log'}")

    async def main():
        tasks = [
            asyncio.create_task(run(str(config_path))),
            asyncio.create_task(log_cleanup_loop(log_dir)),
        ]
        if not args.no_ui:
            from web_ui import start_web_ui
            client_state.ui_host = args.ui_host
            client_state.ui_port = args.ui_port
            client_state.ui_password = os.getenv("EASY_VPN_UI_PASSWORD") or secrets.token_urlsafe(9)
            tasks.append(asyncio.create_task(start_web_ui(host=args.ui_host, port=args.ui_port)))
        await asyncio.gather(*tasks)

    asyncio.run(main())
