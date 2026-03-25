# 模板模式降级原因分析

## 问题描述

用户选择了"销售趋势-日销售趋势"模板后，输入：
```
'时间范围是最近30天' '指标是销售额' '时间粒度是日' '查看销售额Top 10的产品'
```

系统出现降级（fallback到React模式）。

## 根本原因

**问题核心**：用户的输入包含了**两个不同的分析需求**，导致意图分析器无法确定应该使用哪个Pattern。

### 用户输入拆解

1. **趋势分析需求** (trend_analysis)
   - "时间范围是最近30天"
   - "指标是销售额"
   - "时间粒度是日"

2. **排名分析需求** (topn)
   - "查看销售额Top 10的产品"

### 两个Pattern的参数要求

#### 趋势分析 (trend_analysis)
```json
{
  "params_schema": {
    "metric": {"type": "string", "required": true},
    "time_grain": {"type": "enum", "options": ["DAY", "WEEK", "MONTH"]},
    "time_range": {"type": "range", "required": true},
    "dimension": {"type": "string", "default": null}
  }
}
```

#### 排名分析 (topn)
```json
{
  "params_schema": {
    "metric": {"type": "string", "required": true},
    "dimension": {"type": "string", "required": true},
    "n": {"type": "integer", "required": true, "min": 1, "max": 100},
    "time_point": {"type": "string", "required": true}
  }
}
```

### 降级流程

```
用户输入
    ↓
意图分析
    ↓
问题: 输入包含两个不同的分析需求
    ├─ 前半部分匹配 trend_analysis
    └─ 后半部分匹配 topn
    ↓
LLM无法确定唯一Pattern
    ↓
置信度低 或 intent_type != "pattern_match"
    ↓
触发降级条件:
  - intent_type != "pattern_match" OR
  - matched_pattern is None OR
  - confidence < pattern_match_threshold
    ↓
降级到React模式
```

### 代码逻辑（agent_wrapper.py:923-931）

```python
# Step 2: 根据意图选择处理模式
if (intent_result.intent_type == "pattern_match" and 
    intent_result.matched_pattern and
    intent_result.confidence >= chatbi_config.pattern_match_threshold):
    
    logger.info(f"[Pattern模式] 匹配到Pattern: {intent_result.matched_pattern}")
    return await self._process_with_pattern(conversation, message, intent_result)
else:
    logger.info("[React模式] 未匹配Pattern或置信度不足,使用React模式")
```

## 解决方案

### 方案1：分步查询（推荐）

将两个分析需求分开执行：

**第一次查询** - 趋势分析
```
输入: 时间范围是最近30天，指标是销售额，时间粒度是日
预期: 匹配 trend_analysis，生成趋势SQL
结果:
```sql
SELECT DATE(created_at) as period, SUM(total_amount) as value 
FROM sales_analysis 
WHERE created_at BETWEEN '2024-02-23' AND '2024-03-24' 
GROUP BY DATE(created_at) 
ORDER BY period
```

**第二次查询** - 排名分析
```
输入: 查看销售额Top 10的产品
预期: 匹配 topn，生成排名SQL
结果:
```sql
WITH ranked AS (
    SELECT product_name, total_amount as value, 
    ROW_NUMBER() OVER (ORDER BY total_amount DESC) as rank 
    FROM sales_analysis 
    WHERE created_at <= CURRENT_TIMESTAMP 
    GROUP BY product_name
) 
SELECT product_name, value, rank 
FROM ranked 
WHERE rank <= 10 
ORDER BY rank
```

### 方案2：明确表达单一意图

在输入时只表达一个明确的意图：

**查看趋势**
```
我想看最近30天销售额的日趋势
```

**查看排名**
```
我想看销售额Top 10的产品
```

### 方案3：使用模板引导

1. 第一次选择"销售趋势"模板
2. 只输入趋势分析的参数：
   ```
   时间范围是最近30天
   指标是销售额
   时间粒度是日
   ```
3. 系统生成趋势SQL

