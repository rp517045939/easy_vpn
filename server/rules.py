"""
隧道规则管理。

规则分两类：

  HTTP 规则：
    type:       "http"
    client_id:  "nas"
    subdomain:  "nas.ruanpengpeng.cn"
    local_host: "127.0.0.1"
    local_port: 5000
    label:      "NAS 管理页面"

  TCP 规则：
    type:        "tcp"
    client_id:   "mac"
    server_port: 2222            # 云服务器上监听的端口（2200-2299 范围内）
    local_host:  "127.0.0.1"
    local_port:  22              # Client 本地端口（SSH 默认 22）
    label:       "Mac SSH"

存储：JSON 文件持久化（/app/data/rules.json，Docker volume 挂载）

规则变更时：
  - 持久化到 rules.json
  - 若 Client 在线，通过 WebSocket 实时推送更新
  - TCP 规则新增时，启动对应端口的 TcpListener
  - TCP 规则删除时，停止对应端口的 TcpListener
"""
import json
from pathlib import Path

RULES_FILE = Path("/app/data/rules.json")


class RulesManager:

    def get_by_client(self, client_id: str) -> list:
        """获取指定 Client 的所有规则（HTTP + TCP）"""
        pass

    def get_all(self) -> dict:
        """获取所有 Client 的规则，供面板展示"""
        pass

    def add_rule(self, rule: dict) -> dict:
        """
        新增规则。
        HTTP 规则：校验 subdomain 唯一性。
        TCP 规则：校验 server_port 在 2200-2299 范围内且未被占用，
                  启动 TcpListener。
        返回带 id 的完整规则。
        """
        pass

    def update_rule(self, rule_id: str, rule: dict) -> dict:
        """修改规则，若为 TCP 规则且端口变更，重启对应 TcpListener"""
        pass

    def delete_rule(self, rule_id: str) -> None:
        """
        删除规则。
        TCP 规则：停止对应 TcpListener。
        """
        pass

    def resolve_http(self, subdomain: str) -> dict | None:
        """根据 subdomain 查找 HTTP 规则，供 proxy.py 使用"""
        pass

    def resolve_tcp(self, server_port: int) -> dict | None:
        """根据 server_port 查找 TCP 规则，供 tcp_listener.py 使用"""
        pass

    def _load(self) -> dict:
        """从 JSON 文件加载规则"""
        pass

    def _save(self, data: dict) -> None:
        """持久化规则到 JSON 文件"""
        pass


rules_manager = RulesManager()
