"""SQL构建器 - 基于Pattern配置生成SQL"""
import logging
import re
from typing import Dict, Any, Optional, List, Set
from abc import ABC, abstractmethod

from .pattern_loader import PatternLoader, PatternConfig
from .param_mapper import ParamMapper

logger = logging.getLogger(__name__)


class SQLFormatter:
    """SQL格式化器 - 美化SQL输出"""
    
    # SQL关键字（需要换行的）
    MAJOR_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'UNION', 'UNION ALL',
        'WITH', 'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM'
    }
    
    # 缩进关键字
    INDENT_KEYWORDS = {
        'AND', 'OR', 'ON', 'WHEN', 'THEN', 'ELSE', 'END', 'AS'
    }
    
    @classmethod
    def format(cls, sql: str, indent_size: int = 4) -> str:
        """
        格式化SQL语句，使其更易读
        
        Args:
            sql: 原始SQL语句
            indent_size: 缩进空格数
            
        Returns:
            格式化后的SQL
        """
        if not sql:
            return sql
        
        # 清理多余空白
        sql = ' '.join(sql.split())
        
        # 格式化主关键字
        formatted = cls._format_major_keywords(sql, indent_size)
        
        # 格式化AND/OR条件
        formatted = cls._format_conditions(formatted, indent_size)
        
        # 格式化SELECT字段
        formatted = cls._format_select_fields(formatted, indent_size)
        
        # 清理多余空行
        formatted = re.sub(r'\n\s*\n', '\n', formatted)
        
        return formatted.strip()
    
    @classmethod
    def _format_major_keywords(cls, sql: str, indent_size: int) -> str:
        """格式化主要SQL关键字"""
        result = sql
        
        # 按关键字换行
        for keyword in sorted(cls.MAJOR_KEYWORDS, key=len, reverse=True):
            # 匹配关键字（忽略大小写，前面不能是字母）
            pattern = rf'(?<![a-zA-Z0-9_])({keyword})(?![a-zA-Z0-9_])'
            result = re.sub(pattern, rf'\n{keyword}', result, flags=re.IGNORECASE)
        
        return result
    
    @classmethod
    def _format_conditions(cls, sql: str, indent_size: int) -> str:
        """格式化AND/OR条件"""
        lines = sql.split('\n')
        result_lines = []
        
        for line in lines:
            # 检查是否是WHERE或HAVING子句
            stripped = line.strip().upper()
            if stripped.startswith(('WHERE', 'HAVING', 'ON')):
                # 对AND/OR进行换行处理
                indent = ' ' * indent_size
                formatted_line = re.sub(
                    r'\s+(AND|OR)\s+',
                    rf'\n{indent}\1 ',
                    line,
                    flags=re.IGNORECASE
                )
                result_lines.append(formatted_line)
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def _format_select_fields(cls, sql: str, indent_size: int) -> str:
        """格式化SELECT字段列表"""
        lines = sql.split('\n')
        result_lines = []
        
        for line in lines:
            stripped = line.strip().upper()
            if stripped.startswith('SELECT'):
                # 查找字段列表
                match = re.match(r'(SELECT\s+)(.+)', line, re.IGNORECASE)
                if match:
                    prefix = match.group(1)
                    fields_str = match.group(2)
                    
                    # 如果字段较多（包含多个逗号），则分行显示
                    if fields_str.count(',') >= 2:
                        fields = [f.strip() for f in fields_str.split(',')]
                        indent = ' ' * indent_size
                        formatted_fields = f",\n{indent}".join(fields)
                        line = f"{prefix}\n{indent}{formatted_fields}"
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)


