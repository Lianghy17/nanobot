# ChatBI 项目结构说明

## 📁 项目目录结构

```
nanobot/
├── main.py                    # 应用入口
├── start.sh                   # 启动脚本
├── requirements.txt            # Python 依赖
├── pyproject.toml            # 项目配置
├── .env.example              # 环境变量示例
├── README.md                 # 项目说明
├── PROJECT_STRUCTURE.md      # 本文件
│
├── nanobot/                  # 主包目录
│   ├── __init__.py
│   │
│   ├── agent/                # Agent 核心模块
│   │   ├── __init__.py
│   │   ├── core.py          # Agent 主逻辑（LLM 调用、工具执行）
│   │   │
│   │   ├── skills/          # Skills 实现（新架构）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                    # Skill 基类
│   │   │   ├── registry.py                # Skill 注册器
│   │   │   ├── mysql_skill.py             # MySQL 查询技能
│   │   │   ├── hive_skill.py              # Hive 1.0 查询技能
│   │   │   ├── knowledge_search_skill.py  # 知识库搜索（RAG）
│   │   │   ├── schema_search_skill.py     # 表结构查询
│   │   │   ├── qa_skill.py                # 常见问题问答
│   │   │   └── time_series_skill.py       # 时间序列预测
│   │   │
│   │   └── tools/           # 旧版工具（兼容保留）
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── registry.py
│   │       ├── rag_tool.py
│   │       ├── sql_tool.py
│   │       └── time_series_tool.py
│   │
│   ├── api/                  # API 模块
│   │   ├── __init__.py
│   │   ├── routes.py        # FastAPI 路由定义
│   │   └── skill_loader.py  # Skill 加载器
│   │
│   ├── scene/                # 场景管理
│   │   ├── __init__.py
│   │   ├── config.py        # 场景配置（预定义场景）
│   │   └── manager.py       # 场景管理器
│   │
│   ├── session/              # 会话管理
│   │   ├── __init__.py
│   │   └── manager.py       # 会话管理器（持久化、状态管理）
│   │
│   ├── config/               # 配置管理
│   │   ├── __init__.py
│   │   └── settings.py      # Pydantic 配置类
│   │
│   ├── frontend/             # Web 前端
│   │   ├── index.html       # 主页面
│   │   └── app.js           # 前端逻辑
│   │
│   ├── bus/                  # 消息总线（预留）
│   ├── channels/             # 通道管理（预留）
│   ├── cron/                 # 定时任务（预留）
│   ├── heartbeat/            # 心跳检测（预留）
│   ├── providers/            # 服务提供者（预留）
│   └── utils/                # 工具函数（预留）
│
└── workspace/                # 工作区
    └── sessions/             # 会话存储目录
```

## 🔧 核心模块说明

### 1. Agent 模块 (`nanobot/agent/`)

**核心文件：`core.py`**
- `Agent` 类：主要的 AI 代理类
- `process_message()`：处理用户消息的主要方法
- 支持流式响应和工具调用
- 集成 OpenAI API 进行 LLM 调用

**Skills 系统 (`agent/skills/`)**
- `Skill` 基类：所有技能的抽象基类
- `SkillRegistry`：技能注册和管理
- 各个具体技能实现（MySQL、Hive、RAG、QA 等）

### 2. API 模块 (`nanobot/api/`)

**路由定义 (`routes.py`)**
- `GET /api/v1/scenes` - 获取所有场景
- `POST /api/v1/chat` - 非流式对话
- `POST /api/v1/chat/stream` - 流式对话
- `GET /api/v1/skills` - 获取所有技能

**技能加载器 (`skill_loader.py`)**
- 自动加载所有技能到注册表
- 单例模式管理技能注册表

### 3. 场景管理 (`nanobot/scene/`)

**场景配置 (`config.py`)**
- 预定义场景：销售分析、用户行为、通用 BI
- 每个场景包含：场景码、名称、描述、系统提示词、启用的技能

**场景管理器 (`manager.py`)**
- 管理所有场景
- 提供场景查询功能

### 4. 会话管理 (`nanobot/session/`)

**会话管理器 (`manager.py`)**
- `Session` 类：管理单个会话
- `SessionManager` 类：管理所有会话
- 支持会话持久化到文件
- 支持暂停/恢复会话
- 会话状态管理

### 5. 前端模块 (`nanobot/frontend/`)

**HTML (`index.html`)**
- 场景选择界面
- 对话界面
- 响应式设计

**JavaScript (`app.js`)**
- 与后端 API 交互
- SSE 流式数据接收
- 消息展示和工具调用可视化

## 🚀 数据流

```
用户输入 (Frontend)
    ↓
FastAPI API (/api/v1/chat/stream)
    ↓
Agent.process_message()
    ↓
OpenAI LLM (with function calling)
    ↓
Skill.execute() (根据 LLM 决策)
    ↓
数据库/向量库/API 调用
    ↓
返回结果 → Agent 整合 → 流式返回给前端
```

## 🎯 技能 (Skills) 分类

### 数据库查询
- `mysql_skill` - MySQL 数据库查询
- `hive_skill` - Hive 1.0 数据仓库查询

### 知识检索 (RAG)
- `knowledge_search` - 知识库搜索
- `schema_search` - 表结构和元数据查询
- `qa_search` - 常见问题问答

### 数据分析
- `time_series_skill` - 时间序列预测

## 🔑 环境变量

主要配置项（`.env` 文件）：
- `NANOBOT_HOST` - 服务地址
- `NANOBOT_PORT` - 服务端口
- `NANOBOT_LLM_MODEL` - LLM 模型名称
- `NANOBOT_LLM_API_KEY` - LLM API 密钥
- `NANOBOT_LLM_BASE_URL` - LLM API 基础 URL
- `NANOBOT_SESSION_STORAGE_PATH` - 会话存储路径

## 📝 扩展指南

### 添加新技能

1. 在 `nanobot/agent/skills/` 创建新文件
2. 继承 `Skill` 基类
3. 实现必要属性和方法
4. 在 `api/skill_loader.py` 中注册

### 添加新场景

1. 在 `scene/config.py` 中定义 `SceneConfig`
2. 设置场景码、名称、描述、系统提示词
3. 指定启用的技能列表

## 🔌 集成说明

### LLM 集成
- 使用 OpenAI API
- 支持 function calling
- 可替换为其他兼容 API（通过 base_url）

### 数据库集成
- MySQL：使用 aiomysql
- Hive：使用 PyHive
- 需要配置数据库连接字符串

### RAG 集成
- 向量数据库：ChromaDB
- 嵌入模型：OpenAI 或 sentence-transformers
- 需要配置集合和索引
