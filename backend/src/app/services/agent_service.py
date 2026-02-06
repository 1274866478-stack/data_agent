"""
# [AGENT_SERVICE] Agent集成服务

## [HEADER]
**文件名**: agent_service.py
**职责**: 集成LangGraph SQL Agent到后端API，提供Agent响应转换、图表处理、文件/数据库智能路由和幻觉检测功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - Agent集成服务

## [INPUT]
- **question: str** - 用户自然语言问题
- **thread_id: str** - 会话线程ID
- **database_url: Optional[str]** - 数据库连接URL或文件路径（xlsx, csv, /uploads/, /data/等）
- **verbose: bool** - 是否显示详细输出（默认False）
- **enable_echarts: bool** - 是否启用ECharts图表生成（默认True）
- **agent_response: VisualizationResponse** - Agent返回的响应对象
- **query_id: str** - 查询ID
- **tenant_id: str** - 租户ID
- **original_query: str** - 原始查询文本
- **processing_time_ms: int** - 处理时间（毫秒）
- **execution_time: float** - 执行时间（秒）
- **chart_path: str** - 图表文件路径
- **answer: str** - Agent返回的answer文本

## [OUTPUT]
- **VisualizationResponse**: run_agent_query返回Agent响应对象
  - success: bool - 查询是否成功
  - sql: str - 生成的SQL语句
  - answer: str - 自然语言解释
  - data: QueryResult - 查询结果数据
  - chart: ChartConfig - 图表配置
  - echarts_option: Dict - ECharts配置选项
  - metadata: Dict - 元数据（幻觉检测标志等）
- **Dict[str, Any]**: convert_agent_response_to_query_response返回QueryResponseV3格式
  - query_id, tenant_id, original_query
  - generated_sql, results, row_count
  - execution_result: {success, data_columns, chart_type, chart_title, chart_data, echarts_option}
  - explanation, processing_steps, validation_result
  - metadata: {hallucination_detected, hallucination_reason}
- **Dict[str, Any]**: convert_agent_response_to_chat_response返回ChatQueryResponse格式
  - answer, sources, reasoning, confidence, execution_time
  - sql, data: {columns, rows, row_count}
  - chart: {chart_type, title, x_field, y_field, chart_image, chart_data}
  - echarts_option: Dict
- **Optional[str]**: extract_chart_path_from_answer返回提取的图表路径或URL
- **Optional[str]**: load_chart_as_base64返回Base64编码的图片数据（data URI格式）
- **bool**: is_agent_available返回Agent是否可用

**上游依赖** (已读取源码):
- [Agent/models.py](../../Agent/models.py) - Agent数据模型（VisualizationResponse）
- [Agent/sql_agent.py](../../Agent/sql_agent.py) - 旧版Agent（run_agent）
- [Agent/app/services/agent_service.py](../../Agent/app/services/agent_service.py) - 新版Agent（支持enable_echarts）
- [Agent/config.py](../../Agent/config.py) - Agent配置

**下游依赖** (需要反向索引分析):
- [../api/v1/endpoints/query.py](../api/v1/endpoints/query.py) - 查询API端点
- [../api/v1/endpoints/llm.py](../api/v1/endpoints/llm.py) - LLM API端点
- [llm_service.py](./llm_service.py) - LLM服务（Agent查询集成）

**调用方**:
- 自然语言查询API
- 聊天对话中的查询功能
- Agent查询健康检查

## [STATE]
- **Agent路径管理**: 动态添加Agent目录到sys.path
- **版本兼容**: 支持新旧两个版本Agent（_use_new_agent标志）
  - 新版本: 支持enable_echarts参数，返回{response: VisualizationResponse}
  - 旧版本: 不支持enable_echarts，直接返回VisualizationResponse
- **降级机制**: Agent导入失败时设置_agent_available=False，不阻塞应用启动
- **文件/数据库路由**: 早期检测database_url类型（文件扩展名、本地路径、数据库协议）
- **幻觉检测**: 三道防线
  1. metadata.hallucination_detected标志
  2. answer字段假数据模式二次检查（正则匹配测试名）
  3. safe_get安全属性访问（防止Pydantic/字典访问错误）
- **Prompt注入**: 根据路由模式注入不同的系统指令（文件模式禁用SQL工具）
- **配置临时覆盖**: 运行时临时覆盖Agent的database_url配置（查询后恢复）

## [SIDE-EFFECTS]
- **路径操作**: 修改sys.path插入Agent目录
- **模块导入**: 动态导入Agent模块（sql_agent, models, config, agent_service）
- **文件I/O**: load_chart_as_base64读取图表文件
- **Base64编码**: 图表文件转换为Base64 data URI
- **正则匹配**: 提取图表路径、检测假数据模式、提取SQL表名
- **配置修改**: 临时覆盖Agent config.database_url（查询后恢复原值）
- **Prompt工程**: 注入系统指令到用户问题（enhanced_question）
- **异常处理**: 大量try-except保护Agent调用和属性访问
- **日志记录**: 详细的路由、配置、查询执行日志
- **类型转换**: Pydantic模型转字典（metadata, chart等对象的.dict()或.model_dump()）
- **URL清理**: 文件模式下清理database_url防止Postgres工具崩溃

## [POS]
**路径**: backend/src/app/services/agent_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 跨模块依赖Agent目录（外部依赖）
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

# 导入统计分析服务
try:
    from .stats_analysis_service import get_stats_service
    _stats_analysis_available = True
    logger.info("✅ 统计分析服务已加载")
except ImportError as e:
    _stats_analysis_available = False
    get_stats_service = None
    logger.warning(f"⚠️ 统计分析服务导入失败: {e}，统计功能将不可用")

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

    # 🔥 【QA集成】导入错误追踪模块
    try:
        from error_tracker import error_tracker, log_agent_error, ErrorCategory
        _error_tracking_available = True
        logger.info("✅ 错误追踪模块已加载")
    except ImportError as track_err:
        _error_tracking_available = False
        error_tracker = None
        logger.warning(f"⚠️ 错误追踪模块导入失败: {track_err}，错误追踪功能将不可用")
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


def _build_processing_steps(
    success: bool,
    sql: str,
    results: list,
    row_count: int,
    data_obj: Any,
    echarts_option: Any,
    chart_data: Any,
    chart_obj: Any,
    processing_time_ms: int,
    answer: str = ""
) -> list:
    """
    构建包含SQL、表格、图表、数据分析文本的处理步骤列表
    
    🆕 优化：隐藏技术性步骤，只展示业务相关步骤

    Args:
        success: 查询是否成功
        sql: SQL语句
        results: 查询结果列表
        row_count: 行数
        data_obj: 数据对象
        echarts_option: ECharts配置
        chart_data: 图表数据
        chart_obj: 图表对象
        processing_time_ms: 处理时间
        answer: AI数据分析文本（用于步骤8）

    Returns:
        list: 处理步骤列表（已过滤技术步骤）
    """
    if not success:
        return [{
            "step": 1,
            "title": "查询处理失败",
            "description": "无法处理您的请求，请检查数据源配置或重新提问",
            "status": "error"
        }]

    # 计算各步骤的大致耗时（估算）
    # 🆕 优化：减少步骤数量，只保留关键业务步骤
    base_time = processing_time_ms / 5  # 现在有5个关键业务步骤

    # 构建表格数据（用于步骤4）
    table_data = None
    if data_obj:
        columns = safe_get_attr(data_obj, 'columns', [])
        rows = safe_get_attr(data_obj, 'rows', [])
        if columns and rows:
            table_data = {
                "columns": columns,
                "rows": rows[:50],  # 限制最多50行
                "row_count": row_count
            }

    # 构建图表数据（用于步骤5）
    chart_step_data = None
    if echarts_option:
        chart_step_data = {
            "echarts_option": echarts_option,
            "chart_type": _extract_chart_type(chart_obj)
        }
    elif chart_data:
        chart_step_data = {
            "chart_image": chart_data,
            "chart_type": _extract_chart_type(chart_obj)
        }

    # 🆕 优化：只保留关键业务步骤，隐藏技术步骤
    steps = [
        {
            "step": 1,
            "title": "理解查询意图",
            "description": "分析用户查询意图，识别数据需求",
            "status": "completed",
            "duration": int(base_time)
        },
        {
            "step": 2,
            "title": "生成查询语句",
            "description": "AI已生成数据库查询语句",
            "status": "completed",
            "duration": int(base_time * 1.5),
            "content_type": "sql",
            "content_data": {
                "sql": sql
            } if sql else None
        },
        {
            "step": 3,
            "title": "执行数据查询",
            "description": f"查询返回 {row_count} 行结果",
            "status": "completed",
            "duration": int(base_time * 2),
            "content_type": "table",
            "content_data": {
                "table": table_data
            } if table_data else None
        },
    ]

    # 添加步骤4（图表生成）
    if chart_step_data:
        steps.append({
            "step": 4,
            "title": "生成数据可视化",
            "description": f"创建 {chart_step_data.get('chart_type', '图表')} 展示分析结果",
            "status": "completed",
            "duration": int(base_time * 2),
            "content_type": "chart",
            "content_data": {
                "chart": chart_step_data
            }
        })

    # 添加步骤5（数据分析总结）
    if answer and answer.strip():
        steps.append({
            "step": len(steps) + 1,
            "title": "输出分析结论",
            "description": "AI对查询结果的分析和解读",
            "status": "completed",
            "duration": int(base_time * 1.5),
            "content_type": "text",
            "content_data": {
                "text": answer.strip()
            }
        })

    return steps


def _extract_chart_type(chart_obj: Any) -> str:
    """安全提取图表类型"""
    if not chart_obj:
        return "图表"

    # 尝试从chart_obj中提取类型
    if hasattr(chart_obj, 'chart_type'):
        chart_type = getattr(chart_obj, 'chart_type')
        if hasattr(chart_type, 'value'):
            return str(chart_type.value)
        return str(chart_type)

    if isinstance(chart_obj, dict):
        return chart_obj.get('chart_type', '图表')

    return "图表"


def safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """安全获取对象属性"""
    try:
        if hasattr(obj, attr):
            return getattr(obj, attr)
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return default
    except Exception:
        return default


def _format_stats_analysis(stats: Dict[str, Any]) -> str:
    """
    将统计分析结果格式化为关键数据点摘要（非固定模板）

    关键设计原则：
    1. 只提供"值得报告"的关键数据点
    2. 根据数据特征动态选择报告内容
    3. 避免机械式列出所有统计指标
    4. 让 LLM 基于这些关键点生成动态分析

    Args:
        stats: 统计分析结果字典

    Returns:
        格式化后的关键数据点摘要
    """
    if not stats:
        return ""

    key_points = []

    # 1. 基础信息（始终提供）
    basic_stats = stats.get('basic_stats', {})
    if basic_stats:
        count = basic_stats.get('count', 0)
        total = basic_stats.get('total', 0)
        mean = basic_stats.get('mean', 0)
        key_points.append(f"数据量: {count} 条, 总计: {total}, 平均: {mean}")

    # 2. 趋势分析（仅当有明显趋势时报告）
    trend = stats.get('trend_analysis', {})
    if trend and 'error' not in trend:
        total_growth = trend.get('total_growth_percent', 0)
        volatility = trend.get('volatility', 0)
        trend_dir = trend.get('trend_direction', '')

        # 只有当变化幅度 > 5% 或波动性 > 10% 时才报告趋势
        if abs(total_growth) > 5 or volatility > 10:
            key_points.append(f"趋势: {trend_dir} {total_growth:+.1f}%, 波动性: {volatility:.1f}%")

    # 3. 异常值（仅当存在异常值时报告）
    extremes = stats.get('extremes', {})
    if extremes:
        outlier_count = extremes.get('outliers_count', 0)
        if outlier_count > 0:
            key_points.append(f"检测到 {outlier_count} 个异常值")

    # 4. 极值（仅当极值与平均值差异较大时报告）
    if extremes and basic_stats:
        max_val = extremes.get('max_value')
        min_val = extremes.get('min_value')
        mean_val = basic_stats.get('mean', 0)

        # 计算极值与平均值的偏离程度
        if max_val and mean_val > 0:
            max_deviation = abs(max_val - mean_val) / mean_val * 100
            if max_deviation > 30:  # 最大值偏离平均值超过30%
                key_points.append(f"峰值显著: {max_val} (偏离平均 {max_deviation:.0f}%)")

        if min_val and mean_val > 0:
            min_deviation = abs(min_val - mean_val) / mean_val * 100
            if min_deviation > 30:  # 最小值偏离平均值超过30%
                key_points.append(f"谷值显著: {min_val} (偏离平均 {min_deviation:.0f}%)")

    # 5. 数据稳定性（仅当变异系数较高时报告）
    if basic_stats:
        cv_percent = basic_stats.get('cv_percent', 0)
        if cv_percent > 20:  # 变异系数超过20%表示数据不稳定
            key_points.append(f"数据波动较大 (变异系数: {cv_percent:.1f}%)")

    # 如果没有关键数据点，提供最基本的信息
    if not key_points:
        count = basic_stats.get('count', 'N/A')
        total = basic_stats.get('total', 'N/A')
        mean = basic_stats.get('mean', 'N/A')
        return f"\n【统计】 {count} 条数据, 总计 {total}, 平均 {mean}" if basic_stats else ""

    return "\n【关键数据点】\n" + "\n".join(f"• {p}" for p in key_points)


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
    # 🛡️ 通用安全属性访问辅助函数 - 支持 Pydantic 模型、字典和普通对象
    def safe_get(obj, attr, default=None):
        """
        安全获取对象属性，支持多种数据类型
        
        Args:
            obj: 对象（可以是 Pydantic 模型、字典或普通对象）
            attr: 属性名
            default: 默认值
        
        Returns:
            属性值，如果不存在则返回默认值
        """
        try:
            # Case 1: 字典类型
            if isinstance(obj, dict):
                return obj.get(attr, default)
            
            # Case 2: Pydantic 模型或其他对象
            # 方法1: 直接属性访问
            if hasattr(obj, attr):
                value = getattr(obj, attr, default)
                # 如果值是 None，也返回默认值（可选，根据需求调整）
                return value if value is not None else default
            
            # 方法2: 尝试使用 Pydantic 的 .dict() 或 .model_dump()
            try:
                if hasattr(obj, 'dict'):
                    obj_dict = obj.dict()
                    return obj_dict.get(attr, default)
                elif hasattr(obj, 'model_dump'):
                    obj_dict = obj.model_dump()
                    return obj_dict.get(attr, default)
            except (AttributeError, TypeError):
                pass
            
            # 方法3: 尝试 __dict__ 属性
            try:
                if hasattr(obj, '__dict__'):
                    return obj.__dict__.get(attr, default)
            except (AttributeError, TypeError):
                pass
            
            return default
        except Exception as e:
            logger.debug(f"safe_get 访问属性 {attr} 时出错: {e}")
            return default
    
    # 将QueryResult转换为字典列表格式
    results = []
    data_obj = safe_get(agent_response, 'data')
    if data_obj:
        rows = safe_get(data_obj, 'rows', [])
        columns = safe_get(data_obj, 'columns', [])
        if rows:
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    if i < len(row):
                        row_dict[col] = row[i]
                results.append(row_dict)
    
    # 🛡️ 健壮的图表图片提取 - 支持 Pydantic 模型、字典和普通对象
    chart_data = None
    chart_obj = safe_get(agent_response, 'chart')
    if chart_obj:
        # 使用 safe_get 获取 chart_image
        chart_data = safe_get(chart_obj, 'chart_image')
    
    # 降级：如果 chart_image 不存在，尝试从 answer 中提取（向后兼容）
    if not chart_data:
        answer = safe_get(agent_response, 'answer', '')
        chart_path = extract_chart_path_from_answer(answer)
        if chart_path:
            # 如果是本地文件，转换为Base64
            if not (chart_path.startswith('http://') or chart_path.startswith('https://')):
                chart_data = load_chart_as_base64(chart_path)
            else:
                # 如果是URL，直接使用
                chart_data = chart_path
    
    # 构建响应数据
    execution_result = None
    success = safe_get(agent_response, 'success', False)
    if success:
        # 🛡️ 安全访问所有 chart 属性
        chart_type = None
        chart_title = None
        chart_obj = safe_get(agent_response, 'chart')
        if chart_obj:
            chart_type_obj = safe_get(chart_obj, 'chart_type')
            if chart_type_obj:
                if hasattr(chart_type_obj, 'value'):
                    chart_type = chart_type_obj.value
                else:
                    chart_type = str(chart_type_obj)
            chart_title = safe_get(chart_obj, 'title')
        
        # 🛡️ 安全访问 data 属性
        data_obj = safe_get(agent_response, 'data')
        data_columns = []
        if data_obj:
            data_columns = safe_get(data_obj, 'columns', [])
        
        execution_result = {
            "success": success,
            "data_columns": data_columns,
            "chart_type": chart_type,
            "chart_title": chart_title,
            "chart_data": chart_data,  # 添加Base64编码的图表数据或URL
            "echarts_option": safe_get(agent_response, 'echarts_option')  # 🛡️ 安全访问 ECharts 配置选项
        }
    
    # 🔴 第三道防线：提取metadata（如果存在）- 使用 safe_get
    metadata = safe_get(agent_response, 'metadata')
    if metadata and not isinstance(metadata, dict):
        # 如果是 Pydantic 模型，转换为字典
        try:
            if hasattr(metadata, 'dict'):
                metadata = metadata.dict()
            elif hasattr(metadata, 'model_dump'):
                metadata = metadata.model_dump()
            elif hasattr(metadata, '__dict__'):
                metadata = metadata.__dict__
        except Exception:
            metadata = None
    
    # 🔥 优先级1和4：检查幻觉检测标志和进行二次检查
    explanation = safe_get(agent_response, 'answer', '')
    hallucination_detected_in_metadata = False
    hallucination_reason_in_metadata = None
    
    # 检查metadata中的幻觉标志
    if metadata and isinstance(metadata, dict):
        hallucination_detected_in_metadata = metadata.get("hallucination_detected", False)
        hallucination_reason_in_metadata = metadata.get("hallucination_reason", None)
    
    # 如果metadata中检测到幻觉，使用错误消息替换explanation
    if hallucination_detected_in_metadata:
        error_message = (
            "⚠️ **数据验证失败**\n\n"
            "系统检测到AI助手可能返回了不准确的数据。\n\n"
        )
        if hallucination_reason_in_metadata:
            if isinstance(hallucination_reason_in_metadata, list):
                error_message += f"**检测详情：** {', '.join(hallucination_reason_in_metadata)}\n\n"
            else:
                error_message += f"**检测详情：** {hallucination_reason_in_metadata}\n\n"
        error_message += (
            "**可能的原因：**\n"
            "- AI未能正确调用数据查询工具\n"
            "- 工具返回的数据为空或错误\n"
            "- AI生成了测试数据而非真实数据\n\n"
            "**建议操作：**\n"
            "1. 请检查数据源是否正确配置\n"
            "2. 确认数据源已成功加载（状态显示为✓）\n"
            "3. 重新提问您的问题\n"
        )
        explanation = error_message
        # 清除可能包含假数据的结果
        results = []
        logger.error(f"🚫 [响应转换] 检测到metadata中的幻觉标志，已拦截并替换explanation")
    
    # 🔥 优先级4：二次检查 - 即使metadata中没有标志，也要检查answer字段是否包含假数据
    if not hallucination_detected_in_metadata and explanation:
        import re
        # 检测常见的假数据模式
        fake_data_patterns = [
            r"张三|李四|王五|赵六",  # 常见的中文测试名字
            r"用户[1-9]\d*",  # 用户1、用户2等
            r"Alice|Bob|Charlie|Diana|Eve",  # 常见的英文测试名字
        ]
        detected_patterns = []
        for pattern in fake_data_patterns:
            if re.search(pattern, explanation):
                detected_patterns.append(pattern)

        # 如果检测到多个假数据模式，很可能是假数据
        if len(detected_patterns) >= 2:
            error_message = (
                "⚠️ **数据验证失败**\n\n"
                "系统检测到回答中可能包含测试数据而非真实数据。\n\n"
                "**检测到的可疑模式：**\n"
                f"- {', '.join(detected_patterns)}\n\n"
                "**可能的原因：**\n"
                "- AI未能正确调用数据查询工具\n"
                "- 工具返回的数据为空或错误\n"
                "- AI生成了测试数据而非真实数据\n\n"
                "**建议操作：**\n"
                "1. 请检查数据源是否正确配置\n"
                "2. 确认数据源已成功加载（状态显示为✓）\n"
                "3. 重新提问您的问题\n"
            )
            explanation = error_message
            results = []
            logger.error(f"🚫 [响应转换] 二次检查检测到假数据模式，已拦截并替换explanation")

    # 🛡️🛡️🛡️ 安全优先级0：危险 SQL 检查（最高优先级，在假数据检查之前）
    # 检查 explanation 中是否包含危险的 DML/DDL 操作
    if explanation:
        import re
        explanation_upper = explanation.upper()

        # 危险关键字黑名单
        dangerous_keywords = [
            (r'\bUPDATE\b', 'UPDATE'),
            (r'\bDELETE\b', 'DELETE'),
            (r'\bINSERT\b', 'INSERT'),
            (r'\bDROP\b', 'DROP'),
            (r'\bTRUNCATE\b', 'TRUNCATE'),
            (r'\bALTER\b', 'ALTER'),
            (r'\bCREATE\s+TABLE\b', 'CREATE TABLE'),
            (r'\bGRANT\b', 'GRANT'),
            (r'\bREVOKE\b', 'REVOKE'),
        ]

        detected_dangerous = []
        for pattern, keyword in dangerous_keywords:
            if re.search(pattern, explanation_upper):
                detected_dangerous.append(keyword)

        # 检测到危险 SQL - 替换为拒绝消息
        if detected_dangerous:
            security_message = (
                "⛔ **操作被拒绝**\n\n"
                "您请求的操作涉及数据修改，这违反了安全策略。\n\n"
                "🛡️ 作为一个只读数据分析助手，我只能：\n"
                "- ✅ 查询和展示数据（SELECT）\n"
                "- ✅ 分析数据趋势和模式\n"
                "- ✅ 生成数据可视化图表\n"
                "- ❌ 不能修改、删除或新增数据\n\n"
                "如果您需要修改数据，请联系数据库管理员或使用专门的管理工具。"
            )
            explanation = security_message
            results = []  # 清除可能包含危险操作的结果
            logger.error(
                f"🚫 [响应安全检查] 检测到危险SQL关键字并已拦截: {', '.join(detected_dangerous)}",
                extra={
                    "detected_keywords": detected_dangerous,
                    "original_query": original_query[:100]
                }
            )

    # 🆕 深度统计分析增强：从 response 对象获取统计结果，追加到 explanation 中
    # 尝试从 response 对象的 _stats_analysis 属性获取统计结果
    stats_analysis = getattr(agent_response, '_stats_analysis', None)

    # 调试日志
    logger.info(f"🔍 [调试] 检查统计结果: stats_analysis 是否存在 = {stats_analysis is not None}")
    if stats_analysis:
        logger.info(f"🔍 [调试] 统计结果类型: {type(stats_analysis)}, 键: {list(stats_analysis.keys()) if isinstance(stats_analysis, dict) else 'N/A'}")

    if not stats_analysis and metadata and isinstance(metadata, dict):
        # 兼容旧方式：从 metadata 中获取
        stats_analysis = metadata.get('stats_analysis')
        logger.info(f"🔍 [调试] 从 metadata 获取统计结果: {stats_analysis is not None}")

    if stats_analysis and isinstance(stats_analysis, dict) and 'error' not in stats_analysis:
        # 生成统计结果的可读文本
        stats_text = _format_stats_analysis(stats_analysis)

        # 调试日志
        logger.info(f"🔍 [调试] 格式化后统计文本长度: {len(stats_text)}, 前100字符: {stats_text[:100]}")

        # 如果 stats_text 不为空，追加到 explanation
        if stats_text and explanation:
            # 检查是否需要在前面添加分隔符
            if not explanation.endswith('\n'):
                explanation += '\n\n'
            explanation += stats_text
            logger.info("✅ [统计分析] 已将统计结果追加到 explanation 中")
    else:
        if stats_analysis:
            logger.warning(f"⚠️ [统计分析] 统计结果包含错误: {stats_analysis.get('error', 'Unknown error')}")
        else:
            logger.info("ℹ️ [统计分析] 没有可用的统计结果需要追加")

    # 🛡️ 安全访问所有属性
    sql = safe_get(agent_response, 'sql', '')
    data_obj = safe_get(agent_response, 'data')
    row_count = 0
    if data_obj:
        row_count = safe_get(data_obj, 'row_count', 0)

    error = safe_get(agent_response, 'error')
    echarts_option = safe_get(agent_response, 'echarts_option')
    
    response_data = {
        "query_id": query_id,
        "tenant_id": tenant_id,
        "original_query": original_query,
        "generated_sql": sql,
        "results": results,
        "row_count": row_count,
        "processing_time_ms": processing_time_ms,
        "confidence_score": 0.9 if success else 0.5,
        "explanation": explanation,
        # 🔥 扩展的处理步骤：包含SQL、表格、图表数据、数据分析文本
        "processing_steps": _build_processing_steps(
            success=success,
            sql=sql,
            results=results,
            row_count=row_count,
            data_obj=data_obj,
            echarts_option=echarts_option,
            chart_data=chart_data,
            chart_obj=safe_get(agent_response, 'chart'),
            processing_time_ms=processing_time_ms,
            answer=explanation
        ),
        "validation_result": {
            "valid": success,
            "error": error
        } if not success else None,
        "execution_result": execution_result,
        "correction_attempts": 0,
        # 🛡️ 在顶层也添加 echarts_option，使用安全访问
        "echarts_option": echarts_option,
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
    # 🛡️ 通用安全属性访问辅助函数（与 convert_agent_response_to_query_response 中的相同）
    def safe_get(obj, attr, default=None):
        """安全获取对象属性，支持多种数据类型"""
        try:
            if isinstance(obj, dict):
                return obj.get(attr, default)
            if hasattr(obj, attr):
                value = getattr(obj, attr, default)
                return value if value is not None else default
            try:
                if hasattr(obj, 'dict'):
                    obj_dict = obj.dict()
                    return obj_dict.get(attr, default)
                elif hasattr(obj, 'model_dump'):
                    obj_dict = obj.model_dump()
                    return obj_dict.get(attr, default)
            except (AttributeError, TypeError):
                pass
            try:
                if hasattr(obj, '__dict__'):
                    return obj.__dict__.get(attr, default)
            except (AttributeError, TypeError):
                pass
            return default
        except Exception:
            return default
    
    # 提取数据源信息（从SQL中推断）
    sources = []
    sql = safe_get(agent_response, 'sql', '')
    if sql:
        # 简单提取表名（可以改进）
        import re
        table_pattern = r'FROM\s+(\w+)'
        tables = re.findall(table_pattern, sql, re.IGNORECASE)
        sources.extend(tables)
    
    # 🛡️ 安全构建 chart 对象，防止 AttributeError
    chart_dict = None
    chart_obj = safe_get(agent_response, 'chart')
    if chart_obj:
        # 检查是否是 table 类型（不需要图表）
        chart_type_obj = safe_get(chart_obj, 'chart_type')
        chart_type_value = None
        if chart_type_obj:
            if hasattr(chart_type_obj, 'value'):
                chart_type_value = chart_type_obj.value
            else:
                chart_type_value = str(chart_type_obj)
        
        # 只有非 table 类型才构建 chart 对象
        if chart_type_value and chart_type_value != "table":
            # 🛡️ 使用 safe_get 安全提取所有 chart 属性
            chart_image_attr = safe_get(chart_obj, 'chart_image')
            
            # 使用提取的 chart_image 或从 answer 中提取
            chart_data = None
            if chart_image_attr and isinstance(chart_image_attr, str) and len(chart_image_attr) > 0:
                chart_data = chart_image_attr
            else:
                # 降级：从 answer 中提取
                answer = safe_get(agent_response, 'answer', '')
                chart_path = extract_chart_path_from_answer(answer)
                if chart_path:
                    if not (chart_path.startswith('http://') or chart_path.startswith('https://')):
                        chart_data = load_chart_as_base64(chart_path)
                    else:
                        chart_data = chart_path
            
            # 🛡️ 安全访问所有 chart 属性
            chart_dict = {
                "chart_type": chart_type_value,
                "title": safe_get(chart_obj, 'title'),
                "x_field": safe_get(chart_obj, 'x_field'),
                "y_field": safe_get(chart_obj, 'y_field'),
                "chart_image": chart_image_attr if (chart_image_attr and isinstance(chart_image_attr, str) and len(chart_image_attr) > 0) else None,
                "chart_data": chart_data
            }
    
    # 🛡️ 使用 safe_get 安全访问所有属性
    answer = safe_get(agent_response, 'answer', '')
    sql = safe_get(agent_response, 'sql', '')
    success = safe_get(agent_response, 'success', False)
    data_obj = safe_get(agent_response, 'data')
    echarts_option = safe_get(agent_response, 'echarts_option')

    # 🛡️🛡️🛡️ 安全检查：检查 answer 中是否包含危险的 DML/DDL 操作
    if answer:
        import re
        answer_upper = answer.upper()

        # 危险关键字黑名单
        dangerous_keywords = [
            (r'\bUPDATE\b', 'UPDATE'),
            (r'\bDELETE\b', 'DELETE'),
            (r'\bINSERT\b', 'INSERT'),
            (r'\bDROP\b', 'DROP'),
            (r'\bTRUNCATE\b', 'TRUNCATE'),
            (r'\bALTER\b', 'ALTER'),
            (r'\bCREATE\s+TABLE\b', 'CREATE TABLE'),
            (r'\bGRANT\b', 'GRANT'),
            (r'\bREVOKE\b', 'REVOKE'),
        ]

        detected_dangerous = []
        for pattern, keyword in dangerous_keywords:
            if re.search(pattern, answer_upper):
                detected_dangerous.append(keyword)

        # 检测到危险 SQL - 替换为拒绝消息
        if detected_dangerous:
            security_message = (
                "⛔ **操作被拒绝**\n\n"
                "您请求的操作涉及数据修改，这违反了安全策略。\n\n"
                "🛡️ 作为一个只读数据分析助手，我只能：\n"
                "- ✅ 查询和展示数据（SELECT）\n"
                "- ✅ 分析数据趋势和模式\n"
                "- ✅ 生成数据可视化图表\n"
                "- ❌ 不能修改、删除或新增数据\n\n"
                "如果您需要修改数据，请联系数据库管理员或使用专门的管理工具。"
            )
            answer = security_message
            logger.error(
                f"🚫 [Chat响应安全检查] 检测到危险SQL关键字并已拦截: {', '.join(detected_dangerous)}",
                extra={
                    "detected_keywords": detected_dangerous
                }
            )

    # 构建响应
    response = {
        "answer": answer,
        "sources": sources,
        "reasoning": f"执行了SQL查询：{sql}" if sql else "",
        "confidence": 0.9 if success else 0.5,
        "execution_time": execution_time,
        "sql": sql,
        "data": {
            "columns": safe_get(data_obj, 'columns', []) if data_obj else [],
            "rows": safe_get(data_obj, 'rows', []) if data_obj else [],
            "row_count": safe_get(data_obj, 'row_count', 0) if data_obj else 0
        } if data_obj else None,
        "chart": chart_dict,
        "echarts_option": echarts_option  # 🛡️ 安全访问 ECharts 配置选项
    }
    
    return response


async def run_agent_query(
    question: str,
    thread_id: str,
    database_url: Optional[str] = None,
    verbose: bool = False,
    enable_echarts: bool = True,  # 默认启用 ECharts 功能
    db_type: str = "postgresql"  # 数据库类型
) -> Optional[VisualizationResponse]:
    """
    运行Agent查询

    Args:
        question: 用户问题
        thread_id: 线程ID（用于会话管理）
        database_url: 数据库连接URL（可选，如果不提供则使用Agent配置）
        verbose: 是否显示详细输出
        enable_echarts: 是否启用 ECharts 图表生成功能（默认启用）
        db_type: 数据库类型（postgresql, mysql, sqlite, xlsx, csv等）

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
            "db_type": db_type,  # 添加数据库类型到日志
        },
    )
    if not _agent_available:
        logger.error("Agent模块不可用，直接返回 None")
        return None
    
    try:
        # -----------------------------------------------------
        # 1️⃣ STEP 1: EARLY ROUTING DETECTION (Check raw URL before modification)
        # -----------------------------------------------------
        # 先判断文件模式，在清理 database_url 之前
        is_file_mode = False
        raw_url_for_check = database_url or ""
        
        if isinstance(raw_url_for_check, str):
            # Check for file extensions or local paths
            if (raw_url_for_check.endswith(('.xlsx', '.xls', '.csv')) or 
                raw_url_for_check.startswith(('/', './', 'file://', 'local://')) or
                '/uploads/' in raw_url_for_check or
                '/data/' in raw_url_for_check):
                is_file_mode = True
        
        logger.info(
            f"🔧 [Router] 早期路由检测: {'FILE MODE' if is_file_mode else 'DATABASE MODE'}",
            extra={
                "is_file_mode": is_file_mode,
                "raw_url_preview": raw_url_for_check[:100] if raw_url_for_check else None
            }
        )
        
        # -----------------------------------------------------
        # 2️⃣ STEP 2: DATABASE URL SANITIZATION (Prevent Postgres Crash)
        # -----------------------------------------------------
        # 如果检测到是文件模式，清理 database_url，防止 Postgres 工具崩溃
        original_url = None
        if is_file_mode:
            if database_url:
                logger.warning(
                    f"🔧 [Sanitization] 检测到文件路径，清理 database_url 配置以防止 Postgres 工具崩溃: {database_url[:100]}",
                    extra={
                        "database_url_preview": database_url[:100],
                        "reason": "file_mode_detected"
                    }
                )
            # 设置为 None，防止 Postgres 工具尝试连接
            database_url = None
        elif database_url:
            # 这是有效的数据库 URL，可以设置到 config
            # 检查是否是有效的数据库 URL（以数据库协议开头）
            is_valid_db_url = (
                database_url.startswith('postgresql://') or
                database_url.startswith('postgres://') or
                database_url.startswith('mysql://') or
                database_url.startswith('mysql+pymysql://') or
                database_url.startswith('sqlite://') or
                database_url.startswith('sqlite:///') or
                database_url.startswith('mssql://') or
                database_url.startswith('oracle://')
            )
            
            if is_valid_db_url:
                # 这是有效的数据库 URL，可以设置
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
            else:
                # 不是有效的数据库 URL，也不像是文件路径，记录警告
                logger.warning(
                    f"⚠️ database_url 参数格式异常，既不是文件路径也不是有效的数据库 URL: {database_url[:100]}",
                    extra={
                        "database_url_preview": database_url[:100],
                        "reason": "invalid_format"
                    }
                )
        
        # -----------------------------------------------------
        # 3️⃣ STEP 3: CONSTRUCT SYSTEM INSTRUCTION (Based on Step 1)
        # -----------------------------------------------------
        
        system_instruction = ""
        
        if is_file_mode:
            # 📂 FILE MODE: Aggressive Anti-SQL Prompt (核威慑级别)
            system_instruction = (
                "【🛑 SYSTEM ALERT: FILE MODE ACTIVE】\n"
                "You are processing a local Excel/CSV file. \n"
                "CRITICAL RULES:\n"
                "1. The 'query' tool and SQL tools are DISCONNECTED and will cause a SYSTEM CRASH.\n"
                "2. You MUST ONLY use `analyze_dataframe` (for data analysis) or `inspect_file` (for schema).\n"
                "3. DO NOT attempt to list tables or schema. The data is already loaded in the dataframe tool.\n"
                "4. If you use 'query', the task will fail immediately.\n"
                "5. The SQL database connection is NOT available in file mode. All SQL tools (`query`, `list_tables`, `get_schema`, `query_database`, `execute_sql_safe`) are DISABLED and will return errors.\n"
                "6. You MUST use file-specific tools: `inspect_file` to see file structure, `analyze_dataframe` to query data."
            )
            logger.info("🔧 [Router] Detected FILE MODE. Locking SQL tools.")
        else:
            # 🛢️ DATABASE MODE: Standard SQL behavior with enhanced analysis requirements
            system_instruction = (
                "【SYSTEM MODE: DATABASE ANALYSIS】\n"
                "You are connected to a SQL database. \n"
                "RULES:\n"
                "1. Use `list_available_tables` or `list_tables` to see available tables first.\n"
                "2. Query the relevant tables using `execute_sql_safe` or `query_database` tools.\n"
                "\n\n🔴【CRITICAL: DEEP DATA ANALYSIS REQUIREMENT】\n"
                "After executing SQL, you MUST provide detailed analysis including:\n"
                "\n"
                "**1. Statistical Metrics (必填)**:\n"
                "- Total, Mean, Median, Standard Deviation\n"
                "- Min/Max values and Range\n"
                "- Growth rates (同比/环比) if time series data\n"
                "- Coefficient of Variation (data stability)\n"
                "\n"
                "**2. Trend & Pattern Analysis (必填)**:\n"
                "- Overall trend direction (上升/下降/平稳)\n"
                "- Key fluctuations and volatility\n"
                "- Seasonal patterns (if applicable)\n"
                "- Outliers and anomalies detection\n"
                "\n"
                "**3. Numerical Insights (必填)**:\n"
                "- What the numbers actually mean\n"
                "- Percentage changes and comparisons\n"
                "- Rankings (top/bottom performers)\n"
                "- Correlations between metrics\n"
                "\n"
                "**4. Business Intelligence (必填)**:\n"
                "- Actionable recommendations\n"
                "- Risk identification\n"
                "- Opportunity detection\n"
                "- Strategic suggestions\n"
                "\n"
                "**5. Prediction & Forecasting (必填)**:\n"
                "- Short-term prediction based on trends\n"
                "- Prediction methodology and assumptions\n"
                "- Prediction limitations and uncertainty\n"
                "\n"
                "**6. Root Cause Analysis (必填)**:\n"
                "- Driving factors behind data changes\n"
                "- Correlation analysis between metrics\n"
                "- Business logic explanation\n"
                "\n"
                "**7. Actionable Insights (必填)**:\n"
                "- Optimization recommendations (at least 2-3)\n"
                "- Risk identification\n"
                "- Opportunity discovery\n"
                "- Suggested further analysis\n"
                "\n"
                "⚠️ Example format for time series:\n"
                "• 总销售额：X 万元，平均每月 Y 万元\n"
                "• 整体趋势：上升/下降 Z%（从 A 万增长到 B 万）\n"
                "• 峰值：C 万元（某月），谷值：D 万元（某月）\n"
                "• 波动性：标准差 E，变异系数 F%\n"
                "• 预测：预计下月约 [预测值]（基于 [增长率] 推算）\n"
                "• 成因：主要驱动因素是 [因素描述]\n"
                "• 建议：基于以上发现...\n"
                "\n"
                "⚠️ Even for simple queries, calculate and present statistics.\n"
                "⚠️ Do NOT just list data rows - provide insights!\n"
            )
            logger.info("🛢️ [Router] Detected DATABASE MODE.")
        
        # -----------------------------------------------------
        # 4️⃣ STEP 4: INJECT & EXECUTE
        # -----------------------------------------------------
        # Inject the instruction into the question (Prompt Engineering)
        enhanced_question = f"{system_instruction}\n\nUser Question: {question}"
        logger.info("📋 [Prompt Injection] System instruction added to question.")
        
        # Log full system instruction for debugging
        if system_instruction:
            logger.debug(
                f"📋 [系统指令注入] 完整系统指令内容",
                extra={
                    "system_instruction": system_instruction,
                    "instruction_length": len(system_instruction),
                    "is_file_mode": is_file_mode
                }
            )
        
        # -----------------------------------------------------
        
        # 运行Agent
        logger.info(
            "Starting underlying LangGraph Agent run",
            extra={"thread_id": thread_id, "enable_echarts": enable_echarts},
        )

        # 🔥 【QA集成】开始计时
        import time as _time_module
        _qa_start_time = _time_module.time()
        _qa_context = {
            "source": "backend_api",
            "endpoint": "/api/v1/llm/query-with-agent",
            "user_question": question,  # 原始问题（未增强）
            "thread_id": thread_id,
            "db_type": db_type,
            "enable_echarts": enable_echarts,
        }

        # 根据使用的 Agent 版本调用不同的函数
        if _use_new_agent:
            # 新版本：需要传递 database_url，返回 Dict 包含 response 字段
            from config import config as agent_config
            
            # 在文件模式下，传递原始文件路径；在数据库模式下，传递数据库 URL
            if is_file_mode:
                # 文件模式：传递原始文件路径（raw_url_for_check）
                effective_db_url = raw_url_for_check if raw_url_for_check else None
                logger.info(
                    f"📂 [文件模式] 传递文件路径给 run_agent: {effective_db_url[:100] if effective_db_url else None}",
                    extra={"file_path": effective_db_url}
                )
            else:
                # 数据库模式：使用清理后的 database_url 或配置中的默认值
                effective_db_url = database_url or getattr(agent_config, "database_url", None)
                if not effective_db_url:
                    logger.error("无法获取数据库连接URL")
                    return None
                logger.info(
                    f"🛢️ [数据库模式] 传递数据库 URL 给 run_agent",
                    extra={"database_url_preview": effective_db_url[:80] if effective_db_url else None}
                )
            
            result = await run_agent(
                question=enhanced_question,  # 🔥 使用增强后的问题（包含智能路由指令）
                database_url=effective_db_url,  # 文件模式下传递文件路径，数据库模式下传递数据库 URL
                thread_id=thread_id,
                enable_echarts=enable_echarts,
                verbose=verbose,
                db_type=db_type  # 传递数据库类型
            )
            # 新版本返回 Dict，提取 response 字段（VisualizationResponse 对象）
            if result and isinstance(result, dict) and "response" in result:
                response = result["response"]
                # 🔥 修复：response对象已经包含metadata字段，不需要再动态添加
                # metadata已经在run_agent中设置到VisualizationResponse对象中
            else:
                response = None
        else:
            # 旧版本：不支持 enable_echarts 参数
            response = await run_agent(enhanced_question, thread_id, verbose=verbose, db_type=db_type)  # 传递 db_type
        logger.info(
            "Underlying LangGraph Agent finished",
            extra={
                "success": getattr(response, "success", None) if response else None,
                "sql_preview": (response.sql or "")[:120] if getattr(response, "sql", None) else None,
                "row_count": getattr(getattr(response, "data", None), "row_count", None) if response else None,
                "error": getattr(response, "error", None) if response else None,
            },
        )

        # 🔥 【QA集成】记录成功
        if _error_tracking_available and error_tracker:
            _qa_elapsed = _time_module.time() - _qa_start_time
            _response_success = getattr(response, "success", False) if response else False
            _response_answer = getattr(response, "answer", "")[:500] if response else ""
            _response_sql = getattr(response, "sql", "")[:200] if response else ""
            _response_error = getattr(response, "error", None) if response else None

            if _response_success:
                error_tracker.log_success(
                    question=question,
                    response=_response_answer or "查询成功",
                    context={
                        **_qa_context,
                        "sql": _response_sql,
                        "chart_type": getattr(getattr(response, "chart", None), "chart_type", None) if response else None,
                    },
                    execution_time=_qa_elapsed
                )
                logger.info(f"✅ [QA] 成功记录已保存 (耗时: {_qa_elapsed:.2f}s)")
            elif _response_error:
                # 有错误但没抛异常的情况
                log_agent_error(
                    question=question,
                    error=Exception(_response_error),
                    category=ErrorCategory.UNKNOWN,
                    context={**_qa_context, "execution_time": _qa_elapsed}
                )
                logger.info(f"⚠️ [QA] 错误记录已保存 (Agent返回错误: {_response_error[:100]})")

        # 🆕 深度统计分析集成
        stats_result = None  # 在外部变量中保存统计结果
        if _stats_analysis_available and response and getattr(response, 'success', False):
            try:
                # 获取查询数据
                data_obj = getattr(response, 'data', None)
                if data_obj and hasattr(data_obj, 'rows') and data_obj.rows:
                    # 准备数据格式
                    data_for_stats = {
                        "columns": list(data_obj.columns) if hasattr(data_obj, 'columns') else [],
                        "rows": data_obj.rows
                    }

                    # 调用统计分析服务
                    stats_service = get_stats_service()
                    stats_result = stats_service.analyze_query_result(data_for_stats)

                    # 将统计结果添加到 response 对象中（使用私有属性避免冲突）
                    if stats_result and 'error' not in stats_result:
                        setattr(response, '_stats_analysis', stats_result)
                        logger.info(
                            "✅ [统计分析] 深度统计指标计算完成",
                            extra={
                                "stats_basic": stats_result.get('basic_stats', {}),
                                "stats_trend": stats_result.get('trend_analysis', {})
                            }
                        )
            except Exception as stats_error:
                logger.warning(f"统计分析失败（非致命）: {stats_error}", exc_info=True)

        # 恢复原始配置（只有当 original_url 被设置时才恢复）
        if original_url is not None:
            from config import config
            logger.info("Restoring original Agent database_url")
            config.database_url = original_url

        return response
    
    except Exception as e:
        logger.error("Agent查询失败", extra={"error": str(e)}, exc_info=True)

        # 🔥 【QA集成】记录异常错误
        if _error_tracking_available and error_tracker:
            try:
                _qa_elapsed = _time_module.time() - _qa_start_time
                # 自动推断错误类别
                _error_category = ErrorCategory.UNKNOWN
                error_str = str(e).lower()
                if "connection" in error_str or "connect" in error_str:
                    _error_category = ErrorCategory.DATABASE_CONNECTION
                elif "timeout" in error_str:
                    _error_category = ErrorCategory.TIMEOUT
                elif "schema" in error_str or "table" in error_str or "column" in error_str:
                    _error_category = ErrorCategory.SCHEMA_NOT_FOUND
                elif "mcp" in error_str or "tool" in error_str:
                    _error_category = ErrorCategory.MCP_TOOL_FAILURE
                elif "api" in error_str or "llm" in error_str or "rate" in error_str:
                    _error_category = ErrorCategory.LLM_API_ERROR

                log_agent_error(
                    question=question,
                    error=e,
                    category=_error_category,
                    context={**_qa_context, "execution_time": _qa_elapsed}
                )
                logger.info(f"❌ [QA] 异常错误已记录 (类别: {_error_category.value})")
            except Exception as track_error:
                logger.warning(f"错误追踪记录失败: {track_error}")

        return None


def is_agent_available() -> bool:
    """检查Agent是否可用"""
    return _agent_available

