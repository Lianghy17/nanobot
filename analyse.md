# nanobot 项目架构分析

## 1. 项目概述

**nanobot** 是一个超轻量级个人 AI 助手框架，核心代码约 **4,000 行**，相比 Clawdbot 的 430,000+ 行代码精简了 99%。

### 1.1 核心特性

- 🪶 **超轻量级**：核心代码简洁高效
- 🔬 **研究友好**：代码结构清晰，易于理解和扩展
- ⚡️ **高性能**：最小化资源占用，快速启动
- 💎 **易于使用**：一键部署，快速上手

### 1.2 技术栈

- **语言**：Python 3.11+
- **核心依赖**：
  - `typer` - CLI 框架
  - `litellm` - LLM 统一接口
  - `pydantic` - 配置管理
  - `websockets` - WebSocket 通信
  - `asyncio` - 异步处理
  - `loguru` - 日志记录

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          用户交互层                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  CLI     │  │ Telegram │  │ Discord  │  │ WhatsApp │ ... │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │              │              │              │                  │
│       └──────────────┼──────────────┼──────────────┘                  │
│                      │              │                                │
└──────────────────────┼──────────────┼────────────────────────────────┘
                       │              │
┌──────────────────────▼──────────────▼────────────────────────────────┐
│                     Channel Manager (渠道管理器)                      │
├─────────────────────────────────────────────────────────────────────────┤
│  - 初始化和管理多个聊天渠道                                       │
│  - 处理消息接收和发送                                           │
│  - 统一的消息格式转换                                           │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────────┐
│                      Message Bus (消息总线)                           │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │  Inbound Queue     │  │  Outbound Queue   │               │
│  │  (入队消息队列)    │  │  (出队消息队列)    │               │
│  └────────┬──────────┘  └──────────┬─────────┘               │
│           │                          │                            │
└───────────┼──────────────────────────┼────────────────────────────┘
            │                          │
┌───────────▼──────────────────────────▼──────────────────────────────┐
│                    Agent Loop (核心处理引擎)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │              Context Builder (上下文构建器)                  │     │
│  │  - 构建系统提示词                                          │     │
│  │  - 加载记忆信息                                            │     │
│  │  - 加载技能内容                                            │     │
│  │  - 管理对话历史                                            │     │
│  └────────────────────┬────────────────────────────────────┘     │
│                     │                                          │
│  ┌──────────────────▼───────────────────────────────────────┐   │
│  │          Session Manager (会话管理器)                       │   │
│  │  - 管理多会话状态                                         │   │
│  │  - 保存对话历史                                           │   │
│  └──────────────────┬───────────────────────────────────────┘   │
│                     │                                          │
│  ┌──────────────────▼───────────────────────────────────────┐   │
│  │           Memory Store (记忆存储)                          │   │
│  │  - 长期记忆 (MEMORY.md)                                  │   │
│  │  - 历史记录 (HISTORY.md)                                 │   │
│  │  - 自动记忆整合                                           │   │
│  └──────────────────┬───────────────────────────────────────┘   │
│                     │                                          │
│  ┌──────────────────▼───────────────────────────────────────┐   │
│  │          Skills Loader (技能加载器)                        │   │
│  │  - 工作空间技能加载                                       │   │
│  │  - 内置技能加载                                           │   │
│  │  - 技能依赖检查                                           │   │
│  └──────────────────┬───────────────────────────────────────┘   │
│                     │                                          │
│  ┌──────────────────▼───────────────────────────────────────┐   │
│  │         Subagent Manager (子代理管理器)                    │   │
│  │  - 管理后台子代理任务                                     │   │
│  │  - 独立任务执行                                           │   │
│  └──────────────────┬───────────────────────────────────────┘   │
│                     │                                          │
│  ┌──────────────────▼───────────────────────────────────────┐   │
│  │         Tool Registry (工具注册表)                         │   │
│  │  - 工具注册和查询                                         │   │
│  │  - 工具执行管理                                           │   │
│  └──────────────────┬───────────────────────────────────────┘   │
└──────────────────────┼───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────────┐
│                      Tool System (工具系统)                          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  File Tools │  │ Shell Tools │  │  Web Tools │  ...      │
│  │  文件操作    │  │ 命令执行     │  │  网络搜索    │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │Message Tool │  │ Spawn Tool  │  │  Cron Tool  │  ...      │
│  │  消息发送    │  │ 子代理生成   │  │ 定时任务     │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────────┐
│              Provider Layer (LLM 提供商层)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  LiteLLM     │  │   Custom     │  │ OpenAI Codex │ ...    │
│  │  Provider    │  │  Provider    │  │  Provider    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐        │
│  │      Provider Registry (提供商注册表)               │        │
│  │  - 15+ 提供商支持                                     │        │
│  │  - 自动路由和配置                                     │        │
│  │  - OAuth 支持                                        │        │
│  └───────────────────────────────────────────────────────┘        │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────────┐
│               External Services (外部服务)                          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ OpenRouter  │  │  Anthropic  │  │   OpenAI    │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  DeepSeek   │  │   Gemini    │  │  Groq       │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详解

