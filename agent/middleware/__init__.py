# -*- coding: utf-8 -*-
"""
AgentV2 Middleware Module
=========================

Custom middleware for Data Agent V2.

Includes:
    - SQLSecurityMiddleware: SQL 安全验证中间件
    - TenantIsolationMiddleware: 租户隔离中间件
    - XAILoggerMiddleware: 可解释性日志中间件
    - ErrorTrackerMiddleware: 错误追踪中间件
    - ChartGuidanceMiddleware: 图表生成指南中间件
    - LoopDetectionMiddleware: 循环检测中间件
    - SemanticPriorityMiddleware: 语义层优先中间件
    - KnowledgeInjectionMiddleware: 知识注入中间件（双知识系统）
"""

from .sql_security import SQLSecurityMiddleware
from .semantic_priority import (
    SemanticPriorityMiddleware,
    SemanticDetectionResult,
    detect_semantic_terms,
    needs_semantic_layer
)
from .loop_detection import (
    LoopDetectionMiddleware,
    create_loop_detection_middleware
)
from .chart_guidance import (
    ChartGuidanceMiddleware,
    create_chart_guidance_middleware,
    CHART_GUIDANCE_TEMPLATE
)
from .tenant_isolation import (
    TenantIsolationMiddleware,
    TenantManager,
    get_tenant_manager,
    create_tenant_middleware
)
from .xai_logger import (
    XAILoggerMiddleware,
    XAILog,
    ReasoningStep,
    ToolCall,
    DecisionPoint,
    create_xai_logger
)
from .error_tracker import (
    ErrorTracker,
    ErrorTrackerMiddleware,
    ErrorCategory,
    ErrorEntry,
    SuccessEntry,
    create_error_tracker
)
from .table_cache_middleware import (
    TableCacheMiddleware,
    create_table_cache_middleware
)
from .time_aggregation import (
    TimeAggregationMiddleware,
    create_time_aggregation_middleware
)
# 🔴 临时禁用 - knowledge_base.py 文件不存在
# from .knowledge_middleware import (
#     KnowledgeInjectionMiddleware,
#     create_knowledge_middleware
# )

__all__ = [
    "SQLSecurityMiddleware",
    "TenantIsolationMiddleware",
    "TenantManager",
    "get_tenant_manager",
    "create_tenant_middleware",
    "XAILoggerMiddleware",
    "XAILog",
    "ReasoningStep",
    "ToolCall",
    "DecisionPoint",
    "create_xai_logger",
    "ErrorTracker",
    "ErrorTrackerMiddleware",
    "ErrorCategory",
    "ErrorEntry",
    "SuccessEntry",
    "create_error_tracker",
    "ChartGuidanceMiddleware",
    "create_chart_guidance_middleware",
    "CHART_GUIDANCE_TEMPLATE",
    "LoopDetectionMiddleware",
    "create_loop_detection_middleware",
    # 语义层优先中间件
    "SemanticPriorityMiddleware",
    "SemanticDetectionResult",
    "detect_semantic_terms",
    "needs_semantic_layer",
    # 表名缓存中间件
    "TableCacheMiddleware",
    "create_table_cache_middleware",
    # 月度聚合修正中间件
    "TimeAggregationMiddleware",
    "create_time_aggregation_middleware",
    # 知识注入中间件（双知识系统）- 🔴 临时禁用
    # "KnowledgeInjectionMiddleware",
    # "create_knowledge_middleware",
]
