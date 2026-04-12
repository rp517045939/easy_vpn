"""
easy_vpn Server 入口。

启动时：
  1. 加载规则（rules.json）
  2. 为所有 TCP 规则启动对应的 TcpListener
  3. 启动 FastAPI（HTTP 管理 API + WebSocket 隧道端点）

端口说明：
  :8080  HTTP，经 Nginx 代理（管理面板 + HTTP 隧道 + WebSocket 控制通道）
  :2200-2299  TCP，docker-compose 直接暴露（SSH 等 TCP 隧道）
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：加载规则，启动所有 TCP 监听器
    # await startup()
    yield
    # 关闭：停止所有 TCP 监听器
    # await shutdown()


app = FastAPI(title="easy_vpn", lifespan=lifespan)

# 管理面板 REST API
app.include_router(api_router)

# WebSocket 端点：Client 注册隧道、接收规则、收发隧道数据
# @app.websocket("/tunnel/ws")
# async def tunnel_ws(websocket: WebSocket): ...

# HTTP 穿透流量入口（根据 Host 头路由到对应 Client 的隧道）
# @app.api_route("/{path:path}", methods=[...])
# async def proxy_handler(request: Request): ...

# 健康检查（deploy/install.sh 用于验证容器启动状态）
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# Vue 面板静态文件（生产环境，build 产物）
# app.mount("/", StaticFiles(directory="static", html=True), name="static")
