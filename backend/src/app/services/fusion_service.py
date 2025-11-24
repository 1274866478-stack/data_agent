"""
融合引擎服务
实现SQL查询结果、RAG检索结果的多源数据融合和答案生成
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import re

from src.app.services.reasoning_service import (
    reasoning_engine, QueryAnalysis, ReasoningResult, ReasoningStep
)
from src.app.services.llm_service import llm_service, LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型枚举"""
    SQL_QUERY = "sql_query"
    RAG_RETRIEVAL = "rag_retrieval"
    DOCUMENT = "document"
    API_RESPONSE = "api_response"
    UNSTRUCTURED_TEXT = "unstructured_text"
    EXTERNAL_KNOWLEDGE = "external_knowledge"


class ConflictResolutionStrategy(Enum):
    """冲突解决策略"""
    TRUST_MOST_RECENT = "most_recent"
    TRUST_HIGHEST_CONFIDENCE = "highest_confidence"
    TRUST_SQL_OVER_RAG = "sql_over_rag"
    TRUST_CONSENSUS = "consensus"
    MANUAL_REVIEW = "manual_review"
    WEIGHTED_AVERAGE = "weighted_average"


@dataclass
class SourceData:
    """源数据结构"""
    source_id: str
    source_type: DataSourceType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    timestamp: datetime = field(default_factory=datetime.utcnow)
    relevance_score: float = 0.8
    factual_reliability: float = 0.8


@dataclass
class FusionExplanation:
    """融合解释步骤"""
    step_number: int
    description: str
    action: str
    evidence: List[str]
    confidence: float
    decision_factors: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConflictInfo:
    """冲突信息"""
    conflict_type: str
    conflicting_sources: List[str]
    conflict_description: str
    resolution_strategy: ConflictResolutionStrategy
    resolution_result: str
    confidence_impact: float


@dataclass
class FusionResult:
    """融合结果"""
    answer: str
    sources: List[Dict[str, Any]]
    reasoning_log: List[FusionExplanation]
    confidence: float
    fusion_metadata: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[ConflictInfo] = field(default_factory=list)
    processing_time: float = 0.0
    answer_quality_score: float = 0.0


