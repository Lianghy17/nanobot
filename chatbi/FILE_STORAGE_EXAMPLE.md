# 文件存储功能使用示例

## 示例 1：生成简单的图表

### 用户输入
```
帮我画一个简单的折线图，展示最近5天的销售数据
```

### Agent 执行的 Python 代码
```python
import matplotlib.pyplot as plt

# 准备数据
days = ['周一', '周二', '周三', '周四', '周五']
sales = [120, 150, 180, 140, 200]

# 创建图表
plt.figure(figsize=(10, 6))
plt.plot(days, sales, marker='o', linewidth=2, markersize=8)
plt.title('最近5天销售数据')
plt.xlabel('日期')
plt.ylabel('销售额（万元）')
plt.grid(True, alpha=0.3)
plt.savefig('sales_chart.png', dpi=100, bbox_inches='tight')

# 返回 Markdown 格式的图片引用
print('![销售数据折线图](sales_chart.png)')
print(f'\n图表已生成并保存为 sales_chart.png')
print(f'文件大小: {os.path.getsize("sales_chart.png") / 1024:.2f} KB')
```

### 生成的文件信息
```json
{
  "filename": "sales_chart.png",
  "unique_filename": "web_web_default_user_20260319_143022_sales_chart.png",
  "type": "image/png",
  "size": 52428,
  "url": "/files/web_web_default_user_20260319_143022_sales_chart.png"
}
```

### 前端显示
```
销售数据折线图

[图表图片]
```

---

## 示例 2：生成多个图表

### 用户输入
```
帮我分析销售数据，画出销售额和利润的趋势图
```

### Agent 执行的 Python 代码
```python
import matplotlib.pyplot as plt
import numpy as np

# 准备数据
months = ['1月', '2月', '3月', '4月', '5月', '6月']
sales = [100, 120, 110, 150, 180, 200]
profit = [20, 30, 25, 40, 50, 60]

# 创建第一个图表：销售额趋势
plt.figure(figsize=(10, 6))
plt.plot(months, sales, marker='o', color='blue', label='销售额')
plt.title('销售额趋势')
plt.xlabel('月份')
plt.ylabel('销售额（万元）')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('sales_trend.png', dpi=100, bbox_inches='tight')

# 创建第二个图表：利润趋势
plt.figure(figsize=(10, 6))
plt.plot(months, profit, marker='s', color='green', label='利润')
plt.title('利润趋势')
plt.xlabel('月份')
plt.ylabel('利润（万元）')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('profit_trend.png', dpi=100, bbox_inches='tight')

# 返回两个图表
print('## 销售数据分析')
print()
print('### 销售额趋势')
print('![销售额趋势](sales_trend.png)')
print()
print('### 利润趋势')
print('![利润趋势](profit_trend.png)')
```

### 生成的文件信息
```json
[
  {
    "filename": "sales_trend.png",
    "unique_filename": "web_web_default_user_20260319_143025_sales_trend.png",
    "type": "image/png",
    "size": 48256,
    "url": "/files/web_web_default_user_20260319_143025_sales_trend.png"
  },
  {
    "filename": "profit_trend.png",
    "unique_filename": "web_web_default_user_20260319_143030_profit_trend.png",
    "type": "image/png",
    "size": 46800,
    "url": "/files/web_web_default_user_20260319_143030_profit_trend.png"
  }
]
```

### 前端显示
```
## 销售数据分析

### 销售额趋势

[图表图片1]

### 利润趋势

[图表图片2]

生成的文件 (2)
[文件1] sales_trend.png (47.1 KB)
[文件2] profit_trend.png (45.7 KB)
```

---

## 示例 3：生成并导出 CSV 文件

### 用户输入
```
帮我生成一份销售数据的CSV报表
```

### Agent 执行的 Python 代码
```python
import pandas as pd

# 准备数据
data = {
    '月份': ['1月', '2月', '3月', '4月', '5月'],
    '销售额（万元）': [100, 120, 110, 150, 180],
    '利润（万元）': [20, 30, 25, 40, 50],
    '增长率（%）': [5.0, 20.0, -8.3, 36.4, 20.0]
}

# 创建 DataFrame
df = pd.DataFrame(data)

# 保存为 CSV 文件
csv_filename = 'sales_report.csv'
df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

# 计算文件大小
file_size = os.path.getsize(csv_filename)

print(f'✅ 销售数据报表已生成')
print(f'📄 文件名: {csv_filename}')
print(f'📊 文件大小: {file_size / 1024:.2f} KB')
print(f'📈 数据行数: {len(df)}')
print(f'\n**报表预览:**')
print(df.to_markdown(index=False))
```

### 生成的文件信息
```json
{
  "filename": "sales_report.csv",
  "unique_filename": "web_web_default_user_20260319_143035_sales_report.csv",
  "type": "text/csv",
  "size": 512,
  "url": "/files/web_web_default_user_20260319_143035_sales_report.csv"
}
```

### 前端显示
```
✅ 销售数据报表已生成
📄 文件名: sales_report.csv
📊 文件大小: 0.50 KB
📈 数据行数: 5

**报表预览:**
| 月份  | 销售额（万元） | 利润（万元） | 增长率（%） |
|------|----------------|--------------|-------------|
| 1月  | 100            | 20           | 5.0         |
| 2月  | 120            | 30           | 20.0        |
| 3月  | 110            | 25           | -8.3        |
| 4月  | 150            | 40           | 36.4        |
| 5月  | 180            | 50           | 20.0        |

生成的文件 (1)
[文件] sales_report.csv (0.50 KB)
```

---

## 示例 4：生成复杂的多图分析

