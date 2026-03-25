"""记忆管理器 - 会话记忆的更新与整合"""
import json
import json_repair
import logging
from typing import List
from datetime import datetime
from ..config import chatbi_config
from ..models import Conversation, Message
from .llm_client import LLMClient
from .memory import MemoryStore
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 负责memory的更新和整合"""

    def __init__(self, llm_client: LLMClient, workspace_path: str):
        self.llm_client = llm_client
        self.workspace_path = workspace_path
        self.memory_store: MemoryStore = None

    def init_session_memory(self, conversation_id: str = None):
        """初始化会话级别的memory store"""
        memory_key = f"conv:{conversation_id}" if conversation_id else None
        self.memory_store = MemoryStore(Path(self.workspace_path), memory_key=memory_key)

    def get_memory_context(self) -> str:
        """获取当前memory上下文"""
        if self.memory_store:
            return self.memory_store.get_memory_context()
        return ""

    def update_memory(self, conversation: Conversation, message: Message, response_content: str, tools_used: List[str]) -> None:
        """更新memory信息"""
        if not chatbi_config.memory_enabled or not self.memory_store:
            return

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history_entry = f"""## {timestamp}
User: {message.content}
Assistant: {response_content[:200]}{'...' if len(response_content) > 200 else ''}
Tools: {', '.join(tools_used) if tools_used else 'None'}
Scene: {conversation.scene_name}
"""
            self.memory_store.append_history(history_entry, level="session")
            logger.debug("[Memory] 更新history成功")
        except Exception as e:
            logger.error(f"[Memory] 更新memory失败: {e}", exc_info=True)

    async def consolidate_memory(self, conversation: Conversation) -> None:
        """
        将旧消息整合到 MEMORY.md + HISTORY.md

        - 当消息数超过 memory_window 时触发
        - 使用 LLM 将历史对话压缩为摘要
        - 保留最近 memory_window // 2 条消息不整合
        """
        if not chatbi_config.agent_consolidation_enabled or not self.memory_store:
            return

        memory_window = chatbi_config.agent_memory_window
        keep_count = memory_window // 2

        if len(conversation.messages) <= keep_count:
            logger.debug(f"[Memory整合] 消息数({len(conversation.messages)}) <= 保留数({keep_count})，无需整合")
            return

        messages_to_process = len(conversation.messages) - conversation.last_consolidated
        if messages_to_process <= 0:
            logger.debug(f"[Memory整合] 无新消息需要整合 (last_consolidated={conversation.last_consolidated})")
            return

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
        current_memory = self.memory_store.read_long_term()

        # 加载 prompt 模板
        try:
            prompts_dir = Path(chatbi_config.config_dir) / "prompts"
            system_prompt = (prompts_dir / "memory_consolidation_system.md").read_text(encoding="utf-8")
            user_template = (prompts_dir / "memory_consolidation_user.md").read_text(encoding="utf-8")
            prompt = user_template.format(current_memory=current_memory or "(empty)", conversation_text=conversation_text)
        except FileNotFoundError:
            logger.warning("[Memory整合] prompt文件未找到，使用内置prompt")
            system_prompt = "You are a memory consolidation agent. Respond only with valid JSON."
            prompt = f"""Process this conversation and return JSON with keys: "history_entry" (summary paragraph), "memory_update" (updated memory).

Current Memory:
{current_memory or "(empty)"}

Conversation:
{conversation_text}"""

        try:
            logger.info(f"[Memory LLM] 开始记忆整合, model={chatbi_config.llm_model}")
            response = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                tools=None,
            )

            if not response.content:
                logger.warning("[Memory整合] LLM 返回空响应")
                return

            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json_repair.loads(text)

            if not isinstance(result, dict):
                logger.warning(f"[Memory整合] 响应格式错误: {text[:200]}")
                return

            if entry := result.get("history_entry"):
                self.memory_store.append_history(entry, level="session")
                logger.info(f"[Memory整合] 已添加历史条目: {entry[:100]}...")

            if update := result.get("memory_update"):
                if update != current_memory:
                    self.memory_store.write_long_term(update, level="session")
                    logger.info("[Memory整合] 已更新长期记忆")

            conversation.last_consolidated = len(conversation.messages) - keep_count
            logger.info(f"[Memory整合] 完成, last_consolidated={conversation.last_consolidated}")

        except Exception as e:
            logger.error(f"[Memory整合] 失败: {e}", exc_info=True)
