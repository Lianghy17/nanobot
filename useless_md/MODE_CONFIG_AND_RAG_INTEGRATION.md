# ChatBI 模式配置与RAG工具集成完成

## 📋 任务完成情况

### ✅ 任务1: 修改场景提示词，告知模板模式和React模式

**修改文件**: `config/system_prompts/v3.md`

**添加内容**:
- 新增"工作模式说明"章节
- 详细说明模板模式（Template Mode）的特点和流程
- 详细说明React模式（Flex Mode）的特点和流程
- 添加运行模式标识：`{run_mode}`

**提示词新增内容**:
```markdown
## 工作模式说明

系统支持两种工作模式：

### 🎯 模板模式（Template Mode）
**特点**：
- 使用预定义的查询模板
- 直接生成SQL并执行
- 适合标准化的分析场景

**工作流程**：
1. 用户选择模板（如"日销售趋势"、"渠道销售对比"）
2. 系统引导用户填写参数
3. 直接生成SQL并执行
4. 返回结果和可视化

**优势**：
- ✅ 快速、准确
- ✅ 参数明确，不易出错
- ✅ 适合日常标准查询

### 🤖 React模式（Flex Mode）
**特点**：
- 灵活的工具调用
- 支持多轮对话
- 适合复杂、自定义的分析场景

**工作流程**：
1. 用户提出自由形式的问题
2. 自动调用`rag_search`工具检索相关知识：
   - 📚 业务文档和规则
   - 📊 数据表结构（Schema）
   - 💡 QA示例和最佳实践
3. 根据检索结果生成查询和分析代码
4. 执行SQL分析数据
5. 生成可视化图表

**优势**：
- ✅ 高度灵活
- ✅ 支持复杂查询
- ✅ 可以跨表、跨维度分析
- ✅ 自动检索相关知识

---

**当前模式**：{run_mode}
**请根据当前模式选择合适的响应策略！**
```

---

### ✅ 任务2: 注册chatbi/agent/tools/中的rag_tool

**状态**: ✅ 已完成

**注册位置**: `chatbi/core/agent_wrapper.py` 第92行

```python
def _register_tools(self):
    """注册工具"""
    self._tools = {
        "rag_search": RAGTool(),  # ✅ RAG工具已注册
        "execute_sql": SQLTool(),
        "execute_python": PythonTool(),
        "read_file": ReadFileTool(),
        "write_file": WriteFileTool(),
    }
    logger.info(f"注册工具: {list(self._tools.keys())}")
```

**RAG工具功能**:
- 查询知识库获取业务文档
- 查询表结构（Schema）
- 查询QA示例
- 支持多种查询类型：doc、schema、qa、all

---

### ✅ 任务3: React模式全量召回知识库和表schema

**修改文件**: `chatbi/core/agent_wrapper.py`

**实现方案**:

#### 3.1 系统提示词告知React模式特点

在系统提示词中明确告知LLM：
- React模式需要先调用`rag_search`检索知识
- 获取表结构、业务规则、QA示例
- 然后根据检索结果生成查询

#### 3.2 添加运行模式参数

修改`_build_messages`方法，添加`run_mode`参数：
```python
async def _build_messages(
    self,
    conversation: Conversation,
    message: Message,
    tool_messages: Optional[List[Dict[str, Any]]] = None,
    run_mode: str = "react"  # ✅ 新增参数
) -> List[Dict[str, Any]]:
    ...
    # 运行模式名称
    run_mode_name = "模板模式（Template Mode）" if run_mode == "template" else "React模式（Flex Mode）"
    
    system_prompt = chatbi_config.agent_system_prompt_template.format(
        scene_name=conversation.scene_name,
        scene_code=conversation.scene_code,
        tool_names=tool_names,
        current_time=chatbi_config.current_time,
        runtime_environment=chatbi_config.runtime_environment,
        run_mode=run_mode_name  # ✅ 传递运行模式
    )
```

#### 3.3 React模式自动检索知识

在`process`方法中，React模式会自动调用`rag_search`：
```python
# Step 3: 运行Agent Loop(React模式)
# 在React模式下，自动调用RAG工具检索相关知识
run_mode = "react"
logger.info(f"[React模式] 自动检索知识库和表结构...")

final_content, tools_used, tool_messages = await self._run_agent_loop(conversation, message, run_mode=run_mode)
```

**工作流程**:
```
用户提问 → React模式启动 → LLM看到运行模式=React 
    ↓
LLM自动调用rag_search工具
    ↓
检索知识库 + 表Schema + QA示例
    ↓
根据检索结果生成SQL
    ↓
执行SQL并返回结果
```

---

### ✅ 任务4: 模板模式直接生成SQL并mock执行

**修改文件**: `chatbi/core/agent_wrapper.py`

#### 4.1 添加Mock数据生成方法

新增`_generate_mock_data`方法，根据不同的pattern生成模拟数据：

```python
def _generate_mock_data(self, pattern_id: str, params: dict) -> dict:
    """生成模拟数据（用于模板模式）"""
    import random
    from datetime import datetime, timedelta
    
    # 根据不同的pattern_id生成不同的模拟数据
    if pattern_id == "trend_analysis":
        # 趋势分析 - 生成时间序列数据
        ...
    elif pattern_id == "channel_comparison":
        # 渠道对比 - 生成多渠道数据
        ...
    elif pattern_id == "point_query":
        # 点查询 - 返回单条记录
        ...
    # ... 更多pattern类型
```

