# 图片展示问题诊断指南

## 🔍 问题分析

前端无法展示图片通常由以下几个原因造成：

### 1. **Session ID 格式问题**（已修复）
**问题**：session_id 中的冒号 `:` 在 URL 中被处理不一致
**修复**：统一使用 `replace(":", "_")` 处理 session_id

### 2. **图片 URL 构造问题**（已修复）
**问题**：前端构造的图片 URL 可能不正确
**修复**：确保使用正确的 BASE URL 拼接

### 3. **CORS 跨域问题**（已修复）
**问题**：图片请求没有正确的 CORS 头
**修复**：为图片响应添加 `Access-Control-Allow-Origin: *`

### 4. **图片未生成**（需要检查）
**问题**：Python 代码执行后没有生成图片
**原因**：
- 用户代码中没有调用 `plt.show()`
- matplotlib 未安装
- 代码执行出错

## ✅ 已应用的修复

### 后端修复 (`nanobot/server/app.py`)

1. **图片 API 路径处理**：
```python
# 统一使用下划线替换冒号
safe_session_id = session_id.replace(":", "_")
plot_path = workspace / "notebooks" / safe_session_id / plot_name
```

2. **CORS 头**：
```python
response = send_file(str(plot_path), mimetype='image/png')
response.headers.add('Access-Control-Allow-Origin', '*')
```

3. **URL 生成**：
```python
safe_session_id = session_id.replace(":", "_")
plots.append(f"/api/plots/{safe_session_id}/{plot_name}")
```

### 前端修复 (`frontend/index.html`)

1. **图片错误处理**：
```javascript
<img src="${fullUrl}" alt="Chart"
     onerror="this.onerror=null; this.parentElement.innerHTML='<div style=color:#ef4444;>❌ 图片加载失败</div>';">
```

## 🧪 诊断步骤

### 步骤 1: 运行调试脚本

```bash
cd /Users/lianghaoyun/project/nanobot
python debug_images.py
```

这个脚本会：
1. 执行 Python 代码生成图片
2. 验证图片 URL 可访问性
3. 检查 CORS 头
4. 扫描所有可用的图片文件

### 步骤 2: 检查浏览器开发者工具

1. 打开浏览器开发者工具 (F12)
2. 切换到 **Network** 标签
3. 执行生成图表的 Python 代码
4. 查看图片请求：
   - 检查请求 URL 是否正确
   - 检查响应状态码 (应该是 200)
   - 检查响应头中的 `Content-Type` (应该是 `image/png`)

### 步骤 3: 手动测试图片 URL

在浏览器地址栏直接访问图片 URL：
```
http://localhost:5088/api/plots/<session_id>/plot_0.png
```

将 `<session_id>` 替换为实际的会话 ID（冒号替换为下划线）。

### 步骤 4: 检查服务器日志

启动服务器时启用调试日志：
```bash
python -m nanobot.server.app 2>&1 | grep -E "(plot|image|debug)"
```

查看是否有图片相关的调试信息。

## 📝 正确使用方式

### 生成图表的代码示例

```python
/code
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 4))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
plt.show()  # 必须有这一行！
```

**关键要点**：
1. 必须调用 `plt.show()` 来触发生成图表
2. 使用 `/code` 前缀告诉系统这是 Python 代码
3. 图表会自动保存并显示

## 🔧 常见问题

### Q: 图片显示 "❌ 图片加载失败"
**A**: 
1. 检查浏览器开发者工具的 Network 标签，查看具体错误
2. 运行 `python debug_images.py` 诊断
3. 确认服务器日志没有错误

### Q: 图表生成了但前端不显示
**A**:
1. 检查 API 返回的 `plots` 字段是否包含 URL
2. 手动访问图片 URL 测试
3. 检查 CORS 头是否正确

### Q: Python 代码执行报错
**A**:
1. 确认安装了 matplotlib: `pip install matplotlib`
2. 检查代码语法是否正确
3. 查看返回的错误信息

### Q: Notebook 中能看到图片但前端不显示
**A**:
1. Notebook 和图片使用相同的存储路径
2. 检查前端是否正确获取了图片 URL
3. 可能是 URL 拼接问题，检查浏览器 Network 请求

## 🚀 快速验证

执行以下命令验证修复是否生效：

```bash
# 1. 重启服务器
cd /Users/lianghaoyun/project/nanobot
python -m nanobot.server.app

# 2. 在另一个终端运行测试
python debug_images.py

# 3. 在浏览器中测试
# 访问 http://localhost:5088
# 发送 /code 命令生成图表
```

## 📊 预期结果

修复成功后，当你发送以下代码：

```python
/code
import matplotlib.pyplot as plt
plt.plot([1, 2, 3], [1, 4, 9])
plt.title('Test')
plt.show()
```

你应该看到：
1. 执行结果显示 "📊 Generated 1 chart(s)"
2. 聊天界面显示图表图片
3. 可以点击查看 Notebook 中的完整记录
