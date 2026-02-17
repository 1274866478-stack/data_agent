# -*- coding: utf-8 -*-
"""
知识库核心服务 - 双知识系统

提供双知识系统核心功能：
    1. 静态知识库（Static Knowledge）：人工维护的知识
    2. 动态学习库（Learning Knowledge）：自动发现的学习记录

核心功能:
    - 知识检索：向量相似度搜索 + 关键词过滤
    - 知识保存：验证后的查询和错误学习
    - 混合检索：结合语义和关键词的智能检索

作者: Data Agent Team
版本: 1.0.0
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from langchain_core.documents import Document

from .vector_store import ChromaVectorStore, create_vector_store

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

class KnowledgeType(str, Enum):
    """知识类型"""
    QUERY_TEMPLATE = "query_template"  # 查询模板
    BUSINESS_RULE = "business_rule"    # 业务规则
    SCHEMA_INFO = "schema_info"        # Schema 信息
    TABLE_MAPPING = "table_mapping"    # 表名映射
    ERROR_PATTERN = "error_pattern"    # 错误模式


class ErrorCategory(str, Enum):
    """错误类别（与 reflection_node.py 对应）"""
    SQL_SYNTAX = "sql_syntax"
    COLUMN_NOT_FOUND = "column_not_found"
    TABLE_NOT_FOUND = "table_not_found"
    ASSUMED_TABLE_NAME = "assumed_table_name"
    RELATION_ERROR = "relation_error"
    TYPE_MISMATCH = "type_mismatch"
    EMPTY_RESULT = "empty_result"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN = "unknown"


@dataclass
class KnowledgeEntry:
    """知识条目

    用于表示静态知识库中的条目，包括：
    - 查询模板：成功的 SQL 查询模式
    - 业务规则：业务逻辑和计算规则
    - Schema 信息：表结构和字段说明
    """
    id: str
    tenant_id: str
    knowledge_type: KnowledgeType
    question: str
    answer: str
    sql: Optional[str] = None
    tables: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    success_rate: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "knowledge_type": self.knowledge_type.value,
            "question": self.question,
            "answer": self.answer,
            "sql": self.sql,
            "tables": self.tables or [],
            "metadata": self.metadata,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def to_document(self) -> Document:
        """转换为 LangChain Document（用于向量存储）"""
        # 构建用于检索的文本
        content = f"问题: {self.question}\n答案: {self.answer}"
        if self.sql:
            content += f"\nSQL: {self.sql}"
        if self.tables:
            content += f"\n涉及表: {', '.join(self.tables)}"

        metadata = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "knowledge_type": self.knowledge_type.value,
            "tables": json.dumps(self.tables or [], ensure_ascii=False),
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            **self.metadata
        }

        return Document(page_content=content, metadata=metadata)


@dataclass
class LearningEntry:
    """学习条目

    用于表示动态学习库中的条目，包括：
    - 错误模式：常见错误及其修复方案
    - 修复建议：自动生成的修复 SQL
    """
    id: str
    tenant_id: str
    error_category: ErrorCategory
    error_message: str
    fix_suggestion: str
    corrected_sql: Optional[str] = None
    original_query: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    applied_count: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "error_category": self.error_category.value,
            "error_message": self.error_message,
            "fix_suggestion": self.fix_suggestion,
            "corrected_sql": self.corrected_sql,
            "original_query": self.original_query,
            "metadata": self.metadata,
            "applied_count": self.applied_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat()
        }

    def to_document(self) -> Document:
        """转换为 LangChain Document（用于向量存储）"""
        # 构建用于检索的文本
        content = f"错误类型: {self.error_category.value}\n"
        content += f"错误信息: {self.error_message}\n"
        content += f"修复建议: {self.fix_suggestion}"
        if self.corrected_sql:
            content += f"\n修正SQL: {self.corrected_sql}"
        if self.original_query:
            content += f"\n原始查询: {self.original_query}"

        metadata = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "error_category": self.error_category.value,
            "applied_count": self.applied_count,
            "success_rate": self.success_rate,
            **self.metadata
        }

        return Document(page_content=content, metadata=metadata)


# ============================================================================
# 知识库服务
# ============================================================================

class KnowledgeBaseService:
    """
    双知识系统核心服务

    提供：
    1. 静态知识库管理（query_templates, business_rules）
    2. 动态学习库管理（error_patterns, fix_suggestions）
    3. 混合检索（向量 + 关键词）
    4. 知识统计和清理
    """

    # 集合名称常量
    COLLECTION_STATIC_KNOWLEDGE = "static_knowledge"
    COLLECTION_LEARNINGS = "learnings"

    # 类级别缓存：{tenant_id: KnowledgeBaseService}
    _instances: Dict[str, 'KnowledgeBaseService'] = {}

    def __init__(
        self,
        tenant_id: str,
        persist_directory: Optional[Path] = None
    ):
        """初始化知识库服务

        Args:
            tenant_id: 租户 ID
            persist_directory: 持久化目录
        """
        self.tenant_id = tenant_id
        self.persist_directory = persist_directory or Path("./data/chroma_db")

        # 初始化向量存储
        self._static_store: Optional[ChromaVectorStore] = None
        self._learning_store: Optional[ChromaVectorStore] = None

        self._init_stores()

    def _init_stores(self):
        """初始化向量存储"""
        try:
            self._static_store = create_vector_store(
                tenant_id=self.tenant_id,
                collection_name=self.COLLECTION_STATIC_KNOWLEDGE,
                persist_directory=self.persist_directory
            )
            self._learning_store = create_vector_store(
                tenant_id=self.tenant_id,
                collection_name=self.COLLECTION_LEARNINGS,
                persist_directory=self.persist_directory
            )
            logger.info(f"知识库服务初始化完成，租户: {self.tenant_id}")
        except Exception as e:
            logger.error(f"知识库服务初始化失败: {e}")
            raise

    # ========================================================================
    # 静态知识库操作
    # ========================================================================

    async def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[KnowledgeType] = None,
        n_results: int = 5,
        min_score: float = 0.6,
        tables: Optional[List[str]] = None
    ) -> List[KnowledgeEntry]:
        """搜索静态知识

        Args:
            query: 查询文本
            knowledge_type: 知识类型过滤
            n_results: 返回结果数量
            min_score: 最小相似度分数
            tables: 表名过滤

        Returns:
            匹配的知识条目列表
        """
        # 构建过滤条件
        where = {}
        if knowledge_type:
            where["knowledge_type"] = knowledge_type.value

        # 执行向量搜索
        docs = await self._static_store.similarity_search(
            query=query,
            n_results=n_results * 2,
            where=where if where else None,
            min_score=min_score
        )

        # 转换为知识条目
        entries = []
        for doc in docs:
            entry = self._document_to_knowledge_entry(doc)
            if entry:
                # 表名过滤
                if tables and entry.tables:
                    if any(t in tables for t in entry.tables):
                        entries.append(entry)
                else:
                    entries.append(entry)

        # 按相似度和使用频率排序
        entries.sort(
            key=lambda e: (
                e.metadata.get("similarity_score", 0) * 0.7 +
                min(e.usage_count / 100, 0.3)
            ),
            reverse=True
        )

        return entries[:n_results]

    async def save_validated_query(
        self,
        question: str,
        sql: str,
        tables: List[str],
        answer: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """保存验证通过的查询到静态知识库

        Args:
            question: 用户问题
            sql: 生成的 SQL
            tables: 涉及的表
            answer: 答案描述
            metadata: 额外元数据

        Returns:
            知识条目 ID
        """
        entry_id = str(uuid.uuid4())

        # 构建答案描述
        if not answer:
            answer = f"使用 SQL 查询 {', '.join(tables)} 表获取数据"

        entry = KnowledgeEntry(
            id=entry_id,
            tenant_id=self.tenant_id,
            knowledge_type=KnowledgeType.QUERY_TEMPLATE,
            question=question,
            answer=answer,
            sql=sql,
            tables=tables,
            metadata=metadata or {},
            usage_count=1,
            success_rate=1.0
        )

        # 保存到向量存储
        doc = entry.to_document()
        await self._static_store.add_text(
            text=doc.page_content,
            metadata=doc.metadata,
            doc_id=entry_id
        )

        logger.info(f"保存验证查询: {entry_id} - {question[:50]}...")
        return entry_id

    async def get_similar_queries(
        self,
        question: str,
        threshold: float = 0.7,
        n_results: int = 3
    ) -> List[KnowledgeEntry]:
        """获取相似的历史查询

        Args:
            question: 用户问题
            threshold: 相似度阈值
            n_results: 返回结果数量

        Returns:
            相似查询列表
        """
        return await self.search_knowledge(
            query=question,
            knowledge_type=KnowledgeType.QUERY_TEMPLATE,
            n_results=n_results,
            min_score=threshold
        )

    async def increment_usage_count(self, entry_id: str) -> bool:
        """增加知识条目的使用计数

        Args:
            entry_id: 知识条目 ID

        Returns:
            是否成功
        """
        try:
            doc = await self._static_store.get_by_id(entry_id)
            if not doc:
                return False

            metadata = doc.metadata.copy()
            metadata["usage_count"] = metadata.get("usage_count", 0) + 1

            await self._static_store.update(
                doc_ids=[entry_id],
                metadatas=[metadata]
            )
            return True

        except Exception as e:
            logger.error(f"更新使用计数失败: {e}")
            return False

    # ========================================================================
    # 动态学习库操作
    # ========================================================================

    async def search_learnings(
        self,
        query: str,
        error_category: Optional[ErrorCategory] = None,
        n_results: int = 5,
        min_score: float = 0.5
    ) -> List[LearningEntry]:
        """搜索学习记录

        Args:
            query: 查询文本（错误信息或问题描述）
            error_category: 错误类别过滤
            n_results: 返回结果数量
            min_score: 最小相似度分数

        Returns:
            匹配的学习条目列表
        """
        # 构建过滤条件
        where = {}
        if error_category:
            where["error_category"] = error_category.value

        # 执行向量搜索
        docs = await self._learning_store.similarity_search(
            query=query,
            n_results=n_results * 2,
            where=where if where else None,
            min_score=min_score
        )

        # 转换为学习条目
        entries = []
        for doc in docs:
            entry = self._document_to_learning_entry(doc)
            if entry:
                entries.append(entry)

        # 按相似度和成功率排序
        entries.sort(
            key=lambda e: (
                e.metadata.get("similarity_score", 0) * 0.6 +
                e.success_rate * 0.4
            ),
            reverse=True
        )

        return entries[:n_results]

    async def save_learning(
        self,
        error_category: ErrorCategory,
        error_message: str,
        fix_suggestion: str,
        corrected_sql: Optional[str] = None,
        original_query: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """保存错误学习到动态学习库

        Args:
            error_category: 错误类别
            error_message: 错误消息
            fix_suggestion: 修复建议
            corrected_sql: 修正后的 SQL
            original_query: 原始查询
            metadata: 额外元数据

        Returns:
            学习条目 ID
        """
        learning_id = str(uuid.uuid4())

        entry = LearningEntry(
            id=learning_id,
            tenant_id=self.tenant_id,
            error_category=error_category,
            error_message=error_message,
            fix_suggestion=fix_suggestion,
            corrected_sql=corrected_sql,
            original_query=original_query,
            metadata=metadata or {},
            applied_count=0,
            success_rate=0.0
        )

        # 保存到向量存储
        doc = entry.to_document()
        await self._learning_store.add_text(
            text=doc.page_content,
            metadata=doc.metadata,
            doc_id=learning_id
        )

        logger.info(f"保存学习记录: {learning_id} - {error_category.value}")
        return learning_id

    async def get_similar_errors(
        self,
        error_message: str,
        error_category: Optional[ErrorCategory] = None,
        threshold: float = 0.6,
        n_results: int = 3
    ) -> List[LearningEntry]:
        """获取相似的历史错误

        Args:
            error_message: 错误消息
            error_category: 错误类别
            threshold: 相似度阈值
            n_results: 返回结果数量

        Returns:
            相似错误列表
        """
        return await self.search_learnings(
            query=error_message,
            error_category=error_category,
            n_results=n_results,
            min_score=threshold
        )

    async def update_learning_success(
        self,
        learning_id: str,
        success: bool
    ) -> bool:
        """更新学习记录的成功率

        Args:
            learning_id: 学习条目 ID
            success: 是否成功应用

        Returns:
            是否成功
        """
        try:
            doc = await self._learning_store.get_by_id(learning_id)
            if not doc:
                return False

            metadata = doc.metadata.copy()

            # 更新应用计数和成功率
            applied_count = metadata.get("applied_count", 0) + 1
            current_rate = metadata.get("success_rate", 0.0)

            # 计算新的成功率（简单移动平均）
            new_rate = (current_rate * (applied_count - 1) + (1.0 if success else 0.0)) / applied_count

            metadata["applied_count"] = applied_count
            metadata["success_rate"] = new_rate
            metadata["last_applied_at"] = datetime.now().isoformat()

            await self._learning_store.update(
                doc_ids=[learning_id],
                metadatas=[metadata]
            )
            return True

        except Exception as e:
            logger.error(f"更新学习成功率失败: {e}")
            return False

    # ========================================================================
    # 混合检索
    # ========================================================================

    async def hybrid_search(
        self,
        query: str,
        n_results: int = 5,
        include_learnings: bool = True
    ) -> Dict[str, List]:
        """混合检索：同时搜索静态知识和动态学习

        Args:
            query: 查询文本
            n_results: 每类返回结果数量
            include_learnings: 是否包含学习记录

        Returns:
            包含 "knowledge" 和 "learnings" 键的字典
        """
        results = {
            "knowledge": [],
            "learnings": []
        }

        # 搜索静态知识
        knowledge_entries = await self.search_knowledge(
            query=query,
            n_results=n_results,
            min_score=0.5
        )
        results["knowledge"] = [e.to_dict() for e in knowledge_entries]

        # 搜索学习记录
        if include_learnings:
            learning_entries = await self.search_learnings(
                query=query,
                n_results=n_results,
                min_score=0.4
            )
            results["learnings"] = [e.to_dict() for e in learning_entries]

        return results

    # ========================================================================
    # 统计和清理
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息

        Returns:
            统计信息字典
        """
        return {
            "tenant_id": self.tenant_id,
            "static_knowledge_count": self._static_store.count() if self._static_store else 0,
            "learning_count": self._learning_store.count() if self._learning_store else 0
        }

    async def cleanup_low_quality_learnings(
        self,
        min_success_rate: float = 0.3,
        min_applied_count: int = 5
    ) -> int:
        """清理低质量的学习记录

        Args:
            min_success_rate: 最小成功率阈值
            min_applied_count: 最小应用次数阈值

        Returns:
            删除的记录数
        """
        # 这里需要实现遍历和删除逻辑
        # 由于 ChromaDB 的限制，可能需要获取所有记录后过滤
        logger.info("清理低质量学习记录功能待实现")
        return 0

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _document_to_knowledge_entry(self, doc: Document) -> Optional[KnowledgeEntry]:
        """将 Document 转换为 KnowledgeEntry"""
        try:
            metadata = doc.metadata
            return KnowledgeEntry(
                id=metadata.get("id", str(uuid.uuid4())),
                tenant_id=metadata.get("tenant_id", self.tenant_id),
                knowledge_type=KnowledgeType(metadata.get("knowledge_type", "query_template")),
                question=metadata.get("question", ""),
                answer=metadata.get("answer", ""),
                sql=metadata.get("sql"),
                tables=json.loads(metadata.get("tables", "[]")) if metadata.get("tables") else [],
                metadata={k: v for k, v in metadata.items()
                         if k not in ["id", "tenant_id", "knowledge_type", "question", "answer", "sql", "tables", "usage_count", "success_rate"]},
                usage_count=metadata.get("usage_count", 0),
                success_rate=metadata.get("success_rate", 1.0)
            )
        except Exception as e:
            logger.error(f"转换知识条目失败: {e}")
            return None

    def _document_to_learning_entry(self, doc: Document) -> Optional[LearningEntry]:
        """将 Document 转换为 LearningEntry"""
        try:
            metadata = doc.metadata
            return LearningEntry(
                id=metadata.get("id", str(uuid.uuid4())),
                tenant_id=metadata.get("tenant_id", self.tenant_id),
                error_category=ErrorCategory(metadata.get("error_category", "unknown")),
                error_message=metadata.get("error_message", ""),
                fix_suggestion=metadata.get("fix_suggestion", ""),
                corrected_sql=metadata.get("corrected_sql"),
                original_query=metadata.get("original_query"),
                metadata={k: v for k, v in metadata.items()
                         if k not in ["id", "tenant_id", "error_category", "error_message", "fix_suggestion", "corrected_sql", "original_query", "applied_count", "success_rate"]},
                applied_count=metadata.get("applied_count", 0),
                success_rate=metadata.get("success_rate", 0.0)
            )
        except Exception as e:
            logger.error(f"转换学习条目失败: {e}")
            return None

    @classmethod
    def get_or_create_service(
        cls,
        tenant_id: str,
        persist_directory: Optional[Path] = None
    ) -> 'KnowledgeBaseService':
        """获取或创建知识库服务（单例模式）

        Args:
            tenant_id: 租户 ID
            persist_directory: 持久化目录

        Returns:
            KnowledgeBaseService 实例
        """
        if tenant_id not in cls._instances:
            cls._instances[tenant_id] = cls(
                tenant_id=tenant_id,
                persist_directory=persist_directory
            )

        return cls._instances[tenant_id]

    @classmethod
    def clear_cache(cls):
        """清除所有缓存的服务实例"""
        cls._instances.clear()


