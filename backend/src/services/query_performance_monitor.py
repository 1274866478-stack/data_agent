"""
查询性能监控服务
提供详细的查询性能分析和监控功能
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
import statistics
import psutil
import threading
from contextlib import asynccontextmanager

from src.app.core.config import settings

logger = logging.getLogger(__name__)


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


@dataclass
class PerformanceSummary:
    """性能汇总数据类"""
    total_queries: int
    avg_execution_time: float
    avg_total_time: float
    cache_hit_rate: float
    error_rate: float
    slow_queries: int
    queries_per_second: float
    memory_usage: float
    cpu_usage: float
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class QueryPerformanceMonitor:
    """查询性能监控器"""

    def __init__(self, max_history: int = 10000, slow_query_threshold: float = 5.0):
        self.max_history = max_history
        self.slow_query_threshold = slow_query_threshold

        # 存储查询历史
        self.query_history: deque = deque(maxlen=max_history)

        # 按租户分组的历史数据
        self.tenant_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # 按查询类型分组的统计数据
        self.query_type_stats: Dict[str, List[float]] = defaultdict(list)

        # 实时统计数据
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'errors': 0,
            'slow_queries': 0,
            'start_time': datetime.utcnow()
        }

        # 性能警告
        self.warnings = []

        # 锁保护
        self._lock = threading.Lock()

        # 监控任务
        self._monitor_task = None
        self._running = False

    def start_monitoring(self):
        """启动监控任务"""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_system_resources())

    def stop_monitoring(self):
        """停止监控任务"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()

    async def _monitor_system_resources(self):
        """监控系统资源使用情况"""
        while self._running:
            try:
                # 记录当前系统资源使用情况
                memory_percent = psutil.virtual_memory().percent
                cpu_percent = psutil.cpu_percent(interval=1)

                # 检查资源使用警告
                if memory_percent > 90:
                    self._add_warning("high_memory", f"内存使用率过高: {memory_percent:.1f}%")

                if cpu_percent > 90:
                    self._add_warning("high_cpu", f"CPU使用率过高: {cpu_percent:.1f}%")

                await asyncio.sleep(30)  # 每30秒检查一次

            except Exception as e:
                logger.error(f"系统资源监控失败: {e}")
                await asyncio.sleep(60)

    def _add_warning(self, warning_type: str, message: str):
        """添加性能警告"""
        warning = {
            'type': warning_type,
            'message': message,
            'timestamp': datetime.utcnow()
        }
        self.warnings.append(warning)

        # 保留最近100个警告
        if len(self.warnings) > 100:
            self.warnings = self.warnings[-100:]

        logger.warning(f"性能警告: {message}")

    @asynccontextmanager
    async def monitor_query(self, query_id: str, tenant_id: str, query_type: str):
        """查询监控上下文管理器"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent()

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

            # 查询成功完成
            metrics.error = False
            end_time = time.time()
            metrics.total_time = end_time - start_time

            # 计算资源使用情况
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            end_cpu = psutil.cpu_percent()
            metrics.memory_usage = max(0, end_memory - start_memory)
            metrics.cpu_usage = max(0, end_cpu - start_cpu)

        except Exception as e:
            # 查询执行出错
            metrics.error = True
            metrics.error_message = str(e)
            end_time = time.time()
            metrics.total_time = end_time - start_time
            raise
        finally:
            # 记录查询指标
            self._record_query_metrics(metrics)

    def _calculate_query_hash(self, query_type: str) -> str:
        """计算查询哈希值（用于分组相似查询）"""
        import hashlib
        return hashlib.md5(query_type.encode('utf-8')).hexdigest()[:8]

    def _record_query_metrics(self, metrics: QueryMetrics):
        """记录查询指标"""
        with self._lock:
            # 添加到历史记录
            self.query_history.append(metrics)
            self.tenant_history[metrics.tenant_id].append(metrics)

            # 更新统计数据
            self.stats['total_queries'] += 1

            if metrics.cache_hit:
                self.stats['cache_hits'] += 1

            if metrics.error:
                self.stats['errors'] += 1

            if metrics.total_time > self.slow_query_threshold:
                self.stats['slow_queries'] += 1
                self._add_warning(
                    "slow_query",
                    f"慢查询检测: {metrics.query_id} 耗时 {metrics.total_time:.2f}s"
                )

            # 记录按类型的执行时间
            self.query_type_stats[metrics.query_type].append(metrics.total_time)

    def get_real_time_stats(self) -> Dict[str, Any]:
        """获取实时统计信息"""
        with self._lock:
            now = datetime.utcnow()
            uptime = (now - self.stats['start_time']).total_seconds()

            total_queries = self.stats['total_queries']
            queries_per_second = total_queries / uptime if uptime > 0 else 0

            cache_hit_rate = (self.stats['cache_hits'] / total_queries * 100) if total_queries > 0 else 0
            error_rate = (self.stats['errors'] / total_queries * 100) if total_queries > 0 else 0

            # 计算平均执行时间
            if self.query_history:
                recent_times = [m.total_time for m in list(self.query_history)[-100:]]
                avg_execution_time = statistics.mean(recent_times)
            else:
                avg_execution_time = 0.0

            return {
                'total_queries': total_queries,
                'queries_per_second': round(queries_per_second, 2),
                'cache_hit_rate': round(cache_hit_rate, 2),
                'error_rate': round(error_rate, 2),
                'slow_queries': self.stats['slow_queries'],
                'avg_execution_time': round(avg_execution_time, 3),
                'uptime_hours': round(uptime / 3600, 1),
                'memory_usage_mb': round(psutil.Process().memory_info().rss / 1024 / 1024, 1),
                'cpu_usage_percent': psutil.cpu_percent(),
                'warnings_count': len(self.warnings),
                'timestamp': now.isoformat()
            }

    def get_tenant_performance(self, tenant_id: str, hours: int = 24) -> Dict[str, Any]:
        """获取租户性能报告"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        tenant_queries = [
            q for q in self.tenant_history.get(tenant_id, [])
            if q.timestamp > cutoff_time
        ]

        if not tenant_queries:
            return {
                'tenant_id': tenant_id,
                'total_queries': 0,
                'message': '该时间段内无查询记录'
            }

        # 计算统计数据
        execution_times = [q.total_time for q in tenant_queries]
        cache_hits = sum(1 for q in tenant_queries if q.cache_hit)
        errors = sum(1 for q in tenant_queries if q.error)

        # 按查询类型分组
        type_stats = defaultdict(list)
        for q in tenant_queries:
            type_stats[q.query_type].append(q.total_time)

        # 计算性能指标
        avg_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        p95_time = sorted(execution_times)[int(0.95 * len(execution_times))] if len(execution_times) > 20 else max(execution_times)

        return {
            'tenant_id': tenant_id,
            'time_range_hours': hours,
            'total_queries': len(tenant_queries),
            'avg_execution_time': round(avg_time, 3),
            'median_execution_time': round(median_time, 3),
            'p95_execution_time': round(p95_time, 3),
            'cache_hit_rate': round(cache_hits / len(tenant_queries) * 100, 2),
            'error_rate': round(errors / len(tenant_queries) * 100, 2),
            'query_types': {
                qtype: {
                    'count': len(times),
                    'avg_time': round(statistics.mean(times), 3)
                }
                for qtype, times in type_stats.items()
            },
            'slow_queries': sum(1 for q in tenant_queries if q.total_time > self.slow_query_threshold),
            'recent_errors': [
                {
                    'query_id': q.query_id,
                    'error_message': q.error_message,
                    'timestamp': q.timestamp.isoformat()
                }
                for q in tenant_queries if q.error
            ][-5:]  # 最近5个错误
        }

    def get_slow_queries(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        slow_queries = [
            q for q in self.query_history
            if q.total_time > self.slow_query_threshold and q.timestamp > cutoff_time
        ]

        # 按执行时间排序
        slow_queries.sort(key=lambda x: x.total_time, reverse=True)

        return [
            {
                'query_id': q.query_id,
                'tenant_id': q.tenant_id,
                'query_type': q.query_type,
                'execution_time': round(q.total_time, 3),
                'sql_generation_time': round(q.sql_generation_time, 3),
                'sql_validation_time': round(q.sql_validation_time, 3),
                'result_processing_time': round(q.result_processing_time, 3),
                'row_count': q.row_count,
                'memory_usage': round(q.memory_usage, 2),
                'error': q.error,
                'error_message': q.error_message,
                'timestamp': q.timestamp.isoformat()
            }
            for q in slow_queries[:limit]
        ]

    def get_query_type_performance(self) -> Dict[str, Any]:
        """获取按查询类型的性能分析"""
        type_performance = {}

        for query_type, times in self.query_type_stats.items():
            if times:
                type_performance[query_type] = {
                    'total_queries': len(times),
                    'avg_time': round(statistics.mean(times), 3),
                    'median_time': round(statistics.median(times), 3),
                    'min_time': round(min(times), 3),
                    'max_time': round(max(times), 3),
                    'p95_time': round(sorted(times)[int(0.95 * len(times))], 3) if len(times) > 20 else round(max(times), 3)
                }

        return type_performance

    def get_warnings(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近的性能警告"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        recent_warnings = [
            {
                'type': w['type'],
                'message': w['message'],
                'timestamp': w['timestamp'].isoformat()
            }
            for w in self.warnings
            if w['timestamp'] > cutoff_time
        ]

        return recent_warnings

    def clear_history(self):
        """清除历史数据"""
        with self._lock:
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
            self.warnings.clear()

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
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能趋势分析"""
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # 筛选指定时间范围内的查询
            recent_queries = [
                m for m in self.query_history
                if m.timestamp >= cutoff_time
            ]

            if not recent_queries:
                return {"error": "No recent data available"}

            # 按小时分组统计
            hourly_stats = defaultdict(list)
            for query in recent_queries:
                hour = query.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_stats[hour].append(query.total_time)

            # 计算趋势
            trends = {}
            for hour, times in hourly_stats.items():
                trends[hour.isoformat()] = {
                    'count': len(times),
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'median_time': statistics.median(times)
                }

            # 计算性能变化趋势
            hours_list = sorted(trends.keys())
            if len(hours_list) >= 2:
                first_hour = trends[hours_list[0]]['avg_time']
                last_hour = trends[hours_list[-1]]['avg_time']
                trend_change = ((last_hour - first_hour) / first_hour) * 100 if first_hour > 0 else 0

                trend_direction = "improving" if trend_change < 0 else "degrading" if trend_change > 0 else "stable"
            else:
                trend_change = 0
                trend_direction = "stable"

            return {
                "period_hours": hours,
                "total_queries": len(recent_queries),
                "trend_direction": trend_direction,
                "performance_change_percent": round(trend_change, 2),
                "hourly_breakdown": trends,
                "peak_hour": max(trends.items(), key=lambda x: x[1]['avg_time'])[0] if trends else None,
                "best_hour": min(trends.items(), key=lambda x: x[1]['avg_time'])[0] if trends else None
            }

    def get_query_patterns_analysis(self) -> Dict[str, Any]:
        """获取查询模式分析"""
        with self._lock:
            if not self.query_history:
                return {"error": "No query data available"}

            # 分析查询类型分布
            type_distribution = defaultdict(int)
            for query in self.query_history:
                type_distribution[query.query_type] += 1

            # 分析缓存命中率
            cache_stats = {
                'total_with_cache': 0,
                'cache_hits': 0,
                'cache_misses': 0
            }

            for query in self.query_history:
                cache_stats['total_with_cache'] += 1
                if query.cache_hit:
                    cache_stats['cache_hits'] += 1
                else:
                    cache_stats['cache_misses'] += 1

            cache_hit_rate = (cache_stats['cache_hits'] / cache_stats['total_with_cache'] * 100) if cache_stats['total_with_cache'] > 0 else 0

            # 分析错误模式
            error_patterns = defaultdict(int)
            for query in self.query_history:
                if query.error:
                    error_type = self._classify_error(query.error_message)
                    error_patterns[error_type] += 1

            # 分析性能模式
            performance_quartiles = self._calculate_performance_quartiles()

            return {
                "query_type_distribution": dict(type_distribution),
                "most_common_query_type": max(type_distribution.items(), key=lambda x: x[1])[0] if type_distribution else None,
                "cache_analysis": {
                    "hit_rate_percent": round(cache_hit_rate, 2),
                    "total_queries": cache_stats['total_with_cache'],
                    "hits": cache_stats['cache_hits'],
                    "misses": cache_stats['cache_misses']
                },
                "error_patterns": dict(error_patterns),
                "performance_quartiles": performance_quartiles,
                "optimization_suggestions": self._generate_optimization_suggestions()
            }

    def _classify_error(self, error_message: str) -> str:
        """分类错误类型"""
        if not error_message:
            return "unknown"

        error_lower = error_message.lower()

        if any(keyword in error_lower for keyword in ['timeout', 'time out']):
            return "timeout"
        elif any(keyword in error_lower for keyword in ['connection', 'connect']):
            return "connection"
        elif any(keyword in error_lower for keyword in ['syntax', 'parse']):
            return "syntax"
        elif any(keyword in error_lower for keyword in ['permission', 'access denied', 'unauthorized']):
            return "permission"
        elif any(keyword in error_lower for keyword in ['not found', 'does not exist']):
            return "not_found"
        else:
            return "other"

    def _calculate_performance_quartiles(self) -> Dict[str, float]:
        """计算性能四分位数"""
        if not self.query_history:
            return {}

        execution_times = [query.total_time for query in list(self.query_history)[-1000:]]

        if not execution_times:
            return {}

        execution_times.sort()
        n = len(execution_times)

        return {
            "min": execution_times[0],
            "q1": execution_times[n // 4],
            "median": execution_times[n // 2],
            "q3": execution_times[3 * n // 4],
            "max": execution_times[-1],
            "iqr": execution_times[3 * n // 4] - execution_times[n // 4]
        }

    def _generate_optimization_suggestions(self) -> List[str]:
        """生成性能优化建议"""
        suggestions = []

        with self._lock:
            if not self.query_history:
                return ["No data available for analysis"]

            # 分析缓存命中率
            cache_hit_rate = (self.stats['cache_hits'] / self.stats['total_queries'] * 100) if self.stats['total_queries'] > 0 else 0
            if cache_hit_rate < 50:
                suggestions.append("Consider optimizing cache configuration - current hit rate is low")

            # 分析慢查询比例
            slow_query_rate = (self.stats['slow_queries'] / self.stats['total_queries'] * 100) if self.stats['total_queries'] > 0 else 0
            if slow_query_rate > 20:
                suggestions.append("High percentage of slow queries detected - consider query optimization")

            # 分析错误率
            error_rate = (self.stats['errors'] / self.stats['total_queries'] * 100) if self.stats['total_queries'] > 0 else 0
            if error_rate > 5:
                suggestions.append("High error rate detected - review query logic and database connections")

            # 分析执行时间分布
            recent_times = [m.total_time for m in list(self.query_history)[-100:]]
            if recent_times:
                avg_time = statistics.mean(recent_times)
                if avg_time > 3.0:
                    suggestions.append("Average query execution time is high - consider database indexing")

            # 检查内存使用
            current_memory = psutil.virtual_memory().percent
            if current_memory > 80:
                suggestions.append("High memory usage detected - consider increasing cache efficiency")

            return suggestions if suggestions else ["Performance appears to be within acceptable ranges"]

    def get_tenant_performance_comparison(self, limit: int = 10) -> Dict[str, Any]:
        """获取租户性能对比"""
        with self._lock:
            tenant_stats = {}

            for tenant_id, queries in self.tenant_history.items():
                if not queries:
                    continue

                recent_queries = list(queries)[-50:]  # 最近50个查询

                total_time = sum(q.total_time for q in recent_queries)
                avg_time = total_time / len(recent_queries) if recent_queries else 0

                cache_hits = sum(1 for q in recent_queries if q.cache_hit)
                cache_hit_rate = (cache_hits / len(recent_queries) * 100) if recent_queries else 0

                errors = sum(1 for q in recent_queries if q.error)
                error_rate = (errors / len(recent_queries) * 100) if recent_queries else 0

                tenant_stats[tenant_id] = {
                    'query_count': len(recent_queries),
                    'avg_execution_time': round(avg_time, 3),
                    'total_execution_time': round(total_time, 3),
                    'cache_hit_rate': round(cache_hit_rate, 2),
                    'error_rate': round(error_rate, 2),
                    'performance_score': self._calculate_tenant_score(avg_time, cache_hit_rate, error_rate)
                }

            # 按性能评分排序
            sorted_tenants = sorted(tenant_stats.items(), key=lambda x: x[1]['performance_score'], reverse=True)

            return {
                'total_tenants': len(tenant_stats),
                'top_performers': dict(sorted_tenants[:limit]),
                'performance_distribution': self._analyze_tenant_performance_distribution(tenant_stats)
            }

    def _calculate_tenant_score(self, avg_time: float, cache_hit_rate: float, error_rate: float) -> float:
        """计算租户性能评分"""
        # 基础分数100
        score = 100.0

        # 根据执行时间扣分（执行时间越短分数越高）
        if avg_time > 0:
            time_penalty = min(avg_time * 5, 50)  # 最多扣50分
            score -= time_penalty

        # 根据缓存命中率加分
        cache_bonus = cache_hit_rate * 0.3  # 最多加30分
        score += cache_bonus

        # 根据错误率扣分
        error_penalty = error_rate * 2  # 错误率翻倍扣分
        score -= error_penalty

        return max(0, round(score, 2))

    def _analyze_tenant_performance_distribution(self, tenant_stats: Dict) -> Dict[str, Any]:
        """分析租户性能分布"""
        if not tenant_stats:
            return {}

        scores = [stats['performance_score'] for stats in tenant_stats.values()]

        return {
            'average_score': statistics.mean(scores),
            'median_score': statistics.median(scores),
            'std_deviation': statistics.stdev(scores) if len(scores) > 1 else 0,
            'min_score': min(scores),
            'max_score': max(scores),
            'performance_tiers': {
                'excellent': len([s for s in scores if s >= 80]),
                'good': len([s for s in scores if 60 <= s < 80]),
                'fair': len([s for s in scores if 40 <= s < 60]),
                'poor': len([s for s in scores if s < 40])
            }
        }

    async def generate_performance_report(self, hours: int = 24) -> str:
        """生成性能报告"""
        trends = self.get_performance_trends(hours)
        patterns = self.get_query_patterns_analysis()
        tenant_comparison = self.get_tenant_performance_comparison()

        report_lines = [
            f"# 查询性能监控报告",
            f"报告生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            f"分析时间范围: 最近 {hours} 小时",
            "",
            "## 📊 整体统计",
            f"- 总查询数: {self.stats['total_queries']}",
            f"- 平均查询时间: {trends.get('hourly_breakdown', {}).get('avg_time', 0):.3f}s",
            f"- 缓存命中率: {patterns.get('cache_analysis', {}).get('hit_rate_percent', 0):.1f}%",
            f"- 错误率: {patterns.get('cache_analysis', {}).get('error_rate', 0):.1f}%",
            "",
            "## 📈 性能趋势",
            f"- 趋势方向: {trends.get('trend_direction', 'unknown')}",
            f"- 性能变化: {trends.get('performance_change_percent', 0):.1f}%",
            "",
            "## ⚠️ 优化建议",
        ]

        suggestions = patterns.get('optimization_suggestions', [])
        for suggestion in suggestions:
            report_lines.append(f"- {suggestion}")

        report_lines.extend([
            "",
            "## 🏆 租户性能排名",
            ""
        ])

        top_tenants = tenant_comparison.get('top_performers', {})
        for i, (tenant, stats) in enumerate(list(top_tenants.items())[:5], 1):
            report_lines.append(f"{i}. 租户 {tenant}: 评分 {stats['performance_score']:.1f} (平均 {stats['avg_execution_time']:.3f}s)")

        return "\n".join(report_lines)


# 全局性能监控器实例
performance_monitor = QueryPerformanceMonitor(
    max_history=10000,
    slow_query_threshold=5.0
)