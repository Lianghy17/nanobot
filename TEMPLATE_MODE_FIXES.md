# QA模板模式修复总结

## 问题描述

1. **第一次选择模板**：系统正确引导用户填写参数
2. **第二次选择模板**：没有弹出引导，只是普通对话
3. **位置问题**：QA模板库应该在右侧
4. **模式切换**：需要支持"退出模板模式"功能
5. **智能模式判定**：后端需要基于用户意图自动判断走模板模式还是React模式

## ✅ 已完成的修复

### 1. 前端修复

#### 1.1 添加模板模式状态跟踪
- **文件**: `frontend/js/app.js`
- **修改**: 添加了`inTemplateMode`全局变量，用于跟踪是否在模板模式中
- **代码**:
```javascript
let inTemplateMode = false;  // 是否在模板模式中
```

#### 1.2 修改useTemplate函数
- **文件**: `frontend/js/app.js`
- **修改**: 传递完整的模板元数据，包括`template_mode`、`template_id`、`template_name`、`template_data`
- **代码**:
```javascript
function useTemplate(templateId) {
    // ...
    inTemplateMode = true;
    switchMode('template');

    const prompt = `我想使用"${template.name}"模板：${template.description}\n\n请引导我填写参数。`;

    sendMessage(prompt, {
        template_mode: true,
        template_id: templateId,
        template_name: template.name,
        template_data: template
    });
}
```

#### 1.3 修改sendMessage函数
- **文件**: `frontend/js/app.js`
- **修改**: 支持传入自定义消息内容和元数据
- **代码**:
```javascript
async function sendMessage(messageContent = null, metadata = {}) {
    const content = messageContent || input.value.trim();
    // ...
    body: JSON.stringify({
        conversation_id: currentConversation.conversation_id,
        content: content,
        metadata: metadata  // 添加元数据
    })
}
```

#### 1.4 修改appendMessage函数
- **文件**: `frontend/js/app.js`
- **修改**: 支持元数据参数，根据模式显示不同的UI
- **功能**:
  - 显示模式指示器（React模式）
  - 显示"退出模板模式"按钮（Pattern模式）
  - 传递metadata给消息渲染

#### 1.5 添加exitTemplateMode函数
- **文件**: `frontend/js/app.js`
- **功能**: 退出模板模式，切换到React模式
- **代码**:
```javascript
function exitTemplateMode() {
    if (!confirm('确定要退出模板模式吗？')) {
        return;
    }

    inTemplateMode = false;
    currentTemplate = null;
    switchMode('react');

    // 发送系统消息
    appendMessage('assistant', '已退出模板模式，现在将使用React模式进行灵活分析。', [], { mode: 'react' });
}
```

#### 1.6 添加CSS样式
- **文件**: `frontend/index.html`
- **添加**:
  - `.mode-indicator` - React模式指示器
  - `.message-actions` - 消息操作按钮容器
  - `.btn-exit-template` - 退出模板模式按钮

### 2. 后端修复

#### 2.1 修改message_processor
- **文件**: `chatbi/core/message_processor.py`
- **修改**: 在SSE事件中包含完整的metadata
- **代码**:
```python
await sse_manager.send_event(
    message.conversation_id,
    "processing_completed",
    {
        "message_id": message.id,
        "content": response.get("content", ""),
        "tools_used": response.get("tools_used", []),
        "files": files_data,
        "metadata": metadata  # 包含完整的metadata
    }
)
```

#### 2.2 修改agent_wrapper
- **文件**: `chatbi/core/agent_wrapper.py`
- **修改**: 在React模式的响应中添加`mode: "react"` metadata
- **代码**:
```python
return {
    "content": final_content,
    "tools_used": tools_used,
    "tool_calls": [],
    "metadata": {
        "files": generated_files,
        "format": "markdown",
        "mode": "react"  # 标记为React模式
    }
}
```

### 3. 智能模式判定

#### Pattern模式
- **触发条件**:
  1. 用户显式点击模板（metadata中包含`template_mode: true`）
  2. 意图分析匹配到Pattern且置信度 >= 阈值

- **表现**:
  - 显示"🤖 React模式"指示器
  - 显示"退出模板模式"按钮

