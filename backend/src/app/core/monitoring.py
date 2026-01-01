"""
# 性能监控和错误追踪模块

## [HEADER]
**文件名**: monitoring.py
**职责**: 集成Sentry进行应用性能监控、错误追踪和性能分析
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本

## [INPUT]
- error: Exception - 异常对象
- message: str - 消息内容
- context: Optional[Dict[str, Any]] - 上下文信息
- level: str - 日志级别
- operation_name: str - 操作名称
- tags: Optional[Dict[str, str]] - 自定义标签

## [OUTPUT]
- Sentry事件ID: Optional[str]
- 性能监控上下文: context manager

## [LINK]
**上游依赖**:
- [config.py](config.py) - settings配置对象（SENTRY_DSN等）

**下游依赖**:
- 无（监控系统为独立模块）

**调用方**:
- 应用主入口（main.py）
- API端点错误处理
- 性能关键路径

## [POS]
**路径**: backend/src/app/core/monitoring.py
**模块层级**: Level 1（基础设施层）
**依赖深度**: 1 层（依赖config层）
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
import time

from src.app.core.config import settings

logger = logging.getLogger(__name__)

# Sentry集成 (可选依赖)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logger.warning("Sentry SDK未安装,性能监控功能将被禁用")


def init_sentry() -> None:
    """
    初始化Sentry监控
    
    环境变量:
        SENTRY_DSN: Sentry项目DSN
        SENTRY_ENVIRONMENT: 环境名称 (development/staging/production)
        SENTRY_TRACES_SAMPLE_RATE: 性能追踪采样率 (0.0-1.0)
    """
    if not SENTRY_AVAILABLE:
        logger.info("Sentry未安装,跳过初始化")
        return
    
    sentry_dsn = getattr(settings, 'sentry_dsn', None)
    
    if not sentry_dsn:
        logger.info("未配置SENTRY_DSN,跳过Sentry初始化")
        return
    
    try:
        # 获取配置
        environment = getattr(settings, 'sentry_environment', settings.environment)
        traces_sample_rate = getattr(settings, 'sentry_traces_sample_rate', 0.1)
        
        # 初始化Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            release=f"{settings.app_name}@{settings.app_version}",
            traces_sample_rate=traces_sample_rate,
            
            # 集成
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
            ],
            
            # 性能监控
            enable_tracing=True,
            
            # 过滤敏感数据
            before_send=before_send_filter,
            
            # 附加上下文
            attach_stacktrace=True,
            send_default_pii=False,  # 不发送个人身份信息
        )
        
        logger.info(
            f"Sentry初始化成功: environment={environment}, "
            f"traces_sample_rate={traces_sample_rate}"
        )
        
    except Exception as e:
        logger.error(f"Sentry初始化失败: {e}", exc_info=True)


def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    发送前过滤敏感数据
    
    Args:
        event: Sentry事件数据
        hint: 额外提示信息
        
    Returns:
        过滤后的事件,或None表示丢弃
    """
    # 过滤健康检查端点的错误
    if event.get('transaction') == '/health':
        return None
    
    # 过滤敏感字段
    if 'request' in event:
        request = event['request']
        
        # 过滤headers中的敏感信息
        if 'headers' in request:
            sensitive_headers = ['authorization', 'cookie', 'x-api-key']
            for header in sensitive_headers:
                if header in request['headers']:
                    request['headers'][header] = '[Filtered]'
        
        # 过滤query参数中的敏感信息
        if 'query_string' in request:
            sensitive_params = ['password', 'token', 'api_key', 'secret']
            for param in sensitive_params:
                if param in request.get('query_string', ''):
                    request['query_string'] = '[Filtered]'
    
    return event


def capture_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
) -> Optional[str]:
    """
    捕获异常并发送到Sentry
    
    Args:
        error: 异常对象
        context: 额外上下文信息
        level: 错误级别 (error/warning/info)
        
    Returns:
        Sentry事件ID,如果未启用则返回None
    """
    if not SENTRY_AVAILABLE:
        return None
    
    try:
        # 设置上下文
        if context:
            with sentry_sdk.configure_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
        
        # 捕获异常
        event_id = sentry_sdk.capture_exception(error, level=level)
        
        logger.debug(f"异常已发送到Sentry: event_id={event_id}")
        return event_id
        
    except Exception as e:
        logger.error(f"发送异常到Sentry失败: {e}")
        return None


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    捕获消息并发送到Sentry
    
    Args:
        message: 消息内容
        level: 消息级别 (info/warning/error)
        context: 额外上下文信息
        
    Returns:
        Sentry事件ID,如果未启用则返回None
    """
    if not SENTRY_AVAILABLE:
        return None
    
    try:
        # 设置上下文
        if context:
            with sentry_sdk.configure_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
        
        # 捕获消息
        event_id = sentry_sdk.capture_message(message, level=level)
        
        logger.debug(f"消息已发送到Sentry: event_id={event_id}")
        return event_id
        
    except Exception as e:
        logger.error(f"发送消息到Sentry失败: {e}")
        return None


@contextmanager
def monitor_performance(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """
    性能监控上下文管理器
    
    Args:
        operation_name: 操作名称
        tags: 自定义标签
        
    Example:
        with monitor_performance("database_query", {"table": "users"}):
            result = await db.execute(query)
    """
    if not SENTRY_AVAILABLE:
        # 降级为简单的时间记录
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            logger.info(f"操作完成: {operation_name}, 耗时: {duration:.3f}s")
        return
    
    # 使用Sentry性能监控
    with sentry_sdk.start_transaction(op=operation_name, name=operation_name) as transaction:
        if tags:
            for key, value in tags.items():
                transaction.set_tag(key, value)
        
        try:
            yield transaction
        except Exception as e:
            transaction.set_status("internal_error")
            raise

