# ChatBI 快速启动指南

## 系统架构

```
Workspace目录（仅用于sessions和memory）
├── sessions/           # 对话数据
└── memory/             # 长期记忆

沙箱环境（每个conversation一个）
└── sandbox_{conv_id}/
    └── workspace/      # 文件和Python执行环境
        ├── uploaded.csv
        ├── result.csv
        └── chart.png
```

## 启动服务

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python3 chatbi/main.py
```

服务将在 `http://localhost:8080` 启动。

## 核心功能使用

### 1. 创建对话

```bash
curl -X POST "http://localhost:8080/api/conversations/" \
  -H "Content-Type: application/json" \
  -d '{"scene_code": "bi_analysis"}'
```

**响应**：
```json
{
  "conversation_id": "conv_1773710903_e8e9ce91",
  "scene_code": "bi_analysis",
  "scene_name": "数据分析场景",
  "created_at": "2026-03-17T12:00:00"
}
```

### 2. 上传文件到沙箱

```bash
# 上传CSV文件
curl -X POST "http://localhost:8080/api/conversations/{conversation_id}/upload" \
  -F "file=@data.csv"
```

**响应**：
```json
{
  "success": true,
  "filename": "data.csv",
  "file_path": "data.csv",
  "size": 1024,
  "message": "文件已上传到沙箱，可以在Python代码中直接使用"
}
```

### 3. 发送消息（会自动创建沙箱）

```bash
curl -X POST "http://localhost:8080/api/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_1773710903_e8e9ce91",
    "content": "分析上传的CSV文件，生成图表"
  }'
```

**说明**：
- 如果涉及Python执行或文件操作，会自动创建沙箱
- 沙箱会自动上传的文件和生成的结果

### 4. 下载沙箱中的文件

```bash
# 下载生成的图表
curl "http://localhost:8080/api/files/download/web_default_user/{conversation_id}/chart.png" \
  -o chart.png

# 列出沙箱中的所有文件
curl "http://localhost:8080/api/files/list/web_default_user/{conversation_id}"
```

**响应**：
```json
{
  "success": true,
  "files": [
    {
      "filename": "chart.png",
      "size": 45678,
      "type": "png",
      "download_url": "/api/files/download/web_default_user/conv_123/chart.png"
    },
    {
      "filename": "result.csv",
      "size": 1234,
      "type": "csv",
      "download_url": "/api/files/download/web_default_user/conv_123/result.csv"
    }
  ],
  "count": 2
}
```

### 5. 查看沙箱状态

```bash
# 查看沙箱统计
curl "http://localhost:8080/api/sandboxes/stats"

# 列出所有活跃沙箱
curl "http://localhost:8080/api/sandboxes/list"
```

## Python代码示例

### 基础数据分析

```python
import pandas as pd
import matplotlib.pyplot as plt

# 1. 读取上传的文件
df = pd.read_csv('data.csv')

# 2. 查看数据
print(df.head())
print(f"数据形状: {df.shape}")

# 3. 基础统计
stats = df.describe()
print(stats)

# 4. 保存统计结果
stats.to_csv('statistics.csv')

# 5. 生成图表
plt.figure(figsize=(10, 6))
plt.plot(df['date'], df['value'])
plt.title('数据趋势图')
plt.xlabel('日期')
plt.ylabel('值')
plt.savefig('chart.png')
plt.close()

print("分析完成！生成的文件：")
print("- statistics.csv")
print("- chart.png")
```

### 使用读取文件工具

如果文件较大，可以使用 `read_file` 工具预览：

```python
# 先读取文件前几行
import pandas as pd
import io

# 假设LLM已经调用了 read_file 工具
# 这里直接读取完整的文件
df = pd.read_csv('data.csv')

# 继续分析...
```

### 使用写入文件工具

保存分析结果：

```python
# 保存分析报告
with open('analysis_report.txt', 'w') as f:
    f.write("数据分析报告\n")
    f.write("=" * 40 + "\n")
    f.write(f"数据行数: {len(df)}\n")
    f.write(f"数据列数: {len(df.columns)}\n")
    f.write("\n基本统计:\n")
    f.write(str(df.describe()))

print("报告已保存到 analysis_report.txt")
```

## Memory功能

Memory会自动记录对话历史和重要信息。

### 配置Memory

在 `config/chatbi.json` 中：

```json
{
  "memory": {
    "enabled": true,
    "level": "both"
  }
}
```

### Memory级别