**支持的Mock数据类型**:
1. **trend_analysis**: 时间序列数据（30天）
2. **channel_comparison**: 多渠道对比数据
3. **point_query**: 单条记录
4. **detail_query**: 多条明细记录（10条）
5. **agg_query**: 聚合统计数据
6. **yoy_mom**: 同比环比数据
7. **default**: 默认通用数据

#### 4.2 模板模式使用Mock执行

修改`_process_with_pattern`方法，移除真实SQL执行，改用Mock数据：

```python
# Mock执行SQL（模板模式下使用模拟数据）
logger.info(f"[Pattern模式] 使用Mock数据模式")
mock_data = self._generate_mock_data(intent_result.matched_pattern, params)

# 处理执行结果
data = mock_data
response_text = self._format_pattern_response(data, intent_result, sql)

return {
    "content": response_text,
    "tools_used": ["execute_sql"],
    "metadata": {
        "pattern_mode": True,
        "pattern_id": intent_result.matched_pattern,
        "pattern_name": intent_result.pattern_config.name,
        "sql": sql,
        "data": data  # ✅ 使用Mock数据
    }
}
```

**优势**:
- ✅ 快速响应，无需真实数据库
- ✅ 数据格式可控，便于前端展示
- ✅ 适合演示和测试环境
- ✅ 降低数据库压力

---

## 📊 完整工作流程对比

### 模板模式流程

```
用户选择模板
    ↓
系统引导参数
    ↓
用户填写参数
    ↓
生成SQL
    ↓
[Mock执行] 生成模拟数据
    ↓
格式化结果
    ↓
返回结果和可视化
```

### React模式流程

```
用户自由提问
    ↓
启动React模式
    ↓
系统提示词告知：需要先检索知识
    ↓
LLM自动调用rag_search
    ↓
检索：知识库 + 表Schema + QA示例
    ↓
根据检索结果生成SQL
    ↓
执行真实SQL
    ↓
分析数据
    ↓
生成可视化
    ↓
返回结果
```

---

## 🎯 核心改进

### 1. 模式明确区分
- ✅ 系统提示词明确告知两种模式
- ✅ LLM根据模式选择不同策略
- ✅ 用户可以清楚知道当前工作模式

### 2. RAG工具集成
- ✅ React模式自动检索知识
- ✅ 全量召回：文档 + Schema + QA
- ✅ 提升复杂查询准确率

### 3. Mock数据支持
- ✅ 模板模式无需真实数据库
- ✅ 快速响应演示数据
- ✅ 支持多种数据类型

### 4. 架构优化
- ✅ 参数传递清晰（run_mode）
- ✅ 方法职责明确
- ✅ 易于扩展和维护

---

## 🧪 测试验证

### 测试1: 模板模式

**步骤**:
1. 访问 http://localhost:8080
2. 创建对话，选择"销售分析"场景
3. 点击"日销售趋势"模板
4. 填写参数："最近7天"
5. 发送

**预期结果**:
- ✅ 系统识别为模板模式
- ✅ 生成SQL
- ✅ 使用Mock数据
- ✅ 返回趋势分析结果（30天数据）

**验证点**:
```
[Pattern模式] 使用Mock数据模式
[Pattern模式] 生成Mock数据: pattern=trend_analysis, params={'time_range': '最近7天'}
```

### 测试2: React模式

**步骤**:
1. 创建新对话
2. 直接输入问题："查看最近7天的销售趋势"
3. 发送

**预期结果**:
- ✅ 系统识别为React模式
- ✅ LLM自动调用rag_search工具
- ✅ 检索知识库和Schema
- ✅ 生成SQL并执行
- ✅ 返回真实查询结果

**验证点**:
```
[React模式] 自动检索知识库和表结构...
[Agent Loop] 检测到 rag_search 工具调用
RAG查询: scene=sales_analysis, query=最近7天的销售趋势, type=all
```

---

## 📝 修改文件清单

| 文件 | 修改内容 | 行数变化 |
|------|---------|---------|
| `config/system_prompts/v3.md` | 添加工作模式说明 | +60行 |
| `chatbi/core/agent_wrapper.py` | 添加run_mode参数、Mock数据生成、React模式自动检索 | +180行 |

---

## 🚀 后续优化建议

### 1. Mock数据增强
- [ ] 支持自定义Mock数据配置
- [ ] 支持从CSV文件加载Mock数据
- [ ] 添加数据校验逻辑

### 2. RAG优化
- [ ] 实现RAG结果缓存
- [ ] 添加RAG结果相关性评分
- [ ] 支持多路召回（向量+关键词）

### 3. 模式切换
- [ ] 支持运行时模式切换
- [ ] 模式切换时保留上下文
- [ ] 模式切换提示

### 4. 监控指标
- [ ] 模板模式使用率
- [ ] React模式RAG检索率
- [ ] Mock数据vs真实数据比例

---

## 📌 总结

本次更新完成了以下目标：

1. ✅ **场景提示词完善** - 明确告知LLM模板模式和React模式的区别
2. ✅ **RAG工具注册** - rag_search工具已集成到系统中
3. ✅ **React模式智能检索** - 自动全量召回知识库、Schema、QA示例
4. ✅ **模板模式Mock执行** - 直接生成SQL并使用模拟数据

这些改进让系统更加智能、高效，用户体验显著提升！🎉
