"""
LLM服务测试用例
测试统一LLM服务的各项功能
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.app.services.llm_service import (
    LLMService,
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ZhipuProvider,
    OpenRouterProvider
)
from src.app.core.config import settings


class TestLLMService:
    """LLM服务测试类"""

    @pytest.fixture
    def llm_service_instance(self):
        """创建LLM服务实例"""
        return LLMService()

    @pytest.fixture
    def sample_messages(self):
        """创建示例消息"""
        return [
            LLMMessage(role="user", content="你好，请介绍一下自己"),
            LLMMessage(role="assistant", content="你好！我是一个AI助手"),
            LLMMessage(role="user", content="你能做什么？")
        ]

    @pytest.fixture
    def sample_multimodal_messages(self):
        """创建多模态示例消息"""
        return [
            LLMMessage(
                role="user",
                content=[
                    {"type": "text", "text": "请描述这张图片"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/image.jpg"}
                    }
                ]
            )
        ]

    @pytest.mark.asyncio
    async def test_register_zhipu_provider(self, llm_service_instance):
        """测试注册Zhipu提供商"""
        api_key = "test_zhipu_key"
        tenant_id = "test_tenant"

        with patch('src.app.services.llm_service.ZhipuAI'):
            provider = llm_service_instance.register_provider(
                tenant_id, LLMProvider.ZHIPU, api_key
            )

            assert isinstance(provider, ZhipuProvider)
            assert provider.api_key == api_key
            assert provider.tenant_id == tenant_id

            # 验证提供商已注册
            key = f"{tenant_id}_{LLMProvider.ZHIPU.value}"
            assert key in llm_service_instance.providers
            assert llm_service_instance.providers[key] == provider

    @pytest.mark.asyncio
    async def test_register_openrouter_provider(self, llm_service_instance):
        """测试注册OpenRouter提供商"""
        api_key = "test_openrouter_key"
        tenant_id = "test_tenant"

        with patch('src.app.services.llm_service.AsyncOpenAI'):
            provider = llm_service_instance.register_provider(
                tenant_id, LLMProvider.OPENROUTER, api_key
            )

            assert isinstance(provider, OpenRouterProvider)
            assert provider.api_key == api_key
            assert provider.tenant_id == tenant_id

            # 验证提供商已注册
            key = f"{tenant_id}_{LLMProvider.OPENROUTER.value}"
            assert key in llm_service_instance.providers
            assert llm_service_instance.providers[key] == provider

    @pytest.mark.asyncio
    async def test_get_provider(self, llm_service_instance):
        """测试获取提供商"""
        api_key = "test_key"
        tenant_id = "test_tenant"

        with patch('src.app.services.llm_service.ZhipuAI'):
            # 注册Zhipu提供商
            zhipu_provider = llm_service_instance.register_provider(
                tenant_id, LLMProvider.ZHIPU, api_key
            )

        # 测试获取指定提供商
        provider = llm_service_instance.get_provider(tenant_id, LLMProvider.ZHIPU)
        assert provider == zhipu_provider

        # 测试默认获取（返回第一个可用的提供商）
        provider = llm_service_instance.get_provider(tenant_id)
        assert provider == zhipu_provider

        # 测试获取不存在的提供商
        provider = llm_service_instance.get_provider(tenant_id, LLMProvider.OPENROUTER)
        assert provider is None

    @pytest.mark.asyncio
    async def test_chat_completion_zhipu(self, llm_service_instance, sample_messages):
        """测试Zhipu聊天完成"""
        tenant_id = "test_tenant"
        api_key = "test_zhipu_key"

        # Mock Zhipu AI响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "你好！我是智谱AI助手"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "glm-4-flash"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.created = 1234567890

        with patch('src.app.services.llm_service.ZhipuAI') as mock_zhipu:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_zhipu.return_value = mock_client

            # 注册提供商并调用聊天完成
            llm_service_instance.register_provider(tenant_id, LLMProvider.ZHIPU, api_key)
            response = await llm_service_instance.chat_completion(
                tenant_id=tenant_id,
                messages=sample_messages,
                provider=LLMProvider.ZHIPU
            )

            assert isinstance(response, LLMResponse)
            assert response.content == "你好！我是智谱AI助手"
            assert response.provider == LLMProvider.ZHIPU.value
            assert response.model == "glm-4-flash"
            assert response.usage["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_chat_completion_streaming(self, llm_service_instance, sample_messages):
        """测试流式聊天完成"""
        tenant_id = "test_tenant"
        api_key = "test_zhipu_key"

        # Mock流式响应
        mock_chunks = [
            MagicMock(
                choices=[MagicMock(delta=MagicMock(content="你好"))]
            ),
            MagicMock(
                choices=[MagicMock(delta=MagicMock(content="！"))]
            ),
            MagicMock(
                choices=[MagicMock(delta=MagicMock(content="我是"))]
            )
        ]

        with patch('src.app.services.llm_service.ZhipuAI') as mock_zhipu:
            mock_client = MagicMock()

            # 创建异步生成器
            async def mock_stream():
                for chunk in mock_chunks:
                    yield chunk

            mock_client.chat.completions.create.return_value = mock_stream()
            mock_zhipu.return_value = mock_client

            # 注册提供商并调用流式聊天完成
            llm_service_instance.register_provider(tenant_id, LLMProvider.ZHIPU, api_key)
            stream_generator = await llm_service_instance.chat_completion(
                tenant_id=tenant_id,
                messages=sample_messages,
                provider=LLMProvider.ZHIPU,
                stream=True
            )

            # 收集流式响应
            chunks = []
            async for chunk in stream_generator:
                chunks.append(chunk)

            assert len(chunks) == 3
            assert all(isinstance(chunk, LLMStreamChunk) for chunk in chunks)
            assert chunk.type == "content"
            assert chunk.provider == LLMProvider.ZHIPU.value

    @pytest.mark.asyncio
    async def test_chat_completion_thinking_mode(self, llm_service_instance, sample_messages):
        """测试深度思考模式"""
        tenant_id = "test_tenant"
        api_key = "test_zhipu_key"

        # Mock带思考过程的响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "最终回答"
        mock_response.choices[0].message.reasoning_content = "思考过程"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "glm-4.6"
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 25
        mock_response.usage.total_tokens = 40
        mock_response.created = 1234567890

        with patch('src.app.services.llm_service.ZhipuAI') as mock_zhipu:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_zhipu.return_value = mock_client

            # 注册提供商并调用带思考模式的聊天完成
            llm_service_instance.register_provider(tenant_id, LLMProvider.ZHIPU, api_key)
            response = await llm_service_instance.chat_completion(
                tenant_id=tenant_id,
                messages=sample_messages,
                provider=LLMProvider.ZHIPU,
                enable_thinking=True
            )

            assert isinstance(response, LLMResponse)
            assert response.content == "最终回答"
            assert response.thinking == "思考过程"
            assert response.provider == LLMProvider.ZHIPU.value

    @pytest.mark.asyncio
    async def test_multimodal_completion(self, llm_service_instance, sample_multimodal_messages):
        """测试多模态聊天完成"""
        tenant_id = "test_tenant"
        api_key = "test_openrouter_key"

        # Mock OpenRouter响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "这是一张美丽的风景图片"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "google/gemini-2.0-flash-exp"
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 30
        mock_response.usage.total_tokens = 80
        mock_response.created = 1234567890

        with patch('src.app.services.llm_service.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # 注册提供商并调用多模态聊天完成
            llm_service_instance.register_provider(tenant_id, LLMProvider.OPENROUTER, api_key)
            response = await llm_service_instance.chat_completion(
                tenant_id=tenant_id,
                messages=sample_multimodal_messages,
                provider=LLMProvider.OPENROUTER
            )

            assert isinstance(response, LLMResponse)
            assert response.content == "这是一张美丽的风景图片"
            assert response.provider == LLMProvider.OPENROUTER.value
            assert response.model == "google/gemini-2.0-flash-exp"

    @pytest.mark.asyncio
    async def test_validate_providers(self, llm_service_instance):
        """测试提供商验证"""
        tenant_id = "test_tenant"
        zhipu_key = "test_zhipu_key"
        openrouter_key = "test_openrouter_key"

        with patch('src.app.services.llm_service.ZhipuAI') as mock_zhipu, \
             patch('src.app.services.llm_service.AsyncOpenAI') as mock_openai:

            # Mock Zhipu连接测试
            mock_zhipu_client = MagicMock()
            mock_zhipu_response = MagicMock()
            mock_zhipu_response.choices = [MagicMock()]  # 非空响应表示连接成功
            mock_zhipu_client.chat.completions.create.return_value = mock_zhipu_response
            mock_zhipu.return_value = mock_zhipu_client

            # Mock OpenRouter连接测试
            mock_openai_client = AsyncMock()
            mock_openai_response = MagicMock()
            mock_openai_response.choices = [MagicMock()]
            mock_openai_client.chat.completions.create.return_value = mock_openai_response
            mock_openai.return_value = mock_openai_client

            # 注册提供商
            llm_service_instance.register_provider(tenant_id, LLMProvider.ZHIPU, zhipu_key)
            llm_service_instance.register_provider(tenant_id, LLMProvider.OPENROUTER, openrouter_key)

            # 验证提供商连接
            status = await llm_service_instance.validate_providers(tenant_id)

            assert status["zhipu"] is True
            assert status["openrouter"] is True

    @pytest.mark.asyncio
    async def test_get_available_models(self, llm_service_instance):
        """测试获取可用模型"""
        tenant_id = "test_tenant"
        api_key = "test_zhipu_key"

        with patch('src.app.services.llm_service.ZhipuAI') as mock_zhipu:
            # Mock连接测试成功
            mock_zhipu_client = MagicMock()
            mock_zhipu_response = MagicMock()
            mock_zhipu_response.choices = [MagicMock()]
            mock_zhipu_client.chat.completions.create.return_value = mock_zhipu_response
            mock_zhipu.return_value = mock_zhipu_client

            # 注册Zhipu提供商
            llm_service_instance.register_provider(tenant_id, LLMProvider.ZHIPU, api_key)

            # 获取可用模型
            models = await llm_service_instance.get_available_models(tenant_id)

            assert "zhipu" in models
            assert "glm-4-flash" in models["zhipu"]
            assert "glm-4" in models["zhipu"]
            # OpenRouter不可用，不应该在结果中
            assert "openrouter" not in models

    @pytest.mark.asyncio
    async def test_no_provider_error(self, llm_service_instance, sample_messages):
        """测试没有注册提供商时的错误处理"""
        tenant_id = "test_tenant"

        # Mock settings无API密钥
        with patch.object(settings, 'zhipuai_api_key', None), \
             patch.object(settings, 'openrouter_api_key', None):

            with pytest.raises(ValueError, match="No provider configured"):
                await llm_service_instance.chat_completion(
                    tenant_id=tenant_id,
                    messages=sample_messages
                )

    @pytest.mark.asyncio
    async def test_invalid_provider_error(self, llm_service_instance):
        """测试无效提供商错误"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            llm_service_instance.register_provider(
                "test_tenant", "invalid_provider", "test_key"
            )


