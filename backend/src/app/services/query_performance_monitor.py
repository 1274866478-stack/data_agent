"""
# [QUERY_PERFORMANCE_MONITOR] 查询性能监控服务

## [HEADER]
**文件名**: query_performance_monitor.py
**职责**: 提供查询性能监控的统一接口，收集查询指标、系统资源、告警管理
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 查询性能监控服务

## [INPUT]
- **query_id: str** - 查询ID
- **tenant_id: str** - 租户ID
- **query_type: str** - 查询类型
- **alert_type: AlertType** - 告警类型
- **message: str** - 告警消息
- **metric_value: float** - 指标值
- **threshold_value: float** - 阈值
- **hours: int** - 时间范围（小时）
- **limit: int** - 限制数量
- **format: str** - 导出格式（json/csv）
- **history_size: int** - 历史记录大小
- **slow_query_threshold: float** - 慢查询阈值（秒）
- **max_alerts: int** - 最大告警数量

## [OUTPUT]
- **PerformanceAlert**: 性能告警对象
- **QueryMetrics**: 查询指标对象
- **SystemMetrics**: 系统指标对象
- **Dict[str, Any]**: 实时统计信息
  - total_queries, queries_per_second, cache_hit_rate, error_rate, slow_queries
  - avg_execution_time, uptime_hours, memory_usage_mb, cpu_usage_percent
- **Dict[str, Any]**: 租户性能报告
- **List[Dict[str, Any]]**: 慢查询列表
- **Dict[str, Any]**: 查询类型性能统计
- **List[Dict]]**: 性能警告列表
- **str**: 导出的指标数据（JSON/CSV格式）
- **Dict[str, Any]**: 健康状态
  - status: healthy/degraded/unhealthy
  - health_score: 0-100
  - issues: 问题列表

**上游依赖** (已读取源码):
- 无（独立监控服务）

**下游依赖** (需要反向索引分析):
- [llm_service.py](./llm_service.py) - LLM服务记录查询性能
- [query_optimization_service.py](./query_optimization_service.py) - 查询优化服务使用性能数据
- API端点展示监控指标和健康状态

**调用方**:
- LLM服务监控查询性能
- 查询优化服务分析慢查询
- API端点提供监控数据
- 运维脚本获取健康状态

## [STATE]
- **告警级别**: AlertLevel枚举（INFO, WARNING, CRITICAL）
- **告警类型**: AlertType枚举（SLOW_QUERY, HIGH_ERROR_RATE, HIGH_MEMORY, HIGH_CPU, LOW_CACHE_HIT, CONNECTION_POOL）
- **告警阈值**: thresholds字典
  - SLOW_QUERY: 5.0秒
  - HIGH_ERROR_RATE: 10.0%
  - HIGH_MEMORY: 85.0%
  - HIGH_CPU: 90.0%
  - LOW_CACHE_HIT: 30.0%
  - CONNECTION_POOL: 80.0%
- **告警管理器**: AlertManager
  - alerts: deque（最多500条）
  - active_alerts: 字典（活跃告警）
  - _alert_counter: 告警计数器
  - _lock: 线程锁
- **系统资源监控器**: SystemResourceMonitor
  - metrics_history: deque（最多1000条）
  - process: psutil.Process实例
  - _running: 监控运行状态
  - _monitor_task: 后台监控任务
- **查询性能监控器**: QueryPerformanceMonitor
  - query_history: deque（最多10000条）
  - tenant_history: 字典（租户历史）
  - query_type_stats: 字典（查询类型统计）
  - stats: 实时统计字典（total_queries, cache_hits, errors, slow_queries, start_time）
  - alert_manager: 告警管理器
  - resource_monitor: 资源监控器
  - _lock: 线程锁
- **后台检查**: _background_check（30秒间隔）
  - 收集系统指标
  - 检查资源告警（内存、CPU）
  - 检查错误率
  - 生成/解决告警
- **上下文管理器**: monitor_query（查询监控）
- **健康评分**: 基于错误率、响应时间、资源使用率、活跃告警

## [SIDE-EFFECTS]
- **psutil操作**: psutil.virtual_memory()获取内存，psutil.cpu_percent()获取CPU，psutil.disk_usage()获取磁盘
- **进程信息**: psutil.Process()获取当前进程信息
- **线程/连接数**: process.num_threads(), len(process.connections())
- **时间测量**: time.time()计算执行时间
- **内存测量**: psutil.Process().memory_info().rss / 1024 / 1024计算内存使用（MB）
- **哈希计算**: hashlib.md5(query_type.encode('utf-8')).hexdigest()计算查询哈希
- **统计计算**: statistics.mean/max/min计算平均值、最大值、最小值
- **百分比计算**: (cache_hits / total_queries * 100)计算缓存命中率
- **QPS计算**: total_queries / uptime计算每秒查询数
- **条件判断**: 检查阈值（metric_value >= threshold * 1.5判断CRITICAL）
- **上下文管理器**: @asynccontextmanager装饰monitor_query
- **异常处理**: try-except捕获异常，设置metrics.error = True
- **try-finally**: 确保记录查询指标
- **deque操作**: query_history.append(metrics)添加历史
- **列表推导式**: [m for m in tenant_queries if m.timestamp >= cutoff_time]过滤历史
- **排序**: slow.sort(key=lambda x: x.total_time, reverse=True)排序慢查询
- **百分位数**: sorted(times)[int(len(times) * 0.95)]计算P95
- **JSON序列化**: json.dumps(data, indent=2, ensure_ascii=False)导出JSON
- **健康评分**: health_score -= 20/15/5根据问题扣分
- **字典操作**: stats['total_queries'] += 1更新统计
- **异步任务**: asyncio.create_task(monitor_loop())创建后台监控
- **线程锁**: with self._lock保护共享数据
- **异常处理**: try-except捕获所有异常，记录日志
- **日志记录**: logger.warning记录告警，logger.error记录错误
- **全局单例**: query_perf_monitor全局实例

## [POS]
**路径**: backend/src/app/services/query_performance_monitor.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 无外部依赖（仅psutil）
"""

