import asyncio
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api import router as api_router
from auth import verify_client_token
from config import settings
from protocol import MsgType, decode, encode
from rules import rules_manager
from tcp_listener import tcp_listener
from tunnel_manager import tunnel_manager
from udp_listener import udp_listener

logger = logging.getLogger(__name__)

LOG_RETENTION_DAYS = 7
LOG_TOTAL_SIZE_LIMIT = 10 * 1024 * 1024 * 1024  # 10 GiB
LOG_ROTATE_MAX_BYTES = 100 * 1024 * 1024        # 100 MiB / file
LOG_ROTATE_BACKUP_COUNT = 120
LOG_CLEANUP_INTERVAL = 3600                     # 1 hour


def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "easy_vpn_server.log"
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_ROTATE_MAX_BYTES,
        backupCount=LOG_ROTATE_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler],
        force=True,
    )


def _list_log_files(log_dir: Path) -> list[Path]:
    return sorted(
        [p for p in log_dir.glob("easy_vpn_server.log*") if p.is_file()],
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
            stat = path.stat()
            if stat.st_mtime < expire_before:
                size_mb = stat.st_size / (1024 * 1024)
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


_log_dir = Path("logs")
configure_logging(_log_dir)
for _action in cleanup_log_dir(_log_dir):
    logger.info(_action)
logger.info(f"File logging enabled: {_log_dir / 'easy_vpn_server.log'}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化 DB、TCP 监听器、心跳任务、流量 flush 任务
    from traffic_db import init_db
    await init_db()
    tcp_listener.set_tunnel_manager(tunnel_manager)
    udp_listener.set_tunnel_manager(tunnel_manager)
    tunnel_manager.set_udp_listener(udp_listener)
    for rule in rules_manager.get_all():
        if rule["type"] == "tcp" and rule.get("enabled", True):
            await tcp_listener.start(
                rule["server_port"], rule["client_id"],
                rule["local_host"], rule["local_port"],
            )
            if rule.get("app_protocol") == "rdp" and rule.get("udp_enabled", True):
                await udp_listener.start(
                    rule["server_port"], rule["client_id"],
                    rule["local_host"], rule["local_port"],
                )
    heartbeat_task      = asyncio.create_task(tunnel_manager.heartbeat_loop())
    traffic_flush_task  = asyncio.create_task(tunnel_manager.traffic_flush_loop())
    log_cleanup_task    = asyncio.create_task(log_cleanup_loop(_log_dir))
    logger.info("easy_vpn server started")
    yield
    # 关闭：取消任务，最后 flush 一次流量
    heartbeat_task.cancel()
    traffic_flush_task.cancel()
    log_cleanup_task.cancel()
    await tunnel_manager._flush_traffic()
    await tcp_listener.stop_all()
    await udp_listener.stop_all()
    logger.info("easy_vpn server stopped")


app = FastAPI(title="easy_vpn", lifespan=lifespan)
app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/tunnel/ws")
async def tunnel_ws(websocket: WebSocket):
    await websocket.accept()
    client_id = None
    try:
        # 第一条消息必须是 register
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
        msg = decode(raw)

        if msg.get("type") != MsgType.REGISTER:
            await websocket.close(code=4001, reason="First message must be register")
            return

        payload = msg.get("payload", {})
        if not verify_client_token(payload.get("token", "")):
            await websocket.close(code=4003, reason="Invalid token")
            return

        client_id = payload.get("client_id", "").strip()
        if not client_id:
            await websocket.close(code=4002, reason="client_id is required")
            return

        await tunnel_manager.connect(client_id, websocket)

        while True:
            raw = await websocket.receive_text()
            await tunnel_manager.dispatch(client_id, raw)

    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        logger.warning("Client did not register in time")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if client_id:
            await tunnel_manager.disconnect(client_id, websocket=websocket)


# 静态文件（Vue build 产物）
_static_dir = Path("static")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    host = request.headers.get("host", "").split(":")[0]

    # 管理面板域名 → 服务 Vue SPA
    if host == settings.panel_host or host in ("localhost", "127.0.0.1"):
        if _static_dir.exists():
            target = _static_dir / path
            if target.exists() and target.is_file():
                return FileResponse(str(target))
            path_obj = Path(path)
            # 路径含隐藏文件/目录（以 . 开头）或有文件扩展名 → 404
            # 覆盖 /.env /.aws/credentials /.git/config /config.php 等扫描路径
            if any(p.startswith(".") for p in path_obj.parts) or path_obj.suffix:
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            # 无扩展名、无隐藏路径 → SPA 路由，返回 index.html
            return FileResponse(str(_static_dir / "index.html"))
        return JSONResponse({"message": "Dashboard not built yet. Run: cd dashboard && npm run build"}, status_code=503)

    # 其他域名 → HTTP 隧道代理
    from proxy import proxy_handler
    return await proxy_handler(request)