### 3.1 CLI 命令层 (`nanobot/cli/commands.py`)

**职责**：提供命令行接口，处理用户交互

**主要命令**：
- `nanobot onboard` - 初始化配置和工作空间
- `nanobot agent` - 与 Agent 交互（单消息或交互模式）
- `nanobot gateway` - 启动网关服务（连接聊天渠道）
- `nanobot status` - 显示系统状态
- `nanobot provider login` - OAuth 登录提供商
- `nanobot channels login` - WhatsApp 设备链接
- `nanobot cron` - 定时任务管理

**关键实现**：
```python
# 交互式输入处理（使用 prompt_toolkit）
async def _read_interactive_input_async() -> str:
    """处理用户输入，支持粘贴、历史、显示"""
    return await _PROMPT_SESSION.prompt_async(
        HTML("<b fg='ansiblue'>You:</b> ")
    )

# Agent 创建
agent_loop = AgentLoop(
    bus=bus,
    provider=provider,
    workspace=config.workspace_path,
    model=model,
    temperature=temperature,
    ...
)
```

---

### 3.2 Channel Manager (`nanobot/channels/manager.py`)

**职责**：统一管理多个聊天渠道，协调消息路由

**支持的渠道**：
- **Telegram** - Bot API
- **WhatsApp** - 通过 Node.js 桥接器
- **Discord** - WebSocket Gateway
- **Feishu/Lark** - WebSocket 长连接
- **Mochat** - Socket.IO
- **DingTalk** - Stream 模式
- **Slack** - Socket 模式
- **Email** - IMAP/SMTP
- **QQ** - botpy SDK

**核心方法**：
```python
class ChannelManager:
    def __init__(self, config: Config, bus: MessageBus):
        self.config = config
        self.bus = bus
        self.channels: dict[str, BaseChannel] = {}
        self._init_channels()  # 根据配置初始化渠道
    
    async def start_all(self) -> None:
        """启动所有渠道和出队分发器"""
        # 1. 启动出队分发器
        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())
        # 2. 启动所有渠道
        tasks = [asyncio.create_task(channel.start()) 
                 for channel in self.channels.values()]
        await asyncio.gather(*tasks)
    
    async def _dispatch_outbound(self) -> None:
        """将出队消息分发到对应渠道"""
        while True:
            msg = await self.bus.consume_outbound()
            channel = self.channels.get(msg.channel)
            if channel:
                await channel.send(msg)
```

**消息流程**：
```
用户消息
    ↓
Channel (Telegram/Discord/...)
    ↓
publish_inbound(msg)
    ↓
Inbound Queue
    ↓
AgentLoop 消费并处理
    ↓
生成响应
    ↓
publish_outbound(response)
    ↓
Outbound Queue
    ↓
Channel 发送响应
    ↓
用户收到回复
```

---

### 3.3 Agent Loop (`nanobot/agent/loop.py`)

**职责**：核心处理引擎，管理 Agent 生命周期

**核心组件**：
```python
class AgentLoop:
    def __init__(
        self,
        bus: MessageBus,           # 消息总线
        provider: LLMProvider,      # LLM 提供商
        workspace: Path,           # 工作空间路径
        model: str,               # 模型名称
        max_iterations: int = 20,  # 最大工具调用次数
        memory_window: int = 50,    # 记忆窗口大小
        ...
    ):
        self.bus = bus
        self.provider = provider
        self.context = ContextBuilder(workspace)    # 上下文构建器
        self.sessions = SessionManager(workspace)    # 会话管理器
        self.tools = ToolRegistry()               # 工具注册表
        self.subagents = SubagentManager(...)     # 子代理管理器
        self._register_default_tools()            # 注册默认工具
```

**处理流程**：
```python
async def _run_agent_loop(
    self,
    initial_messages: list[dict],
    on_progress: Callable[[str], Awaitable[None]] = None,
) -> tuple[str | None, list[str]]:
    """运行 Agent 迭代循环"""
    messages = initial_messages
    iteration = 0
    final_content = None
    tools_used: list[str] = []
    
    while iteration < self.max_iterations:
        # 1. 调用 LLM
        response = await self.provider.chat(
            messages=messages,
            tools=self.tools.get_definitions(),
            model=self.model,
            ...
        )
        
        # 2. 处理工具调用
        if response.has_tool_calls:
            # 发送进度更新
            if on_progress:
                await on_progress(self._tool_hint(response.tool_calls))
            
            # 添加工具调用到消息历史
            messages = self.context.add_assistant_message(
                messages, response.content, tool_call_dicts
            )
            
            # 执行每个工具调用
            for tool_call in response.tool_calls:
                tools_used.append(tool_call.name)
                result = await self.tools.execute(
                    tool_call.name, tool_call.arguments
                )
                messages = self.context.add_tool_result(
                    messages, tool_call.id, tool_call.name, result
                )
        else:
            # 无工具调用，处理完成
            final_content = self._strip_think(response.content)
            break
    
    return final_content, tools_used
```

