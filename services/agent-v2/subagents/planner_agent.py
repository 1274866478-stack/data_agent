"""
Planner Agent - 规划师

负责：
1. 任务分解 - 将复杂查询分解为子任务
2. 识别目标表 - 确定需要查询的 Cube
3. 识别需求 - 确定需要的度量和维度
"""

from typing import Dict, Any, List
import json

from .base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """
    规划师 Agent

    输入: 用户问题
    输出: 查询计划 (QueryPlan)
    """

    def __init__(self, name: str = "planner", llm=None):
        super().__init__(name, llm)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行规划逻辑

        Args:
            state: 当前状态，包含 query, route_decision 等

        Returns:
            更新后的状态，包含 query_plan
        """
        query = state.get("query", "")
        route_decision = state.get("route_decision", {})
        cube_schema = state.get("cube_schema", {})

        # 构建查询计划
        query_plan = await self._create_query_plan(
            query,
            route_decision,
            cube_schema
        )

        return {"query_plan": query_plan}

    async def _create_query_plan(
        self,
        query: str,
        route_decision: Dict[str, Any],
        cube_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建查询计划

        Args:
            query: 用户问题
            route_decision: 路由决策
            cube_schema: 可用的 Cube 定义

        Returns:
            查询计划
        """
        # 1. 识别目标 Cube
        target_cubes = self._identify_target_cubes(query, cube_schema)

        # 2. 识别需要的度量
        required_measures = self._identify_measures(query, target_cubes, cube_schema)

        # 3. 识别需要的维度
        required_dimensions = self._identify_dimensions(query, target_cubes, cube_schema)

        # 4. 识别时间需求
        time_requirements = self._identify_time_requirements(query)

        # 5. 估算复杂度
        estimated_complexity = route_decision.get("complexity", "medium")

        return {
            "target_cubes": target_cubes,
            "required_measures": required_measures,
            "required_dimensions": required_dimensions,
            "time_requirements": time_requirements,
            "estimated_complexity": estimated_complexity,
            "needs_calculation": self._needs_calculation(query),
            "filters": self._identify_filters(query)
        }

    def _identify_target_cubes(
        self,
        query: str,
        cube_schema: Dict[str, Any]
    ) -> List[str]:
        """识别目标 Cube"""
        cubes = []

        # 简单规则匹配
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["订单", "order"]):
            cubes.append("Orders")

        if any(kw in query_lower for kw in ["客户", "用户", "customer", "user"]):
            cubes.append("Customers")

        if any(kw in query_lower for kw in ["产品", "商品", "product"]):
            cubes.append("Products")

        # 默认使用 Orders
        if not cubes and cube_schema:
            available_cubes = list(cube_schema.keys())
            if available_cubes:
                cubes.append(available_cubes[0])

        return cubes

    def _identify_measures(
        self,
        query: str,
        target_cubes: List[str],
        cube_schema: Dict[str, Any]
    ) -> List[str]:
        """识别需要的度量"""
        measures = []
        query_lower = query.lower()

        # 收集所有可用的度量
        available_measures = []
        for cube in target_cubes:
            if cube in cube_schema:
                cube_measures = cube_schema[cube].get("measures", [])
                available_measures.extend(cube_measures)

        # 根据关键词匹配度量
        if any(kw in query_lower for kw in ["收入", "销售额", "revenue", "sales"]):
            for m in available_measures:
                if "revenue" in m.lower() or "sales" in m.lower() or "收入" in m or "销售" in m:
                    measures.append(m)

        if any(kw in query_lower for kw in ["数量", "count", "订单数"]):
            for m in available_measures:
                if "count" in m.lower() or "数量" in m:
                    measures.append(m)

        # 如果没有匹配到，使用默认度量
        if not measures and available_measures:
            measures.append(available_measures[0])

        return measures

    def _identify_dimensions(
        self,
        query: str,
        target_cubes: List[str],
        cube_schema: Dict[str, Any]
    ) -> List[str]:
        """识别需要的维度"""
        dimensions = []
        query_lower = query.lower()

        # 收集所有可用的维度
        available_dimensions = []
        for cube in target_cubes:
            if cube in cube_schema:
                cube_dims = cube_schema[cube].get("dimensions", [])
                available_dimensions.extend(cube_dims)

        # 根据关键词匹配维度
        if any(kw in query_lower for kw in ["时间", "日期", "time", "date"]):
            for d in available_dimensions:
                if any(time_kw in d.lower() for time_kw in ["time", "date", "时间", "日期", "created", "updated"]):
                    dimensions.append(d)

        if any(kw in query_lower for kw in ["状态", "status"]):
            for d in available_dimensions:
                if "status" in d.lower() or "状态" in d:
                    dimensions.append(d)

        return dimensions

    def _identify_time_requirements(self, query: str) -> Dict[str, Any]:
        """识别时间需求"""
        query_lower = query.lower()
        time_req = {"has_time_filter": False, "time_range": None, "granularity": None}

        # 检测时间范围关键词
        time_ranges = {
            "今天": "today",
            "昨天": "yesterday",
            "本周": "this_week",
            "上周": "last_week",
            "本月": "this_month",
            "上月": "last_month",
            "本年": "this_year",
            "去年": "last_year",
            "最近7天": "last_7_days",
            "最近30天": "last_30_days"
        }

        for keyword, range_val in time_ranges.items():
            if keyword in query_lower:
                time_req["has_time_filter"] = True
                time_req["time_range"] = range_val
                break

        # 检测粒度
        if any(kw in query_lower for kw in ["按天", "每日", "daily"]):
            time_req["granularity"] = "day"
        elif any(kw in query_lower for kw in ["按周", "每周", "weekly"]):
            time_req["granularity"] = "week"
        elif any(kw in query_lower for kw in ["按月", "每月", "monthly"]):
            time_req["granularity"] = "month"

        return time_req

    def _needs_calculation(self, query: str) -> bool:
        """判断是否需要计算"""
        calculation_keywords = ["占比", "比例", "率", "增长", "下降", "平均", "总计"]
        return any(kw in query for kw in calculation_keywords)

    def _identify_filters(self, query: str) -> List[Dict[str, Any]]:
        """识别过滤条件"""
        filters = []
        query_lower = query.lower()

        # 状态过滤
        if "完成" in query_lower or "已完成" in query_lower:
            filters.append({
                "member": "status",
                "operator": "equals",
                "values": ["completed"]
            })
        elif "取消" in query_lower:
            filters.append({
                "member": "status",
                "operator": "equals",
                "values": ["cancelled"]
            })

        return filters
