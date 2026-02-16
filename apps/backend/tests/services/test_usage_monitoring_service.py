"""
使用量监控服务测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.app.services.usage_monitoring_service import (
    usage_monitoring_service,
    UsageTracker,
    UsageLimit,
    UsageRecord,
    CostRecord,
    ProviderType,
    UsageType,
    UsageStatistics
)


class TestUsageTracker:
    """使用量跟踪器测试"""

    @pytest.fixture
    def tracker(self):
        return UsageTracker()

    @pytest.mark.asyncio
    async def test_record_usage(self, tracker):
        """测试记录使用量"""
        tenant_id = "test_tenant"
        provider = ProviderType.ZHIPU
        model = "glm-4"
        usage_type = UsageType.TOKENS
        amount = 100

        success = await tracker.record_usage(
            tenant_id=tenant_id,
            provider=provider,
            model=model,
            usage_type=usage_type,
            amount=amount
        )

        assert success is True
        assert len(tracker.records) == 1

        record = tracker.records[0]
        assert record.tenant_id == tenant_id
        assert record.provider == provider
        assert record.model == model
        assert record.usage_type == usage_type
        assert record.amount == amount

    @pytest.mark.asyncio
    async def test_record_cost(self, tracker):
        """测试记录成本"""
        tenant_id = "test_tenant"
        provider = ProviderType.ZHIPU
        model = "glm-4"
        prompt_tokens = 50
        completion_tokens = 30
        total_tokens = 80

        success = await tracker.record_cost(
            tenant_id=tenant_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        )

        assert success is True
        assert len(tracker.cost_records) == 1

        cost_record = tracker.cost_records[0]
        assert cost_record.tenant_id == tenant_id
        assert cost_record.provider == provider
        assert cost_record.model == model
        assert cost_record.prompt_tokens == prompt_tokens
        assert cost_record.completion_tokens == completion_tokens
        assert cost_record.total_tokens == total_tokens
        assert cost_record.estimated_cost > 0

    def test_calculate_cost_zhipu(self, tracker):
        """测试智谱AI成本计算"""
        provider = ProviderType.ZHIPU
        model = "glm-4"
        prompt_tokens = 1000
        completion_tokens = 500

        cost = tracker._calculate_cost(provider, model, prompt_tokens, completion_tokens)

        # 检查计算逻辑
        expected_prompt_cost = (prompt_tokens / 1000) * tracker.pricing_config[provider][model]["prompt"]
        expected_completion_cost = (completion_tokens / 1000) * tracker.pricing_config[provider][model]["completion"]
        expected_total = expected_prompt_cost + expected_completion_cost

        assert abs(cost - expected_total) < 0.0001

    def test_calculate_cost_openrouter(self, tracker):
        """测试OpenRouter成本计算"""
        provider = ProviderType.OPENROUTER
        model = "anthropic/claude-3.5-sonnet"
        prompt_tokens = 2000
        completion_tokens = 1000

        cost = tracker._calculate_cost(provider, model, prompt_tokens, completion_tokens)

        assert cost > 0
        # OpenRouter的Claude模型应该比智谱GLM-4更贵
        zhipu_cost = tracker._calculate_cost(ProviderType.ZHIPU, "glm-4", prompt_tokens, completion_tokens)
        assert cost > zhipu_cost

    def test_calculate_cost_unknown_model(self, tracker):
        """测试未知模型的成本计算"""
        provider = ProviderType.ZHIPU
        model = "unknown_model"
        prompt_tokens = 1000
        completion_tokens = 500

        cost = tracker._calculate_cost(provider, model, prompt_tokens, completion_tokens)

        # 应该使用默认价格
        assert cost > 0

    @pytest.mark.asyncio
    async def test_get_current_usage(self, tracker):
        """测试获取当前使用量"""
        tenant_id = "test_tenant"
        now = datetime.utcnow()

        # 添加不同时间的使用记录
        # 今天的使用量
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        # 昨天的使用量（不应该计入今天的统计）
        yesterday_record = CostRecord(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            estimated_cost=0.05,
            timestamp=now - timedelta(days=1)
        )
        tracker.cost_records.append(yesterday_record)

        current_usage = await tracker.get_current_usage(tenant_id)

        assert current_usage["daily_tokens"] == 150
        assert current_usage["daily_api_calls"] == 1
        assert current_usage["daily_cost"] > 0
        assert current_usage["monthly_tokens"] == 150
        assert current_usage["monthly_api_calls"] == 1
        assert current_usage["monthly_cost"] > 0

    @pytest.mark.asyncio
    async def test_get_usage_statistics_daily(self, tracker):
        """测试获取每日使用量统计"""
        tenant_id = "test_tenant"
        now = datetime.utcnow()

        # 添加今天的使用记录
        for i in range(3):
            await tracker.record_cost(
                tenant_id=tenant_id,
                provider=ProviderType.ZHIPU,
                model="glm-4",
                prompt_tokens=100 + i * 10,
                completion_tokens=50 + i * 5,
                total_tokens=150 + i * 15
            )

        stats = await tracker.get_usage_statistics(tenant_id, period="daily")

        assert isinstance(stats, UsageStatistics)
        assert stats.tenant_id == tenant_id
        assert stats.period == "daily"
        assert stats.total_tokens == 150 + 165 + 180  # 3条记录的总和
        assert stats.total_api_calls == 3
        assert stats.total_cost > 0
        assert len(stats.provider_breakdown) > 0
        assert "zhipu" in stats.provider_breakdown
        assert "glm-4" in stats.model_breakdown or "zhipu:glm-4" in stats.model_breakdown

    @pytest.mark.asyncio
    async def test_get_usage_statistics_with_provider_filter(self, tracker):
        """测试按提供商过滤的使用量统计"""
        tenant_id = "test_tenant"

        # 添加不同提供商的使用记录
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.OPENROUTER,
            model="anthropic/claude-3.5-sonnet",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300
        )

        # 获取智谱AI的统计
        zhipu_stats = await tracker.get_usage_statistics(tenant_id, provider=ProviderType.ZHIPU)
        assert zhipu_stats.total_tokens == 150
        assert len(zhipu_stats.provider_breakdown) == 1
        assert "zhipu" in zhipu_stats.provider_breakdown

        # 获取OpenRouter的统计
        openrouter_stats = await tracker.get_usage_statistics(tenant_id, provider=ProviderType.OPENROUTER)
        assert openrouter_stats.total_tokens == 300
        assert len(openrouter_stats.provider_breakdown) == 1
        assert "openrouter" in openrouter_stats.provider_breakdown

    @pytest.mark.asyncio
    async def test_check_usage_limits_within_limits(self, tracker):
        """测试检查使用量限制 - 在限制内"""
        tenant_id = "test_tenant"

        # 添加一些使用量，但不超过限制
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        can_proceed, warnings = await tracker.check_usage_limits(tenant_id, ProviderType.ZHIPU, 100)

        assert can_proceed is True
        assert isinstance(warnings, list)

    @pytest.mark.asyncio
    async def test_check_usage_limits_exceeded(self, tracker):
        """测试检查使用量限制 - 超过限制"""
        tenant_id = "test_tenant"

        # Mock一个很低的限制
        low_limit = UsageLimit(
            tenant_id=tenant_id,
            daily_token_limit=100,
            daily_api_limit=1,
            monthly_token_limit=1000,
            monthly_api_limit=10,
            cost_limit=1.0
        )

        with patch.object(tracker, '_get_usage_limit', return_value=low_limit):
            # 添加超过限制的使用量
            await tracker.record_cost(
                tenant_id=tenant_id,
                provider=ProviderType.ZHIPU,
                model="glm-4",
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300
            )

            can_proceed, warnings = await tracker.check_usage_limits(tenant_id, ProviderType.ZHIPU, 50)

            assert can_proceed is False
            assert len(warnings) > 0
            assert any("限制" in warning for warning in warnings)

    @pytest.mark.asyncio
    async def test_get_real_time_usage(self, tracker):
        """测试获取实时使用量"""
        tenant_id = "test_tenant"

        # 记录不同类型的使用量
        await tracker.record_usage(tenant_id, ProviderType.ZHIPU, "glm-4", UsageType.TOKENS, 100)
        await tracker.record_usage(tenant_id, ProviderType.ZHIPU, "glm-4", UsageType.API_CALLS, 1)
        await tracker.record_usage(tenant_id, ProviderType.OPENROUTER, "claude", UsageType.TOKENS, 200)

        real_time_usage = await tracker.get_real_time_usage(tenant_id)

        assert isinstance(real_time_usage, dict)
        assert "zhipu_glm-4_tokens" in real_time_usage
        assert "zhipu_glm-4_api_calls" in real_time_usage
        assert "openrouter_claude_tokens" in real_time_usage
        assert real_time_usage["zhipu_glm-4_tokens"] == 100
        assert real_time_usage["zhipu_glm-4_api_calls"] == 1
        assert real_time_usage["openrouter_claude_tokens"] == 200

    @pytest.mark.asyncio
    async def test_get_hourly_usage(self, tracker):
        """测试获取小时使用量"""
        tenant_id = "test_tenant"

        # 模添加小时数据
        tracker.hourly_usage[tenant_id] = [100, 150, 200, 120, 180]

        hourly_usage = await tracker.get_hourly_usage(tenant_id)

        assert hourly_usage == [100, 150, 200, 120, 180]

        # 测试限制数量
        limited_usage = await tracker.get_hourly_usage(tenant_id, hours=3)
        assert limited_usage == [150, 200, 120]

    def test_get_memory_usage(self, tracker):
        """测试获取内存使用情况"""
        # 添加一些记录
        tracker.records.append(
            UsageRecord("tenant1", ProviderType.ZHIPU, "glm-4", UsageType.TOKENS, 100)
        )
        tracker.records.append(
            UsageRecord("tenant2", ProviderType.OPENROUTER, "claude", UsageType.TOKENS, 200)
        )
        tracker.cost_records.append(
            CostRecord("tenant1", ProviderType.ZHIPU, "glm-4", 50, 25, 75, 0.01)
        )
        tracker.real_time_usage["tenant1"] = {"zhipu_tokens": 1000}

        memory_usage = tracker.get_memory_usage()

        assert isinstance(memory_usage, dict)
        assert "total_records" in memory_usage
        assert "total_cost_records" in memory_usage
        assert "active_tenants" in memory_usage
        assert "memory_estimate_mb" in memory_usage
        assert memory_usage["total_records"] == 2
        assert memory_usage["total_cost_records"] == 1
        assert memory_usage["active_tenants"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_records(self, tracker):
        """测试清理旧记录"""
        now = datetime.utcnow()

        # 添加新记录
        tracker.records.append(
            UsageRecord("tenant1", ProviderType.ZHIPU, "glm-4", UsageType.TOKENS, 100)
        )
        tracker.cost_records.append(
            CostRecord("tenant1", ProviderType.ZHIPU, "glm-4", 50, 25, 75, 0.01)
        )

        # 添加旧记录
        old_record = UsageRecord(
            "tenant2",
            ProviderType.ZHIPU,
            "glm-4",
            UsageType.TOKENS,
            200
        )
        old_record.timestamp = now - timedelta(days=35)
        tracker.records.append(old_record)

        old_cost_record = CostRecord(
            "tenant2",
            ProviderType.ZHIPU,
            "glm-4",
            100,
            50,
            150,
            0.02
        )
        old_cost_record.timestamp = now - timedelta(days=35)
        tracker.cost_records.append(old_cost_record)

        initial_record_count = len(tracker.records)
        initial_cost_count = len(tracker.cost_records)

        # 执行清理
        await tracker.cleanup_old_records(days=30)

        # 验证清理结果
        assert len(tracker.records) < initial_record_count
        assert len(tracker.cost_records) < initial_cost_count

        # 新记录应该保留
        assert any(record.tenant_id == "tenant1" for record in tracker.records)
        assert any(cost.tenant_id == "tenant1" for cost in tracker.cost_records)

    @pytest.mark.asyncio
    async def test_export_usage_data_json(self, tracker):
        """测试导出使用量数据 - JSON格式"""
        tenant_id = "test_tenant"
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()

        # 添加测试数据
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        exported_data = await tracker.export_usage_data(tenant_id, start_date, end_date, "json")

        assert exported_data is not None
        assert isinstance(exported_data, str)

        # 验证JSON格式
        import json
        data = json.loads(exported_data)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "timestamp" in data[0]
        assert "provider" in data[0]
        assert "model" in data[0]
        assert "total_tokens" in data[0]

    @pytest.mark.asyncio
    async def test_export_usage_data_csv(self, tracker):
        """测试导出使用量数据 - CSV格式"""
        tenant_id = "test_tenant"
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()

        # 添加测试数据
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        exported_data = await tracker.export_usage_data(tenant_id, start_date, end_date, "csv")

        assert exported_data is not None
        assert isinstance(exported_data, str)

        # 验证CSV格式
        lines = exported_data.split('\n')
        assert len(lines) >= 2  # 至少包含标题行和数据行
        assert "timestamp" in lines[0]
        assert "provider" in lines[0]
        assert "zhipu" in exported_data


class TestUsageMonitoringService:
    """使用量监控服务测试"""

    @pytest.fixture
    def service(self):
        return UsageMonitoringService()

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, service):
        """测试启动和停止监控"""
        # 启动监控
        await service.start_monitoring()
        assert service.monitoring_active is True

        # 停止监控
        await service.stop_monitoring()
        assert service.monitoring_active is False

    @pytest.mark.asyncio
    async def test_check_and_alert_no_alerts(self, service):
        """测试检查警告 - 无警告"""
        tenant_id = "test_tenant"

        # 模拟低使用量
        with patch.object(service.tracker, 'get_current_usage') as mock_usage:
            mock_usage.return_value = {
                "daily_tokens": 100,
                "daily_api_calls": 5,
                "monthly_cost": 5.0
            }

            with patch.object(service.tracker, '_get_usage_limit') as mock_limit:
                mock_limit.return_value = UsageLimit(
                    tenant_id=tenant_id,
                    daily_token_limit=10000,
                    daily_api_limit=100,
                    cost_limit=100.0
                )

                alerts = await service.check_and_alert(tenant_id)

                assert isinstance(alerts, list)
                # 应该没有警告或只有轻微警告
                assert len(alerts) <= 1

    @pytest.mark.asyncio
    async def test_check_and_alert_with_warnings(self, service):
        """测试检查警告 - 有警告"""
        tenant_id = "test_tenant"

        # 模拟高使用量
        with patch.object(service.tracker, 'get_current_usage') as mock_usage:
            mock_usage.return_value = {
                "daily_tokens": 8500,  # 接近10000的限制
                "daily_api_calls": 95,  # 接近100的限制
                "monthly_cost": 85.0   # 接近100的限制
            }

            with patch.object(service.tracker, '_get_usage_limit') as mock_limit:
                mock_limit.return_value = UsageLimit(
                    tenant_id=tenant_id,
                    daily_token_limit=10000,
                    daily_api_limit=100,
                    cost_limit=100.0
                )

                alerts = await service.check_and_alert(tenant_id)

                assert isinstance(alerts, list)
                # 应该有多个警告
                assert len(alerts) >= 1
                assert any("Token" in alert for alert in alerts)


class TestUsageLimit:
    """使用量限制测试"""

    def test_usage_limit_creation(self):
        """测试使用量限制创建"""
        limit = UsageLimit(
            tenant_id="test_tenant",
            daily_token_limit=50000,
            daily_api_limit=500,
            monthly_token_limit=1500000,
            monthly_api_limit=15000,
            cost_limit=50.0
        )

        assert limit.tenant_id == "test_tenant"
        assert limit.daily_token_limit == 50000
        assert limit.daily_api_limit == 500
        assert limit.monthly_token_limit == 1500000
        assert limit.monthly_api_limit == 15000
        assert limit.cost_limit == 50.0
        assert limit.active is True

    def test_usage_limit_defaults(self):
        """测试使用量限制默认值"""
        limit = UsageLimit(tenant_id="test_tenant")

        assert limit.daily_token_limit == 100000
        assert limit.daily_api_limit == 1000
        assert limit.monthly_token_limit == 3000000
        assert limit.monthly_api_limit == 30000
        assert limit.cost_limit == 100.0
        assert limit.active is True


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_usage_tracking_workflow(self):
        """测试完整的使用量跟踪工作流"""
        service = UsageMonitoringService()
        tracker = service.tracker
        tenant_id = "integration_tenant"

        # 1. 记录API调用
        await tracker.record_usage(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            usage_type=UsageType.API_CALLS,
            amount=1
        )

        # 2. 记录Token使用和成本
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=150,
            completion_tokens=75,
            total_tokens=225
        )

        # 3. 检查当前使用量
        current_usage = await tracker.get_current_usage(tenant_id)
        assert current_usage["daily_tokens"] == 225
        assert current_usage["daily_api_calls"] == 1

        # 4. 获取统计信息
        stats = await tracker.get_usage_statistics(tenant_id)
        assert stats.total_tokens == 225
        assert stats.total_api_calls == 1
        assert stats.total_cost > 0

        # 5. 获取实时使用量
        real_time = await tracker.get_real_time_usage(tenant_id)
        assert "zhipu_glm-4_tokens" in real_time

        # 6. 检查限制
        can_proceed, warnings = await tracker.check_usage_limits(tenant_id, ProviderType.ZHIPU, 100)
        assert can_proceed is True

        # 7. 检查警告
        alerts = await service.check_and_alert(tenant_id)
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_multi_provider_usage_tracking(self):
        """测试多提供商使用量跟踪"""
        tracker = UsageTracker()
        tenant_id = "multi_provider_tenant"

        # 使用智谱AI
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        # 使用OpenRouter
        await tracker.record_cost(
            tenant_id=tenant_id,
            provider=ProviderType.OPENROUTER,
            model="anthropic/claude-3.5-sonnet",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300
        )

        # 获取总体统计
        total_stats = await tracker.get_usage_statistics(tenant_id)
        assert total_stats.total_tokens == 450
        assert total_stats.total_api_calls == 2
        assert len(total_stats.provider_breakdown) == 2

        # 获取各提供商统计
        zhipu_stats = await tracker.get_usage_statistics(tenant_id, provider=ProviderType.ZHIPU)
        assert zhipu_stats.total_tokens == 150
        assert len(zhipu_stats.provider_breakdown) == 1

        openrouter_stats = await tracker.get_usage_statistics(tenant_id, provider=ProviderType.OPENROUTER)
        assert openrouter_stats.total_tokens == 300
        assert len(openrouter_stats.provider_breakdown) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])