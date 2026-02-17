"""
Router Agent - 路由器

负责：
1. 消歧检测 - 检测模糊查询
2. 复杂度评估 - 评估查询复杂度
3. 路由决策 - 决定查询处理路径
"""

from typing import Dict, Any, Literal
from enum import Enum

from .base_agent import BaseAgent


class RouteType(str, Enum):
    """路由类型"""
    DISAMBIGUATION = "disambiguation"  # 需要消歧
    FAST_PATH = "fast_path"            # 快速路径（简单查询）
    DEEP_PATH = "deep_path"            # 深度路径（复杂查询）


class ComplexityLevel(str, Enum):
    """复杂度级别"""
    SIMPLE = "simple"      # 简单查询：单表、单指标
    MEDIUM = "medium"      # 中等查询：多表或需要计算
    COMPLEX = "complex"    # 复杂查询：多表、多指标、复杂计算


class RouterAgent(BaseAgent):
    """
    路由器 Agent

    决策逻辑:
    1. 检测模糊关键词 (最好、最近、销售等)
    2. 判断查询复杂度 (简单/中等/复杂)
    3. 决定处理路径 (消歧/快速/深度)
    """

    # 模糊关键词词典
    AMBIGUOUS_KEYWORDS = {
        "multiple_metrics": ["最好", "最差", "最大", "最小", "最高", "最低", "排名", "top"],
        "time_range": ["最近", "近期", "近期内", "历史上", "过去", "本", "上", "这周", "本月"],
        "comparison_base": ["增长", "下降", "同比", "环比", "超过", "低于", "比"],
        "aggregation": ["总", "平均", "总计", "合计"],
        "context_missing": ["销售", "收益", "利润", "用户", "客户", "订单"]
    }

    def __init__(self, name: str = "router", llm=None):
        super().__init__(name, llm)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行路由逻辑

        Args:
            state: 当前状态，包含 query 等字段

        Returns:
            更新后的状态，包含 route_decision
        """
        query = state.get("query", "")
        cube_schema = state.get("cube_schema", {})

        # 1. 检测模糊性
        ambiguity_detected = self._detect_ambiguity(query)
        ambiguity_types = []

        if ambiguity_detected:
            # 分析模糊类型
            ambiguity_types = self._analyze_ambiguity_types(query)

            # 如果需要消歧，返回消歧路由
            return {
                "route_decision": {
                    "needs_disambiguation": True,
                    "route": RouteType.DISAMBIGUATION,
                    "ambiguity_types": [t.value for t in ambiguity_types],
                    "detected_keywords": self._get_detected_keywords(query)
                }
            }

        # 2. 评估复杂度
        complexity = self._assess_complexity(query, cube_schema)

        # 3. 决定路由
        route = self._determine_route(complexity)

        return {
            "route_decision": {
                "needs_disambiguation": False,
                "route": route.value,
                "complexity": complexity.value
            }
        }

    def _detect_ambiguity(self, query: str) -> bool:
        """
        检测查询中的模糊表达

        Args:
            query: 用户查询

        Returns:
            True 如果检测到模糊表达
        """
        query_lower = query.lower()

        for keywords in self.AMBIGUOUS_KEYWORDS.values():
            if any(kw in query_lower for kw in keywords):
                return True

        return False

    def _analyze_ambiguity_types(self, query: str) -> list:
        """
        分析模糊类型

        Args:
            query: 用户查询

        Returns:
            模糊类型列表
        """
        query_lower = query.lower()
        types = []

        if any(kw in query_lower for kw in self.AMBIGUOUS_KEYWORDS["multiple_metrics"]):
            types.append("multiple_metrics")

        if any(kw in query_lower for kw in self.AMBIGUOUS_KEYWORDS["time_range"]):
            types.append("time_range")

        if any(kw in query_lower for kw in self.AMBIGUOUS_KEYWORDS["comparison_base"]):
            types.append("comparison_base")

        if any(kw in query_lower for kw in self.AMBIGUOUS_KEYWORDS["context_missing"]):
            types.append("context_missing")

        return types

    def _get_detected_keywords(self, query: str) -> list:
        """获取检测到的模糊关键词"""
        query_lower = query.lower()
        detected = []

        for category, keywords in self.AMBIGUOUS_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    detected.append({
                        "category": category,
                        "keyword": kw
                    })

        return detected

    def _assess_complexity(
        self,
        query: str,
        cube_schema: Dict[str, Any]
    ) -> ComplexityLevel:
        """
        评估查询复杂度

        Args:
            query: 用户查询
            cube_schema: 可用的 Cube 定义

        Returns:
            复杂度级别
        """
        query_lower = query.lower()

        # 复杂查询指标
        complex_indicators = [
            "占比", "比例", "率", "增长率", "同比", "环比",
            "趋势", "平均", "总计", "汇总", "聚合"
        ]

        # 多表关联指标
        join_indicators = [
            "关联", "联合", "连接", "对应", "相关"
        ]

        # 计算指标数量
        metric_count = sum(1 for kw in ["收入", "销售额", "订单", "用户", "客户"] if kw in query)

        # 判断复杂度
        if any(ind in query for ind in complex_indicators) or metric_count > 2:
            return ComplexityLevel.COMPLEX

        if any(ind in query for ind in join_indicators) or metric_count == 2:
            return ComplexityLevel.MEDIUM

        return ComplexityLevel.SIMPLE

    def _determine_route(self, complexity: ComplexityLevel) -> RouteType:
        """
        确定处理路径

        Args:
            complexity: 查询复杂度

        Returns:
            路由类型
        """
        if complexity == ComplexityLevel.SIMPLE:
            return RouteType.FAST_PATH
        else:
            return RouteType.DEEP_PATH
