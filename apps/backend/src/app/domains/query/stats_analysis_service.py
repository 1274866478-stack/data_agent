"""
统计分析服务 - 为查询结果提供深度统计分析

功能：
1. 描述性统计：均值、中位数、标准差、极值等
2. 趋势分析：环比增长率、同比增长率、移动平均
3. 异常检测：识别异常值和离群点
4. 分布分析：数据分布特征、分位数
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class StatsAnalysisService:
    """统计分析服务"""

    def __init__(self):
        self.logger = logger

    def analyze_query_result(
        self,
        data: Dict[str, Any],
        time_column: Optional[str] = None,
        value_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析查询结果，生成深度统计指标

        Args:
            data: 查询结果数据
                {
                    "columns": ["列名1", "列名2", ...],
                    "rows": [[值1, 值2, ...], ...]
                }
            time_column: 时间列名（用于趋势分析）
            value_column: 数值列名（用于统计分析）

        Returns:
            统计分析结果
        """
        try:
            if not data or not data.get("rows"):
                return {"error": "无数据可供分析"}

            columns = data.get("columns", [])
            rows = data.get("rows", [])

            # 自动识别时间列和数值列
            if not time_column or not value_column:
                time_column, value_column = self._detect_columns(columns, rows)

            if not value_column:
                return {"error": "未找到数值列，无法进行统计分析"}

            # 提取数值数据
            values = self._extract_numeric_values(rows, columns, value_column)
            if not values:
                return {"error": f"列 '{value_column}' 中没有有效数值"}

            # 执行各项统计分析
            stats_result = {
                "basic_stats": self._calculate_basic_stats(values),
                "trend_analysis": self._calculate_trend_analysis(
                    rows, columns, time_column, value_column
                ) if time_column else None,
                "distribution": self._calculate_distribution(values),
                "extremes": self._find_extremes(rows, columns, value_column, values),
                "value_column": value_column,
                "time_column": time_column,
            }

            return stats_result

        except Exception as e:
            self.logger.error(f"统计分析失败: {e}", exc_info=True)
            return {"error": f"统计分析失败: {str(e)}"}

    def _detect_columns(
        self, columns: List[str], rows: List[List[Any]]
    ) -> tuple[Optional[str], Optional[str]]:
        """自动检测时间列和数值列"""
        time_column = None
        value_column = None

        # 时间关键词检测
        time_keywords = ['time', 'date', '日期', '时间', 'created', 'updated', 'month', 'day']

        # 数值关键词检测
        value_keywords = ['amount', 'count', 'value', 'price', 'sales', 'revenue',
                         '金额', '数量', '销售额', '收入', '总计', '平均']

        # 检测时间列
        for col in columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in time_keywords):
                time_column = col
                break

        # 检测数值列
        for col in columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in value_keywords):
                value_column = col
                break

        # 如果没找到，尝试从数据中推断
        if not value_column and rows:
            for i, col in enumerate(columns):
                # 检查该列是否为数值类型
                if rows and len(rows) > 0:
                    first_value = rows[0][i] if i < len(rows[0]) else None
                    if isinstance(first_value, (int, float)) or (
                        isinstance(first_value, str) and
                        first_value.replace('.', '', 1).replace('-', '', 1).isdigit()
                    ):
                        value_column = col
                        break

        return time_column, value_column

    def _extract_numeric_values(
        self, rows: List[List[Any]], columns: List[str], column_name: str
    ) -> List[float]:
        """从数据中提取数值"""
        try:
            col_index = columns.index(column_name)
            values = []
            for row in rows:
                if col_index < len(row):
                    val = row[col_index]
                    if isinstance(val, (int, float)):
                        values.append(float(val))
                    elif isinstance(val, str):
                        # 尝试转换字符串为数值
                        val_clean = val.replace(',', '').replace('万元', '').replace('元', '')
                        try:
                            values.append(float(val_clean))
                        except ValueError:
                            continue
            return values
        except ValueError:
            return []

    def _calculate_basic_stats(self, values: List[float]) -> Dict[str, Any]:
        """计算基础统计指标"""
        if not values:
            return {}

        n = len(values)
        values_sorted = sorted(values)

        total = sum(values)
        mean = total / n
        median = values_sorted[n // 2] if n % 2 == 1 else (
            values_sorted[n // 2 - 1] + values_sorted[n // 2]
        ) / 2

        # 方差和标准差
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)

        # 变异系数
        cv = (std_dev / mean * 100) if mean != 0 else 0

        return {
            "count": n,
            "total": round(total, 2),
            "mean": round(mean, 2),
            "median": round(median, 2),
            "std_dev": round(std_dev, 2),
            "variance": round(variance, 2),
            "cv_percent": round(cv, 2),  # 变异系数（百分比）
            "min": round(values_sorted[0], 2),
            "max": round(values_sorted[-1], 2),
            "range": round(values_sorted[-1] - values_sorted[0], 2),
        }

    def _calculate_trend_analysis(
        self, rows: List[List[Any]], columns: List[str],
        time_column: str, value_column: str
    ) -> Dict[str, Any]:
        """计算趋势分析指标"""
        try:
            time_idx = columns.index(time_column)
            value_idx = columns.index(value_column)

            # 按时间排序并提取数据
            time_series = []
            for row in rows:
                if time_idx < len(row) and value_idx < len(row):
                    time_val = row[time_idx]
                    num_val = row[value_idx]
                    if isinstance(num_val, (int, float)):
                        time_series.append((time_val, float(num_val)))

            if len(time_series) < 2:
                return {"error": "数据点不足，无法计算趋势"}

            # 计算环比增长率
            growth_rates = []
            for i in range(1, len(time_series)):
                prev_val = time_series[i - 1][1]
                curr_val = time_series[i][1]
                if prev_val != 0:
                    growth_rate = ((curr_val - prev_val) / prev_val) * 100
                    growth_rates.append(growth_rate)

            # 计算移动平均（3期）
            ma_period = 3
            moving_averages = []
            for i in range(ma_period - 1, len(time_series)):
                ma_values = [time_series[j][1] for j in range(i - ma_period + 1, i + 1)]
                ma = sum(ma_values) / ma_period
                moving_averages.append(ma)

            # 整体趋势
            first_val = time_series[0][1]
            last_val = time_series[-1][1]
            total_growth = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0

            # 平均增长率
            avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0

            # 波动性（增长率标准差）
            volatility = math.sqrt(
                sum((r - avg_growth) ** 2 for r in growth_rates) / len(growth_rates)
            ) if growth_rates else 0

            return {
                "total_growth_percent": round(total_growth, 2),
                "avg_growth_percent": round(avg_growth, 2),
                "volatility": round(volatility, 2),  # 波动性
                "growth_rates": [round(r, 2) for r in growth_rates],
                "moving_averages": [round(ma, 2) for ma in moving_averages],
                "first_value": round(first_val, 2),
                "last_value": round(last_val, 2),
                "trend_direction": "上升" if total_growth > 0 else "下降" if total_growth < 0 else "平稳",
            }

        except Exception as e:
            self.logger.error(f"趋势分析失败: {e}")
            return {"error": f"趋势分析失败: {str(e)}"}

    def _calculate_distribution(self, values: List[float]) -> Dict[str, Any]:
        """计算分布特征"""
        if not values:
            return {}

        n = len(values)
        values_sorted = sorted(values)

        # 四分位数
        q1_idx = n // 4
        q2_idx = n // 2
        q3_idx = (3 * n) // 4

        return {
            "q1": round(values_sorted[q1_idx], 2),
            "q2": round(values_sorted[q2_idx], 2),  # 中位数
            "q3": round(values_sorted[q3_idx], 2),
            "iqr": round(values_sorted[q3_idx] - values_sorted[q1_idx], 2),  # 四分位距
        }

    def _find_extremes(
        self, rows: List[List[Any]], columns: List[str],
        column_name: str, values: List[float]
    ) -> Dict[str, Any]:
        """找出极值和异常点"""
        if not values:
            return {}

        col_index = columns.index(column_name)

        # 找出最大值和最小值对应的行
        max_val = max(values)
        min_val = min(values)

        max_rows = []
        min_rows = []

        for row in rows:
            if col_index < len(row):
                val = row[col_index]
                if isinstance(val, (int, float)) and float(val) == max_val:
                    max_rows.append(row)
                elif isinstance(val, (int, float)) and float(val) == min_val:
                    min_rows.append(row)

        # 使用 IQR 方法检测异常值
        values_sorted = sorted(values)
        n = len(values)
        q1 = values_sorted[n // 4]
        q3 = values_sorted[(3 * n) // 4]
        iqr = q3 - q1

        # 异常值边界
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = [
            {"value": v, "row_index": i}
            for i, v in enumerate(values)
            if v < lower_bound or v > upper_bound
        ]

        return {
            "max_value": round(max_val, 2),
            "min_value": round(min_val, 2),
            "max_rows": max_rows[:3],  # 最多返回3个极值行
            "min_rows": min_rows[:3],
            "outliers_count": len(outliers),
            "outliers": outliers[:5],  # 最多返回5个异常值
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
        }


# 全局单例
_stats_service = None


def get_stats_service() -> StatsAnalysisService:
    """获取统计分析服务单例"""
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsAnalysisService()
    return _stats_service