import time
import asyncio
import logging
import psutil
import threading
import hashlib
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型枚举"""
    SLOW_QUERY = "slow_query"
    HIGH_ERROR_RATE = "high_error_rate"
    HIGH_MEMORY = "high_memory"
    HIGH_CPU = "high_cpu"
    LOW_CACHE_HIT = "low_cache_hit"
    CONNECTION_POOL = "connection_pool"


@dataclass
class PerformanceAlert:
    """性能告警数据类"""
    alert_id: str
    alert_type: AlertType
    alert_level: AlertLevel
    message: str
    metric_value: float
    threshold_value: float
    tenant_id: Optional[str] = None
    timestamp: datetime = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "alert_level": self.alert_level.value,
            "message": self.message,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class QueryMetrics:
    """查询指标数据类"""
    query_id: str
    tenant_id: str
    query_type: str
    query_hash: str
    execution_time: float
    sql_generation_time: float
    sql_validation_time: float
    result_processing_time: float
    total_time: float
    row_count: int
    cache_hit: bool
    error: bool
    error_message: Optional[str] = None
    timestamp: datetime = None
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    database_time: float = 0.0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data.get('timestamp'):
            data['timestamp'] = data['timestamp'].isoformat()
        return data


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    open_files: int
    thread_count: int
    connection_count: int
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data.get('timestamp'):
            data['timestamp'] = data['timestamp'].isoformat()
        return data


class AlertManager:
    """告警管理器"""

    def __init__(self, max_alerts: int = 500):
        self.max_alerts = max_alerts
        self.alerts: deque = deque(maxlen=max_alerts)
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self._alert_counter = 0
        self._lock = threading.Lock()

        # 告警阈值配置
        self.thresholds = {
            AlertType.SLOW_QUERY: 5.0,  # 秒
            AlertType.HIGH_ERROR_RATE: 10.0,  # 百分比
            AlertType.HIGH_MEMORY: 85.0,  # 百分比
            AlertType.HIGH_CPU: 90.0,  # 百分比
            AlertType.LOW_CACHE_HIT: 30.0,  # 百分比
            AlertType.CONNECTION_POOL: 80.0  # 百分比
        }

    def _generate_alert_id(self) -> str:
        """生成告警ID"""
        self._alert_counter += 1
        return f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._alert_counter}"

    def create_alert(
        self,
        alert_type: AlertType,
        message: str,
        metric_value: float,
        tenant_id: Optional[str] = None
    ) -> PerformanceAlert:
        """创建告警"""
        with self._lock:
            threshold = self.thresholds.get(alert_type, 0)

            # 确定告警级别
            if metric_value >= threshold * 1.5:
                level = AlertLevel.CRITICAL
            elif metric_value >= threshold:
                level = AlertLevel.WARNING
            else:
                level = AlertLevel.INFO

            alert = PerformanceAlert(
                alert_id=self._generate_alert_id(),
                alert_type=alert_type,
                alert_level=level,
                message=message,
                metric_value=metric_value,
                threshold_value=threshold,
                tenant_id=tenant_id
            )

            self.alerts.append(alert)

            # 添加到活跃告警
            alert_key = f"{alert_type.value}_{tenant_id or 'system'}"
            self.active_alerts[alert_key] = alert

            logger.warning(f"性能告警: [{level.value}] {message}")

            return alert

    def resolve_alert(self, alert_type: AlertType, tenant_id: Optional[str] = None) -> bool:
        """解决告警"""
        with self._lock:
            alert_key = f"{alert_type.value}_{tenant_id or 'system'}"
            if alert_key in self.active_alerts:
                alert = self.active_alerts[alert_key]
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                del self.active_alerts[alert_key]
                logger.info(f"告警已解决: {alert.message}")
                return True
            return False

    def get_active_alerts(self, tenant_id: Optional[str] = None) -> List[PerformanceAlert]:
        """获取活跃告警"""
        with self._lock:
            if tenant_id:
                return [a for a in self.active_alerts.values()
                        if a.tenant_id == tenant_id or a.tenant_id is None]
            return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24, alert_type: Optional[AlertType] = None) -> List[Dict]:
        """获取告警历史"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        with self._lock:
            filtered = [a for a in self.alerts if a.timestamp >= cutoff_time]
            if alert_type:
                filtered = [a for a in filtered if a.alert_type == alert_type]
            return [a.to_dict() for a in filtered]

    def update_threshold(self, alert_type: AlertType, value: float):
        """更新告警阈值"""
        self.thresholds[alert_type] = value
        logger.info(f"更新告警阈值: {alert_type.value} = {value}")


