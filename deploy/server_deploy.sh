#!/bin/bash
# =============================================================================
# easy_vpn 服务器端一键部署脚本
# 在服务器的项目根目录执行：sudo bash deploy/server_deploy.sh
# =============================================================================

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()     { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NGINX_CONF="/etc/nginx/sites-enabled/easy_vpn.conf"

cd "$PROJECT_DIR"
info "项目目录：$PROJECT_DIR"

# ---------- 1. 基础检查 ----------
command -v docker        &>/dev/null || die "未找到 docker，请先安装"
command -v nginx         &>/dev/null || die "未找到 nginx"
docker compose version   &>/dev/null || die "未找到 docker compose"

# ---------- 2. .env ----------
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    warning ".env 不存在，已从 .env.example 创建"
    warning "请编辑 $PROJECT_DIR/.env 后重新运行：nano $PROJECT_DIR/.env"
    exit 0
fi

# 检查 .env 里的关键字段不是占位值
for var in SECRET_KEY ADMIN_USERNAME ADMIN_PASSWORD CLIENT_TOKEN; do
    val=$(grep "^${var}=" "$PROJECT_DIR/.env" | cut -d'=' -f2-)
    if [ -z "$val" ] || echo "$val" | grep -qiE "change.me|YOUR_|example"; then
        die ".env 中的 ${var} 未填写或仍是占位值，请先编辑"
    fi
done
info ".env 检查通过"

# ---------- 3. Docker 构建 & 启动 ----------
info "===== 构建镜像（首次约 5-10 分钟）====="
docker compose -f "$PROJECT_DIR/docker-compose.yml" build

info "===== 启动容器 ====="
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d

# 等待健康
info "等待服务就绪..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/api/health &>/dev/null; then
        info "后端健康检查通过 ✓"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo ""
        echo -e "${RED}===== 容器日志（最后 30 行）=====${NC}"
        docker logs --tail 30 easy_vpn 2>&1 || true
        die "服务启动超时（15s），请查看日志：docker logs easy_vpn"
    fi
    sleep 0.5
done

# ---------- 4. Nginx ----------
info "===== 配置 Nginx ====="

# 从 .env 读取 PANEL_HOST，默认 _（匹配所有域名）
PANEL_HOST=$(grep '^PANEL_HOST=' "$PROJECT_DIR/.env" | cut -d'=' -f2-)
PANEL_HOST="${PANEL_HOST:-_}"

if [ -f "$NGINX_CONF" ]; then
    warning "Nginx 配置已存在（$NGINX_CONF），跳过写入"
else
    cat > "$NGINX_CONF" << EOF
# easy_vpn Nginx 配置（由 server_deploy.sh 生成）
server {
    listen 80;
    server_name ${PANEL_HOST};

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   Upgrade           \$http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_read_timeout 3600s;
    }
}
EOF
    info "已写入：$NGINX_CONF"

    # 语法检查 + 回滚
    if ! nginx -t &>/dev/null 2>&1; then
        rm -f "$NGINX_CONF"
        die "Nginx 配置语法错误，已回滚，现有服务不受影响"
    fi

    nginx -s reload
    info "Nginx 已热重载 ✓"
fi

# ---------- 5. 验证其他服务未受影响 ----------
info "===== 验证现有服务 ====="
for check in "Gitea:http://127.0.0.1:3000" "个人主页:http://127.0.0.1:3001"; do
    name="${check%%:*}"; url="${check#*:}"
    if curl -sf --max-time 5 "$url" &>/dev/null; then
        info "✓ $name 正常"
    else
        warning "✗ $name 未响应（$url），请手动确认"
    fi
done

# ---------- 完成 ----------
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  easy_vpn 部署完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  面板地址：  ${GREEN}http://${PANEL_HOST}${NC}  (或直接 http://服务器IP)"
echo -e "  查看日志：  docker logs -f easy_vpn"
echo -e "  停止服务：  docker compose -f $PROJECT_DIR/docker-compose.yml down"
echo -e "  重新部署：  sudo bash $PROJECT_DIR/deploy/server_deploy.sh"
echo ""
