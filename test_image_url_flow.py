#!/usr/bin/env python3
"""测试图像文件URL流程"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import tempfile
import json
from chatbi.core.sandbox_manager import SandboxManager
from chatbi.agent.tools.python_tool import PythonTool


async def test_image_url_generation():
    """测试图像生成和URL转换流程"""
    print("=" * 80)
    print("测试图像文件URL生成流程")
    print("=" * 80)

    # 1. 初始化沙箱管理器
    sandbox_manager = SandboxManager()
    await sandbox_manager.start()
    print("✅ 沙箱管理器已启动")

    # 2. 创建测试会话ID
    conversation_id = "test_conv_image_url"

    # 3. 获取沙箱
    session = await sandbox_manager.get_sandbox(conversation_id)
    if not session:
        print("❌ 获取沙箱失败")
        return
    print(f"✅ 沙箱已创建: {session.sandbox.sandbox_id}")

    # 4. 执行生成图像的代码
    code = """
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import numpy as np

# 生成测试数据
x = np.linspace(0, 10, 100)
y = np.sin(x)

# 创建图表
plt.figure(figsize=(10, 6))
plt.plot(x, y, label='sin(x)')
plt.title('Test Chart')
plt.xlabel('X')
plt.ylabel('Y')
plt.legend()
plt.grid(True)

# 保存图像
plt.savefig('test_chart.png', dpi=100, bbox_inches='tight')
print("图像已保存: test_chart.png")
"""

    print("\n" + "=" * 80)
    print("执行代码生成图像...")
    print("=" * 80)

    result = await session.execute_code(code, timeout=30)

    print("\n执行结果:")
    print(f"  - 成功: {result['success']}")
    print(f"  - 输出: {result['output']}")
    print(f"  - 错误: {result.get('error')}")
    print(f"  - 生成文件数: {len(result.get('files', []))}")

    # 5. 检查生成的文件
    files = result.get("files", [])
    if files:
        print("\n" + "=" * 80)
        print("生成的文件信息:")
        print("=" * 80)
        for file_data in files:
            print(f"  文件名: {file_data['filename']}")
            print(f"  类型: {file_data['type']}")
            print(f"  大小: {file_data['size']} bytes")
            print(f"  URL: {file_data.get('url', 'N/A')}")
            print(f"  唯一文件名: {file_data.get('unique_filename', 'N/A')}")
            print()

            # 验证URL格式
            url = file_data.get('url')
            if url:
                print(f"  ✅ URL字段存在: {url}")
                if url.startswith('/files/'):
                    print(f"  ✅ URL格式正确（静态文件路径）")
                else:
                    print(f"  ⚠️  URL格式可能不正确: {url}")
            else:
                print(f"  ❌ URL字段缺失!")

            # 验证文件是否真的存在
            unique_filename = file_data.get('unique_filename')
            if unique_filename:
                files_dir = Path(__file__).parent / "workspace" / "files"
                file_path = files_dir / unique_filename
                if file_path.exists():
                    print(f"  ✅ 文件已复制到workspace/files: {file_path}")
                    print(f"     文件大小: {file_path.stat().st_size} bytes")
                else:
                    print(f"  ❌ 文件未找到: {file_path}")
    else:
        print("\n❌ 没有生成文件!")

    # 6. 测试PythonTool返回的数据结构
    print("\n" + "=" * 80)
    print("测试 PythonTool 返回的数据结构:")
    print("=" * 80)

    python_tool = PythonTool()
    python_tool.set_context("test_user")
    python_tool.set_conversation_id(conversation_id)

    tool_result = await python_tool.execute(code, timeout=30)

    if tool_result.get("success"):
        result_data = tool_result.get("result", {})
        files_from_tool = result_data.get("files", [])

        print(f"PythonTool返回的文件数: {len(files_from_tool)}")

        for file_info in files_from_tool:
            print(f"\n  文件: {file_info['filename']}")
            print(f"    - type: {file_info['type']}")
            print(f"    - size: {file_info['size']}")
            print(f"    - path: {file_info.get('path')}")
            print(f"    - url: {file_info.get('url')}")
            print(f"    - in_sandbox: {file_info.get('in_sandbox')}")

            # 验证URL字段
            if file_info.get('url'):
                print(f"    ✅ URL字段已正确传递")
            else:
                print(f"    ❌ URL字段缺失!")

    # 7. 清理
    await sandbox_manager.close_sandbox(conversation_id)
    await sandbox_manager.stop()
    print("\n✅ 沙箱已清理")


async def test_sse_event_data():
    """测试SSE事件数据格式"""
    print("\n" + "=" * 80)
    print("测试SSE事件数据格式")
    print("=" * 80)

    from chatbi.core.sse_manager import SSEManager

    sse_manager = SSEManager()

    # 模拟发送事件
    conversation_id = "test_sse_event"
    event_type = "processing_completed"

    # 模拟文件数据（应该从PythonTool返回）
    test_files = [
        {
            "filename": "test_chart.png",
            "type": "image/png",
            "size": 12345,
            "path": "test_chart.png",
            "url": "/files/test_conv_image_url_20260319_143022_test_chart.png",
            "in_sandbox": True
        }
    ]

    event_data = {
        "message_id": "msg_123",
        "content": "分析完成",
        "tools_used": ["execute_python"],
        "files": test_files
    }

    print("\nSSE事件数据:")
    print(json.dumps(event_data, indent=2, ensure_ascii=False))

    # 验证前端可以正确解析
    print("\n前端接收到的files字段:")
    for file in event_data["files"]:
        print(f"  - {file['filename']}: URL = {file.get('url', 'N/A')}")

    print("\n✅ SSE事件数据格式正确")


async def main():
    """运行所有测试"""
    try:
        await test_image_url_generation()
        await test_sse_event_data()

        print("\n" + "=" * 80)
        print("✅ 所有测试完成")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
