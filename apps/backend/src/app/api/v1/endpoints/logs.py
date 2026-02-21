"""
# 前端日志接收端点

## [HEADER]
**文件名**: logs.py
**职责**: 接收前端发送的结构化日志，写入后端日志系统
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-02-01): 初始版本 - 实现前端日志接收端点

## [INPUT]
- JSON 请求体:
  - level: str - 日志级别（debug, info, warn, error）
  - module: str - 模块名称
  - message: str - 日志消息
  - timestamp: str - ISO格式时间戳
  - context: Dict[str, Any] - 额外上下文信息（可选）
  - user_id: str - 用户ID（可选）
  - tenant_id: str - 租户ID（可选）
  - stack_trace: str - 错误堆栈（可选，仅 error 级别）

## [OUTPUT]
- 200 OK - 日志接收成功
- 422 Unprocessable Entity - 请求格式错误

## [LINK]
**上游依赖**:
- [../../core/logging_config.py](../../core/logging_config.py) - 日志配置

**下游依赖**:
- 后端日志系统

## [POS]
**路径**: backend/src/app/api/v1/endpoints/logs.py
**模块层级**: Level 4 - API端点层
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field

from src.app.core.logging_decorators import log_api_request

router = APIRouter()
logger = logging.getLogger("frontend_logs")


class FrontendLogEntry(BaseModel):
    """单条前端日志条目"""
    level: str = Field(..., description="日志级别: debug, info, warn, error")
    module: str = Field(..., description="模块名称")
    message: str = Field(..., description="日志消息")
    timestamp: str = Field(..., description="ISO格式时间戳")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外上下文")
    user_id: Optional[str] = Field(None, description="用户ID")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    stack_trace: Optional[str] = Field(None, description="错误堆栈（仅error级别）")
    url: Optional[str] = Field(None, description="页面URL")
    component: Optional[str] = Field(None, description="组件名称")


class BatchLogsRequest(BaseModel):
    """批量日志请求"""
    logs: List[FrontendLogEntry] = Field(..., description="日志条目列表")
    user_id: Optional[str] = Field(None, description="全局用户ID")
    tenant_id: Optional[str] = Field(None, description="全局租户ID")


def _log_frontend_entry(entry: FrontendLogEntry, global_user_id: Optional[str] = None,
                        global_tenant_id: Optional[str] = None):
    """将单条前端日志写入后端日志系统"""
    # 合并全局和局部用户ID/租户ID
    user_id = entry.user_id or global_user_id
    tenant_id = entry.tenant_id or global_tenant_id

    # 映射前端日志级别到 Python 日志级别
    level_mapping = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR,
    }
    log_level = level_mapping.get(entry.level.lower(), logging.INFO)

    # 构建日志消息
    prefix = f"[{entry.module}]"
    if entry.component:
        prefix = f"[{entry.module}:{entry.component}]"
    log_message = f"{prefix} {entry.message}"

    # 构建额外字段
    extra_fields = {
        "event_type": "frontend_log",
        "frontend_module": entry.module,
        "frontend_level": entry.level,
        "frontend_timestamp": entry.timestamp,
    }

    if entry.url:
        extra_fields["url"] = entry.url
    if entry.component:
        extra_fields["component"] = entry.component
    if user_id:
        extra_fields["user_id"] = user_id
    if tenant_id:
        extra_fields["tenant_id"] = tenant_id
    if entry.context:
        extra_fields["context"] = entry.context

    # 记录日志
    logger.log(
        log_level,
        log_message,
        extra=extra_fields
    )

    # 如果是错误级别且有堆栈信息，额外记录
    if entry.level.lower() == "error" and entry.stack_trace:
        logger.error(
            f"[{entry.module}] Stack trace:\n{entry.stack_trace}",
            extra={
                "event_type": "frontend_error_stack",
                "frontend_module": entry.module,
                "user_id": user_id,
                "tenant_id": tenant_id,
            }
        )


@router.post("/single", status_code=status.HTTP_200_OK)
@log_api_request("ReceiveFrontendLog")
async def receive_single_log(request: Request, entry: FrontendLogEntry):
    """
    接收单条前端日志

    Args:
        entry: 单条日志条目

    Returns:
        成功确认
    """
    try:
        # 从请求状态中获取认证信息
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
        tenant_id = getattr(request.state, "tenant_id", None) if hasattr(request, "state") else None

        _log_frontend_entry(entry, user_id, tenant_id)

        return {"status": "ok", "message": "Log received"}

    except Exception as e:
        logger.error(f"Failed to process frontend log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process log: {str(e)}"
        )


@router.post("/batch", status_code=status.HTTP_200_OK)
@log_api_request("ReceiveFrontendBatchLogs")
async def receive_batch_logs(request: Request, batch: BatchLogsRequest):
    """
    接收批量前端日志

    前端可以累积多条日志后批量发送，减少网络请求

    Args:
        batch: 包含多条日志的请求

    Returns:
        成功确认及处理数量
    """
    try:
        # 从请求状态中获取认证信息
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
        tenant_id = getattr(request.state, "tenant_id", None) if hasattr(request, "state") else None

        # 处理每条日志
        processed_count = 0
        for entry in batch.logs:
            try:
                _log_frontend_entry(entry, user_id, tenant_id)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process log entry: {str(e)}")

        logger.info(
            f"Received {len(batch.logs)} frontend logs, processed {processed_count}",
            extra={
                "event_type": "frontend_batch_logs",
                "total_logs": len(batch.logs),
                "processed_logs": processed_count,
                "user_id": user_id,
                "tenant_id": tenant_id,
            }
        )

        return {
            "status": "ok",
            "message": f"Processed {processed_count} logs",
            "processed_count": processed_count,
            "total_count": len(batch.logs)
        }

    except Exception as e:
        logger.error(f"Failed to process batch logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process batch: {str(e)}"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """日志接收端点健康检查"""
    return {
        "status": "healthy",
        "service": "frontend_logs_receiver",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# 后端日志查询端点
# ============================================================================

from pathlib import Path

# 日志目录配置
BACKEND_LOG_DIR = Path("backend/logs")
if not BACKEND_LOG_DIR.exists():
    # 相对于后端项目根目录
    BACKEND_LOG_DIR = Path(__file__).parent.parent.parent.parent.parent / "logs"


def parse_json_log_line(line: str) -> Optional[Dict[str, Any]]:
    """解析单行JSON日志"""
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def read_log_file_lines(
    file_path: Path,
    session_id: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    读取日志文件并解析

    Args:
        file_path: 日志文件路径
        session_id: 可选的session_id过滤
        limit: 返回的日志条数限制

    Returns:
        解析后的日志列表
    """
    if not file_path.exists():
        return []

    logs = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # 从末尾开始读取
        for line in reversed(lines[-limit * 10:]):  # 多读一些以应对过滤
            if not line.strip():
                continue
            log = parse_json_log_line(line)
            if log:
                # 应用session过滤
                if session_id is None or log.get('session_id') == session_id:
                    logs.append(log)
                    if len(logs) >= limit:
                        break
    except Exception as e:
        logger.error(f"读取日志文件失败 {file_path}: {e}")

    return logs


