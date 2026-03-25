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
from .pattern_loader import PatternLoader
from .sql_builder import PatternSQLBuilder

logger = logging.getLogger(__name__)


class PatternHandler:
    """Pattern模式处理器 - 负责模板模式的全部处理流程"""

    def __init__(self, pattern_loader: PatternLoader, sql_builder: PatternSQLBuilder):
        self.pattern_loader = pattern_loader
        self.sql_builder = sql_builder

    async def process_with_pattern(
        self,
        conversation: Conversation,
        message: Message,
        intent_result: IntentAnalysisResult
    ) -> Optional[Dict[str, Any]]:
        """
        使用Pattern模式处理消息

        Args:
            conversation: 会话对象
            message: 当前消息
            intent_result: 意图分析结果

        Returns:
            处理结果字典
        """
        logger.info(f"[Pattern模式] 开始处理: {intent_result.matched_pattern}")

        try:
            await sse_manager.send_event(
                conversation.conversation_id,
                "pattern_processing_started",
                {
                    "pattern_id": intent_result.matched_pattern,
                    "pattern_name": intent_result.pattern_config.name if intent_result.pattern_config else "Unknown"
                }
            )

            # 检查pattern_config是否存在
            if not intent_result.pattern_config:
                logger.error(f"[Pattern模式] Pattern配置不存在: {intent_result.matched_pattern}")
                return {
                    "content": f"未找到Pattern配置: {intent_result.matched_pattern}，请重新选择模板或输入查询。",
                    "tools_used": [],
                    "metadata": {
                        "pattern_mode": True,
                        "pattern_id": intent_result.matched_pattern,
                        "mode": "template",
                        "error": "pattern_config_not_found"
                    }
                }

            # 需要澄清
            if intent_result.clarification_needed:
                return self._build_clarification_response(intent_result)

            # 获取参数
            params = intent_result.params or {}

            # 尝试使用默认值
            if not params:
                params = self._apply_defaults(params, intent_result.pattern_config.params_schema)

            # 构建SQL上下文
            sql_context = {
                "table_name": conversation.scene_code,
                "time_field": "created_at",
                "scene_code": conversation.scene_code,
                "params_schema": intent_result.pattern_config.params_schema or {}
            }

            # 构建SQL
            logger.info(f"[Pattern模式] 构建SQL, params: {params}")
            sql, error = await self.sql_builder.build(intent_result.matched_pattern, params, sql_context)

            if error:
                logger.error(f"[Pattern模式] SQL构建失败: {error}")
                return self._build_param_error_response(intent_result, params, error)

            logger.info(f"[Pattern模式] SQL构建成功: {sql}")

            response_text = self._format_sql_response(intent_result, params, sql)

            await sse_manager.send_event(
                conversation.conversation_id,
                "pattern_processing_completed",
                {
                    "pattern_id": intent_result.matched_pattern,
                    "sql": sql
                }
            )

            return {
                "content": response_text,
                "tools_used": [],
                "metadata": {
                    "pattern_mode": True,
                    "template_mode": True,
                    "pattern_id": intent_result.matched_pattern,
                    "pattern_name": intent_result.pattern_config.name,
                    "sql": sql,
                    "params": params,
                    "mode": "template"
                }
            }

        except Exception as e:
            logger.error(f"[Pattern模式] 处理失败: {e}", exc_info=True)
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
        pattern_id = template_data.get("pattern_id")

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

        # 根据Pattern类型显示不同提示
        pattern_config = self.pattern_loader.get_pattern(pattern_id)
        pattern_category = pattern_config.category if pattern_config else "unknown"
        response_lines.extend(self._get_category_hints(pattern_category))

        # 添加Pattern配置的user_prompt和important_notes
        if pattern_config and pattern_config.user_prompt:
            response_lines.append(f"💡 **使用说明**:")
            response_lines.append(f"{pattern_config.user_prompt}")
            response_lines.append(f"")

        if pattern_config and pattern_config.important_notes:
            response_lines.append(f"⚠️ **重要提示**:")
            for note in pattern_config.important_notes:
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
                "template_id": template_data.get("id"),
                "template_name": template_name,
                "pattern_id": pattern_id,
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

        if intent_result.params:
            clarification_text += "### 已识别的参数\n"
            for key, value in intent_result.params.items():
                clarification_text += f"- **{key}**: {value}\n"
            clarification_text += "\n"

        clarification_text += "### 需要补充的参数\n"
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
                "pattern_mode": True,
                "pattern_id": intent_result.matched_pattern,
                "needs_clarification": True,
                "clarification_questions": intent_result.clarification_questions,
                "params": intent_result.params,
                "mode": "template"
            }
        }

    def _build_param_error_response(self, intent_result: IntentAnalysisResult, params: dict, error: str) -> Dict[str, Any]:
        """构建参数错误响应（禁止降级，引导用户修正参数）"""
        pattern_config = intent_result.pattern_config
        params_schema = pattern_config.params_schema if pattern_config else {}

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
                "pattern_mode": True,
                "pattern_id": intent_result.matched_pattern,
                "needs_clarification": True,
                "error": error,
                "params": params,
                "mode": "template"
            }
        }

    def _format_sql_response(self, intent_result: IntentAnalysisResult, params: dict, sql: str) -> str:
        """格式化SQL响应"""
        response_lines = [
            f"## 🎯 模板模式: {intent_result.pattern_config.name}",
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
            params_schema = intent_result.pattern_config.params_schema or {}
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
