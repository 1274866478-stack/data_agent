"""
# [LOGGING] 结构化日志配置

## [HEADER]
**文件名**: logging.py
**职责**: 提供统一的日志记录格式和监控功能，支持JSON结构化日志输出
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现结构化日志格式化器和请求日志记录器

## [INPUT]
- **record: LogRecord** - Python日志记录对象
- **settings: Settings** - 配置对象（应用名称、版本等）
- **method: str** - HTTP请求方法（GET, POST等）
- **path: str** - API请求路径
- **client_ip: str** - 客户端IP地址
- **user_agent: str** - 用户代理字符串（可选）
- **request_id: str** - 请求唯一标识符（可选）

## [OUTPUT]
- **log_entry: str** - JSON格式的日志条目
- **formatted_log: str** - 格式化后的日志字符串
- **logger: logging.Logger** - 配置好的日志记录器实例

## [LINK]
**上游依赖** (已读取源码):
- [./config.py](./config.py) - Settings类，应用名称和版本配置

**下游依赖** (已读取源码):
- [../main.py](../main.py) - 应用入口，配置日志系统
- [../api/v1/endpoints/*.py](../api/v1/endpoints/) - API端点使用日志记录

**调用方**:
- [../middleware/logging_middleware.py](../middleware/logging_middleware.py) - 日志中间件
- 所有服务模块 - 业务日志记录

## [POS]
**路径**: backend/src/app/core/logging.py
**模块层级**: Level 2 - 核心模块
**依赖深度**: 直接依赖 config.py；被所有需要日志的模块依赖
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