class PlaceholderResolver:
    """占位符解析器 - 处理特殊占位符的构建逻辑"""
    
    # 特殊占位符类型
    SPECIAL_PLACEHOLDERS = {
        "time_filter": "time_filter",
        "time_trunc": "time_trunc",
        "filters": "filters",
        "fields": "fields",
        "dimensions": "dimensions",
        "rollup_clause": "rollup_clause",
        "pivot_values": "pivot_values",
        "pivot_columns": "pivot_columns",
    }
    
    def __init__(self, time_field: str = "created_at"):
        self.time_field = time_field
    
    def resolve(self, placeholder: str, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """解析单个占位符"""
        resolver_name = self.SPECIAL_PLACEHOLDERS.get(placeholder)
        
        if resolver_name:
            method = getattr(self, f"_resolve_{resolver_name}", None)
            if method:
                return method(params, context)
        
        # 普通参数：直接从 params 获取
        return self._resolve_simple(placeholder, params)
    
    def _resolve_simple(self, key: str, params: Dict[str, Any]) -> str:
        """解析简单参数"""
        value = params.get(key, "")
        
        # 数组类型：转为逗号分隔字符串
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        
        return str(value) if value is not None else ""
    
    def _resolve_time_filter(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建时间过滤条件"""
        time_point = params.get("time_point")
        time_range = params.get("time_range", {})
        
        if time_point:
            return f"{self.time_field} = '{time_point}'"
        
        start = time_range.get("start")
        end = time_range.get("end")
        if start and end:
            return f"{self.time_field} BETWEEN '{start}' AND '{end}'"
        elif start:
            return f"{self.time_field} >= '{start}'"
        elif end:
            return f"{self.time_field} <= '{end}'"
        
        return f"{self.time_field} <= CURRENT_TIMESTAMP"
    
    def _resolve_time_trunc(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建时间截断表达式"""
        grain = params.get("time_grain", "DAY")
        grain_map = {
            "DAY": f"DATE({self.time_field})",
            "WEEK": f"DATE_TRUNC('week', {self.time_field})",
            "MONTH": f"DATE_TRUNC('month', {self.time_field})"
        }
        return grain_map.get(grain, grain_map["DAY"])
    
    def _resolve_filters(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建过滤条件"""
        filters = params.get("filters", [])
        if not filters:
            return ""
        conditions = []
        for f in filters:
            conditions.append(f"{f['field']} {f['operator']} '{f['value']}'")
        return " AND " + " AND ".join(conditions)
    
    def _resolve_fields(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建字段列表"""
        fields = params.get("fields", ["*"])
        return ", ".join(fields)
    
    def _resolve_dimensions(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建维度列表"""
        dimensions = params.get("dimensions", [])
        return ", ".join(dimensions) if dimensions else ""
    
    def _resolve_rollup_clause(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建 ROLLUP 子句"""
        return "WITH ROLLUP" if params.get("include_subtotal") else ""
    
    def _resolve_pivot_values(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建 pivot 值列表"""
        comparison_field = params.get("comparison_field", "")
        comparison_values = params.get("comparison_values", [])
        if comparison_values:
            return ", ".join([f"'{v}'" for v in comparison_values])
        return ""
    
    def _resolve_pivot_columns(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建 pivot 列"""
        comparison_field = params.get("comparison_field", "")
        comparison_values = params.get("comparison_values", [])
        if comparison_values and comparison_field:
            return ", ".join([f"SUM(CASE WHEN {comparison_field} = '{v}' THEN value ELSE 0 END) as `{v}`" for v in comparison_values])
        return ""


class SQLBuilder(ABC):
    """SQL构建器基类"""
    
    @abstractmethod
    def build_sql(self, pattern_config: PatternConfig, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建SQL"""
        pass
    
    def extract_placeholders(self, template: str) -> Set[str]:
        """从模板中提取所有占位符"""
        return set(re.findall(r'\{(\w+)\}', template))
    
    def render_template(self, template: str, placeholders: Dict[str, str]) -> str:
        """渲染SQL模板"""
        result = template
        for key, value in placeholders.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result


class UniversalSQLBuilder(SQLBuilder):
    """通用SQL构建器 - 基于模板自动解析占位符"""
    
    def build_sql(self, pattern_config: PatternConfig, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        time_field = context.get("time_field", "created_at")
        table_name = context.get("table_name", "unknown_table")
        
        # 创建占位符解析器
        resolver = PlaceholderResolver(time_field)
        
        # 提取模板中的所有占位符
        placeholders_needed = self.extract_placeholders(pattern_config.sql_template)
        
        logger.debug(f"[SQL构建器] 模板占位符: {placeholders_needed}")
        
        # 构建占位符值映射
        placeholders = {}
        
        # 1. 先填充 table（来自 context）
        if "table" in placeholders_needed:
            placeholders["table"] = table_name
        
        # 2. 自动填充其他占位符
        for placeholder in placeholders_needed:
            if placeholder == "table":
                continue  # 已处理
            
            # 使用解析器解析
            value = resolver.resolve(placeholder, params, context)
            placeholders[placeholder] = value
        
        logger.info(f"[SQL构建器] 占位符映射: {placeholders}")
        
        # 渲染模板
        return self.render_template(pattern_config.sql_template, placeholders)


class SQLBuilderFactory:
    """SQL构建器工厂"""
    
    _default_builder = UniversalSQLBuilder
    
    @classmethod
    def create_builder(cls, pattern_config: PatternConfig) -> SQLBuilder:
        """创建SQL构建器 - 统一使用通用构建器"""
        return cls._default_builder()


class PatternSQLBuilder:
    """Pattern SQL构建器主类"""
    
    def __init__(self, pattern_loader: PatternLoader):
        self.pattern_loader = pattern_loader
        self.factory = SQLBuilderFactory()
        self.param_mapper = ParamMapper()
    
    async def build(
        self, 
        pattern_id: str, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        构建SQL
        
        Returns:
            (sql, error_message) - 成功时sql有值，失败时error_message有值
        """
        # 获取pattern配置
        pattern_config = self.pattern_loader.get_pattern(pattern_id)
        if not pattern_config:
            return None, f"Pattern {pattern_id} not found"
        
        # 第一步：使用参数映射器将中文参数转换为SQL友好值（必须在验证之前）
        logger.info(f"[SQL构建器] 原始参数: {params}")
        mapped_params, map_error = await self.param_mapper.map_params(
            pattern_id=pattern_id,
            params=params,
            scene_code=context.get("scene_code", "sales_analysis"),
            context=context
        )
        
        if map_error:
            logger.warning(f"[SQL构建器] 参数映射警告: {map_error}")
        
        logger.info(f"[SQL构建器] 映射后参数: {mapped_params}")
        
        # 第二步：验证映射后的参数
        is_valid, errors = self.pattern_loader.validate_params(pattern_id, mapped_params)
        if not is_valid:
            error_detail = "; ".join(errors)
            logger.error(f"[SQL构建器] 参数验证失败: {error_detail}")
            return None, f"参数验证失败: {error_detail}"
        
        # 创建构建器
        builder = self.factory.create_builder(pattern_config)
        
        try:
            sql = builder.build_sql(pattern_config, mapped_params, context)
            # 格式化SQL
            formatted_sql = SQLFormatter.format(sql)
            logger.info(f"[SQL构建器] 构建成功: {pattern_id}")
            logger.debug(f"[SQL构建器] 格式化SQL:\n{formatted_sql}")
            return formatted_sql, None
        except Exception as e:
            logger.error(f"[SQL构建器] 构建失败: {e}", exc_info=True)
            return None, f"SQL构建失败: {str(e)}"
