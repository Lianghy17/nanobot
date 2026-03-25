# 模板模式SQL生成（不执行）功能更新

## 更新内容

根据需求调整，**模板模式现在只生成SQL，不执行SQL查询**。

## 功能说明

### 核心变更
- ✅ 用户选择模板后，系统引导填写参数
- ✅ 用户提供参数后，系统生成SQL语句
- ✅ **不执行SQL**（不调用execute_sql工具，不查询数据库）
- ✅ 直接返回SQL语句给用户查看
- ✅ 用户可以复制SQL在数据库中手动执行

### 响应格式

模板模式下的SQL响应示例：

```markdown
## 🎯 模板模式: 日销售趋势

已为您生成SQL查询语句：

```sql
SELECT 
    DATE(created_at) as date,
    SUM(actual_amount) as total_sales
FROM sales_analysis
WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY DATE(created_at)
ORDER BY date ASC
```

### 参数说明
- **time_range**: `last_30_days`
- **metric**: `actual_amount`

💡 **提示**: 此SQL已根据您选择的模板和参数生成，您可以直接在数据库中执行此查询。
```

## 技术实现

### 1. _process_with_pattern() 方法修改

**文件**: `chatbi/core/agent_wrapper.py`

**主要变更**:
- 移除mock数据生成
- 移除execute_sql工具调用
- `tools_used`列表为空
- 直接返回SQL语句

**关键代码**:
```python
# 构建SQL
sql, error = self.sql_builder.build(intent_result.matched_pattern, params, sql_context)

# 格式化SQL响应（不执行SQL，只返回SQL语句）
response_lines = [
    f"## 🎯 模板模式: {intent_result.pattern_config.name}",
    f"",
    f"已为您生成SQL查询语句：",
    f"",
    f"```sql",
    f"{sql}",
    f"```",
    # ... 参数说明
]

return {
    "content": "\n".join(response_lines),
    "tools_used": [],  # 不执行SQL，工具列表为空
    "metadata": {
        "pattern_mode": True,
        "template_mode": True,
        "pattern_id": intent_result.matched_pattern,
        "pattern_name": intent_result.pattern_config.name,
        "sql": sql,
        "params": params,
        "mode": "template"
    }
}
```

### 2. 默认参数处理

**功能**: 当参数为空时，使用pattern配置中的默认值

**实现**:
```python
# 如果参数为空，尝试从pattern_config获取默认值
if not params and intent_result.pattern_config:
    logger.info(f"[Pattern模式] 参数为空，使用默认值")
    params_schema = intent_result.pattern_config.params_schema or {}
    for param_name, param_config in params_schema.items():
        if 'default' in param_config:
            params[param_name] = param_config['default']
```

### 3. 续接模式支持

**功能**: 用户填写参数后，系统能识别上下文并继续处理

**实现**:
- 检测用户消息中是否包含`continuing_pattern: True`
- 从上下文中提取pattern_id
- 调用IntentAnalyzer提取参数
- 生成SQL（不执行）

## 工作流程

### 完整流程

```
1. 用户点击右侧模板
   ↓
2. 前端发送消息（metadata包含template_data）
   ↓
3. 后端检测到首次选择模板
   ↓
4. 调用_guide_template_params()生成参数引导
   ↓
5. 前端显示参数引导，更新模式指示器为"模板模式"
   ↓
6. 用户填写参数并发送
   ↓
7. 后端检测到continuing_pattern=True
   ↓
8. IntentAnalyzer提取参数（从上下文获取pattern_id）
   ↓
9. _process_with_pattern()生成SQL（使用默认值或提取的参数）
   ↓
10. 返回SQL语句给用户（不执行）
   ↓
11. 用户查看SQL，可手动执行
```

## 与React模式的区别

| 特性 | 模板模式 | React模式 |
|------|---------|----------|
| SQL执行 | ❌ 不执行 | ✅ 自动执行 |
| 工具调用 | ❌ tools_used=[] | ✅ 调用execute_sql等工具 |
| 数据返回 | ❌ 只返回SQL | ✅ 返回查询结果 |
| 参数来源 | 用户填写或默认值 | LLM自动推断 |
| 适用场景 | 明确的查询模板 | 灵活的复杂分析 |

## 优势

1. **安全性**：不自动执行SQL，避免误操作
2. **透明性**：用户可以查看并理解生成的SQL
3. **灵活性**：用户可以根据需要修改SQL再执行
4. **教学性**：通过查看SQL学习查询逻辑
5. **可控性**：用户决定何时执行SQL

## 注意事项

1. **模式标识**：
   - 首次选择模板：`metadata.template_mode=True` + `template_data`
   - 续接模式：`metadata.continuing_pattern=True` + `pattern_id`

2. **参数提取**：
   - 优先使用IntentAnalyzer提取参数
   - 提取失败时使用pattern配置的默认值
   - 参数仍不完整时引导用户补充

3. **降级处理**：
   - SQL构建失败时降级到React模式
   - Pattern处理异常时降级到React模式

## 相关文件

- `chatbi/core/agent_wrapper.py` - Agent核心逻辑
- `chatbi/core/intent_analyzer.py` - 意图分析器
- `chatbi/core/pattern_loader.py` - Pattern配置加载
- `chatbi/core/sql_builder.py` - SQL构建器
- `TEMPLATE_MODE_IMPLEMENTATION.md` - 完整实现文档

## 测试建议

1. 测试首次选择模板，验证参数引导
2. 测试用户填写参数后，验证SQL生成（不执行）
3. 测试参数为空时，验证默认值使用
4. 测试SQL构建失败时，验证降级到React模式
5. 测试续接模式，验证上下文识别

---

**更新日期**: 2026-03-23
**版本**: v2.0 - SQL生成不执行版本
