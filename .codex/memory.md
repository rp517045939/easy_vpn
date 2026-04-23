# Project Memory

本文件用于给进入本仓库的 CLI/Agent 提供稳定、可复用的项目记忆。
执行层规则请优先查看 `.codex/ops.md`。

## 说明

- 当前仓库内未发现可直接读取的历史线程/会话存档。
- 本文件基于以下可见信息整理：
  - 当前对话中用户明确给出的规则
  - 仓库内现有文档，尤其是 `CLAUDE.md`
- 如果后续发现新的固定约束，应优先更新本文件，而不是依赖会话记忆。

## 已确认环境

- 测试环境服务器：`119.91.235.65:22022`
- 生产环境服务器：`43.163.90.149:22022`

## 长期约定

- 未经用户明确授权，不要操作生产服务器 `43.163.90.149:22022`。
- 服务器上的服务更新，必须通过 GitHub 拉取代码。
- 不要使用 `rsync` 做代码同步发布，这会导致服务器代码与仓库产生漂移。

## 项目部署信息

- 项目：`easy_vpn`
- 服务端部署方式：`Docker Compose`
- Nginx 在宿主机上做反向代理。
- 项目包含一键部署脚本，当前文档中可见入口是：
  - `bash deploy/install.sh`
  - `bash deploy/install.sh --test-skip-ssl`
- 仓库中当前可见的服务端部署脚本文件为：
  - `deploy/server_deploy.sh`

## 项目关键约束

- GitHub 为公开仓库，禁止推送敏感信息：
  - IP
  - 密钥
  - `.env`
  - 密码
  - 真实配置
- TCP 端口范围：`2200-2299`
- 不要硬编码单个 TCP 端口，端口由面板统一分配。
- Server 启动时会从 `rules.json` 恢复已有 TCP 规则并自动监听。

## 代码与架构速记

- `server/main.py`：FastAPI 入口、WebSocket 握手、启动任务
- `server/tunnel_manager.py`：在线 Client、HTTP/TCP channel 生命周期
- `server/tcp_listener.py`：2200-2299 TCP 监听
- `server/api.py`：管理面板 API
- `server/rules.py`：规则持久化与推送
- `client/main.py`：Client 连接、重连、消息分发
- `client/forwarder.py`：本地 HTTP/TCP 转发
- `client/web_ui.py`：本地 Web UI

## 本地开发速记

- 一键启动开发环境：`bash dev.sh`
- 后端文档：`http://localhost:8080/docs`
- 前端开发地址：`http://localhost:5173`

## 维护建议

- 每次出现新的稳定规则，直接追加到本文件。
- 影响日常执行的强约束，优先写入 `.codex/ops.md`。
- 如果后续要实现真正的“跨线程记忆”，需要把会话摘要持久化到仓库或固定路径，而不是依赖 CLI 自动读取历史会话。
