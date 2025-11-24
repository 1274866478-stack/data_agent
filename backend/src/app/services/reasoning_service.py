"""
推理引擎服务
实现查询理解、答案生成、质量控制等功能
"""

import logging
import json
import re
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from src.app.services.zhipu_client import zhipu_service
from src.app.services.llm_service import llm_service, LLMMessage

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """查询类型枚举"""
    FACTUAL = "factual"  # 事实查询
    ANALYTICAL = "analytical"  # 分析查询
    COMPARATIVE = "comparative"  # 比较查询
    TEMPORAL = "temporal"  # 时间相关查询
    CAUSAL = "causal"  # 因果关系查询
    PROCEDURAL = "procedural"  # 流程查询
    PREDICTIVE = "predictive"  # 预测查询
    UNKNOWN = "unknown"


class ReasoningMode(Enum):
    """推理模式枚举"""
    BASIC = "basic"  # 基础推理
    ANALYTICAL = "analytical"  # 分析推理
    STEP_BY_STEP = "step_by_step"  # 逐步推理
    MULTI_SOURCE = "multi_source"  # 多源推理
    CONTEXT_AWARE = "context_aware"  # 上下文感知推理


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    original_query: str
    query_type: QueryType
    intent: str
    entities: List[str]
    keywords: List[str]
    temporal_expressions: List[str]
    complexity_score: float
    confidence: float
    reasoning_mode: ReasoningMode
    suggested_temperature: float
    suggested_max_tokens: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_number: int
    description: str
    reasoning: str
    evidence: List[str]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReasoningResult:
    """推理结果"""
    answer: str
    reasoning_steps: List[ReasoningStep]
    confidence: float
    sources: List[Dict[str, Any]]
    query_analysis: QueryAnalysis
    quality_score: float
    safety_filter_triggered: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryUnderstandingEngine:
    """查询理解引擎"""

    def __init__(self):
        self.intent_patterns = {
            QueryType.FACTUAL: [
                r"什么是", r"定义", r"解释", r"谁", r"哪里", r"何时", r"多少"
            ],
            QueryType.ANALYTICAL: [
                r"分析", r"评估", r"检查", r"研究", r"探讨"
            ],
            QueryType.COMPARATIVE: [
                r"比较", r"对比", r"差异", r"优缺点", r"哪个更好", r"区别"
            ],
            QueryType.TEMPORAL: [
                r"趋势", r"变化", r"增长", r"下降", r"历史", r"预测", r"时间"
            ],
            QueryType.CAUSAL: [
                r"为什么", r"原因", r"导致", r"影响", r"后果"
            ],
            QueryType.PROCEDURAL: [
                r"如何", r"怎么", r"步骤", r"流程", r"方法", r"操作"
            ],
            QueryType.PREDICTIVE: [
                r"预测", r"预期", r"未来", r"可能", r"将会"
            ]
        }

        self.complexity_indicators = [
            "分析", "比较", "评估", "影响", "原因", "结果",
            "趋势", "关系", "模式", "策略", "方案"
        ]

    async def analyze_query(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> QueryAnalysis:
        """
        分析查询

        Args:
            query: 用户查询
            context: 上下文信息

        Returns:
            查询分析结果
        """
        try:
            logger.info(f"开始分析查询: {query[:100]}...")

            # 基础文本分析
            query_type = self._classify_query_type(query)
            intent = self._extract_intent(query)
            entities = self._extract_entities(query)
            keywords = self._extract_keywords(query)
            temporal_expressions = self._extract_temporal_expressions(query)

            # 复杂度评估
            complexity_score = self._calculate_complexity(query, entities, keywords)
            confidence = self._calculate_confidence(query, query_type)

            # 推理模式建议
            reasoning_mode = self._suggest_reasoning_mode(query_type, complexity_score)
            suggested_temperature = self._suggest_temperature(complexity_score)
            suggested_max_tokens = self._suggest_max_tokens(complexity_score)

            analysis = QueryAnalysis(
                original_query=query,
                query_type=query_type,
                intent=intent,
                entities=entities,
                keywords=keywords,
                temporal_expressions=temporal_expressions,
                complexity_score=complexity_score,
                confidence=confidence,
                reasoning_mode=reasoning_mode,
                suggested_temperature=suggested_temperature,
                suggested_max_tokens=suggested_max_tokens
            )

            logger.info(f"查询分析完成: 类型={query_type.value}, 复杂度={complexity_score:.2f}")
            return analysis

        except Exception as e:
            logger.error(f"查询分析失败: {e}")
            # 返回默认分析结果
            return QueryAnalysis(
                original_query=query,
                query_type=QueryType.UNKNOWN,
                intent="未知意图",
                entities=[],
                keywords=[],
                temporal_expressions=[],
                complexity_score=0.5,
                confidence=0.5,
                reasoning_mode=ReasoningMode.BASIC,
                suggested_temperature=0.7,
                suggested_max_tokens=1000
            )

    def _classify_query_type(self, query: str) -> QueryType:
        """分类查询类型"""
        query_lower = query.lower()

        # 计算每种类型的匹配分数
        type_scores = {}
        for query_type, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if re.search(pattern, query_lower))
            type_scores[query_type] = score

        # 返回得分最高的类型
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] > 0:
                return best_type

        return QueryType.UNKNOWN

    def _extract_intent(self, query: str) -> str:
        """提取用户意图"""
        # 简化的意图提取逻辑
        if "什么是" in query or "定义" in query:
            return "寻求定义或解释"
        elif "如何" in query or "怎么" in query:
            return "寻求方法或流程"
        elif "为什么" in query or "原因" in query:
            return "寻求原因或解释"
        elif "比较" in query or "对比" in query:
            return "寻求比较分析"
        elif "分析" in query or "评估" in query:
            return "寻求分析评估"
        else:
            return "一般信息查询"

    def _extract_entities(self, query: str) -> List[str]:
        """提取实体"""
        # 简化的实体提取，实际应用中可以使用NER模型
        # 提取数字、日期、专有名词等
        entities = []

        # 提取数字
        numbers = re.findall(r'\d+(?:\.\d+)?', query)
        entities.extend([f"数字:{num}" for num in numbers])

        # 提取日期时间
        dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}', query)
        entities.extend([f"日期:{date}" for date in dates])

        # 提取引号中的内容（可能是专有名词）
        quoted = re.findall(r'["\"]([^"\"]+)["\"]', query)
        entities.extend(quoted)

        return entities

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        # 移除停用词，提取有意义的词汇
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}

        # 分词（简化版，实际应使用专业分词器）
        words = re.findall(r'[\w]+', query)
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]

        return keywords[:10]  # 限制关键词数量

    def _extract_temporal_expressions(self, query: str) -> List[str]:
        """提取时间表达式"""
        temporal_patterns = [
            r'\d{4}年',
            r'\d{1,2}月',
            r'\d{1,2}日',
            r'昨天|今天|明天',
            r'上周|本周|下周',
            r'上个月|这个月|下个月',
            r'去年|今年|明年',
            r'最近|近期|目前',
            r'过去|未来',
            r'春天|夏天|秋天|冬天'
        ]

        expressions = []
        for pattern in temporal_patterns:
            matches = re.findall(pattern, query)
            expressions.extend(matches)

        return expressions

    def _calculate_complexity(self, query: str, entities: List[str], keywords: List[str]) -> float:
        """计算查询复杂度"""
        complexity = 0.0

        # 基于长度
        length_score = min(len(query) / 200, 1.0) * 0.2
        complexity += length_score

        # 基于实体数量
        entity_score = min(len(entities) / 5, 1.0) * 0.2
        complexity += entity_score

        # 基于复杂度指示词
        complex_word_count = sum(1 for word in self.complexity_indicators if word in query)
        complexity_score = min(complex_word_count / 3, 1.0) * 0.4
        complexity += complexity_score

        # 基于句子结构（问号数量、逗号数量等）
        question_marks = query.count('?') + query.count('？')
        structure_score = min(question_marks / 2, 1.0) * 0.2
        complexity += structure_score

        return min(complexity, 1.0)

    def _calculate_confidence(self, query: str, query_type: QueryType) -> float:
        """计算分析置信度"""
        if query_type == QueryType.UNKNOWN:
            return 0.3

        # 基于查询清晰度
        confidence = 0.7

        # 如果查询包含明确的问题词，增加置信度
        if any(word in query for word in ["什么", "如何", "为什么", "怎么", "哪个"]):
            confidence += 0.2

        # 如果查询长度适中，增加置信度
        if 10 <= len(query) <= 100:
            confidence += 0.1

        return min(confidence, 1.0)

    def _suggest_reasoning_mode(self, query_type: QueryType, complexity: float) -> ReasoningMode:
        """建议推理模式"""
        if complexity > 0.7:
            return ReasoningMode.ANALYTICAL
        elif query_type in [QueryType.COMPARATIVE, QueryType.ANALYTICAL]:
            return ReasoningMode.STEP_BY_STEP
        elif complexity > 0.5:
            return ReasoningMode.CONTEXT_AWARE
        else:
            return ReasoningMode.BASIC

    def _suggest_temperature(self, complexity: float) -> float:
        """建议温度参数"""
        if complexity > 0.7:
            return 0.8  # 高复杂度需要更高的创造性
        elif complexity > 0.5:
            return 0.6
        else:
            return 0.3  # 低复杂度使用较低温度确保准确性

    def _suggest_max_tokens(self, complexity: float) -> int:
        """建议最大Token数"""
        if complexity > 0.7:
            return 2000
        elif complexity > 0.5:
            return 1500
        else:
            return 800


