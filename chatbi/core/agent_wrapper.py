"""Agent包装器 - 封装nanobot的Agent核心"""
import os
import json
import asyncio
import logging
import re
import json_repair
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
from ..config import chatbi_config
from ..models import Conversation, Message
from ..models.llm import LLMResponse, ToolCallRequest
from .conversation_manager import ConversationManager
from ..agent.tools import RAGTool, SQLTool, PythonTool, ReadFileTool, WriteFileTool
from .llm_client import LLMClient
from .memory import MemoryStore
from .sse_manager import sse_manager
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
        self._current_conversation_id = None  # 当前会话ID（用于SSE推送）

        # 初始化LLM客户端
        self.llm_client = LLMClient(
            api_base=chatbi_config.llm_api_base,
            api_key=chatbi_config.llm_api_key,
            model=chatbi_config.llm_model,
            temperature=chatbi_config.llm_temperature,
            max_tokens=chatbi_config.llm_max_tokens,
            timeout=chatbi_config.llm_timeout,
            thinking_disabled=chatbi_config.llm_thinking_disabled
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
        # 会话级别隔离：使用 conversation_id 作为 memory_key
        # 目录结构: workspace/memory/conversations/{conversation_id}/
        memory_key = f"conv:{conversation_id}" if conversation_id else None
        self.memory_store = MemoryStore(Path(chatbi_config.workspace_path), memory_key=memory_key)

        for tool in self._tools.values():
            tool.set_context(user_channel)
            # 如果工具支持设置会话ID，则设置
            if hasattr(tool, 'set_conversation_id') and conversation_id:
                tool.set_conversation_id(conversation_id)

    def _get_tool_definitions(self, scene_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取工具的定义

        Args:
            scene_code: 场景代码，如果提供则只返回该场景支持的工具

        Returns:
            工具定义列表
        """
        if scene_code:
            # 获取场景支持的工具列表
            supported_skills = chatbi_config.get_scene_supported_skills(scene_code)
            if supported_skills:
                # 只返回场景支持的工具
                logger.info(f"[场景工具过滤] 场景={scene_code}, 支持的工具={supported_skills}")
                return [
                    self._tools[skill].get_definition()
                    for skill in supported_skills
                    if skill in self._tools
                ]

        # 返回所有工具定义
        return [tool.get_definition() for tool in self._tools.values()]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        估算文本的token数量（粗略估计）
        - 中文：1字符 ≈ 1.5 tokens
        - 英文：1字符 ≈ 0.3 tokens
        - 平均：1字符 ≈ 0.5 tokens
        """
        # 统计中文字符
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        # 统计非中文字符
        other_chars = len(text) - chinese_chars

        # 估算tokens
        estimated_tokens = int(chinese_chars * 1.5 + other_chars * 0.3)

        # 最小至少返回1
        return max(1, estimated_tokens)

    def _trim_history_by_tokens(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        system_prompt_tokens: int,
        current_user_tokens: int,
        tool_messages_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        根据token限制裁剪历史消息

        Args:
            messages: 历史消息列表
            max_tokens: 最大token限制
            system_prompt_tokens: 系统提示的token数
            current_user_tokens: 当前用户消息的token数
            tool_messages_tokens: 工具消息的token数

        Returns:
            裁剪后的消息列表
        """
        # 计算可用给历史消息的token数
        available_for_history = max_tokens - system_prompt_tokens - current_user_tokens - tool_messages_tokens

        # 保留最近的消息
        trimmed_messages = []
        current_tokens = 0

        # 从最新的消息开始倒序处理
        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens(msg.get("content", ""))

            if current_tokens + msg_tokens > available_for_history:
                logger.warning(f"[Token管理] 跳过历史消息以避免超出限制: {msg_tokens} tokens")
                break

            trimmed_messages.insert(0, msg)
            current_tokens += msg_tokens

        logger.info(f"[Token管理] 历史消息裁剪: 原始{len(messages)}条 -> 保留{len(trimmed_messages)}条, 总tokens: {current_tokens}")
        return trimmed_messages

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

        # 获取场景支持的工具
        supported_skills = chatbi_config.get_scene_supported_skills(conversation.scene_code)

        # 构建系统提示
        if supported_skills:
            # 只使用场景支持的工具
            tool_names = ", ".join(supported_skills)
            logger.info(f"[场景工具过滤] 场景={conversation.scene_code}, 工具列表={tool_names}")
        else:
            # 使用所有工具（如果场景未指定或未找到）
            tool_names = ", ".join(self._tools.keys())
            logger.info(f"[场景工具过滤] 场景={conversation.scene_code}, 使用所有工具")

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

        # 估算各部分的token数
        system_prompt_tokens = self._estimate_tokens(system_prompt)
        current_user_tokens = self._estimate_tokens(message.content)

        # 计算工具消息的token数
        tool_messages_tokens = 0
        if tool_messages:
            tool_messages_tokens = sum(
                self._estimate_tokens(json.dumps(msg, ensure_ascii=False))
                for msg in tool_messages
            )

        # 估算最大token限制（根据模型类型设置）
        model = chatbi_config.llm_model

        # kimi-k2.5模型（禁用思考能力）
        if "kimi-k2.5" in model:
            max_input_tokens = 100000  # kimi-k2.5最大128k，预留28k给输出
        elif "128k" in model:
            max_input_tokens = 128000 - 4096  # moonshot-v1-128k: 128k tokens, 预留4k给输出
        elif "32k" in model:
            max_input_tokens = 32000 - 2048   # moonshot-v1-32k: 32k tokens, 预留2k给输出
        else:
            max_input_tokens = 8192 - 2048    # moonshot-v1-8k: 8192 tokens, 预留2k给输出

        logger.info(f"[Token管理] 系统提示: {system_prompt_tokens} tokens, 用户消息: {current_user_tokens} tokens, 工具消息: {tool_messages_tokens} tokens")

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # 添加历史消息（带token裁剪）
        history = conversation.get_history(max_messages=self.max_history_messages)
        trimmed_history = self._trim_history_by_tokens(
            history,
            max_input_tokens,
            system_prompt_tokens,
            current_user_tokens,
            tool_messages_tokens
        )
        messages.extend(trimmed_history)

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

    def _compress_tool_result(self, result: str, tool_name: str) -> str:
        """
        压缩工具结果（防止token爆炸）

        Args:
            result: 工具执行结果
            tool_name: 工具名称

        Returns:
            压缩后的结果
        """
        max_length = chatbi_config.agent_max_tool_result_length

        # 如果结果已经足够短，直接返回
        if len(result) <= max_length:
            return result

        # 对于不同的工具类型，使用不同的压缩策略
        if tool_name == "execute_python":
            # Python执行结果可能包含大量输出或base64编码
            # 尝试解析JSON，提取关键信息
            try:
                result_obj = json.loads(result)

                # 如果有文件信息，保留文件信息但截断其他内容
                if isinstance(result_obj, dict) and "files" in result_obj:
                    files_info = result_obj["files"]
                    compressed = json.dumps({
                        "success": result_obj.get("success"),
                        "output": result_obj.get("output", "")[:500],
                        "files": files_info,
                        "_truncated": True,
                        "_original_length": len(result)
                    }, ensure_ascii=False)
                    return compressed
            except (json.JSONDecodeError, TypeError):
                pass

            # 如果解析失败，简单截断
            return result[:max_length] + f"\n\n... [结果已截断，原长度: {len(result)} 字符]"

        elif tool_name == "read_file":
            # read_file 工具已经在工具内部做了截断
            return result

        else:
            # 其他工具，简单截断
            return result[:max_length] + f"\n\n... [结果已截断，原长度: {len(result)} 字符]"

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
                # 调用LLM（传递场景代码以过滤工具）
                response: LLMResponse = await self.llm_client.chat(
                    messages=messages,
                    tools=self._get_tool_definitions(conversation.scene_code)
                )
            except Exception as e:
                logger.error(f"[Agent Loop] LLM调用失败: {type(e).__name__}: {e}")
                raise

            # 如果有工具调用
            if response.tool_calls:
                logger.info(f"[Agent Loop] 检测到 {len(response.tool_calls)} 个工具调用，开始执行")

                # 发送工具调用事件
                await sse_manager.send_event(
                    conversation.conversation_id,
                    "tool_calling",
                    {
                        "iteration": iteration,
                        "tools": [tc.name for tc in response.tool_calls]
                    }
                )

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

                    # 压缩工具结果（防止token爆炸）
                    compressed_result = self._compress_tool_result(result, tool_call.name)

                    # 发送工具执行完成事件
                    await sse_manager.send_event(
                        conversation.conversation_id,
                        "tool_completed",
                        {
                            "iteration": iteration,
                            "tool": tool_call.name,
                            "success": "Error" not in compressed_result
                        }
                    )

                    # 添加工具结果消息
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": compressed_result
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

        logger.info(f"[_extract_files_from_tool_results] 开始提取文件，tool_messages数量: {len(tool_messages)}")

        for idx, msg in enumerate(tool_messages):
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                logger.info(f"[_extract_files_from_tool_results] 处理tool消息[{idx}]: {content[:200]}...")

                try:
                    # 解析工具结果（JSON格式）
                    import json
                    result = json.loads(content)
                    logger.info(f"[_extract_files_from_tool_results] 解析结果类型: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

                    # 检查是否有文件信息 - 支持多种格式
                    if isinstance(result, dict):
                        # 格式1: result.files
                        if "files" in result:
                            extracted_files = result["files"]
                            logger.info(f"[_extract_files_from_tool_results] 找到文件（格式1）: {len(extracted_files)} 个")
                            files.extend(extracted_files)
                        # 格式2: result.result.files
                        elif "result" in result and isinstance(result["result"], dict):
                            result_data = result["result"]
                            if "files" in result_data:
                                extracted_files = result_data["files"]
                                logger.info(f"[_extract_files_from_tool_results] 找到文件（格式2）: {len(extracted_files)} 个")
                                files.extend(result_data["files"])
                        else:
                            logger.info(f"[_extract_files_from_tool_results] 结果中未找到files字段")

                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(f"解析工具结果失败: {e}")

        logger.info(f"[_extract_files_from_tool_results] 提取完成，共找到 {len(files)} 个文件")
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
            self.memory_store.append_history(history_entry, level="session")
            logger.debug(f"[Memory] 更新history成功")

        except Exception as e:
            logger.error(f"[Memory] 更新memory失败: {e}", exc_info=True)

    async def _consolidate_memory(self, conversation: Conversation) -> None:
        """
        将旧消息整合到 MEMORY.md + HISTORY.md

        参考 nanobot 的记忆整合机制：
        - 当消息数超过 memory_window 时触发
        - 使用 LLM 将历史对话压缩为摘要
        - 保留最近 memory_window // 2 条消息不整合
        """
        if not chatbi_config.agent_consolidation_enabled:
            return

        memory_window = chatbi_config.agent_memory_window
        keep_count = memory_window // 2

        # 检查是否需要整合
        if len(conversation.messages) <= keep_count:
            logger.debug(f"[Memory整合] 会话消息数({len(conversation.messages)}) <= 保留数({keep_count})，无需整合")
            return

        # 计算待处理的消息数
        messages_to_process = len(conversation.messages) - conversation.last_consolidated
        if messages_to_process <= 0:
            logger.debug(f"[Memory整合] 无新消息需要整合 (last_consolidated={conversation.last_consolidated})")
            return

        # 提取待整合的消息（排除最近 keep_count 条）
        old_messages = conversation.messages[conversation.last_consolidated:-keep_count]
        if not old_messages:
            return

        logger.info(f"[Memory整合] 开始整合: 总消息数={len(conversation.messages)}, 待整合={len(old_messages)}, 保留={keep_count}")

        # 构建对话文本
        lines = []
        for msg in old_messages:
            if not msg.content:
                continue
            tools = f" [tools: {', '.join(msg.tools_used)}]" if msg.tools_used else ""
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M") if msg.timestamp else "?"
            lines.append(f"[{timestamp}] {msg.role.upper()}{tools}: {msg.content}")

        conversation_text = "\n".join(lines)

        # 获取当前memory
        current_memory = self.memory_store.read_long_term()

        # 构建整合提示词
        prompt = f"""You are a memory consolidation agent. Process this conversation and return a JSON object with exactly two keys:

1. "history_entry": A paragraph (2-5 sentences) summarizing the key events/decisions/topics. Start with a timestamp like [YYYY-MM-DD HH:MM]. Include enough detail to be useful when found by grep search later.

2. "memory_update": The updated session-level memory content. Add any new facts from this conversation. If nothing new, return the existing content unchanged.

## Current Memory (may include Global and Personal sections)
{current_memory or "(empty)"}

## Conversation to Process
{conversation_text}

Respond with ONLY valid JSON, no markdown fences."""

        try:
            # 调用 LLM 进行整合
            logger.info(f"[Memory LLM] 开始记忆整合, model={chatbi_config.llm_model}")
            response = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                tools=None,  # 不使用工具
            )

            if not response.content:
                logger.warning("[Memory整合] LLM 返回空响应")
                return

            # 解析响应
            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            # 使用 json_repair 解析（更宽容）
            import json_repair
            result = json_repair.loads(text)

            if not isinstance(result, dict):
                logger.warning(f"[Memory整合] 响应格式错误: {text[:200]}")
                return

            # 更新 history
            if entry := result.get("history_entry"):
                self.memory_store.append_history(entry, level="session")
                logger.info(f"[Memory整合] 已添加历史条目: {entry[:100]}...")

            # 更新长期记忆
            if update := result.get("memory_update"):
                if update != current_memory:
                    self.memory_store.write_long_term(update, level="session")
                    logger.info("[Memory整合] 已更新长期记忆")

            # 更新 last_consolidated 指针
            conversation.last_consolidated = len(conversation.messages) - keep_count
            logger.info(f"[Memory整合] 完成, last_consolidated={conversation.last_consolidated}")

        except Exception as e:
            logger.error(f"[Memory整合] 失败: {e}", exc_info=True)

    async def process(self, conversation: Conversation, message: Message) -> Optional[Dict[str, Any]]:
        """
        处理消息

        Args:
            conversation: 会话对象
            message: 当前消息

        Returns:
            处理结果字典
        """
        # 保存当前会话ID（用于SSE推送）
        self._current_conversation_id = conversation.conversation_id

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

        # 发送Agent开始处理事件
        await sse_manager.send_event(
            conversation.conversation_id,
            "agent_started",
            {
                "conversation_id": conversation.conversation_id,
                "scene": conversation.scene_name
            }
        )

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

                # 后台触发记忆整合（检查是否超过阈值）
                memory_window = chatbi_config.agent_memory_window
                if len(conversation.messages) > memory_window:
                    logger.info(f"[Memory整合] 消息数({len(conversation.messages)}) > 阈值({memory_window})，触发后台整合")
                    import asyncio
                    asyncio.create_task(self._consolidate_memory(conversation))

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
