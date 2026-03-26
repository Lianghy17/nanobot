# 参数映射与SQL生成功能实现文档

## 功能概述

本文档描述了ChatBI系统中参数映射与SQL生成功能的实现。该功能允许用户使用中文参数值（如"销售额"、"日"、"同比"等），系统会自动将其转换为SQL友好的字段值，并生成对应的SQL查询语句。

## 核心功能

### 1. 参数映射（ParamMapper）

**文件位置**: `chatbi/core/param_mapper.py`

**功能描述**:
- 将中文参数值转换为SQL可用的字段名和条件
- 支持多种映射策略：预定义映射、RAG知识库检索、LLM推断
- 处理指标、时间粒度、对比类型、维度、时间等不同类型的参数

**映射示例**:

| 参数类型 | 中文值 | SQL值 | 映射策略 |
|---------|-------|--------|---------|
| 指标 (metric) | 销售额 | total_amount | 预定义映射 |
| 指标 (metric) | 订单量 | order_count | 预定义映射 |
| 时间粒度 (time_grain) | 日 | DAY | 预定义映射 |
| 时间粒度 (time_grain) | 周 | WEEK | 预定义映射 |
| 时间粒度 (time_grain) | 月 | MONTH | 预定义映射 |
| 对比类型 (comparison_types) | 同比 | yoy | 预定义映射 |
| 对比类型 (comparison_types) | 环比 | mom | 预定义映射 |
| 时间点 (time_point) | 今天 | today | 预定义映射 |
| 时间点 (time_point) | 昨天 | yesterday | 预定义映射 |
| 时间点 (time_point) | 本月 | current_month | 预定义映射 |
| 时间点 (time_point) | 上月 | last_month | 预定义映射 |

### 2. SQL构建器增强（SQLBuilder）

**文件位置**: `chatbi/core/sql_builder.py`

**改动内容**:
- 在构建SQL之前先调用参数映射器转换参数值
- 支持异步映射（`async build()`方法）
- 集成RAG知识库和LLM推断作为fallback机制

**工作流程**:
```
用户输入参数
    ↓
参数验证
    ↓
参数映射 (ParamMapper)
    ↓
预定义映射 → RAG检索 → LLM推断 (fallback)
    ↓
SQL模板填充
    ↓
生成SQL
```

### 3. 参数引导显示优化

**文件位置**: `chatbi/core/agent_wrapper.py`

**改动内容**:
- 参数引导时显示中文标签（label）而非参数名（key）
- 参数说明部分使用中文标签
- 优先显示options中的中文label

**示例输出**:

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
- '查看销售额Top 10的产品'

系统会自动将您的中文参数转换为对应的SQL条件。
```

### 4. SQL响应参数说明优化

**改动内容**:
- 在SQL响应中显示参数的中文标签
- 更友好的用户体验

**示例输出**:

```
## 🎯 模板模式: 趋势概览

已为您生成SQL查询语句：

```sql
SELECT DATE(created_at) as period, SUM(total_amount) as value 
FROM sales_analysis 
WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31' 
GROUP BY DATE(created_at) 
ORDER BY period
```

### 参数说明
- **指标**: `total_amount`
- **时间粒度**: `DAY`
- **时间范围**: `{'start': '2024-01-01', 'end': '2024-01-31'}`