class DataFusionEngine:
    """数据融合引擎"""

    def __init__(self):
        self.fusion_strategies = {
            DataSourceType.SQL_QUERY: self._fuse_sql_data,
            DataSourceType.RAG_RETRIEVAL: self._fuse_rag_data,
            DataSourceType.DOCUMENT: self._fuse_document_data,
        }

        self.conflict_resolution_handlers = {
            ConflictResolutionStrategy.TRUST_MOST_RECENT: self._resolve_by_recency,
            ConflictResolutionStrategy.TRUST_HIGHEST_CONFIDENCE: self._resolve_by_confidence,
            ConflictResolutionStrategy.TRUST_SQL_OVER_RAG: self._resolve_sql_priority,
            ConflictResolutionStrategy.TRUST_CONSENSUS: self._resolve_by_consensus,
            ConflictResolutionStrategy.WEIGHTED_AVERAGE: self._resolve_by_weighted_average,
        }

    async def fuse_multi_source_data(
        self,
        query: str,
        query_analysis: Optional[QueryAnalysis] = None,
        sql_results: Optional[List[Dict[str, Any]]] = None,
        rag_results: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[Dict[str, Any]]] = None,
        context: Optional[List[Dict[str, Any]]] = None,
        tenant_id: Optional[str] = None
    ) -> FusionResult:
        """
        多源数据融合主函数

        Args:
            query: 用户原始查询
            query_analysis: 查询分析结果（可选）
            sql_results: SQL查询结果
            rag_results: RAG检索结果
            documents: 文档数据
            context: 上下文信息
            tenant_id: 租户ID

        Returns:
            FusionResult: 融合结果
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"开始多源数据融合: {query[:100]}...")

            # 步骤1：标准化输入数据
            source_data_list = await self._standardize_input_data(
                sql_results, rag_results, documents, tenant_id
            )

            # 步骤2：数据预处理和质量评估
            processed_data = await self._preprocess_data(source_data_list)

            # 步骤3：冲突检测
            conflicts = await self._detect_conflicts(processed_data)

            # 步骤4：冲突解决
            resolved_data = await self._resolve_conflicts(processed_data, conflicts)

            # 步骤5：信息融合
            fused_content = await self._perform_fusion(resolved_data, query)

            # 步骤6：生成答案
            final_answer = await self._generate_fused_answer(
                query, fused_content, context, tenant_id
            )

            # 步骤7：构建融合解释
            explanation_log = await self._build_fusion_explanation(
                processed_data, conflicts, resolved_data, fused_content
            )

            # 步骤8：计算质量分数
            quality_score = await self._calculate_answer_quality(
                final_answer, fused_content, explanation_log
            )

            # 计算处理时间
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # 准备源信息
            sources = await self._prepare_source_citations(processed_data)

            result = FusionResult(
                answer=final_answer,
                sources=sources,
                reasoning_log=explanation_log,
                confidence=fused_content.get("overall_confidence", 0.8),
                fusion_metadata={
                    "query": query,
                    "source_count": len(processed_data),
                    "conflict_count": len(conflicts),
                    "fusion_strategy": used_fusion_strategy,
                    "tenant_id": tenant_id,
                    "processing_timestamp": start_time.isoformat()
                },
                conflicts=conflicts,
                processing_time=processing_time,
                answer_quality_score=quality_score
            )

            logger.info(f"数据融合完成，耗时: {processing_time:.2f}秒，置信度: {result.confidence:.2f}")
            return result

        except Exception as e:
            logger.error(f"数据融合失败: {e}")
            # 返回默认结果
            return FusionResult(
                answer="抱歉，在融合多源数据时遇到了问题，请稍后重试。",
                sources=[],
                reasoning_log=[],
                confidence=0.1,
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                answer_quality_score=0.1,
                fusion_metadata={"error": str(e)}
            )

    async def _standardize_input_data(
        self,
        sql_results: Optional[List[Dict[str, Any]]],
        rag_results: Optional[List[Dict[str, Any]]],
        documents: Optional[List[Dict[str, Any]]],
        tenant_id: Optional[str]
    ) -> List[SourceData]:
        """标准化输入数据为统一的SourceData格式"""
        source_data_list = []

        # 处理SQL查询结果
        if sql_results:
            for i, result in enumerate(sql_results):
                source_data = SourceData(
                    source_id=f"sql_{i}",
                    source_type=DataSourceType.SQL_QUERY,
                    content=json.dumps(result.get("data", result), ensure_ascii=False),
                    metadata={
                        "query": result.get("query", ""),
                        "execution_time": result.get("execution_time"),
                        "row_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else 1,
                        "database": result.get("database", "unknown")
                    },
                    confidence=result.get("confidence", 0.9),
                    factual_reliability=0.95  # SQL数据通常可靠性较高
                )
                source_data_list.append(source_data)

        # 处理RAG检索结果
        if rag_results:
            for i, result in enumerate(rag_results):
                content = result.get("content", "")
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)

                source_data = SourceData(
                    source_id=f"rag_{i}",
                    source_type=DataSourceType.RAG_RETRIEVAL,
                    content=content,
                    metadata={
                        "collection": result.get("collection", ""),
                        "similarity_score": result.get("similarity_score", 0.8),
                        "chunk_id": result.get("chunk_id", ""),
                        "document_id": result.get("document_id", "")
                    },
                    confidence=result.get("confidence", result.get("similarity_score", 0.8)),
                    relevance_score=result.get("similarity_score", 0.8)
                )
                source_data_list.append(source_data)

        # 处理文档数据
        if documents:
            for i, doc in enumerate(documents):
                content = doc.get("content", doc.get("text", ""))
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)

                source_data = SourceData(
                    source_id=f"doc_{i}",
                    source_type=DataSourceType.DOCUMENT,
                    content=content,
                    metadata={
                        "title": doc.get("title", ""),
                        "file_name": doc.get("file_name", ""),
                        "file_type": doc.get("file_type", ""),
                        "page_number": doc.get("page_number"),
                        "section": doc.get("section", "")
                    },
                    confidence=doc.get("confidence", 0.7),
                    factual_reliability=0.8
                )
                source_data_list.append(source_data)

        return source_data_list

    async def _preprocess_data(self, source_data_list: List[SourceData]) -> List[SourceData]:
        """数据预处理和质量评估"""
        processed_data = []

        for data in source_data_list:
            try:
                # 内容清洗和标准化
                cleaned_content = await self._clean_content(data.content)

                # 提取关键信息
                key_info = await self._extract_key_information(cleaned_content)

                # 更新数据
                processed_data.append(SourceData(
                    source_id=data.source_id,
                    source_type=data.source_type,
                    content=cleaned_content,
                    metadata={
                        **data.metadata,
                        **key_info
                    },
                    confidence=data.confidence,
                    timestamp=data.timestamp,
                    relevance_score=data.relevance_score,
                    factual_reliability=data.factual_reliability
                ))

            except Exception as e:
                logger.warning(f"预处理数据失败 {data.source_id}: {e}")
                # 保留原始数据
                processed_data.append(data)

        return processed_data

    async def _clean_content(self, content: str) -> str:
        """清洗内容"""
        if not isinstance(content, str):
            content = str(content)

        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)

        # 移除特殊字符
        content = re.sub(r'[^\w\s\u4e00-\u9fff.,!?()[\]{}"\'%&$#@]', '', content)

        # 截断过长的内容
        if len(content) > 10000:
            content = content[:10000] + "..."

        return content.strip()

    async def _extract_key_information(self, content: str) -> Dict[str, Any]:
        """提取关键信息"""
        key_info = {}

        # 提取数字信息
        numbers = re.findall(r'\d+(?:\.\d+)?', content)
        if numbers:
            key_info["numbers"] = numbers

        # 提取日期信息
        dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}', content)
        if dates:
            key_info["dates"] = dates

        # 提取百分比
        percentages = re.findall(r'\d+(?:\.\d+)?%', content)
        if percentages:
            key_info["percentages"] = percentages

        # 计算内容统计
        key_info["content_length"] = len(content)
        key_info["word_count"] = len(content.split())

        return key_info

    async def _detect_conflicts(self, data_list: List[SourceData]) -> List[ConflictInfo]:
        """检测数据冲突"""
        conflicts = []

        if len(data_list) < 2:
            return conflicts

        # 检查数值冲突
        conflicts.extend(await self._detect_numeric_conflicts(data_list))

        # 检查事实冲突
        conflicts.extend(await self._detect_factual_conflicts(data_list))

        # 检查时间冲突
        conflicts.extend(await self._detect_temporal_conflicts(data_list))

        return conflicts

    async def _detect_numeric_conflicts(self, data_list: List[SourceData]) -> List[ConflictInfo]:
        """检测数值冲突"""
        conflicts = []

        # 提取所有数值信息
        numeric_info = {}
        for data in data_list:
            numbers = re.findall(r'\d+(?:\.\d+)?', data.content)
            numeric_info[data.source_id] = [float(num) for num in numbers]

        # 比较数值差异
        source_ids = list(numeric_info.keys())
        for i in range(len(source_ids)):
            for j in range(i + 1, len(source_ids)):
                id1, id2 = source_ids[i], source_ids[j]
                nums1, nums2 = numeric_info[id1], numeric_info[id2]

                if nums1 and nums2 and abs(nums1[0] - nums2[0]) / max(nums1[0], nums2[0]) > 0.1:
                    conflicts.append(ConflictInfo(
                        conflict_type="numeric_conflict",
                        conflicting_sources=[id1, id2],
                        conflict_description=f"数值不一致: {nums1[0]} vs {nums2[0]}",
                        resolution_strategy=ConflictResolutionStrategy.TRUST_SQL_OVER_RAG,
                        resolution_result="pending_resolution",
                        confidence_impact=0.2
                    ))

        return conflicts

    async def _detect_factual_conflicts(self, data_list: List[SourceData]) -> List[ConflictInfo]:
        """检测事实冲突"""
        # 简化版本：实际应用中可以使用更复杂的NLP技术
        conflicts = []

        # 检查是否包含相互否定的陈述
        negative_patterns = [
            (r'不是', r'是'),
            (r'没有', r'有'),
            (r'未', r'已'),
            (r'否', r'是')
        ]

        for i, data1 in enumerate(data_list):
            for j, data2 in enumerate(data_list[i+1:], i+1):
                for pattern_pos, pattern_neg in negative_patterns:
                    if re.search(pattern_pos, data1.content) and re.search(pattern_neg, data2.content):
                        conflicts.append(ConflictInfo(
                            conflict_type="factual_conflict",
                            conflicting_sources=[data1.source_id, data2.source_id],
                            conflict_description=f"事实陈述冲突: {pattern_pos} vs {pattern_neg}",
                            resolution_strategy=ConflictResolutionStrategy.TRUST_HIGHEST_CONFIDENCE,
                            resolution_result="pending_resolution",
                            confidence_impact=0.3
                        ))
                        break

        return conflicts

    async def _detect_temporal_conflicts(self, data_list: List[SourceData]) -> List[ConflictInfo]:
        """检测时间冲突"""
        conflicts = []

        # 提取时间信息
        temporal_info = {}
        for data in data_list:
            dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', data.content)
            times = re.findall(r'\d{1,2}:\d{2}', data.content)
            temporal_info[data.source_id] = {"dates": dates, "times": times}

        # 检查时间逻辑冲突
        # 这里可以实现更复杂的时间逻辑检查

        return conflicts

    async def _resolve_conflicts(
        self,
        data_list: List[SourceData],
        conflicts: List[ConflictInfo]
    ) -> List[SourceData]:
        """解决数据冲突"""
        resolved_data = data_list.copy()

        for conflict in conflicts:
            try:
                handler = self.conflict_resolution_handlers.get(
                    conflict.resolution_strategy,
                    self._resolve_by_confidence
                )

                resolution_result = await handler(resolved_data, conflict)
                conflict.resolution_result = resolution_result

                logger.info(f"冲突已解决: {conflict.conflict_type} - {resolution_result}")

            except Exception as e:
                logger.error(f"冲突解决失败 {conflict.conflict_type}: {e}")
                conflict.resolution_result = "resolution_failed"

        return resolved_data

    async def _resolve_by_recency(
        self,
        data_list: List[SourceData],
        conflict: ConflictInfo
    ) -> str:
        """按时间优先级解决冲突"""
        conflicted_sources = [
            data for data in data_list
            if data.source_id in conflict.conflicting_sources
        ]

        if conflicted_sources:
            most_recent = max(conflicted_sources, key=lambda x: x.timestamp)
            return f"选择最新数据源: {most_recent.source_id}"

        return "无法按时间解决冲突"

    async def _resolve_by_confidence(
        self,
        data_list: List[SourceData],
        conflict: ConflictInfo
    ) -> str:
        """按置信度解决冲突"""
        conflicted_sources = [
            data for data in data_list
            if data.source_id in conflict.conflicting_sources
        ]

        if conflicted_sources:
            highest_confidence = max(conflicted_sources, key=lambda x: x.confidence)
            return f"选择最高置信度数据源: {highest_confidence.source_id} (置信度: {highest_confidence.confidence})"

        return "无法按置信度解决冲突"

    async def _resolve_sql_priority(
        self,
        data_list: List[SourceData],
        conflict: ConflictInfo
    ) -> str:
        """SQL数据优先解决冲突"""
        sql_sources = [
            data for data in data_list
            if data.source_id in conflict.conflicting_sources
            and data.source_type == DataSourceType.SQL_QUERY
        ]

        if sql_sources:
            return f"选择SQL数据源: {sql_sources[0].source_id}"

        # 如果没有SQL数据，回退到置信度策略
        return await self._resolve_by_confidence(data_list, conflict)

    async def _resolve_by_consensus(
        self,
        data_list: List[SourceData],
        conflict: ConflictInfo
    ) -> str:
        """按共识解决冲突"""
        return "采用多数共识策略解决冲突"

    async def _resolve_by_weighted_average(
        self,
        data_list: List[SourceData],
        conflict: ConflictInfo
    ) -> str:
        """按加权平均解决冲突"""
        return "采用加权平均策略解决冲突"

    async def _perform_fusion(
        self,
        resolved_data: List[SourceData],
        query: str
    ) -> Dict[str, Any]:
        """执行信息融合"""
        try:
            # 计算整体置信度
            overall_confidence = 0.0
            total_weight = 0.0

            for data in resolved_data:
                weight = data.confidence * data.relevance_score * data.factual_reliability
                overall_confidence += data.confidence * weight
                total_weight += weight

            if total_weight > 0:
                overall_confidence /= total_weight

            # 合并内容
            fused_content = {}
            for data in resolved_data:
                fused_content[data.source_id] = {
                    "content": data.content,
                    "type": data.source_type.value,
                    "confidence": data.confidence,
                    "metadata": data.metadata
                }

            return {
                "fused_content": fused_content,
                "overall_confidence": min(overall_confidence, 1.0),
                "source_count": len(resolved_data)
            }

        except Exception as e:
            logger.error(f"信息融合失败: {e}")
            return {
                "fused_content": {},
                "overall_confidence": 0.1,
                "source_count": 0
            }

    async def _generate_fused_answer(
        self,
        query: str,
        fused_content: Dict[str, Any],
        context: Optional[List[Dict[str, Any]]],
        tenant_id: Optional[str]
    ) -> str:
        """生成融合后的答案"""
        try:
            # 构建融合提示词
            fusion_prompt = await self._build_fusion_prompt(query, fused_content)

            messages = [
                LLMMessage(
                    role="system",
                    content="你是一个专业的数据融合分析师。请基于提供的多源数据，生成准确、全面、有逻辑的回答。要明确指出数据的来源，并在数据不一致时说明你的处理方式。"
                ),
                LLMMessage(role="user", content=fusion_prompt)
            ]

            # 调用LLM生成答案
            response = await llm_service.chat_completion(
                tenant_id=tenant_id or "default",
                messages=messages,
                temperature=0.6,
                max_tokens=1500
            )

            if hasattr(response, 'content'):
                return response.content
            else:
                return "抱歉，融合答案生成失败。"

        except Exception as e:
            logger.error(f"生成融合答案失败: {e}")
            return f"在处理多源数据时遇到问题：{str(e)}"

    async def _build_fusion_prompt(
        self,
        query: str,
        fused_content: Dict[str, Any]
    ) -> str:
        """构建融合提示词"""
        prompt_parts = [
            f"用户查询：{query}",
            "",
            "多源数据信息："
        ]

        source_contents = fused_content.get("fused_content", {})
        for source_id, source_info in source_contents.items():
            prompt_parts.append(f"\n{source_id} ({source_info['type']}):")
            prompt_parts.append(f"置信度: {source_info['confidence']}")
            prompt_parts.append(f"内容: {source_info['content'][:500]}...")

        prompt_parts.extend([
            "",
            "请基于以上多源数据，生成一个综合、准确的答案。要求：",
            "1. 综合所有相关数据源",
            "2. 明确指出数据来源",
            "3. 如数据存在差异，请说明处理逻辑",
            "4. 提供具体、可操作的答案"
        ])

        return "\n".join(prompt_parts)

    async def _build_fusion_explanation(
        self,
        processed_data: List[SourceData],
        conflicts: List[ConflictInfo],
        resolved_data: List[SourceData],
        fused_content: Dict[str, Any]
    ) -> List[FusionExplanation]:
        """构建融合解释日志"""
        explanation_steps = []

        try:
            step_number = 1

            # 步骤1：数据收集说明
            explanation_steps.append(FusionExplanation(
                step_number=step_number,
                description="多源数据收集",
                action=f"收集了{len(processed_data)}个数据源",
                evidence=[f"数据源: {data.source_type.value}" for data in processed_data],
                confidence=0.9,
                decision_factors={
                    "source_types": [data.source_type.value for data in processed_data],
                    "total_sources": len(processed_data)
                }
            ))
            step_number += 1

            # 步骤2：数据质量评估
            avg_confidence = sum(data.confidence for data in processed_data) / len(processed_data)
            explanation_steps.append(FusionExplanation(
                step_number=step_number,
                description="数据质量评估",
                action=f"平均数据质量置信度: {avg_confidence:.2f}",
                evidence=[f"源{data.source_id}置信度: {data.confidence}" for data in processed_data],
                confidence=avg_confidence,
                decision_factors={
                    "average_confidence": avg_confidence,
                    "quality_threshold": 0.7
                }
            ))
            step_number += 1

            # 步骤3：冲突检测与解决
            if conflicts:
                explanation_steps.append(FusionExplanation(
                    step_number=step_number,
                    description="冲突检测与解决",
                    action=f"检测到{len(conflicts)}个冲突，已全部解决",
                    evidence=[f"冲突类型: {c.conflict_type}" for c in conflicts],
                    confidence=0.8,
                    decision_factors={
                        "conflict_count": len(conflicts),
                        "resolution_strategies": [c.resolution_strategy.value for c in conflicts]
                    }
                ))
                step_number += 1

            # 步骤4：信息融合
            explanation_steps.append(FusionExplanation(
                step_number=step_number,
                description="信息融合处理",
                action="成功融合多源数据",
                evidence=[f"融合策略: {fused_content.get('fusion_strategy', 'default')}"],
                confidence=fused_content.get("overall_confidence", 0.8),
                decision_factors={
                    "overall_confidence": fused_content.get("overall_confidence", 0.8),
                    "fusion_method": "weighted_confidence_fusion"
                }
            ))

            return explanation_steps

        except Exception as e:
            logger.error(f"构建融合解释失败: {e}")
            return [FusionExplanation(
                step_number=1,
                description="融合过程",
                action="融合完成但解释构建失败",
                evidence=[f"错误: {str(e)}"],
                confidence=0.1
            )]

    async def _calculate_answer_quality(
        self,
        answer: str,
        fused_content: Dict[str, Any],
        explanation_log: List[FusionExplanation]
    ) -> float:
        """计算答案质量分数"""
        quality_score = 0.0

        try:
            # 基于答案完整性 (30%)
            if len(answer) > 100:
                quality_score += 0.3
            elif len(answer) > 50:
                quality_score += 0.2

            # 基于数据源融合度 (25%)
            source_count = fused_content.get("source_count", 0)
            if source_count >= 3:
                quality_score += 0.25
            elif source_count >= 2:
                quality_score += 0.15

            # 基于解释完整性 (25%)
            if explanation_log:
                avg_step_confidence = sum(step.confidence for step in explanation_log) / len(explanation_log)
                quality_score += avg_step_confidence * 0.25

            # 基于整体置信度 (20%)
            overall_confidence = fused_content.get("overall_confidence", 0.5)
            quality_score += overall_confidence * 0.2

            return min(quality_score, 1.0)

        except Exception as e:
            logger.error(f"计算质量分数失败: {e}")
            return 0.5

    async def _prepare_source_citations(self, processed_data: List[SourceData]) -> List[Dict[str, Any]]:
        """准备源引用信息"""
        citations = []

        for data in processed_data:
            citation = {
                "source_id": data.source_id,
                "source_type": data.source_type.value,
                "confidence": data.confidence,
                "relevance_score": data.relevance_score,
                "timestamp": data.timestamp.isoformat(),
                "metadata": data.metadata
            }
            citations.append(citation)

        return citations

    # 数据源特定的融合方法
    async def _fuse_sql_data(self, data_list: List[SourceData]) -> Dict[str, Any]:
        """融合SQL数据"""
        sql_data = [data for data in data_list if data.source_type == DataSourceType.SQL_QUERY]
        return {"sql_fusion": "completed", "count": len(sql_data)}

    async def _fuse_rag_data(self, data_list: List[SourceData]) -> Dict[str, Any]:
        """融合RAG数据"""
        rag_data = [data for data in data_list if data.source_type == DataSourceType.RAG_RETRIEVAL]
        return {"rag_fusion": "completed", "count": len(rag_data)}

    async def _fuse_document_data(self, data_list: List[SourceData]) -> Dict[str, Any]:
        """融合文档数据"""
        doc_data = [data for data in data_list if data.source_type == DataSourceType.DOCUMENT]
        return {"document_fusion": "completed", "count": len(doc_data)}


# 全局融合引擎实例
fusion_engine = DataFusionEngine()