# easy_vpn

基于 WebSocket 的内网穿透工具，支持 HTTP 子域名代理和 TCP 端口转发。适合个人/家庭设备（NAS、Mac、Windows）通过云服务器的公网域名对外暴露内网服务。

## 架构

```
外部用户
  │
  ├── HTTPS 443（Nginx 反向代理）
  │    ├── vpn.example.com       → easy_vpn 管理面板
  │    └── nas.example.com       → HTTP 隧道 → NAS 内网服务
  │
  └── TCP 2200-2299（直连）
       └── server:2222           → TCP 隧道 → NAS SSH:22

云服务器（easy_vpn Server）
  └── WebSocket 长连接
       ├── NAS Client
       ├── Mac Client
       └── Windows Client
```

- **Server**：运行在云服务器，接受 Client 注册，管理隧道规则，代理流量
- **Client**：运行在内网设备，连接 Server，按规则将流量转发到本地服务
- **管理面板**：Web UI，查看在线设备，增删改隧道规则

---

## 服务端部署

### 前置条件

- Docker + Docker Compose
- Nginx（宿主机，作为反向代理）
- 域名，已解析到服务器（如 `vpn.example.com` 及各穿透子域名）

### 1. 克隆项目

```bash
git clone <仓库地址>
cd easy_vpn
```

### 2. 配置环境变量

```bash
cp .env.example .env
nano .env
```

`.env` 关键字段：

| 字段 | 说明 |
|------|------|
| `SECRET_KEY` | JWT 签名密钥，建议 32 位以上随机字符串 |
| `ADMIN_USERNAME` | 管理面板登录用户名 |
| `ADMIN_PASSWORD` | 管理面板登录密码 |
| `CLIENT_TOKEN` | Client 注册时使用的共享 token，建议 32 位以上 |
| `PANEL_HOST` | 管理面板域名，如 `vpn.example.com` |
| `PORT` | 服务监听端口，默认 `8080` |

### 3. 构建前端（可选）

管理面板需先构建 Vue 产物，否则访问面板域名会返回 503：

```bash
cd dashboard
npm install
npm run build        # 产物输出到 server/static/
```

### 4. 一键部署

```bash
# 正式环境（含 SSL 证书申请）
sudo bash deploy/server_deploy.sh

# 测试环境（跳过 SSL）
sudo bash deploy/server_deploy.sh --skip-ssl
```

脚本会自动完成：环境检查 → 构建镜像 → 启动容器 → 写入 Nginx 配置 → 申请 SSL 证书 → 验证现有服务未受影响。

> 脚本只新增 Nginx 配置，不修改服务器上任何已有配置，Gitea 等已有服务不受影响。

### 5. 手动管理容器

```bash
# 启动
docker compose up -d

# 查看日志
docker logs -f easy_vpn

# 停止
docker compose down

# 更新（拉代码后重新部署）
git pull && sudo bash deploy/server_deploy.sh
```

如果服务器上的项目目录做过手工修改，`git pull` 可能会被阻止。此时建议先备份本地改动，再更新：

```bash
git stash push -u -m "pre-deploy backup"
git pull --ff-only origin main
sudo bash deploy/server_deploy.sh
```

### Nginx 配置说明

部署脚本自动写入 `/etc/nginx/sites-enabled/easy_vpn.conf`。如需手动配置或新增穿透子域名，参考 `deploy/nginx/easy_vpn.conf`：

```nginx
# 新增穿透子域名（每台设备一段，复制以下模板）
server {
    listen 443 ssl http2;
    server_name nas.example.com;
    ssl_certificate /etc/letsencrypt/live/nas.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nas.example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;   # Server 通过 Host 头识别目标 Client
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

> 新增子域名后需申请对应证书：`sudo certbot --nginx -d nas.example.com`

---

## 客户端安装

### 前置条件

- Python 3.9+

### 1. 安装依赖

```bash
cd client
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config.example.yml config.yml
nano config.yml
```

`config.yml` 字段说明：

```yaml
server:
  url: wss://vpn.example.com/tunnel/ws   # Server 地址，必须用 wss:// (HTTPS) 或 ws:// (HTTP)
  token: YOUR_CLIENT_TOKEN               # 与 Server .env 中 CLIENT_TOKEN 一致

client:
  id: nas                                # 唯一标识，建议用设备名，如 nas / mac / win
```

### 3. 启动

```bash
python main.py --config config.yml
```

Client 启动后自动连接 Server，连接成功后会从管理面板拉取规则，无需手动配置隧道规则。断线后自动重连，重连间隔指数退避（最长 60 秒）。

**以系统服务方式运行（Linux/NAS，推荐）：**

```ini
# /etc/systemd/system/easy_vpn_client.service
[Unit]
Description=easy_vpn Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/easy_vpn/client
ExecStart=/usr/bin/python3 main.py --config config.yml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now easy_vpn_client
sudo journalctl -u easy_vpn_client -f
```

---

## 管理面板使用

访问 `https://vpn.example.com`，用 `.env` 中的账号密码登录。

### 查看在线设备

首页展示当前已连接的 Client 列表及在线状态。

### 添加隧道规则

点击「添加规则」，填写：

| 字段 | 说明 |
|------|------|
| 类型 | `http`（子域名代理）或 `tcp`（端口转发） |
| Client | 目标设备，从在线列表中选择 |
| 本地地址 | Client 侧的内网 IP，通常填 `127.0.0.1` |
| 本地端口 | Client 侧要暴露的服务端口 |
| 子域名（HTTP） | 如 `nas`，对应 `nas.example.com` |
| 服务端端口（TCP）| 如 `2222`，外部通过 `server:2222` 访问 |

规则保存后立即下发给对应 Client，无需重启任何服务。

### 典型配置示例

**HTTP 穿透 NAS 管理页面：**

| 字段 | 值 |
|------|-----|
| 类型 | http |
| Client | nas |
| 本地地址 | 127.0.0.1 |
| 本地端口 | 8080 |
| 子域名 | nas |

访问 `https://nas.example.com` 即可。

**TCP 穿透 NAS SSH：**

| 字段 | 值 |
|------|-----|
| 类型 | tcp |
| Client | nas |
| 本地地址 | 127.0.0.1 |
| 本地端口 | 22 |
| 服务端端口 | 2222 |

```bash
ssh -p 2222 user@vpn.example.com
```

---

## 本地开发

```bash
# 确保 .env 已配置
cp .env.example .env && nano .env

# 一键启动（后端 + 前端热重载）
bash dev.sh
```

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 管理面板（Vite 开发服务器） |
| http://localhost:8080/docs | 后端 API 文档（Swagger） |

> 默认账号：`ADMIN_USERNAME` / `ADMIN_PASSWORD`（见 .env）

Client 本地测试时，将 `config.yml` 中的 `url` 改为 `ws://localhost:8080/tunnel/ws`。

---

## 端口规划

| 端口 | 用途 |
|------|------|
| 8080 | Server HTTP（仅宿主机 Nginx 访问，不对外开放） |
| 2200–2299 | TCP 隧道端口段，对外开放 |
