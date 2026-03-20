# 文件存储功能实现总结

## 📋 修改概览

本次修改实现了后端生成的图片和文件自动保存到 `workspace/files` 目录，并通过静态 URL 提供给前端访问的功能。

## 🔧 修改内容

### 1. 后端修改

#### 1.1 修改沙箱管理器 - `chatbi/core/sandbox_manager.py`

**文件路径**: `chatbi/core/sandbox_manager.py`

**修改方法**: `_collect_generated_files()`

**主要改动**:
- 在收集生成的文件后，自动复制文件到 `workspace/files` 目录
- 生成唯一的文件名：`{conversation_id}_{timestamp}_{filename}`
- 添加 `url` 字段指向静态 URL：`/files/{unique_filename}`
- 添加 `unique_filename` 字段保存唯一文件名

**关键代码**:
```python
# 复制文件到 workspace/files
files_dir = os.path.join(os.path.dirname(self.temp_dir), '..', 'workspace', 'files')
os.makedirs(files_dir, exist_ok=True)

# 生成唯一的文件名（避免冲突）
from datetime import datetime
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
unique_filename = f"{self.conversation_id}_{timestamp}_{filename}"
target_path = os.path.join(files_dir, unique_filename)

# 复制文件
with open(file_path, 'rb') as src, open(target_path, 'wb') as dst:
    dst.write(src.read())

generated_files.append({
    'filename': filename,  # 原始文件名
    'unique_filename': unique_filename,  # 唯一文件名
    'type': supported_extensions[ext],
    'size': file_size,
    'url': f'/files/{unique_filename}',  # 静态URL
    'content': content
})
```

#### 1.2 添加静态文件服务 - `chatbi/main.py`

**文件路径**: `chatbi/main.py`

**修改内容**: 挂载 `workspace/files` 静态文件服务

**关键代码**:
```python
# 挂载workspace/files静态文件服务
files_path = Path(__file__).parent.parent / "workspace" / "files"
if files_path.exists():
    app.mount("/files", StaticFiles(directory=str(files_path)), name="files")
    logging.info(f"静态文件服务已挂载: /files -> {files_path}")
else:
    logging.warning(f"workspace/files目录不存在: {files_path}")
```

### 2. 前端修改

#### 2.1 修改图片路径修复逻辑 - `frontend/js/app.js`

**文件路径**: `frontend/js/app.js`

**修改函数**: `fixMarkdownImagePaths()`

**主要改动**:
- 优先使用静态 URL（`file.url`）
- 回退到旧的下载 API（`/api/files/download/...`）

**关键代码**:
```javascript
// 优先使用静态URL
if (fileInfo.url) {
    img.setAttribute('src', fileInfo.url);
    console.log('[fixMarkdownImagePaths] 使用静态URL:', src, '->', fileInfo.url);
} else {
    // 回退到旧的下载API
    const downloadUrl = `/api/files/download/web_default_user/${currentConversation.conversation_id}/${fileInfo.path || fileInfo.filename}`;
    img.setAttribute('src', downloadUrl);
    console.log('[fixMarkdownImagePaths] 使用下载API:', src, '->', downloadUrl);
}
```

#### 2.2 修改文件列表渲染逻辑 - `frontend/js/app.js`

**文件路径**: `frontend/js/app.js`

**修改函数**: `renderFiles()`

**主要改动**:
- 优先使用静态 URL（`file.url`）
- 回退到旧的下载 API

**关键代码**:
```javascript
// 优先使用静态URL，否则使用下载API
let downloadUrl;
if (fileInfo.url) {
    downloadUrl = fileInfo.url;
} else if (fileInfo.path) {
    downloadUrl = `/api/files/download/web_default_user/${currentConversation.conversation_id}/${fileInfo.path}`;
} else {
    downloadUrl = fileInfo.download_url || '#';
}
```

## 📁 文件流程

```
用户发送消息
    ↓
Agent 调用 execute_python 工具
    ↓
Python 代码在沙箱中执行
    ↓
生成文件到沙箱 workspace/ (如 chart.png)
    ↓
SandboxManager._collect_generated_files()
    ↓
复制文件到 workspace/files/{conversation_id}_{timestamp}_{filename}
    ↓
生成文件信息:
  {
    "filename": "chart.png",
    "unique_filename": "web_123_20260319_143022_chart.png",
    "type": "image/png",
    "size": 52428,
    "url": "/files/web_123_20260319_143022_chart.png"
  }
    ↓
返回给前端
    ↓
前端渲染图片:
  <img src="/files/web_123_20260319_143022_chart.png">
```

