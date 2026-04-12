#!/bin/bash
# =============================================================================
# easy_vpn 一键部署脚本
#
# 用法：
#   bash install.sh                  # 正式部署（含 SSL 证书申请）
#   bash install.sh --test-skip-ssl  # 测试环境部署（跳过 SSL 证书步骤）
#
# 安全说明：
#   - 只新增 Nginx 配置文件，绝不修改服务器上已有的任何 Nginx 配置
#   - 使用独立的 Docker 网络，不影响 Gitea 等已有容器
#   - 每步操作前均有检查，Nginx 配置有误时自动回滚
# =============================================================================

set -e  # 任何命令失败立即退出

# ---------- 参数解析 ----------
SKIP_SSL=false
for arg in "$@"; do
    case $arg in
        --test-skip-ssl)
            SKIP_SSL=true
            ;;
        *)
            echo "未知参数：$arg"
            echo "用法：bash install.sh [--test-skip-ssl]"
            exit 1
            ;;
    esac
done

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- 脚本所在目录（项目根目录）----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
NGINX_CONF_FILE="/etc/nginx/sites-enabled/easy_vpn.conf"

if [ "$SKIP_SSL" = true ]; then
    warning "已启用 --test-skip-ssl，第五步 SSL 证书将跳过（仅限测试环境）"
fi

# =============================================================================
# 第一步：环境检查
# =============================================================================
info "===== 第一步：环境检查 ====="

# 检查 Docker
if ! command -v docker &>/dev/null; then
    error "未找到 Docker，请先安装 Docker：https://docs.docker.com/engine/install/"
fi
info "Docker 版本：$(docker --version)"

# 检查 docker compose（优先 compose v2，兼容 v1）
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    error "未找到 docker compose，请先安装"
fi
info "Compose 命令：$COMPOSE_CMD"

# 检查 Nginx
if ! command -v nginx &>/dev/null; then
    error "未找到 Nginx，本脚本依赖宿主机 Nginx 作为反向代理"
fi
info "Nginx 版本：$(nginx -v 2>&1)"

# 检查 certbot（仅警告，不强制）
if ! command -v certbot &>/dev/null; then
    warning "未找到 certbot，SSL 证书步骤将跳过，需要手动申请"
    HAS_CERTBOT=false
else
    HAS_CERTBOT=true
fi

# 检查 8080 端口是否已被占用
if ss -tlnp | grep -q ':8080 '; then
    error "端口 8080 已被占用，请检查或修改 .env 中的 PORT 配置"
fi
info "端口 8080 可用"

# 检查现有 Nginx 服务正常
if ! nginx -t &>/dev/null 2>&1; then
    error "当前 Nginx 配置已存在错误，请先修复后再部署：sudo nginx -t"
fi
info "现有 Nginx 配置检查通过"

# =============================================================================
# 第二步：配置初始化
# =============================================================================
info "===== 第二步：配置初始化 ====="

cd "$PROJECT_DIR"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    warning "已从 .env.example 创建 .env 文件"
    warning "请编辑 $PROJECT_DIR/.env，填入以下必填项后重新运行本脚本："
    echo ""
    echo "  SECRET_KEY       - JWT 签名密钥（建议 32 位以上随机字符串）"
    echo "  ADMIN_USERNAME   - 管理面板登录用户名"
    echo "  ADMIN_PASSWORD   - 管理面板登录密码"
    echo "  CLIENT_TOKEN     - Client 注册 token（建议 32 位以上随机字符串）"
    echo ""
    echo "  编辑命令：nano $PROJECT_DIR/.env"
    echo ""
    exit 0
fi

# 检查 .env 中的关键字段是否已填写（不能是默认占位值）
check_env_var() {
    local var_name=$1
    local var_value
    var_value=$(grep "^${var_name}=" .env | cut -d'=' -f2-)
    if [ -z "$var_value" ] || [[ "$var_value" == *"change-me"* ]] || [[ "$var_value" == *"YOUR_"* ]]; then
        error ".env 中的 ${var_name} 未填写或仍为默认值，请先编辑 .env"
    fi
}

check_env_var "SECRET_KEY"
check_env_var "ADMIN_USERNAME"
check_env_var "ADMIN_PASSWORD"
check_env_var "CLIENT_TOKEN"
info ".env 配置检查通过"

# =============================================================================
# 第三步：构建并启动容器
# =============================================================================
info "===== 第三步：构建并启动容器 ====="

# 确保在项目根目录执行，只操作 easy_vpn 自己的 compose 文件
$COMPOSE_CMD -f "$PROJECT_DIR/docker-compose.yml" build
$COMPOSE_CMD -f "$PROJECT_DIR/docker-compose.yml" up -d

# 等待容器健康
info "等待容器启动..."
sleep 3

if ! docker inspect --format='{{.State.Running}}' easy_vpn 2>/dev/null | grep -q true; then
    error "容器启动失败，查看日志：docker logs easy_vpn"
fi
info "容器启动成功"

# 验证服务响应
if ! curl -sf http://127.0.0.1:8080/api/health &>/dev/null; then
    warning "服务健康检查未响应（/api/health），可能还在初始化，继续部署..."
fi

# =============================================================================
# 第四步：Nginx 配置（只新增，绝不修改现有配置）
# =============================================================================
info "===== 第四步：配置 Nginx ====="

if [ -f "$NGINX_CONF_FILE" ]; then
    warning "Nginx 配置文件已存在：$NGINX_CONF_FILE，跳过写入"
