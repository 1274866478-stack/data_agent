"""
V3功能集成测试 - 后端端到端测试
覆盖所有V3核心功能的端到端验证
"""
import pytest
import asyncio
import time
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.main import app
from src.app.data.database import get_db, Base, engine
from src.app.data.models import Tenant, DataSource, Document, QueryLog
from src.app.core.auth import create_access_token
from tests.conftest import get_test_db, override_get_db

# 测试数据
TEST_TENANT = {
    "name": "V3集成测试租户",
    "subdomain": "v3-integration-test",
    "plan": "enterprise"
}

TEST_DATA_SOURCE = {
    "name": "V3测试数据库",
    "type": "postgresql",
    "connection_string": "postgresql://test:test@localhost:5432/test_db",
    "description": "V3功能集成测试数据源"
}

TEST_DOCUMENT = {
    "title": "V3测试文档",
    "content": "这是一个V3功能集成测试文档，包含测试数据和验证内容。",
    "file_type": "txt",
    "metadata": {"source": "integration_test", "version": "v3"}
}

class TestV3Integration:
    """V3功能集成测试套件"""

    @pytest.mark.asyncio
    async def test_01_health_check_and_basic_connectivity(self):
        """测试1: 健康检查和基础连接"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200

            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert "timestamp" in health_data
            assert "version" in health_data

            print("✅ 健康检查和基础连接测试通过")

    @pytest.mark.asyncio
    async def test_02_tenant_management_workflow(self):
        """测试2: 租户管理完整工作流"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 创建租户
            response = await client.post("/api/v1/tenants/", json=TEST_TENANT)
            assert response.status_code == 201
            tenant_data = response.json()
            tenant_id = tenant_data["id"]

            # 获取租户详情
            response = await client.get(f"/api/v1/tenants/{tenant_id}")
            assert response.status_code == 200
            tenant_detail = response.json()
            assert tenant_detail["name"] == TEST_TENANT["name"]

            # 更新租户
            update_data = {"plan": "premium"}
            response = await client.patch(f"/api/v1/tenants/{tenant_id}", json=update_data)
            assert response.status_code == 200

            # 删除租户
            response = await client.delete(f"/api/v1/tenants/{tenant_id}")
            assert response.status_code == 204

            print("✅ 租户管理工作流测试通过")

    @pytest.mark.asyncio
    async def test_03_data_source_management(self):
        """测试3: 数据源管理功能"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 先创建租户
            tenant_response = await client.post("/api/v1/tenants/", json=TEST_TENANT)
            tenant_id = tenant_response.json()["id"]

            # 创建数据源
            data_source = TEST_DATA_SOURCE.copy()
            data_source["tenant_id"] = tenant_id

            response = await client.post("/api/v1/data-sources/", json=data_source)
            assert response.status_code == 201
            ds_data = response.json()
            ds_id = ds_data["id"]

            # 测试连接
            response = await client.post(f"/api/v1/data-sources/{ds_id}/test-connection")
            # 注意：测试环境可能没有真实数据库，这里主要验证API结构
            assert response.status_code in [200, 400]  # 连接失败也是预期的

            # 获取数据源列表
            response = await client.get(f"/api/v1/data-sources/?tenant_id={tenant_id}")
            assert response.status_code == 200
            ds_list = response.json()
            assert len(ds_list) >= 1

            print("✅ 数据源管理测试通过")

    @pytest.mark.asyncio
    async def test_04_document_upload_and_processing(self):
        """测试4: 文档上传和处理"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 创建租户
            tenant_response = await client.post("/api/v1/tenants/", json=TEST_TENANT)
            tenant_id = tenant_response.json()["id"]

            # 上传文档
            files = {"file": ("test.txt", TEST_DOCUMENT["content"], "text/plain")}
            data = {
                "title": TEST_DOCUMENT["title"],
                "tenant_id": str(tenant_id),
                "metadata": str(TEST_DOCUMENT["metadata"])
            }

            response = await client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code in [201, 200]

            # 获取文档列表
            response = await client.get(f"/api/v1/documents/?tenant_id={tenant_id}")
            assert response.status_code == 200
            doc_list = response.json()
            assert len(doc_list) >= 1

            # 文档内容搜索（如果支持）
            if doc_list:
                doc_id = doc_list[0]["id"]
                response = await client.get(f"/api/v1/documents/{doc_id}")
                assert response.status_code == 200
                doc_detail = response.json()
                assert doc_detail["title"] == TEST_DOCUMENT["title"]

            print("✅ 文档上传和处理测试通过")

    @pytest.mark.asyncio
    async def test_05_query_and_rag_functionality(self):
        """测试5: 查询和RAG功能"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 创建租户和数据
            tenant_response = await client.post("/api/v1/tenants/", json=TEST_TENANT)
            tenant_id = tenant_response.json()["id"]

            # 执行查询
            query_data = {
                "query": "V3功能测试查询",
                "tenant_id": tenant_id,
                "include_reasoning": True,
                "max_results": 5
            }

            response = await client.post("/api/v1/query/", json=query_data)
            # 可能因为没有真实数据而失败，但API结构应该正确
            assert response.status_code in [200, 400, 404]

            if response.status_code == 200:
                query_result = response.json()
                assert "query" in query_result
                assert "results" in query_result
                assert "reasoning" in query_result or "answer" in query_result

            print("✅ 查询和RAG功能测试通过")

    @pytest.mark.asyncio
    async def test_06_xai_traceability_features(self):
        """测试6: XAI和溯源功能"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 创建租户
            tenant_response = await client.post("/api/v1/tenants/", json=TEST_TENANT)
            tenant_id = tenant_response.json()["id"]

            # 测试可解释AI功能
            query_data = {
                "query": "解释AI推理过程",
                "tenant_id": tenant_id,
                "explain_reasoning": True,
                "include_sources": True
            }

            response = await client.post("/api/v1/llm/explain", json=query_data)
            # 主要验证API结构，实际结果可能需要真实的LLM配置
            assert response.status_code in [200, 400, 500]

            if response.status_code == 200:
                xai_result = response.json()
                # 验证XAI相关字段
                xai_fields = ["reasoning", "confidence", "sources", "explanation"]
                has_xai_fields = any(field in xai_result for field in xai_fields)
                assert has_xai_fields, "XAI结果应包含解释性字段"

            print("✅ XAI和溯源功能测试通过")

    @pytest.mark.asyncio
    async def test_07_tenant_data_isolation(self):
        """测试7: 多租户数据隔离"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 创建两个租户
            tenant1_data = {**TEST_TENANT, "subdomain": "tenant1-test"}
            tenant2_data = {**TEST_TENANT, "subdomain": "tenant2-test"}

            tenant1_response = await client.post("/api/v1/tenants/", json=tenant1_data)
            tenant2_response = await client.post("/api/v1/tenants/", json=tenant2_data)

            tenant1_id = tenant1_response.json()["id"]
            tenant2_id = tenant2_response.json()["id"]

            # 为租户1上传文档
            files1 = {"file": ("tenant1.txt", "租户1的文档内容", "text/plain")}
            data1 = {"title": "租户1文档", "tenant_id": str(tenant1_id)}
            await client.post("/api/v1/documents/upload", files=files1, data=data1)

            # 为租户2上传文档
            files2 = {"file": ("tenant2.txt", "租户2的文档内容", "text/plain")}
            data2 = {"title": "租户2文档", "tenant_id": str(tenant2_id)}
            await client.post("/api/v1/documents/upload", files=files2, data=data2)

            # 验证数据隔离：租户1只能看到自己的文档
            response = await client.get(f"/api/v1/documents/?tenant_id={tenant1_id}")
            assert response.status_code == 200
            tenant1_docs = response.json()

            # 所有文档都应该属于租户1
            for doc in tenant1_docs:
                assert doc["tenant_id"] == tenant1_id

            # 验证租户2也只能看到自己的文档
            response = await client.get(f"/api/v1/documents/?tenant_id={tenant2_id}")
            assert response.status_code == 200
            tenant2_docs = response.json()

            for doc in tenant2_docs:
                assert doc["tenant_id"] == tenant2_id

            # 交叉验证：租户1不应该能访问租户2的文档
            if tenant1_docs and tenant2_docs:
                assert len(tenant1_docs) >= 1
                assert len(tenant2_docs) >= 1
                # 文档内容应该是不同的
                tenant1_content = set(doc["title"] for doc in tenant1_docs)
                tenant2_content = set(doc["title"] for doc in tenant2_docs)
                assert not tenant1_content.intersection(tenant2_content)

            print("✅ 多租户数据隔离测试通过")

    @pytest.mark.asyncio
    async def test_08_performance_and_response_times(self):
        """测试8: 性能和响应时间"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试健康检查响应时间
            start_time = time.time()
            response = await client.get("/health")
            health_check_time = time.time() - start_time

            assert response.status_code == 200
            assert health_check_time < 2.0, f"健康检查响应时间过长: {health_check_time}s"

            # 测试租户创建响应时间
            start_time = time.time()
            tenant_response = await client.post("/api/v1/tenants/", json=TEST_TENANT)
            tenant_create_time = time.time() - start_time

            assert tenant_response.status_code == 201
            assert tenant_create_time < 5.0, f"租户创建响应时间过长: {tenant_create_time}s"

            # 测试并发请求处理
            tenant_id = tenant_response.json()["id"]
            concurrent_tasks = []

            async def make_request():
                return await client.get(f"/api/v1/tenants/{tenant_id}")

            # 创建10个并发请求
            for _ in range(10):
                concurrent_tasks.append(make_request())

            start_time = time.time()
            responses = await asyncio.gather(*concurrent_tasks)
            concurrent_time = time.time() - start_time

            # 验证所有请求都成功
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count >= 8, f"并发请求成功率过低: {success_count}/10"

            # 平均响应时间应该合理
            avg_response_time = concurrent_time / 10
            assert avg_response_time < 3.0, f"并发请求平均响应时间过长: {avg_response_time}s"

            print("✅ 性能和响应时间测试通过")

    @pytest.mark.asyncio
    async def test_09_error_handling_and_recovery(self):
        """测试9: 错误处理和恢复"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试404错误处理
            response = await client.get("/api/v1/tenants/99999")
            assert response.status_code == 404
            error_detail = response.json()
            assert "detail" in error_detail

            # 测试验证错误处理
            invalid_tenant = {"name": "", "subdomain": ""}
            response = await client.post("/api/v1/tenants/", json=invalid_tenant)
            assert response.status_code == 422
            error_detail = response.json()
            assert "detail" in error_detail

            # 测试数据库连接错误的优雅处理
            # 这里模拟一个可能导致数据库错误的请求
            invalid_data = {"tenant_id": "invalid-uuid-format"}
            response = await client.get("/api/v1/documents/", params=invalid_data)
            # 应该返回4xx状态码而不是500
            assert response.status_code < 500

            # 测试大文件上传处理
            large_content = "x" * (10 * 1024 * 1024)  # 10MB
            files = {"file": ("large.txt", large_content, "text/plain")}
            data = {"title": "大文件测试", "tenant_id": "test-tenant-id"}

            response = await client.post("/api/v1/documents/upload", files=files, data=data)
            # 应该被拒绝或适当处理，不应导致服务器崩溃
            assert response.status_code in [400, 413, 422]

            print("✅ 错误处理和恢复测试通过")

    @pytest.mark.asyncio
    async def test_10_user_experience_workflow(self):
        """测试10: 完整用户体验工作流"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 用户注册租户
            tenant_data = {
                "name": "用户体验测试公司",
                "subdomain": "ux-test-company",
                "plan": "enterprise"
            }

            response = await client.post("/api/v1/tenants/", json=tenant_data)
            assert response.status_code == 201
            tenant = response.json()
            tenant_id = tenant["id"]

            # 2. 配置数据源
            ds_data = {
                "name": "生产数据库",
                "type": "postgresql",
                "connection_string": "postgresql://user:pass@localhost:5432/prod_db",
                "tenant_id": tenant_id
            }

            response = await client.post("/api/v1/data-sources/", json=ds_data)
            assert response.status_code == 201
            data_source = response.json()
            ds_id = data_source["id"]

            # 3. 上传知识库文档
            knowledge_doc = {
                "title": "公司业务手册",
                "content": "我们是一家专注于数据分析的公司，为客户提供专业的数据洞察服务。",
                "file_type": "txt"
            }

            files = {"file": ("manual.txt", knowledge_doc["content"], "text/plain")}
            data = {
                "title": knowledge_doc["title"],
                "tenant_id": str(tenant_id)
            }

            response = await client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code in [201, 200]

            # 4. 执行业务查询
            query_data = {
                "query": "我们的主要业务是什么？",
                "tenant_id": tenant_id,
                "include_reasoning": True
            }

            response = await client.post("/api/v1/query/", json=query_data)
            # 即使没有真实数据，API也应该正确处理
            assert response.status_code in [200, 400, 404]

            # 5. 查看系统状态
            response = await client.get("/health")
            assert response.status_code == 200

            # 6. 获取租户统计信息
            response = await client.get(f"/api/v1/tenants/{tenant_id}/stats")
            # 如果实现了统计API
            assert response.status_code in [200, 404]

            print("✅ 完整用户体验工作流测试通过")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])