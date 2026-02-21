from __future__ import annotations

"""Planner agent for converting user query intent into a query plan."""

from typing import Any, Dict, List, Optional

from .base_agent import AgentState, BaseAgent


class PlannerAgent(BaseAgent):
    """Builds a structured plan used by the DSL generator."""
    TARGET_CUBE_KEYWORDS = {
        "Orders": ["订单", "order"],
        "Customers": ["客户", "用户", "customer", "user"],
        "Products": ["产品", "商品", "product"],
    }
    REVENUE_KEYWORDS = ["收入", "销售额", "revenue", "sales"]
    COUNT_KEYWORDS = ["数量", "count", "订单数", "次数"]
    TIME_KEYWORDS = ["时间", "日期", "time", "date"]
    STATUS_KEYWORDS = ["状态", "status"]
    TIME_RANGES = {
        "今天": "today",
        "昨天": "yesterday",
        "本周": "this_week",
        "上周": "last_week",
        "本月": "this_month",
        "上月": "last_month",
        "今年": "this_year",
        "去年": "last_year",
        "最近7天": "last_7_days",
        "最近30天": "last_30_days",
        "last 7 days": "last_7_days",
        "last 30 days": "last_30_days",
    }
    GRANULARITY_KEYWORDS = {
        "day": ["按天", "每日", "daily"],
        "week": ["按周", "每周", "weekly"],
        "month": ["按月", "每月", "monthly"],
    }
    REVENUE_MEASURE_TOKENS = ["revenue", "sales", "收入", "销售"]
    COUNT_MEASURE_TOKENS = ["count", "数量"]
    TIME_DIMENSION_TOKENS = ["time", "date", "created", "updated", "时间", "日期"]
    STATUS_DIMENSION_TOKENS = ["status", "状态"]
    CALCULATION_KEYWORDS = ["占比", "比例", "环比", "增长", "下降", "平均", "总计", "rate"]
    STATUS_FILTER_KEYWORDS = {
        "completed": ["完成"],
        "cancelled": ["取消"],
    }

    @staticmethod
    def _deduplicate(items: List[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    @staticmethod
    def _collect_cube_items(
        *,
        target_cubes: List[str],
        cube_schema: Dict[str, Any],
        field: str,
    ) -> List[str]:
        items: List[str] = []
        for cube_name in target_cubes:
            cube_info = cube_schema.get(cube_name)
            if cube_info:
                items.extend(cube_info.get(field, []))
        return items

    @staticmethod
    def _match_items_by_tokens(items: List[str], tokens: List[str]) -> List[str]:
        matched: List[str] = []
        for item in items:
            item_lower = str(item).lower()
            if any(token in item_lower for token in tokens):
                matched.append(item)
        return matched

    @staticmethod
    def _match_keyword_groups(
        query_lower: str,
        keyword_groups: Dict[str, List[str]],
    ) -> List[str]:
        matched: List[str] = []
        for group_name, keywords in keyword_groups.items():
            if any(keyword in query_lower for keyword in keywords):
                matched.append(group_name)
        return matched

    @staticmethod
    def _first_cube_name(cube_schema: Dict[str, Any]) -> Optional[str]:
        if not cube_schema:
            return None
        return next(iter(cube_schema.keys()))

    @staticmethod
    def _match_substring_mapping(query_lower: str, mapping: Dict[str, str]) -> Optional[str]:
        for keyword, mapped_value in mapping.items():
            if keyword in query_lower:
                return mapped_value
        return None

    def __init__(self, name: str = "planner", llm: Any = None) -> None:
        super().__init__(name, llm)

    async def execute(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        route_decision = state.get("route_decision", {})
        cube_schema = state.get("cube_schema", {})

        query_plan = await self._create_query_plan(query, route_decision, cube_schema)
        return {"query_plan": query_plan}

    async def _create_query_plan(
        self,
        query: str,
        route_decision: Dict[str, Any],
        cube_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        query_lower = query.lower()
        target_cubes = self._identify_target_cubes(query_lower, cube_schema)
        required_measures = self._identify_measures(query_lower, target_cubes, cube_schema)
        required_dimensions = self._identify_dimensions(query_lower, target_cubes, cube_schema)
        time_requirements = self._identify_time_requirements(query_lower)

        return {
            "target_cubes": target_cubes,
            "required_measures": required_measures,
            "required_dimensions": required_dimensions,
            "time_requirements": time_requirements,
            "estimated_complexity": route_decision.get("complexity", "medium"),
            "needs_calculation": self._needs_calculation(query_lower),
            "filters": self._identify_filters(query_lower),
        }

    def _identify_target_cubes(self, query_lower: str, cube_schema: Dict[str, Any]) -> List[str]:
        cubes = self._match_keyword_groups(query_lower, self.TARGET_CUBE_KEYWORDS)

        if not cubes:
            default_cube = self._first_cube_name(cube_schema)
            if default_cube:
                cubes.append(default_cube)

        return self._deduplicate(cubes)

    def _identify_measures(
        self,
        query_lower: str,
        target_cubes: List[str],
        cube_schema: Dict[str, Any],
    ) -> List[str]:
        available_measures = self._collect_cube_items(
            target_cubes=target_cubes,
            cube_schema=cube_schema,
            field="measures",
        )

        measures: List[str] = []

        if any(keyword in query_lower for keyword in self.REVENUE_KEYWORDS):
            measures.extend(
                self._match_items_by_tokens(
                    available_measures,
                    self.REVENUE_MEASURE_TOKENS,
                )
            )

        if any(keyword in query_lower for keyword in self.COUNT_KEYWORDS):
            measures.extend(
                self._match_items_by_tokens(
                    available_measures,
                    self.COUNT_MEASURE_TOKENS,
                )
            )

        if not measures and available_measures:
            measures.append(available_measures[0])

        return self._deduplicate(measures)

    def _identify_dimensions(
        self,
        query_lower: str,
        target_cubes: List[str],
        cube_schema: Dict[str, Any],
    ) -> List[str]:
        available_dimensions = self._collect_cube_items(
            target_cubes=target_cubes,
            cube_schema=cube_schema,
            field="dimensions",
        )

        dimensions: List[str] = []

        if any(keyword in query_lower for keyword in self.TIME_KEYWORDS):
            dimensions.extend(
                self._match_items_by_tokens(
                    available_dimensions,
                    self.TIME_DIMENSION_TOKENS,
                )
            )

        if any(keyword in query_lower for keyword in self.STATUS_KEYWORDS):
            dimensions.extend(
                self._match_items_by_tokens(
                    available_dimensions,
                    self.STATUS_DIMENSION_TOKENS,
                )
            )

        return self._deduplicate(dimensions)

    def _identify_time_requirements(self, query_lower: str) -> Dict[str, Any]:
        time_info: Dict[str, Any] = {
            "has_time_filter": False,
            "time_range": None,
            "granularity": None,
        }

        time_range = self._match_substring_mapping(query_lower, self.TIME_RANGES)
        if time_range is not None:
            time_info["has_time_filter"] = True
            time_info["time_range"] = time_range

        for granularity, keywords in self.GRANULARITY_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                time_info["granularity"] = granularity
                break

        return time_info

    def _needs_calculation(self, query_lower: str) -> bool:
        return any(keyword in query_lower for keyword in self.CALCULATION_KEYWORDS)

    def _identify_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        filters: List[Dict[str, Any]] = []

        for status, keywords in self.STATUS_FILTER_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                filters.append({"member": "status", "operator": "equals", "values": [status]})
                break

        return filters
