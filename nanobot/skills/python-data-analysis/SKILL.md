---
description: Python data analysis and visualization skill
always: true
metadata: '{"nanobot": {"always": true}}'
---

# Python Data Analysis Skill

This skill guides you through performing data analysis using Python with pandas, matplotlib, and other libraries.

## ⚠️ CRITICAL: Chart Rendering

**Charts MUST be saved as PNG files and served via URLs. The system automatically captures `plt.show()` calls.**

### How it works:
1. You write Python code with matplotlib
2. Call `plt.show()` to trigger chart capture
3. System saves chart to `/plots/<session_id>/plot_XXX.png`
4. Tool returns Markdown: `![Chart](url)`
5. **You MUST include this Markdown in your response for the user to see it!**

### ⚠️ IMPORTANT:
The python_exec tool returns chart URLs in Markdown format like `![Chart 1](/plots/xxx/plot_000.png)`.
**You MUST include these image URLs in your final response.** Without them, the user cannot see the chart!

### ✅ Correct Example:
```python
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.plot([1, 2, 3], [4, 5, 6])
plt.title('My Chart')
plt.xlabel('X')
plt.ylabel('Y')
plt.tight_layout()
plt.show()  # REQUIRED - triggers chart capture!
```

### ❌ Wrong Example:
```python
# Without plt.show() - chart will NOT be displayed!
plt.plot([1, 2, 3], [4, 5, 6])
# Missing plt.show() - nothing happens
```

## Workflow

### 1. Load and Explore Data

```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data from uploaded file
# (File will be in workspace/uploads/<session_id>/)
df = pd.read_csv('path/to/file.csv')

# Basic exploration
print(f"Shape: {df.shape}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nData types:\n{df.dtypes}")
print(f"\nMissing values:\n{df.isnull().sum()}")
print(f"\nBasic stats:\n{df.describe()}")
```

### 2. Data Cleaning

```python
# Handle missing values
df_clean = df.dropna()  # or df.fillna(method='ffill')

# Remove duplicates
df_clean = df_clean.drop_duplicates()

# Type conversions
df_clean['date'] = pd.to_datetime(df_clean['date'])
df_clean['category'] = df_clean['category'].astype('category')
```

### 3. Analysis and Visualization

**Remember: ALWAYS call `plt.show()` after creating charts!**

```python
import matplotlib.pyplot as plt

# Example: Line chart
plt.figure(figsize=(10, 6))
plt.plot(df['date'], df['value'])
plt.title('Trend Over Time')
plt.xlabel('Date')
plt.ylabel('Value')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()  # REQUIRED!

# Example: Bar chart
plt.figure(figsize=(10, 6))
df['category'].value_counts().plot(kind='bar')
plt.title('Category Distribution')
plt.xlabel('Category')
plt.ylabel('Count')
plt.tight_layout()
plt.show()  # REQUIRED!

# Example: Histogram
plt.figure(figsize=(10, 6))
plt.hist(df['value'], bins=20, edgecolor='black')
plt.title('Value Distribution')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.tight_layout()
plt.show()  # REQUIRED!
```

### 4. Advanced Analysis

```python
# Correlation analysis
corr_matrix = df.select_dtypes(include=[np.number]).corr()
print(corr_matrix)

# Plot correlation heatmap
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 8))
plt.imshow(corr_matrix, cmap='coolwarm', aspect='auto')
plt.colorbar()
plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=45)
plt.yticks(range(len(corr_matrix.columns)), corr_matrix.columns)
plt.title('Correlation Matrix')
plt.tight_layout()
plt.show()  # REQUIRED!

# Groupby analysis
grouped = df.groupby('category').agg({
    'value': ['mean', 'sum', 'count']
})
print(grouped)
```

## Important Rules

1. **✅ ALWAYS call `plt.show()`** - This triggers the plot capture mechanism
2. **Set figure size** - Use `plt.figure(figsize=(width, height))` for better readability
3. **Use `plt.tight_layout()`** - Prevents label cutoff
4. **File paths** - Use absolute paths or paths relative to the workspace
5. **One chart per `plt.show()`** - Each call captures the current figure

## Common Patterns

### Time Series Analysis
```python
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# Resample to monthly
df_monthly = df.resample('M').sum()

plt.figure(figsize=(12, 6))
plt.plot(df_monthly.index, df_monthly['value'])
plt.title('Monthly Trend')
plt.xlabel('Month')
plt.ylabel('Value')
plt.tight_layout()
plt.show()  # REQUIRED!
```

### Comparison Charts (Multiple Subplots)
```python
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1
axes[0, 0].bar(df['cat'], df['val1'])
axes[0, 0].set_title('Chart 1')

# Plot 2
axes[0, 1].plot(df['x'], df['y'])
axes[0, 1].set_title('Chart 2')

plt.tight_layout()
plt.show()  # REQUIRED! Captures all subplots
```

### Scatter Plot with Color
```python
plt.figure(figsize=(10, 8))
plt.scatter(df['x'], df['y'], c=df['category'].astype('category').cat.codes, cmap='viridis', alpha=0.6)
plt.colorbar(label='Category')
plt.title('Scatter Plot')
plt.xlabel('X')
plt.ylabel('Y')
plt.tight_layout()
plt.show()  # REQUIRED!
```

## Available Libraries

Standard libraries available:
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `matplotlib` - Plotting (use plt.show()!)
- `seaborn` - Statistical visualization
- `scipy` - Scientific computing
- `sklearn` - Machine learning

## Output

- **Charts**: Automatically saved as PNG files at `/plots/<session_id>/plot_XXX.png`
- **URLs**: Charts are displayed via URL in the frontend
- **Notebooks**: Full analysis saved to `workspace/notebooks/<session_id>/analysis.ipynb`
- **Text output**: Printed to the conversation

## Complete Example

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Generate data
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=30)
values = np.cumsum(np.random.randn(30) * 10) + 100
df = pd.DataFrame({'date': dates, 'value': values})

# 2. Print analysis
print("Summary Statistics:")
print(df.describe())

# 3. Create chart
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(df['date'], df['value'], marker='o')
plt.title('Time Series')
plt.xlabel('Date')
plt.xticks(rotation=45)

plt.subplot(1, 2, 2)
plt.hist(df['value'], bins=10, edgecolor='black')
plt.title('Distribution')
plt.xlabel('Value')

plt.tight_layout()
plt.show()  # REQUIRED! - This captures both charts

print("✅ Analysis complete!")
```
