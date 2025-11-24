"""
缓存服务抽象层
支持内存缓存和Redis分布式缓存
"""

import json
import hashlib
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
import os

logger = logging.getLogger(__name__)


class CacheInterface(ABC):
    """缓存接口抽象类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存键"""
        pass

    @abstractmethod
    async def clear_tenant_cache(self, tenant_id: str) -> None:
        """清除租户所有缓存"""
        pass

    @abstractmethod
    async def clear_all(self) -> None:
        """清除所有缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        pass

    @abstractmethod
    async def get_size(self) -> int:
        """获取缓存大小"""
        pass


class MemoryCache(CacheInterface):
    """内存缓存实现（当前实现）"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.cache: Dict[str, Any] = {}
        self.ttl_cache: Dict[str, datetime] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cleanup_task = None

    async def _cleanup_expired(self):
        """清理过期缓存"""
        current_time = datetime.utcnow()
        expired_keys = []

        for key, expire_time in self.ttl_cache.items():
            if current_time > expire_time:
                expired_keys.append(key)

        for key in expired_keys:
            if key in self.cache:
                del self.cache[key]
            del self.ttl_cache[key]

    async def _ensure_size_limit(self):
        """确保缓存大小限制"""
        if len(self.cache) >= self.max_size:
            # 删除最旧的一半条目
            keys_to_remove = list(self.cache.keys())[:self.max_size // 2]
            for key in keys_to_remove:
                if key in self.cache:
                    del self.cache[key]
                if key in self.ttl_cache:
                    del self.ttl_cache[key]

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # 清理过期缓存
        await self._cleanup_expired()

        if key in self.cache:
            # 检查TTL
            if key in self.ttl_cache:
                if datetime.utcnow() > self.ttl_cache[key]:
                    # 过期，删除并返回None
                    del self.cache[key]
                    del self.ttl_cache[key]
                    return None
            return self.cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """设置缓存值"""
        ttl = ttl or self.default_ttl

        # 确保大小限制
        await self._ensure_size_limit()

        self.cache[key] = value
        self.ttl_cache[key] = datetime.utcnow() + timedelta(seconds=ttl)

    async def delete(self, key: str) -> None:
        """删除缓存键"""
        if key in self.cache:
            del self.cache[key]
        if key in self.ttl_cache:
            del self.ttl_cache[key]

    async def clear_tenant_cache(self, tenant_id: str) -> None:
        """清除租户所有缓存"""
        keys_to_remove = []

        for key in self.cache.keys():
            if key.startswith(f"tenant:{tenant_id}:"):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            await self.delete(key)

    async def clear_all(self) -> None:
        """清除所有缓存"""
        self.cache.clear()
        self.ttl_cache.clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        value = await self.get(key)
        return value is not None

    async def get_size(self) -> int:
        """获取缓存大小"""
        await self._cleanup_expired()
        return len(self.cache)


class RedisCache(CacheInterface):
    """Redis分布式缓存实现（准备）"""

    def __init__(self, redis_url: str = None, max_connections: int = None,
                 timeout: int = 5, socket_timeout: int = 5, socket_connect_timeout: int = 5):
        """
        初始化Redis缓存
        Args:
            redis_url: Redis连接URL
            max_connections: 最大连接数
            timeout: Redis操作超时时间
            socket_timeout: Socket超时时间
            socket_connect_timeout: Socket连接超时时间
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.max_connections = max_connections or int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        self.timeout = timeout or int(os.getenv("REDIS_TIMEOUT", "5"))
        self.socket_timeout = socket_timeout or int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        self.socket_connect_timeout = socket_connect_timeout or int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
        self.redis = None
        self.connection_pool = None
        self._connected = False

    async def _get_redis(self):
        """获取Redis连接"""
        if self.redis is None:
            try:
                # 尝试导入redis
                import redis.asyncio as redis
                from redis.asyncio import ConnectionPool

                # 创建连接池
                self.connection_pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
                self.redis = redis.Redis(connection_pool=self.connection_pool)

                # 测试连接
                await self.redis.ping()
                self._connected = True
                logger.info("Redis缓存连接成功")
            except ImportError:
                logger.error("Redis库未安装，无法使用Redis缓存")
                raise
            except Exception as e:
                logger.error(f"Redis连接失败: {e}")
                self._connected = False
                raise

        return self.redis

    async def _serialize_value(self, value: Any) -> str:
        """序列化值"""
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"缓存值序列化失败: {e}")
            raise

    async def _deserialize_value(self, serialized_value: str) -> Any:
        """反序列化值"""
        try:
            return json.loads(serialized_value)
        except Exception as e:
            logger.error(f"缓存值反序列化失败: {e}")
            return serialized_value

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            redis = await self._get_redis()
            serialized_value = await redis.get(key)

            if serialized_value:
                return await self._deserialize_value(serialized_value)
            return None
        except Exception as e:
            logger.error(f"Redis获取缓存失败: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值"""
        try:
            redis = await self._get_redis()
            serialized_value = await self._serialize_value(value)
            await redis.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Redis设置缓存失败: {e}")

    async def delete(self, key: str) -> None:
        """删除缓存键"""
        try:
            redis = await self._get_redis()
            await redis.delete(key)
        except Exception as e:
            logger.error(f"Redis删除缓存失败: {e}")

    async def clear_tenant_cache(self, tenant_id: str) -> None:
        """清除租户所有缓存"""
        try:
            redis = await self._get_redis()
            pattern = f"tenant:{tenant_id}:*"
            keys = await redis.keys(pattern)

            if keys:
                await redis.delete(*keys)
                logger.info(f"清除了租户 {tenant_id} 的 {len(keys)} 个缓存键")
        except Exception as e:
            logger.error(f"Redis清除租户缓存失败: {e}")

    async def clear_all(self) -> None:
        """清除所有缓存"""
        try:
            redis = await self._get_redis()
            pattern = "tenant:*"
            keys = await redis.keys(pattern)

            if keys:
                await redis.delete(*keys)
                logger.info(f"清除了所有 {len(keys)} 个缓存键")
        except Exception as e:
            logger.error(f"Redis清除所有缓存失败: {e}")

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        try:
            redis = await self._get_redis()
            return bool(await redis.exists(key))
        except Exception as e:
            logger.error(f"Redis检查缓存键存在性失败: {e}")
            return False

    async def get_size(self) -> int:
        """获取缓存大小"""
        try:
            redis = await self._get_redis()
            pattern = "tenant:*"
            keys = await redis.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis获取缓存大小失败: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            redis = await self._get_redis()

            # 测试基本操作
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.utcnow().isoformat()}

            # 测试写入
            await redis.setex(test_key, 10, await self._serialize_value(test_value))

            # 测试读取
            result = await redis.get(test_key)

            # 清理测试键
            await redis.delete(test_key)

            if result:
                return {
                    "status": "healthy",
                    "connected": self._connected,
                    "url": self.redis_url.split("@")[-1] if "@" in self.redis_url else self.redis_url,
                    "max_connections": self.max_connections,
                    "timeout": self.timeout,
                    "message": "Redis缓存运行正常"
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": self._connected,
                    "error": "读写测试失败",
                    "message": "Redis缓存存在问题"
                }

        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "error": str(e),
                "message": "Redis缓存连接失败"
            }

    async def get_info(self) -> Dict[str, Any]:
        """获取Redis信息"""
        try:
            redis = await self._get_redis()
            info = await redis.info()

            return {
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
                "connected": self._connected
            }
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {
                "error": str(e),
                "connected": self._connected
            }

    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
        self._connected = False


