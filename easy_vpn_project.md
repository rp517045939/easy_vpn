# easy_vpn 项目备忘录

## 一、需求背景

家庭环境有 NAS（飞牛，长期开机）、Mac（基本长期开机）、Windows（不固定开机），这些设备都在 NAT 后面，没有公网 IP。需要通过云服务器的公网 IP/域名，从任意外网位置访问家庭设备上的服务（如 NAS 管理页面、Mac 上的开发服务等）。本质是**内网穿透**。

### 核心诉求

- 7×24 稳定运行，随时能访问
- 使用 HTTPS，需要认证和加密
- 有域名（`ruanpengpeng.cn`），通过子域名区分不同设备/服务
- 高性能、低使用门槛
- **不能影响云服务器上已有的服务**（Gitea、个人主页）
- 支持未来与 Cloudflare Tunnel 混合使用
- 有管理面板，能看到哪些设备在线、哪些隧道活跃
- 面向个人/家庭使用，后续可按需二次开发

---

## 二、环境现状

### 云服务器（生产）⚠️ 禁止随便操作

| 项目 | 详情 |
|------|------|
| IP / SSH | `43.163.90.149`，端口 `22022`，用户 `ubuntu`，密钥 `~/.ssh/codex_migration` |
| 反向代理 | Nginx |
| SSL 证书 | Let's Encrypt，已有 `ruanpengpeng.cn`、`git.ruanpengpeng.cn` |
| 已有服务 | Gitea (`:3000`) → `git.ruanpengpeng.cn`，个人主页 (`:3001`) → `ruanpengpeng.cn` |
| 端口占用 | 80、443（Nginx），222（Gitea SSH），22022（Server SSH） |

### 云服务器（测试）✅ 可自由操作

| 项目 | 详情 |
|------|------|
| IP / SSH | `119.91.235.65`，端口 `22022`，用户 `ubuntu`，密钥 `~/.ssh/codex_migration` |
| 环境 | 与生产几乎一致，Nginx + Docker（sudo 可用） |
| 已有服务 | Gitea (`:3000`)、个人主页 (`:3001`) |
| 磁盘 / 内存 | 40G 磁盘（28G 可用），3.3G 内存 |

### 家庭设备

| 设备 | 系统 | 在线情况 | 备注 |
|------|------|---------|------|
| 飞牛 NAS | Linux（飞牛 OS） | 长期开机 | 支持 Docker，Claude Code 当前运行于此 |
| Mac | macOS | 基本长期开机 | |
| Windows | Windows | 不固定 | |

---

## 三、技术方案

### 总体架构

```
外部用户
  │
  ├── HTTPS 443（经 Nginx）
  │    ├── vpn.ruanpengpeng.cn  ──► easy_vpn 管理面板
  │    └── nas.ruanpengpeng.cn  ──► HTTP 隧道 ──► NAS Web UI
  │
  └── TCP 直连（easy_vpn Server，不经 Nginx）
       ├── :2222  ──► SSH 隧道 ──► Mac:22
       └── :2223  ──► SSH 隧道 ──► NAS:22
            （2200-2299 端口段，由管理面板分配）
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
         NAS Client           Mac Client
         （Docker）           （Python 脚本）
              │                    │
     本地 Web/SSH 等服务      本地 Web/SSH 等服务
```

### 隧道协议：WebSocket 多路复用

**一条 WebSocket 连接承载所有流量，通过 channel_id 区分：**

```
WebSocket 帧：
{
    "type":       "control | http_request | http_response | tcp_open | tcp_data | tcp_close",
    "channel_id": "uuid",     # HTTP/TCP 每个连接唯一
    "data":       "base64",   # 原始字节（HTTP body 或 TCP 数据流）
    "payload":    {}          # 控制消息的结构化数据
}
```

- **HTTP 流量**：经 Nginx → Server :8080 → WebSocket channel → Client → 本地 Web 服务
- **TCP 流量**（SSH 等）：直连 Server :22xx → WebSocket channel → Client → 本地 TCP 服务
- **控制消息**（注册、规则下发、心跳）：同一条 WebSocket 连接，type=control

