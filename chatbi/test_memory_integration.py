"""测试memory功能与chatbi的集成"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbi.core.agent_wrapper import AgentWrapper
from chatbi.core.memory import MemoryStore
from chatbi.models import Conversation, Message


async def test_agent_memory_integration():
    """测试AgentWrapper与memory的集成"""
    print("=" * 80)
    print("测试 AgentWrapper 与 Memory 的集成")
    print("=" * 80)

    # 重新初始化AgentWrapper（确保是单例）
    if AgentWrapper._instance is not None:
        AgentWrapper._instance = None

    agent = AgentWrapper()

    # 测试memory store初始化
    print("\n1. 检查memory store初始化")
    agent.memory_manager.init_session_memory()
    print(f"Memory store类型: {type(agent.memory_manager.memory_store)}")
    print(f"Memory store workspace: {agent.memory_manager.memory_store.workspace}")

    # 测试set_tool_context
    print("\n2. 测试设置工具上下文")
    agent.tool_executor.set_tool_context("test_user", "test_conversation")
    agent.memory_manager.init_session_memory("test_conversation")
    print(f"Memory key: {agent.memory_manager.memory_store.memory_key}")
    print(f"User memory path: {agent.memory_manager.memory_store._user_memory}")
    print(f"User history path: {agent.memory_manager.memory_store._user_history}")

    # 测试memory context获取
    print("\n3. 测试获取memory context")
    context = agent.memory_manager.get_memory_context()
    print(f"Memory context长度: {len(context)}")
    if context:
        print(f"Memory context预览: {context[:200]}...")

    # 测试写入memory
    print("\n4. 测试写入memory")
    agent.memory_manager.memory_store.write_long_term("用户偏好：喜欢使用SQL查询", level="user")
    agent.memory_manager.memory_store.write_long_term("全局知识：支持MySQL和Hive", level="global")
    content = agent.memory_manager.memory_store.read_long_term()
    print(f"Memory内容:\n{content}")

    # 测试history记录
    print("\n5. 测试history记录")
    agent.memory_manager.memory_store.append_history("2026-03-17: 用户查询了销售数据", level="user")
    history = agent.memory_manager.memory_store.read_history(level="user")
    print(f"History内容:\n{history}")

    # 测试memory context格式
    print("\n6. 测试memory context格式")
    formatted_context = agent.memory_manager.get_memory_context()
    print(f"格式化的memory context:\n{formatted_context}")

    # 清理
    import shutil
    test_workspace = Path(agent.memory_manager.workspace_path)
    memory_dir = test_workspace / "memory"
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
        print("\n7. 清理测试数据完成")

    print("\n" + "=" * 80)
    print("集成测试完成！")
    print("=" * 80)


async def test_memory_level_configuration():
    """测试memory级别配置"""
    print("\n" + "=" * 80)
    print("测试 Memory 级别配置")
    print("=" * 80)

    from chatbi.config import chatbi_config

    print("\n1. 读取memory配置")
    print(f"Memory enabled: {chatbi_config.memory_enabled}")
    print(f"Memory level: {chatbi_config.memory_level}")

    # 测试不同级别的memory
    print("\n2. 测试不同级别的memory")

    # Global only
    print("\n   - Global only")
    workspace = Path("/tmp/test_memory_levels")
    workspace.mkdir(parents=True, exist_ok=True)
    global_store = MemoryStore(workspace, memory_key=None)
    global_store.write_long_term("全局内容", level="global")
    print(f"Global content: {global_store.read_long_term()}")

    # User only
    print("\n   - User only")
    user_store = MemoryStore(workspace, memory_key="test:web")
    user_store.write_long_term("用户内容", level="user")
    print(f"User content: {user_store.read_long_term()}")

    # Combined
    print("\n   - Combined (global + user)")
    combined_store = MemoryStore(workspace, memory_key="test:web")
    combined_content = combined_store.read_long_term()
    print(f"Combined content: {combined_content}")

    # 清理
    import shutil
    shutil.rmtree(workspace)
    print("\n3. 清理完成")


async def main():
    """主函数"""
    await test_agent_memory_integration()
    await test_memory_level_configuration()
    print("\n" + "=" * 80)
    print("所有集成测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
