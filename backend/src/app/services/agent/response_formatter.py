"""
# Agent 响应格式化器 - API响应标准化

## [HEADER]
**文件名**: response_formatter.py
**职责**: 将内部VisualizationResponse模型转换为前端API期望的响应格式
**作者**: Data Agent Team
**版本**: 1.1.0
**变更记录**:
- v1.1.0 (2026-01-01): 增强Pydantic模型兼容性处理
- v1.0.0 (2025-12-01): 初始版本

## [INPUT]
- VisualizationResponse对象: 包含answer, sql, data, chart等字段
- 错误消息: str - 错误情况下的错误文本

## [OUTPUT]
- API响应字典: Dict[str, Any] - 前端可用的标准化响应
  - answer: str - LLM文字回答
  - table: Dict - 表格数据(可选)
  - chart: Dict - 图表配置(可选)
  - sql: str - SQL语句(可选)
  - echarts_option: Dict - ECharts配置(可选)

## [LINK]
**上游依赖**:
- [models.py](models.py) - VisualizationResponse定义

**下游依赖**:
- [agent_service.py](agent_service.py) - API响应构建

**调用方**:
- API端点 - /api/v1/query, /api/v1/llm/chat等

## [POS]
**路径**: backend/src/app/services/agent/response_formatter.py
**模块层级**: Level 3 (Services → Agent → Response Formatter)
**依赖深度**: 2 层
"""
from typing import Dict, Any, Optional
import logging

from .models import VisualizationResponse, ChartConfig

logger = logging.getLogger(__name__)


def _strip_unwanted_notices(text: Optional[str]) -> str:
    """
    去除前端不需要的固定提示语。
    """
    if not text:
        return ""
    unwanted = [
        "查询已完成，请查看上方的处理步骤。",
        "查询已完成，请查看上方的处理步骤",
    ]
    for phrase in unwanted:
        text = text.replace(phrase, "")
    return text.strip()


def format_api_response(response: VisualizationResponse) -> Dict[str, Any]:
    """
    将 VisualizationResponse 转换为前端期望的 API 响应格式
    
    Args:
        response: VisualizationResponse 对象
    
    Returns:
        前端期望的响应字典，包含 answer, table, chart 等字段
    """
    result: Dict[str, Any] = {
        "answer": _strip_unwanted_notices(response.answer),
        "success": response.success,
    }
    
    # 添加 SQL（如果有）
    if response.sql:
        result["sql"] = response.sql
    
    # 添加表格数据（如果有）
    # 🔧 改进：即使 row_count == 0，也添加空 table 结构以便前端显示"查询结果为空"
    if response.data:
        if response.data.row_count > 0:
            result["table"] = {
                "columns": response.data.columns,
                "rows": [
                    {col: row[i] for i, col in enumerate(response.data.columns)}
                    for row in response.data.rows
                ],
                "row_count": response.data.row_count,
            }
            logger.info(f"✅ [响应格式化] 添加表格数据: {response.data.row_count} 行, {len(response.data.columns)} 列")
        else:
            # 🔥 新增：空结果时也添加 table 结构，让前端显示"查询结果为空"
            result["table"] = {
                "columns": response.data.columns if response.data.columns else [],
                "rows": [],
                "row_count": 0,
                "is_empty": True,  # 标记为空结果
                "message": "查询执行成功，但未返回数据"
            }
            logger.info(f"ℹ️ [响应格式化] 添加空表格结构: {len(response.data.columns)} 列, 0 行")
    else:
        logger.debug(f"ℹ️ [响应格式化] response.data 为空，未添加 table 数据")
    
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