class CacheFactory:
    """缓存工厂类"""

    _instances = {}

    @classmethod
    def create_cache(cls, cache_type: str = None, **kwargs) -> CacheInterface:
        """
        创建缓存实例
        Args:
            cache_type: 缓存类型 ('memory', 'redis')
            **kwargs: 缓存配置参数
        Returns:
            CacheInterface: 缓存接口实例
        """
        cache_type = cache_type or os.getenv("CACHE_TYPE", "memory").lower()

        # 使用单例模式
        instance_key = f"{cache_type}:{hash(tuple(sorted(kwargs.items())))}"
        if instance_key in cls._instances:
            return cls._instances[instance_key]

        try:
            if cache_type == "redis":
                # Redis 缓存需要配置参数
                redis_kwargs = {
                    'redis_url': kwargs.get('redis_url') or os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    'max_connections': kwargs.get('max_connections') or int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
                    'timeout': kwargs.get('timeout') or int(os.getenv("REDIS_TIMEOUT", "5")),
                    'socket_timeout': kwargs.get('socket_timeout') or int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
                    'socket_connect_timeout': kwargs.get('socket_connect_timeout') or int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
                }
                cache = RedisCache(**redis_kwargs)
            elif cache_type == "memory":
                # 内存缓存需要配置参数
                memory_kwargs = {
                    'max_size': kwargs.get('max_size', 10000),
                    'default_ttl': kwargs.get('default_ttl', 3600)
                }
                cache = MemoryCache(**memory_kwargs)
            else:
                logger.warning(f"不支持的缓存类型: {cache_type}，使用内存缓存")
                cache = MemoryCache()

            cls._instances[instance_key] = cache
            logger.info(f"创建缓存实例: {cache_type}")
            return cache

        except Exception as e:
            logger.error(f"创建缓存实例失败: {e}")
            logger.info("回退到内存缓存")
            cache = MemoryCache()
            cls._instances[instance_key] = cache
            return cache

    @classmethod
    def get_default_cache(cls) -> CacheInterface:
        """获取默认缓存实例"""
        return cls.create_cache()

    @classmethod
    async def close_all_instances(cls):
        """关闭所有缓存实例"""
        for instance in cls._instances.values():
            if hasattr(instance, 'close'):
                await instance.close()
        cls._instances.clear()


