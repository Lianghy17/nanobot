#!/bin/bash

# ChatBI 启动脚本

echo "🚀 启动 ChatBI 服务..."





# 创建必要的目录
mkdir -p workspace/sessions

# 启动服务
echo "✅ 启动服务..."
python main.py
