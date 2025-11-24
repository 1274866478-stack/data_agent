"""
增强日志配置模块
提供结构化日志、性能监控和安全过滤功能
"""

import logging
import logging.handlers
import json
import time
import traceback
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.app.core.config import settings
from src.app.core.security_monitor import SensitiveDataFilter


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self.sensitive_filter = SensitiveDataFilter()

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON结构"""
        # 基础日志信息
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self.sensitive_filter.filter_sensitive_data(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加线程和进程信息（在高并发环境中有用）
        if hasattr(record, 'thread'):
            log_data["thread_id"] = record.thread
        if hasattr(record, 'process'):
            log_data["process_id"] = record.process

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # 添加额外的上下文信息
        if self.include_extra and hasattr(record, '__dict__'):
            extra_fields = {
                k: v for k, v in record.__dict__.items()
                if k not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }
            }

            if extra_fields:
                log_data["extra"] = self.sensitive_filter.filter_dict(extra_fields)

        # 添加性能相关字段（如果存在）
        if hasattr(record, 'duration'):
            log_data["duration_ms"] = record.duration * 1000
        if hasattr(record, 'tenant_id'):
            log_data["tenant_id"] = record.tenant_id
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id

        return json.dumps(log_data, ensure_ascii=False, default=str)


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
        self.sensitive_filter = SensitiveDataFilter()

    def log_function_performance(self, func_name: str, duration: float,
                               success: bool = True, **context):
        """记录函数性能"""
        level = logging.INFO if success else logging.WARNING
        message = f"函数执行: {func_name} - 耗时: {duration:.3f}s - 状态: {'成功' if success else '失败'}"

        # 过滤敏感信息
        safe_context = self.sensitive_filter.filter_dict(context)

        self.logger.log(
            level,
            message,
            extra={
                "function": func_name,
                "duration": duration,
                "success": success,
                "context": safe_context
            }
        )

    def log_api_request(self, method: str, endpoint: str, duration: float,
                       status_code: int, user_id: Optional[str] = None,
                       tenant_id: Optional[str] = None, **context):
        """记录API请求性能"""
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING if 400 <= status_code < 500 else logging.ERROR

        message = f"API请求: {method} {endpoint} - 状态码: {status_code} - 耗时: {duration:.3f}s"

        # 过滤敏感信息
        safe_context = self.sensitive_filter.filter_dict(context)

        extra_data = {
            "method": method,
            "endpoint": endpoint,
            "duration": duration,
            "status_code": status_code,
            "context": safe_context
        }

        if user_id:
            extra_data["user_id"] = user_id
        if tenant_id:
            extra_data["tenant_id"] = tenant_id

        self.logger.log(level, message, extra=extra_data)

    def log_database_query(self, query_type: str, table: str, duration: float,
                          rows_affected: int = 0, success: bool = True, **context):
        """记录数据库查询性能"""
        level = logging.INFO if success else logging.WARNING
        message = f"数据库查询: {query_type} {table} - 耗时: {duration:.3f}s - 影响行数: {rows_affected}"

        # 过滤敏感信息
        safe_context = self.sensitive_filter.filter_dict(context)

        self.logger.log(
            level,
            message,
            extra={
                "query_type": query_type,
                "table": table,
                "duration": duration,
                "rows_affected": rows_affected,
                "success": success,
                "context": safe_context
            }
        )


class SecurityLogger:
    """安全日志记录器"""

    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
        self.sensitive_filter = SensitiveDataFilter()

    def log_authentication_event(self, event_type: str, user_id: Optional[str] = None,
                               tenant_id: Optional[str] = None, source_ip: Optional[str] = None,
                               success: bool = True, **context):
        """记录认证事件"""
        level = logging.INFO if success else logging.WARNING
        status = "成功" if success else "失败"
        message = f"用户认证: {event_type} - 状态: {status}"

        extra_data = {
            "event_type": "authentication",
            "auth_event": event_type,
            "success": success,
            "context": self.sensitive_filter.filter_dict(context)
        }

        if user_id:
            extra_data["user_id"] = user_id
        if tenant_id:
            extra_data["tenant_id"] = tenant_id
        if source_ip:
            extra_data["source_ip"] = source_ip

        self.logger.log(level, message, extra=extra_data)

    def log_authorization_event(self, resource: str, action: str, user_id: Optional[str] = None,
                               tenant_id: Optional[str] = None, success: bool = True, **context):
        """记录授权事件"""
        level = logging.INFO if success else logging.WARNING
        status = "成功" if success else "失败"
        message = f"权限检查: {action} {resource} - 状态: {status}"

        extra_data = {
            "event_type": "authorization",
            "resource": resource,
            "action": action,
            "success": success,
            "context": self.sensitive_filter.filter_dict(context)
        }

        if user_id:
            extra_data["user_id"] = user_id
        if tenant_id:
            extra_data["tenant_id"] = tenant_id

        self.logger.log(level, message, extra=extra_data)

    def log_security_event(self, event_type: str, level: str, description: str,
                          user_id: Optional[str] = None, tenant_id: Optional[str] = None,
                          source_ip: Optional[str] = None, **context):
        """记录安全事件"""
        log_level = getattr(logging, level.upper(), logging.INFO)
        message = f"安全事件: {event_type} - {description}"

        extra_data = {
            "event_type": "security",
            "security_event": event_type,
            "description": description,
            "context": self.sensitive_filter.filter_dict(context)
        }

        if user_id:
            extra_data["user_id"] = user_id
        if tenant_id:
            extra_data["tenant_id"] = tenant_id
        if source_ip:
            extra_data["source_ip"] = source_ip

        self.logger.log(log_level, message, extra=extra_data)


def setup_logging():
    """设置应用日志配置"""
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 控制台使用简单格式（开发环境）
    if settings.debug:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        console_formatter = StructuredFormatter(include_extra=False)

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（结构化JSON日志）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "application.log",
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(file_handler)

    # 错误日志文件处理器
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(error_handler)

    # 安全日志文件处理器
    security_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "security.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5,
        encoding="utf-8"
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(StructuredFormatter())

    # 设置安全日志器
    security_logger = logging.getLogger("security")
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False  # 防止传播到根日志器

    # 设置特定模块的日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # 第三方库日志级别控制
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    return root_logger


# 创建全局日志记录器实例
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)


def configure_contextual_logging(request_id: str, user_id: Optional[str] = None,
                               tenant_id: Optional[str] = None):
    """配置上下文日志"""
    # 创建日志适配器来添加上下文信息
    class ContextualAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            kwargs.setdefault("extra", {})
            kwargs["extra"].update({
                "request_id": request_id,
                "user_id": user_id,
                "tenant_id": tenant_id
            })
            return msg, kwargs

    # 返回上下文适配器
    return ContextualAdapter(logging.getLogger(), {})