### 技术栈

| 层 | 技术选型 | 说明 |
|----|---------|------|
| 服务端核心 | Python + asyncio + FastAPI | 异步 I/O，处理并发 WebSocket 连接 |
| 隧道协议 | WebSocket（`websockets` 库） | 双向通信，复用 Nginx TLS |
| 管理面板 | Vue 3 + Vite | 前后端分离 |
| 管理 API | FastAPI REST | 供面板调用 |
| 客户端 | Python 脚本 | 跨平台，NAS/Mac/Windows 均可运行 |
| 服务端部署 | Docker + docker-compose | 与现有 Gitea 容器共存 |
| 客户端守护 | systemd（Linux/NAS）/ launchd（Mac）/ Task Scheduler（Windows） | 开机自启 + 崩溃重启 |
| 认证 | Token（JWT） | Client 和管理面板均需认证 |
| 规则存储 | JSON 文件持久化 | 无需引入数据库，Server 侧集中管理所有隧道规则 |
| TCP 隧道 | asyncio TCP Server | 监听 2200-2299 端口段，支持 SSH 等任意 TCP 服务 |

### 配置管理理念：Server 集中下发，Client 极简

Client 本地只保存三个参数（server地址 + token + client_id），**所有隧道规则在管理面板配置，连接时由 Server 自动下发**。

```
管理员在面板配置：nas → 本地 5000 端口
        ↓
Server 持久化规则（JSON）
        ↓
NAS Client 连上来 → Server 下发规则 → Client 自动生效
        ↓
面板实时修改规则 → 通过 WebSocket 推送给在线 Client → 立即生效，无需重启
```

优势：
- 新增设备只需填 3 个参数，零学习成本
- 规则变更不需要动 Client 配置，面板操作即时生效
- 所有设备的规则一处管理，清晰直观

### 与现有服务的共存方式

easy_vpn Server 只占用一个本地端口（如 `:8080`），Nginx 新增 server block 将新子域名代理过去，**完全不修改现有 gitea.conf 和 ruanpengpeng.cn.conf**。