- `global`: 所有用户共享的全局记忆
- `user`: 用户专属记忆
- `both`: 同时使用全局和用户记忆（推荐）

### Memory内容

Memory会自动记录：
- 用户问题
- Agent回答
- 使用的工具
- 时间戳
- 场景信息

## 常见场景

### 场景1：销售数据分析

```bash
# 1. 上传销售数据
curl -X POST "http://localhost:8080/api/conversations/{conv_id}/upload" \
  -F "file=@sales_data.csv"

# 2. 询问问题
curl -X POST "http://localhost:8080/api/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "{conv_id}",
    "content": "分析销售数据，找出最佳销售产品和月份"
  }'

# 3. 下载生成的图表和报告
curl "http://localhost:8080/api/files/download/web_default_user/{conv_id}/sales_analysis.png" \
  -o sales_analysis.png
```

### 场景2：用户行为分析

```bash
# 1. 上传用户行为日志
curl -X POST "http://localhost:8080/api/conversations/{conv_id}/upload" \
  -F "file=@user_events.csv"

# 2. 分析用户行为
curl -X POST "http://localhost:8080/api/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "{conv_id}",
    "content": "分析用户行为数据，识别关键模式和趋势"
  }'

# 3. 下载分析结果
curl "http://localhost:8080/api/files/list/web_default_user/{conv_id}"
```

### 场景3：知识库搜索

```bash
# 询问知识库
curl -X POST "http://localhost:8080/api/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "{conv_id}",
    "content": "搜索关于销售分析的知识库内容"
  }'
```

## 注意事项

### 1. 沙箱超时

沙箱会在20分钟未使用后自动清理。如果需要长期保存文件：

```bash
# 在超时前下载文件
curl "http://localhost:8080/api/files/download/web_default_user/{conv_id}/result.csv" \
  -o result.csv
```

### 2. 文件大小限制

- 建议上传文件 < 50MB
- 生成的单个文件 < 10MB
- 超大文件可能导致执行超时

### 3. Python执行限制

- 执行时间限制：60秒
- 内存限制：512MB
- 避免无限循环和内存泄漏

### 4. 文件路径

- 所有文件路径都是相对于沙箱workspace目录
- 使用相对路径：`data.csv`, `results/chart.png`
- 不要使用绝对路径

## API文档

完整的API文档：http://localhost:8080/docs

主要API端点：

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/conversations/` | 创建对话 |
| GET | `/api/conversations/` | 列出对话 |
| GET | `/api/conversations/{id}` | 获取对话详情 |
| POST | `/api/conversations/{id}/upload` | 上传文件到沙箱 |
| POST | `/api/messages/` | 发送消息 |
| GET | `/api/messages/{id}` | 获取消息 |
| GET | `/api/files/list/{user}/{conv}` | 列出沙箱文件 |
| GET | `/api/files/download/{user}/{conv}/{file}` | 下载文件 |
| GET | `/api/sandboxes/stats` | 沙箱统计 |
| GET | `/api/sandboxes/list` | 活跃沙箱列表 |
| GET | `/health` | 健康检查 |

## 测试

运行测试验证功能：

```bash
# 测试Memory功能
python3 chatbi/test_memory.py

# 测试沙箱文件操作
python3 chatbi/test_sandbox_files.py
```

## 故障排查

### 问题1：文件上传失败

**可能原因**：沙箱不存在或已超时

**解决方法**：
```bash
# 先发送消息激活沙箱
curl -X POST "http://localhost:8080/api/messages/" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "{conv_id}", "content": "hello"}'
```

### 问题2：Python执行超时

**可能原因**：代码执行时间过长

**解决方法**：
- 优化Python代码
- 减少数据处理量
- 分批处理大数据

### 问题3：下载文件404

**可能原因**：沙箱已清理或文件名错误

**解决方法**：
```bash
# 先列出文件确认
curl "http://localhost:8080/api/files/list/web_default_user/{conv_id}"
```

## 性能优化建议

1. **文件上传**：压缩大文件后再上传
2. **Python执行**：使用向量化操作代替循环
3. **图表生成**：降低图表分辨率
4. **批量操作**：一次上传多个相关文件

## 下一步

- 查看 `SANDBOX_REFACTOR.md` 了解架构细节
- 查看 `MEMORY.md` 了解Memory功能
- 查看 `REFACTOR_SUMMARY.md` 了解完整改动
- 访问 `/docs` 查看完整API文档