💡 **提示**: 此SQL已根据您选择的模板和参数生成，您可以直接在数据库中执行此查询。
```

## 使用场景

### 场景1: 用户选择模板后填写参数

**用户操作**:
1. 点击右侧的"趋势概览"模板
2. 系统显示参数引导（带中文标签）
3. 用户输入："我想看最近30天销售额的趋势，按天统计"

**系统处理**:
1. 参数提取: {metric: "销售额", time_range: "最近30天", time_grain: "日"}
2. 参数映射:
   - "销售额" → "total_amount"
   - "最近30天" → {"start": "2024-02-22", "end": "2024-03-23"}
   - "日" → "DAY"
3. SQL生成:
   ```sql
   SELECT DATE(created_at) as period, SUM(total_amount) as value 
   FROM sales_analysis 
   WHERE created_at BETWEEN '2024-02-22' AND '2024-03-23' 
   GROUP BY DATE(created_at) 
   ORDER BY period
   ```

### 场景2: 用户直接输入问题（RAG匹配模板）

**用户操作**:
- 输入："查看销售额的Top 10产品"

**系统处理**:
1. 意图分析匹配到"排名分析"模板（pattern_id: "topn"）
2. 参数提取: {metric: "销售额", dimension: "产品", n: 10}
3. 参数映射:
   - "销售额" → "total_amount"
   - "产品" → "product_name"
4. SQL生成:
   ```sql
   WITH ranked AS (
       SELECT product_name, total_amount as value, 
       ROW_NUMBER() OVER (ORDER BY total_amount DESC) as rank 
       FROM sales_analysis 
       WHERE created_at <= CURRENT_TIMESTAMP 
       GROUP BY product_name
   ) 
   SELECT product_name, value, rank, 
   CASE WHEN rank <= 10 THEN product_name ELSE '其他' END as category 
   FROM ranked 
   ORDER BY rank
   ```

### 场景3: 同环比分析

**用户操作**:
- 输入："分析销售额的同比和环比变化"

**系统处理**:
1. 意图分析匹配到"对比分析"模板（pattern_id: "yoy_mom"）
2. 参数提取: {metric: "销售额", comparison_types: ["同比", "环比"]}
3. 参数映射:
   - "销售额" → "total_amount"
   - "同比", "环比" → ["yoy", "mom"]
4. SQL生成（包含同比环比计算逻辑）

## 测试

### 测试文件
- `/Users/lianghaoyun/project/nanobot/test_param_mapper.py`

### 运行测试
```bash
cd /Users/lianghaoyun/project/nanobot
python3 test_param_mapper.py
```

### 测试用例

1. **中文指标映射**
   - 输入: {"metric": "销售额", "time_grain": "日"}
   - 输出: {"metric": "total_amount", "time_grain": "DAY"}

2. **中文时间粒度映射**
   - 输入: {"time_grain": "周"}
   - 输出: {"time_grain": "WEEK"}

3. **对比类型映射**
   - 输入: {"comparison_types": ["同比", "环比"]}
   - 输出: {"comparison_types": ["yoy", "mom"]}

4. **时间参数映射**
   - 输入: {"time_point": "昨天"}
   - 输出: {"time_point": "yesterday"}

## 架构设计

### 组件交互图

```
用户输入
    ↓
AgentWrapper.process()
    ↓
IntentAnalyzer.analyze()
    ↓ (如果匹配Pattern)
ProcessWithPattern()
    ↓
ParamMapper.map_params() ← RAG Tool, LLM Client
    ↓
SQLBuilder.build()
    ↓
SQL生成完成
```

### 关键类说明

1. **ParamMapper**: 参数映射器
   - `map_params()`: 主映射方法
   - `_map_metric()`: 指标映射
   - `_map_time_grain()`: 时间粒度映射
   - `_map_comparison_types()`: 对比类型映射
   - `_map_dimension()`: 维度映射
   - `_map_time_param()`: 时间参数映射
   - `_llm_infer_metric()`: LLM推断指标

2. **PatternSQLBuilder**: SQL构建器
   - `build()`: 异步构建方法
   - 集成ParamMapper进行参数转换

3. **AgentWrapper**: Agent包装器
   - `_guide_template_params()`: 引导参数填写
   - `_process_with_pattern()`: 使用Pattern处理

## 扩展性

### 添加新的参数映射

在`ParamMapper`类中添加新的映射方法：

```python
async def _map_custom_param(self, param_value: str, scene_code: str) -> str:
    """自定义参数映射"""
    # 1. 尝试预定义映射
    if param_value in self.predefined_mappings.get("custom", {}):
        return self.predefined_mappings["custom"][param_value]
    
    # 2. 尝试RAG检索
    rag_result = await self.rag_tool.execute(...)
    
    # 3. 尝试LLM推断
    mapped_value = await self._llm_infer_custom(param_value, scene_code)
    
    return mapped_value
```

### 扩展预定义映射

在`__init__()`方法中扩展`predefined_mappings`字典：

```python
self.predefined_mappings = {
    "metrics": {
        "销售额": "total_amount",
        # 添加更多指标...
    },
    "time_grain": {
        # 添加更多时间粒度...
    },
    # 添加更多映射类型...
}
```

## 注意事项

1. **RAG服务配置**: 确保RAG服务地址配置正确（`http://my_rag_v1`）
2. **LLM配置**: 确保LLM API配置正确，temperature等参数符合模型要求
3. **性能优化**: 参数映射可以添加缓存机制，避免重复调用RAG和LLM
4. **错误处理**: 映射失败时应有合理的fallback策略

## 未来改进

1. **缓存机制**: 缓存参数映射结果，提高性能
2. **批量映射**: 支持批量参数映射，减少API调用次数
3. **自定义映射**: 允许用户在配置文件中定义自定义映射规则
4. **映射历史**: 记录映射历史，便于调试和优化
5. **智能推荐**: 根据用户历史推荐参数值

## 相关文件

- `chatbi/core/param_mapper.py`: 参数映射器核心实现
- `chatbi/core/sql_builder.py`: SQL构建器（集成参数映射）
- `chatbi/core/agent_wrapper.py`: Agent包装器（参数引导和响应）
- `config/QA模板库/general_bi/templates.json`: 模板配置文件
- `config/pattern_config.json`: Pattern配置文件
- `test_param_mapper.py`: 参数映射测试文件
