# config/loader.py
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatternConfig:
    """模式配置数据类"""
    id: str
    name: str
    description: str
    category: str
    complexity: int
    time_mode: str
    space_mode: str
    sql_template: str
    features: list = field(default_factory=list)
    required_tables: list = field(default_factory=list)
    optional_features: list = field(default_factory=list)
    params_schema: Dict = field(default_factory=dict)

    # 可选配置
    security_rules: Optional[Dict] = None
    grain_mapping: Optional[Dict] = None
    offset_strategies: Optional[Dict] = None
    table_preferences: Optional[list] = None
    performance_notes: Optional[str] = None
    limits: Optional[Dict] = None
    rank_options: Optional[list] = None
    funnel_types: Optional[list] = None
    retention_windows: Optional[list] = None
    model_weights: Optional[Dict] = None
    semantic_types: Optional[list] = None
    drill_algorithm: Optional[str] = None
    significance_threshold: Optional[float] = None


class ConfigLoader:
    """JSON配置加载器"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if config_path:
                cls._instance.load(config_path)
        return cls._instance

    def load(self, config_path: str):
        """加载JSON配置文件"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)

        # 构建pattern索引
        self._pattern_index = {}
        for pattern_id, pattern_data in self._config.get("patterns", {}).items():
            self._pattern_index[pattern_id] = PatternConfig(**pattern_data)

    def get_pattern(self, pattern_id: str) -> PatternConfig:
        """获取模式配置"""
        if pattern_id not in self._pattern_index:
            raise ValueError(f"Unknown pattern: {pattern_id}")
        return self._pattern_index[pattern_id]

    def get_patterns_by_category(self, category: str) -> list:
        """按类别获取模式"""
        category_def = self._config.get("categories", {}).get(category, {})
        pattern_ids = category_def.get("patterns", [])
        return [self.get_pattern(pid) for pid in pattern_ids]

    def get_all_patterns(self) -> Dict[str, PatternConfig]:
        """获取所有模式"""
        return self._pattern_index

    def get_global_setting(self, key: str, default=None):
        """获取全局配置"""
        return self._config.get("global_settings", {}).get(key, default)

    def validate_params(self, pattern_id: str, params: Dict) -> tuple[bool, list]:
        """验证参数是否符合schema"""
        config = self.get_pattern(pattern_id)
        errors = []

        schema = config.params_schema
        for field_name, field_def in schema.items():
            # 检查必填
            if field_def.get("required") and field_name not in params:
                errors.append(f"Missing required field: {field_name}")
                continue

            value = params.get(field_name)
            if value is None:
                continue

            # 类型检查
            field_type = field_def.get("type")
            if field_type == "array" and not isinstance(value, list):
                errors.append(f"{field_name} must be array")
            elif field_type == "integer" and not isinstance(value, int):
                errors.append(f"{field_name} must be integer")
            elif field_type == "string" and not isinstance(value, str):
                errors.append(f"{field_name} must be string")

            # 范围检查
            if field_type == "integer":
                if "min" in field_def and value < field_def["min"]:
                    errors.append(f"{field_name} must be >= {field_def['min']}")
                if "max" in field_def and value > field_def["max"]:
                    errors.append(f"{field_name} must be <= {field_def['max']}")

            # 枚举检查
            if field_type == "enum" and "options" in field_def:
                if value not in field_def["options"]:
                    errors.append(f"{field_name} must be one of {field_def['options']}")

        return len(errors) == 0, errors


# patterns/handlers.py
import re
from typing import Dict, Any, List
from abc import ABC, abstractmethod


class PatternHandler(ABC):
    """模式处理器基类"""

    def __init__(self, config: PatternConfig):
        self.config = config

    @abstractmethod
    def build_sql(self, params: Dict, table_meta: 'TableMeta', context: Dict) -> str:
        """构建SQL"""
        pass

    def validate(self, params: Dict) -> tuple[bool, list]:
        """参数验证"""
        loader = ConfigLoader()
        return loader.validate_params(self.config.id, params)

    def render_template(self, template: str, placeholders: Dict[str, str]) -> str:
        """渲染模板"""
        result = template
        for key, value in placeholders.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def get_required_features(self, params: Dict) -> List[str]:
        """获取需要的特性"""
        features = list(self.config.features)
        # 根据参数启用可选特性
        for opt_feature in self.config.optional_features:
            if opt_feature == "sensitive_mask" and params.get("include_sensitive"):
                features.append(opt_feature)
            elif opt_feature == "rollup_subtotal" and params.get("include_subtotal"):
                features.append(opt_feature)
        return features


