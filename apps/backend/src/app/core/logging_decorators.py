"""
# 日志装饰器模块

## [HEADER]
**文件名**: logging_decorators.py
**职责**: 提供函数级追踪装饰器，支持同步/异步函数的性能监控和调用链路追踪
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-02-01): 初始版本 - 实现函数级日志装饰器

## [INPUT]
- func: Callable - 被装饰的函数
- log_level: str - 日志级别（默认 INFO）
- log_args: bool - 是否记录参数（默认 True）
- log_result: bool - 是否记录返回值（默认 False）
- log_exception: bool - 是否记录异常详情（默认 True）
- extra_context: Dict[str, Any] - 额外的上下文信息

## [OUTPUT]
- 装饰后的函数，带有完整的日志记录
- 结构化日志包含：执行时间、参数、返回值、异常信息

## [LINK]
**上游依赖**:
- [logging_config.py](logging_config.py) - PerformanceLogger, StructuredFormatter

**下游依赖**:
- 所有使用装饰器的服务模块

## [POS]
**路径**: backend/src/app/core/logging_decorators.py
**模块层级**: Level 2 - 核心工具模块
"""

import functools
import time
import inspect
from typing import Callable, Dict, Any, Optional, TypeVar
from contextvars import ContextVar
import logging
import traceback

from src.app.core.logging_config import PerformanceLogger

# 类型变量
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# 调用链路追踪上下文变量
_trace_context: ContextVar[Dict[str, Any]] = ContextVar("trace_context", default={})


def get_trace_context() -> Dict[str, Any]:
    """获取当前调用链路上下文"""
    return _trace_context.get().copy()


def set_trace_context(**kwargs) -> None:
    """设置调用链路上下文"""
    current = _trace_context.get().copy()
    current.update(kwargs)
    _trace_context.set(current)


def clear_trace_context() -> None:
    """清除调用链路上下文"""
    _trace_context.set({})


def add_trace_context(**kwargs) -> None:
    """添加调用链路上下文"""
    current = _trace_context.get().copy()
    current.update(kwargs)
    _trace_context.set(current)


class FunctionLogger:
    """函数日志记录器"""

    def __init__(self):
        self.performance_logger = PerformanceLogger()
        self.logger = logging.getLogger("function_trace")

    def _format_args(self, args: tuple, kwargs: dict, max_length: int = 200) -> str:
        """格式化函数参数"""
        try:
            args_str = ", ".join(repr(arg) for arg in args)
            kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())

            result = ", ".join(filter(None, [args_str, kwargs_str]))
            if len(result) > max_length:
                result = result[:max_length] + "..."
            return result
        except Exception:
            return "<args formatting error>"

    def _format_result(self, result: Any, max_length: int = 200) -> str:
        """格式化返回值"""
        try:
            result_str = repr(result)
            if len(result_str) > max_length:
                result_str = result_str[:max_length] + "..."
            return result_str
        except Exception:
            return "<result formatting error>"

    def log_entry(self, func_name: str, args: tuple, kwargs: dict, context: Dict[str, Any]):
        """记录函数入口"""
        trace_context = get_trace_context()
        args_str = self._format_args(args, kwargs)

        self.logger.info(
            f"↪️ ENTER {func_name}({args_str})",
            extra={
                "event_type": "function_entry",
                "function": func_name,
                "args": args_str,
                "trace_context": trace_context,
                **context
            }
        )

    def log_exit(self, func_name: str, result: Any, duration: float, context: Dict[str, Any]):
        """记录函数出口"""
        trace_context = get_trace_context()
        result_str = self._format_result(result)

        self.logger.info(
            f"↪️ EXIT {func_name} = {result_str} ({duration*1000:.2f}ms)",
            extra={
                "event_type": "function_exit",
                "function": func_name,
                "result": result_str,
                "duration_ms": duration * 1000,
                "trace_context": trace_context,
                **context
            }
        )

    def log_exception(self, func_name: str, exc: Exception, duration: float, context: Dict[str, Any]):
        """记录函数异常"""
        trace_context = get_trace_context()

        self.logger.error(
            f"↪️ ERROR {func_name} - {type(exc).__name__}: {str(exc)} ({duration*1000:.2f}ms)",
            extra={
                "event_type": "function_error",
                "function": func_name,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
                "duration_ms": duration * 1000,
                "trace_context": trace_context,
                **context
            }
        )


# 全局函数日志记录器实例
_function_logger = FunctionLogger()


