"""
# [XAI_SERVICE] XAI (可解释性AI) 服务

## [HEADER]
**文件名**: xai_service.py
**职责**: 提供AI推理过程透明化、答案溯源、决策树可视化等可解释性AI功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - XAI可解释性AI服务

## [INPUT]
- **query: str** - 原始查询
- **answer: str** - 生成的答案
- **fusion_result: Optional[FusionResult]** - 融合结果（可选）
- **reasoning_steps: Optional[List[Any]]** - 推理步骤（可选）
- **sources: Optional[List[Dict[str, Any]]]** - 数据源信息（可选）
- **tenant_id: Optional[str]** - 租户ID

## [OUTPUT]
- **XAIExplanation**: XAI解释结果对象
  - query, answer: 查询和答案
  - explanation_steps: List[ExplanationStep] - 解释步骤列表
  - source_traces: List[SourceTrace] - 源数据追踪列表
  - decision_tree: Dict[str, DecisionNode] - 决策树
  - uncertainty_quantification: UncertaintyQuantification - 不确定性量化
  - alternative_answers: List[AlternativeAnswer] - 替代答案列表
  - confidence_explanation: Dict[str, Any] - 置信度解释
  - visualization_data: Dict[str, Any] - 可视化数据
  - explanation_quality_score: float - 解释质量分数

**上游依赖** (已读取源码):
- Python标准库: asyncio, dataclasses, datetime, enum, json, logging, re, uuid
- 项目服务: llm_service（LLM调用）, fusion_service（FusionResult, ConflictInfo）

**下游依赖** (需要反向索引分析):
- [llm_service.py](./llm_service.py) - LLM服务使用XAI生成解释
- [agent_service.py](./agent_service.py) - Agent服务使用XAI增强可解释性

**调用方**:
- RAG-SQL链生成答案后调用XAI生成解释
- 用户请求答案解释时调用
- 前端可视化组件使用XAI数据渲染决策树和热力图

## [STATE]
- **解释类型**: ExplanationType枚举
  - DATA_SOURCE, REASONING_PROCESS, CONFIDENCE, ALTERNATIVE, UNCERTAINTY, ASSUMPTION
- **可视化类型**: VisualizationType枚举
  - DECISION_TREE, EVIDENCE_CHAIN, TIMELINE, CONFIDENCE_HEATMAP, INTERACTIVE_EXPLORER
- **数据结构**:
  - ExplanationStep: 解释步骤（step_id, step_number, explanation_type, title, description, evidence, confidence, reasoning, assumptions, limitations）
  - SourceTrace: 源数据追踪（source_id, source_type, source_name, content_snippet, relevance_score, confidence_contribution, trace_path）
  - DecisionNode: 决策树节点（node_id, node_type, title, content, confidence, children, parent）
  - UncertaintyQuantification: 不确定性量化（total_uncertainty, data_uncertainty, model_uncertainty, reasoning_uncertainty, uncertainty_sources, mitigation_suggestions）
  - AlternativeAnswer: 替代答案（answer_id, title, content, reasoning_differences, confidence_comparison, scenario_description, pros, cons）
- **解释模板**: explanation_templates字典（6种类型模板）
- **置信度因素**: confidence_factors列表（6种因素）
- **不确定性指标**: uncertainty_indicators列表（9个指标）
- **LLM调用**: 生成替代答案时调用llm_service.chat_completion
- **质量评分**: explanation_quality_score基于步骤完整性(30%) + 源数据追踪(25%) + 不确定性量化(25%) + 解释深度(20%)
- **决策树结构**: 根节点(查询理解) → 数据源选择 → 推理过程 → 结论

## [SIDE-EFFECTS]
- **LLM调用**: llm_service.chat_completion生成替代答案（详细版和简化版）
- **UUID生成**: str(uuid.uuid4())生成唯一ID
- **正则匹配**: re.findall(r'\b\w+\b', query)提取关键词，re.split(r'[.!?。！？]', answer)分割句子
- **字符串操作**: answer[:200] + "..."截断内容，len(query)计算长度
- **列表推导式**: [complex for indicator in complex_indicators if indicator in query]计算复杂度
- **字典操作**: defaultdict(int), defaultdict(list)统计冲突类型和策略
- **时间戳**: datetime.utcnow()生成时间戳
- **循环累加**: sum(s.get("confidence", 0.5) for s in sources) / len(sources)计算平均置信度
- **条件判断**: 检查不确定性指标、答案长度决定是否生成替代答案
- **异常处理**: 所有异步方法都有try-except捕获异常，返回基础解释
- **字典构建**: 构建决策树节点、可视化数据、置信度解释字典
- **质量计算**: 基于多个因子加权计算explanation_quality_score

## [POS]
**路径**: backend/src/app/services/xai_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 依赖llm_service和fusion_service
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import re
import uuid

from src.app.services.llm_service import llm_service, LLMMessage
from src.app.services.fusion_service import FusionResult, ConflictInfo

logger = logging.getLogger(__name__)


class ExplanationType(Enum):
    """解释类型枚举"""
    DATA_SOURCE = "data_source"           # 数据溯源解释
    REASONING_PROCESS = "reasoning_process"  # 推理过程解释
    CONFIDENCE = "confidence"              # 置信度解释
    ALTERNATIVE = "alternative"            # 替代方案解释
    UNCERTAINTY = "uncertainty"            # 不确定性解释
    ASSUMPTION = "assumption"              # 假设条件解释


class VisualizationType(Enum):
    """可视化类型枚举"""
    DECISION_TREE = "decision_tree"
    EVIDENCE_CHAIN = "evidence_chain"
    TIMELINE = "timeline"
    CONFIDENCE_HEATMAP = "confidence_heatmap"
    INTERACTIVE_EXPLORER = "interactive_explorer"


@dataclass
class ExplanationStep:
    """解释步骤"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    explanation_type: ExplanationType
    title: str
    description: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.8
    reasoning: str = ""
    assumptions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SourceTrace:
    """源数据追踪"""
    source_id: str
    source_type: str
    source_name: str
    content_snippet: str
    relevance_score: float
    confidence_contribution: float
    trace_path: List[str] = field(default_factory=list)
    extraction_method: str = "automatic"
    verification_status: str = "verified"


