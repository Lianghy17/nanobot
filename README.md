# ChatBI - 智能数据查询助手

基于 FastAPI 和 LLM 的智能数据查询系统，支持多场景数据分析。

## 功能特性

- 🎯 **多场景支持** - 支持销售分析、用户行为分析、通用数据查询等场景
- 🔧 **智能工具调用** - 集成 MySQL、Hive、知识库搜索、Schema 查询等技能
- 💬 **对话式交互** - 流式响应，实时展示工具调用过程
- 📊 **数据分析** - 支持时间序列预测和复杂数据查询
- 🌐 **现代化前端** - 简洁美观的 Web 界面

## 项目结构

```
nanobot/
├── agent/              # Agent 核心和技能系统
│   ├── core.py         # Agent 主逻辑
│   └── skills/         # 各类技能实现
│       ├── mysql_skill.py
│       ├── hive_skill.py
│       ├── knowledge_search_skill.py
│       ├── schema_search_skill.py
│       ├── qa_skill.py
│       └── time_series_skill.py
├── api/                # API 路由和加载器
│   ├── routes.py
│   └── skill_loader.py
├── scene/              # 场景管理
│   ├── config.py       # 场景配置
│   └── manager.py      # 场景管理器
├── session/            # 会话管理
│   └── manager.py
├── config/             # 配置管理
│   └── settings.py
└── frontend/           # Web 前端
    ├── index.html
    └── app.js
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置 LLM API 密钥：

```
NANOBOT_LLM_API_KEY=your-openai-api-key-here
```

### 3. 启动服务

```bash
python main.py
```

服务将运行在 `http://localhost:8000`

### 4. 访问前端

打开浏览器访问 `http://localhost:8000`

## 技能说明

### 数据库查询
- **mysql_query** - MySQL 数据库查询
- **hive_query** - Hive 1.0 数据仓库查询

### 知识检索 (RAG)
- **knowledge_search** - 知识库搜索
- **schema_search** - 表结构和元数据查询
- **qa_search** - 常见问题问答

### 数据分析
- **time_series_forecast** - 时间序列预测

## 场景配置

预定义场景：

1. **sales_analysis** - 销售数据分析
2. **user_behavior** - 用户行为分析  
3. **general_bi** - 通用数据查询

每个场景可配置：
- 场景名称和描述
- 系统提示词
- 启用的技能列表

## API 文档

启动服务后访问 `http://localhost:8000/docs` 查看完整 API 文档。

### 主要 API

- `GET /api/v1/scenes` - 获取所有场景
- `POST /api/v1/chat/stream` - 流式对话
- `GET /api/v1/skills` - 获取所有技能

## 开发说明

### 添加新技能

1. 在 `nanobot/agent/skills/` 创建新的技能类
2. 继承 `Skill` 基类
3. 实现 `name`, `description`, `parameters`, `execute` 方法
4. 在 `api/skill_loader.py` 中注册技能

### 添加新场景

在 `scene/config.py` 中添加新的 `SceneConfig`：

```python
SceneConfig(
    scene_code="my_scene",
    scene_name="我的场景",
    description="场景描述",
    system_prompt="系统提示词",
    enabled_skills=["skill1", "skill2"],
)
```

## 依赖项

- FastAPI - Web 框架
- OpenAI - LLM 调用
- ChromaDB - 向量数据库 (RAG)
- Prophet - 时间序列预测
- aiomysql - MySQL 异步连接
- PyHive - Hive 连接

## License

MIT
