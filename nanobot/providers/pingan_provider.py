"""Pingan local service provider — calls local API endpoint."""

from __future__ import annotations

from typing import Any
import aiohttp
import json

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class PinganProvider(LLMProvider):
    """
    Provider that calls local Pingan service.
    
    This is used when the model name contains "pingan",
    routing requests to a local HTTP endpoint.
    """

    def __init__(
        self,
        api_key: str = "no-key",
        api_base: str = "http://localhost:8000/v1",
        default_model: str = "pingan"
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self._api_base = api_base

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request to local Pingan service.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions.
            model: Model identifier (ignored for pingan, uses local service).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content and/or tool calls.
        """
        url = f"{self._api_base}/chat/completions"

        # Prepare request payload (OpenAI-compatible format)
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max(1, max_tokens),
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
        }

        # Add authorization header if api_key is set
        if self.api_key and self.api_key != "no-key":
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return LLMResponse(
                            content=f"Error: HTTP {response.status} - {error_text}",
                            finish_reason="error",
                        )

                    data = await response.json()
                    return self._parse_response(data)

        except aiohttp.ClientError as e:
            return LLMResponse(
                content=f"Error connecting to Pingan service: {str(e)}",
                finish_reason="error",
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                finish_reason="error",
            )

    def _parse_response(self, response: dict[str, Any]) -> LLMResponse:
        """Parse local service response into our standard format."""
        try:
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})

            # Parse tool calls if present
            tool_calls = []
            if "tool_calls" in message and message["tool_calls"]:
                for tc in message["tool_calls"]:
                    args = tc.get("function", {}).get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            pass

                    tool_calls.append(
                        ToolCallRequest(
                            id=tc.get("id", ""),
                            name=tc.get("function", {}).get("name", ""),
                            arguments=args,
                        )
                    )

            # Parse usage
            usage = response.get("usage", {})
            usage_dict = {}
            if usage:
                usage_dict = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

            # Parse reasoning content (if supported)
            reasoning_content = message.get("reasoning_content", None)

            return LLMResponse(
                content=message.get("content"),
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", "stop"),
                usage=usage_dict,
                reasoning_content=reasoning_content,
            )

        except (KeyError, IndexError, TypeError) as e:
            return LLMResponse(
                content=f"Error parsing response: {str(e)}\nRaw response: {response}",
                finish_reason="error",
            )

    def get_default_model(self) -> str:
        """Get default model for Pingan provider."""
        return self.default_model
