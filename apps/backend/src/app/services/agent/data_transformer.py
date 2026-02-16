"""
# Agent 数据转换器 - SQL结果到ECharts格式转换

## [HEADER]
**文件名**: data_transformer.py
**职责**: 将SQL查询结果转换为ECharts可视化所需的数据格式
**作者**: Data Agent Team
**版本**: 1.2.0
**变更记录**:
- v1.2.0 (2026-01-01): 支持图表类型自动推断
- v1.0.0 (2025-12-01): 初始版本，基础数据转换逻辑

## [INPUT]
- SQL查询结果: List[Dict[str, Any]] - 原始数据库返回
- SQL语句: str - 原始SQL查询
- 图表类型: str - 可选的图表类型指定
- 用户问题: str - 用于图表类型推断

## [OUTPUT]
- ECharts数据: List[Dict] - MCP ECharts工具所需格式
- ChartConfig对象: 包含图表类型、轴字段等配置
- ECharts Option: 完整的ECharts配置JSON

## [LINK]
**上游依赖**:
- [models.py](models.py) - ChartType和ChartConfig定义

**下游依赖**:
- [agent_service.py](agent_service.py) - 图表生成逻辑

**调用方**:
- Agent服务 - 数据查询后的可视化转换

## [POS]
**路径**: backend/src/app/services/agent/data_transformer.py
**模块层级**: Level 3 (Services → Agent → Data Transformer)
**依赖深度**: 2 层
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


def infer_chart_type(sql: str, data: List[Dict[str, Any]], question: str = "") -> str:
    """
    根据 SQL 语句、数据特征和用户问题推断合适的图表类型
    
    Args:
        sql: SQL 查询语句
        data: 查询结果
        question: 用户原始问题（可选，用于更准确的推断）
    
    Returns:
        推荐的图表类型: "bar", "line", "pie", "table"
    """
    sql_lower = sql.lower()
    question_lower = question.lower() if question else ""
    
    # 优先从用户问题中推断（更准确）
    if question:
        # 趋势类关键词 -> 折线图
        if any(kw in question_lower for kw in ["趋势", "变化", "时间", "月份", "年度", "季度", "增长", "下降"]):
            return "line"
        # 对比类关键词 -> 柱状图
        if any(kw in question_lower for kw in ["对比", "比较", "排名", "最高", "最低"]):
            return "bar"
        # 占比类关键词 -> 饼图
        if any(kw in question_lower for kw in ["占比", "分布", "比例", "份额"]):
            return "pie"
    
    # 1. 检查是否有时间相关字段 -> 折线图
    time_keywords = ["date", "time", "month", "year", "day", "week", "quarter", "created", "updated"]
    if any(kw in sql_lower for kw in time_keywords):
        if "group by" in sql_lower or "extract" in sql_lower:
            return "line"
        # 检查数据中的列名
        if data and len(data) > 0:
            columns = list(data[0].keys())
            time_cols = [col for col in columns if any(kw in col.lower() for kw in time_keywords)]
            if time_cols:
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
    
    # 4. 检查数据特征：如果有时间序列特征，推断为折线图
    if data and len(data) > 0:
        columns = list(data[0].keys())
        # 检查是否有数值列和时间相关列
        numeric_cols = []
        time_cols = []
        for col in columns:
            # 检查是否是数值列
            try:
                first_val = data[0].get(col)
                if isinstance(first_val, (int, float)) or (isinstance(first_val, str) and first_val.replace('.', '').replace('-', '').isdigit()):
                    numeric_cols.append(col)
            except:
                pass
            # 检查是否是时间列
            if any(kw in col.lower() for kw in time_keywords):
                time_cols.append(col)
        
        # 如果有时间列和数值列，且数据点较多，推断为折线图
        if time_cols and numeric_cols and len(data) >= 3:
            return "line"
        # 如果有数值列，推断为柱状图
        elif numeric_cols and len(data) <= 20:
            return "bar"
    
    # 5. 默认返回表格
    return "table"


def prepare_mcp_chart_request(
    sql_result: List[Dict[str, Any]],
    sql: str,
    title: Optional[str] = None,
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    chart_type: Optional[str] = None,
    question: Optional[str] = None
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
        question: 用户原始问题（可选，用于更准确的图表类型推断）
    
    Returns:
        (mcp_data, chart_config, echarts_option) 元组
        - mcp_data: mcp-echarts 格式的数据
        - chart_config: ChartConfig 对象
        - echarts_option: ECharts 配置选项（可选）
    """
    # 推断图表类型（如果未指定）
    if not chart_type or chart_type in ("table", "none"):
        chart_type = infer_chart_type(sql, sql_result, question or "")
    
    # 转换数据
    mcp_data, actual_x, actual_y = sql_result_to_mcp_echarts_data(
        sql_result, 
        chart_type, 
        x_field, 
        y_field
    )
    
    # 即使类型是 table，如果有数据也生成基础 ECharts 配置（用于前端展示）
    if chart_type == "table":
        chart_config = ChartConfig(
            chart_type=ChartType.TABLE,
            title=title or "查询结果",
            x_field=actual_x,
            y_field=actual_y
        )
        # 即使类型是 table，如果有数据也生成基础的 ECharts 配置
        # 这样前端可以展示表格，或者如果数据适合也可以尝试绘制基础图表
        echarts_option_for_table = None
        if sql_result and len(sql_result) > 0:
            # 尝试生成基础的表格展示配置
            try:
                # 如果有时间相关的字段，尝试推断为折线图
                time_indicators = ['date', 'time', 'month', 'year', 'day', 'created', 'updated']
                has_time_field = any(
                    any(indicator in str(col).lower() for indicator in time_indicators)
                    for col in (actual_x, actual_y)
                )
                
                # 如果有数值字段，生成基础图表配置
                if actual_y and has_time_field:
                    echarts_option_for_table = {
                        "title": {"text": title or "查询结果"},
                        "tooltip": {"trigger": "axis"},
                        "xAxis": {"type": "category", "data": [row.get(actual_x, "") for row in sql_result[:20]]},
                        "yAxis": {"type": "value"},
                        "series": [{
                            "type": "line",
                            "data": [row.get(actual_y, 0) for row in sql_result[:20]]
                        }]
                    }
                elif actual_y:
                    echarts_option_for_table = {
                        "title": {"text": title or "查询结果"},
                        "tooltip": {"trigger": "axis"},
                        "xAxis": {"type": "category", "data": [str(row.get(actual_x, "")) for row in sql_result[:20]]},
                        "yAxis": {"type": "value"},
                        "series": [{
                            "type": "bar",
                            "data": [float(row.get(actual_y, 0)) for row in sql_result[:20]]
                        }]
                    }
            except Exception:
                # 如果生成失败，返回 None（保持原有行为）
                echarts_option_for_table = None
        
        return [], chart_config, echarts_option_for_table
    
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


