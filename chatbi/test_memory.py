"""测试memory功能"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbi.core.memory import MemoryStore, MemoryManager


async def test_memory_store():
    """测试MemoryStore"""
    print("=" * 80)
    print("测试 MemoryStore")
    print("=" * 80)

    # 创建临时workspace
    workspace = Path("/tmp/test_chatbi_memory")
    workspace.mkdir(parents=True, exist_ok=True)

    # 测试global memory
    print("\n1. 测试global memory")
    global_store = MemoryStore(workspace, memory_key=None)
    global_store.write_long_term("这是全局memory内容", level="global")
    content = global_store.read_long_term()
    print(f"Global memory内容: {content}")

    # 测试user memory
    print("\n2. 测试user memory")
    user_store = MemoryStore(workspace, memory_key="user123:web")
    user_store.write_long_term("这是用户专属memory内容", level="user")
    content = user_store.read_long_term()
    print(f"User memory内容: {content}")

    # 测试history
    print("\n3. 测试history")
    user_store.append_history("这是history条目", level="user")
    history = user_store.read_history(level="user")
    print(f"History内容: {history}")

    # 测试memory context
    print("\n4. 测试memory context")
    context = user_store.get_memory_context()
    print(f"Memory context: {context[:200]}...")

    # 清理
    import shutil
    shutil.rmtree(workspace)
    print("\n5. 清理完成")


async def test_memory_manager():
    """测试MemoryManager"""
    print("\n" + "=" * 80)
    print("测试 MemoryManager")
    print("=" * 80)

    # 创建临时workspace
    workspace = Path("/tmp/test_chatbi_memory_manager")
    workspace.mkdir(parents=True, exist_ok=True)

    manager = MemoryManager(workspace)

    # 测试global memory
    print("\n1. 测试global memory")
    manager.set_global_memory("这是全局memory")
    global_memory = manager.get_global_memory()
    print(f"Global memory: {global_memory}")

    # 测试user memory
    print("\n2. 测试user memory")
    manager.set_user_memory("user123", "web", "这是用户memory")
    user_memory = manager.get_user_memory("user123", "web")
    print(f"User memory: {user_memory}")

    # 测试list users
    print("\n3. 测试list users")
    users = manager.list_users()
    print(f"用户列表: {users}")

    # 测试stats
    print("\n4. 测试stats")
    stats = manager.get_stats()
    print(f"统计信息: {stats}")

    # 测试combined memory
    print("\n5. 测试combined memory")
    combined = manager.get_combined_memory("user123", "web")
    print(f"Combined memory: {combined[:200]}...")

    # 清理
    import shutil
    shutil.rmtree(workspace)
    print("\n6. 清理完成")


async def main():
    """主函数"""
    await test_memory_store()
    await test_memory_manager()
    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
