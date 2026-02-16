# -*- coding: utf-8 -*-
"""
Query Stream V2 Endpoint - 流式查询端点
======================================

流式响应端点，使�?Server-Sent Events (SSE) 协议�?

API: POST /api/v2/query/stream

特�?
    - 实时流式输出
    - 处理步骤推�?
    - 可取消的长时间查�?

作�? BMad Master
版本: 2.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator, Callable
import logging
import math
import json
import time
import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime

# 🔧 导入正则表达式模块的别名（用于备用解析）
import re as re_module
from src.app.services.agent.data_validator import validate_chart_fields_in_sql, build_cell_lineage, generate_insights_from_rows

# 缓存服务导入
from src.app.services.cache_service import (
    get_cache_manager,
    TenantCacheKeyGenerator
)

# 数据库依赖导�?
from src.app.data.database import SessionLocal, get_db
from sqlalchemy.orm.session import Session

logger = logging.getLogger(__name__)

# ============================================================================
# 会话状态管�?
# ============================================================================

@dataclass
class StreamSessionState:
    """流式会话状�?""
    session_id: str
    tenant_id: str
    user_id: str
    query: str
    status: str = "running"  # running, paused, completed, error
    accumulated_answer: str = ""
    current_progress: int = 0
    processing_steps: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    abort_controller: Optional[asyncio.Event] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字�?""
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "query": self.query,
            "status": self.status,
            "accumulated_answer": self.accumulated_answer,
            "current_progress": self.current_progress,
            "processing_steps": self.processing_steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

# 全局会话状态存�?(生产环境应使�?Redis)
_active_sessions: Dict[str, StreamSessionState] = {}


def get_session_state(session_id: str) -> Optional[StreamSessionState]:
    """获取会话状�?""
    return _active_sessions.get(session_id)


def set_session_state(state: StreamSessionState):
    """设置会话状�?""
    _active_sessions[state.session_id] = state