## 🎯 URL 结构

### 静态文件 URL（推荐）

```
/files/{unique_filename}
```

示例:
- `/files/web_123_20260319_143022_chart.png`
- `/files/web_456_20260319_150512_data.csv`

### 下载 API URL（备用）

```
/api/files/download/{user_channel}/{conversation_id}/{filename}
```

示例:
- `/api/files/download/web_default_user/conv_abc123/chart.png`

## 📊 支持的文件类型

| 扩展名 | MIME 类型 | 说明 |
|--------|-----------|------|
| `.png` | `image/png` | PNG 图片 |
| `.jpg`, `.jpeg` | `image/jpeg` | JPEG 图片 |
| `.gif` | `image/gif` | GIF 图片 |
| `.svg` | `image/svg+xml` | SVG 矢量图 |
| `.csv` | `text/csv` | CSV 文件 |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Excel 文件 |
| `.xls` | `application/vnd.ms-excel` | Excel 97-2003 文件 |
| `.json` | `application/json` | JSON 文件 |
| `.txt` | `text/plain` | 文本文件 |
| `.md` | `text/markdown` | Markdown 文件 |

## ✅ 优势

### 1. 持久化存储
- 文件保存在 `workspace/files` 目录，不会因为沙箱关闭而丢失
- 可以长期访问历史生成的文件

### 2. 简单的 URL
- 静态 URL 格式简洁：`/files/{filename}`
- 前端可以直接渲染，无需复杂的下载逻辑

### 3. 缓存友好
- 浏览器可以缓存静态文件
- 减少服务器压力

### 4. 回退机制
- 如果静态文件不可用，前端仍可使用下载 API
- 保证系统的健壮性

## 🔍 测试

### 测试文件存储配置

运行测试脚本:

```bash
cd /Users/lianghaoyun/project/nanobot/chatbi
python3 test_file_storage.py
```

### 手动测试

1. 启动服务器:
```bash
cd /Users/lianghaoyun/project/nanobot/chatbi
python3 main.py
```

2. 打开浏览器访问 `http://localhost:8080`

3. 创建对话并发送消息:
```
帮我画一个简单的折线图
```

4. Agent 会执行 Python 代码生成图表

5. 检查 `workspace/files` 目录:
```bash
ls -lh workspace/files/
```

应该能看到类似这样的文件:
```
web_web_default_user_20260319_143022_chart.png
```

6. 直接访问静态 URL:
```
http://localhost:8080/files/web_web_default_user_20260319_143022_chart.png
```

应该能直接看到图片。

## 📝 注意事项

### 1. 文件名冲突
- 使用 `{conversation_id}_{timestamp}_{filename}` 格式避免冲突
- 同一会话中多次生成同名文件会被区分

### 2. 磁盘空间
- 长期使用会占用磁盘空间
- 建议定期清理旧的生成文件

### 3. 安全性
- 静态文件服务需要确保文件来源可靠
- 避免执行不受信任的代码

### 4. 文件大小限制
- 目前限制：仅复制小于 10MB 的文件
- 超过此大小的文件不会被复制到 `workspace/files`

## 📚 相关文档

- `chatbi/FILE_STORAGE.md` - 详细的文件存储机制说明
- `chatbi/test_file_storage.py` - 文件存储配置测试脚本

## 🔧 配置检查清单

启动服务器前，确保以下目录存在:

```
nanobot/
├── workspace/
│   ├── files/              # ✅ 必须存在
│   ├── sessions/
│   └── memory/
```

如果目录不存在，服务器会自动创建，但建议提前创建:

```bash
mkdir -p workspace/files
mkdir -p workspace/sessions
mkdir -p workspace/memory
```

## 🚀 下一步

1. **文件清理策略**: 实现定期清理旧文件的功能
2. **文件权限控制**: 添加文件访问权限管理
3. **文件压缩**: 对大文件进行压缩存储
4. **CDN 集成**: 将文件上传到 CDN，提高访问速度
