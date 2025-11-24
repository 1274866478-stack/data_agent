"""
结构化日志配置模块
提供统一的日志记录格式和监控功能
"""

import logging
import logging.config
import json
import time
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
import traceback

from src.app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式化器
    输出JSON格式的日志，便于日志聚合和分析
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为JSON
        """
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
        }

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 添加自定义字段
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        return json.dumps(log_entry, ensure_ascii=False)


class RequestLogger:
    """
    请求日志记录器
    记录API请求的详细信息
    """

    def __init__(self):
        self.logger = logging.getLogger("request")

    def log_request(
        self,
        method: str,
        path: str,
        client_ip: str,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        记录API请求开始
        """
        self.logger.info(
            f"Request started: {method} {path}",
            extra={
                "event_type": "request_start",
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_id": request_id,
            },
        )

    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        request_id: Optional[str] = None,
    ):
        """
        记录API请求完成
        """
        level = logging.INFO if status_code < 400 else logging.WARNING
        self.logger.log(
            level,
            f"Request completed: {method} {path} - {status_code} in {duration:.3f}s",
            extra={
                "event_type": "request_end",
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": int(duration * 1000),
                "request_id": request_id,
            },
        )


@contextmanager
def performance_logger(operation_name: str, logger: Optional[logging.Logger] = None):
    """
    性能监控上下文管理器
    记录操作执行时间
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info(
        f"Starting operation: {operation_name}",
        extra={"event_type": "operation_start", "operation": operation_name},
    )

    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Operation failed: {operation_name} after {duration:.3f}s - {str(e)}",
            extra={
                "event_type": "operation_error",
                "operation": operation_name,
                "duration_ms": int(duration * 1000),
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise
    else:
        duration = time.time() - start_time
        logger.info(
            f"Operation completed: {operation_name} in {duration:.3f}s",
            extra={
                "event_type": "operation_end",
                "operation": operation_name,
                "duration_ms": int(duration * 1000),
            },
        )


def setup_logging():
    """
    设置应用程序日志配置
    """
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {"()": StructuredFormatter},
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "structured" if settings.debug else "simple",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "structured",
                "filename": "logs/app.log",
                "mode": "a",
            },
        },
        "loggers": {
            "": {"level": "INFO", "handlers": ["console"]},
            "app": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "request": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "database": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }

    # 确保日志目录存在
    import os

    os.makedirs("logs", exist_ok=True)

    logging.config.dictConfig(log_config)

    # 记录应用启动日志
    logger = logging.getLogger("app")
    logger.info(
        f"Application logging initialized: {settings.app_name} v{settings.app_version}",
        extra={"event_type": "app_start", "debug_mode": settings.debug},
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    """
    return logging.getLogger(name)


# 全局请求日志记录器实例
request_logger = RequestLogger()
