#!/bin/bash
# easy_vpn 本地开发一键启动脚本（Mac）
# 用法：bash dev.sh

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv"
LOG_SERVER="$PROJECT_DIR/.dev_server.log"
LOG_FRONTEND="$PROJECT_DIR/.dev_frontend.log"

SERVER_PID=""
FRONTEND_PID=""

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# ---------- 清理函数：杀掉已启动的子进程 ----------
kill_services() {
    [ -n "$SERVER_PID" ]   && kill "$SERVER_PID"   2>/dev/null && wait "$SERVER_PID"   2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && wait "$FRONTEND_PID" 2>/dev/null
}

abort() {
    echo -e "\n${RED}[ERROR]${NC} $1"
    echo -e "${RED}[ERROR]${NC} 正在回收已启动的服务..."
    kill_services
    echo -e "${RED}[ERROR]${NC} 已终止所有服务。"
    exit 1
}

cleanup() {
    echo ""
    info "正在关闭服务..."
    kill_services
    info "已关闭，再见。"
    exit 0
}
trap cleanup INT TERM

# ---------- 检查 .env ----------
if [ ! -f "$PROJECT_DIR/.env" ]; then
    abort ".env 文件不存在，请先复制 .env.example 并填写：cp .env.example .env"
fi

# ---------- 检查 / 创建虚拟环境 ----------
if [ ! -d "$VENV" ]; then
    info "创建 Python 虚拟环境..."
    python3 -m venv "$VENV" || abort "Python 虚拟环境创建失败"
fi

info "检查 Python 依赖..."
"$VENV/bin/pip" install -q -r "$PROJECT_DIR/server/requirements.txt" \
    || abort "Python 依赖安装失败"

# ---------- 检查 node_modules ----------
if [ ! -d "$PROJECT_DIR/dashboard/node_modules" ]; then
    info "安装前端依赖..."
    (cd "$PROJECT_DIR/dashboard" && npm install --silent) \
        || abort "前端依赖安装失败"
fi

# ---------- 启动后端 ----------
info "启动后端 → http://localhost:8080"
cd "$PROJECT_DIR/server"
"$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port 8080 --reload \
    --env-file "$PROJECT_DIR/.env" > "$LOG_SERVER" 2>&1 &
SERVER_PID=$!

for i in $(seq 1 20); do
    sleep 0.5
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo ""
        echo -e "${RED}===== 后端日志 =====${NC}"
        cat "$LOG_SERVER"
        echo -e "${RED}====================${NC}"
        abort "后端进程已崩溃退出"
    fi
    if curl -sf http://localhost:8080/api/health &>/dev/null; then
        info "后端已就绪 ✓"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo ""
        echo -e "${RED}===== 后端日志（最后 30 行）=====${NC}"
        tail -30 "$LOG_SERVER"
        echo -e "${RED}=================================${NC}"
        abort "后端启动超时（10s 内未通过健康检查）"
    fi
done

# ---------- 启动前端 ----------
info "启动前端 → http://localhost:5173"
cd "$PROJECT_DIR/dashboard"
npm run dev > "$LOG_FRONTEND" 2>&1 &
FRONTEND_PID=$!

for i in $(seq 1 20); do
    sleep 0.5
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo ""
        echo -e "${RED}===== 前端日志 =====${NC}"
        cat "$LOG_FRONTEND"
        echo -e "${RED}====================${NC}"
        abort "前端进程已崩溃退出（Vite 启动失败）"
    fi
    if curl -sf http://localhost:5173 &>/dev/null; then
        info "前端已就绪 ✓"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo ""
        echo -e "${RED}===== 前端日志（最后 30 行）=====${NC}"
        tail -30 "$LOG_FRONTEND"
        echo -e "${RED}=================================${NC}"
        abort "前端启动超时（10s 内未通过健康检查）"
    fi
done

# ---------- 全部就绪 ----------
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

# 持续监控：任一服务意外退出则报错并终止另一个
while true; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo ""
        echo -e "${RED}===== 后端日志（最后 30 行）=====${NC}"
        tail -30 "$LOG_SERVER"
        echo -e "${RED}=================================${NC}"
        abort "后端进程意外退出"
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo ""
        echo -e "${RED}===== 前端日志（最后 30 行）=====${NC}"
        tail -30 "$LOG_FRONTEND"
        echo -e "${RED}=================================${NC}"
        abort "前端进程意外退出"
    fi
    sleep 3
done
