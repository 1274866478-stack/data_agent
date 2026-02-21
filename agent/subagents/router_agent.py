from __future__ import annotations

"""Router agent for ambiguity detection and execution path selection."""

from enum import Enum
from typing import Any, Dict, List

from .base_agent import AgentState, BaseAgent


class RouteType(str, Enum):
    DISAMBIGUATION = "disambiguation"
    FAST_PATH = "fast_path"
    DEEP_PATH = "deep_path"


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class RouterAgent(BaseAgent):
    """Route queries to disambiguation/fast/deep execution paths."""

    AMBIGUOUS_KEYWORDS: Dict[str, List[str]] = {
        "multiple_metrics": ["最好", "最差", "最大", "最小", "最高", "最低", "排名", "top"],
        "time_range": ["最近", "近期", "近几天", "历史", "过去", "今天", "本周", "本月"],
        "comparison_base": ["增长", "下降", "同比", "环比", "超过", "低于", "比"],
        "aggregation": ["总", "平均", "总计", "合计"],
        "context_missing": ["销售", "收入", "利润", "用户", "客户", "订单"],
    }
    AMBIGUOUS_KEYWORDS_LOWER: Dict[str, List[str]] = {
        category: [keyword.lower() for keyword in keywords]
        for category, keywords in AMBIGUOUS_KEYWORDS.items()
    }
    COMPLEX_INDICATORS = [
        "占比",
        "比例",
        "环比",
        "增长率",
        "同比",
        "趋势",
        "平均",
        "总计",
        "汇总",
        "聚合",
        "correlation",
    ]
    JOIN_INDICATORS = ["关联", "联合", "连接", "对应", "相关", "join"]
    METRIC_KEYWORDS = ["收入", "销售额", "订单", "用户", "客户", "profit", "revenue"]

    def __init__(self, name: str = "router", llm: Any = None) -> None:
        super().__init__(name, llm)

    async def execute(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        query_lower = query.lower()
        cube_schema = state.get("cube_schema", {})

        if self._detect_ambiguity(query_lower):
            ambiguity_types = self._analyze_ambiguity_types(query_lower)
            return {
                "route_decision": {
                    "needs_disambiguation": True,
                    "route": RouteType.DISAMBIGUATION.value,
                    "ambiguity_types": ambiguity_types,
                    "detected_keywords": self._get_detected_keywords(query_lower),
                }
            }

        complexity = self._assess_complexity(query_lower, cube_schema)
        return {
            "route_decision": {
                "needs_disambiguation": False,
                "route": self._determine_route(complexity).value,
                "complexity": complexity.value,
            }
        }

    def _detect_ambiguity(self, query_lower: str) -> bool:
        return bool(self._matched_ambiguity_categories(query_lower))

    def _analyze_ambiguity_types(self, query_lower: str) -> List[str]:
        return self._matched_ambiguity_categories(query_lower)

    def _matched_ambiguity_categories(self, query_lower: str) -> List[str]:
        return [
            category
            for category, keywords in self.AMBIGUOUS_KEYWORDS_LOWER.items()
            if self._contains_any(query_lower, keywords)
        ]

    def _get_detected_keywords(self, query_lower: str) -> List[Dict[str, str]]:
        detected: List[Dict[str, str]] = []
        for category, keywords in self.AMBIGUOUS_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    detected.append({"category": category, "keyword": keyword})
        return detected

    def _assess_complexity(self, query_lower: str, cube_schema: Dict[str, Any]) -> ComplexityLevel:
        _ = cube_schema
        metric_count = sum(1 for keyword in self.METRIC_KEYWORDS if keyword in query_lower)

        if self._contains_any(query_lower, self.COMPLEX_INDICATORS) or metric_count > 2:
            return ComplexityLevel.COMPLEX
        if self._contains_any(query_lower, self.JOIN_INDICATORS) or metric_count == 2:
            return ComplexityLevel.MEDIUM
        return ComplexityLevel.SIMPLE

    @staticmethod
    def _contains_any(query_lower: str, keywords: List[str]) -> bool:
        return any(keyword in query_lower for keyword in keywords)

    def _determine_route(self, complexity: ComplexityLevel) -> RouteType:
        if complexity == ComplexityLevel.SIMPLE:
            return RouteType.FAST_PATH
        return RouteType.DEEP_PATH
