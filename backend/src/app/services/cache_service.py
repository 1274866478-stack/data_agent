"""
# [CACHE_SERVICE] 缓存服务抽象层

## [HEADER]
**文件名**: cache_service.py
**职责**: 提供统一的缓存抽象层，支持内存缓存和Redis分布式缓存，为RAG-SQL服务提供租户隔离的缓存支持
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 缓存服务抽象层

## [INPUT]
- **key: str** - 缓存键
- **value: Any** - 缓存值
- **ttl: Optional[int]** - 缓存过期时间（秒）
- **pattern: Optional[str]** - 缓存清理模式
- **tenant_id: str** - 租户ID
- **db_connection_id: int** - 数据库连接ID
- **query: str** - 自然语言查询
- **sql: str** - SQL语句
- **query_type: str** - 查询类型
- **query_pattern: str** - SQL模板模式
- **time_range: str** - 时间范围
- **cache_type: str** - 缓存类型（"memory" 或 "redis"）
- **max_size: int** - 内存缓存最大条目数
- **default_ttl: int** - 默认TTL（秒）
- **redis_url: str** - Redis连接URL
- **key_prefix: str** - Redis键前缀
- **cache: CacheInterface** - 缓存实例
- **key_generator: Callable** - 自定义键生成函数

## [OUTPUT]
- **Optional[Any]** - 缓存值（CacheInterface.get）
- **bool** - 操作是否成功（CacheInterface.set, delete, exists）
- **int** - 清理的缓存条目数（CacheInterface.clear）
- **Dict[str, Any]** - 缓存统计信息（CacheInterface.get_stats）
  - MemoryCache: type, size, max_size, hit_rate, hits, misses, sets, deletes, evictions
  - RedisCache: type, connected_clients, used_memory, total_commands_processed, keyspace_hits, keyspace_misses
- **CacheInterface** - 缓存实例（CacheFactory.create_cache）
- **CacheManager** - 缓存管理器实例（initialize_cache）

**上游依赖** (已读取源码):
- Python标准库: abc（抽象基类）, asyncio（异步操作）, functools（wraps装饰器）, hashlib（MD5哈希）, json（序列化）, logging（日志）, time（时间戳）
- 第三方库: redis.asyncio（Redis异步客户端，可选）

**下游依赖** (需要反向索引分析):
- [llm_service.py](./llm_service.py) - RAG-SQL服务使用缓存
- [agent_service.py](./agent_service.py) - Agent集成使用缓存

**调用方**:
- RAG-SQL服务缓存数据库schema
- Agent服务缓存查询结果
- 应用启动时初始化全局缓存管理器

## [STATE]
- **抽象基类**: CacheInterface定义缓存操作契约（get, set, delete, exists, clear, get_stats）
- **内存缓存**: MemoryCache使用Dict存储，支持LRU淘汰策略（max_size=1000）
- **Redis缓存**: RedisCache使用redis.asyncio客户端，支持分布式缓存（可选依赖）
- **租户隔离**: TenantCacheKeyGenerator生成租户级别缓存键（tenant:{tenant_id}:...）
- **缓存键生成**:
  - Schema缓存: `tenant:{tenant_id}:schema:{db_connection_id}`
  - Query缓存: `tenant:{tenant_id}:query:{query_hash}`（MD5哈希SQL）
  - SQL模板缓存: `tenant:{tenant_id}:sql_template:{query_type}:{pattern_hash}`
  - 性能缓存: `tenant:{tenant_id}:performance:{time_range}`
- **工厂模式**: CacheFactory.create_cache根据类型创建缓存实例
- **缓存装饰器**: @cached_result支持函数级缓存
- **全局单例**: _cache_manager全局缓存管理器实例
- **降级策略**: Redis不可用时自动降级到MemoryCache
- **默认配置**: max_size=1000, default_ttl=3600秒（1小时）

## [SIDE-EFFECTS]
- **字典操作**: MemoryCache中使用Dict读写缓存项
- **时间戳记录**: created_at, expires_at记录缓存创建和过期时间
- **过期检查**: _is_expired中time.time() > expires_at检查
- **LRU淘汰**: _evict_if_needed中min找出最旧项并删除
- **统计计数**: hits, misses, sets, deletes, evictions计数器更新
- **模式匹配**: fnmatch.fnmatch实现模式匹配清理（clear方法）
- **JSON序列化**: RedisCache中json.dumps/json.loads序列化值
- **Redis操作**: redis.get, redis.setex, redis.delete, redis.exists, redis.keys, redis.info
- **键前缀**: RedisCache中添加dataagent:前缀避免冲突
- **MD5哈希**: hashlib.md5(sql.encode()).hexdigest()生成缓存键哈希
- **全局状态修改**: initialize_cache修改_cache_manager全局变量
- **异常处理**: 所有缓存操作捕获异常并记录日志
- **装饰器副作用**: @cached_result包装函数，修改函数行为（缓存优先）
- **异步操作**: 所有缓存方法都是async（支持await）
- **日志记录**: logger.debug/info/warning/error记录缓存操作

## [POS]
**路径**: backend/src/app/services/cache_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 外部依赖redis库（可选）
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from functools import wraps
import hashlib
import logging

logger = logging.getLogger(__name__)


class CacheInterface(ABC):
    """缓存接口抽象基类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """清理缓存，支持模式匹配"""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        pass