**消息处理**：
```python
async def _process_message(
    self, msg: InboundMessage, session_key: str | None = None
) -> OutboundMessage | None:
    """处理单个入队消息"""
    
    # 1. 获取或创建会话
    session = self.sessions.get_or_create(session_key or msg.session_key)
    
    # 2. 处理斜杠命令
    if msg.content.strip().lower() == "/new":
        session.clear()
        return OutboundMessage(content="新会话已开始")
    
    # 3. 记忆整合（如果会话过长）
    if len(session.messages) > self.memory_window:
        asyncio.create_task(self._consolidate_memory(session))
    
    # 4. 构建上下文消息
    initial_messages = self.context.build_messages(
        history=session.get_history(max_messages=self.memory_window),
        current_message=msg.content,
        channel=msg.channel,
        chat_id=msg.chat_id,
    )
    
    # 5. 运行 Agent 循环
    final_content, tools_used = await self._run_agent_loop(
        initial_messages, on_progress=_bus_progress
    )
    
    # 6. 保存到会话
    session.add_message("user", msg.content)
    session.add_message("assistant", final_content, tools_used=tools_used)
    self.sessions.save(session)
    
    # 7. 返回响应
    return OutboundMessage(
        channel=msg.channel,
        chat_id=msg.chat_id,
        content=final_content
    )
```

---

### 3.4 Context Builder (`nanobot/agent/context.py`)

**职责**：构建 LLM 的系统提示和上下文

**构建层次**：
```python
def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
    """构建系统提示词"""
    parts = []
    
    # 1. 核心身份（包含时间、系统信息、工作空间路径）
    parts.append(self._get_identity())
    
    # 2. 引导文件（AGENTS.md, SOUL.md, USER.md 等）
    bootstrap = self._load_bootstrap_files()
    if bootstrap:
        parts.append(bootstrap)
    
    # 3. 记忆上下文
    memory = self.memory.get_memory_context()
    if memory:
        parts.append(f"# Memory\n\n{memory}")
    
    # 4. 始终加载的技能（完整内容）
    always_skills = self.skills.get_always_skills()
    if always_skills:
        always_content = self.skills.load_skills_for_context(always_skills)
        parts.append(f"# Active Skills\n\n{always_content}")
    
    # 5. 可用技能（仅摘要，按需加载）
    skills_summary = self.skills.build_skills_summary()
    if skills_summary:
        parts.append(f"# Skills\n\n{skills_summary}")
    
    return "\n\n---\n\n".join(parts)
```

**系统提示词结构**：
```markdown
# nanobot 🐈

You are nanobot, a helpful AI assistant. You have access to tools...

## Current Time
2026-02-26 10:30 (Thursday) (UTC)

## Runtime
macOS arm64, Python 3.11.0

## Workspace
Your workspace is at: /Users/user/.nanobot/workspace
- Long-term memory: /Users/user/.nanobot/workspace/memory/MEMORY.md
- History log: /Users/user/.nanobot/workspace/memory/HISTORY.md
- Custom skills: /Users/user/.nanobot/workspace/skills/{skill-name}/SKILL.md

## SOUL.md
I am nanobot, a lightweight AI assistant...

## MEMORY.md
User preferences: User prefers casual communication...

## Active Skills
### Skill: github
GitHub integration instructions...

## Skills
<skills>
  <skill available="true">
    <name>weather</name>
    <description>Weather information</description>
    <location>/path/to/weather/skill.md</location>
  </skill>
</skills>
```

---

### 3.5 Tool Registry (`nanobot/agent/tools/registry.py`)

**职责**：管理工具注册、查询和执行

**工具接口**：
```python
class Tool(ABC):
    @abstractmethod
    def to_schema(self) -> dict[str, Any]:
        """返回 OpenAI 格式的工具定义"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具并返回结果"""
        pass
    
    def validate_params(self, params: dict) -> list[str]:
        """验证参数，返回错误列表"""
        return []
```

**工具注册**：
```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
    
    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI 格式定义"""
        return [tool.to_schema() for tool in self._tools.values()]
    
    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """执行工具"""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        
        errors = tool.validate_params(params)
        if errors:
            return f"Error: Invalid parameters: {'; '.join(errors)}"
        
        return await tool.execute(**params)
```

**内置工具列表**：

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `read_file` | 读取文件 | `file_path` |
| `write_file` | 写入文件 | `file_path`, `content` |
| `edit_file` | 编辑文件 | `file_path`, `old_str`, `new_str` |
| `list_dir` | 列出目录 | `directory`, `recursive` |
| `exec` | 执行 shell 命令 | `command` |
| `web_search` | 网络搜索 | `query`, `max_results` |
| `web_fetch` | 抓取网页 | `url`, `fetch_info` |
| `message` | 发送消息到渠道 | `channel`, `chat_id`, `content` |
| `spawn` | 生成子代理 | `task`, `label` |
| `cron` | 定时任务管理 | `action`, `name`, ... |

