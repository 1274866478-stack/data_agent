"""
# Core 性能优化器 - 连接池与缓存管理

## [HEADER]
**文件名**: performance_optimizer.py
**职责**: 提供通用连接池、智能缓存、批处理器和资源监控功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本，完整性能优化工具集

## [INPUT]
- 连接创建函数: Callable - 工厂函数创建新连接
- 缓存键: List[Any] - 缓存键值列表
- 批处理项: Any - 待处理的项目

## [OUTPUT]
- 连接对象: T - 从连接池获取的连接
- 缓存值: Any - 从缓存中获取的值
- 批处理结果: List[Any] - 批处理后的结果列表
- 性能指标: Dict[str, Any] - 性能统计数据

## [LINK]
**上游依赖**:
- Python标准库 - asyncio, threading, functools
- 第三方库 - dataclasses

**下游依赖**:
- 数据库连接管理 - 可用于database.py
- API缓存 - 可用于endpoint层

**调用方**:
- 数据库服务 - 连接复用
- API服务 - 响应缓存

## [POS]
**路径**: backend/src/app/core/performance_optimizer.py
**模块层级**: Level 2 (Core → Performance)
**依赖深度**: 1 层
"""

import asyncio
import time
import weakref
import json
import hashlib
from typing import Dict, Any, Optional, List, Callable, Union, TypeVar, Generic
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import wraps, lru_cache

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation_count: int = 0
    total_duration: float = 0.0
    success_count: int = 0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_operation_time: float = 0.0

    @property
    def average_duration(self) -> float:
        return self.total_duration / self.operation_count if self.operation_count > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return (self.success_count / self.operation_count * 100) if self.operation_count > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        total_cache_ops = self.cache_hits + self.cache_misses
        return (self.cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0.0


class ConnectionPool(Generic[T]):
    """通用连接池"""

    def __init__(
        self,
        create_connection: Callable[[], T],
        close_connection: Callable[[T], None],
        max_connections: int = 10,
        min_connections: int = 2,
        max_idle_time: float = 300.0,
        health_check: Optional[Callable[[T], bool]] = None
    ):
        self.create_connection = create_connection
        self.close_connection = close_connection
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.max_idle_time = max_idle_time
        self.health_check = health_check

        self._pool: deque = deque(maxlen=max_connections)
        self._in_use: weakref.WeakSet = weakref.WeakSet()
        self._lock = asyncio.Lock()
        self._created_count = 0
        self._metrics = PerformanceMetrics()

        # 启动后台任务
        self._maintenance_task = None

    async def initialize(self):
        """初始化连接池"""
        async with self._lock:
            # 创建最小连接数
            for _ in range(self.min_connections):
                try:
                    conn = await self._create_connection_safe()
                    self._pool.append(conn)
                except Exception as e:
                    logger.warning(f"初始化连接池失败: {e}")

        # 启动维护任务
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())

    async def _create_connection_safe(self) -> T:
        """安全创建连接"""
        if self._created_count >= self.max_connections:
            raise Exception("连接池已达到最大连接数")

        try:
            conn = await self._create_connection()
            self._created_count += 1
            return conn
        except Exception as e:
            logger.error(f"创建连接失败: {e}")
            raise

    @asynccontextmanager
    async def get_connection(self):
        """获取连接"""
        conn = None
        try:
            conn = await self._acquire_connection()
            yield conn
        finally:
            if conn is not None:
                await self._release_connection(conn)

    async def _acquire_connection(self) -> T:
        """获取连接"""
        start_time = time.time()

        async with self._lock:
            # 尝试从池中获取连接
            while self._pool:
                conn = self._pool.popleft()

                # 健康检查
                if self.health_check and not await self._run_health_check(conn):
                    await self._close_connection_safe(conn)
                    self._created_count -= 1
                    continue

                self._in_use.add(conn)
                duration = time.time() - start_time
                self._metrics.operation_count += 1
                self._metrics.total_duration += duration
                self._metrics.success_count += 1
                self._metrics.last_operation_time = time.time()
                return conn

            # 池中没有可用连接，创建新连接
            if self._created_count < self.max_connections:
                try:
                    conn = await self._create_connection_safe()
                    self._in_use.add(conn)
                    duration = time.time() - start_time
                    self._metrics.operation_count += 1
                    self._metrics.total_duration += duration
                    self._metrics.success_count += 1
                    self._metrics.last_operation_time = time.time()
                    return conn
                except Exception as e:
                    self._metrics.error_count += 1
                    raise Exception(f"无法创建新连接: {e}")

            # 达到最大连接数，等待
            self._metrics.error_count += 1
            raise Exception("连接池已满，无法获取连接")

    async def _release_connection(self, conn: T):
        """释放连接"""
        try:
            # 健康检查
            if self.health_check and not await self._run_health_check(conn):
                await self._close_connection_safe(conn)
                self._created_count -= 1
                return

            async with self._lock:
                if len(self._pool) < self.max_connections and conn in self._in_use:
                    self._pool.append(conn)
                    self._in_use.remove(conn)
                else:
                    await self._close_connection_safe(conn)
                    self._created_count -= 1

        except Exception as e:
            logger.error(f"释放连接时出错: {e}")

    async def _run_health_check(self, conn: T) -> bool:
        """运行健康检查"""
        try:
            if self.health_check:
                return await self.health_check(conn)
            return True
        except Exception:
            return False

    async def _close_connection_safe(self, conn: T):
        """安全关闭连接"""
        try:
            await self.close_connection(conn)
        except Exception as e:
            logger.warning(f"关闭连接时出错: {e}")

    async def _maintenance_loop(self):
        """维护循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟运行一次
                await self._maintenance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"连接池维护任务出错: {e}")

    async def _maintenance(self):
        """维护任务"""
        current_time = time.time()
        async with self._lock:
            # 清理过期连接
            expired_connections = []
            for i, (conn, created_time) in enumerate(list(self._pool)):
                if current_time - created_time > self.max_idle_time:
                    expired_connections.append(conn)

            for conn in expired_connections:
                self._pool.remove(conn)
                await self._close_connection_safe(conn)
                self._created_count -= 1

            # 确保最小连接数
            current_size = len(self._pool)
            needed = self.min_connections - current_size
            if needed > 0:
                for _ in range(min(needed, self.max_connections - self._created_count)):
                    try:
                        conn = await self._create_connection_safe()
                        self._pool.append(conn)
                    except Exception as e:
                        logger.warning(f"维护时创建连接失败: {e}")
                        break

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            "pool_size": len(self._pool),
            "in_use_count": len(self._in_use),
            "created_count": self._created_count,
            "max_connections": self.max_connections,
            "min_connections": self.min_connections,
            "metrics": {
                "operation_count": self._metrics.operation_count,
                "average_duration": self._metrics.average_duration,
                "success_rate": self._metrics.success_rate,
                "error_count": self._metrics.error_count
            }
        }

    async def close(self):
        """关闭连接池"""
        if self._maintenance_task:
            self._maintenance_task.cancel()

        async with self._lock:
            # 关闭池中的连接
            while self._pool:
                conn = self._pool.popleft()
                await self._close_connection_safe(conn)

            # 等待所有连接释放
            while self._in_use:
                await asyncio.sleep(0.1)


class SmartCache:
    """智能缓存系统"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._metrics = PerformanceMetrics()

    def _generate_key(self, key_parts: List[Any]) -> str:
        """生成缓存键"""
        key_str = json.dumps(key_parts, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    async def get(self, key_parts: List[Any]) -> Optional[Any]:
        """获取缓存值"""
        key = self._generate_key(key_parts)
        start_time = time.time()

        async with self._lock:
            self._metrics.operation_count += 1

            if key not in self._cache:
                self._metrics.cache_misses += 1
                return None

            entry = self._cache[key]
            current_time = time.time()

            # 检查是否过期
            if current_time - entry['created_at'] > entry['ttl']:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                self._metrics.cache_misses += 1
                return None

            # 更新访问时间
            self._access_times[key] = current_time
            self._metrics.cache_hits += 1
            self._metrics.success_count += 1

            duration = time.time() - start_time
            self._metrics.total_duration += duration

            return entry['value']

    async def set(self, key_parts: List[Any], value: Any, ttl: Optional[float] = None):
        """设置缓存值"""
        key = self._generate_key(key_parts)
        start_time = time.time()

        async with self._lock:
            # 检查容量限制
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()

            ttl = ttl or self.default_ttl
            current_time = time.time()

            self._cache[key] = {
                'value': value,
                'created_at': current_time,
                'ttl': ttl
            }
            self._access_times[key] = current_time

            duration = time.time() - start_time
            self._metrics.operation_count += 1
            self._metrics.total_duration += duration
            self._metrics.success_count += 1

    async def _evict_lru(self):
        """LRU淘汰"""
        if not self._access_times:
            return

        # 找到最久未访问的键
        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]

        # 删除条目
        if lru_key in self._cache:
            del self._cache[lru_key]
        del self._access_times[lru_key]

    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            self._access_times.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """获取缓存指标"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
            "metrics": {
                "operation_count": self._metrics.operation_count,
                "average_duration": self._metrics.average_duration,
                "success_rate": self._metrics.success_rate,
                "cache_hit_rate": self._metrics.cache_hit_rate,
                "cache_hits": self._metrics.cache_hits,
                "cache_misses": self._metrics.cache_misses
            }
        }


class BatchProcessor:
    """批处理器"""

    def __init__(
        self,
        process_func: Callable[[List[Any]], List[Any]],
        batch_size: int = 10,
        max_wait_time: float = 1.0,
        max_concurrent_batches: int = 5
    ):
        self.process_func = process_func
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.max_concurrent_batches = max_concurrent_batches

        self._queue: asyncio.Queue = asyncio.Queue()
        self._pending_batches: int = 0
        self._semaphore = asyncio.Semaphore(max_concurrent_batches)
        self._processor_task = None
        self._metrics = PerformanceMetrics()

    async def start(self):
        """启动批处理器"""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(self._process_loop())

    async def stop(self):
        """停止批处理器"""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

    async def add_item(self, item: Any) -> Any:
        """添加项目到批处理队列"""
        start_time = time.time()

        # 创建事件用于等待结果
        event = asyncio.Event()
        result_container = {'result': None, 'error': None}

        await self._queue.put((item, event, result_container))

        # 等待处理完成
        await event.wait()

        duration = time.time() - start_time
        self._metrics.operation_count += 1
        self._metrics.total_duration += duration

        if result_container['error']:
            self._metrics.error_count += 1
            raise result_container['error']
        else:
            self._metrics.success_count += 1
            return result_container['result']

    async def _process_loop(self):
        """批处理循环"""
        while True:
            try:
                batch = []
                events = []
                results = []

                # 收集批次
                deadline = time.time() + self.max_wait_time
                while (len(batch) < self.batch_size and time.time() < deadline):
                    try:
                        item, event, result = await asyncio.wait_for(
                            self._queue.get(),
                            timeout=max(0.1, deadline - time.time())
                        )
                        batch.append(item)
                        events.append(event)
                        results.append(result)
                    except asyncio.TimeoutError:
                        break

                if batch:
                    async with self._semaphore:
                        await self._process_batch(batch, events, results)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"批处理循环出错: {e}")

    async def _process_batch(self, batch: List[Any], events: List[asyncio.Event], results: List[Dict]):
        """处理单个批次"""
        start_time = time.time()

        try:
            # 调用处理函数
            processed_results = await self.process_func(batch)

            # 确保结果数量匹配
            if len(processed_results) != len(batch):
                raise ValueError(f"批处理结果数量不匹配: 期望 {len(batch)}, 实际 {len(processed_results)}")

            # 设置结果
            for i, (result, event, result_container) in enumerate(zip(processed_results, events, results)):
                result_container['result'] = result
                event.set()

        except Exception as e:
            # 设置错误结果
            for event, result_container in zip(events, results):
                result_container['error'] = e
                event.set()

        duration = time.time() - start_time
        logger.debug(f"批处理完成: {len(batch)} 项, 耗时: {duration:.3f}s")

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            "batch_size": self.batch_size,
            "max_wait_time": self.max_wait_time,
            "max_concurrent_batches": self.max_concurrent_batches,
            "queue_size": self._queue.qsize(),
            "pending_batches": self._pending_batches,
            "metrics": {
                "operation_count": self._metrics.operation_count,
                "average_duration": self._metrics.average_duration,
                "success_rate": self._metrics.success_rate,
                "error_count": self._metrics.error_count
            }
        }


class ResourceMonitor:
    """资源监控器"""

    def __init__(self):
        self._metrics = defaultdict(list)
        self._lock = threading.Lock()
        self._max_history = 1000

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录指标"""
        with self._lock:
            self._metrics[name].append({
                'timestamp': time.time(),
                'value': value,
                'labels': labels or {}
            })

            # 限制历史记录数量
            if len(self._metrics[name]) > self._max_history:
                self._metrics[name] = self._metrics[name][-self._max_history:]

    def get_metric_history(self, name: str, duration: Optional[float] = None) -> List[Dict]:
        """获取指标历史"""
        with self._lock:
            if name not in self._metrics:
                return []

            history = self._metrics[name]

            if duration is not None:
                cutoff_time = time.time() - duration
                history = [m for m in history if m['timestamp'] >= cutoff_time]

            return history

    def get_metric_summary(self, name: str, duration: Optional[float] = None) -> Dict[str, float]:
        """获取指标摘要"""
        history = self.get_metric_history(name, duration)

        if not history:
            return {}

        values = [m['value'] for m in history]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1] if values else 0
        }


# 全局资源监控器实例
resource_monitor = ResourceMonitor()


def performance_monitor(operation_name: str):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                resource_monitor.record_metric(f"{operation_name}_duration", duration)
                resource_monitor.record_metric(f"{operation_name}_success", 1)
                return result
            except Exception as e:
                duration = time.time() - start_time
                resource_monitor.record_metric(f"{operation_name}_duration", duration)
                resource_monitor.record_metric(f"{operation_name}_error", 1)
                raise

        return wrapper
    return decorator


@lru_cache(maxsize=128)
def memoize_async(ttl: float = 300.0):
    """异步记忆化装饰器"""
    def decorator(func):
        cache = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()

            # 检查缓存
            if key in cache:
                cached_data, cached_time = cache[key]
                if current_time - cached_time < ttl:
                    return cached_data
                else:
                    del cache[key]

            # 执行函数
            result = await func(*args, **kwargs)
            cache[key] = (result, current_time)

            # 清理过期缓存
            expired_keys = [
                k for k, (_, t) in cache.items()
                if current_time - t > ttl
            ]
            for k in expired_keys:
                del cache[k]

            return result

        return wrapper
    return decorator