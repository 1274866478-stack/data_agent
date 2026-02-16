"""
# [SECURITY_MONITOR] 安全监控和审计

## [HEADER]
**文件名**: security_monitor.py
**职责**: 提供敏感信息过滤、安全事件记录和威胁检测功能，保护系统安全
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现安全监控和审计功能

## [INPUT]
- **log_data: str** - 原始日志数据
- **event_type: SecurityEventType** - 安全事件类型枚举
- **level: SecurityEventLevel** - 安全事件级别枚举
- **source_ip: str** - 事件来源IP地址
- **user_id: str** - 用户ID（可选）
- **tenant_id: str** - 租户ID（可选）
- **details: dict** - 事件详情字典（可选）

## [OUTPUT]
- **filtered_log: str** - 过滤敏感信息后的日志
- **security_event: SecurityEvent** - 安全事件记录对象
- **threat_score: float** - 威胁评分（0-1）
- **alert: dict** - 安全告警信息
- **audit_log: dict** - 审计日志记录

## [LINK]
**上游依赖** (已读取源码):
- 无外部依赖（仅使用Python标准库）

**下游依赖** (已读取源码):
- [../middleware/security_middleware.py](../middleware/security_middleware.py) - 安全中间件
- [../main.py](../main.py) - 应用入口，注册安全监控

**调用方**:
- [../api/v1/endpoints/](../api/v1/endpoints/) - API端点使用安全监控
- [logging handler](../) - 日志处理器使用敏感信息过滤

## [POS]
**路径**: backend/src/app/core/security_monitor.py
**模块层级**: Level 2 - 核心模块
**依赖深度**: 无直接依赖；被所有需要安全监控的模块依赖
"""

