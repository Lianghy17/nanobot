"""意图分析器 - 分析用户意图并匹配Pattern"""
import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .pattern_loader import PatternLoader, PatternConfig
from ..models.llm import LLMResponse
from .llm_client import LLMClient
from ..config import chatbi_config

logger = logging.getLogger(__name__)


@dataclass
class IntentAnalysisResult:
    """意图分析结果"""
    # 用户意图类型
    intent_type: str  # "pattern_match" 或 "llm_react"
    
    # 匹配到的pattern(如果有)
    matched_pattern: Optional[str] = None
    pattern_config: Optional[PatternConfig] = None
    
    # confidence分数
    confidence: float = 0.0
    
    # 解析出的参数
    params: Dict[str, Any] = None
    
    # 需要澄清的问题(如果参数不完整)
    clarification_needed: bool = False
    clarification_questions: List[str] = None
    
    # 模式描述
    description: str = ""


class IntentAnalyzer:
    """意图分析器 - 使用LLM分析用户意图并匹配Pattern"""
    
    def __init__(self, llm_client: LLMClient, pattern_loader: PatternLoader):
        self.llm_client = llm_client
        self.pattern_loader = pattern_loader
    
    async def analyze(
        self, 
        user_query: str, 
        scene_code: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> IntentAnalysisResult:
        """
        分析用户意图
        
        Args:
            user_query: 用户查询
            scene_code: 场景代码
            context: 上下文信息
        
        Returns:
            IntentAnalysisResult: 意图分析结果
        """
        context = context or {}
        
        logger.info(f"{'='*80}")
        logger.info(f"[意图分析开始] ==================================================================")
        logger.info(f"[意图分析] 用户查询: {user_query}")
        logger.info(f"[意图分析] 场景代码: {scene_code}")
        logger.info(f"[意图分析] 续接模式: {context.get('continuing_pattern', False)}")
        if context.get('continuing_pattern'):
            pattern_context = context.get('pattern_context', {})
            logger.info(f"[意图分析] 上下文 - template_id: {pattern_context.get('template_id')}")
            logger.info(f"[意图分析] 上下文 - continuing_pattern: {pattern_context.get('continuing_pattern')}")
            logger.info(f"[意图分析] 上下文 - pattern_id: {pattern_context.get('pattern_id')}")

        # 获取场景支持的patterns
        supported_patterns = self._get_supported_patterns(scene_code)
        logger.info(f"[意图分析] 支持的patterns数量: {len(supported_patterns)}")
        if supported_patterns:
            logger.info(f"[意图分析] 可用patterns: {[p.id for p in supported_patterns[:5]]}...")

        # 如果是continuing_pattern模式，直接从上下文获取pattern_id
        if context.get('continuing_pattern'):
            pattern_context = context.get('pattern_context', {})

            # 尝试从不同位置获取pattern_id
            template_data = pattern_context.get('template_data', {})
            pattern_id = (
                template_data.get('pattern_id') or
                pattern_context.get('pattern_id') or
                pattern_context.get('matched_pattern')
            )

            if pattern_id:
                pattern_config = self.pattern_loader.get_pattern(pattern_id)
                if pattern_config:
                    logger.info(f"[意图分析] 续接模式，直接使用Pattern: {pattern_id}")
                    
                    # 获取已收集的参数（来自上一轮）
                    previous_params = pattern_context.get('previous_params', {})
                    logger.info(f"[意图分析] 已收集参数: {previous_params}")
                    
                    # 使用LLM提取参数
                    from .llm_client import LLMClient
                    llm = LLMClient(
                        api_base=chatbi_config.llm_api_base,
                        api_key=chatbi_config.llm_api_key,
                        model=chatbi_config.llm_model,
                        temperature=chatbi_config.llm_temperature,
                        max_tokens=chatbi_config.llm_max_tokens,
                        timeout=chatbi_config.llm_timeout,
                        thinking_disabled=chatbi_config.llm_thinking_disabled  # 必须传递，否则kimi-k2.5报错
                    )

                    # 构建参数提取prompt
                    params_schema = pattern_config.params_schema or {}
                    
                    # 构建已收集参数的提示
                    previous_params_hint = ""
                    if previous_params:
                        previous_params_hint = f"""
## 已收集的参数（请保留这些参数，除非用户新输入有覆盖）
{json.dumps(previous_params, ensure_ascii=False, indent=2)}
"""
                    
                    prompt = f"""你是一个参数提取专家。请从用户的输入中提取Pattern所需的参数，并与已收集的参数合并。

## 用户输入
{user_query}
{previous_params_hint}
## Pattern配置
Pattern ID: {pattern_id}
Pattern Name: {pattern_config.name}
Pattern Description: {pattern_config.description}

## 需要提取的参数
{json.dumps(params_schema, ensure_ascii=False, indent=2)}

## 任务
1. 从用户输入中提取新的参数值
2. 与已收集的参数合并（保留未覆盖的参数）
3. 判断是否还有缺少的必需参数

## 响应格式(严格JSON)
{{
    "params": {{"参数名": "值", ...}},  // 合并后的完整参数
    "clarification_needed": true|false,
    "clarification_questions": ["问题1", "问题2"] 或 [],
    "description": "参数提取说明"
}}

注意:
- 只返回JSON,不要有其他文字
- 必须返回合并后的完整参数（包括已收集的和新提取的）
- 只提取能确定的参数,不确定的不要填写
- 如果仍缺少必需参数,设置clarification_needed=true并提供clarification_questions
"""

                    try:
                        # 使用temperature=1.0避免模型不支持的问题
                        response = await llm.chat(
                            messages=[{"role": "user", "content": prompt}],
                            tools=None
                        )

                        import json_repair
                        response_text = response.content.strip()
                        if response_text.startswith("```"):
                            response_text = response_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

                        data = json_repair.loads(response_text)
                        params = data.get("params", {})
                        clarification_needed = data.get("clarification_needed", False)
                        clarification_questions = data.get("clarification_questions", [])

                        logger.info(f"[意图分析] 参数提取完成: {params}, 需要澄清: {clarification_needed}")

                        return IntentAnalysisResult(
                            intent_type="pattern_match",
                            matched_pattern=pattern_id,
                            pattern_config=pattern_config,
                            confidence=1.0,  # 续接模式默认高置信度
                            params=params,
                            clarification_needed=clarification_needed,
                            clarification_questions=clarification_questions,
                            description=f"续接Pattern模式，使用模板: {pattern_config.name}"
                        )

                    except Exception as e:
                        logger.error(f"[意图分析] 参数提取失败: {e}, 降级到返回空参数")
                        # 降级：返回空参数，让Pattern模式处理
                        return IntentAnalysisResult(
                            intent_type="pattern_match",
                            matched_pattern=pattern_id,
                            pattern_config=pattern_config,
                            confidence=1.0,
                            params={},
                            clarification_needed=False,
                            clarification_questions=[],
                            description="续接Pattern模式，参数提取失败，使用默认参数"
                        )
                else:
                    logger.warning(f"[意图分析] 续接模式但找不到Pattern配置: {pattern_id}")
            else:
                logger.warning(f"[意图分析] 续接模式但未找到pattern_id")
        
        # 使用RAG检索相关的QA示例和模板
        rag_context = ""
        try:
            from ..agent.tools import RAGTool
            rag_tool = RAGTool()
            
            # 使用RAG工具检索QA示例
            logger.info(f"[意图分析] 使用RAG检索相关QA示例...")
            rag_result = await rag_tool.execute(
                scene_code=scene_code or "sales_analysis",
                query=user_query,
                type="qa"  # 只检索QA示例
            )
            
            if rag_result.get("success") and rag_result.get("result"):
                qa_examples = rag_result["result"].get("qa_examples", [])
                if qa_examples:
                    logger.info(f"[意图分析] RAG检索到 {len(qa_examples)} 个相关QA示例")
                    rag_context = "\n\n## RAG检索到的相关QA示例\n"
                    for i, qa in enumerate(qa_examples[:3], 1):
                        rag_context += f"{i}. 问题: {qa.get('question', 'N/A')}\n"
                        rag_context += f"   模板: {qa.get('template_name', 'N/A')}\n"
                        rag_context += f"   Pattern: {qa.get('pattern_id', 'N/A')}\n\n"
        except Exception as e:
            logger.warning(f"[意图分析] RAG检索失败: {e}")
        
        # 构建分析prompt
        prompt = self._build_analysis_prompt(user_query, supported_patterns, context, rag_context)
        logger.info(f"[意图分析] Prompt长度: {len(prompt)} 字符")
        
        try:
            # 调用LLM进行意图分析
            logger.info(f"[意图分析] 调用LLM进行意图分析...")
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                tools=None
            )
            logger.info(f"[意图分析] LLM响应长度: {len(response.content)} 字符")
            
            # 解析LLM响应
            logger.info(f"[意图分析] 解析LLM响应...")
            result = self._parse_llm_response(response.content, supported_patterns, context)
            
            logger.info(f"[意图分析] ✓ 意图类型: {result.intent_type}")
            logger.info(f"[意图分析] ✓ 匹配Pattern: {result.matched_pattern}")
            logger.info(f"[意图分析] ✓ Pattern配置: {result.pattern_config.name if result.pattern_config else 'None'}")
            logger.info(f"[意图分析] ✓ 置信度: {result.confidence}")
            logger.info(f"[意图分析] ✓ 提取参数: {result.params}")
            logger.info(f"[意图分析] ✓ 需要澄清: {result.clarification_needed}")
            if result.clarification_needed:
                logger.info(f"[意图分析] ✓ 澄清问题数量: {len(result.clarification_questions)}")
                for i, q in enumerate(result.clarification_questions, 1):
                    logger.info(f"[意图分析]   - 问题{i}: {q}")
            
            logger.info(f"[意图分析] ✓ 描述: {result.description}")
            logger.info(f"[意图分析完成] ==================================================================")
            logger.info(f"{'='*80}")
            
            return result
            logger.info(f"[意图分析] pattern_config: {result.pattern_config.name if result.pattern_config else 'None'}")
            
            return result
            
        except Exception as e:
            logger.error(f"[意图分析] 失败: {e}", exc_info=True)
            # 降级到LLM React模式
            return IntentAnalysisResult(
                intent_type="llm_react",
                confidence=0.0,
                params={},
                description="无法确定Pattern,使用大模型React模式"
            )
    
    def _get_supported_patterns(self, scene_code: Optional[str]) -> List[PatternConfig]:
        """获取场景支持的patterns"""
        # TODO: 从场景配置中读取支持的patterns
        # 目前返回所有patterns
        return list(self.pattern_loader.get_all_patterns().values())
    
    def _build_analysis_prompt(
        self, 
        user_query: str, 
        supported_patterns: List[PatternConfig],
        context: Dict,
        rag_context: str = ""
    ) -> str:
        """构建意图分析prompt"""
        # 构建pattern列表描述
        pattern_descriptions = []
        for pattern in supported_patterns:
            desc = f"- {pattern.id} ({pattern.name}): {pattern.description}\n"
            desc += f"  类别: {pattern.category}, 复杂度: {pattern.complexity}\n"
            desc += f"  必需参数: {list(pattern.params_schema.keys())}\n"
            pattern_descriptions.append(desc)
        
        patterns_info = "\n".join(pattern_descriptions)
        
        # 检查是否正在继续Pattern模式
        continuing_pattern = context.get("continuing_pattern", False)
        pattern_context = context.get("pattern_context", {})
        
        continuation_hint = ""
        if continuing_pattern and pattern_context:
            # 尝试获取正确的pattern_id
            template_data = pattern_context.get("template_data", {})
            pattern_id = template_data.get("pattern_id") or pattern_context.get("pattern_id")
            pattern_name = pattern_context.get("pattern_name")
            
            continuation_hint = f"""
## 重要提示：继续Pattern模式
用户正在提供参数以完成之前的Pattern查询:
- Pattern ID: {pattern_id}
- Pattern名称: {pattern_name}

**关键要求**:
1. 必须返回 matched_pattern = "{pattern_id}"（这是真实的Pattern ID）
2. 不要返回template_id，必须返回pattern_id
3. 将此查询解析为pattern_match
4. 从用户输入中提取参数
"""
        
        prompt = f"""你是一个意图分析专家。请分析用户的查询,判断是使用预定义Pattern模板还是直接使用大模型React模式。

## 用户查询
{user_query}
{rag_context}
{continuation_hint}
## 可用的Pattern模板
{patterns_info}

## 分析任务
1. 确定用户的查询类型:
   - 如果查询匹配某个Pattern模板,返回intent_type="pattern_match"
   - 如果查询复杂、模糊或不匹配任何模板,返回intent_type="llm_react"

2. 如果匹配Pattern,请提取参数:
   - matched_pattern: 匹配的pattern_id
   - params: 从查询中提取的参数
   - confidence: 匹配置信度(0-1)
   - clarification_needed: 是否需要向用户澄清缺少的参数
   - clarification_questions: 需要澄清的问题列表

3. 如果使用LLM React模式:
   - intent_type="llm_react"
   - confidence=0.0
   - description: 说明原因

## 响应格式(严格JSON)
{{
    "intent_type": "pattern_match" | "llm_react",
    "matched_pattern": "pattern_id或null",
    "confidence": 0.0-1.0,
    "params": {{"参数名": "值", ...}} 或 {{}},
    "clarification_needed": true|false,
    "clarification_questions": ["问题1", "问题2"] 或 [],
    "description": "分析说明"
}}

注意:
- 只返回JSON,不要有其他文字
- 如果clarification_needed=true,需要提供clarification_questions
- params中只包含能确定的参数,不确定的不要填写
- 参考RAG检索到的QA示例来提高匹配准确度
"""
        return prompt
    
    def _parse_llm_response(
        self, 
        llm_response: str, 
        supported_patterns: List[PatternConfig],
        context: Dict = None
    ) -> IntentAnalysisResult:
        """解析LLM响应
        
        Args:
            llm_response: LLM响应内容
            supported_patterns: 支持的pattern列表
            context: 上下文信息（用于续接Pattern模式）
        """
        if context is None:
            context = {}
        
        try:
            import json_repair
            
            # 提取JSON(处理markdown代码块)
            response_text = llm_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            # 使用json_repair解析
            data = json_repair.loads(response_text)
            
            intent_type = data.get("intent_type", "llm_react")
            matched_pattern_id = data.get("matched_pattern")
            confidence = data.get("confidence", 0.0)
            params = data.get("params", {})
            clarification_needed = data.get("clarification_needed", False)
            clarification_questions = data.get("clarification_questions", [])
            description = data.get("description", "")
            
            # 获取pattern配置
            pattern_config = None
            if matched_pattern_id and intent_type == "pattern_match":
                # 先尝试直接获取pattern
                pattern_config = self.pattern_loader.get_pattern(matched_pattern_id)
                
                # 如果找不到，检查是否是续接Pattern模式，尝试从template_id映射
                if not pattern_config and context.get("continuing_pattern"):
                    pattern_context = context.get("pattern_context", {})
                    template_data = pattern_context.get("template_data", {})
                    real_pattern_id = template_data.get("pattern_id")
                    
                    if real_pattern_id:
                        logger.info(f"[意图分析] LLM返回了template_id({matched_pattern_id}), 修正为pattern_id({real_pattern_id})")
                        matched_pattern_id = real_pattern_id
                        pattern_config = self.pattern_loader.get_pattern(real_pattern_id)
                
                logger.info(f"[意图分析] 尝试获取pattern: {matched_pattern_id}, 找到: {pattern_config is not None}")
                if not pattern_config:
                    logger.warning(f"[意图分析] 找不到pattern配置: {matched_pattern_id}, 可用patterns: {list(self.pattern_loader.get_all_patterns().keys())[:5]}...")
            
            return IntentAnalysisResult(
                intent_type=intent_type,
                matched_pattern=matched_pattern_id,
                pattern_config=pattern_config,
                confidence=confidence,
                params=params,
                clarification_needed=clarification_needed,
                clarification_questions=clarification_questions,
                description=description
            )
            
        except Exception as e:
            logger.error(f"[意图分析] 解析响应失败: {e}, 响应: {llm_response[:500]}")
            # 降级到LLM React模式
            return IntentAnalysisResult(
                intent_type="llm_react",
                confidence=0.0,
                params={},
                description="响应解析失败,使用大模型React模式"
            )
    
    def complete_params(
        self, 
        pattern_id: str, 
        user_clarification: str
    ) -> Dict[str, Any]:
        """
        根据用户澄清完善参数
        
        Args:
            pattern_id: Pattern ID
            user_clarification: 用户澄清信息
        
        Returns:
            完善后的参数
        """
        # 这里可以调用LLM从用户澄清中提取参数
        # 简化实现: 直接返回空字典,实际应该在AgentWrapper中处理
        return {}
