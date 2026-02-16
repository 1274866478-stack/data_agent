"""
# 增强版性能监控API端点

## [HEADER]
**文件名**: performance_enhanced.py
**职责**: 提供全面的查询性能分析、监控统计、优化建议和性能仪表板的RESTful API
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本

## [INPUT]
- time_range: str - 时间范围（1h, 24h, 7d, 30d）
- limit: int - 返回数量限制
- query_id: str - 查询ID
- current_user: User - 当前用户（通过依赖注入）
- tenant_id: str - 租户ID（通过依赖注入）

## [OUTPUT]
- 性能汇总统计: Dict[str, Any]
- 慢查询列表: List[Dict[str, Any]]
- 错误分析报告: Dict[str, Any]
- 优化建议列表: List[Dict[str, Any]]
- 查询详细指标: Dict[str, Any]
- 监控系统统计: Dict[str, Any]
- 性能仪表板数据: Dict[str, Any]
- 性能警报列表: List[Dict[str, Any]]

## [LINK]
**上游依赖**:
- [../../core/dependencies.py](../../core/dependencies.py) - get_current_user, tenant_required依赖注入
- [../../services/performance_monitor.py](../../services/performance_monitor.py) - PerformanceMonitor核心服务
- [../../data/models.py](../../data/models.py) - User模型

**下游依赖**:
- 无（API端点为最外层）

**调用方**:
- 前端性能监控仪表板
- 运维监控平台
- 性能优化工具

## [POS]
**路径**: backend/src/app/api/v1/endpoints/performance_enhanced.py
**模块层级**: Level 3（API端点层）
**依赖深度**: 2 层（依赖于services和core层）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from src.app.core.dependencies import get_current_user, tenant_required
from src.app.services.performance_monitor import (
    get_performance_monitor, PerformanceMonitor, QueryMetrics
)
from src.app.data.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/summary")
async def get_performance_summary(
    time_range: str = Query("24h", description="时间范围: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_required)
) -> Dict[str, Any]:
    """
    获取性能汇总统计

    Args:
        time_range: 时间范围
        current_user: 当前用户
        tenant_id: 租户ID

    Returns:
        Dict: 性能汇总统计
    """
    try:
        monitor = get_performance_monitor()
        summary = monitor.get_performance_summary(tenant_id=tenant_id, time_range=time_range)
        return summary.to_dict()

    except Exception as e:
        logger.error(f"获取性能汇总统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能汇总统计失败: {str(e)}")


@router.get("/slow-queries")
async def get_slow_queries(
    limit: int = Query(10, description="返回数量限制", ge=1, le=100),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_required)
) -> List[Dict[str, Any]]:
    """
    获取最慢查询列表

    Args:
        limit: 返回数量限制
        current_user: 当前用户
        tenant_id: 租户ID

    Returns:
        List[Dict]: 最慢查询列表
    """
    try:
        monitor = get_performance_monitor()
        slow_queries = monitor.get_slow_queries(limit=limit, tenant_id=tenant_id)
        return [query.to_dict() for query in slow_queries]

    except Exception as e:
        logger.error(f"获取最慢查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最慢查询失败: {str(e)}")


@router.get("/error-analysis")
async def get_error_analysis(
    time_range: str = Query("24h", description="时间范围: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_required)
) -> Dict[str, Any]:
    """
    获取错误分析报告

    Args:
        time_range: 时间范围
        current_user: 当前用户
        tenant_id: 租户ID

    Returns:
        Dict: 错误分析结果
    """
    try:
        monitor = get_performance_monitor()
        error_analysis = monitor.get_error_analysis(tenant_id=tenant_id, time_range=time_range)
        return error_analysis

    except Exception as e:
        logger.error(f"获取错误分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取错误分析失败: {str(e)}")


@router.get("/optimization-suggestions")
async def get_optimization_suggestions(
    limit: int = Query(20, description="建议数量限制", ge=1, le=50),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_required)
) -> List[Dict[str, Any]]:
    """
    获取性能优化建议

    Args:
        limit: 建议数量限制
        current_user: 当前用户
        tenant_id: 租户ID

    Returns:
        List[Dict]: 优化建议列表
    """
    try:
        monitor = get_performance_monitor()
        suggestions = monitor.get_optimization_suggestions(tenant_id=tenant_id, limit=limit)
        return suggestions

    except Exception as e:
        logger.error(f"获取优化建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优化建议失败: {str(e)}")


@router.get("/query/{query_id}")
async def get_query_details(
    query_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_required)
) -> Dict[str, Any]:
    """
    获取特定查询的详细性能指标

    Args:
        query_id: 查询ID
        current_user: 当前用户
        tenant_id: 租户ID

    Returns:
        Dict: 查询详细指标
    """
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_query_metrics(query_id)

        if not metrics:
            raise HTTPException(status_code=404, detail="查询不存在")

        # 验证租户权限
        if metrics.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问此查询数据")

        return metrics.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取查询详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取查询详情失败: {str(e)}")


@router.get("/monitoring-stats")
async def get_monitoring_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取监控系统状态统计

    Args:
        current_user: 当前用户

    Returns:
        Dict: 监控系统统计信息
    """
    try:
        monitor = get_performance_monitor()
        stats = monitor.get_monitoring_stats()
        return stats

    except Exception as e:
        logger.error(f"获取监控统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取监控统计失败: {str(e)}")