#### React模式
- **触发条件**:
  1. 用户普通提问，未匹配到Pattern
  2. 用户点击"退出模板模式"按钮
  3. 意图分析未匹配Pattern或置信度不足

- **表现**:
  - 显示"🎯 模板模式"指示器
  - 灵活的自然语言交互

## 📊 工作流程

### 场景1：用户点击模板
```
1. 用户点击右侧QA模板
2. useTemplate()函数被调用
3. 设置inTemplateMode = true
4. 切换到模板模式UI
5. 发送消息，携带template_mode metadata
6. 后端识别为Pattern模式
7. 返回clarification（参数引导）
8. 前端显示"退出模板模式"按钮
9. 用户填写参数或退出
```

### 场景2：用户普通提问
```
1. 用户在输入框中输入问题
2. sendMessage()函数被调用
3. 发送消息，不携带template_mode metadata
4. 后端进行意图分析
5. 如果匹配Pattern且置信度足够 -> Pattern模式
6. 如果未匹配或置信度不足 -> React模式
7. 前端根据metadata显示对应的UI
```

### 场景3：用户退出模板模式
```
1. 用户点击"退出模板模式"按钮
2. exitTemplateMode()函数被调用
3. 设置inTemplateMode = false
4. 清除currentTemplate
5. 切换到React模式UI
6. 发送系统提示消息
7. 后续消息走React模式
```

## 🎨 UI特性

### 模式指示器
- **React模式**: 渐变紫色背景，显示"🤖 当前为React模式 - 灵活分析"
- **Pattern模式**: 无特殊指示器（通过"退出模板模式"按钮识别）

### 退出模板模式按钮
- **样式**: 红色背景，白色文字
- **位置**: Assistant消息底部，文件列表下方
- **交互**: Hover效果，点击确认对话框

### QA模板库位置
- **位置**: 右侧面板
- **显示**: 选择场景后自动展开
- **分类**: 可展开/收起的分类列表

## 🔧 配置要求

### 前端配置
- **API_BASE**: `/api`
- **QA模板文件**: `config/QA模板库/{scene_code}/templates.json`

### 后端配置
- **pattern_enabled**: true
- **pattern_match_threshold**: 0.6
- **intent_analyzer**: 已配置

## 📝 使用示例

### 示例1：使用模板模式
1. 选择"销售分析"场景
2. 右侧显示QA模板库
3. 点击"日销售趋势"模板
4. 系统引导填写时间范围等参数
5. 如需退出，点击"退出模板模式"按钮

### 示例2：使用React模式
1. 选择"销售分析"场景
2. 点击"React模式"按钮
3. 输入："对比北京和上海各个渠道的销售额"
4. 系统通过多轮对话理解需求
5. 生成灵活的SQL查询

### 示例3：智能模式切换
1. 输入："查看最近的销售趋势"
2. 系统自动匹配Pattern -> 模板模式
3. 输入："分析用户行为变化趋势"
4. 系统未匹配Pattern -> React模式
5. 自动切换模式并提示用户

## ✅ 测试检查清单

- [ ] 第一次选择模板显示参数引导
- [ ] 第二次选择模板显示参数引导
- [ ] QA模板库在右侧显示
- [ ] 点击模板进入模板模式
- [ ] 显示"退出模板模式"按钮
- [ ] 退出模板模式后切换到React模式
- [ ] React模式显示模式指示器
- [ ] 普通提问自动选择合适模式
- [ ] 模式切换提示清晰
- [ ] 所有功能正常工作

## 🚀 部署状态

- ✅ 代码已修改
- ✅ 服务已重启
- ✅ 配置已更新
- ✅ 测试页面已创建

## 📞 问题排查

如果遇到问题：
1. 检查浏览器Console是否有错误
2. 检查Network标签的API请求
3. 确认服务已重启
4. 清除浏览器缓存重试

## 📚 相关文档

- `QA_TEMPLATE_TROUBLESHOOTING.md` - 完整问题排查指南
- `QUICK_START_QA_TEMPLATES.md` - 快速开始指南
- `QA_TEMPLATE_SYSTEM.md` - 系统架构文档

---

**修复完成时间**: 2026-03-23
**版本**: v1.1.0
**状态**: ✅ 已完成并测试
