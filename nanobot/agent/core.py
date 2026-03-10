"""Core Agent implementation for LLM interaction."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from nanobot.agent.skills.registry import SkillRegistry
from nanobot.session.manager import Session
from nanobot.scene.config import SceneConfig


class Agent:
    """AI Agent with skill support and session management."""

    def __init__(
        self,
        skill_registry: SkillRegistry,
        model: str = "gpt-4",
        api_key: str = "",
        base_url: str | None = None,
    ) -> None:
        self.skill_registry = skill_registry
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def process_message(
        self,
        session: Session,
        user_message: str,
        scene: SceneConfig,
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
        yield {"type": "thinking", "content": "思考中..."}

        try:
            # Build messages for LLM
            messages = self._build_messages(session, scene)

            # Get enabled skills for this scene
            enabled_tools = self._get_enabled_tools(scene)

            # Call LLM with function calling
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=enabled_tools,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            # Handle tool calls
            if assistant_message.tool_calls:
                # Add assistant message to history
                session.add_message("assistant", assistant_message.content or "")
                
                for tool_call in assistant_message.tool_calls:
                    # Check if session was paused during processing
                    await session.wait_if_paused()

                    function_name = tool_call.function.name
                    function_args = eval(tool_call.function.arguments)

                    yield {
                        "type": "tool_call",
                        "name": function_name,
                        "params": function_args,
                    }

                    # Execute skill
                    result = await self.skill_registry.execute(
                        function_name, function_args
                    )

                    yield {
                        "type": "tool_result",
                        "name": function_name,
                        "result": result,
                    }

                    # Add tool result to session
                    session.add_message(
                        "tool",
                        result,
                        tool_call_id=tool_call.id,
                        tool_name=function_name,
                    )

                # Get final response after tool calls
                messages = self._build_messages(session, scene)
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=enabled_tools,
                    tool_choice="auto",
                )

                final_message = final_response.choices[0].message
                content = final_message.content or ""
                session.add_message("assistant", content)
                yield {"type": "content", "content": content}
            else:
                # No tool calls, direct response
                content = assistant_message.content or ""
                session.add_message("assistant", content)
                yield {"type": "content", "content": content}

            yield {"type": "done"}

        except Exception as e:
            error_msg = f"处理消息时出错: {str(e)}"
            yield {"type": "error", "message": error_msg}
            yield {"type": "done"}

    def _build_messages(self, session: Session, scene: SceneConfig) -> list[dict[str, Any]]:
        """Build messages list for LLM."""
        messages = [{"role": "system", "content": scene.system_prompt}]

        # Add conversation history
        for msg in session.messages:
            role = msg["role"]
            content = msg["content"]

            if role == "tool":
                messages.append({
                    "role": "tool",
                    "content": content,
                    "tool_call_id": msg.get("tool_call_id"),
                })
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})
            else:
                messages.append({"role": role, "content": content})

        return messages

    def _get_enabled_tools(self, scene: SceneConfig) -> list[dict[str, Any]]:
        """Get enabled tools for the scene."""
        all_tools = self.skill_registry.get_openai_tools()
        enabled_skill_names = set(scene.enabled_skills)
        
        return [
            tool for tool in all_tools
            if tool["function"]["name"] in enabled_skill_names
        ]
