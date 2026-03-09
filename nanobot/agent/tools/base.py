"""Base Tool class with parameter validation."""
from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for identification."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM to understand usage."""
        pass

    @property
    def parameters(self) -> dict[str, Any]:
        """JSON Schema format parameter definition."""
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given parameters."""
        pass

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """Validate parameters against schema, return list of errors."""
        errors: list[str] = []
        schema = self.parameters
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required fields
        for field in required:
            if field not in params:
                errors.append(f"missing required {field}")

        # Validate each provided parameter
        for key, value in params.items():
            if key not in properties:
                continue  # Ignore unknown fields

            prop_schema = properties[key]
            errors.extend(self._validate_value(key, value, prop_schema))

        return errors

    def _validate_value(
        self, path: str, value: Any, schema: dict[str, Any]
    ) -> list[str]:
        """Recursively validate a value against schema."""
        errors: list[str] = []
        expected_type = schema.get("type")

        if expected_type == "string":
            if not isinstance(value, str):
                errors.append(f"{path} should be string")
            elif "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(f"{path} must be at least {schema['minLength']} chars")
            elif "enum" in schema and value not in schema["enum"]:
                errors.append(f"{path} must be one of {schema['enum']}")

        elif expected_type == "integer":
            if not isinstance(value, int):
                errors.append(f"{path} should be integer")
            elif "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path} must be >= {schema['minimum']}")
            elif "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path} must be <= {schema['maximum']}")

        elif expected_type == "number":
            if not isinstance(value, (int, float)):
                errors.append(f"{path} should be number")

        elif expected_type == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{path} should be boolean")

        elif expected_type == "array":
            if not isinstance(value, list):
                errors.append(f"{path} should be array")
            elif "items" in schema:
                items_schema = schema["items"]
                for i, item in enumerate(value):
                    errors.extend(
                        self._validate_value(f"{path}[{i}]", item, items_schema)
                    )

        elif expected_type == "object":
            if not isinstance(value, dict):
                errors.append(f"{path} should be object")
            else:
                nested_props = schema.get("properties", {})
                nested_required = schema.get("required", [])

                for field in nested_required:
                    if field not in value:
                        errors.append(f"missing required {path}.{field}")

                for k, v in value.items():
                    if k in nested_props:
                        errors.extend(
                            self._validate_value(f"{path}.{k}", v, nested_props[k])
                        )

        return errors

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
