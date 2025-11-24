"""
查询性能监控服务
提供详细的查询性能分析和监控功能
"""

import time
import logging
import psutil
import sqlparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """查询性能指标数据类"""
    tenant_id: str
    query_id: str
    query_type: str  # SELECT, INSERT, UPDATE, etc.
    table_names: List[str]

    # 时间指标 (毫秒)
    total_time: float
    parsing_time: float
    execution_time: float
    result_processing_time: float

    # 资源指标
    rows_examined: int
    rows_returned: int
    memory_usage_mb: float

    # 质量指标
    complexity_score: float
    cache_hit: bool
    error_occurred: bool

    # 元数据
    timestamp: datetime
    query_hash: str

    # Optional fields must come last
    error_message: Optional[str] = None


class QueryComplexityAnalyzer:
    """查询复杂度分析器"""

    def __init__(self):
        self.complexity_weights = {
            "JOIN": 3,
            "SUBQUERY": 2,
            "AGGREGATE": 1.5,
            "WINDOW_FUNCTION": 4,
            "CTE": 2,
            "UNION": 1.5,
            "WHERE_CLAUSE": 1,
            "ORDER_BY": 1,
            "GROUP_BY": 1.5
        }

    def analyze_query_complexity(self, query: str) -> float:
        """
        分析查询复杂度，返回复杂度评分(0-10)

        Args:
            query: SQL查询语句

        Returns:
            float: 复杂度评分
        """
        try:
            # 使用sqlparse解析SQL
            parsed_query = sqlparse.parse(query)[0]

            complexity_score = 1.0  # 基础复杂度

            # 分析JOIN数量
            complexity_score += self._count_joins(parsed_query) * self.complexity_weights["JOIN"]

            # 分析子查询数量
            complexity_score += self._count_subqueries(parsed_query) * self.complexity_weights["SUBQUERY"]

            # 分析聚合函数
            complexity_score += self._count_aggregates(parsed_query) * self.complexity_weights["AGGREGATE"]

            # 分析窗口函数
            complexity_score += self._count_window_functions(parsed_query) * self.complexity_weights["WINDOW_FUNCTION"]

            # 分析CTE
            complexity_score += self._count_ctes(parsed_query) * self.complexity_weights["CTE"]

            # 分析UNION
            complexity_score += self._count_unions(parsed_query) * self.complexity_weights["UNION"]

            return min(complexity_score, 10.0)  # 最大复杂度10

        except Exception as e:
            logger.warning(f"查询复杂度分析失败: {e}")
            return 5.0  # 默认中等复杂度

    def _count_joins(self, parsed_query) -> int:
        """统计JOIN数量"""
        join_count = 0
        for token in parsed_query.flatten():
            if token.ttype is None and isinstance(token, sqlparse.sql.Identifier):
                if hasattr(token, 'value') and token.value.upper() in ["JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN"]:
                    join_count += 1
        return join_count

    def _count_subqueries(self, parsed_query) -> int:
        """统计子查询数量"""
        count = 0
        for token in parsed_query.flatten():
            if token.ttype is None and isinstance(token, sqlparse.sql.Parenthesis):
                count += 1
        return count

    def _count_aggregates(self, parsed_query) -> int:
        """统计聚合函数数量"""
        aggregate_functions = ["COUNT", "SUM", "AVG", "MAX", "MIN", "STDDEV", "VARIANCE"]
        count = 0
        for token in parsed_query.flatten():
            if token.ttype is None and hasattr(token, 'value') and token.value.upper() in aggregate_functions:
                count += 1
        return count

    def _count_window_functions(self, parsed_query) -> int:
        """统计窗口函数数量"""
        # 简化实现，检测OVER关键字
        count = 0
        for token in parsed_query.flatten():
            if token.ttype is None and hasattr(token, 'value') and token.value.upper() == "OVER":
                count += 1
        return count

    def _count_ctes(self, parsed_query) -> int:
        """统计CTE数量"""
        # 检测WITH关键字
        count = 0
        for token in parsed_query.flatten():
            if token.ttype is None and hasattr(token, 'value') and token.value.upper() == "WITH":
                count += 1
        return count

    def _count_unions(self, parsed_query) -> int:
        """统计UNION数量"""
        count = 0
        for token in parsed_query.flatten():
            if token.ttype is None and hasattr(token, 'value') and token.value.upper() == "UNION":
                count += 1
        return count


