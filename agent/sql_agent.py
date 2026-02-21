"""
# [SQL AGENT] LangGraph SQL智能代理主程序

## [HEADER]
**文件名**: sql_agent.py
**职责**: 实现基于LangGraph和MCP的SQL智能查询代理 - 自然语言理解、Schema发现、SQL生成、图表可视化、多轮对话
**作者**: Data Agent Team
**版本**: 1.3.0
**变更记录**:
- v1.3.0 (2026-01-27): 企业级可信智能数据体优化 - 集成 planning、reflection、clarification 节点
- v1.2.0 (2026-01-06): 稳定性增强 - 动态时间上下文注入、JSON解析容错处理
- v1.1.0 (2026-01-06): 安全增强 - 集成 SQLValidator 模块，增强 should_continue 错误重试逻辑
- v1.0.1 (2026-01-02): 修复MCP echarts服务器URL配置（本地开发使用localhost）
- v1.0.0 (2026-01-01): 初始版本 - LangGraph SQL Agent实现

## [INPUT]
### 主函数参数
- **run_agent(question, thread_id, verbose)**:
  - question: str - 用户问题（自然语言查询）
  - thread_id: str - 会话ID（默认"1"）
  - verbose: bool - 是否打印详细过程（默认True）

### 配置依赖
- **config** - 从config.py导入（DeepSeek API配置、数据库URL）
- **ENABLE_ECHARTS_MCP** - 是否启用mcp-echarts服务（默认True）

## [OUTPUT]
### 主函数返回值
- **run_agent()**: VisualizationResponse - 结构化的可视化响应
  - answer: str - AI回复内容
  - sql: str - 生成的SQL语句
  - data: QueryResult - 查询结果数据
  - chart: ChartConfig - 图表配置
  - success: bool - 是否成功

### 辅助函数返回值
- **create_llm()**: ChatOpenAI - DeepSeek LLM实例
- **parse_chart_config()**: Optional[Dict[str, Any]] - 解析出的JSON配置
- **extract_tool_data()**: tuple[Optional[str], list] - (SQL语句, 原始数据列表)
- **extract_chart_tool_call()**: Optional[Dict[str, Any]] - 图表工具调用信息
- **call_mcp_chart_tool()**: Optional[str] - 保存的图片路径
- **build_visualization_response()**: VisualizationResponse - 可视化响应对象
- **_generate_chart_file()**: Optional[str] - 生成的图表文件路径
- **_get_or_create_agent()**: tuple[agent, mcp_client] - 编译好的agent和MCP客户端
- **interactive_mode()**: None - 交互模式循环

## [LINK]
**上游依赖** (已读取源码):
- [./config.py](./config.py) - 配置管理（config对象）
- [./models.py](./models.py) - 数据模型（VisualizationResponse, QueryResult, ChartConfig, ChartType）
- [./sql_validator.py](./sql_validator.py) - SQL安全校验（SQLValidator, SQLValidationError）
- [./terminal_viz.py](./terminal_viz.py) - 终端可视化（render_response）
- [./data_transformer.py](./data_transformer.py) - 数据转换（sql_result_to_echarts_data, sql_result_to_mcp_echarts_data）
- [./chart_service.py](./chart_service.py) - 图表服务（ChartRequest, generate_chart_simple, ChartResponse）
- [backend/src/app/services/agent/tools.py](../../backend/src/app/services/agent/tools.py) - 文件数据源工具（inspect_file, analyze_dataframe）

**外部依赖**:
- [langgraph](https://github.com/langchain-ai/langgraph) - LangGraph智能体框架（StateGraph, MessagesState, START, END）
- [langchain-openai](https://github.com/langchain-ai/langchain-openai) - LangChain OpenAI集成（ChatOpenAI）
- [langchain-core](https://github.com/langchain-ai/langchain-core) - LangChain核心（HumanMessage, SystemMessage, AIMessage, ToolMessage）
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) - MCP适配器（MultiServerMCPClient）
- [mcp](https://modelcontextprotocol.io/) - Model Context Protocol（ClientSession, sse_client）

**下游依赖** (已读取源码):
- [./run.py](./run.py) - 启动脚本（调用interactive_mode）
- [backend/src/app/api/v1/endpoints/query.py](../../backend/src/app/api/v1/endpoints/query.py) - 查询API端点（调用run_agent）

**调用方**:
- **run.py**: 启动脚本入口（if __name__ == "__main__"）
- **查询API**: 通过API端点调用run_agent函数

## [POS]
**路径**: Agent/sql_agent.py
**模块层级**: Level 1（Agent根目录）
**依赖深度**: 直接依赖 5 层（config.py, models.py, terminal_viz.py, data_transformer.py, chart_service.py）
"""
import asyncio
import json
import logging
import re
import sys
import os
import copy
import builtins
from pathlib import Path
from datetime import datetime, date
from typing import Literal, Optional, Dict, Any, List, Tuple

# 配置日志记录器
logger = logging.getLogger(__name__)


_stdout_flag = os.getenv("AGENT_STDOUT_VERBOSE")
if _stdout_flag is None:
    # CLI 直跑保留 stdout，服务模式默认降为 debug 日志
    _stdout_flag = "1" if __name__ == "__main__" else "0"
_print_to_stdout = _stdout_flag.lower() in {"1", "true", "yes", "on"}


def _agent_print(*args, **kwargs):
    if _print_to_stdout:
        builtins.print(*args, **kwargs)
        return

    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "")
    try:
        message = sep.join(str(arg) for arg in args) + ("" if end == "\n" else str(end))
    except Exception:
        message = " ".join(str(arg) for arg in args)
    logger.debug(message)


# 统一模块内遗留 print 输出，避免污染容器标准输出
print = _agent_print

try:
    from .core.backend_runtime import import_first_available
except ImportError:  # pragma: no cover - script mode fallback
    from core.backend_runtime import import_first_available

DATA_VALIDATOR_MODULE_CANDIDATES = (
    "app.domains.query.agent.data_validator",
    "app.services.agent.data_validator",
    "src.app.domains.query.agent.data_validator",
    "src.app.services.agent.data_validator",
)

FILE_TOOLS_MODULE_CANDIDATES = (
    "app.services.agent.tools",
    "app.domains.query.agent.tools",
    "src.app.services.agent.tools",
    "src.app.domains.query.agent.tools",
)


def _load_backend_exports(module_candidates, required_attrs):
    module = import_first_available(
        module_candidates,
        required_attrs=required_attrs,
    )
    return module, {attr: getattr(module, attr) for attr in required_attrs}


def _looks_like_year_trend(question: str) -> bool:
    if not question:
        return False
    has_year = bool(re.search(r"\b20\d{2}\b", question)) or any(
        kw in question for kw in ["年", "年度", "今年", "去年", "往年"]
    )
    has_trend = any(kw in question for kw in ["趋势", "走势", "变化", "按月", "月度", "同比", "环比", "销售趋势"])
    return has_year and has_trend


def _has_month_aggregation(sql: str) -> bool:
    patterns = [
        r"DATE_TRUNC\s*\(\s*'month'",
        r"DATE_TRUNC\s*\(\s*\"month\"",
        r"strftime\s*\(.*%Y-%m",
        r"TO_CHAR\s*\(.*YYYY-MM",
        r"DATE_FORMAT\s*\(.*%Y-%m",
    ]
    return any(re.search(pat, sql, re.IGNORECASE) for pat in patterns)


def _rewrite_sql_monthly(sql: str) -> str:
    """粗暴但有效：把日级 order_date 聚合改成按月。"""
    month_expr = "strftime('%Y-%m', order_date)"
    sql_new = re.sub(r"DATE_TRUNC\s*\(\s*'day'\s*,\s*order_date\s*\)", month_expr, sql, flags=re.IGNORECASE)
    sql_new = re.sub(r"\border_date\b", f"{month_expr} AS month", sql_new, count=1, flags=re.IGNORECASE)
    sql_new = re.sub(r"GROUP BY\s+order_date", f"GROUP BY {month_expr}", sql_new, flags=re.IGNORECASE)
    sql_new = re.sub(r"ORDER BY\s+order_date", f"ORDER BY {month_expr}", sql_new, flags=re.IGNORECASE)
    return sql_new


def _extract_year(question: str) -> Optional[int]:
    """从用户问题中提取年份（命中第一个 20xx）。"""
    if not question:
        return None
    m = re.search(r"\b(20\d{2})\b", question)
    return int(m.group(1)) if m else None


