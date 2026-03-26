# Template 模式重构说明

## 重构目标

将原来基于 `pattern_config.json` 的通用模式复用架构，改为每个场景独立配置模板的架构。

## 核心变化

### 1. 配置结构变化

**之前**（pattern_config.json + scenes.json）：
```json
// pattern_config.json - 定义16种通用模式
{
  "patterns": {
    "point_query": { ... },
    "trend_analysis": { ... },
    ...
  }
}

// scenes.json - 场景复用模式
{
  "scenes": [
    {
      "scene_code": "sales_analysis",
      "supported_patterns": ["point_query", "trend_analysis", ...]
    }
  ]
}
```

**现在**（仅 scenes.json）：
```json
// scenes.json - 每个场景独立定义模板
{
  "scenes": [
    {
      "scene_code": "sales_analysis",
      "templates": [
        {
          "template_id": "sales_point_query",
          "name": "销售点查",
          "description": "查询单个时间点的销售指标值",
          "sql_template": "SELECT {metric_field} as value FROM {table_name} WHERE {time_filter}",
          "params_schema": { ... },
          "user_prompt": "...",
          "important_notes": [...],
          "examples": [...]
        },
        {
          "template_id": "sales_trend_analysis",
          "name": "销售趋势分析",
          ...
        }
      ]
    }
  ]
}
```

### 2. 代码结构变化

#### 新增文件

- `chatbi/core/template_loader.py` - 场景模板加载器
  - `TemplateConfig` - 模板配置数据类
  - `SceneTemplateLoader` - 从场景配置加载模板
  - 提供模板查询、验证、映射等功能

#### 修改文件

1. **intent_analyzer.py**
   - 将 `PatternLoader` 改为 `SceneTemplateLoader`
   - 将 `PatternConfig` 改为 `TemplateConfig`
   - `matched_pattern` 改为 `matched_template`
   - `pattern_match` 改为 `template_match`
   - 从场景的 `templates` 列表获取可用模板

2. **pattern_handler.py**
   - 将 `PatternLoader` 改为 `SceneTemplateLoader`
   - 将 `pattern_config` 改为 `template_config`
   - 从模板配置获取 `user_prompt` 和 `important_notes`

3. **sql_builder.py**
   - 将 `PatternLoader` 改为 `SceneTemplateLoader`
   - 将 `PatternConfig` 改为 `TemplateConfig`
   - 占位符 `{table}` 改为 `{table_name}`

4. **agent_wrapper.py**
   - 使用 `SceneTemplateLoader` 替代 `PatternLoader`
   - 从 `scenes.json` 加载配置

5. **param_mapper.py**
   - 参数 `pattern_id` 改为 `template_id`
   - 注释更新

### 3. 模板配置示例

每个场景的模板包含以下字段：

```json
{
  "template_id": "sales_point_query",
  "name": "销售点查",
  "description": "查询单个时间点的销售指标值",
  "sql_template": "SELECT {metric_field} as value FROM {table_name} WHERE {time_filter}",
  "params_schema": {
    "metric": {
      "label": "指标",
      "type": "string",
      "required": true,
      "options": ["销售额", "销售量", "订单数", "客单价"],
      "field_mapping": {
        "销售额": "total_amount",
        "销售量": "quantity",
        "订单数": "COUNT(order_id)",
        "客单价": "AVG(total_amount)"
      }
    },
    "time_point": {
      "label": "时间点",
      "type": "string",
      "required": true,
      "description": "如：今天、昨天、本月、2024-01-01"
    }
  },
  "user_prompt": "查询单个时间点的销售指标值，适合快速获取某个时间点的数据快照。",
  "important_notes": [
    "指标和时间点是必填参数",
    "支持相对时间(今天/昨天/本周/本月)和绝对时间(2024-01-01)",
    "指标会自动求和聚合"
  ],
  "examples": [
    "查询今天的销售额",
    "查询昨天的订单量"
  ]
}
```

## 优势

1. **更灵活** - 每个场景可以完全自定义模板，不受通用模式限制
2. **更清晰** - 场景和模板是一对多的关系，配置结构一目了然
3. **更易维护** - 修改某个场景的模板不影响其他场景
4. **更好扩展** - 添加新场景时只需在 scenes.json 中添加新配置

## 兼容性

- API 接口保持兼容，前端无需修改
- SSE 事件名称保持一致（`pattern_processing_started` → `template_processing_started` 可选）
- 核心处理流程不变，只是数据来源从 PatternLoader 改为 TemplateLoader

## 待优化

1. pattern_config.json 可以保留作为模式定义参考
2. 可以进一步简化模板配置，使用更多继承机制
3. 前端可以根据场景动态显示可用模板