import json
import logging
import time
import re
import hashlib
import ipaddress
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class SecurityEventLevel(Enum):
    """安全事件级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """安全事件类型"""
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_ERROR = "auth_error"
    RATE_LIMIT_EXCEEDED = "rate_limit"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_EXPOSURE = "data_exposure"
    INJECTION_ATTEMPT = "injection_attempt"
    BRUTE_FORCE = "brute_force"
    ANOMALOUS_ACCESS = "anomalous_access"


@dataclass
class SecurityEvent:
    """安全事件记录"""
    timestamp: datetime
    event_type: SecurityEventType
    level: SecurityEventLevel
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    description: str = ""
    resolved: bool = False


class SensitiveDataFilter:
    """敏感信息过滤器"""

    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        # API密钥
        (r'(api[_-]?key[_-]?[=:\s]+)[\'"]?([a-zA-Z0-9_-]{20,})[\'"]?', r'\1***REDACTED***'),
        (r'(zhipuai[_-]?api[_-]?key[_-]?[=:\s]+)[\'"]?([a-zA-Z0-9_-]{20,})[\'"]?', r'\1***REDACTED***'),
        (r'(openrouter[_-]?api[_-]?key[_-]?[=:\s]+)[\'"]?([a-zA-Z0-9_-]{20,})[\'"]?', r'\1***REDACTED***'),

        # 数据库连接字符串
        (r'(postgresql://[^:]+:)([^@]+)(@)', r'\1***REDACTED***\3'),
        (r'(mysql://[^:]+:)([^@]+)(@)', r'\1***REDACTED***\3'),

        # JWT tokens
        (r'(Bearer\s+)([a-zA-Z0-9_-]+\.){2}[a-zA-Z0-9_-]+', r'\1***JWT_TOKEN_REDACTED***'),

        # 密码字段
        (r'(password[_-]?)[=:\s]+[\'"]?([^\'"\s]{6,})[\'"]?', r'\1***REDACTED***'),
        (r'(secret[_-]?)[=:\s]+[\'"]?([^\'"\s]{6,})[\'"]?', r'\1***REDACTED***'),
        (r'(token[_-]?)[=:\s]+[\'"]?([^\'"\s]{10,})[\'"]?', r'\1***REDACTED***'),

        # 邮箱地址（部分遮蔽）
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'\1***@\2'),

        # IP地址（可选，用于隐私保护）
        # (r'(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)', r'***.***.***.***'),
    ]

    @classmethod
    def filter_sensitive_data(cls, text: str) -> str:
        """
        过滤文本中的敏感信息

        Args:
            text: 原始文本

        Returns:
            过滤后的文本
        """
        if not isinstance(text, str):
            return text

        filtered_text = text

        try:
            for pattern, replacement in cls.SENSITIVE_PATTERNS:
                filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE)
        except Exception as e:
            logger.warning(f"敏感信息过滤失败: {e}")
            return text

        return filtered_text

    @classmethod
    def filter_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归过滤字典中的敏感信息

        Args:
            data: 原始字典

        Returns:
            过滤后的字典
        """
        if not isinstance(data, dict):
            return data

        filtered_data = {}
        sensitive_keys = {
            'api_key', 'apikey', 'key', 'secret', 'password', 'token',
            'authorization', 'auth', 'credential', 'private', 'confidential',
            'connection_string', 'database_url', 'jwt', 'bearer'
        }

        for key, value in data.items():
            key_lower = key.lower()

            if key_lower in sensitive_keys:
                filtered_data[key] = "***REDACTED***"
            elif isinstance(value, str):
                filtered_data[key] = cls.filter_sensitive_data(value)
            elif isinstance(value, dict):
                filtered_data[key] = cls.filter_dict(value)
            elif isinstance(value, list):
                filtered_data[key] = [
                    cls.filter_sensitive_data(item) if isinstance(item, str) else
                    cls.filter_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered_data[key] = value

        return filtered_data


class ThreatDetector:
    """威胁检测器"""

    def __init__(self):
        self.suspicious_patterns = [
            # SQL注入
            r'(union\s+select|drop\s+table|delete\s+from|insert\s+into)',
            r'(\bOR\b\s+[\'"]?[1-9]+[\'"]?\s*=\s*[\'"]?[1-9]+[\'"]?)',
            r'(--[#;\s]|\/\*|\*\/)',

            # XSS攻击
            r'(javascript:|<script|on\w+\s*=)',
            r'(<iframe|<object|<embed)',

            # 路径遍历
            r'(\.\.[\/\\]+|%2e%2e%2f)',
            r'(etc\/passwd|windows\/system32)',

            # 命令注入
            r'(;|\||&|`|\$\()\s*(rm|del|format|shutdown|reboot)',

            # LDAP注入
            r'(\*\)\(\!\))|(\*\)\()',
        ]

        self.rate_limit_threshold = 100  # 每分钟最大请求数
        self.request_history = defaultdict(lambda: deque(maxlen=1000))

    def detect_injection_attempt(self, input_text: str) -> bool:
        """
        检测注入攻击尝试

        Args:
            input_text: 输入文本

        Returns:
            bool: 是否检测到注入尝试
        """
        if not isinstance(input_text, str):
            return False

        text_lower = input_text.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"检测到可疑模式: {pattern} in {input_text[:100]}...")
                return True

        return False

    def check_rate_limit(self, client_ip: str, window_minutes: int = 1) -> bool:
        """
        检查速率限制

        Args:
            client_ip: 客户端IP
            window_minutes: 时间窗口（分钟）

        Returns:
            bool: 是否超过限制
        """
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)

        # 清理过期记录
        while (self.request_history[client_ip] and
               self.request_history[client_ip][0] < window_start):
            self.request_history[client_ip].popleft()

        # 添加当前请求
        self.request_history[client_ip].append(current_time)

        # 检查是否超过限制
        request_count = len(self.request_history[client_ip])
        if request_count > self.rate_limit_threshold:
            logger.warning(f"IP {client_ip} 超过速率限制: {request_count}/{self.rate_limit_threshold}")
            return True

        return False

    def detect_anomalous_access(self, user_id: str, action: str, context: Dict[str, Any]) -> bool:
        """
        检测异常访问模式

        Args:
            user_id: 用户ID
            action: 执行的操作
            context: 上下文信息

        Returns:
            bool: 是否检测到异常
        """
        # 这里可以实现更复杂的异常检测逻辑
        # 例如：异地登录、权限提升尝试、异常时间访问等

        suspicious_time = datetime.now().hour < 6 or datetime.now().hour > 22
        sensitive_actions = {'delete', 'drop', 'admin', 'config', 'key'}

        if suspicious_time and action.lower() in sensitive_actions:
            logger.warning(f"检测到异常访问模式: 用户 {user_id} 在异常时间执行敏感操作 {action}")
            return True

        return False


