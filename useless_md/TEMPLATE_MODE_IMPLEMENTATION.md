# 模板模式功能实现总结

## 需求概述

实现以下功能：

1. **当用户选择右侧某个模板时**：
   - 对话框引导用户完成模板参数输入
   - 输入框右上角模式改成：模板模式

2. **当未选择模板时**：
   - 右上角显示：React模式
   - 当用户输入问题时，利用RAG模块判定是否匹配上模板
   - 匹配上的话：告知用户当前使用的是哪个模板，引导用户完成模板参数输入，**生成SQL但不执行**
   - 如果未匹配上模板：使用React模式，直接用大模型和Python等工具完成数据分析

## 核心变更

### SQL生成但不执行

**重要变更**：模板模式下，系统**只生成SQL语句，不执行SQL查询**。

**工作流程**：
1. 用户选择模板并填写参数
2. 系统使用Pattern模式构建SQL
3. **不执行SQL**（不调用execute_sql工具，不查询数据库）
4. 直接返回SQL语句给用户查看
5. 用户可以复制SQL在数据库中手动执行

**实现细节**：
- `_process_with_pattern()`方法不再生成mock数据
- 不调用`execute_sql`工具
- `tools_used`列表为空
- 响应中只包含SQL语句和参数说明
- 响应格式简洁明了，便于用户查看SQL

## 实现细节

### 1. 后端修改

#### 1.1 AgentWrapper.process() 方法

**文件**: `chatbi/core/agent_wrapper.py`

**主要修改**：
- 在处理消息时，首先检查用户是否选择了模板（通过`metadata.template_mode`判断）
- 如果用户选择了模板，调用`_guide_template_params()`方法引导用户填写参数
- 如果未选择模板，使用IntentAnalyzer进行意图分析，利用RAG检索相关QA示例
- 根据意图分析结果选择Pattern模式或React模式

**关键代码**:
```python
# 检查是否是用户选择了模板（前端点击模板）
if message.metadata and message.metadata.get("template_mode"):
    template_id = message.metadata.get("template_id")
    template_data = message.metadata.get("template_data", {})

    logger.info(f"[模板模式] 用户选择了模板: {template_id}")

    # 引导用户填写参数
    return await self._guide_template_params(conversation, message, template_data)
```

#### 1.2 新增 _guide_template_params() 方法

**文件**: `chatbi/core/agent_wrapper.py`

**功能**：
- 接收用户选择的模板数据
- 根据模板的`params_schema`生成参数引导信息
- 按必需参数和可选参数分组展示
- 返回格式化的参数引导文本

**返回格式**:
```python
{
    "content": "参数引导文本",
    "tools_used": [],
    "metadata": {
        "template_mode": True,
        "template_id": "template_id",
        "template_name": "模板名称",
        "pattern_id": "pattern_id",
        "params_schema": {...},
        "mode": "template"
    }
}
```

#### 1.3 IntentAnalyzer.analyze() 方法增强

**文件**: `chatbi/core/intent_analyzer.py`

**主要修改**：
- 在分析用户意图时，使用RAG工具检索相关的QA示例
- 将RAG检索到的上下文加入到分析prompt中
- 提高模板匹配的准确度

**关键代码**:
```python
# 使用RAG工具检索QA示例
logger.info(f"[意图分析] 使用RAG检索相关QA示例...")
rag_result = await rag_tool.execute(
    scene_code=scene_code or "sales_analysis",
    query=user_query,
    type="qa"  # 只检索QA示例
)

# 将RAG上下文加入到prompt中
prompt = self._build_analysis_prompt(user_query, supported_patterns, context, rag_context)
```

#### 1.4 修复 _process_with_pattern() 方法的mode标记

**文件**: `chatbi/core/agent_wrapper.py`

**修改**：
- 在Pattern模式需要澄清时，确保metadata中包含`mode: "template"`

### 2. 前端修改

#### 2.1 修改默认模式为React模式

**文件**: `frontend/js/app.js`

**修改**：
- 在创建对话时，默认显示React模式（`switchMode('react')`）
- 移除了之前默认显示模板模式的代码

