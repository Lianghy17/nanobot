# 问答模板系统实现说明

## 概述

本文档描述了ChatBI问答模板系统的完整实现，包括知识库、表schema、QA模板库的创建，以及前端3种问答模式的支持。

## 目录结构

```
config/
├── 知识库/
│   ├── sales_analysis/
│   │   ├── 业务知识.md
│   │   └── 指标说明.md
│   ├── user_behavior/
│   │   ├── 业务知识.md
│   │   └── 指标说明.md
│   └── general_bi/
│       └── 业务知识.md
├── 表schema/
│   ├── sales_analysis/
│   │   └── sales_schema.json
│   ├── user_behavior/
│   │   └── user_behavior_schema.json
│   └── general_bi/
│       └── general_schema.json
└── QA模板库/
    ├── sales_analysis/
    │   └── templates.json
    ├── user_behavior/
    │   └── templates.json
    └── general_bi/
        └── templates.json
```

## 1. 知识库配置

### 1.1 销售分析 (sales_analysis)

**业务知识.md** 包含：
- 核心指标定义（销售额、订单量、客单价、转化率、复购率）
- 常见分析场景（销售趋势、产品表现、渠道表现、客户分析）
- 数据分析建议
- 注意事项

**指标说明.md** 包含：
- 基础指标（销售额、订单数量、客单价、商品数量）
- 客户指标（客户数、新客数、老客数、复购率）
- 转化指标（转化率、下单率、支付成功率）
- 利润指标（毛利润、毛利率、净利润）
- 对比指标（同比增长率、环比增长率）

### 1.2 用户行为 (user_behavior)

**业务知识.md** 包含：
- 核心指标定义（活跃用户数、留存率、转化率、跳出率、平均会话时长）
- 用户行为分析场景（漏斗分析、留存分析、路径分析、分群分析）
- 数据分析建议
- 注意事项

**指标说明.md** 包含：
- 用户活跃指标（DAU、WAU、MAU、活跃度）
- 留存指标（次日留存、7日留存、30日留存、用户生命周期）
- 转化指标（注册转化率、激活转化率、付费转化率）
- 互动指标（页面浏览量、平均会话时长、跳出率、点击率）
- 漏斗指标（步骤转化率、整体转化率、流失率）
- 路径指标（路径频次、路径转化率）

### 1.3 通用BI (general_bi)

**业务知识.md** 包含：
- 核心概念（什么是通用BI分析）
- 分析模式（模板模式、React模式、QA模式）
- 数据分析能力（基础查询、时序分析、维度探索、智能分析）
- 使用指南
- 常见问题类型
- 最佳实践

## 2. 表Schema配置

### 2.1 销售分析Schema

**sales_schema.json** 定义了：
- **fact_sales** - 销售事实表
  - 订单基本信息（订单ID、客户ID、产品ID、日期、时间）
  - 销售数据（数量、单价、总金额、优惠金额、实付金额、成本）
  - 关联维度（产品、类别、渠道、地区、客户）
- **dim_product** - 产品维度表
- **dim_category** - 产品类别维度表
- **dim_channel** - 渠道维度表
- **dim_region** - 地区维度表
- **dim_customer** - 客户维度表
- **dim_date** - 日期维度表

### 2.2 用户行为Schema

**user_behavior_schema.json** 定义了：
- **fact_user_events** - 用户行为事实表
  - 事件信息（事件ID、用户ID、事件类型、日期、时间）
  - 页面信息（URL、标题）
  - 会话信息（会话ID）
  - 设备和来源（设备类型、平台、来源、活动）
- **dim_user** - 用户维度表
- **fact_sessions** - 会话事实表
- **fact_funnel** - 漏斗事实表
- **fact_retention** - 留存事实表
- **dim_event_type** - 事件类型维度表
- **dim_date** - 日期维度表

### 2.3 通用BISchema

**general_schema.json** 定义了：
- **fact_sales** - 销售事实表（简化版）
- **fact_user_events** - 用户行为事实表（简化版）
- **dim_customer** - 客户维度表
- **dim_product** - 产品维度表
- **dim_date** - 日期维度表

## 3. QA模板库配置

### 3.1 销售分析模板

