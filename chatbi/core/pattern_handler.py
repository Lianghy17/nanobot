"""Pattern模式处理器 - 模板模式的所有处理逻辑"""
import json
import random
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ..config import chatbi_config
from ..models import Conversation, Message
from .sse_manager import sse_manager
from .intent_analyzer import IntentAnalysisResult
from .template_loader import SceneTemplateLoader, TemplateConfig
from .sql_builder import PatternSQLBuilder
from .datasource_loader import datasource_loader

logger = logging.getLogger(__name__)


class PatternHandler:
    """Pattern模式处理器 - 负责模板模式的全部处理流程"""

    def __init__(self, template_loader: SceneTemplateLoader, sql_builder: PatternSQLBuilder):
        self.template_loader = template_loader
        self.sql_builder = sql_builder

    async def process_with_pattern(
        self,
        conversation: Conversation,
        message: Message,
        intent_result: IntentAnalysisResult
    ) -> Optional[Dict[str, Any]]:
        """
        使用Template模式处理消息

        ⚠️ **硬编码逻辑**：
        1. 当前系统没有真实数据库，execute_sql 是假的
        2. Template模式只生成SQL，不执行SQL
        3. 返回生成的SQL语句给用户查看
        4. 如果用户想要执行SQL，需要切换到React模式或手动执行

        Args:
            conversation: 会话对象
            message: 当前消息
            intent_result: 意图分析结果

        Returns:
            处理结果字典（包含生成的SQL语句）
        """
        logger.info(f"[Template模式] 开始处理: {intent_result.matched_template}")

        try:
            await sse_manager.send_event(
                conversation.conversation_id,
                "template_processing_started",
                {
                    "template_id": intent_result.matched_template,
                    "template_name": intent_result.template_config.name if intent_result.template_config else "Unknown"
                }
            )

            # 检查template_config是否存在
            if not intent_result.template_config:
                logger.error(f"[Template模式] Template配置不存在: {intent_result.matched_template}")
                return {
                    "content": f"未找到Template配置: {intent_result.matched_template}，请重新选择模板或输入查询。",
                    "tools_used": [],
                    "metadata": {
                        "template_mode": True,
                        "template_id": intent_result.matched_template,
                        "mode": "template",
                        "error": "template_config_not_found"
                    }
                }

            # 需要澄清
            if intent_result.clarification_needed:
                return self._build_clarification_response(intent_result)

            # 获取参数
            params = intent_result.params or {}

            # 尝试使用默认值
            if not params:
                params = self._apply_defaults(params, intent_result.template_config.params_schema)

            # 构建SQL上下文（优先从 datasource 配置获取正确的表名和时间字段）
            template_datasource = intent_result.template_config.datasource
            ds_config = datasource_loader.get_datasource(template_datasource) if template_datasource else None
            
            sql_context = {
                "table_name": ds_config.table_name if ds_config else conversation.scene_code,
                "time_field": ds_config.time_field if ds_config else "created_at",
                "datasource_id": template_datasource,
                "scene_code": conversation.scene_code,
                "params_schema": intent_result.template_config.params_schema or {}
            }
            
            if ds_config:
                logger.info(f"[Template模式] datasource配置: table={ds_config.table_name}, time_field={ds_config.time_field}, metrics={len(ds_config.metrics)}")

            # 🎯 硬编码逻辑：只生成SQL，不执行SQL
            # 原因：当前系统没有真实数据库，execute_sql 是假的
            logger.info(f"[Template模式] 🎯 构建SQL（不执行SQL）, params: {params}")
            sql, error = await self.sql_builder.build(intent_result.matched_template, params, sql_context)

            if error:
                logger.error(f"[Template模式] SQL构建失败: {error}")
                return self._build_param_error_response(intent_result, params, error)

            logger.info(f"[Template模式] ✅ SQL构建成功（已生成，未执行）: {sql}")

            # 格式化SQL响应（显示SQL语句，但不执行）
            response_text = self._format_sql_response(intent_result, params, sql)

            await sse_manager.send_event(
                conversation.conversation_id,
                "template_processing_completed",
                {
                    "template_id": intent_result.matched_template,
                    "sql": sql,
                    "executed": False  # 硬编码：未执行SQL
                }
            )

            return {
                "content": response_text,
                "tools_used": [],
                "metadata": {
                    "template_mode": True,
                    "template_id": intent_result.matched_template,
                    "template_name": intent_result.template_config.name,
                    "sql": sql,
                    "params": params,
                    "mode": "template",
                    "executed": False  # 硬编码：未执行SQL
                }
            }

        except Exception as e:
            logger.error(f"[Template模式] 处理失败: {e}", exc_info=True)
            raise

    async def guide_template_params(
        self,
        conversation: Conversation,
        message: Message,
        template_data: dict
    ) -> Optional[Dict[str, Any]]:
        """引导用户填写模板参数"""
        logger.info(f"[模板参数引导] 模板: {template_data.get('name')}")

        template_name = template_data.get("name", "未命名模板")
        template_description = template_data.get("description", "")
        params_schema = template_data.get("params_schema", {})
        template_id = template_data.get("template_id")

        response_lines = [
            f"## 📋 模板模式: {template_name}",
            f"",
            f"{template_description}",
            f"",
            f"为了完成分析，请提供以下参数：",
            f""
        ]

        # 按必需和可选分组
        required_params = []
        optional_params = []
        for param_name, param_config in params_schema.items():
            param_info = {
                "name": param_name,
                "label": param_config.get("label", param_name),
                "type": param_config.get("type", "text"),
                "required": param_config.get("required", False),
                "default": param_config.get("default"),
                "options": param_config.get("options", []),
            }
            if param_config.get("required", False):
                required_params.append(param_info)
            else:
                optional_params.append(param_info)

        if required_params:
            response_lines.append(f"### 必填参数")
            response_lines.extend(self._format_param_list(required_params))

        if optional_params:
            response_lines.append(f"### 可选参数")
            response_lines.extend(self._format_param_list(optional_params))

        response_lines.append(f"---")

        # 添加Template配置的user_prompt和important_notes
        template_config = self.template_loader.get_template(template_id)
        if template_config and template_config.user_prompt:
            response_lines.append(f"💡 **使用说明**:")
            response_lines.append(f"{template_config.user_prompt}")
            response_lines.append(f"")

        if template_config and template_config.important_notes:
            response_lines.append(f"⚠️ **重要提示**:")
            for note in template_config.important_notes:
                response_lines.append(f"- {note}")
            response_lines.append(f"")
        else:
            # 如果没有配置，使用默认提示
            response_lines.append(f"⚠️ **重要提示**:")
            response_lines.append(f"- 趋势分析需要：时间范围 + 时间粒度 + 指标")
            response_lines.append(f"- 维度分析需要：时间点（如本月/昨天）+ 维度 + 指标")
            response_lines.append(f"- 请勿在一次查询中混合不同类型的分析需求")
            response_lines.append(f"")
            response_lines.append(f"系统会自动将您的中文参数转换为对应的SQL条件。")

        logger.info(f"[模板参数引导] 引导文本生成完成")

        return {
            "content": "\n".join(response_lines),
            "tools_used": [],
            "metadata": {
                "template_mode": True,
                "template_id": template_data.get("id") or template_data.get("template_id"),
                "template_name": template_name,
                "params_schema": params_schema,
                "mode": "template"
            }
        }

    def build_clarification_from_intent(self, intent_result: IntentAnalysisResult) -> Dict[str, Any]:
        """从意图分析结果构建澄清响应"""
        return self._build_clarification_response(intent_result)

    # ========== 私有方法 ==========

    def _build_clarification_response(self, intent_result: IntentAnalysisResult) -> Dict[str, Any]:
        """构建澄清响应"""
        clarification_text = "## 🤔 需要更多信息\n\n"
        clarification_text += "为了准确生成查询，请补充以下信息：\n\n"

        # 获取缺失的必需参数
        missing_params = []
        if intent_result.template_config and intent_result.template_config.params_schema:
            params_schema = intent_result.template_config.params_schema
            for param_name, param_config in params_schema.items():
                if param_config.get("required", False) and param_name not in (intent_result.params or {}):
                    missing_params.append({
                        "name": param_name,
                        "label": param_config.get("label", param_name),
                        "type": param_config.get("type", "string"),
                        "options": param_config.get("options", []),
                        "default": param_config.get("default")
                    })

        if intent_result.params:
            clarification_text += "### 已识别的参数\n"
            for key, value in intent_result.params.items():
                clarification_text += f"- **{key}**: {value}\n"
            clarification_text += "\n"

        clarification_text += "### 需要补充的参数\n"
        if missing_params:
            for param in missing_params:
                line = f"- **{param['label']}**"
                if param.get('options'):
                    options = [f"`{opt.get('label', opt.get('value', opt))}`" if isinstance(opt, dict) else f"`{opt}`" 
                             for opt in param['options']]
                    line += f" - 可选: {', '.join(options)}"
                if param.get('default'):
                    line += f" - 默认: `{param['default']}`"
                clarification_text += f"{line}\n"
        elif intent_result.clarification_questions:
            for i, q in enumerate(intent_result.clarification_questions, 1):
                clarification_text += f"{i}. {q}\n"

        clarification_text += "\n---\n"
        clarification_text += "💡 您可以直接告诉我缺失的参数，例如：\n"
        clarification_text += "- '指标是销售额'\n"
        clarification_text += "- '查看产品维度的数据'\n"
        clarification_text += "- '指标是订单量，按产品类别分组'\n"

        return {
            "content": clarification_text,
            "tools_used": [],
            "metadata": {
                "template_mode": True,
                "template_id": intent_result.matched_template,
                "needs_clarification": True,
                "clarification_questions": intent_result.clarification_questions,
                "missing_params": missing_params,
                "params": intent_result.params,
                "allow_fallback_to_react": True,  # 允许降级到React模式
                "mode": "template"
            }
        }

    def _build_param_error_response(self, intent_result: IntentAnalysisResult, params: dict, error: str) -> Dict[str, Any]:
        """构建参数错误响应（禁止降级，引导用户修正参数）"""
        template_config = intent_result.template_config
        params_schema = template_config.params_schema if template_config else {}

        error_text = "## ❌ 参数有误，请修正\n\n"
        error_text += f"**错误原因**: {error}\n\n"

        if params:
            error_text += "### 您当前提供的参数\n"
            for key, value in params.items():
                param_label = params_schema[key].get("label", key) if key in params_schema else key
                error_text += f"- **{param_label}**: `{value}`\n"
            error_text += "\n"

        error_text += "### 该模板接受的参数\n"
        for key, schema in params_schema.items():
            label = schema.get("label", key)
            param_type = schema.get("type", "string")
            required = schema.get("required", False)
            required_mark = "（必填）" if required else "（可选）"

            line = f"- **{label}** ({param_type}{required_mark})"
            if "options" in schema:
                options_display = []
                for opt in schema["options"]:
                    if isinstance(opt, dict):
                        options_display.append(f"`{opt.get('label', opt.get('value'))}`")
                    else:
                        options_display.append(f"`{opt}`")
                line += f" - 可选: {', '.join(options_display)}"
            if "default" in schema:
                line += f" - 默认: `{schema['default']}`"
            error_text += f"{line}\n"

        error_text += "\n---\n"
        error_text += "💡 请重新输入正确的参数值，例如：\n"
        error_text += "- '指标是销售额，时间粒度是日，时间范围是最近30天'\n"

        return {
            "content": error_text,
            "tools_used": [],
            "metadata": {
                "template_mode": True,
                "template_id": intent_result.matched_template,
                "needs_clarification": True,
                "error": error,
                "params": params,
                "mode": "template"
            }
        }

    def _format_sql_response(self, intent_result: IntentAnalysisResult, params: dict, sql: str) -> str:
        """格式化SQL响应"""
        response_lines = [
            f"## 🎯 模板模式: {intent_result.template_config.name}",
            f"",
            f"已为您生成SQL查询语句：",
            f"",
            f"```sql",
            f"{sql}",
            f"```",
            f"",
            f"### 参数说明",
            f""
        ]

        if params:
            params_schema = intent_result.template_config.params_schema or {}
            for key, value in params.items():
                label = params_schema[key].get("label", key) if key in params_schema else key
                response_lines.append(f"- **{label}**: `{value}`")
        else:
            response_lines.append("- 未指定参数，使用默认值")

        response_lines.append(f"")
        response_lines.append(f"💡 **提示**: 此SQL已根据您选择的模板和参数生成，您可以直接在数据库中执行此查询。")
        return "\n".join(response_lines)

    def _apply_defaults(self, params: dict, params_schema: dict) -> dict:
        """从params_schema中应用默认值"""
        if not params_schema:
            return params
        logger.info("[Pattern模式] 参数为空，使用默认值")
        for param_name, param_config in params_schema.items():
            if 'default' in param_config:
                params[param_name] = param_config['default']
                logger.info(f"[Pattern模式] 使用默认参数: {param_name} = {param_config['default']}")
        return params

    def _format_param_list(self, params: list) -> list:
        """格式化参数列表为文本行"""
        lines = []
        for param in params:
            lines.append(f"- **{param['label']}** ({param['type']})")
            if param['default'] is not None:
                lines.append(f"  - 默认值: `{param['default']}`")
            if param['options']:
                options_text = ", ".join([
                    f"`{opt.get('label', opt.get('value', opt))}`"
                    if isinstance(opt, dict)
                    else f"`{opt}`"
                    for opt in param['options']
                ])
                lines.append(f"  - 可选值: {options_text}")
            lines.append(f"")
        return lines

    def _get_category_hints(self, pattern_category: str) -> list:
        """根据Pattern分类获取提示信息"""
        if pattern_category == "time_series":
            return [
                f"📊 **时间序列分析模板**",
                f"此模板需要指定时间范围和时间粒度来查看趋势。",
                f"",
                f"💡 **示例输入**:",
                f"- '时间范围是最近30天，指标是销售额，时间粒度是日'",
                f"- '指标是订单量，时间范围是今年，时间粒度是月'",
                f""
            ]
        elif pattern_category in ["dimensional", "basic"]:
            return [
                f"📈 **维度分析模板**",
                f"此模板需要指定时间点（不是时间范围）来查看特定时刻的数据。",
                f"",
                f"💡 **示例输入**:",
                f"- '本月销售额Top 10的产品'",
                f"- '按产品类别查看销售额分布'",
                f""
            ]
        else:
            return [
                f"💡 **提示**: 您可以直接用中文告诉我参数值，例如：",
                f"- '时间范围是最近30天'",
                f"- '指标是销售额'",
                f"- '时间粒度是日'",
            ]
