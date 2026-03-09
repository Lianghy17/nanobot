"""Core Agent implementation for LLM interaction."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from nanobot.agent.tools.registry import ToolRegistry
from nanobot.session.manager import Session, SessionState


class Agent:
    """AI Agent with tool support and session management."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        model: str = "gpt-4",
        system_prompt: str | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.model = model
        self.system_prompt = system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt for the agent."""
        return """You are a helpful AI assistant with access to various tools.
You can use the following tools to help users:
- rag_search: Search and retrieve information from the knowledge base
- sql_execute: Execute SQL queries on databases
- time_series_forecast: Perform time series analysis and forecasting

Always think carefully about which tool to use and validate parameters before calling.
Provide clear and helpful responses to users."""

    async def process_message(
        self,
        session: Session,
        user_message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a user message and yield response chunks.

        This generator yields events:
        - {"type": "thinking", "content": "..."}
        - {"type": "tool_call", "name": "...", "params": {...}}
        - {"type": "tool_result", "name": "...", "result": "..."}
        - {"type": "content", "content": "..."}
        - {"type": "done"}
        """
        # Check if session is paused
        await session.wait_if_paused()

        # Add user message to session
        session.add_message("user", user_message)

        # Yield thinking status
        yield {"type": "thinking", "content": "Processing your message..."}

        # Simulate LLM processing (TODO: integrate actual LLM)
        await asyncio.sleep(0.1)

        # Check for tool calls in the message (simplified demo)
        tool_calls = self._extract_tool_calls(user_message)

        if tool_calls:
            for tool_call in tool_calls:
                # Check if session was paused during processing
                await session.wait_if_paused()

                yield {
                    "type": "tool_call",
                    "name": tool_call["name"],
                    "params": tool_call["params"],
                }

                # Execute tool
                result = await self.tool_registry.execute(
                    tool_call["name"], tool_call["params"]
                )

                yield {
                    "type": "tool_result",
                    "name": tool_call["name"],
                    "result": result,
                }

        # Generate response (placeholder)
        response = await self._generate_response(session, tool_calls)

        # Add assistant message to session
        session.add_message("assistant", response)

        yield {"type": "content", "content": response}
        yield {"type": "done"}

    def _extract_tool_calls(self, message: str) -> list[dict[str, Any]]:
        """Extract tool calls from message (simplified demo).

        TODO: Replace with actual LLM function calling.
        """
        # Simple keyword detection for demo
        tool_calls = []

        if "search" in message.lower() or "rag" in message.lower():
            tool_calls.append({
                "name": "rag_search",
                "params": {"query": message, "top_k": 5},
            })

        if "sql" in message.lower() or "query" in message.lower():
            tool_calls.append({
                "name": "sql_execute",
                "params": {"query": "SELECT * FROM users LIMIT 10", "database": "main"},
            })

        if "forecast" in message.lower() or "predict" in message.lower():
            tool_calls.append({
                "name": "time_series_forecast",
                "params": {
                    "data_source": "sales_data",
                    "model": "prophet",
                    "forecast_periods": 7,
                },
            })

        return tool_calls

    async def _generate_response(
        self, session: Session, tool_calls: list[dict[str, Any]]
    ) -> str:
        """Generate response based on session context and tool results.

        TODO: Integrate actual LLM API call.
        """
        history = session.get_history(max_messages=10)
        context = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in history[-5:]
        )

        if tool_calls:
            tool_names = [tc["name"] for tc in tool_calls]
            return (
                f"Based on your request, I used the following tools: {', '.join(tool_names)}.\n"
                f"[Demo Mode] Full LLM integration pending. Context:\n{context[-200:]}"
            )

        return (
            f"[Demo Mode] Received your message. Here's the context:\n{context[-200:]}\n\n"
            f"Full LLM integration pending. This is a placeholder response."
        )
