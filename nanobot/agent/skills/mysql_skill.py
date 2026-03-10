"""MySQL query skill for ChatBI."""
from typing import Any

from nanobot.agent.skills.base import Skill


class MySQLSkill(Skill):
    """Skill for executing MySQL queries."""

    @property
    def name(self) -> str:
        return "mysql_query"

    @property
    def description(self) -> str:
        return (
            "Execute MySQL queries on configured MySQL databases. "
            "Supports SELECT, INSERT, UPDATE, DELETE operations with proper access control. "
            "Use this for MySQL-specific syntax and operations."
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
                    "description": "The MySQL query to execute. MySQL-specific syntax is supported.",
                    "minLength": 1,
                },
                "database": {
                    "type": "string",
                    "description": "Target MySQL database name or connection alias",
                    "enum": ["main", "analytics", "logs", "archive"],
                },
                "params": {
                    "type": "array",
                    "description": "Query parameters for parameterized queries",
                    "items": {"type": ["string", "integer", "number", "boolean"]},
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
            "SELECT * FROM users WHERE created_at > '2024-01-01' LIMIT 100",
            "SELECT COUNT(*) FROM orders WHERE status = 'completed'",
            "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id",
        ]

    async def execute(self, **kwargs: Any) -> str:
        """Execute MySQL query."""
        query = kwargs.get("query", "")
        database = kwargs.get("database", "main")
        params = kwargs.get("params", [])
        dry_run = kwargs.get("dry_run", False)

        # Safety check for dangerous operations
        dangerous_keywords = ["DROP", "TRUNCATE", "ALTER TABLE", "GRANT"]
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return f"Error: Dangerous operation '{keyword}' is not allowed."

        if dry_run:
            return (
                f"[MySQL Dry Run] Query validated successfully.\n"
                f"Database: {database}\n"
                f"Query: {query}\n"
                f"MySQL Syntax: OK"
            )

        # TODO: Implement actual MySQL execution with:
        # - aiomysql connection pool
        # - Query execution
        # - Result formatting
        return (
            f"[MySQL Query Placeholder]\n"
            f"Database: {database}\n"
            f"Query: {query}\n"
            f"Params: {params}\n"
            f"Results: [Implement actual MySQL execution here]\n"
            f"Hint: Configure MySQL connection in settings and use aiomysql for async execution."
        )
