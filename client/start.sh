#!/usr/bin/env bash
# easy_vpn Client 一键启动脚本
# 支持 macOS 和 Ubuntu
# 用法：bash start.sh [--no-ui]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
CONFIG="$SCRIPT_DIR/config.yml"
EXTRA_ARGS="$*"

# ── 颜色输出 ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 检查 Python ───────────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON=python
else
    error "未找到 Python 3，请先安装：\n  macOS:  brew install python\n  Ubuntu: sudo apt install python3 python3-venv"
fi

info "Python: $($PYTHON --version)"

# ── 检查配置文件 ───────────────────────────────────────────────────────────
if [ ! -f "$CONFIG" ]; then
    if [ -f "$SCRIPT_DIR/config.example.yml" ]; then
        warn "未找到 config.yml，已从 config.example.yml 复制，请编辑后重新运行"
        cp "$SCRIPT_DIR/config.example.yml" "$CONFIG"
        error "请先编辑 config.yml 填入 server url 和 token"
    else
        error "未找到 config.yml，请参考 config.example.yml 创建"
    fi
fi

# ── 创建/更新虚拟环境 ──────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "创建虚拟环境..."
    $PYTHON -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# 检查依赖是否需要安装/更新
REQS="$SCRIPT_DIR/requirements.txt"
REQS_STAMP="$VENV_DIR/.reqs_installed"
if [ ! -f "$REQS_STAMP" ] || [ "$REQS" -nt "$REQS_STAMP" ]; then
    info "安装依赖..."
    pip install -q -r "$REQS"
    touch "$REQS_STAMP"
else
    info "依赖已是最新，跳过安装"
fi

# ── 启动 ──────────────────────────────────────────────────────────────────
info "启动 easy_vpn client..."
exec python main.py --config "$CONFIG" $EXTRA_ARGS
