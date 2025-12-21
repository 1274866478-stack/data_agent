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
    
    # 🛡️ 安全添加图表配置（如果有）- 支持 Pydantic 模型
    if response.chart:
        chart_obj = response.chart
        
        # 安全获取 chart_type
        chart_type_value = None
        if isinstance(chart_obj, dict):
            chart_type_value = chart_obj.get('chart_type')
            if hasattr(chart_type_value, 'value'):
                chart_type_value = chart_type_value.value
        else:
            try:
                if hasattr(chart_obj, 'chart_type') and chart_obj.chart_type:
                    if hasattr(chart_obj.chart_type, 'value'):
                        chart_type_value = chart_obj.chart_type.value
                    else:
                        chart_type_value = str(chart_obj.chart_type)
            except AttributeError:
                pass
        
        # 只有非 table 类型才构建图表配置
        if chart_type_value and chart_type_value != "table":
            chart_dict: Dict[str, Any] = {
                "chart_type": chart_type_value,
            }
            
            # 安全访问其他属性
            if isinstance(chart_obj, dict):
                if chart_obj.get('title'):
                    chart_dict["title"] = chart_obj.get('title')
                if chart_obj.get('x_field'):
                    chart_dict["x_field"] = chart_obj.get('x_field')
                if chart_obj.get('y_field'):
                    chart_dict["y_field"] = chart_obj.get('y_field')
            else:
                try:
                    if hasattr(chart_obj, 'title') and chart_obj.title:
                        chart_dict["title"] = chart_obj.title
                    if hasattr(chart_obj, 'x_field') and chart_obj.x_field:
                        chart_dict["x_field"] = chart_obj.x_field
                    if hasattr(chart_obj, 'y_field') and chart_obj.y_field:
                        chart_dict["y_field"] = chart_obj.y_field
                except AttributeError:
                    pass
        
        # 🛡️ 安全添加图表图片（如果有）- 支持 Pydantic 模型
        chart_image = None
        chart_obj = response.chart
        
        # 尝试多种方式获取 chart_image
        if isinstance(chart_obj, dict):
            chart_image = chart_obj.get('chart_image')
        else:
            # 方法1: 属性访问
            try:
                if hasattr(chart_obj, 'chart_image'):
                    chart_image = getattr(chart_obj, 'chart_image', None)
            except AttributeError:
                pass
            
            # 方法2: Pydantic 的 .dict() 或 .model_dump()
            if not chart_image:
                try:
                    if hasattr(chart_obj, 'dict'):
                        chart_dict_temp = chart_obj.dict()
                        chart_image = chart_dict_temp.get('chart_image')
                    elif hasattr(chart_obj, 'model_dump'):
                        chart_dict_temp = chart_obj.model_dump()
                        chart_image = chart_dict_temp.get('chart_image')
                except (AttributeError, TypeError):
                    pass
        
        # 只有找到有效的图片字符串才添加
        if chart_image and isinstance(chart_image, str) and len(chart_image) > 0:
            chart_dict["chart_image"] = chart_image
        
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