class PerformanceMonitor:
    """性能监控主类"""

    def __init__(self, buffer_size: int = 1000):
        self.metrics_buffer: deque = deque(maxlen=buffer_size)
        self.tenant_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total_queries': 0,
            'avg_response_time': 0.0,
            'slow_queries': 0,
            'cache_hits': 0,
            'error_rate': 0.0
        })
        self.complexity_analyzer = QueryComplexityAnalyzer()
        self.process = psutil.Process()

    async def start_query_monitoring(self, query_id: str) -> Dict[str, Any]:
        """
        开始查询监控

        Args:
            query_id: 查询唯一标识

        Returns:
            Dict: 监控上下文
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()

        return {
            "start_time": start_time,
            "start_memory": start_memory,
            "query_id": query_id,
            "parsing_start": start_time
        }

    async def record_execution_step(self, context: Dict[str, Any], step: str, duration: float):
        """
        记录执行步骤耗时

        Args:
            context: 监控上下文
            step: 步骤名称
            duration: 耗时(毫秒)
        """
        if f"{step}_time" in context:
            context[f"{step}_time"] = duration
        else:
            logger.warning(f"未知的监控步骤: {step}")

    async def finish_query_monitoring(
        self,
        context: Dict[str, Any],
        query_info: Dict[str, Any]
    ) -> QueryPerformanceMetrics:
        """
        完成查询监控，生成性能指标

        Args:
            context: 监控上下文
            query_info: 查询信息

        Returns:
            QueryPerformanceMetrics: 性能指标
        """
        end_time = time.time()
        end_memory = self._get_memory_usage()

        # 计算各阶段耗时
        total_time = (end_time - context["start_time"]) * 1000  # 转换为毫秒
        parsing_time = query_info.get("parsing_time", 0)
        execution_time = query_info.get("execution_time", 0)
        result_processing_time = total_time - parsing_time - execution_time

        # 计算复杂度
        complexity_score = self.complexity_analyzer.analyze_query_complexity(
            query_info.get("query", "")
        )

        # 生成查询哈希
        query_hash = self._generate_query_hash(query_info.get("query", ""))

        metrics = QueryPerformanceMetrics(
            tenant_id=query_info["tenant_id"],
            query_id=context["query_id"],
            query_type=query_info.get("query_type", "SELECT"),
            table_names=query_info.get("table_names", []),
            total_time=total_time,
            parsing_time=parsing_time,
            execution_time=execution_time,
            result_processing_time=result_processing_time,
            rows_examined=query_info.get("rows_examined", 0),
            rows_returned=query_info.get("rows_returned", 0),
            memory_usage_mb=end_memory - context["start_memory"],
            complexity_score=complexity_score,
            cache_hit=query_info.get("cache_hit", False),
            error_occurred=query_info.get("error_occurred", False),
            error_message=query_info.get("error_message"),
            timestamp=datetime.utcnow(),
            query_hash=query_hash
        )

        # 添加到缓冲区
        self.metrics_buffer.append(metrics)

        # 更新租户统计
        await self._update_tenant_stats(metrics)

        return metrics

    async def _update_tenant_stats(self, metrics: QueryPerformanceMetrics):
        """更新租户统计信息"""
        tenant_id = metrics.tenant_id
        stats = self.tenant_stats[tenant_id]

        # 更新总查询数
        stats['total_queries'] += 1

        # 更新平均响应时间
        current_avg = stats['avg_response_time']
        stats['avg_response_time'] = (
            (current_avg * (stats['total_queries'] - 1) + metrics.total_time) /
            stats['total_queries']
        )

        # 更新慢查询数（超过5秒）
        if metrics.total_time > 5000:
            stats['slow_queries'] += 1

        # 更新缓存命中数
        if metrics.cache_hit:
            stats['cache_hits'] += 1

        # 更新错误率
        if metrics.error_occurred:
            error_count = stats.get('error_count', 0) + 1
            stats['error_count'] = error_count
            stats['error_rate'] = (error_count / stats['total_queries']) * 100

    def _get_memory_usage(self) -> float:
        """获取当前内存使用量(MB)"""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def _generate_query_hash(self, query: str) -> str:
        """生成查询哈希值"""
        import hashlib
        normalized_query = query.lower().strip()
        return hashlib.md5(normalized_query.encode()).hexdigest()

    async def get_tenant_metrics(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取租户性能指标

        Args:
            tenant_id: 租户ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量

        Returns:
            List[Dict]: 性能指标列表
        """
        filtered_metrics = []

        for metrics in self.metrics_buffer:
            if metrics.tenant_id != tenant_id:
                continue

            # 时间过滤
            if start_time and metrics.timestamp < start_time:
                continue
            if end_time and metrics.timestamp > end_time:
                continue

            filtered_metrics.append(asdict(metrics))

        # 按时间倒序排列
        filtered_metrics.sort(key=lambda x: x['timestamp'], reverse=True)

        return filtered_metrics[:limit]

    async def get_performance_summary(
        self,
        tenant_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取性能摘要统计

        Args:
            tenant_id: 租户ID
            days: 天数

        Returns:
            Dict: 性能摘要
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        # 过滤指定时间范围的指标
        recent_metrics = [
            m for m in self.metrics_buffer
            if m.tenant_id == tenant_id and start_time <= m.timestamp <= end_time
        ]

        if not recent_metrics:
            return {
                "message": "暂无性能数据",
                "tenant_id": tenant_id,
                "period_days": days
            }

        # 计算统计指标
        total_queries = len(recent_metrics)
        avg_response_time = sum(m.total_time for m in recent_metrics) / total_queries
        slow_queries = [m for m in recent_metrics if m.total_time > 5000]
        cache_hit_count = sum(1 for m in recent_metrics if m.cache_hit)
        error_count = sum(1 for m in recent_metrics if m.error_occurred)

        # 查询类型分布
        query_type_dist = defaultdict(int)
        for metrics in recent_metrics:
            query_type_dist[metrics.query_type] += 1

        # 最常用的表
        table_usage = defaultdict(int)
        for metrics in recent_metrics:
            for table in metrics.table_names:
                table_usage[table] += 1

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "summary": {
                "total_queries": total_queries,
                "avg_response_time_ms": round(avg_response_time, 2),
                "slow_query_count": len(slow_queries),
                "slow_query_rate": round(len(slow_queries) / total_queries * 100, 2),
                "cache_hit_rate": round(cache_hit_count / total_queries * 100, 2),
                "error_rate": round(error_count / total_queries * 100, 2)
            },
            "query_type_distribution": dict(query_type_dist),
            "most_used_tables": dict(sorted(table_usage.items(), key=lambda x: x[1], reverse=True)[:10]),
            "slow_queries": [
                {
                    "query_id": m.query_id,
                    "total_time": m.total_time,
                    "query_type": m.query_type,
                    "tables": m.table_names,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in sorted(slow_queries, key=lambda x: x.total_time, reverse=True)[:5]
            ]
        }

    async def get_slow_queries(
        self,
        tenant_id: str,
        threshold_ms: float = 5000.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取慢查询列表

        Args:
            tenant_id: 租户ID
            threshold_ms: 慢查询阈值(毫秒)
            limit: 限制数量

        Returns:
            List[Dict]: 慢查询列表
        """
        slow_queries = [
            asdict(m) for m in self.metrics_buffer
            if m.tenant_id == tenant_id and m.total_time > threshold_ms
        ]

        # 按执行时间倒序排列
        slow_queries.sort(key=lambda x: x['total_time'], reverse=True)

        return slow_queries[:limit]

    async def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取租户统计信息

        Args:
            tenant_id: 租户ID

        Returns:
            Dict: 统计信息
        """
        return dict(self.tenant_stats.get(tenant_id, {
            'total_queries': 0,
            'avg_response_time': 0.0,
            'slow_queries': 0,
            'cache_hits': 0,
            'error_rate': 0.0
        }))

    async def clear_tenant_metrics(self, tenant_id: str):
        """清除租户性能指标"""
        # 保留其他租户的指标
        self.metrics_buffer = deque(
            [m for m in self.metrics_buffer if m.tenant_id != tenant_id],
            maxlen=self.metrics_buffer.maxlen
        )

        # 清除租户统计
        if tenant_id in self.tenant_stats:
            del self.tenant_stats[tenant_id]

    def get_buffer_size(self) -> int:
        """获取缓冲区大小"""
        return len(self.metrics_buffer)

    async def export_metrics(self, format: str = "json") -> str:
        """
        导出性能指标

        Args:
            format: 导出格式 (json, csv)

        Returns:
            str: 导出的数据
        """
        if format == "json":
            import json
            metrics_list = [asdict(m) for m in self.metrics_buffer]
            return json.dumps(metrics_list, indent=2, default=str)
        else:
            raise ValueError(f"不支持的导出格式: {format}")


# 全局性能监控实例
performance_monitor = PerformanceMonitor()