```nginx
# 新增，不影响已有配置
server {
    listen 443 ssl http2;
    server_name vpn.ruanpengpeng.cn;
    # ... ssl 配置 ...
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Cloudflare Tunnel 混合策略（未来扩展）

| 场景 | 走哪条路 |
|------|---------|
| HTTP/HTTPS 网页服务（NAS UI 等） | 可选走 CF Tunnel（免费 CDN） |
| 对延迟敏感（远程桌面、SSH） | 走 easy_vpn 直连 |
| 非 HTTP 协议 | 走 easy_vpn 直连 |

---

## 四、项目结构

```
easy_vpn/
├── server/
│   ├── main.py              # FastAPI 入口，启动时初始化 TCP 监听器
│   ├── config.py            # 从环境变量读取配置
│   ├── auth.py              # JWT 认证
│   ├── protocol.py          # WebSocket 消息协议（类型定义、编解码）
│   ├── tunnel_manager.py    # WebSocket 多路复用，HTTP/TCP channel 路由
│   ├── tcp_listener.py      # TCP 端口监听，桥接到 Client 的 TCP channel
│   ├── rules.py             # 规则存储（HTTP/TCP 两类）+ 实时下发
│   ├── proxy.py             # HTTP 反代，按 Host 头路由到对应隧道
│   ├── api.py               # 管理面板 REST API（含规则 CRUD、可用端口查询）
│   ├── requirements.txt
│   └── Dockerfile
│
├── client/
│   ├── main.py              # 入口：连接 Server，接收规则下发，心跳重连
│   ├── forwarder.py         # 将隧道流量转发到本地端口
│   ├── config.example.yml   # 极简配置示例（仅 server地址+token+client_id）
│   └── requirements.txt
│
├── dashboard/               # Vue 3 管理面板
│   ├── src/
│   │   ├── api/index.js     # axios 封装（含规则管理接口）
│   │   ├── router/index.js  # 路由 + 登录守卫
│   │   ├── stores/auth.js   # Pinia 认证状态
│   │   └── views/
│   │       ├── Login.vue
│   │       └── Dashboard.vue  # 设备在线状态 + 隧道规则管理
│   ├── vite.config.js       # 开发代理 + 构建输出到 server/static
│   └── Dockerfile
│
├── server_deploy.sh            # 服务端一键部署脚本（Docker + Nginx + SSL）
├── docker-compose.yml          # 服务端一键部署
├── .env.example                # 环境变量模板
└── easy_vpn_project.md         # 本文件
```

---

## 五、开发路线图

### Phase 1 — 管理面板骨架

目标：`vpn.ruanpengpeng.cn` 可访问，能登录，能看到基本界面

- [ ] 服务端 FastAPI 基础框架搭起来
- [ ] JWT 登录认证接口
- [ ] WebSocket 接受 Client 注册、维护在线状态
- [ ] REST API：返回在线 Client 列表
- [ ] Vue 面板：登录页 + 主面板（显示在线设备）
- [ ] Docker 化，测试服务器跑通
- [ ] Nginx 配置 `vpn.ruanpengpeng.cn`（测试服务器）

### Phase 2 — HTTP 隧道核心

目标：从外网访问 NAS Web 管理页面

- [ ] protocol.py：WebSocket 消息协议编解码
- [ ] tunnel_manager.py：channel_id 多路复用，HTTP channel 管理
- [ ] Server proxy.py：收到外部 HTTP 请求，通过 WebSocket channel 转发
- [ ] Client forwarder.forward_http()：连接本地 Web 服务，回传响应
- [ ] 支持 `nas.ruanpengpeng.cn` → NAS 本地端口

### Phase 3 — TCP 隧道核心

目标：SSH 进家里的 Mac / NAS

- [ ] tunnel_manager.py：TCP channel 管理（tcp_open/tcp_data/tcp_close）
- [ ] tcp_listener.py：监听 2200-2299 端口，接受外部 TCP 连接，桥接到 Client
- [ ] Client forwarder.open_tcp()：连接本地 sshd，双向转发数据流
- [ ] docker-compose 开放 2200-2299 端口段
- [ ] 面板支持创建 TCP 规则，自动分配可用端口

### Phase 4 — 规则管理

目标：面板可视化管理所有规则，无需改 Client 配置

- [ ] rules.py：HTTP/TCP 两类规则 CRUD + JSON 持久化
- [ ] API：规则增删改查 + 可用端口查询接口
- [ ] 面板 Dashboard.vue：规则列表，支持增删改，TCP 规则显示端口号
- [ ] Client 连接时自动接收规则，面板修改后实时推送给在线 Client

### Phase 4 — 稳定性与体验

目标：7×24 稳定运行

- [ ] 心跳检测（Server 定时 ping Client，超时标记离线）
- [ ] Client 断线自动重连（指数退避）
- [ ] 面板显示流量统计、连接时长
- [ ] NAS 客户端 Docker 化
- [ ] Mac 客户端 launchd 守护配置

### Phase 5 — 高级功能（按需）

- [ ] Windows 客户端开机自启
- [ ] Cloudflare Tunnel 集成选项
- [ ] 访问日志、告警通知
- [ ] UDP 隧道支持（游戏服务器等场景，暂缓）

---

## 六、待确认事项

- [ ] `vpn.ruanpengpeng.cn` DNS 是否需要先指向测试服务器 `119.91.235.65`？还是先用 `/etc/hosts` 本地开发？
- [ ] 管理面板的登录方式：单一管理员 token，还是用户名+密码？
- [ ] NAS 客户端：直接跑 Python 脚本，还是打包成 Docker 容器？
- [ ] 子域名最终规划（`nas.ruanpengpeng.cn`、`mac.ruanpengpeng.cn` 等）
