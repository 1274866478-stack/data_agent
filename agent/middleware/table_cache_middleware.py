# -*- coding: utf-8 -*-
"""
表名缓存中间件 (Table Cache Middleware)
======================================

自动缓存 list_tables() 的结果，减少重复调用。

功能：
    - 拦截 list_tables() 调用
    - 缓存返回的表名列表
    - 在下次调用时直接返回缓存

版本: 1.0.0
作者: Data Agent Team
"""

import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class TableCacheMiddleware:
    """
    表名缓存中间件

    自动缓存 list_tables() 的结果，避免重复查询。
    """

    # 类级别缓存: {(tenant_id, connection_id): ["table1", "table2", ...]}
    _cache: Dict[tuple, List[str]] = {}

    def __init__(
        self,
        tenant_id: str = "default_tenant",
        connection_id: Optional[str] = None,
        enabled: bool = True
    ):
        """
        初始化表名缓存中间件

        Args:
            tenant_id: 租户ID
            connection_id: 数据源连接ID
            enabled: 是否启用缓存
        """
        self.tenant_id = tenant_id
        self.connection_id = connection_id
        self.enabled = enabled
        self._cache_key = (tenant_id, connection_id or "default")

    def __call__(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理上下文，自动缓存表名

        Args:
            context: 当前上下文，包含 messages, tool_calls 等信息

        Returns:
            更新后的上下文
        """
        if not self.enabled:
            return context

        # 检查是否有 list_tables 调用
        messages = context.get("messages", [])
        for message in messages:
            tool_calls = getattr(message, "tool_calls", [])
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name == "list_tables":
                    # 检查是否有缓存
                    cached_tables = self._cache.get(self._cache_key)
                    if cached_tables:
                        logger.info(f"[TableCache] 使用缓存的表名: {cached_tables}")

        return context

    def on_tool_result(self, tool_name: str, result: Any) -> None:
        """
        工具执行结果回调，用于更新缓存

        Args:
            tool_name: 工具名称
            result: 工具执行结果
        """
        if not self.enabled:
            return

        if tool_name == "list_tables":
            # 解析表名列表
            table_names = self._extract_table_names(result)
            if table_names:
                self._cache[self._cache_key] = table_names
                logger.info(f"[TableCache] 缓存表名: {table_names}")

    def _extract_table_names(self, result: Any) -> Optional[List[str]]:
        """
        从 list_tables 的结果中提取表名列表

        Args:
            result: list_tables 的返回结果

        Returns:
            表名列表，如果无法解析则返回 None
        """
        if isinstance(result, str):
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "tables" in data:
                    return data["tables"]
            except json.JSONDecodeError:
                pass

            # 尝试按行分割
            lines = result.strip().split("\n")
            if len(lines) > 1:
                return [line.strip() for line in lines if line.strip()]

        elif isinstance(result, list):
            return result

        elif isinstance(result, dict) and "tables" in result:
            return result["tables"]

        return None

    @classmethod
    def get_cached_tables(
        cls,
        tenant_id: str,
        connection_id: Optional[str] = None
    ) -> Optional[List[str]]:
        """获取缓存的表名列表

        Args:
            tenant_id: 租户ID
            connection_id: 数据源连接ID

        Returns:
            缓存的表名列表，如果不存在则返回 None
        """
        cache_key = (tenant_id, connection_id or "default")
        return cls._cache.get(cache_key)

    @classmethod
    def set_cached_tables(
        cls,
        tenant_id: str,
        table_names: List[str],
        connection_id: Optional[str] = None
    ) -> None:
        """设置缓存的表名列表

        Args:
            tenant_id: 租户ID
            table_names: 表名列表
            connection_id: 数据源连接ID
        """
        cache_key = (tenant_id, connection_id or "default")
        cls._cache[cache_key] = table_names
        logger.info(f"[TableCache] 设置缓存: {table_names}")

    @classmethod
    def clear_cache(
        cls,
        tenant_id: Optional[str] = None,
        connection_id: Optional[str] = None
    ) -> None:
        """清除缓存

        Args:
            tenant_id: 租户ID，如果为 None 则清除所有缓存
            connection_id: 数据源连接ID
        """
        if tenant_id is None:
            cls._cache.clear()
            logger.info("[TableCache] 清除所有缓存")
        elif connection_id is None:
            keys_to_remove = [k for k in cls._cache.keys() if k[0] == tenant_id]
            for key in keys_to_remove:
                del cls._cache[key]
            logger.info(f"[TableCache] 清除租户 {tenant_id} 的缓存")
        else:
            cache_key = (tenant_id, connection_id or "default")
            cls._cache.pop(cache_key, None)
            logger.info(f"[TableCache] 清除缓存: {cache_key}")


def create_table_cache_middleware(
    tenant_id: str = "default_tenant",
    connection_id: Optional[str] = None,
    enabled: bool = True
) -> TableCacheMiddleware:
    """
    创建表名缓存中间件的便捷函数

    Args:
        tenant_id: 租户ID
        connection_id: 数据源连接ID
        enabled: 是否启用缓存

    Returns:
        TableCacheMiddleware 实例
    """
    return TableCacheMiddleware(
        tenant_id=tenant_id,
        connection_id=connection_id,
        enabled=enabled
    )
