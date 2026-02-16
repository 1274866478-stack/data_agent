"""
AI 服务测试 API 端点集成测试

测试 /api/v1/test 路由下的所有端点
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.app.main import app


class TestZhipuTestEndpoints:
    """智谱AI测试端点测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    # ========== POST /test/zhipu 测试 ==========

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_connection_success(self, mock_service, client):
        """测试智谱AI连接 - 成功"""
        mock_service.check_connection = AsyncMock(return_value=True)
        mock_service.get_model_info = AsyncMock(return_value={
            "model": "glm-4",
            "status": "available"
        })
        
        response = client.post("/api/v1/test/zhipu")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ZhipuAI"
        assert data["status"] == "success"
        assert "model_info" in data

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_connection_failed(self, mock_service, client):
        """测试智谱AI连接 - 失败"""
        mock_service.check_connection = AsyncMock(return_value=False)
        
        response = client.post("/api/v1/test/zhipu")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_connection_exception(self, mock_service, client):
        """测试智谱AI连接 - 异常"""
        mock_service.check_connection = AsyncMock(side_effect=Exception("API不可用"))
        
        response = client.post("/api/v1/test/zhipu")
        
        assert response.status_code == 500
        assert "失败" in response.json()["detail"] or "error" in response.json()["detail"].lower()

    # ========== POST /test/zhipu/chat 测试 ==========

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_chat_success(self, mock_service, client):
        """测试智谱AI聊天 - 成功"""
        mock_service.default_model = "glm-4"
        mock_service.chat_completion = AsyncMock(return_value={
            "content": "你好！有什么可以帮助你的吗？",
            "role": "assistant",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "glm-4",
            "finish_reason": "stop",
            "created_at": 1234567890.0
        })
        
        response = client.post(
            "/api/v1/test/zhipu/chat",
            json={"message": "你好"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["test_type"] == "chat_completion"
        assert "response" in data

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_chat_failed(self, mock_service, client):
        """测试智谱AI聊天 - 无响应"""
        mock_service.default_model = "glm-4"
        mock_service.chat_completion = AsyncMock(return_value=None)
        
        response = client.post(
            "/api/v1/test/zhipu/chat",
            json={"message": "你好"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_chat_exception(self, mock_service, client):
        """测试智谱AI聊天 - 异常"""
        mock_service.chat_completion = AsyncMock(side_effect=Exception("聊天服务异常"))
        
        response = client.post(
            "/api/v1/test/zhipu/chat",
            json={"message": "你好"}
        )
        
        assert response.status_code == 500

    def test_zhipu_chat_invalid_message(self, client):
        """测试智谱AI聊天 - 无效消息（空字符串）"""
        response = client.post(
            "/api/v1/test/zhipu/chat",
            json={"message": ""}
        )
        
        assert response.status_code == 422  # Validation error

    # ========== POST /test/zhipu/embedding 测试 ==========

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_embedding_success(self, mock_service, client):
        """测试智谱AI嵌入 - 成功"""
        mock_service.embedding = AsyncMock(return_value=[
            [0.1, 0.2, 0.3, 0.4, 0.5] * 256  # 1280维向量
        ])
        
        response = client.post(
            "/api/v1/test/zhipu/embedding",
            json={"texts": ["测试文本"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["test_type"] == "embedding_generation"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_embedding_failed(self, mock_service, client):
        """测试智谱AI嵌入 - 失败"""
        mock_service.embedding = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/test/zhipu/embedding",
            json={"texts": ["测试文本"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_embedding_exception(self, mock_service, client):
        """测试智谱AI嵌入 - 异常"""
        mock_service.embedding = AsyncMock(side_effect=Exception("嵌入服务异常"))

        response = client.post(
            "/api/v1/test/zhipu/embedding",
            json={"texts": ["测试文本"]}
        )

        assert response.status_code == 500

    # ========== POST /test/zhipu/semantic-search 测试 ==========

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_semantic_search_success(self, mock_service, client):
        """测试智谱AI语义搜索 - 成功"""
        mock_service.semantic_search = AsyncMock(return_value={
            "results": [
                {"document": "文档1", "score": 0.95},
                {"document": "文档2", "score": 0.85}
            ],
            "query": "搜索查询"
        })

        response = client.post(
            "/api/v1/test/zhipu/semantic-search",
            json={
                "query": "搜索查询",
                "documents": ["文档1", "文档2", "文档3"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["test_type"] == "semantic_search"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_semantic_search_failed(self, mock_service, client):
        """测试智谱AI语义搜索 - 失败"""
        mock_service.semantic_search = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/test/zhipu/semantic-search",
            json={
                "query": "搜索查询",
                "documents": ["文档1"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_semantic_search_exception(self, mock_service, client):
        """测试智谱AI语义搜索 - 异常"""
        mock_service.semantic_search = AsyncMock(side_effect=Exception("搜索服务异常"))

        response = client.post(
            "/api/v1/test/zhipu/semantic-search",
            json={
                "query": "搜索查询",
                "documents": ["文档1"]
            }
        )

        assert response.status_code == 500

    # ========== POST /test/zhipu/text-analysis 测试 ==========

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_text_analysis_success(self, mock_service, client):
        """测试智谱AI文本分析 - 成功"""
        mock_service.text_analysis = AsyncMock(return_value="这是一段测试文本的摘要。")

        response = client.post(
            "/api/v1/test/zhipu/text-analysis",
            json={
                "text": "这是一段需要分析的长文本内容。",
                "analysis_type": "summary"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["test_type"] == "text_analysis"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_text_analysis_failed(self, mock_service, client):
        """测试智谱AI文本分析 - 失败"""
        mock_service.text_analysis = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/test/zhipu/text-analysis",
            json={
                "text": "测试文本",
                "analysis_type": "summary"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_text_analysis_exception(self, mock_service, client):
        """测试智谱AI文本分析 - 异常"""
        mock_service.text_analysis = AsyncMock(side_effect=Exception("分析服务异常"))

        response = client.post(
            "/api/v1/test/zhipu/text-analysis",
            json={
                "text": "测试文本",
                "analysis_type": "summary"
            }
        )

        assert response.status_code == 500

    # ========== GET /test/zhipu/models 测试 ==========

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_models_success(self, mock_service, client):
        """测试获取智谱AI模型信息 - 成功"""
        mock_service.get_model_info = AsyncMock(return_value={
            "model": "glm-4",
            "status": "available",
            "capabilities": ["chat", "embedding"]
        })

        response = client.get("/api/v1/test/zhipu/models")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["test_type"] == "model_availability"
        assert "tested_models" in data

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_models_exception(self, mock_service, client):
        """测试获取智谱AI模型信息 - 异常"""
        mock_service.get_model_info = AsyncMock(side_effect=Exception("模型服务异常"))

        response = client.get("/api/v1/test/zhipu/models")

        assert response.status_code == 500

    # ========== GET /test/zhipu/comprehensive 测试 ==========

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_comprehensive_all_success(self, mock_service, client):
        """测试智谱AI综合测试 - 全部成功"""
        mock_service.check_connection = AsyncMock(return_value=True)
        mock_service.chat_completion = AsyncMock(return_value={
            "content": "测试响应",
            "role": "assistant"
        })
        mock_service.embedding = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        mock_service.text_analysis = AsyncMock(return_value="分析结果")

        response = client.get("/api/v1/test/zhipu/comprehensive")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "success"
        assert data["successful_tests"] == data["total_tests"]

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_comprehensive_connection_failed(self, mock_service, client):
        """测试智谱AI综合测试 - 连接失败"""
        mock_service.check_connection = AsyncMock(return_value=False)

        response = client.get("/api/v1/test/zhipu/comprehensive")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "failed"
        assert "连接失败" in data["message"]

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_comprehensive_partial_success(self, mock_service, client):
        """测试智谱AI综合测试 - 部分成功"""
        mock_service.check_connection = AsyncMock(return_value=True)
        mock_service.chat_completion = AsyncMock(return_value={
            "content": "测试响应",
            "role": "assistant"
        })
        mock_service.embedding = AsyncMock(return_value=None)  # 嵌入失败
        mock_service.text_analysis = AsyncMock(return_value="分析结果")

        response = client.get("/api/v1/test/zhipu/comprehensive")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "partial_success"

    @patch("src.app.api.v1.endpoints.test.zhipu_service")
    def test_zhipu_comprehensive_exception(self, mock_service, client):
        """测试智谱AI综合测试 - 异常"""
        mock_service.check_connection = AsyncMock(side_effect=Exception("服务异常"))

        response = client.get("/api/v1/test/zhipu/comprehensive")

        assert response.status_code == 500

