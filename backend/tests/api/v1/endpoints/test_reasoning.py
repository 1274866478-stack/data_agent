"""
推理API端点测试
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.app.api.v1.endpoints.reasoning import router, ReasoningRequest, ReasoningResponse
from src.app.services.reasoning_service import (
    reasoning_engine,
    QueryType,
    ReasoningMode,
    QueryAnalysis,
    ReasoningResult,
    ReasoningStep
)
from src.app.services.conversation_service import conversation_manager
from src.app.services.usage_monitoring_service import usage_monitoring_service
from src.app.data.models import Tenant


class MockTenant:
    """模拟租户对象"""
    def __init__(self, tenant_id="test_tenant"):
        self.id = tenant_id
        self.email = f"test@{tenant_id}.com"
        self.display_name = f"Test {tenant_id}"


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_current_user():
    """模拟当前用户"""
    return MockTenant()


@pytest.fixture
def sample_reasoning_request():
    """示例推理请求"""
    return ReasoningRequest(
        query="什么是机器学习？",
        context=[{"role": "user", "content": "我对AI很感兴趣"}],
        data_sources=[{"id": "doc1", "name": "AI文档", "type": "pdf"}],
        conversation_id="test_conv_123",
        reasoning_mode="basic",
        provider="zhipu",
        model="glm-4",
        stream=False
    )


@pytest.fixture
def sample_query_analysis():
    """示例查询分析结果"""
    return QueryAnalysis(
        original_query="什么是机器学习？",
        query_type=QueryType.FACTUAL,
        intent="寻求定义",
        entities=["机器学习"],
        keywords=["机器学习", "定义"],
        temporal_expressions=[],
        complexity_score=0.4,
        confidence=0.9,
        reasoning_mode=ReasoningMode.BASIC,
        suggested_temperature=0.3,
        suggested_max_tokens=1000
    )


@pytest.fixture
def sample_reasoning_result(sample_query_analysis):
    """示例推理结果"""
    return ReasoningResult(
        answer="机器学习是人工智能的一个重要分支，它使计算机能够从数据中学习并改进性能。",
        reasoning_steps=[
            ReasoningStep(1, "理解查询", "识别用户想了解机器学习的定义", [], 0.9),
            ReasoningStep(2, "提供定义", "给出机器学习的标准定义", [], 0.8)
        ],
        confidence=0.85,
        sources=[{"id": "doc1", "name": "AI文档", "relevance": 0.9}],
        query_analysis=sample_query_analysis,
        quality_score=0.8,
        safety_filter_triggered=False
    )


class TestAnalyzeQueryEndpoint:
    """查询分析端点测试"""

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.reasoning_engine')
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_analyze_query_success(
        self,
        mock_auth,
        mock_usage_service,
        mock_reasoning_engine,
        client,
        mock_current_user,
        sample_query_analysis
    ):
        """测试成功的查询分析"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.record_usage = AsyncMock(return_value=True)
        mock_reasoning_engine.query_understanding.analyze_query = AsyncMock(return_value=sample_query_analysis)

        # 发送请求
        request_data = {"query": "什么是机器学习？"}
        response = client.post("/reasoning/analyze", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        result_data = data["data"]
        assert result_data["original_query"] == "什么是机器学习？"
        assert result_data["query_type"] == "factual"
        assert result_data["intent"] == "寻求定义"
        assert result_data["complexity_score"] == 0.4
        assert result_data["confidence"] == 0.9

        # 验证服务调用
        mock_usage_service.tracker.record_usage.assert_called_once()
        mock_reasoning_engine.query_understanding.analyze_query.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_analyze_query_error(self, mock_auth, client):
        """测试查询分析错误"""
        mock_auth.return_value = mock_current_user

        # 发送无效请求
        request_data = {"query": ""}  # 空查询
        response = client.post("/reasoning/analyze", json=request_data)

        # 验证响应
        assert response.status_code == 422  # 验证错误


class TestReasonQueryEndpoint:
    """推理查询端点测试"""

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.reasoning_engine')
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.conversation_manager')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_reason_query_success(
        self,
        mock_auth,
        mock_conv_manager,
        mock_usage_service,
        mock_reasoning_engine,
        client,
        mock_current_user,
        sample_reasoning_request,
        sample_reasoning_result
    ):
        """测试成功的推理查询"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.check_usage_limits = AsyncMock(return_value=(True, []))
        mock_usage_service.tracker.record_usage = AsyncMock(return_value=True)
        mock_usage_service.check_and_alert = AsyncMock(return_value=[])
        mock_reasoning_engine.reason = AsyncMock(return_value=sample_reasoning_result)
        mock_conv_manager.add_message = AsyncMock(return_value=True)

        # 发送请求
        request_data = {
            "query": "什么是机器学习？",
            "context": [{"role": "user", "content": "我对AI很感兴趣"}],
            "conversation_id": "test_conv_123"
        }
        response = client.post("/reasoning/reason", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == sample_reasoning_result.answer
        assert len(data["reasoning_steps"]) == 2
        assert data["confidence"] == 0.85
        assert data["quality_score"] == 0.8
        assert data["conversation_id"] == "test_conv_123"
        assert data["safety_filter_triggered"] is False
        assert "usage_info" in data
        assert "query_analysis" in data

        # 验证推理步骤格式
        steps = data["reasoning_steps"]
        assert steps[0]["step_number"] == 1
        assert steps[0]["description"] == "理解查询"
        assert steps[0]["reasoning"] is not None

        # 验证服务调用
        mock_usage_service.tracker.check_usage_limits.assert_called_once()
        mock_reasoning_engine.reason.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_reason_query_usage_limit_exceeded(
        self,
        mock_auth,
        mock_usage_service,
        client,
        mock_current_user
    ):
        """测试使用量限制超出"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.check_usage_limits = AsyncMock(return_value=(False, ["已达到使用量限制"]))

        # 发送请求
        request_data = {"query": "什么是机器学习？"}
        response = client.post("/reasoning/reason", json=request_data)

        # 验证响应
        assert response.status_code == 429
        assert "已达到使用量限制" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.reasoning_engine')
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_reason_query_without_conversation(
        self,
        mock_auth,
        mock_usage_service,
        mock_reasoning_engine,
        client,
        mock_current_user,
        sample_reasoning_result
    ):
        """测试不带对话ID的推理查询"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.check_usage_limits = AsyncMock(return_value=(True, []))
        mock_usage_service.tracker.record_usage = AsyncMock(return_value=True)
        mock_usage_service.check_and_alert = AsyncMock(return_value=[])
        mock_reasoning_engine.reason = AsyncMock(return_value=sample_reasoning_result)

        # 发送请求（不带对话ID）
        request_data = {"query": "什么是机器学习？"}
        response = client.post("/reasoning/reason", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] is None

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.reasoning_engine')
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_reason_query_safety_filter_triggered(
        self,
        mock_auth,
        mock_usage_service,
        mock_reasoning_engine,
        client,
        mock_current_user,
        sample_query_analysis
    ):
        """测试安全过滤触发"""
        # 创建触发安全过滤的结果
        unsafe_result = ReasoningResult(
            answer="请求被安全过滤器阻止",
            reasoning_steps=[],
            confidence=0.1,
            sources=[],
            query_analysis=sample_query_analysis,
            quality_score=0.1,
            safety_filter_triggered=True
        )

        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.check_usage_limits = AsyncMock(return_value=(True, []))
        mock_usage_service.tracker.record_usage = AsyncMock(return_value=True)
        mock_usage_service.check_and_alert = AsyncMock(return_value=[])
        mock_reasoning_engine.reason = AsyncMock(return_value=unsafe_result)

        # 发送请求
        request_data = {"query": "什么是机器学习？"}
        response = client.post("/reasoning/reason", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["safety_filter_triggered"] is True
        assert data["confidence"] == 0.1


class TestStreamReasoningEndpoint:
    """流式推理端点测试"""

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.reasoning_engine')
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_stream_reasoning_success(
        self,
        mock_auth,
        mock_usage_service,
        mock_reasoning_engine,
        client,
        mock_current_user,
        sample_reasoning_result
    ):
        """测试成功的流式推理"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.check_usage_limits = AsyncMock(return_value=(True, []))
        mock_reasoning_engine.reason = AsyncMock(return_value=sample_reasoning_result)

        # 发送请求
        request_data = {
            "query": "什么是机器学习？",
            "stream": True
        }

        response = client.post("/reasoning/stream", json=request_data)

        # 验证响应
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "cache-control" in response.headers

        # 验证流式响应内容
        content = response.content.decode('utf-8')
        assert "data:" in content
        assert '"type": "start"' in content
        assert '"type": "reasoning_step"' in content
        assert '"type": "content"' in content
        assert '"type": "complete"' in content

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_stream_reasoning_usage_limit_exceeded(
        self,
        mock_auth,
        mock_usage_service,
        client,
        mock_current_user
    ):
        """测试流式推理使用量限制"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.check_usage_limits = AsyncMock(return_value=(False, ["已达到使用量限制"]))

        # 发送请求
        request_data = {"query": "什么是机器学习？", "stream": True}
        response = client.post("/reasoning/stream", json=request_data)

        # 验证响应
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert '"type": "error"' in content
        assert "已达到使用量限制" in content


class TestConversationEndpoints:
    """对话端点测试"""

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.conversation_manager')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_create_conversation(
        self,
        mock_auth,
        mock_conv_manager,
        client,
        mock_current_user
    ):
        """测试创建对话"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_conv_manager.create_conversation = AsyncMock(return_value="conv_12345")

        # 发送请求
        request_data = {
            "tenant_id": "test_tenant",
            "user_id": "test_user",
            "conversation_id": "custom_conv_123",
            "metadata": {"source": "web"}
        }
        response = client.post("/reasoning/conversations", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["conversation_id"] == "conv_12345"

        # 验证服务调用
        mock_conv_manager.create_conversation.assert_called_once_with(
            tenant_id="test_tenant",
            user_id="test_user",
            conversation_id="custom_conv_123",
            metadata={"source": "web"}
        )

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.conversation_manager')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_add_conversation_message(
        self,
        mock_auth,
        mock_conv_manager,
        client,
        mock_current_user
    ):
        """测试添加对话消息"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_conv_manager.add_message = AsyncMock(return_value=True)

        # 发送请求
        request_data = {
            "role": "user",
            "content": "你好，我想了解AI",
            "token_count": 15,
            "metadata": {"source": "chat"}
        }
        response = client.post("/reasoning/conversations/test_conv_123/messages", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "消息添加成功"

        # 验证服务调用
        mock_conv_manager.add_message.assert_called_once_with(
            conversation_id="test_conv_123",
            role="user",
            content="你好，我想了解AI",
            token_count=15,
            metadata={"source": "chat"}
        )

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.conversation_manager')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_add_message_nonexistent_conversation(
        self,
        mock_auth,
        mock_conv_manager,
        client,
        mock_current_user
    ):
        """测试向不存在的对话添加消息"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_conv_manager.add_message = AsyncMock(return_value=False)

        # 发送请求
        request_data = {
            "role": "user",
            "content": "测试消息"
        }
        response = client.post("/reasoning/conversations/nonexistent/messages", json=request_data)

        # 验证响应
        assert response.status_code == 404
        assert "对话不存在" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.conversation_manager')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_get_conversation(
        self,
        mock_auth,
        mock_conv_manager,
        client,
        mock_current_user
    ):
        """测试获取对话信息"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_conv_context = {
            "conversation_id": "test_conv_123",
            "tenant_id": "test_tenant",
            "state": "active",
            "message_count": 5,
            "created_at": "2025-11-18T00:00:00Z"
        }
        mock_conv_manager.get_conversation_context = AsyncMock(return_value=mock_conv_context)

        # 发送请求
        response = client.get("/reasoning/conversations/test_conv_123")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["conversation_id"] == "test_conv_123"
        assert data["data"]["message_count"] == 5

        # 验证服务调用
        mock_conv_manager.get_conversation_context.assert_called_once_with("test_conv_123")

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.conversation_manager')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_get_conversation_history(
        self,
        mock_auth,
        mock_conv_manager,
        client,
        mock_current_user
    ):
        """测试获取对话历史"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_history = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "问题2"}
        ]
        mock_conv_manager.get_conversation_history = AsyncMock(return_value=mock_history)

        # 发送请求
        response = client.get("/reasoning/conversations/test_conv_123/history?limit=10&offset=0")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["messages"]) == 3
        assert data["data"]["total"] == 3

        # 验证服务调用
        mock_conv_manager.get_conversation_history.assert_called_once_with("test_conv_123", 10, 0)


