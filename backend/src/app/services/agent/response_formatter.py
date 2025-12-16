"""
API 响应格式化模块
将 VisualizationResponse 转换为前端期望的格式
"""
from typing import Dict, Any, Optional
import logging

from .models import VisualizationResponse, ChartConfig

logger = logging.getLogger(__name__)


def format_api_response(response: VisualizationResponse) -> Dict[str, Any]:
    """
    将 VisualizationResponse 转换为前端期望的 API 响应格式
    
    Args:
        response: VisualizationResponse 对象
    
    Returns:
        前端期望的响应字典，包含 answer, table, chart 等字段
    """
    result: Dict[str, Any] = {
        "answer": response.answer or "",
        "success": response.success,
    }
    
    # 添加 SQL（如果有）
    if response.sql:
        result["sql"] = response.sql
    
    # 添加表格数据（如果有）
    if response.data and response.data.row_count > 0:
        result["table"] = {
            "columns": response.data.columns,
            "rows": [
                {col: row[i] for i, col in enumerate(response.data.columns)}
                for row in response.data.rows
            ],
            "row_count": response.data.row_count,
        }
    
    # 添加图表配置（如果有）
    if response.chart and response.chart.chart_type.value != "table":
        chart_dict: Dict[str, Any] = {
            "chart_type": response.chart.chart_type.value,
        }
        
        if response.chart.title:
            chart_dict["title"] = response.chart.title
        
        if response.chart.x_field:
            chart_dict["x_field"] = response.chart.x_field
        
        if response.chart.y_field:
            chart_dict["y_field"] = response.chart.y_field
        
        # 添加图表图片（如果有）
        if response.chart.chart_image:
            chart_dict["chart_image"] = response.chart.chart_image
        
        result["chart"] = chart_dict
    
    # 添加错误信息（如果有）
    if response.error:
        result["error"] = response.error
    
    # 添加 ECharts 选项（如果有）
    if response.echarts_option:
        result["echarts_option"] = response.echarts_option
    
    return result


def format_error_response(error_message: str, sql: Optional[str] = None) -> Dict[str, Any]:
    """
    格式化错误响应
    
    Args:
        error_message: 错误消息
        sql: 可选的 SQL 语句（如果执行失败）
    
    Returns:
        错误响应字典
    """
    result: Dict[str, Any] = {
        "answer": f"执行失败: {error_message}",
        "success": False,
        "error": error_message,
    }
    
    if sql:
        result["sql"] = sql
    
    return result

