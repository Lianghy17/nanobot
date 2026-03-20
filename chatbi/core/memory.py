"""Memory system for persistent agent memory with multi-level isolation."""

from pathlib import Path
from typing import Literal, Any
import shutil

from ..config import settings


class MemoryStore:
    """
    Two-level memory system: global + session.

    Directory structure:
    workspace/
    └── memory/
        ├── _global/
        │   ├── MEMORY.md      # Shared across all conversations
        │   └── HISTORY.md
        └── conversations/
            └── {conversation_id}/
                ├── MEMORY.md  # Session-specific memory
                └── HISTORY.md # Session-specific history
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
            memory_key: Memory key in format "conv:{conversation_id}" for session-level isolation.
        """
        self.workspace = workspace
        self.memory_key = memory_key
        self.memory_root = workspace / "memory"

        # Global-level paths
        self._global_dir = self._ensure_dir(self.memory_root / "_global")
        self._global_memory = self._global_dir / "MEMORY.md"
        self._global_history = self._global_dir / "HISTORY.md"

        # Session-level paths (lazy init)
        self._session_dir: Path | None = None
        self._session_memory: Path | None = None
        self._session_history: Path | None = None
        if memory_key:
            # memory_key format: "conv:{conversation_id}"
            # Extract conversation_id and create path
            if memory_key.startswith("conv:"):
                conv_id = memory_key[5:]  # Remove "conv:" prefix
            else:
                conv_id = memory_key
            self._session_dir = self._ensure_dir(self.memory_root / "conversations" / conv_id)
            self._session_memory = self._session_dir / "MEMORY.md"
            self._session_history = self._session_dir / "HISTORY.md"

    def _ensure_dir(self, path: Path) -> Path:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ==================== Long-term Memory ====================

    def read_long_term(self) -> str:
        """Read combined memory from global + session levels."""
        parts = []

        # Global memory
        if self._global_memory.exists():
            global_content = self._global_memory.read_text(encoding="utf-8").strip()
            if global_content:
                parts.append(("Global", global_content))

        # Session memory
        if self._session_memory and self._session_memory.exists():
            session_content = self._session_memory.read_text(encoding="utf-8").strip()
            if session_content:
                parts.append(("Session", session_content))

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
        level: Literal["global", "session"] = "session"
    ) -> None:
        """
        Write memory to specific level.

        Args:
            content: Memory content to write.
            level: Target level - "global" or "session".
        """
        if level == "global":
            self._global_memory.write_text(content, encoding="utf-8")
        elif level == "session" and self._session_memory:
            self._session_memory.write_text(content, encoding="utf-8")

    def append_long_term(
        self,
        content: str,
        level: Literal["global", "session"] = "session"
    ) -> None:
        """Append content to existing memory at specific level."""
        target_file = self._get_memory_file(level)
        if target_file:
            existing = target_file.read_text(encoding="utf-8") if target_file.exists() else ""
            new_content = f"{existing}\n\n{content}".strip()
            target_file.write_text(new_content, encoding="utf-8")

    def _get_memory_file(self, level: Literal["global", "session"]) -> Path | None:
        """Get memory file path for specific level."""
        if level == "global":
            return self._global_memory
        elif level == "session":
            return self._session_memory
        return None

    # ==================== History ====================

    def append_history(self, entry: str, level: Literal["global", "session"] = "session") -> None:
        """
        Append entry to history log.

        Args:
            entry: History entry to append.
            level: Target level - defaults to "session".
        """
        target_file = self._get_history_file(level)
        if target_file:
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(entry.rstrip() + "\n\n")

    def read_history(self, level: Literal["global", "session"] = "session") -> str:
        """Read history from specific level."""
        target_file = self._get_history_file(level)
        if target_file and target_file.exists():
            return target_file.read_text(encoding="utf-8")
        return ""

    def _get_history_file(self, level: Literal["global", "session"]) -> Path | None:
        """Get history file path for specific level."""
        if level == "global":
            return self._global_history
        elif level == "session":
            return self._session_history
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
            "session_memory": self._session_memory,
            "session_history": self._session_history,
        }


# ==================== Memory Manager ====================

class MemoryManager:
    """
    Manager for two-level memory with CRUD operations.

    Used by API endpoints to manage memories across conversations.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_root = workspace / "memory"
        self._global_dir = self._ensure_dir(self.memory_root / "_global")
        self._conversations_dir = self._ensure_dir(self.memory_root / "conversations")

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

    def get_session_memory(self, conversation_id: str) -> dict[str, Any]:
        """Get session-level memory content."""
        conv_dir = self._conversations_dir / conversation_id
        memory_file = conv_dir / "MEMORY.md"
        history_file = conv_dir / "HISTORY.md"

        return {
            "level": "session",
            "conversation_id": conversation_id,
            "memory": memory_file.read_text(encoding="utf-8") if memory_file.exists() else "",
            "history": history_file.read_text(encoding="utf-8") if history_file.exists() else "",
        }

    def get_combined_memory(self, conversation_id: str | None = None) -> str:
        """Get combined memory for a specific context."""
        memory_key = f"conv:{conversation_id}" if conversation_id else None
        store = MemoryStore(self.workspace, memory_key=memory_key)
        return store.read_long_term()

    # ==================== Write Operations ====================

    def set_global_memory(self, content: str) -> None:
        """Set global memory content."""
        memory_file = self._global_dir / "MEMORY.md"
        memory_file.write_text(content, encoding="utf-8")

    def set_session_memory(self, conversation_id: str, content: str) -> None:
        """Set session-level memory content."""
        conv_dir = self._ensure_dir(self._conversations_dir / conversation_id)
        memory_file = conv_dir / "MEMORY.md"
        memory_file.write_text(content, encoding="utf-8")

    # ==================== Delete Operations ====================

    def delete_session_memory(self, conversation_id: str) -> bool:
        """Delete session-level memory."""
        conv_dir = self._conversations_dir / conversation_id
        if conv_dir.exists():
            shutil.rmtree(conv_dir)
            return True
        return False

    # ==================== List Operations ====================

    def list_conversations(self) -> list[dict[str, Any]]:
        """List all conversations with memory."""
        conversations = []

        if self._conversations_dir.exists():
            for conv_dir in self._conversations_dir.iterdir():
                if not conv_dir.is_dir():
                    continue

                conversation_id = conv_dir.name
                memory_file = conv_dir / "MEMORY.md"
                history_file = conv_dir / "HISTORY.md"

                conversations.append({
                    "conversation_id": conversation_id,
                    "has_memory": memory_file.exists(),
                    "has_history": history_file.exists(),
                })

        return conversations

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        conversations = self.list_conversations()

        global_memory = self._global_dir / "MEMORY.md"
        global_history = self._global_dir / "HISTORY.md"

        return {
            "global": {
                "has_memory": global_memory.exists(),
                "has_history": global_history.exists(),
            },
            "conversations": {
                "count": len(conversations),
                "list": conversations,
            },
        }
