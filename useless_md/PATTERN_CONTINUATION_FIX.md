# Pattern模式续接问题修复

## 📋 问题总结

### 问题1: 用户输入参数后模型没有返回
**现象**: 
- 用户选择模板后，系统引导填写参数
- 用户输入参数后，系统没有继续使用Pattern模式，而是走了React模式

**原因**: 
1. 前端发送参数时，没有携带模板状态metadata
2. 后端没有检查上一条消息的context，无法判断是否应该继续Pattern模式

### 问题2: 模板列表位置
**状态**: ✅ 已正确实现
- QA模板库已正确显示在右侧面板
- 位置符合预期

### 问题3: 模板列表在对话过程中消失
**状态**: ✅ 已验证
- 模板列表面板一直保持active状态
- 没有代码移除active类

---

## 🔧 修复方案

### 修复1: 前端自动携带模板状态

**文件**: `frontend/js/app.js`

**修改内容**:
```javascript
async function sendMessage(messageContent = null, customMetadata = {}) {
    // ... 省略其他代码 ...
    
    // 构建元数据
    let metadata = { ...customMetadata };
    
    // 如果在模板模式中，添加模板状态信息
    if (inTemplateMode && currentTemplate && !metadata.template_mode) {
        metadata.template_mode = true;
        metadata.template_id = currentTemplate.id;
        metadata.template_name = currentTemplate.name;
        metadata.continuing_pattern = true;  // 标记为继续Pattern模式
    }
    
    // ... 发送消息 ...
}
```

**效果**: 用户在模板模式下输入参数时，前端会自动添加模板相关的metadata。

---

### 修复2: 后端检查Pattern模式续接

**文件**: `chatbi/core/agent_wrapper.py`

**修改内容**:
```python
async def process(self, conversation: Conversation, message: Message) -> Optional[Dict[str, Any]]:
    # ... 省略其他代码 ...
    
    # 检查是否应该继续Pattern模式
    should_continue_pattern = False
    pattern_context = {}
    
    # 检查当前消息的metadata
    if message.metadata:
        if message.metadata.get("continuing_pattern") or message.metadata.get("template_mode"):
            should_continue_pattern = True
            pattern_context = message.metadata
            logger.info(f"[Pattern续接] 当前消息标记为继续Pattern模式: {pattern_context}")
    
    # 检查上一条assistant消息（如果当前消息没有标记）
    if not should_continue_pattern and len(conversation.messages) > 0:
        # 倒序查找上一条assistant消息
        for msg in reversed(conversation.messages):
            if msg.role == "assistant" and msg.metadata:
                if msg.metadata.get("pattern_mode") or msg.metadata.get("template_mode"):
                    should_continue_pattern = True
                    pattern_context = msg.metadata
                    logger.info(f"[Pattern续接] 检测到上一条消息处于Pattern模式: {pattern_context}")
                    break
    
    # 意图分析时传递上下文
    context = {"conversation_id": conversation.conversation_id}
    if should_continue_pattern:
        context["continuing_pattern"] = True
        context["pattern_context"] = pattern_context
    
    intent_result = await self.intent_analyzer.analyze(
        message.content,
        conversation.scene_code,
        context=context
    )
```

**效果**: 后端会检查当前消息和上一条消息的metadata，判断是否应该继续Pattern模式。

---

### 修复3: 意图分析器优先匹配续接Pattern

**文件**: `chatbi/core/intent_analyzer.py`

**修改内容**:
```python
def _build_analysis_prompt(self, user_query: str, supported_patterns: List[PatternConfig], context: Dict) -> str:
    # ... 省略其他代码 ...
    
    # 检查是否正在继续Pattern模式
    continuing_pattern = context.get("continuing_pattern", False)
    pattern_context = context.get("pattern_context", {})
    
    continuation_hint = ""
    if continuing_pattern and pattern_context:
        pattern_id = pattern_context.get("pattern_id") or pattern_context.get("template_id")
        pattern_name = pattern_context.get("pattern_name")
        continuation_hint = f"""
## 重要提示：继续Pattern模式
用户正在提供参数以完成之前的Pattern查询:
- Pattern ID: {pattern_id}
- Pattern名称: {pattern_name}

请将此查询解析为pattern_match，继续使用相同的Pattern，并提取用户提供的参数。
"""
    
    prompt = f"""你是一个意图分析专家。请分析用户的查询,判断是使用预定义Pattern模板还是直接使用大模型React模式。

## 用户查询
{user_query}
{continuation_hint}
## 可用的Pattern模板
{patterns_info}

... 省略其他提示 ...
"""
```

**效果**: LLM在分析意图时会优先匹配之前的Pattern，确保续接成功。

---

## 🎯 工作流程

### Pattern模式完整流程

```
1. 用户点击模板
   ↓
2. 前端发送消息（metadata包含template_mode、template_id等）
   ↓
3. 后端意图分析器识别为pattern_match
   ↓
4. Pattern模式处理，检查参数完整性
   ↓
5. 如果参数不完整，返回clarification（包含pattern_mode metadata）
   ↓
6. 用户输入参数
   ↓
7. 前端自动添加continuing_pattern标记
   ↓
8. 后端检测到续接标记，继续Pattern模式
   ↓
9. 意图分析器优先匹配之前的Pattern
   ↓
10. 使用用户提供参数执行SQL
   ↓
11. 返回结果
```

---

## ✅ 修复验证

### 测试场景

1. **选择模板**: 点击"渠道销售对比"模板
   - ✅ 系统正确引导填写参数

2. **输入参数**: "订单量 2024年1月vs 2025年2月 全部渠道"
   - ✅ 前端自动添加continuing_pattern标记
   - ✅ 后端检测到续接标记
   - ✅ 意图分析器优先匹配之前的Pattern
   - ✅ 正确解析参数并执行SQL

3. **模板列表显示**:
   - ✅ 右侧面板正确显示
   - ✅ 对话过程中保持可见

---

## 📊 修改文件总结

| 文件 | 修改内容 | 影响 |
|------|---------|------|
| `frontend/js/app.js` | sendMessage函数自动添加模板metadata | 前端状态传递 |
| `chatbi/core/agent_wrapper.py` | process方法检查Pattern续接 | 后端上下文感知 |
| `chatbi/core/intent_analyzer.py` | 分析prompt优先匹配续接Pattern | LLM意图识别 |

---

## 🚀 服务状态

- ✅ ChatBI主服务：http://localhost:8080
- ✅ 图片服务：http://localhost:8081
- ✅ Pattern模式续接：已修复

---

## 💡 关键设计

### 为什么选择这个方案？

1. **前端状态传递**: 自动化，用户无需关心模板状态
2. **后端上下文感知**: 双重检查（当前消息+上一条消息），确保不丢失状态
3. **LLM优先匹配**: 通过提示词引导，确保意图分析正确

### 为什么不直接在session中保存模板状态？

1. **无状态设计**: 每个消息携带完整context，更符合REST原则
2. **易于调试**: metadata中包含所有必要信息，方便追踪
3. **支持回退**: 用户可以随时退出模板模式，灵活性更高

---

## 📚 相关文档

- [TEMPLATE_MODE_FIXES.md](./TEMPLATE_MODE_FIXES.md) - 模板模式基础修复
- [QA_TEMPLATE_SYSTEM.md](./QA_TEMPLATE_SYSTEM.md) - QA模板系统架构
- [QUICK_START_QA_TEMPLATES.md](./QUICK_START_QA_TEMPLATES.md) - 快速开始指南