**categories** (分类):
- 销售趋势: sales_trend_daily, sales_yoy_mom
- 产品分析: top_products, category_breakdown
- 渠道分析: channel_comparison
- 客户分析: customer_type_analysis, repurchase_rate
- 区域分析: regional_sales

**templates** (模板):
1. **sales_trend_daily** - 日销售趋势
   - 参数: 时间范围、指标、时间粒度
2. **sales_yoy_mom** - 销售同环比分析
   - 参数: 指标、时间粒度、时间范围、对比类型
3. **top_products** - TopN产品销售
   - 参数: 时间点、指标、Top N、包含其他
4. **category_breakdown** - 产品类别销售分布
   - 参数: 时间点、指标、维度
5. **channel_comparison** - 渠道销售对比
   - 参数: 时间点、指标、对比渠道
6. **customer_type_analysis** - 客户类型分析
   - 参数: 时间范围、指标
7. **repurchase_rate** - 复购率分析
   - 参数: 时间点
8. **regional_sales** - 地区销售分析
   - 参数: 时间点、指标、地区维度

### 3.2 用户行为模板

**categories** (分类):
- 用户活跃: dau_trend
- 转化分析: funnel_conversion
- 留存分析: day7_retention
- 路径分析: user_path_analysis
- 用户分析: user_segmentation
- 互动分析: bounce_rate, session_duration

**templates** (模板):
1. **dau_trend** - DAU趋势分析
   - 参数: 时间范围、活跃指标、时间粒度
2. **funnel_conversion** - 漏斗转化分析
   - 参数: 漏斗名称、漏斗步骤、时间窗口、严格顺序
3. **day7_retention** - 7日留存分析
   - 参数: 时间范围、同期群粒度、留存天数
4. **user_path_analysis** - 用户路径分析
   - 参数: 时间范围、起始事件、结束事件、最大路径长度
5. **user_segmentation** - 用户分群分析
   - 参数: 时间范围、指标、分群维度
6. **bounce_rate** - 跳出率分析
   - 参数: 时间点、分组维度
7. **session_duration** - 会话时长分析
   - 参数: 时间范围、时间粒度、时长指标

### 3.3 通用BI模板

**categories** (分类):
- 自由查询: flexible_query, data_exploration, custom_report
- 快速查询: quick_point_query
- 趋势分析: trend_overview
- 维度分析: multi_dimension_analysis
- 排名分析: ranking_analysis
- 对比分析: comparison_analysis

**templates** (模板):
1. **flexible_query** - 灵活查询
2. **data_exploration** - 数据探索
3. **custom_report** - 自定义报表
4. **quick_point_query** - 快速点查
5. **trend_overview** - 趋势概览
6. **multi_dimension_analysis** - 多维度分析
7. **ranking_analysis** - 排名分析
8. **comparison_analysis** - 对比分析

## 4. 前端实现

### 4.1 UI组件

**右侧QA面板**:
- 标题: "📋 QA模板库"
- 模式选择器: 3个模式按钮
  - 🎯 模板模式 - 快速匹配
  - 🤖 React模式 - 灵活分析
  - 📝 QA模式 - 直接提问
- QA列表: 按分类展示模板

**模式提示**:
- 在消息列表顶部显示当前模式的说明
- 包含模式特点和优势

### 4.2 JavaScript功能

**全局状态**:
```javascript
let currentMode = 'template';  // 当前问答模式
let qaTemplates = {};  // QA模板数据
let currentTemplate = null;  // 当前选中的模板
```

**核心函数**:
- `loadHotQuestions(sceneCode)` - 加载场景的QA模板
- `renderQATemplates(qaData)` - 渲染QA模板列表
- `renderTemplateItem(template)` - 渲染单个模板项
- `toggleCategory(categoryKey)` - 切换分类展开/收起
- `switchMode(mode)` - 切换问答模式
- `useTemplate(templateId)` - 使用QA模板

### 4.3 模式说明

#### 模板模式
- 系统自动匹配用户提问与预定义模板
- 引导用户完善查询条件
- 基于模板生成SQL
- 优点: 快速响应、SQL质量高、参数验证严格

#### React模式
- 当问题未命中模板时采用
- 使用大模型理解用户意图
- 通过多轮对话逐步明确需求
- 基于schema智能生成SQL
- 优点: 灵活性高、支持复杂查询、自然语言交互友好

