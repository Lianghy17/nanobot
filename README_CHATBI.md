# ChatBI - 对话式数据分析平台

## 项目简介

ChatBI是一个基于nanobot的agent核心能力构建的多用户对话式数据查询和分析平台。

### 核心特性

- **多用户支持**: 支持多用户并发访问，用户间数据完全隔离
- **多Channel接入**: 支持自建Web前端、钉钉、飞书等渠道
- **场景管理**: 基于配置文件管理不同业务场景（销售分析、用户行为分析等）
- **强大的工具集**: 
  - RAG知识库查询
  - SQL数据查询
  - Python代码执行（沙箱环境）
  - 文件读写操作
- **安全隔离**: 用户级文件系统隔离，代码沙箱执行
- **简单前端**: 纯HTML/CSS/JavaScript实现，零依赖

## 项目结构

```
nanobot/
├── prd/                          # PRD文档
│   ├── 01_系统架构.md
│   ├── 02_详细需求规格.md
│   ├── 03_交互逻辑.md
│   ├── 04_后端服务架构.md
│   └── 05_关键流程时序图.md
├── chatbi/                        # ChatBI业务层
│   ├── __init__.py
│   ├── main.py                    # 主应用入口
│   ├── config.py                  # 配置管理
│   ├── api/                       # API路由
│   │   ├── conversations.py       # 对话管理API
│   │   ├── messages.py            # 消息API
│   │   ├── scenes.py              # 场景API
│   │   └── files.py               # 文件API
│   ├── core/                      # 核心服务
│   │   ├── loop_queue.py          # Loop队列
│   │   ├── conversation_manager.py # 对话管理器
│   │   ├── message_processor.py   # 消息处理器
│   │   └── agent_wrapper.py       # Agent包装器
│   ├── agent/tools/               # 工具系统
│   │   ├── base.py                # 工具基类
│   │   ├── rag_tool.py            # RAG查询工具
│   │   ├── sql_tool.py            # SQL执行工具
│   │   ├── python_tool.py         # Python执行工具
│   │   └── file_ops.py            # 文件操作工具
│   ├── channels/                  # Channel适配器
│   │   ├── base.py                # Channel基类
│   │   └── web_channel.py         # Web前端Channel
│   └── models/                    # 数据模型
│       ├── conversation.py         # 对话模型
│       ├── message.py             # 消息模型
│       └── scene.py               # 场景模型
├── frontend/                      # 前端（简化HTML）
│   ├── index.html                 # 主页面
│   └── js/app.js                 # 前端逻辑
├── config/                        # 配置文件
│   └── scenes.json               # 场景配置
├── workspace/                     # 工作空间
│   ├── sessions/                  # 会话存储
│   ├── files/                     # 用户文件
│   └── shared/                   # 共享资源
└── requirements-chatbi.txt        # 依赖包
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements-chatbi.txt
```

### 2. 配置环境变量

创建`.env`文件：

```bash
LLM_MODEL=gpt-4
DEBUG=true
LOOP_WORKERS=4
```

### 3. 启动服务

```bash
# 方式1：使用启动脚本
chmod +x chatbi/run.sh
./chatbi/run.sh

# 方式2：直接启动
python3 -m uvicorn chatbi.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问应用

- 前端页面: http://localhost:8000/
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## API接口

### 对话管理

```bash
# 创建对话
POST /api/conversations
{
  "scene_code": "sales_analysis"
}

# 获取对话列表
GET /api/conversations

# 获取对话详情
GET /api/conversations/{conversation_id}

# 删除对话
DELETE /api/conversations/{conversation_id}
```

### 消息接口

```bash
# 发送消息
POST /api/messages
{
  "conversation_id": "conv_xxx",
  "content": "查询上个月销售额"
}

# 获取消息历史
GET /api/conversations/{conversation_id}/messages
```

### 场景接口

```bash
# 获取场景列表
GET /api/scenes

# 获取场景详情
GET /api/scenes/{scene_code}
```

### 文件接口

```bash
# 上传文件
POST /api/files/upload
Content-Type: multipart/form-data

# 获取文件列表
GET /api/files

