"""Pattern配置加载器 - 基于JSON配置驱动的SQL模式系统"""
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


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
    features: List[str] = field(default_factory=list)
    required_tables: List[str] = field(default_factory=list)
    optional_features: List[str] = field(default_factory=list)
    params_schema: Dict = field(default_factory=dict)
    
    # 用户提示信息（用于前端展示和LLM理解）
    user_prompt: Optional[str] = None
    important_notes: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    
    # 可选配置
    security_rules: Optional[Dict] = None
    grain_mapping: Optional[Dict] = None
    offset_strategies: Optional[Dict] = None
    table_preferences: Optional[List[str]] = None
    performance_notes: Optional[str] = None
    limits: Optional[Dict] = None
    rank_options: Optional[List[str]] = None
    funnel_types: Optional[List[str]] = None
    retention_windows: Optional[List[int]] = None
    model_weights: Optional[Dict] = None
    semantic_types: Optional[List[str]] = None
    drill_algorithm: Optional[str] = None
    significance_threshold: Optional[float] = None
    step_time_limit: Optional[int] = None  # 漏斗分析的步骤时间限制
    
    # 热门问题模板
    hot_templates: Optional[List[Dict[str, Any]]] = None


class PatternLoader:
    """Pattern配置加载器(单例模式)"""
    
    _instance: Optional["PatternLoader"] = None
    _config: Dict[str, Any] = {}
    _pattern_index: Dict[str, PatternConfig] = {}
    
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
            logger.warning(f"Pattern配置文件不存在: {config_path}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            
            # 构建pattern索引
            self._pattern_index = {}
            for pattern_id, pattern_data in self._config.get("patterns", {}).items():
                self._pattern_index[pattern_id] = PatternConfig(**pattern_data)
            
            logger.info(f"Pattern配置加载成功: {len(self._pattern_index)} 个模式")
        except Exception as e:
            logger.error(f"加载Pattern配置失败: {e}", exc_info=True)
            raise
    
    def get_pattern(self, pattern_id: str) -> Optional[PatternConfig]:
        """获取模式配置"""
        return self._pattern_index.get(pattern_id)
    
    def get_patterns_by_category(self, category: str) -> List[PatternConfig]:
        """按类别获取模式"""
        category_def = self._config.get("categories", {}).get(category, {})
        pattern_ids = category_def.get("patterns", [])
        return [self.get_pattern(pid) for pid in pattern_ids if self.get_pattern(pid)]
    
    def get_all_patterns(self) -> Dict[str, PatternConfig]:
        """获取所有模式"""
        return self._pattern_index
    
    def get_global_setting(self, key: str, default=None):
        """获取全局配置"""
        return self._config.get("global_settings", {}).get(key, default)
    
    def validate_params(self, pattern_id: str, params: Dict) -> tuple[bool, List[str]]:
        """验证参数是否符合schema"""
        config = self.get_pattern(pattern_id)
        if not config:
            return False, [f"Pattern {pattern_id} not found"]
        
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
    
    def get_pattern_catalog(self) -> Dict[str, Any]:
        """获取模式目录(用于前端展示)"""
        catalog = {}
        for cat_id, cat_def in self._config.get("categories", {}).items():
            catalog[cat_id] = {
                "name": cat_def["name"],
                "patterns": []
            }
            for pid in cat_def.get("patterns", []):
                config = self.get_pattern(pid)
                if config:
                    catalog[cat_id]["patterns"].append({
                        "id": config.id,
                        "name": config.name,
                        "description": config.description,
                        "complexity": config.complexity,
                        "category": config.category
                    })
        return catalog
    
    def get_hot_templates(self, pattern_id: str) -> List[Dict[str, Any]]:
        """获取指定pattern的热门问题模板"""
        config = self.get_pattern(pattern_id)
        if config and config.hot_templates:
            return config.hot_templates
        
        # 如果没有配置,返回默认示例模板
        return self._generate_default_templates(pattern_id)
    
    def _generate_default_templates(self, pattern_id: str) -> List[Dict[str, Any]]:
        """生成默认模板(当配置中没有hot_templates时)"""
        config = self.get_pattern(pattern_id)
        if not config:
            return []
        
        templates = []
        
        # 根据不同pattern类型生成默认模板
        if pattern_id == "point_query":
            templates = [
                {
                    "id": f"{pattern_id}_1",
                    "question": "查询今天的销售额",
                    "template": "查询{{time_point}}的{{metric}}",
                    "default_params": {
                        "metric": "销售额",
                        "time_point": "今天"
                    }
                },
                {
                    "id": f"{pattern_id}_2",
                    "question": "查询昨天的订单数量",
                    "template": "查询{{time_point}}的{{metric}}",
                    "default_params": {
                        "metric": "订单数量",
                        "time_point": "昨天"
                    }
                }
            ]
        elif pattern_id == "trend_analysis":
            templates = [
                {
                    "id": f"{pattern_id}_1",
                    "question": "最近30天的销售趋势",
                    "template": "分析最近{{days}}天的{{metric}}趋势",
                    "default_params": {
                        "metric": "销售额",
                        "days": "30"
                    }
                },
                {
                    "id": f"{pattern_id}_2",
                    "question": "最近7天的用户增长趋势",
                    "template": "分析最近{{days}}天的{{metric}}趋势",
                    "default_params": {
                        "metric": "用户数",
                        "days": "7"
                    }
                }
            ]
        elif pattern_id == "agg_query":
            templates = [
                {
                    "id": f"{pattern_id}_1",
                    "question": "按地区统计销售额",
                    "template": "按{{dimension}}统计{{metric}}",
                    "default_params": {
                        "dimension": "地区",
                        "metric": "销售额"
                    }
                },
                {
                    "id": f"{pattern_id}_2",
                    "question": "按品类统计订单数",
                    "template": "按{{dimension}}统计{{metric}}",
                    "default_params": {
                        "dimension": "品类",
                        "metric": "订单数"
                    }
                }
            ]
        
        return templates
