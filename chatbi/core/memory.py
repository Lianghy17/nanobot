"""Memory system for persistent agent memory with multi-level isolation."""

from pathlib import Path
from typing import Literal, Any
import shutil

from ..config import settings


class MemoryStore:
    """
    Two-level memory system: global + user.

    Directory structure:
    workspace/
    └── memory/
        ├── _global/
        │   ├── MEMORY.md      # Shared across all users
        │   └── HISTORY.md
        └── users/
            └── {user_id}_{channel}/
                ├── MEMORY.md  # User-specific memory
                └── HISTORY.md
    """

    def __init__(
        self,
        workspace: Path,
        memory_key: str | None = None,
    ):
        """
        Initialize memory store.

        Args:
            workspace: Workspace root path.
            memory_key: Memory key in format "user_id:channel" for user-level isolation.
        """
        self.workspace = workspace
        self.memory_key = memory_key
        self.memory_root = workspace / "memory"

        # Global-level paths
        self._global_dir = self._ensure_dir(self.memory_root / "_global")
        self._global_memory = self._global_dir / "MEMORY.md"
        self._global_history = self._global_dir / "HISTORY.md"

        # User-level paths (lazy init)
        self._user_dir: Path | None = None
        self._user_memory: Path | None = None
        self._user_history: Path | None = None
        if memory_key:
            # memory_key format: "user_id:channel"
            # Convert to directory name: "user_id_channel"
            safe_key = memory_key.replace(":", "_")
            self._user_dir = self._ensure_dir(self.memory_root / "users" / safe_key)
            self._user_memory = self._user_dir / "MEMORY.md"
            self._user_history = self._user_dir / "HISTORY.md"

    def _ensure_dir(self, path: Path) -> Path:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ==================== Long-term Memory ====================

    def read_long_term(self) -> str:
        """Read combined memory from global + user levels."""
        parts = []

        # Global memory
        if self._global_memory.exists():
            global_content = self._global_memory.read_text(encoding="utf-8").strip()
            if global_content:
                parts.append(("Global", global_content))

        # User memory
        if self._user_memory and self._user_memory.exists():
            user_content = self._user_memory.read_text(encoding="utf-8").strip()
            if user_content:
                parts.append(("Personal", user_content))

        if not parts:
            return ""

        # Format combined memory
        lines = []
        for label, content in parts:
            lines.append(f"### {label}\n{content}")
        return "\n\n".join(lines)

    def write_long_term(
        self,
        content: str,
        level: Literal["global", "user"] = "user"
    ) -> None:
        """
        Write memory to specific level.

        Args:
            content: Memory content to write.
            level: Target level - "global" or "user".
        """
        if level == "global":
            self._global_memory.write_text(content, encoding="utf-8")
        elif level == "user" and self._user_memory:
            self._user_memory.write_text(content, encoding="utf-8")

    def append_long_term(
        self,
        content: str,
        level: Literal["global", "user"] = "user"
    ) -> None:
        """Append content to existing memory at specific level."""
        target_file = self._get_memory_file(level)
        if target_file:
            existing = target_file.read_text(encoding="utf-8") if target_file.exists() else ""
            new_content = f"{existing}\n\n{content}".strip()
            target_file.write_text(new_content, encoding="utf-8")

    def _get_memory_file(self, level: Literal["global", "user"]) -> Path | None:
        """Get memory file path for specific level."""
        if level == "global":
            return self._global_memory
        elif level == "user":
            return self._user_memory
        return None

    # ==================== History ====================

    def append_history(self, entry: str, level: Literal["global", "user"] = "user") -> None:
        """
        Append entry to history log.

        Args:
            entry: History entry to append.
            level: Target level - defaults to "user".
        """
        target_file = self._get_history_file(level)
        if target_file:
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(entry.rstrip() + "\n\n")

    def read_history(self, level: Literal["global", "user"] = "user") -> str:
        """Read history from specific level."""
        target_file = self._get_history_file(level)
        if target_file and target_file.exists():
            return target_file.read_text(encoding="utf-8")
        return ""

    def _get_history_file(self, level: Literal["global", "user"]) -> Path | None:
        """Get history file path for specific level."""
        if level == "global":
            return self._global_history
        elif level == "user":
            return self._user_history
        return None

    # ==================== Context ====================

    def get_memory_context(self) -> str:
        """Get formatted memory context for LLM prompt."""
        content = self.read_long_term()
        return f"## Long-term Memory\n{content}" if content else ""

    # ==================== Utils ====================

    def get_memory_paths(self) -> dict[str, Path | None]:
        """Get all memory file paths for current context."""
        return {
            "global_memory": self._global_memory,
            "global_history": self._global_history,
            "user_memory": self._user_memory,
            "user_history": self._user_history,
        }


