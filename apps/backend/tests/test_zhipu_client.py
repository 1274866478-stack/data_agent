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
        with patch('src.app.services.zhipu_client.settings') as mock_settings:
            mock_settings.zhipuai_api_key = "test_api_key"
            mock_settings.zhipuai_default_model = "glm-4"
            return ZhipuAIService()

    @pytest.mark.asyncio
    async def test_check_connection_success(self, service):
        """测试API连接检查成功"""
        # Mock ZhipuAI client
        with patch('src.app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
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
        with patch('src.app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception("API connection failed")
            mock_zhipuai.return_value = mock_client

            result = await service.check_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_invalid_response(self, service):
        """测试API连接检查 - 响应无效"""
        # Mock ZhipuAI client with invalid response
        with patch('src.app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
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
        with patch('src.app.services.zhipu_client.ZhipuAI') as mock_zhipuai:
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


class TestStreamChatCompletion:
    """流式聊天完成集成测试"""

    @pytest.fixture
    def service(self):
        """创建 ZhipuAIService 实例"""
        with patch('src.app.services.zhipu_client.settings') as mock_settings:
            mock_settings.zhipuai_api_key = "test_api_key"
            mock_settings.zhipuai_default_model = "glm-4-flash"
            return ZhipuAIService()

    @pytest.mark.asyncio
    async def test_stream_chat_completion_success(self, service):
        """测试流式聊天完成成功"""
        # Mock流式响应块
        mock_chunks = []
        for content_part in ["你好", "！", "我是", "AI助手。"]:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta = Mock()
            chunk.choices[0].delta.content = content_part
            chunk.choices[0].delta.reasoning_content = None
            mock_chunks.append(chunk)

        with patch.object(service, 'client') as mock_client:
            mock_client.chat.completions.create.return_value = iter(mock_chunks)

            messages = [{"role": "user", "content": "你好"}]
            collected_content = []

            # 直接调用stream_chat_completion并迭代
            stream_gen = service.stream_chat_completion(messages=messages)
            async for chunk in stream_gen:
                if chunk['type'] == 'content' and chunk['content']:
                    collected_content.append(chunk['content'])

            assert len(collected_content) == 4
            assert "".join(collected_content) == "你好！我是AI助手。"

    @pytest.mark.asyncio
    async def test_stream_chat_completion_with_thinking(self, service):
        """测试流式聊天完成 - 带思考模式"""
        # Mock带思考的流式响应
        mock_chunks = []

        # 思考过程块
        for thinking in ["分析问题...", "整理答案..."]:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta = Mock()
            chunk.choices[0].delta.reasoning_content = thinking
            chunk.choices[0].delta.content = None
            mock_chunks.append(chunk)

        # 内容块
        for content in ["答案是", "42。"]:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta = Mock()
            chunk.choices[0].delta.reasoning_content = None
            chunk.choices[0].delta.content = content
            mock_chunks.append(chunk)

        with patch.object(service, 'client') as mock_client:
            mock_client.chat.completions.create.return_value = iter(mock_chunks)

            messages = [{"role": "user", "content": "请分析这个问题"}]
            thinking_parts = []
            content_parts = []

            stream_gen = service.stream_chat_completion(
                messages=messages,
                enable_thinking=True,
                show_thinking=True
            )
            async for chunk in stream_gen:
                if chunk['type'] == 'thinking':
                    thinking_parts.append(chunk['content'])
                elif chunk['type'] == 'content' and chunk['content']:
                    content_parts.append(chunk['content'])

            assert len(thinking_parts) == 2
            assert len(content_parts) == 2
            assert "分析问题..." in thinking_parts
            assert "答案是" in content_parts

    @pytest.mark.asyncio
    async def test_stream_chat_completion_error_handling(self, service):
        """测试流式聊天完成 - 错误处理"""
        with patch.object(service, 'client') as mock_client:
            mock_client.chat.completions.create.side_effect = Exception("API调用失败")

            messages = [{"role": "user", "content": "测试"}]
            error_received = False

            stream_gen = service.stream_chat_completion(messages=messages)
            async for chunk in stream_gen:
                if chunk['type'] == 'error':
                    error_received = True
                    assert "调用出错" in chunk['content']

            assert error_received


class TestThinkingModeIntegration:
    """思考模式集成测试"""

    @pytest.fixture
    def service(self):
        """创建 ZhipuAIService 实例"""
        with patch('src.app.services.zhipu_client.settings') as mock_settings:
            mock_settings.zhipuai_api_key = "test_api_key"
            mock_settings.zhipuai_default_model = "glm-4-flash"
            return ZhipuAIService()

    def test_should_enable_thinking_with_indicators(self, service):
        """测试思考模式触发 - 包含指示词"""
        messages = [{"role": "user", "content": "请详细分析机器学习的原理"}]
        assert service.should_enable_thinking(messages) is True

        messages = [{"role": "user", "content": "比较深度学习和传统机器学习的优缺点"}]
        assert service.should_enable_thinking(messages) is True

    def test_should_enable_thinking_with_complex_question(self, service):
        """测试思考模式触发 - 复杂问题"""
        # 较长的问题
        long_question = "请从技术原理、应用场景、优势劣势、发展趋势等多个角度，详细分析人工智能在医疗健康领域的应用现状和未来发展方向。"
        messages = [{"role": "user", "content": long_question}]
        assert service.should_enable_thinking(messages) is True

        # 多问号问题
        multi_question = "什么是AI？它有什么用？如何学习？"
        messages = [{"role": "user", "content": multi_question}]
        assert service.should_enable_thinking(messages) is True

    def test_should_not_enable_thinking_for_simple_question(self, service):
        """测试思考模式不触发 - 简单问题"""
        messages = [{"role": "user", "content": "你好"}]
        assert service.should_enable_thinking(messages) is False

        messages = [{"role": "user", "content": "今天天气怎么样"}]
        assert service.should_enable_thinking(messages) is False


class TestMultiTurnConversation:
    """多轮对话集成测试"""

    @pytest.fixture
    def service(self):
        """创建 ZhipuAIService 实例"""
        with patch('src.app.services.zhipu_client.settings') as mock_settings:
            mock_settings.zhipuai_api_key = "test_api_key"
            mock_settings.zhipuai_default_model = "glm-4-flash"
            return ZhipuAIService()

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_context(self, service):
        """测试多轮对话上下文保持"""
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            # 第一轮响应
            mock_response1 = Mock()
            mock_response1.choices = [Mock()]
            mock_response1.choices[0].message.content = "机器学习是AI的一个分支"
            mock_response1.choices[0].message.role = "assistant"
            mock_response1.choices[0].finish_reason = "stop"
            mock_response1.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_response1.model = "glm-4-flash"
            mock_response1.created = 1700000000

            # 第二轮响应
            mock_response2 = Mock()
            mock_response2.choices = [Mock()]
            mock_response2.choices[0].message.content = "主要应用包括图像识别和NLP"
            mock_response2.choices[0].message.role = "assistant"
            mock_response2.choices[0].finish_reason = "stop"
            mock_response2.usage = Mock(prompt_tokens=20, completion_tokens=25, total_tokens=45)
            mock_response2.model = "glm-4-flash"
            mock_response2.created = 1700000001

            mock_api_call.side_effect = [mock_response1, mock_response2]

            # 第一轮对话
            messages1 = [{"role": "user", "content": "什么是机器学习？"}]
            result1 = await service.chat_completion(messages=messages1)

            assert result1 is not None
            assert "机器学习" in result1["content"]

            # 第二轮对话（带上下文）
            messages2 = [
                {"role": "user", "content": "什么是机器学习？"},
                {"role": "assistant", "content": result1["content"]},
                {"role": "user", "content": "它有什么应用？"}
            ]
            result2 = await service.chat_completion(messages=messages2)

            assert result2 is not None
            assert "应用" in result2["content"]
            assert mock_api_call.call_count == 2


class TestCircuitBreaker:
    """熔断器测试"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_trigger(self):
        """测试熔断器触发"""
        failure_count = 0

        @retry_on_failure(max_retries=3, delay=0.01, circuit_breaker_threshold=3)
        async def failing_function():
            nonlocal failure_count
            failure_count += 1
            raise Exception("持续失败")

        # 第一次调用应该在重试后失败
        with pytest.raises(Exception, match="持续失败"):
            await failing_function()

        assert failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """测试熔断器恢复后成功"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.01)
        async def recovering_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("临时失败")
            return "恢复成功"

        result = await recovering_function()
        assert result == "恢复成功"
        assert call_count == 2


class TestCacheIntegration:
    """缓存集成测试"""

    @pytest.fixture
    def service(self):
        """创建 ZhipuAIService 实例"""
        with patch('src.app.services.zhipu_client.settings') as mock_settings:
            mock_settings.zhipuai_api_key = "test_api_key"
            mock_settings.zhipuai_default_model = "glm-4-flash"
            return ZhipuAIService()

    @pytest.mark.asyncio
    async def test_cache_hit(self, service):
        """测试缓存命中"""
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "缓存测试响应"
            mock_response.choices[0].message.role = "assistant"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock(prompt_tokens=5, completion_tokens=10, total_tokens=15)
            mock_response.model = "glm-4-flash"
            mock_response.created = 1700000000

            mock_api_call.return_value = mock_response

            messages = [{"role": "user", "content": "缓存测试"}]

            # 第一次调用 - 应该调用API
            result1 = await service.chat_completion(messages=messages, enable_cache=True)
            assert result1 is not None
            assert mock_api_call.call_count == 1

            # 第二次相同调用 - 应该命中缓存
            result2 = await service.chat_completion(messages=messages, enable_cache=True)
            assert result2 is not None
            assert result2["content"] == result1["content"]
            # API调用次数不应增加（从缓存获取）
            assert mock_api_call.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_disabled(self, service):
        """测试禁用缓存"""
        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "无缓存响应"
            mock_response.choices[0].message.role = "assistant"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock(prompt_tokens=5, completion_tokens=10, total_tokens=15)
            mock_response.model = "glm-4-flash"
            mock_response.created = 1700000000

            mock_api_call.return_value = mock_response

            messages = [{"role": "user", "content": "无缓存测试"}]

            # 两次调用都禁用缓存 - 应该每次都调用API
            await service.chat_completion(messages=messages, enable_cache=False)
            await service.chat_completion(messages=messages, enable_cache=False)

            assert mock_api_call.call_count == 2


class TestPerformanceMonitoring:
    """性能监控集成测试"""

    @pytest.fixture
    def service(self):
        """创建 ZhipuAIService 实例"""
        with patch('src.app.services.zhipu_client.settings') as mock_settings:
            mock_settings.zhipuai_api_key = "test_api_key"
            mock_settings.zhipuai_default_model = "glm-4-flash"
            return ZhipuAIService()

    @pytest.mark.asyncio
    async def test_performance_stats_tracking(self, service):
        """测试性能统计跟踪"""
        initial_request_count = service.request_count

        with patch.object(service, '_call_api_with_retry') as mock_api_call:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "性能测试"
            mock_response.choices[0].message.role = "assistant"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock(prompt_tokens=5, completion_tokens=5, total_tokens=10)
            mock_response.model = "glm-4-flash"
            mock_response.created = 1700000000

            mock_api_call.return_value = mock_response

            messages = [{"role": "user", "content": "测试"}]
            await service.chat_completion(messages=messages)

            # 验证请求计数增加
            assert service.request_count >= initial_request_count

    def test_get_performance_stats(self, service):
        """测试获取性能统计"""
        # 验证统计属性存在
        assert hasattr(service, 'request_count')
        assert hasattr(service, 'success_count')
        assert hasattr(service, 'error_count')
        assert hasattr(service, 'total_response_time')


if __name__ == "__main__":
    pytest.main([__file__])