class TestUsageEndpoints:
    """使用量端点测试"""

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_get_usage_statistics(
        self,
        mock_auth,
        mock_usage_service,
        client,
        mock_current_user
    ):
        """测试获取使用量统计"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_stats = {
            "tenant_id": "test_tenant",
            "period": "daily",
            "total_tokens": 1500,
            "total_api_calls": 15,
            "total_cost": 0.75,
            "timestamp": "2025-11-18T00:00:00Z"
        }
        mock_usage_service.tracker.get_usage_statistics = AsyncMock(return_value=mock_stats)

        # 发送请求
        response = client.get("/reasoning/usage/statistics?period=daily")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_tokens"] == 1500
        assert data["data"]["period"] == "daily"

        # 验证服务调用
        mock_usage_service.tracker.get_usage_statistics.assert_called_once_with(
            tenant_id=mock_current_user.id,
            period="daily"
        )

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_get_usage_limits(
        self,
        mock_auth,
        mock_usage_service,
        client,
        mock_current_user
    ):
        """测试获取使用量限制"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_current_usage = {
            "daily_tokens": 5000,
            "daily_api_calls": 50,
            "monthly_cost": 25.0
        }
        mock_usage_service.tracker.get_current_usage = AsyncMock(return_value=mock_current_usage)
        mock_usage_service.tracker._get_usage_limit = AsyncMock(return_value=None)

        # 发送请求
        response = client.get("/reasoning/usage/limits")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "current_usage" in data["data"]
        assert data["data"]["current_usage"]["daily_tokens"] == 5000


