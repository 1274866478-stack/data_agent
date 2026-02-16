"""
# [TENANT_CONFIG_MANAGER] 租户配置管理器

## [HEADER]
**文件名**: tenant_config_manager.py
**职责**: 实现分层API密钥管理、租户隔离、模型配置管理和配置缓存
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 租户配置管理器（简化版本）

## [INPUT]
- **tenant_id: str** - 租户ID
- **provider: ProviderType** - AI提供商类型
- **api_key: str** - API密钥
- **priority: int** - 优先级
- **daily_limit/monthly_limit: Optional[int]** - 调用限制
- **config: Dict[str, Any]** - 配置信息

## [OUTPUT]
- **Optional[str]**: API密钥（get_tenant_api_key, _get_global_api_key）
- **bool**: 设置成功（set_tenant_api_key, set_tenant_model_config）
- **Dict[str, Any]**: 模型配置（get_tenant_model_config）
  - default_model, max_tokens, temperature, enable_thinking, enable_multimodal
- **List[str]**: 可用提供商列表（get_tenant_providers）
- **Dict[str, bool]**: 配置验证结果（validate_tenant_config）
- **int**: 清理数量（cleanup_expired_configs）
- **Dict[str, Any]**: 所有配置（get_all_tenant_configs）

**上游依赖** (已读取源码):
- 项目配置: src.app.core.config.settings

**下游依赖** (需要反向索引分析):
- [llm_service.py](./llm_service.py) - LLM服务获取API密钥和模型配置
- [zhipu_client.py](./zhipu_client.py) - 智谱客户端获取API密钥

**调用方**:
- LLM服务获取租户API密钥
- 查询服务获取模型配置
- 管理API设置租户配置

## [STATE]
- **提供商类型**: ProviderType枚举（ZHIPU, OPENROUTER, OPENAI）
- **数据类**: APIKeyConfig（provider, api_key, is_active, priority, tenant_id）
- **配置缓存**: _config_cache字典（租户ID→配置），TTL=5分钟
- **缓存时间戳**: _cache_timestamps字典（租户ID→时间戳）
- **全局配置**: _global_config字典（从settings加载）
  - zhipuai_api_key, openrouter_api_key, openai_api_key
- **租户配置**: _tenant_configs字典（内存存储，生产环境应使用数据库）
- **分层配置**: 租户配置优先，全局配置回退
- **缓存验证**: _is_cache_valid检查TTL（5分钟）
- **缓存更新**: _update_cache更新配置和时间戳
- **缓存清理**: _clear_cache清理缓存（按租户或全部）
- **默认模型配置**:
  - ZHIPU: glm-4-flash, max_tokens=4000, temperature=0.7
  - OPENROUTER: google/gemini-2.0-flash-exp
  - enable_thinking=True, enable_multimodal=True

## [SIDE-EFFECTS]
- **环境变量读取**: getattr(settings, 'zhipuai_api_key', None)读取全局配置
- **字典操作**: self._config_cache[tenant_id] = config缓存配置，self._config_cache.pop(tenant_id)删除缓存
- **时间戳**: datetime.utcnow()记录缓存时间
- **条件判断**: if self._is_cache_valid(tenant_id)检查缓存有效性
- **字典读取**: self._tenant_configs.get(tenant_id, {})获取租户配置
- **字典更新**: self._tenant_configs[tenant_id][key] = value设置租户配置
- **列表推导式**: [provider.value for provider in ProviderType]遍历提供商
- **循环遍历**: for provider in ProviderType遍历所有提供商
- **字典合并**: {**default_config, **model_config}合并配置
- **异常处理**: try-except捕获所有异常，返回None或默认配置
- **日志记录**: logger.debug/info/warning/error记录操作
- **全局单例**: tenant_config_manager全局实例

## [POS]
**路径**: backend/src/app/services/tenant_config_manager.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 依赖项目配置settings
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import logging

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """AI提供商类型"""
    ZHIPU = "zhipu"
    OPENROUTER = "openrouter"
    OPENAI = "openai"


@dataclass
class APIKeyConfig:
    """API密钥配置"""
    provider: str
    api_key: str
    is_active: bool = True
    priority: int = 1
    tenant_id: str = "global"


class TenantConfigManager:
    """租户配置管理器 - 简化版本"""

    def __init__(self):
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps: Dict[str, datetime] = {}

        # 从环境变量加载全局配置
        self._load_global_config()

    def _load_global_config(self):
        """加载全局配置"""
        self._global_config = {
            ProviderType.ZHIPU.value: getattr(settings, 'zhipuai_api_key', None),
            ProviderType.OPENROUTER.value: getattr(settings, 'openrouter_api_key', None),
            ProviderType.OPENAI.value: getattr(settings, 'openai_api_key', None)
        }

        # 模拟租户配置（在实际项目中应从数据库加载）
        self._tenant_configs = {}

    def _is_cache_valid(self, tenant_id: str) -> bool:
        """检查缓存是否有效"""
        if tenant_id not in self._cache_timestamps:
            return False
        return datetime.utcnow() - self._cache_timestamps[tenant_id] < self._cache_ttl

    def _update_cache(self, tenant_id: str, config: Dict[str, Any]):
        """更新缓存"""
        self._config_cache[tenant_id] = config
        self._cache_timestamps[tenant_id] = datetime.utcnow()

    def _clear_cache(self, tenant_id: str = None):
        """清除缓存"""
        if tenant_id:
            self._config_cache.pop(tenant_id, None)
            self._cache_timestamps.pop(tenant_id, None)
        else:
            self._config_cache.clear()
            self._cache_timestamps.clear()

    async def get_tenant_api_key(
        self,
        tenant_id: str,
        provider: ProviderType,
        use_global_fallback: bool = True
    ) -> Optional[str]:
        """
        获取租户API密钥，支持分层配置

        Args:
            tenant_id: 租户ID
            provider: 提供商类型
            use_global_fallback: 是否使用全局配置作为回退

        Returns:
            str: API密钥
        """
        try:
            # 首先检查缓存
            if self._is_cache_valid(tenant_id):
                cached_config = self._config_cache.get(tenant_id, {})
                provider_key = f"{provider.value}_api_key"
                if provider_key in cached_config:
                    logger.debug(f"从缓存获取租户API密钥: {tenant_id}")
                    return cached_config[provider_key]

            # 从模拟的租户配置获取
            tenant_config = self._tenant_configs.get(tenant_id, {})
            provider_key = f"{provider.value}_api_key"
            tenant_api_key = tenant_config.get(provider_key)

            if tenant_api_key:
                logger.info(f"获取租户 {tenant_id} 的 {provider.value} API密钥")

                # 更新缓存
                current_config = self._config_cache.get(tenant_id, {})
                current_config[provider_key] = tenant_api_key
                self._update_cache(tenant_id, current_config)

                return tenant_api_key

            # 如果没有找到租户配置，尝试使用全局配置
            if use_global_fallback:
                return await self._get_global_api_key(provider)

            logger.warning(f"未找到租户 {tenant_id} 的 {provider.value} API密钥")
            return None

        except Exception as e:
            logger.error(f"获取租户API密钥失败: {e}")
            # 发生错误时尝试全局配置
            if use_global_fallback:
                return await self._get_global_api_key(provider)
            return None

    async def _get_global_api_key(self, provider: ProviderType) -> Optional[str]:
        """获取全局API密钥"""
        try:
            return self._global_config.get(provider.value)
        except Exception as e:
            logger.error(f"获取全局API密钥失败: {e}")
            return None

    async def set_tenant_api_key(
        self,
        tenant_id: str,
        provider: ProviderType,
        api_key: str,
        priority: int = 1,
        daily_limit: Optional[int] = None,
        monthly_limit: Optional[int] = None
    ) -> bool:
        """
        设置租户API密钥（内存版本，实际应用应持久化到数据库）

        Args:
            tenant_id: 租户ID
            provider: 提供商类型
            api_key: API密钥
            priority: 优先级
            daily_limit: 每日调用限制
            monthly_limit: 每月调用限制

        Returns:
            bool: 设置是否成功
        """
        try:
            # 在实际应用中，这里应该保存到数据库
            # 现在只是模拟保存到内存
            if tenant_id not in self._tenant_configs:
                self._tenant_configs[tenant_id] = {}

            self._tenant_configs[tenant_id][f"{provider.value}_api_key"] = api_key
            self._tenant_configs[tenant_id][f"{provider.value}_priority"] = priority
            self._tenant_configs[tenant_id][f"{provider.value}_daily_limit"] = daily_limit
            self._tenant_configs[tenant_id][f"{provider.value}_monthly_limit"] = monthly_limit

            # 清除缓存
            self._clear_cache(tenant_id)

            logger.info(f"设置租户 {tenant_id} 的 {provider.value} API密钥成功")
            return True

        except Exception as e:
            logger.error(f"设置租户API密钥失败: {e}")
            return False

    async def get_tenant_model_config(
        self,
        tenant_id: str,
        provider: ProviderType
    ) -> Dict[str, Any]:
        """
        获取租户模型配置

        Args:
            tenant_id: 租户ID
            provider: 提供商类型

        Returns:
            Dict: 模型配置
        """
        try:
            # 默认配置
            default_config = {
                "default_model": "glm-4-flash" if provider == ProviderType.ZHIPU else "google/gemini-2.0-flash-exp",
                "max_tokens": 4000,
                "temperature": 0.7,
                "enable_thinking": True,
                "enable_multimodal": True
            }

            # 从缓存获取
            if self._is_cache_valid(tenant_id):
                cached_config = self._config_cache.get(tenant_id, {})
                model_key = f"{provider.value}_model_config"
                if model_key in cached_config:
                    return {**default_config, **cached_config[model_key]}

            # 从模拟的租户配置获取
            tenant_config = self._tenant_configs.get(tenant_id, {})
            model_key = f"{provider.value}_model_config"
            model_config = tenant_config.get(model_key, {})

            final_config = {**default_config, **model_config}

            # 更新缓存
            current_config = self._config_cache.get(tenant_id, {})
            current_config[model_key] = model_config
            self._update_cache(tenant_id, current_config)

            return final_config

        except Exception as e:
            logger.error(f"获取租户模型配置失败: {e}")
            return {
                "default_model": "glm-4-flash",
                "max_tokens": 4000,
                "temperature": 0.7,
                "enable_thinking": False,
                "enable_multimodal": False
            }

    async def set_tenant_model_config(
        self,
        tenant_id: str,
        provider: ProviderType,
        config: Dict[str, Any]
    ) -> bool:
        """
        设置租户模型配置

        Args:
            tenant_id: 租户ID
            provider: 提供商类型
            config: 配置信息

        Returns:
            bool: 设置是否成功
        """
        try:
            if tenant_id not in self._tenant_configs:
                self._tenant_configs[tenant_id] = {}

            self._tenant_configs[tenant_id][f"{provider.value}_model_config"] = config

            # 清除缓存
            self._clear_cache(tenant_id)

            logger.info(f"设置租户 {tenant_id} 的 {provider.value} 模型配置成功")
            return True

        except Exception as e:
            logger.error(f"设置租户模型配置失败: {e}")
            return False

    async def get_tenant_providers(self, tenant_id: str) -> List[str]:
        """获取租户可用的提供商列表"""
        providers = []

        for provider in ProviderType:
            api_key = await self.get_tenant_api_key(tenant_id, provider, use_global_fallback=True)
            if api_key:
                providers.append(provider.value)

        return providers

    async def validate_tenant_config(self, tenant_id: str) -> Dict[str, bool]:
        """
        验证租户配置完整性

        Args:
            tenant_id: 租户ID

        Returns:
            Dict: 各提供商的验证结果
        """
        results = {}

        for provider in ProviderType:
            try:
                api_key = await self.get_tenant_api_key(tenant_id, provider, use_global_fallback=True)
                results[provider.value] = bool(api_key)
            except Exception as e:
                logger.error(f"验证租户 {tenant_id} 的 {provider.value} 配置失败: {e}")
                results[provider.value] = False

        return results

    async def cleanup_expired_configs(self) -> int:
        """
        清理过期的配置（简化版本，仅记录日志）

        Returns:
            int: 清理的配置数量
        """
        # 在实际应用中，这里应该清理数据库中的过期配置
        logger.info("清理过期配置功能（需要数据库支持）")
        return 0

    def get_all_tenant_configs(self) -> Dict[str, Any]:
        """获取所有租户配置（用于调试）"""
        return {
            "global_config": self._global_config,
            "tenant_configs": self._tenant_configs,
            "cache_info": {
                "cached_tenants": list(self._config_cache.keys()),
                "cache_timestamps": {
                    k: v.isoformat() for k, v in self._cache_timestamps.items()
                }
            }
        }


# 全局租户配置管理器实例
tenant_config_manager = TenantConfigManager()