def _enforce_year_filter_and_month(sql: str, year: int) -> str:
    """
    将年过滤改为范围查询，并强制按月聚合（针对 orders 表销售趋势场景）。
    - 使用 >= year-01-01 AND < next_year-01-01 避免索引失效
    - 统一月粒度，生成订单数/销售额/客单价
    """
    if not year:
        return sql

    sql_lower = sql.lower()
    if " from orders" not in sql_lower:
        return sql

    date_col = "order_date" if "order_date" in sql_lower else "order_date"
    year_start = f"'{year:04d}-01-01'"
    year_end = f"'{year + 1:04d}-01-01'"

    # 1) 将 SUBSTRING/LIKE 年份过滤改为范围过滤
    sql = re.sub(
        rf"substring\s*\(\s*{date_col}\s*,\s*1\s*,\s*4\s*\)\s*=\s*'?\d{{4}}'?",
        f"{date_col} >= {year_start} AND {date_col} < {year_end}",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        rf"{date_col}\s+like\s+'{year}\%'",
        f"{date_col} >= {year_start} AND {date_col} < {year_end}",
        sql,
        flags=re.IGNORECASE,
    )

    # 2) 如缺失年份条件，插入范围过滤
    sql_lower = sql.lower()
    if f"{year_start.lower()}" not in sql_lower and f"{year_end.lower()}" not in sql_lower:
        if " where " in sql_lower:
            sql = re.sub(
                r"\bwhere\b",
                f"WHERE {date_col} >= {year_start} AND {date_col} < {year_end} AND",
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
            sql = sql.replace("AND  AND", "AND ")
        elif " group by " in sql_lower:
            sql = re.sub(
                r"\bgroup\s+by\b",
                f"WHERE {date_col} >= {year_start} AND {date_col} < {year_end} GROUP BY",
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
        elif " order by " in sql_lower:
            sql = re.sub(
                r"\border\s+by\b",
                f"WHERE {date_col} >= {year_start} AND {date_col} < {year_end} ORDER BY",
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            sql = f"{sql} WHERE {date_col} >= {year_start} AND {date_col} < {year_end}"

    # 3) 强制按月聚合 + 生成三项指标
    month_expr = f"strftime('%Y-%m', {date_col})"
    select_pattern = re.compile(r"select\s+.*?\bfrom\b", re.IGNORECASE | re.DOTALL)
    replacement_select = (
        f"SELECT {month_expr} AS month, "
        "COUNT(*) AS order_count, "
        "SUM(total_amount) AS total_sales, "
        "AVG(total_amount) AS avg_order_amount FROM"
    )
    sql = select_pattern.sub(replacement_select, sql)
    # 统一 GROUP BY / ORDER BY
    sql = re.sub(r"GROUP BY\s+[^;]+", f"GROUP BY {month_expr}", sql, flags=re.IGNORECASE)
    sql = re.sub(r"ORDER BY\s+[^;]+", "ORDER BY month", sql, flags=re.IGNORECASE)
    if "group by" not in sql.lower():
        sql += f" GROUP BY {month_expr}"
    if "order by" not in sql.lower():
        sql += " ORDER BY month"
    return sql


def _normalize_tool_call_v2(tc: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
    """
    兼容 OpenAI function-call / 平铺格式的 tool_call，提取工具名和参数。
    返回 (tool_name, args_dict, format_tag)
    """
    tool_name = ""
    args_dict: Dict[str, Any] = {}
    format_tag = "flat"

    if isinstance(tc, dict):
        func_block = tc.get("function")
        if func_block:
            format_tag = "function"
            tool_name = func_block.get("name") or tc.get("name") or ""
            raw_args = func_block.get("arguments")
        else:
            tool_name = tc.get("name", "") or tc.get("tool", "") or ""
            raw_args = tc.get("args") or tc.get("input_data") or {}
    else:
        func_block = getattr(tc, "function", None)
        if func_block:
            format_tag = "function"
            tool_name = getattr(func_block, "name", "") or getattr(tc, "name", "") or ""
            raw_args = getattr(func_block, "arguments", None)
        else:
            tool_name = getattr(tc, "name", "") or getattr(tc, "tool", "") or ""
            raw_args = getattr(tc, "args", None)

    if isinstance(raw_args, str):
        try:
            args_dict = json.loads(raw_args) or {}
        except Exception:
            args_dict = {}
    elif isinstance(raw_args, dict):
        args_dict = raw_args
    else:
        args_dict = {}

    # 兼容 input_data 结构
    if not args_dict and isinstance(tc, dict):
        input_data = tc.get("input_data")
        if isinstance(input_data, dict):
            args_dict = input_data
            format_tag = "input"

    return tool_name, args_dict, format_tag


def _write_back_tool_call_v2(tc: Dict[str, Any], args: Dict[str, Any], format_tag: str) -> None:
    """按原始格式写回参数，兼容 function/flat。"""
    if format_tag == "function":
        if isinstance(tc, dict):
            func_block = tc.get("function") or {}
            func_block["arguments"] = json.dumps(args, ensure_ascii=False)
            tc["function"] = func_block
            tc["args"] = args
        else:
            func_block = getattr(tc, "function", None)
            if func_block is not None:
                try:
                    func_block.arguments = json.dumps(args, ensure_ascii=False)
                except Exception:
                    pass
            try:
                tc.args = args
            except Exception:
                pass
    elif format_tag == "input":
        if isinstance(tc, dict):
            tc["input_data"] = args
        else:
            try:
                tc.input_data = args
            except Exception:
                pass
    else:
        if isinstance(tc, dict):
            tc["args"] = args
        else:
            try:
                tc.args = args
            except Exception:
                pass


def apply_time_aggregation_fix_to_tool_calls_v2(
    tool_calls: List[Dict[str, Any]],
    question: str
) -> List[Dict[str, Any]]:
    """在 AgentV2 中对工具调用强制月度聚合。"""
    if not tool_calls or not _looks_like_year_trend(question):
        return tool_calls

    target_year = _extract_year(question)

    fixed = []
    for tc in tool_calls:
        tc_copy = copy.deepcopy(tc)
        name, args, fmt = _normalize_tool_call_v2(tc_copy)
        sql = args.get("sql") or args.get("query")
        if name in ("query", "execute_query", "execute_sql_safe") and sql:
            corrected = sql
            # 针对销售趋势类（orders 表）强制范围过滤+月聚合+三指标
            if target_year:
                corrected = _enforce_year_filter_and_month(corrected, target_year)

            if not _has_month_aggregation(corrected):
                corrected = _rewrite_sql_monthly(corrected)

            args["sql"] = corrected
            args["query"] = corrected
            _write_back_tool_call_v2(tc_copy, args, fmt)
        fixed.append(tc_copy)
    return fixed


def _build_dual_axis_chart_config(raw_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    基于查询结果自动生成双轴配置（销售额 + 订单量）。
    返回 chart_config_data 兼容结构。
    """
    if not raw_data:
        return None

    columns = list(raw_data[0].keys())
    if len(columns) < 3:
        return None

    # 识别时间列与数值列
    time_col = None
    numeric_cols: List[str] = []
    for col in columns:
        col_lower = col.lower()
        sample_val = raw_data[0].get(col)
        if any(key in col_lower for key in ["month", "date", "day"]):
            time_col = col
        if isinstance(sample_val, (int, float)):
            numeric_cols.append(col)

    if not time_col or len(numeric_cols) < 2:
        return None

    def _pick_metric(candidates: List[str], keywords: List[str]) -> Optional[str]:
        for kw in keywords:
            for col in candidates:
                if kw in col.lower():
                    return col
        return None

    main_metric = _pick_metric(numeric_cols, ["sale", "amount", "total", "revenue"]) or numeric_cols[0]
    secondary_metric = _pick_metric([c for c in numeric_cols if c != main_metric], ["count", "qty", "quantity", "order"]) \
        or (numeric_cols[1] if len(numeric_cols) > 1 else None)

    if not secondary_metric:
        return None

    return {
        "chart_type": "line",
        "chart_title": "销售额 vs 订单量（双轴）",
        "x_field": time_col,
        "y_field": main_metric,
        "series": [
            {"column": main_metric, "chart_type": "line", "y_axis_index": 0, "unit": ""},
            {"column": secondary_metric, "chart_type": "bar", "y_axis_index": 1, "unit": ""},
        ],
        "is_dual_axis": True,
        "left_axis_name": main_metric,
        "right_axis_name": secondary_metric,
    }


def _extract_date_bounds(rows: List[List[Any]], columns: List[str]) -> Optional[Tuple[date, date]]:
    """提取结果中的最小/最大日期，用于覆盖范围提示。"""
    candidates = []

    def _parse(val):
        if isinstance(val, (datetime, date)):
            return val.date() if isinstance(val, datetime) else val
        if isinstance(val, str):
            txt = val.strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m"):
                try:
                    dt = datetime.strptime(txt, fmt)
                    return dt.date()
                except ValueError:
                    continue
        return None

    for row in rows:
        for idx, col in enumerate(columns):
            if any(k in col.lower() for k in ["date", "month", "day"]):
                if idx < len(row):
                    d = _parse(row[idx])
                    if d:
                        candidates.append(d)

    if not candidates:
        return None
    return min(candidates), max(candidates)

# Fix Windows GBK encoding issue
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

try:
    # 作为包导入时（from AgentV2.sql_agent import ...）
    from .config import config
    from .models import VisualizationResponse, QueryResult, ChartConfig, ChartType
    from .terminal_viz import render_response
    from .data_transformer import sql_result_to_echarts_data
    from .chart_service import ChartRequest, generate_chart_simple, ChartResponse
except ImportError:
    # 直接运行时（python sql_agent.py）
    from config import config
    from models import VisualizationResponse, QueryResult, ChartConfig, ChartType
    from terminal_viz import render_response
    from data_transformer import sql_result_to_echarts_data
    from chart_service import ChartRequest, generate_chart_simple, ChartResponse

# 🔥 加载精简版 prompt（包含趋势查询强制规则）
def load_simplified_prompt() -> str:
    """加载 prompt_simplified.txt 的内容"""
    prompt_file = Path(__file__).parent / "prompt_simplified.txt"
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
            # 提取 BASE_SYSTEM_PROMPT_SIMPLIFIED 的值
            if 'BASE_SYSTEM_PROMPT_SIMPLIFIED = """' in content:
                start = content.index('BASE_SYSTEM_PROMPT_SIMPLIFIED = """') + len('BASE_SYSTEM_PROMPT_SIMPLIFIED = """')
                end = content.rindex('"""')
                return content[start:end].strip()
            return content
    except Exception as e:
        logger.warning(f"无法加载 prompt_simplified.txt: {e}，使用默认 prompt")
        return ""

# 加载精简版 prompt
SIMPLIFIED_PROMPT = load_simplified_prompt()

# 常量定义
MIN_ANALYSIS_LENGTH = 50  # 最短分析长度阈值

# 🔧 新增：企业级可信智能数据体节点
try:
    from .nodes import (
        create_planning_node,
        create_reflection_node,
        create_clarification_node,
    )
except ImportError:
    from nodes import (
        create_planning_node,
        create_reflection_node,
        create_clarification_node,
    )

# 🔥 导入语义层工具
try:
    from .tools import (
        resolve_business_term,
        get_semantic_measure,
        list_available_cubes,
        get_cube_measures,
        normalize_status_value,
    )
except ImportError:
    from tools import (
        resolve_business_term,
        get_semantic_measure,
        list_available_cubes,
        get_cube_measures,
        normalize_status_value,
    )

# 数据一致性验证：防止 LLM 幻觉导致的数据不匹配
smart_field_mapping = None
recommend_chart = None
try:
    _validator_module, _validator_exports = _load_backend_exports(
        DATA_VALIDATOR_MODULE_CANDIDATES,
        ("smart_field_mapping", "recommend_chart"),
    )
    smart_field_mapping = _validator_exports["smart_field_mapping"]
    recommend_chart = _validator_exports["recommend_chart"]
    DATA_VALIDATION_ENABLED = True
except Exception:
    DATA_VALIDATION_ENABLED = False
    logger.warning("数据验证模块未启用（data_validator.py 不可用）")

# 🔧 新增：导入 database_tools 模块用于设置用户查询上下文
try:
    from .tools import clear_user_query_context, set_user_query_context
    DATABASE_TOOLS_AVAILABLE = True
except ImportError:
    try:
        from tools import clear_user_query_context, set_user_query_context
        DATABASE_TOOLS_AVAILABLE = True
    except ImportError:
        DATABASE_TOOLS_AVAILABLE = False
        logger.warning("database_tools 模块未可用")

# 表推荐工具
try:
    from .tools.table_recommendation_tools import (
        get_recommended_tables_for_query,
        get_table_description_by_name,
    )
    TABLE_RECOMMENDATION_TOOLS_AVAILABLE = True
except ImportError:
    try:
        from tools.table_recommendation_tools import (
            get_recommended_tables_for_query,
            get_table_description_by_name,
        )
        TABLE_RECOMMENDATION_TOOLS_AVAILABLE = True
    except ImportError:
        TABLE_RECOMMENDATION_TOOLS_AVAILABLE = False
        logger.warning("table_recommendation_tools 模块未可用")

# 🔍 错误追踪模块（质量保证）
_error_category_cls = None
_error_tracker_decorator = None
_log_agent_error_fn = None
try:
    from .error_tracker import (
        error_tracker as _error_tracker_decorator,
        log_agent_error as _log_agent_error_fn,
        ErrorCategory as _error_category_cls,
    )
    ERROR_TRACKING_ENABLED = True
except ImportError:
    try:
        from error_tracker import (
            error_tracker as _error_tracker_decorator,
            log_agent_error as _log_agent_error_fn,
            ErrorCategory as _error_category_cls,
        )
        ERROR_TRACKING_ENABLED = True
    except ImportError:
        ERROR_TRACKING_ENABLED = False
        logger.warning("错误追踪模块未启用（error_tracker.py 不可用）")

if _error_category_cls is not None:
    ErrorCategory = _error_category_cls
    error_tracker = _error_tracker_decorator
    log_agent_error = _log_agent_error_fn
else:
    # 提供回退的 ErrorCategory 定义
    from enum import Enum

    class ErrorCategory(str, Enum):
        DANGEROUS_OPERATION = "dangerous_operation"
        SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
        DATABASE_CONNECTION = "database_connection"
        LLM_API_ERROR = "llm_api_error"
        SCHEMA_NOT_FOUND = "schema_not_found"
        EMPTY_RESULT = "empty_result"
        SQL_SYNTAX_ERROR = "sql_syntax_error"
        DATA_TYPE_MISMATCH = "data_type_mismatch"
        MCP_TOOL_FAILURE = "mcp_tool_failure"
        AMBIGUOUS_QUERY = "ambiguous_query"
        UNKNOWN = "unknown"

    # 提供 no-op 的回退函数
    def error_tracker(func):
        return func

    def log_agent_error(error, question, sql="", category=None):
        pass

# 🔥 强制导入文件数据源工具（多种路径尝试）
_inspect_file_tool = None
_analyze_dataframe_tool = None

try:
    module, file_tool_exports = _load_backend_exports(
        FILE_TOOLS_MODULE_CANDIDATES,
        ("inspect_file", "analyze_dataframe"),
    )
    _inspect_file_tool = file_tool_exports["inspect_file"]
    _analyze_dataframe_tool = file_tool_exports["analyze_dataframe"]
    logger.info("文件数据源工具导入成功: %s", module.__name__)

except Exception as exc:
    logger.warning("文件数据源工具导入失败，将继续运行: %s", exc)

import base64

# 🔒 导入独立的 SQL 安全校验模块
try:
    from .sql_validator import SQLValidator
except ImportError:
    from sql_validator import SQLValidator


# ===============================================
# 🔧 SQL 质量优化器（自动修复常见SQL问题）
# ===============================================

class SQLQualityOptimizer:
    """
    SQL质量优化器 - 自动检测并修复常见的SQL质量问题

    检测和修复的问题：
    1. 重复的 WHERE 条件（如 tenant_id 重复）
    2. 多次 COUNT 查询转换为一次 GROUP BY
    3. 优先使用 address LIKE 而非 region_id
    """

    @staticmethod
    def detect_and_fix_duplicate_conditions(sql: str) -> tuple[str, list[str]]:
        """
        检测并修复重复的WHERE条件

        Returns:
            (修复后的SQL, 发现的问题列表)
        """
        issues = []

        # 检测重复的 tenant_id
        import re
        pattern = r"tenant_id\s*=\s*'([^']+)'"
        matches = re.findall(pattern, sql, re.IGNORECASE)

        # 检查是否有重复（相同值出现多次）
        if len(matches) > len(set(matches)):
            unique_matches = list(dict.fromkeys(matches))  # 保持顺序的去重
            issues.append(f"检测到重复的 WHERE 条件: tenant_id 重复 {len(matches)} 次")

            # 构建修复后的SQL：保留第一个出现，删除重复的
            fixed_sql = sql
            for i, match in enumerate(unique_matches):
                if i == 0:
                    continue  # 保留第一个

            # 使用正则表达式替换重复的tenant_id条件
            # 找到所有 tenant_id = 'xxx' 并替换，只保留第一个
            def replace_duplicates(match_obj):
                value = match_obj.group(1)
                # 如果这个值已经被替换过，就删除这个匹配
                if hasattr(replace_duplicates, 'seen_values'):
                    if value in replace_duplicates.seen_values:
                        return ''  # 删除重复的
                    replace_duplicates.seen_values.add(value)
                    return match_obj.group(0)
                else:
                    replace_duplicates.seen_values = {value}
                    return match_obj.group(0)

            # 从右向左替换（避免索引变化）
            # 更简单的方法：直接重建 WHERE 子句
            where_match = re.search(r'WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
            if where_match:
                where_clause = where_match.group(1)

                # 提取所有条件
                conditions = [cond.strip() for cond in re.split(r'\s+AND\s+', where_clause)]

                # 去重（保持顺序）
                seen = set()
                unique_conditions = []
                for cond in conditions:
                    # 检查是否是 tenant_id 条件
                    tenant_match = re.match(r"tenant_id\s*=\s*'([^']+)'", cond, re.IGNORECASE)
                    if tenant_match:
                        value = tenant_match.group(1)
                        if value not in seen:
                            seen.add(value)
                            unique_conditions.append(cond)
                        else:
                            issues.append(f"  - 删除重复条件: {cond}")
                    else:
                        unique_conditions.append(cond)

                # 重建 WHERE 子句
                new_where = ' AND '.join(unique_conditions)
                fixed_sql = re.sub(
                    r'WHERE\s+.+?(GROUP BY|ORDER BY|LIMIT|$)',
                    f'WHERE {new_where} \\1',
                    sql,
                    flags=re.IGNORECASE | re.DOTALL,
                    count=1
                )
            else:
                fixed_sql = sql
        else:
            fixed_sql = sql

        return fixed_sql, issues

    @staticmethod
    def is_proportion_query(question: str) -> bool:
        """检测是否是占比类问题"""
        proportion_keywords = ['占比', '比例', '百分比', '分布', '多少%']
        return any(kw in question for kw in proportion_keywords)

    @staticmethod
    def detect_city_in_question(question: str) -> Optional[str]:
        """从问题中提取城市名"""
        common_cities = [
            '北京', '上海', '广州', '深圳', '杭州', '成都', '重庆',
            '武汉', '西安', '苏州', '南京', '天津', '青岛', '大连',
            '厦门', '长沙', '郑州', '东莞', '佛山', '宁波'
        ]
        for city in common_cities:
            if city in question:
                return city
        return None


# Base system prompt for the SQL Agent (will be dynamically enhanced based on db_type)
# 🔥 优先使用 prompt_simplified.txt 的内容，如果加载失败则使用默认 prompt
if SIMPLIFIED_PROMPT:
    BASE_SYSTEM_PROMPT = SIMPLIFIED_PROMPT
else:
    BASE_SYSTEM_PROMPT = """你是一个专业的数据库助手，具备数据查询和图表可视化能力。

## 🔴🔴🔴【生死攸关】生成SQL前必须先调用list_tables()！🔴🔴🔴

**每次生成SQL前，必须按以下顺序执行**：
1. 首先调用 `list_tables()` 获取数据库中的实际表名
2. 根据返回的实际表名选择合适的表
3. 调用 `get_schema()` 了解表结构
4. 最后生成SQL并执行

**❌ 绝对禁止**：
- 禁止使用prompt示例中的表名（示例仅供参考）
- 禁止猜测或假设表名
- 禁止跳过list_tables()直接生成SQL

---

## 🔴🔴🔴【生死攸关】时间范围查询必须过滤！🔴🔴🔴

**用户问"2023年的销售"，你必须添加 WHERE EXTRACT(YEAR FROM order_date) = 2023！**
**用户问"5月份的订单"，你必须添加 WHERE EXTRACT(MONTH FROM order_date) = 5！**
**违反此规则 = 严重错误！**

---

## 🚨🚨🚨【最高优先级规则】每次生成SQL前必须检查！🚨🚨🚨

### ✅ SQL质量强制检查清单（违反任一条即严重错误！）

```
□ 检查1: tenant_id 是否重复？（数一下，必须≤1次！）
□ 检查2: 是否使用 GROUP BY 一次查询？（禁止多次COUNT！）
□ 检查3: 城市查询是否优先使用 address LIKE？（不是region_id！）
□ 检查4: 表名是否正确？（不是data_source_connections等系统表！）
□ 检查5: 【最高优先级】用户提到年份/日期时是否添加了WHERE时间过滤？
```

### ❌ 绝对禁止的SQL错误模式

**1. 重复WHERE条件**（最常见！）：
```sql
-- ❌ 错误：重复的相同条件
WHERE region_id = '5' AND region_id = '5'

-- ✅ 正确：每个条件只一次
WHERE region_id = '5'
```

**2. WHERE子句位置错误**（极常见！）：
```sql
-- ❌ 错误：WHERE 在 GROUP BY/ORDER BY 之后
SELECT ... GROUP BY year ORDER BY year WHERE status = 'active'
SELECT ... ORDER BY year AND status = 'active'

-- ✅ 正确：WHERE 必须在 GROUP BY/ORDER BY 之前
SELECT ... WHERE status = 'active' GROUP BY year ORDER BY year
```

**3. 禁止在 SQL 中手动添加 tenant_id**：
```sql
-- ❌ 错误：不要手动添加 tenant_id，系统会自动处理
WHERE tenant_id = 'xxx' AND ...

-- ✅ 正确：系统会自动注入租户过滤条件
WHERE status = 'active'
```

**4. 禁止多次COUNT查询**（占比类问题！）：
```sql
-- ❌ 错误：多次查询
SELECT COUNT(*) FROM users WHERE city = '杭州';
SELECT COUNT(*) FROM users;

-- ✅ 正确：一次GROUP BY查询
SELECT
    CASE WHEN city LIKE '%杭州%' THEN '杭州' ELSE '其他' END as category,
    COUNT(*) as value
FROM users
GROUP BY category;
```

**3. 地址字段优先级**（城市查询！）：
```
优先级: address LIKE '%杭州%' > 独立city字段 > region_id关联
```

**4. 禁止查询系统元数据表**：
```sql
-- ❌ 错误
SELECT * FROM data_source_connections WHERE name = '杭州用户'

-- ✅ 正确：查询业务数据表
SELECT * FROM users WHERE city LIKE '%杭州%'
```

---

## 📅 【最高优先级】时间范围查询规则

**⚠️ 当用户问题中包含时间关键词时，必须在WHERE子句中添加时间过滤条件！**

**时间关键词识别**：
- 年份: "2023年"、"2024年"、"去年"、"今年"、"前年"
- 月份: "1月"、"5月"、"本月"、"上个月"、"下个月"
- 日期: "2023-05-01"、"昨天"、"今天"、"明天"
- 季度: "第一季度"、"Q1"、"上半年"、"下半年"

**🚨 严重错误示例（必须避免！）**：
```sql
-- ❌ 错误：用户问"2023年的销售"，但没有年份过滤
SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as total
FROM orders
GROUP BY month;
-- 结果：返回了2023年、2024年所有数据！

-- ❌ 错误：用户问"5月份的订单"，但没有月份过滤
SELECT COUNT(*) as total FROM orders;
-- 结果：返回了所有月份的订单总数！
```

**✅ 正确做法**：
```sql
-- 用户问"2023年的销售"
SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as total
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2023
GROUP BY month;

-- 用户问"2024年5月的订单"
SELECT COUNT(*) as total
FROM orders
WHERE order_date >= '2024-05-01' AND order_date < '2024-06-01';

-- 用户问"今年的销售额"
SELECT SUM(amount) as total
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2026;

-- 用户问"上个月的数据"
SELECT COUNT(*) as total
FROM orders
WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND order_date < DATE_TRUNC('month', CURRENT_DATE);
```

**对照检查表**：
| 用户问题 | 必须包含的WHERE条件 |
|---------|-------------------|
| "2023年的销售趋势" | `WHERE EXTRACT(YEAR FROM order_date) = 2023` |
| "2024年5月的订单" | `WHERE order_date >= '2024-05-01' AND order_date < '2024-06-01'` |
| "今年的销售额" | `WHERE EXTRACT(YEAR FROM order_date) = {当前年份}` |
| "Q1的数据" | `WHERE order_date >= '2024-01-01' AND order_date < '2024-04-01'` |

---

## 🛡️ 安全规则（只读模式）

你是一个**只读数据分析助手**，严禁执行任何数据修改操作！

**禁止操作**：UPDATE、INSERT、DELETE、TRUNCATE、CREATE、ALTER、DROP、GRANT、REVOKE

**拒绝回复模板**：
```
⛔ **操作被拒绝**
您请求的操作涉及数据修改，这违反了安全策略。
我只能：✅查询和展示数据、✅分析数据趋势、✅生成图表
❌不能修改、删除或新增数据
```

---

## 🛠️ 可用工具

### 🔧 数据库表查询工具
- ✅ **list_tables** - 必须先调用此工具查看可用表名
- ✅ **get_schema** - 获取表结构信息
- ✅ **query** - 执行SQL查询

### 📋 表查询工作流程（必须遵守）
1. **首先**调用 `list_tables()` 查看所有可用表
2. 使用 `list_tables()` 返回的**确切表名**（可能是中文或英文）
3. 如需了解字段信息，调用 `get_schema(表名)`
4. 最后调用 `query()` 执行查询

### 图表工具
- generate_bar_chart - 柱状图：[{"category": "名称", "value": 数值}]
- generate_line_chart - 折线图：[{"time": "时间", "value": 数值}]
- generate_pie_chart - 饼图：[{"category": "名称", "value": 数值}]
- generate_scatter_chart - 散点图：[{"x": 数值, "y": 数值, "label": "名称"}]
- generate_funnel_chart - 漏斗图：[{"category": "名称", "value": 数值}]

### 双轴图/混合图表
当用户要求"双轴图"、"双Y轴"、"折线+柱状"等混合图表时：
- 请使用 **两个独立的图表工具** 分别生成柱状图和折线图
- 例如：先调用 generate_bar_chart(柱状数据)，再调用 generate_line_chart(折线数据)
- ❌ 不要使用 generate_echarts 工具（它需要复杂的JSON配置）

### 🔥 语义层工具（业务术语解析）

**重要**：在生成 SQL 之前，请先使用语义层工具解析业务术语！

1. **resolve_business_term** - 解析业务术语
   - 用途：将"销售额"、"总收入"、"订单数"等业务术语映射到正确的表和字段
   - 输入：术语名称（如"销售额"）
   - 输出：JSON格式的度量定义（包含表名、字段名、SQL表达式）

2. **list_available_cubes** - 列出可用的语义层Cube
   - 输出：所有可用的Cube列表（如Orders、Customers、Products）

3. **get_semantic_measure** - 获取指定Cube的度量详情
   - 输入：cube名称和度量名称
   - 输出：完整的度量定义

4. **get_cube_measures** - 获取指定Cube的所有度量
   - 输入：cube名称
   - 输出：该Cube的所有度量列表

5. **normalize_status_value** - 规范化状态值
   - 用途：将"已完成"映射为"completed"等标准值
   - 输入：原始状态值
   - 输出：规范化后的状态信息

**语义层使用工作流程**：
```
用户查询 → resolve_business_term(术语) → 获取SQL表达式 → 生成完整SQL
```

**关键提示**：
- 项目中没有独立的 `sales` 表，所有销售数据在 `orders` 表中
- "销售额"对应的字段是 `orders.total_amount`
- 使用语义层工具获取正确的表名和字段名

### 工作流程
1. 理解问题并分析需要的数据
2. 使用语义层工具解析业务术语（如需要）
3. 使用 query 工具执行SQL
4. 调用图表工具生成可视化（如需）

---

## 📊 占比类问题（"XX的占比"）

**处理流程**：
1. 使用一次GROUP BY查询获取所有分类数据
2. 调用generate_pie_chart生成饼图
3. 从结果中计算目标分类的占比

**示例**（"杭州客户的占比"）：
```sql
-- ✅ 正确：一次GROUP BY获取所有城市分布
-- 注意：不要手动添加 tenant_id，系统会自动注入租户过滤条件
SELECT
    CASE
        WHEN address LIKE '%杭州%' THEN '杭州'
        WHEN address LIKE '%北京%' THEN '北京'
        WHEN address LIKE '%上海%' THEN '上海'
        ELSE '其他'
    END as category,
    COUNT(*) as value
FROM customers
GROUP BY category;
```

**回答模板**：
```
📊 [客户城市分布]
总客户200人，各城市分布：
- 上海：50人（25%）
- 杭州：34人（17%）
- 北京：40人（20%）
...
💡 杭州客户占17%，排名第3位
```

---

## 🌍 城市查询规则

**优先级**：address LIKE '%城市%' > city字段 > region_id

**常见城市**：北京、上海、广州、深圳、杭州、成都、重庆、武汉、西安、苏州、南京、天津

**处理流程**：
1. 识别城市关键词
2. 查找城市字段（address、city、ship_city等）
3. 执行GROUP BY获取所有城市分布
4. 从结果中计算目标城市占比

---

## 📈 模糊查询（"最近生意怎么样"）

**默认时间范围**：
- "最近" → 30天
- "最近一周" → 7天
- "本月" → 当月1日至今

**必须按日期分组**（生成时间序列数据）：
```sql
SELECT
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as orders,
    SUM(amount) as sales
FROM orders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date;
```

**必须生成图表**：调用generate_line_chart或generate_bar_chart

---

## 🔍 图表拆分规则

当用户说"把图分开"、"拆分"、"分别显示"时：
1. 必须调用query工具获取数据
2. 根据用户要求调用对应数量的图表工具
3. 禁止只输出SQL文本而不调用工具！

---

## 📋 SQL生成自查清单

每生成一条SQL必须逐项检查：
```
□ 不要手动添加 tenant_id 条件（系统会自动处理）
□ WHERE 子句必须在 GROUP BY/ORDER BY 之前
□ 表名正确（非系统元数据表）
□ 字段名存在（基于get_schema结果）
□ 占比问题用GROUP BY（不是多次COUNT）
□ 城市查询优先用address LIKE（不是region_id）
```

**🚨 任何检查失败，立即重新生成SQL！**

---

## 🔄 智能表名回退规则（当表不存在时）

**当用户询问的表名不存在时，不要直接放弃！**

**处理流程**：
1. 调用 `list_tables()` 查看所有可用表
2. 根据业务语义找到相关表
3. 使用找到的相关表查询数据

**常见业务术语映射（仅供参考，实际表名以list_tables()为准）**：
```
用户术语          →  可能的表名（仅供参考，实际表名以list_tables()为准）
───────────────────────────────────────────────────────────
销售/销售额/收入    → 订单表、销售表、orders、sales
客户/用户         → 用户表、客户表、users、customers
产品/商品         → 产品表、商品表、products
订单             → 订单表、订单明细、orders
```

**正确示例**：
```
❌ 错误：表不存在就直接放弃
用户：查询2023年销售趋势
AI：很抱歉，sales表不存在...

✅ 正确：查找相关表并使用
用户：查询2023年销售趋势
AI：
1. 调用 list_tables() → 查看数据库中实际存在的表名
2. 从返回的表名中识别与"销售"相关的表（如：订单表、销售表等）
3. 使用实际存在的表名进行查询，并添加时间过滤 WHERE EXTRACT(YEAR FROM 订单日期) = 2023
```

---

## 📊 图表生成决策规则（🔴 强制执行）

**⚠️ 执行查询后，必须根据数据特征和用户问题类型判断是否生成图表！**

### 必须生成图表的场景

| 用户问题类型 | 数据特征 | 必须调用的图表工具 |
|-------------|----------|-------------------|
| 趋势/变化/增长 | 含时间/日期字段 | `generate_line_chart` |
| 对比/排名/Top N | 含分类字段 + 数值字段 | `generate_bar_chart` |
| 占比/分布 | 含分组 + 计数/百分比 | `generate_pie_chart` |
| 销售趋势/订单趋势 | 时间 + 数值 | `generate_line_chart` |
| XX的排名/XX排行 | 分组 + 数值排序 | `generate_bar_chart` |
| 每月/每年/每日 | 时间序列 | `generate_line_chart` |

### 判断流程
```
查询返回数据 → 分析数据特征 → 匹配上表场景 → 调用对应图表工具 → 生成文字分析
```

### 示例
```
❌ 错误：只输出文字，不生成图表
用户：查询2023年销售趋势
AI：2023年销售额为XXX...（没有任何图表）

✅ 正确：先调用图表工具，再分析
用户：查询2023年销售趋势
AI：
1. 调用 query() 获取数据
2. 调用 generate_line_chart() 生成趋势图
3. 输出文字分析：📊 2023年销售趋势分析...
```

### 图表数据格式
```json
// 折线图/柱状图
[{"time": "2023-01", "value": 1000}, {"time": "2023-02", "value": 1200}]
// 或 [{"category": "产品A", "value": 100}, {"category": "产品B", "value": 200}]

// 饼图
[{"category": "北京", "value": 30}, {"category": "上海", "value": 50}]
```

---

## 💡 数据分析输出要求（🔴 强制执行，不可跳过）

⚠️ **每次查询后，你必须生成详细的数据分析文本！这不是可选项，是必选项！**

分析内容必须包含以下四个部分：

### 1. 数据概要（必填）
- 查询返回了多少条记录
- 涉及的时间范围（如有）
- 主要的数据维度

### 2. 关键发现（必填）
- 数据中的重要趋势（上升/下降/波动）
- 异常值识别（最高/最低/异常点）
- 数据分布特征

### 3. 数值解读（必填）
- 具体数字的含义（如"销售额增长了20%"）
- 关键指标的计算结果
- 数据之间的关联关系

### 4. 业务洞察（必填）
- 数据对业务的启示
- 建议的下一步行动
- 潜在的风险或机会

**❌ 禁止行为**：
- 只输出SQL或图表，不生成文字分析
- 只说"查询完成"、"已生成图表"等无意义回复
- 跳过上述任何一个分析部分

**✅ 正确示例**：
```
📊 [数据分析结果]

根据查询结果，共找到 15 条订单记录：

🔍 **关键发现**：
• 小米品牌的总销售额为 ¥125,000，占总销售额的 32%
• 平均订单金额为 ¥8,333，最高单笔订单为 ¥15,000（2024-05-15）
• 销售额呈现上升趋势，5月份比4月份增长了 25%

💡 **业务洞察**：
小米品牌表现良好，销售额占比超过三成，是核心品牌之一。建议继续关注该品牌的库存和促销活动，同时分析增长驱动因素以复制成功经验。
```
"""

def get_system_prompt(db_type: str = "postgresql") -> str:
    """
    根据数据库类型获取系统提示词，并注入动态时间上下文

    Args:
        db_type: 数据库类型（postgresql, mysql, sqlite, xlsx, csv等）

    Returns:
        str: 系统提示词（包含当前时间信息）
    """
    logger.debug("[get_system_prompt] db_type=%s", db_type)

    # 🕒 动态时间上下文（对于"昨天"、"上月"等时间查询至关重要）
    current_time = datetime.now()
    time_context = f"""

## 🕒 当前时间上下文
- **当前时间**: {current_time.strftime("%Y-%m-%d %H:%M:%S")}
- **当前年份**: {current_time.year}
- **当前月份**: {current_time.month}月
- **当前日期**: {current_time.day}日
- **星期**: 星期{['一', '二', '三', '四', '五', '六', '日'][current_time.weekday()]}

在处理时间相关查询时（如"昨天"、"上周"、"上个月"、"今年"等），请以此时间为准进行计算。

## 🚨🚨🚨 【强制】时间范围查询规则

当用户问题中明确提到年份、月份、日期等时间关键词时：
1. **必须**在WHERE子句中添加时间过滤条件
2. 使用正确的日期函数（EXTRACT, DATE_TRUNC等）
3. 确保**只返回**用户指定时间范围内的数据

**错误示例**：
- 用户问"2023年的销售" → ❌ 查询返回2023和2024年数据
- 用户问"5月份的订单" → ❌ 查询返回所有月份数据
- 用户问"去年的趋势" → ❌ 没有添加任何时间过滤

**正确示例**：
- 用户问"2023年的销售" → ✅ WHERE EXTRACT(YEAR FROM order_date) = 2023
- 用户问"5月份的订单" → ✅ WHERE EXTRACT(MONTH FROM order_date) = 5
- 用户问"今年的销售额" → ✅ WHERE EXTRACT(YEAR FROM order_date) = {current_time.year}
- 用户问"上个月的数据" → ✅ WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND order_date < DATE_TRUNC('month', CURRENT_DATE)

**时间关键词识别**：
- 年份: "2023年"、"2024年"、"去年"、"今年"、"前年"
- 月份: "1月"、"5月"、"本月"、"上个月"
- 日期: "2023-05-01"、"昨天"、"今天"
- 季度: "第一季度"、"Q1"、"上半年"
"""

    # 🔥🔥🔥 【关键】数据分析输出强制要求（确保 answer 字段始终有内容）
    data_analysis_output_requirement = """

## 🔴🔴🔴 【强制要求】必须生成数据分析文本！

**⚠️ 调用工具后，必须用文字总结查询结果！**

每次查询后，你必须在文本回复中包含：
1. **数据概要**：查询返回了多少条记录
2. **关键发现**：数据中的重要趋势或异常值
3. **数值解读**：具体数字的含义（如"销售额增长了20%"）
4. **业务洞察**：数据对业务的启示

**正确格式示例**：
```
📊 [数据分析结果]

根据查询结果，共找到 15 条订单记录：

🔍 **关键发现**：
• 小米品牌的总销售额为 ¥125,000，占总销售额的 32%
• 平均订单金额为 ¥8,333
• 最高单笔订单为 ¥15,000（2024-05-15）

💡 **业务洞察**：
小米品牌表现良好，销售额占比超过三成，是核心品牌之一。建议继续关注该品牌的库存和促销活动。
```

**❌ 禁止做法**：
- 只调用工具，不生成文本总结
- 只输出"查询完成"、"已生成图表"等无意义回复
- 只展示SQL语句而不解释结果

**✅ 正确做法**：
- 调用 query 工具获取数据
- 调用图表工具生成可视化（如需要）
- **用文字详细分析数据结果**
"""

    try:
        try:
            from .prompt_generator import generate_database_aware_system_prompt
        except ImportError:
            from prompt_generator import generate_database_aware_system_prompt
        result = generate_database_aware_system_prompt(db_type, BASE_SYSTEM_PROMPT)

        # 🔧 检测是否为测试数据库，注入正确的表结构信息
        if 'ecommerce_test_db' in config.database_url:
            test_db_schema = """

## 🧪 测试数据库表结构（重要！使用以下表名和字段）

**核心业务表**：
1. **users** - 用户表（不是customers！）
   - id: 用户ID
   - username: 用户名
   - vip_level: VIP等级（0=普通, 1=银卡, 2=金卡, 3=钻石）
   - total_spent: 累计消费金额
   - gender: 性别
   - registration_date: 注册时间

2. **orders** - 订单表
   - id: 订单ID
   - user_id: 用户ID（关联users.id，不是customer_id！）
   - total_amount: 订单总金额
   - final_amount: 实付金额
   - status: 订单状态（pending/completed/cancelled）
   - order_date: 订单日期（date类型）
   - created_at: 创建时间

3. **products** - 商品表
   - id: 商品ID
   - name: 商品名称
   - category_id: 类别ID（关联categories.id）
   - brand: 品牌
   - price: 价格
   - sales_count: 销量
   - rating: 平均评分
   - review_count: 评价数

4. **reviews** - 评价表
   - id: 评价ID
   - product_id: 商品ID
   - user_id: 用户ID（关联users.id）
   - rating: 评分（1-5）
   - content: 评价内容
   - created_at: 创建时间

5. **categories** - 商品类别表
   - id: 类别ID
   - name: 类别名称
   - parent_id: 父类别ID

6. **order_items** - 订单明细表
   - order_id: 订单ID
   - product_id: 商品ID
   - quantity: 数量
   - price: 单价
   - subtotal: 小计

7. **addresses** - 地址表
   - user_id: 用户ID（关联users.id）
   - city: 城市
   - province: 省份

## ⚠️⚠️⚠️ 重要：查询用户和订单关联时使用 user_id
- ❌ 错误：customer_id, cid
- ✅ 正确：user_id, u.user_id
- 关联方式：FROM orders o JOIN users u ON o.user_id = u.id

## 📋 用户复购分析专用SQL模板
```sql
-- 统计每个用户的下单次数
SELECT user_id, COUNT(*) as order_count
FROM orders
GROUP BY user_id
ORDER BY order_count DESC;

-- 分析复购用户占比
SELECT
    CASE WHEN order_count >= 2 THEN '复购用户' ELSE '单次购买用户' END as user_type,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM (SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id) sub
GROUP BY user_type;

-- 用户订单数量分布（直方图）
SELECT order_count, COUNT(*) as user_count
FROM (SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id) sub
GROUP BY order_count
ORDER BY order_count;
```
   - user_id: 用户ID
   - city: 城市
   - province: 省份
"""
            result = result + test_db_schema

        # 在提示词末尾追加数据分析输出要求和时间上下文
        result = result + data_analysis_output_requirement + time_context
        logger.debug("[get_system_prompt] 生成提示词长度=%s", len(result))
        # 打印提示词的前200字符，验证是否包含数据库特定信息
        preview = result[:200].replace('\n', ' ')
        logger.debug("[get_system_prompt] 提示词预览: %s...", preview)
        return result
    except ImportError as e:
        logger.warning("无法导入 prompt_generator，使用默认 PostgreSQL 提示词: %s", e)
        return BASE_SYSTEM_PROMPT + data_analysis_output_requirement + time_context
    except Exception as e:
        logger.warning("生成动态提示词失败，使用默认 PostgreSQL 提示词: %s", e)
        return BASE_SYSTEM_PROMPT + data_analysis_output_requirement + time_context


# 默认提示词（向后兼容）
SYSTEM_PROMPT = BASE_SYSTEM_PROMPT


def create_llm():
    """Create DeepSeek LLM instance using OpenAI-compatible API"""
    return ChatOpenAI(
        model=config.deepseek_model,
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
        temperature=0,
    )


def parse_chart_config(content: str) -> Optional[Dict[str, Any]]:
    """从LLM回复中解析JSON图表配置（增强版，支持多种格式和容错）

    Args:
        content: LLM的文本回复

    Returns:
        解析出的JSON配置，如果没有则返回None

    支持的格式:
        1. ```json ... ``` 代码块
        2. ```JSON ... ``` 代码块（大写）
        3. 直接的 JSON 对象 {...}
        4. 带有 JavaScript 注释的 JSON（会尝试清理）
    """
    if not content or not content.strip():
        return None

    # 策略1: 尝试匹配 ```json ... ``` 代码块（不区分大小写）
    json_pattern = r'```(?:json|JSON)\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, content)

    if match:
        json_str = match.group(1).strip()
        result = _try_parse_json(json_str)
        if result is not None:
            return result

    # 策略2: 尝试匹配任意代码块中的 JSON
    code_block_pattern = r'```\s*([\s\S]*?)\s*```'
    for match in re.finditer(code_block_pattern, content):
        json_str = match.group(1).strip()
        # 检查是否像 JSON（以 { 或 [ 开头）
        if json_str.startswith('{') or json_str.startswith('['):
            result = _try_parse_json(json_str)
            if result is not None:
                return result

    # 策略3: 尝试直接匹配 JSON 对象 {...}
    # 使用贪婪但平衡的匹配（简单版本）
    direct_json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    for match in re.finditer(direct_json_pattern, content):
        json_str = match.group(0)
        result = _try_parse_json(json_str)
        if result is not None:
            # 验证是否是图表配置（至少包含一些预期字段）
            if any(key in result for key in ['chart_type', 'data', 'title', 'type']):
                return result

    return None


def _try_parse_json(json_str: str) -> Optional[Dict[str, Any]]:
    """尝试解析 JSON 字符串，支持容错处理

    Args:
        json_str: JSON 字符串

    Returns:
        解析后的字典，失败返回 None
    """
    if not json_str:
        return None

    # 尝试1: 直接解析
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 尝试2: 清理常见的 LLM 错误后再解析
    cleaned = json_str

    # 移除 JavaScript 风格的单行注释
    cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)

    # 移除 JavaScript 风格的多行注释
    cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)

    # 移除尾随逗号（JSON 不允许，但 JS 允许）
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)

    # 将 Python 的 None/True/False 转换为 JSON 的 null/true/false
    cleaned = re.sub(r'\bNone\b', 'null', cleaned)
    cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
    cleaned = re.sub(r'\bFalse\b', 'false', cleaned)

    # 将单引号转换为双引号（JSON 要求双引号）
    # 注意：这个替换比较危险，只在其他方法都失败时使用
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 尝试3: 单引号转双引号（最后手段）
    try:
        # 简单的单引号到双引号转换（不处理嵌套引号）
        cleaned_quotes = cleaned.replace("'", '"')
        return json.loads(cleaned_quotes)
    except json.JSONDecodeError:
        pass

    return None


def extract_tool_data(messages: list) -> tuple[Optional[str], list]:
    """从消息历史中提取工具调用的SQL和返回数据

    Args:
        messages: 消息历史列表

    Returns:
        (sql语句, 原始数据列表)
    """
    sql = None
    raw_data = []

    for msg in messages:
        # 提取SQL（从AIMessage的tool_calls中）
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get('name') in ('query', 'execute_query'):
                    sql = tc.get('args', {}).get('sql')

        # 提取数据（从ToolMessage中）
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if isinstance(data, list):
                    raw_data = data
            except (json.JSONDecodeError, TypeError):
                pass

    return sql, raw_data


def extract_chart_tool_call(messages: list) -> Optional[Dict[str, Any]]:
    """从消息历史中提取图表工具调用信息

    Args:
        messages: 消息历史列表

    Returns:
        包含工具名和参数的字典，如果没有图表工具调用则返回 None
    """
    chart_tools = [
        "generate_bar_chart", "generate_line_chart", "generate_pie_chart",
        "generate_scatter_chart", "generate_radar_chart", "generate_funnel_chart",
        "generate_echarts"
    ]

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get('name', '')
                if tool_name in chart_tools:
                    return {
                        "tool_name": tool_name,
                        "args": tc.get('args', {})
                    }
    return None


async def call_mcp_chart_tool(tool_name: str, args: Dict[str, Any], output_dir: str = "./charts", timeout: float = 30.0) -> Optional[str]:
    """使用原始 MCP 客户端调用图表工具（绕过 LangChain 适配器的限制）

    Args:
        tool_name: 工具名称
        args: 工具参数
        output_dir: 输出目录
        timeout: 超时时间（秒），默认30秒

    Returns:
        保存的图片路径，失败返回 None
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    import asyncio

    url = "http://localhost:3033/sse"

    try:
        # 添加超时保护
        async def _call_with_session():
            async with sse_client(url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()

                    result = await session.call_tool(tool_name, args)

                    if hasattr(result, 'content') and result.content:
                        for item in result.content:
                            if hasattr(item, 'type') and item.type == 'image':
                                if hasattr(item, 'data') and item.data:
                                    return _save_base64_image(item.data, output_dir, "png")
                            elif hasattr(item, 'text') and item.text:
                                # 可能是 URL 或其他文本
                                text = item.text
                                if text.startswith("http"):
                                    return text
                    return None

        return await asyncio.wait_for(_call_with_session(), timeout=timeout)

    except asyncio.TimeoutError:
        print(f"[MCP] Chart tool call timeout after {timeout}s")
        return None
    except Exception as e:
        print(f"[MCP] Chart tool call failed: {e}")
        return None


def _save_base64_image(base64_data: str, output_dir: str, ext: str = "png") -> str:
    """保存 Base64 编码的图片到文件

    Args:
        base64_data: Base64 编码的图片数据
        output_dir: 输出目录
        ext: 文件扩展名

    Returns:
        保存的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mcp_chart_{timestamp}.{ext}"
    filepath = os.path.join(output_dir, filename)

    # 解码并保存
    image_data = base64.b64decode(base64_data)
    with open(filepath, "wb") as f:
        f.write(image_data)

    print(f"📊 图表已保存: {filepath}")
    return filepath


def _should_generate_chart_for_query(query: str) -> bool:
    """
    判断是否应该为查询生成图表

    Args:
        query: 用户查询

    Returns:
        bool: 是否应该生成图表
    """
    if not query:
        return False

    query_lower = query.lower()

    # 图表关键词 - 这些查询通常需要可视化
    chart_keywords = [
        # 占比/分布类
        '占比', '比例', '分布', '百分比', '%', 'proportion', 'distribution',
        # 趋势类
        '趋势', '变化', '增长', '下降', '走势', 'trend', 'change',
        # 排名类
        '排名', '排行', 'top', 'highest', 'lowest', 'ranking',
        # 统计类
        '统计', '数量', '总计', '平均', 'maximum', 'minimum', 'count', 'total', 'average',
        # 可视化类
        '图表', '可视化', '展示', 'chart', 'graph', 'visualize',
        # 对比类
        '对比', '比较', '差异', 'compare', 'difference', 'vs',
    ]

    # 检查是否包含图表关键词
    for keyword in chart_keywords:
        if keyword in query_lower:
            return True

    # 时间相关查询
    time_keywords = ['每月', '每年', '月度', '年度', 'daily', 'monthly', 'yearly', '按月', '按年']
    for keyword in time_keywords:
        if keyword in query_lower:
            return True

    # 省份/地区相关查询
    location_keywords = ['省份', '城市', '地区', '各', 'province', 'city', 'region']
    for keyword in location_keywords:
        if keyword in query_lower:
            return True

    return False


async def _generate_default_answer(query_result: QueryResult, sql: str, chart_config: ChartConfig, user_query: str = "") -> str:
    """
    生成默认的数据分析文本（当 LLM 没有生成分析时使用）

    🔧 新增：集成 AnalysisNode 生成智能分析报告

    Args:
        query_result: 查询结果
        sql: SQL 语句
        chart_config: 图表配置
        user_query: 用户原始查询（可选）

    Returns:
        str: 默认分析文本
    """
    if query_result.row_count == 0:
        return "📊 [查询结果]\n\n未找到符合条件的数据记录。"

    rows = query_result.rows
    columns = query_result.columns
    row_count = query_result.row_count

    # 数据覆盖范围提示（最小/最大日期）
    coverage_bounds = _extract_date_bounds(rows, columns)
    coverage_text = ""
    if coverage_bounds:
        min_d, max_d = coverage_bounds
        coverage_text = f"数据覆盖范围：{min_d.isoformat()} 至 {max_d.isoformat()}"

    # 🔧 新增：尝试使用 AnalysisNode 生成智能分析
    try:
        # 导入 AnalysisNode
        from .nodes.analysis_node import create_analysis_node

        # 将 QueryResult 转换为字典列表格式
        data_list = []
        for row in rows:
            row_dict = {}
            for j, col in enumerate(columns):
                if j < len(row):
                    row_dict[col] = row[j]
            data_list.append(row_dict)

        # 创建分析节点并生成报告
        analysis_node = create_analysis_node()
        report = analysis_node.generate_analysis_report(
            query=user_query or "数据查询",
            data=data_list,
            sql=sql
        )

        # 构建增强的分析文本
        answer_parts = [
            "📊 [数据分析结果]\n"
        ]

        # 数据概要
        answer_parts.append(f"📈 **数据概要**: 共 {row_count} 条记录\n")
        if coverage_text:
            answer_parts.append(f"📅 {coverage_text}\n")

        # 洞察发现
        if report.insights:
            answer_parts.append("💡 **洞察发现**:\n")
            for insight in report.insights:
                severity_emoji = {
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "critical": "🚨"
                }.get(insight.severity, "•")
                answer_parts.append(f"{severity_emoji} {insight.title}: {insight.description}\n")

        # 数值统计
        if report.column_stats:
            answer_parts.append("\n📊 **数值统计**:\n")
            for col, stat in report.column_stats.items():
                if stat["type"] == "numeric":
                    answer_parts.append(f"• **{col}**: 最小={stat['min']}, 最大={stat['max']}, 平均={stat['mean']:.2f}\n")

        # 建议和图表说明
        if report.suggestions:
            answer_parts.append("\n💡 **分析建议**:\n")
            for suggestion in report.suggestions[:3]:  # 最多3条建议
                answer_parts.append(f"• {suggestion}\n")

        # 图表推荐
        if report.chart_recommendation:
            rec = report.chart_recommendation
            answer_parts.append(f"\n📊 **可视化**: 已推荐 {rec.get('chart_type', '图表')} 类型\n")

        return "".join(answer_parts)

    except Exception as e:
        logger.warning(f"AnalysisNode 集成失败，使用基础分析: {e}")
        # 回退到原始逻辑
        pass

    # ===== 原始逻辑（作为回退） =====
    # 构建分析文本
    answer_parts = [
        "📊 [数据分析结果]",
        f"\n根据查询结果，共找到 {row_count} 条记录：\n"
    ]
    if coverage_text:
        answer_parts.append(f"📅 {coverage_text}\n")

    # 添加前几条数据预览
    preview_count = min(5, row_count)
    answer_parts.append("🔍 **数据预览**（前{}条）：".format(preview_count))

    for i in range(preview_count):
        row_data = []
        for j, col in enumerate(columns):
            if j < len(rows[i]):
                row_data.append(f"{col}: {rows[i][j]}")
        answer_parts.append(f"• {', '.join(row_data)}")

    if row_count > 5:
        answer_parts.append(f"\n... 还有 {row_count - 5} 条记录")

    # 尝试进行数值分析
    numeric_analysis = _analyze_numeric_data(rows, columns)
    if numeric_analysis:
        answer_parts.append("\n🔍 **数值统计**：")
        answer_parts.append(numeric_analysis)

    # 添加图表说明
    if chart_config and chart_config.title:
        chart_type = chart_config.chart_type.value if hasattr(chart_config.chart_type, 'value') else str(chart_config.chart_type)
        answer_parts.append(f"\n📊 已生成 {chart_type} 图表：{chart_config.title}")

    return "\n".join(answer_parts)


def _analyze_numeric_data(rows: list, columns: list) -> str:
    """
    分析数值数据，生成统计摘要

    Args:
        rows: 数据行
        columns: 列名

    Returns:
        str: 数值分析摘要
    """
    if not rows or not columns:
        return ""

    analysis_parts = []

    # 寻找数值列
    for col_idx, col_name in enumerate(columns):
        if col_idx >= len(rows[0]):
            continue

        # 检查该列是否为数值类型
        is_numeric = True
        numeric_values = []

        for row in rows:
            if col_idx < len(row):
                val = row[col_idx]
                if isinstance(val, (int, float)):
                    numeric_values.append(float(val))
                elif isinstance(val, str) and val.replace('.', '').replace('-', '').replace('+', '').isdigit():
                    try:
                        numeric_values.append(float(val))
                    except ValueError:
                        is_numeric = False
                        break
                else:
                    is_numeric = False
                    break

        if is_numeric and numeric_values:
            # 计算统计信息
            count = len(numeric_values)
            total = sum(numeric_values)
            avg = total / count if count > 0 else 0
            max_val = max(numeric_values)
            min_val = min(numeric_values)

            analysis_parts.append(
                f"• {col_name}: 总计={total:.2f}, 平均={avg:.2f}, 最大={max_val}, 最小={min_val}"
            )

    return "\n".join(analysis_parts) if analysis_parts else ""


def _validate_numerical_claims(
    answer: str,
    query_result: QueryResult,
    sql: str
) -> tuple[str, bool]:
    """
    验证AI回答中的数值声明是否与查询结果一致

    主要检测占比计算错误，例如：
    - 安徽客户1000人，总客户1000人，AI却得出"占比10%"（应为100%）

    Args:
        answer: AI生成的回答文本
        query_result: 查询结果对象
        sql: 执行的SQL语句

    Returns:
        (修复后的回答, 是否需要修复)
    """
    if not query_result.raw_data or len(query_result.raw_data) == 0:
        return answer, False

    # 提取回答中的百分比声明
    # 匹配模式: "10%", "占比为10", "比例 10.5", etc.
    percentage_patterns = [
        r'(\d+\.?\d*)%',                    # 10%
        r'占比\s*(?:为)?\s*(\d+\.?\d*)',    # 占比为10
        r'比例\s*(?:为)?\s*(\d+\.?\d*)',    # 比例为10
        r'(\d+\.?\d*)\s*个百分比',          # 10个百分比
    ]

    import re
    all_matches = []
    for pattern in percentage_patterns:
        matches = re.findall(pattern, answer)
        all_matches.extend([(m, pattern) for m in matches])

    if not all_matches:
        return answer, False

    # 获取查询结果中的数值
    values = []
    if query_result.raw_data:
        for row in query_result.raw_data:
            for v in row.values():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    values.append(float(v))

    if len(values) < 2:
        # 单点数据无法验证占比
        return answer, False

    # 核心验证逻辑：检测相同数值时的占比错误
    # 如果两个主要数值相等（如安徽客户1000，总客户1000），占比应该是100%
    # 提取前两个主要数值进行比较
    main_values = sorted(values, key=abs, reverse=True)[:2]

    if len(main_values) >= 2:
        val1, val2 = main_values[0], main_values[1]

        # 如果两个数值非常接近（相对误差小于0.1%）
        if val1 > 0 and abs(val1 - val2) / val1 < 0.001:
            # 应该是100%，检查AI是否声明了错误的百分比
            needs_fix = False
            fixed_answer = answer

            for match_str, pattern in all_matches:
                try:
                    percentage_val = float(match_str)
                    # 如果声明的百分比不是100%或接近100%，需要修复
                    if abs(percentage_val - 100) > 1:
                        needs_fix = True
                        # 替换错误的百分比为100%
                        if '%' in pattern:
                            fixed_answer = re.sub(
                                r'\d+\.?\d*%',
                                '100%',
                                fixed_answer
                            )
                        else:
                            fixed_answer = re.sub(
                                r'占比\s*(?:为)?\s*\d+\.?\d*',
                                '占比为100',
                                fixed_answer
                            )
                            fixed_answer = re.sub(
                                r'比例\s*(?:为)?\s*\d+\.?\d*',
                                '比例为100',
                                fixed_answer
                            )
                except (ValueError, TypeError):
                    continue

            if needs_fix:
                print(f"[Agent] ⚠️ 检测到数值计算错误（两个主要数值相近: {val1} vs {val2}），已自动修复为100%")
                return fixed_answer, True

    # 额外检查：如果只有一个数值且是计数，避免声明错误的占比
    if len(values) == 1:
        val = values[0]
        # 检查是否声明了与自身相关的百分比
        for match_str, pattern in all_matches:
            try:
                percentage_val = float(match_str)
                # 如果数值较大（>100）且声明了小百分比，可能是错误
                if val > 100 and percentage_val < 50:
                    # 这种情况下可能是AI幻觉，但不直接修复，只记录警告
                    print(f"[Agent] ⚠️ 可能的数值幻觉: 单一数值{val}但声明了{percentage_val}%占比")
            except (ValueError, TypeError):
                continue

    return answer, False


async def build_visualization_response(
    messages: list,
    final_content: str,
    auto_generate_chart: bool = True,
    user_query: str = ""
) -> VisualizationResponse:
    """构建完整的可视化响应，并可选生成图表

    Args:
        messages: 完整的消息历史
        final_content: 最终的AI回复内容
        auto_generate_chart: 是否自动生成图表文件
        user_query: 用户原始查询（用于智能数据分析）

    Returns:
        VisualizationResponse对象
    """
    # 🔧 从 messages 中提取用户查询（如果未提供）
    if not user_query and messages:
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                user_query = msg.content
                break
            elif isinstance(msg, dict) and msg.get('type') == 'human':
                user_query = msg.get('content', '')
                break
            elif hasattr(msg, 'content') and not hasattr(msg, 'type'):
                # 可能是 HumanMessage
                content = msg.content
                if isinstance(content, str) and len(content) < 500:
                    user_query = content
                    break
    # ========================================================================
    # 🔍 检测反射节点的错误消息
    # ========================================================================
    # 如果最终回答包含这些错误指示器，说明反射节点检测到了错误但被当作正常回答返回
    ERROR_INDICATORS = [
        "**执行失败，正在进行自我修正**",
        "**错误类型**:",
        "error_category",
    ]

    is_error_response = any(indicator in final_content for indicator in ERROR_INDICATORS)

    if is_error_response:
        # 这是一个错误响应，返回失败状态
        print("⚠️ [错误检测] 检测到反射节点错误消息，返回失败状态")
        return VisualizationResponse(
            success=False,
            answer=final_content,
            sql="",
            chart=None,
            error="Reflection node detected an error in the query"
        )

    # 提取SQL和原始数据
    sql, raw_data = extract_tool_data(messages)

    # 🆕 检查是否有 mcp-echarts 图表工具调用
    chart_tool_call = extract_chart_tool_call(messages)
    mcp_chart_path = None

    # 如果 LLM 调用了图表工具，使用原始 MCP 客户端重新获取图片
    if chart_tool_call and ENABLE_ECHARTS_MCP:
        print(f"[MCP] Detected chart tool call: {chart_tool_call['tool_name']}")
        try:
            mcp_chart_path = await call_mcp_chart_tool(
                chart_tool_call['tool_name'],
                chart_tool_call['args']
            )
        except Exception as e:
            print(f"[MCP] Failed to call chart tool: {e}")

    # 解析图表配置
    chart_config_data = parse_chart_config(final_content)

    # 构建QueryResult
    query_result = QueryResult.from_raw_data(raw_data) if raw_data else QueryResult()

    # ========================================================================
    # 🔥 数据一致性验证：防止 LLM 幻觉导致的数据不匹配问题
    # ========================================================================
    # 验证 LLM 生成的字段是否真实存在于查询结果中
    llm_x_field = chart_config_data.get('x_field') if chart_config_data else None
    llm_y_field = chart_config_data.get('y_field') if chart_config_data else None

    actual_columns = []
    if raw_data and len(raw_data) > 0:
        actual_columns = list(raw_data[0].keys())

    # 检测幻觉字段
    hallucinated_fields = []
    if llm_x_field and llm_x_field not in actual_columns:
        hallucinated_fields.append(f"x_field: {llm_x_field}")
    if llm_y_field and llm_y_field not in actual_columns:
        hallucinated_fields.append(f"y_field: {llm_y_field}")

    if hallucinated_fields:
        print(f"⚠️ [数据验证] 检测到 LLM 幻觉字段: {hallucinated_fields}")
        print(f"   实际字段: {actual_columns}，将使用智能字段映射")
        # 清除幻觉配置，强制使用智能映射
        chart_config_data = None

    # 使用智能字段映射（如果有数据）
    if raw_data and DATA_VALIDATION_ENABLED:
        field_mapping = smart_field_mapping(raw_data, sql)
        chart_rec = recommend_chart(raw_data, sql, final_content[:200] if final_content else "")

        # 覆盖 LLM 提供的字段，使用真实数据映射
        if not chart_config_data:
            chart_config_data = {
                'chart_type': chart_rec.chart_type,
                'chart_title': chart_rec.title,
                'x_field': field_mapping.x_field,
                'y_field': field_mapping.y_field,
            }
            print(f"📊 [智能映射] X={field_mapping.x_field}, Y={field_mapping.y_field}, 类型={chart_rec.chart_type}")
        else:
            # 验证 LLM 配置的字段，如果无效则使用智能映射
            if llm_x_field and llm_x_field not in actual_columns:
                chart_config_data['x_field'] = field_mapping.x_field
            if llm_y_field and llm_y_field not in actual_columns:
                chart_config_data['y_field'] = field_mapping.y_field

    # 基于数据自动生成双轴配置（销售额+订单量），避免单轴挤压
    if raw_data:
        dual_cfg = _build_dual_axis_chart_config(raw_data)
        if dual_cfg:
            if not chart_config_data:
                chart_config_data = dual_cfg
            else:
                chart_config_data.setdefault('series', dual_cfg.get('series', []))
                chart_config_data.setdefault('chart_type', dual_cfg.get('chart_type', 'line'))
                chart_config_data.setdefault('x_field', dual_cfg.get('x_field'))
                chart_config_data.setdefault('y_field', dual_cfg.get('y_field'))
                chart_config_data['is_dual_axis'] = True
                chart_config_data['left_axis_name'] = dual_cfg.get('left_axis_name', '')
                chart_config_data['right_axis_name'] = dual_cfg.get('right_axis_name', '')

    # 🔧 新增：如果没有图表配置但有数据，使用 AnalysisNode 生成图表推荐
    if not chart_config_data and raw_data and len(raw_data) > 0:
        try:
            from .nodes.analysis_node import create_analysis_node

            # 将 raw_data 转换为字典列表
            data_list = raw_data if isinstance(raw_data[0], dict) else [
                {col: row[i] for i, col in enumerate(actual_columns)}
                for row in [[list(r.values()) if isinstance(r, dict) else r][0] for r in raw_data[:100]]
            ] if actual_columns else []

            if data_list:
                analysis_node = create_analysis_node()
                report = analysis_node.generate_analysis_report(
                    query=user_query or "数据查询",
                    data=data_list,
                    sql=sql
                )

                # 使用 AnalysisNode 的图表推荐
                if report.chart_recommendation:
                    rec = report.chart_recommendation
                    chart_type_map = {
                        'pie': 'pie',
                        'bar': 'bar',
                        'line': 'line',
                        'scatter': 'scatter',
                        'radar': 'radar',
                        'table': 'table'
                    }
                    recommended_type = chart_type_map.get(rec.get('chart_type', 'table'), 'table')

                    # 判断是否应该生成图表（基于查询类型）
                    should_gen = _should_generate_chart_for_query(user_query)
                    if should_gen:
                        chart_config_data = {
                            'chart_type': recommended_type,
                            'chart_title': f"{user_query[:20]}..." if len(user_query) > 20 else user_query,
                            'x_field': rec.get('x_field'),
                            'y_field': rec.get('y_field'),
                            'generate_chart': True  # 标记需要生成图表
                        }
                        print(f"📊 [AnalysisNode推荐] 类型={recommended_type}, X={rec.get('x_field')}, Y={rec.get('y_field')}")
        except Exception as e:
            logger.warning(f"AnalysisNode 图表推荐失败: {e}")

    # 构建ChartConfig
    chart_path = mcp_chart_path  # 优先使用 mcp-echarts 的图表

    if chart_config_data:
        chart_type_str = chart_config_data.get('chart_type', 'table')
        try:
            chart_type = ChartType(chart_type_str)
        except ValueError:
            chart_type = ChartType.TABLE

        chart_config = ChartConfig(
            chart_type=chart_type,
            title=chart_config_data.get('chart_title', ''),
            x_field=chart_config_data.get('x_field'),
            y_field=chart_config_data.get('y_field'),
            series=chart_config_data.get('series', []),
            is_dual_axis=chart_config_data.get('is_dual_axis', False),
            left_axis_name=chart_config_data.get('left_axis_name', chart_config_data.get('y_field', '')),
            right_axis_name=chart_config_data.get('right_axis_name', '')
        )

        # 🔧 修复：避免重复内容
        # 如果 chart_config_data['answer'] 和 final_content 重复，只保留一个
        chart_answer = chart_config_data.get('answer', '').strip()
        final_answer = final_content.strip()

        if chart_answer and chart_answer in final_answer:
            # chart_answer 是 final_answer 的子集，使用完整的
            answer = final_answer
        elif chart_answer and final_answer and chart_answer != final_answer:
            # 两者不同且都有内容，检查是否有大量重复
            # 如果相似度高，只保留较长的那个
            similarity = len(set(chart_answer) & set(final_answer)) / max(len(set(chart_answer)), len(set(final_answer)), 1)
            if similarity > 0.7:
                answer = final_answer if len(final_answer) > len(chart_answer) else chart_answer
            else:
                answer = final_answer  # 默认使用 final_content
        else:
            answer = final_answer if final_answer else chart_answer

        # 如果没有 mcp-echarts 图表，尝试使用本地生成（回退方案）
        if not chart_path and auto_generate_chart:
            should_generate = chart_config_data.get('generate_chart', False)
            # 🔧 如果没有明确设置 generate_chart，根据查询类型判断
            if not should_generate:
                should_generate = _should_generate_chart_for_query(user_query)

            if should_generate and raw_data and chart_type != ChartType.TABLE:
                chart_path = _generate_chart_file(
                    raw_data=raw_data,
                    chart_type=chart_type_str,
                    title=chart_config.title,
                    x_field=chart_config.x_field,
                    y_field=chart_config.y_field
                )
    else:
        chart_config = ChartConfig()
        answer = final_content

        # 🔧 新增：即使没有 chart_config_data，如果查询需要图表且有数据，尝试生成
        if not chart_path and auto_generate_chart and raw_data and _should_generate_chart_for_query(user_query):
            try:
                from .nodes.analysis_node import create_analysis_node

                # 转换数据
                actual_columns = list(raw_data[0].keys()) if raw_data and len(raw_data) > 0 else []
                data_list = raw_data if isinstance(raw_data[0], dict) else []

                if data_list:
                    analysis_node = create_analysis_node()
                    report = analysis_node.generate_analysis_report(
                        query=user_query or "数据查询",
                        data=data_list,
                        sql=sql
                    )

                    if report.chart_recommendation:
                        rec = report.chart_recommendation
                        chart_type_str = rec.get('chart_type', 'table')
                        if chart_type_str != 'table':
                            chart_path = _generate_chart_file(
                                raw_data=raw_data,
                                chart_type=chart_type_str,
                                title=f"{user_query[:20]}..." if len(user_query) > 20 else user_query,
                                x_field=rec.get('x_field'),
                                y_field=rec.get('y_field')
                            )
                            if chart_path:
                                print(f"📊 [自动生成图表] {chart_type_str} 图表: {chart_path}")
            except Exception as e:
                logger.warning(f"自动图表生成失败: {e}")

    # 🔥🔥🔥 【关键修复】数值验证：防止 AI 幻觉导致计算错误
    # 验证AI生成的数值（如百分比）是否与查询结果一致
    validated_answer, needs_fix = _validate_numerical_claims(answer, query_result, sql or '')
    if needs_fix:
        answer = validated_answer

    # 🔥🔥🔥 【关键修复】确保 answer 字段始终有内容
    # 如果 LLM 没有生成分析文本，基于查询结果生成默认分析
    if not answer or not answer.strip():
        answer = await _generate_default_answer(query_result, sql or '', chart_config, user_query)
        print("[Agent] LLM未生成分析文本，已生成默认数据分析")

    response = VisualizationResponse(
        answer=answer,
        sql=sql or '',
        data=query_result,
        chart=chart_config,
        success=True
    )

    # 将图表路径添加到响应中（如果生成了）
    if chart_path and isinstance(chart_path, str):
        # 🔧 修复：检查 answer 中是否已经包含图表信息，避免重复添加
        chart_link_text = f"图表链接: {chart_path}" if chart_path.startswith("http") else f"图表已保存: {chart_path}"
        answer_str = str(answer) if answer is not None else ""
        if "📊" not in answer_str and chart_link_text not in answer_str:
            response.answer = f"{answer}\n\n📊 {chart_link_text}"

    return response


def _generate_chart_file(
    raw_data: list,
    chart_type: str,
    title: str,
    x_field: Optional[str],
    y_field: Optional[str]
) -> Optional[str]:
    """生成图表文件

    Args:
        raw_data: SQL查询的原始数据
        chart_type: 图表类型
        title: 图表标题
        x_field: X轴字段
        y_field: Y轴字段

    Returns:
        生成的图表文件路径，失败返回None
    """
    # 跳过不需要图表的类型
    if chart_type in ('table', 'none'):
        return None

    try:
        # 转换数据格式
        echarts_data, actual_x, actual_y = sql_result_to_echarts_data(
            raw_data, x_field, y_field
        )

        if not echarts_data:
            return None

        # 创建图表请求
        request = ChartRequest(
            type=chart_type,
            data=echarts_data,
            title=title or "查询结果",
            series_name=actual_y or "数值",
            x_axis_name=actual_x,
            y_axis_name=actual_y
        )

        # 生成图表（使用简化版，生成HTML）
        response: ChartResponse = generate_chart_simple(request, output_dir="./charts")

        if response.success:
            return response.image_path
        else:
            print(f"⚠️ 图表生成失败: {response.error}")
            return None

    except Exception as e:
        print(f"⚠️ 图表生成异常: {e}")
        return None


# MCP client 配置
# 是否启用 mcp-echarts（需要先运行: mcp-echarts -t sse -p 3033）
ENABLE_ECHARTS_MCP = True  # 已启用 mcp-echarts

# ============================================================
# 🚀 性能优化：持久化单例模式
# ============================================================
# 全局缓存，避免每次查询都重新初始化
_cached_agent = None
_cached_mcp_client = None
_cached_tools = None
_cached_checkpointer = None
_cached_db_type = "postgresql"  # 缓存当前数据库类型


def _get_mcp_config():
    """获取 MCP 服务器配置"""
    import shutil
    import sys
    
    # Check if npx is available
    npx_command = "npx.cmd" if sys.platform == "win32" else "npx"
    npx_path = shutil.which(npx_command)
    
    if not npx_path:
        error_msg = (
            f"❌ npx 命令不可用。MCP PostgreSQL 服务器需要 Node.js/npm。\n"
            f"   请安装 Node.js 或设置 DISABLE_MCP_TOOLS=true 使用自定义工具。\n"
            f"   当前平台: {sys.platform}, 查找的命令: {npx_command}"
        )
        print(error_msg)
        raise RuntimeError(
            f"npx command not found. Node.js is required for MCP servers. "
            f"Platform: {sys.platform}, Command: {npx_command}. "
            f"Set DISABLE_MCP_TOOLS=true to use custom tools instead."
        )
    
    print(f"✅ npx 可用: {npx_path}")

    # 确保DATABASE_URL包含SSL参数
    db_url = config.database_url
    if "sslmode" not in db_url.lower():
        if "?" in db_url:
            db_url += "&sslmode=require"
        else:
            db_url += "?sslmode=require"
        print("🔒 添加SSL参数到数据库连接")

    mcp_config = {
        "postgres": {
            "transport": "stdio",
            "command": npx_command,
            "args": [
                "-y",
                "@modelcontextprotocol/server-postgres",
                db_url
            ],
        }
    }

    if ENABLE_ECHARTS_MCP:
        # 本地开发使用 localhost，Docker环境使用服务名 mcp_echarts
        mcp_config["echarts"] = {
            "transport": "sse",
            "url": "http://localhost:3033/sse",
            "timeout": 30.0,
            "sse_read_timeout": 30.0,
        }

    return mcp_config


async def _get_or_create_agent(db_type: str = "postgresql"):
    """获取或创建持久化的 Agent 实例（单例模式）

    Args:
        db_type: 数据库类型，用于生成特定的系统提示词

    Returns:
        tuple: (agent, mcp_client) - 编译好的agent和MCP客户端
    """
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer, _cached_db_type

    # 检查数据库类型是否变化，如果变化则重置 Agent
    if _cached_agent is not None and _cached_db_type != db_type:
        print(f"🔄 数据库类型变化: {_cached_db_type} -> {db_type}，重置 Agent...")
        await reset_agent()
        _cached_db_type = db_type

    # 如果已缓存，直接返回
    if _cached_agent is not None and _cached_mcp_client is not None:
        return _cached_agent, _cached_mcp_client

    print(f"🔄 首次初始化 Agent（数据库类型: {db_type}，后续查询将复用连接）...")

    # 创建 MCP 客户端
    try:
        mcp_config = _get_mcp_config()
        _cached_mcp_client = MultiServerMCPClient(mcp_config)
    except RuntimeError as e:
        print(f"❌ MCP 配置失败: {e}")
        print("   提示: 设置 DISABLE_MCP_TOOLS=true 可以禁用 MCP 并使用自定义工具")
        raise
    except Exception as e:
        print(f"❌ MCP 客户端创建失败: {e}")
        raise

    # 获取工具
    try:
        _cached_tools = await _cached_mcp_client.get_tools()
        print(f"✅ MCP 工具加载成功，共 {len(_cached_tools)} 个工具")
        
        # 🔥🔥🔥 强制添加文件数据源工具（硬编码方式，不依赖任何条件）
        tool_names_before = [getattr(t, "name", str(t)) for t in _cached_tools]
        print(f"📋 MCP 工具列表: {', '.join(tool_names_before)}")
        
        # 强制添加 inspect_file
        if _inspect_file_tool:
            tool_name = getattr(_inspect_file_tool, "name", "inspect_file")
            if tool_name not in tool_names_before:
                print("➕ [强制添加] inspect_file 工具")
                _cached_tools.append(_inspect_file_tool)
            else:
                print("ℹ️ inspect_file 工具已存在于 MCP 工具列表中")
        else:
            print("⚠️ inspect_file 工具未导入，无法添加")
        
        # 强制添加 analyze_dataframe
        if _analyze_dataframe_tool:
            tool_name = getattr(_analyze_dataframe_tool, "name", "analyze_dataframe")
            if tool_name not in tool_names_before:
                print("➕ [强制添加] analyze_dataframe 工具")
                _cached_tools.append(_analyze_dataframe_tool)
            else:
                print("ℹ️ analyze_dataframe 工具已存在于 MCP 工具列表中")
        else:
            print("⚠️ analyze_dataframe 工具未导入，无法添加")
        
        # 🔥 添加语义层工具
        from langchain_core.tools import StructuredTool

        semantic_tools = [
            StructuredTool.from_function(
                func=resolve_business_term,
                name="resolve_business_term",
                description="解析业务术语（如'总收入'、'销售额'），返回语义层定义。输入: 术语名称，输出: JSON格式的度量定义",
            ),
            StructuredTool.from_function(
                func=get_semantic_measure,
                name="get_semantic_measure",
                description="获取指定 Cube 的度量详情。输入: cube名称和度量名称，输出: 完整度量定义",
            ),
            StructuredTool.from_function(
                func=list_available_cubes,
                name="list_available_cubes",
                description="列出所有可用的语义层 Cube（如 Orders、Customers、Products）",
            ),
            StructuredTool.from_function(
                func=get_cube_measures,
                name="get_cube_measures",
                description="获取指定 Cube 的所有度量。输入: cube名称，输出: 度量列表",
            ),
            StructuredTool.from_function(
                func=normalize_status_value,
                name="normalize_status_value",
                description="规范化状态值（如'已完成'→'completed'）",
            ),
        ]

        # 将语义层工具添加到工具列表
        _cached_tools.extend(semantic_tools)
        print(f"✅ 已添加 {len(semantic_tools)} 个语义层工具")

        # 添加表推荐工具
        if TABLE_RECOMMENDATION_TOOLS_AVAILABLE:
            table_recommendation_tools = [
                StructuredTool.from_function(
                    func=get_recommended_tables_for_query,
                    name="get_recommended_tables",
                    description="🎯 智能表推荐工具 - 基于查询内容推荐最相关的数据表。输入: 用户查询字符串，输出: 推荐表列表及理由",
                ),
                StructuredTool.from_function(
                    func=get_table_description_by_name,
                    name="get_table_description",
                    description="获取指定表的详细描述信息。输入: 表名，输出: 表的详细描述、推荐用途、包含的列等",
                ),
            ]
            _cached_tools.extend(table_recommendation_tools)
            print(f"✅ 已添加 {len(table_recommendation_tools)} 个表推荐工具")
        else:
            print("⚠️  表推荐工具未可用，跳过注册")

        # 最终验证
        final_tool_count = len(_cached_tools)
        final_tool_names = [getattr(t, "name", str(t)) for t in _cached_tools]
        semantic_tool_names = [getattr(t, "name", str(t)) for t in semantic_tools]
        print(f"\n{'='*60}")
        print(f"✅ FORCED REGISTRATION: 最终工具列表包含 {final_tool_count} 个工具")
        print(f"   工具名称: {', '.join(final_tool_names)}")
        print(f"   - inspect_file: {'✅' if 'inspect_file' in final_tool_names else '❌'}")
        print(f"   - analyze_dataframe: {'✅' if 'analyze_dataframe' in final_tool_names else '❌'}")
        print(f"   - 语义层工具: {', '.join(semantic_tool_names)}")
        print(f"{'='*60}\n")

    except FileNotFoundError as e:
        error_message = str(e)
        print(
            f"❌ MCP 工具初始化失败：命令未找到\n"
            f"   错误信息: {error_message}\n"
            f"   可能原因: Node.js/npm 未安装或不在 PATH 中\n"
            f"   解决方案: 安装 Node.js 或设置 DISABLE_MCP_TOOLS=true"
        )
        raise RuntimeError(
            f"MCP initialization failed: command not found. "
            f"Error: {error_message}. "
            f"Install Node.js or set DISABLE_MCP_TOOLS=true"
        ) from e
    except Exception as e:
        print(f"❌ MCP 工具加载失败: {e}")
        raise

    # 创建 LLM
    llm = create_llm()
    llm_with_tools = llm.bind_tools(_cached_tools)

    # 获取数据库特定的系统提示词
    system_prompt = get_system_prompt(db_type)

    # 🔴🔴🔴 图表拆分关键词检测（用于强制工具调用）
    CHART_SPLIT_KEYWORDS = ["分开", "拆分", "分别显示", "单独展示", "单独显示", "各自显示", "拆成"]

    # 🔴🔴🔴 图表合并关键词检测（用于强制工具调用）
    CHART_MERGE_KEYWORDS = ["合并", "合在一起", "放到一起", "合并在一张图", "合并到一起", "合并显示", "组合"]

    # 定义节点
    async def call_model(state: MessagesState):
        messages = state["messages"]

        # 🔧 检测是否是图表拆分或合并请求
        last_human_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg.content
                break

        is_split_request = False
        is_merge_request = False
        if last_human_message:
            is_split_request = any(keyword in str(last_human_message) for keyword in CHART_SPLIT_KEYWORDS)
            is_merge_request = any(keyword in str(last_human_message) for keyword in CHART_MERGE_KEYWORDS)

        # 如果是拆分或合并请求，增强系统提示词
        enhanced_system_prompt = system_prompt
        chart_count = None  # 🔴 必须在外层初始化，否则后续代码无法访问
        if is_split_request:
            # 🔴 检测用户是否指定了图表数量
            import re
            if last_human_message:
                # 匹配各种图表数量表达方式
                # 注意：模式顺序很重要，更具体的模式应该在前面
                number_patterns = [
                    # 直接 "拆X个" 或 "拆成X个" 或 "拆分成X个"
                    r'拆(?:分)?(?:成)?([一二三四五六七八九十\d]+)个',
                    # "分成X个"
                    r'分成([一二三四五六七八九十\d]+)个',
                    # "分[别成]X个" - 原有模式保留
                    r'分[别成]([一二三四五六七八九十\d]+)个',
                    # "分别显示X个"
                    r'分别显示([一二三四五六七八九十\d]+)个',
                    # "单独展示X个"
                    r'单独展示([一二三四五六七八九十\d]+)个',
                ]
                for pattern in number_patterns:
                    match = re.search(pattern, str(last_human_message))
                    if match:
                        num_str = match.group(1)
                        # 中文数字转阿拉伯数字
                        cn_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                                  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
                                  '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
                                  '6': 6, '7': 7, '8': 8, '9': 9, '10': 10}
                        chart_count = cn_nums.get(num_str, int(num_str) if num_str.isdigit() else None)
                        if chart_count:
                            print(f"🔍 [匹配成功] 正则模式: {pattern}, 匹配值: {num_str}, 转换结果: {chart_count}")
                            break

            chart_count_instruction = ""
            if chart_count:
                chart_count_instruction = f"""

🔴🔴🔴 **用户明确要求生成 {chart_count} 个图表！你必须生成正好 {chart_count} 个图表！**

**如何生成 {chart_count} 个图表：**
- 如果有2个指标（如订单数量、销售额），每个指标用2种图表类型（折线图+柱状图）= 4个图表
- 如果有1个指标，用{chart_count}种不同图表类型（折线图、柱状图、饼图、散点图等）
- **关键**：同一个数据可以用不同图表类型展示，这是允许的！
"""
                print(f"🔴📊 [拆分请求] 检测到用户要求 {chart_count} 个图表！原始消息: {last_human_message}")
            else:
                print(f"📊 [拆分请求] 未检测到具体图表数量。原始消息: {last_human_message}")

            enhanced_system_prompt = f"""{system_prompt}

## 🚨🚨🚴【当前请求特殊指令 - 必须执行】🚨🚨🚨

用户刚刚请求将图表拆分（说"{'或 '.join(CHART_SPLIT_KEYWORDS)}"）。{chart_count_instruction}

**你必须执行以下操作，不能只输出文本：**

1. **第1步**：调用 `query` 工具执行SQL查询获取数据
2. **第2步**：根据数据特征和用户要求，调用对应数量的图表工具
   - 时间趋势数据 → generate_line_chart（折线图）
   - 分类对比数据 → generate_bar_chart（柱状图）
   - 占比分布数据 → generate_pie_chart（饼图）
   - 同一数据可以用多种图表类型展示！

**禁止行为**：
- ❌ 只输出SQL语句而不调用 query 工具
- ❌ 只输出JSON配置而不调用图表工具
- ❌ 解释SQL而不执行
- ❌ 生成的图表数量少于用户要求！

**正确响应示例**：
```
用户说：把销售额和订单数拆成四个
你的响应：
1. 调用 query 工具执行 SQL 获取数据
2. 调用 generate_line_chart(销售额趋势)
3. 调用 generate_bar_chart(销售额对比)
4. 调用 generate_line_chart(订单数量趋势)
5. 调用 generate_bar_chart(订单数量对比)
```

现在请执行工具调用，生成用户要求数量的图表！
"""
        elif is_merge_request:
            enhanced_system_prompt = f"""{system_prompt}

## 🚨🚨🚨【当前请求特殊指令 - 图表合并】🚨🚨🚨

用户刚刚请求将图表合并（说"{'或 '.join(CHART_MERGE_KEYWORDS)}"）。

**你必须执行以下操作：**

1. **分析历史对话**：从对话历史中找出之前生成的所有图表配置
2. **提取图表数据**：提取每个图表的 xAxis、yAxis、series 等配置
3. **生成合并图表**：调用 `generate_echarts` 工具生成双Y轴合并图表

**合并规则**：
- 数值量级差异>10倍的分配到不同Y轴
- 金额类指标（销售额、收入）→ 左Y轴（yAxisIndex: 0）
- 数量类指标（订单数、人数）→ 右Y轴（yAxisIndex: 1）
- 使用不同图表类型区分（折线图表示趋势，柱状图表示数量）

**禁止行为**：
- ❌ 只输出文本说明而不生成图表
- ❌ 要求用户手动选择图表
- ❌ 解释如何合并而不实际执行

**正确响应示例**：
```
用户说：把它们合并在一起
你的响应：
1. 从历史中提取之前生成的图表配置
2. 调用 generate_echarts 工具，传入合并后的双Y轴图表配置
```

**输出格式**：必须使用 [CHART_START]...[CHART_END] 格式输出完整的图表配置。

现在请执行工具调用生成合并图表！
"""

        # 🔧 优化上下文窗口：根据请求类型限制历史消息数量
        # 这有助于提高 LLM 对重要信息的关注度，避免被过多历史干扰
        MAX_CONTEXT_MESSAGES = 20  # 默认保留最近20条消息
        if is_merge_request:
            # 合并请求需要更多上下文来查找之前的图表配置
            MAX_CONTEXT_MESSAGES = 30
            print(f"📊 [合并请求] 扩展上下文窗口到 {MAX_CONTEXT_MESSAGES} 条消息")
        elif is_split_request:
            # 拆分请求需要中等上下文
            MAX_CONTEXT_MESSAGES = 15
            print(f"📊 [拆分请求] 设置上下文窗口到 {MAX_CONTEXT_MESSAGES} 条消息")

        # 截断历史消息，保留最近的消息（但保留系统消息）
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

        if len(other_messages) > MAX_CONTEXT_MESSAGES:
            print(f"📊 [上下文优化] 原始消息数: {len(other_messages)}, 截断到: {MAX_CONTEXT_MESSAGES}")
            # 🔧 智能截断：保留 AIMessage-ToolMessage 配对关系
            # 从后往前扫描，确保每条 AIMessage 后面有完整的 ToolMessage 响应
            from langchain_core.messages import AIMessage
            selected_messages = []
            tool_call_ids_to_include = set()

            # 首先找到最近的 MAX_CONTEXT_MESSAGES 条消息
            temp_selected = other_messages[-MAX_CONTEXT_MESSAGES:]

            # 从后往前扫描，找出所有需要保留的 tool_call_id
            for msg in reversed(temp_selected):
                selected_messages.insert(0, msg)
                if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 记录这个 AIMessage 的所有 tool_call_id
                    for tc in msg.tool_calls:
                        tool_call_ids_to_include.add(tc.get('id', ''))

            # 🔥 关键修复：检查 selected_messages 中是否有 ToolMessage 的 tool_call_id
            # 不在 tool_call_ids_to_include 中，如果是的话，这表示截断破坏了配对
            # 需要找到完整的消息组重新构建
            clean_messages = []
            pending_tool_calls = {}  # tool_call_id -> AIMessage

            for msg in selected_messages:
                if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 记录待匹配的工具调用
                    for tc in msg.tool_calls:
                        pending_tool_calls[tc.get('id', '')] = msg
                    clean_messages.append(msg)
                elif isinstance(msg, ToolMessage):
                    # 检查这个 ToolMessage 是否有对应的 AIMessage
                    if msg.tool_call_id in pending_tool_calls:
                        clean_messages.append(msg)
                        del pending_tool_calls[msg.tool_call_id]
                    # 如果 ToolMessage 的 tool_call_id 不在 pending_tool_calls 中，
                    # 说明它的 AIMessage 被截断了，这个 ToolMessage 也要跳过
                else:
                    clean_messages.append(msg)

            other_messages = clean_messages
            messages = system_messages + other_messages

        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=enhanced_system_prompt)] + messages
            print("📝 [系统提示词] 添加新的系统消息")
        elif is_split_request or is_merge_request:
            # 替换已有的系统消息
            old_system_count = len([m for m in messages if isinstance(m, SystemMessage)])
            messages = [SystemMessage(content=enhanced_system_prompt)] + [m for m in messages if not isinstance(m, SystemMessage)]
            print(f"📝 [系统提示词] 替换系统消息 (原有: {old_system_count} 个)")
            # 打印增强提示词的关键部分用于调试
            if chart_count:
                print(f"📝 [增强提示词] 包含图表数量指令: {chart_count} 个图表")
            else:
                print("📝 [增强提示词] 包含拆分指令 (无具体数量)")

        # 🔧 标准化消息内容：将 ToolMessage 的 list 格式转换为 string
        # MCP 服务器返回的 ToolMessage.content 可能是 list 格式
        # 但 LLM API 只接受 string 格式
        normalized_messages = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and isinstance(msg.content, list):
                # 提取 list 中的 text 内容
                text_parts = []
                image_count = 0
                for item in msg.content:
                    if isinstance(item, dict):
                        item_type = item.get('type', '')
                        if item_type == 'image':
                            # 图表成功生成，记录但不包含完整 base64 数据
                            image_count += 1
                            text_parts.append(f"[图表已生成: image/{item.get('id', 'unknown')}]")
                        else:
                            text = item.get('text', '')
                            if text:
                                # 截断过长的文本
                                if len(text) > 10000:
                                    text = text[:10000] + "...[内容过长已截断]"
                                text_parts.append(text)
                    elif isinstance(item, str):
                        if len(item) > 10000:
                            item = item[:10000] + "...[内容过长已截断]"
                        text_parts.append(item)
                # 创建新的 ToolMessage，content 为字符串
                from langchain_core.messages import ToolMessage as TM
                normalized_content = '\n'.join(text_parts) if text_parts else f"[工具返回了 {image_count} 个图像]"
                normalized_messages.append(TM(content=normalized_content, tool_call_id=msg.tool_call_id))
            else:
                normalized_messages.append(msg)
        messages = normalized_messages

        # 🔧 [修复1] 消息清理逻辑：过滤未完成的 tool_calls
        # 确保 LLM 收到的消息序列符合规范：AIMessage 的 tool_calls 必须有对应的 ToolMessage
        from langchain_core.messages import AIMessage as LC_AIMessage, ToolMessage as LC_ToolMessage

        # 第一遍：收集所有待处理的 tool_call_id
        pending_tool_calls = set()
        for msg in messages:
            if isinstance(msg, LC_AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                    if tc_id:
                        pending_tool_calls.add(tc_id)

        # 第二遍：检查 ToolMessage 是否响应了这些 tool_calls
        for msg in messages:
            if isinstance(msg, LC_ToolMessage):
                tool_call_id = msg.tool_call_id
                if tool_call_id in pending_tool_calls:
                    pending_tool_calls.remove(tool_call_id)

        # 第三遍：创建清理后的消息
        if pending_tool_calls:
            print(f"🔧 [消息清理] 发现 {len(pending_tool_calls)} 个未完成的 tool_calls，将被过滤")
            cleaned_messages = []
            for msg in messages:
                if isinstance(msg, LC_AIMessage) and msg.tool_calls:
                    # 只保留有对应 ToolMessage 的 tool_calls
                    valid_tool_calls = []
                    for tc in msg.tool_calls:
                        tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                        if tc_id and tc_id not in pending_tool_calls:
                            valid_tool_calls.append(tc)

                    if valid_tool_calls:
                        # 复制消息并只保留有效的 tool_calls
                        cleaned_messages.append(LC_AIMessage(
                            content=msg.content,
                            tool_calls=valid_tool_calls,
                            additional_kwargs=getattr(msg, 'additional_kwargs', {})
                        ))
                    else:
                        # 如果没有有效的 tool_calls，保留消息但移除 tool_calls
                        cleaned_messages.append(LC_AIMessage(content=msg.content))
                        print("🔧 [消息清理] AIMessage 的所有 tool_calls 被移除")
                else:
                    cleaned_messages.append(msg)
            messages = cleaned_messages
        else:
            print("🔧 [消息清理] 所有 tool_calls 均有效，无需清理")

        response = await llm_with_tools.ainvoke(messages)

        # 🔧 时间聚合修正：年度/月份趋势必须按月分组
        if getattr(response, "tool_calls", None):
            try:
                response.tool_calls = apply_time_aggregation_fix_to_tool_calls_v2(
                    list(response.tool_calls),
                    str(last_human_message or "")
                )
            except Exception as e:
                print(f"⚠️ [时间聚合修正失败] {e}")

        # 🔴 记录工具调用数量
        if response.tool_calls:
            tool_names = [tc.get('name') for tc in response.tool_calls]
            chart_tools = [t for t in tool_names if 'chart' in t.lower()]
            print(f"🔧 [工具调用] 总计: {len(response.tool_calls)} 个, 图表工具: {len(chart_tools)} 个 -> {chart_tools}")
            if is_split_request and chart_count:
                if len(chart_tools) < chart_count:
                    print(f"⚠️ [警告] 用户要求 {chart_count} 个图表，但 LLM 只调用了 {len(chart_tools)} 个图表工具！")
        else:
            print("🔧 [工具调用] 本次 LLM 调用没有工具调用")

        # 🔧 如果是拆分请求但LLM没有调用工具，强制提取SQL并创建工具调用
        if is_split_request and not response.tool_calls:
            print("🔴 检测到拆分请求但LLM未调用工具，尝试提取SQL强制执行...")
            content = response.content or ""

            # 尝试提取SQL（使用正则表达式）
            import re
            sql_pattern = r'```sql\s*([\s\S]*?)\s*```'
            sql_matches = re.findall(sql_pattern, str(content))

            if sql_matches:
                extracted_sql = sql_matches[0].strip()
                print(f"✅ 提取到SQL: {extracted_sql[:100]}...")

                # 验证SQL安全性（获取用户查询以支持占比查询检测）
                user_query_for_validation = ""
                for msg in messages:
                    if isinstance(msg, HumanMessage):
                        user_query_for_validation = str(msg.content)
                        break
                is_safe, error_msg = SQLValidator.validate(extracted_sql, user_query_for_validation)
                if not is_safe:
                    print(f"❌ 提取的SQL不安全: {error_msg}")
                    return {"messages": [response]}

                # 创建强制工具调用
                import uuid

                # 🔧 使用 LangChain 标准的工具调用格式
                # 必须包含所有必需字段：name, args, id, type
                forced_tool_call = {
                    "name": "query",
                    "args": {"sql": extracted_sql},
                    "id": str(uuid.uuid4()),
                    "type": "tool_call"  # 🔴 必需字段，用于 LangChain 识别
                }

                # 🔴 创建新的响应，带有工具调用和明确的后续指令
                from langchain_core.messages import AIMessage

                # 🔴🔴🔴 关键修复：在 content 中明确告诉 LLM 在看到查询结果后要做什么
                # 这样当查询结果返回时，LLM 会继续调用图表工具
                forced_instruction = f"""好的，我来执行查询拆分图表。

**【重要】查询执行后，你必须：**

1. 分析查询结果中的数据
2. 根据数据特征，为每个指标调用**单独的图表工具**：
   - 时间趋势数据 → 调用 `generate_line_chart`
   - 分类对比数据 → 调用 `generate_bar_chart`
   - 占比分布数据 → 调用 `generate_pie_chart`

3. **必须调用工具生成图表**，不要只解释数据！

执行SQL：
```sql
{extracted_sql}
```
"""
                enhanced_response = AIMessage(
                    content=forced_instruction,
                    tool_calls=[forced_tool_call]
                )
                print("🔧 已创建强制工具调用，包含明确的后续指令")
                print(f"   工具调用格式: {forced_tool_call}")
                return {"messages": [enhanced_response]}
            else:
                print("⚠️ 未能从响应中提取SQL")

        return {"messages": [response]}

    def should_continue(state: MessagesState) -> Literal["tools", "agent", END]:
        """
        增强的路由逻辑：
        - 检测工具错误并路由回 Agent 进行自我修正
        - 检测 SQL 安全问题并阻止执行
        - 限制修复次数防止无限循环
        - 🔥 修复：强制工具执行后回到 agent 节点生成最终分析答案
        """
        messages = state["messages"]
        last_message = messages[-1]

        # 新增: 检查修复次数，防止无限循环
        tool_message_count = sum(1 for m in messages if isinstance(m, ToolMessage))
        if tool_message_count > 10:  # 增加到10次以支持双轴图等复杂场景
            print(f"⚠️ 达到最大工具调用次数限制 ({tool_message_count})，结束执行")
            return END

        # A. 检查工具执行结果是否出错（ToolMessage 返回错误时路由回 Agent 修复）
        if isinstance(last_message, ToolMessage):
            content_str = str(last_message.content).lower()
            # 常见的 SQL/数据库错误关键词
            error_indicators = [
                "error", "exception", "failed", "invalid",
                "relation does not exist", "column does not exist",
                "syntax error", "permission denied", "does not exist",
                "no such table", "undefined column", "ambiguous column",
                # DuckDB 类型不匹配错误 (如 SUBSTRING 用于 TIMESTAMP 列)
                "no function matches", "argument types", "binder error",
                "cannot be applied to", "type mismatch"
            ]
            for indicator in error_indicators:
                if indicator in content_str:
                    # 新增: 如果已经多次修复仍然出错，直接结束
                    if tool_message_count >= 3:
                        print(f"❌ 修复次数已达上限 ({tool_message_count})，停止尝试")
                        return END
                    print("🚨 检测到工具执行错误，路由回 Agent 进行自我修正...")
                    return "agent"

            # 🔥 核心修复：工具执行成功后，强制回到 agent 让 LLM 生成最终分析答案
            # 这解决了"工具调用后只返回原始数据而不生成分析文本"的问题
            if tool_message_count < 5:  # 确保不会无限循环
                print("✅ 工具执行完成，路由回 Agent 生成最终分析答案...")
                return "agent"

        # B. 检查 AI 是否要调用工具
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            # 🔒 SQL 安全拦截：在工具执行前校验 SQL（使用独立的 SQLValidator 模块）
            # 获取用户查询以支持占比查询检测
            user_query_for_validation = ""
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    user_query_for_validation = str(msg.content)
                    break
            for tc in last_message.tool_calls:
                if tc.get('name') in ('query', 'execute_query'):
                    sql = tc.get('args', {}).get('sql', '')
                    # 🔧 SQL 安全校验（传入 user_query 以支持占比查询检测）
                    is_safe, error_msg = SQLValidator.validate(sql, user_query_for_validation)
                    if not is_safe:
                        # 记录被拦截的 SQL（截断以保护日志）
                        sanitized_sql = SQLValidator.sanitize_for_logging(sql, 100)
                        print(f"🛑 SQL 安全拦截: {error_msg}")
                        print(f"   被拦截的 SQL: {sanitized_sql}")
                        # 注意：这里返回 "tools" 让 SafeToolNode 处理，它会返回错误消息给 Agent
                        # 这样 Agent 可以看到错误并尝试修正
            return "tools"

        # 🔥 新增：如果最后一条消息是 AIMessage 但没有有意义的 content，继续生成
        if isinstance(last_message, AIMessage):
            content = last_message.content
            # 检查是否没有 content 或 content 太短（少于20个字符）
            if not content or len(content.strip()) < 20:
                print(f"⚠️ AIMessage 没有有意义的 content (长度: {len(content) if content else 0})，需要继续生成...")
                # 但要避免无限循环，检查前面是否已经有多次尝试
                empty_content_count = sum(
                    1 for m in messages
                    if isinstance(m, AIMessage) and (not m.content or len(m.content.strip()) < 20)
                )
                if empty_content_count < 3:  # 最多允许3次空内容尝试
                    return "agent"
                else:
                    print(f"❌ 空内容尝试次数已达上限 ({empty_content_count})，结束执行")

        return END

    # 🔒 创建带安全校验的工具节点（使用独立的 SQLValidator 模块）
    class SafeToolNode:
        """
        带 SQL 安全校验和优化的工具节点包装器

        功能：
        1. 拦截危险 SQL（DML/DDL 操作）
        2. 自动优化占比类查询的单次 COUNT 模式为 GROUP BY 查询

        当 Agent 尝试执行危险 SQL 时，不会真正执行，
        而是返回一个错误消息，让 Agent 有机会修正并重试。
        """
        def __init__(self, tools):
            self._tool_node = ToolNode(tools)

        def _optimize_proportion_query(self, query: str, user_query: str) -> str:
            """
            检测占比类查询的单次 COUNT 模式，自动转换为 GROUP BY 查询

            检测条件：
            1. 用户问题包含"占比"、"比例"、"分布"、"多少"等关键词
            2. SQL 是 SELECT COUNT(*) FROM table WHERE single_condition
            3. WHERE 条件是简单的等值比较或 LIKE

            返回优化后的 GROUP BY 查询
            """
            import re

            # 检测占比类关键词
            proportion_keywords = ['占比', '比例', '分布', '多少', '百分比', '客户占比']
            is_proportion_question = any(kw in user_query for kw in proportion_keywords)

            if not is_proportion_question:
                return query

            # 检测 SQL 模式：SELECT COUNT(*) FROM table WHERE condition
            # 支持多种 COUNT 格式: COUNT(*), COUNT( * ), COUNT(column)
            count_pattern = r"SELECT\s+COUNT\s*\(\s*(\*|\w+)\s*\)\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s*(?:=|LIKE)\s*([^\s;]+)"
            match = re.match(count_pattern, query, re.IGNORECASE)

            if match:
                table_name = match.group(2)
                column_name = match.group(3)
                value_match = match.group(4)

                # 解析目标值（去除引号）
                target_value = value_match.strip("'\"")

                # 生成优化的 GROUP BY 查询
                if 'LIKE' in query.upper():
                    # 地址类型查询，使用 CASE WHEN 分类
                    optimized = f'''SELECT
    CASE
        WHEN {column_name} LIKE '%{target_value}%' THEN '{target_value}'
        WHEN {column_name} LIKE '%北京%' THEN '北京'
        WHEN {column_name} LIKE '%上海%' THEN '上海'
        WHEN {column_name} LIKE '%深圳%' THEN '深圳'
        WHEN {column_name} LIKE '%广州%' THEN '广州'
        ELSE '其他'
    END as category,
    COUNT(*) as value
FROM {table_name}
GROUP BY category;'''
                else:
                    # 简单等值查询
                    optimized = f'''SELECT
    CASE
        WHEN {column_name} = '{target_value}' THEN '{target_value}'
        ELSE '其他'
    END as category,
    COUNT(*) as value
FROM {table_name}
GROUP BY category;'''

                logger.info("[SQL优化] 检测到占比类单次COUNT查询，自动转换为GROUP BY")
                logger.info(f"  原始SQL: {query[:100]}...")
                logger.info(f"  优化SQL: {optimized[:100]}...")
                return optimized

            return query

        async def __call__(self, state: MessagesState):
            messages = state["messages"]
            last_message = messages[-1]

            # 🔧 提取原始用户查询用于趋势查询检测和占比查询优化
            user_query = ""
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    user_query = str(msg.content)
                    break

            # 在执行 query 工具前进行安全校验和优化
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                for tc in last_message.tool_calls:
                    if tc.get('name') in ('query', 'execute_query'):
                        sql = tc.get('args', {}).get('sql', '')

                        # 🔧 核心修复：占比类查询自动优化
                        optimized_sql = self._optimize_proportion_query(sql, user_query)
                        if optimized_sql != sql:
                            # 需要修改 tool_call 中的 SQL
                            # 由于 tool_call 是不可变的，我们需要创建新的工具调用
                            new_tool_calls = []
                            for original_tc in last_message.tool_calls:
                                if original_tc.get('name') in ('query', 'execute_query'):
                                    # 创建修改后的工具调用参数
                                    new_args = dict(original_tc.get('args', {}))
                                    new_args['sql'] = optimized_sql
                                    new_tool_calls.append({
                                        'name': original_tc.get('name'),
                                        'args': new_args,
                                        'id': original_tc.get('id', ''),
                                        'type': original_tc.get('type', 'tool_call')
                                    })
                                else:
                                    # 其他工具调用保持不变
                                    new_tool_calls.append(dict(original_tc))

                            # 创建带有修改后工具调用的新 AIMessage
                            modified_message = AIMessage(
                                content=last_message.content,
                                tool_calls=new_tool_calls
                            )
                            # 用修改后的消息替换原消息
                            state["messages"] = list(messages[:-1]) + [modified_message]
                            # 重新获取 last_message
                            last_message = modified_message
                            sql = optimized_sql

                        # 🔧 SQL 安全校验（传入 user_query 以支持占比查询检测）
                        is_safe, error_msg = SQLValidator.validate(sql, user_query)
                        if not is_safe:
                            # 返回一个错误消息，而不是执行危险的 SQL
                            # 这让 Agent 知道被拦截了，可以尝试生成安全的查询
                            return {
                                "messages": [
                                    ToolMessage(
                                        content=f"🚫 SQL 执行被安全系统拦截: {error_msg}\n\n"
                                                f"请只生成 SELECT 查询语句，不要尝试修改或删除数据。",
                                        tool_call_id=tc.get('id', 'unknown')
                                    )
                                ]
                            }

                        # 🔧 新增：表选择验证（地理查询专用）
                        is_table_valid, table_error_msg, suggested_sql = SQLValidator.validate_table_selection(sql, user_query)
                        if not is_table_valid:
                            # 返回一个错误消息，引导 Agent 使用正确的表
                            suggestion = f"\n\n建议使用: {suggested_sql}" if suggested_sql else ""
                            return {
                                "messages": [
                                    ToolMessage(
                                        content=f"⚠️ 表选择错误: {table_error_msg}{suggestion}\n\n"
                                                f"请修改 SQL 使用正确的表后重试。",
                                        tool_call_id=tc.get('id', 'unknown')
                                    )
                                ]
                            }

            # 安全校验通过，执行原始工具
            return await self._tool_node.ainvoke(state)

    tool_node = SafeToolNode(_cached_tools)

    # 🔧 SQL 质量检查节点（在工具执行后检查并修复SQL）
    async def sql_quality_check_node(state: MessagesState):
        """
        SQL 质量检查节点 - 在工具执行后检查 SQL 质量

        功能：
        1. 检测并修复重复的 WHERE 条件
        2. 记录质量问题供后续分析
        3. 返回修复建议给 Agent
        """
        messages = state["messages"]
        last_message = messages[-1]

        # 只检查 ToolMessage（工具执行结果）
        if not isinstance(last_message, ToolMessage):
            return {"messages": []}

        # 检查最近的 query 工具调用
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') in ('query', 'execute_query'):
                        original_sql = tc.get('args', {}).get('sql', '')

                        # 执行 SQL 质量检查
                        fixed_sql, issues = SQLQualityOptimizer.detect_and_fix_duplicate_conditions(original_sql)

                        if issues:
                            # 发现问题，返回修复建议
                            issue_summary = "\n".join(issues)
                            suggestion = f"""🔧 SQL 质量检查发现问题：

{issue_summary}

建议修复后的 SQL：
```sql
{fixed_sql}
```

请使用修复后的 SQL 重新查询。"""

                            print("🔧 [SQL质量检查] 检测到问题并已修复")
                            for issue in issues:
                                print(f"  - {issue}")

                            # 返回错误消息，让 Agent 看到并修正
                            return {
                                "messages": [
                                    ToolMessage(
                                        content=suggestion,
                                        tool_call_id=tc.get('id', 'unknown')
                                    )
                                ]
                            }

        # 没有发现问题，直接返回
        return {"messages": []}

    # ================================================================
    # 🔧 新增：企业级可信智能数据体节点
    # ================================================================

    # 创建节点实例
    planning_node = create_planning_node(enable_logging=True, min_confidence=0.6)
    reflection_node = create_reflection_node(max_retries=3, enable_logging=True)
    clarification_node = create_clarification_node(confidence_threshold=0.6, enable_logging=True)

    # Planning 节点包装
    async def planning_node_wrapper(state: MessagesState) -> Dict:
        """Planning 节点包装器"""
        return planning_node(state)

    # Reflection 节点包装
    async def reflection_node_wrapper(state: MessagesState) -> Dict:
        """Reflection 节点包装器"""
        return reflection_node(state)

    # Clarification 节点包装
    async def clarification_node_wrapper(state: MessagesState) -> Dict:
        """Clarification 节点包装器"""
        return clarification_node(state)

    # 路由函数：决定是否需要澄清
    def should_clarify(state: MessagesState) -> Literal["clarification", "agent"]:
        """检查是否需要澄清"""
        messages = state["messages"]

        # 检查是否有澄清结果
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, 'content'):
                # 检查是否是澄清消息
                if "需要澄清" in str(msg.content) or "🤔" in str(msg.content):
                    return "clarification"

        # 检查是否有执行计划中的低置信度
        if "__execution_plan__" in state:
            plan = state["__execution_plan__"]
            if plan.get("confidence", 1.0) < 0.6:
                return "clarification"

        return "agent"

    # 路由函数：决定是否重试
    def should_retry_after_reflection(state: MessagesState) -> Literal["agent", END]:
        """反思后决定是否重试或继续执行"""
        messages = state["messages"]

        # 首先检查是否已经执行了SQL查询
        has_sql_data = False
        has_chart = False  # 🔧 新增：检查是否已生成图表

        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                content = str(msg.content)
                # 检查是否是SQL查询返回的数据（有列名和行）
                if '"columns"' in content or '"rows"' in content:
                    has_sql_data = True
                    break
                # 🔧 检查是否生成了图表（image类型内容）
                if isinstance(msg.content, list):
                    for item in msg.content:
                        if isinstance(item, dict) and item.get('type') == 'image':
                            has_chart = True
                            break
                elif 'image' in content.lower() or '图表已生成' in content:
                    has_chart = True
                    break
        # 检查反思结果
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = str(msg.content)
                # 如果有错误且重试次数未超限
                if "🔄 执行失败" in content and "正在重新生成查询" in content:
                    retry_count = state.get("__retry_count__", 0)
                    if retry_count < 3:
                        return "agent"
                    return END

                if "❌ 检测到错误" in content:
                    retry_count = state.get("__retry_count__", 0)
                    if retry_count < 3:
                        return "agent"
                    return END

                # 如果执行成功但还没有SQL数据，继续执行
                if "✅ 执行成功" in content or "查询已成功执行" in content:
                    # 🔧 改进的停止条件：
                    # 1. 有图表 + 分析完整 -> 结束
                    # 2. 有SQL数据但无图表 -> 也允许结束（避免无限循环）
                    # 3. 没有SQL数据 -> 继续执行

                    analysis_length = len(content)

                    # 情况1：完美完成（图表 + 分析）
                    if has_chart and analysis_length >= 100:
                        logger.info(f"已生成图表且分析完整({analysis_length}字)，结束执行")
                        return END
                    elif has_chart:
                        logger.info(f"已生成图表但分析过短({analysis_length}字)，继续生成分析...")
                        return "agent"

                    # 情况2：有SQL数据但无图表（趋势查询可能未生成图表）
                    # 允许结束以避免无限循环，但记录日志
                    if has_sql_data:
                        if analysis_length < MIN_ANALYSIS_LENGTH:
                            logger.warning(f"有SQL数据但分析过短({analysis_length}字)，允许结束以避免循环")
                        else:
                            logger.info(f"已获取SQL查询结果且有基本分析({analysis_length}字)，结束执行")
                        return END

                    # 情况3：还没有SQL数据，继续执行
                    logger.info("工具执行成功，但还没有SQL查询结果，继续执行...")
                    return "agent"

        # 如果还没有SQL数据且没有错误，继续执行
        if not has_sql_data:
            # 检查是否有任何query工具调用
            query_called = False
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get('name') in ('query', 'execute_query'):
                            query_called = True
                            break

            if not query_called:
                logger.info("还没有执行SQL查询，继续执行...")
                return "agent"

        return END

    # 构建图
    builder = StateGraph(MessagesState)

    # 添加节点
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    builder.add_node("sql_quality_check", sql_quality_check_node)
    builder.add_node("planning", planning_node_wrapper)    # 🔧 新增：计划节点
    builder.add_node("reflection", reflection_node_wrapper)  # 🔧 新增：反思节点
    builder.add_node("clarification", clarification_node_wrapper)  # 🔧 新增：澄清节点

    # 构建边（新的工作流）
    # START → planning → [needs_clarification?] → clarification → agent → tools → reflection → [should_retry?] → agent/END
    builder.add_edge(START, "planning")
    builder.add_conditional_edges("planning", should_clarify)
    builder.add_edge("clarification", "agent")
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "reflection")  # 🔧 修改：工具执行后进入反思节点
    builder.add_conditional_edges("reflection", should_retry_after_reflection)  # 🔧 新增：反思后路由
    builder.add_edge("sql_quality_check", END)  # 🔧 修改：质量检查后结束（进入reflection处理）

    # 持久化 checkpointer
    _cached_checkpointer = MemorySaver()
    _cached_agent = builder.compile(checkpointer=_cached_checkpointer)

    print("✅ Agent 初始化完成！")
    print("📋 工作流: START → planning → clarification → agent → tools → reflection → agent/END")

    return _cached_agent, _cached_mcp_client