class SystemResourceMonitor:
    """系统资源监控器"""

    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.metrics_history: deque = deque(maxlen=history_size)
        self.process = psutil.Process()
        self._running = False
        self._monitor_task = None
        self._lock = threading.Lock()

    def collect_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metrics = SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=disk.percent,
                open_files=len(self.process.open_files()) if hasattr(self.process, 'open_files') else 0,
                thread_count=self.process.num_threads(),
                connection_count=len(self.process.connections()) if hasattr(self.process, 'connections') else 0
            )

            with self._lock:
                self.metrics_history.append(metrics)

            return metrics
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return SystemMetrics(
                cpu_percent=0, memory_percent=0, memory_used_mb=0,
                memory_available_mb=0, disk_usage_percent=0,
                open_files=0, thread_count=0, connection_count=0
            )

    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前系统指标"""
        metrics = self.collect_metrics()
        return metrics.to_dict()

    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取历史指标"""
        with self._lock:
            recent = list(self.metrics_history)[-limit:]
            return [m.to_dict() for m in recent]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标汇总"""
        with self._lock:
            if not self.metrics_history:
                return {"error": "No metrics available"}

            recent = list(self.metrics_history)[-100:]

            cpu_values = [m.cpu_percent for m in recent]
            memory_values = [m.memory_percent for m in recent]

            return {
                "sample_count": len(recent),
                "cpu": {
                    "current": cpu_values[-1] if cpu_values else 0,
                    "average": statistics.mean(cpu_values) if cpu_values else 0,
                    "max": max(cpu_values) if cpu_values else 0,
                    "min": min(cpu_values) if cpu_values else 0
                },
                "memory": {
                    "current": memory_values[-1] if memory_values else 0,
                    "average": statistics.mean(memory_values) if memory_values else 0,
                    "max": max(memory_values) if memory_values else 0,
                    "min": min(memory_values) if memory_values else 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }

    async def start_background_monitoring(self, interval_seconds: int = 30):
        """启动后台监控"""
        if self._running:
            return

        self._running = True

        async def monitor_loop():
            while self._running:
                try:
                    self.collect_metrics()
                    await asyncio.sleep(interval_seconds)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"后台监控错误: {e}")
                    await asyncio.sleep(interval_seconds)

        self._monitor_task = asyncio.create_task(monitor_loop())
        logger.info("系统资源后台监控已启动")

    def stop_background_monitoring(self):
        """停止后台监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("系统资源后台监控已停止")



