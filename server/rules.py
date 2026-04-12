import json
import uuid
import logging
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)
RULES_FILE = Path("/app/data/rules.json")


class RulesManager:

    def __init__(self):
        self._data: dict = self._load()

    # ------------------------------------------------------------------ 读

    def get_all(self) -> list:
        return self._data["rules"]

    def get_by_client(self, client_id: str) -> list:
        return [r for r in self._data["rules"] if r["client_id"] == client_id]

    def resolve_http(self, subdomain: str) -> dict | None:
        for r in self._data["rules"]:
            if r["type"] == "http" and r["subdomain"] == subdomain:
                return r
        return None

    def resolve_tcp(self, server_port: int) -> dict | None:
        for r in self._data["rules"]:
            if r["type"] == "tcp" and r["server_port"] == server_port:
                return r
        return None

    def get_used_tcp_ports(self) -> set:
        return {r["server_port"] for r in self._data["rules"] if r["type"] == "tcp"}

    def get_available_ports(self) -> list:
        used = self.get_used_tcp_ports()
        return [p for p in range(settings.tcp_port_min, settings.tcp_port_max + 1)
                if p not in used]

    # ------------------------------------------------------------------ 写

    def add_rule(self, rule: dict) -> dict:
        self._validate(rule)
        new_rule = {**rule, "id": str(uuid.uuid4())}
        self._data["rules"].append(new_rule)
        self._save()
        logger.info(f"Rule added: {new_rule}")
        return new_rule

    def update_rule(self, rule_id: str, updates: dict) -> dict:
        for i, r in enumerate(self._data["rules"]):
            if r["id"] == rule_id:
                updated = {**r, **updates, "id": rule_id}
                self._validate(updated, exclude_id=rule_id)
                self._data["rules"][i] = updated
                self._save()
                logger.info(f"Rule updated: {updated}")
                return updated
        raise ValueError(f"Rule not found: {rule_id}")

    def delete_rule(self, rule_id: str) -> dict:
        for i, r in enumerate(self._data["rules"]):
            if r["id"] == rule_id:
                self._data["rules"].pop(i)
                self._save()
                logger.info(f"Rule deleted: {rule_id}")
                return r
        raise ValueError(f"Rule not found: {rule_id}")

    # ------------------------------------------------------------------ 内部

    def _validate(self, rule: dict, exclude_id: str = None):
        rule_type = rule.get("type")
        if rule_type == "http":
            for f in ("client_id", "subdomain", "local_host", "local_port"):
                if not rule.get(f):
                    raise ValueError(f"HTTP rule missing field: {f}")
            # subdomain 唯一性检查
            for r in self._data["rules"]:
                if r["type"] == "http" and r["subdomain"] == rule["subdomain"] and r.get("id") != exclude_id:
                    raise ValueError(f"Subdomain already in use: {rule['subdomain']}")

        elif rule_type == "tcp":
            for f in ("client_id", "server_port", "local_host", "local_port"):
                if not rule.get(f):
                    raise ValueError(f"TCP rule missing field: {f}")
            port = rule["server_port"]
            if not (settings.tcp_port_min <= port <= settings.tcp_port_max):
                raise ValueError(f"server_port must be in {settings.tcp_port_min}-{settings.tcp_port_max}")
            # 端口唯一性检查
            for r in self._data["rules"]:
                if r["type"] == "tcp" and r["server_port"] == port and r.get("id") != exclude_id:
                    raise ValueError(f"TCP port already in use: {port}")
        else:
            raise ValueError(f"Invalid rule type: {rule_type}")

    def _load(self) -> dict:
        if RULES_FILE.exists():
            try:
                with open(RULES_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load rules: {e}")
        return {"rules": []}

    def _save(self):
        RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)


rules_manager = RulesManager()
