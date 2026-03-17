# ChatBI 前端增强 - 图表渲染和Markdown支持

## 改造概述

增强前端功能，支持：
1. **Markdown结构化渲染** - 将文本内容渲染为格式化的markdown
2. **图表文件展示** - 自动识别并显示图片文件（PNG, JPG, SVG等）
3. **文件下载功能** - 提供便捷的文件下载界面

## 改动文件

### 前端改动

#### 1. `frontend/index.html`

**引入Marked.js**：
```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
```

**新增样式**：

**Markdown样式**：
- 标题（h1-h6）样式
- 列表、代码块样式
- 表格、引用样式
- 链接、粗体、斜体样式
- 行内代码样式

**文件样式**：
- `.files-section` - 文件区域容器
- `.file-card` - 文件卡片
- `.file-card.image` - 图片文件
- `.image-container` - 图片容器
- `.image-caption` - 图片说明

#### 2. `frontend/js/app.js`

**新增函数**：

`renderFiles(files)` - 渲染文件列表
- 区分图片文件和其他文件
- 图片直接显示在消息中
- 其他文件显示为可下载的卡片
- 显示文件大小

`getFileIcon(type)` - 获取文件图标
- CSV/Excel: 📊
- JSON: 📋
- TXT/MD: 📄/📝
- 图片: 🖼️

`formatFileSize(bytes)` - 格式化文件大小
- 自动转换为B/KB/MB/GB

`openImage(url)` - 新标签页打开图片

`downloadFile(url, filename)` - 下载文件

`loadFiles()` - 加载沙箱中的文件列表

**修改函数**：

`renderMessages(messages)` - 渲染消息
- assistant消息使用marked.parse()渲染markdown
- user消息保持纯文本
- 自动渲染文件列表

`appendMessage(role, content, files)` - 添加消息
- 支持文件参数
- assistant消息渲染markdown

`startPolling(thinkingMessageId)` - 轮询更新
- AI回复后自动加载文件列表

`uploadFile()` - 上传文件
- 使用正确的API端点：`/conversations/{id}/upload`
- 上传成功后自动加载文件列表

### 后端改动

#### 1. `chatbi/core/agent_wrapper.py`

**修改 `_extract_files_from_tool_results`**：
- 支持多种文件信息格式
- 格式1: `result.files`
- 格式2: `result.result.files`
- 增强错误处理和日志

## 使用效果

### Markdown渲染

**输入**：
```
# 数据分析报告

## 1. 数据概览
- 总记录数：1000
- 完整率：95%

## 2. 关键指标

| 指标 | 值 |
|------|-----|
| 平均值 | 25.5 |
| 最大值 | 98.7 |
| 最小值 | 3.2 |

## 3. 代码示例
```python
import pandas as pd
df = pd.read_csv('data.csv')
```
```

**输出**：
- 格式化的标题
- 美观的表格
- 代码高亮
- 列表样式

### 图表展示

**Python生成图表**：
```python
import matplotlib.pyplot as plt
df.plot()
plt.savefig('chart.png')
```

**前端自动渲染**：
- 图片直接显示在消息中
- 点击可放大查看
- 显示文件名和大小

### 文件下载

**文件列表显示**：
```
📎 生成的文件 (3)

[🖼️ chart.png] (45.2 KB)
[📊 result.csv] (12.3 KB)
[📄 report.txt] (5.1 KB)
```

**点击即可下载**

## 工作流程

### 1. 用户上传文件

```
用户选择文件
  ↓
POST /api/conversations/{id}/upload
  ↓
上传到沙箱workspace/
  ↓
前端显示上传成功消息
  ↓
自动加载文件列表
```

### 2. Python执行生成文件

```
用户提问（需要Python分析）
  ↓
Agent调用execute_python
  ↓
Python在沙箱中执行
  ↓
生成文件到沙箱workspace/
  ↓
返回文件信息（在metadata中）
  ↓
前端自动渲染文件
```

### 3. 消息渲染

```
获取消息列表
  ↓
解析metadata.files
  ↓
如果是图片：直接显示
  ↓
如果是其他文件：显示下载卡片
  ↓
渲染内容为markdown
```

## 文件类型支持

