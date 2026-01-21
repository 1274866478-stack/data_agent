"""
Cube.js 语义层服务

提供 Cube.js API 的封装，支持：
- 执行语义层查询
- 获取 Cube 定义
- 多租户隔离
"""

from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime
import json
import asyncio

from ...core.config import settings


class CubeService:
    """Cube.js 语义层服务"""

    def __init__(self):
        self.base_url = settings.cube_api_url or "http://localhost:4000"
        self.api_secret = settings.cube_api_secret or ""
        self._cache: Dict[str, Any] = {}

    async def execute_query(
        self,
        cube_name: str,
        measures: List[str],
        dimensions: List[str] = None,
        filters: List[Dict[str, Any]] = None,
        time_dimension: str = None,
        granularity: str = None,
        limit: int = None,
        offset: int = None,
        order: List[Dict[str, str]] = None,
        tenant_id: str = None,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        执行 Cube.js 查询

        Args:
            cube_name: Cube 名称 (如 "Orders", "Customers")
            measures: 度量列表 (如 ["total_revenue", "order_count"])
            dimensions: 维度列表 (如 ["created_at", "status"])
            filters: 过滤条件
            time_dimension: 时间维度
            granularity: 时间粒度 (day, week, month, year)
            limit: 返回行数限制
            offset: 偏移量
            order: 排序 (如 [{"Orders.created_at": "desc"}])
            tenant_id: 租户ID (自动注入到 filters)
            refresh: 是否刷新缓存

        Returns:
            查询结果，包含 data 和 annotation

        Example:
            result = await cube_service.execute_query(
                cube_name="Orders",
                measures=["total_revenue", "order_count"],
                dimensions=["created_at", "status"],
                filters=[{"member": "Orders.status", "operator": "equals", "values": ["completed"]}],
                time_dimension="Orders.created_at",
                granularity="day",
                tenant_id="tenant_123"
            )
        """
        # 构建查询
        query = {
            "measures": measures or [],
        }

        if dimensions:
            query["dimensions"] = dimensions

        if time_dimension:
            query["timeDimensions"] = [{
                "dimension": time_dimension,
                "granularity": granularity or "day"
            }]

        # 多租户过滤器注入
        all_filters = []

        # 优先添加租户过滤器（确保多租户隔离）
        if tenant_id:
            all_filters.append({
                "member": f"{cube_name}.tenant_id",
                "operator": "equals",
                "values": [tenant_id]
            })

        # 添加用户指定的过滤器
        if filters:
            all_filters.extend(filters)

        if all_filters:
            query["filters"] = all_filters

        if limit:
            query["limit"] = limit

        if offset:
            query["offset"] = offset

        if order:
            query["order"] = order

        # 检查缓存
        cache_key = f"{cube_name}:{json.dumps(query, sort_keys=True)}"
        if not refresh and cache_key in self._cache:
            return self._cache[cache_key]

        # 调用 Cube.js API
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/cubejs-api/v1/load",
                    json={
                        "query": query,
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_secret}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                result = response.json()

                # 缓存结果
                self._cache[cache_key] = result

                return result

        except httpx.HTTPError as e:
            raise Exception(f"Cube.js 查询失败: {str(e)}") from e

    async def get_cube_schema(self, cube_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取 Cube 定义

        Args:
            cube_name: 指定 Cube 名称，返回该 Cube 的定义
                     如果为 None，返回所有 Cube 的定义

        Returns:
            Cube 定义字典
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/cubejs-api/v1/meta",
                    headers={
                        "Authorization": f"Bearer {self.api_secret}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                meta = response.json()

                if cube_name:
                    return meta.get("cubes", {}).get(cube_name, {})
                return meta.get("cubes", {})

        except httpx.HTTPError as e:
            raise Exception(f"获取 Cube 定义失败: {str(e)}") from e

    async def list_cubes(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的 Cube

        Returns:
            Cube 列表，每个元素包含 name, title, description 等信息
        """
        schema = await self.get_cube_schema()
        cubes = []

        for cube_name, cube_def in schema.items():
            cubes.append({
                "name": cube_name,
                "title": cube_def.get("title", cube_name),
                "description": cube_def.get("description", ""),
                "measures": cube_def.get("measures", []),
                "dimensions": cube_def.get("dimensions", []),
            })

        return cubes

    async def get_available_measures(self, cube_name: str) -> List[str]:
        """获取指定 Cube 的所有度量"""
        schema = await self.get_cube_schema(cube_name)
        return list(schema.get("measures", {}).keys())

    async def get_available_dimensions(self, cube_name: str) -> List[str]:
        """获取指定 Cube 的所有维度"""
        schema = await self.get_cube_schema(cube_name)
        return list(schema.get("dimensions", {}).keys())

    def clear_cache(self):
        """清除查询缓存"""
        self._cache.clear()

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            True 如果服务可用
        """
        try:
            import asyncio
            asyncio.run(self.get_cube_schema())
            return True
        except Exception:
            return False
