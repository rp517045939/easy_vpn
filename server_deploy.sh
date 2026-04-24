#!/bin/bash
# =============================================================================
# easy_vpn 服务器端一键部署脚本
#
# 用法：
#   sudo bash server_deploy.sh                      # 正式部署（含 SSL 证书）
#   sudo bash server_deploy.sh --skip-ssl           # 测试环境（跳过 SSL）
# =============================================================================

set -euo pipefail

SKIP_SSL=false
for arg in "$@"; do
    case $arg in
        --skip-ssl) SKIP_SSL=true ;;
        *) echo "未知参数：$arg"; echo "用法：sudo bash server_deploy.sh [--skip-ssl]"; exit 1 ;;
    esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()     { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="/etc/nginx/sites-enabled/easy_vpn.conf"
# Nginx 备份目录放在 sites-enabled 之外，避免被 `include sites-enabled/*` 重复加载
NGINX_BACKUP_DIR="/etc/nginx/easy_vpn-backups"
DEPLOY_USER="${SUDO_USER:-$(id -un)}"

cd "$PROJECT_DIR"
info "项目目录：$PROJECT_DIR"

if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    GIT_CMD=(sudo -H -u "$SUDO_USER" git -C "$PROJECT_DIR")
else
    GIT_CMD=(git -C "$PROJECT_DIR")
fi

run_git() {
    "${GIT_CMD[@]}" "$@"
}

# ---------- 0. 拉取最新代码 ----------
info "===== 拉取最新代码 ====="
if [ "$(id -u)" -eq 0 ] && [ -z "${SUDO_USER:-}" ]; then
    warning "当前是直接 root 用户，跳过自动 git pull，避免改坏 .git 权限"
elif run_git remote get-url origin &>/dev/null; then
    if ! run_git diff --quiet || \
       ! run_git diff --cached --quiet || \
       [ -n "$(run_git ls-files --others --exclude-standard)" ]; then
        warning "检测到仓库存在本地修改或未跟踪文件，已跳过自动 git pull"
        run_git status --short || true
        warning "如需更新到远端最新版本，建议先备份本地改动，再执行："
        warning "  git -C \"$PROJECT_DIR\" stash push -u -m \"pre-deploy backup\""
        warning "  git -C \"$PROJECT_DIR\" pull --ff-only origin main"
    else
        if command -v timeout &>/dev/null; then
            GIT_PULL_CMD=(timeout 30s "${GIT_CMD[@]}" pull --ff-only origin main)
        else
            GIT_PULL_CMD=("${GIT_CMD[@]}" pull --ff-only origin main)
        fi

        if "${GIT_PULL_CMD[@]}" 2>&1; then
            info "代码已更新到最新版本 ✓"
        else
            warning "git pull 失败（网络、分支、远端或 .git 权限问题），继续使用当前版本"
            warning "若看到 .git/objects 权限错误，请执行：sudo chown -R $DEPLOY_USER:$DEPLOY_USER \"$PROJECT_DIR/.git\""
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
if ! nginx -t 2>/tmp/easy_vpn_nginx_pretest.log; then
    echo -e "${RED}===== 现有 Nginx 配置校验失败 =====${NC}"
    cat /tmp/easy_vpn_nginx_pretest.log
    die "现有 Nginx 配置已存在语法错误，请先手动修复后再部署"
fi

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
[ -n "$PANEL_HOST" ] || die ".env 中的 PANEL_HOST 不能为空"
# ADMIN_EMAIL 用于 certbot 注册（可选，为空时使用 --register-unsafely-without-email）
ADMIN_EMAIL=$(grep '^ADMIN_EMAIL=' "$PROJECT_DIR/.env" | cut -d'=' -f2- || true)
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

# 管理面板静态页面探测：/api/health 通不代表前端打进镜像了，这里额外确认面板入口可访问
PANEL_STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: ${PANEL_HOST}" http://127.0.0.1:8080/ || echo "000")
if [ "$PANEL_STATUS" = "200" ] || [ "$PANEL_STATUS" = "304" ]; then
    info "管理面板入口 (/) 响应正常：HTTP ${PANEL_STATUS} ✓"
else
    warning "管理面板入口 (/) 返回 HTTP ${PANEL_STATUS}，前端可能未构建进镜像"
    warning "请执行：docker logs easy_vpn；或本地 cd dashboard && npm ci && npm run build 后重跑"
fi

# ---------- 4. Nginx 配置 ----------
info "===== 配置 Nginx ====="
mkdir -p "$NGINX_BACKUP_DIR"
# 一次性清理历史遗留：如果上一版脚本在 sites-enabled 下留过 .bak.* 文件，把它们搬走
# 否则 Debian/Ubuntu 的 `include sites-enabled/*` 会把备份当成活配置加载
for stale in "${NGINX_CONF}.bak."*; do
    [ -f "$stale" ] || continue
    mv "$stale" "$NGINX_BACKUP_DIR/$(basename "$stale")"
    warning "发现历史遗留备份文件，已搬离 sites-enabled：$stale"
done

if [ -f "$NGINX_CONF" ]; then
    BACKUP_CONF="$NGINX_BACKUP_DIR/easy_vpn.conf.bak.$(date +%Y%m%d%H%M%S)"
    cp "$NGINX_CONF" "$BACKUP_CONF"
    warning "Nginx 配置已存在，已备份到：$BACKUP_CONF"
fi

write_nginx_config() {
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
        # 正式环境：先写 HTTP 反代，certbot --nginx 会自动补充 SSL 配置。
        cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name ${PANEL_HOST};
    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_set_header   Upgrade           \$http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_read_timeout 3600s;
    }
}
EOF
        info "已写入 Nginx 配置 ✓"
    fi
}

