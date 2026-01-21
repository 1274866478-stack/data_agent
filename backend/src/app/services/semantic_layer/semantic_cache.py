"""
语义层缓存服务

提供基于 Redis 的语义查询结果缓存，提升查询性能。
"""

from typing import Optional, Any, Dict
import json
import hashlib

from ...core.config import settings


class SemanticCache:
    """语义层缓存服务"""

    def __init__(self):
        self._enabled = True
        self._local_cache: Dict[str, Any] = {}
        # TODO: Phase 2 - 集成 Redis
        # self._redis_client = None

    def _generate_cache_key(
        self,
        cube_name: str,
        query: Dict[str, Any],
        tenant_id: str
    ) -> str:
        """生成缓存键"""
        key_data = f"{tenant_id}:{cube_name}:{json.dumps(query, sort_keys=True)}"
        return f"semantic:query:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def get(
        self,
        cube_name: str,
        query: Dict[str, Any],
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        从缓存获取查询结果

        Args:
            cube_name: Cube 名称
            query: 查询参数
            tenant_id: 租户ID

        Returns:
            缓存的查询结果，如果不存在返回 None
        """
        if not self._enabled:
            return None

        cache_key = self._generate_cache_key(cube_name, query, tenant_id)

        # 本地缓存
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]

        # TODO: Redis 缓存
        # if self._redis_client:
        #     cached = await self._redis_client.get(cache_key)
        #     if cached:
        #         return json.loads(cached)

        return None

    async def set(
        self,
        cube_name: str,
        query: Dict[str, Any],
        tenant_id: str,
        result: Dict[str, Any],
        ttl: int = 300
    ):
        """
        将查询结果存入缓存

        Args:
            cube_name: Cube 名称
            query: 查询参数
            tenant_id: 租户ID
            result: 查询结果
            ttl: 缓存过期时间（秒），默认 5 分钟
        """
        if not self._enabled:
            return

        cache_key = self._generate_cache_key(cube_name, query, tenant_id)

        # 本地缓存
        self._local_cache[cache_key] = result

        # TODO: Redis 缓存
        # if self._redis_client:
        #     await self._redis_client.setex(
        #         cache_key,
        #         ttl,
        #         json.dumps(result, ensure_ascii=False)
        #     )

    async def invalidate_tenant(self, tenant_id: str):
        """
        使租户的所有缓存失效

        Args:
            tenant_id: 租户ID
        """
        # 本地缓存：删除所有该租户的缓存
        keys_to_delete = [
            k for k in self._local_cache.keys()
            if k.startswith(f"semantic:query:") and f":{tenant_id}:" in k
        ]
        for key in keys_to_delete:
            del self._local_cache[key]

        # TODO: Redis 缓存
        # if self._redis_client:
        #     pattern = f"semantic:query:*:{tenant_id}:*"
        #     keys = await self._redis_client.keys(pattern)
        #     if keys:
        #         await self._redis_client.delete(*keys)

    async def clear_all(self):
        """清除所有缓存"""
        self._local_cache.clear()

        # TODO: Redis 缓存
        # if self._redis_client:
        #     pattern = "semantic:query:*"
        #     keys = await self._redis_client.keys(pattern)
        #     if keys:
        #         await self._redis_client.delete(*keys)

    def set_enabled(self, enabled: bool):
        """启用或禁用缓存"""
        self._enabled = enabled