class AnswerGenerator:
    """答案生成器"""

    def __init__(self):
        self.generation_templates = {
            QueryType.FACTUAL: "请基于提供的信息，准确回答以下问题：{query}",
            QueryType.ANALYTICAL: "请深入分析以下问题，提供详细的见解：{query}",
            QueryType.COMPARATIVE: "请比较分析以下内容，突出异同点：{query}",
            QueryType.TEMPORAL: "请分析以下时间相关问题：{query}",
            QueryType.CAUSAL: "请分析以下因果关系：{query}",
            QueryType.PROCEDURAL: "请提供详细的步骤说明：{query}",
            QueryType.PREDICTIVE: "请基于现有信息进行合理预测：{query}"
        }

    async def generate_answer(
        self,
        query_analysis: QueryAnalysis,
        context: Optional[List[Dict[str, Any]]] = None,
        data_sources: Optional[List[Dict[str, Any]]] = None,
        tenant_id: Optional[str] = None
    ) -> ReasoningResult:
        """
        生成答案

        Args:
            query_analysis: 查询分析结果
            context: 上下文信息
            data_sources: 数据源信息
            tenant_id: 租户ID

        Returns:
            推理结果
        """
        try:
            logger.info(f"开始生成答案: {query_analysis.original_query[:50]}...")

            # 构建推理步骤
            reasoning_steps = await self._generate_reasoning_steps(query_analysis, context, data_sources)

            # 生成主答案
            answer = await self._generate_main_answer(query_analysis, reasoning_steps, context, tenant_id)

            # 计算置信度和质量分数
            confidence = self._calculate_confidence(reasoning_steps, answer)
            quality_score = self._calculate_quality_score(answer, reasoning_steps)

            # 安全过滤
            safety_triggered = await self._safety_filter(answer)

            # 准备源信息
            sources = self._prepare_sources(data_sources)

            result = ReasoningResult(
                answer=answer,
                reasoning_steps=reasoning_steps,
                confidence=confidence,
                sources=sources,
                query_analysis=query_analysis,
                quality_score=quality_score,
                safety_filter_triggered=safety_triggered
            )

            logger.info(f"答案生成完成，置信度: {confidence:.2f}, 质量分数: {quality_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            # 返回默认结果
            return ReasoningResult(
                answer="抱歉，在生成答案时遇到了问题，请稍后重试。",
                reasoning_steps=[],
                confidence=0.1,
                sources=[],
                query_analysis=query_analysis,
                quality_score=0.1,
                safety_filter_triggered=True
            )

    async def _generate_reasoning_steps(
        self,
        query_analysis: QueryAnalysis,
        context: Optional[List[Dict[str, Any]]],
        data_sources: Optional[List[Dict[str, Any]]]
    ) -> List[ReasoningStep]:
        """生成推理步骤"""
        steps = []

        try:
            # 步骤1：理解查询意图
            step1 = ReasoningStep(
                step_number=1,
                description="理解查询意图和类型",
                reasoning=f"识别查询为{query_analysis.query_type.value}类型，意图：{query_analysis.intent}",
                evidence=[f"关键词：{', '.join(query_analysis.keywords)}"],
                confidence=query_analysis.confidence
            )
            steps.append(step1)

            # 步骤2：分析实体和关键信息
            if query_analysis.entities:
                step2 = ReasoningStep(
                    step_number=2,
                    description="提取关键实体和概念",
                    reasoning=f"识别出重要实体：{', '.join(query_analysis.entities)}",
                    evidence=query_analysis.entities,
                    confidence=0.8
                )
                steps.append(step2)

            # 步骤3：分析时间信息（如果存在）
            if query_analysis.temporal_expressions:
                step3 = ReasoningStep(
                    step_number=3,
                    description="分析时间相关信息",
                    reasoning=f"识别时间表达式：{', '.join(query_analysis.temporal_expressions)}",
                    evidence=query_analysis.temporal_expressions,
                    confidence=0.9
                )
                steps.append(step3)

            # 步骤4：整合上下文信息
            if context:
                step4 = ReasoningStep(
                    step_number=len(steps) + 1,
                    description="整合上下文信息",
                    reasoning=f"利用{len(context)}条上下文信息辅助推理",
                    evidence=[f"上下文消息{len(context)}条"],
                    confidence=0.7
                )
                steps.append(step4)

        except Exception as e:
            logger.error(f"生成推理步骤失败: {e}")
            # 至少返回一个基础步骤
            steps.append(ReasoningStep(
                step_number=1,
                description="基础分析",
                reasoning="对查询进行基础分析",
                evidence=[],
                confidence=0.5
            ))

        return steps

    async def _generate_main_answer(
        self,
        query_analysis: QueryAnalysis,
        reasoning_steps: List[ReasoningStep],
        context: Optional[List[Dict[str, Any]]],
        tenant_id: Optional[str]
    ) -> str:
        """生成主要答案"""
        try:
            # 构建提示词
            template = self.generation_templates.get(
                query_analysis.query_type,
                "请回答以下问题：{query}"
            )

            # 添加推理上下文
            reasoning_context = ""
            if reasoning_steps:
                reasoning_context = "\n\n推理过程：\n" + "\n".join([
                    f"{step.step_number}. {step.description}: {step.reasoning}"
                    for step in reasoning_steps
                ])

            # 添加上下文信息
            context_info = ""
            if context:
                context_info = "\n\n相关上下文：\n" + "\n".join([
                    f"- {msg.get('content', '')[:200]}..."
                    for msg in context[-3:]  # 只使用最近3条上下文
                ])

            prompt = template.format(
                query=query_analysis.original_query
            ) + reasoning_context + context_info

            messages = [
                {"role": "system", "content": "你是一个专业的AI助手，请基于提供的推理过程和上下文信息，生成准确、有用的答案。"},
                {"role": "user", "content": prompt}
            ]

            # 调用LLM生成答案
            response = await llm_service.chat_completion(
                tenant_id=tenant_id or "default",
                messages=[LLMMessage(role=msg["role"], content=msg["content"]) for msg in messages],
                temperature=query_analysis.suggested_temperature,
                max_tokens=query_analysis.suggested_max_tokens
            )

            if response and hasattr(response, 'content'):
                return response.content
            else:
                # 回退到zhipu服务
                zhipu_response = await zhipu_service.chat_completion(
                    messages=messages,
                    temperature=query_analysis.suggested_temperature,
                    max_tokens=query_analysis.suggested_max_tokens
                )

                if zhipu_response:
                    return zhipu_response.get("content", "无法生成答案")
                else:
                    return "抱歉，当前无法生成答案，请稍后重试。"

        except Exception as e:
            logger.error(f"生成主要答案失败: {e}")
            return "抱歉，生成答案时遇到了技术问题。"

    def _calculate_confidence(self, reasoning_steps: List[ReasoningStep], answer: str) -> float:
        """计算置信度"""
        if not reasoning_steps:
            return 0.1

        # 基于推理步骤的平均置信度
        step_confidence = sum(step.confidence for step in reasoning_steps) / len(reasoning_steps)

        # 基于答案长度和完整性
        length_score = min(len(answer) / 200, 1.0) * 0.3

        # 综合计算
        confidence = step_confidence * 0.7 + length_score
        return min(confidence, 1.0)

    def _calculate_quality_score(self, answer: str, reasoning_steps: List[ReasoningStep]) -> float:
        """计算质量分数"""
        quality = 0.0

        # 基于答案完整性
        if len(answer) > 50:
            quality += 0.3

        # 基于结构化程度
        if any(marker in answer for marker in ["首先", "其次", "最后", "总之", "总结"]):
            quality += 0.2

        # 基于推理步骤数量
        step_score = min(len(reasoning_steps) / 3, 1.0) * 0.3
        quality += step_score

        # 基于专业性（是否包含专业术语）
        professional_terms = ["分析", "评估", "建议", "方案", "策略", "优化"]
        term_count = sum(1 for term in professional_terms if term in answer)
        term_score = min(term_count / 2, 1.0) * 0.2
        quality += term_score

        return min(quality, 1.0)

    async def _safety_filter(self, content: str) -> bool:
        """安全过滤"""
        try:
            # 简单的安全检查
            unsafe_patterns = [
                r'暴力|血腥|恐怖',
                r'色情|成人内容',
                r'仇恨|歧视|侮辱',
                r'自残|自杀',
                r'违法|犯罪'
            ]

            for pattern in unsafe_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    logger.warning(f"安全过滤触发，匹配模式: {pattern}")
                    return True

            return False

        except Exception as e:
            logger.error(f"安全过滤失败: {e}")
            return True  # 出错时默认过滤

    def _prepare_sources(self, data_sources: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """准备源信息"""
        if not data_sources:
            return []

        sources = []
        for i, source in enumerate(data_sources[:5]):  # 限制最多5个源
            sources.append({
                "id": source.get("id", f"source_{i}"),
                "name": source.get("name", f"数据源{i+1}"),
                "type": source.get("type", "unknown"),
                "relevance": source.get("relevance", 0.8)
            })

        return sources


class ReasoningEngine:
    """推理引擎主类"""

    def __init__(self):
        self.query_understanding = QueryUnderstandingEngine()
        self.answer_generator = AnswerGenerator()

    async def reason(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        data_sources: Optional[List[Dict[str, Any]]] = None,
        tenant_id: Optional[str] = None,
        reasoning_mode: Optional[ReasoningMode] = None
    ) -> ReasoningResult:
        """
        执行完整推理过程

        Args:
            query: 用户查询
            context: 上下文信息
            data_sources: 数据源信息
            tenant_id: 租户ID
            reasoning_mode: 推理模式（可选）

        Returns:
            推理结果
        """
        try:
            start_time = time.time()
            logger.info(f"开始推理过程: {query[:100]}...")

            # 步骤1：查询分析
            query_analysis = await self.query_understanding.analyze_query(query, context)

            # 如果指定了推理模式，覆盖分析结果
            if reasoning_mode:
                query_analysis.reasoning_mode = reasoning_mode

            # 步骤2：生成答案
            result = await self.answer_generator.generate_answer(
                query_analysis, context, data_sources, tenant_id
            )

            # 添加处理时间
            processing_time = time.time() - start_time
            result.metadata["processing_time"] = processing_time
            result.metadata["reasoning_mode"] = query_analysis.reasoning_mode.value

            logger.info(f"推理完成，耗时: {processing_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"推理过程失败: {e}")
            # 返回默认推理结果
            default_analysis = QueryAnalysis(
                original_query=query,
                query_type=QueryType.UNKNOWN,
                intent="未知意图",
                entities=[],
                keywords=[],
                temporal_expressions=[],
                complexity_score=0.5,
                confidence=0.1,
                reasoning_mode=ReasoningMode.BASIC,
                suggested_temperature=0.7,
                suggested_max_tokens=1000
            )

            return ReasoningResult(
                answer="抱歉，处理您的查询时遇到了问题，请稍后重试。",
                reasoning_steps=[],
                confidence=0.1,
                sources=[],
                query_analysis=default_analysis,
                quality_score=0.1,
                safety_filter_triggered=True,
                metadata={"error": str(e)}
            )


# 全局推理引擎实例
reasoning_engine = ReasoningEngine()


class EnhancedReasoningEngine:
    """增强版推理引擎，集成融合和XAI功能"""

    def __init__(self):
        self.base_engine = reasoning_engine

        # 延迟导入避免循环依赖
        self._fusion_engine = None
        self._xai_service = None

    @property
    def fusion_engine(self):
        """延迟加载融合引擎"""
        if self._fusion_engine is None:
            from src.app.services.fusion_service import fusion_engine
            self._fusion_engine = fusion_engine
        return self._fusion_engine

    @property
    def xai_service(self):
        """延迟加载XAI服务"""
        if self._xai_service is None:
            from src.app.services.xai_service import xai_service
            self._xai_service = xai_service
        return self._xai_service

    async def enhanced_reason(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        sql_results: Optional[List[Dict[str, Any]]] = None,
        rag_results: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[Dict[str, Any]]] = None,
        tenant_id: Optional[str] = None,
        enable_fusion: bool = True,
        enable_xai: bool = True,
        reasoning_mode: Optional[ReasoningMode] = None
    ) -> Dict[str, Any]:
        """
        增强版推理，支持数据融合和XAI解释

        Args:
            query: 用户查询
            context: 上下文信息
            sql_results: SQL查询结果
            rag_results: RAG检索结果
            documents: 文档数据
            tenant_id: 租户ID
            enable_fusion: 是否启用数据融合
            enable_xai: 是否启用XAI解释
            reasoning_mode: 推理模式

        Returns:
            Dict: 包含推理结果、融合结果和XAI解释的综合结果
        """
        try:
            start_time = time.time()
            logger.info(f"开始增强推理: {query[:100]}...")

            # 步骤1：基础推理分析
            base_result = await self.base_engine.reason(
                query=query,
                context=context,
                data_sources=self._prepare_data_sources(sql_results, rag_results, documents),
                tenant_id=tenant_id,
                reasoning_mode=reasoning_mode
            )

            # 初始化结果
            enhanced_result = {
                "query": query,
                "base_reasoning": base_result,
                "fusion_result": None,
                "xai_explanation": None,
                "enhanced_answer": base_result.answer,
                "processing_metadata": {
                    "tenant_id": tenant_id,
                    "reasoning_mode": reasoning_mode.value if reasoning_mode else "auto",
                    "fusion_enabled": enable_fusion,
                    "xai_enabled": enable_xai
                }
            }

            # 步骤2：数据融合（如果启用）
            if enable_fusion and (sql_results or rag_results or documents):
                try:
                    fusion_result = await self.fusion_engine.fuse_multi_source_data(
                        query=query,
                        query_analysis=base_result.query_analysis,
                        sql_results=sql_results,
                        rag_results=rag_results,
                        documents=documents,
                        context=context,
                        tenant_id=tenant_id
                    )

                    enhanced_result["fusion_result"] = fusion_result

                    # 如果融合结果质量更高，使用融合后的答案
                    if fusion_result.answer_quality_score > base_result.quality_score:
                        enhanced_result["enhanced_answer"] = fusion_result.answer
                        logger.info(f"使用融合答案，质量提升: {fusion_result.answer_quality_score - base_result.quality_score:.2f}")

                except Exception as e:
                    logger.error(f"数据融合失败，使用基础推理结果: {e}")

            # 步骤3：XAI解释（如果启用）
            if enable_xai:
                try:
                    xai_explanation = await self.xai_service.generate_explanation(
                        query=query,
                        answer=enhanced_result["enhanced_answer"],
                        fusion_result=enhanced_result["fusion_result"],
                        reasoning_steps=base_result.reasoning_steps,
                        sources=self._prepare_sources_for_xai(sql_results, rag_results, documents),
                        tenant_id=tenant_id
                    )

                    enhanced_result["xai_explanation"] = xai_explanation

                    # 根据XAI结果调整答案（如果需要）
                    if xai_explanation.explanation_quality_score < 0.5:
                        logger.warning(f"XAI解释质量较低: {xai_explanation.explanation_quality_score:.2f}")

                except Exception as e:
                    logger.error(f"XAI解释生成失败: {e}")

            # 步骤4：添加处理时间和统计信息
            processing_time = time.time() - start_time
            enhanced_result["processing_metadata"]["total_processing_time"] = processing_time
            enhanced_result["processing_metadata"]["timestamp"] = datetime.utcnow().isoformat()

            # 添加质量指标
            enhanced_result["quality_metrics"] = self._calculate_quality_metrics(enhanced_result)

            logger.info(f"增强推理完成，耗时: {processing_time:.2f}秒")
            return enhanced_result

        except Exception as e:
            logger.error(f"增强推理失败: {e}")
            # 返回基础推理结果作为后备
            base_result = await self.base_engine.reason(
                query=query, context=context, tenant_id=tenant_id
            )

            return {
                "query": query,
                "base_reasoning": base_result,
                "fusion_result": None,
                "xai_explanation": None,
                "enhanced_answer": base_result.answer,
                "processing_metadata": {"error": str(e), "fallback_to_base": True},
                "quality_metrics": {}
            }

    def _prepare_data_sources(
        self,
        sql_results: Optional[List[Dict[str, Any]]],
        rag_results: Optional[List[Dict[str, Any]]],
        documents: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """为基础推理引擎准备数据源格式"""
        data_sources = []

        # 转换SQL结果
        if sql_results:
            for i, result in enumerate(sql_results):
                data_sources.append({
                    "id": f"sql_{i}",
                    "type": "sql_query",
                    "name": f"SQL查询结果{i+1}",
                    "content": json.dumps(result.get("data", result), ensure_ascii=False),
                    "confidence": result.get("confidence", 0.9)
                })

        # 转换RAG结果
        if rag_results:
            for i, result in enumerate(rag_results):
                content = result.get("content", "")
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)

                data_sources.append({
                    "id": f"rag_{i}",
                    "type": "rag_retrieval",
                    "name": f"RAG检索结果{i+1}",
                    "content": content,
                    "confidence": result.get("similarity_score", 0.8)
                })

        # 转换文档结果
        if documents:
            for i, doc in enumerate(documents):
                content = doc.get("content", doc.get("text", ""))
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)

                data_sources.append({
                    "id": f"doc_{i}",
                    "type": "document",
                    "name": doc.get("title", f"文档{i+1}"),
                    "content": content,
                    "confidence": doc.get("confidence", 0.7)
                })

        return data_sources

    def _prepare_sources_for_xai(
        self,
        sql_results: Optional[List[Dict[str, Any]]],
        rag_results: Optional[List[Dict[str, Any]]],
        documents: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """为XAI服务准备数据源格式"""
        sources = []

        # 转换所有数据源为统一格式
        all_data = {
            "sql_results": sql_results or [],
            "rag_results": rag_results or [],
            "documents": documents or []
        }

        for source_type, data_list in all_data.items():
            for i, data in enumerate(data_list):
                sources.append({
                    "source_id": f"{source_type}_{i}",
                    "source_type": source_type.rstrip('s'),  # 移除复数形式
                    "name": data.get("name", f"{source_type}_{i}"),
                    "content": data.get("content", ""),
                    "confidence": data.get("confidence", data.get("similarity_score", 0.7)),
                    "relevance_score": data.get("relevance_score", data.get("similarity_score", 0.8)),
                    "metadata": {
                        k: v for k, v in data.items()
                        if k not in ["content", "confidence", "relevance_score"]
                    }
                })

        return sources

    def _calculate_quality_metrics(self, enhanced_result: Dict[str, Any]) -> Dict[str, Any]:
        """计算综合质量指标"""
        metrics = {}

        try:
            base_reasoning = enhanced_result.get("base_reasoning")
            fusion_result = enhanced_result.get("fusion_result")
            xai_explanation = enhanced_result.get("xai_explanation")

            # 基础推理质量
            if base_reasoning:
                metrics["base_reasoning_quality"] = base_reasoning.quality_score
                metrics["base_reasoning_confidence"] = base_reasoning.confidence

            # 融合质量
            if fusion_result:
                metrics["fusion_quality"] = fusion_result.answer_quality_score
                metrics["fusion_confidence"] = fusion_result.confidence
                metrics["source_count"] = len(fusion_result.sources)
                metrics["conflict_count"] = len(fusion_result.conflicts)

            # XAI质量
            if xai_explanation:
                metrics["xai_quality"] = xai_explanation.explanation_quality_score
                metrics["explanation_steps"] = len(xai_explanation.explanation_steps)
                metrics["source_traces"] = len(xai_explanation.source_traces)

            # 综合质量分数
            quality_scores = []
            if "base_reasoning_quality" in metrics:
                quality_scores.append(metrics["base_reasoning_quality"])
            if "fusion_quality" in metrics:
                quality_scores.append(metrics["fusion_quality"])
            if "xai_quality" in metrics:
                quality_scores.append(metrics["xai_quality"])

            if quality_scores:
                metrics["overall_quality"] = sum(quality_scores) / len(quality_scores)
            else:
                metrics["overall_quality"] = 0.5

            # 质量等级
            overall_quality = metrics["overall_quality"]
            if overall_quality >= 0.8:
                metrics["quality_grade"] = "优秀"
            elif overall_quality >= 0.6:
                metrics["quality_grade"] = "良好"
            elif overall_quality >= 0.4:
                metrics["quality_grade"] = "一般"
            else:
                metrics["quality_grade"] = "需要改进"

        except Exception as e:
            logger.error(f"计算质量指标失败: {e}")
            metrics["error"] = str(e)

        return metrics

    async def get_reasoning_capabilities(self) -> Dict[str, Any]:
        """获取推理能力信息"""
        try:
            capabilities = {
                "reasoning_modes": [mode.value for mode in ReasoningMode],
                "query_types": [qtype.value for qtype in QueryType],
                "supported_features": {
                    "multi_source_fusion": True,
                    "xai_explanation": True,
                    "conflict_resolution": True,
                    "uncertainty_quantification": True,
                    "source_tracing": True,
                    "alternative_answers": True,
                    "decision_tree": True
                },
                "fusion_algorithms": [
                    "weighted_confidence_fusion",
                    "sql_priority_resolution",
                    "conflict_detection",
                    "evidence_based_synthesis"
                ],
                "xai_types": [
                    "data_source", "reasoning_process", "confidence",
                    "alternative", "uncertainty", "assumption"
                ],
                "visualization_types": [
                    "decision_tree", "evidence_chain", "timeline",
                    "confidence_heatmap", "interactive_explorer"
                ]
            }

            return capabilities

        except Exception as e:
            logger.error(f"获取推理能力失败: {e}")
            return {"error": str(e)}

    async def benchmark_reasoning(
        self,
        test_queries: List[str],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """推理性能基准测试"""
        try:
            benchmark_results = {
                "test_queries_count": len(test_queries),
                "results": [],
                "performance_metrics": {
                    "average_processing_time": 0.0,
                    "average_quality_score": 0.0,
                    "success_rate": 0.0
                }
            }

            total_processing_time = 0.0
            total_quality_score = 0.0
            success_count = 0

            for i, query in enumerate(test_queries):
                try:
                    start_time = time.time()

                    result = await self.enhanced_reason(
                        query=query,
                        tenant_id=tenant_id,
                        enable_fusion=True,
                        enable_xai=True
                    )

                    processing_time = time.time() - start_time
                    quality_score = result.get("quality_metrics", {}).get("overall_quality", 0.0)

                    test_result = {
                        "query_index": i + 1,
                        "query": query,
                        "processing_time": processing_time,
                        "quality_score": quality_score,
                        "success": True,
                        "answer_length": len(result.get("enhanced_answer", "")),
                        "fusion_used": result.get("fusion_result") is not None,
                        "xai_used": result.get("xai_explanation") is not None
                    }

                    benchmark_results["results"].append(test_result)

                    total_processing_time += processing_time
                    total_quality_score += quality_score
                    success_count += 1

                except Exception as e:
                    logger.error(f"基准测试查询 {i+1} 失败: {e}")
                    benchmark_results["results"].append({
                        "query_index": i + 1,
                        "query": query,
                        "processing_time": 0.0,
                        "quality_score": 0.0,
                        "success": False,
                        "error": str(e)
                    })

            # 计算性能指标
            if success_count > 0:
                benchmark_results["performance_metrics"]["average_processing_time"] = (
                    total_processing_time / success_count
                )
                benchmark_results["performance_metrics"]["average_quality_score"] = (
                    total_quality_score / success_count
                )
                benchmark_results["performance_metrics"]["success_rate"] = (
                    success_count / len(test_queries)
                )

            return benchmark_results

        except Exception as e:
            logger.error(f"基准测试失败: {e}")
            return {"error": str(e)}


# 全局增强推理引擎实例
enhanced_reasoning_engine = EnhancedReasoningEngine()