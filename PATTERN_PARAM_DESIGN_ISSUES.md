# Pattern模板参数设计问题分析

## 问题背景

用户在使用"销售趋势-日销售趋势"模板时，输入了混合的参数：
```
'时间范围是最近30天' '指标是销售额' '时间粒度是日' '查看销售额Top 10的产品'
```

导致系统降级到React模式，无法使用Pattern模式生成SQL。

## 根本原因

### 1. 模板参数设计不符合业务逻辑

不同的分析类型应该有不同的时间参数需求：

| 分析类型 | Pattern | time_mode | 需要的时间参数 | 说明 |
|---------|---------|------------|---------------|------|
| 时间序列分析 | trend_analysis | SERIES | time_range + time_grain | 需要时间范围和粒度来查看趋势 |
| 同环比分析 | yoy_mom | OFFSET | time_range + time_grain | 需要时间范围和粒度来对比 |
| 累积分析 | cumulative | SERIES | time_range + time_grain | 需要时间范围和粒度来累积 |
| TopN排名 | topn | SINGLE_POINT | time_point | 只需要时间点，不需要粒度 |
| 维度拆解 | breakdown | SINGLE_POINT | time_point | 只需要时间点，不需要粒度 |
| 维度对比 | comparison | SINGLE_POINT | time_point | 只需要时间点，不需要粒度 |
| 聚合查询 | agg_query | SINGLE_POINT | time_point | 只需要时间点，不需要粒度 |

### 2. 用户输入包含多个分析需求

用户的一次输入包含了：
- **趋势分析需求**：时间范围（最近30天）+ 指标（销售额）+ 时间粒度（日）
- **排名分析需求**：查看销售额Top 10的产品

这两个需求对应不同的Pattern：
- 趋势分析 → `trend_analysis` pattern
- 排名分析 → `topn` pattern

### 3. 意图分析器无法确定唯一Pattern

由于输入冲突：
- 前半部分匹配 `trend_analysis`
- 后半部分匹配 `topn`
- LLM无法确定用户真正想要哪个Pattern
- 置信度低于阈值 → 触发降级

## 解决方案

### 方案1：分步查询（推荐）

**查询1 - 趋势分析**：
```
时间范围是最近30天，指标是销售额，时间粒度是日
```

**查询2 - 排名分析**：
```
查看销售额Top 10的产品
```

### 方案2：明确表达单一意图

只选择一种分析类型：

**趋势分析**：
```
我想看最近30天销售额的日趋势
```

**排名分析**：
```
我想看本月销售额Top 10的产品
```

### 方案3：改进模板引导

优化参数引导提示，根据Pattern类型显示不同的提示：

**时间序列分析模板**：
- 说明：需要指定时间范围和时间粒度来查看趋势
- 示例：'时间范围是最近30天，指标是销售额，时间粒度是日'

**维度分析模板**：
- 说明：需要指定时间点（不是时间范围）来查看特定时刻的数据
- 示例：'本月销售额Top 10的产品'

## 改进措施

### 1. 优化参数引导代码

在 `chatbi/core/agent_wrapper.py` 中：

```python
# 根据Pattern类型显示不同的提示
pattern_config = self.pattern_loader.get_pattern(pattern_id)
pattern_category = pattern_config.category if pattern_config else "unknown"

if pattern_category == "time_series":
    response_lines.append(f"📊 **时间序列分析模板**")
    response_lines.append(f"此模板需要指定时间范围和时间粒度来查看趋势。")
    response_lines.append(f"")
    response_lines.append(f"💡 **示例输入**:")
    response_lines.append(f"- '时间范围是最近30天，指标是销售额，时间粒度是日'")
    response_lines.append(f"- '指标是订单量，时间范围是今年，时间粒度是月'")
elif pattern_category in ["dimensional", "basic"]:
    response_lines.append(f"📈 **维度分析模板**")
    response_lines.append(f"此模板需要指定时间点（不是时间范围）来查看特定时刻的数据。")
    response_lines.append(f"")
    response_lines.append(f"💡 **示例输入**:")
    response_lines.append(f"- '本月销售额Top 10的产品'")
    response_lines.append(f"- '按产品类别查看销售额分布'")
```