write_nginx_config

if ! nginx -t 2>/tmp/easy_vpn_nginx_test.log; then
    echo -e "${RED}===== Nginx 校验失败，详细错误如下 =====${NC}"
    cat /tmp/easy_vpn_nginx_test.log
    if [ -n "${BACKUP_CONF:-}" ] && [ -f "$BACKUP_CONF" ]; then
        cp "$BACKUP_CONF" "$NGINX_CONF"
        die "Nginx 配置语法错误，已恢复备份：$BACKUP_CONF"
    else
        rm -f "$NGINX_CONF"
        die "Nginx 配置语法错误，已回滚（无备份可恢复）"
    fi
fi
nginx -s reload
info "Nginx 已热重载 ✓"

# ---------- 5. SSL 证书（正式环境）----------
if [ "$SKIP_SSL" = false ]; then
    info "===== SSL 证书 ====="
    HOOK="/etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh"
    mkdir -p "$(dirname "$HOOK")"
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
        # 构造邮箱参数：优先读 .env 的 ADMIN_EMAIL，为空则显式匿名注册，避免伪造邮箱
        if [ -n "${ADMIN_EMAIL:-}" ]; then
            CERTBOT_EMAIL_ARGS=(--email "$ADMIN_EMAIL")
            info "使用 .env 中的 ADMIN_EMAIL 注册证书：$ADMIN_EMAIL"
        else
            CERTBOT_EMAIL_ARGS=(--register-unsafely-without-email)
            warning ".env 未填 ADMIN_EMAIL，将匿名注册证书（续期通知不会有邮件提醒）"
        fi

        if certbot --nginx -d "$PANEL_HOST" --non-interactive --agree-tos \
            "${CERTBOT_EMAIL_ARGS[@]}"; then
            info "SSL 证书申请成功 ✓"
        else
            echo -e "${RED}===== SSL 证书申请失败，常见原因排查 =====${NC}"
            echo "  1) DNS 未解析：dig +short $PANEL_HOST  应返回本机公网 IP"
            echo "  2) 80 端口不通：curl -I http://$PANEL_HOST  应能被 certbot 回源"
            echo "  3) 防火墙/安全组未放行 TCP 80"
            echo "  4) Let's Encrypt 限流（每域名每周 5 次），换子域名或等一周"
            echo "  修复后重跑：sudo certbot --nginx -d $PANEL_HOST"
            die "SSL 证书申请失败，部署已停止；当前 Nginx 仅有 HTTP:80，HTTPS 尚不可用"
        fi
    else
        die "未安装 certbot，无法申请 SSL；请执行：sudo apt install -y certbot python3-certbot-nginx 后重跑"
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
echo -e "  重新部署：  sudo bash $PROJECT_DIR/server_deploy.sh"
echo ""