@dataclass
class DecisionNode:
    """决策树节点"""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: str  # "decision", "evidence", "conclusion"
    title: str
    content: str
    confidence: float
    children: List[str] = field(default_factory=list)  # 子节点ID
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UncertaintyQuantification:
    """不确定性量化"""
    total_uncertainty: float
    data_uncertainty: float
    model_uncertainty: float
    reasoning_uncertainty: float
    uncertainty_sources: List[str] = field(default_factory=list)
    mitigation_suggestions: List[str] = field(default_factory=list)


@dataclass
class AlternativeAnswer:
    """替代答案"""
    answer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    reasoning_differences: List[str]
    confidence_comparison: Dict[str, float]
    scenario_description: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)


@dataclass
class XAIExplanation:
    """XAI解释结果"""
    query: str
    answer: str
    explanation_steps: List[ExplanationStep]
    source_traces: List[SourceTrace]
    decision_tree: Dict[str, DecisionNode]
    uncertainty_quantification: UncertaintyQuantification
    alternative_answers: List[AlternativeAnswer]
    confidence_explanation: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    visualization_data: Dict[str, Any] = field(default_factory=dict)
    explanation_quality_score: float = 0.8


class XAIService:
    """XAI可解释性AI服务"""

    def __init__(self):
        self.explanation_templates = {
            ExplanationType.DATA_SOURCE: "数据来源分析：{content}",
            ExplanationType.REASONING_PROCESS: "推理过程分析：{content}",
            ExplanationType.CONFIDENCE: "置信度分析：{content}",
            ExplanationType.ALTERNATIVE: "替代方案分析：{content}",
            ExplanationType.UNCERTAINTY: "不确定性分析：{content}",
            ExplanationType.ASSUMPTION: "假设条件分析：{content}"
        }

        self.confidence_factors = [
            "数据质量", "信息完整性", "逻辑一致性",
            "来源可靠性", "冲突解决", "时间相关性"
        ]

        self.uncertainty_indicators = [
            "可能", "或许", "估计", "大约", "左右",
            "推测", "假设", "不确定", "待确认"
        ]

    async def generate_explanation(
        self,
        query: str,
        answer: str,
        fusion_result: Optional[FusionResult] = None,
        reasoning_steps: Optional[List[Any]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        tenant_id: Optional[str] = None
    ) -> XAIExplanation:
        """
        生成全面的XAI解释

        Args:
            query: 原始查询
            answer: 生成的答案
            fusion_result: 融合结果（可选）
            reasoning_steps: 推理步骤（可选）
            sources: 数据源信息（可选）
            tenant_id: 租户ID

        Returns:
            XAIExplanation: 完整的可解释性分析结果
        """
        try:
            logger.info(f"开始生成XAI解释: {query[:100]}...")

            # 步骤1：生成解释步骤
            explanation_steps = await self._generate_explanation_steps(
                query, answer, fusion_result, reasoning_steps, sources
            )

            # 步骤2：构建源数据追踪
            source_traces = await self._build_source_traces(sources or [], answer)

            # 步骤3：构建决策树
            decision_tree = await self._build_decision_tree(explanation_steps, sources)

            # 步骤4：量化不确定性
            uncertainty_quant = await self._quantify_uncertainty(
                explanation_steps, fusion_result, sources
            )

            # 步骤5：生成替代答案
            alternative_answers = await self._generate_alternative_answers(
                query, answer, sources, tenant_id
            )

            # 步骤6：置信度解释
            confidence_explanation = await self._explain_confidence(
                explanation_steps, fusion_result
            )

            # 步骤7：生成可视化数据
            visualization_data = await self._generate_visualization_data(
                explanation_steps, decision_tree, uncertainty_quant
            )

            # 步骤8：计算解释质量分数
            explanation_quality = await self._calculate_explanation_quality(
                explanation_steps, source_traces, uncertainty_quant
            )

            xai_result = XAIExplanation(
                query=query,
                answer=answer,
                explanation_steps=explanation_steps,
                source_traces=source_traces,
                decision_tree=decision_tree,
                uncertainty_quantification=uncertainty_quant,
                alternative_answers=alternative_answers,
                confidence_explanation=confidence_explanation,
                metadata={
                    "tenant_id": tenant_id,
                    "generation_time": datetime.utcnow().isoformat(),
                    "explanation_types": [step.explanation_type.value for step in explanation_steps],
                    "total_sources": len(source_traces),
                    "decision_tree_nodes": len(decision_tree)
                },
                visualization_data=visualization_data,
                explanation_quality_score=explanation_quality
            )

            logger.info(f"XAI解释生成完成，质量分数: {explanation_quality:.2f}")
            return xai_result

        except Exception as e:
            logger.error(f"XAI解释生成失败: {e}")
            # 返回基础解释
            return XAIExplanation(
                query=query,
                answer=answer,
                explanation_steps=[],
                source_traces=[],
                decision_tree={},
                uncertainty_quantification=UncertaintyQuantification(
                    total_uncertainty=1.0,
                    data_uncertainty=0.5,
                    model_uncertainty=0.3,
                    reasoning_uncertainty=0.2,
                    uncertainty_sources=["generation_error"]
                ),
                alternative_answers=[],
                confidence_explanation={"error": str(e)},
                metadata={"error": str(e)},
                explanation_quality_score=0.1
            )

    async def _generate_explanation_steps(
        self,
        query: str,
        answer: str,
        fusion_result: Optional[FusionResult],
        reasoning_steps: Optional[List[Any]],
        sources: Optional[List[Dict[str, Any]]]
    ) -> List[ExplanationStep]:
        """生成解释步骤"""
        steps = []

        try:
            step_number = 1

            # 步骤1：查询理解解释
            steps.append(await self._explain_query_understanding(query, step_number))
            step_number += 1

            # 步骤2：数据源选择解释
            if sources:
                steps.append(await self._explain_data_source_selection(sources, step_number))
                step_number += 1

            # 步骤3：推理过程解释
            steps.append(await self._explain_reasoning_process(
                query, answer, reasoning_steps, step_number
            ))
            step_number += 1

            # 步骤4：冲突处理解释
            if fusion_result and fusion_result.conflicts:
                steps.append(await self._explain_conflict_resolution(
                    fusion_result.conflicts, step_number
                ))
                step_number += 1

            # 步骤5：答案生成解释
            steps.append(await self._explain_answer_generation(
                query, answer, fusion_result, step_number
            ))
            step_number += 1

            # 步骤6：假设和限制解释
            steps.append(await self._explain_assumptions_limitations(
                query, answer, sources, step_number
            ))

            return steps

        except Exception as e:
            logger.error(f"生成解释步骤失败: {e}")
            return [ExplanationStep(
                step_number=1,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="解释过程",
                description="生成解释时遇到问题",
                confidence=0.1
            )]

    async def _explain_query_understanding(self, query: str, step_number: int) -> ExplanationStep:
        """解释查询理解过程"""
        try:
            # 分析查询特征
            query_length = len(query)
            question_count = query.count("?") + query.count("？")
            keywords = re.findall(r'\b\w+\b', query)[:10]  # 前10个关键词

            # 识别查询复杂度
            complex_indicators = ["分析", "比较", "为什么", "如何", "评估", "影响"]
            complexity_score = sum(1 for indicator in complex_indicators if indicator in query) / len(complex_indicators)

            evidence = [
                f"查询长度: {query_length} 字符",
                f"问题数量: {question_count} 个",
                f"关键概念: {', '.join(keywords[:5])}",
                f"复杂度分数: {complexity_score:.2f}"
            ]

            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="查询理解",
                description=f"系统理解用户查询为包含{len(keywords)}个关键概念的问题",
                evidence=evidence,
                confidence=0.9,
                reasoning=f"基于查询长度、问题数量和关键概念识别，系统判断查询复杂度为{complexity_score:.2f}",
                assumptions=["用户查询表达清晰", "关键概念识别准确"],
                limitations=["可能遗漏隐含含义", "复杂度评估可能存在偏差"]
            )

        except Exception as e:
            logger.error(f"查询理解解释失败: {e}")
            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="查询理解",
                description="查询理解过程分析",
                confidence=0.5
            )

    async def _explain_data_source_selection(
        self,
        sources: List[Dict[str, Any]],
        step_number: int
    ) -> ExplanationStep:
        """解释数据源选择过程"""
        try:
            source_types = {}
            total_sources = len(sources)
            avg_confidence = 0.0
            high_quality_sources = 0

            for source in sources:
                source_type = source.get("source_type", "unknown")
                source_types[source_type] = source_types.get(source_type, 0) + 1

                confidence = source.get("confidence", 0.5)
                avg_confidence += confidence

                if confidence > 0.8:
                    high_quality_sources += 1

            if total_sources > 0:
                avg_confidence /= total_sources

            evidence = [
                f"总数据源数量: {total_sources}",
                f"高质量数据源: {high_quality_sources} 个",
                f"平均置信度: {avg_confidence:.2f}",
                f"数据源类型分布: {dict(source_types)}"
            ]

            description = f"系统选择了{total_sources}个数据源，平均置信度为{avg_confidence:.2f}"

            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.DATA_SOURCE,
                title="数据源选择",
                description=description,
                evidence=evidence,
                confidence=avg_confidence,
                reasoning="基于数据源的可靠性、相关性和置信度评分进行选择",
                assumptions=["数据源信息准确", "置信度评估合理"],
                limitations=["可能遗漏相关数据源", "质量评估可能不够全面"]
            )

        except Exception as e:
            logger.error(f"数据源选择解释失败: {e}")
            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.DATA_SOURCE,
                title="数据源选择",
                description="数据源选择过程分析",
                confidence=0.5
            )

    async def _explain_reasoning_process(
        self,
        query: str,
        answer: str,
        reasoning_steps: Optional[List[Any]],
        step_number: int
    ) -> ExplanationStep:
        """解释推理过程"""
        try:
            # 分析答案特征
            answer_length = len(answer)
            sentences = re.split(r'[.!?。！？]', answer)
            sentence_count = len([s for s in sentences if s.strip()])

            # 识别推理模式
            reasoning_patterns = []
            if "首先" in answer or "第一步" in answer:
                reasoning_patterns.append("分步骤推理")
            if "因为" in answer or "由于" in answer:
                reasoning_patterns.append("因果推理")
            if "比较" in answer or "对比" in answer:
                reasoning_patterns.append("比较推理")
            if "因此" in answer or "所以" in answer:
                reasoning_patterns.append("逻辑推理")

            evidence = [
                f"答案长度: {answer_length} 字符",
                f"句子数量: {sentence_count} 个",
                f"推理模式: {', '.join(reasoning_patterns) if reasoning_patterns else '直接回答'}",
                f"推理步骤数: {len(reasoning_steps) if reasoning_steps else 0}"
            ]

            reasoning_description = f"采用{', '.join(reasoning_patterns) if reasoning_patterns else '直接'}推理方式生成{sentence_count}句话的答案"

            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="推理过程",
                description=reasoning_description,
                evidence=evidence,
                confidence=0.8,
                reasoning=f"基于查询复杂度和数据源信息，选择最适合的推理策略",
                assumptions=["推理逻辑合理", "答案结构清晰"],
                limitations=["可能存在推理跳跃", "复杂推理可能简化"]
            )

        except Exception as e:
            logger.error(f"推理过程解释失败: {e}")
            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="推理过程",
                description="推理过程分析",
                confidence=0.5
            )

    async def _explain_conflict_resolution(
        self,
        conflicts: List[ConflictInfo],
        step_number: int
    ) -> ExplanationStep:
        """解释冲突解决过程"""
        try:
            conflict_types = {}
            resolution_strategies = {}

            for conflict in conflicts:
                conflict_type = conflict.conflict_type
                strategy = conflict.resolution_strategy.value

                conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1
                resolution_strategies[strategy] = resolution_strategies.get(strategy, 0) + 1

            evidence = [
                f"检测到冲突总数: {len(conflicts)}",
                f"冲突类型分布: {dict(conflict_types)}",
                f"解决策略分布: {dict(resolution_strategies)}"
            ]

            description = f"检测到{len(conflicts)}个数据冲突，采用多种策略进行解决"

            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="冲突解决",
                description=description,
                evidence=evidence,
                confidence=0.8,
                reasoning="系统自动检测并解决数据源间的冲突，确保答案的一致性",
                assumptions=["冲突检测准确", "解决策略有效"],
                limitations=["可能遗漏隐性冲突", "解决策略可能不够完善"]
            )

        except Exception as e:
            logger.error(f"冲突解决解释失败: {e}")
            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="冲突解决",
                description="冲突解决过程分析",
                confidence=0.5
            )

    async def _explain_answer_generation(
        self,
        query: str,
        answer: str,
        fusion_result: Optional[FusionResult],
        step_number: int
    ) -> ExplanationStep:
        """解释答案生成过程"""
        try:
            # 分析答案特征
            key_points = []
            sentences = re.split(r'[.!?。！？]', answer)

            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:  # 忽略太短的句子
                    key_points.append(sentence)

            # 识别答案结构
            structure_indicators = []
            if any(marker in answer for marker in ["首先", "其次", "最后"]):
                structure_indicators.append("分点结构")
            if "总结" in answer or "结论" in answer:
                structure_indicators.append("总结结构")
            if "数据" in answer or "统计" in answer:
                structure_indicators.append("数据支撑")

            overall_confidence = fusion_result.confidence if fusion_result else 0.8
            quality_score = fusion_result.answer_quality_score if fusion_result else 0.8

            evidence = [
                f"关键观点数: {len(key_points)}",
                f"答案结构: {', '.join(structure_indicators) if structure_indicators else '简单结构'}",
                f"整体置信度: {overall_confidence:.2f}",
                f"质量评分: {quality_score:.2f}"
            ]

            description = f"基于多源数据融合生成包含{len(key_points)}个关键观点的答案"

            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="答案生成",
                description=description,
                evidence=evidence,
                confidence=overall_confidence,
                reasoning="综合多个数据源信息，通过逻辑推理生成结构化答案",
                assumptions=["数据源可靠", "融合算法有效"],
                limitations=["信息融合可能不完整", "生成质量受数据质量限制"]
            )

        except Exception as e:
            logger.error(f"答案生成解释失败: {e}")
            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="答案生成",
                description="答案生成过程分析",
                confidence=0.5
            )

    async def _explain_assumptions_limitations(
        self,
        query: str,
        answer: str,
        sources: Optional[List[Dict[str, Any]]],
        step_number: int
    ) -> ExplanationStep:
        """解释假设和限制"""
        try:
            # 识别假设
            assumptions = [
                "用户提供的信息是准确的",
                "数据源的信息是可靠的",
                "推理逻辑是合理的",
                "答案能够满足用户需求"
            ]

            # 识别限制
            limitations = [
                "可能存在未考虑到的数据源",
                "推理过程可能存在简化",
                "答案的准确性依赖于输入数据质量",
                "复杂情况可能需要人工验证"
            ]

            # 检查不确定性指标
            uncertainty_count = sum(1 for indicator in self.uncertainty_indicators if indicator in answer)

            evidence = [
                f"识别假设数量: {len(assumptions)}",
                f"识别限制数量: {len(limitations)}",
                f"不确定性指标: {uncertainty_count} 个",
                f"数据源依赖: {'是' if sources else '否'}"
            ]

            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.ASSUMPTION,
                title="假设与限制",
                description=f"基于{len(assumptions)}个假设和{len(limitations)}个限制生成答案",
                evidence=evidence,
                confidence=0.7,
                reasoning="系统明确生成答案时的假设条件和存在限制",
                assumptions=assumptions,
                limitations=limitations
            )

        except Exception as e:
            logger.error(f"假设限制解释失败: {e}")
            return ExplanationStep(
                step_number=step_number,
                explanation_type=ExplanationType.ASSUMPTION,
                title="假设与限制",
                description="假设条件和限制因素分析",
                confidence=0.5
            )

    async def _build_source_traces(
        self,
        sources: List[Dict[str, Any]],
        answer: str
    ) -> List[SourceTrace]:
        """构建源数据追踪"""
        traces = []

        try:
            for source in sources:
                # 提取与答案相关的内容片段
                content = source.get("content", "")
                source_snippet = content[:200] + "..." if len(content) > 200 else content

                # 计算相关性分数（简化版）
                relevance_score = source.get("relevance_score", 0.8)
                confidence_contribution = source.get("confidence", 0.8)

                trace = SourceTrace(
                    source_id=source.get("source_id", f"source_{len(traces)}"),
                    source_type=source.get("source_type", "unknown"),
                    source_name=source.get("name", f"数据源{len(traces)+1}"),
                    content_snippet=source_snippet,
                    relevance_score=relevance_score,
                    confidence_contribution=confidence_contribution,
                    trace_path=[source.get("source_type", "unknown")],
                    extraction_method="content_matching",
                    verification_status="verified"
                )
                traces.append(trace)

        except Exception as e:
            logger.error(f"构建源数据追踪失败: {e}")

        return traces

    async def _build_decision_tree(
        self,
        explanation_steps: List[ExplanationStep],
        sources: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, DecisionNode]:
        """构建决策树"""
        tree = {}

        try:
            # 根节点：查询理解
            root_node = DecisionNode(
                node_type="decision",
                title="查询理解",
                content=f"理解用户查询，识别关键概念和意图",
                confidence=0.9,
                children=["data_selection"]
            )
            tree["root"] = root_node

            # 数据源选择节点
            if sources:
                data_node = DecisionNode(
                    node_id="data_selection",
                    node_type="decision",
                    title="数据源选择",
                    content=f"选择了{len(sources)}个相关数据源",
                    confidence=0.8,
                    children=["reasoning"]
                )
                tree["data_selection"] = data_node
            else:
                data_node = DecisionNode(
                    node_id="data_selection",
                    node_type="decision",
                    title="数据源选择",
                    content="未找到特定数据源，使用通用知识",
                    confidence=0.6,
                    children=["reasoning"]
                )
                tree["data_selection"] = data_node

            # 推理过程节点
            reasoning_node = DecisionNode(
                node_id="reasoning",
                node_type="evidence",
                title="推理过程",
                content="基于数据和逻辑推理生成答案",
                confidence=0.8,
                children=["conclusion"]
            )
            tree["reasoning"] = reasoning_node

            # 结论节点
            conclusion_node = DecisionNode(
                node_id="conclusion",
                node_type="conclusion",
                title="生成答案",
                content="综合所有信息，生成最终答案",
                confidence=0.8,
                parent="reasoning"
            )
            tree["conclusion"] = conclusion_node

            # 为每个解释步骤添加节点
            for step in explanation_steps:
                step_node = DecisionNode(
                    node_id=f"step_{step.step_number}",
                    node_type="evidence",
                    title=step.title,
                    content=step.description,
                    confidence=step.confidence,
                    parent="reasoning"
                )
                tree[f"step_{step.step_number}"] = step_node

        except Exception as e:
            logger.error(f"构建决策树失败: {e}")

        return tree

    async def _quantify_uncertainty(
        self,
        explanation_steps: List[ExplanationStep],
        fusion_result: Optional[FusionResult],
        sources: Optional[List[Dict[str, Any]]]
    ) -> UncertaintyQuantification:
        """量化不确定性"""
        try:
            # 数据不确定性
            data_uncertainty = 0.3
            if sources:
                avg_confidence = sum(s.get("confidence", 0.5) for s in sources) / len(sources)
                data_uncertainty = 1.0 - avg_confidence

            # 模型不确定性
            model_uncertainty = 0.2  # 基础模型不确定性
            if fusion_result:
                model_uncertainty = max(0.1, 1.0 - fusion_result.confidence)

            # 推理不确定性
            reasoning_uncertainty = 0.2
            if explanation_steps:
                avg_step_confidence = sum(step.confidence for step in explanation_steps) / len(explanation_steps)
                reasoning_uncertainty = 1.0 - avg_step_confidence

            # 总不确定性
            total_uncertainty = (data_uncertainty + model_uncertainty + reasoning_uncertainty) / 3

            # 不确定性来源
            uncertainty_sources = []
            if data_uncertainty > 0.3:
                uncertainty_sources.append("数据质量限制")
            if model_uncertainty > 0.3:
                uncertainty_sources.append("模型能力限制")
            if reasoning_uncertainty > 0.3:
                uncertainty_sources.append("推理复杂性")

            # 缓解建议
            mitigation_suggestions = []
            if total_uncertainty > 0.4:
                mitigation_suggestions.append("建议人工验证关键信息")
            if data_uncertainty > 0.3:
                mitigation_suggestions.append("建议补充更多数据源")
            if model_uncertainty > 0.3:
                mitigation_suggestions.append("建议使用多个模型交叉验证")

            return UncertaintyQuantification(
                total_uncertainty=total_uncertainty,
                data_uncertainty=data_uncertainty,
                model_uncertainty=model_uncertainty,
                reasoning_uncertainty=reasoning_uncertainty,
                uncertainty_sources=uncertainty_sources,
                mitigation_suggestions=mitigation_suggestions
            )

        except Exception as e:
            logger.error(f"不确定性量化失败: {e}")
            return UncertaintyQuantification(
                total_uncertainty=0.5,
                data_uncertainty=0.2,
                model_uncertainty=0.2,
                reasoning_uncertainty=0.1,
                uncertainty_sources=["量化失败"]
            )

    async def _generate_alternative_answers(
        self,
        query: str,
        primary_answer: str,
        sources: Optional[List[Dict[str, Any]]],
        tenant_id: Optional[str]
    ) -> List[AlternativeAnswer]:
        """生成替代答案"""
        alternatives = []

        try:
            # 替代答案1：更详细的分析
            if len(primary_answer) < 500:  # 如果原答案较短
                detailed_prompt = f"""
                原始查询：{query}
                原始答案：{primary_answer}

                请提供一个更详细、更深入的答案，包含更多的背景信息、数据支撑和分析过程。
                """

                messages = [
                    LLMMessage(role="system", content="你是一个专业的分析师，请提供详细深入的分析。"),
                    LLMMessage(role="user", content=detailed_prompt)
                ]

                try:
                    response = await llm_service.chat_completion(
                        tenant_id=tenant_id or "default",
                        messages=messages,
                        temperature=0.6,
                        max_tokens=800
                    )

                    if hasattr(response, 'content'):
                        alternatives.append(AlternativeAnswer(
                            title="详细分析版本",
                            content=response.content,
                            reasoning_differences=[
                                "提供了更多背景信息",
                                "增加了详细的数据支撑",
                                "扩展了分析深度"
                            ],
                            confidence_comparison={
                                "primary": 0.8,
                                "alternative": 0.7
                            },
                            scenario_description="当用户需要更深入了解问题时使用",
                            pros=["信息更全面", "分析更深入"],
                            cons=["可能过于冗长", "包含推测内容"]
                        ))
                except Exception as e:
                    logger.warning(f"生成详细替代答案失败: {e}")

            # 替代答案2：简化版本
            if len(primary_answer) > 300:  # 如果原答案较长
                simplified_prompt = f"""
                原始查询：{query}
                原始答案：{primary_answer}

                请提供一个简化的答案，突出最重要的关键信息，控制在150字以内。
                """

                messages = [
                    LLMMessage(role="system", content="你是一个专业的总结师，请提炼核心信息。"),
                    LLMMessage(role="user", content=simplified_prompt)
                ]

                try:
                    response = await llm_service.chat_completion(
                        tenant_id=tenant_id or "default",
                        messages=messages,
                        temperature=0.3,
                        max_tokens=200
                    )

                    if hasattr(response, 'content'):
                        alternatives.append(AlternativeAnswer(
                            title="简化核心版本",
                            content=response.content,
                            reasoning_differences=[
                                "突出核心观点",
                                "简化分析过程",
                                "聚焦关键信息"
                            ],
                            confidence_comparison={
                                "primary": 0.8,
                                "alternative": 0.9
                            },
                            scenario_description="当用户需要快速获取核心信息时使用",
                            pros=["简洁明了", "重点突出"],
                            cons=["可能遗漏细节", "分析不够深入"]
                        ))
                except Exception as e:
                    logger.warning(f"生成简化替代答案失败: {e}")

        except Exception as e:
            logger.error(f"生成替代答案失败: {e}")

        return alternatives

    async def _explain_confidence(
        self,
        explanation_steps: List[ExplanationStep],
        fusion_result: Optional[FusionResult]
    ) -> Dict[str, Any]:
        """解释置信度"""
        try:
            confidence_factors = {}

            # 基于解释步骤计算置信度
            if explanation_steps:
                avg_step_confidence = sum(step.confidence for step in explanation_steps) / len(explanation_steps)
                confidence_factors["推理步骤置信度"] = avg_step_confidence

            # 基于融合结果计算置信度
            if fusion_result:
                confidence_factors["融合结果置信度"] = fusion_result.confidence
                confidence_factors["答案质量分数"] = fusion_result.answer_quality_score

            # 基于数据源计算置信度
            if hasattr(fusion_result, 'sources') and fusion_result.sources:
                avg_source_confidence = sum(
                    source.get("confidence", 0.5) for source in fusion_result.sources
                ) / len(fusion_result.sources)
                confidence_factors["数据源平均置信度"] = avg_source_confidence

            # 计算综合置信度
            if confidence_factors:
                overall_confidence = sum(confidence_factors.values()) / len(confidence_factors)
            else:
                overall_confidence = 0.5

            # 置信度等级描述
            if overall_confidence >= 0.8:
                confidence_level = "高置信度"
                confidence_description = "答案基于充分可靠的数据，具有较高可信度"
            elif overall_confidence >= 0.6:
                confidence_level = "中等置信度"
                confidence_description = "答案基于合理的数据和推理，具有一定可信度"
            else:
                confidence_level = "低置信度"
                confidence_description = "答案可能存在不确定性，建议进一步验证"

            return {
                "overall_confidence": overall_confidence,
                "confidence_level": confidence_level,
                "confidence_description": confidence_description,
                "confidence_factors": confidence_factors,
                "improvement_suggestions": self._get_confidence_improvement_suggestions(confidence_factors)
            }

        except Exception as e:
            logger.error(f"置信度解释失败: {e}")
            return {
                "overall_confidence": 0.5,
                "confidence_level": "未知",
                "confidence_description": "无法计算置信度",
                "confidence_factors": {},
                "error": str(e)
            }

    def _get_confidence_improvement_suggestions(
        self,
        confidence_factors: Dict[str, float]
    ) -> List[str]:
        """获取置信度改进建议"""
        suggestions = []

        for factor, value in confidence_factors.items():
            if value < 0.6:
                if "推理步骤" in factor:
                    suggestions.append("改进推理逻辑，增加推理步骤的严谨性")
                elif "融合结果" in factor:
                    suggestions.append("优化数据融合算法，提高融合质量")
                elif "数据源" in factor:
                    suggestions.append("增加更高质量的数据源，提高数据可靠性")

        if not suggestions:
            suggestions.append("当前置信度水平良好，保持现有质量标准")

        return suggestions

    async def _generate_visualization_data(
        self,
        explanation_steps: List[ExplanationStep],
        decision_tree: Dict[str, DecisionNode],
        uncertainty_quant: UncertaintyQuantification
    ) -> Dict[str, Any]:
        """生成可视化数据"""
        try:
            visualization_data = {}

            # 决策树可视化数据
            if decision_tree:
                tree_nodes = []
                tree_edges = []

                for node_id, node in decision_tree.items():
                    tree_nodes.append({
                        "id": node_id,
                        "label": node.title,
                        "type": node.node_type,
                        "confidence": node.confidence,
                        "content": node.content
                    })

                    for child_id in node.children:
                        tree_edges.append({
                            "from": node_id,
                            "to": child_id,
                            "label": "推导"
                        })

                visualization_data["decision_tree"] = {
                    "nodes": tree_nodes,
                    "edges": tree_edges
                }

            # 解释步骤时间线
            if explanation_steps:
                timeline_data = []
                for step in explanation_steps:
                    timeline_data.append({
                        "step": step.step_number,
                        "title": step.title,
                        "description": step.description,
                        "confidence": step.confidence,
                        "type": step.explanation_type.value,
                        "timestamp": step.timestamp.isoformat()
                    })

                visualization_data["timeline"] = timeline_data

            # 不确定性热力图数据
            uncertainty_data = {
                "data_uncertainty": uncertainty_quant.data_uncertainty,
                "model_uncertainty": uncertainty_quant.model_uncertainty,
                "reasoning_uncertainty": uncertainty_quant.reasoning_uncertainty,
                "total_uncertainty": uncertainty_quant.total_uncertainty
            }
            visualization_data["uncertainty_heatmap"] = uncertainty_data

            # 置信度分布
            confidence_scores = [step.confidence for step in explanation_steps]
            if confidence_scores:
                visualization_data["confidence_distribution"] = {
                    "scores": confidence_scores,
                    "average": sum(confidence_scores) / len(confidence_scores),
                    "min": min(confidence_scores),
                    "max": max(confidence_scores)
                }

            return visualization_data

        except Exception as e:
            logger.error(f"生成可视化数据失败: {e}")
            return {}

    async def _calculate_explanation_quality(
        self,
        explanation_steps: List[ExplanationStep],
        source_traces: List[SourceTrace],
        uncertainty_quant: UncertaintyQuantification
    ) -> float:
        """计算解释质量分数"""
        try:
            quality_score = 0.0

            # 步骤完整性 (30%)
            if len(explanation_steps) >= 5:
                quality_score += 0.3
            elif len(explanation_steps) >= 3:
                quality_score += 0.2

            # 源数据追踪 (25%)
            if source_traces:
                trace_quality = sum(trace.verification_status == "verified" for trace in source_traces) / len(source_traces)
                quality_score += trace_quality * 0.25

            # 不确定性量化 (25%)
            if uncertainty_quant.total_uncertainty < 0.3:
                quality_score += 0.25
            elif uncertainty_quant.total_uncertainty < 0.5:
                quality_score += 0.15

            # 解释深度 (20%)
            explanation_types = set(step.explanation_type for step in explanation_steps)
            type_coverage = len(explanation_types) / len(ExplanationType)
            quality_score += type_coverage * 0.2

            return min(quality_score, 1.0)

        except Exception as e:
            logger.error(f"计算解释质量分数失败: {e}")
            return 0.5


# 全局XAI服务实例
xai_service = XAIService()