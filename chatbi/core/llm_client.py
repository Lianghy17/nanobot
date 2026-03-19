"""OpenAI兼容的LLM客户端"""
from typing import Any, Dict, List, Optional
import json
import logging
import json_repair
import asyncio
from openai import AsyncOpenAI
from ..models.llm import LLMResponse, ToolCallRequest, UsageInfo

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI兼容的LLM客户端"""

    def __init__(
        self,
        api_base: str,
        api_key: str = "no-key",
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        thinking_disabled: bool = False
    ):
        """
        初始化LLM客户端

        Args:
            api_base: API基础URL
            api_key: API密钥
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            thinking_disabled: 是否禁用思考能力（kimi-k2.5专用）
        """
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.thinking_disabled = thinking_disabled

        # 创建OpenAI客户端
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=timeout
        )

        logger.info(f"LLM客户端初始化: api_base={api_base}, model={model}, thinking_disabled={thinking_disabled}")

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> LLMResponse:
        """
        调用LLM聊天接口（带重试机制）

        Args:
            messages: 消息列表
            tools: 工具定义列表
            temperature: 温度参数（可选，默认使用实例配置）
            max_tokens: 最大token数（可选，默认使用实例配置）
            model: 模型名称（可选，默认使用实例配置）

        Returns:
            LLMResponse: LLM响应对象
        """
        # 确定使用的模型和参数
        current_model = model or self.model
        current_temp = temperature if temperature is not None else self.temperature
        current_max_tokens = max(1, max_tokens or self.max_tokens)

        logger.info("=" * 80)
        logger.info("[LLM 请求]")
        logger.info(f"模型: {current_model}")
        logger.info(f"消息数: {len(messages)}")
        logger.info(f"工具数: {len(tools) if tools else 0}")
        logger.info(f"温度: {current_temp}")
        logger.info(f"最大Token: {current_max_tokens}")
        logger.info(f"最后一条消息: {messages[-1]['content'][:100]}...")

        # 打印完整消息列表（用于调试）
        for i, msg in enumerate(messages):
            logger.debug(f"  [{i}] role={msg['role']}, content={msg['content'][:80]}...")

        logger.info("=" * 80)

        # 构建OpenAI API参数
        kwargs: Dict[str, Any] = {
            "model": current_model,
            "messages": messages,
            "max_tokens": current_max_tokens,
            "temperature": current_temp,
        }

        # 如果有工具定义，添加到请求中
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # 对于kimi-k2.5，如果需要禁用思考能力，使用extra_body参数
        extra_body = {}
        if self.thinking_disabled and "kimi-k2.5" in current_model:
            extra_body["thinking"] = {"type": "disabled"}
            logger.info("[LLM 请求] 添加 thinking={disabled} 参数")

        # 如果有extra_body参数，添加到请求中
        if extra_body:
            kwargs["extra_body"] = extra_body

        # 重试机制
        max_retries = 3
        base_delay = 2  # 初始延迟2秒
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # 调用OpenAI API
                response = await self._client.chat.completions.create(**kwargs)

                # 解析响应
                return self._parse_response(response)

            except Exception as e:
                last_error = e
                error_str = str(e)

                # 判断是否需要重试的错误（429、5xx等）
                should_retry = False
                if "429" in error_str or "RateLimitError" in str(type(e)):
                    should_retry = True
                    logger.warning(f"[LLM 重试] 速率限制错误 (429)，第 {attempt + 1}/{max_retries + 1} 次尝试")
                elif "5" in error_str and "Error code:" in error_str:
                    # 5xx服务器错误
                    should_retry = True
                    logger.warning(f"[LLM 重试] 服务器错误 (5xx)，第 {attempt + 1}/{max_retries + 1} 次尝试")
                elif "overloaded" in error_str.lower() or "engine" in error_str.lower():
                    should_retry = True
                    logger.warning(f"[LLM 重试] 服务过载，第 {attempt + 1}/{max_retries + 1} 次尝试")

                # 如果不需要重试或已达最大重试次数，返回错误
                if not should_retry or attempt >= max_retries:
                    logger.error(f"LLM调用失败: {e}", exc_info=True)
                    return LLMResponse(
                        content=f"LLM调用失败: {str(e)}",
                        finish_reason="error",
                        metadata={"error": str(e), "retries": attempt}
                    )

                # 指数退避等待
                delay = base_delay * (2 ** attempt)
                logger.info(f"[LLM 重试] 等待 {delay} 秒后重试...")
                await asyncio.sleep(delay)

        # 如果所有重试都失败，返回最后一个错误
        logger.error(f"LLM调用失败（已重试 {max_retries} 次）: {last_error}", exc_info=True)
        return LLMResponse(
            content=f"LLM调用失败（已重试 {max_retries} 次）: {str(last_error)}",
            finish_reason="error",
            metadata={"error": str(last_error), "retries": max_retries}
        )

    def _parse_response(self, response: Any) -> LLMResponse:
        """
        解析OpenAI API响应

        Args:
            response: OpenAI API原始响应

        Returns:
            LLMResponse: 解析后的响应对象
        """
        choice = response.choices[0]
        msg = choice.message

        # 解析工具调用
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                # 解析工具参数
                arguments: Dict[str, Any] = {}
                if isinstance(tc.function.arguments, str):
                    try:
                        arguments = json_repair.loads(tc.function.arguments)
                    except Exception as e:
                        logger.warning(f"解析工具参数失败: {e}, 原始数据: {tc.function.arguments}")
                        arguments = {}
                else:
                    arguments = tc.function.arguments

                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments
                ))

        # 解析使用量信息
        usage_info = UsageInfo()
        if response.usage:
            usage_info = UsageInfo(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )

        # 获取推理内容（如果有）
        reasoning_content = getattr(msg, "reasoning_content", None)

        # 详细打印LLM响应
        logger.info("=" * 80)
        logger.info("[LLM 响应]")
        logger.info(f"响应ID: {response.id}")
        logger.info(f"模型: {response.model}")
        logger.info(f"完成原因: {choice.finish_reason}")

        # Token使用量
        if response.usage:
            logger.info(f"Token使用: prompt={response.usage.prompt_tokens}, "
                       f"completion={response.usage.completion_tokens}, "
                       f"total={response.usage.total_tokens}")

        # 响应内容
        if msg.content:
            logger.info(f"响应内容: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")
        else:
            logger.info("响应内容: (空)")

        # 推理内容
        if reasoning_content:
            logger.info(f"推理内容: {reasoning_content[:200]}{'...' if len(reasoning_content) > 200 else ''}")

        # 工具调用
        if tool_calls:
            logger.info(f"工具调用数: {len(tool_calls)}")
            for i, tc in enumerate(tool_calls, 1):
                logger.info(f"  [{i}] 工具: {tc.name}")
                logger.info(f"      ID: {tc.id}")
                logger.info(f"      参数: {json.dumps(tc.arguments, ensure_ascii=False)}")
        else:
            logger.info("工具调用: (无)")

        logger.info("=" * 80)

        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage_info,
            reasoning_content=reasoning_content,
            metadata={"model": response.model, "id": response.id}
        )
