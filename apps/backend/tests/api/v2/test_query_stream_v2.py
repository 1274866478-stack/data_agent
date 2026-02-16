# -*- coding: utf-8 -*-
"""
V2 流式查询端点测试
==================

测试 /api/v2/query/stream 端点的功能。

作者: BMad Master
版本: 2.0.0
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.src.app.main import app


class TestQueryStreamV2:
    """V2 流式查询端点测试类"""

    @pytest.fixture
    async def client(self) -> AsyncClient:
        """创建测试客户端"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_stream_health_check(self, client: AsyncClient):
        """测试流式端点健康检查"""
        response = await client.get("/api/v2/query/stream/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert data["streaming"] == "enabled"
        assert data["protocol"] == "Server-Sent Events (SSE)"

    @pytest.mark.asyncio
    async def test_stream_query_basic(self, client: AsyncClient):
        """测试基本流式查询"""
        query = "How many users exist?"

        response = await client.post(
            "/api/v2/query/stream",
            json={"query": query},
            params={"tenant_id": "default_tenant"},
            timeout=180.0
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_stream_query_events(self, client: AsyncClient):
        """测试流式事件结构"""
        query = "Count all records"

        response = await client.post(
            "/api/v2/query/stream",
            json={"query": query},
            params={"tenant_id": "default_tenant"},
        )

        assert response.status_code == 200

        # 读取响应内容
        content = response.text
        assert "event: start" in content
        assert "event: step" in content
        assert "event: progress" in content
        assert "event: done" in content

    @pytest.mark.asyncio
    async def test_stream_query_with_session(self, client: AsyncClient):
        """测试带会话ID的流式查询"""
        query = "What is the total revenue?"
        session_id = "test_session_123"

        response = await client.post(
            "/api/v2/query/stream",
            json={"query": query, "session_id": session_id},
            params={"tenant_id": "default_tenant"},
        )

        assert response.status_code == 200
        # 验证响应是 SSE 格式
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_stream_query_max_results(self, client: AsyncClient):
        """测试 max_results 参数"""
        query = "List all products"
        max_results = 50

        response = await client.post(
            "/api/v2/query/stream",
            json={
                "query": query,
                "max_results": max_results,
            },
            params={"tenant_id": "default_tenant"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_query_validation_error(self, client: AsyncClient):
        """测试输入验证"""
        # 发送无效请求（空查询）
        response = await client.post(
            "/api/v2/query/stream",
            json={"query": ""},  # 空查询应该被验证拒绝
            params={"tenant_id": "default_tenant"},
        )

        # 空查询应该被 Pydantic 验证拒绝
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_stream_query_too_long_query(self, client: AsyncClient):
        """测试超长查询"""
        # 创建一个非常长的查询
        long_query = "Show me " + "data " * 1000 + "please"

        response = await client.post(
            "/api/v2/query/stream",
            json={"query": long_query},
            params={"tenant_id": "default_tenant"},
        )

        # 应该正常处理或返回适当错误
        assert response.status_code in [200, 413, 422]  # OK, Payload Too Large, 或 Validation Error

    @pytest.mark.asyncio
    async def test_stream_query_special_characters(self, client: AsyncClient):
        """测试特殊字符处理"""
        special_queries = [
            "Show me users with name containing 'O'Reilly'",
            "Display data with \"quotes\" and \\backslashes\\",
            "Query for <script>alert('xss')</script>",
        ]

        for query in special_queries:
            response = await client.post(
                "/api/v2/query/stream",
                json={"query": query},
                params={"tenant_id": "default_tenant"},
            )

            # 应该正确处理或清理特殊字符
            assert response.status_code in [200, 400, 422]


class TestStreamSessionManagement:
    """V2 流式会话管理端点测试类"""

    @pytest.fixture
    async def client(self) -> AsyncClient:
        """创建测试客户端"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, client: AsyncClient):
        """测试获取不存在的会话"""
        response = await client.get("/api/v2/query/stream/session/nonexistent_session")

        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data.get("detail", "")

    @pytest.mark.asyncio
    async def test_pause_nonexistent_session(self, client: AsyncClient):
        """测试暂停不存在的会话"""
        response = await client.post("/api/v2/query/stream/session/nonexistent_session/pause")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resume_nonexistent_session(self, client: AsyncClient):
        """测试恢复不存在的会话"""
        response = await client.post("/api/v2/query/stream/session/nonexistent_session/resume")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_session(self, client: AsyncClient):
        """测试取消不存在的会话"""
        response = await client.delete("/api/v2/query/stream/session/nonexistent_session")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_session_id_in_start_event(self, client: AsyncClient):
        """测试 start 事件包含 session_id"""
        response = await client.post(
            "/api/v2/query/stream",
            json={"query": "test query"},
            params={"tenant_id": "default_tenant"},
        )

        assert response.status_code == 200
        content = response.text

        # 验证 start 事件包含 session_id
        assert "event: start" in content
        # session_id 应该在 start 事件的 data 中
        assert '"session_id"' in content

    @pytest.mark.asyncio
    async def test_custom_session_id(self, client: AsyncClient):
        """测试自定义会话ID"""
        custom_session_id = "my_custom_session_12345"

        response = await client.post(
            "/api/v2/query/stream",
            json={"query": "test query", "session_id": custom_session_id},
            params={"tenant_id": "default_tenant"},
        )

        assert response.status_code == 200
        content = response.text

        # 验证使用了自定义的 session_id
        assert f'"{custom_session_id}"' in content


class TestStreamEdgeCases:
    """V2 流式端点边界情况测试类"""

    @pytest.fixture
    async def client(self) -> AsyncClient:
        """创建测试客户端"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_session(self, client: AsyncClient):
        """测试同一会话的并发请求"""
        import asyncio

        session_id = "concurrent_test_session"

        # 发送两个使用相同 session_id 的并发请求
        async def make_request():
            return await client.post(
                "/api/v2/query/stream",
                json={"query": "test", "session_id": session_id},
                params={"tenant_id": "default_tenant"},
            )

        results = await asyncio.gather(make_request(), make_request())
        # 两个请求都应该成功（虽然会互相覆盖会话状态）
        for response in results:
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_zero_max_results(self, client: AsyncClient):
        """测试 max_results 边界值"""
        response = await client.post(
            "/api/v2/query/stream",
            json={"query": "test", "max_results": 0},
            params={"tenant_id": "default_tenant"},
        )

        # max_results 应该有最小值限制（1）
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_max_results_boundary(self, client: AsyncClient):
        """测试 max_results 边界值"""
        # 测试最大允许值
        response = await client.post(
            "/api/v2/query/stream",
            json={"query": "test", "max_results": 1000},
            params={"tenant_id": "default_tenant"},
        )
        assert response.status_code == 200

        # 测试超过最大值
        response = await client.post(
            "/api/v2/query/stream",
            json={"query": "test", "max_results": 1001},
            params={"tenant_id": "default_tenant"},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_unicode_query(self, client: AsyncClient):
        """测试 Unicode 字符"""
        unicode_queries = [
            "显示中文查询结果",
            "Показать результаты на русском",
            "Afficher les résultats en français",
            "🎨🎭 Emoji test 🚀🌟",
        ]

        for query in unicode_queries:
            response = await client.post(
                "/api/v2/query/stream",
                json={"query": query},
                params={"tenant_id": "default_tenant"},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_include_chart_parameter(self, client: AsyncClient):
        """测试 include_chart 参数"""
        response = await client.post(
            "/api/v2/query/stream",
            json={"query": "test", "include_chart": True},
            params={"tenant_id": "default_tenant"},
        )

        # 参数应该被接受（即使图表功能未完全实现）
        assert response.status_code == 200


class TestStreamCacheIntegration:
    """V2 流式端点缓存集成测试类"""

    @pytest.fixture
    async def client(self) -> AsyncClient:
        """创建测试客户端"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_cache_hit_response(self, client: AsyncClient):
        """测试缓存命中时的响应格式"""
        query = "cache test query"

        # 第一次请求 - 缓存未命中
        response1 = await client.post(
            "/api/v2/query/stream",
            json={"query": query},
            params={"tenant_id": "default_tenant", "user_id": "cache_test_user"},
        )
        assert response1.status_code == 200

        # 第二次请求 - 可能缓存命中（如果缓存管理器可用）
        response2 = await client.post(
            "/api/v2/query/stream",
            json={"query": query},
            params={"tenant_id": "default_tenant", "user_id": "cache_test_user"},
        )
        assert response2.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
