"""
Agent服务模块
集成 LangGraph SQL Agent 功能到后端API
"""
import sys
import os
import base64
import re
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

# 添加 Agent 目录到 Python 路径
# agent_service.py 位于 backend/src/app/services/
# 需要向上到项目根目录，然后进入 Agent 目录
_agent_path = Path(__file__).parent.parent.parent.parent.parent / "Agent"
if _agent_path.exists() and str(_agent_path) not in sys.path:
    sys.path.insert(0, str(_agent_path))

try:
    from sql_agent import run_agent
    from models import VisualizationResponse
    _agent_available = True
except ImportError as e:
    logger.warning(f"Agent模块导入失败: {e}，Agent功能将不可用")
    _agent_available = False
    run_agent = None
    VisualizationResponse = None


def extract_chart_path_from_answer(answer: str) -> Optional[str]:
    """
    从answer文本中提取图表路径
    
    Args:
        answer: Agent返回的answer文本
    
    Returns:
        图表路径，如果未找到则返回None
    """
    if not answer:
        return None
    
    # 匹配图表路径模式：图表已保存: <path> 或 图表链接: <url>
    patterns = [
        r'图表已保存:\s*([^\n]+)',
        r'图表链接:\s*([^\n]+)',
        r'📊\s*图表已保存:\s*([^\n]+)',
        r'📊\s*图表链接:\s*([^\n]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, answer)
        if match:
            path = match.group(1).strip()
            # 如果是URL，直接返回
            if path.startswith('http://') or path.startswith('https://'):
                return path
            # 如果是本地路径，返回绝对路径
            if os.path.exists(path):
                return os.path.abspath(path)
            # 尝试相对于Agent目录的路径
            agent_charts_dir = _agent_path / "charts"
            if agent_charts_dir.exists():
                chart_path = agent_charts_dir / os.path.basename(path)
                if chart_path.exists():
                    return str(chart_path.absolute())
    
    return None


def load_chart_as_base64(chart_path: str) -> Optional[str]:
    """
    将图表文件加载为Base64编码
    
    Args:
        chart_path: 图表文件路径
    
    Returns:
        Base64编码的图片数据（data URI格式），如果失败则返回None
    """
    try:
        if not os.path.exists(chart_path):
            logger.warning(f"图表文件不存在: {chart_path}")
            return None
        
        # 读取文件
        with open(chart_path, 'rb') as f:
            image_data = f.read()
        
        # 确定MIME类型
        ext = os.path.splitext(chart_path)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.html': 'text/html'
        }
        mime_type = mime_types.get(ext, 'image/png')
        
        # 转换为Base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
    
    except Exception as e:
        logger.error(f"加载图表文件失败: {e}", exc_info=True)
        return None


def convert_agent_response_to_query_response(
    agent_response: VisualizationResponse,
    query_id: str,
    tenant_id: str,
    original_query: str,
    processing_time_ms: int = 0
) -> Dict[str, Any]:
    """
    将Agent的VisualizationResponse转换为后端QueryResponseV3格式
    
    Args:
        agent_response: Agent返回的可视化响应
        query_id: 查询ID
        tenant_id: 租户ID
        original_query: 原始查询
        processing_time_ms: 处理时间（毫秒）
    
    Returns:
        Dict: 符合QueryResponseV3格式的字典
    """
    # 将QueryResult转换为字典列表格式
    results = []
    if agent_response.data and agent_response.data.rows:
        for row in agent_response.data.rows:
            row_dict = {}
            for i, col in enumerate(agent_response.data.columns):
                if i < len(row):
                    row_dict[col] = row[i]
            results.append(row_dict)
    
    # 处理图表数据
    chart_data = None
    chart_path = extract_chart_path_from_answer(agent_response.answer or "")
    if chart_path:
        # 如果是本地文件，转换为Base64
        if not (chart_path.startswith('http://') or chart_path.startswith('https://')):
            chart_data = load_chart_as_base64(chart_path)
        else:
            # 如果是URL，直接使用
            chart_data = chart_path
    
    # 构建响应数据
    execution_result = None
    if agent_response.success:
        execution_result = {
            "success": agent_response.success,
            "data_columns": agent_response.data.columns if agent_response.data else [],
            "chart_type": agent_response.chart.chart_type.value if agent_response.chart else None,
            "chart_title": agent_response.chart.title if agent_response.chart else None,
            "chart_data": chart_data  # 添加Base64编码的图表数据或URL
        }
    
    response_data = {
        "query_id": query_id,
        "tenant_id": tenant_id,
        "original_query": original_query,
        "generated_sql": agent_response.sql or "",
        "results": results,
        "row_count": agent_response.data.row_count if agent_response.data else 0,
        "processing_time_ms": processing_time_ms,
        "confidence_score": 0.9 if agent_response.success else 0.5,
        "explanation": agent_response.answer or "",
        "processing_steps": [
            "解析用户查询",
            "生成SQL语句",
            "执行SQL查询",
            "生成可视化响应"
        ] if agent_response.success else ["查询处理失败"],
        "validation_result": {
            "valid": agent_response.success,
            "error": agent_response.error
        } if not agent_response.success else None,
        "execution_result": execution_result,
        "correction_attempts": 0
    }
    
    return response_data


