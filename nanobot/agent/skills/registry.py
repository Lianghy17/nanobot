"""Skill registry for managing and executing skills."""
from typing import Any

from nanobot.agent.skills.base import Skill


class SkillRegistry:
    """Registry for managing skills and executing them."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill instance."""
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> bool:
        """Unregister a skill by name."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def get_skills_by_category(self, category: str) -> list[Skill]:
        """Get all skills in a category."""
        return [skill for skill in self._skills.values() if skill.category == category]

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get all skills in OpenAI function calling format."""
        return [skill.to_openai_tool() for skill in self._skills.values()]

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """Execute a skill by name with given parameters."""
        skill = self.get(name)
        if skill is None:
            return f"Error: Skill '{name}' not found"

        # Validate parameters
        errors = skill.validate_params(params)
        if errors:
            return f"Invalid parameters: {'; '.join(errors)}"

        # Execute skill
        try:
            result = await skill.execute(**params)
            return result
        except Exception as e:
            return f"Error executing skill '{name}': {str(e)}"
