#!/bin/bash
# easy_vpn 根目录部署入口（薄封装）
# 用法：
#   sudo bash server_deploy.sh              # 正式部署（含 SSL）
#   sudo bash server_deploy.sh --skip-ssl   # 测试环境，跳过 SSL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/deploy/server_deploy.sh" "$@"