def generate_cache_key(*args, **kwargs) -> str:
    """
    生成缓存键
    Args:
        *args: 位置参数
        **kwargs: 关键字参数
    Returns:
        str: 缓存键
    """
    # 构建缓存内容
    parts = []

    # 处理位置参数
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            parts.append(str(arg))
        else:
            parts.append(str(hash(str(arg))))

    # 处理关键字参数
    if kwargs:
        # 排序确保一致性
        sorted_kwargs = sorted(kwargs.items())
        for key, value in sorted_kwargs:
            parts.append(f"{key}={value}")

    # 合并内容
    content = ":".join(parts)

    # 生成MD5哈希
    return hashlib.md5(content.encode('utf-8')).hexdigest()


# 租户缓存键生成器
class TenantCacheKeyGenerator:
    """租户缓存键生成器"""

    @staticmethod
    def query_result(tenant_id: str, connection_id: int, query: str) -> str:
        """生成查询结果缓存键"""
        content = generate_cache_key("tenant", tenant_id, "connection", connection_id, "query", query)
        return f"tenant:{tenant_id}:query:{content}"

    @staticmethod
    def schema(tenant_id: str, connection_id: int) -> str:
        """生成schema缓存键"""
        return f"tenant:{tenant_id}:schema:{connection_id}"

    @staticmethod
    def stats(tenant_id: str) -> str:
        """生成统计信息缓存键"""
        return f"tenant:{tenant_id}:stats"

    @staticmethod
    def session(tenant_id: str, session_id: str) -> str:
        """生成会话缓存键"""
        return f"tenant:{tenant_id}:session:{session_id}"


# 全局缓存实例
default_cache = CacheFactory.get_default_cache()