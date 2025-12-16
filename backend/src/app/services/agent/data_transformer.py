"""
数据转换模块 - 将 SQL 查询结果转换为 ECharts 数据格式

SQL 返回格式: [{"col1": val1, "col2": val2}, ...]

mcp-echarts 需要的格式:
- 柱状图/饼图: [{"category": "xxx", "value": 123}, ...]
- 折线图: [{"time": "xxx", "value": 123}, ...]

旧格式 (本地 PyEcharts): [[val1, val2], [val1, val2], ...]
"""
from typing import List, Dict, Any, Tuple, Optional

from .models import ChartConfig, ChartType


def sql_result_to_echarts_data(
    sql_result: List[Dict[str, Any]],
    x_field: Optional[str] = None,
    y_field: Optional[str] = None
) -> Tuple[List[List[Any]], str, str]:
    """
    将 SQL 查询结果转换为 ECharts 二维数组格式
    
    Args:
        sql_result: SQL 查询返回的字典列表
        x_field: X轴对应的字段名（可选，默认取第一列）
        y_field: Y轴对应的字段名（可选，默认取第二列）
    
    Returns:
        (data, x_field_name, y_field_name) 元组
        - data: [[x1, y1], [x2, y2], ...] 格式的数据
        - x_field_name: 实际使用的 X 字段名
        - y_field_name: 实际使用的 Y 字段名
    
    Example:
        >>> result = [{"name": "Alice", "score": 95}, {"name": "Bob", "score": 87}]
        >>> data, x, y = sql_result_to_echarts_data(result, "name", "score")
        >>> print(data)  # [["Alice", 95], ["Bob", 87]]
    """
    if not sql_result:
        return [], "", ""
    
    # 获取所有列名
    columns = list(sql_result[0].keys())
    
    if len(columns) < 2:
        # 只有一列，无法生成图表
        return [], columns[0] if columns else "", ""
    
    # 确定 X 和 Y 字段
    if x_field and x_field in columns:
        actual_x = x_field
    else:
        actual_x = columns[0]  # 默认第一列
    
    if y_field and y_field in columns:
        actual_y = y_field
    else:
        # 默认第二列，但如果第一列已被用作 X，则取第二列
        remaining = [c for c in columns if c != actual_x]
        actual_y = remaining[0] if remaining else columns[1]
    
    # 转换数据
    data = []
    for row in sql_result:
        x_val = row.get(actual_x, "")
        y_val = row.get(actual_y, 0)
        
        # 确保 Y 值是数值类型
        try:
            y_val = float(y_val) if y_val is not None else 0
        except (ValueError, TypeError):
            y_val = 0
        
        data.append([x_val, y_val])
    
    return data, actual_x, actual_y


def sql_result_to_mcp_echarts_data(
    sql_result: List[Dict[str, Any]],
    chart_type: str = "bar",
    x_field: Optional[str] = None,
    y_field: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str, str]:
    """
    将 SQL 查询结果转换为 mcp-echarts 需要的格式

    Args:
        sql_result: SQL 查询返回的字典列表
        chart_type: 图表类型 ("bar", "pie", "line" 等)
        x_field: X轴/分类字段名（可选）
        y_field: Y轴/数值字段名（可选）

    Returns:
        (data, x_field_name, y_field_name) 元组
        - data: mcp-echarts 格式的数据
        - x_field_name: 实际使用的分类字段名
        - y_field_name: 实际使用的数值字段名

    Example:
        >>> result = [{"department": "技术部", "count": 45}]
        >>> data, x, y = sql_result_to_mcp_echarts_data(result, "bar")
        >>> print(data)  # [{"category": "技术部", "value": 45}]
    """
    if not sql_result:
        return [], "", ""

    # 获取所有列名
    columns = list(sql_result[0].keys())

    if len(columns) < 2:
        return [], columns[0] if columns else "", ""

    # 确定分类字段和数值字段
    if x_field and x_field in columns:
        actual_x = x_field
    else:
        actual_x = columns[0]

    if y_field and y_field in columns:
        actual_y = y_field
    else:
        remaining = [c for c in columns if c != actual_x]
        actual_y = remaining[0] if remaining else columns[1]

    # 根据图表类型转换数据格式
    data = []
    for row in sql_result:
        x_val = row.get(actual_x, "")
        y_val = row.get(actual_y, 0)

        # 确保数值类型
        try:
            y_val = float(y_val) if y_val is not None else 0
        except (ValueError, TypeError):
            y_val = 0

        if chart_type == "line":
            # 折线图使用 time/value 格式
            data.append({"time": str(x_val), "value": y_val})
        else:
            # 柱状图、饼图等使用 category/value 格式
            data.append({"category": str(x_val), "value": y_val})

    return data, actual_x, actual_y


