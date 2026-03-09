"""Tool registry for managing and executing tools."""
from typing import Any

from nanobot.agent.tools.base import Tool


class ToolRegistry:
    """Registry for managing tools and executing them."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get all tools in OpenAI function calling format."""
        return [tool.to_openai_tool() for tool in self._tools.values()]

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """Execute a tool by name with given parameters."""
        tool = self.get(name)
        if tool is None:
            return f"Error: Tool '{name}' not found"

        # Validate parameters
        errors = tool.validate_params(params)
        if errors:
            return f"Invalid parameters: {'; '.join(errors)}"

        # Execute tool
        try:
            result = await tool.execute(**params)
            return result
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"