---

### 3.6 Memory System (`nanobot/agent/memory.py`)

**职责**：长期记忆和历史记录管理

**记忆整合机制**：
```python
async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
    """将旧消息整合到 MEMORY.md 和 HISTORY.md"""
    
    memory = MemoryStore(self.workspace)
    
    # 获取需要处理的消息
    if archive_all:
        old_messages = session.messages
    else:
        keep_count = self.memory_window // 2
        old_messages = session.messages[
            session.last_consolidated:-keep_count
        ]
    
    # 使用 LLM 提取关键信息
    prompt = f"""Process this conversation and return JSON:
    1. "history_entry": Summary of key events (2-5 sentences)
    2. "memory_update": Updated long-term memory content
    
    ## Current Memory
    {current_memory}
    
    ## Conversation
    {conversation}"""
    
    response = await self.provider.chat(
        messages=[{"role": "system", "content": prompt}],
        model=self.model,
    )
    
    result = json_repair.loads(response.content)
    
    # 更新记忆文件
    if entry := result.get("history_entry"):
        memory.append_history(entry)
    if update := result.get("memory_update"):
        memory.write_long_term(update)
    
    # 更新会话状态
    session.last_consolidated = len(session.messages) - keep_count
```

**记忆存储结构**：
```
workspace/
├── memory/
│   ├── MEMORY.md        # 长期记忆（用户信息、偏好、项目上下文）
│   └── HISTORY.md       # 历史日志（可搜索的事件记录）
├── AGENTS.md          # Agent 指令
├── SOUL.md            # AI 性格设定
├── USER.md            # 用户信息
└── skills/            # 自定义技能
```

---

### 3.7 Skills System (`nanobot/agent/skills.py`)

**职责**：加载和管理 Agent 技能

**技能加载优先级**：
1. **工作空间技能** (`workspace/skills/*/SKILL.md`) - 最高优先级
2. **内置技能** (`nanobot/skills/*/SKILL.md`) - 作为备选

**技能元数据**：
```yaml
---
name: github
description: GitHub integration for repository operations
always: true  # 始终加载（完整内容）
requires:
  bins: [git, gh]
  env: [GITHUB_TOKEN]
metadata: {"nanobot": {"always": true}}
---

# GitHub Integration

You have access to GitHub tools...
```

**技能摘要格式**（用于按需加载）：
```xml
<skills>
  <skill available="true">
    <name>github</name>
    <description>GitHub integration</description>
    <location>/workspace/skills/github/SKILL.md</location>
  </skill>
  <skill available="false">
    <name>docker</name>
    <description>Docker container management</description>
    <location>/workspace/skills/docker/SKILL.md</location>
    <requires>CLI: docker</requires>
  </skill>
</skills>
```

---

### 3.8 Provider Registry (`nanobot/providers/registry.py`)

**职责**：统一管理多个 LLM 提供商

**提供商类型**：

1. **网关类型**（可路由任何模型）
   - **OpenRouter** - 全球网关，支持 100+ 模型
   - **AiHubMix** - API 网关
   - **SiliconFlow** - 硅基流动网关

2. **标准提供商**（通过模型名称关键词匹配）
   - **Anthropic** (Claude)
   - **OpenAI** (GPT)
   - **DeepSeek**
   - **Gemini**
   - **Zhipu** (GLM)
   - **DashScope** (Qwen)
   - **Moonshot** (Kimi)
   - **MiniMax**

3. **本地部署**
   - **vLLM** - 任何 OpenAI 兼容服务器

4. **OAuth 提供商**
   - **OpenAI Codex** - OAuth 认证
   - **GitHub Copilot** - OAuth 认证

5. **辅助服务**
   - **Groq** - Whisper 语音转录 + LLM

**提供商元数据**：
```python
@dataclass(frozen=True)
class ProviderSpec:
    name: str                     # 配置字段名
    keywords: tuple[str, ...]       # 模型名关键词
    env_key: str                    # LiteLLM 环境变量
    display_name: str = ""          # 状态显示名称
    
    litellm_prefix: str = ""        # 模型前缀
    skip_prefixes: tuple[str, ...] = ()  # 跳过前缀的条件
    
    is_gateway: bool = False        # 是否为网关
    is_local: bool = False          # 是否为本地部署
    is_oauth: bool = False          # 是否使用 OAuth
    is_direct: bool = False         # 是否直接连接（绕过 LiteLLM）
    
    default_api_base: str = ""      # 默认 API 基础 URL
    model_overrides: tuple = ()      # 特定模型的参数覆盖
```