class MemoryCache(CacheInterface):
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }

    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """检查缓存项是否过期"""
        if item.get("ttl") is None:
            return False
        return time.time() > item["expires_at"]

    def _evict_if_needed(self):
        """如果需要，清理最旧的缓存项"""
        if len(self.cache) >= self.max_size:
            # 找到最旧的项并删除
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k]["created_at"])
            del self.cache[oldest_key]
            self.stats["evictions"] += 1

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            self.stats["misses"] += 1
            return None

        item = self.cache[key]
        if self._is_expired(item):
            del self.cache[key]
            self.stats["misses"] += 1
            return None

        self.stats["hits"] += 1
        return item["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            self._evict_if_needed()

            ttl = ttl or self.default_ttl
            expires_at = time.time() + ttl if ttl > 0 else None

            self.cache[key] = {
                "value": value,
                "created_at": time.time(),
                "expires_at": expires_at,
                "ttl": ttl
            }

            self.stats["sets"] += 1
            return True
        except Exception as e:
            logger.error(f"内存缓存设置失败: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            self.stats["deletes"] += 1
            return True
        return False

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if key not in self.cache:
            return False

        item = self.cache[key]
        if self._is_expired(item):
            del self.cache[key]
            return False

        return True

    async def clear(self, pattern: Optional[str] = None) -> int:
        """清理缓存"""
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            return count

        # 简单的模式匹配
        import fnmatch
        keys_to_delete = [
            key for key in self.cache.keys()
            if fnmatch.fnmatch(key, pattern)
        ]

        for key in keys_to_delete:
            del self.cache[key]

        return len(keys_to_delete)

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "type": "memory",
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 4),
            **self.stats
        }