def log_execution(
    log_level: str = "INFO",
    log_args: bool = True,
    log_result: bool = False,
    log_exception: bool = True,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    同步函数日志装饰器

    Args:
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR）
        log_args: 是否记录函数参数
        log_result: 是否记录返回值
        log_exception: 是否记录异常详情
        extra_context: 额外的上下文信息

    Usage:
        @log_execution()
        def my_function(arg1, arg2):
            return arg1 + arg2

        @log_execution(log_result=True, extra_context={"module": "UserModule"})
        def sensitive_function(user_id: str):
            return get_user(user_id)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            context = (extra_context or {}).copy()

            # 添加请求ID、用户ID、租户ID等上下文
            trace_context = get_trace_context()
            context.update(trace_context)

            start_time = time.time()

            # 记录函数入口
            if log_args:
                _function_logger.log_entry(func_name, args, kwargs, context)

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # 记录性能
                _function_logger.performance_logger.log_function_performance(
                    func_name, duration, success=True
                )

                # 记录函数出口
                if log_result:
                    _function_logger.log_exit(func_name, result, duration, context)

                return result

            except Exception as e:
                duration = time.time() - start_time

                # 记录性能
                _function_logger.performance_logger.log_function_performance(
                    func_name, duration, success=False
                )

                # 记录异常
                if log_exception:
                    _function_logger.log_exception(func_name, e, duration, context)

                raise

        return wrapper  # type: ignore
    return decorator


def log_async_execution(
    log_level: str = "INFO",
    log_args: bool = True,
    log_result: bool = False,
    log_exception: bool = True,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    异步函数日志装饰器

    Args:
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR）
        log_args: 是否记录函数参数
        log_result: 是否记录返回值
        log_exception: 是否记录异常详情
        extra_context: 额外的上下文信息

    Usage:
        @log_async_execution()
        async def my_async_function(arg1, arg2):
            return await async_operation(arg1, arg2)

        @log_async_execution(log_result=True)
        async def fetch_user(user_id: str):
            return await db.fetch_user(user_id)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            context = (extra_context or {}).copy()

            # 添加请求ID、用户ID、租户ID等上下文
            trace_context = get_trace_context()
            context.update(trace_context)

            start_time = time.time()

            # 记录函数入口
            if log_args:
                _function_logger.log_entry(func_name, args, kwargs, context)

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # 记录性能
                _function_logger.performance_logger.log_function_performance(
                    func_name, duration, success=True
                )

                # 记录函数出口
                if log_result:
                    _function_logger.log_exit(func_name, result, duration, context)

                return result

            except Exception as e:
                duration = time.time() - start_time

                # 记录性能
                _function_logger.performance_logger.log_function_performance(
                    func_name, duration, success=False
                )

                # 记录异常
                if log_exception:
                    _function_logger.log_exception(func_name, e, duration, context)

                raise

        return wrapper  # type: ignore
    return decorator


def log_method(
    log_level: str = "INFO",
    log_args: bool = False,  # 方法默认不记录参数（避免过多日志）
    log_result: bool = False,
    log_exception: bool = True,
) -> Callable[[F], F]:
    """
    类方法日志装饰器（轻量级版本）

    与 log_execution 的区别：
    - 默认不记录参数（适合类方法）
    - 日志格式更简洁

    Usage:
        class MyService:
            @log_method()
            def process_data(self, data_id: str):
                # ...
                pass
    """
    return log_execution(
        log_level=log_level,
        log_args=log_args,
        log_result=log_result,
        log_exception=log_exception,
    )


def log_async_method(
    log_level: str = "INFO",
    log_args: bool = False,
    log_result: bool = False,
    log_exception: bool = True,
) -> Callable[[F], F]:
    """
    异步类方法日志装饰器（轻量级版本）

    Usage:
        class MyService:
            @log_async_method()
            async def fetch_data(self, data_id: str):
                # ...
                pass
    """
    return log_async_execution(
        log_level=log_level,
        log_args=log_args,
        log_result=log_result,
        log_exception=log_exception,
    )


def log_api_request(
    operation_name: Optional[str] = None,
) -> Callable[[F], F]:
    """
    API 请求日志装饰器

    专门用于 FastAPI 端点的日志记录

    Usage:
        @router.post("/query")
        @log_api_request("ExecuteQuery")
        async def execute_query(request: QueryRequest):
            # ...
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = operation_name or func.__name__
            start_time = time.time()

            # 获取 FastAPI 请求上下文
            request = None
            for arg in args:
                if hasattr(arg, "method") and hasattr(arg, "url"):
                    request = arg
                    break

            context = {}
            if request:
                context["method"] = request.method
                context["path"] = str(request.url.path)
                context["client_ip"] = request.client.host if request.client else None

                # 从状态中获取用户ID和租户ID
                if hasattr(request.state, "user_id"):
                    context["user_id"] = request.state.user_id
                if hasattr(request.state, "tenant_id"):
                    context["tenant_id"] = request.state.tenant_id

            add_trace_context(**context)

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                _function_logger.logger.info(
                    f"✓ API {func_name} completed in {duration*1000:.2f}ms",
                    extra={
                        "event_type": "api_success",
                        "operation": func_name,
                        "duration_ms": duration * 1000,
                        **context
                    }
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                _function_logger.logger.error(
                    f"✗ API {func_name} failed: {type(e).__name__} - {str(e)}",
                    extra={
                        "event_type": "api_error",
                        "operation": func_name,
                        "duration_ms": duration * 1000,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        **context
                    }
                )
                raise

        return wrapper  # type: ignore
    return decorator


# 便捷别名
log_fn = log_execution
log_async_fn = log_async_execution
log_call = log_execution
