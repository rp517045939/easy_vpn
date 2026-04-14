# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

easy_vpn：基于 WebSocket 的内网穿透工具。云服务器运行 Server，内网设备运行 Client，通过 WebSocket 长连接多路复用实现 HTTP 子域名代理和 TCP 端口转发。管理面板（Vue 3）负责在线设备展示和隧道规则管理。

## 本地开发

```bash
# 前置：复制并填写 .env
cp .env.example .env

# 一键启动（后端 + 前端热重载）
bash dev.sh
```

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 管理面板（Vite 开发服务器） |
| http://localhost:8080/docs | 后端 API 文档（Swagger） |

单独启动后端（在项目根目录，需激活 `.venv`）：

```bash
source .venv/bin/activate
cd server
uvicorn main:app --host 0.0.0.0 --port 8080 --reload --env-file ../.env
```

单独启动前端：

```bash
cd dashboard
npm run dev
```

构建前端产物（输出到 `server/static/`）：

```bash
cd dashboard
npm install
npm run build
```

启动 Client：

```bash
cd client
pip install -r requirements.txt
python main.py --config config.yml         # 默认开启 Web UI localhost:7070
python main.py --config config.yml --no-ui # 关闭 Web UI
```

## 架构概览

### 通信协议

一条 WebSocket 连接（`/tunnel/ws`）通过 `channel_id` 多路复用，所有消息为 JSON 文本帧：

```json
{"type": "...", "channel_id": "uuid", "data": "base64", "payload": {}}
```

消息类型定义在 `server/protocol.py` 和 `client/protocol.py`（两份保持同步）：

- `register` / `rules_push` / `heartbeat` / `heartbeat_ack`：控制消息
- `http_request` / `http_response`：HTTP 隧道，每个请求一个 channel_id，Future 等待响应
- `tcp_open` / `tcp_data` / `tcp_close`：TCP 隧道，每个连接一个 channel_id，Queue 传输数据流

### Server 关键模块

| 文件 | 职责 |
|------|------|
| `main.py` | FastAPI 入口；启动 TCP 监听器和心跳任务；WebSocket 握手和注册；`catch_all` 路由区分管理面板域名和 HTTP 隧道域名 |
| `tunnel_manager.py` | `TunnelManager` 单例；管理所有 Client 连接；HTTP channel（Future）和 TCP channel（Queue）的生命周期；心跳检测 |
| `tcp_listener.py` | 动态监听 2200-2299 端口段；外部 TCP 连接到达后通过 WebSocket 桥接到对应 Client |
| `proxy.py` | 收到 HTTP 请求，按 `Host` 头找到对应 Client，调用 `tunnel_manager.forward_http()` |
| `rules.py` | JSON 文件持久化规则；规则变更后调用 `tunnel_manager.push_rules()` 实时推送给在线 Client |
| `api.py` | 管理面板 REST API：登录、规则 CRUD、在线设备列表、可用端口查询 |
| `config.py` | 从环境变量读取配置（SECRET_KEY、ADMIN_USERNAME 等） |
| `auth.py` | JWT 认证（面板登录）和 Client token 校验 |

### Client 关键模块

| 文件 | 职责 |
|------|------|
| `main.py` | 连接 Server，发送 register，接收规则和消息，分发给 forwarder；指数退避重连（最长 60s）；支持配置热重载 |
| `forwarder.py` | `forward_http()`：向本地服务发 HTTP 请求；`open_tcp()`：与本地端口建立 TCP 连接并双向转发 |
| `state.py` | `ClientState` 单例，保存连接状态、规则列表、日志缓冲，供 Web UI 读取 |
| `web_ui.py` | 本地 Web 管理界面（默认 localhost:7070），展示连接状态和规则 |

### 规则下发流程

1. 管理员在面板 CRUD 规则 → `api.py` 调用 `rules_manager`
2. `rules_manager` 持久化规则（`server/data/rules.json`）
3. 若 Client 在线，立即调用 `tunnel_manager.push_rules()` 推送 `rules_push` 消息
4. Client 收到 `rules_push` 后更新内存规则，立即生效，无需重启

### 部署

服务端通过 Docker Compose 部署：

```bash
docker compose up -d       # 启动
docker logs -f easy_vpn    # 查看日志
```

一键部署脚本（自动处理 Nginx + SSL）：

```bash
bash deploy/install.sh              # 正式环境
bash deploy/install.sh --test-skip-ssl  # 测试环境
```

## 重要约束

- **生产服务器（43.163.90.149:22022）禁止随便操作**；测试服务器（119.91.235.65:22022）可自由使用
- **GitHub 公开仓库**：禁止推送 IP、密钥、.env、密码、真实配置等敏感信息
- TCP 端口范围：2200–2299，由面板统一分配，不要硬编码特定端口
- Server 启动时会自动从 `rules.json` 恢复并监听已有 TCP 规则