**提供商匹配逻辑**：
```python
def _match_provider(self, model: str | None = None) -> tuple[ProviderConfig | None, str | None]:
    """匹配提供商配置和注册表名"""
    model_lower = (model or self.agents.defaults.model).lower()
    
    # 1. 按模型关键词匹配
    for spec in PROVIDERS:
        p = getattr(self.providers, spec.name, None)
        if p and any(kw in model_lower for kw in spec.keywords):
            if spec.is_oauth or p.api_key:
                return p, spec.name
    
    # 2. 回退：优先网关，然后其他
    for spec in PROVIDERS:
        if spec.is_oauth:
            continue
        p = getattr(self.providers, spec.name, None)
        if p and p.api_key:
            return p, spec.name
    
    return None, None
```

**环境变量设置**：
```python
def _setup_env(self, spec: ProviderSpec, api_key: str, api_base: str | None) -> None:
    """设置提供商所需的环境变量"""
    os.environ[spec.env_key] = api_key
    
    if spec.litellm_prefix:
        os.environ["LITELLM_MODEL_PREFIX"] = spec.litellm_prefix
    
    for env_key, env_value in spec.env_extras:
        # 支持占位符：{api_key}, {api_base}
        resolved_value = env_value.format(
            api_key=api_key,
            api_base=api_base or spec.default_api_base
        )
        os.environ[env_key] = resolved_value
```

---

### 3.9 Subagent Manager (`nanobot/agent/subagent.py`)

**职责**：管理后台子代理任务

**子代理特性**：
- 独立的 LLM 实例
- 简化的系统提示
- 专注于特定任务
- 无法直接发送消息或生成其他子代理
- 通过 Message Bus 将结果返回给主 Agent

**子代理生成流程**：
```python
async def spawn(
    self,
    task: str,
    label: str | None = None,
    origin_channel: str = "cli",
    origin_chat_id: str = "direct",
) -> str:
    """生成子代理执行后台任务"""
    task_id = str(uuid.uuid4())[:8]
    display_label = label or task[:30]
    
    # 创建后台任务
    bg_task = asyncio.create_task(
        self._run_subagent(task_id, task, display_label, {
            "channel": origin_channel,
            "chat_id": origin_chat_id,
        })
    )
    self._running_tasks[task_id] = bg_task
    
    return f"Subagent [{display_label}] started (id: {task_id}). I'll notify you when it completes."

async def _run_subagent(self, task_id: str, task: str, label: str, origin: dict) -> None:
    """执行子代理任务"""
    # 1. 构建子代理工具（无 message 和 spawn 工具）
    tools = ToolRegistry()
    tools.register(ReadFileTool(...))
    tools.register(WriteFileTool(...))
    tools.register(ExecTool(...))
    tools.register(WebSearchTool(...))
    # ... 不包含 MessageTool 和 SpawnTool
    
    # 2. 构建子代理系统提示
    system_prompt = self._build_subagent_prompt(task)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]
    
    # 3. 运行 Agent 循环（最多 15 次迭代）
    for iteration in range(15):
        response = await self.provider.chat(
            messages=messages,
            tools=tools.get_definitions(),
            model=self.model,
        )
        
        if response.has_tool_calls:
            # 执行工具...
            pass
        else:
            final_result = response.content
            break
    
    # 4. 通过 Message Bus 宣布结果
    await self._announce_result(task_id, label, task, final_result, origin, "ok")
```

**子代理系统提示**：
```markdown
# Subagent

## Current Time
2026-02-26 10:30 (Thursday) (UTC)

You are a subagent spawned by main agent to complete a specific task.

## Rules
1. Stay focused - complete only the assigned task, nothing else
2. Your final response will be reported back to main agent
3. Do not initiate conversations or take on side tasks
4. Be concise but informative in your findings

## What You Can Do
- Read and write files in workspace
- Execute shell commands
- Search web and fetch web pages
- Complete task thoroughly

## What You Cannot Do
- Send messages directly to users (no message tool available)
- Spawn other subagents
- Access main agent's conversation history

## Workspace
Your workspace is at: /workspace
Skills are available at: /workspace/skills/

When you have completed the task, provide a clear summary of your findings.
```

---

### 3.10 Message Bus (`nanobot/bus/queue.py`)

**职责**：解耦聊天渠道和 Agent 核心，提供异步消息传递

**队列设计**：
```python
class MessageBus:
    def __init__(self):
        # 入队消息队列（Channel → Agent）
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        
        # 出队消息队列（Agent → Channel）
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        
        # 出队订阅者
        self._outbound_subscribers: dict[str, list[Callable]] = {}
    
    async def publish_inbound(self, msg: InboundMessage) -> None:
        """发布入队消息（从渠道到 Agent）"""
        await self.inbound.put(msg)
    
    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """发布出队消息（从 Agent 到渠道）"""
        await self.outbound.put(msg)
    
    async def consume_inbound(self) -> InboundMessage:
        """消费下一个入队消息（阻塞）"""
        return await self.inbound.get()
    
    async def consume_outbound(self) -> OutboundMessage:
        """消费下一个出队消息（阻塞）"""
        return await self.outbound.get()
```

