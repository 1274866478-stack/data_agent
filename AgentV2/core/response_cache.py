# -*- coding: utf-8 -*-
"""
Agent Response Cache - Agent 响应缓存
====================================

为 AgentV2 的完整响应提供缓存支持，避免重复的 LLM 调用。

核心功能:
    - 基于查询内容的智能缓存
    - 支持 tenant_id 隔离
    - TTL 过期机制
    - 缓存统计

使用场景:
    - 相同的自然语言查询
    - 租户隔离的响应缓存
    - 减少重复的 LLM API 调用

作者: BMad Master
版本: 1.0.0
"""

import hashlib
import json
import time
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Agent 响应缓存

    缓存完整的 Agent 响应，包括:
        - answer (AI 回答)
        - processing_steps (处理步骤)
        - chart_config (图表配置)
        - subagent_calls (子代理调用)
    """

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        初始化响应缓存

        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
            max_size: 最大缓存条目数
        """
        self._cache: Dict[str, tuple] = {}  # key -> (value, expire_time, metadata)
        self.ttl = ttl
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _make_key(
        self,
        query: str,
        tenant_id: str,
        connection_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成缓存键

        Args:
            query: 用户查询
            tenant_id: 租户 ID
            connection_id: 连接 ID
            context: 上下文信息

        Returns:
            缓存键 (MD5 hash)
        """
        # 标准化查询 (转小写，去空格)
        normalized_query = ' '.join(query.lower().strip().split())

        # 构建键数据
        key_data = {
            "query": normalized_query,
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            # 只包含上下文的关键信息，避免数据源列表影响缓存
            "has_data_sources": bool(context and context.get("data_sources")),
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(
        self,
        query: str,
        tenant_id: str,
        connection_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存的响应

        Args:
            query: 用户查询
            tenant_id: 租户 ID
            connection_id: 连接 ID
            context: 上下文信息

        Returns:
            缓存的响应，如果不存在或已过期则返回 None
        """
        key = self._make_key(query, tenant_id, connection_id, context)

        if key in self._cache:
            value, expire_time, metadata = self._cache[key]
            if time.time() < expire_time:
                self._hits += 1
                logger.info(f"Response cache HIT: query='{query[:30]}...', tenant={tenant_id}")
                return value
            else:
                # 缓存过期，删除
                del self._cache[key]
                logger.info(f"Response cache EXPIRED: query='{query[:30]}...'")

        self._misses += 1
        logger.info(f"Response cache MISS: query='{query[:30]}...', tenant={tenant_id}")
        return None

    def set(
        self,
        query: str,
        response: Dict[str, Any],
        tenant_id: str,
        connection_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        缓存响应

        Args:
            query: 用户查询
            response: Agent 响应
            tenant_id: 租户 ID
            connection_id: 连接 ID
            context: 上下文信息
        """
        # 检查缓存大小限制
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        key = self._make_key(query, tenant_id, connection_id, context)
        expire_time = time.time() + self.ttl

        # 元数据
        metadata = {
            "query_length": len(query),
            "response_length": len(json.dumps(response, default=str)),
            "cached_at": time.time(),
            "has_chart": bool(response.get("chart_config")),
        }

        self._cache[key] = (response, expire_time, metadata)
        logger.info(f"Response cached: query='{query[:30]}...', tenant={tenant_id}")

    def _evict_oldest(self) -> None:
        """淘汰最旧的缓存条目"""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k][2]["cached_at"]
        )
        del self._cache[oldest_key]
        self._evictions += 1
        logger.info(f"Cache eviction: removed oldest entry")

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        logger.info("Response cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

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
        """
        使租户的所有缓存失效

        Args:
            tenant_id: 租户 ID

        Returns:
            删除的缓存条目数
        """
        # 由于缓存键包含 tenant_id，我们需要重建缓存
        # 这是一个简单的实现，可能不是最高效的
        count = 0
        keys_to_remove = []

        for key in self._cache:
            # 从键中提取租户信息 (需要重新生成)
            # 这里使用一个简化的方法：记录所有键并在清除时重建
            keys_to_remove.append(key)

        # 注意：这个实现不完整，因为无法从键反推租户ID
        # 实际使用时可能需要维护一个租户到键的映射
        logger.warning(f"Tenant invalidation not fully implemented for tenant={tenant_id}")
        return 0


# 全局响应缓存实例
_response_cache = ResponseCache(ttl=300, max_size=1000)


def get_response_cache() -> ResponseCache:
    """获取全局响应缓存实例"""
    return _response_cache


def get_cache_stats() -> Dict[str, Any]:
    """获取所有缓存统计信息"""
    from ..tools.database_tools import get_cache_stats as get_db_cache_stats

    return {
        "response_cache": _response_cache.get_stats(),
        "database_cache": get_db_cache_stats(),
    }
