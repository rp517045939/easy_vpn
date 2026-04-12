"""
隧道规则管理。

职责：
- 存储每个 Client 的隧道规则（subdomain → local_host:local_port）
- 提供规则的增删改查接口，供管理面板 API 调用
- Client 连接时，将其对应的规则下发给 Client

数据结构示例：
{
    "nas": [
        {"subdomain": "nas.ruanpengpeng.cn", "local_host": "127.0.0.1", "local_port": 5000},
    ],
    "mac": [
        {"subdomain": "mac.ruanpengpeng.cn", "local_host": "127.0.0.1", "local_port": 3000},
    ]
}

存储方式：JSON 文件持久化（无需引入数据库）
"""


class RulesManager:

    def get_rules(self, client_id: str) -> list:
        """获取指定 Client 的所有隧道规则"""
        pass

    def set_rules(self, client_id: str, rules: list) -> None:
        """更新指定 Client 的隧道规则，并推送给已在线的 Client"""
        pass

    def add_rule(self, client_id: str, rule: dict) -> None:
        """新增一条隧道规则"""
        pass

    def delete_rule(self, client_id: str, subdomain: str) -> None:
        """删除一条隧道规则"""
        pass

    def get_all(self) -> dict:
        """获取所有 Client 的规则（供面板展示）"""
        pass

    def resolve(self, subdomain: str) -> dict | None:
        """根据 subdomain 反查对应的 client_id 和本地端口（供 proxy.py 使用）"""
        pass


rules_manager = RulesManager()
