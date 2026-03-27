"""参数映射器 - 使用LLM + 配置规则将自然语言参数值转换为SQL可用的值"""
import json
import logging
from typing import Dict, Any, Optional
from ..config import chatbi_config
from .llm_client import LLMClient

logger = logging.getLogger(__name__)

# 参数映射的系统提示词
SYSTEM_PROMPT = """你是一个专业的数据分析参数映射助手。你的任务是将用户输入的自然语言参数值转换为数据库和SQL可用的标准值。

## 工作原则
1. 严格按照配置中定义的映射规则和示例进行转换
2. 对于配置中未明确列出的值，根据规律合理推断
3. 如果无法确定映射，保留原始值并标注 uncertainty
4. metric 和 dimension 类参数使用 snake_case 英文命名
5. 时间类参数使用 MySQL 兼容的 SQL 表达式
6. 枚举类参数只能输出配置中允许的值

## 输出要求
- 只返回 JSON，不要包含任何其他文字说明
- JSON 格式: {"mapped_params": {"参数名": "映射后的值", ...}, "notes": {"参数名": "映射说明", ...}}
- 无法映射的参数设为 null，并在 notes 中说明
"""


class ParamMapper:
    """参数映射器 - 使用LLM进行参数映射"""

    def __init__(self):
        self._llm_client: Optional[LLMClient] = None
        self._rules = chatbi_config.param_mapper_rules
        self._enabled = chatbi_config.param_mapper_enabled

    def _get_llm_client(self) -> LLMClient:
        """延迟初始化LLM客户端"""
        if self._llm_client is None:
            # 优先使用param_mapper配置的api_base和api_key
            param_config = chatbi_config.param_mapper_config
            api_base = param_config.get("api_base", chatbi_config.llm_api_base)
            api_key = param_config.get("api_key", chatbi_config.llm_api_key)

            self._llm_client = LLMClient(
                api_base=api_base,
                api_key=api_key,
                model=chatbi_config.param_mapper_model,
                temperature=chatbi_config.param_mapper_temperature,
                max_tokens=chatbi_config.param_mapper_max_tokens,
                timeout=chatbi_config.param_mapper_timeout,
                thinking_disabled=chatbi_config.param_mapper_thinking_disabled
            )
            logger.info(
                f"[参数映射] LLM客户端初始化: model={chatbi_config.param_mapper_model}, "
                f"api_base={api_base}, temperature={chatbi_config.param_mapper_temperature}"
            )
        return self._llm_client

    def _build_user_prompt(
        self,
        params: Dict[str, Any],
        params_schema: Dict[str, Any]
    ) -> str:
        """构建用户提示词"""
        # 构建参数映射规则部分
        rules_text = "## 参数映射规则\n\n"
        for param_name, param_value in params.items():
            if param_value is None:
                continue

            # 获取该参数类型的映射规则
            rule = self._rules.get(param_name, None)

            # 如果是 enum 类型，添加约束
            schema_info = params_schema.get(param_name, {})

            rules_text += f"### 参数: {param_name}\n"
            rules_text += f"- 原始值: `{json.dumps(param_value, ensure_ascii=False)}`\n"

            if rule:
                rules_text += f"- 说明: {rule['description']}\n"
                if "allowed_values" in rule:
                    rules_text += f"- 允许的值: {json.dumps(rule['allowed_values'])}\n"
                if "output_format" in rule:
                    rules_text += f"- 输出格式: {rule['output_format']}\n"
                if "examples" in rule:
                    rules_text += "- 映射示例:\n"
                    for k, v in rule["examples"].items():
                        rules_text += f"  - `{k}` → `{json.dumps(v, ensure_ascii=False)}`\n"

            if schema_info:
                if "type" in schema_info:
                    rules_text += f"- 参数类型: {schema_info['type']}\n"
                if "options" in schema_info:
                    rules_text += f"- 可选值: {json.dumps(schema_info['options'])}\n"
                if "default" in schema_info:
                    rules_text += f"- 默认值: {json.dumps(schema_info['default'])}\n"

            rules_text += "\n"

        return rules_text

    async def map_params(
        self,
        template_id: str,
        params: Dict[str, Any],
        scene_code: str,
        context: Optional[Dict] = None
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """
        使用LLM映射参数值

        Args:
            template_id: Template ID
            params: 原始参数（可能包含中文值）
            scene_code: 场景代码
            context: 上下文信息（可包含 template 的 params_schema）

        Returns:
            (mapped_params, error_message)
        """
        if not params:
            return {}, None

        # 过滤掉 None 值
        params_to_map = {k: v for k, v in params.items() if v is not None}
        if not params_to_map:
            return params, None

        if not self._enabled:
            logger.info("[参数映射] LLM映射已禁用，跳过映射")
            return params, None

        # 检测多值参数（逗号/顿号分隔），跳过LLM映射
        # 多值参数（如多指标）由SQL构建器的 field_mapping 处理中文→SQL映射
        multi_value_separators = [',', '，', '、']
        params_for_llm = {}
        skipped_multi = []

        for key, value in params_to_map.items():
            if isinstance(value, str) and any(sep in value for sep in multi_value_separators):
                skipped_multi.append(key)
            else:
                params_for_llm[key] = value

        if skipped_multi:
            logger.info(f"[参数映射] 跳过多值参数（由SQL构建器field_mapping处理）: {skipped_multi}")

        if not params_for_llm:
            logger.info("[参数映射] 所有参数均为多值，跳过LLM映射")
            return params, None

        # 获取 params_schema（从 context 或 template 配置中）
        params_schema = {}
        if context and "params_schema" in context:
            params_schema = context["params_schema"]

        # 构建 prompt（使用过滤后的参数）
        user_prompt = self._build_user_prompt(params_for_llm, params_schema)

        logger.info(f"[参数映射] 开始LLM映射, template={template_id}, params={list(params_for_llm.keys())}")
        logger.info(f"[参数映射] 使用模型: {chatbi_config.param_mapper_model}")
        logger.info(f"[参数映射] Prompt长度: {len(user_prompt)} 字符")
        logger.debug(f"[参数映射] Prompt:\n{user_prompt}")

        try:
            llm = self._get_llm_client()
            response = await llm.chat(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=chatbi_config.param_mapper_temperature,
                max_tokens=chatbi_config.param_mapper_max_tokens
            )

            # 解析响应
            response_text = response.content.strip()
            # 去除可能的 markdown code block
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            # 使用 json_repair 处理不规范的 JSON
            import json_repair
            result = json_repair.loads(response_text)

            mapped_params = result.get("mapped_params", {})
            notes = result.get("notes", {})

            # 将映射结果合并回原始 params（保留未映射的和跳过的多值参数）
            final_params = {}
            for key, value in params.items():
                if value is None:
                    final_params[key] = value
                elif key in skipped_multi:
                    # 跳过的多值参数保留原始值
                    final_params[key] = value
                elif key in mapped_params and mapped_params[key] is not None:
                    final_params[key] = mapped_params[key]
                else:
                    final_params[key] = value

            # 日志记录映射详情
            for key in params_for_llm:
                old_val = params_for_llm[key]
                new_val = final_params.get(key, old_val)
                note = notes.get(key, "")
                if old_val != new_val:
                    logger.info(f"[参数映射] {key}: {old_val} -> {new_val} {note}")
                else:
                    logger.info(f"[参数映射] {key}: {old_val} (未变化) {note}")

            return final_params, None

        except json_repair.JSONDecodeError as e:
            logger.warning(f"[参数映射] JSON解析失败: {e}, response: {response_text[:200]}")
            return params, f"参数映射JSON解析失败: {e}"

        except Exception as e:
            logger.error(f"[参数映射] LLM映射异常: {e}", exc_info=True)
            # 返回原始参数，不阻断流程
            return params, f"参数映射失败: {e}"


# 全局单例
_param_mapper_instance: Optional[ParamMapper] = None


def get_param_mapper() -> ParamMapper:
    """获取参数映射器单例"""
    global _param_mapper_instance
    if _param_mapper_instance is None:
        _param_mapper_instance = ParamMapper()
    return _param_mapper_instance
