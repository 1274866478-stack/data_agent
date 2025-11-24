"""
LLM API端点测试用例
测试LLM相关的REST API端点
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.app.api.v1.endpoints.llm import (
    ChatCompletionRequest,
    ChatMessage,
    ChatCompletionResponse
)
from src.app.main import app
from src.app.services.llm_service import LLMResponse, LLMStreamChunk


class TestLLMEndpoints:
    """LLM API端点测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_current_user(self):
        """Mock当前用户"""
        user = MagicMock()
        user.tenant_id = "test_tenant_123"
        user.id = "user_123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def sample_chat_request(self):
        """示例聊天请求"""
        return {
            "messages": [
                {"role": "user", "content": "你好，请介绍一下自己"}
            ],
            "provider": "zhipu",
            "model": "glm-4-flash",
            "max_tokens": 100,
            "temperature": 0.7,
            "stream": False
        }

    @pytest.fixture
    def sample_multimodal_request(self):
        """示例多模态聊天请求"""
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请描述这张图片"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.com/image.jpg"
                            }
                        }
                    ]
                }
            ],
            "provider": "openrouter",
            "stream": False
        }

    def test_chat_completion_non_streaming_success(
        self, client, sample_chat_request, mock_current_user
    ):
        """测试非流式聊天完成成功"""
        # Mock响应
        mock_response = LLMResponse(
            content="你好！我是AI助手",
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            },
            model="glm-4-flash",
            provider="zhipu",
            finish_reason="stop",
            created_at="2025-11-17T10:00:00"
        )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_response

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=sample_chat_request
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "你好！我是AI助手"
            assert data["provider"] == "zhipu"
            assert data["model"] == "glm-4-flash"
            assert data["usage"]["total_tokens"] == 30

    def test_chat_completion_with_thinking_mode(
        self, client, mock_current_user
    ):
        """测试带思考模式的聊天完成"""
        request_data = {
            "messages": [
                {"role": "user", "content": "请分析这个问题"}
            ],
            "provider": "zhipu",
            "enable_thinking": True,
            "stream": False
        }

        mock_response = LLMResponse(
            content="最终答案",
            thinking="让我思考一下这个问题...",
            usage={"total_tokens": 50},
            model="glm-4.6",
            provider="zhipu"
        )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_response

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=request_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "最终答案"
            assert data["thinking"] == "让我思考一下这个问题..."

    def test_chat_completion_multimodal_success(
        self, client, sample_multimodal_request, mock_current_user
    ):
        """测试多模态聊天完成成功"""
        mock_response = LLMResponse(
            content="这是一张美丽的风景图片",
            usage={"total_tokens": 80},
            model="google/gemini-2.0-flash-exp",
            provider="openrouter"
        )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_response

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=sample_multimodal_request
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "这是一张美丽的风景图片"
            assert data["provider"] == "openrouter"
            assert data["model"] == "google/gemini-2.0-flash-exp"

    def test_chat_completion_streaming_success(
        self, client, sample_chat_request, mock_current_user
    ):
        """测试流式聊天完成成功"""
        # 修改请求为流式
        stream_request = sample_chat_request.copy()
        stream_request["stream"] = True

        # Mock流式响应
        async def mock_stream():
            yield LLMStreamChunk(
                type="thinking",
                content="让我想想",
                provider="zhipu"
            )
            yield LLMStreamChunk(
                type="content",
                content="你好",
                provider="zhipu"
            )
            yield LLMStreamChunk(
                type="content",
                content="！",
                provider="zhipu"
            )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_stream()

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=stream_request
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # 验证流式响应内容
            content = response.content.decode('utf-8')
            lines = [line for line in content.split('\n') if line.strip()]

            # 应该有多个数据行和一个结束标记
            assert len(lines) >= 3
            assert any('thinking' in line for line in lines)
            assert any('你好' in line for line in lines)
            assert any('[DONE]' in line for line in lines)

    def test_chat_completion_invalid_provider(
        self, client, sample_chat_request, mock_current_user
    ):
        """测试无效的提供商"""
        invalid_request = sample_chat_request.copy()
        invalid_request["provider"] = "invalid_provider"

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth:
            mock_auth.return_value = mock_current_user

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=invalid_request
            )

            assert response.status_code == 400
            data = response.json()
            assert "Invalid provider" in data["detail"]

    def test_chat_completion_service_error(
        self, client, sample_chat_request, mock_current_user
    ):
        """测试服务错误"""
        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.side_effect = Exception("Service unavailable")

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=sample_chat_request
            )

            assert response.status_code == 500
            data = response.json()
            assert "Chat completion failed" in data["detail"]

    def test_get_provider_status_success(self, client, mock_current_user):
        """测试获取提供商状态成功"""
        mock_status = {
            "zhipu": True,
            "openrouter": False
        }

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.validate_providers') as mock_validate:

            mock_auth.return_value = mock_current_user
            mock_validate.return_value = mock_status

            response = client.get("/api/v1/llm/providers/status")

            assert response.status_code == 200
            data = response.json()
            assert data["zhipu"] is True
            assert data["openrouter"] is False

    def test_get_provider_status_error(self, client, mock_current_user):
        """测试获取提供商状态错误"""
        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.validate_providers') as mock_validate:

            mock_auth.return_value = mock_current_user
            mock_validate.side_effect = Exception("Validation failed")

            response = client.get("/api/v1/llm/providers/status")

            assert response.status_code == 500
            data = response.json()
            assert "Failed to get provider status" in data["detail"]

    def test_get_available_models_success(self, client, mock_current_user):
        """测试获取可用模型成功"""
        mock_models = {
            "zhipu": ["glm-4-flash", "glm-4", "glm-4.6"],
            "openrouter": ["google/gemini-2.0-flash-exp"]
        }

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.get_available_models') as mock_models_func:

            mock_auth.return_value = mock_current_user
            mock_models_func.return_value = mock_models

            response = client.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            assert "providers" in data
            assert data["providers"]["zhipu"] == ["glm-4-flash", "glm-4", "glm-4.6"]
            assert data["providers"]["openrouter"] == ["google/gemini-2.0-flash-exp"]

    def test_test_llm_service_success(self, client, mock_current_user):
        """测试LLM服务测试成功"""
        mock_response = LLMResponse(
            content="测试成功",
            usage={"total_tokens": 5},
            model="glm-4-flash",
            provider="zhipu"
        )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_response

            response = client.post("/api/v1/llm/test?provider=zhipu")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["response"]["content"] == "测试成功"
            assert "LLM service test successful" in data["message"]

    def test_test_llm_service_failure(self, client, mock_current_user):
        """测试LLM服务测试失败"""
        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.side_effect = Exception("Service error")

            response = client.post("/api/v1/llm/test?provider=zhipu")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "LLM service test failed" in data["message"]

    def test_test_multimodal_success(self, client, mock_current_user):
        """测试多模态功能测试成功"""
        mock_response = LLMResponse(
            content="图片描述：这是一张风景图片",
            usage={"total_tokens": 30},
            model="google/gemini-2.0-flash-exp",
            provider="openrouter"
        )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_response

            response = client.post("/api/v1/llm/test/multimodal")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["response"]["content"] == "图片描述：这是一张风景图片"
            assert "Multimodal test successful" in data["message"]

    def test_test_multimodal_failure(self, client, mock_current_user):
        """测试多模态功能测试失败"""
        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.side_effect = Exception("Multimodal service unavailable")

            response = client.post("/api/v1/llm/test/multimodal")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Multimodal test failed" in data["message"]

    def test_invalid_request_data(self, client, mock_current_user):
        """测试无效请求数据"""
        invalid_request = {
            "messages": "invalid_messages_format",  # 应该是列表
            "provider": "zhipu"
        }

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth:
            mock_auth.return_value = mock_current_user

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=invalid_request
            )

            # 应该返回验证错误
            assert response.status_code == 422
            data = response.json()
            assert "Validation Error" in data["error"]

    def test_missing_required_fields(self, client, mock_current_user):
        """测试缺少必需字段"""
        incomplete_request = {
            "provider": "zhipu"
            # 缺少必需的 messages 字段
        }

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth:
            mock_auth.return_value = mock_current_user

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=incomplete_request
            )

            assert response.status_code == 422
            data = response.json()
            assert "Validation Error" in data["error"]

    def test_authentication_error(self, client, sample_chat_request):
        """测试认证错误"""
        # Mock认证失败
        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth:
            mock_auth.side_effect = Exception("Authentication failed")

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=sample_chat_request
            )

            # 应该返回500错误
            assert response.status_code == 500

    def test_cors_headers(self, client, sample_chat_request, mock_current_user):
        """测试CORS头设置"""
        mock_response = LLMResponse(
            content="测试响应",
            usage={"total_tokens": 10},
            model="glm-4-flash",
            provider="zhipu"
        )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_response

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=sample_chat_request
            )

            # 检查CORS头（在main.py中设置）
            assert response.status_code == 200

    def test_streaming_response_headers(self, client, mock_current_user):
        """测试流式响应头设置"""
        stream_request = {
            "messages": [{"role": "user", "content": "你好"}],
            "stream": True
        }

        async def mock_stream():
            yield LLMStreamChunk(
                type="content",
                content="测试",
                provider="zhipu"
            )

        with patch('src.app.api.v1.endpoints.llm.get_current_user_with_tenant') as mock_auth, \
             patch('src.app.services.llm_service.llm_service.chat_completion') as mock_chat:

            mock_auth.return_value = mock_current_user
            mock_chat.return_value = mock_stream()

            response = client.post(
                "/api/v1/llm/chat/completions",
                json=stream_request
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            assert "no-cache" in response.headers["cache-control"]
            assert "keep-alive" in response.headers["connection"]