@router.get("/dashboard")
async def get_performance_dashboard(
    time_range: str = Query("24h", description="时间范围: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_required)
) -> Dict[str, Any]:
    """
    获取性能仪表板数据（综合多个API的结果）

    Args:
        time_range: 时间范围
        current_user: 当前用户
        tenant_id: 租户ID

    Returns:
        Dict: 仪表板数据
    """
    try:
        monitor = get_performance_monitor()

        # 并行获取各种数据
        summary_task = asyncio.create_task(
            asyncio.to_thread(monitor.get_performance_summary, tenant_id, time_range)
        )
        slow_queries_task = asyncio.create_task(
            asyncio.to_thread(monitor.get_slow_queries, 5, tenant_id)
        )
        error_analysis_task = asyncio.create_task(
            asyncio.to_thread(monitor.get_error_analysis, tenant_id, time_range)
        )
        optimization_task = asyncio.create_task(
            asyncio.to_thread(monitor.get_optimization_suggestions, tenant_id, 10)
        )

        # 等待所有任务完成
        summary, slow_queries, error_analysis, optimization = await asyncio.gather(
            summary_task, slow_queries_task, error_analysis_task, optimization_task
        )

        # 构建仪表板数据
        dashboard_data = {
            "summary": summary.to_dict(),
            "slow_queries": [query.to_dict() for query in slow_queries],
            "error_analysis": error_analysis,
            "optimization_suggestions": optimization,
            "monitoring_stats": monitor.get_monitoring_stats(),
            "generated_at": datetime.now().isoformat()
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"获取性能仪表板数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能仪表板数据失败: {str(e)}")


@router.get("/alerts")
async def get_performance_alerts(
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_required)
) -> List[Dict[str, Any]]:
    """
    获取性能警报

    Args:
        current_user: 当前用户
        tenant_id: 租户ID

    Returns:
        List[Dict]: 性能警报列表
    """
    try:
        monitor = get_performance_monitor()

        alerts = []

        # 检查最近的查询性能
        recent_slow_queries = monitor.get_slow_queries(limit=5, tenant_id=tenant_id)
        for query in recent_slow_queries:
            if query.total_duration and query.total_duration > 10.0:
                alerts.append({
                    "type": "slow_query",
                    "severity": "high",
                    "message": f"查询执行时间过长: {query.total_duration:.2f}秒",
                    "query_id": query.query_id,
                    "user_query": query.user_query[:100] + "..." if len(query.user_query) > 100 else query.user_query,
                    "timestamp": query.start_time.isoformat()
                })

        # 检查错误率
        error_analysis = monitor.get_error_analysis(tenant_id=tenant_id, time_range="1h")
        if error_analysis["error_rate"] > 0.1:  # 错误率超过10%
            alerts.append({
                "type": "high_error_rate",
                "severity": "critical",
                "message": f"查询错误率过高: {error_analysis['error_rate']:.2%}",
                "error_rate": error_analysis["error_rate"],
                "failed_queries": error_analysis["failed_queries"],
                "total_queries": error_analysis["total_queries"],
                "timestamp": datetime.now().isoformat()
            })

        # 检查活跃查询数量
        stats = monitor.get_monitoring_stats()
        if stats["active_queries"] > 20:
            alerts.append({
                "type": "high_concurrency",
                "severity": "medium",
                "message": f"活跃查询数量过多: {stats['active_queries']}",
                "active_queries": stats["active_queries"],
                "timestamp": datetime.now().isoformat()
            })

        return alerts

    except Exception as e:
        logger.error(f"获取性能警报失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能警报失败: {str(e)}")


# 健康检查端点
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """性能监控服务健康检查"""
    try:
        monitor = get_performance_monitor()
        stats = monitor.get_monitoring_stats()

        return {
            "status": "healthy",
            "service": "performance_monitor",
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }

    except Exception as e:
        logger.error(f"性能监控健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "service": "performance_monitor",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }