# 前端文件显示问题诊断指南

## 问题现象
前端显示了markdown文本，但没有显示生成的图片文件。

## 已确认的数据
从session文件可以看到，metadata中确实有文件数据：
```json
"metadata": {
  "files": [
    {
      "filename": "temperature_trend.png",
      "type": "image/png",
      "size": 47124,
      "path": "temperature_trend.png",
      "in_sandbox": true
    }
  ]
}
```

## 诊断步骤

### 1. 打开测试页面
在浏览器中打开：
```
file:///Users/lianghaoyun/project/nanobot/test_file_display.html
```
或者在Web服务器中访问：
```
http://localhost:port/test_file_display.html
```

### 2. 测试API连接
点击"测试API连接"按钮，确保后端API可以访问。

### 3. 加载会话
在"加载指定会话"中输入你的会话ID：`conv_1773809745_a5e1017a`
点击"加载会话"按钮。

**期望结果：**
- ✅ 会话加载成功
- ✅ 显示消息数量
- ✅ 第2条消息（第一条assistant消息）显示：
  - 有metadata: ✅
  - 有files字段: ✅
  - files数组长度: 2
  - 文件列表包括 temperature_trend.png

**如果显示"没有文件数据！**：**
- 说明API返回的数据有问题

### 4. 测试图片下载
在"测试文件下载"中，点击"测试下载"按钮。

**期望结果：**
- ✅ 图片正常显示
- ✅ 没有显示404或错误

**如果图片显示为破损图标：**
- 说明文件下载API有问题

### 5. 测试文件列表API
点击"获取文件列表"按钮。

**期望结果：**
- ✅ 显示找到的文件
- ✅ 包括 temperature_trend.png

## 浏览器控制台调试

### 方法1：在测试页面中加载调试脚本
在浏览器控制台中执行：

```javascript
// 加载调试脚本
const script = document.createElement('script');
script.src = '/frontend/js/debug.js';
document.head.appendChild(script);

// 然后运行调试函数
debugMessageRendering(messages);
```

### 方法2：直接在实际页面中调试
在ChatBI前端页面打开控制台（F12），在加载消息后执行：

```javascript
// 获取当前对话的消息
fetch('/api/conversations/conv_1773809745_a5e1017a')
  .then(r => r.json())
  .then(conv => {
    console.log('=== 会话数据 ===');
    console.log('消息列表:', conv.messages);

    // 检查每条消息的metadata
    conv.messages.forEach((msg, idx) => {
      if (msg.role === 'assistant') {
        console.log(`\n消息 ${idx}:`);
        console.log('  有metadata:', !!msg.metadata);
        console.log('  metadata:', msg.metadata);
        console.log('  files:', msg.metadata?.files);
      }
    });
  });
```

### 方法3：检查网络请求
在浏览器开发者工具的Network标签中：

1. 刷新页面，加载会话
2. 找到 `/api/conversations/conv_1773809745_a5e1017a` 请求
3. 点击查看Response
4. 检查消息的metadata字段

**期望看到的响应：**
```json
{
  "conversation_id": "conv_1773809745_a5e1017a",
  "messages": [
    {
      "role": "assistant",
      "content": "...",
      "metadata": {
        "files": [
          {
            "filename": "temperature_trend.png",
            "type": "image/png",
            "size": 47124,
            "path": "temperature_trend.png",
            "in_sandbox": true
          }
        ],
        "format": "markdown"
      }
    }
  ]
}
```

## 常见问题和解决方案

### 问题1：API返回的metadata为空
**原因：** ConversationManager保存消息时没有保存metadata

**解决：** 检查 message_processor.py 的 add_message 调用

### 问题2：metadata存在但files为空
**原因：** Agent没有正确提取文件信息

**解决：** 检查后端日志中的 `_extract_files_from_tool_results` 输出

### 问题3：metadata和files都正确，但前端不显示
**原因：** 前端renderFiles函数返回空字符串

**解决：** 检查浏览器控制台是否有JavaScript错误

### 问题4：文件显示但图片不显示
**原因：** 图片下载URL不正确或文件不存在

**解决：** 检查 `/api/files/download/` 端点

## 前端渲染流程

```
1. loadConversation(conversationId)
   ↓
2. fetch('/api/conversations/{id}')
   ↓
3. renderMessages(conversation.messages)
   ↓
4. 对每条assistant消息:
   - markdownHtml = marked.parse(content)
   - filesHtml = renderFiles(msg.metadata?.files)
   ↓
5. renderFiles(files):
   - 检查files是否为空
   - 对每个文件判断是否为图片
   - 生成HTML
   ↓
6. 插入到页面DOM
```

## 临时修复方案

如果确认是前端渲染问题，可以临时在浏览器控制台手动添加图片：

```javascript
// 找到消息容器
const messages = document.querySelectorAll('.message.assistant .bubble');

// 获取第二条assistant消息（包含文件的那条）
if (messages[1]) {
  // 手动添加图片
  const imgHtml = `
    <div class="files-section">
      <div class="files-section-title">📎 生成的文件 (2)</div>
      <div class="image-container">
        <img src="/api/files/download/web_default_user/conv_1773809745_a5e1017a/temperature_trend.png"
             alt="temperature_trend.png"
             style="max-width:100%; border-radius:4px;">
        <div class="image-caption">temperature_trend.png (47.0 KB)</div>
      </div>
    </div>
  `;
  messages[1].insertAdjacentHTML('beforeend', imgHtml);
}
```

## 下一步

1. 使用测试页面进行诊断
2. 在浏览器控制台运行调试代码
3. 检查网络请求和响应
4. 将诊断结果反馈，以便进一步定位问题