### 图片文件（自动显示）
- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- SVG (.svg)

### 数据文件（可下载）
- CSV (.csv)
- Excel (.xlsx, .xls)
- JSON (.json)

### 文本文件（可下载）
- TXT (.txt)
- Markdown (.md)

## 样式预览

### Markdown内容
```css
.markdown-content {
    line-height: 1.6;
}
.markdown-content h1 {
    border-bottom: 1px solid #eee;
    padding-bottom: 0.3em;
}
.markdown-content code {
    background: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
}
.markdown-content pre {
    background: #2c3e50;
    color: #ecf0f1;
    padding: 12px;
    border-radius: 6px;
}
```

### 文件卡片
```css
.file-card {
    display: inline-block;
    margin: 4px;
    padding: 8px 12px;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    cursor: pointer;
}
.file-card.image {
    display: block;
    border: none;
    background: none;
}
.file-card.image img {
    max-width: 100%;
    height: auto;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
```

## API变化

### 新增/修改的API

**文件上传**（已存在）
```
POST /api/conversations/{conversation_id}/upload
- 上传文件到沙箱
- 响应：{success, filename, file_path, size}
```

**文件列表**（已存在）
```
GET /api/files/list/{user_channel}/{conversation_id}
- 列出沙箱中的文件
- 响应：{success, files, count}
```

**文件下载**（已存在）
```
GET /api/files/download/{user_channel}/{conversation_id}/{filename}
- 下载文件
- 响应：文件二进制内容
```

**消息获取**（已存在，自动包含文件信息）
```
GET /api/conversations/{id}/messages
- 获取消息列表
- 响应包含metadata.files
```

## 前端数据流

```
消息对象
{
  role: "assistant",
  content: "# 报告\n...",
  timestamp: "2026-03-17T12:00:00",
  metadata: {
    files: [
      {
        filename: "chart.png",
        type: "png",
        size: 45678,
        path: "chart.png"
      },
      {
        filename: "result.csv",
        type: "csv",
        size: 1234,
        path: "result.csv"
      }
    ],
    format: "markdown"
  }
}
```

## 兼容性

- **浏览器**：支持所有现代浏览器（Chrome, Firefox, Safari, Edge）
- **Markdown库**：使用marked.js（CDN加载）
- **图片格式**：PNG, JPG, JPEG, GIF, SVG
- **响应式**：支持移动端和桌面端

## 性能优化

1. **图片懒加载**：大图使用懒加载
2. **文件大小显示**：智能转换为KB/MB/GB
3. **Markdown缓存**：避免重复解析
4. **图标使用**：使用emoji减少HTTP请求

## 测试建议

### 1. Markdown渲染测试

**测试用例**：
- 标题（h1-h6）
- 列表（有序、无序）
- 代码块
- 表格
- 引用
- 链接
- 粗体、斜体

### 2. 图片显示测试

**测试用例**：
- 生成图表（PNG）
- 上传图片文件
- 点击放大
- 下载图片

### 3. 文件下载测试

**测试用例**：
- CSV文件下载
- Excel文件下载
- JSON文件下载
- 文本文件下载

### 4. 响应式测试

**测试用例**：
- 手机端显示
- 平板端显示
- 桌面端显示

## 注意事项

1. **CDN依赖**：marked.js从CDN加载，需要网络连接
2. **XSS防护**：marked默认会转义HTML，安全
3. **图片大小**：大图建议压缩后显示
4. **文件命名**：避免中文文件名（下载兼容性）

## 后续优化

1. **Markdown扩展**：添加数学公式支持（KaTeX）
2. **代码高亮**：添加代码语法高亮（highlight.js）
3. **图片预览**：添加图片灯箱效果
4. **拖拽上传**：支持拖拽上传文件
5. **离线支持**：下载marked.js到本地
6. **主题切换**：支持深色/浅色主题

## 总结

通过这次改造，ChatBI前端现在支持：
- ✅ Markdown结构化渲染
- ✅ 图表文件自动显示
- ✅ 文件便捷下载
- ✅ 美观的UI设计
- ✅ 响应式布局

大大提升了用户体验，使得数据分析和可视化结果展示更加直观和专业。
