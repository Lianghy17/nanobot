#!/usr/bin/env python3
"""
修复会话文件中的不完整消息。

Moonshot/kimi-k2.5 模型要求：当 assistant 消息包含 tool_calls 时，
必须同时包含 reasoning_content 字段，否则 API 会返回 400 错误。

这个脚本会扫描所有会话文件，为包含 tool_calls 但缺少 reasoning_content 的
assistant 消息添加空的 reasoning_content 字段。
"""

import json
import sys
from pathlib import Path


def fix_session_file(session_path: Path, dry_run: bool = False) -> tuple[int, int]:
    """
    修复单个会话文件。

    Returns:
        (fixed_count, total_messages)
    """
    try:
        with open(session_path, 'r') as f:
            lines = f.readlines()

        if not lines:
            return 0, 0

        # 解析第一行（元数据）
        metadata = json.loads(lines[0])
        if metadata.get("_type") != "metadata":
            print(f"⚠ Invalid session file: {session_path}")
            return 0, 0

        # 解析消息行
        messages = []
        fixed_count = 0
        total_messages = 0

        for i, line in enumerate(lines[1:], start=1):
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                total_messages += 1

                # 检查是否为需要修复的 assistant 消息
                if (msg.get("role") == "assistant" and
                    msg.get("tool_calls") and
                    "reasoning_content" not in msg):

                    msg["reasoning_content"] = ""
                    fixed_count += 1
                    print(f"  ✓ Fixed message at index {i-1}")

                messages.append(msg)
            except json.JSONDecodeError as e:
                print(f"  ✗ Failed to parse line {i+1}: {e}")
                continue

        if fixed_count == 0:
            return 0, total_messages

        if not dry_run:
            # 写回修复后的文件
            with open(session_path, 'w') as f:
                # 写入元数据行
                f.write(json.dumps(metadata, ensure_ascii=False) + '\n')
                # 写入消息行
                for msg in messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + '\n')

            print(f"  ✓ Saved {session_path.name}")
        else:
            print(f"  → Would fix {fixed_count} messages (dry run)")

        return fixed_count, total_messages

    except Exception as e:
        print(f"  ✗ Error processing {session_path}: {e}")
        return 0, 0


def fix_all_sessions(sessions_dir: Path, dry_run: bool = False) -> None:
    """修复指定目录中的所有会话文件。"""
    if not sessions_dir.exists():
        print(f"❌ Sessions directory not found: {sessions_dir}")
        return

    session_files = list(sessions_dir.glob("*.jsonl"))
    if not session_files:
        print(f"ℹ No session files found in {sessions_dir}")
        return

    print(f"\n📂 Found {len(session_files)} session files")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE FIX'}\n")

    total_fixed = 0
    total_messages = 0

    for session_file in sorted(session_files):
        print(f"Processing: {session_file.name}")
        fixed, total = fix_session_file(session_file, dry_run)
        total_fixed += fixed
        total_messages += total

    print(f"\n{'='*50}")
    print(f"📊 Summary:")
    print(f"   Total sessions: {len(session_files)}")
    print(f"   Total messages: {total_messages}")
    print(f"   Messages fixed: {total_fixed}")
    if dry_run:
        print(f"\n💡 Run without --dry-run to apply fixes")
    else:
        print(f"\n✅ Completed! Fixed {total_fixed} messages")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix session files for Moonshot thinking compatibility")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed without making changes")
    parser.add_argument("--path", type=Path, help="Custom sessions directory path")
    args = parser.parse_args()

    # 获取 sessions 目录
    if args.path:
        sessions_dir = args.path
    else:
        # 尝试从项目根目录获取
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        sessions_dir = project_root / "workspace" / "sessions"

    print(f"🔧 Moonshot Session Fixer")
    print(f"   Sessions dir: {sessions_dir}")

    fix_all_sessions(sessions_dir, dry_run=args.dry_run)
