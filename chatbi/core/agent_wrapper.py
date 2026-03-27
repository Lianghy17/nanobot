"""Agent包装器 - 核心入口，协调各模块完成消息处理"""
import os
import json
import asyncio
import logging
import re
from typing import Dict, Any, Optional, List, Callable, Awaitable
from ..config import chatbi_config
from ..models import Conversation, Message
from ..models.llm import LLMResponse, ToolCallRequest
from .conversation_manager import ConversationManager
from .llm_client import LLMClient
from .sse_manager import sse_manager
from .template_loader import SceneTemplateLoader
from .intent_analyzer import IntentAnalyzer
from .token_manager import estimate_tokens, trim_history_by_tokens
from .tool_executor import ToolExecutor
from .memory_manager import MemoryManager
from .pattern_handler import PatternHandler
from .sql_builder import PatternSQLBuilder
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskCancelledException(Exception):
    """任务被取消的异常"""
    pass


class AgentWrapper:
    """Agent包装器 - 核心入口，协调各子模块"""

    _instance: Optional["AgentWrapper"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._current_conversation_id = None

        # LLM 客户端
        self.llm_client = LLMClient(
            api_base=chatbi_config.llm_api_base,
            api_key=chatbi_config.llm_api_key,
            model=chatbi_config.llm_model,
            temperature=chatbi_config.llm_temperature,
            max_tokens=chatbi_config.llm_max_tokens,
            timeout=chatbi_config.llm_timeout,
            thinking_disabled=chatbi_config.llm_thinking_disabled
        )

        # Agent 配置
        self.max_iterations = chatbi_config.agent_max_iterations
        self.max_history_messages = chatbi_config.agent_max_history_messages

        # 子模块
        self.conversation_manager = ConversationManager()
        self.tool_executor = ToolExecutor()
        self.memory_manager = MemoryManager(self.llm_client, chatbi_config.workspace_path)

        # Pattern 相关组件（使用TemplateLoader）
        if chatbi_config.pattern_enabled:
            try:
                logger.info(f"[Agent初始化] 开始加载Template组件")
                import os
                from pathlib import Path

                # 正确构建场景配置路径
                scenes_config_path = os.path.join(chatbi_config.config_dir, "scenes.json")
                logger.info(f"[Agent初始化] 场景配置路径: {scenes_config_path}")

                # 验证文件是否存在
                if not os.path.exists(scenes_config_path):
                    logger.error(f"[Agent初始化] 场景配置文件不存在: {scenes_config_path}")
                    self._init_pattern_none()
                    return

                self.template_loader = SceneTemplateLoader(scenes_config_path)
                logger.info(f"[Agent初始化] SceneTemplateLoader加载成功, 模板数: {len(self.template_loader.get_all_templates())}")
                self.intent_analyzer = IntentAnalyzer(self.llm_client, self.template_loader)
                logger.info("[Agent初始化] IntentAnalyzer加载成功")
                sql_builder = PatternSQLBuilder(self.template_loader)
                logger.info("[Agent初始化] PatternSQLBuilder加载成功")
                self.pattern_handler = PatternHandler(self.template_loader, sql_builder)
                logger.info("[Agent初始化] Pattern组件加载成功")
            except Exception as e:
                logger.error(f"[Agent初始化] Pattern组件加载失败: {e}", exc_info=True)
                self._init_pattern_none()
        else:
            logger.info("[Agent初始化] Pattern功能已禁用")
            self._init_pattern_none()

    def _init_pattern_none(self):
        """Pattern组件初始化失败时的空值设置"""
        self.template_loader = None
        self.intent_analyzer = None
        self.pattern_handler = None

    # ========== 消息构建 ==========

    async def _get_files_context(self, conversation_id: str) -> str:
        """获取沙箱中的可用文件列表"""
        try:
            from .sandbox_manager import SandboxManager
            sandbox_manager = SandboxManager()
            session = sandbox_manager._sandboxes.get(conversation_id)

            if not session or not session.sandbox:
                return ""

            files = await session.sandbox.list_files()
            if not files:
                return ""

            files_info = [f"- {f['filename']} ({f['size']} bytes, {f['type']})" for f in files]

            return f"""## 可用文件

沙箱工作目录中有以下文件可用（位于当前工作目录）：

{chr(10).join(files_info)}

**注意**：
|- 使用 `read_file` 工具读取文件内容时，只需提供文件名（如 "daily_sales.csv"）
|- 使用 `execute_python` 时，可以直接读取文件（如 `pd.read_csv('daily_sales.csv')`）
|- 所有文件都位于当前工作目录中，无需使用路径前缀
"""
        except Exception as e:
            logger.warning(f"[文件上下文] 获取文件列表失败: {e}")
            return ""

    async def _build_messages(
        self,
        conversation: Conversation,
        message: Message,
        tool_messages: Optional[List[Dict[str, Any]]] = None,
        run_mode: str = "react"
    ) -> List[Dict[str, Any]]:
        """构建发送给LLM的消息列表"""
        memory_context = self.memory_manager.get_memory_context()
        tool_names = self.tool_executor.get_tool_names(conversation.scene_code, run_mode=run_mode)
        files_context = await self._get_files_context(conversation.conversation_id)

        run_mode_name = "模板模式（Template Mode）" if run_mode == "template" else "React模式（Flex Mode）"

        system_prompt = chatbi_config.agent_system_prompt_template.format(
            scene_name=conversation.scene_name,
            scene_code=conversation.scene_code,
            tool_names=tool_names,
            current_time=chatbi_config.current_time,
            runtime_environment=chatbi_config.runtime_environment,
            run_mode=run_mode_name
        )

        if files_context:
            system_prompt = f"{system_prompt}\n\n{files_context}"
        if memory_context:
            system_prompt = f"{system_prompt}\n\n{memory_context}"

        # Token 估算与裁剪
        system_prompt_tokens = estimate_tokens(system_prompt)
        current_user_tokens = estimate_tokens(message.content)

        tool_messages_tokens = 0
        if tool_messages:
            tool_messages_tokens = sum(
                estimate_tokens(json.dumps(msg, ensure_ascii=False))
                for msg in tool_messages
            )

        max_input_tokens = self._get_max_input_tokens()

        logger.info(f"[Token管理] 系统提示: {system_prompt_tokens}, 用户: {current_user_tokens}, 工具: {tool_messages_tokens}")

        messages = [{"role": "system", "content": system_prompt}]

        history = conversation.get_history(max_messages=self.max_history_messages)
        trimmed_history = trim_history_by_tokens(
            history, max_input_tokens, system_prompt_tokens, current_user_tokens, tool_messages_tokens
        )
        messages.extend(trimmed_history)
        messages.append({"role": "user", "content": message.content})

        if tool_messages:
            messages.extend(tool_messages)

        return messages

    def _get_max_input_tokens(self) -> int:
        """根据模型类型计算最大输入token数"""
        model = chatbi_config.llm_model
        if "kimi-k2.5" in model:
            return 100000
        elif "128k" in model:
            return 128000 - 4096
        elif "32k" in model:
            return 32000 - 2048
        else:
            return 8192 - 2048

    # ========== Agent Loop ==========

    async def _run_agent_loop(
        self,
        conversation: Conversation,
        message: Message,
        on_progress: Optional[Callable[[str], Awaitable[None]]] = None,
        run_mode: str = "react"
    ) -> tuple[Optional[str], List[str], List[Dict[str, Any]]]:
        """运行Agent迭代循环"""
        iteration = 0
        final_content = None
        tools_used: List[str] = []
        tool_messages: List[Dict[str, Any]] = []

        logger.info("=" * 80)
        logger.info(f"[Agent Loop 开始] 场景={conversation.scene_name}, 用户消息={message.content}")
        logger.info(f"[Agent Loop 开始] 最大迭代={self.max_iterations}")
        logger.info("=" * 80)

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"[Agent Loop 迭代 {iteration}/{self.max_iterations}]")

            if sse_manager.is_cancelled(message.id):
                raise TaskCancelledException("任务已被用户取消")

            messages = await self._build_messages(conversation, message, tool_messages or None, run_mode=run_mode)

            try:
                response: LLMResponse = await self.llm_client.chat(
                    messages=messages,
                    tools=self.tool_executor.get_tool_definitions(conversation.scene_code, run_mode=run_mode)
                )
            except Exception as e:
                logger.error(f"[Agent Loop] LLM调用失败: {type(e).__name__}: {e}")
                raise

            if response.tool_calls:
                logger.info(f"[Agent Loop] 检测到 {len(response.tool_calls)} 个工具调用")

                await sse_manager.send_event(
                    conversation.conversation_id,
                    "tool_calling",
                    {"iteration": iteration, "tools": [tc.name for tc in response.tool_calls]}
                )

                if on_progress:
                    clean_content = self._strip_think(response.content)
                    await on_progress(clean_content or self._tool_hint(response.tool_calls))

                # 构建 assistant 消息
                assistant_message = {"role": "assistant", "content": response.content}
                if response.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}
                        }
                        for tc in response.tool_calls
                    ]
                tool_messages.append(assistant_message)

                # 执行工具
                for tool_call in response.tool_calls:
                    if sse_manager.is_cancelled(message.id):
                        raise TaskCancelledException("任务已被用户取消")

                    tools_used.append(tool_call.name)
                    result = await self.tool_executor.execute_tool(tool_call.name, tool_call.arguments)
                    compressed_result = self.tool_executor.compress_tool_result(result, tool_call.name)

                    await sse_manager.send_event(
                        conversation.conversation_id,
                        "tool_completed",
                        {"iteration": iteration, "tool": tool_call.name, "success": "Error" not in compressed_result}
                    )

                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": compressed_result
                    })
            else:
                logger.info("[Agent Loop] 没有工具调用，结束循环")
                final_content = self._strip_think(response.content)
                break

        logger.info(f"[Agent Loop 结束] 迭代: {iteration}, 工具: {tools_used}")
        return final_content, tools_used, tool_messages

    # ========== 主处理入口 ==========

    async def process(self, conversation: Conversation, message: Message) -> Optional[Dict[str, Any]]:
        """处理消息 - 主入口"""
        self._current_conversation_id = conversation.conversation_id

        pid = os.getpid()
        print(f"\n{'='*80}")
        print(f"[PID:{pid}] [终端输出] Agent处理开始: {conversation.conversation_id}")
        print(f"[PID:{pid}] 用户消息: {message.content}")
        print(f"{'='*80}\n")

        logger.info(f"[PID:{pid}] " + "=" * 80)
        logger.info(f"[PID:{pid}] [Agent 处理开始] 场景: {conversation.scene_name} ({conversation.scene_code})")
        logger.info(f"[PID:{pid}] 用户消息: {message.content}")
        logger.info(f"[PID:{pid}] " + "=" * 80)

        await sse_manager.send_event(
            conversation.conversation_id, "agent_started",
            {"conversation_id": conversation.conversation_id, "scene": conversation.scene_name}
        )

        # 设置工具和 memory 上下文
        self.tool_executor.set_tool_context(conversation.user_channel, conversation.conversation_id)
        self.memory_manager.init_session_memory(conversation.conversation_id)

        try:
            result = await self._dispatch(conversation, message)
            if result and chatbi_config.memory_enabled:
                self.memory_manager.update_memory(
                    conversation, message,
                    result.get("content", ""), result.get("tools_used", [])
                )
                if len(conversation.messages) > chatbi_config.agent_memory_window:
                    asyncio.create_task(self.memory_manager.consolidate_memory(conversation))
            return result

        except TaskCancelledException:
            logger.info(f"[Agent] 任务被取消: {message.id}")
            return {"content": "任务已被取消", "tools_used": [], "metadata": {"cancelled": True}}

        except Exception as e:
            logger.error(f"[Agent 处理失败] {e}", exc_info=True)
            return {"content": f"处理失败：{str(e)}", "tools_used": [], "metadata": {"error": True}}

    async def _dispatch(self, conversation: Conversation, message: Message) -> Optional[Dict[str, Any]]:
        """分发消息到Pattern模式或React模式"""
        # 检查是否降级到React模式
        if message.metadata and message.metadata.get("fallback_to_react"):
            logger.info("[降级模式] 用户选择降级到React模式")
            return await self._process_react(conversation, message)

        # 检查是否首次选择模板
        if self._is_template_selection(message):
            if not self.pattern_handler:
                logger.warning("[Pattern模式] Pattern组件未初始化，无法处理模板选择")
                return {"content": "模板功能暂时不可用，请稍后再试或使用普通对话模式。", "tools_used": [], "metadata": {"error": True}}
            template_data = message.metadata.get("template_data", {})
            return await self.pattern_handler.guide_template_params(conversation, message, template_data)

        # 检查是否续接Pattern模式
        should_continue_pattern, pattern_context = self._check_pattern_continuation(conversation, message)

        # 意图分析
        if self.intent_analyzer and chatbi_config.pattern_enabled:
            logger.info("[意图分析] 开始分析用户意图...")

            context = {"conversation_id": conversation.conversation_id}
            if should_continue_pattern:
                context["continuing_pattern"] = True
                context["pattern_context"] = pattern_context

            intent_result = await self.intent_analyzer.analyze(
                message.content, conversation.scene_code, context=context
            )

            await sse_manager.send_event(
                conversation.conversation_id, "intent_analyzed",
                {
                    "intent_type": intent_result.intent_type,
                    "matched_template": intent_result.matched_template,
                    "confidence": intent_result.confidence,
                    "mode": "template" if intent_result.intent_type == "template_match" else "react"
                }
            )

            # 匹配到 Template
            if (intent_result.intent_type == "template_match"
                and intent_result.matched_template
                and intent_result.template_config
                and intent_result.confidence >= chatbi_config.pattern_match_threshold):

                logger.info(f"[Template模式] 匹配到Template: {intent_result.matched_template}")
                return await self.pattern_handler.process_with_pattern(conversation, message, intent_result)

            # 需要澄清
            if intent_result.clarification_needed:
                logger.info(f"[Pattern模式] 需要澄清: {intent_result.clarification_questions}")
                return self.pattern_handler.build_clarification_from_intent(intent_result)

        # React 模式
        logger.info("[React模式] 使用React模式处理")
        return await self._process_react(conversation, message)

    async def _process_react(self, conversation: Conversation, message: Message) -> Dict[str, Any]:
        """React模式处理"""
        final_content, tools_used, tool_messages = await self._run_agent_loop(conversation, message, run_mode="react")

        generated_files = self.tool_executor.extract_files_from_tool_results(tool_messages)

        if final_content is None:
            final_content = "处理完成，但没有可用的响应内容。"

        logger.info(f"[React模式完成] 工具: {tools_used}, 文件: {len(generated_files)}")

        return {
            "content": final_content,
            "tools_used": tools_used,
            "tool_calls": [],
            "metadata": {"files": generated_files, "format": "markdown", "mode": "react"}
        }

    # ========== 辅助方法 ==========

    def _is_template_selection(self, message: Message) -> bool:
        """检查消息是否为首次模板选择"""
        return bool(
            message.metadata
            and message.metadata.get("template_mode")
            and message.metadata.get("template_data")
            and not message.metadata.get("continuing_pattern")
        )

    def _check_pattern_continuation(
        self, conversation: Conversation, message: Message
    ) -> tuple[bool, dict]:
        """检查是否应续接Pattern模式"""
        # 获取上一条 assistant 消息的 metadata（包含正确的 pattern_id）
        last_assistant_metadata = {}
        for msg in reversed(conversation.messages):
            if msg.role == "assistant" and msg.metadata:
                if msg.metadata.get("pattern_mode") or msg.metadata.get("template_mode"):
                    last_assistant_metadata = msg.metadata
                    break
                break

        # 检查当前消息 metadata
        if message.metadata:
            if message.metadata.get("continuing_pattern") or message.metadata.get("template_mode"):
                logger.info(f"[Pattern续接] 当前消息标记为继续Pattern模式")
                # 合并 metadata：优先使用上一条 assistant 消息中的 pattern_id
                merged_metadata = {**message.metadata}
                if last_assistant_metadata:
                    # 上一条消息中有正确的 pattern_id
                    if last_assistant_metadata.get("pattern_id"):
                        merged_metadata["pattern_id"] = last_assistant_metadata["pattern_id"]
                    # 保留上一条消息中的参数
                    if last_assistant_metadata.get("params"):
                        merged_metadata["previous_params"] = last_assistant_metadata["params"]
                    logger.info(f"[Pattern续接] 合并metadata，pattern_id={merged_metadata.get('pattern_id')}")
                return True, merged_metadata

        # 检查上一条 assistant 消息（当前消息没有标记时）
        if last_assistant_metadata:
            logger.info(f"[Pattern续接] 检测到上一条消息处于Pattern模式")
            return True, last_assistant_metadata

        return False, {}

    @staticmethod
    def _strip_think(text: Optional[str]) -> Optional[str]:
        """移除思考块"""
        if not text:
            return None
        return re.sub(r"理智[\s\S]*?理", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: List[ToolCallRequest]) -> str:
        """格式化工具调用提示"""
        def _fmt(tc: ToolCallRequest) -> str:
            val = next(iter(tc.arguments.values()), None) if tc.arguments else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'
        return ", ".join(_fmt(tc) for tc in tool_calls)