def convert_agent_response_to_chat_response(
    agent_response: VisualizationResponse,
    execution_time: float = 0.0
) -> Dict[str, Any]:
    """
    将Agent的VisualizationResponse转换为前端ChatQueryResponse格式
    
    Args:
        agent_response: Agent返回的可视化响应
        execution_time: 执行时间（秒）
    
    Returns:
        Dict: 符合ChatQueryResponse格式的字典
    """
    # 提取数据源信息（从SQL中推断）
    sources = []
    if agent_response.sql:
        # 简单提取表名（可以改进）
        import re
        table_pattern = r'FROM\s+(\w+)'
        tables = re.findall(table_pattern, agent_response.sql, re.IGNORECASE)
        sources.extend(tables)
    
    # 构建响应
    response = {
        "answer": agent_response.answer or "",
        "sources": sources,
        "reasoning": f"执行了SQL查询：{agent_response.sql}" if agent_response.sql else "",
        "confidence": 0.9 if agent_response.success else 0.5,
        "execution_time": execution_time,
        "sql": agent_response.sql or "",
        "data": {
            "columns": agent_response.data.columns if agent_response.data else [],
            "rows": agent_response.data.rows if agent_response.data else [],
            "row_count": agent_response.data.row_count if agent_response.data else 0
        } if agent_response.data else None,
        "chart": {
            "chart_type": agent_response.chart.chart_type.value if agent_response.chart else None,
            "title": agent_response.chart.title if agent_response.chart else None,
            "x_field": agent_response.chart.x_field if agent_response.chart else None,
            "y_field": agent_response.chart.y_field if agent_response.chart else None,
            "chart_data": load_chart_as_base64(extract_chart_path_from_answer(agent_response.answer or "") or "") if extract_chart_path_from_answer(agent_response.answer or "") else None
        } if agent_response.chart and agent_response.chart.chart_type.value != "table" else None
    }
    
    return response


async def run_agent_query(
    question: str,
    thread_id: str,
    database_url: Optional[str] = None,
    verbose: bool = False
) -> Optional[VisualizationResponse]:
    """
    运行Agent查询
    
    Args:
        question: 用户问题
        thread_id: 线程ID（用于会话管理）
        database_url: 数据库连接URL（可选，如果不提供则使用Agent配置）
        verbose: 是否显示详细输出
    
    Returns:
        VisualizationResponse: Agent响应，如果失败则返回None
    """
    if not _agent_available:
        logger.error("Agent模块不可用")
        return None
    
    try:
        # 如果提供了数据库URL，临时更新Agent配置
        if database_url:
            from config import config
            original_url = config.database_url
            config.database_url = database_url
        
        # 运行Agent
        response = await run_agent(question, thread_id, verbose=verbose)
        
        # 恢复原始配置
        if database_url:
            config.database_url = original_url
        
        return response
    
    except Exception as e:
        logger.error(f"Agent查询失败: {e}", exc_info=True)
        return None


def is_agent_available() -> bool:
    """检查Agent是否可用"""
    return _agent_available

