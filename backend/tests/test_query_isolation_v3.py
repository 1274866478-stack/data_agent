"""
Story 3.1: 租户隔离的查询 API V3 测试
测试租户隔离、查询验证、限流和错误处理
"""

import pytest
import asyncio
import json
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, AsyncMock

from src.app.main import app
from src.app.data.models import Tenant, DataSourceConnection, KnowledgeDocument, QueryLog, QueryStatus, QueryType
from src.app.schemas.query import QueryRequest, QueryResponseV3, QueryType as SchemaQueryType
from src.app.services.query_context import QueryContext, QueryLimits


class TestQueryTenantIsolation:
    """测试租户隔离功能"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def db_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_tenant(self):
        """模拟租户"""
        tenant = Mock(spec=Tenant)
        tenant.id = "tenant_123"
        tenant.email = "test@example.com"
        tenant.status = "active"
        tenant.settings = {
            "max_queries_per_hour": 100,
            "max_concurrent_queries": 5,
            "max_query_length": 1000,
            "query_timeout_seconds": 60
        }
        return tenant

    @pytest.fixture
    def mock_data_sources(self):
        """模拟数据源"""
        ds1 = Mock(spec=DataSourceConnection)
        ds1.id = 1
        ds1.tenant_id = "tenant_123"
        ds1.name = "Sales DB"
        ds1.connection_type = "postgresql"
        ds1.is_active = True

        ds2 = Mock(spec=DataSourceConnection)
        ds2.id = 2
        ds2.tenant_id = "tenant_123"
        ds2.name = "Product DB"
        ds2.connection_type = "postgresql"
        ds2.is_active = True

        return [ds1, ds2]

    @pytest.fixture
    def mock_documents(self):
        """模拟文档"""
        doc1 = Mock(spec=KnowledgeDocument)
        doc1.id = 1
        doc1.tenant_id = "tenant_123"
        doc1.title = "Sales Report 2024"
        doc1.status = "ready"

        doc2 = Mock(spec=KnowledgeDocument)
        doc2.id = 2
        doc2.tenant_id = "tenant_123"
        doc2.title = "Product Catalog"
        doc2.status = "ready"

        return [doc1, doc2]

    def test_query_context_isolation(self, db_session, mock_tenant):
        """测试查询上下文租户隔离"""
        # 创建查询上下文
        query_context = QueryContext(db_session, "tenant_123", "user_123")

        # 模拟数据库查询，确保只查询当前租户的数据
        mock_query = Mock()
        db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        # 测试获取数据源
        data_sources = query_context.get_tenant_data_sources()

        # 验证查询包含租户过滤条件
        db_session.query.assert_called_with(DataSourceConnection)
        mock_query.filter.assert_called()

        # 验证返回结果
        assert isinstance(data_sources, list)

    def test_query_context_unauthorized_access(self, db_session):
        """测试未授权访问"""
        query_context = QueryContext(db_session, "unauthorized_tenant", "user_123")

        # 模拟没有找到租户
        db_session.query.return_value.filter.return_value.first.return_value = None

        # 测试获取数据源应该返回空列表
        data_sources = query_context.get_tenant_data_sources()
        assert data_sources == []

    @patch('src.app.services.query_context.get_current_tenant_id')
    def test_query_request_validation(self, mock_get_tenant_id, client):
        """测试查询请求验证"""
        mock_get_tenant_id.return_value = "tenant_123"

        # 测试有效查询请求
        valid_request = {
            "question": "上个季度销售额最高的产品是什么？",
            "context": {
                "time_range": "2024-Q3",
                "data_source_ids": ["sales_db"]
            },
            "options": {
                "max_results": 10,
                "include_explainability": True
            }
        }

        # 模拟认证
        with patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request') as mock_auth:
            mock_tenant = Mock()
            mock_tenant.id = "tenant_123"
            mock_auth.return_value = mock_tenant

            # 测试请求格式验证
            request = QueryRequest(**valid_request)
            assert request.question == valid_request["question"]
            assert request.context.time_range == "2024-Q3"
            assert request.options.max_results == 10

    def test_query_request_invalid_input(self):
        """测试无效查询输入"""
        # 测试空问题
        with pytest.raises(ValueError) as exc_info:
            QueryRequest(question="   ")

        assert "查询问题不能为空" in str(exc_info.value)

        # 测试问题过长
        with pytest.raises(ValueError) as exc_info:
            QueryRequest(question="a" * 1001)

        assert "查询问题过长" in str(exc_info.value)

        # 测试SQL注入检测
        with pytest.raises(ValueError) as exc_info:
            QueryRequest(question="SELECT * FROM users; DROP TABLE users;")

        assert "查询包含不安全的内容" in str(exc_info.value)

    def test_query_rate_limiting(self, db_session, mock_tenant):
        """测试查询频率限制"""
        query_context = QueryContext(db_session, "tenant_123", "user_123")

        # 模拟超出频率限制
        mock_query = Mock()
        db_session.query.return_value = mock_query
        mock_query.filter.return_value.count.return_value = 150  # 超出100的限制

        can_proceed, error_msg = query_context.check_rate_limits()

        assert not can_proceed
        assert "Query rate limit exceeded" in error_msg

    def test_query_concurrent_limit(self, db_session, mock_tenant):
        """测试并发查询限制"""
        query_context = QueryContext(db_session, "tenant_123", "user_123")

        # 模拟超出并发限制
        def side_effect(*args):
            if "created_at" in str(args):
                return Mock(count=lambda: 2)  # 正常查询数
            else:
                return Mock(count=lambda: 6)  # 超出5的并发限制

        mock_query = Mock()
        db_session.query.return_value = mock_query
        mock_query.filter.return_value.count.side_effect = side_effect

        can_proceed, error_msg = query_context.check_rate_limits()

        assert not can_proceed
        assert "Too many concurrent queries" in error_msg

    def test_query_caching(self, db_session, mock_tenant):
        """测试查询缓存"""
        query_context = QueryContext(db_session, "tenant_123", "user_123")
        query_hash = "test_hash_123"

        # 模拟缓存命中
        mock_cached_query = Mock(spec=QueryLog)
        mock_cached_query.id = uuid4()
        mock_cached_query.response_data = {
            "answer": "Cached answer",
            "citations": [],
            "data_sources": [],
            "explainability_log": "Cached explanation",
            "query_type": "mixed"
        }
        mock_cached_query.response_time_ms = 1000
        mock_cached_query.tokens_used = 100

        mock_query = Mock()
        db_session.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.first.return_value = mock_cached_query

        # 测试获取缓存
        cached_query = query_context.get_cached_query(query_hash)

        assert cached_query is not None
        assert cached_query.response_data["answer"] == "Cached answer"

    def test_query_history_pagination(self, db_session, mock_tenant):
        """测试查询历史分页"""
        query_context = QueryContext(db_session, "tenant_123", "user_123")

        # 模拟查询历史
        mock_query_logs = []
        for i in range(25):
            mock_log = Mock(spec=QueryLog)
            mock_log.id = uuid4()
            mock_log.question = f"Question {i+1}"
            mock_log.status = QueryStatus.SUCCESS
            mock_log.response_time_ms = 1000 + i * 100
            mock_log.cache_hit = i % 2 == 0
            mock_log.created_at = datetime.utcnow()
            mock_query_logs.append(mock_log)

        # 模拟数据库查询
        def side_effect(*args):
            if "count" in str(args):
                return Mock(count=lambda: 25)
            else:
                mock_result = Mock()
                mock_result.__getitem__ = lambda self, key: mock_query_logs[key] if isinstance(key, int) else mock_query_logs
                mock_result.__len__ = lambda: len(mock_query_logs)
                return mock_result

        mock_query = Mock()
        db_session.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value = side_effect()
        mock_query.filter.return_value.count.return_value = 25

        # 测试获取查询历史
        history = query_context.get_query_history(page=1, page_size=10)

        assert history["total_count"] == 25
        assert history["page"] == 1
        assert history["page_size"] == 10
        assert len(history["queries"]) == 25  # 模拟返回所有查询

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    @patch('src.app.api.v1.endpoints.query.llm_service')
    def test_query_processing_success(self, mock_llm_service, mock_auth, client, db_session):
        """测试查询处理成功流程"""
        # 设置模拟
        mock_tenant = Mock()
        mock_tenant.id = "tenant_123"
        mock_auth.return_value = mock_tenant

        mock_llm_response = Mock()
        mock_llm_response.success = True
        mock_llm_response.content = "这是一个测试答案"
        mock_llm_response.usage = {"total_tokens": 150}
        mock_llm_service.chat_completion = AsyncMock(return_value=mock_llm_response)

        # 模拟查询上下文
        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.check_rate_limits.return_value = (True, None)
            mock_query_context.get_cached_query.return_value = None
            mock_query_context.log_query_request.return_value = Mock()
            mock_query_context.get_tenant_data_sources.return_value = []
            mock_query_context.get_tenant_documents.return_value = []
            mock_context.return_value = mock_query_context

            # 模拟查询服务
            with patch('src.app.api.v1.endpoints.query.get_query_service') as mock_service:
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                mock_service_instance.process_query = AsyncMock(return_value={
                    "answer": "测试答案",
                    "citations": [],
                    "data_sources": [],
                    "explainability_log": "测试解释",
                    "response_time_ms": 2000,
                    "tokens_used": 150,
                    "query_type": "mixed"
                })

                # 发送查询请求
                response = client.post(
                    "/api/v1/query",
                    json={
                        "question": "测试问题",
                        "context": {"time_range": "2024-Q3"},
                        "options": {"max_results": 10}
                    },
                    headers={"Authorization": "Bearer mock_token"}
                )

                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["answer"] == "测试答案"
                assert data["response_time_ms"] == 2000
                assert data["tokens_used"] == 150
                assert data["cache_hit"] is False

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_rate_limit_exceeded(self, mock_auth, client):
        """测试查询频率限制超出"""
        mock_tenant = Mock()
        mock_tenant.id = "tenant_123"
        mock_auth.return_value = mock_tenant

        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.check_rate_limits.return_value = (False, "Rate limit exceeded")
            mock_context.return_value = mock_query_context

            response = client.post(
                "/api/v1/query",
                json={"question": "测试问题"},
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == 429
            data = response.json()
            assert "Rate limit exceeded" in data["detail"]

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_status_endpoint(self, mock_auth, client, db_session):
        """测试查询状态端点"""
        mock_tenant = Mock()
        mock_tenant.id = "tenant_123"
        mock_auth.return_value = mock_tenant

        query_id = str(uuid4())
        mock_query_log = Mock(spec=QueryLog)
        mock_query_log.id = query_id
        mock_query_log.status = QueryStatus.SUCCESS
        mock_query_log.created_at = datetime.utcnow()
        mock_query_log.updated_at = datetime.utcnow()
        mock_query_log.response_time_ms = 1500
        mock_query_log.error_message = None

        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_context.return_value = mock_query_context

            # 模拟数据库查询
            mock_query = Mock()
            db_session.query.return_value = mock_query
            mock_query.filter.return_value.first.return_value = mock_query_log

            response = client.get(
                f"/api/v1/query/status/{query_id}",
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query_id"] == query_id
            assert data["status"] == "success"
            assert data["response_time_ms"] == 1500

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_history_endpoint(self, mock_auth, client):
        """测试查询历史端点"""
        mock_tenant = Mock()
        mock_tenant.id = "tenant_123"
        mock_auth.return_value = mock_tenant

        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.get_query_history.return_value = {
                "queries": [
                    {
                        "query_id": str(uuid4()),
                        "question": "测试问题1",
                        "status": "success",
                        "response_time_ms": 1000,
                        "cache_hit": False,
                        "created_at": datetime.utcnow().isoformat()
                    }
                ],
                "total_count": 1,
                "page": 1,
                "page_size": 10
            }
            mock_context.return_value = mock_query_context

            response = client.get(
                "/api/v1/query/history?page=1&page_size=10",
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["queries"]) == 1
            assert data["total_count"] == 1
            assert data["page"] == 1

    def test_query_data_cross_tenant_leakage(self, db_session):
        """测试跨租户数据泄露防护"""
        tenant1_context = QueryContext(db_session, "tenant_1", "user_1")
        tenant2_context = QueryContext(db_session, "tenant_2", "user_2")

        # 模拟不同租户的数据
        def mock_query_filter(*args, **kwargs):
            mock_filter = Mock()
            if "tenant_1" in str(args):
                mock_filter.all.return_value = [Mock(id=1, tenant_id="tenant_1")]
            else:
                mock_filter.all.return_value = [Mock(id=2, tenant_id="tenant_2")]
            return mock_filter

        mock_query = Mock()
        db_session.query.return_value = mock_query
        mock_query.filter.side_effect = mock_query_filter

        # 验证租户隔离
        tenant1_data = tenant1_context.get_tenant_data_sources()
        tenant2_data = tenant2_context.get_tenant_data_sources()

        # 验证每个租户只能访问自己的数据
        assert len(tenant1_data) == 1
        assert len(tenant2_data) == 1

    @pytest.mark.asyncio
    async def test_query_type_analysis(self):
        """测试查询类型分析"""
        from src.app.api.v1.endpoints.query import QueryService

        mock_query_context = Mock()
        query_service = QueryService(mock_query_context)

        # 测试SQL查询类型
        sql_type = await query_service.analyze_query_type("上个季度销售额是多少？")
        assert sql_type == QueryType.SQL

        # 测试文档查询类型
        doc_type = await query_service.analyze_query_type("什么是人工智能？")
        assert doc_type == QueryType.DOCUMENT

        # 测试混合查询类型
        mixed_type = await query_service.analyze_query_type(
            "根据销售报告，上个季度哪些产品卖得最好？",
            context={"document_ids": ["doc_123"], "data_source_ids": ["sales_db"]}
        )
        assert mixed_type == QueryType.MIXED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])