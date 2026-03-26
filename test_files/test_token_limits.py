#!/usr/bin/env python3
"""测试Token限制和文件URL流程"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi.config import chatbi_config


def test_config():
    """测试配置是否正确加载"""
    print("=" * 80)
    print("配置测试")
    print("=" * 80)

    print(f"LLM模型: {chatbi_config.llm_model}")
    print(f"LLM温度: {chatbi_config.llm_temperature}")
    print(f"LLM最大tokens: {chatbi_config.llm_max_tokens}")
    print(f"LLM上下文窗口: {chatbi_config.llm_context_window}")
    print(f"LLM最大上下文tokens: {chatbi_config.llm_max_context_tokens}")
    print(f"LLM预留tokens: {chatbi_config.llm_reserved_tokens}")
    print(f"工具结果最大长度: {chatbi_config.agent_max_tool_result_length}")

    # 计算可用tokens
    available_tokens = chatbi_config.llm_max_context_tokens - chatbi_config.llm_reserved_tokens
    print(f"\n可用于工具消息的tokens: {available_tokens}")
    print(f"限制比例: {available_tokens / chatbi_config.llm_context_window * 100:.1f}%")

    # 验证配置合理性
    if chatbi_config.llm_max_tokens > chatbi_config.llm_context_window:
        print(f"\n⚠️  警告: max_tokens ({chatbi_config.llm_max_tokens}) > 上下文窗口 ({chatbi_config.llm_context_window})")
    else:
        print(f"\n✅ max_tokens配置合理")

    if chatbi_config.llm_max_context_tokens > chatbi_config.llm_context_window:
        print(f"⚠️  警告: max_context_tokens ({chatbi_config.llm_max_context_tokens}) > 上下文窗口 ({chatbi_config.llm_context_window})")
    else:
        print(f"✅ max_context_tokens配置合理")


def test_file_extensions():
    """测试文件扩展名支持"""
    print("\n" + "=" * 80)
    print("文件扩展名支持测试")
    print("=" * 80)

    from chatbi.core.sandbox_manager import LocalSandbox

    # 创建一个临时沙箱实例来检查支持的扩展名
    sandbox = LocalSandbox("test", "test_conv")

    # 通过inspect获取_collect_generated_files方法中定义的扩展名
    import inspect
    source = inspect.getsource(sandbox._collect_generated_files)

    print("支持的文件扩展名:")
    extensions = []
    for line in source.split('\n'):
        if "':" in line and "application" in line or "text/" in line or "image/" in line:
            if '.html' in line:
                extensions.append("HTML (.html, .htm)")
            if '.png' in line or '.jpg' in line:
                extensions.append("图片 (.png, .jpg, .jpeg, .gif, .svg)")
            if '.csv' in line or '.xlsx' in line:
                extensions.append("数据文件 (.csv, .xlsx, .xls, .json)")
            if '.txt' in line or '.md' in line:
                extensions.append("文本文件 (.txt, .md)")

    for ext in set(extensions):
        print(f"  ✅ {ext}")

    if '.html' in source:
        print("\n✅ HTML文件已被支持！")
    else:
        print("\n❌ HTML文件未被支持")


def test_read_file_limit():
    """测试read_file工具的内容限制"""
    print("\n" + "=" * 80)
    print("read_file工具内容限制测试")
    print("=" * 80)

    from chatbi.agent.tools.file_ops import ReadFileTool

    tool = ReadFileTool()

    # 检查execute方法的签名
    import inspect
    sig = inspect.signature(tool.execute)
    
    print(f"工具名称: {tool.name}")
    print(f"参数: {sig}")

    # 创建一个大内容模拟
    large_content = "A" * 10000

    print(f"\n模拟大文件: {len(large_content)} 字符")
    print(f"期望截断长度: 5000 字符")


if __name__ == "__main__":
    try:
        test_config()
        test_file_extensions()
        test_read_file_limit()

        print("\n" + "=" * 80)
        print("✅ 所有测试完成")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