async def reset_agent():
    """重置 Agent 缓存（用于重新连接或配置变更）"""
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer, _cached_db_type

    # 🔥 关闭 MCP 客户端连接
    if _cached_mcp_client is not None:
        try:
            # 尝试关闭 MCP 客户端
            if hasattr(_cached_mcp_client, 'close'):
                await _cached_mcp_client.close()
            elif hasattr(_cached_mcp_client, '__aenter__'):
                # 如果是 async context manager，尝试清理
                await _cached_mcp_client.__aexit__(None, None, None)
            print("🔄 MCP 客户端已关闭")
        except Exception as e:
            print(f"⚠️ 关闭MCP客户端时出错: {e}")

    _cached_agent = None
    _cached_mcp_client = None
    _cached_tools = None
    _cached_checkpointer = None
    _cached_db_type = "postgresql"  # 重置为默认值
    print("🔄 Agent 缓存已重置")


async def run_agent(question: str, thread_id: str = "1", verbose: bool = True, db_type: str = "postgresql") -> VisualizationResponse:
    """Run the SQL Agent with a question

    Args:
        question: 用户问题
        thread_id: 会话ID
        verbose: 是否打印详细过程
        db_type: 数据库类型（postgresql, mysql, sqlite, xlsx, csv等）

    Returns:
        VisualizationResponse: 结构化的可视化响应
    """
    # 🔧 新增：设置用户查询上下文（用于地理查询智能推荐）
    if DATABASE_TOOLS_AVAILABLE:
        set_user_query_context(question)

    # 🚀 使用持久化的 Agent（传递 db_type 参数）
    agent, mcp_client = await _get_or_create_agent(db_type=db_type)

    # Run the agent
    config_dict = {"configurable": {"thread_id": thread_id}}

    if verbose:
        print(f"\n{'='*60}")
        print(f"问题: {question}")
        print(f"{'='*60}\n")

    step_count = 0
    all_messages = []  # 收集所有消息
    final_content = ""

    # 使用 stream_mode="updates" 只获取增量更新
    async for step in agent.astream(
        {"messages": [HumanMessage(content=question)]},
        config_dict,
        stream_mode="updates",
    ):
        step_count += 1

        if verbose:
            print(f"\n{'─'*60}")
            print(f"� 第 {step_count} 步")
            print(f"{'─'*60}")

        for node_name, node_output in step.items():
            if verbose:
                print(f"\n🔹 节点名称: {node_name}")

            if "messages" in node_output:
                messages = node_output["messages"]
                # 🔧 处理 LangGraph Overwrite 对象和 None 值
                if messages is not None:
                    if hasattr(messages, 'value'):
                        messages = messages.value
                    all_messages.extend(messages)  # 收集消息

                    for msg in messages:
                        if verbose:
                            print(f"  📨 消息类型: {type(msg).__name__}")

                        # 根据消息类型处理
                        if isinstance(msg, AIMessage):
                            if msg.content:
                                final_content = msg.content  # 保存最后的AI回复
                                if verbose:
                                    preview = msg.content[:200] + ('...' if len(msg.content) > 200 else '')
                                    print(f"     🤖 AI: {preview}")
                            if msg.tool_calls and verbose:
                                for tc in msg.tool_calls:
                                    print(f"     🔧 调用工具: {tc['name']}")

                        elif isinstance(msg, ToolMessage) and verbose:
                            preview = str(msg.content)[:200] + ('...' if len(str(msg.content)) > 200 else '')
                            print(f"     📦 工具返回: {preview}")

    # 构建可视化响应（异步，支持 mcp-echarts 图表生成）
    viz_response = await build_visualization_response(all_messages, str(final_content) if final_content else "", auto_generate_chart=True, user_query=question)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ 完成! 共 {step_count} 步")
        print(f"{'='*60}")
        
        # 打印结构化数据摘要
        print("\n📊 结构化数据摘要:")
        print(f"   - SQL: {viz_response.sql[:50]}..." if viz_response.sql else "   - SQL: 无")
        print(f"   - 数据行数: {viz_response.data.row_count}")
        print(f"   - 推荐图表: {viz_response.chart.chart_type.value}")
        print(f"   - 图表标题: {viz_response.chart.title or '无'}")

    # 🔧 新增：清除用户查询上下文
    if DATABASE_TOOLS_AVAILABLE:
        clear_user_query_context()

    return viz_response


