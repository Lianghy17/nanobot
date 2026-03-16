#!/usr/bin/env python3
"""检查ChatBI依赖是否正确安装"""

import sys

print("=== ChatBI 依赖检查 ===\n")

required_packages = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic_settings",
    "httpx",
    "PyJWT",
    "loguru",
    "python_multipart",
]

missing_packages = []

for package in required_packages:
    try:
        __import__(package)
        print(f"✅ {package}")
    except ImportError:
        print(f"❌ {package} (未安装)")
        missing_packages.append(package)

if missing_packages:
    print(f"\n缺少的包: {', '.join(missing_packages)}")
    print("\n请运行:")
    print("  pip install -r requirements-chatbi.txt")
    sys.exit(1)
else:
    print("\n✅ 所有依赖已安装！")

# 尝试导入主模块
try:
    from chatbi.config import settings
    print(f"\n✅ 配置模块加载成功")
    print(f"   工作空间: {settings.workspace_path}")
except Exception as e:
    print(f"\n❌ 配置模块加载失败: {e}")
    sys.exit(1)

print("\n✅ 所有检查通过！")
