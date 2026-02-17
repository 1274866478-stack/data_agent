# -*- coding: utf-8 -*-
"""
数据分析节点 (Analysis Node) - LangGraph 节点

这个节点负责生成智能数据分析报告，包括：
1. 数据概要统计
2. 趋势分析
3. 异常检测
4. 业务洞察
5. 可视化建议

核心功能：
    - generate_analysis_report: 生成数据分析报告
    - detect_trends: 检测数据趋势
    - find_anomalies: 查找异常值
    - recommend_insights: 推荐业务洞察

作者: BMad Master
版本: 1.0.0
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ChartType(str, Enum):
    """图表类型"""
    LINE = "line"           # 折线图
    BAR = "bar"            # 柱状图
    PIE = "pie"            # 饼图
    SCATTER = "scatter"     # 散点图
    RADAR = "radar"         # 雷达图
    TABLE = "table"         # 表格


class InsightType(str, Enum):
    """洞察类型"""
    TREND_UP = "trend_up"           # 上升趋势
    TREND_DOWN = "trend_down"       # 下降趋势
    ANOMALY_HIGH = "anomaly_high"   # 异常高值
    ANOMALY_LOW = "anomaly_low"     # 异常低值
    CORRELATION = "correlation"     # 相关性
    DISTRIBUTION = "distribution"   # 分布特征
    COMPARISON = "comparison"       # 对比发现


@dataclass
class DataInsight:
    """数据洞察"""
    type: InsightType
    title: str
    description: str
    value: Any = None
    confidence: float = 1.0
    severity: str = "info"  # info, warning, critical

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "value": self.value,
            "confidence": self.confidence,
            "severity": self.severity
        }


@dataclass
class AnalysisReport:
    """数据分析报告"""
    query: str                                    # 用户查询
    row_count: int                                # 返回行数
    column_stats: Dict[str, Dict[str, Any]]      # 列统计
    insights: List[DataInsight] = field(default_factory=list)  # 洞察列表
    chart_recommendation: Optional[Dict[str, Any]] = None  # 图表推荐
    suggestions: List[str] = field(default_factory=list)     # 建议
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "row_count": self.row_count,
            "column_stats": self.column_stats,
            "insights": [i.to_dict() for i in self.insights],
            "chart_recommendation": self.chart_recommendation,
            "suggestions": self.suggestions,
            "generated_at": self.generated_at
        }


class AnalysisNode:
    """
    数据分析节点

    根据查询结果生成智能数据分析报告。
    """

    def __init__(self):
        self.logger = logger

    def generate_analysis_report(
        self,
        query: str,
        data: List[Dict[str, Any]],
        sql: Optional[str] = None
    ) -> AnalysisReport:
        """
        生成数据分析报告

        Args:
            query: 用户查询
            data: 查询结果数据
            sql: 执行的 SQL（可选）

        Returns:
            分析报告
        """
        if not data:
            return self._generate_empty_report(query)

        # 识别查询类型
        query_type = self._classify_query(query)

        # 计算列统计
        column_stats = self._calculate_column_stats(data)

        # 生成洞察
        insights = self._generate_insights(data, column_stats, query_type)

        # 图表推荐
        chart_rec = self._recommend_chart(data, query, query_type)

        # 生成建议
        suggestions = self._generate_suggestions(data, insights, query_type)

        return AnalysisReport(
            query=query,
            row_count=len(data),
            column_stats=column_stats,
            insights=insights,
            chart_recommendation=chart_rec,
            suggestions=suggestions
        )

    def _generate_empty_report(self, query: str) -> AnalysisReport:
        """生成空结果报告"""
        return AnalysisReport(
            query=query,
            row_count=0,
            column_stats={},
            insights=[
                DataInsight(
                    type=InsightType.DISTRIBUTION,
                    title="无数据返回",
                    description="查询未返回任何数据，请检查查询条件或数据源",
                    severity="warning"
                )
            ],
            suggestions=[
                "检查 WHERE 条件是否过于严格",
                "确认数据源中有符合条件的数据",
                "尝试使用更宽松的查询条件"
            ]
        )

    def _classify_query(self, query: str) -> str:
        """
        分类查询类型

        Returns:
            查询类型: proportion, trend, comparison, ranking, detail
        """
        query_lower = query.lower()

        # 占比/分布类
        if any(kw in query_lower for kw in ['占比', '比例', '分布', '百分比', '%']):
            return "proportion"

        # 趋势类
        if any(kw in query_lower for kw in ['趋势', '变化', '增长', '下降', '走势', '每月', '每年', '月度', '年度']):
            return "trend"

        # 对比类
        if any(kw in query_lower for kw in ['对比', '比较', '差异', 'vs', ' versus']):
            return "comparison"

        # 排名类
        if any(kw in query_lower for kw in ['排名', '排行', 'top', '最高', '最低', '前几', '最多', '最少']):
            return "ranking"

        # 默认为详细查询
        return "detail"

    def _calculate_column_stats(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        计算列统计信息

        Args:
            data: 数据行列表

        Returns:
            列名 -> 统计信息的字典
        """
        if not data:
            return {}

        stats = {}
        numeric_columns = []
        string_columns = []

        # 识别列类型
        for col in data[0].keys():
            is_numeric = True
            sample_values = []
            for row in data[:100]:  # 采样前100行
                val = row.get(col)
                if val is None:
                    continue
                sample_values.append(val)
                if not isinstance(val, (int, float)):
                    is_numeric = False
                    break

            if is_numeric and sample_values:
                numeric_columns.append(col)
            else:
                string_columns.append(col)

        # 计算数值列统计
        for col in numeric_columns:
            values = [row.get(col) for row in data if row.get(col) is not None]
            if values:
                stats[col] = {
                    "type": "numeric",
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "sum": sum(values)
                }

        # 计算字符串列统计
        for col in string_columns:
            values = [str(row.get(col)) for row in data if row.get(col) is not None]
            if values:
                unique_values = list(set(values))
                stats[col] = {
                    "type": "string",
                    "count": len(values),
                    "unique_count": len(unique_values),
                    "sample_values": unique_values[:5]
                }

        return stats

    def _generate_insights(
        self,
        data: List[Dict[str, Any]],
        column_stats: Dict[str, Dict[str, Any]],
        query_type: str
    ) -> List[DataInsight]:
        """
        生成数据洞察

        Args:
            data: 数据行列表
            column_stats: 列统计信息
            query_type: 查询类型

        Returns:
            洞察列表
        """
        insights = []

        # 基于查询类型生成特定洞察
        if query_type == "proportion":
            insights.extend(self._proportion_insights(data, column_stats))
        elif query_type == "trend":
            insights.extend(self._trend_insights(data, column_stats))
        elif query_type == "ranking":
            insights.extend(self._ranking_insights(data, column_stats))

        # 通用洞察
        insights.extend(self._general_insights(data, column_stats))

        return insights

    def _proportion_insights(
        self,
        data: List[Dict[str, Any]],
        column_stats: Dict[str, Dict[str, Any]]
    ) -> List[DataInsight]:
        """占比类查询的洞察"""
        insights = []

        # 找到占比列和分类列
        percentage_col = None
        category_col = None
        value_col = None

        for col, stat in column_stats.items():
            col_lower = col.lower()
            if stat["type"] == "numeric":
                if 'percent' in col_lower or '占比' in col_lower or 'ratio' in col_lower:
                    percentage_col = col
                elif 'count' in col_lower or '数量' in col_lower or 'value' in col_lower:
                    value_col = col
            elif stat["type"] == "string":
                if stat["unique_count"] > 1 and stat["unique_count"] < len(data) / 2:
                    category_col = col

        # 最大占比洞察
        if value_col:
            values = [(row.get(value_col), row.get(category_col)) for row in data if row.get(value_col) is not None]
            if values:
                max_item = max(values, key=lambda x: x[0])
                insights.append(DataInsight(
                    type=InsightType.DISTRIBUTION,
                    title=f"最大占比",
                    description=f"'{max_item[1]}' 占比最高，为 {max_item[0]}",
                    value={"category": max_item[1], "value": max_item[0]},
                    severity="info"
                ))

        return insights

    def _trend_insights(
        self,
        data: List[Dict[str, Any]],
        column_stats: Dict[str, Dict[str, Any]]
    ) -> List[DataInsight]:
        """趋势类查询的洞察"""
        insights = []

        # 找到时间列和数值列
        time_col = None
        value_col = None

        for col, stat in column_stats.items():
            col_lower = col.lower()
            if stat["type"] == "string" and any(
                kw in col_lower for kw in ['date', 'time', 'month', 'year', '日期', '时间', '月', '年']
            ):
                time_col = col
            elif stat["type"] == "numeric":
                if any(kw in col_lower for kw in ['amount', 'sales', 'count', 'value', '金额', '销售', '数量']):
                    value_col = col

        if time_col and value_col and len(data) >= 3:
            # 计算趋势
            values = [row.get(value_col) for row in data if row.get(value_col) is not None]
            if values:
                first_val = values[0]
                last_val = values[-1]
                change = last_val - first_val
                change_pct = (change / first_val * 100) if first_val != 0 else 0

                if change_pct > 10:
                    insights.append(DataInsight(
                        type=InsightType.TREND_UP,
                        title="上升趋势",
                        description=f"从 {first_val} 增长到 {last_val}，增长 {change_pct:.1f}%",
                        value={"change": change, "change_pct": change_pct},
                        severity="info"
                    ))
                elif change_pct < -10:
                    insights.append(DataInsight(
                        type=InsightType.TREND_DOWN,
                        title="下降趋势",
                        description=f"从 {first_val} 下降到 {last_val}，下降 {abs(change_pct):.1f}%",
                        value={"change": change, "change_pct": change_pct},
                        severity="warning"
                    ))

        return insights

    def _ranking_insights(
        self,
        data: List[Dict[str, Any]],
        column_stats: Dict[str, Dict[str, Any]]
    ) -> List[DataInsight]:
        """排名类查询的洞察"""
        insights = []

        # 找到排名列和数值列
        label_col = None
        value_col = None

        for col, stat in column_stats.items():
            if stat["type"] == "string":
                if stat["unique_count"] == len(data) or stat["unique_count"] > len(data) * 0.8:
                    label_col = col
            elif stat["type"] == "numeric":
                if any(kw in col.lower() for kw in ['amount', 'sales', 'count', 'score', '金额', '销售', '数量', '得分']):
                    value_col = col

        if label_col and value_col and data:
            # Top 1 洞察
            top_item = max(data, key=lambda row: row.get(value_col, 0))
            insights.append(DataInsight(
                type=InsightType.COMPARISON,
                title="排名第一",
                description=f"'{top_item.get(label_col)}' 以 {top_item.get(value_col)} 排名第一",
                value=top_item,
                severity="info"
            ))

            # Top 3 集中度
            if len(data) >= 3:
                sorted_data = sorted(data, key=lambda row: row.get(value_col, 0), reverse=True)
                top3_sum = sum(row.get(value_col, 0) for row in sorted_data[:3])
                total_sum = sum(row.get(value_col, 0) for row in data)
                concentration = top3_sum / total_sum * 100 if total_sum > 0 else 0

                if concentration > 70:
                    insights.append(DataInsight(
                        type=InsightType.DISTRIBUTION,
                        title="高度集中",
                        description=f"Top 3 占比 {concentration:.1f}%，数据高度集中",
                        value={"concentration": concentration},
                        severity="info"
                    ))

        return insights

    def _general_insights(
        self,
        data: List[Dict[str, Any]],
        column_stats: Dict[str, Dict[str, Any]]
    ) -> List[DataInsight]:
        """通用洞察"""
        insights = []

        # 数据量洞察
        if len(data) == 0:
            insights.append(DataInsight(
                type=InsightType.DISTRIBUTION,
                title="无数据",
                description="查询未返回任何数据",
                severity="warning"
            ))
        elif len(data) == 1:
            insights.append(DataInsight(
                type=InsightType.DISTRIBUTION,
                title="单条记录",
                description="查询仅返回 1 条记录",
                severity="info"
            ))
        elif len(data) >= 1000:
            insights.append(DataInsight(
                type=InsightType.DISTRIBUTION,
                title="大量数据",
                description=f"查询返回 {len(data)} 条记录，建议添加筛选条件",
                severity="info"
            ))

        return insights

    def _recommend_chart(
        self,
        data: List[Dict[str, Any]],
        query: str,
        query_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        推荐图表类型和配置

        Args:
            data: 数据行列表
            query: 用户查询
            query_type: 查询类型

        Returns:
            图表推荐配置
        """
        if not data or len(data) < 2:
            return None

        chart_type = None
        title = f"{query[:20]}..." if len(query) > 20 else query

        # 根据查询类型选择图表
        if query_type == "proportion":
            chart_type = ChartType.PIE
        elif query_type == "trend":
            chart_type = ChartType.LINE
        elif query_type == "ranking":
            chart_type = ChartType.BAR
        elif query_type == "comparison":
            chart_type = ChartType.BAR
        else:
            chart_type = ChartType.TABLE

        # 提取数据用于图表
        x_field = None
        y_field = None
        x_data = []
        y_data = []

        # 查找合适的列
        for col in data[0].keys():
            col_lower = col.lower()
            # X轴：通常是字符串/分类列
            if not x_field and (
                any(kw in col_lower for kw in ['name', 'title', 'category', 'type', '名', '名称', '类别']) or
                (col in [d.keys() for d in data] and isinstance(list(data)[0].get(col), str))
            ):
                x_field = col
                x_data = [row.get(col) for row in data]

            # Y轴：数值列
            if not y_field and col_lower in ['count', 'amount', 'value', 'sales', 'quantity', 'price', '数量', '金额', '销售']:
                y_field = col
                y_data = [row.get(col, 0) for row in data]

        # 如果没找到，使用前两列
        if not x_field and len(data[0]) >= 1:
            x_field = list(data[0].keys())[0]
            x_data = [row.get(x_field) for row in data]

        if not y_field and len(data[0]) >= 2:
            y_field = list(data[0].keys())[1]
            y_data = [row.get(y_field, 0) for row in data]

        return {
            "chart_type": chart_type.value,
            "title": title,
            "x_field": x_field,
            "y_field": y_field,
            "x_data": x_data[:20],  # 限制最多20个数据点
            "y_data": y_data[:20],
            "reasoning": f"根据查询类型 '{query_type}' 推荐 {chart_type.value} 图表"
        }

    def _generate_suggestions(
        self,
        data: List[Dict[str, Any]],
        insights: List[DataInsight],
        query_type: str
    ) -> List[str]:
        """生成分析建议"""
        suggestions = []

        if not data:
            return [
                "检查数据源中是否有符合条件的数据",
                "尝试放宽查询条件",
                "确认数据源连接正常"
            ]

        # 基于查询类型的建议
        if query_type == "proportion":
            suggestions.append("可以进一步分析各分类的详细数据")
        elif query_type == "trend":
            suggestions.append("可以按时间粒度（月/季度）进一步细分")
        elif query_type == "ranking":
            suggestions.append("可以查看排名靠后项的原因分析")

        # 基于洞察的建议
        for insight in insights:
            if insight.severity == "warning":
                if insight.type == InsightType.TREND_DOWN:
                    suggestions.append("建议分析下降原因并采取改进措施")
                elif insight.type == InsightType.ANOMALY_HIGH:
                    suggestions.append(f"建议核实 '{insight.title}' 的数据准确性")

        return suggestions


# ============================================================================
# 便捷函数
# ============================================================================

def create_analysis_node() -> AnalysisNode:
    """创建分析节点实例"""
    return AnalysisNode()


def analyze_query_result(
    query: str,
    data: List[Dict[str, Any]],
    sql: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析查询结果的便捷函数

    Args:
        query: 用户查询
        data: 查询结果数据
        sql: 执行的 SQL（可选）

    Returns:
        分析报告字典
    """
    node = create_analysis_node()
    report = node.generate_analysis_report(query, data, sql)
    return report.to_dict()


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("数据分析节点测试")
    print("=" * 60)

    # 测试数据
    test_data = [
        {"province": "安徽", "count": 50, "percentage": 8.5},
        {"province": "浙江", "count": 120, "percentage": 20.3},
        {"province": "江苏", "count": 100, "percentage": 16.9},
        {"province": "广东", "count": 150, "percentage": 25.3},
        {"province": "山东", "count": 80, "percentage": 13.5},
        {"province": "河南", "count": 93, "percentage": 15.7},
    ]

    # 创建分析节点
    node = create_analysis_node()

    # 生成报告
    report = node.generate_analysis_report(
        query="各省份客户占比如何",
        data=test_data
    )

    print(f"\n查询: {report.query}")
    print(f"返回行数: {report.row_count}")
    print(f"\n列统计:")
    for col, stat in report.column_stats.items():
        print(f"  {col}: {stat}")

    print(f"\n洞察:")
    for insight in report.insights:
        print(f"  - [{insight.type.value}] {insight.title}: {insight.description}")

    print(f"\n建议:")
    for suggestion in report.suggestions:
        print(f"  - {suggestion}")

    if report.chart_recommendation:
        print(f"\n图表推荐:")
        rec = report.chart_recommendation
        print(f"  类型: {rec['chart_type']}")
        print(f"  理由: {rec['reasoning']}")
