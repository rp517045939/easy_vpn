"""
easy_vpn Server 入口。

启动方式：
  uvicorn main:app --host 0.0.0.0 --port 8080
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api import router as api_router

app = FastAPI(title="easy_vpn")

# 管理面板 REST API
app.include_router(api_router)

# WebSocket：Client 注册隧道
# @app.websocket("/tunnel/ws")

# HTTP 穿透流量入口（根据 Host 路由到对应隧道）
# app.add_route(...)

# Vue 面板静态文件（生产环境）
# app.mount("/", StaticFiles(directory="static", html=True), name="static")