# ============================================================================
# 便捷函数
# ============================================================================

def create_knowledge_base(
    tenant_id: str,
    persist_directory: Optional[Path] = None
) -> KnowledgeBaseService:
    """创建知识库服务

    Args:
        tenant_id: 租户 ID
        persist_directory: 持久化目录

    Returns:
        KnowledgeBaseService 实例
    """
    return KnowledgeBaseService.get_or_create_service(
        tenant_id=tenant_id,
        persist_directory=persist_directory
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test_knowledge_base():
        print("=" * 60)
        print("知识库服务测试")
        print("=" * 60)

        # 创建知识库服务
        kb = create_knowledge_base(tenant_id="test_tenant")

        # 保存验证查询
        print("\n[测试] 保存验证查询")
        query_id = await kb.save_validated_query(
            question="2023年的销售趋势",
            sql="SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as total FROM orders WHERE EXTRACT(YEAR FROM order_date) = 2023 GROUP BY month ORDER BY month",
            tables=["orders"],
            answer="按月统计2023年销售趋势"
        )
        print(f"  保存查询: {query_id}")

        # 搜索知识
        print("\n[测试] 搜索知识")
        results = await kb.search_knowledge("2023销售数据", n_results=3)
        print(f"  找到 {len(results)} 条相关知识")
        for r in results:
            print(f"    - {r.question}: {r.sql[:50]}...")

        # 保存学习记录
        print("\n[测试] 保存学习记录")
        learning_id = await kb.save_learning(
            error_category=ErrorCategory.TABLE_NOT_FOUND,
            error_message="relation 'sales' does not exist",
            fix_suggestion="使用 list_tables() 查看实际表名",
            corrected_sql="SELECT * FROM 订单表"
        )
        print(f"  保存学习: {learning_id}")

        # 搜索学习记录
        print("\n[测试] 搜索学习记录")
        learnings = await kb.search_learnings("表不存在", n_results=3)
        print(f"  找到 {len(learnings)} 条学习记录")
        for l in learnings:
            print(f"    - {l.error_category}: {l.fix_suggestion[:50]}...")

        # 混合检索
        print("\n[测试] 混合检索")
        hybrid = await kb.hybrid_search("销售表查询", n_results=2)
        print(f"  知识: {len(hybrid['knowledge'])} 条")
        print(f"  学习: {len(hybrid['learnings'])} 条")

        # 统计信息
        print("\n[测试] 统计信息")
        stats = kb.get_stats()
        print(f"  静态知识: {stats['static_knowledge_count']}")
        print(f"  学习记录: {stats['learning_count']}")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    asyncio.run(test_knowledge_base())
