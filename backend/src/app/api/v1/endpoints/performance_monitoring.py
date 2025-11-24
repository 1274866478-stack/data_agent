"""
性能监控API端点
提供查询性能监控和统计信息
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse

from src.app.core.auth import get_current_tenant_user
from src.app.services.query_performance_monitor import query_perf_monitor
from src.app.data.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats/real-time")
async def get_real_time_stats(current_user: Tenant = Depends(get_current_tenant_user)):
    """
    获取实时性能统计信息
    """
    try:
        stats = query_perf_monitor.get_real_time_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取实时统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取性能统计失败")


@router.get("/stats/tenant/{tenant_id}")
async def get_tenant_performance(
    tenant_id: str,
    hours: int = Query(24, ge=1, le=168),  # 1小时到7天
    current_user: Tenant = Depends(get_current_tenant_user)
):
    """
    获取租户性能报告

    Args:
        tenant_id: 租户ID
        hours: 统计时间范围（小时）
    """
    try:
        # 权限检查：只能查看自己的数据或管理员权限
        if tenant_id != current_user.id and not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="无权访问其他租户的性能数据")

        performance = query_perf_monitor.get_tenant_performance(tenant_id, hours)
        return {
            "success": True,
            "data": performance
        }
    except Exception as e:
        logger.error(f"获取租户性能报告失败: {e}")
        raise HTTPException(status_code=500, detail="获取租户性能数据失败")


@router.get("/queries/slow")
async def get_slow_queries(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    current_user: Tenant = Depends(get_current_tenant_user)
):
    """
    获取慢查询列表

    Args:
        hours: 时间范围（小时）
        limit: 返回数量限制
    """
    try:
        slow_queries = query_perf_monitor.get_slow_queries(hours, limit)
        return {
            "success": True,
            "data": slow_queries,
            "total": len(slow_queries)
        }
    except Exception as e:
        logger.error(f"获取慢查询失败: {e}")
        raise HTTPException(status_code=500, detail="获取慢查询数据失败")


@router.get("/queries/types")
async def get_query_type_performance(
    current_user: Tenant = Depends(get_current_tenant_user)
):
    """
    获取按查询类型的性能分析
    """
    try:
        type_performance = query_perf_monitor.get_query_type_performance()
        return {
            "success": True,
            "data": type_performance
        }
    except Exception as e:
        logger.error(f"获取查询类型性能失败: {e}")
        raise HTTPException(status_code=500, detail="获取查询类型性能数据失败")


@router.get("/warnings")
async def get_performance_warnings(
    hours: int = Query(24, ge=1, le=168),
    current_user: Tenant = Depends(get_current_tenant_user)
):
    """
    获取性能警告

    Args:
        hours: 时间范围（小时）
    """
    try:
        warnings = query_perf_monitor.get_warnings(hours)
        return {
            "success": True,
            "data": warnings,
            "total": len(warnings)
        }
    except Exception as e:
        logger.error(f"获取性能警告失败: {e}")
        raise HTTPException(status_code=500, detail="获取性能警告失败")


@router.get("/export")
async def export_performance_metrics(
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: Tenant = Depends(get_current_tenant_user)
):
    """
    导出性能指标数据

    Args:
        format: 导出格式 (json, csv)
    """
    try:
        if format == "json":
            data = query_perf_monitor.export_metrics("json")
            return PlainTextResponse(
                content=data,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )
        else:
            # CSV格式导出
            csv_data = _export_to_csv()
            return PlainTextResponse(
                content=csv_data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
    except Exception as e:
        logger.error(f"导出性能指标失败: {e}")
        raise HTTPException(status_code=500, detail="导出性能指标失败")


@router.post("/monitor/start")
async def start_monitoring(current_user: Tenant = Depends(get_current_tenant_user)):
    """
    启动性能监控
    """
    try:
        query_perf_monitor.start_monitoring()
        return {
            "success": True,
            "message": "性能监控已启动"
        }
    except Exception as e:
        logger.error(f"启动性能监控失败: {e}")
        raise HTTPException(status_code=500, detail="启动性能监控失败")


@router.post("/monitor/stop")
async def stop_monitoring(current_user: Tenant = Depends(get_current_tenant_user)):
    """
    停止性能监控
    """
    try:
        query_perf_monitor.stop_monitoring()
        return {
            "success": True,
            "message": "性能监控已停止"
        }
    except Exception as e:
        logger.error(f"停止性能监控失败: {e}")
        raise HTTPException(status_code=500, detail="停止性能监控失败")


@router.delete("/history")
async def clear_performance_history(
    confirm: bool = Query(False, description="确认清除历史数据"),
    current_user: Tenant = Depends(get_current_tenant_user)
):
    """
    清除性能历史数据

    Args:
        confirm: 确认标志
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="请添加 confirm=true 参数确认清除操作"
            )

        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=403,
                detail="只有管理员可以清除性能历史数据"
            )

        query_perf_monitor.clear_history()
        return {
            "success": True,
            "message": "性能历史数据已清除"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除性能历史数据失败: {e}")
        raise HTTPException(status_code=500, detail="清除性能历史数据失败")


@router.get("/health")
async def get_performance_monitor_health(
    current_user: Tenant = Depends(get_current_tenant_user)
):
    """
    获取性能监控服务健康状态
    """
    try:
        stats = query_perf_monitor.get_real_time_stats()

        # 健康状态评估
        health_status = "healthy"
        issues = []

        # 检查错误率
        error_rate = stats.get('error_rate', 0)
        if error_rate > 10:  # 错误率超过10%
            health_status = "unhealthy"
            issues.append(f"查询错误率过高: {error_rate}%")
        elif error_rate > 5:  # 错误率超过5%
            health_status = "warning"
            issues.append(f"查询错误率较高: {error_rate}%")

        # 检查平均执行时间
        avg_time = stats.get('avg_execution_time', 0)
        if avg_time > 10:  # 平均执行时间超过10秒
            health_status = "unhealthy"
            issues.append(f"平均执行时间过长: {avg_time}秒")
        elif avg_time > 5:  # 平均执行时间超过5秒
            health_status = "warning"
            issues.append(f"平均执行时间较长: {avg_time}秒")

        # 检查缓存命中率
        cache_hit_rate = stats.get('cache_hit_rate', 0)
        if cache_hit_rate < 30:  # 缓存命中率低于30%
            health_status = "warning"
            issues.append(f"缓存命中率较低: {cache_hit_rate}%")

        # 检查系统资源
        memory_usage = stats.get('memory_usage_mb', 0)
        cpu_usage = stats.get('cpu_usage_percent', 0)
        if memory_usage > 1000:  # 内存使用超过1GB
            health_status = "unhealthy"
            issues.append(f"内存使用过高: {memory_usage}MB")
        elif memory_usage > 500:  # 内存使用超过500MB
            health_status = "warning"
            issues.append(f"内存使用较高: {memory_usage}MB")

        if cpu_usage > 80:  # CPU使用超过80%
            health_status = "unhealthy"
            issues.append(f"CPU使用过高: {cpu_usage}%")
        elif cpu_usage > 60:  # CPU使用超过60%
            health_status = "warning"
            issues.append(f"CPU使用较高: {cpu_usage}%")

        return {
            "success": True,
            "data": {
                "status": health_status,
                "uptime_hours": stats.get('uptime_hours', 0),
                "total_queries": stats.get('total_queries', 0),
                "queries_per_second": stats.get('queries_per_second', 0),
                "issues": issues,
                "metrics": {
                    "error_rate": error_rate,
                    "avg_execution_time": avg_time,
                    "cache_hit_rate": cache_hit_rate,
                    "memory_usage_mb": memory_usage,
                    "cpu_usage_percent": cpu_usage
                }
            }
        }
    except Exception as e:
        logger.error(f"获取性能监控健康状态失败: {e}")
        return {
            "success": False,
            "status": "error",
            "error": str(e)
        }


def _export_to_csv() -> str:
    """导出为CSV格式"""
    import csv
    from io import StringIO

    stats = query_perf_monitor.get_real_time_stats()
    slow_queries = query_perf_monitor.get_slow_queries(hours=24, limit=100)

    # 创建CSV内容
    output = StringIO()
    writer = csv.writer(output)

    # 写入统计数据
    writer.writerow(["性能监控数据导出"])
    writer.writerow(["导出时间", datetime.now().isoformat()])
    writer.writerow([])

    # 实时统计
    writer.writerow(["实时统计"])
    writer.writerow(["指标", "值"])
    for key, value in stats.items():
        writer.writerow([key, value])

    writer.writerow([])

    # 慢查询
    writer.writerow(["慢查询列表"])
    writer.writerow(["查询ID", "租户ID", "查询类型", "执行时间", "行数", "错误", "时间戳"])
    for query in slow_queries:
        writer.writerow([
            query.get('query_id', ''),
            query.get('tenant_id', ''),
            query.get('query_type', ''),
            query.get('execution_time', 0),
            query.get('row_count', 0),
            query.get('error', False),
            query.get('timestamp', '')
        ])

    return output.getvalue()