4. 第二次选择"排名分析"模板（或直接输入）
5. 输入排名分析的参数：
   ```
   指标是销售额
   维度是产品
   Top N是10
   ```
6. 系统生成排名SQL

### 方案4：改进意图分析器（未来优化）

增强意图分析器的能力：

1. **多意图检测**：
   - 检测用户输入是否包含多个分析需求
   - 例如：同时检测到趋势和排名

2. **智能澄清**：
   ```
   检测到您的查询包含多个分析需求：
   1. 查看最近30天销售额的日趋势
   2. 查看销售额Top 10的产品
   
   请问您想先执行哪个分析？
   ```

3. **多查询拆分**：
   - 自动将复合查询拆分为多个独立查询
   - 依次执行并返回结果

## 参数映射验证

即使正确分离查询，参数映射也需要验证：

### 趋势分析参数映射

| 中文参数 | SQL参数 | 映射结果 |
|---------|---------|---------|
| "销售额" | metric | "total_amount" |
| "日" | time_grain | "DAY" |
| "最近30天" | time_range | {"start": "2024-02-23", "end": "2024-03-24"} |

### 排名分析参数映射

| 中文参数 | SQL参数 | 映射结果 |
|---------|---------|---------|
| "销售额" | metric | "total_amount" |
| "产品" | dimension | "product_name" |
| "10" | n | 10 |
| "Top 10" | 隐含n=10 | 10 |

## 用户引导改进

为了帮助用户避免此类问题，已优化参数引导提示：

```
## 📋 模板模式: 趋势概览

查看关键指标的趋势变化

为了完成分析，请提供以下参数：

### 必填参数
- **指标** (select)
  - 可选值: `销售额`, `订单量`, `活跃用户数`
- **时间粒度** (select)
  - 可选值: `日`, `周`, `月`
- **时间范围** (date_range)

---
💡 **提示**: 您可以直接用中文告诉我参数值，例如：
- '时间范围是最近30天'
- '指标是销售额'
- '时间粒度是日'

⚠️ **注意**: 一次查询只执行一种分析。如果您需要多种分析，请分别输入：
- 例1: '时间范围是最近30天，指标是销售额，时间粒度是日'（趋势分析）
- 例2: '查看销售额Top 10的产品'（排名分析）

系统会自动将您的中文参数转换为对应的SQL条件。
```

## 日志分析建议

当遇到降级时，查看以下日志：

```bash
# 查看意图分析日志
grep "意图分析" logs/chatbi.log

# 查看Pattern匹配日志
grep "Pattern模式\|React模式" logs/chatbi.log

# 查看置信度
grep "置信度" logs/chatbi.log

# 查看降级原因
grep "降级\|fallback" logs/chatbi.log
```

## 测试用例

### 用例1：正确使用趋势分析
```
用户选择: 销售趋势模板
用户输入: 时间范围是最近30天，指标是销售额，时间粒度是日
预期结果: 
  - 匹配 pattern_id = "trend_analysis"
  - 置信度 >= 0.7
  - 生成趋势SQL
```

### 用例2：正确使用排名分析
```
用户输入: 查看销售额Top 10的产品
预期结果:
  - 匹配 pattern_id = "topn"
  - 置信度 >= 0.7
  - 生成排名SQL
```

### 用例3：错误使用 - 多个分析需求
```
用户输入: 时间范围是最近30天，指标是销售额，查看Top 10产品
预期结果:
  - 置信度 < 0.7（或 intent_type = "llm_react"）
  - 降级到React模式
  - 系统提示: "您的查询包含多个分析需求，请分别输入"
```

## 总结

**核心问题**：一次输入包含多个不同的分析需求

**根本原因**：意图分析器无法确定唯一的Pattern，导致置信度低或匹配失败

**解决方案**：
1. ✅ 分步查询（推荐）
2. ✅ 明确表达单一意图
3. ✅ 使用模板引导
4. 🔧 改进意图分析器（未来）

**用户引导**：已优化参数提示，明确告知用户"一次查询只执行一种分析"
