# nanobot 记忆系统深度解读

## 📚 目录

1. [系统架构概览](#1-系统架构概览)
2. [三层记忆结构](#2-三层记忆结构)
3. [MemoryStore 类详解](#3-memorystore-类详解)
4. [SessionManager 类详解](#4-sessionmanager-类详解)
5. [记忆整合流程](#5-记忆整合流程)
6. [记忆使用流程](#6-记忆使用流程)
7. [完整流程图](#7-完整流程图)
8. [设计亮点分析](#8-设计亮点分析)
9. [实际案例演示](#9-实际案例演示)
10. [常见问题解答](#10-常见问题解答)

---

## 1. 系统架构概览

### 1.1 记忆系统定位

nanobot 的记忆系统是其核心组件之一，负责：
- **持久化对话历史**：确保对话不丢失
- **长期记忆管理**：记住用户偏好、项目上下文等关键信息
- **智能记忆整合**：自动提取重要信息，避免记忆无限膨胀
- **快速检索**：在对话中提供相关上下文

### 1.2 核心设计理念

```
┌─────────────────────────────────────────────────────────┐
│              nanobot 记忆系统架构                 │
├─────────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌─────────────┐               │
│  │ MEMORY.md   │  │ HISTORY.md  │               │
│  │ 长期记忆    │  │ 历史日志    │               │
│  └──────┬──────┘  └──────┬──────┘               │
│         │                  │                       │
│         │  MemoryStore   │                       │
│         └──────────────────┘                       │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐               │
│  │ Session 1   │  │ Session 2   │               │
│  │ .jsonl 文件 │  │ .jsonl 文件 │  ...          │
│  └──────┬──────┘  └──────┬──────┘               │
│         │                  │                       │
│         │  SessionManager   │                       │
│         └──────────────────┘                       │
│         │                                          │
│         └──────────────┐                             │
│                        ↓                             │
│              AgentLoop (触发整合）                       │
└─────────────────────────────────────────────────────────┘
```

**核心特点**：
1. **分层存储**：长期记忆 + 历史日志 + 活跃会话
2. **智能整合**：使用 LLM 自动提取关键信息
3. **增量更新**：只处理新消息，避免重复整合
4. **异步处理**：后台执行整合，不阻塞对话

---

## 2. 三层记忆结构

### 2.1 存储层次

```
workspace/
│
├── memory/                          # 记忆存储目录
│   ├── MEMORY.md                   # 第一层：长期记忆（结构化事实）
│   └── HISTORY.md                  # 第二层：历史日志（时间线记录）
│
└── sessions/                        # 第三层：活跃会话（JSONL 格式）
    ├── cli_direct.jsonl            # CLI 会话
    ├── telegram_12345.jsonl       # Telegram 会话
    ├── discord_67890.jsonl        # Discord 会话
    └── feishu_abc123.jsonl        # 飞书会话
```

### 2.2 各层职责对比

| 层级 | 文件 | 存储内容 | 更新方式 | 使用场景 |
|------|-------|----------|----------|----------|
| **活跃会话** | `sessions/*.jsonl` | 完整对话历史（含工具调用、时间戳） | 每条消息后追加 | 当前对话、最近上下文 |
| **长期记忆** | `memory/MEMORY.md` | 结构化事实（用户信息、偏好、项目上下文） | LLM 智能整合时覆盖 | 系统提示词、跨会话持久化 |
| **历史日志** | `memory/HISTORY.md` | 时间线摘要（事件、决策、话题） | LLM 智能整合时追加 | 历史搜索、回顾 |

### 2.3 数据生命周期

```
消息进入系统
    ↓
添加到 Session.messages（活跃会话层）
    ↓
保存到 sessions/xxx.jsonl（持久化）
    ↓
检查是否触发整合条件
    ├─→ 是：执行记忆整合
    │       ↓
    │   LLM 分析对话
    │       ↓
    │   生成 history_entry（摘要）
    │   ↓
    │   生成 memory_update（更新）
    │       ↓
    │   ├─→ 追加到 HISTORY.md（历史日志层）
    │   └─→ 覆盖 MEMORY.md（长期记忆层）
    │
    └─→ 否：继续累积消息
```

---

## 3. MemoryStore 类详解

### 3.1 类定义

```python
class MemoryStore:
    """
    双层记忆系统：
    - MEMORY.md：长期记忆（结构化事实）
    - HISTORY.md：历史日志（可搜索的时间线）
    """
    
    def __init__(self, workspace: Path):
        self.memory_dir = workspace / "memory"
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"
```

### 3.2 三个核心方法

#### 3.2.1 读取长期记忆

```python
def read_long_term(self) -> str:
    """
    读取 MEMORY.md 的完整内容
    
    Returns:
        MEMORY.md 的文本内容，如果文件不存在返回空字符串
    """
    if self.memory_file.exists():
        return self.memory_file.read_text(encoding="utf-8")
    return ""
```

**使用场景**：
- 在构建系统提示词时读取
- 将长期记忆注入到 LLM 上下文

**示例**：
```python
memory = MemoryStore(workspace)

# 读取长期记忆
long_term = memory.read_long_term()

# 结果示例：
# """
# # 长期记忆
#
# ## 用户信息
# - 姓名：张三
# - 邮箱：zhangsan@example.com
#
# ## 偏好设置
# - 沟通风格：随意，喜欢用表情
# - 编程语言：Python, TypeScript
# """
```

#### 3.2.2 写入长期记忆

```python
def write_long_term(self, content: str) -> None:
    """
    完全覆盖 MEMORY.md
    
    Args:
        content: 新的长期记忆内容（完整替换旧内容）
    """
    self.memory_file.write_text(content, encoding="utf-8")
```

**重要特性**：
- **完全覆盖**：不是追加，而是替换整个文件
- **LLM 驱动**：由 LLM 智能生成新内容，保留旧信息的同时添加新信息

**使用场景**：
- 记忆整合完成后更新长期记忆
- 手动编辑记忆文件

#### 3.2.3 追加历史记录

```python
def append_history(self, entry: str) -> None:
    """
    追加一条历史记录到 HISTORY.md
    
    Args:
        entry: 历史记录条目（通常是 2-5 句话的摘要）
    """
    with open(self.history_file, "a", encoding="utf-8") as f:
        f.write(entry.rstrip() + "\n\n")  # 注意：追加模式 + 双换行
```

**重要特性**：
- **追加模式**：使用 `"a"` 模式打开文件，不覆盖已有内容
- **格式化**：每条记录后加两个换行，便于阅读
- **累积增长**：HISTORY.md 会不断增长，记录所有历史事件

**使用场景**：
- 每次记忆整合时添加新摘要
- 创建可搜索的历史时间线

#### 3.2.4 获取记忆上下文

```python
def get_memory_context(self) -> str:
    """
    获取记忆上下文，用于注入到系统提示词
    
    Returns:
        格式化的记忆内容，如果为空返回空字符串
    """
    long_term = self.read_long_term()
    return f"## Long-term Memory\n{long_term}" if long_term else ""
```

**使用场景**：
- 在 `ContextBuilder.build_system_prompt()` 中调用
- 将长期记忆注入到 LLM 的系统提示词中

---

## 4. SessionManager 类详解

### 4.1 Session 数据结构

```python
@dataclass
class Session:
    """
    对话会话数据结构
    
    设计要点：
    - messages 只增不减：保留完整历史，便于 LLM 缓存
    - last_consolidated：追踪已整合的消息数量
    - JSONL 持久化：每行一条 JSON，易于流式处理
    """
    key: str                              # 会话键，格式："channel:chat_id"
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now())
    metadata: dict[str, Any] = field(default_factory=dict)
    last_consolidated: int = 0              # 已整合到文件的消息数量
```

**关键字段说明**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `key` | str | 会话唯一标识 | `"cli:direct"`, `"telegram:123456"` |
| `messages` | list | 完整对话历史 | `[{"role": "user", "content": "你好"}, ...]` |
| `last_consolidated` | int | 已整合的消息数 | `20` 表示前 20 条消息已整合 |
| `created_at` | datetime | 会话创建时间 | `2026-02-26T10:30:00` |
| `metadata` | dict | 元数据（可自定义） | `{"user_name": "张三"}` |

### 4.2 SessionManager 核心方法

#### 4.2.1 初始化和路径管理

```python
class SessionManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_dir = workspace / "sessions"  # 新路径：workspace/sessions/
        self.legacy_sessions_dir = Path.home() / ".nanobot" / "sessions"  # 旧路径
        self._cache: dict[str, Session] = {}  # 内存缓存
    
    def _get_session_path(self, key: str) -> Path:
        """获取会话文件路径（新路径）"""
        safe_key = safe_filename(key.replace(":", "_"))  # "cli:direct" → "cli_direct"
        return self.sessions_dir / f"{safe_key}.jsonl"
    
    def _get_legacy_session_path(self, key: str) -> Path:
        """获取旧版会话文件路径（兼容迁移）"""
        safe_key = safe_filename(key.replace(":", "_"))
        return self.legacy_sessions_dir / f"{safe_key}.jsonl"
```

**路径说明**：
- **新路径**：`workspace/sessions/` - 与项目代码在一起
- **旧路径**：`~/.nanobot/sessions/` - 全局目录（旧版本）
- **自动迁移**：首次加载时会自动从旧路径迁移到新路径

#### 4.2.2 获取或创建会话

```python
def get_or_create(self, key: str) -> Session:
    """
    获取现有会话或创建新会话
    
    流程：
    1. 检查内存缓存
    2. 从磁盘加载（如果缓存未命中）
    3. 创建新会话（如果文件不存在）
    4. 存入缓存并返回
    
    Args:
        key: 会话键，通常是 "channel:chat_id"
    
    Returns:
        Session 对象
    """
    # 1. 检查缓存
    if key in self._cache:
        return self._cache[key]
    
    # 2. 尝试从磁盘加载
    session = self._load(key)
    if session is None:
        # 3. 创建新会话
        session = Session(key=key)
    
    # 4. 存入缓存
    self._cache[key] = session
    return session
```

**使用示例**：
```python
session_manager = SessionManager(workspace)

# 获取 CLI 会话
session1 = session_manager.get_or_create("cli:direct")

# 获取 Telegram 会话
session2 = session_manager.get_or_create("telegram:123456")

# 两个会话在内存中是独立的
session1.add_message("user", "你好")
session2.add_message("user", "Hi")
# 互不影响
```

#### 4.2.3 从磁盘加载会话

```python
def _load(self, key: str) -> Session | None:
    """
    从磁盘加载会话（JSONL 格式）
    
    JSONL 文件格式：
    第一行：元数据（_type="metadata"）
    后续行：消息（role, content, timestamp, tools_used 等）
    """
    path = self._get_session_path(key)
    
    # 处理旧路径迁移
    if not path.exists():
        legacy_path = self._get_legacy_session_path(key)
        if legacy_path.exists():
            shutil.move(str(legacy_path), str(path))
            logger.info(f"会话 {key} 已从旧路径迁移")
    
    if not path.exists():
        return None
    
    try:
        messages = []
        metadata = {}
        created_at = None
        last_consolidated = 0
        
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                data = json.loads(line)
                
                if data.get("_type") == "metadata":
                    # 元数据行
                    metadata = data.get("metadata", {})
                    created_at = datetime.fromisoformat(data["created_at"])
                    last_consolidated = data.get("last_consolidated", 0)
                else:
                    # 消息行
                    messages.append(data)
        
        return Session(
            key=key,
            messages=messages,
            created_at=created_at or datetime.now(),
            metadata=metadata,
            last_consolidated=last_consolidated
        )
    except Exception as e:
        logger.warning(f"加载会话 {key} 失败: {e}")
        return None
```

**JSONL 文件示例**：
```jsonl
{"_type":"metadata","created_at":"2026-02-26T10:30:00","updated_at":"2026-02-26T11:00:00","metadata":{},"last_consolidated":20}
{"role":"user","content":"你好","timestamp":"2026-02-26T10:30:00"}
{"role":"assistant","content":"你好！有什么我可以帮你的吗？","timestamp":"2026-02-26T10:30:01"}
{"role":"user","content":"帮我分析一下记忆系统","timestamp":"2026-02-26T10:30:02"}
{"role":"assistant","content":"好的，我来详细解释记忆系统...","tools_used":["read_file","web_search"],"timestamp":"2026-02-26T10:30:03"}
```

**第一行元数据**：
- `_type: "metadata"` - 标识这是元数据行
- `created_at`, `updated_at` - 时间戳
- `last_consolidated` - 已整合的消息数量
- `metadata` - 自定义元数据

**后续行消息**：
- `role` - "user" 或 "assistant"
- `content` - 消息内容
- `timestamp` - 时间戳
- `tools_used` - 使用的工具列表（可选）
- `tool_calls` - 工具调用详情（可选）

#### 4.2.4 保存会话到磁盘

```python
def save(self, session: Session) -> None:
    """
    保存会话到磁盘（JSONL 格式）
    
    流程：
    1. 写入元数据行
    2. 写入所有消息行
    3. 更新内存缓存
    """
    path = self._get_session_path(session.key)
    
    with open(path, "w") as f:
        # 1. 写入元数据行
        metadata_line = {
            "_type": "metadata",
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata,
            "last_consolidated": session.last_consolidated
        }
        f.write(json.dumps(metadata_line) + "\n")
        
        # 2. 写入所有消息行
        for msg in session.messages:
            f.write(json.dumps(msg) + "\n")
    
    # 3. 更新缓存
    self._cache[session.key] = session
```

**写入示例**：
```python
session = session_manager.get_or_create("cli:direct")
session.add_message("user", "你好")
session.add_message("assistant", "你好！")
session_manager.save(session)

# 写入文件：sessions/cli_direct.jsonl
# {"_type":"metadata",...}
# {"role":"user","content":"你好","timestamp":"2026-02-26T10:30:00"}
# {"role":"assistant","content":"你好！","timestamp":"2026-02-26T10:30:01"}
```

#### 4.2.5 添加消息到会话

```python
# Session 类的方法
def add_message(self, role: str, content: str, **kwargs: Any) -> None:
    """
    添加一条消息到会话
    
    Args:
        role: "user" 或 "assistant"
        content: 消息内容
        **kwargs: 额外字段（tools_used, tool_calls 等）
    """
    msg = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        **kwargs
    }
    self.messages.append(msg)  # 只增不减！
    self.updated_at = datetime.now()
```

**使用示例**：
```python
session.add_message("user", "你好")

session.add_message(
    "assistant", 
    "你好！",
    tools_used=["web_search"]
)

session.add_message(
    "assistant",
    "我已经完成了搜索",
    tool_calls=[{"id": "call_123", "type": "function", ...}]
)
```

#### 4.2.6 获取对话历史

```python
def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
    """
    获取最近的 N 条消息（LLM 格式）
    
    重要：保留工具元数据，便于 LLM 理解工具调用链
    
    Args:
        max_messages: 最多返回的消息数（默认 500）
    
    Returns:
        LLM 格式的消息列表
    """
    out: list[dict[str, Any]] = []
    
    # 只取最后的 max_messages 条
    for m in self.messages[-max_messages:]:
        entry: dict[str, Any] = {
            "role": m["role"],
            "content": m.get("content", "")
        }
        
        # 保留工具元数据
        for k in ("tool_calls", "tool_call_id", "name"):
            if k in m:
                entry[k] = m[k]
        
        out.append(entry)
    
    return out
```

**返回格式**：
```python
history = session.get_history(max_messages=10)

# 结果：
# [
#   {"role": "user", "content": "你好"},
#   {"role": "assistant", "content": "你好！有什么我可以帮你的吗？"},
#   {"role": "user", "content": "帮我搜索"},
#   {"role": "assistant", "content": "我来搜索...", "tool_calls": [...]},
#   ...
# ]
```

#### 4.2.7 清空会话

```python
def clear(self) -> None:
    """
    清空所有消息并重置会话状态
    
    用途：
    - 用户输入 /new 命令时
    - 开始全新对话时
    """
    self.messages = []  # 清空消息列表
    self.last_consolidated = 0  # 重置整合状态
    self.updated_at = datetime.now()
```

---

## 5. 记忆整合流程

### 5.1 整合触发条件

在 `AgentLoop._process_message()` 中：

```python
async def _process_message(self, msg: InboundMessage, ...) -> OutboundMessage:
    session = self.sessions.get_or_create(session_key or msg.session_key)
    
    # 检查斜杠命令
    cmd = msg.content.strip().lower()
    
    # ┌─────────────────────────────────────────────────┐
    # │ 条件 1：用户输入 /new 命令              │
    # └─────────────────────────────────────────────────┘
    if cmd == "/new":
        # 捕获消息，避免竞态条件
        messages_to_archive = session.messages.copy()
        session.clear()  # 清空消息
        self.sessions.save(session)
        
        # 触发整合（archive_all=True）
        asyncio.create_task(
            self._consolidate_memory(session, archive_all=True)
        )
        
        return OutboundMessage(
            content="新会话已开始。记忆整合正在进行中。"
        )
    
    # ┌─────────────────────────────────────────────────┐
    # │ 条件 2：会话超过记忆窗口（默认 50 条）   │
    # └─────────────────────────────────────────────────┘
    if len(session.messages) > self.memory_window:  # 默认 50
        # 触发整合（archive_all=False）
        asyncio.create_task(
            self._consolidate_memory(session, archive_all=False)
        )
```

**两种触发模式对比**：

| 触发条件 | archive_all | 处理范围 | last_consolidated 设置 | 使用场景 |
|-----------|-------------|----------|---------------------|----------|
| `/new` 命令 | `True` | 所有消息 | `0` | 开始全新对话 |
| 消息数 > 50 | `False` | 部分旧消息 | `len(messages) - 25` | 自动维护会话长度 |

### 5.2 记忆整合核心方法

```python
async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
    """
    将旧消息整合到 MEMORY.md 和 HISTORY.md
    
    整合流程：
    1. 确定需要处理的消息范围
    2. 格式化消息为文本
    3. 读取当前长期记忆
    4. 调用 LLM 分析对话
    5. 解析 LLM 响应
    6. 更新 MEMORY.md（覆盖）和 HISTORY.md（追加）
    7. 更新会话的 last_consolidated
    """
    
    memory = MemoryStore(self.workspace)
    
    # ──────────────────────────────────────────────────
    # 步骤 1：确定需要处理的消息
    # ──────────────────────────────────────────────────
    
    if archive_all:
        # /new 命令：整合所有消息
        old_messages = session.messages
        keep_count = 0
        logger.info(
            f"记忆整合（archive_all）："
            f"总计 {len(session.messages)} 条消息"
        )
    else:
        # 正常情况：保留前半部分，整合后半部分
        keep_count = self.memory_window // 2  # 50 // 2 = 25
        
        # 不需要整合
        if len(session.messages) <= keep_count:
            logger.debug(
                f"会话 {session.key}：不需要整合 "
                f"（消息数={len(session.messages)}, 保留={keep_count}）"
            )
            return
        
        # 获取需要整合的消息
        messages_to_process = (
            len(session.messages) - session.last_consolidated
        )
        if messages_to_process <= 0:
            logger.debug(
                f"会话 {session.key}：没有新消息需要整合 "
                f"（last_consolidated={session.last_consolidated}, "
                f"总计={len(session.messages)}）"
            )
            return
        
        # 从上次整合点到保留边界
        old_messages = session.messages[
            session.last_consolidated:-keep_count
        ]
        
        if not old_messages:
            return
        
        logger.info(
            f"记忆整合开始：总计 {len(session.messages)} 条, "
            f"新需整合 {len(old_messages)} 条, "
            f"保留 {keep_count} 条"
        )
    
    # ──────────────────────────────────────────────────
    # 步骤 2：格式化消息为文本
    # ──────────────────────────────────────────────────
    
    lines = []
    for m in old_messages:
        if not m.get("content"):
            continue
        
        # 添加工具使用信息
        tools = ""
        if m.get("tools_used"):
            tools = f" [tools: {', '.join(m['tools_used'])}]"
        
        # 格式：[时间戳] 角色[工具]: 内容
        lines.append(
            f"[{m.get('timestamp', '?')[:16]}] "
            f"{m['role'].upper()}{tools}: {m['content']}"
        )
    
    conversation = "\n".join(lines)
    
    # ──────────────────────────────────────────────────
    # 步骤 3：读取当前长期记忆
    # ──────────────────────────────────────────────────
    
    current_memory = memory.read_long_term()
    
    # ──────────────────────────────────────────────────
    # 步骤 4：构建 LLM 提示词
    # ──────────────────────────────────────────────────
    
    prompt = f"""You are a memory consolidation agent. Process this conversation and return a JSON object with exactly two keys:

1. "history_entry": A paragraph (2-5 sentences) summarizing the key events/decisions/topics. Start with a timestamp like [YYYY-MM-DD HH:MM]. Include enough detail to be useful when found by grep search later.

2. "memory_update": The updated long-term memory content. Add any new facts: user location, preferences, personal info, habits, project context, technical decisions, tools/services used. If nothing new, return the existing content unchanged.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{conversation}

Respond with ONLY valid JSON, no markdown fences."""
    
    # ──────────────────────────────────────────────────
    # 步骤 5：调用 LLM 分析对话
    # ──────────────────────────────────────────────────
    
    try:
        response = await self.provider.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a memory consolidation agent. "
                               "Respond only with valid JSON."
                },
                {"role": "user", "content": prompt},
            ],
            model=self.model,
        )
        
        text = (response.content or "").strip()
        
        # 移除可能的 markdown 代码块标记
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        
        # ──────────────────────────────────────────────────
        # 步骤 6：解析 LLM 响应
        # ──────────────────────────────────────────────────
        
        result = json_repair.loads(text)
        
        if not isinstance(result, dict):
            logger.warning(
                f"记忆整合：响应类型错误，跳过。响应: {text[:200]}"
            )
            return
        
        # ──────────────────────────────────────────────────
        # 步骤 7：更新记忆文件
        # ──────────────────────────────────────────────────
        
        # 追加历史日志
        if entry := result.get("history_entry"):
            memory.append_history(entry)
        
        # 更新长期记忆
        if update := result.get("memory_update"):
            if update != current_memory:
                memory.write_long_term(update)
        
        # ──────────────────────────────────────────────────
        # 步骤 8：更新会话状态
        # ──────────────────────────────────────────────────
        
        if archive_all:
            session.last_consolidated = 0
        else:
            session.last_consolidated = (
                len(session.messages) - keep_count
            )
        
        logger.info(
            f"记忆整合完成：{len(session.messages)} 条消息, "
            f"last_consolidated={session.last_consolidated}"
        )
        
    except Exception as e:
        logger.error(f"记忆整合失败: {e}")
```

### 5.3 LLM 提示词详解

**提示词结构**：

```
System Prompt（系统提示）:
You are a memory consolidation agent. Respond only with valid JSON.

User Prompt（用户提示）:
You are a memory consolidation agent. Process this conversation and return a JSON object with exactly two keys:

1. "history_entry": 
   - 摘要段落（2-5 句话）
   - 必须包含时间戳：[YYYY-MM-DD HH:MM]
   - 包含足够的细节，便于 grep 搜索

2. "memory_update":
   - 更新后的长期记忆内容
   - 添加新事实：用户位置、偏好、个人信息、习惯、项目上下文
   - 如果没有新信息，返回现有内容

## Current Long-term Memory
{当前长期记忆内容}

## Conversation to Process
{需要整合的对话}

Respond with ONLY valid JSON, no markdown fences.
```

**提示词设计要点**：

| 要点 | 说明 |
|------|------|
| 明确输出格式 | 要求返回 JSON 对象，包含 `history_entry` 和 `memory_update` |
| 时间戳要求 | `history_entry` 必须包含 `[YYYY-MM-DD HH:MM]` 格式的时间戳 |
| 摘要长度 | 2-5 句话，简洁但包含足够细节 |
| 新事实提取 | 明确列出需要提取的信息类型（位置、偏好、项目等） |
| 保留旧内容 | 如果没有新信息，返回现有内容不变 |
| 纯 JSON 输出 | 禁止 markdown 代码块标记（虽然代码中做了容错处理） |

**LLM 响应示例**：

```json
{
  "history_entry": "[2026-02-26 10:30] User asked for explanation of nanobot's memory system. I provided detailed breakdown of the three-layer architecture, including MEMORY.md for long-term facts, HISTORY.md for searchable logs, and sessions/*.jsonl for active conversations. User followed up with questions about consolidation logic.",
  "memory_update": "# 长期记忆\n\n## 用户信息\n- 姓名：张三\n- 邮箱：zhangsan@example.com\n\n## 学习状态\n- 正在学习 nanobot 记忆系统\n- 对记忆整合流程特别感兴趣\n- 偏好详细的技术解释"
}
```

### 5.4 整合结果文件示例

#### HISTORY.md（历史日志）

```markdown
[2026-02-26 09:00] USER: 早安
[2026-02-26 09:00] ASSISTANT: 早安！今天有什么我可以帮你的吗？
[2026-02-26 10:30] USER [tools: web_search]: 帮我查一下今天天气
[2026-02-26 10:31] ASSISTANT [tools: web_search]: 北京今天晴转多云，气温 15-25°C
[2026-02-26 14:00] USER: 帮我写个 Python 脚本
[2026-02-26 14:05] ASSISTANT [tools: write_file]: 我已经创建了脚本
[2026-02-26 14:10] USER: 谢谢
[2026-02-26 14:10] ASSISTANT: 不客气！

---

[2026-02-26 10:30] User asked for explanation of nanobot's memory system. I provided detailed breakdown of the three-layer architecture, including MEMORY.md for long-term facts, HISTORY.md for searchable logs, and sessions/*.jsonl for active conversations. User followed up with questions about consolidation logic, which I explained with flow diagrams and code examples. The discussion covered memory storage, session management, consolidation triggers, and LLM-driven information extraction.

---

[2026-02-27 09:00] USER: 昨天讨论了什么？
[2026-02-27 09:01] ASSISTANT [tools: read_file]: 我来帮你查看历史记录...
```

**HISTORY.md 特点**：
- **时间线格式**：每条记录都有时间戳
- **可搜索**：便于使用 `grep` 搜索历史事件
- **增量追加**：不断增长，记录所有重要对话
- **双换行分隔**：每次整合后用 `---` 分隔

#### MEMORY.md（长期记忆）

```markdown
# 长期记忆

## 用户信息
- 姓名：张三
- 邮箱：zhangsan@example.com
- 时区：Asia/Shanghai

## 偏好设置
- 沟通风格：随意，喜欢用表情
- 编程语言：Python, TypeScript
- AI 模型：偏好 Claude 3.5 Sonnet

## 学习状态
- 正在学习 nanobot 的记忆系统
- 对记忆整合流程特别感兴趣
- 偏好详细的技术解释和代码示例

## 项目上下文
- 当前项目：nanobot 架构分析
- 项目路径：/Users/zhangsan/project/nanobot
- 使用 Docker 进行部署
- 集成了 Telegram 和 Discord 两个渠道

## 重要笔记
- 用户喜欢看到完整的代码示例
- 对记忆的存储和整合机制有深入研究需求
```

**MEMORY.md 特点**：
- **结构化格式**：清晰的标题层次
- **分类明确**：用户信息、偏好、项目上下文等分类
- **完全覆盖**：每次整合完全替换，不是追加
- **跨会话持久化**：不同会话共享同一份长期记忆

---

## 6. 记忆使用流程

### 6.1 记忆注入到系统提示词

在 `ContextBuilder.build_system_prompt()` 中：

```python
def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
    parts = []
    
    # 1. 核心身份
    parts.append(self._get_identity())
    
    # 2. 引导文件（AGENTS.md, SOUL.md, USER.md）
    bootstrap = self._load_bootstrap_files()
    if bootstrap:
        parts.append(bootstrap)
    
    # 3. ──────────────────────────────────────────
    #    记忆上下文注入（关键步骤！）
    # ──────────────────────────────────────────
    memory = self.memory.get_memory_context()
    if memory:
        parts.append(f"# Memory\n\n{memory}")
    
    # 4. 技能...
    
    return "\n\n---\n\n".join(parts)
```

**系统提示词中的记忆部分**：

```markdown
---

# Memory

## Long-term Memory

# 长期记忆

## 用户信息
- 姓名：张三
- 邮箱：zhangsan@example.com
- 时区：Asia/Shanghai

## 偏好设置
- 沟通风格：随意，喜欢用表情 😊
- 编程语言：Python, TypeScript
- AI 模型：偏好 Claude 3.5 Sonnet

## 项目上下文
- 当前项目：nanobot 架构分析
- 项目路径：/Users/zhangsan/project/nanobot
- 使用 Docker 进行部署

---
```

**注入效果**：
- LLM 在每次对话时都能访问长期记忆
- 跨会话保持上下文一致性
- 自动记住用户偏好和信息

### 6.2 记忆搜索和使用

用户可以通过 `read_file` 工具搜索历史记录：

```python
# 用户输入："查看昨天讨论了什么"

# LLM 上下文包含：
# 1. 长期记忆（知道用户的项目、偏好等）
# 2. 最近 50 条对话历史
# 3. 可用工具列表（包括 read_file）

# LLM 决定：
# "我需要查看 HISTORY.md 来找到昨天的讨论"

# LLM 调用工具：
read_file(file_path="workspace/memory/HISTORY.md")

# 返回 HISTORY.md 内容给 LLM
# LLM 找到相关条目并回答用户
```

**HISTORY.md 搜索示例**：

```bash
# 用户可以手动搜索
grep "昨天" workspace/memory/HISTORY.md
grep "记忆" workspace/memory/HISTORY.md
grep "2026-02-26" workspace/memory/HISTORY.md

# LLM 也可以通过 read_file 工具读取后搜索
```

---

## 7. 完整流程图

### 7.1 消息处理和记忆整合流程

```
用户发送消息
    │
    ├─→ AgentLoop._process_message()
    │       │
    │       ├─→ SessionManager.get_or_create(session_key)
    │       │       │
    │       │       ├─→ 检查内存缓存 (_cache)
    │       │       │   ↓ (命中）
    │       │       │   返回缓存的 Session
    │       │       │
    │       │       └─→ 未命中
    │       │           ↓
    │       │       SessionManager._load(session_key)
    │       │           ↓
    │       │       读取 sessions/xxx.jsonl
    │       │           ↓
    │       │       返回 Session(messages, last_consolidated)
    │       │
    │       ├─→ Session.add_message("user", msg)
    │       │       ↓
    │       │   session.messages.append({
    │       │       "role": "user",
    │       │       "content": msg,
    │       │       "timestamp": now
    │       │   })
    │       │
    │       ├─→ ContextBuilder.build_messages()
    │       │       │
    │       │       ├─→ MemoryStore.get_memory_context()
    │       │       │       ↓
    │       │       │   读取 memory/MEMORY.md
    │       │       │       ↓
    │       │       │   返回 "## Long-term Memory\n..."
    │       │       │       ↓
    │       │       │   注入到系统提示词
    │       │       │
    │       │       ├─→ Session.get_history(memory_window=50)
    │       │       │       ↓
    │       │       │   返回最近 50 条消息
    │       │       │
    │       │       └─→ 构建完整消息列表
    │       │           [system_prompt, history_50, user_message]
    │       │
    │       ├─→ 运行 Agent 循环
    │       │       │
    │       │       ├─→ LLM.chat(messages, tools, ...)
    │       │       │       │
    │       │       │       LLM 收到：
    │       │       │       ├─ 系统提示词（含长期记忆）
    │       │       │       ├─ 最近 50 条对话历史
    │       │       │       └─ 用户新消息
    │       │       │       ↓
    │       │       │   生成响应（可能调用工具）
    │       │       │       ↓
    │       │       │   返回 response.content
    │       │       │
    │       │       └─→ 生成响应
    │       │
    │       ├─→ Session.add_message("assistant", response, tools_used=...)
    │       │       ↓
    │       │   session.messages.append({
    │       │       "role": "assistant",
    │       │       "content": response,
    │       │       "tools_used": ["web_search", ...]
    │       │   })
    │       │
    │       └─→ SessionManager.save(session)
    │               ↓
    │           写入 sessions/xxx.jsonl
    │           ├─→ 元数据行（更新 last_consolidated）
    │           └─→ 所有消息行（包括新消息）
    │
    └─→ 检查是否触发记忆整合
            │
            ├─→ /new 命令？
            │   ↓ (是）
            │   Session.clear()
            │       ↓
            │       messages = []
            │       last_consolidated = 0
            │       ↓
            │   SessionManager.save(session)  # 保存清空后的会话
            │       ↓
            │   _consolidate_memory(archive_all=True)
            │       │
            │       ├─→ 获取所有消息
            │       │       old_messages = session.messages.copy()
            │       │
            │       ├─→ 格式化为文本
            │       │       lines = []
            │       │       for msg in old_messages:
            │       │           lines.append(f"[timestamp] {role}: {content}")
            │       │       conversation = "\n".join(lines)
            │       │
            │       ├─→ 读取当前记忆
            │       │       current_memory = memory.read_long_term()
            │       │
            │       ├─→ 调用 LLM 分析
            │       │       result = await provider.chat(
            │       │           messages=[system, user_prompt],
            │       │           model=model
            │       │       )
            │       │       # LLM 返回：
            │       │       # {
            │       │       #   "history_entry": "[2026-02-26 10:30] ...",
            │       │       #   "memory_update": "# 长期记忆\n..."
            │       │       # }
            │       │
            │       ├─→ 解析 LLM 响应
            │       │       result = json_repair.loads(text)
            │       │
            │       ├─→ 更新文件
            │       │       ├─→ memory.append_history(result["history_entry"])
            │       │       │   # 追加到 HISTORY.md
            │       │       │   # [2026-02-26 10:30] ...
            │       │       │   # ---
            │       │       │
            │       │       └─→ memory.write_long_term(result["memory_update"])
            │       │           # 完全覆盖 MEMORY.md
            │       │
            │       └─→ 更新会话状态
            │           session.last_consolidated = 0
            │
            └─→ 消息数 > memory_window (50)？
                ↓ (是）
                _consolidate_memory(archive_all=False)
                │
                ├─→ 计算需要整合的消息
                │       keep_count = 25
                │       old_messages = session.messages[last_consolidated:-25]
                │       # 假设：session.messages 有 60 条
                │       # last_consolidated = 20
                │       # 则：old_messages = session.messages[20:35] (15 条)
                │
                ├─→ 格式化、调用 LLM、解析
                │       （同上）
                │
                ├─→ 更新文件
                │       ├─→ memory.append_history(entry)
                │       └─→ memory.write_long_term(update)
                │
                └─→ 更新会话状态
                    session.last_consolidated = 60 - 25 = 35
                    # 标记前 35 条消息已整合
                    # 剩余 25 条仍在会话中
```

### 7.2 会话生命周期

```
会话创建
    │
    ├─→ SessionManager.get_or_create(key)
    │       ↓
    │   key 不在缓存
    │       ↓
    │   SessionManager._load(key)
    │       ↓
    │   sessions/xxx.jsonl 不存在
    │       ↓
    │   创建新 Session(messages=[], last_consolidated=0)
    │       ↓
    │   存入缓存
    │       ↓
    返回新会话
    │
    ↓
对话进行中
    │
    ├─→ 每条消息：Session.add_message()
    │       ↓
    │   messages.append(...)
    │       ↓
    │   SessionManager.save(session)
    │       ↓
    │   写入 sessions/xxx.jsonl
    │
    ↓
检查整合条件
    │
    ├─→ 消息数 < 50
    │   │   不整合，继续累积
    │   │
    │   ↓
    │   消息数 = 51
    │   ↓
    ├─→ 触发整合（archive_all=False）
    │   │
    │   ├─→ old_messages = messages[25:50] (25 条）
    │   ├─→ 整合到 MEMORY.md 和 HISTORY.md
    │   ├─→ last_consolidated = 35
    │   │
    │   ↓
    │   会话中剩余 25 条消息
    │   │
    │   ↓
    │   消息数 = 51（整合后不减少！）
    │   │
    │   ↓
    │   消息数 = 52, 53, ..., 75
    │   │
    │   ↓
    │   再次触发整合
    │   │   ├─→ old_messages = messages[35:50] (15 条）
    │   │   ├─→ 整合到 MEMORY.md 和 HISTORY.md
    │   │   └─→ last_consolidated = 50
    │
    └─→ 用户输入 /new 命令
        │
        ├─→ Session.clear()
        │       messages = []
        │       last_consolidated = 0
        │
        ├─→ 触发整合（archive_all=True）
        │       ├─→ old_messages = 所有消息
        │       ├─→ 整合到 MEMORY.md 和 HISTORY.md
        │       └─→ last_consolidated = 0
        │
        └─→ 会话重置
```

---

## 8. 设计亮点分析

### 8.1 三层记忆架构的优势

| 层级 | 优势 | 具体体现 |
|------|------|----------|
| **活跃会话** | 快速访问、最近上下文 | 内存缓存 + JSONL 持久化 |
| **长期记忆** | 跨会话持久化、结构化 | 注入到系统提示词、自动更新 |
| **历史日志** | 可搜索、时间线 | 增量追加、grep 友好 |

**为什么需要三层？**

```
问题：如果只有一层会话存储会怎样？

方案 A：只保留 sessions/*.jsonl
├─ 优点：简单
└─ 缺点：
    ├─ 会话无限增长，性能下降
    ├─ 无法跨会话共享记忆
    └─ 每次都需要加载完整历史

方案 B：只保留 MEMORY.md
├─ 优点：跨会话共享
└─ 缺点：
    ├─ 缺少时间线细节
    ├─ 无法搜索历史事件
    └─ 频繁覆盖可能丢失信息

✅ nanobot 方案：三层互补
├─ 活跃会话：快速、详细、最近
├─ 长期记忆：结构化、持久、跨会话
└─ 历史日志：可搜索、时间线、累积
```

### 8.2 增量整合机制

```python
# last_consolidated 字段的作用

# 示例场景
session.messages = [
    msg_1, msg_2, ..., msg_20,  # 已整合
    msg_21, msg_22, ..., msg_50,  # 新消息
]
session.last_consolidated = 20

# 第一次整合（消息数达到 50）
old_messages = session.messages[20:25]  # 只处理新消息 21-25
# 整合后
session.last_consolidated = 35

# 对话继续，消息数增长到 75
old_messages = session.messages[35:50]  # 处理消息 36-50
# 整合后
session.last_consolidated = 50
```

**优势**：
1. **避免重复处理**：每条消息只整合一次
2. **LLM 效率**：每次只处理新消息，输入更小
3. **增量更新**：长期记忆逐步累积，不会突然丢失

### 8.3 LLM 驱动的信息提取

```python
# 传统方案：规则提取
def extract_memory_by_rules(messages):
    memory = {}
    for msg in messages:
        if "我叫" in msg:
            memory["name"] = msg.split("我叫")[1]
        elif "住在" in msg:
            memory["location"] = msg.split("住在")[1]
    return memory

# 问题：
# - 规则有限，覆盖不全
# - 需要预先定义所有模式
# - 无法理解上下文

# ✅ nanobot 方案：LLM 提取
prompt = """
Process this conversation and return JSON:
1. "history_entry": Summary with timestamp
2. "memory_update": Updated memory with new facts
"""
result = await llm.chat(prompt)

# 优势：
# - 自动理解各种表达方式
# - 提取隐含信息
# - 生成自然的总结
```

### 8.4 异步整合不阻塞

```python
async def _process_message(self, msg, ...):
    # ... 处理消息 ...
    
    # 检查整合条件
    if len(session.messages) > self.memory_window:
        # 创建后台任务
        asyncio.create_task(self._consolidate_memory(session))
    
    # 立即返回响应给用户
    return response  # 不等待整合完成！
```

**效果**：
```
用户：你好！
AI：你好！有什么我可以帮你的吗？
[后台：正在整合记忆...]
用户：帮我写个脚本
AI：好的，我来写...
[后台：记忆整合完成，更新了 MEMORY.md 和 HISTORY.md]
```

**用户体验**：
- 响应迅速，不等待整合
- 整合在后台静默进行
- 不影响对话流畅性

### 8.5 JSONL 格式的优势

```python
# JSONL (每行一个 JSON）
{"role":"user","content":"你好","timestamp":"2026-02-26T10:30:00"}
{"role":"assistant","content":"你好！","timestamp":"2026-02-26T10:30:01"}

# vs JSON 数组
[
  {"role":"user","content":"你好","timestamp":"2026-02-26T10:30:00"},
  {"role":"assistant","content":"你好！","timestamp":"2026-02-26T10:30:01"}
]
```

**JSONL 优势**：
1. **流式读取**：可以逐行读取，无需加载整个文件
2. **增量写入**：追加新消息只需追加一行
3. **容错性**：某行损坏不影响其他行
4. **内存友好**：处理大文件时不需要全部加载到内存

```python
# 流式处理示例
def load_session_large(path):
    messages = []
    with open(path) as f:
        for line in f:  # 逐行读取
            if line.strip():
                msg = json.loads(line)
                messages.append(msg)
    return messages
```

### 8.6 路径兼容性设计

```python
def _load(self, key: str) -> Session | None:
    path = self._get_session_path(key)  # workspace/sessions/
    
    # 检查旧路径
    if not path.exists():
        legacy_path = self._get_legacy_session_path(key)  # ~/.nanobot/sessions/
        if legacy_path.exists():
            shutil.move(str(legacy_path), str(path))
            logger.info(f"会话 {key} 已从旧路径迁移")
    
    if not path.exists():
        return None
    # ... 继续加载
```

**迁移场景**：

```
旧版本用户目录：
~/.nanobot/
├── config.json
└── sessions/
    ├── cli_direct.jsonl
    └── telegram_12345.jsonl

新版本：
project/workspace/
└── sessions/
    ├── cli_direct.jsonl  # 首次启动时自动迁移
    └── telegram_12345.jsonl
```

**优势**：
- 用户体验无缝升级
- 自动迁移旧数据
- 不丢失历史会话

---

## 9. 实际案例演示

### 案例 1：新用户首次对话

**场景**：用户第一次使用 nanobot，通过 CLI 对话

```
[10:00] 用户：你好，我是张三
[10:00] AI：你好张三！很高兴认识你。有什么我可以帮你的吗？
[10:01] 用户：帮我写个 Python 脚本
[10:02] AI：好的，你想要这个脚本做什么？
[10:03] 用户：用来处理 CSV 文件
[10:05] AI：我来帮你写一个 CSV 处理脚本...
[10:10] 用户：谢谢！
```

**内部流程**：

```
1. 会话创建
   ├─ SessionManager.get_or_create("cli:direct")
   ├─ 新建 Session(messages=[], last_consolidated=0)
   └─ 保存到 sessions/cli_direct.jsonl

2. 每条消息处理
   ├─ 消息 1：add_message("user", "你好，我是张三")
   ├─ 消息 2：add_message("assistant", "你好张三！...")
   ├─ ... 继续添加消息
   ├─ 每条消息后调用 save(session)
   └─ 会话中消息数：1, 2, 3, 4, 5

3. 系统提示词构建
   ├─ MemoryStore.get_memory_context()
   │   ├─ memory/MEMORY.md 不存在
   │   └─ 返回 ""
   └─ 系统提示词中无记忆内容

4. 消息数达到 6（仍 < 50）
   ├─ 不触发整合
   └─ 继续累积消息
```

### 案例 2：触发自动整合

**场景**：对话达到 51 条消息

```
...（对话已进行 50 条消息）
[14:30] 用户：对了，我喜欢用 Python 编程
[14:31] AI：好的，记住了。
```

**内部流程**：

```
1. 检查消息数
   len(session.messages) = 51
   memory_window = 50
   条件：51 > 50 ✅ 触发整合

2. 确定整合范围
   keep_count = 50 // 2 = 25
   last_consolidated = 20（假设之前已整合过）
   
   old_messages = session.messages[20:35]  # 15 条消息
   # 保留：session.messages[0:20] + session.messages[35:51]
   # 总计：20 + 15 + 16 = 51 条

3. 格式化消息
   lines = []
   for msg in old_messages:
       tools = f" [tools: {', '.join(msg['tools_used'])}]" if msg.get("tools_used") else ""
       lines.append(f"[{msg['timestamp'][:16]}] {msg['role'].upper()}{tools}: {msg['content']}")
   conversation = "\n".join(lines)

4. 调用 LLM 分析
   prompt = f"""
   Current Long-term Memory
   {memory.read_long_term()}  # 可能为空
   
   Conversation to Process
   {conversation}  # 15 条消息的文本
   
   Return JSON with history_entry and memory_update
   """
   
   result = await provider.chat(prompt)
   # LLM 响应：
   # {
   #   "history_entry": "[2026-02-26 14:30] User mentioned they prefer Python programming...",
   #   "memory_update": "# 长期记忆\n\n## 用户信息\n- 姓名：张三\n\n## 偏好设置\n- 编程语言：Python"
   # }

5. 更新文件
   memory.append_history(result["history_entry"])
   # HISTORY.md 追加：
   # [2026-02-26 14:30] User mentioned they prefer Python programming...
   # ---
   
   memory.write_long_term(result["memory_update"])
   # MEMORY.md 覆盖：
   # # 长期记忆
   # 
   # ## 用户信息
   # - 姓名：张三
   # 
   # ## 偏好设置
   # - 编程语言：Python

6. 更新会话状态
   session.last_consolidated = 35
   # 标记前 35 条消息已整合

7. 后台执行
   asyncio.create_task(_consolidate_memory(...))
   # 不阻塞主对话，立即返回响应
```

### 案例 3：用户输入 /new 命令

**场景**：用户想开始新对话

```
[15:00] 用户：/new
[15:00] AI：新会话已开始。记忆整合正在进行中。
```

**内部流程**：

```
1. 检测到 /new 命令
   cmd = msg.content.strip().lower()  # "/new"
   
2. 清空会话
   messages_to_archive = session.messages.copy()  # 保存所有消息
   session.clear()
   # messages = []
   # last_consolidated = 0
   session_manager.save(session)
   # sessions/cli_direct.jsonl 被清空（只保留元数据行）

3. 触发完整整合（archive_all=True）
   old_messages = messages_to_archive  # 所有旧消息
   keep_count = 0
   
4. 格式化并调用 LLM
   conversation = 所有消息的文本
   result = await provider.chat(prompt)
   # LLM 返回完整的摘要和记忆更新

5. 更新文件
   memory.append_history(result["history_entry"])
   memory.write_long_term(result["memory_update"])
   # MEMORY.md 和 HISTORY.md 都被更新

6. 更新会话状态
   session.last_consolidated = 0  # 已整合所有消息

7. 返回响应
   OutboundMessage(content="新会话已开始。记忆整合正在进行中。")
```

### 案例 4：跨会话记忆共享

**场景**：用户在不同渠道对话，记忆共享

```
渠道 1：Telegram
[10:00] 用户：我叫张三
[10:00] AI：你好张三！
...
[10:10] 用户：我喜欢用 Python 编程
[10:10] AI：好的，记住了。

（消息数达到 51，触发整合）
MEMORY.md 更新：
## 用户信息
- 姓名：张三
## 偏好设置
- 编程语言：Python

---

渠道 2：CLI
[15:00] 用户：你好
[15:00] AI：你好张三！有什么我可以帮你的吗？
```

**内部流程**：

```
1. Telegram 会话整合
   - MEMORY.md 更新为包含张三的信息
   
2. 用户切换到 CLI
   session = session_manager.get_or_create("cli:direct")
   # 这是一个新会话（messages=[]）
   
3. 构建系统提示词
   system_prompt = ContextBuilder.build_system_prompt()
   # 包含：
   # ...
   # # Memory
   # 
   # ## Long-term Memory
   # 
   # # 长期记忆
   # 
   # ## 用户信息
   # - 姓名：张三
   # 
   # ## 偏好设置
   # - 编程语言：Python
   # ...
   
4. LLM 生成响应
   # LLM 从记忆中读取到用户是张三，使用自然称呼
   response = "你好张三！有什么我可以帮你的吗？"
```

**效果**：
- 不同渠道共享同一份长期记忆
- 用户信息跨会话持久化
- AI 能记住用户的偏好和上下文

---

## 10. 常见问题解答

### Q1：为什么需要三层记忆而不是一层？

**A**：每层解决不同的问题

| 层级 | 解决的问题 | 替代方案的缺点 |
|------|-----------|---------------|
| 活跃会话 | 快速访问、最近上下文 | 只保留历史：每次加载全部，性能差 |
| 长期记忆 | 跨会话共享、结构化 | 只保留会话：无法跨渠道共享 |
| 历史日志 | 可搜索、时间线 | 只保留记忆：丢失细节和可搜索性 |

**三层互补**：
- **快速访问**：活跃会话在内存中
- **持久共享**：长期记忆跨渠道可用
- **历史追溯**：HISTORY.md 可 grep 搜索

---

### Q2：为什么不删除已整合的消息？

**A**：`messages` 只增不减的设计原因

1. **LLM 缓存友好**
   - 某些 LLM（如 Claude）可以缓存对话历史
   - 只增不减保持历史完整性
   - 提升后续对话效率

2. **灵活的 `get_history()`
   ```python
   def get_history(self, max_messages=500):
       # 只返回需要的消息数
       return self.messages[-max_messages:]
   ```
   - 可以控制返回多少条
   - 不需要物理删除旧消息

3. **`last_consolidated` 追踪状态**
   - 记录哪些消息已整合
   - 避免重复整合
   - 不需要删除消息来标记

---

### Q3：为什么 MEMORY.md 是覆盖而 HISTORY.md 是追加？

**A**：不同的数据特性决定不同的更新策略

**MEMORY.md（长期记忆）**：
- **结构化事实**：姓名、偏好、项目等
- **增量更新**：LLM 生成包含旧信息和新信息的完整内容
- **覆盖原因**：
  - 事实可能变化（如项目状态）
  - 避免信息重复累积
  - 保持文件简洁

```python
# 每次整合生成完整的记忆内容
memory_update = """
# 长期记忆

## 用户信息
- 姓名：张三
- 邮箱：zhangsan@example.com  # 新增

## 偏好设置
- 编程语言：Python  # 保留
- 沟通风格：随意  # 保留
"""
memory.write_long_term(memory_update)  # 完全覆盖
```

**HISTORY.md（历史日志）**：
- **时间线记录**：每次对话的摘要
- **累积增长**：每次整合追加新条目
- **追加原因**：
  - 保留完整历史
  - 便于搜索和回顾
  - 不丢失任何历史事件

```python
# 每次整合追加新条目
entry = "[2026-02-26 14:30] User discussed Python preferences..."
memory.append_history(entry)  # 追加到文件末尾
# --- (双换行分隔）
```

---

### Q4：整合是同步还是异步？为什么？

**A**：异步整合，不阻塞对话

```python
async def _process_message(self, msg, ...):
    # ... 处理消息，生成响应 ...
    
    if len(session.messages) > self.memory_window:
        # 创建后台任务
        asyncio.create_task(self._consolidate_memory(session))
    
    # 立即返回响应，不等待整合完成
    return response
```

**用户体验对比**：

| 方案 | 用户体验 | 问题 |
|------|----------|------|
| **同步整合** | 用户发送消息 → 等待整合 → 收到响应 | 等待时间长，体验差 |
| **异步整合** | 用户发送消息 → 立即收到响应 → [后台整合完成] | 响应快，整合不影响 |

**nanobot 选择异步**：提升用户体验

---

### Q5：如何确保记忆不会无限增长？

**A**：多重机制控制

1. **会话层面**
   ```python
   memory_window = 50  # 会话窗口大小
   # 会话最多保留完整历史（get_history 可以控制返回数量）
   ```

2. **整合机制**
   ```python
   # 每当消息数 > 50 时触发整合
   # 整合后，last_consolidated 增加
   # 下次整合只处理新消息
   ```

3. **HISTORY.md 增长**
   ```python
   # HISTORY.md 会持续增长
   # 但每次只追加摘要（2-5 句话）
   # 增长速度远慢于原始消息
   ```

4. **建议**（手动管理）
   ```bash
   # 用户可以手动清理历史
   vim workspace/memory/HISTORY.md  # 删除不需要的旧记录
   ```

---

### Q6：如果 LLM 整合失败会怎样？

**A**：容错机制保护数据

```python
try:
    response = await self.provider.chat(prompt)
    result = json_repair.loads(text)
    
    if not isinstance(result, dict):
        logger.warning(f"记忆整合：响应类型错误，跳过")
        return  # 不更新文件，但继续执行
    
    # 更新文件
    if entry := result.get("history_entry"):
        memory.append_history(entry)
    
except Exception as e:
    logger.error(f"记忆整合失败: {e}")
    # 不抛出异常，避免影响主对话
```

**保护措施**：
1. **异常捕获**：不因整合失败导致主对话中断
2. **响应验证**：检查 LLM 返回的是有效 JSON
3. **日志记录**：记录失败原因，便于调试
4. **json_repair**：容错解析，处理格式问题

---

### Q7：不同会话的记忆会冲突吗？

**A**：不会，通过 `last_consolidated` 区分

```python
# 会话 1（CLI）
session1 = Session(key="cli:direct", messages=[...], last_consolidated=20)

# 会话 2（Telegram）
session2 = Session(key="telegram:12345", messages=[...], last_consolidated=0)

# 整合时
# CLI 会话：整合 messages[20:35]，更新 MEMORY.md
# Telegram 会话：整合 messages[0:25]，更新 MEMORY.md（覆盖 CLI 的更新）
```

**潜在问题和解决方案**：

| 场景 | 问题 | 解决方案 |
|------|------|----------|
| 两会话同时整合 | 后更新的会话覆盖先更新的 | 异步任务 + 文件锁（当前未实现） |
| 用户信息冲突 | 不同会话记录不同信息 | LLM 在整合时合并信息 |
| 记忆混乱 | 不同渠道偏好冲突 | LLM 提示词要求"如果矛盾，保留最新信息" |

**当前策略**：
- 依赖 LLM 智能合并信息
- 最后更新的记忆会覆盖之前的
- 用户可以手动编辑 MEMORY.md 修正

---

### Q8：如何搜索历史记录？

**A**：两种方式

**方式 1：通过 LLM 搜索**

```
用户："昨天讨论了什么？"
    ↓
LLM 上下文包含长期记忆
    ↓
LLM 调用工具：read_file(file_path="workspace/memory/HISTORY.md")
    ↓
LLM 搜索并回答用户
```

**方式 2：手动 grep 搜索**

```bash
# 搜索特定关键词
grep "昨天" workspace/memory/HISTORY.md
grep "Python" workspace/memory/HISTORY.md
grep "2026-02-26" workspace/memory/HISTORY.md

# 使用正则表达式
grep -E "(记忆|Python)" workspace/memory/HISTORY.md

# 显示上下文
grep -C 3 "张三" workspace/memory/HISTORY.md
```

---

## 总结

### nanobot 记忆系统核心特点

| 特点 | 实现 | 优势 |
|------|------|------|
| **三层架构** | 活跃会话 + 长期记忆 + 历史日志 | 快速访问 + 持久化 + 可搜索 |
| **智能整合** | LLM 自动提取关键信息 | 理解上下文，提取隐含信息 |
| **增量更新** | `last_consolidated` 追踪已整合消息 | 避免重复处理，提升效率 |
| **异步执行** | 后台整合不阻塞对话 | 用户体验流畅，响应迅速 |
| **JSONL 格式** | 每行一个 JSON | 流式处理、容错性强 |
| **路径兼容** | 自动迁移旧会话到新路径 | 无缝升级，不丢失数据 |
| **跨会话共享** | 同一 MEMORY.md 跨渠道使用 | 用户信息持久化，上下文一致 |

### 记忆流程总结

```
消息进入系统
    ↓
添加到 Session.messages（活跃会话）
    ↓
保存到 sessions/xxx.jsonl（持久化）
    ↓
检查整合条件（/new 或 消息数 > 50）
    ↓（触发）
异步执行整合
    ├─ 格式化消息为文本
    ├─ 读取当前 MEMORY.md
    ├─ 调用 LLM 分析
    ├─ 生成 history_entry（摘要）
    ├─ 生成 memory_update（更新）
    ├─ 追加到 HISTORY.md
    ├─ 覆盖 MEMORY.md
    └─ 更新 last_consolidated
    ↓
长期记忆在下次对话时注入到系统提示词
    ↓
LLM 生成响应时知道用户的偏好和历史上下文
```

---

**文档版本**：1.0  
**更新日期**：2026-02-26  
**nanobot 版本**：0.1.4