### 用户输入
```
帮我分析用户行为数据，画出多个图表
```

### Agent 执行的 Python 代码
```python
import matplotlib.pyplot as plt
import numpy as np

# 准备数据
days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
new_users = [120, 150, 180, 140, 200, 250, 230]
active_users = [800, 950, 1100, 980, 1200, 1500, 1400]
avg_session_time = [15, 18, 20, 17, 22, 25, 23]

# 创建第一个图表：新增用户趋势
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 图1: 新增用户
axes[0, 0].plot(days, new_users, marker='o', color='blue')
axes[0, 0].set_title('新增用户趋势')
axes[0, 0].set_ylabel('用户数')
axes[0, 0].grid(True, alpha=0.3)

# 图2: 活跃用户
axes[0, 1].plot(days, active_users, marker='s', color='green')
axes[0, 1].set_title('活跃用户趋势')
axes[0, 1].set_ylabel('用户数')
axes[0, 1].grid(True, alpha=0.3)

# 图3: 平均会话时长
axes[1, 0].bar(days, avg_session_time, color='orange', alpha=0.7)
axes[1, 0].set_title('平均会话时长')
axes[1, 0].set_ylabel('分钟')
axes[1, 0].grid(True, alpha=0.3, axis='y')

# 图4: 用户留存率
retention = [100, 85, 75, 68, 62, 58, 55]
axes[1, 1].bar(range(len(retention)), retention, color='purple', alpha=0.7)
axes[1, 1].set_title('7日留存率')
axes[1, 1].set_ylabel('留存率（%）')
axes[1, 1].set_xlabel('天数')
axes[1, 1].set_xticks(range(len(retention)))
axes[1, 1].set_xticklabels([f'D{i}' for i in range(len(retention))])
axes[1, 1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('user_behavior_analysis.png', dpi=100, bbox_inches='tight')

print('## 用户行为数据分析')
print()
print('![用户行为分析](user_behavior_analysis.png)')
print()
print('**数据摘要:**')
print(f'- 本周新增用户: {sum(new_users)} 人')
print(f'- 周均活跃用户: {int(np.mean(active_users))} 人')
print(f'- 平均会话时长: {np.mean(avg_session_time):.1f} 分钟')
print(f'- 7日留存率: {retention[-1]}%')
```

### 生成的文件信息
```json
{
  "filename": "user_behavior_analysis.png",
  "unique_filename": "web_web_default_user_20260319_143040_user_behavior_analysis.png",
  "type": "image/png",
  "size": 98304,
  "url": "/files/web_web_default_user_20260319_143040_user_behavior_analysis.png"
}
```

### 前端显示
```
## 用户行为数据分析

[四图组合分析图]

**数据摘要:**
- 本周新增用户: 1270 人
- 周均活跃用户: 1132 人
- 平均会话时长: 20.0 分钟
- 7日留存率: 55%

生成的文件 (1)
[文件] user_behavior_analysis.png (96.0 KB)
```

---

## 最佳实践

### 1. 文件命名
```python
# 好的命名：描述性强、无特殊字符
plt.savefig('sales_trend_2024q1.png')  # ✅ 推荐
plt.savefig('chart1.png')  # ⚠️ 可接受
plt.savefig('图表.png')  # ❌ 避免使用中文
plt.savefig('sales/trend.png')  # ❌ 避免使用子目录
```

### 2. 文件大小控制
```python
# 控制图片大小
plt.savefig('chart.png', dpi=100, bbox_inches='tight')  # ✅ 推荐
plt.savefig('chart.png', dpi=300)  # ⚠️ 文件较大

# 对于简单图表，使用较低的 DPI
plt.savefig('simple_chart.png', dpi=80)  # ✅ 简单图表
```

### 3. 图片格式选择
```python
# PNG：高质量，适合图表
plt.savefig('chart.png', dpi=100)  # ✅ 推荐

# JPEG：照片，不适合图表（有压缩损失）
plt.savefig('chart.jpg')  # ❌ 不推荐

# SVG：矢量图，适合需要缩放的场景
plt.savefig('chart.svg')  # ✅ 需要矢量图时
```

### 4. 多文件生成
```python
# 好的做法：使用循环生成多个文件
for i, data in enumerate(datasets):
    plt.figure(figsize=(10, 6))
    plt.plot(data)
    plt.savefig(f'chart_{i+1}.png', dpi=100)
    plt.close()
```

### 5. Markdown 引用
```python
# 在 Python 代码中直接输出 Markdown 引用
print('![销售趋势](sales_trend.png)')  # ✅ 推荐
print(f'![销售趋势]({filename})')  # ✅ 使用变量
print('<img src="sales_trend.png">')  # ⚠️ 可用，但不推荐
```

---

## 故障排查

### 问题 1：图片没有显示

**可能原因：**
- 文件路径错误
- 文件复制失败
- URL 格式错误

**解决方法：**
1. 检查控制台日志
2. 查看 `workspace/files` 目录
3. 确认文件名是否正确

### 问题 2：文件太大无法复制

**可能原因：**
- 文件超过 10MB 限制

**解决方法：**
```python
# 减小图片 DPI
plt.savefig('chart.png', dpi=80)  # 降低 DPI

# 或者压缩图片大小
plt.figure(figsize=(8, 6))  # 减小画布尺寸
```

### 问题 3：文件名包含特殊字符

**可能原因：**
- 使用了中文或特殊字符

**解决方法：**
```python
# 使用英文文件名
plt.savefig('sales_chart.png')  # ✅
# 而不是
plt.savefig('销售图表.png')  # ❌
```
