# ChatBI Memory功能说明

## 概述

ChatBI集成了memory功能，提供两级内存系统：
- **Global Memory**: 全局共享的内存，所有用户都能访问
- **User Memory**: 用户专属的内存，基于user_id:channel进行隔离

## 目录结构

```
workspace/
└── memory/
    ├── _global/
    │   ├── MEMORY.md      # 全局内存
    │   └── HISTORY.md     # 全局历史记录
    └── users/
        └── {user_id}_{channel}/
            ├── MEMORY.md  # 用户专属内存
            └── HISTORY.md # 用户历史记录
```

## 核心组件

### 1. MemoryStore

用于读写memory的核心类。

**主要方法：**
- `read_long_term()`: 读取全局+用户memory
- `write_long_term(content, level)`: 写入指定级别的memory
- `append_long_term(content, level)`: 追加到指定级别的memory
- `get_memory_context()`: 获取格式化的memory上下文（用于LLM）
- `append_history(entry, level)`: 添加历史记录

### 2. MemoryManager

提供CRUD操作的管理类，主要用于API端点。

**主要方法：**
- `get_global_memory()`: 获取全局memory
- `get_user_memory(user_id, channel)`: 获取用户memory
- `set_global_memory(content)`: 设置全局memory
- `set_user_memory(user_id, channel, content)`: 设置用户memory
- `delete_user_memory(user_id, channel)`: 删除用户memory
- `list_users()`: 列出所有有memory的用户
- `get_stats()`: 获取memory统计信息

## 配置

在 `config/chatbi.json` 中配置memory：

```json
{
  "memory": {
    "enabled": true,
    "level": "both"
  }
}
```

- `enabled`: 是否启用memory功能
- `level`: memory级别，可选值：`global`, `user`, `both`

## 使用示例

### 基本使用

```python
from chatbi.core.memory import MemoryStore
from pathlib import Path

# 创建MemoryStore（用户级别）
workspace = Path("/path/to/workspace")
memory_store = MemoryStore(workspace, memory_key="user123:web")

# 读取memory
content = memory_store.read_long_term()

# 写入memory
memory_store.write_long_term("用户偏好：喜欢使用Python进行数据分析", level="user")

# 追加memory
memory_store.append_long_term("新增信息", level="user")

# 获取memory上下文（用于LLM）
context = memory_store.get_memory_context()
```

### 在Agent中使用

AgentWrapper自动集成了memory功能：

1. **读取memory**: 在构建系统提示时，会自动读取memory并添加到上下文中
2. **更新memory**: 在处理完用户请求后，会自动记录历史到memory

### API管理（可选）

可以添加API端点来管理memory：

```python
from chatbi.core.memory import MemoryManager

manager = MemoryManager(workspace)

# 获取全局memory
global_memory = manager.get_global_memory()

# 获取用户memory
user_memory = manager.get_user_memory("user123", "web")

# 设置用户memory
manager.set_user_memory("user123", "web", "新的memory内容")

# 列出所有用户
users = manager.list_users()

# 获取统计信息
stats = manager.get_stats()
```

## 集成说明

### 1. MemoryStore的创建

在 `AgentWrapper.__init__` 中：
```python
self.memory_store = MemoryStore(workspace)
```

### 2. Memory上下文设置

在 `AgentWrapper._set_tool_context` 中：
```python
memory_key = f"{user_channel}:web"
self.memory_store = MemoryStore(workspace, memory_key=memory_key)
```

### 3. Memory上下文注入

在 `AgentWrapper._build_messages` 中：
```python
memory_context = self.memory_store.get_memory_context()
if memory_context:
    system_prompt = f"{system_prompt}\n\n{memory_context}"
```

### 4. History记录

在 `AgentWrapper.process` 中：
```python
if chatbi_config.memory_enabled:
    self._update_memory(conversation, message, final_content, tools_used)
```

## 使用场景

1. **用户偏好记忆**: 记住用户的分析偏好（如图表类型、数据维度等）
2. **上下文延续**: 跨会话保持上下文信息
3. **经验总结**: 记录成功的分析案例和经验
4. **全局知识**: 存储所有用户共享的知识库

## 注意事项

1. **Memory大小**: Memory文件可能很大，建议定期清理或限制大小
2. **隐私保护**: User memory是隔离的，但Global memory对所有用户可见
3. **性能考虑**: 读取大文件可能影响性能，建议使用增量更新
4. **数据持久化**: Memory数据保存在文件系统中，注意备份

## 测试

运行memory功能测试：
```bash
python3 chatbi/test_memory.py
```

## 后续优化

1. 添加memory大小限制
2. 实现memory的自动压缩和归档
3. 添加memory的向量检索（RAG）
4. 实现memory的导入/导出功能
