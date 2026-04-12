#!/bin/bash
# easy_vpn 本地开发一键启动脚本（Mac）
# 用法：bash dev.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv"
LOG_SERVER="$PROJECT_DIR/.dev_server.log"
LOG_FRONTEND="$PROJECT_DIR/.dev_frontend.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- 清理函数（Ctrl+C 时关闭所有子进程）----------
cleanup() {
    echo ""
    info "正在关闭服务..."
    kill "$SERVER_PID" "$FRONTEND_PID" 2>/dev/null
    wait "$SERVER_PID" "$FRONTEND_PID" 2>/dev/null
    info "已关闭，再见。"
    exit 0
}
trap cleanup INT TERM

# ---------- 检查 .env ----------
if [ ! -f "$PROJECT_DIR/.env" ]; then
    error ".env 文件不存在，请先复制 .env.example 并填写：cp .env.example .env"
fi

# ---------- 检查 / 创建虚拟环境 ----------
if [ ! -d "$VENV" ]; then
    info "创建 Python 虚拟环境..."
    python3 -m venv "$VENV"
fi

info "检查 Python 依赖..."
"$VENV/bin/pip" install -q -r "$PROJECT_DIR/server/requirements.txt"

# ---------- 检查 node_modules ----------
if [ ! -d "$PROJECT_DIR/dashboard/node_modules" ]; then
    info "安装前端依赖..."
    cd "$PROJECT_DIR/dashboard" && npm install --silent
fi

# ---------- 启动后端 ----------
info "启动后端 → http://localhost:8080"
cd "$PROJECT_DIR/server"
"$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port 8080 --reload \
    --env-file "$PROJECT_DIR/.env" > "$LOG_SERVER" 2>&1 &
SERVER_PID=$!

# 等待后端就绪
for i in $(seq 1 15); do
    sleep 0.5
    if curl -sf http://localhost:8080/api/health &>/dev/null; then
        info "后端已就绪 ✓"
        break
    fi
    if [ "$i" -eq 15 ]; then
        error "后端启动失败，查看日志：cat $LOG_SERVER"
    fi
done

# ---------- 启动前端 ----------
info "启动前端 → http://localhost:5173"
cd "$PROJECT_DIR/dashboard"
npm run dev > "$LOG_FRONTEND" 2>&1 &
FRONTEND_PID=$!

sleep 2

# ---------- 完成 ----------
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  easy_vpn 本地开发环境已启动${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  管理面板：  ${GREEN}http://localhost:5173${NC}"
echo -e "  后端 API：  ${GREEN}http://localhost:8080/docs${NC}"
echo -e "  默认账号：  admin / admin123"
echo ""
echo -e "  后端日志：  tail -f $LOG_SERVER"
echo -e "  前端日志：  tail -f $LOG_FRONTEND"
echo ""
echo -e "  ${YELLOW}按 Ctrl+C 关闭所有服务${NC}"
echo ""

# 保持脚本运行，等待 Ctrl+C
wait
