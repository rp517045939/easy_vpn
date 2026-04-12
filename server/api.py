import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import create_access_token, verify_admin, get_current_user
from rules import rules_manager
from tunnel_manager import tunnel_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ------------------------------------------------------------------ 认证

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(req: LoginRequest):
    if not verify_admin(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": req.username})
    return {"access_token": token, "token_type": "bearer"}


# ------------------------------------------------------------------ Clients

@router.get("/clients")
async def list_clients(user=Depends(get_current_user)):
    return tunnel_manager.get_online_clients()


# ------------------------------------------------------------------ 规则

@router.get("/rules")
async def list_rules(user=Depends(get_current_user)):
    return rules_manager.get_all()


@router.post("/rules")
async def add_rule(rule: dict, user=Depends(get_current_user)):
    try:
        new_rule = rules_manager.add_rule(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # TCP 规则：立即启动端口监听
    if rule["type"] == "tcp":
        from tcp_listener import tcp_listener
        await tcp_listener.start(
            rule["server_port"], rule["client_id"],
            rule["local_host"], rule["local_port"]
        )

    # 推送最新规则给在线 Client
    await tunnel_manager.push_rules(rule["client_id"], rules_manager.get_by_client(rule["client_id"]))
    return new_rule


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, updates: dict, user=Depends(get_current_user)):
    try:
        old_rule = next((r for r in rules_manager.get_all() if r["id"] == rule_id), None)
        updated = rules_manager.update_rule(rule_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # TCP 规则端口变更：重启监听器
    if updated["type"] == "tcp" and old_rule:
        from tcp_listener import tcp_listener
        if old_rule["server_port"] != updated["server_port"]:
            await tcp_listener.stop(old_rule["server_port"])
        await tcp_listener.start(
            updated["server_port"], updated["client_id"],
            updated["local_host"], updated["local_port"]
        )

    await tunnel_manager.push_rules(updated["client_id"], rules_manager.get_by_client(updated["client_id"]))
    return updated


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, user=Depends(get_current_user)):
    try:
        deleted = rules_manager.delete_rule(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # TCP 规则：停止端口监听
    if deleted["type"] == "tcp":
        from tcp_listener import tcp_listener
        await tcp_listener.stop(deleted["server_port"])

    await tunnel_manager.push_rules(deleted["client_id"], rules_manager.get_by_client(deleted["client_id"]))
    return {"ok": True}


# ------------------------------------------------------------------ 端口

@router.get("/ports/available")
async def available_ports(user=Depends(get_current_user)):
    return rules_manager.get_available_ports()


# ------------------------------------------------------------------ 统计

@router.get("/stats")
async def get_stats(user=Depends(get_current_user)):
    clients = tunnel_manager.get_online_clients()
    all_rules = rules_manager.get_all()
    return {
        "online_clients": len(clients),
        "total_rules": len(all_rules),
        "http_rules": sum(1 for r in all_rules if r["type"] == "http"),
        "tcp_rules":  sum(1 for r in all_rules if r["type"] == "tcp"),
    }
