# NanoBot Web 界面

这是一个功能丰富的 Web 界面，用于与 NanoBot AI 助手进行交互。

## ✨ 功能特性

### 基础功能
- ✅ **会话管理**：左侧会话列表，显示所有历史对话
- ✅ **新建会话**：一键创建新的对话
- ✅ **消息发送**：支持文本输入和发送
- ✅ **会话操作**：查看、删除会话

### 高级功能
- 📁 **文件上传**：支持 CSV, Excel, JSON, 文本文件, 图片等多种格式
- 🐍 **Python 代码执行**：使用 `/code` 命令执行 Python 代码
- 📊 **图表展示**：自动显示 matplotlib 等生成的图表
- 📓 **Jupyter Notebook 持久化**：所有代码执行自动保存到 Notebook

## 🚀 快速开始

### 1. 启动 NanoBot 服务器

```bash
cd /Users/lianghaoyun/project/nanobot
python -m nanobot.server.app
```

服务器将在 `http://localhost:5088` 启动

### 2. 访问 Web 界面

在浏览器中打开：
```
http://localhost:5088
```

## 📖 使用指南

### 文件上传

1. 点击输入框上方的 **"上传文件"** 按钮
2. 选择要上传的文件（支持 CSV, Excel, JSON, PNG, JPG 等）
3. 文件会自动保存到工作区，可以在后续分析中使用

上传的文件路径格式：`workspace/uploads/<session_id>/<filename>`

### Python 代码执行

在输入框中使用 `/code` 前缀执行 Python 代码：

```
/code
import pandas as pd
import matplotlib.pyplot as plt

# 读取上传的 CSV 文件
df = pd.read_csv('workspace/uploads/<session_id>/data.csv')
print(df.head())

# 绘制图表
plt.figure(figsize=(10, 6))
plt.plot(df.index, df['value'])
plt.title('Data Analysis')
plt.show()
```

**特点：**
- 代码会自动保存到 Jupyter Notebook
- 点击右上角 **"Notebook"** 按钮可以查看完整的 Notebook
- matplotlib 图表会自动显示在聊天界面

### 图表展示

当 Python 代码生成图表时（使用 `plt.show()`），图表会自动：
1. 显示在聊天消息中
2. 保存为 PNG 文件
3. 嵌入到 Jupyter Notebook 中

## 📡 API 端点

Web 界面使用以下 API：

### 基础 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/sessions` | GET | 获取会话列表 |
| `/api/sessions/<session_id>` | GET | 获取会话历史 |
| `/api/sessions/<session_id>` | DELETE | 删除会话 |
| `/api/agent/chat` | POST | 发送消息给 AI |

### 文件上传 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传文件 |
| `/api/files/<session_id>` | GET | 获取会话文件列表 |
| `/api/files/<session_id>/<filename>` | GET | 获取文件 |

### Python 执行 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/python/execute` | POST | 执行 Python 代码 |
| `/api/notebooks/<session_id>` | GET | 获取 Jupyter Notebook |
| `/api/plots/<session_id>/<plot_name>` | GET | 获取生成的图表 |

## 🗂️ 文件结构

```
workspace/
├── uploads/
│   └── <session_id>/
│       ├── data.csv
│       ├── image.png
│       └── ...
└── notebooks/
    └── <session_id>/
        └── analysis.ipynb  # 自动生成的 Notebook
```

## ⚙️ 配置说明

如需修改 API 地址，编辑 `frontend/index.html` 中的：

```javascript
const API_BASE = 'http://localhost:5088/api';
```

## 🔧 依赖要求

- Python 3.11+
- Flask（已在项目中）
- 可选：pandas, matplotlib, seaborn（用于数据分析）

安装数据分析依赖：
```bash
pip install pandas matplotlib seaborn plotly
```

## 📝 使用示例

### 示例 1：数据分析

1. 上传一个 CSV 文件
2. 发送消息：
```
请分析这个 CSV 文件的数据特征
```
3. AI 会自动读取文件并分析

### 示例 2：代码执行

```
/code
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 4))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
plt.show()
```

### 示例 3：文件处理

```
/code
import pandas as pd

# 读取上传的 CSV
df = pd.read_csv('workspace/uploads/<your_session>/sales.csv')

# 显示统计信息
print(df.describe())

# 创建可视化
import matplotlib.pyplot as plt
df['revenue'].hist(bins=20)
plt.title('Revenue Distribution')
plt.show()
```

## 🐛 故障排除

### 文件上传失败
- 检查文件大小（最大 50MB）
- 检查文件格式是否被允许
- 查看浏览器控制台错误信息

### Python 代码执行失败
- 确保所需的 Python 包已安装
- 检查代码语法
- 查看服务器日志获取详细错误

### 图表不显示
- 确保使用了 `plt.show()`
- 检查 matplotlib 是否正确安装
- 查看浏览器网络请求是否正常

## 🔒 安全说明

- 所有代码在沙箱环境中执行，有超时限制
- 文件访问被限制在工作区目录内
- 危险命令（如 rm -rf）被自动阻止
