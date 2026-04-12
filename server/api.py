"""
管理面板 REST API。

路由：
  POST /api/auth/login        - 用户名密码登录，返回 JWT
  GET  /api/clients           - 在线 Client 列表
  GET  /api/clients/{id}      - 单个 Client 详情（隧道规则、流量统计）
  GET  /api/stats             - 全局流量统计
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.post("/auth/login")
async def login():
    pass


@router.get("/clients")
async def list_clients():
    pass


@router.get("/clients/{client_id}")
async def get_client(client_id: str):
    pass


@router.get("/stats")
async def get_stats():
    pass
