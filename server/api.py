import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import create_access_token, verify_admin, get_current_user
from config import settings
from rules import rules_manager
from tunnel_manager import tunnel_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _udp_enabled(rule: dict) -> bool:
    return rule.get("type") == "tcp" and rule.get("app_protocol") == "rdp" and rule.get("udp_enabled", True)


async def _start_tcp_udp(rule: dict) -> None:
    from tcp_listener import tcp_listener
    await tcp_listener.start(
        rule["server_port"], rule["client_id"],
        rule["local_host"], rule["local_port"]
    )
    if _udp_enabled(rule):
        from udp_listener import udp_listener
        await udp_listener.start(
            rule["server_port"], rule["client_id"],
            rule["local_host"], rule["local_port"]
        )


async def _stop_tcp_udp(rule: dict) -> None:
    from tcp_listener import tcp_listener
    await tcp_listener.stop(rule["server_port"])
    if _udp_enabled(rule):
        from udp_listener import udp_listener
        await udp_listener.stop(rule["server_port"])


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
    return await tunnel_manager.get_online_clients()


@router.get("/traffic")
async def list_traffic(user=Depends(get_current_user)):
    """所有设备的流量（含离线历史），按最近活跃时间倒序。"""
    return await tunnel_manager.get_all_traffic()


@router.get("/traffic/{client_id}")
async def get_client_traffic(client_id: str, user=Depends(get_current_user)):
    """指定设备的今日/本月/本年流量及近 30 天明细。先 flush 确保数据最新。"""
    await tunnel_manager._flush_traffic()
    from traffic_db import query_client_detail
    return await query_client_detail(client_id)


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

    # TCP 规则：新规则默认启用，立即启动端口监听
    if rule["type"] == "tcp":
        await _start_tcp_udp(new_rule)

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

    # TCP/RDP 规则：只要有任意字段变更，一律先 stop 再 start（避免目标不更新）
    if old_rule and old_rule["type"] == "tcp":
        await _stop_tcp_udp(old_rule)
    if updated["type"] == "tcp" and updated.get("enabled", True):
        await _start_tcp_udp(updated)

    # 推送规则：如果 client_id 发生变更，旧 client 也要收到通知（规则已从它那边移走）
    old_client_id = old_rule["client_id"] if old_rule else None
    new_client_id = updated["client_id"]
    await tunnel_manager.push_rules(new_client_id, rules_manager.get_by_client(new_client_id))
    if old_client_id and old_client_id != new_client_id:
        await tunnel_manager.push_rules(old_client_id, rules_manager.get_by_client(old_client_id))

    return updated


@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, user=Depends(get_current_user)):
    try:
        rule = rules_manager.toggle_rule(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # TCP 规则：根据新状态启动或停止监听
    if rule["type"] == "tcp":
        if rule["enabled"]:
            await _start_tcp_udp(rule)
        else:
            await _stop_tcp_udp(rule)

    # 推送给 client（get_by_client 只推 enabled 的规则）
    await tunnel_manager.push_rules(rule["client_id"], rules_manager.get_by_client(rule["client_id"]))
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, user=Depends(get_current_user)):
    try:
        deleted = rules_manager.delete_rule(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # TCP 规则：停止端口监听
    if deleted["type"] == "tcp":
        await _stop_tcp_udp(deleted)

    await tunnel_manager.push_rules(deleted["client_id"], rules_manager.get_by_client(deleted["client_id"]))
    return {"ok": True}


# ------------------------------------------------------------------ 公开配置

@router.get("/config")
async def get_config():
    """返回前端需要的公开配置（无需登录）。"""
    return {"http_domain": settings.http_domain}


# ------------------------------------------------------------------ 端口

@router.get("/ports/available")
async def available_ports(user=Depends(get_current_user)):
    return rules_manager.get_available_ports()


# ------------------------------------------------------------------ 统计

@router.get("/stats")
async def get_stats(user=Depends(get_current_user)):
    all_rules = rules_manager.get_all()
    return {
        "online_clients": tunnel_manager.count_online(),
        "total_rules":    len(all_rules),
        "http_rules":     sum(1 for r in all_rules if r["type"] == "http"),
        "tcp_rules":      sum(1 for r in all_rules if r["type"] == "tcp"),
    }
