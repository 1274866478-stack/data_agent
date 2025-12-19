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
    from models import VisualizationResponse
    # 优先使用新版本的 run_agent（支持 enable_echarts）
    try:
        from app.services.agent.agent_service import run_agent
        _use_new_agent = True
        logger.info("使用新版本 Agent (支持 enable_echarts)")
    except ImportError:
        # 回退到旧版本
        from sql_agent import run_agent as run_agent_legacy
        run_agent = run_agent_legacy
        _use_new_agent = False
        logger.info("使用旧版本 Agent (不支持 enable_echarts)")
    _agent_available = True
except ImportError as e:
    logger.warning(f"Agent模块导入失败: {e}，Agent功能将不可用")
    _agent_available = False
    run_agent = None
    _use_new_agent = False
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
    
    # 处理图表数据 - 优先使用 chart.chart_image 字段
    chart_data = None
    if agent_response.chart and agent_response.chart.chart_image:
        # 直接使用 chart_image 字段（已经是 Base64 data URI 或 HTTP URL）
        chart_data = agent_response.chart.chart_image
    else:
        # 降级：尝试从 answer 中提取（向后兼容）
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
            "chart_data": chart_data,  # 添加Base64编码的图表数据或URL
            "echarts_option": agent_response.echarts_option  # 添加 ECharts 配置选项
        }
    
    # 🔴 第三道防线：提取metadata（如果存在）
    metadata = None
    if hasattr(agent_response, "metadata") and agent_response.metadata:
        metadata = agent_response.metadata
    elif hasattr(agent_response, "__dict__") and "metadata" in agent_response.__dict__:
        metadata = agent_response.__dict__["metadata"]
    
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
        "correction_attempts": 0,
        # 在顶层也添加 echarts_option，方便前端直接访问
        "echarts_option": agent_response.echarts_option,
        # 🔴 第三道防线：添加metadata供前端使用
        "metadata": metadata
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
            "chart_image": agent_response.chart.chart_image if agent_response.chart else None,  # 使用 chart_image 字段
            # 向后兼容：如果 chart_image 不存在，尝试从 answer 中提取
            "chart_data": agent_response.chart.chart_image if (agent_response.chart and agent_response.chart.chart_image) else (
                load_chart_as_base64(extract_chart_path_from_answer(agent_response.answer or "") or "") if extract_chart_path_from_answer(agent_response.answer or "") else None
            )
        } if agent_response.chart and agent_response.chart.chart_type.value != "table" else None,
        "echarts_option": agent_response.echarts_option  # 添加 ECharts 配置选项
    }
    
    return response


async def run_agent_query(
    question: str,
    thread_id: str,
    database_url: Optional[str] = None,
    verbose: bool = False,
    enable_echarts: bool = True  # 默认启用 ECharts 功能
) -> Optional[VisualizationResponse]:
    """
    运行Agent查询
    
    Args:
        question: 用户问题
        thread_id: 线程ID（用于会话管理）
        database_url: 数据库连接URL（可选，如果不提供则使用Agent配置）
        verbose: 是否显示详细输出
        enable_echarts: 是否启用 ECharts 图表生成功能（默认启用）
    
    Returns:
        VisualizationResponse: Agent响应，如果失败则返回None
    """
    logger.info(
        "run_agent_query called",
        extra={
            "question_preview": question[:100],
            "thread_id": thread_id,
            "has_database_url": bool(database_url),
            "agent_available": _agent_available,
        },
    )
    if not _agent_available:
        logger.error("Agent模块不可用，直接返回 None")
        return None
    
    try:
        # 如果提供了数据库URL，临时更新Agent配置
        original_url = None
        if database_url:
            from config import config
            original_url = getattr(config, "database_url", None)
            logger.info(
                "Temporarily overriding Agent database_url",
                extra={
                    "old_url_preview": str(original_url)[:80] if original_url else None,
                    "new_url_preview": str(database_url)[:80],
                },
            )
            config.database_url = database_url
        
        # 运行Agent
        logger.info(
            "Starting underlying LangGraph Agent run",
            extra={"thread_id": thread_id, "enable_echarts": enable_echarts},
        )
        # 根据使用的 Agent 版本调用不同的函数
        if _use_new_agent:
            # 新版本：需要传递 database_url，返回 Dict 包含 response 字段
            from config import config as agent_config
            effective_db_url = database_url or getattr(agent_config, "database_url", None)
            if not effective_db_url:
                logger.error("无法获取数据库连接URL")
                return None
            result = await run_agent(
                question=question,
                database_url=effective_db_url,
                thread_id=thread_id,
                enable_echarts=enable_echarts,
                verbose=verbose
            )
            # 新版本返回 Dict，提取 response 字段（VisualizationResponse 对象）
            if result and isinstance(result, dict) and "response" in result:
                response = result["response"]
                # 🔴 第三道防线：将metadata附加到response对象
                if "metadata" in result:
                    # 将metadata作为属性附加到response对象
                    response.metadata = result["metadata"]
            else:
                response = None
        else:
            # 旧版本：不支持 enable_echarts 参数
            response = await run_agent(question, thread_id, verbose=verbose)
        logger.info(
            "Underlying LangGraph Agent finished",
            extra={
                "success": getattr(response, "success", None) if response else None,
                "sql_preview": (response.sql or "")[:120] if getattr(response, "sql", None) else None,
                "row_count": getattr(getattr(response, "data", None), "row_count", None) if response else None,
                "error": getattr(response, "error", None) if response else None,
            },
        )
        
        # 恢复原始配置
        if database_url and original_url is not None:
            from config import config
            logger.info("Restoring original Agent database_url")
            config.database_url = original_url
        
        return response
    
    except Exception as e:
        logger.error("Agent查询失败", extra={"error": str(e)}, exc_info=True)
        return None


def is_agent_available() -> bool:
    """检查Agent是否可用"""
    return _agent_available