def convert_simple_chart_to_echarts(simple_chart: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    将简化格式的图表配置转换为完整的 ECharts 配置

    支持的简化格式:
    {
        "chart_type": "line" | "bar" | "pie" | "scatter",
        "title": "图表标题",
        "x_data": [...],           # X轴数据（类别/时间）
        "y_data": [...],           # Y轴数据（数值）
        "series_name": "系列名称"   # 可选
    }

    Args:
        simple_chart: 简化格式的图表配置

    Returns:
        完整的 ECharts 配置，如果格式无效则返回 None
    """
    if not simple_chart or not isinstance(simple_chart, dict):
        return None

    # 提取必需字段
    chart_type = simple_chart.get("chart_type", "bar")
    title = simple_chart.get("title", "数据可视化")
    x_data = simple_chart.get("x_data", [])
    y_data = simple_chart.get("y_data", [])
    series_name = simple_chart.get("series_name", "数值")

    # 验证数据
    if not x_data or not y_data:
        return None

    # 饼图需要特殊处理（需要 category + value 格式）
    if chart_type == "pie":
        # 将 x_data 和 y_data 转换为饼图格式
        pie_data = []
        for i, x in enumerate(x_data):
            if i < len(y_data):
                pie_data.append({"name": str(x), "value": y_data[i]})

        return {
            "title": {"text": title},
            "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b}: {c} ({d}%)"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [{
                "name": series_name,
                "type": "pie",
                "radius": "50%",
                "data": pie_data,
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        }

    # 柱状图、折线图、散点图（坐标系图表）
    return {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": [str(x) for x in x_data]
        },
        "yAxis": {
            "type": "value"
        },
        "series": [{
            "name": series_name,
            "type": chart_type,
            "data": y_data,
            "smooth": chart_type == "line"  # 折线图启用平滑
        }],
        "grid": {
            "left": "15%",
            "right": "5%",
            "bottom": "10%",
            "top": "15%",
            "containLabel": True
        }
    }


def extract_simple_charts_from_text(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取所有简化格式的图表配置

    支持从 markdown 代码块中提取 JSON，格式如：
    ```json
    {"chart_type": "line", "x_data": [...], "y_data": [...]}
    ```

    Args:
        text: 要解析的文本内容

    Returns:
        提取到的图表配置列表（已转换为完整的 ECharts 格式）
    """
    import re
    import json

    charts = []

    if not text:
        return charts

    # 尝试匹配 markdown 代码块中的 JSON
    # 格式：```json ... ``` 或 ``` ... ```
    code_block_pattern = r'```(?:json)?\s*\n(\{[\s\S]*?\})\s*```'
    matches = re.findall(code_block_pattern, text)

    for json_str in matches:
        try:
            chart_data = json.loads(json_str)
            # 检查是否是简化格式（包含 x_data 和 y_data）
            if "x_data" in chart_data and "y_data" in chart_data:
                echarts_option = convert_simple_chart_to_echarts(chart_data)
                if echarts_option:
                    charts.append(echarts_option)
            # 如果已经是完整的 ECharts 格式，直接添加
            elif "xAxis" in chart_data or "series" in chart_data:
                charts.append(chart_data)
        except (json.JSONDecodeError, TypeError):
            continue

    return charts