class BasicQueryHandler(PatternHandler):
    """基础查询处理器（点查、明细、聚合）"""

    def build_sql(self, params: Dict, table_meta: 'TableMeta', context: Dict) -> str:
        placeholders = {
            "table": table_meta.table_name,
            "time_filter": self._build_time_filter(params, table_meta),
        }

        if self.config.id == "point_query":
            placeholders["metric"] = params.get("metric", "COUNT(*)")

        elif self.config.id == "detail_query":
            fields = params.get("fields", ["*"])
            placeholders["fields"] = ", ".join(fields)
            placeholders["filters"] = self._build_filters(params.get("filters", []))
            placeholders["limit"] = str(params.get("limit", 100))

            # 敏感字段脱敏
            if "sensitive_mask" in self.get_required_features(params):
                placeholders["fields"] = self._apply_mask(fields, table_meta)

        elif self.config.id == "agg_query":
            placeholders["dimensions"] = ", ".join(params.get("dimensions", []))
            placeholders["metric"] = params.get("metric", "COUNT(*)")
            placeholders["filters"] = self._build_filters(params.get("filters", []))

        return self.render_template(self.config.sql_template, placeholders)

    def _build_time_filter(self, params: Dict, table_meta: 'TableMeta') -> str:
        time_point = params.get("time_point") or params.get("time_range", {}).get("end")
        if table_meta.table_type.value == "FULL_SNAPSHOT":
            return f"{table_meta.partition_field} = '{time_point}'"
        return f"{table_meta.partition_field} = '{time_point}' AND {table_meta.event_time_field} BETWEEN '{time_point} 00:00:00' AND '{time_point} 23:59:59'"

    def _build_filters(self, filters: List[Dict]) -> str:
        if not filters:
            return ""
        conditions = []
        for f in filters:
            conditions.append(f"{f['field']} {f['operator']} '{f['value']}'")
        return " AND " + " AND ".join(conditions)

    def _apply_mask(self, fields: List[str], table_meta: 'TableMeta') -> str:
        """敏感字段脱敏"""
        sensitive = self.config.security_rules.get("sensitive_fields", []) if self.config.security_rules else []
        result = []
        for field in fields:
            if field in sensitive:
                result.append(f"MASK({field}) as {field}")
            else:
                result.append(field)
        return ", ".join(result)


class TimeSeriesHandler(PatternHandler):
    """时序分析处理器"""

    def build_sql(self, params: Dict, table_meta: 'TableMeta', context: Dict) -> str:
        time_spec = params.get("time_range", {})
        grain = params.get("time_grain", "DAY")

        placeholders = {
            "table": table_meta.table_name,
            "start": time_spec.get("start"),
            "end": time_spec.get("end"),
            "time_filter": self._build_time_filter(time_spec, table_meta),
            "time_trunc": self._get_time_trunc(grain, table_meta.time_field),
            "metric_calc": self._build_metric_calc(params.get("metric")),
        }

        if self.config.id == "trend_analysis":
            placeholders["dimension_selects"] = self._build_dimension_select(params.get("dimension"))
            placeholders["dimension_nulls"] = self._build_dimension_nulls(params.get("dimension"))
            placeholders["group_by"] = f"GROUP BY {placeholders['time_trunc']}" if not params.get(
                "dimension") else f"GROUP BY {placeholders['time_trunc']}, {params.get('dimension')}"
            placeholders["filters"] = self._build_filters(params.get("filters", []))

        elif self.config.id == "yoy_mom":
            placeholders["group_by"] = f"GROUP BY {placeholders['time_trunc']}"
            # YOY/MOM时间偏移
            yoy_shift = self._get_time_shift(grain, "yoy")
            mom_shift = self._get_time_shift(grain, "mom")
            placeholders["yoy_time_shift"] = yoy_shift
            placeholders["mom_time_shift"] = mom_shift
            placeholders["yoy_time_filter"] = self._build_offset_time_filter(time_spec, yoy_shift, table_meta)
            placeholders["mom_time_filter"] = self._build_offset_time_filter(time_spec, mom_shift, table_meta)

        elif self.config.id == "cumulative":
            placeholders["group_by"] = f"GROUP BY {placeholders['time_trunc']}"

        return self.render_template(self.config.sql_template, placeholders)

    def _get_time_trunc(self, grain: str, time_field: str) -> str:
        """获取时间截断表达式"""
        grain_map = self.config.grain_mapping or {
            "DAY": "{time_field}",
            "WEEK": "DATE_TRUNC('week', {time_field})",
            "MONTH": "DATE_TRUNC('month', {time_field})"
        }
        template = grain_map.get(grain, grain_map["DAY"])
        return template.replace("{time_field}", time_field)

    def _get_time_shift(self, grain: str, shift_type: str) -> str:
        """获取时间偏移表达式"""
        strategies = self.config.offset_strategies or {}
        if shift_type == "yoy":
            return strategies.get("yoy", {}).get("shift", "DATE_ADD({time_trunc}, INTERVAL 1 YEAR)")
        return strategies.get("mom", {}).get("shift", "DATE_ADD({time_trunc}, INTERVAL 1 MONTH)")

    def _build_offset_time_filter(self, time_spec: Dict, shift_expr: str, table_meta: 'TableMeta') -> str:
        """构建偏移时间过滤"""
        # 简化实现：直接计算偏移后的日期范围
        return f"{table_meta.partition_field} BETWEEN '{time_spec.get('start')}' AND '{time_spec.get('end')}'"