class SecurityMonitor:
    """安全监控器"""

    def __init__(self):
        self.events: List[SecurityEvent] = []
        self.max_events = 10000
        self.threat_detector = ThreatDetector()
        self.sensitive_filter = SensitiveDataFilter()

    def record_event(
        self,
        event_type: SecurityEventType,
        level: SecurityEventLevel,
        description: str,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        记录安全事件

        Args:
            event_type: 事件类型
            level: 事件级别
            description: 事件描述
            source_ip: 来源IP
            user_id: 用户ID
            tenant_id: 租户ID
            details: 事件详情
        """
        event = SecurityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            level=level,
            source_ip=source_ip,
            user_id=user_id,
            tenant_id=tenant_id,
            details=self.sensitive_filter.filter_dict(details or {}),
            description=description
        )

        self.events.append(event)

        # 限制事件数量
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        # 记录日志
        log_message = f"安全事件 [{level.value.upper()}] {event_type.value}: {description}"
        if user_id:
            log_message += f" | 用户: {user_id}"
        if tenant_id:
            log_message += f" | 租户: {tenant_id}"
        if source_ip:
            log_message += f" | IP: {source_ip}"

        if level == SecurityEventLevel.CRITICAL:
            logger.critical(log_message)
        elif level == SecurityEventLevel.HIGH:
            logger.error(log_message)
        elif level == SecurityEventLevel.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def check_request_security(
        self,
        request_data: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        source_ip: Optional[str] = None
    ) -> bool:
        """
        检查请求安全性

        Args:
            request_data: 请求数据
            user_id: 用户ID
            tenant_id: 租户ID
            source_ip: 来源IP

        Returns:
            bool: 请求是否安全
        """
        # 检查速率限制
        if source_ip and self.threat_detector.check_rate_limit(source_ip):
            self.record_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityEventLevel.HIGH,
                f"IP {source_ip} 超过速率限制",
                source_ip=source_ip,
                user_id=user_id,
                tenant_id=tenant_id
            )
            return False

        # 检查注入攻击
        request_str = json.dumps(request_data, ensure_ascii=False)
        if self.threat_detector.detect_injection_attempt(request_str):
            self.record_event(
                SecurityEventType.INJECTION_ATTEMPT,
                SecurityEventLevel.CRITICAL,
                "检测到注入攻击尝试",
                source_ip=source_ip,
                user_id=user_id,
                tenant_id=tenant_id,
                details={"request_sample": request_str[:200]}
            )
            return False

        # 检查异常访问
        if user_id and self.threat_detector.detect_anomalous_access(
            user_id,
            request_data.get("action", "unknown"),
            request_data
        ):
            self.record_event(
                SecurityEventType.ANOMALOUS_ACCESS,
                SecurityEventLevel.MEDIUM,
                "检测到异常访问模式",
                source_ip=source_ip,
                user_id=user_id,
                tenant_id=tenant_id
            )

        return True

    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取安全事件摘要

        Args:
            hours: 时间范围（小时）

        Returns:
            安全事件摘要
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_time]

        summary = {
            "total_events": len(recent_events),
            "time_range_hours": hours,
            "by_level": defaultdict(int),
            "by_type": defaultdict(int),
            "by_source_ip": defaultdict(int),
            "by_user": defaultdict(int),
            "by_tenant": defaultdict(int),
            "unresolved_critical": 0,
            "trend": []
        }

        for event in recent_events:
            summary["by_level"][event.level.value] += 1
            summary["by_type"][event.event_type.value] += 1

            if event.source_ip:
                summary["by_source_ip"][event.source_ip] += 1
            if event.user_id:
                summary["by_user"][event.user_id] += 1
            if event.tenant_id:
                summary["by_tenant"][event.tenant_id] += 1

            if not event.resolved and event.level == SecurityEventLevel.CRITICAL:
                summary["unresolved_critical"] += 1

        # 转换为普通字典
        return {
            k: dict(v) if isinstance(v, defaultdict) else v
            for k, v in summary.items()
        }

    def export_events(self, format: str = "json", hours: int = 24) -> str:
        """
        导出安全事件

        Args:
            format: 导出格式 (json, csv)
            hours: 时间范围（小时）

        Returns:
            导出的事件数据
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_time]

        if format.lower() == "json":
            events_data = [asdict(event) for event in recent_events]
            # 转换datetime为字符串
            for event_data in events_data:
                event_data["timestamp"] = event_data["timestamp"].isoformat()
                event_data["event_type"] = event_data["event_type"].value
                event_data["level"] = event_data["level"].value

            return json.dumps(events_data, ensure_ascii=False, indent=2)

        elif format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            if recent_events:
                fieldnames = ["timestamp", "event_type", "level", "description",
                            "source_ip", "user_id", "tenant_id", "resolved"]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                for event in recent_events:
                    row = {
                        "timestamp": event.timestamp.isoformat(),
                        "event_type": event.event_type.value,
                        "level": event.level.value,
                        "description": event.description,
                        "source_ip": event.source_ip or "",
                        "user_id": event.user_id or "",
                        "tenant_id": event.tenant_id or "",
                        "resolved": event.resolved
                    }
                    writer.writerow(row)

            return output.getvalue()

        else:
            raise ValueError(f"不支持的导出格式: {format}")


# 全局安全监控器实例
security_monitor = SecurityMonitor()


def secure_log(level: str, message: str, **kwargs):
    """
    安全日志记录函数

    Args:
        level: 日志级别
        message: 日志消息
        **kwargs: 额外的日志数据
    """
    # 过滤敏感信息
    safe_message = SensitiveDataFilter.filter_sensitive_data(message)
    safe_kwargs = SensitiveDataFilter.filter_dict(kwargs)

    # 记录日志
    if level.upper() == "CRITICAL":
        logger.critical(safe_message, extra=safe_kwargs)
    elif level.upper() == "ERROR":
        logger.error(safe_message, extra=safe_kwargs)
    elif level.upper() == "WARNING":
        logger.warning(safe_message, extra=safe_kwargs)
    elif level.upper() == "INFO":
        logger.info(safe_message, extra=safe_kwargs)
    else:
        logger.debug(safe_message, extra=safe_kwargs)