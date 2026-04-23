#!/bin/bash
# =============================================================================
# easy_vpn 服务器端一键部署脚本
#
# 用法：
#   sudo bash deploy/server_deploy.sh               # 正式部署（含 SSL 证书）
#   sudo bash deploy/server_deploy.sh --skip-ssl    # 测试环境（跳过 SSL）
# =============================================================================

set -euo pipefail

SKIP_SSL=false
for arg in "$@"; do
    case $arg in
        --skip-ssl) SKIP_SSL=true ;;
        *) echo "未知参数：$arg"; echo "用法：sudo bash deploy/server_deploy.sh [--skip-ssl]"; exit 1 ;;
    esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()     { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NGINX_CONF="/etc/nginx/sites-enabled/easy_vpn.conf"

cd "$PROJECT_DIR"
info "项目目录：$PROJECT_DIR"

# ---------- 0. 拉取最新代码 ----------
info "===== 拉取最新代码 ====="
if git -C "$PROJECT_DIR" remote get-url origin &>/dev/null; then
    if ! git -C "$PROJECT_DIR" diff --quiet || \
       ! git -C "$PROJECT_DIR" diff --cached --quiet || \
       [ -n "$(git -C "$PROJECT_DIR" ls-files --others --exclude-standard)" ]; then
        warning "检测到仓库存在本地修改或未跟踪文件，已跳过自动 git pull"
        git -C "$PROJECT_DIR" status --short || true
        warning "如需更新到远端最新版本，建议先备份本地改动，再执行："
        warning "  git -C \"$PROJECT_DIR\" stash push -u -m \"pre-deploy backup\""
        warning "  git -C \"$PROJECT_DIR\" pull --ff-only origin main"
    else
        if command -v timeout &>/dev/null; then
            GIT_PULL_CMD=(timeout 30s git -C "$PROJECT_DIR" pull --ff-only origin main)
        else
            GIT_PULL_CMD=(git -C "$PROJECT_DIR" pull --ff-only origin main)
        fi

        if "${GIT_PULL_CMD[@]}" 2>&1; then
            info "代码已更新到最新版本 ✓"
        else
            warning "git pull 失败（网络问题、分支无法快进或远端不可达），继续使用当前版本"
        fi
    fi
else
    warning "未找到 git remote，跳过更新步骤"
fi

# ---------- 1. 基础检查 ----------
info "===== 环境检查 ====="
command -v docker      &>/dev/null || die "未找到 docker，请先安装"
command -v nginx       &>/dev/null || die "未找到 nginx"
docker compose version &>/dev/null || die "未找到 docker compose"
nginx -t               &>/dev/null 2>&1 || die "现有 Nginx 配置有误，请先修复：sudo nginx -t"

if ss -tlnp | grep -q ':8080 ' && ! docker ps --format '{{.Names}}' | grep -q '^easy_vpn$'; then
    die "端口 8080 已被其他进程占用"
fi
info "环境检查通过 ✓"

# ---------- 2. .env 检查 ----------
info "===== 配置检查 ====="
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    warning ".env 不存在，已从 .env.example 创建"
    warning "请编辑后重新运行：nano $PROJECT_DIR/.env"
    exit 0
fi
for var in SECRET_KEY ADMIN_USERNAME ADMIN_PASSWORD CLIENT_TOKEN; do
    val=$(grep "^${var}=" "$PROJECT_DIR/.env" | cut -d'=' -f2-)
    if [ -z "$val" ] || echo "$val" | grep -qiE "change.me|YOUR_|example"; then
        die ".env 中的 ${var} 未填写或仍是占位值"
    fi
done
PANEL_HOST=$(grep '^PANEL_HOST=' "$PROJECT_DIR/.env" | cut -d'=' -f2-)
info ".env 检查通过 ✓"

# ---------- 3. 构建并启动容器 ----------
info "===== 构建镜像（首次约 5-10 分钟）====="
docker compose -f "$PROJECT_DIR/docker-compose.yml" build

info "===== 启动容器 ====="
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d

info "等待服务就绪..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/api/health &>/dev/null; then
        info "后端健康检查通过 ✓"; break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}===== 容器日志（最后 30 行）=====${NC}"
        docker logs --tail 30 easy_vpn 2>&1 || true
        die "服务启动超时，请查看日志：docker logs easy_vpn"
    fi
    sleep 0.5
done

# ---------- 4. Nginx 配置 ----------
info "===== 配置 Nginx ====="
if [ -f "$NGINX_CONF" ]; then
    warning "Nginx 配置已存在，跳过写入：$NGINX_CONF"
else
    if [ "$SKIP_SSL" = true ]; then
        # 测试环境：HTTP only
        cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name ${PANEL_HOST:-_};
    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host            \$host;
        proxy_set_header   X-Real-IP       \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   Upgrade         \$http_upgrade;
        proxy_set_header   Connection      "upgrade";
        proxy_read_timeout 3600s;
    }
}
EOF
        info "已写入 HTTP-only Nginx 配置 ✓"
    else
        # 正式环境：从模板复制（含 SSL 占位）
        cp "$PROJECT_DIR/deploy/nginx/easy_vpn.conf" "$NGINX_CONF"
        info "已写入 Nginx 配置 ✓"
    fi

    if ! nginx -t &>/dev/null 2>&1; then
        rm -f "$NGINX_CONF"
        die "Nginx 配置语法错误，已回滚"
    fi
    nginx -s reload
    info "Nginx 已热重载 ✓"
fi

# ---------- 5. SSL 证书（正式环境）----------
if [ "$SKIP_SSL" = false ]; then
    info "===== SSL 证书 ====="
    HOOK="/etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh"
    if [ ! -f "$HOOK" ]; then
        bash -c "cat > $HOOK" << 'EOF'
#!/bin/bash
nginx -s reload
EOF
        chmod +x "$HOOK"
        info "已创建续期 hook：$HOOK"
    fi

    if [ -f "/etc/letsencrypt/live/${PANEL_HOST}/fullchain.pem" ]; then
        info "SSL 证书已存在，跳过申请"
    elif command -v certbot &>/dev/null; then
        certbot --nginx -d "$PANEL_HOST" --non-interactive --agree-tos \
            --email "admin@${PANEL_HOST#*.}" || warning "SSL 申请失败，请手动执行：sudo certbot --nginx -d $PANEL_HOST"
    else
        warning "未安装 certbot，请手动申请：sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d $PANEL_HOST"
    fi
fi

# ---------- 6. 验证现有服务 ----------
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
if [ "$SKIP_SSL" = true ]; then
    echo -e "  面板地址：  ${GREEN}http://${PANEL_HOST:-服务器IP}${NC}"
else
    echo -e "  面板地址：  ${GREEN}https://${PANEL_HOST}${NC}"
fi
echo -e "  查看日志：  docker logs -f easy_vpn"
echo -e "  停止服务：  docker compose -f $PROJECT_DIR/docker-compose.yml down"
echo -e "  重新部署：  sudo bash $PROJECT_DIR/deploy/server_deploy.sh"
echo ""