def infer_chart_type(sql: str, data: List[Dict[str, Any]]) -> str:
    """
    根据 SQL 语句和数据特征推断合适的图表类型
    
    Args:
        sql: SQL 查询语句
        data: 查询结果
    
    Returns:
        推荐的图表类型: "bar", "line", "pie", "table"
    """
    sql_lower = sql.lower()
    
    # 1. 检查是否有时间相关字段 -> 折线图
    time_keywords = ["date", "time", "month", "year", "day", "week", "quarter"]
    if any(kw in sql_lower for kw in time_keywords):
        if "group by" in sql_lower:
            return "line"
    
    # 2. 检查是否是占比类查询 -> 饼图
    if "count" in sql_lower or "sum" in sql_lower:
        if data and len(data) <= 8:  # 饼图适合少量类别
            # 检查是否有 GROUP BY
            if "group by" in sql_lower:
                return "pie"
    
    # 3. 检查是否是分类比较 -> 柱状图
    if "group by" in sql_lower:
        return "bar"
    
    # 4. 默认返回表格
    return "table"


def prepare_mcp_chart_request(
    sql_result: List[Dict[str, Any]],
    sql: str,
    title: Optional[str] = None,
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    chart_type: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], ChartConfig, Optional[Dict[str, Any]]]:
    """
    准备 ECharts MCP 的请求参数，并返回 ChartConfig 和 ECharts 选项
    
    Args:
        sql_result: SQL 查询结果
        sql: SQL 语句
        title: 图表标题（可选）
        x_field: X轴字段（可选）
        y_field: Y轴字段（可选）
        chart_type: 图表类型（可选，不传则自动推断）
    
    Returns:
        (mcp_data, chart_config, echarts_option) 元组
        - mcp_data: mcp-echarts 格式的数据
        - chart_config: ChartConfig 对象
        - echarts_option: ECharts 配置选项（可选）
    """
    # 转换数据
    mcp_data, actual_x, actual_y = sql_result_to_mcp_echarts_data(
        sql_result, 
        chart_type or "bar", 
        x_field, 
        y_field
    )
    
    # 推断图表类型
    if not chart_type or chart_type in ("table", "none"):
        chart_type = infer_chart_type(sql, sql_result)
    
    # 如果还是 table，就不生成图表
    if chart_type == "table":
        chart_config = ChartConfig(
            chart_type=ChartType.TABLE,
            title=title or "查询结果",
            x_field=actual_x,
            y_field=actual_y
        )
        return [], chart_config, None
    
    # 创建 ChartConfig
    chart_type_enum = ChartType(chart_type) if chart_type in [e.value for e in ChartType] else ChartType.BAR
    chart_config = ChartConfig(
        chart_type=chart_type_enum,
        title=title or "查询结果",
        x_field=actual_x,
        y_field=actual_y
    )
    
    # 创建简单的 ECharts 选项（可选）
    echarts_option = {
        "title": {"text": title or "查询结果"},
        "xAxis": {"type": "category", "name": actual_x},
        "yAxis": {"type": "value", "name": actual_y},
        "series": [{
            "type": chart_type,
            "data": mcp_data
        }]
    }
    
    return mcp_data, chart_config, echarts_option