class FunnelHandler(PatternHandler):
    """漏斗分析处理器"""

    def build_sql(self, params: Dict, table_meta: 'TableMeta', context: Dict) -> str:
        steps = params.get("steps", [])
        window_days = params.get("time_window", 7)
        strict = params.get("strict_order", True)

        # 动态生成CTE
        ctes = []
        for i, step in enumerate(steps):
            if i == 0:
                ctes.append(self._build_first_step_cte(i, step, table_meta, window_days))
            else:
                ctes.append(self._build_subsequent_step_cte(i, step, table_meta, window_days, strict))

        # 动态生成SELECT
        select_parts = [f"COUNT(DISTINCT step_0.user_id) as step_0_cnt"]
        for i in range(1, len(steps)):
            select_parts.append(f"COUNT(DISTINCT step_{i}.user_id) as step_{i}_cnt")
            select_parts.append(
                f"ROUND(COUNT(DISTINCT step_{i}.user_id) * 100.0 / NULLIF(COUNT(DISTINCT step_{i - 1}.user_id), 0), 2) as step_{i}_rate")

        # 动态生成JOIN
        joins = " ".join([f"LEFT JOIN step_{i} ON step_0.user_id = step_{i}.user_id " for i in range(1, len(steps))])

        placeholders = {
            "funnel_ctes": "WITH " + ",\n".join(ctes),
            "funnel_select": ", ".join(select_parts),
            "funnel_joins": joins
        }

        return self.render_template(self.config.sql_template, placeholders)

    def _build_first_step_cte(self, idx: int, step: str, table_meta: 'TableMeta', window: int) -> str:
        return f"""step_{idx} AS (
    SELECT DISTINCT user_id, MIN(event_time) as step_{idx}_time
    FROM {table_meta.table_name}
    WHERE event_type = '{step}' AND dt >= DATE_SUB(CURRENT_DATE, {window})
    GROUP BY user_id
)"""

    def _build_subsequent_step_cte(self, idx: int, step: str, table_meta: 'TableMeta',
                                   window: int, strict: bool) -> str:
        time_limit = self.config.step_time_limit if self.config.step_time_limit else window * 24
        return f"""step_{idx} AS (
    SELECT s{idx - 1}.user_id, s{idx - 1}.step_{idx - 1}_time, MIN(e.event_time) as step_{idx}_time
    FROM step_{idx - 1} s{idx - 1}
    JOIN {table_meta.table_name} e ON s{idx - 1}.user_id = e.user_id 
        AND e.event_type = '{step}'
        AND e.event_time > s{idx - 1}.step_{idx - 1}_time
        AND TIMESTAMPDIFF(HOUR, s{idx - 1}.step_{idx - 1}_time, e.event_time) <= {time_limit}
    GROUP BY s{idx - 1}.user_id, s{idx - 1}.step_{idx - 1}_time
)"""


