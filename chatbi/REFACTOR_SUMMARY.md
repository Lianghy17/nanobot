# ChatBI 沙箱改造总结

## 改造目标

将所有用户相关的文件操作和Python执行都迁移到沙箱环境中，确保安全性。workspace目录仅用于存储sessions和memory。

## 改造文件清单

### 1. 核心沙箱模块

#### `chatbi/core/sandbox_manager.py`
**改动类型**：增强功能

**新增方法**：
- `read_file(filename, limit)` - 从沙箱读取文件
- `list_files()` - 列出沙箱中的所有文件
- `upload_file(filename, content)` - 上传文件到沙箱
- `get_file(filename)` - 获取文件二进制内容

**增强方法**：
- `write_file(filename, content)` - 增加父目录自动创建

### 2. 文件操作工具

#### `chatbi/agent/tools/file_ops.py`
**改动类型**：完全重构

**ReadFileTool改造**：
- 从直接读取 `/workspace/files/{user_channel}` 改为从沙箱读取
- 新增 `conversation_id` 和 `sandbox_manager` 属性
- 新增 `set_conversation_id()` 方法
- 调用 `session.sandbox.read_file()` 读取文件

**WriteFileTool改造**：
- 从直接写入 `/workspace/files/{user_channel}` 改为写入沙箱
- 新增 `conversation_id` 和 `sandbox_manager` 属性
- 新增 `set_conversation_id()` 方法
- 调用 `session.sandbox.write_file()` 写入文件

### 3. Python执行工具

#### `chatbi/agent/tools/python_tool.py`
**改动类型**：简化文件处理

**改动**：
- 移除 `_save_file_to_conversation()` 方法
- 生成的文件保留在沙箱中，不再保存到sessions目录
- 文件元数据标记 `in_sandbox: True`

### 4. 文件API

#### `chatbi/api/files.py`
**改动类型**：完全重构

**download_file**：
- 从 `sessions_path` 读取文件改为从沙箱读取
- 调用 `session.sandbox.get_file()` 获取文件内容
- 返回 Response 对象而不是 FileResponse

**list_files**：
- 从 `sessions_path` 遍历文件改为从沙箱获取
- 调用 `session.sandbox.list_files()` 获取文件列表
- 沙箱不存在时返回空列表（而不是错误）

### 5. 对话API

#### `chatbi/api/conversations.py`
**改动类型**：新增功能

**新增方法**：
- `upload_file(conversation_id, file)` - 上传文件到沙箱
  - 获取沙箱会话
  - 读取文件内容
  - 调用 `session.sandbox.upload_file()` 上传到沙箱

### 6. 配置模块

#### `chatbi/config.py`
**改动类型**：新增属性

**新增属性**：
- `memory_path` - 内存目录路径
- `workspace_path` - 工作空间路径（通过settings）
- `memory_enabled` - 是否启用memory
- `memory_level` - memory级别（global/user/both）

### 7. Agent包装器

#### `chatbi/core/agent_wrapper.py`
**改动类型**：集成memory（之前已完成）

**改动**：
- 导入 MemoryStore
- 初始化 memory_store
- _set_tool_context 中设置 memory_key
- _build_messages 中注入 memory 上下文
- process 结束时更新 memory（可选）

## 新增文件

### 1. Memory模块

#### `chatbi/core/memory.py`
**功能**：两级内存系统（global + user）

**主要类**：
- `MemoryStore` - 内存读写操作
- `MemoryManager` - 内存CRUD管理器

**核心方法**：
- `read_long_term()` - 读取内存
- `write_long_term()` - 写入内存
- `append_long_term()` - 追加内存
- `get_memory_context()` - 获取LLM上下文格式
- `append_history()` - 记录历史

### 2. Memory配置

#### `config/chatbi.json`
**新增配置段**：
```json
{
  "memory": {
    "enabled": true,
    "level": "both"
  }
}
```

### 3. 文档

#### `chatbi/MEMORY.md`
Memory功能使用文档

#### `chatbi/SANDBOX_REFACTOR.md`
沙箱重构架构文档

### 4. 测试文件

#### `chatbi/test_memory.py`
Memory基本功能测试

#### `chatbi/test_memory_integration.py`
Memory与Agent集成测试

#### `chatbi/test_sandbox_files.py`
沙箱文件操作测试

## 工作流程变化

### 重构前

```
用户上传文件 → workspace/files/{user_channel}/
用户执行Python → 沙箱执行 → 生成文件 → sessions/{user_channel}/{conv_id}/
读取文件 → workspace/files/{user_channel}/
```

### 重构后

```
用户上传文件 → 沙箱 workspace/
用户执行Python → 沙箱执行 → 生成文件 → 沙箱 workspace/
读取文件 → 沙箱 workspace/
```

**关键变化**：
- 所有文件操作都在沙箱中进行
- workspace只存放sessions和memory（后续迁移到数据库）
- 不再有 `/workspace/files` 目录