class TestHealthEndpoint:
    """健康检查端点测试"""

    async def test_reasoning_health_check(self, client):
        """测试推理服务健康检查"""
        # 发送请求
        response = client.get("/reasoning/health")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "reasoning_engine" in data["services"]
        assert "conversation_manager" in data["services"]
        assert "usage_monitoring" in data["services"]


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    @patch('src.app.api.v1.endpoints.reasoning.reasoning_engine')
    @patch('src.app.api.v1.endpoints.reasoning.conversation_manager')
    @patch('src.app.api.v1.endpoints.reasoning.usage_monitoring_service')
    @patch('src.app.api.v1.endpoints.reasoning.get_current_user_with_tenant')
    async def test_full_conversation_workflow(
        self,
        mock_auth,
        mock_usage_service,
        mock_conv_manager,
        mock_reasoning_engine,
        client,
        mock_current_user,
        sample_reasoning_result
    ):
        """测试完整对话工作流"""
        # 设置模拟
        mock_auth.return_value = mock_current_user
        mock_usage_service.tracker.check_usage_limits = AsyncMock(return_value=(True, []))
        mock_usage_service.tracker.record_usage = AsyncMock(return_value=True)
        mock_usage_service.check_and_alert = AsyncMock(return_value=[])
        mock_reasoning_engine.reason = AsyncMock(return_value=sample_reasoning_result)
        mock_conv_manager.create_conversation = AsyncMock(return_value="conv_123")
        mock_conv_manager.add_message = AsyncMock(return_value=True)

        # 1. 创建对话
        conv_request = {
            "tenant_id": "test_tenant",
            "user_id": "test_user"
        }
        conv_response = client.post("/reasoning/conversations", json=conv_request)
        assert conv_response.status_code == 200
        conv_id = conv_response.json()["conversation_id"]

        # 2. 进行推理（带对话ID）
        reason_request = {
            "query": "什么是机器学习？",
            "conversation_id": conv_id
        }
        reason_response = client.post("/reasoning/reason", json=reason_request)
        assert reason_response.status_code == 200
        reason_data = reason_response.json()
        assert reason_data["conversation_id"] == conv_id

        # 3. 获取对话历史
        history_response = client.get(f"/reasoning/conversations/{conv_id}/history")
        assert history_response.status_code == 200

        # 4. 获取使用量统计
        stats_response = client.get("/reasoning/usage/statistics")
        assert stats_response.status_code == 200

        # 验证服务调用
        assert mock_conv_manager.create_conversation.called
        assert mock_conv_manager.add_message.call_count >= 2  # 用户消息 + AI回复
        assert mock_reasoning_engine.reason.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])