"""
# [QUERY_OPTIMIZATION_SERVICE] ??????????

## [HEADER]
**?????**: query_optimization_service.py
**???**: Story 2.4??????? - ????ßπ???????????????LRU??????????????
**????**: Data Agent Team
**?∑⁄**: 1.0.0

## [INPUT]
- **db: AsyncSession** - ????????
- **tenant_id: str** - ??ID
- **status: Optional[DocumentStatus]** - ???????????
- **file_type: Optional[str]** - ????????????
- **search_query: Optional[str]** - ???????
- **skip: int** - ????????????
- **limit: int** - ???????????
- **sort_by: str** - ???????
- **sort_order: str** - ???????
- **search_term: str** - ??????
- **query_type: Optional[QueryType]** - ????????

## [OUTPUT]
- **QueryResult**: ?????????
  - success: bool - ????????
  - data: Any - ???????
  - total: int - ??????
  - query_time_ms: float - ??????????
  - cached: bool - ??????????
  - error: Optional[str] - ???????

**????????** (???????):
- [./data/models.py](./data/models.py) - ???????

**????????** (???????????????):
- [./document_service.py](./document_service.py) - ???????????????

**???°¬?**:
- ????ß“??????
- ???????????
- ??????????
- ??????????

## [STATE]
- **????TTL????**:
  - DOCUMENT_LIST: 300??5?????
  - DOCUMENT_STATS: 600??10?????
  - TENANT_SUMMARY: 1800??30?????
  - SEARCH: 120??2?????
  - TREND_ANALYSIS: 3600??1ß≥???
- **??ùH??**: Dict[str, CacheEntry]??????????????Redis??
- **???????**: hits, misses, evictions??????
- **?????????**: query_stats??????????????????
- **?????????**: f"{query_type}:{tenant_id}:{params_hash}"
- **??????**: QueryResult, CacheEntry???@dataclass

## [SIDE-EFFECTS]
- **?????ß’**: _get_from_cache, _set_cache????
- **???????**: datetime.utcnow() - created_at < ttl???
- **???????**: ????????????????evictions
- **?????**: func.count(), func.sum(), func.avg(), func.max()
- **?????**: AsyncSession.execute, scalars().all()
- **???????**: _record_query_stats???count/time_ms/min/max
- **????????**: _calculate_relevance_score???????????
- **JSON???ß›?**: json.dumps(params, sort_keys=True)????????
- **????????**: clear_cache????query_type????????????

## [POS]
**°§??**: backend/src/app/domains/rag_sql/query_optimization_service.py
**????**: Level 1 (?????)
**???????**: ??????? data.models
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
    """??????????"""
    DOCUMENT_LIST = "document_list"
    DOCUMENT_STATS = "document_stats"
    TENANT_SUMMARY = "tenant_summary"
    SEARCH = "search"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class QueryResult:
    """?????????"""
    success: bool
    data: Any
    total: int = 0
    query_time_ms: float = 0.0
    cached: bool = False
    error: Optional[str] = None


@dataclass
class CacheEntry:
    """???????"""
    key: str
    data: Any
    created_at: datetime
    ttl_seconds: int
    query_type: QueryType


class QueryOptimizationService:
    """??????????"""

    def __init__(self):
        # ????????
        self.cache_enabled = True
        self.cache_ttl_seconds = {
            QueryType.DOCUMENT_LIST: 300,      # 5????
            QueryType.DOCUMENT_STATS: 600,     # 10????
            QueryType.TENANT_SUMMARY: 1800,    # 30????
            QueryType.SEARCH: 120,             # 2????
            QueryType.TREND_ANALYSIS: 3600     # 1ß≥?
        }

        # ??ùH?ó§????????????Redis??
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

        # ?????????
        self.query_stats: Dict[str, Dict] = {}

    def _generate_cache_key(
        self,
        query_type: QueryType,
        tenant_id: str,
        **params
    ) -> str:
        """????????"""
        param_str = json.dumps(params, sort_keys=True, default=str)
        return f"{query_type.value}:{tenant_id}:{hash(param_str)}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """???????????"""
        if not self.cache_enabled:
            return None

        entry = self.cache.get(cache_key)
        if entry:
            # ?????????
            if datetime.utcnow() - entry.created_at < timedelta(seconds=entry.ttl_seconds):
                self.cache_stats["hits"] += 1
                return entry.data
            else:
                # ????????
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
        """???????"""
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
        """???????????"""
        start_time = datetime.utcnow()

        try:
            # ????????
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

            # ??????????
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

            # ???????????
            base_query = select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_id == tenant_id
            )

            # ??®¥?????
            filters = []
            if status:
                filters.append(KnowledgeDocument.status == status)
            if file_type:
                filters.append(KnowledgeDocument.file_type == file_type)
            if search_query:
                filters.append(
                    or_(
                        KnowledgeDocument.file_name.ilike(f"%{search_query}%"),
                        # ????????title??¶≤?????????????
                        # KnowledgeDocument.title.ilike(f"%{search_query}%")
                    )
                )

            if filters:
                base_query = base_query.where(and_(*filters))

            # ????????
            count_query = select(func.count()).select_from(
                base_query.subquery()
            )
            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # ???????
            sort_column = getattr(KnowledgeDocument, sort_by, KnowledgeDocument.created_at)
            if sort_order.lower() == "desc":
                order_by = desc(sort_column)
            else:
                order_by = asc(sort_column)

            # ??ßŸ?????
            query = base_query.order_by(order_by).offset(skip).limit(limit)
            result = await db.execute(query)
            documents = result.scalars().all()

            # ???????
            documents_data = []
            for doc in documents:
                doc_dict = doc.to_dict()
                documents_data.append(doc_dict)

            # ??????
            cache_data = {
                "documents": documents_data,
                "total": total
            }
            self._set_cache(cache_key, cache_data, QueryType.DOCUMENT_LIST)

            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # ?????????
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

            logger.error(f"??????????????: {str(e)}")
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
        """?????????????"""
        start_time = datetime.utcnow()

        try:
            # ????????
            cache_key = self._generate_cache_key(
                QueryType.DOCUMENT_STATS,
                tenant_id
            )

            # ??????????
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return QueryResult(
                    success=True,
                    data=cached_result,
                    query_time_ms=query_time,
                    cached=True
                )

            # ????????????
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

            # ?????????????
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

            # ??????????
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

            # ??????
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

            logger.error(f"???????????: {str(e)}")
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
        """????????????"""
        start_time = datetime.utcnow()

        try:
            # ????????
            cache_key = self._generate_cache_key(
                QueryType.TENANT_SUMMARY,
                tenant_id
            )

            # ??????????
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return QueryResult(
                    success=True,
                    data=cached_result,
                    query_time_ms=query_time,
                    cached=True
                )

            # ??????????????????????
            tenant_query = select(Tenant).where(
                Tenant.id == tenant_id
            )
            tenant_result = await db.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()

            if not tenant:
                return QueryResult(
                    success=False,
                    data={},
                    error="????????"
                )

            # ?????????
            stats_query = select(
                func.count(KnowledgeDocument.id).label('document_count'),
                func.sum(KnowledgeDocument.file_size).label('total_size'),
                func.max(KnowledgeDocument.created_at).label('last_activity')
            ).where(
                KnowledgeDocument.tenant_id == tenant_id
            )

            stats_result = await db.execute(stats_query)
            stats_row = stats_result.first()

            # ??????????????
            recent_docs_query = select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_id == tenant_id
            ).order_by(desc(KnowledgeDocument.created_at)).limit(5)

            recent_docs_result = await db.execute(recent_docs_query)
            recent_documents = [doc.to_dict() for doc in recent_docs_result.scalars().all()]

            # ???????
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

            # ??????
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

            logger.error(f"??????????: {str(e)}")
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
        """????????????"""
        start_time = datetime.utcnow()

        try:
            # ????????
            cache_key = self._generate_cache_key(
                QueryType.SEARCH,
                tenant_id,
                search_term=search_term,
                limit=limit
            )

            # ??????????
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return QueryResult(
                    success=True,
                    data=cached_result,
                    query_time_ms=query_time,
                    cached=True
                )

            # ???????????????????
            search_pattern = f"%{search_term}%"

            search_query = select(KnowledgeDocument).where(
                and_(
                    KnowledgeDocument.tenant_id == tenant_id,
                    or_(
                        KnowledgeDocument.file_name.ilike(search_pattern),
                        # ?????????????????
                    )
                )
            ).order_by(
                # ??????????????????
                desc(KnowledgeDocument.created_at)
            ).limit(limit)

            result = await db.execute(search_query)
            documents = result.scalars().all()

            # ???????????????????
            search_results = []
            for doc in documents:
                doc_dict = doc.to_dict()
                # ????????????
                relevance_score = self._calculate_relevance_score(search_term, doc.file_name)
                doc_dict["relevance_score"] = relevance_score
                search_results.append(doc_dict)

            # ???????????
            search_results.sort(key=lambda x: x["relevance_score"], reverse=True)

            # ??????
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

            logger.error(f"??????????: {str(e)}")
            return QueryResult(
                success=False,
                data=[],
                query_time_ms=query_time,
                error=str(e)
            )

    def _calculate_relevance_score(self, search_term: str, text: str) -> float:
        """????????????????"""
        search_term_lower = search_term.lower()
        text_lower = text.lower()

        score = 0.0

        # ??????
        if search_term_lower == text_lower:
            score += 1.0
        # ??????
        elif text_lower.startswith(search_term_lower):
            score += 0.8
        # ???????
        elif search_term_lower in text_lower:
            score += 0.6
        # ???????
        else:
            search_words = search_term_lower.split()
            text_words = text_lower.split()
            matching_words = sum(1 for word in search_words if word in text_words)
            if search_words:
                score += matching_words / len(search_words) * 0.4

        return score

    def _record_query_stats(self, query_name: str, query_time_ms: float, success: bool) -> None:
        """????????????"""
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
        """?????????????"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.cache_stats,
            "total_requests": total_requests,
            "hit_rate_percent": hit_rate,
            "cached_items": len(self.cache)
        }

    def get_query_stats(self) -> Dict[str, Dict]:
        """?????????????"""
        return self.query_stats

    async def clear_cache(self, query_type: Optional[QueryType] = None) -> Dict[str, Any]:
        """???????"""
        if query_type:
            # ????????????????
            keys_to_remove = [
                key for key, entry in self.cache.items()
                if entry.query_type == query_type
            ]
            for key in keys_to_remove:
                del self.cache[key]

            return {
                "success": True,
                "message": f"?????? {query_type.value} ????????",
                "cleared_count": len(keys_to_remove)
            }
        else:
            # ???????ß›???
            cleared_count = len(self.cache)
            self.cache.clear()

            return {
                "success": True,
                "message": "?????????ß›???",
                "cleared_count": cleared_count
            }


# ???????????????????
query_optimization_service = QueryOptimizationService()