else
    if [ "$SKIP_SSL" = true ]; then
        # 测试环境：写入 HTTP-only 配置（无需 SSL 证书）
        PANEL_HOST_VAL=$(grep '^PANEL_HOST=' "$PROJECT_DIR/.env" | cut -d'=' -f2-)
        sudo bash -c "cat > $NGINX_CONF_FILE" << EOF
# easy_vpn 测试环境 Nginx 配置（HTTP only，--test-skip-ssl）
server {
    listen 80;
    server_name ${PANEL_HOST_VAL:-_};

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
EOF
        info "已写入测试 Nginx 配置（HTTP only）：$NGINX_CONF_FILE"
    else
        # 正式环境：使用 SSL 配置模板
        sudo cp "$SCRIPT_DIR/nginx/easy_vpn.conf" "$NGINX_CONF_FILE"
        info "已写入 Nginx 配置：$NGINX_CONF_FILE"
    fi

    # 测试 Nginx 配置语法
    if ! sudo nginx -t &>/dev/null 2>&1; then
        # 回滚：删除刚写入的文件，确保现有服务不受影响
        sudo rm -f "$NGINX_CONF_FILE"
        error "Nginx 配置语法错误，已自动回滚（现有服务未受影响）。\n请检查配置后重新运行"
    fi
    info "Nginx 配置语法检查通过"

    # 热重载（不重启，zero downtime）
    sudo nginx -s reload
    info "Nginx 已热重载，现有服务不受影响"
fi

# =============================================================================
# 第五步：SSL 证书 + 自动续期
# =============================================================================
info "===== 第五步：SSL 证书 ====="

# 从 Nginx 配置里提取域名
DOMAIN=$(grep 'server_name' "$NGINX_CONF_FILE" | head -1 | awk '{print $2}' | tr -d ';')

if [ "$SKIP_SSL" = true ]; then
    warning "【--test-skip-ssl】跳过 SSL 证书步骤，测试环境通过 HTTP 访问即可"
    warning "生产环境部署时去掉此参数以启用 SSL"
    # 跳过整个第五步，直接进入第六步
else

# --- 5.1 设置 renewal deploy hook（所有证书续期成功后执行，graceful reload）---
# 说明：certbot renew 每天自动跑两次，续期成功后需要 reload nginx 让新证书生效。
# deploy hook 对服务器上所有证书生效，是统一入口，避免每个证书单独配置。
# 使用 nginx -s reload（graceful），不中断现有连接，不影响 Gitea 等其他服务。
HOOK_FILE="/etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh"
if [ ! -f "$HOOK_FILE" ]; then
    sudo bash -c "cat > $HOOK_FILE" << 'EOF'
#!/bin/bash
# certbot 证书续期成功后自动执行，graceful reload nginx
# 所有域名（包括 Gitea、个人主页、easy_vpn）共用此 hook
nginx -s reload
EOF
    sudo chmod +x "$HOOK_FILE"
    info "已创建续期 hook：$HOOK_FILE"
else
    info "续期 hook 已存在，跳过：$HOOK_FILE"
fi

# --- 5.2 申请证书 ---
if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    info "SSL 证书已存在，跳过申请：/etc/letsencrypt/live/${DOMAIN}/"
elif [ "$HAS_CERTBOT" = true ]; then
    info "申请 SSL 证书：$DOMAIN"
    ADMIN_EMAIL="$(grep '^ADMIN_USERNAME' .env | cut -d'=' -f2-)@$(echo "$DOMAIN" | cut -d'.' -f2-)"
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$ADMIN_EMAIL" \
        || warning "SSL 证书申请失败，请手动执行：sudo certbot --nginx -d $DOMAIN"
else
    warning "未安装 certbot，请手动申请 SSL 证书："
    echo "  sudo apt install certbot python3-certbot-nginx"
    echo "  sudo certbot --nginx -d $DOMAIN"
    echo ""
    echo "  申请成功后，请确认续期 hook 已创建："
    echo "  $HOOK_FILE"
fi

# --- 5.3 验证自动续期配置正常（dry-run，不真正申请）---
if [ "$HAS_CERTBOT" = true ] && [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    info "验证自动续期配置（dry-run）..."
    if sudo certbot renew --dry-run --cert-name "$DOMAIN" &>/dev/null 2>&1; then
        info "自动续期验证通过（certbot timer 每天自动运行两次）"
    else
        warning "自动续期 dry-run 失败，请手动检查：sudo certbot renew --dry-run"
    fi
fi

fi  # end of SKIP_SSL check

# =============================================================================
# 第六步：验证现有服务未受影响
# =============================================================================
info "===== 第六步：验证现有服务 ====="

check_service() {
    local name=$1
    local url=$2
    if curl -sf --max-time 5 "$url" &>/dev/null; then
        info "✓ $name 正常"
    else
        warning "✗ $name 可能异常，请手动检查：$url"
    fi
}

check_service "Gitea"    "http://127.0.0.1:3000"
check_service "个人主页"  "http://127.0.0.1:3001"

# =============================================================================
# 完成
# =============================================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  easy_vpn 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
if [ "$SKIP_SSL" = true ]; then
    echo "  管理面板：http://${DOMAIN}（测试环境，无 SSL）"
else
    echo "  管理面板：https://${DOMAIN}"
fi
echo "  查看日志：docker logs -f easy_vpn"
echo "  停止服务：docker compose -f $PROJECT_DIR/docker-compose.yml down"
echo "  更新服务：git pull && bash $0"
echo ""
