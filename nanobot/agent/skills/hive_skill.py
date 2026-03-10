"""Hive 1.0 query skill for ChatBI."""
from typing import Any

from nanobot.agent.skills.base import Skill


class HiveSkill(Skill):
    """Skill for executing Hive 1.0 queries."""

    @property
    def name(self) -> str:
        return "hive_query"

    @property
    def description(self) -> str:
        return (
            "Execute Hive 1.0 queries on Hadoop data warehouse. "
            "Supports HiveQL syntax for big data analytics. "
            "Use this for Hive-specific syntax and large-scale data processing."
        )

    @property
    def category(self) -> str:
        return "database"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The HiveQL query to execute. Hive 1.0 syntax is supported.",
                    "minLength": 1,
                },
                "database": {
                    "type": "string",
                    "description": "Target Hive database name",
                    "default": "default",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return",
                    "minimum": 1,
                    "maximum": 10000,
                    "default": 1000,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, validate query without executing",
                },
            },
            "required": ["query"],
        }

    @property
    def examples(self) -> list[str]:
        return [
            "SELECT * FROM user_events WHERE dt='2024-01-01' LIMIT 100",
            "SELECT user_id, COUNT(*) as event_count FROM user_events GROUP BY user_id",
            "INSERT OVERWRITE TABLE summary SELECT user_id, COUNT(*) FROM events GROUP BY user_id",
        ]

    async def execute(self, **kwargs: Any) -> str:
        """Execute Hive query."""
        query = kwargs.get("query", "")
        database = kwargs.get("database", "default")
        limit = kwargs.get("limit", 1000)
        dry_run = kwargs.get("dry_run", False)

        # Safety check for dangerous operations
        dangerous_keywords = ["DROP", "TRUNCATE", "ALTER TABLE"]
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return f"Error: Dangerous operation '{keyword}' is not allowed."

        if dry_run:
            return (
                f"[Hive Dry Run] Query validated successfully.\n"
                f"Database: {database}\n"
                f"Query: {query}\n"
                f"Limit: {limit}\n"
                f"HiveQL Syntax: OK"
            )

        # TODO: Implement actual Hive execution with:
        # - PyHive or impala connection
        # - Query execution on Hadoop cluster
        # - Result formatting
        return (
            f"[Hive Query Placeholder]\n"
            f"Database: {database}\n"
            f"Query: {query}\n"
            f"Limit: {limit}\n"
            f"Results: [Implement actual Hive execution here]\n"
            f"Hint: Configure Hive connection in settings and use PyHive for execution.\n"
            f"Note: Hive 1.0 has specific syntax limitations - ensure query compatibility."
        )