#### QA模式
- 用户直接点击右侧QA模板
- 显示模板详情和参数定义
- 引导用户填写参数
- 生成SQL并执行查询
- 优点: 操作简单、问题明确、参数填写有引导

## 5. 后端API实现

### 5.1 API路由

**文件**: `chatbi/api/qa_templates.py`

**端点**:
1. `GET /api/qa/templates/{scene_code}`
   - 获取场景的QA模板
   - 返回: 模板列表和分类信息

2. `GET /api/qa/templates/{scene_code}/{template_id}`
   - 获取QA模板详情
   - 返回: 单个模板的完整信息

3. `GET /api/qa/schema/{scene_code}`
   - 获取场景的表结构
   - 返回: 表定义和关系

4. `GET /api/qa/knowledge/{scene_code}`
   - 获取场景的知识库
   - 返回: 知识库文件列表

### 5.2 路由注册

**main.py**:
```python
from chatbi.api import conversations_router, messages_router, scenes_router, files_router, sse_router, patterns_router, qa_templates_router

app.include_router(qa_templates_router, prefix="/api/qa", tags=["qa"])
```

## 6. 使用流程

### 6.1 用户使用流程

1. **选择场景**
   - 点击"➕ 新建对话"
   - 选择分析场景（销售分析/用户行为/通用BI）

2. **选择问答模式**
   - 右侧面板显示3种模式按钮
   - 点击选择适合的模式
   - 消息列表显示模式说明

3. **使用QA模式** (推荐新手)
   - 在右侧QA模板库中浏览分类
   - 点击感兴趣的模板
   - 系统引导填写参数
   - 生成查询并执行

4. **使用模板模式** (标准查询)
   - 直接在输入框提问
   - 系统自动匹配模板
   - 引导完善参数
   - 生成SQL并执行

5. **使用React模式** (复杂查询)
   - 直接在输入框描述需求
   - 系统多轮对话理解
   - 智能生成SQL
   - 执行并返回结果

### 6.2 模式切换

- 3种模式可以随时切换
- 切换后显示对应模式的说明
- 不会影响当前对话历史

## 7. 扩展说明

### 7.1 添加新场景

1. 在`config/知识库/`创建场景文件夹
2. 在`config/表schema/`创建场景schema文件
3. 在`config/QA模板库/`创建场景模板文件
4. 在`config/scenes.json`中添加场景配置

### 7.2 添加新模板

在对应场景的`templates.json`中添加模板定义：
```json
{
  "id": "template_id",
  "name": "模板名称",
  "category": "分类名称",
  "description": "模板描述",
  "question_template": "问题模板",
  "pattern_id": "pattern_id",
  "default_params": {},
  "params_schema": {},
  "examples": []
}
```

### 7.3 扩展知识库

在场景文件夹下添加新的`.md`文件，内容会被自动加载到知识库中。

## 8. 技术要点

### 8.1 前端技术
- CSS Grid/Flexbox布局
- 动态DOM操作
- Fetch API调用
- 状态管理

### 8.2 后端技术
- FastAPI路由
- JSON文件读取
- 路径拼接和验证
- 异常处理

### 8.3 数据结构
- 模板结构: id, name, category, description, pattern_id, default_params, params_schema, examples
- Schema结构: tables, relationships
- 知识库: Markdown格式文档

## 9. 注意事项

1. **文件编码**: 所有JSON和MD文件使用UTF-8编码
2. **路径拼接**: 使用`os.path.join`确保跨平台兼容
3. **错误处理**: 添加完整的异常处理和日志记录
4. **前端兼容**: 确保旧浏览器兼容性（如需要）
5. **性能优化**: 大量模板时考虑分页加载
6. **权限控制**: 未来可添加用户权限验证

## 10. 总结

本问答模板系统实现了：
- ✅ 3个场景的完整配置（销售分析、用户行为、通用BI）
- ✅ 知识库、Schema、QA模板的分离管理
- ✅ 前端3种问答模式支持
- ✅ 灵活的模式切换机制
- ✅ 可扩展的架构设计
- ✅ 完整的API接口

该系统为用户提供了灵活、易用的数据分析体验，同时保持了代码的可维护性和可扩展性。
