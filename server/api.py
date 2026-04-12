"""
管理面板 REST API。

路由：
  POST   /api/auth/login          - 登录，返回 JWT

  GET    /api/clients             - 在线 Client 列表（含规则和状态）

  GET    /api/rules               - 所有规则（HTTP + TCP）
  POST   /api/rules               - 新增规则（HTTP 或 TCP）
  PUT    /api/rules/{rule_id}     - 修改规则
  DELETE /api/rules/{rule_id}     - 删除规则

  GET    /api/ports/available     - 查询可用的 TCP 端口（2200-2299 范围内未被占用的）

  GET    /api/stats               - 全局流量统计
"""
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api")


# ---------- 认证 ----------

@router.post("/auth/login")
async def login():
    pass


# ---------- Clients ----------

@router.get("/clients")
async def list_clients():
    """返回在线 Client 列表，每个 Client 含其规则列表和连接时长"""
    pass


# ---------- 规则管理（HTTP + TCP 统一入口）----------

@router.get("/rules")
async def list_rules():
    pass


@router.post("/rules")
async def add_rule():
    """
    新增规则，body 示例：

    HTTP 规则：
    {"type": "http", "client_id": "nas", "subdomain": "nas.ruanpengpeng.cn",
     "local_host": "127.0.0.1", "local_port": 5000, "label": "NAS 管理页面"}

    TCP 规则：
    {"type": "tcp", "client_id": "mac", "server_port": 2222,
     "local_host": "127.0.0.1", "local_port": 22, "label": "Mac SSH"}
    """
    pass


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str):
    pass


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    pass


# ---------- 端口管理 ----------

@router.get("/ports/available")
async def available_ports():
    """返回 2200-2299 范围内未被占用的端口列表，供面板创建 TCP 规则时选择"""
    pass


# ---------- 统计 ----------

@router.get("/stats")
async def get_stats():
    pass
