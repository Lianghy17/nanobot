"""测试沙箱文件操作功能"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbi.core.sandbox_manager import SandboxManager


async def test_sandbox_file_operations():
    """测试沙箱文件操作"""
    print("=" * 80)
    print("测试沙箱文件操作")
    print("=" * 80)

    conversation_id = "test_conv_123"
    sandbox_manager = SandboxManager()

    # 1. 创建沙箱
    print("\n1. 创建沙箱")
    session = await sandbox_manager.get_sandbox(conversation_id)
    print(f"沙箱ID: {session.sandbox.sandbox_id}")
    print(f"临时目录: {session.sandbox.temp_dir}")

    # 2. 上传文件
    print("\n2. 上传文件")
    test_content = b"name,age,city\nAlice,30,Beijing\nBob,25,Shanghai"
    success, file_path, error = await session.sandbox.upload_file("test.csv", test_content)
    print(f"上传结果: success={success}, path={file_path}, error={error}")

    # 3. 写入文件
    print("\n3. 写入文件")
    write_content = "这是测试内容\n第二行内容"
    await session.sandbox.write_file("test.txt", write_content)
    print(f"写入文件成功: test.txt")

    # 4. 读取文件
    print("\n4. 读取文件")
    success, content, error = await session.sandbox.read_file("test.txt", limit=100)
    print(f"读取结果: success={success}")
    print(f"内容: {content}")
    if error:
        print(f"错误: {error}")

    # 5. 列出文件
    print("\n5. 列出文件")
    files = await session.sandbox.list_files()
    print(f"文件列表:")
    for f in files:
        print(f"  - {f['filename']} ({f['type']}, {f['size']} bytes)")

    # 6. 获取文件（二进制）
    print("\n6. 获取文件（二进制）")
    success, binary_content, error = await session.sandbox.get_file("test.csv")
    print(f"获取结果: success={success}, size={len(binary_content)} bytes")
    if binary_content:
        print(f"内容预览: {binary_content[:50]}...")

    # 7. 测试文件不存在的情况
    print("\n7. 测试文件不存在的情况")
    success, content, error = await session.sandbox.read_file("nonexistent.txt", limit=100)
    print(f"读取不存在的文件: success={success}, error={error}")

    # 8. 测试嵌套目录
    print("\n8. 测试嵌套目录")
    await session.sandbox.write_file("data/test2.txt", "嵌套目录中的文件")
    success, content, error = await session.sandbox.read_file("data/test2.txt", limit=100)
    print(f"读取嵌套目录文件: success={success}, content={content}")

    # 9. 列出所有文件（包括嵌套）
    print("\n9. 列出所有文件（包括嵌套）")
    files = await session.sandbox.list_files()
    print(f"所有文件列表:")
    for f in files:
        print(f"  - {f['filename']} ({f['type']}, {f['size']} bytes)")

    # # 10. 清理沙箱
    # print("\n10. 清理沙箱")
    # await sandbox_manager.close_sandbox(conversation_id)
    # print(f"沙箱已关闭: {conversation_id}")
    #
    # print("\n" + "=" * 80)
    # print("所有测试完成！")
    # print("=" * 80)


async def main():
    """主函数"""
    await test_sandbox_file_operations()


if __name__ == "__main__":
    asyncio.run(main())
