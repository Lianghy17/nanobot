"""Session management for conversation history with channel/user isolation."""

import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from nanobot.utils.helpers import ensure_dir, safe_filename


@dataclass
class Session:
    """
    A conversation session.

    Stores messages in JSONL format for easy reading and persistence.

    Important: Messages are append-only for LLM cache efficiency.
    The consolidation process writes summaries to MEMORY.md/HISTORY.md
    but does NOT modify the messages list or get_history() output.
    """

    key: str  # channel:chat_id
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_consolidated: int = 0  # Number of messages already consolidated to files
    
    @property
    def channel(self) -> str:
        """Extract channel from key."""
        if ":" in self.key:
            return self.key.split(":", 1)[0]
        return "unknown"
    
    @property
    def chat_id(self) -> str:
        """Extract chat_id from key."""
        if ":" in self.key:
            return self.key.split(":", 1)[1]
        return self.key
    
    @property
    def user_name(self) -> str | None:
        """Get user name from metadata."""
        return self.metadata.get("user_name")
    
    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the session."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()
    
    def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """Get recent messages in LLM format, preserving tool metadata."""
        out: list[dict[str, Any]] = []
        for m in self.messages[-max_messages:]:
            entry: dict[str, Any] = {"role": m["role"], "content": m.get("content", "")}
            for k in ("tool_calls", "tool_call_id", "name"):
                if k in m:
                    entry[k] = m[k]
            out.append(entry)
        return out
    
    def clear(self) -> None:
        """Clear all messages and reset session to initial state."""
        self.messages = []
        self.last_consolidated = 0
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert session to dict for API response."""
        return {
            "key": self.key,
            "channel": self.channel,
            "chat_id": self.chat_id,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class SessionManager:
    """
    Manages conversation sessions with channel/user isolation.

    Directory structure:
    workspace/
    └── sessions/
        ├── _index.json           # Channel/user index
        ├── cli_direct.jsonl
        ├── telegram_123.jsonl
        ├── telegram_123_username.jsonl  # With username if available
        ├── slack_456.jsonl
        └── ...

    File naming convention:
    - With username: {channel}_{chatid}_{username}.jsonl (e.g., dingtalk_01531937510226598025_张三.jsonl)
    - Without username: {channel}_{chatid}.jsonl (e.g., telegram_123.jsonl)

    User name sources (channel-specific):
    - DingTalk: metadata["sender_name"]
    - Mochat: metadata["sender_name"] or metadata["sender_username"]
    - Telegram: metadata["username"] or metadata["first_name"]
    - Other channels: not currently supported
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_dir = ensure_dir(self.workspace / "sessions")
        self.legacy_sessions_dir = Path.home() / ".nanobot" / "sessions"
        self._cache: dict[str, Session] = {}
        self._index_path = self.sessions_dir / "_index.json"
        self._index: dict[str, dict[str, Any]] = self._load_index()

    def _load_index(self) -> dict[str, dict[str, Any]]:
        """Load session index from disk."""
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text())
            except Exception:
                return {}
        return {}

    def _save_index(self) -> None:
        """Save session index to disk."""
        self._index_path.write_text(json.dumps(self._index, indent=2, ensure_ascii=False))

    def _get_session_path(self, key: str, user_name: str | None = None) -> Path:
        """Get the file path for a session.
        
        Args:
            key: Session key (channel:chat_id)
            user_name: Optional user name to include in filename
        
        Returns:
            Path to the session file
        """
        # Parse channel and chat_id from key
        if ":" in key:
            channel, chat_id = key.split(":", 1)
        else:
            channel, chat_id = "unknown", key
        
        # Build filename: channel_chatid_username.jsonl (if username exists)
        safe_channel = safe_filename(channel)
        safe_chatid = safe_filename(chat_id)
        
        if user_name:
            safe_username = safe_filename(user_name)
            filename = f"{safe_channel}_{safe_chatid}_{safe_username}.jsonl"
        else:
            filename = f"{safe_channel}_{safe_chatid}.jsonl"
        
        return self.sessions_dir / filename
    
    def _find_existing_session_path(self, key: str) -> Path | None:
        """Find existing session file (with or without username).
        
        Args:
            key: Session key (channel:chat_id)
        
        Returns:
            Path to existing session file, or None if not found
        """
        # Parse channel and chat_id from key
        if ":" in key:
            channel, chat_id = key.split(":", 1)
        else:
            channel, chat_id = "unknown", key
        
        safe_channel = safe_filename(channel)
        safe_chatid = safe_filename(chat_id)
        
        # Check for files with username: channel_chatid_*.jsonl
        pattern = f"{safe_channel}_{safe_chatid}_*.jsonl"
        matching_files = list(self.sessions_dir.glob(pattern))
        if matching_files:
            return matching_files[0]
        
        # Check for old format without username: channel_chatid.jsonl
        old_path = self.sessions_dir / f"{safe_channel}_{safe_chatid}.jsonl"
        if old_path.exists():
            return old_path
        
        return None
    
    @staticmethod
    def _extract_username_from_filename(filename: str, key: str) -> str | None:
        """Extract user name from filename if present.
        
        Args:
            filename: Filename stem (without .jsonl extension)
            key: Session key (channel:chat_id)
        
        Returns:
            User name if found, None otherwise
        """
        # Parse channel and chat_id from key
        if ":" in key:
            channel, chat_id = key.split(":", 1)
        else:
            channel, chat_id = "unknown", key
        
        safe_channel = safe_filename(channel)
        safe_chatid = safe_filename(chat_id)
        
        # Check if filename matches pattern: channel_chatid_username
        prefix = f"{safe_channel}_{safe_chatid}_"
        if filename.startswith(prefix):
            username = filename[len(prefix):]
            return username if username else None
        
        return None

    def _get_legacy_session_path(self, key: str) -> Path:
        """Legacy global session path (~/.nanobot/sessions/)."""
        # Legacy path uses old naming: channel_chatid.jsonl
        if ":" in key:
            channel, chat_id = key.split(":", 1)
        else:
            channel, chat_id = "unknown", key
        
        safe_channel = safe_filename(channel)
        safe_chatid = safe_filename(chat_id)
        return self.legacy_sessions_dir / f"{safe_channel}_{safe_chatid}.jsonl"
    
    def _update_index(self, session: Session) -> None:
        """Update index entry for a session."""
        self._index[session.key] = {
            "channel": session.channel,
            "chat_id": session.chat_id,
            "user_name": session.user_name,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
        }
        self._save_index()
    
    def get_or_create(self, key: str, metadata: dict[str, Any] | None = None) -> Session:
        """
        Get an existing session or create a new one.
        
        Args:
            key: Session key (usually channel:chat_id).
            metadata: Optional metadata to update session with (e.g., user_name).
        
        Returns:
            The session.
        """
        if key in self._cache:
            session = self._cache[key]
            # Update metadata if provided
            if metadata:
                user_name = metadata.get("sender_name")
                if user_name and session.user_name != user_name:
                    session.metadata["user_name"] = user_name
                    session.updated_at = datetime.now()
                    self._update_index(session)
            return session
        
        session = self._load(key)
        if session is None:
            session = Session(key=key)
        
        # Update metadata if provided
        if metadata:
            user_name = metadata.get("sender_name")
            if user_name and session.user_name != user_name:
                session.metadata["user_name"] = user_name
                session.updated_at = datetime.now()
        
        self._cache[key] = session
        return session
    
    def _load(self, key: str) -> Session | None:
        """Load a session from disk."""
        # Find existing session file (may be with or without username)
        path = self._find_existing_session_path(key)
        
        if not path:
            # Try legacy path
            legacy_path = self._get_legacy_session_path(key)
            if legacy_path.exists():
                import shutil
                path = self._get_session_path(key)
                shutil.move(str(legacy_path), str(path))
                logger.info(f"Migrated session {key} from legacy path to {path.name}")
            else:
                return None

        try:
            messages = []
            metadata = {}
            created_at = None
            last_consolidated = 0

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)

                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                        last_consolidated = data.get("last_consolidated", 0)
                    else:
                        messages.append(data)
            
            # Extract user_name from filename if not in metadata
            if "user_name" not in metadata:
                user_name = self._extract_username_from_filename(path.stem, key)
                if user_name:
                    metadata["user_name"] = user_name

            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata,
                last_consolidated=last_consolidated
            )
        except Exception as e:
            logger.warning(f"Failed to load session {key}: {e}")
            return None
    
    def save(self, session: Session) -> None:
        """Save a session to disk."""
        path = self._get_session_path(session.key, session.user_name)
        
        # Check if old file exists with different name (user name changed)
        old_path = self._find_existing_session_path(session.key)
        if old_path and old_path != path and old_path.exists():
            # Rename the file to new name
            import shutil
            try:
                shutil.move(str(old_path), str(path))
                logger.info(f"Renamed session file {old_path.name} -> {path.name}")
            except Exception as e:
                logger.warning(f"Failed to rename session file: {e}")

        with open(path, "w", encoding="utf-8") as f:
            metadata_line = {
                "_type": "metadata",
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata,
                "last_consolidated": session.last_consolidated
            }
            f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        self._cache[session.key] = session
        self._update_index(session)
    
    def invalidate(self, key: str) -> None:
        """Remove a session from the in-memory cache."""
        self._cache.pop(key, None)
    
    def delete(self, key: str) -> bool:
        """Delete a session from disk and cache."""
        path = self._find_existing_session_path(key)
        deleted = False
        
        if path and path.exists():
            path.unlink()
            deleted = True
        
        self._cache.pop(key, None)
        self._index.pop(key, None)
        self._save_index()
        
        return deleted
    
    # ==================== Query Methods ====================

    def list_sessions(
        self,
        channel: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List sessions with optional channel filter.
        
        Args:
            channel: Filter by channel (e.g., "telegram", "slack").
            limit: Max number of results.
            offset: Offset for pagination.
        
        Returns:
            List of session info dicts.
        """
        sessions = []
        
        for key, info in self._index.items():
            if channel and info.get("channel") != channel:
                continue
            sessions.append({
                "key": key,
                **info,
            })
        
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return sessions[offset:offset + limit]
    
    def list_channels(self) -> list[dict[str, Any]]:
        """List all channels with session counts."""
        channels: dict[str, dict[str, Any]] = {}
        
        for key, info in self._index.items():
            channel = info.get("channel", "unknown")
            if channel not in channels:
                channels[channel] = {
                    "name": channel,
                    "session_count": 0,
                    "latest_activity": None,
                }
            channels[channel]["session_count"] += 1
            updated = info.get("updated_at", "")
            if not channels[channel]["latest_activity"] or updated > channels[channel]["latest_activity"]:
                channels[channel]["latest_activity"] = updated
        
        return list(channels.values())
    
    def get_channel_users(self, channel: str) -> list[dict[str, Any]]:
        """Get all users for a specific channel."""
        users = []
        
        for key, info in self._index.items():
            if info.get("channel") == channel:
                users.append({
                    "chat_id": info.get("chat_id"),
                    "key": key,
                    "message_count": info.get("message_count", 0),
                    "updated_at": info.get("updated_at"),
                })
        
        users.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return users
    
    def get_stats(self) -> dict[str, Any]:
        """Get overall session statistics."""
        channels = self.list_channels()
        total_sessions = len(self._index)
        total_messages = sum(info.get("message_count", 0) for info in self._index.values())
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "channel_count": len(channels),
            "channels": channels,
        }
    
    def rebuild_index(self) -> int:
        """Rebuild index from session files. Returns count of sessions indexed."""
        self._index = {}
        count = 0
        
        for path in self.sessions_dir.glob("*.jsonl"):
            if path.stem.startswith("_"):
                continue
            
            try:
                with open(path, encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            # Try to extract key from metadata or filename
                            metadata = data.get("metadata", {})
                            user_name = metadata.get("user_name")
                            
                            # Parse key from filename
                            # Filename format: channel_chatid_username.jsonl or channel_chatid.jsonl
                            filename_parts = path.stem.split("_", 2)
                            if len(filename_parts) >= 2:
                                channel = filename_parts[0]
                                chat_id = filename_parts[1]
                                key = f"{channel}:{chat_id}"
                            else:
                                # Old format: filename was "key.jsonl" with key containing ":"
                                # Convert back to key
                                key = path.stem.replace("_", ":", 1)
                                if ":" in key:
                                    channel, chat_id = key.split(":", 1)
                                else:
                                    channel, chat_id = "unknown", key
                            
                            # Extract username from filename if not in metadata
                            if not user_name and len(filename_parts) >= 3:
                                user_name = filename_parts[2]
                            
                            self._index[key] = {
                                "channel": channel,
                                "chat_id": chat_id,
                                "user_name": user_name,
                                "created_at": data.get("created_at", ""),
                                "updated_at": data.get("updated_at", ""),
                                "message_count": 0,  # Will count messages
                            }
                            count += 1
            except Exception as e:
                logger.warning(f"Failed to index {path}: {e}")
        
        self._save_index()
        return count
