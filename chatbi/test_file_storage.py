#!/usr/bin/env python3
"""测试文件存储功能"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from chatbi.config import settings

def test_file_storage():
    """测试文件存储配置"""

    print("=" * 80)
    print("文件存储配置测试")
    print("=" * 80)

    # 1. 检查 workspace 目录
    workspace_path = Path(settings.workspace_path)
    print(f"\n1. Workspace 路径: {workspace_path}")
    print(f"   存在: {workspace_path.exists()}")

    # 2. 检查 files 目录
    files_path = workspace_path / "files"
    print(f"\n2. Files 路径: {files_path}")
    print(f"   存在: {files_path.exists()}")

    if not files_path.exists():
        print("   创建目录...")
        files_path.mkdir(parents=True, exist_ok=True)
        print(f"   已创建: {files_path}")

    # 3. 检查其他目录
    sessions_path = workspace_path / "sessions"
    memory_path = workspace_path / "memory"

    print(f"\n3. Sessions 路径: {sessions_path}")
    print(f"   存在: {sessions_path.exists()}")

    print(f"\n4. Memory 路径: {memory_path}")
    print(f"   存在: {memory_path.exists()}")

    # 4. 测试创建测试文件
    test_file = files_path / "test_file.txt"
    print(f"\n5. 创建测试文件: {test_file}")
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("这是一个测试文件\n测试时间: 2026-03-19\n")
        print(f"   创建成功")
        print(f"   文件大小: {test_file.stat().st_size} 字节")

        # 读取测试文件
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"   文件内容:\n{content}")

    except Exception as e:
        print(f"   创建失败: {e}")

    # 5. 列出 files 目录中的文件
    print(f"\n6. Files 目录内容:")
    if files_path.exists():
        files = list(files_path.glob("*"))
        if files:
            for f in sorted(files):
                size_kb = f.stat().st_size / 1024
                print(f"   - {f.name} ({size_kb:.2f} KB)")
        else:
            print("   (空目录)")
    else:
        print("   (目录不存在)")

    # 6. 预期的 URL 格式
    print(f"\n7. 预期的 URL 格式:")
    print(f"   静态文件: /files/<unique_filename>")
    print(f"   示例: /files/web_123_20260319_143022_chart.png")
    print(f"   下载API: /api/files/download/<user_channel>/<conversation_id>/<filename>")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_file_storage()
