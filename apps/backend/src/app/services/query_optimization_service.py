"""
# [QUERY_OPTIMIZATION_SERVICE] 查询优化服务

## [HEADER]
**文件名**: query_optimization_service.py
**职责**: Story 2.4性能优化 - 提供高效的数据库查询方法、LRU缓存策略和性能监控
**作者**: Data Agent Team
**版本**: 1.0.0

## [INPUT]
- **db: AsyncSession** - 异步数据库会话
- **tenant_id: str** - 租户ID
- **status: Optional[DocumentStatus]** - 文档状态过滤器
- **file_type: Optional[str]** - 文件类型过滤器
- **search_query: Optional[str]** - 搜索查询
- **skip: int** - 分页跳过记录数
- **limit: int** - 分页限制记录数
- **sort_by: str** - 排序字段
- **sort_order: str** - 排序顺序
- **search_term: str** - 搜索词
- **query_type: Optional[QueryType]** - 缓存类型

## [OUTPUT]
- **QueryResult**: 查询结果封装
  - success: bool - 查询是否成功
  - data: Any - 结果数据
  - total: int - 总记录数
  - query_time_ms: float - 查询时间（毫秒）
  - cached: bool - 是否来自缓存
  - error: Optional[str] - 错误信息

**上游依赖** (已读取源码):
- [./data/models.py](./data/models.py) - 数据模型

**下游依赖** (需要反向索引分析):
- [./document_service.py](./document_service.py) - 文档服务（优化查询）

**调用方**:
- 文档列表查询优化
- 文档统计查询优化
- 租户摘要查询优化
- 文档搜索优化

## [STATE]
- **缓存TTL配置**:
  - DOCUMENT_LIST: 300秒（5分钟）
  - DOCUMENT_STATS: 600秒（10分钟）
  - TENANT_SUMMARY: 1800秒（30分钟）
  - SEARCH: 120秒（2分钟）
  - TREND_ANALYSIS: 3600秒（1小时）
- **内存缓存**: Dict[str, CacheEntry]（生产环境应使用Redis）
- **缓存统计**: hits, misses, evictions计数器
- **查询性能监控**: query_stats记录每个查询的性能指标
- **缓存键生成**: f"{query_type}:{tenant_id}:{params_hash}"
- **数据类**: QueryResult, CacheEntry使用@dataclass

## [SIDE-EFFECTS]
- **缓存读写**: _get_from_cache, _set_cache操作
- **缓存过期**: datetime.utcnow() - created_at < ttl检查
- **缓存淘汰**: 超时项自动删除并记录evictions
- **聚合查询**: func.count(), func.sum(), func.avg(), func.max()
- **异步查询**: AsyncSession.execute, scalars().all()
- **性能统计**: _record_query_stats记录count/time_ms/min/max
- **相关性计算**: _calculate_relevance_score字符串匹配分数
- **JSON序列化**: json.dumps(params, sort_keys=True)生成缓存键
- **缓存清理**: clear_cache支持按query_type清理或全部清理

## [POS]
**路径**: backend/src/app/services/query_optimization_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 data.models
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, or_, text
from sqlalchemy.orm import selectinload, joinedload

from src.app.data.models import KnowledgeDocument, Tenant, DocumentStatus
from src.app.core.logging import get_logger

logger = get_logger(__name__)


class QueryType(str, Enum):
    """查询类型枚举"""
    DOCUMENT_LIST = "document_list"
    DOCUMENT_STATS = "document_stats"
    TENANT_SUMMARY = "tenant_summary"
    SEARCH = "search"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class QueryResult:
    """查询结果封装"""
    success: bool
    data: Any
    total: int = 0
    query_time_ms: float = 0.0
    cached: bool = False
    error: Optional[str] = None


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_at: datetime
    ttl_seconds: int
    query_type: QueryType


class QueryOptimizationService:
    """查询优化服务"""

    def __init__(self):
        # 缓存配置
        self.cache_enabled = True
        self.cache_ttl_seconds = {
            QueryType.DOCUMENT_LIST: 300,      # 5分钟
            QueryType.DOCUMENT_STATS: 600,     # 10分钟
            QueryType.TENANT_SUMMARY: 1800,    # 30分钟
            QueryType.SEARCH: 120,             # 2分钟
            QueryType.TREND_ANALYSIS: 3600     # 1小时
        }

        # 内存缓存（生产环境应使用Redis）
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

        # 查询性能监控
        self.query_stats: Dict[str, Dict] = {}

    def _generate_cache_key(
        self,
        query_type: QueryType,
        tenant_id: str,
        **params
    ) -> str:
        """生成缓存键"""
        param_str = json.dumps(params, sort_keys=True, default=str)
        return f"{query_type.value}:{tenant_id}:{hash(param_str)}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.cache_enabled:
            return None

        entry = self.cache.get(cache_key)
        if entry:
            # 检查是否过期
            if datetime.utcnow() - entry.created_at < timedelta(seconds=entry.ttl_seconds):
                self.cache_stats["hits"] += 1
                return entry.data
            else:
                # 过期，删除
                del self.cache[cache_key]
                self.cache_stats["evictions"] += 1

        self.cache_stats["misses"] += 1
        return None

    def _set_cache(
        self,
        cache_key: str,
        data: Any,
        query_type: QueryType
    ) -> None:
        """设置缓存"""
        if not self.cache_enabled:
            return

        entry = CacheEntry(
            key=cache_key,
            data=data,
            created_at=datetime.utcnow(),
            ttl_seconds=self.cache_ttl_seconds[query_type],
            query_type=query_type
        )

        self.cache[cache_key] = entry

    async def get_documents_optimized(
        self,
        db: AsyncSession,
        tenant_id: str,
        status: Optional[DocumentStatus] = None,
        file_type: Optional[str] = None,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> QueryResult:
        """优化的文档查询"""
        start_time = datetime.utcnow()

        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(
                QueryType.DOCUMENT_LIST,
                tenant_id,
                status=status.value if status else None,
                file_type=file_type,
                search_query=search_query,
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order
            )

            # 尝试从缓存获取
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return QueryResult(
                    success=True,
                    data=cached_result["documents"],
                    total=cached_result["total"],
                    query_time_ms=query_time,
                    cached=True
                )

            # 构建基础查询
            base_query = select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_id == tenant_id
            )

            # 应用过滤器
            filters = []
            if status:
                filters.append(KnowledgeDocument.status == status)
            if file_type:
                filters.append(KnowledgeDocument.file_type == file_type)
            if search_query:
                filters.append(
                    or_(
                        KnowledgeDocument.file_name.ilike(f"%{search_query}%"),
                        # 如果添加了title字段，可以搜索标题
                        # KnowledgeDocument.title.ilike(f"%{search_query}%")
                    )
                )

            if filters:
                base_query = base_query.where(and_(*filters))

            # 计算总数
            count_query = select(func.count()).select_from(
                base_query.subquery()
            )
            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # 应用排序
            sort_column = getattr(KnowledgeDocument, sort_by, KnowledgeDocument.created_at)
            if sort_order.lower() == "desc":
                order_by = desc(sort_column)
            else:
                order_by = asc(sort_column)

            # 执行分页查询
            query = base_query.order_by(order_by).offset(skip).limit(limit)
            result = await db.execute(query)
            documents = result.scalars().all()

            # 转换为字典
            documents_data = []
            for doc in documents:
                doc_dict = doc.to_dict()
                documents_data.append(doc_dict)

            # 缓存结果
            cache_data = {
                "documents": documents_data,
                "total": total
            }
            self._set_cache(cache_key, cache_data, QueryType.DOCUMENT_LIST)

            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # 记录查询统计
            self._record_query_stats("get_documents_optimized", query_time, True)

            return QueryResult(
                success=True,
                data=documents_data,
                total=total,
                query_time_ms=query_time
            )

        except Exception as e:
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_query_stats("get_documents_optimized", query_time, False)

            logger.error(f"优化的文档查询失败: {str(e)}")
            return QueryResult(
                success=False,
                data=[],
                query_time_ms=query_time,
                error=str(e)
            )

    async def get_document_stats_optimized(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> QueryResult:
        """优化的文档统计查询"""
        start_time = datetime.utcnow()

        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(
                QueryType.DOCUMENT_STATS,
                tenant_id
            )

            # 尝试从缓存获取
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return QueryResult(
                    success=True,
                    data=cached_result,
                    query_time_ms=query_time,
                    cached=True
                )

            # 使用优化的聚合查询
            stats_query = select(
                func.count(KnowledgeDocument.id).label('total_documents'),
                func.count().filter(
                    KnowledgeDocument.status == DocumentStatus.READY
                ).label('ready_documents'),
                func.count().filter(
                    KnowledgeDocument.status == DocumentStatus.PENDING
                ).label('pending_documents'),
                func.count().filter(
                    KnowledgeDocument.status == DocumentStatus.INDEXING
                ).label('indexing_documents'),
                func.count().filter(
                    KnowledgeDocument.status == DocumentStatus.ERROR
                ).label('error_documents'),
                func.sum(KnowledgeDocument.file_size).label('total_file_size'),
                func.avg(KnowledgeDocument.file_size).label('avg_file_size'),
                func.max(KnowledgeDocument.created_at).label('last_upload_date')
            ).where(
                KnowledgeDocument.tenant_id == tenant_id
            )

            result = await db.execute(stats_query)
            row = result.first()

            # 获取文件类型统计
            file_type_query = select(
                KnowledgeDocument.file_type,
                func.count().label('count'),
                func.sum(KnowledgeDocument.file_size).label('total_size')
            ).where(
                KnowledgeDocument.tenant_id == tenant_id
            ).group_by(KnowledgeDocument.file_type)

            file_type_result = await db.execute(file_type_query)
            file_type_stats = {
                row.file_type: {
                    "count": row.count,
                    "total_size": row.total_size or 0
                }
                for row in file_type_result
            }

            # 组装统计数据
            stats_data = {
                "total_documents": row.total_documents or 0,
                "by_status": {
                    DocumentStatus.READY.value: row.ready_documents or 0,
                    DocumentStatus.PENDING.value: row.pending_documents or 0,
                    DocumentStatus.INDEXING.value: row.indexing_documents or 0,
                    DocumentStatus.ERROR.value: row.error_documents or 0
                },
                "by_file_type": file_type_stats,
                "total_size_bytes": row.total_file_size or 0,
                "total_size_mb": (row.total_file_size or 0) / (1024 * 1024),
                "avg_file_size": row.avg_file_size or 0,
                "last_upload_date": row.last_upload_date.isoformat() if row.last_upload_date else None
            }

            # 缓存结果
            self._set_cache(cache_key, stats_data, QueryType.DOCUMENT_STATS)

            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_query_stats("get_document_stats_optimized", query_time, True)

            return QueryResult(
                success=True,
                data=stats_data,
                query_time_ms=query_time
            )

        except Exception as e:
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_query_stats("get_document_stats_optimized", query_time, False)

            logger.error(f"文档统计查询失败: {str(e)}")
            return QueryResult(
                success=False,
                data={},
                query_time_ms=query_time,
                error=str(e)
            )

    async def get_tenant_summary_optimized(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> QueryResult:
        """优化的租户摘要查询"""
        start_time = datetime.utcnow()

        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(
                QueryType.TENANT_SUMMARY,
                tenant_id
            )

            # 尝试从缓存获取
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return QueryResult(
                    success=True,
                    data=cached_result,
                    query_time_ms=query_time,
                    cached=True
                )

            # 使用优化的连接查询获取租户信息
            tenant_query = select(Tenant).where(
                Tenant.id == tenant_id
            )
            tenant_result = await db.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()

            if not tenant:
                return QueryResult(
                    success=False,
                    data={},
                    error="租户不存在"
                )

            # 获取文档统计
            stats_query = select(
                func.count(KnowledgeDocument.id).label('document_count'),
                func.sum(KnowledgeDocument.file_size).label('total_size'),
                func.max(KnowledgeDocument.created_at).label('last_activity')
            ).where(
                KnowledgeDocument.tenant_id == tenant_id
            )

            stats_result = await db.execute(stats_query)
            stats_row = stats_result.first()

            # 获取最近上传的文档
            recent_docs_query = select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_id == tenant_id
            ).order_by(desc(KnowledgeDocument.created_at)).limit(5)

            recent_docs_result = await db.execute(recent_docs_query)
            recent_documents = [doc.to_dict() for doc in recent_docs_result.scalars().all()]

            # 组装租户摘要
            summary_data = {
                "tenant": {
                    "id": tenant.id,
                    "email": tenant.email,
                    "display_name": tenant.display_name,
                    "is_active": tenant.is_active,
                    "created_at": tenant.created_at.isoformat() if tenant.created_at else None
                },
                "document_summary": {
                    "total_documents": stats_row.document_count or 0,
                    "total_storage_used": stats_row.total_size or 0,
                    "total_storage_used_mb": (stats_row.total_size or 0) / (1024 * 1024),
                    "last_activity": stats_row.last_activity.isoformat() if stats_row.last_activity else None
                },
                "recent_documents": recent_documents
            }

            # 缓存结果
            self._set_cache(cache_key, summary_data, QueryType.TENANT_SUMMARY)

            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_query_stats("get_tenant_summary_optimized", query_time, True)

            return QueryResult(
                success=True,
                data=summary_data,
                query_time_ms=query_time
            )

        except Exception as e:
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_query_stats("get_tenant_summary_optimized", query_time, False)

            logger.error(f"租户摘要查询失败: {str(e)}")
            return QueryResult(
                success=False,
                data={},
                query_time_ms=query_time,
                error=str(e)
            )

    async def search_documents_optimized(
        self,
        db: AsyncSession,
        tenant_id: str,
        search_term: str,
        limit: int = 20
    ) -> QueryResult:
        """优化的文档搜索"""
        start_time = datetime.utcnow()

        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(
                QueryType.SEARCH,
                tenant_id,
                search_term=search_term,
                limit=limit
            )

            # 尝试从缓存获取
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return QueryResult(
                    success=True,
                    data=cached_result,
                    query_time_ms=query_time,
                    cached=True
                )

            # 使用全文搜索（如果支持）
            search_pattern = f"%{search_term}%"

            search_query = select(KnowledgeDocument).where(
                and_(
                    KnowledgeDocument.tenant_id == tenant_id,
                    or_(
                        KnowledgeDocument.file_name.ilike(search_pattern),
                        # 可以添加更多搜索字段
                    )
                )
            ).order_by(
                # 按相关性和创建时间排序
                desc(KnowledgeDocument.created_at)
            ).limit(limit)

            result = await db.execute(search_query)
            documents = result.scalars().all()

            # 转换为字典并计算相关性分数
            search_results = []
            for doc in documents:
                doc_dict = doc.to_dict()
                # 简单的相关性计算
                relevance_score = self._calculate_relevance_score(search_term, doc.file_name)
                doc_dict["relevance_score"] = relevance_score
                search_results.append(doc_dict)

            # 按相关性排序
            search_results.sort(key=lambda x: x["relevance_score"], reverse=True)

            # 缓存结果
            self._set_cache(cache_key, search_results, QueryType.SEARCH)

            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_query_stats("search_documents_optimized", query_time, True)

            return QueryResult(
                success=True,
                data=search_results,
                total=len(search_results),
                query_time_ms=query_time
            )

        except Exception as e:
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_query_stats("search_documents_optimized", query_time, False)

            logger.error(f"文档搜索失败: {str(e)}")
            return QueryResult(
                success=False,
                data=[],
                query_time_ms=query_time,
                error=str(e)
            )

    def _calculate_relevance_score(self, search_term: str, text: str) -> float:
        """计算搜索相关性分数"""
        search_term_lower = search_term.lower()
        text_lower = text.lower()

        score = 0.0

        # 完全匹配
        if search_term_lower == text_lower:
            score += 1.0
        # 开头匹配
        elif text_lower.startswith(search_term_lower):
            score += 0.8
        # 包含匹配
        elif search_term_lower in text_lower:
            score += 0.6
        # 部分匹配
        else:
            search_words = search_term_lower.split()
            text_words = text_lower.split()
            matching_words = sum(1 for word in search_words if word in text_words)
            if search_words:
                score += matching_words / len(search_words) * 0.4

        return score

    def _record_query_stats(self, query_name: str, query_time_ms: float, success: bool) -> None:
        """记录查询统计信息"""
        if query_name not in self.query_stats:
            self.query_stats[query_name] = {
                "count": 0,
                "total_time_ms": 0.0,
                "avg_time_ms": 0.0,
                "min_time_ms": float('inf'),
                "max_time_ms": 0.0,
                "success_count": 0,
                "error_count": 0
            }

        stats = self.query_stats[query_name]
        stats["count"] += 1
        stats["total_time_ms"] += query_time_ms
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
        stats["min_time_ms"] = min(stats["min_time_ms"], query_time_ms)
        stats["max_time_ms"] = max(stats["max_time_ms"], query_time_ms)

        if success:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.cache_stats,
            "total_requests": total_requests,
            "hit_rate_percent": hit_rate,
            "cached_items": len(self.cache)
        }

    def get_query_stats(self) -> Dict[str, Dict]:
        """获取查询性能统计"""
        return self.query_stats

    async def clear_cache(self, query_type: Optional[QueryType] = None) -> Dict[str, Any]:
        """清理缓存"""
        if query_type:
            # 只清理特定类型的缓存
            keys_to_remove = [
                key for key, entry in self.cache.items()
                if entry.query_type == query_type
            ]
            for key in keys_to_remove:
                del self.cache[key]

            return {
                "success": True,
                "message": f"已清理 {query_type.value} 类型的缓存",
                "cleared_count": len(keys_to_remove)
            }
        else:
            # 清理所有缓存
            cleared_count = len(self.cache)
            self.cache.clear()

            return {
                "success": True,
                "message": "已清理所有缓存",
                "cleared_count": cleared_count
            }


# 创建全局查询优化服务实例
query_optimization_service = QueryOptimizationService()