class NLFilterHandler(PatternHandler):
    """自然语言筛选处理器"""

    def __init__(self, config: PatternConfig, llm_engine: 'LLMSemanticEngine'):
        super().__init__(config)
        self.llm = llm_engine

    async def build_sql(self, params: Dict, table_meta: 'TableMeta', context: Dict) -> str:
        nl_condition = params.get("nl_condition", "")

        # 调用LLM解析语义条件
        structured = await self.llm.nl_to_filter(nl_condition, {
            "fields": list(table_meta.fields.keys()),
            "types": table_meta.fields
        })

        # 处理需要计算的阈值
        if structured.get("needs_calculation"):
            threshold_sql = self._build_threshold_sql(structured, table_meta)
            # 这里简化处理，实际应先执行获取阈值
            structured = await self._resolve_threshold(threshold_sql, structured)

        # 构建SQL条件
        sql_condition = self._build_sql_condition(structured)

        placeholders = {
            "table": table_meta.table_name,
            "fields": ", ".join(params.get("output_fields", ["*"])),
            "semantic_conditions": sql_condition,
            "time_filter": self._build_time_filter(params.get("time_range"), table_meta),
            "limit": str(params.get("limit", 100))
        }

        return self.render_template(self.config.sql_template, placeholders)

    def _build_threshold_sql(self, structured: Dict, table_meta: 'TableMeta') -> str:
        """构建阈值计算SQL"""
        field = structured.get("field")
        return f"SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY {field}) FROM {table_meta.table_name}"

    def _build_sql_condition(self, structured: Dict) -> str:
        """构建SQL条件"""
        conditions = structured.get("conditions", [])
        parts = []
        for cond in conditions:
            parts.append(f"{cond['field']} {cond['operator']} {cond['value']}")

        logic = structured.get("logic", "AND")
        return f" {logic} ".join(parts) if parts else "1=1"


class HandlerFactory:
    """处理器工厂（JSON配置驱动）"""

    _handlers = {
        "basic": BasicQueryHandler,
        "time_series": TimeSeriesHandler,
        "dimensional": None,  # 类似实现
        "behavioral": {
            "funnel": FunnelHandler,
            "retention": None,
            "path": None
        },
        "attribution": None,
        "intelligent": {
            "nl_filter": NLFilterHandler,
            "anomaly": None,
            "smart_drilldown": None
        }
    }

    @classmethod
    def create_handler(cls, pattern_id: str, config_loader: ConfigLoader,
                       llm_engine: Optional['LLMSemanticEngine'] = None) -> PatternHandler:
        """创建处理器"""
        config = config_loader.get_pattern(pattern_id)
        category = config.category

        # 特殊处理需要LLM的模式
        if pattern_id in (config_loader.get_global_setting("llm_enabled_patterns") or []):
            if not llm_engine:
                raise ValueError(f"Pattern {pattern_id} requires LLM engine")
            return NLFilterHandler(config, llm_engine)

        # 按类别创建
        handler_class = None
        if category == "basic":
            handler_class = BasicQueryHandler
        elif category == "time_series":
            handler_class = TimeSeriesHandler
        elif category == "behavioral":
            handler_class = cls._handlers["behavioral"].get(pattern_id)
        elif category == "intelligent":
            handler_class = cls._handlers["intelligent"].get(pattern_id)

        if not handler_class:
            raise ValueError(f"No handler for pattern: {pattern_id}")

        return handler_class(config)


# engine/chatbi_engine.py
import json
from typing import Dict, Any, Optional


