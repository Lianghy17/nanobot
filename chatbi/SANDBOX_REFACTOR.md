# ChatBI 沙箱架构重构文档

## 重构概述

将所有用户相关的文件操作、Python执行都迁移到沙箱环境中进行，确保安全性。workspace目录仅用于存储sessions和memory，后续将由数据库提供支持。

## 架构变化

### 重构前

```
workspace/
├── files/              # 用户文件（不安全）
│   └── {user_channel}/
├── sessions/           # 对话数据
└── memory/             # 内存数据
```

**问题**：
- 用户文件直接存储在workspace中，存在安全风险
- 文件操作直接访问文件系统，没有隔离
- Python执行和文件操作不在同一环境中

### 重构后

```
workspace/
├── sessions/           # 对话数据（后续迁移到数据库）
└── memory/             # 内存数据（后续迁移到数据库）

沙箱环境（临时目录）：
/var/folders/.../sandbox_{conversation_id}_/
└── workspace/         # 沙箱工作目录
    ├── uploaded.csv    # 用户上传的文件
    ├── analysis.py     # Python代码
    ├── chart.png       # 生成的图表
    └── data/          # 其他生成的文件
```

**改进**：
- 所有用户文件在沙箱中操作，完全隔离
- 沙箱基于临时目录，自动清理
- 统一的文件操作接口
- 安全的资源限制（内存、CPU、进程数）

## 核心组件

### 1. LocalSandbox（本地沙箱）

负责提供隔离的执行环境。

**新增方法**：
```python
async def write_file(filename: str, content: str)
async def read_file(filename: str, limit: int) -> tuple[bool, str, str]
async def list_files() -> list
async def upload_file(filename: str, content: bytes) -> tuple[bool, str, str]
async def get_file(filename: str) -> tuple[bool, bytes, str]
```

**安全特性**：
- 独立的临时工作目录
- 限制的环境变量
- 资源限制（512MB内存、60秒CPU、100文件句柄、10进程）
- 自动超时清理（20分钟）

### 2. SandboxManager（沙箱管理器）

管理会话级别的沙箱生命周期。

**功能**：
- 按conversation_id创建/复用沙箱
- 自动清理超时沙箱
- 沙箱统计信息

### 3. 文件工具改造

#### ReadFileTool
```python
# 重构前：直接读取 /workspace/files/{user_channel}/{file_path}
# 重构后：从沙箱 workspace 目录读取
async def execute(self, file_path: str, limit: int = 100):
    session = await self.sandbox_manager.get_sandbox(self.conversation_id)
    success, content, error = await session.sandbox.read_file(file_path, limit)
```

#### WriteFileTool
```python
# 重构前：直接写入 /workspace/files/{user_channel}/{file_path}
# 重构后：写入到沙箱 workspace 目录
async def execute(self, file_path: str, content: str):
    session = await self.sandbox_manager.get_sandbox(self.conversation_id)
    await session.sandbox.write_file(file_path, content)
```

### 4. PythonTool改造

```python
# 重构前：生成文件保存到 sessions 目录
# 重构后：文件保留在沙箱中
async def execute(self, code: str, timeout: int = 60):
    session = await self.sandbox_manager.get_sandbox(self.conversation_id)
    result = await session.execute_code(code, timeout)
    # result["files"] 中的文件已经在沙箱中
```

### 5. API改造

#### 文件上传 API
```python
@router.post("/{conversation_id}/upload")
async def upload_file(conversation_id: str, file: UploadFile):
    # 获取沙箱
    session = await sandbox_manager.get_sandbox(conversation_id)

    # 读取文件内容
    content = await file.read()

    # 上传到沙箱
    success, file_path, error = await session.sandbox.upload_file(file.filename, content)
```

#### 文件下载 API
```python
@router.get("/download/{user_channel}/{conversation_id}/{filename}")
async def download_file(conversation_id: str, filename: str):
    # 从沙箱获取文件
    session = await sandbox_manager.get_sandbox(conversation_id)
    success, content, error = await session.sandbox.get_file(filename)
```

#### 文件列表 API
```python
@router.get("/list/{user_channel}/{conversation_id}")
async def list_files(conversation_id: str):
    # 列出沙箱中的文件
    session = await sandbox_manager.get_sandbox(conversation_id)
    files = await session.sandbox.list_files()
```

## 工作流程

### 1. 用户上传文件

```
用户上传文件
  ↓
POST /api/conversations/{conversation_id}/upload
  ↓
创建/获取沙箱（如果不存在）
  ↓
上传文件到沙箱的 workspace 目录
  ↓
返回文件路径
```

### 2. Python数据分析

```
用户问题："分析上传的CSV文件"
  ↓
LLM调用 execute_python 工具
  ↓
创建/获取沙箱
  ↓
执行Python代码
  ↓
代码中可以访问上传的文件（在workspace目录）
  ↓
生成的图表/结果文件保存在沙箱中
  ↓
返回文件元数据（路径、类型、大小）
```

### 3. 文件读写

```
LLM需要读取文件
  ↓
调用 read_file 工具
  ↓
从沙箱 workspace 目录读取
  ↓
返回文件内容
```

```
LLM需要保存结果
  ↓
调用 write_file 工具
  ↓
写入到沙箱 workspace 目录
  ↓
返回成功
```

