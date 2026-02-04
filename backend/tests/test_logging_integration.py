"""
# 全量埋点验证测试

验证日志装饰器和前端日志接收端点的功能
"""

import pytest
import logging
import json
import time
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.core.logging_decorators import (
    log_execution,
    log_async_execution,
    log_api_request,
    get_trace_context,
    set_trace_context,
    clear_trace_context,
)


class TestLoggingDecorators:
    """测试日志装饰器功能"""

    def setup_method(self):
        """每个测试前清空链路上下文"""
        clear_trace_context()

    def test_log_execution_sync(self, caplog):
        """测试同步函数日志装饰器"""

        @log_execution(log_args=True, log_result=True)
        def test_function(x: int, y: int) -> int:
            return x + y

        with caplog.at_level(logging.INFO):
            result = test_function(1, 2)

        assert result == 3
        # 检查是否有入口和出口日志
        assert any("ENTER" in record.message for record in caplog.records)
        assert any("EXIT" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_log_async_execution(self, caplog):
        """测试异步函数日志装饰器"""

        @log_async_execution(log_args=True, log_result=True)
        async def async_test_function(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        import asyncio

        with caplog.at_level(logging.INFO):
            result = await async_test_function(5)

        assert result == 10
        assert any("ENTER" in record.message for record in caplog.records)
        assert any("EXIT" in record.message for record in caplog.records)

    def test_log_execution_with_exception(self, caplog):
        """测试异常日志记录"""

        @log_execution()
        def failing_function():
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                failing_function()

        assert any("ERROR" in record.message for record in caplog.records)

    def test_trace_context(self):
        """测试调用链路追踪"""
        set_trace_context(user_id="test_user", tenant_id="test_tenant")
        context = get_trace_context()

        assert context["user_id"] == "test_user"
        assert context["tenant_id"] == "test_tenant"

        clear_trace_context()
        context = get_trace_context()
        assert context == {}


class TestFrontendLogEndpoint:
    """测试前端日志接收端点"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/v1/logs/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "frontend_logs_receiver"

    def test_single_log(self, client, caplog):
        """测试单条日志接收"""
        log_entry = {
            "level": "info",
            "module": "TestModule",
            "message": "Test log message",
            "timestamp": "2026-02-01T00:00:00Z",
            "context": {"key": "value"},
        }

        with caplog.at_level(logging.INFO):
            response = client.post("/api/v1/logs/single", json=log_entry)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # 检查日志是否被记录
        assert any("TestModule" in record.message for record in caplog.records)

    def test_batch_logs(self, client, caplog):
        """测试批量日志接收"""
        logs = [
            {
                "level": "info",
                "module": "Module1",
                "message": "Message 1",
                "timestamp": "2026-02-01T00:00:00Z",
            },
            {
                "level": "warn",
                "module": "Module2",
                "message": "Message 2",
                "timestamp": "2026-02-01T00:00:01Z",
            },
        ]

        with caplog.at_level(logging.INFO):
            response = client.post(
                "/api/v1/logs/batch", json={"logs": logs, "user_id": "test_user"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed_count"] == 2

    def test_error_log_with_stack(self, client, caplog):
        """测试带堆栈的错误日志"""
        log_entry = {
            "level": "error",
            "module": "ErrorModule",
            "message": "Test error",
            "timestamp": "2026-02-01T00:00:00Z",
            "stack_trace": "Traceback (most recent call last):\n  ...",
        }

        with caplog.at_level(logging.ERROR):
            response = client.post("/api/v1/logs/single", json=log_entry)

        assert response.status_code == 200

        # 检查是否有堆栈日志
        assert any("Stack trace" in record.message for record in caplog.records)


class TestPerformanceMonitoring:
    """测试性能监控功能"""

    def test_function_performance(self, caplog):
        """测试函数性能记录"""

        @log_execution()
        def slow_function():
            time.sleep(0.05)
            return "done"

        with caplog.at_level(logging.INFO):
            result = slow_function()

        assert result == "done"
        # 检查性能日志（包含执行时间）
        assert any("ms" in record.message for record in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
