#!/bin/bash

# Nanobot Server 快速启动脚本
# 启动 Flask API 服务器（包含图片服务器功能）

set -e

echo "🐈 启动 Nanobot Server..."

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "📦 激活虚拟环境..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 激活虚拟环境..."
    source venv/bin/activate
fi

# 默认配置
HOST="${NANOBOT_HOST:-localhost}"
PORT="${NANOBOT_PORT:-5088}"
DEBUG="${NANOBOT_DEBUG:-false}"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --debug)
            DEBUG="true"
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --host HOST    绑定主机地址 (默认: localhost)"
            echo "  --port PORT    绑定端口号 (默认: 5088)"
            echo "  --debug        启用调试模式"
            echo "  --help         显示帮助信息"
            echo ""
            echo "环境变量:"
            echo "  NANOBOT_HOST   绑定主机地址"
            echo "  NANOBOT_PORT   绑定端口号"
            echo "  NANOBOT_DEBUG  启用调试模式 (true/false)"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "=================================="
echo "  🐈 Nanobot Server 配置"
echo "=================================="
echo "  主机: $HOST"
echo "  端口: $PORT"
echo "  调试: $DEBUG"
echo "=================================="
echo ""



# 转换 debug 为 Python 布尔值
if [ "$DEBUG" = "true" ]; then
    PY_DEBUG="True"
else
    PY_DEBUG="False"
fi

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
python3 -c "
from nanobot.server.app import run_server
run_server(host='$HOST', port=$PORT, debug=$PY_DEBUG)
"
