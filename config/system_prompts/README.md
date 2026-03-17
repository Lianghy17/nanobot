# System Prompts 管理说明

## 目录结构

```
config/system_prompts/
├── v1.md      # 基础版本 - 清晰简洁，适合一般场景
├── v2.md      # 结构化版本 - 使用表格和分段，强调规范
├── v3.md      # 专家版本 - 详细指南，包含检查清单和最佳实践
└── README.md  # 本文件
```

## 如何切换版本

### 方法1：修改配置文件（推荐）

编辑 `config/chatbi.json`：

```json
{
  "agent": {
    "max_iterations": 10,
    "max_history_messages": 20,
    "system_prompt_file": "system_prompts/v1.md"  // 修改这里切换版本
  }
}
```

可选项：
- `"system_prompts/v1.md"` - 基础版本
- `"system_prompts/v2.md"` - 结构化版本
- `"system_prompts/v3.md"` - 专家版本

### 方法2：使用环境变量

```bash
# 启动服务时设置环境变量
export SYSTEM_PROMPT_FILE=system_prompts/v2.md
python chatbi/main.py
```

（需要在代码中添加环境变量支持）

## 版本对比

| 版本 | 特点 | 适用场景 | 长度 |
|------|------|----------|------|
| v1 | 清晰简洁，直接明了 | 一般数据分析任务 | 短 |
| v2 | 结构化展示，强调规范 | 需要严格遵循规范的场景 | 中 |
| v3 | 详细指南，包含检查清单 | 复杂分析任务，需要高质量输出 | 长 |

## 创建自定义版本

1. 在 `config/system_prompts/` 目录下创建新文件，如 `v4.md`
2. 复制现有版本作为模板
3. 根据需求修改内容
4. 在 `config/chatbi.json` 中指定使用新版本

## 变量说明

所有系统提示词支持以下变量：

- `{scene_name}` - 场景名称
- `{scene_code}` - 场景代码
- `{tool_names}` - 可用工具列表

在代码中使用时，这些变量会被自动替换：

```python
prompt = chatbi_config.agent_system_prompt_template
formatted_prompt = prompt.format(
    scene_name="销售分析",
    scene_code="sales_analysis",
    tool_names="execute_python, execute_sql, rag_search"
)
```

## 测试建议

### A/B 测试

1. 使用 v1 版本运行一系列测试用例
2. 记录输出质量和用户满意度
3. 切换到 v2 版本，重复相同测试
4. 对比结果，选择最优版本

### 监控指标

- 工具选择准确性
- 代码执行成功率
- 图表生成质量
- 输出格式规范性
- 用户反馈评分

## 注意事项

1. **变量占位符**：确保所有模板都包含 `{scene_name}`, `{scene_code}`, `{tool_names}` 占位符
2. **Markdown格式**：所有版本都应使用 Markdown 格式
3. **图表保存**：所有版本都必须强调保存图表文件（不要使用 plt.show()）
4. **兼容性**：注意 Matplotlib 已弃用的参数（如 use_line_collection）

## 快速参考

### 当前使用的版本

查看 `config/chatbi.json` 中的 `system_prompt_file` 配置。

### 切换版本步骤

1. 编辑 `config/chatbi.json`
2. 修改 `"system_prompt_file"` 的值
3. 重启服务（或热重载）

### 回退到内置提示词

如果提示词文件加载失败，系统会自动使用内置的默认提示词。