def remove_session_state(session_id: str):
    """移除会话状�?""
    _active_sessions.pop(session_id, None)

# ============================================================================
# 图表配置提取函数
# ============================================================================

def extract_chart_config_from_answer(answer: str) -> Optional[str]:
    """�?AI 回答中提取图表配�?JSON

    Args:
        answer: AI 的文本回�?

    Returns:
        JSON 字符串格式的图表配置，如果没有则返回 None
    """
    if not answer or not answer.strip():
        return None

    # 策略0 (最高优先级): 尝试匹配 [CHART_START]...[CHART_END] 格式
    # 这是 V1 API �?AI 生成图表时使用的标准格式
    chart_marker_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
    marker_match = re.search(chart_marker_pattern, answer)
    if marker_match:
        json_str = marker_match.group(1).strip()
        try:
            parsed = json.loads(json_str)

            # 🔧 优先检查是否为 MCP 简化格式并转换
            if all(key in parsed for key in ['chart_type', 'title', 'data']):
                logger.info(f"[图表提取] 检测到 MCP 简化格式，尝试转换�?ECharts 格式")
                converted = convert_mcp_chart_to_echarts(json_str)
                if converted:
                    logger.info(f"[图表提取] �?MCP格式转换成功")
                    return converted
                else:
                    logger.warning(f"[图表提取] MCP格式转换失败，返回原始格�?)
                    return json.dumps(parsed, ensure_ascii=False)

            # ECharts 配置通常包含 series, xAxis, yAxis, title 等字�?
            if any(key in parsed for key in ['series', 'xAxis', 'yAxis', 'title', 'legend', 'grid', 'tooltip']):
                logger.info(f"[图表提取] 成功�?[CHART_START]...[CHART_END] 格式提取 ECharts 配置")
                return json.dumps(parsed, ensure_ascii=False)
            # 简化格式图表配�?
            elif any(key in parsed for key in ['chart_type', 'data', 'x_axis', 'y_axis']):
                logger.info(f"[图表提取] 成功�?[CHART_START]...[CHART_END] 格式提取简化图表配�?)
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.warning(f"[图表提取] [CHART_START] JSON 解析失败: {e}")

    # 策略1: 尝试匹配 ```json ... ``` 代码�?
    json_pattern = r'```(?:json|JSON)\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, answer)

    if match:
        json_str = match.group(1).strip()
        # 处理双大括号问题（Python f-string 模板格式�?
        json_str = json_str.replace('{{', '{').replace('}}', '}')
        # 验证是否为有�?JSON
        try:
            parsed = json.loads(json_str)
            # 验证是否是图表配�?
            if any(key in parsed for key in ['chart_type', 'series', 'data', 'title', 'x_axis', 'y_axis']):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

    # 策略2: 尝试匹配任意代码块中�?JSON
    code_block_pattern = r'```\s*([\s\S]*?)\s*```'
    for match in re.finditer(code_block_pattern, answer):
        json_str = match.group(1).strip()
        # 检查是否像 JSON（以 { �?[ 开头）
        if json_str.startswith('{') or json_str.startswith('['):
            # 处理双大括号
            json_str = json_str.replace('{{', '{').replace('}}', '}')
            try:
                parsed = json.loads(json_str)
                if any(key in parsed for key in ['chart_type', 'series', 'data', 'title']):
                    return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass

    return None


def _is_valid_chart_config(chart_json: str) -> bool:
    """验证图表配置是否有效（支持多种格式）

    Args:
        chart_json: JSON 字符串格式的图表配置

    Returns:
        True 如果配置有效，False 否则
    """
    try:
        config = json.loads(chart_json)

        # 🔧 新增：支�?MCP ECharts 工具的简化格�?
        # 格式: {"chart_type": "line", "title": "...", "data": [...]}
        if all(key in config for key in ['chart_type', 'title', 'data']):
            data = config.get("data")
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"[图表验证] �?MCP ECharts 简化格式有�? type={config.get('chart_type')}")
                return True

        # 标准格式：必须有 series 字段
        if "series" not in config or not config["series"]:
            logger.info(f"[图表验证] 失败: 缺少 series 字段")
            return False

        series = config["series"]
        if not isinstance(series, list) or len(series) == 0:
            logger.info(f"[图表验证] 失败: series 不是非空数组")
            return False

        first_series = series[0]
        if not isinstance(first_series, dict):
            logger.info(f"[图表验证] 失败: series[0] 不是对象")
            return False

        series_type = first_series.get("type", "")

        # 饼图特殊验证
        if series_type == "pie":
            if "data" not in first_series or not first_series["data"]:
                logger.info(f"[图表验证] 失败: 饼图缺少 data 字段")
                return False
            # 验证饼图数据格式
            pie_data = first_series["data"]
            if not isinstance(pie_data, list) or len(pie_data) == 0:
                logger.info(f"[图表验证] 失败: 饼图 data 不是非空数组")
                return False
        elif series_type in ["gauge", "indicator"]:
            # 仪表盘类图表只需要有数值即�?
            if "data" not in first_series:
                logger.info(f"[图表验证] 失败: {series_type} 图表缺少 data 字段")
                return False
        else:
            # 其他图表类型（line, bar）需要有 data �?xAxis
            if "data" not in first_series or not first_series["data"]:
                logger.info(f"[图表验证] 失败: series 缺少 data 字段")
                return False

            # 检查数据是否为空数�?
            series_data = first_series["data"]
            if isinstance(series_data, list) and len(series_data) == 0:
                logger.info(f"[图表验证] 失败: series.data 是空数组")
                return False

            # 检查是否有 xAxis（坐标轴类图表需要）
            if "xAxis" in config:
                xAxis = config["xAxis"]
                if isinstance(xAxis, dict) and "data" not in xAxis:
                    logger.info(f"[图表验证] 警告: xAxis 存在但缺�?data 字段")
                    # 不返�?False，因为可能由 series.data 提供

        # 验证通过
        logger.info(f"[图表验证] �?图表配置有效, type={series_type}")
        return True

    except json.JSONDecodeError as e:
        logger.warning(f"[图表验证] JSON 解析失败: {e}")
        return False
    except Exception as e:
        logger.warning(f"[图表验证] 验证过程出错: {e}")
        return False


def convert_mcp_chart_to_echarts(chart_json: str) -> Optional[str]:
    """�?MCP ECharts 简化格式转换为标准 ECharts 格式

    MCP ECharts 工具返回的格�?
    {"chart_type": "line", "title": "...", "data": [{"time": "...", "value": 123}, ...]}

    标准ECharts格式:
    {"title": {"text": "..."}, "xAxis": {...}, "yAxis": {...}, "series": [...]}

    Args:
        chart_json: MCP ECharts 简化格式的 JSON 字符�?

    Returns:
        标准格式�?ECharts 配置 JSON 字符串，如果转换失败则返�?None
    """
    try:
        config = json.loads(chart_json)

        # 检查是否是 MCP 简化格�?
        if not all(key in config for key in ['chart_type', 'title', 'data']):
            return None  # 不是 MCP 格式

        chart_type = config.get("chart_type", "line")
        title = config.get("title", "数据图表")
        data = config.get("data", [])

        if not data:
            logger.warning("[图表转换] MCP 格式中没有数�?)
            return None

        # 提取 x �?y 数据
        x_data = []
        y_data = []

        for item in data:
            if isinstance(item, dict):
                # 尝试不同的字段名
                x_val = item.get("time") or item.get("category") or item.get("name") or item.get("x")
                y_val = item.get("value") or item.get("y") or item.get("amount")

                if x_val is not None:
                    x_data.append(x_val)
                if y_val is not None:
                    y_data.append(y_val)

        # 构建 ECharts 配置
        echarts_config = {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [title]},
            "xAxis": {
                "type": "category",
                "data": x_data,
                "axisLabel": {"rotate": 45 if len(x_data) > 10 else 0}
            },
            "yAxis": {"type": "value", "name": "数�?},
            "series": [{
                "name": title,
                "type": chart_type,
                "data": y_data,
                "smooth": chart_type == "line"
            }]
        }

        logger.info(f"[图表转换] �?MCP格式转ECharts成功: {len(x_data)}个数据点")
        return json.dumps(echarts_config, ensure_ascii=False)

    except Exception as e:
        logger.warning(f"[图表转换] 转换失败: {e}")
        return None


# 数值格式化：截断长尾浮点，保证展示层两位小�?
def sanitize_table_numbers(table: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not table:
        return {}

    columns = table.get("columns", [])
    rows = table.get("rows", table.get("data", [])) or []

    def _fmt(val: Any):
        try:
            num = float(val)
        except (TypeError, ValueError):
            return val
        if not math.isfinite(num):
            return val
        rounded = round(num, 2)
        if rounded == -0.0:
            rounded = 0.0
        return int(rounded) if rounded.is_integer() else rounded

    sanitized_rows: list = []
    for row in rows:
        if isinstance(row, list):
            sanitized_rows.append([_fmt(v) for v in row])
        elif isinstance(row, dict):
            sanitized_rows.append({k: _fmt(v) for k, v in row.items()})
        else:
            sanitized_rows.append(row)

    return {
        "columns": columns,
        "rows": sanitized_rows,
        "row_count": table.get("row_count", len(sanitized_rows)),
        "source_label": table.get("source_label"),
        "merged_from_steps": table.get("merged_from_steps"),
    }


def generate_default_chart_config_from_table(
    columns: List[str],
    rows: List[Any],  # 🔧 修改：支持列表格式或字典列表
    query: str = ""
) -> Optional[str]:
    """从表格数据自动生成默认的 ECharts 图表配置

    Args:
        columns: 表格列名列表
        rows: 表格行数据（支持字典列表或数组列表）
        query: 原始查询（用于判断图表类型）

    Returns:
        JSON 字符串格式的 ECharts 配置，如果无法生成则返回 None
    """
    # 🔧 计划修复2：增加图表生成诊断日�?
    logger.info(f"[图表诊断] 📊 generate_default_chart_config_from_table 调用: "
                f"columns={len(columns) if columns else 0}, "
                f"rows={len(rows) if rows else 0}, "
                f"query='{query[:50] if query else ''}...'")

    if not columns or not rows:
        logger.warning(f"[图表诊断] ⚠️ 缺少必要数据: columns={columns}, rows存在={bool(rows)}")
        return None

    try:
        # 🔧 修复：检测数据格式并统一处理
        # 如果 rows 是列表格式（数组数组），转换为字典列�?
        if rows and isinstance(rows[0], list):
            # 数组数组格式: [[val1, val2], ...] + columns
            logger.info(f"[图表生成] 检测到数组格式，将转换为字典格�?)
            dict_rows = []
            for row in rows:
                dict_row = {}
                for i, col in enumerate(columns):
                    if i < len(row):
                        dict_row[col] = row[i]
                dict_rows.append(dict_row)
            rows = dict_rows  # 使用转换后的字典列表
        elif not isinstance(rows[0], dict):
            logger.warning(f"[图表生成] 不支持的行格�? {type(rows[0])}")
            return None

        # 数据分析：检测列类型和数据特�?
        from datetime import datetime
        import re

        # 查找可能的类别列和数值列
        category_col = None
        value_cols = []
        time_col = None

        for col in columns:
            # 检查第一行的值类�?
            if rows and len(rows) > 0:
                first_val = rows[0].get(col)
                if first_val is None:
                    continue

                # 检测时间列（包�?date, time, year, month, day 等关键词�?
                if any(keyword in col.lower() for keyword in ['date', 'time', 'year', 'month', 'day', '日期', '时间', '�?, '�?, '�?]):
                    time_col = col
                    continue

                # 检测数值列
                try:
                    float(first_val)
                    value_cols.append(col)
                except (ValueError, TypeError):
                    # 不是数值，可能是类�?
                    if category_col is None:
                        category_col = col

        # 如果没有找到类别列，使用第一�?
        if category_col is None and columns:
            category_col = columns[0]

        # 🔧 计划修复2：添加列类型诊断日志
        logger.info(f"[图表诊断] 📊 列类型分�? category_col={category_col}, value_cols={value_cols}, time_col={time_col}")

        # 如果没有数值列，跳�?
        if not value_cols:
            logger.warning("[图表诊断] ⚠️ 没有找到数值列，无法生成图�?)
            logger.info(f"[图表诊断] 🔍 所有列�? {columns}")
            logger.info(f"[图表诊断] 🔍 第一行数�? {rows[0] if rows else 'N/A'}")
            return None

        # 限制数据行数（避免图表过于复杂）
        chart_rows = rows[:100]

        # 🔧 改进：更准确的时间列检�?
        time_keywords = ['date', 'time', 'year', 'month', 'day', 'quarter', '日期', '时间', '�?, '�?, '�?, '季度']
        has_time_column = any(kw in col.lower() for col in columns for kw in time_keywords)

        # 🔧 新增：分析用户查询意图来选择图表类型
        query_lower = query.lower()
        is_trend_query = any(kw in query_lower for kw in ['趋势', '变化', '每月', '每年', '增长', '下降', 'trend', '时间序列'])
        is_proportion_query = any(kw in query_lower for kw in ['占比', '分布', '比例', 'percent', 'ratio', '百分�?])

        # 判断图表类型
        chart_type = "bar"  # 默认柱状�?
        is_time_series = False

        # 🔧 改进的图表类型选择逻辑
        if is_proportion_query:
            chart_type = "pie"
            logger.info(f"[图表生成] 检测到占比查询，使用饼�?)
        elif is_trend_query or has_time_column:
            chart_type = "line"
            is_time_series = True
            if time_col:
                category_col = time_col
            logger.info(f"[图表生成] 检测到趋势查询或时间列，使用折线图")
        else:
            chart_type = "bar"
            logger.info(f"[图表生成] 使用默认柱状�?)

        # 提取类别数据
        categories = [str(row.get(category_col, "")) for row in chart_rows if row.get(category_col) is not None]

        # 提取数值数据（只取第一个数值列�?
        value_col = value_cols[0]
        values = []
        for row in chart_rows:
            val = row.get(value_col)
            try:
                values.append(float(val) if val is not None else 0)
            except (ValueError, TypeError):
                values.append(0)

        # 生成图表配置
        if chart_type == "pie":
            # 饼图配置
            data = [{"value": v, "name": c} for c, v in zip(categories, values) if v > 0]
            chart_config = {
                "title": {"text": f"{category_col}分布�?, "left": "center"},
                "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                "legend": {"orient": "vertical", "left": "left"},
                "series": [{
                    "name": value_col,
                    "type": "pie",
                    "radius": "50%",
                    "data": data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    }
                }]
            }
        else:
            # 折线图或柱状图配�?
            chart_config = {
                "title": {"text": f"{category_col}-{value_col}{'趋势' if is_time_series else '对比'}"},
                "tooltip": {"trigger": "axis"},
                "legend": {"data": [value_col]},
                "xAxis": {
                    "type": "category",
                    "data": categories,
                    "axisLabel": {"rotate": 45 if len(categories) > 10 else 0}
                },
                "yAxis": {"type": "value", "name": value_col},
                "series": [{
                    "name": value_col,
                    "type": chart_type,
                    "data": values,
                    "smooth": chart_type == "line"
                }]
            }

        logger.info(f"[图表生成] 自动生成{chart_type}�? {len(categories)}个数据点")
        return json.dumps(chart_config, ensure_ascii=False)

    except Exception as e:
        logger.warning(f"[图表生成] 自动生成图表配置失败: {e}")
        return None


# ============================================================================
# 占比查询辅助函数
# ============================================================================

def is_proportion_query(query: str) -> bool:
    """检测是否为占比类查�?

    Args:
        query: 用户查询文本

    Returns:
        True 如果是占比类查询，False 否则
    """
    if not query:
        return False
    query_lower = query.lower()
    proportion_keywords = ['占比', '比例', '分布', '多少', 'percent', 'ratio', '%']
    return any(kw in query_lower for kw in proportion_keywords)


def _extract_numeric_value(rows: list) -> Optional[float]:
    """从行数据中提取数�?

    Args:
        rows: 表格行数�?

    Returns:
        提取到的数值，如果未找到则返回 None
    """
    if not rows:
        return None
    for row in rows:
        if isinstance(row, list):
            for v in row:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return float(v)
        elif isinstance(row, dict):
            for v in row.values():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return float(v)
    return None


def _extract_category_from_query(query: str) -> Optional[str]:
    """从查询中提取类别名称（如"安徽"�?

    Args:
        query: SQL 查询语句

    Returns:
        提取到的类别名称，如果未找到则返�?None
    """
    import re
    # 匹配 WHERE province = '安徽' �?WHERE province = "安徽"
    match = re.search(r"(?:where|and)\s+\w+\s*=\s*['\"]([^'\"]+)['\"]", query, re.IGNORECASE)
    if match:
        return match.group(1)
    # 尝试其他常见模式
    match = re.search(r"(?:where|and)\s+(\w+)\s*=\s*['\"]?([^'\"]+)['\"]?", query, re.IGNORECASE)
    if match:
        return match.group(2)
    return None


def _check_table_consistency(query_history: list) -> tuple[bool, str]:
    """检查占比查询中分子分母是否来自同一张表

    解决问题：当用户询问"XX的客户占�?时，AI 可能�?users 表查询分子，
    �?addresses 表查询分母，导致数据口径不一致�?

    Args:
        query_history: 查询历史列表，每项包�?query (SQL) �?rows

    Returns:
        (is_consistent, error_message)
        - is_consistent: True 表示表一致，False 表示检测到跨表问题
        - error_message: 不一致时的错误提示信�?
    """
    if not query_history or len(query_history) < 2:
        return True, ""

    # 提取所有查询中使用的表�?
    tables_used = []
    for h in query_history:
        sql = h.get("query", "")
        if not sql:
            continue

        # 提取 FROM 子句中的表名
        # 匹配 FROM tablename �?FROM "tablename" �?FROM 'tablename'
        from_match = re.search(r'FROM\s+"?([\w]+)"?', sql, re.IGNORECASE)
        if from_match:
            table_name = from_match.group(1)
            # 过滤掉系统表和子查询
            if table_name and not table_name.startswith('('):
                tables_used.append(table_name.lower())

    # 检查是否使用了多个不同的表
    unique_tables = list(set(tables_used))
    if len(unique_tables) > 1:
        # 检查是否是 users �?addresses 的组合（常见错误模式�?
        has_users = any(t in ["users", "user"] for t in unique_tables)
        has_addresses = any(t in ["addresses", "address"] for t in unique_tables)

        if has_users and has_addresses:
            error_msg = (
                f"⚠️ 检测到跨表查询问题：查询同时使用了 users �?addresses 表�?
                f"这会导致分子分母数据口径不一致！"
                f"\n\n建议：对于省�?城市占比查询，请只使�?addresses 表，"
                f"使用一�?GROUP BY 查询获取所有分类的分布数据�?
            )
            logger.warning(f"[表一致性检查] 检测到跨表问题: {unique_tables}")
            return False, error_msg

        error_msg = (
            f"⚠️ 查询涉及多个表：{', '.join(unique_tables)}�?
            f"占比查询的分子分母必须来自同一张表，否则会导致数据口径不一致�?
        )
        logger.warning(f"[表一致性检查] 检测到多表查询: {unique_tables}")
        return False, error_msg

    logger.info(f"[表一致性检查] �?表一�? {unique_tables}")
    return True, ""


def _generate_smart_analysis(
    rows: list,
    columns: list,
    query: str,
    query_history: list = None
) -> str:
    """基于查询结果生成智能分析文本

    Args:
        rows: 查询结果行数�?
        columns: 列名
        query: 用户原始查询
        query_history: 查询历史（用于占比类分析�?

    Returns:
        详细的分析文�?
    """
    if not rows or not columns:
        return "查询已完成，但未返回数据�?

    row_count = len(rows)
    col_count = len(columns)

    # 检测查询类�?
    is_proportion = any(kw in query for kw in ["占比", "比例", "百分�?, "分布"])
    is_trend = any(kw in query for kw in ["趋势", "变化", "增长", "下降"])

    parts = []

    # 占比类查询的详细分析
    if is_proportion and query_history and len(query_history) >= 2:
        parts.append("📊 **数据分析总结**\n\n")

        # 从查询历史中提取分子分母（使用安全的方式�?
        for i, h in enumerate(query_history):
            if isinstance(h, dict) and h.get("rows"):
                parts.append(f"**查询{i+1}**: {h.get('query', 'N/A')}\n")
                history_rows = h.get("rows", [])
                # 安全地显示行数据
                for row in history_rows[:3]:
                    parts.append(f"�?{row}\n")
                parts.append("\n")

        # 计算占比（使�?_extract_numeric_value 函数安全提取�?
        if len(query_history) >= 2:
            numerator = 0
            denominator = 0

            # 安全地从第一个查询历史中提取分子
            if isinstance(query_history[0], dict):
                first_rows = query_history[0].get("rows", [])
                numerator = _extract_numeric_value(first_rows) or 0

            # 安全地从第二个查询历史中提取分母
            if isinstance(query_history[1], dict):
                second_rows = query_history[1].get("rows", [])
                denominator = _extract_numeric_value(second_rows) or 0

            if denominator > 0:
                proportion = (numerator / denominator) * 100
                parts.append(f"**占比结果**: {proportion:.1f}%\n\n")

    # 通用分析
    parts.append(f"📈 **数据概览**\n")
    parts.append(f"�?返回 **{row_count}** 条记录\n")
    parts.append(f"�?包含 **{col_count}** 个字�? {', '.join(columns[:5])}\n\n")

    # 数值统�?
    numeric_cols = []
    for i, col in enumerate(columns):
        if rows and i < len(rows[0]):
            val = rows[0][i]
            if isinstance(val, (int, float)):
                numeric_cols.append((col, i))

    if numeric_cols:
        parts.append("**🔢 数值统�?*\n")
        for col, idx in numeric_cols[:3]:
            values = [row[idx] for row in rows if idx < len(row) and isinstance(row[idx], (int, float))]
            if values:
                parts.append(f"�?**{col}**: 最�?{min(values)}, 最�?{max(values)}, 平均={sum(values)/len(values):.2f}\n")
        parts.append("\n")

    # 数据预览
    parts.append("**📋 数据预览**\n")
    for row in rows[:5]:
        parts.append(f"�?{' | '.join(str(v) for v in row)}\n")

    if row_count > 5:
        parts.append(f"\n（共 {row_count} 条记录，仅显示前5条）\n")

    return "".join(parts)


def _validate_and_fix_percentage(
    answer: str,
    query_history: list
) -> tuple[str, bool]:
    """动态验证和修复百分比计�?

    根据多次查询结果动态计算正确的百分比，并修复AI回答中的错误数值�?

    Args:
        answer: AI 生成的回答文�?
        query_history: 查询历史列表

    Returns:
        (修复后的回答, 是否进行了修�?
    """
    if not query_history or len(query_history) < 2:
        return answer, False

    # 提取所有查询中的数�?
    values = []
    for h in query_history:
        rows = h.get("rows", [])
        val = _extract_numeric_value(rows)
        if val is not None:
            values.append(val)

    if len(values) < 2:
        return answer, False

    # 动态计算正确百分比
    # 假设：第一个值是子集（如安徽），第二个值是全集（如总数�?
    subset_val, total_val = values[0], values[1]

    if total_val <= 0:
        logger.warning(f"[数值验证] 分母为零，无法计算百分比")
        return answer, False

    correct_percentage = round((subset_val / total_val) * 100, 2)
    logger.info(f"[数值验证] 计算得出正确百分�? {subset_val}/{total_val} = {correct_percentage}%")

    # 提取AI声明的百分比
    percentage_patterns = [
        r'(\d+\.?\d*)%',
        r'占比\s*(?:�??\s*(\d+\.?\d*)',
        r'比例\s*(?:�??\s*(\d+\.?\d*)',
        r'�?*?(\d+\.?\d*)\s*%',
    ]

    needs_fix = False
    fixed_answer = answer
    ai_percentage = None

    for pattern in percentage_patterns:
        matches = re.findall(pattern, answer)
        if matches:
            try:
                ai_percentage = float(matches[0])
                # 允许1%的误差，超过则需要修�?
                if abs(ai_percentage - correct_percentage) > 1:
                    needs_fix = True
                    logger.info(f"[数值验证] 检测到错误: AI说{ai_percentage}%，实际应为{correct_percentage}%")
                    break
            except (ValueError, TypeError):
                continue

    if needs_fix and ai_percentage is not None:
        # 动态替换为正确的百分比
        # 先尝试精确匹配AI的百分比格式
        for pattern in percentage_patterns:
            fixed_answer = re.sub(
                pattern.replace(r'(\d+\.?\d*)', str(ai_percentage)).replace(str(ai_percentage), r'(\d+\.?\d*)'),
                f'{correct_percentage}%',
                fixed_answer,
                count=1
            )
        # 如果上述替换失败，使用简单替�?
        if f"{ai_percentage}%" in fixed_answer:
            fixed_answer = fixed_answer.replace(f"{ai_percentage}%", f"{correct_percentage}%")
        elif f"{ai_percentage}" in fixed_answer:
            fixed_answer = fixed_answer.replace(f"{ai_percentage}", f"{correct_percentage}")

        logger.info(f"[数值验证] �?修复百分�? {ai_percentage}% -> {correct_percentage}%")
        return fixed_answer, True

    return answer, False


def generate_proportion_chart_from_history(
    query_history: list,
    user_query: str
) -> Optional[str]:
    """基于查询历史生成占比饼图

    示例�?
    - 第一次查询：COUNT(*) WHERE province='安徽' �?1000
    - 第二次查询：COUNT(*) �?1000
    - 生成：饼图显�?"安徽: 1000 (100%)"

    Args:
        query_history: 查询历史列表
        user_query: 原始用户查询

    Returns:
        JSON 字符串格式的 ECharts 配置，如果无法生成则返回 None
    """
    if not query_history or len(query_history) < 2:
        return None

    try:
        # 提取数值构建图表数�?
        chart_data = {
            "title": {"text": "客户占比分布", "left": "center"},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [{
                "type": "pie",
                "radius": "50%",
                "data": []
            }]
        }

        # 从查询历史中提取数据
        # 假设第一个是条件查询（如安徽），第二个是总数查询
        first_query = query_history[0]
        second_query = query_history[1]

        first_val = _extract_numeric_value(first_query.get("rows", []))
        second_val = _extract_numeric_value(second_query.get("rows", []))

        if first_val is not None and second_val is not None:
            # 确定类别名称（从查询中提取）
            category_name = _extract_category_from_query(first_query.get("query", ""))
            if not category_name:
                category_name = "目标类别"

            # 添加主数�?
            if second_val > 0:
                percentage = round((first_val / second_val) * 100, 1)
            else:
                percentage = 0

            chart_data["series"][0]["data"].append({
                "value": first_val,
                "name": f"{category_name} ({percentage}%)"
            })

            # 如果占比小于100%，添�?其他"类别
            if percentage < 99:
                other_val = second_val - first_val
                chart_data["series"][0]["data"].append({
                    "value": other_val,
                    "name": f"其他 ({round(100 - percentage, 1)}%)"
                })

            logger.info(f"[图表生成] 基于查询历史生成饼图: {category_name}={first_val}, 总数={second_val}, 占比={percentage}%")
            return json.dumps(chart_data, ensure_ascii=False)

    except Exception as e:
        logger.warning(f"[图表生成] 基于历史生成图表失败: {e}")

    return None


def enhance_proportion_response(
    answer: str,
    data: List[Dict],
    user_query: str
) -> str:
    """
    为占比类查询增强响应文本

    计算各省�?类别的占比百分比，并添加到响应中�?
    此函数用于处理带�?GROUP BY 的占比查询结果�?

    Args:
        answer: AI 生成的原始回�?
        data: 查询结果数据（包�?province/city 等分组列�?count 值）
        user_query: 用户原始查询

    Returns:
        增强后的回答文本
    """
    if not data or len(data) < 1:
        return answer

    # 检查数据是否包含必要的字段
    first_row = data[0]
    if not isinstance(first_row, dict):
        return answer

    # 查找分组列和计数�?
    group_column = None
    count_column = None

    for col in first_row.keys():
        col_lower = col.lower()
        if col_lower in ['province', 'city', 'region', 'category', 'type']:
            group_column = col
        elif col_lower in ['count', 'total', 'num', 'value']:
            count_column = col

    if not group_column or not count_column:
        # 数据格式不匹配，不进行增�?
        return answer

    # 计算总数
    total = sum(row.get(count_column, 0) for row in data if isinstance(row.get(count_column), (int, float)))

    if total <= 0:
        return answer

    # 找到目标省份/类别
    target_location = None
    for kw in ['内蒙�?, '安徽', '浙江', '江苏', '上海', '北京', '广东', '山东', '河南', '湖北']:
        if kw in user_query:
            target_location = kw
            break

    # 构建占比分析文本
    proportion_text = "\n\n📊 **分布分析**:\n\n"

    # 按数量排序（降序�?
    sorted_data = sorted(
        [row for row in data if isinstance(row.get(count_column), (int, float))],
        key=lambda x: x.get(count_column, 0),
        reverse=True
    )

    for row in sorted_data[:10]:  # 最多显示前10�?
        category = row.get(group_column, "未知")
        count = row.get(count_column, 0)
        percentage = (count / total * 100) if total > 0 else 0
        marker = "👈" if str(category) == target_location else ""
        proportion_text += f"- {category}: {count} ({percentage:.1f}%) {marker}\n"

    # 添加目标类别的占比总结
    if target_location:
        target_count = next(
            (r.get(count_column, 0) for r in data if str(r.get(group_column, "")) == target_location),
            0
        )
        if target_count > 0:
            target_pct = (target_count / total * 100) if total > 0 else 0
            proportion_text += f"\n**{target_location}占比**: {target_pct:.1f}% ({target_count}/{total})\n"

    logger.info(f"[占比增强] 添加�?{len(sorted_data)} 个类别的分布分析")

    return answer + proportion_text


# ============================================================================
# 性能监控辅助函数
# ============================================================================

def log_performance(
    step: str,
    tenant_id: str,
    user_id: str,
    duration_ms: float,
    metadata: Optional[Dict[str, Any]] = None
):
    """记录性能指标"""
    logger.info(
        "Performance metric",
        extra={
            "metric_type": "query_performance",
            "step": step,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "duration_ms": round(duration_ms, 2),
            "metadata": metadata or {}
        }
    )

# ============================================================================
# 路由�?
# ============================================================================

router = APIRouter(prefix="/query", tags=["query-v2-stream"])

# ============================================================================
# 依赖�?
# ============================================================================

# 延迟导入 AgentFactory（可能不可用�?
try:
    from AgentV2.core import AgentFactory, get_default_factory
    AGENTV2_AVAILABLE = True
except ImportError:
    AGENTV2_AVAILABLE = False
    AgentFactory = None


def get_agent_factory() -> AgentFactory:
    """获取 AgentFactory 实例"""
    if not AGENTV2_AVAILABLE:
        raise RuntimeError("AgentV2 不可�?)
    return get_default_factory()


# ============================================================================
# 请求模型
# ============================================================================

class StreamQueryRequestV2(BaseModel):
    """流式查询请求模型"""
    query: str = Field(..., description="自然语言查询", min_length=1)
    connection_id: Optional[str] = Field(None, description="数据源连�?ID")
    session_id: Optional[str] = Field(None, description="会话 ID")
    max_results: int = Field(100, ge=1, le=1000, description="最大结果数")
    include_chart: bool = Field(False, description="是否生成图表")

# ============================================================================
# 端点
# ============================================================================

@router.post("/stream")
async def create_stream_query_v2(
    request: StreamQueryRequestV2,
    tenant_id: str = "default_tenant",
    user_id: str = "default_user",
    agent_factory: AgentFactory = Depends(get_agent_factory),
    db: Session = Depends(get_db)
):
    """
    流式查询端点 (Server-Sent Events)

    返回 SSE 格式的流式响应�?

    ## 事件类型
    - `step`: 处理步骤更新
    - `progress`: 进度更新 (0-100)
    - `data`: 部分数据
    - `error`: 错误信息
    - `done`: 完成信号

    ## 使用示例
    ```javascript
    const eventSource = new EventSource('/api/v2/query/stream?query=xxx');

    eventSource.addEventListener('step', (e) => {
        console.log('Step:', e.data);
    });

    eventSource.addEventListener('done', (e) => {
        console.log('Final result:', e.data);
        eventSource.close();
    });
    ```
    """
    # 记录请求开始时�?
    request_start_time = time.time()

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 事件生成�?""

        # 🔧 表格数据收集（用于自动生成图表配置的兜底方案�?
        # 支持累积结构，用于占比类查询
        collected_table_data = {
            "query_history": [],  # 累积所有查询结果（用于占比计算�?
            "columns": None,
            "rows": None,
            "has_data": False
        }

        def send_event(event_type: str, data: Dict[str, Any]):
            """发�?SSE 事件（同步生成器�?""
            event_data = json.dumps(data, ensure_ascii=False)
            yield f"event: {event_type}\n"
            yield f"data: {event_data}\n\n"

        try:
            # 步骤时间记录
            step_timings: Dict[str, float] = {}
            overall_start = time.time()  # 初始化总开始时�?

            # 初始化会话状�?
            session_id = request.session_id or f"stream_{int(time.time() * 1000)}"
            abort_event = asyncio.Event()
            session_state = StreamSessionState(
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                query=request.query,
                status="running",
                abort_controller=abort_event
            )
            set_session_state(session_state)

            # 发送开始事件（包含 session_id�?
            for event in send_event("start", {
                "query": request.query,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "timestamp": time.time()
            }):
                yield event

            # 步骤 1: 接收查询（保留，作为唯一的初始化步骤�?
            step_start = time.time()
            step_timings["receive_query"] = (time.time() - step_start) * 1000

            for event in send_event("step", {
                "step": 1,
                "message": "理解问题",
                "detail": f"正在分析: {request.query[:50]}...",
                "status": "running"
            }):
                yield event

            for event in send_event("progress", {"value": 10}):
                yield event

            # 🔧 删除了步�?2（租户隔离验证）和步�?3（AgentV2 处理�?
            # 这些是内部步骤，对用户无价�?

            # 缓存检查（内部处理，不发送步骤）
            step_start = time.time()
            cache_manager = get_cache_manager()
            cache_hit = False
            cached_data = None

            if cache_manager is not None:
                cache_key = TenantCacheKeyGenerator.generate_v2_query_key(
                    tenant_id, user_id, request.query, request.session_id
                )
                cached_data = await cache_manager.cache.get(cache_key)
                cache_hit = cached_data is not None

            step_timings["cache_check"] = (time.time() - step_start) * 1000

            # 🔧 占比查询强制跳过缓存（因为需要实时计算）
            # 占比查询的结果依赖于实时数据计算，缓存可能导致显示过时的百分�?
            if is_proportion_query(request.query):
                cache_hit = False
                cached_data = None
                logger.info(f"[占比查询] 检测到占比查询，跳过缓存强制重新执�? {request.query[:50]}")

            if cache_hit and cached_data:
                # 缓存命中 - 流式返回缓存结果
                step_timings["agent_execution"] = 0

                # 🔧 修复：发�?从缓存加�?步骤开始事�?
                for event in send_event("step", {
                    "step": 1,
                    "message": "从缓存加�?,
                    "detail": f"使用缓存的查询结�?,
                    "status": "running"
                }):
                    yield event

                # 从缓存数据中提取答案
                cached_answer = cached_data.get("answer", "")
                processing_steps = cached_data.get("processing_steps", [])

                for event in send_event("progress", {"value": 80}):
                    yield event

                # 分块发送答�?
                step_start = time.time()
                chunk_size = 200
                for i in range(0, len(cached_answer), chunk_size):
                    chunk = cached_answer[i:i+chunk_size]
                    progress = 80 + int((i / len(cached_answer)) * 15)

                    for event in send_event("data", {
                        "chunk": chunk,
                        "progress": progress
                    }):
                        yield event

                step_timings["answer_streaming"] = (time.time() - step_start) * 1000

                # 🔧 修复：发送缓存步骤完成事�?
                for event in send_event("step", {
                    "step": 1,
                    "message": "从缓存加�?,
                    "detail": f"已从缓存加载结果",
                    "status": "completed",
                    "duration": round((time.time() - overall_start) * 1000, 2)
                }):
                    yield event

                # 计算总处理时�?
                total_processing_time_ms = (time.time() - overall_start) * 1000

                # 完成事件
                log_performance(
                    step="stream_query_cache_hit",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    duration_ms=total_processing_time_ms,
                    metadata={
                        "query_length": len(request.query),
                        "answer_length": len(cached_answer),
                        "step_timings": step_timings,
                        "cache_hit": True
                    }
                )

                for event in send_event("done", {
                    "success": True,
                    "answer": cached_answer,
                    "processing_steps": processing_steps,
                    "tenant_id": tenant_id,
                    "processing_time_ms": round(total_processing_time_ms, 2),
                    "step_timings": {k: round(v, 2) for k, v in step_timings.items()},
                    "from_cache": True
                }):
                    yield event

                for event in send_event("progress", {"value": 100}):
                    yield event

            else:
                # 缓存未命�?- 执行 AgentV2 查询
                step_start = time.time()
                try:
                    # 🔧 修复：使用依赖注入的 agent_factory（包含中间件�?
                    # 而不是直接调�?get_default_factory()
                    # 🔧 使用依赖注入�?db 会话（FastAPI 自动管理生命周期�?
                    agent = agent_factory.get_or_create_agent(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        session_id=request.session_id,
                        connection_id=request.connection_id,
                        db_session=db,
                        force_refresh=True  # 🔧 强制刷新以确保使用最新的系统提示�?
                    )

                    # 🔧 使用原始用户查询（CHART_GUIDANCE_TEMPLATE 已包含图表生成指令）
                    agent_input = {
                        "messages": [
                            {"role": "user", "content": request.query}
                        ]
                    }

                    # 🔧 删除�?AgentV2 处理步骤的发送，直接进入实际工具调用
                    for event in send_event("progress", {"value": 20}):
                        yield event

                        # 🔧🔧🔧 使用 astream_events 实现真正�?token 级别流式输出
                        # 参�? LangGraph 文档 - Streaming Events
                        # astream_events 可以捕获 LLM 生成过程中的每个 token
                        all_messages = []
                        accumulated_answer = ""
                        step_count = 0
                        processing_step_number = 1  # 🔧 从步�?开始计数（删除了步�?�?�?
                        last_progress_update = time.time()
                        current_tool_call = None  # 跟踪当前工具调用

                        # 🔧 新增：诊断计数器
                        tool_start_events = 0
                        tool_end_events = 0
                        llm_stream_events = 0

                        # 🔧 添加超时保护
                        STREAM_TIMEOUT = 120.0  # 120秒超�?
                        agent_start_time = time.time()

                        # 🔧 包装 astream_events 以捕获异常和超时
                        try:
                            async for event in agent.astream_events(
                                agent_input,
                                config={
                                    "configurable": {"thread_id": request.session_id},
                                    "recursion_limit": 50  # 🔧 提高递归限制，避免复杂工作流达到限制
                                },
                                version="v2"
                            ):
                                # 🔧 检查超�?
                                elapsed = time.time() - agent_start_time
                                if elapsed > STREAM_TIMEOUT:
                                    logger.error(f"[V2 Stream] Agent 执行超时: {elapsed:.1f}�?)
                                    raise asyncio.TimeoutError(f"Agent execution exceeded {STREAM_TIMEOUT} seconds")

                                event_kind = event.get("event", "")
                                event_data = event.get("data", {})

                                # 🔧 处理 LLM 流式输出 (token 级别)
                                if event_kind == "on_chat_model_stream":
                                    llm_stream_events += 1
                                    chunk = event_data.get("chunk")
                                    if chunk and hasattr(chunk, "content") and chunk.content:
                                        # 累积答案
                                        accumulated_answer += chunk.content

                                        # 计算进度 (30% -> 80%)
                                        step_count += 1
                                        progress = 30 + min(int((step_count / 100) * 50), 50)

                                        # 实时发送每�?token
                                        for sse in send_event("data", {
                                            "chunk": chunk.content,
                                            "progress": progress
                                        }):
                                            yield sse

                                        # 定期发送进度更新（�?0.5 秒）
                                        now = time.time()
                                        if now - last_progress_update > 0.5:
                                            for sse in send_event("progress", {"value": progress}):
                                                yield sse
                                            last_progress_update = now

                                # 🔧 处理工具调用开�?
                                elif event_kind == "on_tool_start":
                                    tool_start_events += 1
                                    tool_name = event.get("name", "unknown")
                                    tool_input = event_data.get("input", {})
                                    logger.info(f"[V2 Stream] 🔧 on_tool_start: tool={tool_name}, count={tool_start_events}")

                                    processing_step_number += 1
                                    step_data = {
                                        "step": processing_step_number,
                                        "message": f"调用工具: {tool_name}",
                                        "status": "running",
                                        "duration": 0
                                    }

                                    # 根据工具类型添加内容详情
                                    if "sql" in tool_name.lower() or "query" in tool_name.lower():
                                        sql_query = tool_input.get("query") or tool_input.get("sql", "")
                                        if sql_query:
                                            # 使用友好的步骤标题，避免被前端过滤器隐藏
                                            # 标题包含"SQL"�?生成"以匹配前端图标逻辑
                                            step_data["message"] = "生成SQL语句"
                                            step_data["content_type"] = "sql"
                                            step_data["content_data"] = {"sql": sql_query}
                                            step_data["detail"] = f"AI已生成SQL: {sql_query[:80]}..."
                                    elif "schema" in tool_name.lower():
                                        step_data["message"] = "获取数据库结�?
                                        step_data["detail"] = f"�? {tool_input.get('table_name', 'unknown')}"
                                    elif "list" in tool_name.lower() and "table" in tool_name.lower():
                                        step_data["message"] = "列出数据库表"
                                        step_data["detail"] = "正在获取表列�?.."
                                    elif "chart" in tool_name.lower():
                                        step_data["message"] = "生成图表"
                                        step_data["detail"] = "正在生成可视化图�?.."

                                    # 🔧 保存 tool_input 用于后续查询历史记录
                                    step_data["_tool_input"] = tool_input
                                    step_data["_tool_name"] = tool_name
                                    current_tool_call = step_data
                                    for sse in send_event("step", step_data):
                                        yield sse

                                # 🔧 处理工具调用结束
                                elif event_kind == "on_tool_end":
                                    tool_end_events += 1

                                    # 🆕 检测循环检测的终止信号
                                    raw_output = event_data.get("output", "")
                                    if hasattr(raw_output, 'additional_kwargs'):
                                        additional_kwargs = raw_output.additional_kwargs
                                        if additional_kwargs.get('_loop_detected') or additional_kwargs.get('_force_terminate'):
                                            logger.warning("[V2 Stream] 检测到循环终止信号，中�?Agent 执行")
                                            # 发送终止事�?
                                            error_content = raw_output.content if hasattr(raw_output, 'content') else str(raw_output)
                                            for sse in send_event("error", {
                                                "error": "检测到循环，已终止",
                                                "error_type": "loop_detected",
                                                "detail": error_content
                                            }):
                                                yield sse

                                            # 发送完成事件（确保前端能够完成处理�?
                                            total_processing_time_ms = (time.time() - overall_start) * 1000
                                            for sse in send_event("done", {
                                                "success": False,
                                                "answer": error_content,
                                                "processing_steps": [],
                                                "processing_time_ms": round(total_processing_time_ms, 2),
                                                "terminated": True,
                                                "termination_reason": "loop_detected"
                                            }):
                                                yield sse
                                            return  # 终止事件生成�?

                                    if current_tool_call:
                                        raw_output = event_data.get("output", "")
                                        tool_name = event.get("name", "unknown")

                                        # 🔧 修复：LangGraph �?on_tool_end 返回的是 ToolMessage 对象
                                        # 需要从 content 属性获取实际的字符串输�?
                                        if hasattr(raw_output, 'content'):
                                            tool_output = raw_output.content
                                            logger.info(f"[V2 Stream] on_tool_end: tool={tool_name}, ToolMessage detected, content_len={len(tool_output) if tool_output else 0}")
                                        else:
                                            tool_output = raw_output if isinstance(raw_output, str) else str(raw_output)
                                            logger.info(f"[V2 Stream] on_tool_end: tool={tool_name}, raw output, type={type(raw_output).__name__}")

                                        # 🔧 新增：记录工具输出的�?00个字符用于诊�?
                                        if tool_output and isinstance(tool_output, str):
                                            logger.info(f"[V2 Stream] on_tool_end: tool={tool_name}, output_preview={tool_output[:200]}")
                                        else:
                                            logger.warning(f"[V2 Stream] on_tool_end: tool={tool_name}, 无输出或输出格式异常, type={type(tool_output)}")

                                        current_tool_call["status"] = "completed"
                                        current_tool_call["duration"] = 100  # 估算时间

                                        # 🔧 增强：根据工具类型提取有用信息到 detail
                                        tool_message = current_tool_call.get("message", "")
                                        if tool_output and isinstance(tool_output, str):
                                            try:
                                                import json as json_module
                                                output_data = json_module.loads(tool_output)

                                                # 列出数据库表 - 显示表名列表
                                                if "列出数据库表" in tool_message or "list" in tool_message.lower():
                                                    if isinstance(output_data, list):
                                                        table_names = [t.get("table_name", t.get("name", str(t))) if isinstance(t, dict) else str(t) for t in output_data[:10]]
                                                        current_tool_call["detail"] = f"找到 {len(output_data)} 张表: {', '.join(table_names)}"
                                                        if len(output_data) > 10:
                                                            current_tool_call["detail"] += "..."

                                                # 获取数据库结�?- 显示列信�?
                                                elif "获取数据库结�? in tool_message or "schema" in tool_message.lower():
                                                    if isinstance(output_data, dict):
                                                        columns = output_data.get("columns", [])
                                                        if columns:
                                                            col_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in columns[:5]]
                                                            current_tool_call["detail"] = f"包含 {len(columns)} �? {', '.join(col_names)}"
                                                            if len(columns) > 5:
                                                                current_tool_call["detail"] += "..."
                                            except (json_module.JSONDecodeError, TypeError):
                                                pass

                                        for sse in send_event("step", current_tool_call):
                                            yield sse

                                        # 🔧 从工具输出中提取表格数据 - 增强�?
                                        if tool_output and isinstance(tool_output, str):
                                            # 🔧 优先检查：如果工具名称包含query/execute，说明是查询工具
                                            is_query_tool = any(keyword in tool_name.lower() for keyword in
                                                ['query', 'execute', 'select', 'sql', 'run_query'])

                                            # 尝试解析�?JSON 表格数据
                                            try:
                                                import json as json_module
                                                output_data = json_module.loads(tool_output)
                                                logger.info(f"[V2 Stream] 工具输出解析成功，类�? {type(output_data).__name__}, tool={tool_name}")

                                                # 检测是否为表格格式（包�?columns �?data/rows�?
                                                if isinstance(output_data, dict):
                                                    columns = output_data.get("columns", [])
                                                    rows = output_data.get("data", output_data.get("rows", []))
                                                    row_count = output_data.get("row_count", len(rows) if isinstance(rows, list) else 0)
                                                    logger.info(f"[V2 Stream] 检测表格数�? columns={len(columns)}, rows={len(rows) if rows else 0}, row_count={row_count}")

                                                    # 🔧 过滤元数据查询：只对真正的数据查询发送表格步�?
                                                    # 检查工具名称，排除 list_tables �?get_schema 等元数据工具
                                                    is_metadata_tool = any(keyword in tool_message.lower() for keyword in
                                                        ['list_tables', 'get_schema', '列出数据库表', '获取数据库结�?,
                                                         'list tables', 'database tables', 'schema'])

                                                    if columns and rows and not is_metadata_tool:
                                                        # 发送表格数据步�?
                                                        processing_step_number += 1
                                                        source_label = tool_name if 'tool_name' in locals() else tool_message
                                                        sanitized_table = sanitize_table_numbers({
                                                            "columns": columns,
                                                            "rows": rows[:50],  # 限制�?0�?
                                                            "row_count": row_count,
                                                            "source_label": source_label
                                                        })
                                                        table_step = {
                                                            "step": processing_step_number,
                                                            "message": "查询结果",
                                                            "status": "completed",
                                                            "duration": 50,
                                                            "content_type": "table",
                                                            "content_data": {
                                                                "table": sanitized_table
                                                            }
                                                        }
                                                        for sse in send_event("step", table_step):
                                                            yield sse
                                                        logger.info(f"[V2 Stream] 发送表格数�? {row_count} �? {len(columns)} �?)
                                                        # 🔧 保存表格数据用于自动生成图表（累积模式）
                                                        # 获取当前查询的SQL（如果可用）
                                                        current_query = ""
                                                        if current_tool_call and "_tool_input" in current_tool_call:
                                                            current_query = current_tool_call["_tool_input"].get("query", "")

                                                        # 累积查询历史（用于占比计算）
                                                        collected_table_data["query_history"].append({
                                                            "query": current_query,
                                                            "columns": columns,
                                                            "rows": rows[:100],
                                                            "row_count": row_count,
                                                            "timestamp": time.time()
                                                        })
                                                        logger.info(f"[V2 Stream] 累积查询历史: 当前历史记录�?{len(collected_table_data['query_history'])}")

                                                        # 更新当前数据（用于兼容性）
                                                        collected_table_data["columns"] = columns
                                                        collected_table_data["rows"] = rows[:100]
                                                        collected_table_data["has_data"] = True

                                                # 检测是否为列表格式（直接是行数组）
                                                elif isinstance(output_data, list) and len(output_data) > 0:
                                                    if isinstance(output_data[0], dict):
                                                        columns = list(output_data[0].keys())
                                                        rows = output_data
                                                        row_count = len(rows)

                                                        # 🔧 过滤元数据查询：只对真正的数据查询发送表格步�?
                                                        is_metadata_tool = any(keyword in tool_message.lower() for keyword in
                                                            ['list_tables', 'get_schema', '列出数据库表', '获取数据库结�?,
                                                             'list tables', 'database tables', 'schema'])

                                                        # 发送表格数据步骤（仅非元数据查询）
                                                        if not is_metadata_tool:
                                                            processing_step_number += 1
                                                            source_label = tool_name if 'tool_name' in locals() else tool_message
                                                            sanitized_table = sanitize_table_numbers({
                                                                "columns": columns,
                                                                "rows": rows[:50],
                                                                "row_count": row_count,
                                                                "source_label": source_label
                                                            })
                                                            table_step = {
                                                                "step": processing_step_number,
                                                                "message": "查询结果",
                                                                "status": "completed",
                                                                "duration": 50,
                                                                "content_type": "table",
                                                                "content_data": {
                                                                    "table": sanitized_table
                                                                }
                                                            }
                                                            for sse in send_event("step", table_step):
                                                                yield sse
                                                            logger.info(f"[V2 Stream] 发送表格数�?(列表): {row_count} �?)
                                                            # 🔧 保存表格数据用于自动生成图表（累积模式）
                                                            # 获取当前查询的SQL（如果可用）
                                                            current_query = ""
                                                            if current_tool_call and "_tool_input" in current_tool_call:
                                                                current_query = current_tool_call["_tool_input"].get("query", "")

                                                            # 累积查询历史（用于占比计算）
                                                            collected_table_data["query_history"].append({
                                                                "query": current_query,
                                                                "columns": columns,
                                                                "rows": rows[:100],
                                                                "row_count": row_count,
                                                                "timestamp": time.time()
                                                            })
                                                            logger.info(f"[V2 Stream] 累积查询历史(列表): 当前历史记录�?{len(collected_table_data['query_history'])}")

                                                            # 更新当前数据（用于兼容性）
                                                            collected_table_data["columns"] = columns
                                                            collected_table_data["rows"] = rows[:100]
                                                            collected_table_data["has_data"] = True
                                            except (json_module.JSONDecodeError, TypeError) as json_err:
                                                # 🔧 JSON 解析失败，尝试备用方�?
                                                logger.warning(f"[V2 Stream] JSON解析失败: {json_err}, tool={tool_name}, 尝试备用解析")

                                                # 备用方案1: 尝试从字符串化数据中提取表格信息
                                                # 某些MCP工具返回的是字符串格式的JSON
                                                try:
                                                    # 清理可能的转义字�?
                                                    cleaned_output = tool_output.strip()
                                                    if cleaned_output.startswith('"') and cleaned_output.endswith('"'):
                                                        # 去除外层引号
                                                        cleaned_output = cleaned_output[1:-1]
                                                        # 处理转义
                                                        cleaned_output = cleaned_output.replace('\\"', '"').replace('\\\\', '\\')

                                                    # 再次尝试解析
                                                    output_data = json_module.loads(cleaned_output)
                                                    logger.info(f"[V2 Stream] 备用解析成功，类�? {type(output_data).__name__}")

                                                    # 重新进入表格检测逻辑
                                                    if isinstance(output_data, dict):
                                                        columns = output_data.get("columns", [])
                                                        rows = output_data.get("data", output_data.get("rows", []))
                                                        row_count = output_data.get("row_count", len(rows) if isinstance(rows, list) else 0)

                                                        is_metadata_tool = any(keyword in tool_message.lower() for keyword in
                                                            ['list_tables', 'get_schema', '列出数据库表', '获取数据库结�?,
                                                             'list tables', 'database tables', 'schema'])

                                                    if columns and rows and not is_metadata_tool:
                                                        processing_step_number += 1
                                                        source_label = tool_name if 'tool_name' in locals() else tool_message
                                                        sanitized_table = sanitize_table_numbers({
                                                            "columns": columns,
                                                            "rows": rows[:50],
                                                            "row_count": row_count,
                                                            "source_label": source_label
                                                        })
                                                        table_step = {
                                                            "step": processing_step_number,
                                                            "message": "查询结果",
                                                            "status": "completed",
                                                            "duration": 50,
                                                            "content_type": "table",
                                                            "content_data": {
                                                                "table": sanitized_table
                                                            }
                                                        }
                                                        for sse in send_event("step", table_step):
                                                            yield sse
                                                        logger.info(f"[V2 Stream] 备用解析发送表格数�? {row_count} �?)
                                                        # 🔧 累积查询历史（备用解析方案）
                                                        current_query = ""
                                                        if current_tool_call and "_tool_input" in current_tool_call:
                                                            current_query = current_tool_call["_tool_input"].get("query", "")
                                                        collected_table_data["query_history"].append({
                                                            "query": current_query,
                                                            "columns": columns,
                                                            "rows": rows[:100],
                                                            "row_count": row_count,
                                                            "timestamp": time.time()
                                                        })
                                                        collected_table_data["columns"] = columns
                                                        collected_table_data["rows"] = rows[:100]
                                                        collected_table_data["has_data"] = True

                                                except Exception as backup_err:
                                                    logger.warning(f"[V2 Stream] 备用解析也失�? {backup_err}")

                                                # 备用方案2: 尝试从纯文本表格中提取数据（针对MCP PostgreSQL工具的文本格式）
                                                # PostgreSQL MCP 工具可能返回格式化文本表�?
                                                if is_query_tool and len(tool_output) > 0:
                                                    logger.info(f"[V2 Stream] 检测到查询工具，尝试解析文本格式输�?)

                                                    lines = tool_output.strip().split('\n')
                                                    if len(lines) >= 3:
                                                        # 尝试解析文本表格（假设有表头分隔符）
                                                        # 格式通常是：
                                                        # | col1 | col2 | col3 |
                                                        # |------|------|------|
                                                        # | val1 | val2 | val3 |
                                                        import re as re_module
                                                        header_line = None
                                                        data_start_idx = None

                                                        for idx, line in enumerate(lines):
                                                            if '|' in line:
                                                                if header_line is None:
                                                                    header_line = line
                                                                elif data_start_idx is None and re.match(r'^\|[\s\-:]+\|$', line.strip()):
                                                                    data_start_idx = idx + 1

                                                        if header_line and data_start_idx:
                                                            # 解析表头
                                                            columns = [col.strip() for col in header_line.split('|') if col.strip()]
                                                            logger.info(f"[V2 Stream] 文本表格解析: columns={columns}")

                                                            # 解析数据�?
                                                            rows = []
                                                            for line in lines[data_start_idx:]:
                                                                if '|' in line and not line.strip().startswith('+') and not line.strip().startswith('-'):
                                                                    values = [val.strip() for val in line.split('|') if val.strip()]
                                                                    if len(values) == len(columns):
                                                                        rows.append(values)

                                                        if rows:
                                                            logger.info(f"[V2 Stream] 文本表格解析成功: {len(rows)} �?)
                                                            processing_step_number += 1
                                                            source_label = tool_name if 'tool_name' in locals() else tool_message
                                                            sanitized_table = sanitize_table_numbers({
                                                                "columns": columns,
                                                                "rows": rows[:50],
                                                                "row_count": len(rows),
                                                                "source_label": source_label
                                                            })
                                                            table_step = {
                                                                "step": processing_step_number,
                                                                "message": "查询结果",
                                                                "status": "completed",
                                                                "duration": 50,
                                                                "content_type": "table",
                                                                "content_data": {
                                                                    "table": sanitized_table
                                                                }
                                                            }
                                                            for sse in send_event("step", table_step):
                                                                yield sse
                                                            # 🔧 累积查询历史（文本表格解析）
                                                            current_query = ""
                                                            if current_tool_call and "_tool_input" in current_tool_call:
                                                                current_query = current_tool_call["_tool_input"].get("query", "")
                                                            collected_table_data["query_history"].append({
                                                                "query": current_query,
                                                                "columns": columns,
                                                                "rows": rows[:100],
                                                                "row_count": len(rows),
                                                                "timestamp": time.time()
                                                            })
                                                            collected_table_data["columns"] = columns
                                                            collected_table_data["rows"] = rows[:100]
                                                            collected_table_data["has_data"] = True

                                        current_tool_call = None

                                # 🔧 处理 LLM 调用结束（收集最终消息）
                                elif event_kind == "on_chat_model_end":
                                    output = event_data.get("output")
                                    if output:
                                        all_messages.append(output)

                        except asyncio.TimeoutError as te:
                            # 🔧 处理超时错误
                            logger.error(f"[V2 Stream] 查询超时: {te}")

                            # 发送超时错误事�?
                            for event in send_event("error", {
                                "error": "查询超时",
                                "error_type": "timeout",
                                "detail": f"查询时间超过 {int(STREAM_TIMEOUT)} 秒，请简化查询条�?
                            }):
                                yield event

                            # 🔧 新增：发送步�?完成事件（让前端完成步骤显示�?
                            step1_duration = round((time.time() - overall_start) * 1000, 2)
                            for event in send_event("step", {
                                "step": 1,
                                "message": "理解问题",
                                "detail": f"已分�? {request.query[:50]}...",
                                "status": "completed",
                                "duration": step1_duration
                            }):
                                yield event

                            # 🔧 发送done事件（确保前端能够完成处理）
                            # 新增：解研班分成命中的查询历�?
                        query_chain = []
                        query_history = collected_table_data.get("query_history", []) if isinstance(collected_table_data, dict) else []
                        for idx, h in enumerate(query_history or []):
                            if isinstance(h, dict):
                                query_chain.append({
                                    "step": idx + 1,
                                    "sql": h.get("query") or h.get("sql"),
                                    "row_count": len(h.get("rows", []) or []),
                                    "columns": h.get("columns") or []
                                })

                        # 分布回调
                        rows_dict = []
                        if isinstance(collected_table_data, dict) and collected_table_data.get("rows"):
                            cols = collected_table_data.get("columns") or []
                            for row in collected_table_data.get("rows", []):
                                if isinstance(row, list):
                                    rows_dict.append({c: row[i] if i < len(row) else None for i, c in enumerate(cols)})
                                elif isinstance(row, dict):
                                    rows_dict.append(row)

                        lineage = build_cell_lineage(
                            query_history[-1].get("query") if query_history else None,
                            rows_dict
                        ) if rows_dict else []
                        insights = generate_insights_from_rows(rows_dict, request.query) if rows_dict else []

                        chart_validation = None
                        if chart_config:
                            try:
                                chart_obj = json.loads(chart_config) if isinstance(chart_config, str) else chart_config
                            except Exception:
                                chart_obj = None
                            required_fields = []
                            if isinstance(chart_obj, dict):
                                required_fields = [chart_obj.get("x_field"), chart_obj.get("y_field")]
                            last_sql = query_history[-1].get("query") if query_history else ""
                            if chart_obj is not None:
                                chart_validation = validate_chart_fields_in_sql(
                                    last_sql or "",
                                    rows_dict,
                                    required_fields
                                ).model_dump()
                                if chart_validation and not chart_validation.get("is_valid"):
                                    chart_config = None

                        for event in send_event("done", {
                                "success": False,
                                "answer": f"查询超时（超�?{int(STREAM_TIMEOUT)} 秒），请简化查询条件或稍后重试",
                                "processing_steps": [
                                    {"step": 1, "title": "理解问题", "status": "completed", "duration": step1_duration},
                                    {"step": 2, "title": "查询执行", "status": "error"}
                                ],
                            }):
                                yield event

                            return  # 确保不再继续执行

                        except Exception as agent_error:
                            # 🔧 处理 Agent 执行过程中的其他异常
                            logger.error(f"[V2 Stream] Agent 执行错误: {agent_error}")
                            import traceback
                            traceback.print_exc()
                            total_processing_time_ms = (time.time() - overall_start) * 1000

                            # 发送错误事�?
                            for event in send_event("error", {
                                "error": str(agent_error),
                                "error_type": "agent_error",
                                "detail": "AI 执行过程中出现错�?
                            }):
                                yield event

                            # 🔧 新增：发送步�?完成事件（让前端完成步骤显示�?
                            step1_duration = round(total_processing_time_ms, 2)
                            for event in send_event("step", {
                                "step": 1,
                                "message": "理解问题",
                                "detail": f"已分�? {request.query[:50]}...",
                                "status": "completed",
                                "duration": step1_duration
                            }):
                                yield event

                            # 🔧 新增：发送done事件（确保前端能够完成处理）
                            # 新增：解研班分成命中的查询历�?
                        query_chain = []
                        query_history = collected_table_data.get("query_history", []) if isinstance(collected_table_data, dict) else []
                        for idx, h in enumerate(query_history or []):
                            if isinstance(h, dict):
                                query_chain.append({
                                    "step": idx + 1,
                                    "sql": h.get("query") or h.get("sql"),
                                    "row_count": len(h.get("rows", []) or []),
                                    "columns": h.get("columns") or []
                                })

                        # 分布回调
                        rows_dict = []
                        if isinstance(collected_table_data, dict) and collected_table_data.get("rows"):
                            cols = collected_table_data.get("columns") or []
                            for row in collected_table_data.get("rows", []):
                                if isinstance(row, list):
                                    rows_dict.append({c: row[i] if i < len(row) else None for i, c in enumerate(cols)})
                                elif isinstance(row, dict):
                                    rows_dict.append(row)

                        lineage = build_cell_lineage(
                            query_history[-1].get("query") if query_history else None,
                            rows_dict
                        ) if rows_dict else []
                        insights = generate_insights_from_rows(rows_dict, request.query) if rows_dict else []

                        chart_validation = None
                        if chart_config:
                            try:
                                chart_obj = json.loads(chart_config) if isinstance(chart_config, str) else chart_config
                            except Exception:
                                chart_obj = None
                            required_fields = []
                            if isinstance(chart_obj, dict):
                                required_fields = [chart_obj.get("x_field"), chart_obj.get("y_field")]
                            last_sql = query_history[-1].get("query") if query_history else ""
                            if chart_obj is not None:
                                chart_validation = validate_chart_fields_in_sql(
                                    last_sql or "",
                                    rows_dict,
                                    required_fields
                                ).model_dump()
                                if chart_validation and not chart_validation.get("is_valid"):
                                    chart_config = None

                        for event in send_event("done", {
                                "success": False,
                                "answer": f"查询执行失败：{str(agent_error)}",
                                "processing_steps": [
                                    {"step": 1, "title": "理解问题", "status": "completed", "duration": step1_duration},
                                    {"step": 2, "title": "执行查询", "status": "error"}
                                ],
                                "processing_time_ms": round(total_processing_time_ms, 2),
                            }):
                                yield event

                            return  # 确保不再继续执行

                        step_timings["agent_execution"] = (time.time() - step_start) * 1000

                        # 🔧 新增：诊断日�?- 输出工具调用统计
                        logger.info(f"[V2 Stream] 🔧 诊断统计: tool_start_events={tool_start_events}, tool_end_events={tool_end_events}, llm_stream_events={llm_stream_events}")
                        if tool_start_events == 0:
                            logger.warning(f"[V2 Stream] ⚠️ 没有收到任何工具调用事件！LLM可能没有调用工具，直接生成了回答�?)
                        else:
                            logger.info(f"[V2 Stream] �?收到 {tool_start_events} 个工具调用开始事�?)

                        # 从流式消息中提取最终答�?
                        answer = accumulated_answer

                        # 🔧 新增：兜底机�?- 如果 answer 为空，检查是否有工具结果
                        if not answer or not answer.strip():
                            logger.warning("[V2 Stream] accumulated_answer 为空，尝试兜底处�?)

                            # 检查是否至少有工具调用（说明执行了但未生成文字�?
                            if processing_step_number > 1:
                                answer = "查询已执行，�?AI 未生成文字说明。请查看上方的处理步骤了解详情�?
                                logger.info(f"[V2 Stream] 生成兜底响应（有工具调用�?)
                            else:
                                answer = "查询处理中遇到问题，未返回任何结果。请检查后端日志或重试�?
                                logger.warning(f"[V2 Stream] 生成兜底响应（无工具调用�?)

                        # 🔧 新增：如果兜底后仍为空，基于 collected_table_data 生成回答
                        if not answer or not answer.strip():
                            logger.warning("[V2 Stream] answer 仍为空，基于 collected_table_data 生成兜底响应")

                            if collected_table_data["has_data"]:
                                rows = collected_table_data["rows"]
                                columns = collected_table_data["columns"]

                                # 尝试生成简单的数据总结
                                if len(rows) == 1 and len(columns) == 2:
                                    # 单行两列数据，可能是类别-数值对
                                    category = str(rows[0][0]) if len(rows[0]) > 0 else ""
                                    value = rows[0][1] if len(rows[0]) > 1 else 0
                                    answer = f"查询结果：{category} = {value}"
                                elif len(rows) > 0:
                                    answer = f"查询返回 {len(rows)} 行数�?
                                else:
                                    answer = ""  # 不显示任何提示，后续会使用智能分�?
                            else:
                                answer = "查询处理完成，但未返回数据�?

                        # 确保answer不为�?
                        if not answer:
                            answer = ""  # 不显示任何提示，后续会使用智能分�?

                        # 🔧 始终尝试提取图表配置（如果存在）
                        # 不再检�?include_chart 标志，因�?AI 可能会根据问题类型自主决定生成图�?
                        logger.info(f"[图表提取] AI 回答长度: {len(answer)}, 包含 [CHART_START]: {'[CHART_START]' in answer}")
                        chart_config = extract_chart_config_from_answer(answer)

                        # 🔧 使用验证函数检查提取的图表配置是否有效
                        if chart_config and _is_valid_chart_config(chart_config):
                            logger.info(f"[图表提取] �?AI 生成的图表配置有�? {chart_config[:100]}...")
                        elif chart_config:
                            # AI 生成了配置但无效，尝试使用兜底方�?
                            logger.warning(f"[图表提取] ⚠️ AI 生成的图表配置无效，将尝试兜底方�?)
                            chart_config = None

                        # 🔧 计划修复1：检测是否是分组查询（如"每个省市的客户数�?�?
                        query_lower = request.query.lower() if request.query else ""
                        is_group_by_query = any(kw in query_lower for kw in [
                            '每个', '�?, '分组', '每个省市', '每个地区', '每个城市',
                            '各个', '各省�?, '各地�?, '各城�?, '每种', '各类'
                        ])
                        if is_group_by_query:
                            logger.info(f"[图表自动生成] 🔍 检测到分组查询关键�? {request.query[:50]}...")

                        # 🔧 兜底方案：如果没有图表配置但有表格数据，自动生成
                        # 🆕 计划修复1：如果是分组查询且有表格数据，强制生成图�?
                        should_generate_chart = (
                            not chart_config and
                            collected_table_data["has_data"] and
                            collected_table_data["columns"] and
                            collected_table_data["rows"] and
                            len(collected_table_data["rows"]) > 0
                        )

                        if should_generate_chart:
                            logger.info(f"[图表自动生成] 📊 表格数据可用: 列数={len(collected_table_data['columns'])}, 行数={len(collected_table_data['rows'])}")
                            if is_group_by_query:
                                logger.info(f"[图表自动生成] 🎯 分组查询强制生成图表")
                            chart_config = generate_default_chart_config_from_table(
                                columns=collected_table_data["columns"],
                                rows=collected_table_data["rows"],
                                query=request.query
                            )
                            if chart_config and _is_valid_chart_config(chart_config):
                                logger.info(f"[图表自动生成] �?自动生成图表配置成功: {chart_config[:100]}...")
                            else:
                                logger.warning(f"[图表自动生成] �?自动生成失败或配置无�?)

                        # 🔧 最终图表配置状态日�?
                        if chart_config:
                            logger.info(f"[图表配置] �?最终图表配置长�? {len(chart_config)} 字符")
                            # 🔧 新增：打印图表配置的结构用于诊断
                            try:
                                chart_obj = json.loads(chart_config)
                                logger.info(f"[图表配置] 📊 图表结构: keys={list(chart_obj.keys())}, has_series={('series' in chart_obj)}")
                            except:
                                logger.info(f"[图表配置] 📊 图表配置是对象格式，非JSON字符�?)
                        else:
                            logger.warning(f"[图表配置] �?未生成有效的图表配置")
                            # 🔧 新增：诊断为什么没有图表配�?
                            logger.warning(f"[图表配置诊断] collected_table_data.has_data={collected_table_data.get('has_data')}, columns={len(collected_table_data.get('columns', []))}")
                            logger.warning(f"[图表配置诊断] answer长度={len(answer)}, has_chart_marker={'[CHART_START]' in answer}")

                        # 计算总处理时�?
                        total_processing_time_ms = (time.time() - overall_start) * 1000

                        # 完成事件
                        processing_steps = [
                            "接收查询",
                            "租户隔离验证",
                            "AgentV2 处理",
                            "DeepSeek LLM 调用",
                            "返回结果"
                        ]

                        # 记录性能日志
                        log_performance(
                            step="stream_query_complete",
                            tenant_id=tenant_id,
                            user_id=user_id,
                            duration_ms=total_processing_time_ms,
                            metadata={
                                "query_length": len(request.query),
                                "answer_length": len(answer),
                                "step_timings": step_timings,
                                "processing_steps": processing_steps,
                                "connection_id": request.connection_id,
                            "query_chain": query_chain,
                            "chart_validation": chart_validation,
                            "lineage": lineage,
                            "insights": insights
                            }
                        )

                        # 存储到缓存（如果缓存管理器可用）
                        if cache_manager is not None and answer:
                            cache_key = TenantCacheKeyGenerator.generate_v2_query_key(
                                tenant_id, user_id, request.query, request.session_id
                            )
                            cache_data = {
                                "answer": answer,
                                "processing_steps": processing_steps,
                                "query": request.query
                            }
                            await cache_manager.cache.set(cache_key, cache_data, ttl=600)
                            logger.debug(f"查询结果已缓�? {cache_key}")

                        # 🔧 智能兜底：如�?answer 为空，基�?collected_table_data 生成分析
                        if answer and answer.strip():
                            final_answer = answer
                        elif collected_table_data["has_data"]:
                            final_answer = _generate_smart_analysis(
                                collected_table_data["rows"],
                                collected_table_data["columns"],
                                request.query,
                                collected_table_data.get("query_history", [])
                            )
                            logger.info(f"[智能分析] 基于 collected_table_data 生成分析，长�? {len(final_answer)}")
                        else:
                            # 🔧 修复：始终返回至少一个占位符，避免前端显示空�?
                            final_answer = "查询已完成，请查看上方处理步骤�?

                        # 🔧 修复：发送步�?完成事件（理解问题步骤）
                        # 使用 overall_start 计算准确的持续时�?
                        step1_duration = round((time.time() - overall_start) * 1000, 2)
                        for event in send_event("step", {
                            "step": 1,
                            "message": "理解问题",
                            "detail": f"已分�? {request.query[:50]}...",
                            "status": "completed",
                            "duration": step1_duration
                        }):
                            yield event

                        # 🔧 新增：占比查询的一致性检查（先检查表一致性，再验证数值）
                        query_history = collected_table_data.get("query_history", [])
                        if is_proportion_query(request.query) and len(query_history) >= 2:
                            # Step 1: 检查分子分母是否来自同一张表
                            is_consistent, consistency_error = _check_table_consistency(query_history)
                            if not is_consistent:
                                # 检测到跨表问题，添加警告信息到回答
                                logger.warning(f"[表一致性] 检测到跨表问题，添加警�?)
                                final_answer = f"⚠️ {consistency_error}\n\n{final_answer}"
                                answer = final_answer

                            # Step 2: 动态数值验�?
                            logger.info(f"[数值验证] 检测到占比查询且有{len(query_history)}条历史记录，进行动态验�?)
                            validated_answer, needs_fix = _validate_and_fix_percentage(
                                final_answer,
                                query_history
                            )
                            if needs_fix:
                                final_answer = validated_answer
                                # 同时更新 accumulated_answer 以便后续使用
                                answer = validated_answer

                        # 🔧 新增 v6：增强占比查询响应（�?GROUP BY 查询添加分布分析�?
                        if is_proportion_query(request.query) and collected_table_data.get("has_data"):
                            rows = collected_table_data.get("rows", [])
                            columns = collected_table_data.get("columns", [])

                            # 检查是否为 GROUP BY 查询结果（多行数据）
                            if len(rows) > 1 and columns:
                                # 将行数据转换为字典格�?
                                data_list = []
                                for row in rows:
                                    row_dict = {}
                                    for i, col in enumerate(columns):
                                        if i < len(row):
                                            row_dict[col] = row[i]
                                    data_list.append(row_dict)

                                # 调用增强函数
                                enhanced_answer = enhance_proportion_response(
                                    final_answer,
                                    data_list,
                                    request.query
                                )
                                if enhanced_answer != final_answer:
                                    logger.info(f"[占比增强] 已添加分布分析到响应")
                                    final_answer = enhanced_answer
                                    answer = enhanced_answer

                        # 🔧 新增：使用查询历史生成占比图表（优先级更高）
                        if not chart_config and is_proportion_query(request.query) and len(query_history) >= 2:
                            logger.info(f"[图表生成] 检测到占比查询且有{len(query_history)}条历史记录，尝试生成占比图表")
                            history_chart = generate_proportion_chart_from_history(
                                query_history,
                                request.query
                            )
                            if history_chart and _is_valid_chart_config(history_chart):
                                chart_config = history_chart
                                logger.info(f"[图表生成] �?基于查询历史生成占比图表成功")

                        # 🆕 发送数据分析步�?- 跨表警告、AI回答和多维度分析共存
                        parts = []

                        # 1. 添加跨表警告（如果有�?
                        has_cross_table_warning = False
                        if is_proportion_query(request.query):
                            query_history = collected_table_data.get("query_history", [])
                            if len(query_history) >= 2:
                                is_consistent, consistency_error = _check_table_consistency(query_history)
                                if not is_consistent:
                                    parts.append(f"{consistency_error}\n\n")
                                    has_cross_table_warning = True

                        # 2. 添加 AI 回答（如果有原始 AI 分析�?
                        if final_answer and final_answer.strip():
                            # 过滤掉跨表警告（避免重复�?
                            ai_only_answer = final_answer
                            if has_cross_table_warning and final_answer.startswith("⚠️"):
                                # 移除已添加的警告部分
                                warning_end = final_answer.find("\n\n") + 2
                                if warning_end > 0:
                                    ai_only_answer = final_answer[warning_end:]
                            if ai_only_answer.strip():
                                parts.append(ai_only_answer.strip() + "\n\n")

                        # 3. 添加多维度数据分析（始终生成�?
                        if collected_table_data["has_data"]:
                            smart_analysis = _generate_smart_analysis(
                                collected_table_data["rows"],
                                collected_table_data["columns"],
                                request.query,
                                collected_table_data.get("query_history", [])
                            )
                            parts.append(smart_analysis)

                        # 4. 发送完整的分析内容
                        analysis_content = "".join(parts)

                        # 🔧 修复：确保始终发送数据分析步�?
                        analysis_step_number = processing_step_number + 1
                        if not analysis_content or not analysis_content.strip():
                            # 确保始终有内容可发�?
                            analysis_content = "📊 **数据分析**\n\n查询已完成，请查看上方处理步骤�?

                        for event in send_event("step", {
                            "step": analysis_step_number,
                            "message": "数据分析",
                            "title": "数据分析总结",
                            "detail": "AI对查询结果进行详细解读和分析",
                            "status": "completed",
                            "duration": round((time.time() - overall_start) * 1000, 2),
                            "content_type": "text",
                            "content_data": {
                                "text": analysis_content
                            }
                        }):
                            yield event
                        logger.info(f"[数据分析] �?已发送数据分析步�?(步骤{analysis_step_number}), 内容长度: {len(analysis_content)}")

                        # 🔧 新增：发送图表步骤（如果有图表配置）
                        if chart_config and _is_valid_chart_config(chart_config):
                            chart_step_number = analysis_step_number + 1
                            try:
                                chart_obj = json.loads(chart_config) if isinstance(chart_config, str) else chart_config
                            except:
                                chart_obj = chart_config

                            for event in send_event("step", {
                                "step": chart_step_number,
                                "message": "图表生成",
                                "title": "数据可视�?,
                                "detail": "自动生成数据图表",
                                "status": "completed",
                                "duration": 100,
                                "content_type": "chart",
                                "content_data": {
                                    "chart": chart_obj
                                }
                            }):
                                yield event
                            logger.info(f"[图表步骤] �?已发送图表步�?(步骤{chart_step_number})")

                        # 新增：解研班分成命中的查询历�?
                        query_chain = []
                        query_history = collected_table_data.get("query_history", []) if isinstance(collected_table_data, dict) else []
                        for idx, h in enumerate(query_history or []):
                            if isinstance(h, dict):
                                query_chain.append({
                                    "step": idx + 1,
                                    "sql": h.get("query") or h.get("sql"),
                                    "row_count": len(h.get("rows", []) or []),
                                    "columns": h.get("columns") or []
                                })

                        # 分布回调
                        rows_dict = []
                        if isinstance(collected_table_data, dict) and collected_table_data.get("rows"):
                            cols = collected_table_data.get("columns") or []
                            for row in collected_table_data.get("rows", []):
                                if isinstance(row, list):
                                    rows_dict.append({c: row[i] if i < len(row) else None for i, c in enumerate(cols)})
                                elif isinstance(row, dict):
                                    rows_dict.append(row)

                        lineage = build_cell_lineage(
                            query_history[-1].get("query") if query_history else None,
                            rows_dict
                        ) if rows_dict else []
                        insights = generate_insights_from_rows(rows_dict, request.query) if rows_dict else []

                        chart_validation = None
                        if chart_config:
                            try:
                                chart_obj = json.loads(chart_config) if isinstance(chart_config, str) else chart_config
                            except Exception:
                                chart_obj = None
                            required_fields = []
                            if isinstance(chart_obj, dict):
                                required_fields = [chart_obj.get("x_field"), chart_obj.get("y_field")]
                            last_sql = query_history[-1].get("query") if query_history else ""
                            if chart_obj is not None:
                                chart_validation = validate_chart_fields_in_sql(
                                    last_sql or "",
                                    rows_dict,
                                    required_fields
                                ).model_dump()
                                if chart_validation and not chart_validation.get("is_valid"):
                                    chart_config = None

                        for event in send_event("done", {
                            "success": True,
                            "answer": final_answer,  # 🔧 修复：发送实际答案而非空字符串
                            "chart_config": chart_config,  # 🔧 添加图表配置
                            "processing_steps": processing_steps,
                            "tenant_id": tenant_id,
                            "processing_time_ms": round(total_processing_time_ms, 2),
                            "step_timings": {k: round(v, 2) for k, v in step_timings.items()},
                            "connection_id": request.connection_id,
                            "query_chain": query_chain,
                            "chart_validation": chart_validation,
                            "lineage": lineage,
                            "insights": insights
                        }):
                            yield event

                        for event in send_event("progress", {"value": 100}):
                            yield event
                    # 🔧 注意：不再需要手动关�?db_session，因为使用依赖注入的 db 会话
                    # FastAPI 会自动管理会话生命周�?

                except ImportError:
                    # AgentV2 不可�?
                    total_processing_time_ms = (time.time() - overall_start) * 1000

                    log_performance(
                        step="stream_query_import_error",
                        tenant_id=tenant_id,
                        user_id=user_id,
                        duration_ms=total_processing_time_ms,
                        metadata={"error": "AgentV2 not available"}
                    )

                    for event in send_event("error", {
                        "error": "AgentV2 not available",
                        "detail": "流式查询功能需�?AgentV2 模块"
                    }):
                        yield event

        except Exception as e:
            total_processing_time_ms = (time.time() - overall_start) * 1000

            log_performance(
                step="stream_query_error",
                tenant_id=tenant_id,
                user_id=user_id,
                duration_ms=total_processing_time_ms,
                metadata={"error": str(e), "error_type": type(e).__name__}
            )

            logger.error(f"Stream query error: {e}")
            for event in send_event("error", {
                "error": str(e),
                "error_type": "internal_error"
            }):
                yield event

        finally:
            # 清理会话状�?
            if 'session_state' in locals():
                if session_state.status == "running":
                    session_state.status = "completed"
                session_state.updated_at = time.time()
                # 保留会话状态一段时间以便客户端查询状�?
                # 可以在之后的任务中添加定时清理机�?

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


@router.get("/stream/health")
async def stream_health_check():
    """流式端点健康检�?""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "streaming": "enabled",
        "protocol": "Server-Sent Events (SSE)"
    }


# ============================================================================
# 会话管理端点
# ============================================================================

@router.get("/stream/session/{session_id}")
async def get_session_status(session_id: str):
    """
    获取流式会话状�?

    Args:
        session_id: 会话ID

    Returns:
        会话状态信�?
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过�?
        )

    return session_state.to_dict()


@router.post("/stream/session/{session_id}/pause")
async def pause_stream_session(session_id: str):
    """
    暂停流式查询

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过�?
        )

    if session_state.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只能暂停正在运行的会话，当前状�? {session_state.status}"
        )

    # 更新状态为暂停
    session_state.status = "paused"
    session_state.updated_at = time.time()
    set_session_state(session_state)

    # 设置中止事件以停止流式输�?
    if session_state.abort_controller:
        session_state.abort_controller.set()

    logger.info(f"会话 {session_id} 已暂�?)

    return {
        "success": True,
        "session_id": session_id,
        "status": "paused",
        "accumulated_answer": session_state.accumulated_answer,
        "current_progress": session_state.current_progress
    }


@router.post("/stream/session/{session_id}/resume")
async def resume_stream_session(
    session_id: str,
    tenant_id: str = "default_tenant",
    user_id: str = "default_user"
):
    """
    恢复暂停的流式查�?

    注意: 由于流式查询的特性，完整恢复需要重新发起查询�?
    此端点返回已累积的内容，客户端可决定是否重新查询�?

    Args:
        session_id: 会话ID
        tenant_id: 租户ID
        user_id: 用户ID

    Returns:
        已累积的内容和建议操�?
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过�?
        )

    if session_state.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只能恢复已暂停的会话，当前状�? {session_state.status}"
        )

    # 更新状�?
    session_state.status = "running"
    session_state.updated_at = time.time()
    set_session_state(session_state)

    logger.info(f"会话 {session_id} 已恢�?)

    return {
        "success": True,
        "session_id": session_id,
        "status": "running",
        "message": "由于流式查询的特性，完整恢复需要重新发起查�?,
        "accumulated_answer": session_state.accumulated_answer,
        "current_progress": session_state.current_progress,
        "recommendation": "使用相同参数重新发起 /stream 查询以获得完整结�?
    }


@router.delete("/stream/session/{session_id}")
async def cancel_stream_session(session_id: str):
    """
    取消流式查询

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过�?
        )

    # 更新状态为已取�?
    session_state.status = "cancelled"
    session_state.updated_at = time.time()

    # 设置中止事件
    if session_state.abort_controller:
        session_state.abort_controller.set()

    # 从活动会话中移除
    remove_session_state(session_id)

    logger.info(f"会话 {session_id} 已取�?)

    return {
        "success": True,
        "session_id": session_id,
        "status": "cancelled",
        "accumulated_answer": session_state.accumulated_answer
    }