**消息事件**：
```python
# InboundMessage (入队消息)
@dataclass
class InboundMessage:
    channel: str           # 来源渠道（telegram, discord, cli, system）
    sender_id: str        # 发送者 ID
    chat_id: str          # 聊天 ID
    content: str          # 消息内容
    media: list[str] | None = None  # 媒体附件路径
    metadata: dict | None = None    # 额外元数据
    session_key: str = ""   # 会话键（channel:chat_id）

# OutboundMessage (出队消息)
@dataclass
class OutboundMessage:
    channel: str           # 目标渠道
    chat_id: str          # 目标聊天 ID
    content: str          # 响应内容
    metadata: dict | None = None    # 额外元数据（如 Slack thread_ts）
```

---

## 4. 配置系统

### 4.1 配置文件位置
- **主配置**：`~/.nanobot/config.json`
- **工作空间**：`~/.nanobot/workspace`
- **数据目录**：`~/.nanobot/data`

### 4.2 配置结构 (`nanobot/config/schema.py`)

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-opus-4-5",
      "max_tokens": 8192,
      "temperature": 0.7,
      "max_tool_iterations": 20,
      "memory_window": 50
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "BOT_TOKEN",
      "allowFrom": ["USER_ID"]
    },
    "discord": {
      "enabled": true,
      "token": "BOT_TOKEN",
      "allowFrom": ["USER_ID"]
    },
    "whatsapp": {
      "enabled": true,
      "bridgeUrl": "ws://localhost:3001",
      "bridgeToken": "SHARED_TOKEN",
      "allowFrom": ["+1234567890"]
    },
    "email": {
      "enabled": true,
      "consentGranted": true,
      "imapHost": "imap.gmail.com",
      "imapPort": 993,
      "imapUsername": "bot@gmail.com",
      "imapPassword": "app_password",
      "smtpHost": "smtp.gmail.com",
      "smtpPort": 587,
      "smtpUsername": "bot@gmail.com",
      "smtpPassword": "app_password",
      "fromAddress": "bot@gmail.com",
      "autoReplyEnabled": true,
      "allowFrom": ["user@gmail.com"]
    }
  },
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-xxx"
    },
    "anthropic": {
      "apiKey": "sk-ant-xxx"
    },
    "openai": {
      "apiKey": "sk-xxx"
    },
    "deepseek": {
      "apiKey": "sk-xxx"
    }
  },
  "tools": {
    "web": {
      "search": {
        "apiKey": "BRAVE_API_KEY",
        "maxResults": 5
      }
    },
    "exec": {
      "timeout": 60
    },
    "restrictToWorkspace": false,
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
      },
      "brave-search": {
        "url": "https://mcp.example.com/sse"
      }
    }
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790
  }
}
```

---

## 5. 定时任务系统 (`nanobot/cron/`)

**职责**：支持 Cron 表达式的定时任务调度

**定时任务类型**：
1. **Cron 表达式** - 标准的 cron 格式 (`0 9 * * *`)
2. **间隔执行** - 每隔 N 秒执行一次
3. **一次性任务** - 在指定时间执行一次

**定时任务管理**：
```bash
# 添加定时任务
nanobot cron add --name "daily" --message "Good morning!" --cron "0 9 * * *"
nanobot cron add --name "hourly" --message "Check status" --every 3600

# 列出所有任务
nanobot cron list

# 移除任务
nanobot cron remove <job_id>

# 手动运行任务
nanobot cron run <job_id>

# 启用/禁用任务
nanobot cron enable <job_id>
nanobot cron enable <job_id> --disable
```

---

## 6. MCP (Model Context Protocol) 集成

**职责**：连接外部工具服务器，作为原生 Agent 工具使用

**支持的模式**：

1. **Stdio 模式** - 通过进程标准输入/输出通信
```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
        "env": {"NODE_ENV": "production"}
      }
    }
  }
}
```

2. **HTTP 模式** - 通过 HTTP/SSE 端点通信
```json
{
  "tools": {
    "mcpServers": {
      "brave-search": {
        "url": "https://mcp.example.com/sse"
      }
    }
  }
}
```

**MCP 工具自动发现**：
- 在 Agent 启动时连接所有配置的 MCP 服务器
- 自动注册 MCP 提供的工具到 ToolRegistry
- Agent 可以像使用内置工具一样使用 MCP 工具

---

## 7. 数据流全景图

```
用户输入
    │
    ├─→ CLI → nanobot agent -m "消息"
    │       ↓
    │   AgentLoop.process_direct()
    │       ↓
    │   ContextBuilder.build_messages()
    │       ↓
    │   Provider.chat() → LLM API
    │       ↓
    │   Tool Registry.execute()
    │       ↓
    │   ├─ read_file / write_file
    │   ├─ exec (shell command)
    │   ├─ web_search / web_fetch
    │   └─ spawn (subagent)
    │           ↓
    │       Subagent._run_subagent()
    │           ↓
    │       返回结果
    │       ↓
    │   返回最终响应
    │       ↓
    │   Console 输出
    │
    └─→ Chat App (Telegram/Discord/...)
            ↓
        Channel.receive()
            ↓
        MessageBus.publish_inbound()
            ↓
        AgentLoop.run()
            ↓
            ├─ 获取/创建 Session
            ├─ 记忆整合（如需要）
            ├─ 构建上下文
            ├─ 运行 Agent 循环
            │   ├─ 调用 LLM
            │   ├─ 执行工具
            │   └─ 迭代直到完成
            ├─ 保存到 Session
            ↓
        MessageBus.publish_outbound()
            ↓
        Channel.send()
            ↓
        用户收到回复
