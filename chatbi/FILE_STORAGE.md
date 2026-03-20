# 文件存储机制说明

## 概述

ChatBI 支持在 Python 沙箱中执行代码并生成文件（如图表、CSV、Excel 等）。生成的文件会自动保存到 `workspace/files` 目录，并通过静态 URL 提供给前端访问。

## 文件流程

### 1. Python 代码执行

用户发送消息后，Agent 可能会调用 `execute_python` 工具执行 Python 代码：

```python
import matplotlib.pyplot as plt
import pandas as pd

# 生成示例数据
data = pd.DataFrame({
    'x': [1, 2, 3, 4, 5],
    'y': [10, 20, 15, 25, 30]
})

# 绘制图表
plt.figure(figsize=(10, 6))
plt.plot(data['x'], data['y'])
plt.title('示例图表')
plt.xlabel('X轴')
plt.ylabel('Y轴')

# 保存图表到沙箱workspace
plt.savefig('chart.png')
print('图表已保存为 chart.png')
```

### 2. 文件收集与复制

沙箱执行完成后，`SandboxManager._collect_generated_files()` 方法会：

1. 扫描沙箱的 `workspace` 目录
2. 识别生成的文件（支持图片、CSV、Excel、JSON 等）
3. **将文件复制到 `workspace/files` 目录**
4. 生成唯一的文件名：`{conversation_id}_{timestamp}_{filename}`
   - 示例：`web_123_20260319_143022_chart.png`

### 3. 文件信息返回

文件信息会返回给前端，包含以下字段：

```json
{
  "filename": "chart.png",           // 原始文件名
  "unique_filename": "web_123_20260319_143022_chart.png",  // 唯一文件名
  "type": "image/png",              // MIME 类型
  "size": 52428,                   // 文件大小（字节）
  "url": "/files/web_123_20260319_143022_chart.png"  // 静态URL
}
```

### 4. 前端渲染

前端通过以下方式渲染文件：

#### 方式1：Markdown 中的图片

如果 Python 代码输出包含 Markdown 格式的图片引用：

```python
print('![图表](chart.png)')
```

前端会自动将 `chart.png` 替换为静态 URL：

```html
<img src="/files/web_123_20260319_143022_chart.png" alt="chart.png">
```

#### 方式2：独立的文件卡片

前端会渲染所有生成的文件列表：

```html
<div class="files-section">
  <div class="files-section-title">📎 生成的文件 (1)</div>
  <div class="image-container">
    <img src="/files/web_123_20260319_143022_chart.png" alt="chart.png" onclick="openImage('/files/web_123_20260319_143022_chart.png')">
    <div class="image-caption">chart.png (51.2 KB)</div>
  </div>
</div>
```

## 支持的文件类型

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

## URL 结构

### 静态文件 URL（推荐）

```
/files/{unique_filename}
```

示例：
- `/files/web_123_20260319_143022_chart.png`
- `/files/web_456_20260319_150512_data.csv`

### 下载 API URL（备用）

```
/api/files/download/{user_channel}/{conversation_id}/{filename}
```

示例：
- `/api/files/download/web_default_user/conv_abc123/chart.png`

## 配置

### 静态文件挂载

在 `main.py` 中配置：

```python
# 挂载workspace/files静态文件服务
files_path = Path(__file__).parent.parent / "workspace" / "files"
if files_path.exists():
    app.mount("/files", StaticFiles(directory=str(files_path)), name="files")
    logging.info(f"静态文件服务已挂载: /files -> {files_path}")
```

### 目录结构

```
nanobot/
├── workspace/
│   ├── files/                    # 生成的文件存储目录
│   │   ├── web_123_20260319_143022_chart.png
│   │   ├── web_123_20260319_143030_data.csv
│   │   └── ...
│   ├── sessions/                 # 会话数据
│   └── memory/                   # 记忆数据
├── chatbi/
│   ├── core/
│   │   └── sandbox_manager.py    # 沙箱管理器
│   └── ...
└── frontend/
    └── js/
        └── app.js                # 前端应用
```

## 优势

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

## 注意事项

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

## 示例

### 生成图表并显示

**用户输入：**
```
帮我画一个销售数据的折线图
```

**Agent 执行：**
```python
import matplotlib.pyplot as plt

# 生成图表数据
months = ['1月', '2月', '3月', '4月', '5月']
sales = [100, 120, 90, 150, 180]

plt.figure(figsize=(10, 6))
plt.plot(months, sales, marker='o')
plt.title('销售数据折线图')
plt.xlabel('月份')
plt.ylabel('销售额（万元）')
plt.grid(True)
plt.savefig('sales_chart.png')

print('![销售数据折线图](sales_chart.png)')
```

**文件信息：**
```json
{
  "filename": "sales_chart.png",
  "unique_filename": "web_abc_20260319_151234_sales_chart.png",
  "type": "image/png",
  "size": 24576,
  "url": "/files/web_abc_20260319_151234_sales_chart.png"
}
```

**前端显示：**
```
销售数据折线图

[图表图片]
```

## 相关文件

- `chatbi/core/sandbox_manager.py` - 沙箱管理和文件收集
- `chatbi/main.py` - 静态文件服务配置
- `chatbi/api/files.py` - 文件下载 API
- `frontend/js/app.js` - 前端文件渲染逻辑
