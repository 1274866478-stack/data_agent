"""
智谱AI客户端测试用例
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.app.services.zhipu_client import ZhipuAIService, zhipu_service, retry_on_failure


class TestRetryDecorator:
    """重试装饰器测试类"""

    @pytest.mark.asyncio
    async def test_retry_on_failure_success_first_attempt(self):
        """测试重试装饰器 - 第一次尝试成功"""
        @retry_on_failure(max_retries=3, delay=0.1)
        async def test_function():
            return "success"

        result = await test_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_failure_success_after_retry(self):
        """测试重试装饰器 - 重试后成功"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_failure_all_attempts_failed(self):
        """测试重试装饰器 - 所有尝试都失败"""
        @retry_on_failure(max_retries=2, delay=0.01)
        async def test_function():
            raise Exception("Persistent failure")

        with pytest.raises(Exception, match="Persistent failure"):
            await test_function()


class TestZhipuAIService:
    """ZhipuAIService 测试类"""

    @pytest.fixture
    def service(self):
        """创建 ZhipuAIService 实例"""
        with patch('app.services.zhipu_client.settings') as mock_settings:
            mock_settings.zhipuai_api_key = "test_api_key"
            mock_settings.zhipuai_default_model = "glm-4"
            return ZhipuAIService()

    @pytest.mark.asyncio
    async def test_check_connection_success(self, service):
        """测试API连接检查成功"""
        # Mock ZhipuAI client
        with patch('app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Hello response"
            mock_client.chat.completions.create.return_value = mock_response

            mock_zhipuai.return_value = mock_client

            result = await service.check_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, service):
        """测试API连接检查失败"""
        # Mock ZhipuAI client to raise exception
        with patch('app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception("API connection failed")
            mock_zhipuai.return_value = mock_client

            result = await service.check_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_invalid_response(self, service):
        """测试API连接检查 - 响应无效"""
        # Mock ZhipuAI client with invalid response
        with patch('app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = []  # 空选择列表
            mock_client.chat.completions.create.return_value = mock_response

            mock_zhipuai.return_value = mock_client

            result = await service.check_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, service):
        """测试聊天完成成功"""
        # Mock ZhipuAI client
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Chat response"
            mock_response.choices[0].message.role = "assistant"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            mock_response.model = "glm-4"
            mock_response.created = 1640995200

            mock_api_call.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            result = await service.chat_completion(messages=messages)

            assert result is not None
            assert result["content"] == "Chat response"
            assert result["role"] == "assistant"
            assert result["usage"]["total_tokens"] == 30
            assert result["model"] == "glm-4"

    @pytest.mark.asyncio
    async def test_chat_completion_failure(self, service):
        """测试聊天完成失败"""
        # Mock API call to raise exception
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_api_call.side_effect = Exception("API call failed")

            messages = [{"role": "user", "content": "Hello"}]
            result = await service.chat_completion(messages=messages)

            assert result is None

    @pytest.mark.asyncio
    async def test_chat_completion_with_custom_params(self, service):
        """测试聊天完成使用自定义参数"""
        # Mock ZhipuAI client
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Custom response"
            mock_response.choices[0].message.role = "assistant"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.prompt_tokens = 15
            mock_response.usage.completion_tokens = 25
            mock_response.usage.total_tokens = 40
            mock_response.model = "glm-4-turbo"
            mock_response.created = 1640995200

            mock_api_call.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            result = await service.chat_completion(
                messages=messages,
                model="glm-4-turbo",
                max_tokens=1000,
                temperature=0.5
            )

            assert result is not None
            assert result["content"] == "Custom response"
            assert result["model"] == "glm-4-turbo"

            # 验证调用参数
            mock_api_call.assert_called_once()
            call_args = mock_api_call.call_args[0][0]
            # 验证 lambda 函数被正确调用（这里只验证函数被调用）
            assert callable(call_args)

    @pytest.mark.asyncio
    async def test_embedding_success(self, service):
        """测试嵌入生成成功"""
        # Mock API call
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_response = Mock()
            mock_data1 = Mock()
            mock_data1.embedding = [0.1, 0.2, 0.3]
            mock_data2 = Mock()
            mock_data2.embedding = [0.4, 0.5, 0.6]
            mock_response.data = [mock_data1, mock_data2]

            mock_api_call.return_value = mock_response

            texts = ["text1", "text2"]
            result = await service.embedding(texts=texts)

            assert result is not None
            assert len(result) == 2
            assert result[0] == [0.1, 0.2, 0.3]
            assert result[1] == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_embedding_failure(self, service):
        """测试嵌入生成失败"""
        # Mock API call to raise exception
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_api_call.side_effect = Exception("Embedding API failed")

            texts = ["text1", "text2"]
            result = await service.embedding(texts=texts)

            assert result is None

    @pytest.mark.asyncio
    async def test_semantic_search_success(self, service):
        """测试语义搜索成功"""
        # Mock embedding call
        with patch.object(service, 'embedding') as mock_embedding:
            mock_embedding.return_value = [
                [0.1, 0.2, 0.3],  # query embedding
                [0.4, 0.5, 0.6],  # doc1 embedding
                [0.7, 0.8, 0.9]   # doc2 embedding
            ]

            documents = ["Document 1", "Document 2"]
            result = await service.semantic_search(
                query="test query",
                documents=documents,
                top_k=2
            )

            assert result is not None
            assert result["query"] == "test query"
            assert result["total_documents"] == 2
            assert len(result["results"]) == 2
            assert all("similarity" in r for r in result["results"])

    @pytest.mark.asyncio
    async def test_semantic_search_no_documents(self, service):
        """测试语义搜索 - 无文档"""
        result = await service.semantic_search(
            query="test query",
            documents=[],
            top_k=2
        )

        assert result is not None
        assert result["query"] == "test query"
        assert result["total_documents"] == 0
        assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_semantic_search_embedding_failure(self, service):
        """测试语义搜索 - 嵌入生成失败"""
        # Mock embedding to return None
        with patch.object(service, 'embedding') as mock_embedding:
            mock_embedding.return_value = None

            documents = ["Document 1", "Document 2"]
            result = await service.semantic_search(
                query="test query",
                documents=documents,
                top_k=2
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_text_analysis_success(self, service):
        """测试文本分析成功"""
        # Mock chat completion
        with patch.object(service, 'chat_completion') as mock_chat:
            mock_chat.return_value = {
                "content": "Text analysis result",
                "role": "assistant"
            }

            text = "This is a test text for analysis."
            result = await service.text_analysis(text=text, analysis_type="summary")

            assert result is not None
            assert result == "Text analysis result"

            # 验证调用参数
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            assert len(call_args[1]["messages"]) == 2  # system + user
            assert call_args[1]["max_tokens"] == 500
            assert call_args[1]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_text_analysis_different_types(self, service):
        """测试不同类型的文本分析"""
        # Mock chat completion
        with patch.object(service, 'chat_completion') as mock_chat:
            mock_chat.return_value = {
                "content": "Analysis result",
                "role": "assistant"
            }

            text = "Test text"
            analysis_types = ["summary", "keywords", "sentiment", "topics", "custom"]

            for analysis_type in analysis_types:
                result = await service.text_analysis(text=text, analysis_type=analysis_type)
                assert result == "Analysis result"

    @pytest.mark.asyncio
    async def test_text_analysis_failure(self, service):
        """测试文本分析失败"""
        # Mock chat completion to return None
        with patch.object(service, 'chat_completion') as mock_chat:
            mock_chat.return_value = None

            text = "Test text"
            result = await service.text_analysis(text=text, analysis_type="summary")

            assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, service):
        """测试API密钥验证成功"""
        # Mock check_connection
        with patch.object(service, 'check_connection') as mock_check:
            mock_check.return_value = True

            result = await service.validate_api_key()

            assert result is True
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_api_key_failure(self, service):
        """测试API密钥验证失败"""
        # Mock check_connection
        with patch.object(service, 'check_connection') as mock_check:
            mock_check.return_value = False

            result = await service.validate_api_key()

            assert result is False
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_info_success(self, service):
        """测试获取模型信息成功"""
        # Mock chat completion
        with patch.object(service, 'chat_completion') as mock_chat:
            mock_chat.return_value = {
                "content": "Test response",
                "role": "assistant"
            }

            result = await service.get_model_info()

            assert result is not None
            assert result["model"] == service.default_model
            assert result["status"] == "available"
            assert result["max_tokens"] == service.max_tokens

    @pytest.mark.asyncio
    async def test_get_model_info_failure(self, service):
        """测试获取模型信息失败"""
        # Mock chat completion to return None
        with patch.object(service, 'chat_completion') as mock_chat:
            mock_chat.return_value = None

            result = await service.get_model_info()

            assert result is not None
            assert result["model"] == service.default_model
            assert result["status"] == "unavailable"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_model_info_with_custom_model(self, service):
        """测试获取指定模型信息"""
        # Mock chat completion
        with patch.object(service, 'chat_completion') as mock_chat:
            mock_chat.return_value = {
                "content": "Test response",
                "role": "assistant"
            }

            result = await service.get_model_info(model="glm-4-turbo")

            assert result is not None
            assert result["model"] == "glm-4-turbo"

            # 验证调用使用了正确的模型
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            assert call_args[1]["model"] == "glm-4-turbo"

    @pytest.mark.asyncio
    async def test_call_api_with_retry_success(self, service):
        """测试API调用重试机制成功"""
        # Mock ZhipuAI client
        with patch('app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
            mock_client = Mock()
            mock_response = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_zhipuai.return_value = mock_client

            api_func = lambda: mock_client.chat.completions.create()
            result = await service._call_api_with_retry(api_func)

            assert result == mock_response

    @pytest.mark.asyncio
    async def test_call_api_with_retry_success_after_retry(self, service):
        """测试API调用重试机制 - 重试后成功"""
        call_count = 0

        def api_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return Mock()

        result = await service._call_api_with_retry(api_func, max_retries=3)

        assert result is not None
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_call_api_with_retry_all_attempts_failed(self, service):
        """测试API调用重试机制 - 所有尝试都失败"""
        def api_func():
            raise Exception("Persistent failure")

        with pytest.raises(Exception, match="Persistent failure"):
            await service._call_api_with_retry(api_func, max_retries=2)


class TestGlobalService:
    """全局服务实例测试"""

    @pytest.mark.asyncio
    async def test_global_zhipu_service(self):
        """测试全局智谱服务实例"""
        assert zhipu_service is not None
        assert isinstance(zhipu_service, ZhipuAIService)


if __name__ == "__main__":
    pytest.main([__file__])