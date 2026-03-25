"""Token管理 - 估算和裁剪消息的token数量"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    估算文本的token数量（粗略估计）
    - 中文：1字符 ≈ 1.5 tokens
    - 英文：1字符 ≈ 0.3 tokens
    - 平均：1字符 ≈ 0.5 tokens
    """
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return max(1, int(chinese_chars * 1.5 + other_chars * 0.3))


def trim_history_by_tokens(
    messages: List[Dict[str, Any]],
    max_tokens: int,
    system_prompt_tokens: int,
    current_user_tokens: int,
    tool_messages_tokens: int
) -> List[Dict[str, Any]]:
    """
    根据token限制裁剪历史消息，保留最近的消息

    Args:
        messages: 历史消息列表
        max_tokens: 最大token限制
        system_prompt_tokens: 系统提示的token数
        current_user_tokens: 当前用户消息的token数
        tool_messages_tokens: 工具消息的token数

    Returns:
        裁剪后的消息列表
    """
    available_for_history = max_tokens - system_prompt_tokens - current_user_tokens - tool_messages_tokens

    trimmed_messages = []
    current_tokens = 0

    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg.get("content", ""))
        if current_tokens + msg_tokens > available_for_history:
            logger.warning(f"[Token管理] 跳过历史消息以避免超出限制: {msg_tokens} tokens")
            break
        trimmed_messages.insert(0, msg)
        current_tokens += msg_tokens

    logger.info(f"[Token管理] 历史消息裁剪: 原始{len(messages)}条 -> 保留{len(trimmed_messages)}条, 总tokens: {current_tokens}")
    return trimmed_messages