#### 2.2 添加 intent_analyzed 事件处理

**文件**: `frontend/js/app.js`

**功能**：
- 监听后端发送的`intent_analyzed`事件
- 根据意图分析结果更新模式指示器

**关键代码**:
```javascript
eventSource.addEventListener('intent_analyzed', (event) => {
    const data = JSON.parse(event.data);

    // 根据意图分析结果更新模式指示器
    if (data.mode) {
        switchMode(data.mode);
    }
});
```

#### 2.3 修改HTML初始模式状态

**文件**: `frontend/index.html`

**修改**：
- 将模式指示器的初始状态从`template-mode`改为`react-mode`
- 图标从🎯改为🤖
- 文字从"模板模式"改为"React模式"

### 3. 测试验证

#### 3.1 测试脚本

**文件**: `test_template_mode.py`

**测试用例**：
1. **测试1：用户选择模板**
   - 验证模式识别为template
   - 验证正确引导用户填写参数
   - 验证metadata中包含正确的模板信息

2. **测试2：用户直接输入问题**
   - 验证系统使用IntentAnalyzer进行意图分析
   - 验证使用RAG检索相关QA示例
   - 验证根据匹配结果选择合适的模式

**测试结果**：所有测试通过 ✅

## 工作流程

### 场景1：用户选择模板

1. 用户点击右侧QA模板库中的某个模板
2. 前端调用`useTemplate()`，发送消息并携带模板元数据
3. 后端检测到`metadata.template_mode=True`且包含完整的`template_data`
4. 后端调用`_guide_template_params()`生成参数引导
5. 后端返回参数引导信息，metadata中标记`mode: "template"`
6. 前端收到响应，更新模式指示器为"模板模式"
7. 用户看到参数引导，填写参数
8. 用户继续提供参数，系统使用Pattern模式**生成SQL（不执行）**
9. 后端返回SQL语句给用户查看

### 场景2：用户直接输入问题

1. 用户在输入框直接输入问题
2. 后端检测到没有模板元数据
3. 后端使用IntentAnalyzer进行意图分析
4. IntentAnalyzer调用RAG工具检索相关QA示例
5. 根据RAG检索结果和Pattern定义，判断是否匹配模板
6. 如果匹配模板：
   - 标记为Pattern模式
   - 引导用户填写参数
   - **生成SQL（不执行）**
7. 如果未匹配模板：
   - 使用React模式
   - 调用大模型和Python等工具灵活分析

## 关键特性

1. **智能意图识别**：利用RAG检索相关QA示例，提高模板匹配准确度
2. **清晰的参数引导**：按必需参数和可选参数分组，提供默认值和选项说明
3. **模式自动切换**：根据用户行为和意图分析结果自动切换模式
4. **视觉反馈**：输入框右上角的模式指示器实时显示当前模式
5. **降级处理**：当Pattern模式失败时，自动降级到React模式
6. **SQL生成不执行**：模板模式下只生成SQL，不执行查询，用户可手动执行
7. **续接模式支持**：用户填写参数后，系统能识别上下文并继续处理

## 文件清单

### 后端文件
- `chatbi/core/agent_wrapper.py` - Agent核心逻辑
- `chatbi/core/intent_analyzer.py` - 意图分析器

### 前端文件
- `frontend/index.html` - HTML结构
- `frontend/js/app.js` - JavaScript逻辑

### 测试文件
- `test_template_mode.py` - 功能测试脚本

## 注意事项

1. RAG服务需要正确配置，否则会使用模拟数据
2. Pattern配置文件需要正确定义模板和参数schema
3. 前端和后端的模式标识需要保持一致
4. SSE连接需要正常建立才能接收实时事件

## 后续优化建议

1. 增强RAG检索的准确性，添加更多QA示例
2. 优化参数引导界面，提供更友好的输入方式（如下拉选择、日期选择器等）
3. 添加模板使用历史记录，方便用户快速重复使用
4. 支持模板参数的保存和复用
5. 添加模板匹配的可视化展示，让用户了解匹配过程