# 删除文件
DELETE /api/files/{file_path}
```

## 场景配置

在`config/scenes.json`中配置场景：

```json
{
  "scenes": [
    {
      "scene_code": "sales_analysis",
      "scene_name": "销售数据分析",
      "description": "用于分析销售业绩、趋势、产品表现等",
      "supported_skills": ["sql_query", "file_read", "python_execute", "rag_search"],
      "default_model": "gpt-4",
      "max_iterations": 15
    }
  ]
}
```

## 工具使用

### RAG查询

```python
# 工具调用
{
  "name": "rag_search",
  "arguments": {
    "scene_code": "sales_analysis",
    "query": "销售数据表结构",
    "type": "schema"
  }
}
```

### SQL执行

```python
# 工具调用
{
  "name": "execute_sql",
  "arguments": {
    "sql_text": "SELECT SUM(amount) FROM sales WHERE date >= '2024-01-01'",
    "scene_code": "sales_analysis"
  }
}
```

### Python执行

```python
# 工具调用
{
  "name": "execute_python",
  "arguments": {
    "code": "import pandas as pd\n# 数据分析代码...",
    "timeout": 60
  }
}
```

### 文件操作

```python
# 读取文件
{
  "name": "read_file",
  "arguments": {
    "file_path": "data/sales.csv",
    "limit": 100
  }
}

# 写入文件
{
  "name": "write_file",
  "arguments": {
    "file_path": "analysis/report.py",
    "content": "# Python代码..."
  }
}
```

## 开发说明

### 添加新工具

1. 继承`BaseTool`类
2. 实现`execute`方法
3. 在`AgentWrapper`中注册工具

示例：

```python
from .base import BaseTool, tool_result

class MyTool(BaseTool):
    name = "my_tool"
    description = "我的工具描述"
    
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        },
        "required": ["param1"]
    }
    
    async def execute(self, param1: str) -> Dict[str, Any]:
        # 实现工具逻辑
        result = "处理结果"
        return tool_result(result)
```

### 添加新Channel

1. 继承`BaseChannel`类
2. 实现认证、消息发送方法

示例：

```python
from .base import BaseChannel

class MyChannel(BaseChannel):
    def __init__(self):
        super().__init__("my_channel")
    
    async def authenticate(self, token: str):
        # 实现认证逻辑
        pass
    
    def get_user_id(self, request):
        # 获取用户ID
        return "user_id"
    
    async def send_message(self, chat_id, content, metadata=None):
        # 发送消息
        pass
```

## 存储结构

```
/workspace/
├── sessions/                          # 会话存储
│   ├── web_user123/                    # Web用户
│   │   ├── conv_20240315_001.json     # 对话1
│   │   └── conv_20240315_002.json     # 对话2
│   ├── dingtalk_ding456/               # 钉钉用户
│   └── feishu_fei789/                  # 飞书用户
├── files/                             # 用户文件
│   ├── web_user123/
│   │   └── sales_data.csv
│   └── dingtalk_ding456/
└── shared/                            # 共享资源
    └── scenes.json                    # 场景配置
```

## 外部服务集成

### RAG服务

需要配置RAG服务地址（在`chatbi/config.py`中）：

```python
rag_api_url: str = "http://my_rag_v1"
```

### SQL服务

需要配置SQL执行服务地址：

```python
sql_api_url: str = "http://my_hive_sql_exec"
```

## 注意事项

1. **安全性**: 
   - Python代码在沙箱中执行（生产环境建议使用opensandbox）
   - 文件操作限制在用户目录内
   - SQL仅允许SELECT查询

2. **性能优化**:
   - Loop队列使用多worker并发处理
   - 对话历史支持滑动窗口
   - 文件上传限制50MB

3. **扩展性**:
   - 支持水平扩展（无状态服务）
   - 支持多LLM提供商
   - 支持自定义工具和Channel

## 故障排查

### 服务无法启动

检查：
- Python版本（需要3.10+）
- 依赖包是否安装完整
- 工作目录权限

### 消息处理失败

检查：
- Loop队列是否正常运行
- Agent包装器是否初始化
- 日志中的错误信息

### 文件操作失败

检查：
- 用户目录是否存在
- 文件路径是否正确
- 文件大小是否超限

## 许可证

基于nanobot项目构建，遵循原项目许可证。

## 联系方式

如有问题，请提交Issue或联系开发团队。
