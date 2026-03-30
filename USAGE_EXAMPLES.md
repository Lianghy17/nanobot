# NanoBot 新功能使用示例

## 📁 文件上传与分析

### 示例 1：上传 CSV 并进行分析

1. 点击 "上传文件" 按钮，选择 CSV 文件
2. 输入以下消息：

```
请分析这个 CSV 文件，包括：
1. 数据的基本统计信息
2. 缺失值情况
3. 生成一个数据分布图
```

3. AI 会自动读取文件并生成分析报告

### 示例 2：图片分析

1. 上传一张图片
2. 输入：

```
请描述这张图片的内容
```

## 🐍 Python 代码执行

### 使用 `/code` 命令

在输入框中输入 `/code` 后跟 Python 代码：

```
/code
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_csv('workspace/uploads/web_xxxxx/data.csv')

# 显示前5行
print(df.head())

# 基本统计
print(df.describe())
```

### 示例：数据可视化

```
/code
import matplotlib.pyplot as plt
import numpy as np

# 生成示例数据
np.random.seed(42)
data = np.random.randn(1000)

# 创建直方图
plt.figure(figsize=(10, 6))
plt.hist(data, bins=30, edgecolor='black', alpha=0.7)
plt.title('数据分布直方图', fontsize=14)
plt.xlabel('值')
plt.ylabel('频次')
plt.grid(True, alpha=0.3)
plt.show()
```

### 示例：多子图

```
/code
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 子图1: 折线图
x = np.linspace(0, 10, 100)
axes[0, 0].plot(x, np.sin(x))
axes[0, 0].set_title('Sine Wave')

# 子图2: 散点图
x = np.random.randn(50)
y = np.random.randn(50)
axes[0, 1].scatter(x, y)
axes[0, 1].set_title('Scatter Plot')

# 子图3: 柱状图
categories = ['A', 'B', 'C', 'D']
values = [23, 45, 56, 78]
axes[1, 0].bar(categories, values)
axes[1, 0].set_title('Bar Chart')

# 子图4: 饼图
sizes = [30, 20, 25, 25]
axes[1, 1].pie(sizes, labels=categories, autopct='%1.1f%%')
axes[1, 1].set_title('Pie Chart')

plt.tight_layout()
plt.show()
```

## 📊 数据分析完整流程

### 步骤 1：上传数据文件

上传一个名为 `sales_data.csv` 的文件

### 步骤 2：数据探索

```
/code
import pandas as pd
import matplotlib.pyplot as plt

# 加载数据
df = pd.read_csv('workspace/uploads/web_xxxxx/sales_data.csv')

# 查看数据信息
print("数据形状:", df.shape)
print("\n列名:")
print(df.columns.tolist())
print("\n数据类型:")
print(df.dtypes)
print("\n前5行:")
print(df.head())
```

### 步骤 3：数据清洗和分析

```
/code
# 缺失值分析
print("缺失值统计:")
print(df.isnull().sum())

# 基本统计
print("\n数值列统计:")
print(df.describe())
```

### 步骤 4：生成可视化

```
/code
# 销售趋势图
plt.figure(figsize=(12, 6))
plt.plot(df['date'], df['sales'], marker='o', linewidth=2)
plt.title('销售趋势', fontsize=16)
plt.xlabel('日期')
plt.ylabel('销售额')
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

### 步骤 5：查看 Notebook

点击右上角的 **"Notebook"** 按钮，查看完整的分析记录

## 🔧 高级用法

### 使用 Seaborn

```
/code
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

# 加载数据
df = pd.read_csv('workspace/uploads/web_xxxxx/data.csv')

# 设置样式
sns.set_style("whitegrid")

# 创建热力图
plt.figure(figsize=(10, 8))
sns.heatmap(df.corr(), annot=True, cmap='coolwarm', center=0)
plt.title('相关性热力图')
plt.show()
```

### 使用 Plotly（交互式图表）

```
/code
import plotly.express as px
import pandas as pd

df = pd.read_csv('workspace/uploads/web_xxxxx/data.csv')

# 创建交互式散点图
fig = px.scatter(df, x='column1', y='column2', color='category',
                 title='交互式散点图',
                 hover_data=['column3'])

# 保存为 HTML
fig.write_html('workspace/uploads/web_xxxxx/plot.html')
print("图表已保存为 HTML 文件")
```

## 📁 文件路径说明

上传的文件保存在：`workspace/uploads/<session_id>/<filename>`

生成的 Notebook 保存在：`workspace/notebooks/<session_id>/analysis.ipynb`

生成的图表保存在：`workspace/notebooks/<session_id>/plot_X.png`

## 💡 提示

1. **文件引用**：在 Python 代码中使用完整路径引用上传的文件
2. **图表显示**：确保调用 `plt.show()` 来显示图表
3. **Notebook 查看**：点击右上角 "Notebook" 按钮可查看完整记录
4. **多图表支持**：一次代码执行可以生成多个图表
5. **错误处理**：代码错误会在聊天中显示详细信息