# ==================== Memory Manager ====================

class MemoryManager:
    """
    Manager for two-level memory with CRUD operations.

    Used by API endpoints to manage memories across users.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_root = workspace / "memory"
        self._global_dir = self._ensure_dir(self.memory_root / "_global")
        self._users_dir = self._ensure_dir(self.memory_root / "users")

    def _ensure_dir(self, path: Path) -> Path:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ==================== Read Operations ====================

    def get_global_memory(self) -> dict[str, Any]:
        """Get global memory content."""
        memory_file = self._global_dir / "MEMORY.md"
        history_file = self._global_dir / "HISTORY.md"

        return {
            "level": "global",
            "memory": memory_file.read_text(encoding="utf-8") if memory_file.exists() else "",
            "history": history_file.read_text(encoding="utf-8") if history_file.exists() else "",
        }

    def get_user_memory(self, user_id: str, channel: str) -> dict[str, Any]:
        """Get user-level memory content."""
        memory_key = f"{user_id}:{channel}"
        safe_key = memory_key.replace(":", "_")
        user_dir = self._users_dir / safe_key
        memory_file = user_dir / "MEMORY.md"
        history_file = user_dir / "HISTORY.md"

        return {
            "level": "user",
            "user_id": user_id,
            "channel": channel,
            "memory_key": memory_key,
            "memory": memory_file.read_text(encoding="utf-8") if memory_file.exists() else "",
            "history": history_file.read_text(encoding="utf-8") if history_file.exists() else "",
        }

    def get_combined_memory(self, user_id: str | None = None, channel: str | None = None) -> str:
        """Get combined memory for a specific context."""
        memory_key = f"{user_id}:{channel}" if user_id and channel else None
        store = MemoryStore(self.workspace, memory_key=memory_key)
        return store.read_long_term()

    # ==================== Write Operations ====================

    def set_global_memory(self, content: str) -> None:
        """Set global memory content."""
        memory_file = self._global_dir / "MEMORY.md"
        memory_file.write_text(content, encoding="utf-8")

    def set_user_memory(self, user_id: str, channel: str, content: str) -> None:
        """Set user-level memory content."""
        memory_key = f"{user_id}:{channel}"
        safe_key = memory_key.replace(":", "_")
        user_dir = self._ensure_dir(self._users_dir / safe_key)
        memory_file = user_dir / "MEMORY.md"
        memory_file.write_text(content, encoding="utf-8")

    # ==================== Delete Operations ====================

    def delete_user_memory(self, user_id: str, channel: str) -> bool:
        """Delete user-level memory."""
        memory_key = f"{user_id}:{channel}"
        safe_key = memory_key.replace(":", "_")
        user_dir = self._users_dir / safe_key
        if user_dir.exists():
            shutil.rmtree(user_dir)
            return True
        return False

    # ==================== List Operations ====================

    def list_users(self) -> list[dict[str, Any]]:
        """List all users with memory."""
        users = []

        if self._users_dir.exists():
            for user_dir in self._users_dir.iterdir():
                if not user_dir.is_dir():
                    continue

                # Parse user_id_channel from directory name
                name = user_dir.name
                if "_" in name:
                    # Find the last underscore to split user_id and channel
                    # Format: {user_id}_{channel}
                    last_underscore = name.rfind("_")
                    user_id = name[:last_underscore]
                    channel = name[last_underscore + 1:]
                else:
                    user_id, channel = name, "unknown"

                memory_file = user_dir / "MEMORY.md"
                history_file = user_dir / "HISTORY.md"

                users.append({
                    "user_id": user_id,
                    "channel": channel,
                    "memory_key": f"{user_id}:{channel}",
                    "has_memory": memory_file.exists(),
                    "has_history": history_file.exists(),
                })

        return users

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        users = self.list_users()

        global_memory = self._global_dir / "MEMORY.md"
        global_history = self._global_dir / "HISTORY.md"

        return {
            "global": {
                "has_memory": global_memory.exists(),
                "has_history": global_history.exists(),
            },
            "users": {
                "count": len(users),
                "list": users,
            },
        }
