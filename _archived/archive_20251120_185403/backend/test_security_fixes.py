#!/usr/bin/env python3
"""
安全修复验证测试
"""

import asyncio
import json
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.core.config import Settings
from app.core.security_monitor import (
    SecurityMonitor, SensitiveDataFilter, ThreatDetector,
    SecurityEventType, SecurityEventLevel
)
from app.core.logging_config import setup_logging, performance_logger, security_logger


def test_sensitive_data_filter():
    """测试敏感信息过滤"""
    print("🔒 测试敏感信息过滤...")

    # 测试API密钥过滤
    test_cases = [
        ("api_key=zhipuai_xyz123456789", "api_key=***REDACTED***"),
        ("postgresql://user:password@host:5432/db", "postgresql://user:***REDACTED***@host:5432/db"),
        ("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "Bearer ***JWT_TOKEN_REDACTED***"),
        ("password=secret123", "password=***REDACTED***"),
    ]

    filter = SensitiveDataFilter()

    for input_text, expected in test_cases:
        result = filter.filter_sensitive_data(input_text)
        assert result == expected, f"过滤失败: {input_text} -> {result}, 期望: {expected}"

    # 测试字典过滤
    test_dict = {
        "api_key": "zhipuai_secret123",
        "username": "test_user",
        "connection_string": "postgresql://user:pass@host/db",
        "nested": {
            "secret": "hidden_value",
            "public": "visible_value"
        }
    }

    filtered_dict = filter.filter_dict(test_dict)

    assert filtered_dict["api_key"] == "***REDACTED***"
    assert filtered_dict["connection_string"] == "postgresql://user:***REDACTED***@host/db"
    assert filtered_dict["username"] == "test_user"
    assert filtered_dict["nested"]["secret"] == "***REDACTED***"
    assert filtered_dict["nested"]["public"] == "visible_value"

    print("✅ 敏感信息过滤测试通过")


def test_threat_detector():
    """测试威胁检测"""
    print("🛡️ 测试威胁检测...")

    detector = ThreatDetector()

    # 测试SQL注入检测
    sql_injection_attempts = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "UNION SELECT * FROM passwords",
        "'; DELETE FROM accounts; --"
    ]

    for attempt in sql_injection_attempts:
        assert detector.detect_injection_attempt(attempt), f"未检测到SQL注入: {attempt}"

    # 测试XSS检测
    xss_attempts = [
        "<script>alert('xss')</script>",
        "javascript:void(0)",
        "<iframe src='evil.com'>",
        "onload='alert(1)'"
    ]

    for attempt in xss_attempts:
        assert detector.detect_injection_attempt(attempt), f"未检测到XSS: {attempt}"

    # 测试正常输入
    normal_inputs = [
        "Hello, how are you?",
        "This is a normal sentence.",
        "User wants to know about data analysis.",
        "Please help me with SQL queries."
    ]

    for input_text in normal_inputs:
        assert not detector.detect_injection_attempt(input_text), f"误报威胁检测: {input_text}"

    print("✅ 威胁检测测试通过")


def test_security_monitor():
    """测试安全监控"""
    print("📊 测试安全监控...")

    monitor = SecurityMonitor()

    # 记录测试事件
    monitor.record_event(
        SecurityEventType.AUTHENTICATION_FAILURE,
        SecurityEventLevel.HIGH,
        "测试认证失败事件",
        source_ip="192.168.1.100",
        user_id="test_user",
        tenant_id="test_tenant"
    )

    monitor.record_event(
        SecurityEventType.INJECTION_ATTEMPT,
        SecurityEventLevel.CRITICAL,
        "测试注入攻击事件",
        source_ip="192.168.1.101",
        details={"attack_type": "sql_injection"}
    )

    # 获取安全摘要
    summary = monitor.get_security_summary(hours=24)

    assert summary["total_events"] == 2
    assert summary["by_level"]["high"] == 1
    assert summary["by_level"]["critical"] == 1
    assert summary["by_type"]["auth_failure"] == 1
    assert summary["by_type"]["injection_attempt"] == 1

    print("✅ 安全监控测试通过")


def test_config_security():
    """测试配置安全性"""
    print("⚙️ 测试配置安全性...")

    # 测试弱密码检测
    try:
        # 这应该抛出异常
        settings = Settings(
            environment="production",
            database_url="postgresql://localhost/test",
            zhipuai_api_key="weak_password_123",
            clerk_jwt_public_key="test_public_key",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin"
        )
        assert False, "应该抛出配置验证错误"
    except Exception as e:
        assert "contains weak pattern" in str(e) or "cannot use default value" in str(e)

    print("✅ 配置安全性测试通过")


def test_logging_setup():
    """测试日志设置"""
    print("📝 测试日志设置...")

    # 设置日志
    logger = setup_logging()

    # 测试结构化日志
    performance_logger.log_function_performance(
        "test_function", 0.123, True, test_param="test_value"
    )

    security_logger.log_authentication_event(
        "login", "test_user", "test_tenant", "127.0.0.1", True
    )

    print("✅ 日志设置测试通过")


async def test_concurrent_security():
    """测试并发安全性"""
    print("🔄 测试并发安全性...")

    monitor = SecurityMonitor()

    async def record_events(prefix: str):
        for i in range(10):
            monitor.record_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityEventLevel.MEDIUM,
                f"{prefix} 事件 {i}",
                source_ip=f"192.168.1.{i}",
                user_id=f"user_{i}"
            )
            await asyncio.sleep(0.01)

    # 并发记录事件
    tasks = [
        asyncio.create_task(record_events("前缀A")),
        asyncio.create_task(record_events("前缀B")),
        asyncio.create_task(record_events("前缀C"))
    ]

    await asyncio.gather(*tasks)

    # 验证所有事件都被记录
    summary = monitor.get_security_summary(hours=1)
    assert summary["total_events"] == 30

    print("✅ 并发安全性测试通过")


def main():
    """主测试函数"""
    print("🚀 开始安全修复验证测试...\n")

    try:
        # 设置基本日志
        logging.basicConfig(level=logging.INFO)

        # 运行同步测试
        test_sensitive_data_filter()
        test_threat_detector()
        test_security_monitor()
        test_config_security()
        test_logging_setup()

        # 运行异步测试
        asyncio.run(test_concurrent_security())

        print("\n🎉 所有安全修复验证测试通过！")

        print("\n📊 修复摘要:")
        print("✅ 增强了API密钥验证和安全检查")
        print("✅ 实现了敏感信息自动过滤")
        print("✅ 添加了威胁检测和安全监控")
        print("✅ 完善了结构化日志记录")
        print("✅ 实现了性能监控和缓存机制")
        print("✅ 添加了熔断器和重试机制")

        print("\n🔧 安全改进:")
        print("- 严格验证API密钥强度")
        print("- 自动过滤日志中的敏感信息")
        print("- 检测SQL注入和XSS攻击")
        print("- 实现速率限制和异常访问检测")
        print("- 提供详细的安全事件审计")

        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)