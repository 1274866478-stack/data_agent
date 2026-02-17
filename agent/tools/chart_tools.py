# -*- coding: utf-8 -*-
"""
Chart Tools - 图表配置生成工具
==================================

为 AgentV2 提供图表配置生成能力（不依赖 MCP ECharts）。

核心功能:
    - generate_bar_chart: 生成柱状图配置 JSON
    - generate_line_chart: 生成折线图配置 JSON
    - generate_pie_chart: 生成饼图配置 JSON
    - generate_table_chart: 生成表格配置 JSON
    - generate_scatter_chart: 生成散点图配置 JSON
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool, BaseTool
from pydantic import BaseModel, Field


class BarChartInput(BaseModel):
    """柱状图输入"""
    data: str = Field(description="图表数据，JSON数组字符串: [{\"category\": \"名称\", \"value\": 数值}]")
    title: str = Field(default="图表", description="图表标题")
    x_field: str = Field(default="category", description="X轴字段名")
    y_field: str = Field(default="value", description="Y轴字段名")


def generate_bar_chart_func(data: str, title: str = "图表", x_field: str = "category", y_field: str = "value") -> str:
    """生成柱状图配置"""
    import json
    try:
        data_list = json.loads(data) if isinstance(data, str) else data
        return json.dumps({
            "chart_type": "bar",
            "title": title,
            "data": data_list,
            "xField": x_field,
            "yField": y_field,
            "success": True
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "success": False}, ensure_ascii=False)


class LineChartInput(BaseModel):
    """折线图输入"""
    data: str = Field(description="图表数据，JSON数组字符串: [{\"time\": \"时间\", \"value\": 数值}]")
    title: str = Field(default="图表", description="图表标题")
    x_field: str = Field(default="time", description="X轴字段名")
    y_field: str = Field(default="value", description="Y轴字段名")


def generate_line_chart_func(data: str, title: str = "图表", x_field: str = "time", y_field: str = "value") -> str:
    """生成折线图配置"""
    import json
    try:
        data_list = json.loads(data) if isinstance(data, str) else data
        return json.dumps({
            "chart_type": "line",
            "title": title,
            "data": data_list,
            "xField": x_field,
            "yField": y_field,
            "success": True
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "success": False}, ensure_ascii=False)


class PieChartInput(BaseModel):
    """饼图输入"""
    data: str = Field(description="图表数据，JSON数组字符串: [{\"category\": \"名称\", \"value\": 数值}]")
    title: str = Field(default="图表", description="图表标题")
    color_field: str = Field(default="category", description="分类字段名")
    angle_field: str = Field(default="value", description="数值字段名")


def generate_pie_chart_func(data: str, title: str = "图表", color_field: str = "category", angle_field: str = "value") -> str:
    """生成饼图配置"""
    import json
    try:
        data_list = json.loads(data) if isinstance(data, str) else data
        return json.dumps({
            "chart_type": "pie",
            "title": title,
            "data": data_list,
            "colorField": color_field,
            "angleField": angle_field,
            "success": True
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "success": False}, ensure_ascii=False)


class TableChartInput(BaseModel):
    """表格输入"""
    data: str = Field(description="表格数据，JSON数组字符串: [{\"col1\": \"值1\", \"col2\": \"值2\"}]")
    title: str = Field(default="表格", description="表格标题")


def generate_table_chart_func(data: str, title: str = "表格") -> str:
    """生成表格配置"""
    import json
    try:
        data_list = json.loads(data) if isinstance(data, str) else data
        return json.dumps({
            "chart_type": "table",
            "title": title,
            "data": data_list,
            "success": True
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "success": False}, ensure_ascii=False)


class ScatterChartInput(BaseModel):
    """散点图输入"""
    data: str = Field(description="图表数据，JSON数组字符串: [{\"x\": 数值1, \"y\": 数值2}]")
    title: str = Field(default="散点图", description="图表标题")
    x_field: str = Field(default="x", description="X轴字段名")
    y_field: str = Field(default="y", description="Y轴字段名")


def generate_scatter_chart_func(data: str, title: str = "散点图", x_field: str = "x", y_field: str = "y") -> str:
    """生成散点图配置"""
    import json
    try:
        data_list = json.loads(data) if isinstance(data, str) else data
        return json.dumps({
            "chart_type": "scatter",
            "title": title,
            "data": data_list,
            "xField": x_field,
            "yField": y_field,
            "success": True
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "success": False}, ensure_ascii=False)


class AreaChartInput(BaseModel):
    """面积图输入"""
    data: str = Field(description="图表数据，JSON数组字符串: [{\"time\": \"时间\", \"value\": 数值}]")
    title: str = Field(default="面积图", description="图表标题")
    x_field: str = Field(default="time", description="X轴字段名")
    y_field: str = Field(default="value", description="Y轴字段名")


def generate_area_chart_func(data: str, title: str = "面积图", x_field: str = "time", y_field: str = "value") -> str:
    """生成面积图配置"""
    import json
    try:
        data_list = json.loads(data) if isinstance(data, str) else data
        return json.dumps({
            "chart_type": "area",
            "title": title,
            "data": data_list,
            "xField": x_field,
            "yField": y_field,
            "success": True
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "success": False}, ensure_ascii=False)


# 创建工具实例
generate_bar_chart = StructuredTool.from_function(
    func=generate_bar_chart_func,
    name="generate_bar_chart",
    description="生成柱状图配置。输入: JSON数据 [{\"category\": \"名称\", \"value\": 数值}]，可选参数 title（标题）、x_field（X轴字段）、y_field（Y轴字段）",
    args_schema=BarChartInput,
)

generate_line_chart = StructuredTool.from_function(
    func=generate_line_chart_func,
    name="generate_line_chart",
    description="生成折线图配置。输入: JSON数据 [{\"time\": \"时间\", \"value\": 数值}]，可选参数 title（标题）、x_field（X轴字段）、y_field（Y轴字段）",
    args_schema=LineChartInput,
)

generate_pie_chart = StructuredTool.from_function(
    func=generate_pie_chart_func,
    name="generate_pie_chart",
    description="生成饼图配置。输入: JSON数据 [{\"category\": \"名称\", \"value\": 数值}]，可选参数 title（标题）、color_field（分类字段）、angle_field（数值字段）",
    args_schema=PieChartInput,
)

generate_table_chart = StructuredTool.from_function(
    func=generate_table_chart_func,
    name="generate_table_chart",
    description="生成表格配置。输入: JSON数据 [{\"col1\": \"值1\", \"col2\": \"值2\"}]，可选参数 title（标题）",
    args_schema=TableChartInput,
)

generate_scatter_chart = StructuredTool.from_function(
    func=generate_scatter_chart_func,
    name="generate_scatter_chart",
    description="生成散点图配置。输入: JSON数据 [{\"x\": 数值1, \"y\": 数值2}]，可选参数 title（标题）、x_field（X轴字段）、y_field（Y轴字段）",
    args_schema=ScatterChartInput,
)

generate_area_chart = StructuredTool.from_function(
    func=generate_area_chart_func,
    name="generate_area_chart",
    description="生成面积图配置。输入: JSON数据 [{\"time\": \"时间\", \"value\": 数值}]，可选参数 title（标题）、x_field（X轴字段）、y_field（Y轴字段）",
    args_schema=AreaChartInput,
)


def get_chart_tools() -> List[BaseTool]:
    """获取所有图表工具"""
    return [
        generate_bar_chart,
        generate_line_chart,
        generate_pie_chart,
        generate_table_chart,
        generate_scatter_chart,
        generate_area_chart,
    ]


# 向后兼容的别名
create_chart_tools = get_chart_tools
