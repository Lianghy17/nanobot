#!/bin/bash
# 快速关闭 8080 和 8081 端口的进程

for port in 8080 8081; do
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null && echo "✅ 已关闭端口 $port (PID: $pid)"
    else
        echo "⚠️  端口 $port 无进程"
    fi
done
