import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化 TCP 监听器 + 心跳任务
    tcp_listener.set_tunnel_manager(tunnel_manager)
    for rule in rules_manager.get_all():
        if rule["type"] == "tcp":
            await tcp_listener.start(
                rule["server_port"], rule["client_id"],
                rule["local_host"], rule["local_port"],
            )
    heartbeat_task = asyncio.create_task(tunnel_manager.heartbeat_loop())
    logger.info("easy_vpn server started")
    yield
    # 关闭
    heartbeat_task.cancel()
    await tcp_listener.stop_all()
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