## 安全性提升

### 1. 隔离性
- 每个会话独立的沙箱环境
- 独立的临时目录
- 限制的环境变量

### 2. 资源限制
- 内存：512MB
- CPU：60秒
- 文件句柄：100
- 进程数：10

### 3. 自动清理
- 超时沙箱自动清理（20分钟）
- 临时目录由系统回收

### 4. 路径安全
- 限制在沙箱workspace目录内
- 相对路径访问
- 防止路径遍历攻击

## API变化

### 新增API

```
POST /api/conversations/{conversation_id}/upload
- 上传文件到沙箱
```

### 变更API

```
GET /api/files/download/{user_channel}/{conversation_id}/{filename}
- 从沙箱下载文件（原：从sessions下载）

GET /api/files/list/{user_channel}/{conversation_id}
- 列出沙箱文件（原：列出sessions文件）
```

### 新增管理API

```
GET /api/sandboxes/stats
- 沙箱统计信息

GET /api/sandboxes/list
- 列出所有活跃沙箱
```

## 测试结果

### Memory功能测试

✅ Memory基本功能测试通过
✅ AgentWrapper集成测试通过
✅ Memory级别配置测试通过

### 沙箱文件操作测试

✅ 沙箱创建
✅ 文件上传
✅ 文件写入
✅ 文件读取
✅ 文件列表
✅ 二进制文件获取
✅ 嵌套目录支持
✅ 沙箱清理

## 使用示例

### 1. 上传文件

```bash
curl -X POST "http://localhost:8080/api/conversations/conv_123/upload" \
  -F "file=@data.csv"
```

### 2. Python中使用

```python
import pandas as pd

# 读取上传的文件（在沙箱中）
df = pd.read_csv('data.csv')

# 分析数据
result = df.describe()

# 保存结果（在沙箱中）
result.to_csv('result.csv')
```

### 3. 下载文件

```bash
curl "http://localhost:8080/api/files/download/web_default_user/conv_123/result.csv" \
  -o result.csv
```

### 4. 查看沙箱状态

```bash
curl "http://localhost:8080/api/sandboxes/stats"
```

## 向后兼容性

### 不兼容的改动

1. **文件路径变化**：
   - 旧：`/workspace/files/{user_channel}/file.csv`
   - 新：沙箱workspace目录

2. **文件访问方式**：
   - 旧：直接访问文件系统
   - 新：必须通过沙箱API

3. **文件持久化**：
   - 旧：文件保存在sessions目录
   - 新：文件在沙箱中，超时清理

### 兼容方案

1. **前端需要更新**：
   - 文件上传endpoint改为 `/upload`
   - 文件下载URL保持不变（API层适配）
   - 文件列表调用保持不变（API层适配）

2. **现有数据迁移**：
   - `/workspace/files` 中的旧文件需要手动迁移或清理
   - sessions目录中的文件可以保留（但建议清理）

## 后续计划

### 短期（已完成）

- ✅ Memory功能集成
- ✅ 沙箱文件操作
- ✅ 文件上传到沙箱
- ✅ 文件从沙箱下载

### 中期

- [ ] Sessions数据库迁移
- [ ] Memory数据库迁移
- [ ] 数据库CRUD API
- [ ] 沙箱性能优化

### 长期

- [ ] 沙箱池化
- [ ] 分布式沙箱管理
- [ ] 文件病毒扫描
- [ ] 沙箱镜像和快照

## 注意事项

1. **沙箱临时性**
   - 沙箱中的文件20分钟后自动清理
   - 需要长期保存的文件应该通过API下载

2. **内存功能**
   - Memory已集成到AgentWrapper
   - 配置文件中可控制启用/禁用
   - 支持global和user两级

3. **资源限制**
   - 注意文件大小（建议<10MB）
   - 注意Python执行时间（限制60秒）
   - 注意内存使用（限制512MB）

4. **并发访问**
   - 同一conversation_id复用沙箱
   - 避免并发修改同一文件

## 故障排查

### 问题：沙箱创建失败

**检查**：
```bash
# 查看沙箱统计
curl "http://localhost:8080/api/sandboxes/stats"

# 查看日志
tail -f logs/chatbi.log
```

### 问题：文件上传404

**原因**：沙箱不存在或已超时

**解决**：先发送消息激活沙箱

### 问题：下载文件失败

**检查**：
```bash
# 列出沙箱文件
curl "http://localhost:8080/api/files/list/web_default_user/conv_123"
```

## 总结

本次改造实现了以下目标：

1. ✅ 所有文件操作迁移到沙箱
2. ✅ workspace只存放sessions和memory
3. ✅ 提升系统安全性和隔离性
4. ✅ 集成Memory功能
5. ✅ 保持API兼容性（大部分）

系统架构更加清晰、安全、可维护。
