"""数据源加载器 - 管理数据源配置，提供指标和维度查询"""
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """指标定义"""
    id: str
    name: str
    field: str
    type: str
    agg: str
    description: str = ""
    filter: Optional[str] = None  # 可选的过滤条件


@dataclass
class DimensionDefinition:
    """维度定义"""
    id: str
    name: str
    field: str
    description: str = ""


@dataclass
class DataSourceConfig:
    """数据源配置"""
    datasource_id: str
    name: str
    description: str
    table_name: str
    time_field: str
    primary_key: str
    metrics: List[MetricDefinition] = field(default_factory=list)
    dimensions: List[DimensionDefinition] = field(default_factory=list)
    common_filters: List[Dict[str, Any]] = field(default_factory=list)


class DataSourceLoader:
    """数据源加载器 - 单例模式"""
    
    _instance: Optional["DataSourceLoader"] = None
    
    def __new__(cls, config_dir: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_dir: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self._datasources: Dict[str, DataSourceConfig] = {}
        
        # 确定配置目录
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 默认从 chatbi/config 获取项目根目录
            from ..config import chatbi_config
            self.config_dir = Path(chatbi_config.config_dir) / "datasources"
        
        # 加载所有数据源
        self._load_all_datasources()
    
    def _load_all_datasources(self):
        """加载所有数据源配置"""
        if not self.config_dir.exists():
            logger.warning(f"数据源配置目录不存在: {self.config_dir}")
            return
        
        for config_file in self.config_dir.glob("*.json"):
            try:
                self._load_datasource(config_file)
            except Exception as e:
                logger.error(f"加载数据源配置失败 {config_file}: {e}")
    
    def _load_datasource(self, config_path: Path):
        """加载单个数据源配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析指标
        metrics = []
        for m in data.get("metrics", []):
            metrics.append(MetricDefinition(
                id=m["id"],
                name=m["name"],
                field=m["field"],
                type=m["type"],
                agg=m["agg"],
                description=m.get("description", ""),
                filter=m.get("filter")
            ))
        
        # 解析维度
        dimensions = []
        for d in data.get("dimensions", []):
            dimensions.append(DimensionDefinition(
                id=d["id"],
                name=d["name"],
                field=d["field"],
                description=d.get("description", "")
            ))
        
        # 创建数据源配置
        datasource = DataSourceConfig(
            datasource_id=data["datasource_id"],
            name=data["name"],
            description=data.get("description", ""),
            table_name=data["table_name"],
            time_field=data["time_field"],
            primary_key=data["primary_key"],
            metrics=metrics,
            dimensions=dimensions,
            common_filters=data.get("common_filters", [])
        )
        
        self._datasources[datasource.datasource_id] = datasource
        logger.info(f"加载数据源: {datasource.datasource_id}, 指标数: {len(metrics)}, 维度数: {len(dimensions)}")
    
    def get_datasource(self, datasource_id: str) -> Optional[DataSourceConfig]:
        """获取数据源配置"""
        return self._datasources.get(datasource_id)
    
    def get_metric(self, datasource_id: str, metric_id: str) -> Optional[MetricDefinition]:
        """获取指定指标"""
        datasource = self.get_datasource(datasource_id)
        if not datasource:
            return None
        
        for metric in datasource.metrics:
            if metric.id == metric_id or metric.name == metric_id:
                return metric
        return None
    
    def get_dimension(self, datasource_id: str, dimension_id: str) -> Optional[DimensionDefinition]:
        """获取指定维度"""
        datasource = self.get_datasource(datasource_id)
        if not datasource:
            return None
        
        for dimension in datasource.dimensions:
            if dimension.id == dimension_id or dimension.name == dimension_id:
                return dimension
        return None
    
    def get_all_metrics(self, datasource_id: str) -> List[MetricDefinition]:
        """获取数据源的所有指标"""
        datasource = self.get_datasource(datasource_id)
        return datasource.metrics if datasource else []
    
    def get_all_dimensions(self, datasource_id: str) -> List[DimensionDefinition]:
        """获取数据源的所有维度"""
        datasource = self.get_datasource(datasource_id)
        return datasource.dimensions if datasource else []
    
    def get_metric_options(self, datasource_id: str) -> List[Dict[str, str]]:
        """获取指标选项列表（用于前端下拉框）"""
        metrics = self.get_all_metrics(datasource_id)
        return [{"value": m.name, "label": m.name, "id": m.id} for m in metrics]
    
    def get_dimension_options(self, datasource_id: str) -> List[Dict[str, str]]:
        """获取维度选项列表（用于前端下拉框）"""
        dimensions = self.get_all_dimensions(datasource_id)
        return [{"value": d.name, "label": d.name, "id": d.id} for d in dimensions]
    
    def resolve_metric_field(self, datasource_id: str, metric_name: str) -> Optional[str]:
        """解析指标名称到字段名（用于SQL构建）"""
        metric = self.get_metric(datasource_id, metric_name)
        if not metric:
            return None
        
        # 根据聚合函数构建字段表达式
        if metric.agg == "COUNT":
            return f"COUNT({metric.field})"
        elif metric.agg == "COUNT_DISTINCT":
            return f"COUNT(DISTINCT {metric.field})"
        elif metric.agg == "SUM":
            return f"SUM({metric.field})"
        elif metric.agg == "AVG":
            return f"AVG({metric.field})"
        elif metric.agg == "MAX":
            return f"MAX({metric.field})"
        elif metric.agg == "MIN":
            return f"MIN({metric.field})"
        else:
            return metric.field
    
    def resolve_dimension_field(self, datasource_id: str, dimension_name: str) -> Optional[str]:
        """解析维度名称到字段名"""
        dimension = self.get_dimension(datasource_id, dimension_name)
        return dimension.field if dimension else None


# 全局实例
datasource_loader = DataSourceLoader()
