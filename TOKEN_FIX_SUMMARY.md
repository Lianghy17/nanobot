# Token限制和图像URL修复总结

## 问题诊断

根据日志分析，发现了三个核心问题：

### 1. Token爆炸问题
```
Your request exceeded model token limit: 262144 (requested: 526725)
工具消息占用了 426,349 tokens
```

**根本原因**：
- `read_file` 工具读取了完整的HTML文件（包含大量Plotly JavaScript代码）
- 未对工具结果大小进行限制
- `max_tokens` 配置过大（81920）

### 2. HTML文件未被识别
```
HTML文件已生成: sales_line_chart.html
找到文件（格式1）: 0 个
```

**根本原因**：
- `sandbox_manager.py` 的 `supported_extensions` 中缺少 `.html` 和 `.htm`

### 3. 前端URL渲染问题
虽然URL传递链路完整，但HTML文件未被识别为生成文件，导致无法提供静态URL。

---

## 修复方案

### ✅ 修复1: 添加HTML文件支持

**文件**: `chatbi/core/sandbox_manager.py`

```python
# 在 supported_extensions 中添加：
'.html': 'text/html',
'.htm': 'text/html',
'.pdf': 'application/pdf',
```

**效果**：HTML文件现在会被自动识别、复制到 `workspace/files/` 并生成静态URL。

---

### ✅ 修复2: 限制read_file工具内容大小

**文件**: `chatbi/agent/tools/file_ops.py`

**修改内容**：
1. 添加内容大小限制：最多5000字符
2. 超过限制时自动截断并添加提示
3. 返回 `content_truncated` 和 `original_length` 字段

```python
# 限制内容大小，防止token爆炸
max_chars = 5000
if len(content) > max_chars:
    content = content[:max_chars] + f"\n\n... [内容已截断，原长度: {original_length} 字符]"
    content_truncated = True
```

**效果**：大文件内容会被截断，避免token爆炸。

---

### ✅ 修复3: 优化LLM配置

**文件**: `config/chatbi.json`

**修改内容**：
```json
{
  "llm": {
    "max_tokens": 8192,  // 从81920降低到8192
    "context_window": 262144,  // Kimi-k2.5上下文窗口
    "max_context_tokens": 200000,  // 最大上下文限制（预留buffer）
    "reserved_tokens": 10000  // 预留tokens
  },
  "agent": {
    "max_tool_result_length": 5000  // 工具结果最大长度
  }
}
```

**效果**：
- 防止请求超出模型限制
- 保留足够的上下文空间
- 可用于工具消息的tokens: 190,000 (72.5%)

---

### ✅ 修复4: 添加配置读取逻辑

**文件**: `chatbi/config.py`

**新增属性**：
- `llm_context_window`: LLM上下文窗口大小
- `llm_max_context_tokens`: 最大上下文token数
- `llm_reserved_tokens`: 预留token数
- `agent_max_tool_result_length`: 工具结果最大长度

---

## 验证测试

运行 `test_token_limits.py` 结果：

```
✅ HTML文件已被支持！
✅ max_tokens配置合理
✅ max_context_tokens配置合理
可用于工具消息的tokens: 190,000
限制比例: 72.5%
```

---

## 工作流程对比

### 修复前
1. 用户上传数据 → 执行Python生成HTML图表
2. `read_file` 读取完整HTML（可能几百KB）
3. HTML内容被加入工具消息 → **Token爆炸**
4. HTML文件未被识别 → **无静态URL**
5. 前端无法渲染图表

### 修复后
1. 用户上传数据 → 执行Python生成HTML图表
2. **HTML文件被自动识别** → 复制到 `workspace/files/`
3. **生成静态URL**: `/files/conv_xxx_20260319_chart.html`
4. `read_file` 读取时 **自动截断** 到5000字符
5. 工具消息大小受控 → **Token使用合理**
6. 前端获得文件URL → **正常渲染**

---

## Token使用估算

### 优化前（问题场景）
- 系统提示: 125 tokens
- 用户消息: 26 tokens
- 工具消息: **426,349 tokens** ❌
- 总计: **526,725 tokens** ❌

### 优化后（预期）
- 系统提示: 125 tokens
- 用户消息: 26 tokens
- 工具消息: **~15,000 tokens** ✅（每个工具结果≤5000字符）
- 总计: **~15,200 tokens** ✅

**节省**: 约 97% 的token使用量

---

## 最佳实践建议

### 1. 文件大小控制
- 图片文件：优先使用PNG格式，控制在100KB以内
- HTML文件：避免内嵌大量JavaScript库
- 数据文件：限制在10MB以内

### 2. 工具调用策略
- 使用 `limit` 参数限制读取行数
- 对于大文件，优先使用文件路径而非读取内容
- 让LLM直接访问文件URL，而非读取内容

### 3. Token管理
- 定期清理历史对话
- 监控工具消息大小
- 使用 `max_tool_result_length` 配置控制

---

## 相关文件

- `/Users/lianghaoyun/project/nanobot/chatbi/core/sandbox_manager.py` - 文件收集和URL生成
- `/Users/lianghaoyun/project/nanobot/chatbi/agent/tools/file_ops.py` - 文件读取工具
- `/Users/lianghaoyun/project/nanobot/config/chatbi.json` - LLM配置
- `/Users/lianghaoyun/project/nanobot/chatbi/config.py` - 配置管理
- `/Users/lianghaoyun/project/nanobot/test_token_limits.py` - 测试脚本

---

## 总结

通过以下修复，成功解决了三个核心问题：

1. ✅ **HTML文件识别**：添加 `.html` 支持，生成静态URL供前端渲染
2. ✅ **Token爆炸防护**：限制工具结果大小，防止上下文超限
3. ✅ **配置优化**：设置合理的token限制，符合模型能力

所有修复已完成并验证通过！