### 2. 增加重要提示

```python
response_lines.append(f"⚠️ **重要提示**:")
response_lines.append(f"- 趋势分析需要：时间范围 + 时间粒度 + 指标")
response_lines.append(f"- 维度分析需要：时间点（如本月/昨天）+ 维度 + 指标")
response_lines.append(f"- 请勿在一次查询中混合不同类型的分析需求")
```

### 3. 模板配置最佳实践

对于不同的分析类型，模板配置应该：

**时间序列分析模板**：
```json
{
  "params_schema": {
    "time_range": {"label": "时间范围", "required": true},
    "time_grain": {"label": "时间粒度", "required": true},
    "metric": {"label": "指标", "required": true}
  }
}
```

**维度分析模板**：
```json
{
  "params_schema": {
    "time_point": {"label": "时间点", "required": true},
    "dimension": {"label": "维度", "required": true},
    "metric": {"label": "指标", "required": true}
  }
}
```

## 用户使用建议

### 使用时间序列分析（趋势/同环比/累积）

1. 必须提供：时间范围
2. 必须提供：时间粒度（日/周/月）
3. 必须提供：指标

**示例**：
- "最近30天销售额的日趋势"
- "今年订单量的月趋势"
- "上季度的销售额环比分析"

### 使用维度分析（TopN/对比/拆解）

1. 必须提供：时间点（如本月/昨天/2024-01）
2. 必须提供：维度（如产品类别/品牌）
3. 必须提供：指标

**示例**：
- "本月销售额Top 10的产品"
- "昨天订单量Top 5的城市"
- "按产品类别查看销售额分布"

### 避免混淆

❌ **错误示例**：
- "最近30天销售额Top 10的产品"（时间范围+排名，冲突）
- "本月销售额日趋势"（时间点+时间粒度，冲突）

✅ **正确示例**：
- "本月销售额Top 10的产品"（时间点+排名）
- "最近30天销售额日趋势"（时间范围+时间粒度）

## 技术总结

### 降级流程

```
用户输入包含多个分析需求
    ↓
意图分析器同时匹配多个Pattern
    ↓
LLM无法确定唯一Pattern
    ↓
置信度 < pattern_match_threshold
    ↓
触发降级条件
    ↓
降级到React模式（不使用Pattern）
```

### Pattern时间模式

- **SERIES**: 时间序列，需要时间范围和粒度
- **OFFSET**: 偏移对比，需要时间范围和粒度
- **SINGLE_POINT**: 单时间点，只需要时间点
- **RANGE**: 时间范围，只需要范围
- **WINDOW**: 时间窗口，需要窗口参数
- **NONE**: 不涉及时间

### 参数映射

| 用户输入（中文） | SQL字段值 | 说明 |
|----------------|----------|------|
| 日 | DAY | 时间粒度 |
| 周 | WEEK | 时间粒度 |
| 月 | MONTH | 时间粒度 |
| 销售额 | actual_amount | 指标 |
| 订单量 | order_count | 指标 |
| 最近30天 | {"start": "30_days_ago", "end": "today"} | 时间范围 |
| 本月 | "current_month" | 时间点 |
| 昨天 | "yesterday" | 时间点 |

## 结论

1. **问题根源**：模板参数设计不符合不同分析类型的实际需求
2. **用户影响**：输入冲突导致降级，无法使用Pattern模式
3. **解决方案**：
   - 分别执行不同类型的查询
   - 明确表达单一分析意图
   - 改进模板引导提示
4. **长期优化**：考虑改进意图分析器，支持多意图拆分和澄清对话
