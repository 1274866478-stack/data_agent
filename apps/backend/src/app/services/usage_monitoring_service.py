"""
# [USAGE_MONITORING_SERVICE] 使用量监控服务

## [HEADER]
**文件名**: usage_monitoring_service.py
**职责**: 监控Token使用量、API调用次数、成本计算，提供使用量限制检查和统计功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 使用量监控服务

## [INPUT]
- **tenant_id: str** - 租户ID
- **provider: ProviderType** - 提供商类型（ZHIPU, OPENROUTER, LOCAL）
- **model: str** - 模型名称
- **usage_type: UsageType** - 使用量类型（TOKENS, API_CALLS, CHARACTERS, REQUESTS, RESPONSES）
- **amount: int** - 使用量
- **prompt_tokens: int** - 提示Token数
- **completion_tokens: int** - 完成Token数
- **total_tokens: int** - 总Token数
- **requested_tokens: int** - 请求的Token数
- **period: str** - 统计周期（"daily", "weekly", "monthly"）
- **start_date: datetime** - 开始日期
- **end_date: datetime** - 结束日期
- **format: str** - 导出格式（"json", "csv"）
- **days: int** - 保留天数
- **usage_limit: UsageLimit** - 使用量限制配置
- **metadata: Optional[Dict[str, Any]]** - 元数据

## [OUTPUT]
- **bool**: 操作是否成功（record_usage, record_cost, check_usage_limits, set_usage_limit）
- **Tuple[bool, List[str]]**: (是否允许, 警告消息列表)（check_usage_limits）
- **Dict[str, Any]**: 当前使用量统计（get_current_usage）
  - daily_tokens, daily_api_calls, daily_cost
  - monthly_tokens, monthly_api_calls, monthly_cost
  - timestamp
- **UsageStatistics**: 使用量统计对象（get_usage_statistics）
- **Dict[str, Any]**: 实时使用量数据（get_real_time_usage）
- **List[int]**: 每小时使用量列表（get_hourly_usage）
- **Optional[str]**: 导出数据路径或内容（export_usage_data）
- **Dict[str, Any]**: 内存使用情况（get_memory_usage）
- **List[str]**: 警告消息列表（check_and_alert）

**上游依赖** (已读取源码):
- Python标准库: asyncio, collections（defaultdict, deque）, dataclasses, datetime, enum, json, logging, time
- 项目配置: src.app.core.config.settings

**下游依赖** (需要反向索引分析):
- [llm_service.py](./llm_service.py) - LLM服务记录使用量
- [agent_service.py](./agent_service.py) - Agent服务记录使用量

**调用方**:
- LLM服务调用时记录Token使用量和成本
- Agent服务调用时检查使用量限制
- 定期清理任务（24小时一次）

## [STATE]
- **数据结构**:
  - UsageRecord: 使用量记录（tenant_id, provider, model, usage_type, amount, timestamp, metadata）
  - CostRecord: 成本记录（prompt_tokens, completion_tokens, total_tokens, estimated_cost）
  - UsageLimit: 使用量限制（daily_token_limit, daily_api_limit, monthly_token_limit, monthly_api_limit, cost_limit）
  - UsageStatistics: 使用量统计（total_tokens, total_api_calls, total_cost, provider_breakdown, model_breakdown）
- **内存存储**: deque(maxlen=10000)保留最近10000条记录
- **实时使用量**: Dict[tenant_id, Dict[key, count]]实时统计
- **小时统计**: Dict[tenant_id, List[int]]最近24小时每小时使用量
- **Token定价**: pricing_config配置各模型价格（每1000 tokens价格）
  - ZHIPU: glm-4-flash ($0.0001/0.0002), glm-4 ($0.0005/0.001), glm-4-9b ($0.0003/0.0006)
  - OPENROUTER: gemini-2.0-flash-exp ($0.000075/0.00015), claude-3.5-sonnet ($0.0015/0.0075), gpt-4o ($0.0025/0.01)
- **成本计算**: (prompt_tokens/1000)*prompt_price + (completion_tokens/1000)*completion_price
- **限制检查**: 检查每日/每月Token限制、API调用限制、成本限制
- **警告阈值**: daily_token_usage 80%, daily_api_calls 80%, monthly_cost 90%
- **定期清理**: 24小时自动清理旧记录（默认保留30天）
- **导出格式**: JSON和CSV两种格式

## [SIDE-EFFECTS]
- **deque操作**: records.append添加记录，自动淘汰最旧记录（maxlen=10000）
- **实时统计更新**: real_time_usage[tenant_id][key] += amount
- **小时统计更新**: hourly_usage[tenant_id][-1] += amount
- **成本计算**: _calculate_cost根据模型和Token数计算成本
- **时间过滤**: datetime.utcnow()替换、today_start、month_start计算
- **列表推导式过滤**: [record for record in self.cost_records if conditions]
- **聚合计算**: sum(record.total_tokens for record in filtered_costs)
- **分组统计**: defaultdict(lambda: {"tokens": 0, "calls": 0, "cost": 0.0})按提供商/模型分组
- **JSON序列化**: json.dumps(data, indent=2, ensure_ascii=False)导出JSON
- **CSV格式化**: "\n".join(lines)生成CSV字符串
- **内存估算**: (len(records)*200 + len(cost_records)*300 + ...) / (1024*1024)
- **deque清理**: deque((record for record in self.records if record.timestamp >= cutoff_date), maxlen=10000)
- **全局单例**: usage_monitoring_service全局实例
- **异步任务**: asyncio.create_task(self._periodic_cleanup())启动定期清理

## [POS]
**路径**: backend/src/app/services/usage_monitoring_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 外部依赖无，依赖项目配置settings
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from collections import defaultdict, deque

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class UsageType(Enum):
    """使用量类型枚举"""
    TOKENS = "tokens"
    API_CALLS = "api_calls"
    CHARACTERS = "characters"
    REQUESTS = "requests"
    RESPONSES = "responses"


class ProviderType(Enum):
    """提供商类型枚举"""
    ZHIPU = "zhipu"
    OPENROUTER = "openrouter"
    LOCAL = "local"


@dataclass
class UsageRecord:
    """使用量记录"""
    tenant_id: str
    provider: ProviderType
    model: str
    usage_type: UsageType
    amount: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostRecord:
    """成本记录"""
    tenant_id: str
    provider: ProviderType
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageLimit:
    """使用量限制"""
    tenant_id: str
    provider: Optional[ProviderType] = None
    daily_token_limit: int = 100000
    daily_api_limit: int = 1000
    monthly_token_limit: int = 3000000
    monthly_api_limit: int = 30000
    cost_limit: float = 100.0
    active: bool = True


@dataclass
class UsageStatistics:
    """使用量统计"""
    tenant_id: str
    period: str  # "daily", "weekly", "monthly"
    total_tokens: int = 0
    total_api_calls: int = 0
    total_cost: float = 0.0
    provider_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    model_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class UsageTracker:
    """使用量跟踪器"""

    def __init__(self):
        self.records: deque = deque(maxlen=10000)  # 内存中保留最近10000条记录
        self.cost_records: deque = deque(maxlen=10000)
        self.real_time_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.hourly_usage: Dict[str, List[int]] = defaultdict(list)  # 最近24小时的每小时使用量

        # Token定价配置（示例价格，实际应根据API提供商定价调整）
        self.pricing_config = {
            ProviderType.ZHIPU: {
                "glm-4-flash": {"prompt": 0.0001, "completion": 0.0002},  # 每1000 tokens的价格
                "glm-4": {"prompt": 0.0005, "completion": 0.001},
                "glm-4-9b": {"prompt": 0.0003, "completion": 0.0006}
            },
            ProviderType.OPENROUTER: {
                "google/gemini-2.0-flash-exp": {"prompt": 0.000075, "completion": 0.00015},
                "anthropic/claude-3.5-sonnet": {"prompt": 0.0015, "completion": 0.0075},
                "openai/gpt-4o": {"prompt": 0.0025, "completion": 0.01}
            }
        }

    async def record_usage(
        self,
        tenant_id: str,
        provider: ProviderType,
        model: str,
        usage_type: UsageType,
        amount: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        记录使用量

        Args:
            tenant_id: 租户ID
            provider: 提供商
            model: 模型名称
            usage_type: 使用量类型
            amount: 使用量
            metadata: 元数据

        Returns:
            是否成功记录
        """
        try:
            record = UsageRecord(
                tenant_id=tenant_id,
                provider=provider,
                model=model,
                usage_type=usage_type,
                amount=amount,
                metadata=metadata or {}
            )

            # 添加到内存记录
            self.records.append(record)

            # 更新实时使用量
            self.real_time_usage[tenant_id][f"{provider.value}_{model.value if hasattr(model, 'value') else model}_{usage_type.value}"] += amount

            # 更新小时统计
            current_hour = datetime.utcnow().hour
            if len(self.hourly_usage[tenant_id]) <= 24:
                self.hourly_usage[tenant_id].append(0)
            self.hourly_usage[tenant_id][-1] += amount

            logger.debug(f"记录使用量: {tenant_id} {provider.value} {model} {usage_type.value} {amount}")
            return True

        except Exception as e:
            logger.error(f"记录使用量失败: {e}")
            return False

    async def record_cost(
        self,
        tenant_id: str,
        provider: ProviderType,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        记录成本

        Args:
            tenant_id: 租户ID
            provider: 提供商
            model: 模型名称
            prompt_tokens: 提示Token数
            completion_tokens: 完成Token数
            total_tokens: 总Token数
            metadata: 元数据

        Returns:
            是否成功记录
        """
        try:
            # 计算预估成本
            estimated_cost = self._calculate_cost(provider, model, prompt_tokens, completion_tokens)

            cost_record = CostRecord(
                tenant_id=tenant_id,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                metadata=metadata or {}
            )

            # 添加到内存记录
            self.cost_records.append(cost_record)

            logger.debug(f"记录成本: {tenant_id} {provider.value} {model} ${estimated_cost:.6f}")
            return True

        except Exception as e:
            logger.error(f"记录成本失败: {e}")
            return False

    def _calculate_cost(
        self,
        provider: ProviderType,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        计算成本

        Args:
            provider: 提供商
            model: 模型名称
            prompt_tokens: 提示Token数
            completion_tokens: 完成Token数

        Returns:
            预估成本（美元）
        """
        try:
            provider_config = self.pricing_config.get(provider, {})
            model_config = provider_config.get(model, {"prompt": 0.001, "completion": 0.002})

            prompt_cost = (prompt_tokens / 1000) * model_config["prompt"]
            completion_cost = (completion_tokens / 1000) * model_config["completion"]

            total_cost = prompt_cost + completion_cost
            return total_cost

        except Exception as e:
            logger.error(f"计算成本失败: {e}")
            return 0.0

    async def check_usage_limits(
        self,
        tenant_id: str,
        provider: ProviderType,
        requested_tokens: int = 0
    ) -> Tuple[bool, List[str]]:
        """
        检查使用量限制

        Args:
            tenant_id: 租户ID
            provider: 提供商
            requested_tokens: 请求的Token数

        Returns:
            (是否允许, 限制消息列表)
        """
        try:
            # 获取租户限制配置
            usage_limit = await self._get_usage_limit(tenant_id)
            if not usage_limit or not usage_limit.active:
                return True, []

            # 获取当前使用量
            current_usage = await self.get_current_usage(tenant_id, provider)

            warnings = []

            # 检查每日Token限制
            if current_usage["daily_tokens"] + requested_tokens > usage_limit.daily_token_limit:
                warnings.append(f"接近每日Token限制: {current_usage['daily_tokens']}/{usage_limit.daily_token_limit}")
                if current_usage["daily_tokens"] >= usage_limit.daily_token_limit:
                    return False, [f"已达到每日Token限制: {usage_limit.daily_token_limit}"]

            # 检查每日API调用限制
            if current_usage["daily_api_calls"] >= usage_limit.daily_api_limit:
                return False, [f"已达到每日API调用限制: {usage_limit.daily_api_limit}"]

            # 检查每月Token限制
            if current_usage["monthly_tokens"] + requested_tokens > usage_limit.monthly_token_limit:
                warnings.append(f"接近每月Token限制: {current_usage['monthly_tokens']}/{usage_limit.monthly_token_limit}")
                if current_usage["monthly_tokens"] >= usage_limit.monthly_token_limit:
                    return False, [f"已达到每月Token限制: {usage_limit.monthly_token_limit}"]

            # 检查成本限制
            if current_usage["monthly_cost"] >= usage_limit.cost_limit:
                return False, [f"已达到每月成本限制: ${usage_limit.cost_limit}"]

            return True, warnings

        except Exception as e:
            logger.error(f"检查使用量限制失败: {e}")
            return True, ["无法检查使用量限制"]

    async def get_current_usage(
        self,
        tenant_id: str,
        provider: Optional[ProviderType] = None
    ) -> Dict[str, Any]:
        """
        获取当前使用量

        Args:
            tenant_id: 租户ID
            provider: 提供商，可选

        Returns:
            当前使用量统计
        """
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # 过滤记录
            filtered_costs = [
                record for record in self.cost_records
                if record.tenant_id == tenant_id
                and (provider is None or record.provider == provider)
            ]

            # 计算每日使用量
            daily_costs = [
                record for record in filtered_costs
                if record.timestamp >= today_start
            ]
            daily_tokens = sum(record.total_tokens for record in daily_costs)
            daily_api_calls = len(daily_costs)
            daily_cost = sum(record.estimated_cost for record in daily_costs)

            # 计算每月使用量
            monthly_costs = [
                record for record in filtered_costs
                if record.timestamp >= month_start
            ]
            monthly_tokens = sum(record.total_tokens for record in monthly_costs)
            monthly_api_calls = len(monthly_costs)
            monthly_cost = sum(record.estimated_cost for record in monthly_costs)

            return {
                "daily_tokens": daily_tokens,
                "daily_api_calls": daily_api_calls,
                "daily_cost": daily_cost,
                "monthly_tokens": monthly_tokens,
                "monthly_api_calls": monthly_api_calls,
                "monthly_cost": monthly_cost,
                "timestamp": now.isoformat()
            }

        except Exception as e:
            logger.error(f"获取当前使用量失败: {e}")
            return {}

    async def get_usage_statistics(
        self,
        tenant_id: str,
        period: str = "daily",
        provider: Optional[ProviderType] = None
    ) -> UsageStatistics:
        """
        获取使用量统计

        Args:
            tenant_id: 租户ID
            period: 统计周期 ("daily", "weekly", "monthly")
            provider: 提供商，可选

        Returns:
            使用量统计
        """
        try:
            now = datetime.utcnow()

            # 计算时间范围
            if period == "daily":
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "weekly":
                days_since_monday = now.weekday()
                start_time = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "monthly":
                start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_time = now - timedelta(days=1)

            # 过滤记录
            filtered_costs = [
                record for record in self.cost_records
                if (record.tenant_id == tenant_id and
                    record.timestamp >= start_time and
                    (provider is None or record.provider == provider))
            ]

            # 计算总体统计
            total_tokens = sum(record.total_tokens for record in filtered_costs)
            total_api_calls = len(filtered_costs)
            total_cost = sum(record.estimated_cost for record in filtered_costs)

            # 按提供商分组
            provider_breakdown = defaultdict(lambda: {"tokens": 0, "calls": 0, "cost": 0.0})
            for record in filtered_costs:
                key = record.provider.value
                provider_breakdown[key]["tokens"] += record.total_tokens
                provider_breakdown[key]["calls"] += 1
                provider_breakdown[key]["cost"] += record.estimated_cost

            # 按模型分组
            model_breakdown = defaultdict(lambda: {"tokens": 0, "calls": 0, "cost": 0.0})
            for record in filtered_costs:
                key = f"{record.provider.value}:{record.model}"
                model_breakdown[key]["tokens"] += record.total_tokens
                model_breakdown[key]["calls"] += 1
                model_breakdown[key]["cost"] += record.estimated_cost

            return UsageStatistics(
                tenant_id=tenant_id,
                period=period,
                total_tokens=total_tokens,
                total_api_calls=total_api_calls,
                total_cost=total_cost,
                provider_breakdown=dict(provider_breakdown),
                model_breakdown=dict(model_breakdown),
                timestamp=now
            )

        except Exception as e:
            logger.error(f"获取使用量统计失败: {e}")
            return UsageStatistics(tenant_id=tenant_id, period=period)

    async def get_real_time_usage(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取实时使用量

        Args:
            tenant_id: 租户ID

        Returns:
            实时使用量数据
        """
        try:
            return dict(self.real_time_usage.get(tenant_id, {}))

        except Exception as e:
            logger.error(f"获取实时使用量失败: {e}")
            return {}

    async def get_hourly_usage(self, tenant_id: str, hours: int = 24) -> List[int]:
        """
        获取小时使用量

        Args:
            tenant_id: 租户ID
            hours: 小时数

        Returns:
            每小时使用量列表
        """
        try:
            hourly_data = self.hourly_usage.get(tenant_id, [])
            return hourly_data[-hours:] if len(hourly_data) >= hours else hourly_data

        except Exception as e:
            logger.error(f"获取小时使用量失败: {e}")
            return []

    async def _get_usage_limit(self, tenant_id: str) -> Optional[UsageLimit]:
        """
        获取使用量限制配置

        Args:
            tenant_id: 租户ID

        Returns:
            使用量限制配置
        """
        try:
            # 这里应该从数据库获取配置，暂时返回默认配置
            return UsageLimit(
                tenant_id=tenant_id,
                daily_token_limit=100000,
                daily_api_limit=1000,
                monthly_token_limit=3000000,
                monthly_api_limit=30000,
                cost_limit=100.0,
                active=True
            )

        except Exception as e:
            logger.error(f"获取使用量限制失败: {e}")
            return None

    async def set_usage_limit(self, usage_limit: UsageLimit) -> bool:
        """
        设置使用量限制

        Args:
            usage_limit: 使用量限制配置

        Returns:
            是否成功设置
        """
        try:
            # 这里应该保存到数据库
            logger.info(f"设置使用量限制: {usage_limit.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"设置使用量限制失败: {e}")
            return False

    async def export_usage_data(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> Optional[str]:
        """
        导出使用量数据

        Args:
            tenant_id: 租户ID
            start_date: 开始日期
            end_date: 结束日期
            format: 导出格式 ("json", "csv")

        Returns:
            导出数据路径或内容
        """
        try:
            # 过滤记录
            filtered_costs = [
                record for record in self.cost_records
                if (record.tenant_id == tenant_id and
                    start_date <= record.timestamp <= end_date)
            ]

            if format == "json":
                data = []
                for record in filtered_costs:
                    data.append({
                        "timestamp": record.timestamp.isoformat(),
                        "provider": record.provider.value,
                        "model": record.model,
                        "prompt_tokens": record.prompt_tokens,
                        "completion_tokens": record.completion_tokens,
                        "total_tokens": record.total_tokens,
                        "estimated_cost": record.estimated_cost
                    })
                return json.dumps(data, indent=2, ensure_ascii=False)

            elif format == "csv":
                # 简化的CSV导出
                lines = ["timestamp,provider,model,prompt_tokens,completion_tokens,total_tokens,estimated_cost"]
                for record in filtered_costs:
                    lines.append(f"{record.timestamp.isoformat()},{record.provider.value},{record.model},"
                               f"{record.prompt_tokens},{record.completion_tokens},{record.total_tokens},"
                               f"{record.estimated_cost}")
                return "\n".join(lines)

            else:
                return None

        except Exception as e:
            logger.error(f"导出使用量数据失败: {e}")
            return None

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            return {
                "total_records": len(self.records),
                "total_cost_records": len(self.cost_records),
                "active_tenants": len(self.real_time_usage),
                "hourly_usage_tenants": len(self.hourly_usage),
                "memory_estimate_mb": (
                    len(self.records) * 200 +  # 每条记录约200字节
                    len(self.cost_records) * 300 +  # 每条成本记录约300字节
                    len(self.real_time_usage) * 1000  # 每个租户约1KB
                ) / (1024 * 1024)
            }

        except Exception as e:
            logger.error(f"获取内存使用情况失败: {e}")
            return {}

    async def cleanup_old_records(self, days: int = 30):
        """
        清理旧记录

        Args:
            days: 保留天数
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # 清理使用量记录
            initial_count = len(self.records)
            self.records = deque(
                (record for record in self.records if record.timestamp >= cutoff_date),
                maxlen=10000
            )
            cleaned_records = initial_count - len(self.records)

            # 清理成本记录
            initial_cost_count = len(self.cost_records)
            self.cost_records = deque(
                (record for record in self.cost_records if record.timestamp >= cutoff_date),
                maxlen=10000
            )
            cleaned_costs = initial_cost_count - len(self.cost_records)

            logger.info(f"清理旧记录完成: 使用量记录 {cleaned_records} 条, 成本记录 {cleaned_costs} 条")

        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")


class UsageMonitoringService:
    """使用量监控服务主类"""

    def __init__(self):
        self.tracker = UsageTracker()
        self.monitoring_active = True
        self.alert_thresholds = {
            "daily_token_usage": 0.8,  # 80%时发出警告
            "daily_api_calls": 0.8,
            "monthly_cost": 0.9
        }

    async def start_monitoring(self):
        """启动监控"""
        try:
            logger.info("启动使用量监控服务")
            # 可以在这里启动定期清理任务
            asyncio.create_task(self._periodic_cleanup())
        except Exception as e:
            logger.error(f"启动监控失败: {e}")

    async def stop_monitoring(self):
        """停止监控"""
        try:
            logger.info("停止使用量监控服务")
            self.monitoring_active = False
        except Exception as e:
            logger.error(f"停止监控失败: {e}")

    async def _periodic_cleanup(self):
        """定期清理任务"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(24 * 3600)  # 每24小时执行一次
                await self.tracker.cleanup_old_records()
            except Exception as e:
                logger.error(f"定期清理失败: {e}")

    async def check_and_alert(self, tenant_id: str) -> List[str]:
        """
        检查并发送警告

        Args:
            tenant_id: 租户ID

        Returns:
            警告消息列表
        """
        try:
            alerts = []
            current_usage = await self.tracker.get_current_usage(tenant_id)
            usage_limit = await self.tracker._get_usage_limit(tenant_id)

            if not usage_limit:
                return alerts

            # 检查各项阈值
            if usage_limit.daily_token_limit > 0:
                token_ratio = current_usage.get("daily_tokens", 0) / usage_limit.daily_token_limit
                if token_ratio >= self.alert_thresholds["daily_token_usage"]:
                    alerts.append(f"每日Token使用量已达 {token_ratio:.1%}")

            if usage_limit.daily_api_limit > 0:
                api_ratio = current_usage.get("daily_api_calls", 0) / usage_limit.daily_api_limit
                if api_ratio >= self.alert_thresholds["daily_api_calls"]:
                    alerts.append(f"每日API调用已达 {api_ratio:.1%}")

            if usage_limit.cost_limit > 0:
                cost_ratio = current_usage.get("monthly_cost", 0) / usage_limit.cost_limit
                if cost_ratio >= self.alert_thresholds["monthly_cost"]:
                    alerts.append(f"每月成本已达 {cost_ratio:.1%}")

            return alerts

        except Exception as e:
            logger.error(f"检查警告失败: {e}")
            return []


# 全局使用量监控服务实例
usage_monitoring_service = UsageMonitoringService()