class RedisCache(CacheInterface):
    """Redis分布式缓存实现"""

    def __init__(self, redis_client, default_ttl: int = 3600, key_prefix: str = "dataagent:"):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        """生成Redis键"""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            redis_key = self._make_key(key)
            value = await self.redis.get(redis_key)

            if value is None:
                return None

            # 尝试JSON反序列化
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value.decode('utf-8') if isinstance(value, bytes) else value

        except Exception as e:
            logger.error(f"Redis获取缓存失败: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            redis_key = self._make_key(key)
            ttl = ttl or self.default_ttl

            # 序列化值
            if not isinstance(value, (str, bytes)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = value

            await self.redis.setex(redis_key, ttl, serialized_value)
            return True

        except Exception as e:
            logger.error(f"Redis设置缓存失败: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            redis_key = self._make_key(key)
            result = await self.redis.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis删除缓存失败: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            redis_key = self._make_key(key)
            result = await self.redis.exists(redis_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis检查缓存存在性失败: {e}")
            return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """清理缓存"""
        try:
            if pattern is None:
                # 删除所有带前缀的键
                pattern = f"{self.key_prefix}*"
            else:
                pattern = f"{self.key_prefix}{pattern}"

            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis清理缓存失败: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            info = await self.redis.info()
            return {
                "type": "redis",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"Redis获取统计信息失败: {e}")
            return {"type": "redis", "error": str(e)}


class TenantCacheKeyGenerator:
    """租户缓存键生成器"""

    @staticmethod
    def generate_schema_key(tenant_id: str, db_connection_id: int) -> str:
        """生成数据库schema缓存键"""
        return f"tenant:{tenant_id}:schema:{db_connection_id}"

    @staticmethod
    def generate_query_cache_key(tenant_id: str, query: str, sql: str) -> str:
        """生成查询结果缓存键"""
        # 对查询SQL进行哈希处理，避免键过长
        query_hash = hashlib.md5(sql.encode('utf-8')).hexdigest()
        return f"tenant:{tenant_id}:query:{query_hash}"

    @staticmethod
    def generate_sql_template_key(tenant_id: str, query_type: str, query_pattern: str) -> str:
        """生成SQL模板缓存键"""
        pattern_hash = hashlib.md5(query_pattern.encode('utf-8')).hexdigest()
        return f"tenant:{tenant_id}:sql_template:{query_type}:{pattern_hash}"

    @staticmethod
    def generate_performance_key(tenant_id: str, time_range: str) -> str:
        """生成性能统计缓存键"""
        return f"tenant:{tenant_id}:performance:{time_range}"

    @staticmethod
    def generate_v2_query_key(tenant_id: str, user_id: str, query: str, session_id: Optional[str] = None) -> str:
        """
        生成 V2 流式查询缓存键

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            query: 自然语言查询
            session_id: 会话ID（可选）

        Returns:
            缓存键
        """
        # 组合查询内容并哈希
        content = f"{tenant_id}:{user_id}:{query}"
        if session_id:
            content += f":{session_id}"
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return f"v2:query:{content_hash}"

    @staticmethod
    def generate_v2_session_key(tenant_id: str, session_id: str) -> str:
        """
        生成 V2 会话上下文缓存键

        Args:
            tenant_id: 租户ID
            session_id: 会话ID

        Returns:
            缓存键
        """
        return f"v2:session:{tenant_id}:{session_id}"


class CacheFactory:
    """缓存工厂类"""

    @staticmethod
    async def create_cache(cache_type: str = "memory", **kwargs) -> CacheInterface:
        """
        创建缓存实例

        Args:
            cache_type: 缓存类型 ("memory" 或 "redis")
            **kwargs: 缓存配置参数

        Returns:
            CacheInterface: 缓存实例
        """
        if cache_type.lower() == "memory":
            max_size = kwargs.get("max_size", 1000)
            default_ttl = kwargs.get("default_ttl", 3600)
            return MemoryCache(max_size=max_size, default_ttl=default_ttl)

        elif cache_type.lower() == "redis":
            try:
                # 尝试导入redis
                import redis.asyncio as aioredis

                redis_url = kwargs.get("redis_url", "redis://localhost:6379/0")
                default_ttl = kwargs.get("default_ttl", 3600)
                key_prefix = kwargs.get("key_prefix", "dataagent:")

                redis_client = await aioredis.from_url(redis_url)
                return RedisCache(redis_client, default_ttl=default_ttl, key_prefix=key_prefix)

            except ImportError:
                logger.warning("Redis不可用，回退到内存缓存")
                return await CacheFactory.create_cache("memory", **kwargs)
            except Exception as e:
                logger.error(f"Redis连接失败: {e}，回退到内存缓存")
                return await CacheFactory.create_cache("memory", **kwargs)

        else:
            raise ValueError(f"不支持的缓存类型: {cache_type}")


def cached_result(cache: CacheInterface, ttl: Optional[int] = None, key_generator=None):
    """
    缓存装饰器

    Args:
        cache: 缓存实例
        ttl: 缓存TTL
        key_generator: 自定义键生成函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                # 默认键生成策略
                func_name = func.__name__
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = f"func:{func_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

            # 尝试从缓存获取
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            logger.debug(f"缓存设置: {cache_key}")

            return result

        return wrapper
    return decorator


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache: CacheInterface):
        self.cache = cache
        self.key_gen = TenantCacheKeyGenerator()

    async def get_tenant_schema(self, tenant_id: str, db_connection_id: int) -> Optional[Dict[str, Any]]:
        """获取租户数据库schema缓存"""
        key = self.key_gen.generate_schema_key(tenant_id, db_connection_id)
        return await self.cache.get(key)

    async def set_tenant_schema(self, tenant_id: str, db_connection_id: int,
                              schema: Dict[str, Any], ttl: int = 1800) -> bool:
        """设置租户数据库schema缓存"""
        key = self.key_gen.generate_schema_key(tenant_id, db_connection_id)
        return await self.cache.set(key, schema, ttl)

    async def get_query_result(self, tenant_id: str, query: str, sql: str) -> Optional[Dict[str, Any]]:
        """获取查询结果缓存"""
        key = self.key_gen.generate_query_cache_key(tenant_id, query, sql)
        return await self.cache.get(key)

    async def set_query_result(self, tenant_id: str, query: str, sql: str,
                             result: Dict[str, Any], ttl: int = 600) -> bool:
        """设置查询结果缓存"""
        key = self.key_gen.generate_query_cache_key(tenant_id, query, sql)
        return await self.cache.set(key, result, ttl)

    async def clear_tenant_cache(self, tenant_id: str) -> int:
        """清理租户的所有缓存"""
        pattern = f"tenant:{tenant_id}:*"
        return await self.cache.clear(pattern)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return await self.cache.get_stats()


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


async def initialize_cache(cache_type: str = "memory", **kwargs) -> CacheManager:
    """
    初始化全局缓存管理器

    Args:
        cache_type: 缓存类型
        **kwargs: 缓存配置参数

    Returns:
        CacheManager: 缓存管理器实例
    """
    global _cache_manager

    cache = await CacheFactory.create_cache(cache_type, **kwargs)
    _cache_manager = CacheManager(cache)

    logger.info(f"缓存初始化完成: {cache_type}")
    return _cache_manager


def get_cache_manager() -> Optional[CacheManager]:
    """获取全局缓存管理器"""
    return _cache_manager