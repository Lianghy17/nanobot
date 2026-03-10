"""Table schema search skill for ChatBI."""
from typing import Any

from nanobot.agent.skills.base import Skill


class SchemaSearchSkill(Skill):
    """Skill for searching table schemas and metadata."""

    @property
    def name(self) -> str:
        return "schema_search"

    @property
    def description(self) -> str:
        return (
            "Search and retrieve table schemas, column information, and metadata. "
            "Use this to understand table structure before writing queries. "
            "Returns table names, column names, data types, and relationships."
        )

    @property
    def category(self) -> str:
        return "rag"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Table name to search for (supports partial match)",
                },
                "database": {
                    "type": "string",
                    "description": "Database name to search within",
                    "enum": ["all", "main", "analytics", "logs"],
                    "default": "all",
                },
                "include_samples": {
                    "type": "boolean",
                    "description": "Include sample data for better context",
                    "default": False,
                },
            },
        }

    @property
    def examples(self) -> list[str]:
        return [
            "Show me the schema for users table",
            "What columns are in the orders table?",
            "Find tables related to sales data",
        ]

    async def execute(self, **kwargs: Any) -> str:
        """Execute schema search."""
        table_name = kwargs.get("table_name", "")
        database = kwargs.get("database", "all")
        include_samples = kwargs.get("include_samples", False)

        # TODO: Implement actual schema retrieval from:
        # - Database metadata tables (information_schema)
        # - Pre-defined schema documents
        # - Data dictionary
        result = (
            f"[Schema Search Placeholder]\n"
            f"Table: {table_name or 'All tables'}\n"
            f"Database: {database}\n\n"
        )

        if table_name:
            result += (
                f"Table: {table_name}\n"
                f"Columns:\n"
                f"  - id (INTEGER, PRIMARY KEY, NOT NULL)\n"
                f"  - name (VARCHAR(255), NOT NULL)\n"
                f"  - email (VARCHAR(255), UNIQUE)\n"
                f"  - created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)\n"
                f"  - status (VARCHAR(50), DEFAULT 'active')\n\n"
                f"Indexes:\n"
                f"  - PRIMARY KEY (id)\n"
                f"  - UNIQUE INDEX idx_email (email)\n"
                f"  - INDEX idx_created_at (created_at)\n"
            )
            if include_samples:
                result += (
                    f"\nSample Data (2 rows):\n"
                    f"  1 | John Doe | john@example.com | 2024-01-15 10:30:00 | active\n"
                    f"  2 | Jane Smith | jane@example.com | 2024-01-16 14:20:00 | active\n"
                )
        else:
            result += (
                f"Related Tables:\n"
                f"  - users: User information table\n"
                f"  - user_events: User activity events\n"
                f"  - user_preferences: User settings\n"
                f"  - user_sessions: Login sessions\n"
            )

        result += (
            f"\nHint: Configure database connections to retrieve actual schema information."
        )

        return result