### 4. 文件下载

```
用户下载文件
  ↓
GET /api/files/download/{user_channel}/{conversation_id}/{filename}
  ↓
从沙箱获取文件内容
  ↓
返回文件响应
```

## 沙箱创建策略

### 自动创建

沙箱在以下情况下自动创建：

1. **文件上传时**：调用 `/upload` endpoint
2. **执行Python代码时**：调用 `execute_python` 工具
3. **读取文件时**：调用 `read_file` 工具
4. **写入文件时**：调用 `write_file` 工具

### 沙箱生命周期

```
创建（首次使用工具时）
  ↓
复用（会话期间多次使用）
  ↓
超时（20分钟未使用）自动清理
  ↓
或者手动删除对话时清理
```

## 安全性

### 1. 隔离性
- 每个conversation_id有独立的沙箱
- 独立的临时目录和资源限制
- 限制的环境变量

### 2. 资源限制
- **内存**: 512MB
- **CPU时间**: 60秒
- **文件句柄**: 100
- **进程数**: 10

### 3. 自动清理
- 超时沙箱自动清理（20分钟）
- 应用关闭时清理所有沙箱
- 临时目录由系统自动回收

### 4. 路径安全
- 文件操作限制在沙箱workspace目录内
- 相对路径访问
- 防止路径遍历攻击

## 配置

在 `config/chatbi.json` 中配置沙箱：

```json
{
  "sandbox": {
    "timeout_minutes": 20,
    "cleanup_interval": 60
  }
}
```

**参数说明**：
- `timeout_minutes`: 沙箱超时时间（分钟）
- `cleanup_interval`: 清理间隔（秒）

## 使用示例

### 上传文件

```bash
curl -X POST "http://localhost:8080/api/conversations/conv_123/upload" \
  -F "file=@data.csv"
```

**响应**：
```json
{
  "success": true,
  "filename": "data.csv",
  "file_path": "data.csv",
  "size": 1024,
  "message": "文件已上传到沙箱，可以在Python代码中直接使用"
}
```

### Python代码中使用

```python
import pandas as pd

# 读取上传的文件
df = pd.read_csv('data.csv')

# 进行分析
result = df.describe()

# 保存结果
result.to_csv('result.csv')

# 生成图表
import matplotlib.pyplot as plt
df.plot()
plt.savefig('chart.png')
```

### 下载文件

```bash
# 下载图表
curl "http://localhost:8080/api/files/download/web_default_user/conv_123/chart.png" \
  -o chart.png

# 列出所有文件
curl "http://localhost:8080/api/files/list/web_default_user/conv_123"
```

### 查看沙箱状态

```bash
# 查看沙箱统计
curl "http://localhost:8080/api/sandboxes/stats"

# 列出所有活跃沙箱
curl "http://localhost:8080/api/sandboxes/list"
```

## 测试

运行测试文件验证功能：

```bash
# 测试沙箱文件操作
python3 chatbi/test_sandbox_files.py
```

## 后续计划

1. **数据库迁移**
   - Sessions迁移到数据库
   - Memory迁移到数据库
   - 提供CRUD API

2. **沙箱优化**
   - 支持持久化沙箱（可选）
   - 沙箱镜像和快照
   - 分布式沙箱管理

3. **安全增强**
   - 添加文件类型白名单
   - 文件大小限制
   - 病毒扫描集成

4. **性能优化**
   - 沙箱池化
   - 预热沙箱
   - 缓存机制

## 注意事项

1. **沙箱临时性**
   - 沙箱中的文件在超时后会被清理
   - 需要长期保存的文件应该通过API下载
   - 重要数据建议保存在sessions或memory中

2. **文件路径**
   - 所有文件路径都是相对于沙箱workspace目录
   - 不要使用绝对路径
   - 支持嵌套目录（如 `data/test.csv`）

3. **并发访问**
   - 同一conversation_id的沙箱会复用
   - 避免同时修改同一文件
   - 使用文件锁或临时文件名

4. **资源限制**
   - 大文件上传可能超时
   - 长时间运行的Python代码会被中断
   - 注意内存使用

## 故障排查

### 问题：沙箱创建失败

**可能原因**：
- 磁盘空间不足
- 权限问题
- 资源限制

**解决方法**：
```python
# 查看沙箱统计
curl "http://localhost:8080/api/sandboxes/stats"

# 查看日志
tail -f logs/chatbi.log
```

### 问题：文件上传失败

**可能原因**：
- 沙箱不存在或已超时
- 文件过大
- 磁盘空间不足

**解决方法**：
```python
# 先发送一条消息，激活沙箱
curl -X POST "http://localhost:8080/api/conversations/conv_123/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "hello"}'

# 然后再上传文件
curl -X POST "http://localhost:8080/api/conversations/conv_123/upload" \
  -F "file=@data.csv"
```

### 问题：下载文件404

**可能原因**：
- 沙箱已超时清理
- 文件名错误
- 文件在嵌套目录中

**解决方法**：
```python
# 先列出文件，确认文件名
curl "http://localhost:8080/api/files/list/web_default_user/conv_123"

# 使用正确的文件名下载
curl "http://localhost:8080/api/files/download/web_default_user/conv_123/data/test.csv"
```