# ===============================================
# 🔍 带错误追踪的包装函数（质量保证）
# ===============================================

async def run_agent_with_tracking(
    question: str,
    thread_id: str = "1",
    verbose: bool = True,
    db_type: str = "postgresql",
    context: Optional[Dict[str, Any]] = None
) -> VisualizationResponse:
    """
    带错误追踪的run_agent包装函数

    在原有run_agent基础上添加：
    - 性能监控（执行时间）
    - 错误自动记录和分类
    - 成功率统计
    - 失败案例收集

    Args:
        question: 用户问题
        thread_id: 会话ID
        verbose: 是否打印详细过程
        db_type: 数据库类型
        context: 额外上下文信息（用户ID、租户ID等）

    Returns:
        VisualizationResponse: 与run_agent相同的返回值
    """
    import time

    if not ERROR_TRACKING_ENABLED:
        # 如果错误追踪未启用，直接调用原函数
        return await run_agent(question, thread_id, verbose, db_type)

    start_time = time.time()
    response = None

    try:
        # 调用原始run_agent函数
        response = await run_agent(question, thread_id, verbose, db_type)

        # 记录成功
        elapsed = time.time() - start_time
        error_tracker.log_success(
            question=question,
            response=response.answer[:500] if response.answer else "无回复",
            context={
                **(context or {}),
                "thread_id": thread_id,
                "db_type": db_type,
                "sql": response.sql[:200] if response.sql else None,
                "chart_type": response.chart.chart_type.value if response.chart else None,
            },
            execution_time=elapsed
        )

        return response

    except Exception as e:
        # 记录错误
        elapsed = time.time() - start_time

        # 自动推断错误类别
        error_category = _categorize_error(e, question)

        log_agent_error(
            question=question,
            error=e,
            category=error_category,
            context={
                **(context or {}),
                "thread_id": thread_id,
                "db_type": db_type,
                "execution_time": elapsed,
            }
        )

        # 重新抛出异常（保持原有行为）
        raise