```

---

## 8. 关键设计模式

### 8.1 消息总线模式 (Message Bus Pattern)
- **目的**：解耦 Channel 和 Agent
- **实现**：异步队列 (`asyncio.Queue`)
- **优势**：易于扩展新渠道，消息传递可靠

### 8.2 注册表模式 (Registry Pattern)
- **Provider Registry**：管理多个 LLM 提供商
- **Tool Registry**：管理工具注册和执行
- **优势**：动态扩展，统一接口

### 8.3 构建器模式 (Builder Pattern)
- **Context Builder**：分步骤构建复杂的系统提示
- **优势**：灵活组合不同组件

### 8.4 策略模式 (Strategy Pattern)
- **Provider 抽象**：不同的 LLM 提供商实现统一接口
- **Channel 抽象**：不同的聊天渠道实现统一接口
- **优势**：易于切换和扩展

### 8.5 观察者模式 (Observer Pattern)
- **Message Bus 订阅者**：渠道订阅出队消息
- **优势**：松耦合，事件驱动

---

## 9. 扩展性分析

### 9.1 添加新的聊天渠道
1. 创建 `nanobot/channels/newchannel.py`，继承 `BaseChannel`
2. 实现必需方法：`start()`, `stop()`, `send()`
3. 在 `ChannelsConfig` 中添加配置字段
4. 在 `ChannelManager._init_channels()` 中初始化

### 9.2 添加新的 LLM 提供商
1. 在 `ProviderSpec` 元组中添加提供商元数据
2. 在 `ProvidersConfig` 中添加配置字段
3. 完成！环境变量、模型前缀、配置匹配自动工作

### 9.3 添加新的工具
1. 创建工具类，继承 `Tool`，实现 `to_schema()` 和 `execute()`
2. 在 `AgentLoop._register_default_tools()` 中注册
3. 工具自动可用

### 9.4 添加新的技能
1. 在 `workspace/skills/myskill/` 创建 `SKILL.md`
2. 编写技能说明和元数据
3. Agent 自动发现并可用

---

## 10. 安全机制

### 10.1 工作空间限制
```json
{
  "tools": {
    "restrictToWorkspace": true
  }
}
```
- 限制所有工具（文件、Shell、列表）只能访问工作空间目录
- 防止路径遍历攻击

### 10.2 渠道访问控制
```json
{
  "channels": {
    "telegram": {
      "allowFrom": ["USER_ID1", "USER_ID2"]
    }
  }
}
```
- 白名单机制，空列表表示允许所有人
- 防止未授权访问

### 10.3 Email 访问控制
```json
{
  "channels": {
    "email": {
      "consentGranted": true,
      "allowFrom": ["trusted@email.com"]
    }
  }
}
```
- 显式同意机制（`consentGranted`）
- 发件人白名单

---

## 11. 性能优化

### 11.1 异步处理
- 所有 I/O 操作使用 `async/await`
- 避免阻塞事件循环

### 11.2 进度流式输出
```python
async def _run_agent_loop(self, ..., on_progress: Callable) -> ...:
    if response.has_tool_calls:
        if on_progress:
            await on_progress(self._tool_hint(response.tool_calls))
