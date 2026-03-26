"""场景模板加载器 - 从QA模板库目录加载模板，支持数据源引用"""
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TemplateConfig:
    """模板配置数据类"""
    template_id: str
    name: str
    description: str = ""
    pattern_id: Optional[str] = None
    datasource: Optional[str] = None
    params_schema: Dict[str, Any] = field(default_factory=dict)
    
    # 用户提示信息
    user_prompt: Optional[str] = None
    important_notes: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    
    # 留存分析专用字段
    retention_windows: Optional[List[int]] = None
    
    # 默认参数
    default_params: Dict[str, Any] = field(default_factory=dict)
    
    # 兼容旧字段（逐步废弃）
    sql_template: Optional[str] = None


class SceneTemplateLoader:
    """场景模板加载器 - 从QA模板库目录加载模板"""

    def __init__(self, scenes_config_path: Optional[str] = None, qa_template_dir: Optional[str] = None):
        """
        初始化模板加载器

        Args:
            scenes_config_path: 场景配置文件路径（用于获取场景元信息）
            qa_template_dir: QA模板库目录路径
        """
        self.scenes_config_path = scenes_config_path
        self._scenes_config = {}
        self._template_index: Dict[str, TemplateConfig] = {}  # template_id -> TemplateConfig
        self._scene_templates_index: Dict[str, List[str]] = {}  # scene_code -> [template_ids]
        self._template_datasource_index: Dict[str, str] = {}  # template_id -> datasource_id
        
        # 加载场景配置（用于获取场景元信息）
        if scenes_config_path:
            self._load_scenes_config(scenes_config_path)
        
        # 加载QA模板库
        if qa_template_dir:
            self._load_qa_templates(qa_template_dir)
        elif scenes_config_path:
            # 从项目根目录推断QA模板库路径
            project_root = Path(scenes_config_path).parent.parent
            qa_dir = project_root / "config" / "QA模板库"
            if qa_dir.exists():
                self._load_qa_templates(str(qa_dir))
            else:
                logger.warning(f"QA模板库目录不存在: {qa_dir}")

    def _load_scenes_config(self, config_path: str):
        """加载场景配置文件（只获取场景元信息）"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"场景配置文件不存在: {config_path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self._scenes_config = json.load(f)
            logger.info(f"加载场景配置成功: {len(self._scenes_config.get('scenes', []))} 个场景")
        except Exception as e:
            logger.error(f"加载场景配置失败: {e}", exc_info=True)

    def _load_qa_templates(self, qa_dir: str):
        """加载QA模板库目录"""
        qa_path = Path(qa_dir)
        if not qa_path.exists():
            logger.warning(f"QA模板库目录不存在: {qa_dir}")
            return

        try:
            # 遍历场景子目录
            for scene_dir in qa_path.iterdir():
                if not scene_dir.is_dir():
                    continue
                
                scene_code = scene_dir.name
                templates_file = scene_dir / "templates.json"
                
                if not templates_file.exists():
                    logger.warning(f"场景模板文件不存在: {templates_file}")
                    continue
                
                self._load_scene_templates(scene_code, templates_file)
            
            logger.info(f"QA模板库加载成功: 共 {len(self._template_index)} 个模板")
        except Exception as e:
            logger.error(f"加载QA模板库失败: {e}", exc_info=True)

    def _load_scene_templates(self, scene_code: str, templates_file: Path):
        """加载单个场景的模板文件"""
        try:
            with open(templates_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            datasource = data.get("datasource")
            templates = data.get("templates", [])
            
            template_ids = []
            for template_data in templates:
                template_id = template_data.get("id")
                if not template_id:
                    continue
                
                # 构建TemplateConfig
                config = TemplateConfig(
                    template_id=template_id,
                    name=template_data.get("name", template_id),
                    description=template_data.get("description", ""),
                    pattern_id=template_data.get("pattern_id"),
                    datasource=datasource,
                    params_schema=template_data.get("params_schema", {}),
                    user_prompt=template_data.get("user_prompt"),
                    important_notes=template_data.get("important_notes"),
                    examples=template_data.get("examples"),
                    retention_windows=template_data.get("retention_windows"),
                    default_params=template_data.get("default_params", {}),
                    sql_template=template_data.get("sql_template")
                )
                
                self._template_index[template_id] = config
                self._template_datasource_index[template_id] = datasource
                template_ids.append(template_id)
                
                logger.debug(f"加载模板: {scene_code}.{template_id} (datasource={datasource})")
            
            self._scene_templates_index[scene_code] = template_ids
            logger.info(f"场景 {scene_code} 加载 {len(template_ids)} 个模板, 数据源: {datasource}")
            
        except Exception as e:
            logger.error(f"加载场景模板失败 {templates_file}: {e}", exc_info=True)

    def get_template(self, template_id: str) -> Optional[TemplateConfig]:
        """获取模板配置"""
        return self._template_index.get(template_id)

    def get_template_by_qa_id(self, qa_template_id: str) -> Optional[TemplateConfig]:
        """
        通过QA模板ID获取场景模板配置
        
        ⚠️ 重要变更：QA模板ID已统一，直接使用template_id即可

        Args:
            qa_template_id: QA模板ID（与template_id一致）
        
        Returns:
            TemplateConfig 或 None
        """
        # 直接查找（ID已统一）
        if qa_template_id in self._template_index:
            logger.info(f"[模板查找] 直接找到模板: {qa_template_id}")
            return self._template_index[qa_template_id]
        
        # 兼容旧版ID的映射（逐步废弃）
        LEGACY_ID_MAPPING = {
            "top_products": "sales_topn",
            "category_breakdown": "sales_breakdown",
            "sales_trend_daily": "sales_trend_analysis",
            "sales_trend_weekly": "sales_trend_analysis",
            "sales_trend_monthly": "sales_trend_analysis",
        }
        
        if qa_template_id in LEGACY_ID_MAPPING:
            mapped_id = LEGACY_ID_MAPPING[qa_template_id]
            if mapped_id in self._template_index:
                logger.info(f"[兼容映射] 旧ID {qa_template_id} -> 新ID {mapped_id}")
                return self._template_index[mapped_id]
        
        logger.warning(f"未找到QA模板ID对应的场景模板: {qa_template_id}")
        return None

    def get_template_datasource(self, template_id: str) -> Optional[str]:
        """获取模板关联的数据源ID"""
        return self._template_datasource_index.get(template_id)

    def get_scene_templates(self, scene_code: str) -> List[TemplateConfig]:
        """获取场景的所有模板"""
        template_ids = self._scene_templates_index.get(scene_code, [])
        return [self._template_index[tid] for tid in template_ids if tid in self._template_index]

    def get_all_templates(self) -> Dict[str, TemplateConfig]:
        """获取所有模板"""
        return self._template_index

    def get_scene(self, scene_code: str) -> Optional[Dict[str, Any]]:
        """获取场景配置"""
        scenes = self._scenes_config.get("scenes", [])
        for scene in scenes:
            if scene.get("scene_code") == scene_code:
                return scene
        return None

    def get_all_scenes(self) -> List[Dict[str, Any]]:
        """获取所有场景"""
        return self._scenes_config.get("scenes", [])

    def get_template_catalog(self, scene_code: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模板目录(用于前端展示)

        Args:
            scene_code: 场景代码，如果不指定则返回所有场景的模板
        """
        catalog = {}
        
        if scene_code:
            # 返回指定场景的模板
            templates = self.get_scene_templates(scene_code)
            catalog[scene_code] = {
                "scene_name": self._get_scene_name(scene_code),
                "templates": [
                    {
                        "id": t.template_id,
                        "name": t.name,
                        "description": t.description,
                        "pattern_id": t.pattern_id
                    }
                    for t in templates
                ]
            }
        else:
            # 返回所有场景的模板
            for scene_code, template_ids in self._scene_templates_index.items():
                catalog[scene_code] = {
                    "scene_name": self._get_scene_name(scene_code),
                    "templates": []
                }
                for tid in template_ids:
                    template = self._template_index.get(tid)
                    if template:
                        catalog[scene_code]["templates"].append({
                            "id": template.template_id,
                            "name": template.name,
                            "description": template.description,
                            "pattern_id": template.pattern_id
                        })
        
        return catalog

    def _get_scene_name(self, scene_code: str) -> str:
        """获取场景名称"""
        scene = self.get_scene(scene_code)
        return scene.get("scene_name", scene_code) if scene else scene_code

    def resolve_param_schema(self, template_id: str) -> Dict[str, Any]:
        """
        解析模板的参数schema，将 metric_ref/dimension_ref 类型解析为具体选项
        
        Args:
            template_id: 模板ID
        
        Returns:
            解析后的参数schema
        """
        template = self.get_template(template_id)
        if not template:
            return {}
        
        resolved_schema = {}
        datasource_id = template.datasource
        
        for param_name, param_def in template.params_schema.items():
            param_type = param_def.get("type")
            resolved_def = dict(param_def)
            
            # 解析引用类型
            if param_type == "metric_ref" and datasource_id:
                # 从数据源获取指标选项
                resolved_def["type"] = "select"
                resolved_def["options"] = self._get_metric_options(datasource_id)
            
            elif param_type == "dimension_ref" and datasource_id:
                # 从数据源获取维度选项
                resolved_def["type"] = "select"
                resolved_def["options"] = self._get_dimension_options(datasource_id)
            
            elif param_type == "dimension_ref_array" and datasource_id:
                # 从数据源获取维度选项（多选）
                resolved_def["type"] = "multiselect"
                resolved_def["options"] = self._get_dimension_options(datasource_id)
            
            elif param_type == "time_grain":
                # 时间粒度选项
                resolved_def["type"] = "select"
                resolved_def["options"] = [
                    {"value": "DAY", "label": "日"},
                    {"value": "WEEK", "label": "周"},
                    {"value": "MONTH", "label": "月"}
                ]
            
            resolved_schema[param_name] = resolved_def
        
        return resolved_schema

    def _get_metric_options(self, datasource_id: str) -> List[Dict[str, str]]:
        """从数据源获取指标选项"""
        try:
            from .datasource_loader import datasource_loader
            return datasource_loader.get_metric_options(datasource_id)
        except Exception as e:
            logger.warning(f"获取数据源指标失败: {datasource_id}, error: {e}")
            return []

    def _get_dimension_options(self, datasource_id: str) -> List[Dict[str, str]]:
        """从数据源获取维度选项"""
        try:
            from .datasource_loader import datasource_loader
            return datasource_loader.get_dimension_options(datasource_id)
        except Exception as e:
            logger.warning(f"获取数据源维度失败: {datasource_id}, error: {e}")
            return []

    def validate_params(self, template_id: str, params: Dict) -> tuple[bool, List[str]]:
        """验证参数是否符合schema"""
        template = self.get_template(template_id)
        if not template:
            return False, [f"Template {template_id} not found"]
        
        errors = []
        schema = template.params_schema
        
        # 特殊字段：这些字段在SQL构建时会被特殊处理，允许复杂类型
        special_fields = {"time_range", "time_point", "filters", "fields", "dimensions"}
        
        for field_name, field_def in schema.items():
            # 检查必填
            if field_def.get("required") and field_name not in params:
                errors.append(f"Missing required field: {field_name}")
                continue
            
            value = params.get(field_name)
            if value is None:
                continue
            
            # 特殊字段跳过类型检查（会被SQL构建器特殊处理）
            if field_name in special_fields:
                continue
            
            # 类型检查
            field_type = field_def.get("type")
            if field_type in ("array", "dimension_ref_array") and not isinstance(value, list):
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
        
        return len(errors) == 0, errors

    def get_field_mapping(self, template_id: str, param_name: str, user_value: str) -> Optional[str]:
        """
        获取字段的映射值（通过数据源解析）
        
        例如：用户说"销售额"，映射为"SUM(total_amount)"
        """
        template = self.get_template(template_id)
        if not template:
            return None
        
        datasource_id = template.datasource
        param_config = template.params_schema.get(param_name, {})
        param_type = param_config.get("type")
        
        # 通过数据源解析
        if datasource_id:
            try:
                from .datasource_loader import datasource_loader
                
                if param_type == "metric_ref":
                    return datasource_loader.resolve_metric_field(datasource_id, user_value)
                elif param_type in ("dimension_ref", "dimension_ref_array"):
                    return datasource_loader.resolve_dimension_field(datasource_id, user_value)
            except Exception as e:
                logger.warning(f"解析字段映射失败: {e}")
        
        # 回退到旧的 field_mapping
        field_mapping = param_config.get("field_mapping", {})
        return field_mapping.get(user_value)
    
    def get_time_trunc_mapping(self, template_id: str, time_grain: str, sql_context: Dict[str, Any]) -> Optional[str]:
        """
        获取时间截断映射
        
        例如：time_grain="DAY", 映射为 "DATE({time_field})"
        """
        template = self.get_template(template_id)
        if not template:
            return None
        
        time_grain_config = template.params_schema.get("time_grain", {})
        mapping = time_grain_config.get("time_trunc_mapping", {})
        
        template_str = mapping.get(time_grain)
        if template_str:
            # 替换模板中的占位符
            time_field = sql_context.get("time_field", "created_at")
            return template_str.replace("{time_field}", time_field)
        
        # 默认映射
        default_mapping = {
            "DAY": f"DATE({sql_context.get('time_field', 'created_at')})",
            "WEEK": f"DATE_TRUNC('week', {sql_context.get('time_field', 'created_at')})",
            "MONTH": f"DATE_TRUNC('month', {sql_context.get('time_field', 'created_at')})"
        }
        return default_mapping.get(time_grain)