def _categorize_error(error: Exception, question: str) -> ErrorCategory:
    """
    根据错误类型和用户问题自动分类错误

    Args:
        error: 异常对象
        question: 用户问题

    Returns:
        ErrorCategory: 错误类别
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # 危险操作检测
    dangerous_keywords = ["drop", "delete", "update", "insert", "truncate", "alter"]
    if any(kw in question.lower() for kw in dangerous_keywords):
        return ErrorCategory.DANGEROUS_OPERATION

    # SQL注入尝试
    if "injection" in error_str or "malicious" in error_str:
        return ErrorCategory.SQL_INJECTION_ATTEMPT

    # 数据库连接问题
    if "connection" in error_str or "connect" in error_str or "timeout" in error_str:
        return ErrorCategory.DATABASE_CONNECTION

    # LLM API错误
    if "api" in error_str or "openai" in error_str or "deepseek" in error_str:
        return ErrorCategory.LLM_API_ERROR

    # Schema不存在
    if "not found" in error_str or "does not exist" in error_str or "unknown" in error_str:
        return ErrorCategory.SCHEMA_NOT_FOUND

    # 空结果
    if "empty" in error_str or "no data" in error_str or "no result" in error_str:
        return ErrorCategory.EMPTY_RESULT

    # 数据类型不匹配
    if error_type in ["ValueError", "TypeError"] or "type" in error_str:
        return ErrorCategory.DATA_TYPE_MISMATCH

    # MCP工具失败
    if "mcp" in error_str or "tool" in error_str:
        return ErrorCategory.MCP_TOOL_FAILURE

    # 模糊问题
    if len(question.strip()) < 5:
        return ErrorCategory.AMBIGUOUS_QUERY

    # 默认为未知错误
    return ErrorCategory.UNKNOWN


async def interactive_mode():
    """Run the agent in interactive mode"""
    print("\n" + "="*60)
    print("🤖 SQL Agent 交互模式（可视化版）")
    print("="*60)
    print("命令:")
    print("  exit/quit - 退出程序")
    print("  debug     - 切换调试模式")
    print("  reset     - 重置连接（如遇连接问题）")
    print("="*60)
    print("\n💡 提示: 首次查询需要初始化连接（约5-10秒），后续查询将很快！\n")

    thread_id = "interactive_session"
    verbose = False  # 默认关闭详细输出，只显示漂亮的可视化结果

    while True:
        try:
            question = input("\n📝 请输入你的问题: ").strip()

            if question.lower() in ["exit", "quit", "q"]:
                print("\n👋 再见!")
                break

            if question.lower() == "debug":
                verbose = not verbose
                print(f"\n🔧 调试模式: {'开启' if verbose else '关闭'}")
                continue

            if question.lower() == "reset":
                await reset_agent()
                continue

            if not question:
                continue

            # 计时
            import time
            start_time = time.time()

            # 运行Agent并获取结构化响应
            viz_response = await run_agent(question, thread_id, verbose=verbose)

            # 计算耗时
            elapsed = time.time() - start_time

            # 使用漂亮的可视化渲染
            if not verbose:  # 非调试模式下显示漂亮输出
                render_response(viz_response)

            print(f"\n⏱️  响应时间: {elapsed:.2f} 秒")

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            print("💡 提示: 输入 'reset' 可重置连接")


if __name__ == "__main__":
    # Validate configuration
    config.validate_config()

    # Run interactive mode
    asyncio.run(interactive_mode())


