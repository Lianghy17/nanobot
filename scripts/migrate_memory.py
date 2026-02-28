#!/usr/bin/env python3
"""Migrate legacy memory files to new multi-level structure.

Legacy structure:
  workspace/memory/MEMORY.md
  workspace/memory/HISTORY.md

New structure:
  workspace/memory/_global/MEMORY.md
  workspace/memory/_global/HISTORY.md
"""

import shutil
from pathlib import Path
import sys


def migrate_memory(workspace: Path) -> None:
    """Migrate legacy memory files to new structure."""
    memory_dir = workspace / "memory"
    
    if not memory_dir.exists():
        print(f"Memory directory not found: {memory_dir}")
        return
    
    legacy_memory = memory_dir / "MEMORY.md"
    legacy_history = memory_dir / "HISTORY.md"
    
    # Create new global directory
    global_dir = memory_dir / "_global"
    global_dir.mkdir(exist_ok=True)
    
    new_memory = global_dir / "MEMORY.md"
    new_history = global_dir / "HISTORY.md"
    
    migrated = False
    
    # Migrate MEMORY.md
    if legacy_memory.exists() and not new_memory.exists():
        shutil.move(str(legacy_memory), str(new_memory))
        print(f"Migrated: {legacy_memory} -> {new_memory}")
        migrated = True
    
    # Migrate HISTORY.md
    if legacy_history.exists() and not new_history.exists():
        shutil.move(str(legacy_history), str(new_history))
        print(f"Migrated: {legacy_history} -> {new_history}")
        migrated = True
    
    # Create new directories
    channels_dir = memory_dir / "channels"
    users_dir = memory_dir / "users"
    channels_dir.mkdir(exist_ok=True)
    users_dir.mkdir(exist_ok=True)
    
    if migrated:
        print(f"\nMigration complete!")
        print(f"  - Global memory: {global_dir}/MEMORY.md")
        print(f"  - Channel memory: {channels_dir}/{{channel}}/MEMORY.md")
        print(f"  - User memory: {users_dir}/{{channel}}_{{chat_id}}/MEMORY.md")
    else:
        print("No legacy files to migrate or already migrated.")


def main():
    workspace = Path(__file__).parent.parent / "workspace"
    
    if len(sys.argv) > 1:
        workspace = Path(sys.argv[1])
    
    print(f"Workspace: {workspace}")
    migrate_memory(workspace)


if __name__ == "__main__":
    main()