class TestZhipuProvider:
    """Zhipu提供商测试类"""

    @pytest.mark.asyncio
    async def test_zhipu_provider_creation(self):
        """测试Zhipu提供商创建"""
        with patch('src.app.services.llm_service.ZhipuAI'):
            provider = ZhipuProvider("test_key", "test_tenant")
            assert provider.api_key == "test_key"
            assert provider.tenant_id == "test_tenant"
            assert provider.default_model == "glm-4-flash"

    @pytest.mark.asyncio
    async def test_zhipu_validate_connection_success(self):
        """测试Zhipu连接验证成功"""
        with patch('src.app.services.llm_service.ZhipuAI') as mock_zhipu:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]  # 非空响应表示连接成功
            mock_client.chat.completions.create.return_value = mock_response
            mock_zhipu.return_value = mock_client

            provider = ZhipuProvider("test_key", "test_tenant")
            result = await provider.validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_zhipu_validate_connection_failure(self):
        """测试Zhipu连接验证失败"""
        with patch('src.app.services.llm_service.ZhipuAI') as mock_zhipu:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("Connection failed")
            mock_zhipu.return_value = mock_client

            provider = ZhipuProvider("test_key", "test_tenant")
            result = await provider.validate_connection()
            assert result is False


class TestOpenRouterProvider:
    """OpenRouter提供商测试类"""

    @pytest.mark.asyncio
    async def test_openrouter_provider_creation(self):
        """测试OpenRouter提供商创建"""
        with patch('src.app.services.llm_service.AsyncOpenAI'):
            provider = OpenRouterProvider("test_key", "test_tenant")
            assert provider.api_key == "test_key"
            assert provider.tenant_id == "test_tenant"
            assert provider.default_model == "google/gemini-2.0-flash-exp"

    @pytest.mark.asyncio
    async def test_openrouter_validate_connection_success(self):
        """测试OpenRouter连接验证成功"""
        with patch('src.app.services.llm_service.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]  # 非空响应表示连接成功
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenRouterProvider("test_key", "test_tenant")
            result = await provider.validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_openrouter_validate_connection_failure(self):
        """测试OpenRouter连接验证失败"""
        with patch('src.app.services.llm_service.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = Exception("Connection failed")
            mock_openai.return_value = mock_client

            provider = OpenRouterProvider("test_key", "test_tenant")
            result = await provider.validate_connection()
            assert result is False