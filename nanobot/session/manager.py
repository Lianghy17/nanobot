"""Session and SessionManager for user conversation isolation."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SessionState(Enum):
    """Session state for managing conversation flow."""

    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"


@dataclass
class Session:
    """User session with conversation history and state management."""

    key: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_consolidated: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    state: SessionState = SessionState.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # Pause/resume control
    _pause_event: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        """Initialize pause event as set (not paused)."""
        self._pause_event.set()

    def add_message(self, role: str, content: str, **metadata: Any) -> None:
        """Add a message to the conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            **metadata,
        }
        self.messages.append(message)
        self.updated_at = time.time()

    def get_history(self, max_messages: int | None = None) -> list[dict[str, Any]]:
        """Get message history, optionally limited to last N messages."""
        if max_messages is None:
            return self.messages.copy()
        return self.messages[-max_messages:]

    def clear(self) -> None:
        """Clear session history while preserving session identity."""
        self.messages = []
        self.last_consolidated = 0
        self.updated_at = time.time()

    def pause(self) -> None:
        """Pause the session, blocking any processing."""
        self.state = SessionState.PAUSED
        self._pause_event.clear()
        self.updated_at = time.time()

    def resume(self) -> None:
        """Resume a paused session."""
        self.state = SessionState.ACTIVE
        self._pause_event.set()
        self.updated_at = time.time()

    async def wait_if_paused(self) -> None:
        """Wait until the session is resumed."""
        await self._pause_event.wait()

    def is_paused(self) -> bool:
        """Check if session is paused."""
        return self.state == SessionState.PAUSED

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "key": self.key,
            "messages": self.messages,
            "last_consolidated": self.last_consolidated,
            "metadata": self.metadata,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserialize session from dictionary."""
        session = cls(
            key=data["key"],
            messages=data.get("messages", []),
            last_consolidated=data.get("last_consolidated", 0),
            metadata=data.get("metadata", {}),
            state=SessionState(data.get("state", "active")),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
        # Restore state-specific event
        if session.state == SessionState.PAUSED:
            session._pause_event.clear()
        return session


class SessionManager:
    """Manager for user sessions with persistence support."""

    MEMORY_WINDOW = 50
    KEEP_COUNT = 25

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize session manager with optional storage path."""
        self._sessions: dict[str, Session] = {}
        self._storage_path = storage_path
        self._lock = asyncio.Lock()

        if storage_path:
            self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure storage directory exists."""
        if self._storage_path:
            self._storage_path.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, key: str) -> Path | None:
        """Get the file path for a session."""
        if not self._storage_path:
            return None
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self._storage_path / f"{safe_key}.json"

    async def get_or_create(
        self, key: str, user_id: str | None = None, channel: str | None = None
    ) -> Session:
        """Get existing session or create a new one."""
        async with self._lock:
            if key in self._sessions:
                return self._sessions[key]

            # Try to load from storage
            session = await self._load_session(key)
            if session is None:
                # Create new session
                session = Session(
                    key=key,
                    metadata={
                        "user_id": user_id,
                        "channel": channel,
                    },
                )

            self._sessions[key] = session
            return session

    async def save(self, session: Session) -> None:
        """Save session to storage."""
        if not self._storage_path:
            return

        session_file = self._get_session_file(session.key)
        if session_file:
            async with self._lock:
                session_file.write_text(
                    json.dumps(session.to_dict(), ensure_ascii=False, indent=2)
                )

    async def _load_session(self, key: str) -> Session | None:
        """Load session from storage."""
        session_file = self._get_session_file(key)
        if session_file and session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                return Session.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    async def delete(self, key: str) -> bool:
        """Delete a session."""
        async with self._lock:
            if key in self._sessions:
                del self._sessions[key]

            session_file = self._get_session_file(key)
            if session_file and session_file.exists():
                session_file.unlink()

            return True

    def get_all_keys(self) -> list[str]:
        """Get all session keys."""
        return list(self._sessions.keys())

    async def consolidate(self, session: Session, archive_all: bool = False) -> None:
        """Consolidate old messages to save memory."""
        if archive_all:
            # Archive all messages (used for /new command)
            session.last_consolidated = len(session.messages)
        else:
            # Archive messages outside the memory window
            messages_to_keep = min(self.KEEP_COUNT, len(session.messages))
            if len(session.messages) > self.MEMORY_WINDOW:
                session.last_consolidated = len(session.messages) - messages_to_keep

        await self.save(session)
