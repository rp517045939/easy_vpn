import asyncio
import aiohttp
import logging
from typing import Callable

from state import client_state

logger = logging.getLogger(__name__)

# channel_id → asyncio.StreamWriter（本地 TCP 连接）
_tcp_writers: dict[str, asyncio.StreamWriter] = {}


# ------------------------------------------------------------------ HTTP

async def forward_http(local_host: str, local_port: int, request_data: dict) -> dict:
    path = request_data.get("path", "/")
    qs   = request_data.get("query_string", "")
    url  = f"http://{local_host}:{local_port}{path}"
    if qs:
        url += f"?{qs}"

    headers = {
        k: v for k, v in request_data.get("headers", {}).items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }
    headers["Host"] = f"{local_host}:{local_port}"

    body = request_data.get("body", "")
    raw_body = body.encode("latin-1") if body else None

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method=request_data.get("method", "GET"),
                url=url,
                headers=headers,
                data=raw_body,
                allow_redirects=False,
            ) as resp:
                resp_body = await resp.read()
                # 统计流量：recv = 收到的请求字节，sent = 发回的响应字节
                client_state.record_traffic(
                    recv=len(raw_body) if raw_body else 0,
                    sent=len(resp_body),
                    http_req=1,
                )
                return {
                    "status_code": resp.status,
                    "headers":     dict(resp.headers),
                    "body":        resp_body.decode("latin-1"),
                }
    except Exception as e:
        logger.error(f"HTTP forward error [{local_host}:{local_port}]: {e}")
        return {"status_code": 502, "headers": {}, "body": f"Bad Gateway: {e}"}


# ------------------------------------------------------------------ TCP

async def open_tcp(local_host: str, local_port: int,
                   channel_id: str,
                   send_data_fn: Callable,   # send_data_fn(channel_id, bytes)
                   send_close_fn: Callable   # send_close_fn(channel_id)
                   ) -> None:
    """
    连接本地 TCP 服务，建立双向数据管道。
    持续运行直到本地连接断开或收到 close_tcp() 调用。
    """
    try:
        reader, writer = await asyncio.open_connection(local_host, local_port)
        _tcp_writers[channel_id] = writer
        client_state.record_traffic(tcp_conn=1)
        logger.info(f"TCP channel {channel_id[:8]} -> {local_host}:{local_port}")

        # 本地 TCP → Server（上行：本地服务 → 发给 server）
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                client_state.record_traffic(sent=len(data))
                await send_data_fn(channel_id, data)
        except Exception as e:
            logger.debug(f"TCP read {channel_id[:8]}: {e}")
        finally:
            _tcp_writers.pop(channel_id, None)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            await send_close_fn(channel_id)

    except Exception as e:
        logger.error(f"TCP open {channel_id[:8]} [{local_host}:{local_port}]: {e}")
        await send_close_fn(channel_id)


async def write_tcp(channel_id: str, data: bytes) -> None:
    writer = _tcp_writers.get(channel_id)
    if writer:
        try:
            writer.write(data)
            await writer.drain()
            client_state.record_traffic(recv=len(data))
        except Exception as e:
            logger.error(f"TCP write {channel_id[:8]}: {e}")


async def close_tcp(channel_id: str) -> None:
    writer = _tcp_writers.pop(channel_id, None)
    if writer:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
    logger.info(f"TCP channel {channel_id[:8]} closed")