class QueryPerformanceMonitor:
    """查询性能监控器 - 核心类"""

    def __init__(self, max_history: int = 10000, slow_query_threshold: float = 5.0):
        self.max_history = max_history
        self.slow_query_threshold = slow_query_threshold

        # 查询历史存储
        self.query_history: deque = deque(maxlen=max_history)
        self.tenant_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.query_type_stats: Dict[str, List[float]] = defaultdict(list)

        # 实时统计
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'errors': 0,
            'slow_queries': 0,
            'start_time': datetime.utcnow()
        }

        # 组件
        self.alert_manager = AlertManager()
        self.resource_monitor = SystemResourceMonitor()

        # 锁保护
        self._lock = threading.Lock()
        self._running = False
        self._monitor_task = None

    def start_monitoring(self):
        """启动监控"""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._background_check())
        logger.info("性能监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        self.resource_monitor.stop_background_monitoring()
        logger.info("性能监控已停止")

    async def _background_check(self):
        """后台检查任务"""
        while self._running:
            try:
                # 收集系统指标
                metrics = self.resource_monitor.collect_metrics()

                # 检查资源告警
                if metrics.memory_percent > self.alert_manager.thresholds[AlertType.HIGH_MEMORY]:
                    self.alert_manager.create_alert(
                        AlertType.HIGH_MEMORY,
                        f"内存使用率过高: {metrics.memory_percent:.1f}%",
                        metrics.memory_percent
                    )
                else:
                    self.alert_manager.resolve_alert(AlertType.HIGH_MEMORY)

                if metrics.cpu_percent > self.alert_manager.thresholds[AlertType.HIGH_CPU]:
                    self.alert_manager.create_alert(
                        AlertType.HIGH_CPU,
                        f"CPU使用率过高: {metrics.cpu_percent:.1f}%",
                        metrics.cpu_percent
                    )
                else:
                    self.alert_manager.resolve_alert(AlertType.HIGH_CPU)

                # 检查错误率
                error_rate = self._calculate_error_rate()
                if error_rate > self.alert_manager.thresholds[AlertType.HIGH_ERROR_RATE]:
                    self.alert_manager.create_alert(
                        AlertType.HIGH_ERROR_RATE,
                        f"查询错误率过高: {error_rate:.1f}%",
                        error_rate
                    )
                else:
                    self.alert_manager.resolve_alert(AlertType.HIGH_ERROR_RATE)

                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"后台检查错误: {e}")
                await asyncio.sleep(60)

    def _calculate_error_rate(self) -> float:
        """计算错误率"""
        with self._lock:
            if self.stats['total_queries'] == 0:
                return 0.0
            return (self.stats['errors'] / self.stats['total_queries']) * 100

    @asynccontextmanager
    async def monitor_query(self, query_id: str, tenant_id: str, query_type: str):
        """查询监控上下文管理器"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        metrics = QueryMetrics(
            query_id=query_id,
            tenant_id=tenant_id,
            query_type=query_type,
            query_hash=self._calculate_query_hash(query_type),
            execution_time=0.0,
            sql_generation_time=0.0,
            sql_validation_time=0.0,
            result_processing_time=0.0,
            total_time=0.0,
            row_count=0,
            cache_hit=False,
            error=False
        )

        try:
            yield metrics
            metrics.error = False
        except Exception as e:
            metrics.error = True
            metrics.error_message = str(e)
            raise
        finally:
            end_time = time.time()
            metrics.total_time = end_time - start_time
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            metrics.memory_usage = max(0, end_memory - start_memory)
            self._record_query_metrics(metrics)

    def _calculate_query_hash(self, query_type: str) -> str:
        """计算查询哈希"""
        return hashlib.md5(query_type.encode('utf-8')).hexdigest()[:8]

    def _record_query_metrics(self, metrics: QueryMetrics):
        """记录查询指标"""
        with self._lock:
            self.query_history.append(metrics)
            self.tenant_history[metrics.tenant_id].append(metrics)

            self.stats['total_queries'] += 1
            if metrics.cache_hit:
                self.stats['cache_hits'] += 1
            if metrics.error:
                self.stats['errors'] += 1
            if metrics.total_time > self.slow_query_threshold:
                self.stats['slow_queries'] += 1
                self.alert_manager.create_alert(
                    AlertType.SLOW_QUERY,
                    f"慢查询: {metrics.query_id} 耗时 {metrics.total_time:.2f}s",
                    metrics.total_time,
                    metrics.tenant_id
                )

            self.query_type_stats[metrics.query_type].append(metrics.total_time)

    def get_real_time_stats(self) -> Dict[str, Any]:
        """获取实时统计"""
        with self._lock:
            now = datetime.utcnow()
            uptime = (now - self.stats['start_time']).total_seconds()
            total = self.stats['total_queries']

            qps = total / uptime if uptime > 0 else 0
            cache_rate = (self.stats['cache_hits'] / total * 100) if total > 0 else 0
            error_rate = (self.stats['errors'] / total * 100) if total > 0 else 0

            recent_times = [m.total_time for m in list(self.query_history)[-100:]]
            avg_time = statistics.mean(recent_times) if recent_times else 0

            system_metrics = self.resource_monitor.get_current_metrics()

            return {
                'total_queries': total,
                'queries_per_second': round(qps, 2),
                'cache_hit_rate': round(cache_rate, 2),
                'error_rate': round(error_rate, 2),
                'slow_queries': self.stats['slow_queries'],
                'avg_execution_time': round(avg_time, 3),
                'uptime_hours': round(uptime / 3600, 1),
                'memory_usage_mb': system_metrics.get('memory_used_mb', 0),
                'cpu_usage_percent': system_metrics.get('cpu_percent', 0),
                'active_alerts': len(self.alert_manager.get_active_alerts()),
                'timestamp': now.isoformat()
            }

    def get_tenant_performance(self, tenant_id: str, hours: int = 24) -> Dict[str, Any]:
        """获取租户性能报告"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        with self._lock:
            tenant_queries = [
                m for m in self.tenant_history.get(tenant_id, [])
                if m.timestamp >= cutoff_time
            ]

            if not tenant_queries:
                return {
                    'tenant_id': tenant_id,
                    'total_queries': 0,
                    'message': '该时间段内无查询记录'
                }

            times = [m.total_time for m in tenant_queries]
            errors = sum(1 for m in tenant_queries if m.error)
            cache_hits = sum(1 for m in tenant_queries if m.cache_hit)

            return {
                'tenant_id': tenant_id,
                'time_range_hours': hours,
                'total_queries': len(tenant_queries),
                'avg_execution_time': round(statistics.mean(times), 3),
                'max_execution_time': round(max(times), 3),
                'min_execution_time': round(min(times), 3),
                'p95_execution_time': round(sorted(times)[int(len(times) * 0.95)] if times else 0, 3),
                'error_count': errors,
                'error_rate': round(errors / len(tenant_queries) * 100, 2),
                'cache_hit_rate': round(cache_hits / len(tenant_queries) * 100, 2),
                'slow_query_count': sum(1 for t in times if t > self.slow_query_threshold)
            }

    def get_slow_queries(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        with self._lock:
            slow = [
                m for m in self.query_history
                if m.timestamp >= cutoff_time and m.total_time > self.slow_query_threshold
            ]
            slow.sort(key=lambda x: x.total_time, reverse=True)
            return [m.to_dict() for m in slow[:limit]]

    def get_query_type_performance(self) -> Dict[str, Any]:
        """获取查询类型性能统计"""
        with self._lock:
            result = {}
            for query_type, times in self.query_type_stats.items():
                if times:
                    result[query_type] = {
                        'count': len(times),
                        'avg_time': round(statistics.mean(times), 3),
                        'max_time': round(max(times), 3),
                        'min_time': round(min(times), 3)
                    }
            return result

    def get_warnings(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取性能警告"""
        return self.alert_manager.get_alert_history(hours)

    def get_active_alerts(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        alerts = self.alert_manager.get_active_alerts(tenant_id)
        return [a.to_dict() for a in alerts]

    def export_metrics(self, format: str = "json") -> str:
        """导出性能指标"""
        data = {
            'export_time': datetime.utcnow().isoformat(),
            'stats': self.get_real_time_stats(),
            'query_types': self.get_query_type_performance(),
            'warnings': self.get_warnings(),
            'recent_slow_queries': self.get_slow_queries(hours=1, limit=20)
        }

        if format.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format.lower() == "csv":
            # 简单CSV导出
            lines = ["metric,value"]
            stats = data['stats']
            for key, value in stats.items():
                lines.append(f"{key},{value}")
            return "\n".join(lines)
        else:
            raise ValueError(f"不支持的导出格式: {format}")

    def clear_history(self, hours: Optional[int] = None):
        """清除历史数据"""
        with self._lock:
            if hours is None:
                self.query_history.clear()
                self.tenant_history.clear()
                self.query_type_stats.clear()
                self.stats = {
                    'total_queries': 0,
                    'cache_hits': 0,
                    'errors': 0,
                    'slow_queries': 0,
                    'start_time': datetime.utcnow()
                }
            else:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                self.query_history = deque(
                    [m for m in self.query_history if m.timestamp >= cutoff_time],
                    maxlen=self.max_history
                )
        logger.info(f"已清除历史数据: hours={hours}")

    def get_health_status(self) -> Dict[str, Any]:
        """获取监控健康状态"""
        stats = self.get_real_time_stats()
        system_metrics = self.resource_monitor.get_current_metrics()

        # 计算健康评分
        health_score = 100
        issues = []

        if stats['error_rate'] > 5:
            health_score -= 20
            issues.append(f"错误率过高: {stats['error_rate']}%")

        if stats['avg_execution_time'] > 2:
            health_score -= 15
            issues.append(f"平均响应时间过长: {stats['avg_execution_time']}s")

        if system_metrics.get('memory_percent', 0) > 80:
            health_score -= 15
            issues.append(f"内存使用率过高: {system_metrics['memory_percent']}%")

        if system_metrics.get('cpu_percent', 0) > 80:
            health_score -= 15
            issues.append(f"CPU使用率过高: {system_metrics['cpu_percent']}%")

        active_alerts = len(self.alert_manager.get_active_alerts())
        if active_alerts > 0:
            health_score -= active_alerts * 5
            issues.append(f"存在 {active_alerts} 个活跃告警")

        health_score = max(0, health_score)

        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            'status': status,
            'health_score': health_score,
            'issues': issues,
            'monitoring_active': self._running,
            'stats': stats,
            'system_metrics': system_metrics,
            'timestamp': datetime.utcnow().isoformat()
        }


# 全局性能监控器实例
query_perf_monitor = QueryPerformanceMonitor(
    max_history=10000,
    slow_query_threshold=5.0
)


def get_query_perf_monitor() -> QueryPerformanceMonitor:
    """获取全局性能监控器实例"""
    return query_perf_monitor