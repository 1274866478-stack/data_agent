"""
模糊检测器 - 检测查询中的模糊性

负责：
1. 识别模糊关键词
2. 分类模糊类型
3. 评估模糊严重程度
"""

import re
from typing import Dict, List, Any, Optional, Set


class AmbiguityDetector:
    """模糊查询检测器"""

    # 模糊关键词词典
    AMBIGUOUS_KEYWORDS = {
        "multiple_metrics": {
            "keywords": ["最好", "最差", "最大", "最小", "最高", "最低", "排名", "前", "后"],
            "description": "多个可能的指标",
            "examples": ["哪个产品最好", "销售额最大的是"]
        },
        "time_range": {
            "keywords": ["最近", "近期", "当前", "这段时间", "最近一段"],
            "description": "时间范围不明确",
            "examples": ["最近销售情况", "这段时期的订单"]
        },
        "comparison_base": {
            "keywords": ["增长", "下降", "同比", "环比", "变化", "趋势"],
            "description": "缺少对比基准",
            "examples": ["销售额增长了多少", "用户变化趋势"]
        },
        "aggregation_level": {
            "keywords": ["汇总", "总计", "平均", "分布"],
            "description": "聚合维度不明确",
            "examples": ["总销售额", "平均订单金额"]
        },
        "missing_context": {
            "keywords": ["那个", "这个", "它", "他们", "具体"],
            "description": "缺少上下文指代",
            "examples": ["那个产品的销量", "它的价格"]
        }
    }

    def __init__(self):
        self.compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """编译正则表达式模式"""
        patterns = {}
        for ambiguity_type, config in self.AMBIGUOUS_KEYWORDS.items():
            # 构建正则表达式（匹配任意关键词）
            keyword_pattern = "|".join(re.escape(kw) for kw in config["keywords"])
            patterns[ambiguity_type] = re.compile(keyword_pattern)
        return patterns

    async def detect(
        self,
        query: str,
        cube_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检测查询中的模糊性

        Args:
            query: 用户查询
            cube_schema: 可选的 Cube 定义

        Returns:
            检测结果
        """
        detected_types = []
        detected_keywords = []
        severity = "low"

        for ambiguity_type, pattern in self.compiled_patterns.items():
            matches = pattern.findall(query)
            if matches:
                detected_types.append(ambiguity_type)
                detected_keywords.extend(matches)

        # 评估严重程度
        if len(detected_types) >= 3:
            severity = "high"
        elif len(detected_types) >= 2:
            severity = "medium"

        # 检查是否有明确的维度/度量
        has_clear_terms = self._has_clear_terms(query, cube_schema)

        is_ambiguous = len(detected_types) > 0 or not has_clear_terms

        return {
            "is_ambiguous": is_ambiguous,
            "ambiguity_types": detected_types,
            "detected_keywords": detected_keywords,
            "severity": severity,
            "confidence": self._calculate_confidence(detected_types, detected_keywords)
        }

    def _has_clear_terms(
        self,
        query: str,
        cube_schema: Optional[Dict[str, Any]]
    ) -> bool:
        """检查查询是否有明确的术语"""
        if not cube_schema:
            # 如果没有 schema，简单检查查询长度
            return len(query) >= 10

        # 检查是否包含明确的度量或维度名称
        all_terms = set()
        for cube_name, cube_def in cube_schema.items():
            all_terms.update(cube_def.get("measures", []))
            all_terms.update(cube_def.get("dimensions", []))

        query_lower = query.lower()
        for term in all_terms:
            if term.lower() in query_lower:
                return True

        return False

    def _calculate_confidence(
        self,
        detected_types: List[str],
        detected_keywords: List[str]
    ) -> float:
        """
        计算模糊检测的置信度

        Args:
            detected_types: 检测到的模糊类型
            detected_keywords: 检测到的关键词

        Returns:
            置信度 (0-1)
        """
        if not detected_types:
            return 0.0

        # 基础分数
        base_score = min(len(detected_types) * 0.3, 0.6)

        # 关键词密度加分
        keyword_score = min(len(detected_keywords) * 0.1, 0.4)

        return min(base_score + keyword_score, 1.0)

    def get_ambiguity_description(self, ambiguity_type: str) -> Optional[str]:
        """获取模糊类型的描述"""
        return self.AMBIGUOUS_KEYWORDS.get(ambiguity_type, {}).get("description")
