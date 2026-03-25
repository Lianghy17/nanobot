# 前端模式指示器更新

## 修改说明

### 1. 输入框右上角添加模式指示器

在输入框右上角添加了一个浮动的模式指示器，实时显示当前的工作模式（模板模式或React模式）。

**HTML结构** (index.html):
```html
<!-- 输入区域 -->
<div class="input-area">
    <!-- 模式指示器 -->
    <div class="mode-indicator template-mode" id="modeIndicator">
        <span class="mode-icon">🎯</span>
        <span id="modeText">模板模式</span>
    </div>
    ...
</div>
```

**CSS样式** (index.html):
```css
.mode-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 10;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.mode-indicator.template-mode {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.mode-indicator.react-mode {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}
```

**JavaScript函数** (js/app.js):
```javascript
// 更新模式指示器（在输入框右上角）
function updateModeIndicator(mode) {
    const indicator = document.getElementById('modeIndicator');
    const modeText = document.getElementById('modeText');

    if (!indicator || !modeText) {
        return;
    }

    // 移除所有模式类
    indicator.classList.remove('template-mode', 'react-mode');

    if (mode === 'template') {
        indicator.classList.add('template-mode');
        indicator.querySelector('.mode-icon').textContent = '🎯';
        modeText.textContent = '模板模式';
    } else if (mode === 'react') {
        indicator.classList.add('react-mode');
        indicator.querySelector('.mode-icon').textContent = '🤖';
        modeText.textContent = 'React模式';
    }
}
```

### 2. QA模板库只显示模板模式的模板

修改了`renderQATemplates`函数，只过滤并显示`mode='template'`或没有`mode`字段的模板。

**JavaScript修改** (js/app.js):
```javascript
// 只显示模板模式的模板（mode='template'或没有mode字段的模板）
const allTemplates = qaData.templates || [];
const templateModeTemplates = allTemplates.filter(t => !t.mode || t.mode === 'template');

if (templateModeTemplates.length === 0) {
    hotQuestionsList.innerHTML = '<div class="loading"><p>暂无模板模式的QA模板</p></div>';
    return;
}
```

### 3. 移除右侧面板的模式选择器

移除了右侧QA模板库面板顶部的模式选择器，简化界面。

**修改前**:
```html
<div class="hot-questions-header">
    <h3>📋 QA模板库</h3>
    <div class="mode-selector">
        <div class="mode-btn active" data-mode="template">...</div>
        <div class="mode-btn" data-mode="react">...</div>
        <div class="mode-btn" data-mode="qa">...</div>
    </div>
</div>
```

**修改后**:
```html
<div class="hot-questions-header">
    <h3>📋 QA模板库</h3>
    <p style="font-size: 12px; color: #7f8c8d; margin: 5px 0 0 0;">点击模板快速生成分析</p>
</div>
```

### 4. 删除冗余的CSS

删除了不再使用的模式选择器相关的CSS样式：
- `.mode-selector`
- `.mode-btn`
- `.mode-btn .mode-label`
- `.mode-btn .mode-desc`

### 5. 重命名消息中的模式指示器样式

为了避免样式冲突，将消息中的模式指示器样式重命名为`.message-mode-indicator`：
```css
.message-mode-indicator {
    /* 原来的.mode-indicator样式 */
}
```

## 功能说明

### 模式指示器行为

1. **初始状态**: 创建对话后，默认显示"模板模式"（🎯 模板模式）
2. **自动切换**: 当系统响应消息的`metadata.mode`字段时，指示器自动更新
3. **手动切换**: 用户点击"退出模板模式"按钮时，切换到React模式（🤖 React模式）

### 模式区分

| 模式 | 图标 | 颜色 | 说明 |
|------|------|------|------|
| 模板模式 | 🎯 | 紫色渐变 | 使用预定义模板，快速生成SQL |
| React模式 | 🤖 | 粉红渐变 | 灵活工具调用，支持复杂分析 |

### QA模板库

- 只显示`mode='template'`或没有`mode`字段的模板
- 点击模板后会进入模板模式
- 系统会引导用户填写参数并生成SQL

## 技术细节

### 1. 响应消息中的模式

当收到后端响应时，系统会检查`metadata.mode`字段：
```javascript
// 在appendMessage函数中
if (metadata.mode) {
    switchMode(metadata.mode);
}
```

### 2. 退出模板模式

点击"退出模板模式"按钮会：
1. 设置`inTemplateMode = false`
2. 清除`currentTemplate`
3. 调用`switchMode('react')`更新指示器
4. 发送系统消息提示用户

### 3. 样式隔离

- 输入框的模式指示器: `.mode-indicator`
- 消息中的模式提示: `.message-mode-indicator`

两者使用不同的类名，避免样式冲突。

## 修改文件

1. **frontend/index.html**
   - 添加模式指示器HTML
   - 修改右侧面板HTML（移除模式选择器）
   - 添加CSS样式
   - 删除冗余CSS

2. **frontend/js/app.js**
   - 添加`updateModeIndicator()`函数
   - 修改`renderQATemplates()`过滤模板
   - 简化`switchMode()`函数
   - 修改`appendMessage()`自动更新模式

## 测试建议

1. **创建对话**: 验证指示器初始显示为"模板模式"
2. **点击QA模板**: 验证使用模板后指示器保持为"模板模式"
3. **触发React模式**: 提问一个不匹配模板的问题，验证指示器切换为"React模式"
4. **退出模板模式**: 点击"退出模板模式"按钮，验证指示器切换为"React模式"
5. **QA模板过滤**: 检查右侧面板只显示模板模式的模板

## 更新日期

2026-03-23