class ChatBIEngine:
    """JSON配置驱动的ChatBI引擎"""

    def __init__(self, config_path: str, openai_key: Optional[str] = None):
        # 加载JSON配置
        self.config_loader = ConfigLoader(config_path)

        # 初始化LLM（如果需要）
        self.llm = None
        if openai_key and self._needs_llm():
            self.llm = LLMSemanticEngine(openai_key)

        # SQL构建器
        self.sql_builder = SQLBuilder(self.config_loader)

        # 查询执行器
        self.executor = QueryExecutor()

    def _needs_llm(self) -> bool:
        """检查是否有需要LLM的模式"""
        llm_patterns = self.config_loader.get_global_setting("llm_enabled_patterns", [])
        return len(llm_patterns) > 0

    async def query(self, nl_query: str, scene_id: str, context: Dict = None) -> Dict:
        """主查询入口"""
        context = context or {}
        context["scene_id"] = scene_id

        # Step 1: 意图识别（使用LLM或规则）
        parse_result = await self._parse_intent(nl_query, context)

        if parse_result.get("status") == "need_clarification":
            return parse_result

        # Step 2: 确定模式
        pattern_id = self._determine_pattern(parse_result)
        pattern_config = self.config_loader.get_pattern(pattern_id)

        # Step 3: 参数验证
        params = parse_result.get("params", {})
        is_valid, errors = self.config_loader.validate_params(pattern_id, params)
        if not is_valid:
            return {
                "status": "param_error",
                "errors": errors,
                "pattern": pattern_id
            }

        # Step 4: 创建处理器并构建SQL
        handler = HandlerFactory.create_handler(pattern_id, self.config_loader, self.llm)

        # 异步构建（某些模式需要LLM）
        if isinstance(handler, NLFilterHandler):
            sql = await handler.build_sql(params, self._get_table_meta(scene_id), context)
        else:
            sql = handler.build_sql(params, self._get_table_meta(scene_id), context)

        # Step 5: 执行
        result = await self.executor.execute(sql)

        # Step 6: 生成洞察（对复杂模式）
        insight = None
        if pattern_config.complexity >= 3:
            insight = await self._generate_insight(result, pattern_id)

        return {
            "status": "success",
            "pattern": {
                "id": pattern_id,
                "name": pattern_config.name,
                "category": pattern_config.category,
                "complexity": pattern_config.complexity
            },
            "sql": sql,
            "data": result,
            "insight": insight,
            "features_used": handler.get_required_features(params)
        }

    async def _parse_intent(self, nl_query: str, context: Dict) -> Dict:
        """意图解析"""
        if self.llm:
            return await self.llm.parse(nl_query, context)

        # 简化的规则解析
        return self._rule_based_parse(nl_query, context)

    def _determine_pattern(self, parse_result: Dict) -> str:
        """确定使用哪个模式"""
        # 基于解析结果和配置推荐
        suggested = parse_result.get("suggested_pattern", "point_query")

        # 检查复杂度限制
        config = self.config_loader.get_pattern(suggested)
        max_complexity = self.config_loader.get_global_setting("max_complexity", 5)

        if config.complexity > max_complexity:
            # 降级到简单模式
            return "point_query"

        return suggested

    def _get_table_meta(self, scene_id: str) -> 'TableMeta':
        """获取场景表元数据"""
        # 从注册中心获取
        pass

    def get_pattern_catalog(self) -> Dict:
        """获取模式目录（用于前端展示）"""
        catalog = {}
        for cat_id, cat_def in self.config_loader._config.get("categories", {}).items():
            catalog[cat_id] = {
                "name": cat_def["name"],
                "patterns": []
            }
            for pid in cat_def.get("patterns", []):
                config = self.config_loader.get_pattern(pid)
                catalog[cat_id]["patterns"].append({
                    "id": config.id,
                    "name": config.name,
                    "description": config.description,
                    "complexity": config.complexity,
                    "features": config.features
                })
        return catalog

    def get_pattern_params_schema(self, pattern_id: str) -> Dict:
        """获取模式参数Schema（用于前端表单生成）"""
        config = self.config_loader.get_pattern(pattern_id)
        return {
            "pattern_id": config.id,
            "pattern_name": config.name,
            "params_schema": config.params_schema,
            "time_mode": config.time_mode,
            "space_mode": config.space_mode
        }


# 初始化引擎
engine = ChatBIEngine(
    config_path="config/patterns.json",
    openai_key="sk-..."
)

# 获取可用模式目录
catalog = engine.get_pattern_catalog()
print(json.dumps(catalog, indent=2, ensure_ascii=False))


# 查询示例
async def demo():
    # 趋势分析
    result = await engine.query(
        "最近30天销售额趋势",
        scene_id="ecommerce",
        context={"available_metrics": ["销售额", "订单数"], "available_dimensions": ["地区", "品类"]}
    )
    print(result)

    # 漏斗分析（JSON配置驱动）
    result = await engine.query(
        "注册到购买的转化漏斗",
        scene_id="ecommerce",
        context={"steps": ["注册", "浏览", "加购", "下单", "支付"]}
    )
    print(result)

    # 自然语言筛选（需要LLM）
    result = await engine.query(
        "高价值且最近未购买的用户",
        scene_id="ecommerce"
    )
    print(result)


# 动态修改配置（热更新）
def update_pattern_config():
    loader = ConfigLoader()
    config = loader.get_pattern("funnel")

    # 修改最大步骤数
    new_limits = {"max_steps": 10}
    # 保存回JSON（实际实现需考虑并发安全）