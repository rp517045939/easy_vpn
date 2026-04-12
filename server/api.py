"""
管理面板 REST API。

路由：
  POST /api/auth/login                          - 用户名密码登录，返回 JWT
  GET  /api/clients                             - 在线 Client 列表及其规则
  GET  /api/clients/{client_id}/rules           - 指定 Client 的隧道规则
  POST /api/clients/{client_id}/rules           - 新增隧道规则
  PUT  /api/clients/{client_id}/rules/{subdomain} - 修改隧道规则
  DELETE /api/clients/{client_id}/rules/{subdomain} - 删除隧道规则
  GET  /api/stats                               - 全局流量统计
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.post("/auth/login")
async def login():
    pass


@router.get("/clients")
async def list_clients():
    pass


@router.get("/clients/{client_id}/rules")
async def get_rules(client_id: str):
    pass


@router.post("/clients/{client_id}/rules")
async def add_rule(client_id: str):
    pass


@router.put("/clients/{client_id}/rules/{subdomain:path}")
async def update_rule(client_id: str, subdomain: str):
    pass


@router.delete("/clients/{client_id}/rules/{subdomain:path}")
async def delete_rule(client_id: str, subdomain: str):
    pass


@router.get("/stats")
async def get_stats():
    pass
