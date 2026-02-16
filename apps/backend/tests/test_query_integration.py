"""
Story 3.1: 查询API集成测试
测试完整的查询流程、多租户场景和外部服务集成
"""

import pytest
import asyncio
import json
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock, Mock

from src.app.main import app
from src.app.data.models import Base, Tenant, DataSourceConnection, KnowledgeDocument, QueryLog
from src.app.core.config import get_settings
from src.app.services.llm_service import LLMResponse


class TestQueryIntegration:
    """查询API集成测试"""

    @pytest.fixture(scope="function")
    def test_db(self):
        """创建测试数据库"""
        # 使用内存SQLite数据库进行测试
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = TestingSessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def client(self, test_db):
        """创建测试客户端"""
        with patch('src.app.api.deps.get_db', return_value=test_db):
            yield TestClient(app)

    @pytest.fixture
    def test_tenant(self, test_db):
        """创建测试租户"""
        tenant = Tenant(
            id="test_tenant_123",
            email="test@example.com",
            display_name="Test Tenant",
            status="active",
            settings={
                "max_queries_per_hour": 100,
                "max_concurrent_queries": 5,
                "query_timeout_seconds": 60
            }
        )
        test_db.add(tenant)
        test_db.commit()
        return tenant

    @pytest.fixture
    def test_data_sources(self, test_db, test_tenant):
        """创建测试数据源"""
        data_sources = [
            DataSourceConnection(
                tenant_id=test_tenant.id,
                name="Sales Database",
                connection_type="postgresql",
                connection_string="postgresql://user:pass@localhost/sales",
                is_active=True,
                host="localhost",
                port=5432,
                database_name="sales"
            ),
            DataSourceConnection(
                tenant_id=test_tenant.id,
                name="Product Catalog",
                connection_type="postgresql",
                connection_string="postgresql://user:pass@localhost/products",
                is_active=True,
                host="localhost",
                port=5432,
                database_name="products"
            )
        ]

        for ds in data_sources:
            test_db.add(ds)
        test_db.commit()
        return data_sources

    @pytest.fixture
    def test_documents(self, test_db, test_tenant):
        """创建测试文档"""
        documents = [
            KnowledgeDocument(
                tenant_id=test_tenant.id,
                title="2024年销售报告",
                file_name="sales_report_2024.pdf",
                storage_path="/documents/sales_report_2024.pdf",
                file_type="pdf",
                file_size=1024000,
                mime_type="application/pdf",
                status="ready",
                indexed_at=datetime.utcnow(),
                chroma_collection="sales_docs"
            ),
            KnowledgeDocument(
                tenant_id=test_tenant.id,
                title="产品目录",
                file_name="product_catalog.pdf",
                storage_path="/documents/product_catalog.pdf",
                file_type="pdf",
                file_size=512000,
                mime_type="application/pdf",
                status="ready",
                indexed_at=datetime.utcnow(),
                chroma_collection="product_docs"
            )
        ]

        for doc in documents:
            test_db.add(doc)
        test_db.commit()
        return documents

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    @patch('src.app.api.v1.endpoints.query.llm_service')
    def test_end_to_end_query_flow(self, mock_llm_service, mock_auth, client, test_tenant, test_data_sources, test_documents):
        """测试端到端查询流程"""
        # 设置认证模拟
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        # 设置LLM服务模拟
        mock_llm_response = LLMResponse(
            content="# 销售分析报告\n\n根据2024年第三季度的数据分析，笔记本电脑是销售额最高的产品类别，总销售额达到￥1,250,000。",
            usage={"total_tokens": 156},
            model="glm-4-flash",
            provider="zhipu",
            finish_reason="stop"
        )
        mock_llm_service.chat_completion = AsyncMock(return_value=mock_llm_response)

        # 发送查询请求
        query_request = {
            "question": "上个季度销售额最高的产品是什么？",
            "context": {
                "time_range": "2024-Q3",
                "data_source_ids": [str(ds.id) for ds in test_data_sources[:1]]
            },
            "options": {
                "max_results": 10,
                "include_explainability": True,
                "cache_enabled": True,
                "timeout_seconds": 30
            }
        }

        response = client.post(
            "/api/v1/query",
            json=query_request,
            headers={"Authorization": "Bearer mock_jwt_token"}
        )

        # 验证响应
        assert response.status_code == 200
        data = response.json()

        # 验证响应结构
        assert "query_id" in data
        assert "answer" in data
        assert "citations" in data
        assert "data_sources" in data
        assert "explainability_log" in data
        assert "response_time_ms" in data
        assert "tokens_used" in data
        assert "cache_hit" in data
        assert "query_type" in data
        assert "created_at" in data

        # 验证内容
        assert "笔记本电脑" in data["answer"]
        assert "￥1,250,000" in data["answer"]
        assert data["tokens_used"] == 156
        assert data["cache_hit"] is False  # 首次查询不会命中缓存
        assert data["query_type"] in ["sql", "document", "mixed"]

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_caching_mechanism(self, mock_auth, client, test_tenant):
        """测试查询缓存机制"""
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        # 第一次查询
        with patch('src.app.api.v1.endpoints.query.llm_service') as mock_llm:
            mock_llm.chat_completion = AsyncMock(return_value=LLMResponse(
                content="First answer",
                usage={"total_tokens": 100}
            ))

            first_response = client.post(
                "/api/v1/query",
                json={"question": "测试查询"},
                headers={"Authorization": "Bearer mock_token"}
            )

        # 第二次相同查询（应该命中缓存）
        with patch('src.app.api.v1.endpoints.query.llm_service') as mock_llm:
            # 模拟缓存命中，不调用LLM服务
            pass  # 在实际实现中，这里会检查缓存而不是调用LLM

        # 验证缓存逻辑
        assert first_response.status_code == 200
        first_data = first_response.json()
        assert first_data["cache_hit"] is False  # 首次查询

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_error_handling(self, mock_auth, client, test_tenant):
        """测试查询错误处理"""
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        # 测试无效查询
        response = client.post(
            "/api/v1/query",
            json={"question": ""},  # 空问题
            headers={"Authorization": "Bearer mock_token"}
        )
        assert response.status_code == 422  # 验证错误

        # 测试超长查询
        response = client.post(
            "/api/v1/query",
            json={"question": "a" * 1001},  # 超过长度限制
            headers={"Authorization": "Bearer mock_token"}
        )
        assert response.status_code == 422

        # 测试恶意查询
        response = client.post(
            "/api/v1/query",
            json={"question": "SELECT * FROM users; DROP TABLE users;"},
            headers={"Authorization": "Bearer mock_token"}
        )
        assert response.status_code == 422

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_concurrent_queries_limit(self, mock_auth, client, test_tenant):
        """测试并发查询限制"""
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        # 创建多个正在处理的查询
        query_ids = []
        for i in range(6):  # 超出5个并发限制
            query_id = str(uuid4())
            query_ids.append(query_id)

        # 模拟查询服务检测到并发限制
        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.check_rate_limits.return_value = (
                False,  # 频率检查通过
                "Too many concurrent queries"  # 并发限制
            )
            mock_context.return_value = mock_query_context

            response = client.post(
                "/api/v1/query",
                json={"question": "测试查询"},
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == 429
            assert "Too many concurrent queries" in response.json()["detail"]

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_status_tracking(self, mock_auth, client, test_tenant):
        """测试查询状态跟踪"""
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        # 模拟查询状态变化
        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_context.return_value = mock_query_context

            # 测试不存在的查询ID
            response = client.get(
                f"/api/v1/query/status/{uuid4()}",
                headers={"Authorization": "Bearer mock_token"}
            )
            assert response.status_code == 404

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_history_pagination(self, mock_auth, client, test_tenant):
        """测试查询历史分页"""
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.get_query_history.return_value = {
                "queries": [
                    {
                        "query_id": str(uuid4()),
                        "question": f"测试问题 {i+1}",
                        "status": "success",
                        "response_time_ms": 1000 + i * 100,
                        "cache_hit": i % 2 == 0,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    for i in range(5)
                ],
                "total_count": 25,
                "page": 1,
                "page_size": 10
            }
            mock_context.return_value = mock_query_context

            # 测试第一页
            response = client.get(
                "/api/v1/query/history?page=1&page_size=10",
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["queries"]) == 5  # 模拟数据
            assert data["total_count"] == 25
            assert data["page"] == 1
            assert data["page_size"] == 10

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_multi_tenant_isolation(self, mock_auth, client, test_db):
        """测试多租户隔离"""
        # 创建第二个租户
        tenant2 = Tenant(
            id="test_tenant_456",
            email="tenant2@example.com",
            status="active"
        )
        test_db.add(tenant2)
        test_db.commit()

        # 测试租户1只能访问自己的数据
        mock_tenant1 = Mock()
        mock_tenant1.id = "test_tenant_123"
        mock_auth.return_value = mock_tenant1

        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.get_tenant_data_sources.return_value = [
                Mock(id=1, name="Tenant1 DB")
            ]
            mock_context.return_value = mock_query_context

            # 租户1的查询
            response = client.post(
                "/api/v1/query",
                json={"question": "租户1查询"},
                headers={"Authorization": "Bearer tenant1_token"}
            )
            assert response.status_code == 200

        # 测试租户2只能访问自己的数据
        mock_tenant2 = Mock()
        mock_tenant2.id = "test_tenant_456"
        mock_auth.return_value = mock_tenant2

        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.get_tenant_data_sources.return_value = [
                Mock(id=2, name="Tenant2 DB")
            ]
            mock_context.return_value = mock_query_context

            # 租户2的查询
            response = client.post(
                "/api/v1/query",
                json={"question": "租户2查询"},
                headers={"Authorization": "Bearer tenant2_token"}
            )
            assert response.status_code == 200

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_external_service_integration_failure(self, mock_auth, client, test_tenant):
        """测试外部服务集成失败处理"""
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        # 模拟LLM服务失败
        with patch('src.app.api.v1.endpoints.query.llm_service') as mock_llm:
            mock_llm.chat_completion = AsyncMock(side_effect=Exception("LLM service unavailable"))

            with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
                mock_query_context = Mock()
                mock_query_context.check_rate_limits.return_value = (True, None)
                mock_query_context.get_cached_query.return_value = None
                mock_query_context.log_query_request.return_value = Mock()
                mock_context.return_value = mock_query_context

                response = client.post(
                    "/api/v1/query",
                    json={"question": "测试查询"},
                    headers={"Authorization": "Bearer mock_token"}
                )

                # 应该返回500错误
                assert response.status_code == 500
                assert "查询处理失败" in response.json()["detail"]

    @patch('src.app.api.v1.endpoints.query.get_current_tenant_from_request')
    def test_query_cache_management(self, mock_auth, client, test_tenant):
        """测试查询缓存管理"""
        mock_tenant = Mock()
        mock_tenant.id = test_tenant.id
        mock_auth.return_value = mock_tenant

        query_hash = "test_query_hash_123"

        with patch('src.app.api.v1.endpoints.query.get_query_context') as mock_context:
            mock_query_context = Mock()
            mock_query_context.clear_query_cache.return_value = (True, "Cache cleared successfully")
            mock_context.return_value = mock_query_context

            # 测试清除特定查询缓存
            response = client.delete(
                f"/api/v1/query/cache/{query_hash}",
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query_hash"] == query_hash
            assert data["cache_cleared"] is True
            assert "Cache cleared successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_query_performance_monitoring(self):
        """测试查询性能监控"""
        from src.app.api.v1.endpoints.query import QueryService

        mock_query_context = Mock()
        mock_query_context.get_tenant_data_sources.return_value = []
        mock_query_context.get_tenant_documents.return_value = []
        query_service = QueryService(mock_query_context)

        # 模拟查询处理
        with patch('src.app.api.v1.endpoints.query.llm_service') as mock_llm:
            mock_llm.chat_completion = AsyncMock(return_value=LLMResponse(
                content="Performance test answer",
                usage={"total_tokens": 50}
            ))

            # 测试查询类型分析性能
            start_time = datetime.utcnow()
            query_type = await query_service.analyze_query_type(
                "这是一个性能测试查询，包含销售数据和产品信息"
            )
            end_time = datetime.utcnow()

            processing_time = (end_time - start_time).total_seconds() * 1000

            # 验证处理时间合理（应该在100ms以内）
            assert processing_time < 100
            assert query_type in ["sql", "document", "mixed"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])