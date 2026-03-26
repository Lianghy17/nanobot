"""本文件已弃用 - 系统现在只使用 scenes.json 中的场景和模板配置

本文件中的 PatternLoader 类已被 SceneTemplateLoader 替代。
所有场景和模板配置现在统一从 config/scenes.json 加载。

如需访问场景和模板配置，请使用 SceneTemplateLoader:
    from chatbi.core.template_loader import SceneTemplateLoader
    
    template_loader = SceneTemplateLoader("config/scenes.json")
    template_config = template_loader.get_template("sales_point_query")
"""

import logging

logger = logging.getLogger(__name__)

logger.warning("[已弃用] pattern_loader.py 已被 SceneTemplateLoader 替代，请使用 template_loader.py")

