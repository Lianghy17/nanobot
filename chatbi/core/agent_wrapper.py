"""Agent包装器 - 封装nanobot的Agent核心"""
import os
import json
import logging
import re
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
from ..config import chatbi_config
from ..models import Conversation, Message
from ..models.llm import LLMResponse, ToolCallRequest
from .conversation_manager import ConversationManager
from ..agent.tools import RAGTool, SQLTool, PythonTool, ReadFileTool, WriteFileTool
from .llm_client import LLMClient
from .memory import MemoryStore
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentWrapper:
    """Agent包装器 - 使用Agent Loop模式（单例模式）"""

    _instance: Optional["AgentWrapper"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._tools = {}
        self._initialized = False
        self.conversation_manager = ConversationManager()

        # 初始化LLM客户端
        self.llm_client = LLMClient(
            api_base=chatbi_config.llm_api_base,
            api_key=chatbi_config.llm_api_key,
            model=chatbi_config.llm_model,
            temperature=chatbi_config.llm_temperature,
            max_tokens=chatbi_config.llm_max_tokens,
            timeout=chatbi_config.llm_timeout
        )

        # Agent配置
        self.max_iterations = chatbi_config.agent_max_iterations
        self.max_history_messages = chatbi_config.agent_max_history_messages

        # 初始化Memory Store
        workspace = Path(chatbi_config.workspace_path)
        self.memory_store = MemoryStore(workspace)

        # 初始化工具
        self._register_tools()

    def _register_tools(self):
        """注册工具"""
        self._tools = {
            "rag_search": RAGTool(),
            "execute_sql": SQLTool(),
            "execute_python": PythonTool(),
            "read_file": ReadFileTool(),
            "write_file": WriteFileTool(),
        }
        logger.info(f"注册工具: {list(self._tools.keys())}")

    def _set_tool_context(self, user_channel: str, conversation_id: str = None):
        """设置所有工具的上下文"""
        # 更新memory的memory_key
        memory_key = f"{user_channel}:web" if conversation_id else None
        self.memory_store = MemoryStore(Path(chatbi_config.workspace_path), memory_key=memory_key)

        for tool in self._tools.values():
            tool.set_context(user_channel)
            # 如果工具支持设置会话ID，则设置
            if hasattr(tool, 'set_conversation_id') and conversation_id:
                tool.set_conversation_id(conversation_id)

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具的定义"""
        return [tool.get_definition() for tool in self._tools.values()]

    def _build_messages(
        self,
        conversation: Conversation,
        message: Message,
        tool_messages: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        构建发送给LLM的消息列表

        Args:
            conversation: 会话对象
            message: 当前消息
            tool_messages: 工具相关消息（tool_calls和tool_results）

        Returns:
            消息列表
        """
        # 获取memory上下文
        memory_context = self.memory_store.get_memory_context()

        # 构建系统提示
        tool_names = ", ".join(self._tools.keys())
        system_prompt = chatbi_config.agent_system_prompt_template.format(
            scene_name=conversation.scene_name,
            scene_code=conversation.scene_code,
            tool_names=tool_names,
            current_time=chatbi_config.current_time,
            runtime_environment=chatbi_config.runtime_environment
        )

        # 将memory上下文添加到系统提示中
        if memory_context:
            system_prompt = f"{system_prompt}\n\n{memory_context}"

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # 添加历史消息
        history = conversation.get_history(max_messages=self.max_history_messages)
        messages.extend(history)

        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": message.content
        })

        # 如果有工具消息，添加到列表
        if tool_messages:
            messages.extend(tool_messages)

        return messages

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        执行工具并返回结果

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            工具执行结果（字符串格式）
        """
        if tool_name not in self._tools:
            logger.error(f"[工具执行] 工具 '{tool_name}' 不存在")
            return f"Error: Tool '{tool_name}' not found"

        tool = self._tools[tool_name]

        try:
            logger.info("=" * 80)
            logger.info(f"[工具执行] 开始执行: {tool_name}")
            logger.info(f"[工具执行] 参数: {json.dumps(tool_args, ensure_ascii=False)}")

            result = await tool.execute(**tool_args)

            if result.get("success"):
                # 将结果转换为字符串
                result_str = json.dumps(result.get("result"), ensure_ascii=False)
                logger.info(f"[工具执行] 成功: {result_str[:200]}{'...' if len(result_str) > 200 else ''}")
                logger.info("=" * 80)
                return result_str
            else:
                error_msg = result.get("result", "Unknown error")
                logger.error(f"[工具执行] 失败: {tool_name}, 错误: {error_msg}")
                logger.info("=" * 80)
                return f"Error: {error_msg}"

        except Exception as e:
            logger.error(f"[工具执行] 异常: {tool_name}, 错误: {e}", exc_info=True)
            logger.info("=" * 80)
            return f"Error: {str(e)}"

    @staticmethod
    def _strip_think(text: Optional[str]) -> Optional[str]:
        """
        移除思考块（有些模型会在内容中嵌入 thinking 块）

        Args:
            text: 原始文本

        Returns:
            移除思考块后的文本
        """
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: List[ToolCallRequest]) -> str:
        """
        格式化工具调用提示，例如 'web_search("query")'

        Args:
            tool_calls: 工具调用列表

        Returns:
            格式化后的工具调用提示
        """
        def _fmt(tc: ToolCallRequest) -> str:
            val = next(iter(tc.arguments.values()), None) if tc.arguments else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'
        return ", ".join(_fmt(tc) for tc in tool_calls)

    async def _run_agent_loop(
        self,
        conversation: Conversation,
        message: Message,
        on_progress: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[Optional[str], List[str], List[Dict[str, Any]]]:
        """
        运行Agent迭代循环

        Args:
            conversation: 会话对象
            message: 当前消息
            on_progress: 可选的进度回调函数

        Returns:
            Tuple of (final_content, list_of_tools_used, tool_messages)
        """
        # 初始化
        iteration = 0
        final_content = None
        tools_used: List[str] = []
        tool_messages: List[Dict[str, Any]] = []

        logger.info("=" * 80)
        logger.info(f"[Agent Loop 开始] 场景={conversation.scene_name}, 用户消息={message.content}")
        logger.info(f"[Agent Loop 开始] 最大迭代={self.max_iterations}")
        logger.info("=" * 80)

        # 调试断点 - 如果需要调试，请取消下面这行的注释
        # breakpoint()

        while iteration < self.max_iterations:
            iteration += 1
            logger.info("=" * 80)
            logger.info(f"[Agent Loop 迭代 {iteration}/{self.max_iterations}]")
            logger.info("=" * 80)

            # 构建消息列表
            messages = self._build_messages(conversation, message, tool_messages if tool_messages else None)

            logger.info(f"[Agent Loop] 当前上下文消息数: {len(messages)}")

            try:
                # 调用LLM
                response: LLMResponse = await self.llm_client.chat(
                    messages=messages,
                    tools=self._get_tool_definitions()
                )
            except Exception as e:
                logger.error(f"[Agent Loop] LLM调用失败: {type(e).__name__}: {e}")
                raise

            # 如果有工具调用
            if response.tool_calls:
                logger.info(f"[Agent Loop] 检测到 {len(response.tool_calls)} 个工具调用，开始执行")

                # 进度回调
                if on_progress:
                    clean_content = self._strip_think(response.content)
                    await on_progress(clean_content or self._tool_hint(response.tool_calls))

                # 构建assistant消息（包含tool_calls）
                assistant_message = {
                    "role": "assistant",
                    "content": response.content
                }

                if response.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in response.tool_calls
                    ]

                tool_messages.append(assistant_message)

                # 执行每个工具调用
                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)

                    # 执行工具
                    result = await self._execute_tool(tool_call.name, tool_call.arguments)

                    # 添加工具结果消息
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": result
                    })

                logger.info(f"[Agent Loop] 工具执行完成，已使用工具: {tools_used}")
                logger.info(f"[Agent Loop] 准备进入下一轮迭代")

            else:
                # 没有工具调用，结束循环
                logger.info("[Agent Loop] 没有工具调用，结束循环")
                final_content = self._strip_think(response.content)
                break

        logger.info("=" * 80)
        logger.info(f"[Agent Loop 结束] 总迭代次数: {iteration}")
        logger.info(f"[Agent Loop 结束] 使用工具: {tools_used}")
        logger.info(f"[Agent Loop 结束] 响应长度: {len(final_content) if final_content else 0} 字符")
        logger.info("=" * 80)

        return final_content, tools_used, tool_messages

    def _extract_files_from_tool_results(self, tool_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从工具结果中提取文件信息"""
        files = []

        for msg in tool_messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                try:
                    # 解析工具结果（JSON格式）
                    import json
                    result = json.loads(content)

                    # 检查是否有文件信息 - 支持多种格式
                    if isinstance(result, dict):
                        # 格式1: result.files
                        if "files" in result:
                            files.extend(result["files"])
                        # 格式2: result.result.files
                        elif "result" in result and isinstance(result["result"], dict):
                            result_data = result["result"]
                            if "files" in result_data:
                                files.extend(result_data["files"])

                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(f"解析工具结果失败: {e}")

        return files

    def _update_memory(
        self,
        conversation: Conversation,
        message: Message,
        response_content: str,
        tools_used: List[str]
    ) -> None:
        """
        更新memory信息

        Args:
            conversation: 会话对象
            message: 用户消息
            response_content: 响应内容
            tools_used: 使用的工具列表
        """
        try:
            # 构建history条目
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history_entry = f"""## {timestamp}
User: {message.content}
Assistant: {response_content[:200]}{'...' if len(response_content) > 200 else ''}
Tools: {', '.join(tools_used) if tools_used else 'None'}
Scene: {conversation.scene_name}
"""
            # 更新history
            self.memory_store.append_history(history_entry, level="user")
            logger.debug(f"[Memory] 更新history成功")

        except Exception as e:
            logger.error(f"[Memory] 更新memory失败: {e}", exc_info=True)

    async def process(self, conversation: Conversation, message: Message) -> Optional[Dict[str, Any]]:
        """
        处理消息

        Args:
            conversation: 会话对象
            message: 当前消息

        Returns:
            处理结果字典
        """
        # 测试终端输出
        pid = os.getpid()
        print(f"\n{'='*80}")
        print(f"[PID:{pid}] [终端输出] Agent处理开始: {conversation.conversation_id}")
        print(f"[PID:{pid}] 用户消息: {message.content}")
        print(f"{'='*80}\n")

        logger.info(f"[PID:{pid}] " + "=" * 80)
        logger.info(f"[PID:{pid}] [Agent 处理开始]")
        logger.info(f"[PID:{pid}] 会话ID: {conversation.conversation_id}")
        logger.info(f"[PID:{pid}] 场景: {conversation.scene_name} ({conversation.scene_code})")
        logger.info(f"[PID:{pid}] 用户消息: {message.content}")
        logger.info(f"[PID:{pid}] " + "=" * 80)

        # 设置工具上下文
        self._set_tool_context(conversation.user_channel, conversation.conversation_id)

        try:
            # 运行Agent Loop
            final_content, tools_used, tool_messages = await self._run_agent_loop(conversation, message)

            # 提取文件信息
            generated_files = self._extract_files_from_tool_results(tool_messages)

            if final_content is None:
                final_content = "处理完成，但没有可用的响应内容。"

            # 如果有生成的文件，添加到响应中
            if generated_files:
                logger.info(f"生成的文件: {len(generated_files)} 个")

            logger.info("=" * 80)
            logger.info("[Agent 处理完成]")
            logger.info(f"使用工具: {tools_used}")
            logger.info(f"响应长度: {len(final_content)} 字符")
            logger.info(f"生成文件: {len(generated_files)} 个")
            logger.info(f"响应内容: {final_content[:200]}{'...' if len(final_content) > 200 else ''}")
            logger.info("=" * 80)

            # 如果启用了memory功能，更新memory
            if chatbi_config.memory_enabled:
                self._update_memory(conversation, message, final_content, tools_used)

            return {
                "content": final_content,
                "tools_used": tools_used,
                "tool_calls": [],
                "metadata": {
                    "files": generated_files,
                    "format": "markdown"
                }
            }

        except Exception as e:
            logger.error("=" * 80)
            logger.error("[Agent 处理失败]")
            logger.error(f"错误信息: {e}")
            logger.error("=" * 80)
            return {
                "content": f"处理失败：{str(e)}",
                "tools_used": [],
                "metadata": {"error": True}
            }
