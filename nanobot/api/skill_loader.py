"""Skill loader for ChatBI."""
from nanobot.agent.skills.registry import SkillRegistry
from nanobot.agent.skills.mysql_skill import MySQLSkill
from nanobot.agent.skills.hive_skill import HiveSkill
from nanobot.agent.skills.knowledge_search_skill import KnowledgeSearchSkill
from nanobot.agent.skills.schema_search_skill import SchemaSearchSkill
from nanobot.agent.skills.qa_skill import QASkill
from nanobot.agent.skills.time_series_skill import TimeSeriesSkill


class SkillLoader:
    """Loader for all ChatBI skills."""

    _registry: SkillRegistry | None = None

    @classmethod
    def get_registry(cls) -> SkillRegistry:
        """Get or create skill registry."""
        if cls._registry is None:
            cls._registry = SkillRegistry()
            cls._load_skills()
        return cls._registry

    @classmethod
    def _load_skills(cls) -> None:
        """Load all skills."""
        skills = [
            MySQLSkill(),
            HiveSkill(),
            KnowledgeSearchSkill(),
            SchemaSearchSkill(),
            QASkill(),
            TimeSeriesSkill(),
        ]

        for skill in skills:
            cls._registry.register(skill)
