#!/bin/bash

# ChatBI 启动脚本（包含图片服务器）
# 同时启动 ChatBI 主服务和图片服务器

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 创建工作目录
echo "创建工作目录..."
mkdir -p workspace/sessions
mkdir -p workspace/files
mkdir -p workspace/images
mkdir -p workspace/shared

# 定义清理函数
cleanup() {
    echo ""
    echo "正在停止服务..."
    if [ ! -z "$IMAGE_PID" ]; then
        kill $IMAGE_PID 2>/dev/null
        echo "图片服务器已停止"
    fi
    if [ ! -z "$CHATBI_PID" ]; then
        kill $CHATBI_PID 2>/dev/null
        echo "ChatBI服务已停止"
    fi
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 启动图片服务器（后台运行）
echo "启动图片服务器 (http://localhost:8081)..."
python3 -m chatbi.services.image_server &
IMAGE_PID=$!
sleep 2

# 检查图片服务器是否启动成功
if ! kill -0 $IMAGE_PID 2>/dev/null; then
    echo "❌ 图片服务器启动失败"
    exit 1
fi
echo "✅ 图片服务器已启动 (PID: $IMAGE_PID)"

# 启动 ChatBI 主服务
echo "启动 ChatBI 主服务 (http://localhost:8080)..."
echo ""
echo "=========================================="
echo "ChatBI 服务地址: http://localhost:8080"
echo "图片服务器地址: http://localhost:8081"
echo "=========================================="
echo ""

python3 -m chatbi.main &
CHATBI_PID=$!

# 等待任一进程退出
wait $CHATBI_PID $IMAGE_PID

# 清理
cleanup
