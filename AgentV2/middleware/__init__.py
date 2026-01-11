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
"""

from .sql_security import SQLSecurityMiddleware
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
    "create_error_tracker"
]