```
- 实时反馈工具执行进度
- 改善用户体验

### 11.3 记忆整合优化
- 仅在会话超过窗口大小时触发整合
- 后台异步执行，不阻塞主流程
- 保留最近的对话，整合历史记录

---

## 12. 总结

### 12.1 架构优势
1. **模块化**：各组件职责清晰，易于维护
2. **可扩展**：注册表模式支持动态扩展
3. **解耦**：消息总线实现松耦合
4. **轻量**：核心代码仅 4,000 行
5. **灵活**：支持 15+ LLM 提供商、9+ 聊天渠道

### 12.2 技术亮点
1. **Provider Registry**：单一数据源，2 步添加新提供商
2. **Tool Registry**：动态工具管理，统一执行接口
3. **Subagent**：后台任务独立执行，不阻塞主流程
4. **Memory Consolidation**：自动记忆整合，使用 LLM 提取关键信息
5. **Skills Progressive Loading**：技能摘要 + 按需加载，节省 Token

### 12.3 适用场景
- 🚀 **个人 AI 助手**：日常任务、信息查询
- 📚 **知识助手**：文档整理、搜索总结
- 💬 **聊天机器人**：多平台接入、自动回复
- 🔄 **任务自动化**：定时任务、工作流编排
- 🔧 **开发助手**：代码生成、调试、部署

---

## 13. 项目结构

```
nanobot/
├── nanobot/
│   ├── __init__.py              # 版本信息
│   │
│   ├── cli/                     # CLI 命令层
│   │   └── commands.py          # 所有命令实现
│   │
│   ├── agent/                   # 核心 Agent 逻辑
│   │   ├── loop.py             # Agent 循环（核心处理引擎）
│   │   ├── context.py          # 上下文构建器
│   │   ├── memory.py           # 记忆存储
│   │   ├── skills.py           # 技能加载器
│   │   ├── subagent.py         # 子代理管理器
│   │   └── tools/            # 工具系统
│   │       ├── base.py         # 工具基类
│   │       ├── registry.py     # 工具注册表
│   │       ├── filesystem.py   # 文件操作工具
│   │       ├── shell.py        # Shell 执行工具
│   │       ├── web.py         # Web 搜索/抓取工具
│   │       ├── message.py     # 消息发送工具
│   │       ├── spawn.py       # 子代理生成工具
│   │       ├── cron.py        # 定时任务工具
│   │       └── mcp.py        # MCP 工具适配器
│   │
│   ├── channels/               # 聊天渠道集成
│   │   ├── manager.py         # 渠道管理器
│   │   ├── base.py           # 渠道基类
│   │   ├── telegram.py       # Telegram 集成
│   │   ├── discord.py        # Discord 集成
│   │   ├── whatsapp.py       # WhatsApp 集成
│   │   ├── feishu.py        # 飞书集成
│   │   ├── mochat.py        # Mochat 集成
│   │   ├── dingtalk.py      # 钉钉集成
│   │   ├── slack.py         # Slack 集成
│   │   ├── qq.py            # QQ 集成
│   │   └── email.py         # Email 集成
│   │
│   ├── providers/              # LLM 提供商
│   │   ├── registry.py       # 提供商注册表（核心）
│   │   ├── base.py           # 提供商基类
│   │   ├── litellm_provider.py   # LiteLLM 适配
│   │   ├── custom_provider.py     # 自定义提供商
│   │   ├── openai_codex_provider.py  # OpenAI Codex (OAuth)
│   │   └── transcription.py   # Groq Whisper 转录
│   │
│   ├── bus/                   # 消息总线
│   │   ├── events.py         # 消息事件定义
│   │   └── queue.py         # 异步消息队列
│   │
│   ├── session/               # 会话管理
│   │   └── manager.py       # 会话管理器
│   │
│   ├── config/                # 配置管理
│   │   ├── schema.py         # Pydantic 配置模型
│   │   └── loader.py        # 配置加载器
│   │
│   ├── cron/                  # 定时任务
│   │   ├── service.py        # Cron 服务
│   │   └── types.py         # Cron 类型定义
│   │
│   ├── heartbeat/             # 心跳服务
│   │   └── service.py        # 主动唤醒
│   │
│   ├── skills/               # 内置技能
│   │   ├── github/           # GitHub 集成
│   │   ├── weather/          # 天气查询
│   │   ├── tmux/            # Tmux 会话管理
│   │   ├── memory/           # 记忆管理
│   │   ├── summarize/        # 文本总结
│   │   ├── cron/             # 定时任务
│   │   ├── clawhub/          # ClawHub 技能
│   │   └── skill-creator/    # 技能创建工具
│   │
│   └── utils/                # 工具函数
│       └── helpers.py        # 辅助函数
│
├── bridge/                   # Node.js 桥接器（WhatsApp）
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       └── index.ts
│
├── tests/                    # 测试
│   ├── test_agent.py
│   ├── test_config.py
│   └── test_tools.py
│
├── pyproject.toml            # 项目配置
├── Dockerfile                # Docker 镜像
├── docker-compose.yml         # Docker Compose
├── README.md                 # 项目文档
└── analyse.md               # 本文档
```

---

## 14. 核心代码统计

| 模块 | 文件数 | 代码行数（估算） |
|------|--------|----------------|
| Agent 核心 | 6 | ~800 |
| Tools | 10 | ~600 |
| Channels | 11 | ~1,200 |
| Providers | 5 | ~500 |
| CLI | 1 | ~1,000 |
| Config | 2 | ~350 |
| Bus | 2 | ~100 |
| Session | 1 | ~200 |
| Skills | 8 | ~300 |
| Cron | 2 | ~400 |
| 其他 | 5 | ~200 |
| **总计** | **53** | **~5,650** |

**注**：核心 Agent 逻辑约 4,000 行，其余为周边支持代码。

---

**文档版本**：1.0  
**更新日期**：2026-02-26  
**nanobot 版本**：0.1.4
