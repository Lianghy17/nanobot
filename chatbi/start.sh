#!/bin/bash

# ChatBI快速启动脚本

echo "=== ChatBI 快速启动 ==="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 创建工作目录
echo "创建工作目录..."
mkdir -p workspace/sessions
mkdir -p workspace/files
mkdir -p workspace/shared

# 启动服务
echo "启动服务 (http://localhost:8080)..."

# 直接运行 main.py（从项目根目录）
python3 -m chatbi.main