@router.get("/backend/session/{session_id}")
@log_api_request("GetBackendSessionLogs")
async def get_session_logs(
    session_id: str,
    limit: int = 100
):
    """
    获取指定会话的后端日志

    Args:
        session_id: 会话ID
        limit: 返回的日志条数限制

    Returns:
        会话相关的日志列表
    """
    try:
        all_logs = []

        # 读取各个日志文件
        log_files = [
            BACKEND_LOG_DIR / "application.log",
            BACKEND_LOG_DIR / "error.log",
            BACKEND_LOG_DIR / "debug.log",
        ]

        # 添加Agent日期日志
        agent_logs = sorted(
            BACKEND_LOG_DIR.glob("agent_*.log"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        log_files.extend(agent_logs[:3])  # 只读最近的3个Agent日志文件

        for log_file in log_files:
            logs = read_log_file_lines(log_file, session_id=session_id, limit=limit)
            all_logs.extend(logs)

        # 按时间戳排序
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=False)

        # 应用限制
        all_logs = all_logs[:limit]

        return {
            "session_id": session_id,
            "count": len(all_logs),
            "logs": all_logs
        }

    except Exception as e:
        logger.error(f"获取会话日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志失败: {str(e)}"
        )


@router.get("/backend/recent")
@log_api_request("GetRecentBackendLogs")
async def get_recent_logs(
    limit: int = 100,
    level: Optional[str] = None
):
    """
    获取最近的后端日志

    Args:
        limit: 返回的日志条数限制
        level: 可选的日志级别过滤 (DEBUG, INFO, WARNING, ERROR)

    Returns:
        最近的日志列表
    """
    try:
        all_logs = []

        # 读取最新的Agent日志
        agent_logs = sorted(
            BACKEND_LOG_DIR.glob("agent_*.log"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        for log_file in agent_logs[:3]:
            logs = read_log_file_lines(log_file, limit=limit)
            all_logs.extend(logs)

        # 按时间戳排序（最近的在前）
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # 应用级别过滤
        if level:
            all_logs = [log for log in all_logs if log.get('level') == level.upper()]

        # 应用限制
        all_logs = all_logs[:limit]

        return {
            "count": len(all_logs),
            "logs": all_logs
        }

    except Exception as e:
        logger.error(f"获取最近日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志失败: {str(e)}"
        )


@router.get("/backend/errors")
@log_api_request("GetBackendErrorLogs")
async def get_error_logs(
    limit: int = 50,
    hours: Optional[int] = None
):
    """
    获取错误日志

    Args:
        limit: 返回的日志条数限制
        hours: 时间范围（小时），None表示全部

    Returns:
        错误日志列表
    """
    try:
        all_logs = []

        # 从多个日志文件中收集错误
        log_files = [
            BACKEND_LOG_DIR / "error.log",
            BACKEND_LOG_DIR / "application.log",
        ]

        # 添加Agent日志
        agent_logs = list(BACKEND_LOG_DIR.glob("agent_*.log"))
        log_files.extend(agent_logs)

        for log_file in log_files:
            logs = read_log_file_lines(log_file, limit=limit * 2)
            all_logs.extend(logs)

        # 过滤错误级别
        error_logs = [
            log for log in all_logs
            if log.get('level') in ('ERROR', 'error', 'CRITICAL', 'critical')
            or log.get('message_type') == 'error'
        ]

        # 按时间戳排序（最近的在前）
        error_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # 应用时间范围过滤（如果指定）
        if hours:
            from datetime import datetime, timedelta
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            error_logs = [
                log for log in error_logs
                if log.get('timestamp', '') >= cutoff_time
            ]

        # 应用限制
        error_logs = error_logs[:limit]

        return {
            "count": len(error_logs),
            "logs": error_logs
        }

    except Exception as e:
        logger.error(f"获取错误日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取错误日志失败: {str(e)}"
        )


@router.get("/backend/summary")
@log_api_request("GetBackendLogSummary")
async def get_log_summary():
    """
    获取后端日志摘要

    Returns:
        日志摘要信息
    """
    try:
        summary = {
            "total_files": 0,
            "total_size_mb": 0,
            "log_files": [],
            "error_count": 0,
            "last_errors": []
        }

        # 统计日志文件
        for log_file in BACKEND_LOG_DIR.glob("*.log"):
            size_mb = log_file.stat().st_size / (1024 * 1024)
            summary["total_size_mb"] += size_mb
            summary["total_files"] += 1
            summary["log_files"].append({
                "name": log_file.name,
                "size_mb": round(size_mb, 2),
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })

        # 获取最近的错误
        error_log = BACKEND_LOG_DIR / "error.log"
        if error_log.exists():
            recent_errors = read_log_file_lines(error_log, limit=10)
            summary["error_count"] = len(recent_errors)
            summary["last_errors"] = recent_errors[:5]

        return summary

    except Exception as e:
        logger.error(f"获取日志摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取摘要失败: {str(e)}"
        )
