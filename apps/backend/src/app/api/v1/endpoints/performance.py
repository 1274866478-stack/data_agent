"""
# 性能监控API端点

## [HEADER]
**文件名**: performance.py
**职责**: 提供查询性能指标、慢查询分析和缓存状态监控的RESTful API
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本

## [INPUT]
- tenant_id: str - 租户ID（用于数据隔离）
- start_time: Optional[datetime] - 查询起始时间
- end_time: Optional[datetime] - 查询结束时间
- limit: int - 返回记录数限制（最大1000）
- threshold_ms: float - 慢查询阈值（毫秒）
- days: int - 统计天数（1-90天）

## [OUTPUT]
- 查询性能指标列表: Dict[str, Any]
- 性能摘要统计: Dict[str, Any]
- 慢查询列表: List[Dict[str, Any]]
- 缓存状态信息: Dict[str, Any]
- 支持的数据库类型信息: Dict[str, Any]

## [LINK]
**上游依赖**:
- [../../core/auth.py](../../core/auth.py) - get_current_user依赖注入
- [../../services/rag_sql_service.py](../../services/rag_sql_service.py) - RAGSQLService性能指标获取
- [../../data/models.py](../../data/models.py) - User模型

**下游依赖**:
- 无（API端点为最外层）

**调用方**:
- 前端性能监控仪表板
- 管理员监控界面
- 性能分析工具

## [POS]
**路径**: backend/src/app/api/v1/endpoints/performance.py
**模块层级**: Level 3（API端点层）
**依赖深度**: 2 层（依赖于services和core层）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta

from ...services.rag_sql_service import RAGSQLService
from ...core.auth import get_current_user
from ...data.models import User

router = APIRouter()


@router.get("/query-metrics", summary="获取查询性能指标")
async def get_query_metrics(
    tenant_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, le=1000, description="限制数量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定租户的查询性能指标

    Args:
        tenant_id: 租户ID
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        limit: 返回记录数限制（最大1000）
        current_user: 当前用户

    Returns:
        Dict: 包含性能指标列表的响应

    Raises:
        HTTPException: 权限不足或服务错误
    """
    try:
        # 验证租户权限
        if current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问其他租户数据")

        # 创建RAG-SQL服务实例
        rag_service = RAGSQLService()

        # 获取性能指标
        metrics = await rag_service.get_performance_metrics(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "metrics": metrics,
                "total": len(metrics),
                "filters": {
                    "tenant_id": tenant_id,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "limit": limit
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.get("/performance-summary", summary="获取性能摘要统计")
async def get_performance_summary(
    tenant_id: str,
    days: int = Query(7, le=90, ge=1, description="统计天数（1-90天）"),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定天数内的性能摘要统计

    Args:
        tenant_id: 租户ID
        days: 统计天数（1-90天）
        current_user: 当前用户

    Returns:
        Dict: 性能摘要统计

    Raises:
        HTTPException: 权限不足或服务错误
    """
    try:
        # 验证租户权限
        if current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问其他租户数据")

        # 创建RAG-SQL服务实例
        rag_service = RAGSQLService()

        # 获取性能摘要
        summary = await rag_service.get_performance_summary(
            tenant_id=tenant_id,
            days=days
        )

        return {
            "success": True,
            "data": summary
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能摘要失败: {str(e)}")


@router.get("/slow-queries", summary="获取慢查询列表")
async def get_slow_queries(
    tenant_id: str,
    threshold_ms: float = Query(5000.0, ge=1000.0, description="慢查询阈值（毫秒）"),
    limit: int = Query(50, le=200, ge=1, description="返回数量限制"),
    current_user: User = Depends(get_current_user)
):
    """
    获取超过指定阈值的慢查询列表

    Args:
        tenant_id: 租户ID
        threshold_ms: 慢查询阈值（毫秒，最小1000ms）
        limit: 返回数量限制（1-200）
        current_user: 当前用户

    Returns:
        Dict: 慢查询列表

    Raises:
        HTTPException: 权限不足或服务错误
    """
    try:
        # 验证租户权限
        if current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问其他租户数据")

        # 创建RAG-SQL服务实例
        rag_service = RAGSQLService()

        # 获取慢查询
        slow_queries = await rag_service.get_slow_queries(
            tenant_id=tenant_id,
            threshold_ms=threshold_ms,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "slow_queries": slow_queries,
                "threshold_ms": threshold_ms,
                "total": len(slow_queries),
                "tenant_id": tenant_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取慢查询失败: {str(e)}")


@router.delete("/metrics", summary="清除性能指标")
async def clear_performance_metrics(
    tenant_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    清除指定租户的性能指标数据

    Args:
        tenant_id: 租户ID
        current_user: 当前用户

    Returns:
        Dict: 操作结果

    Raises:
        HTTPException: 权限不足或服务错误
    """
    try:
        # 验证租户权限
        if current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问其他租户数据")

        # 创建RAG-SQL服务实例
        rag_service = RAGSQLService()

        # 清除性能指标
        await rag_service.clear_performance_metrics(tenant_id)

        return {
            "success": True,
            "message": f"已清除租户 {tenant_id} 的性能指标数据",
            "tenant_id": tenant_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除性能指标失败: {str(e)}")


@router.get("/database-types", summary="获取支持的数据库类型")
async def get_supported_database_types():
    """
    获取系统支持的数据库类型列表

    Returns:
        Dict: 支持的数据库类型信息

    Raises:
        HTTPException: 服务错误
    """
    try:
        from .....services.database_factory import DatabaseAdapterFactory

        # 获取支持的数据库类型
        supported_types = DatabaseAdapterFactory.get_supported_types()

        # 获取详细的适配器信息
        adapter_info = {}
        for db_type in supported_types:
            info = DatabaseAdapterFactory.get_adapter_info(db_type)
            if info:
                adapter_info[db_type] = info

        return {
            "success": True,
            "data": {
                "supported_types": supported_types,
                "adapter_info": adapter_info,
                "total": len(supported_types)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库类型信息失败: {str(e)}")


@router.get("/cache-status", summary="获取缓存状态")
async def get_cache_status(
    tenant_id: Optional[str] = Query(None, description="租户ID（可选）"),
    current_user: User = Depends(get_current_user)
):
    """
    获取缓存状态信息

    Args:
        tenant_id: 租户ID（可选，不提供则返回全局状态）
        current_user: 当前用户

    Returns:
        Dict: 缓存状态信息

    Raises:
        HTTPException: 权限不足或服务错误
    """
    try:
        # 如果提供了租户ID，验证权限
        if tenant_id and current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问其他租户数据")

        # 创建RAG-SQL服务实例
        rag_service = RAGSQLService()

        # 获取健康状态（包含缓存信息）
        health_status = await rag_service.get_health_status()

        # 提取缓存相关信息
        cache_info = {
            "cache_type": health_status.get("cache_type"),
            "cache_size": health_status.get("cache_size"),
            "stats_cache_size": health_status.get("stats_cache_size"),
            "performance_monitor_buffer_size": health_status.get("performance_monitor_buffer_size"),
            "active_tenants": health_status.get("active_tenants"),
            "last_updated": health_status.get("last_updated")
        }

        # 如果指定了租户ID，添加租户特定信息
        if tenant_id:
            # 获取租户统计信息
            tenant_stats = await performance_monitor.get_tenant_stats(tenant_id)
            cache_info["tenant_stats"] = tenant_stats

        return {
            "success": True,
            "data": cache_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存状态失败: {str(e)}")