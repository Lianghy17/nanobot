# nanobot 项目统一迁移说明

## 概述

本迁移将 nanobot 的配置和数据文件从用户主目录 (`~/.nanobot/`) 迁移到项目根目录，实现项目统一管理。

## 迁移后的目录结构

```
/Users/lianghaoyun/project/nanobot/
├── config.json          # 配置文件（从 ~/.nanobot/config.json 迁移）
├── workspace/           # 工作空间（保持不变）
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── USER.md
│   ├── TOOLS.md
│   ├── HEARTBEAT.md
│   ├── memory/
│   │   ├── MEMORY.md
│   │   └── HISTORY.md
│   ├── sessions/        # 会话文件（从 ~/.nanobot/sessions 迁移）
│   └── skills/
├── data/                # 数据目录（新建）
│   ├── cron/           # 定时任务（从 ~/.nanobot/cron 迁移）
│   ├── history/        # CLI 历史记录（从 ~/.nanobot/history 迁移）
│   ├── media/          # 媒体文件（新建，从 ~/.nanobot/media 迁移）
│   └── bridge/         # 桥接器（按需创建）
├── nanobot/            # 源代码
└── ...
```

## 代码修改

### 1. `nanobot/config/loader.py`
- **修改前**: `get_config_path()` 返回 `~/.nanobot/config.json`
- **修改后**: 返回项目根目录的 `config.json`

```python
def get_config_path() -> Path:
    """Get the default configuration file path."""
    # Get project root (parent of nanobot package)
    project_root = Path(__file__).parent.parent.parent
    return project_root / "config.json"
```

### 2. `nanobot/utils/helpers.py`
- **修改前**: `get_data_path()` 返回 `~/.nanobot/`
- **修改后**: 返回项目根目录的 `data/`

```python
def get_data_path() -> Path:
    """Get the nanobot data directory."""
    # Get project root (parent of nanobot package)
    project_root = Path(__file__).parent.parent.parent
    return ensure_dir(project_root / "data")
```

- **修改前**: `get_workspace_path()` 默认返回 `~/.nanobot/workspace`
- **修改后**: 默认返回项目根目录的 `workspace/`

```python
def get_workspace_path(workspace: str | None = None) -> Path:
    """
    Get the workspace path.
    
    Args:
        workspace: Optional workspace path. Defaults to project/workspace.
    
    Returns:
        Expanded and ensured workspace path.
    """
    if workspace:
        path = Path(workspace).expanduser()
    else:
        # Get project root (parent of nanobot package)
        project_root = Path(__file__).parent.parent.parent
        path = project_root / "workspace"
    return ensure_dir(path)
```

### 3. `nanobot/config/schema.py`
- **修改前**: `workspace: str = "~/.nanobot/workspace"`
- **修改后**: `workspace: str = "./workspace"`

### 4. `nanobot/session/manager.py`
- **移除**: `legacy_sessions_dir` 相关代码（不再需要从旧路径迁移）
- **简化**: `_load()` 方法，移除旧路径兼容逻辑

```python
def __init__(self, workspace: Path):
    self.workspace = workspace
    self.sessions_dir = ensure_dir(self.workspace / "sessions")
    self._cache: dict[str, Session] = {}
```

### 5. `nanobot/cli/commands.py`
- **修改**: CLI 历史文件路径从 `~/.nanobot/history/` 改为 `data/history/`
- **修改**: 桥接器目录路径从 `~/.nanobot/bridge/` 改为 `data/bridge/`
- **修改**: 提示信息从 `~/.nanobot/config.json` 改为 `config.json`

```python
from nanobot.utils.helpers import get_data_path
history_file = get_data_path() / "history" / "cli_history"
```

### 6. `nanobot/channels/discord.py`
- **修改**: 媒体目录路径从 `~/.nanobot/media` 改为 `data/media`

```python
from nanobot.utils.helpers import get_data_path
media_dir = get_data_path() / "media"
```

### 7. `nanobot/channels/telegram.py`
- **修改**: 媒体目录路径从 `~/.nanobot/media` 改为 `data/media`

```python
from nanobot.utils.helpers import get_data_path
media_dir = get_data_path() / "media"
```

## 配置文件修改

### `config.json`

```json
{
  "agents": {
    "defaults": {
      "workspace": "./workspace",  // 从 "~/.nanobot/workspace" 改为 "./workspace"
      "model": "moonshot/kimi-k2.5",
      "maxTokens": 8192,
      "temperature": 0.7,
      "maxToolIterations": 20
    }
  }
}
```

## 使用方法

### 激活虚拟环境后使用

```bash
cd /Users/lianghaoyun/project/nanobot
source .venv/bin/activate
python -m nanobot status
python -m nanobot agent -m "你好"
```

### 全局命令（需要更新）

如果你想使用全局 `nanobot` 命令，需要重新安装：

```bash
cd /Users/lianghaoyun/project/nanobot
pip uninstall nanobot -y
pip install -e .
```

然后可以直接使用：

```bash
nanobot status
nanobot agent -m "你好"
```

## 旧数据保留

原始的 `~/.nanobot/` 目录中的数据已迁移到项目目录：
- `~/.nanobot/config.json` → `config.json`
- `~/.nanobot/sessions/` → `workspace/sessions/`
- `~/.nanobot/cron/` → `data/cron/`
- `~/.nanobot/history/` → `data/history/`

你可以根据需要删除或备份旧目录：

```bash
# 备份旧数据
mv ~/.nanobot ~/.nanobot.backup

# 或者直接删除
# rm -rf ~/.nanobot
```

## .gitignore 更新

已更新 `.gitignore` 文件，忽略以下内容：

```gitignore
config.json  # 配置文件（包含 API 密钥）
data/        # 运行时数据（sessions, cron, history, media, bridge）
```

## 验证步骤

### 1. 检查配置文件路径

```bash
cd /Users/lianghaoyun/project/nanobot
source .venv/bin/activate
python -m nanobot status
```

应该显示：
```
Config: /Users/lianghaoyun/project/nanobot/config.json ✓
Workspace: workspace ✓
```

### 2. 测试 agent 功能

```bash
python -m nanobot agent -m "测试一下配置"
```

### 3. 检查目录结构

```bash
ls -la
ls -la data/
ls -la workspace/sessions/
```

## 注意事项

1. **虚拟环境**: 建议使用项目虚拟环境 (`.venv/bin/activate`)
2. **配置文件**: `config.json` 包含敏感信息，已加入 `.gitignore`
3. **数据目录**: `data/` 目录包含运行时数据，已加入 `.gitignore`
4. **全局命令**: 如果使用全局 `nanobot` 命令，确保已重新安装

## 迁移收益

1. **项目统一**: 所有配置和数据都在项目目录下，便于管理
2. **版本控制**: 项目代码和配置分离，便于版本控制
3. **部署友好**: 更容易部署到不同环境
4. **协作便利**: 团队成员可以直接使用项目中的配置模板
