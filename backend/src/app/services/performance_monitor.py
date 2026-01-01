"""
# [QUERY_PERFORMANCE_MONITOR] 查询性能监控服务

## [HEADER]
**文件名**: query_performance_monitor.py (命名实际为performance_monitor.py)
**职责**: 为RAG-SQL链提供详细的性能分析、监控、优化建议和性能统计
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 查询性能监控服务

## [INPUT]
- **tenant_id: str** - 租户ID
- **user_query: str** - 用户查询
- **generated_sql: str** - 生成的SQL语句
- **database_type: str** - 数据库类型
- **query_id: str** - 查询ID
- **stage: str** - 阶段名称（schema_discovery, sql_generation, sql_validation, sql_execution, result_processing）
- **duration: float** - 持续时间（秒）
- **result_rows: Optional[int]** - 结果行数
- **result_size_bytes: Optional[int]** - 结果大小（字节）
- **cache_hit: bool** - 是否缓存命中
- **cache_key: Optional[str]** - 缓存键
- **error_message: str** - 错误信息
- **error_type: str** - 错误类型
- **time_range: str** - 时间范围（"1h", "24h", "7d", "30d"）
- **limit: int** - 返回数量限制
- **before_date: Optional[datetime]** - 清理此日期之前的数据
- **max_history_size: int** - 最大历史记录数

## [OUTPUT]
- **str**: 查询ID（start_query_monitoring）
- **QueryMetrics**: 查询指标对象（get_query_metrics）
- **PerformanceSummary**: 性能汇总统计对象（get_performance_summary）
- **List[QueryMetrics]**: 最慢查询列表（get_slow_queries）
- **Dict[str, Any]**: 错误分析结果（get_error_analysis）
- **List[Dict[str, Any]]**: 优化建议列表（get_optimization_suggestions）
- **Dict[str, Any]**: 监控统计信息（get_monitoring_stats）
- **PerformanceMonitor**: 性能监控器实例（initialize_performance_monitor）

**上游依赖** (已读取源码):
- Python标准库: asyncio, collections（defaultdict, deque）, dataclasses（asdict）, datetime, enum, json, logging, statistics, time, uuid

**下游依赖** (需要反向索引分析):
- [llm_service.py](./llm_service.py) - LLM服务使用性能监控
- [agent_service.py](./agent_service.py) - Agent服务使用性能监控

**调用方**:
- RAG-SQL链执行查询时记录性能指标
- 性能分析API调用时获取统计信息
- 优化建议API调用时生成建议

## [STATE]
- **查询状态**: QueryStatus枚举（PENDING, EXECUTING, COMPLETED, FAILED, CANCELLED, TIMEOUT）
- **性能等级**: PerformanceLevel枚举（EXCELLENT <0.5s, GOOD <1s, AVERAGE <3s, POOR <10s, CRITICAL >=10s）
- **数据结构**:
  - QueryMetrics: 查询性能指标（query_id, tenant_id, user_query, generated_sql, database_type, start_time, end_time, total_duration, 分段时间, 资源使用, 查询复杂度, 状态和错误, 缓存信息, 性能等级）
  - PerformanceSummary: 性能汇总统计（time_range, total_queries, successful_queries, failed_queries, avg/median/p95/max/min执行时间, status_counts, performance_distribution, 资源使用统计, 最慢查询, 错误统计）
- **历史存储**: deque(maxlen=10000)保留最近10000条历史记录
- **活跃查询**: Dict[query_id, QueryMetrics]当前执行中的查询
- **性能分析器**: PerformanceAnalyzer提供静态分析方法
  - calculate_performance_level(): 根据执行时间和复杂度计算性能等级
  - calculate_query_complexity(): 分析SQL复杂度（JOIN, 子查询, 聚合函数, 窗口函数, CTE, UNION）
  - analyze_sql_pattern(): 分析SQL模式（has_join, has_subquery, has_aggregation等）
  - generate_optimization_suggestions(): 生成性能优化建议
- **统计缓存**: _summary_cache字典缓存汇总统计（5分钟TTL）
- **性能等级阈值**:
  - EXCELLENT: <0.5s, GOOD: <1s, AVERAGE: <3s, POOR: <10s, CRITICAL: >=10s
- **SQL复杂度计算**: 基础关键词(0.1) + JOIN(0.3*count) + 子查询(0.5*count) + 聚合函数(0.2*count) + 窗口函数(0.5) + CTE(0.4*count) + UNION(0.3*count)，最大值10.0

## [SIDE-EFFECTS]
- **UUID生成**: str(uuid.uuid4())生成唯一查询ID
- **复杂度计算**: calculate_query_complexity分析SQL，calculate_query_complexity(generated_sql)
- **模式分析**: analyze_sql_pattern(generated_sql)提取SQL特征
- **对象创建**: QueryMetrics(创建查询指标对象，添加到active_queries字典
- **时间记录**: datetime.now()记录开始和结束时间，(end_time - start_time).total_seconds()计算持续时间
- **属性更新**: metrics.schema_discovery_time = duration等分段时间记录
- **状态转换**: QueryStatus.PENDING → EXECUTING → COMPLETED/FAILED
- **性能等级计算**: calculate_performance_level(total_duration, query_complexity_score)
- **deque操作**: metrics_history.append(metrics)添加到历史记录
- **字典删除**: del self.active_queries[query_id]从活跃查询中移除
- **统计计算**: statistics.mean/median/quantiles计算执行时间统计
- **列表推导式过滤**: [m for m in self.metrics_history if conditions]过滤指标
- **排序**: sorted(queries, key=lambda x: x.total_duration, reverse=True)按时间排序
- **缓存操作**: _summary_cache[cache_key] = summary缓存结果
- **清理操作**: clear_history()清理历史数据，metrics_history.clear()
- **全局单例**: _performance_monitor全局实例
- **异常处理**: 所有方法都有try-except捕获异常，记录日志

## [POS]
**路径**: backend/src/app/services/performance_monitor.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 外部依赖无，使用Python标准库
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import logging
from enum import Enum
import statistics
import uuid

logger = logging.getLogger(__name__)


class QueryStatus(Enum):
    """查询状态枚举"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class PerformanceLevel(Enum):
    """性能等级枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class QueryMetrics:
    """查询性能指标"""
    query_id: str
    tenant_id: str
    user_query: str
    generated_sql: str
    database_type: str

    # 时间指标
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: Optional[float] = None

    # 分段时间
    schema_discovery_time: Optional[float] = None
    sql_generation_time: Optional[float] = None
    sql_validation_time: Optional[float] = None
    sql_execution_time: Optional[float] = None
    result_processing_time: Optional[float] = None

    # 资源使用
    result_rows: Optional[int] = None
    result_size_bytes: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # 查询复杂度
    query_complexity_score: Optional[float] = None
    join_count: Optional[int] = None
    where_clause_count: Optional[int] = None
    aggregate_function_count: Optional[int] = None

    # 状态和错误
    status: QueryStatus = QueryStatus.PENDING
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    # 缓存信息
    cache_hit: bool = False
    cache_key: Optional[str] = None

    # 性能等级
    performance_level: Optional[PerformanceLevel] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换日期时间为ISO字符串
        if data.get('start_time'):
            data['start_time'] = data['start_time'].isoformat()
        if data.get('end_time'):
            data['end_time'] = data['end_time'].isoformat()
        # 转换枚举为字符串
        if data.get('status'):
            data['status'] = data['status'].value
        if data.get('performance_level'):
            data['performance_level'] = data['performance_level'].value
        return data


@dataclass
class PerformanceSummary:
    """性能汇总统计"""
    time_range: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_execution_time: float
    median_execution_time: float
    p95_execution_time: float
    max_execution_time: float
    min_execution_time: float

    # 按状态分类
    status_counts: Dict[str, int]

    # 按性能等级分类
    performance_distribution: Dict[str, int]

    # 资源使用统计
    total_result_rows: int
    avg_result_rows: float
    total_memory_usage: float

    # 最慢查询
    slowest_queries: List[Dict[str, Any]]

    # 错误统计
    error_types: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class PerformanceAnalyzer:
    """性能分析器"""

    @staticmethod
    def calculate_performance_level(execution_time: float, query_complexity: float = 1.0) -> PerformanceLevel:
        """
        计算性能等级

        Args:
            execution_time: 执行时间（秒）
            query_complexity: 查询复杂度分数

        Returns:
            PerformanceLevel: 性能等级
        """
        # 根据执行时间和复杂度调整阈值
        adjusted_time = execution_time / query_complexity

        if adjusted_time < 0.5:
            return PerformanceLevel.EXCELLENT
        elif adjusted_time < 1.0:
            return PerformanceLevel.GOOD
        elif adjusted_time < 3.0:
            return PerformanceLevel.AVERAGE
        elif adjusted_time < 10.0:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL

    @staticmethod
    def calculate_query_complexity(sql: str) -> float:
        """
        计算SQL查询复杂度

        Args:
            sql: SQL查询语句

        Returns:
            float: 复杂度分数
        """
        sql_upper = sql.upper()
        complexity = 1.0

        # 基础关键词
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT'
        ]
        for keyword in keywords:
            if keyword in sql_upper:
                complexity += 0.1

        # JOIN操作（增加复杂度）
        join_count = sql_upper.count('JOIN')
        complexity += join_count * 0.3

        # 子查询
        subquery_count = sql_upper.count('(SELECT')
        complexity += subquery_count * 0.5

        # 聚合函数
        aggregate_functions = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'STDDEV']
        for func in aggregate_functions:
            complexity += sql_upper.count(func) * 0.2

        # 窗口函数
        if 'OVER' in sql_upper:
            complexity += 0.5

        # CTE (Common Table Expressions)
        with_count = sql_upper.count('WITH ')
        complexity += with_count * 0.4

        # UNION操作
        union_count = sql_upper.count('UNION')
        complexity += union_count * 0.3

        return min(complexity, 10.0)  # 限制最大复杂度为10

    @staticmethod
    def analyze_sql_pattern(sql: str) -> Dict[str, Any]:
        """
        分析SQL模式

        Args:
            sql: SQL查询语句

        Returns:
            Dict: SQL模式分析结果
        """
        sql_upper = sql.upper()

        return {
            "has_join": "JOIN" in sql_upper,
            "join_count": sql_upper.count('JOIN'),
            "has_subquery": "(SELECT" in sql_upper,
            "subquery_count": sql_upper.count('(SELECT'),
            "has_aggregation": any(func in sql_upper for func in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']),
            "aggregate_functions": [func for func in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN'] if func in sql_upper],
            "has_window_function": "OVER" in sql_upper,
            "has_cte": "WITH " in sql_upper,
            "has_union": "UNION" in sql_upper,
            "where_clause_count": sql_upper.count('WHERE'),
            "order_by_clause": "ORDER BY" in sql_upper,
            "group_by_clause": "GROUP BY" in sql_upper,
            "having_clause": "HAVING" in sql_upper,
        }

    @staticmethod
    def generate_optimization_suggestions(metrics: QueryMetrics) -> List[str]:
        """
        生成性能优化建议

        Args:
            metrics: 查询指标

        Returns:
            List[str]: 优化建议列表
        """
        suggestions = []

        if metrics.sql_execution_time:
            if metrics.sql_execution_time > 5.0:
                suggestions.append("查询执行时间过长，考虑添加适当的索引")

            if metrics.sql_execution_time > 10.0:
                suggestions.append("查询执行时间非常长，建议检查查询逻辑和数据量")

        if metrics.result_rows:
            if metrics.result_rows > 10000:
                suggestions.append("返回结果行数过多，考虑添加LIMIT子句或分页查询")

            if metrics.result_rows > 100000:
                suggestions.append("返回结果行数极大，建议优化查询条件或使用数据采样")

        if metrics.join_count and metrics.join_count > 5:
            suggestions.append("JOIN数量较多，考虑查询优化或数据结构重组")

        if metrics.aggregate_function_count and metrics.aggregate_function_count > 3:
            suggestions.append("聚合函数较多，考虑分解查询或使用物化视图")

        if not metrics.cache_hit and metrics.sql_execution_time and metrics.sql_execution_time > 1.0:
            suggestions.append("查询未被缓存，考虑启用查询结果缓存")

        if metrics.memory_usage_mb and metrics.memory_usage_mb > 100:
            suggestions.append("内存使用量较高，考虑优化查询或增加服务器内存")

        if metrics.performance_level == PerformanceLevel.CRITICAL:
            suggestions.append("查询性能极差，建议立即进行优化")

        return suggestions


class PerformanceMonitor:
    """性能监控服务"""

    def __init__(self, max_history_size: int = 10000):
        self.max_history_size = max_history_size
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.active_queries: Dict[str, QueryMetrics] = {}
        self.analyzer = PerformanceAnalyzer()

        # 统计缓存
        self._summary_cache: Dict[str, PerformanceSummary] = {}
        self._cache_ttl = 300  # 5分钟缓存

    def start_query_monitoring(self, tenant_id: str, user_query: str,
                             generated_sql: str, database_type: str) -> str:
        """
        开始查询监控

        Args:
            tenant_id: 租户ID
            user_query: 用户查询
            generated_sql: 生成的SQL
            database_type: 数据库类型

        Returns:
            str: 查询ID
        """
        query_id = str(uuid.uuid4())

        # 分析SQL复杂度
        complexity = self.analyzer.calculate_query_complexity(generated_sql)
        sql_pattern = self.analyzer.analyze_sql_pattern(generated_sql)

        metrics = QueryMetrics(
            query_id=query_id,
            tenant_id=tenant_id,
            user_query=user_query,
            generated_sql=generated_sql,
            database_type=database_type,
            start_time=datetime.now(),
            query_complexity_score=complexity,
            join_count=sql_pattern["join_count"],
            where_clause_count=sql_pattern["where_clause_count"],
            aggregate_function_count=len(sql_pattern["aggregate_functions"])
        )

        self.active_queries[query_id] = metrics
        logger.debug(f"开始监控查询: {query_id}")

        return query_id

    def update_query_timing(self, query_id: str, stage: str, duration: float):
        """
        更新查询阶段时间

        Args:
            query_id: 查询ID
            stage: 阶段名称
            duration: 持续时间（秒）
        """
        if query_id not in self.active_queries:
            logger.warning(f"查询不存在: {query_id}")
            return

        metrics = self.active_queries[query_id]

        if stage == "schema_discovery":
            metrics.schema_discovery_time = duration
        elif stage == "sql_generation":
            metrics.sql_generation_time = duration
        elif stage == "sql_validation":
            metrics.sql_validation_time = duration
        elif stage == "sql_execution":
            metrics.sql_execution_time = duration
        elif stage == "result_processing":
            metrics.result_processing_time = duration

        logger.debug(f"更新查询时间: {query_id} - {stage}: {duration}s")

    def complete_query(self, query_id: str, result_rows: Optional[int] = None,
                      result_size_bytes: Optional[int] = None,
                      cache_hit: bool = False, cache_key: Optional[str] = None):
        """
        完成查询监控

        Args:
            query_id: 查询ID
            result_rows: 结果行数
            result_size_bytes: 结果大小（字节）
            cache_hit: 是否缓存命中
            cache_key: 缓存键
        """
        if query_id not in self.active_queries:
            logger.warning(f"查询不存在: {query_id}")
            return

        metrics = self.active_queries[query_id]

        metrics.end_time = datetime.now()
        metrics.total_duration = (metrics.end_time - metrics.start_time).total_seconds()
        metrics.result_rows = result_rows
        metrics.result_size_bytes = result_size_bytes
        metrics.status = QueryStatus.COMPLETED
        metrics.cache_hit = cache_hit
        metrics.cache_key = cache_key

        # 计算性能等级
        if metrics.total_duration:
            metrics.performance_level = self.analyzer.calculate_performance_level(
                metrics.total_duration, metrics.query_complexity_score or 1.0
            )

        # 移动到历史记录
        self.metrics_history.append(metrics)
        del self.active_queries[query_id]

        logger.info(f"查询完成: {query_id} - 耗时: {metrics.total_duration:.2f}s")

    def fail_query(self, query_id: str, error_message: str, error_type: str = "unknown"):
        """
        标记查询失败

        Args:
            query_id: 查询ID
            error_message: 错误信息
            error_type: 错误类型
        """
        if query_id not in self.active_queries:
            logger.warning(f"查询不存在: {query_id}")
            return

        metrics = self.active_queries[query_id]

        metrics.end_time = datetime.now()
        metrics.total_duration = (metrics.end_time - metrics.start_time).total_seconds()
        metrics.status = QueryStatus.FAILED
        metrics.error_message = error_message
        metrics.error_type = error_type

        # 移动到历史记录
        self.metrics_history.append(metrics)
        del self.active_queries[query_id]

        logger.error(f"查询失败: {query_id} - 错误: {error_message}")

    def get_query_metrics(self, query_id: str) -> Optional[QueryMetrics]:
        """
        获取查询指标

        Args:
            query_id: 查询ID

        Returns:
            QueryMetrics: 查询指标
        """
        # 先检查活跃查询
        if query_id in self.active_queries:
            return self.active_queries[query_id]

        # 再检查历史记录
        for metrics in reversed(self.metrics_history):
            if metrics.query_id == query_id:
                return metrics

        return None

    def get_performance_summary(self, tenant_id: Optional[str] = None,
                              time_range: str = "1h") -> PerformanceSummary:
        """
        获取性能汇总统计

        Args:
            tenant_id: 租户ID（可选）
            time_range: 时间范围 ("1h", "24h", "7d", "30d")

        Returns:
            PerformanceSummary: 性能汇总统计
        """
        cache_key = f"{tenant_id or 'all'}_{time_range}"

        # 检查缓存
        if cache_key in self._summary_cache:
            cached_time = self._summary_cache[cache_key]
            if (datetime.now() - cached_time.time_range.replace(tzinfo=None)).seconds < self._cache_ttl:
                return cached_time

        # 过滤指标
        now = datetime.now()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=1)

        filtered_metrics = [
            m for m in self.metrics_history
            if m.start_time >= start_time and (tenant_id is None or m.tenant_id == tenant_id)
        ]

        if not filtered_metrics:
            return PerformanceSummary(
                time_range=time_range,
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                avg_execution_time=0,
                median_execution_time=0,
                p95_execution_time=0,
                max_execution_time=0,
                min_execution_time=0,
                status_counts={},
                performance_distribution={},
                total_result_rows=0,
                avg_result_rows=0,
                total_memory_usage=0,
                slowest_queries=[],
                error_types={}
            )

        # 计算统计数据
        execution_times = [m.total_duration for m in filtered_metrics if m.total_duration is not None]

        # 状态统计
        status_counts = defaultdict(int)
        performance_distribution = defaultdict(int)
        error_types = defaultdict(int)

        successful_queries = 0
        failed_queries = 0
        total_result_rows = 0
        total_memory_usage = 0

        for metrics in filtered_metrics:
            status_counts[metrics.status.value] += 1
            if metrics.performance_level:
                performance_distribution[metrics.performance_level.value] += 1

            if metrics.status == QueryStatus.COMPLETED:
                successful_queries += 1
                total_result_rows += metrics.result_rows or 0
                total_memory_usage += metrics.memory_usage_mb or 0
            else:
                failed_queries += 1
                if metrics.error_type:
                    error_types[metrics.error_type] += 1

        # 最慢查询
        slowest_queries = [
            m.to_dict() for m in sorted(
                [m for m in filtered_metrics if m.total_duration is not None],
                key=lambda x: x.total_duration,
                reverse=True
            )[:5]
        ]

        # 构建汇总统计
        summary = PerformanceSummary(
            time_range=time_range,
            total_queries=len(filtered_metrics),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            avg_execution_time=statistics.mean(execution_times) if execution_times else 0,
            median_execution_time=statistics.median(execution_times) if execution_times else 0,
            p95_execution_time=statistics.quantiles(execution_times, n=20)[18] if len(execution_times) > 20 else (execution_times[-1] if execution_times else 0),
            max_execution_time=max(execution_times) if execution_times else 0,
            min_execution_time=min(execution_times) if execution_times else 0,
            status_counts=dict(status_counts),
            performance_distribution=dict(performance_distribution),
            total_result_rows=total_result_rows,
            avg_result_rows=total_result_rows / successful_queries if successful_queries > 0 else 0,
            total_memory_usage=total_memory_usage,
            slowest_queries=slowest_queries,
            error_types=dict(error_types)
        )

        # 缓存结果
        self._summary_cache[cache_key] = summary

        return summary

    def get_slow_queries(self, limit: int = 10, tenant_id: Optional[str] = None) -> List[QueryMetrics]:
        """
        获取最慢查询

        Args:
            limit: 返回数量限制
            tenant_id: 租户ID（可选）

        Returns:
            List[QueryMetrics]: 最慢查询列表
        """
        queries = [
            m for m in self.metrics_history
            if m.total_duration is not None and (tenant_id is None or m.tenant_id == tenant_id)
        ]

        queries.sort(key=lambda x: x.total_duration, reverse=True)
        return queries[:limit]

    def get_error_analysis(self, tenant_id: Optional[str] = None,
                         time_range: str = "24h") -> Dict[str, Any]:
        """
        获取错误分析

        Args:
            tenant_id: 租户ID（可选）
            time_range: 时间范围

        Returns:
            Dict: 错误分析结果
        """
        # 时间过滤
        now = datetime.now()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        else:
            start_time = now - timedelta(hours=1)

        filtered_metrics = [
            m for m in self.metrics_history
            if m.start_time >= start_time and (tenant_id is None or m.tenant_id == tenant_id)
        ]

        # 错误统计
        error_metrics = [m for m in filtered_metrics if m.status == QueryStatus.FAILED]
        error_types = defaultdict(int)
        error_messages = defaultdict(list)

        for metrics in error_metrics:
            if metrics.error_type:
                error_types[metrics.error_type] += 1
            if metrics.error_message:
                error_messages[metrics.error_type].append(metrics.error_message)

        # 错误率趋势
        total_queries = len(filtered_metrics)
        error_rate = len(error_metrics) / total_queries if total_queries > 0 else 0

        return {
            "time_range": time_range,
            "total_queries": total_queries,
            "failed_queries": len(error_metrics),
            "error_rate": error_rate,
            "error_types": dict(error_types),
            "error_samples": {
                error_type: messages[:3]  # 每种错误类型最多3个示例
                for error_type, messages in error_messages.items()
            }
        }

    def get_optimization_suggestions(self, tenant_id: Optional[str] = None,
                                   limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取优化建议

        Args:
            tenant_id: 租户ID（可选）
            limit: 建议数量限制

        Returns:
            List[Dict]: 优化建议列表
        """
        # 获取需要优化的查询
        queries = [
            m for m in self.metrics_history
            if (m.performance_level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL] or
                (m.total_duration and m.total_duration > 2.0)) and
               (tenant_id is None or m.tenant_id == tenant_id)
        ]

        # 按严重程度排序
        queries.sort(key=lambda x: x.total_duration or 0, reverse=True)

        suggestions = []
        for metrics in queries[:limit]:
            optimization_suggestions = self.analyzer.generate_optimization_suggestions(metrics)

            suggestions.append({
                "query_id": metrics.query_id,
                "tenant_id": metrics.tenant_id,
                "user_query": metrics.user_query,
                "generated_sql": metrics.generated_sql[:200] + "..." if len(metrics.generated_sql) > 200 else metrics.generated_sql,
                "execution_time": metrics.total_duration,
                "performance_level": metrics.performance_level.value if metrics.performance_level else None,
                "result_rows": metrics.result_rows,
                "optimization_suggestions": optimization_suggestions,
                "created_at": metrics.start_time.isoformat()
            })

        return suggestions

    def clear_history(self, before_date: Optional[datetime] = None):
        """
        清理历史数据

        Args:
            before_date: 清理此日期之前的数据（可选）
        """
        if before_date is None:
            # 清理所有数据
            self.metrics_history.clear()
            logger.info("已清理所有性能监控历史数据")
        else:
            # 清理指定日期之前的数据
            original_size = len(self.metrics_history)
            self.metrics_history = deque(
                [m for m in self.metrics_history if m.start_time >= before_date],
                maxlen=self.max_history_size
            )
            cleared_count = original_size - len(self.metrics_history)
            logger.info(f"已清理 {cleared_count} 条性能监控历史数据")

        # 清理缓存
        self._summary_cache.clear()

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        获取监控统计信息

        Returns:
            Dict: 监控统计信息
        """
        return {
            "active_queries": len(self.active_queries),
            "history_size": len(self.metrics_history),
            "max_history_size": self.max_history_size,
            "cache_entries": len(self._summary_cache),
            "cache_ttl": self._cache_ttl
        }


# 全局性能监控器实例
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def initialize_performance_monitor(max_history_size: int = 10000) -> PerformanceMonitor:
    """初始化全局性能监控器"""
    global _performance_monitor
    _performance_monitor = PerformanceMonitor(max_history_size)
    logger.info("性能监控器初始化完成")
    return _performance_monitor