# -*- coding: utf-8 -*-
"""Agent response cache."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CacheMetadata = Dict[str, Any]
CacheEntry = Tuple[Dict[str, Any], float, CacheMetadata]


class ResponseCache:
    """In-memory response cache with tenant isolation and TTL."""

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self.ttl = ttl
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = threading.RLock()

    @staticmethod
    def _normalize_query(query: str) -> str:
        return " ".join(query.lower().strip().split())

    @staticmethod
    def _now() -> float:
        return time.time()

    @staticmethod
    def _preview_query(query: str, max_len: int = 30) -> str:
        return f"{query[:max_len]}..."

    def _log_cache_event(self, event: str, query: str, tenant_id: str) -> None:
        logger.debug(
            "Response cache %s: query='%s', tenant=%s",
            event,
            self._preview_query(query),
            tenant_id,
        )

    @staticmethod
    def _calc_hit_rate(hits: int, misses: int) -> float:
        total_requests = hits + misses
        return hits / total_requests if total_requests > 0 else 0.0

    def _tenant_cache_keys(self, tenant_id: str) -> List[str]:
        return [
            key
            for key, (_, _, metadata) in self._cache.items()
            if metadata.get("tenant_id") == tenant_id
        ]

    def _make_key(
        self,
        query: str,
        tenant_id: str,
        connection_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        normalized_query = self._normalize_query(query)
        key_data = {
            "query": normalized_query,
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            "has_data_sources": bool(context and context.get("data_sources")),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def _build_metadata(
        *,
        query: str,
        response: Dict[str, Any],
        tenant_id: str,
        cached_at: float,
    ) -> CacheMetadata:
        return {
            "query_length": len(query),
            "response_length": len(json.dumps(response, default=str)),
            "cached_at": cached_at,
            "has_chart": bool(response.get("chart_config")),
            "tenant_id": tenant_id,
        }

    def get(
        self,
        query: str,
        tenant_id: str,
        connection_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        key = self._make_key(query, tenant_id, connection_id, context)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                self._log_cache_event("MISS", query, tenant_id)
                return None

            value, expire_time, _metadata = entry
            if self._now() < expire_time:
                self._hits += 1
                self._log_cache_event("HIT", query, tenant_id)
                return value

            del self._cache[key]
            self._misses += 1
            self._log_cache_event("EXPIRED", query, tenant_id)
            return None

    def set(
        self,
        query: str,
        response: Dict[str, Any],
        tenant_id: str,
        connection_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        key = self._make_key(query, tenant_id, connection_id, context)
        cached_at = self._now()
        expire_time = cached_at + self.ttl
        metadata = self._build_metadata(
            query=query,
            response=response,
            tenant_id=tenant_id,
            cached_at=cached_at,
        )

        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict_oldest_locked()
            self._cache[key] = (response, expire_time, metadata)

        self._log_cache_event("SET", query, tenant_id)

    def _evict_oldest_locked(self) -> None:
        if not self._cache:
            return

        oldest_key, _ = min(
            self._cache.items(),
            key=lambda item: item[1][2]["cached_at"],
        )
        del self._cache[oldest_key]
        self._evictions += 1
        logger.debug("Cache eviction: removed oldest entry")

    def _evict_oldest(self) -> None:
        with self._lock:
            self._evict_oldest_locked()

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
        logger.debug("Response cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            hit_rate = self._calc_hit_rate(self._hits, self._misses)
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": hit_rate,
                "ttl": self.ttl,
            }

    def invalidate_tenant(self, tenant_id: str) -> int:
        with self._lock:
            keys_to_remove = self._tenant_cache_keys(tenant_id)
            for key in keys_to_remove:
                del self._cache[key]
            removed = len(keys_to_remove)

        logger.debug(
            "Response cache tenant invalidation: tenant=%s removed=%s",
            tenant_id,
            removed,
        )
        return removed


_response_cache = ResponseCache(ttl=300, max_size=1000)


def get_response_cache() -> ResponseCache:
    """Return global response cache instance."""
    return _response_cache


def get_cache_stats() -> Dict[str, Any]:
    """Return combined cache stats for response + database tool cache."""
    from ..tools.database_tools import get_cache_stats as get_db_cache_stats

    return {
        "response_cache": _response_cache.get_stats(),
        "database_cache": get_db_cache_stats(),
    }
