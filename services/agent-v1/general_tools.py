# -*- coding: utf-8 -*-
"""
# [GENERAL TOOLS] 通用工具模块

## [HEADER]
**文件名**: general_tools.py
**职责**: 提供不需要数据库查询的通用工具函数（日期计算、数学运算等）
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-08): 从 V2 迁移 - 简化版本，保留核心功能

## [INPUT]
### 工具函数参数
- **get_current_date()**: 无参数
- **get_current_time()**: 无参数
- **get_relative_date(days_offset)**: days_offset (int) - 天数偏移量
- **evaluate_math_expression(expression)**: expression (str) - 数学表达式

## [OUTPUT]
### 工具函数返回值
- 日期/时间字符串
- 数学计算结果
- 系统信息

## [LINK]
**上游依赖**:
- [datetime](https://docs.python.org/3/library/datetime.html) - 日期时间处理

**下游依赖**:
- [./sql_agent.py](./sql_agent.py) - 可集成到 Agent 工具列表

## [POS]
**路径**: Agent/general_tools.py
**模块层级**: Level 1（Agent根目录）
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ============================================================================
# 日期时间工具
# ============================================================================

def get_current_date() -> str:
    """
    获取当前日期

    返回当前日期的字符串表示，格式：YYYY-MM-DD

    Returns:
        当前日期字符串

    Example:
        >>> get_current_date()
        '2026-01-08'
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_current_time() -> str:
    """
    获取当前时间

    返回当前时间的字符串表示，格式：YYYY-MM-DD HH:MM:SS

    Returns:
        当前时间字符串

    Example:
        >>> get_current_time()
        '2026-01-08 14:30:45'
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_relative_date(days_offset: int) -> str:
    """
    获取相对日期

    Args:
        days_offset: 天数偏移量，负数表示过去，正数表示未来
            -1: 昨天
            0: 今天
            1: 明天

    Returns:
        日期字符串

    Example:
        >>> get_relative_date(-1)
        '2026-01-07'
        >>> get_relative_date(0)
        '2026-01-08'
        >>> get_relative_date(1)
        '2026-01-09'
    """
    target_date = datetime.now() + timedelta(days=days_offset)
    return target_date.strftime("%Y-%m-%d")


def get_date_range_info() -> str:
    """
    获取日期范围信息（昨天、今天、明天）

    返回包含昨天、今天、明天日期的格式化信息

    Returns:
        日期范围信息字符串

    Example:
        >>> get_date_range_info()
        '昨天: 2026-01-07\\n今天: 2026-01-08\\n明天: 2026-01-09'
    """
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    return f"""昨天: {yesterday.strftime('%Y-%m-%d')}
今天: {today.strftime('%Y-%m-%d')}
明天: {tomorrow.strftime('%Y-%m-%d')}"""


def get_week_info() -> str:
    """
    获取本周信息

    Returns:
        本周日期范围信息
    """
    now = datetime.now()
    # 假设周一为一周的开始
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)

    return f"""本周: {monday.strftime('%Y-%m-%d')} 至 {sunday.strftime('%Y-%m-%d')}
周一是: {monday.strftime('%Y-%m-%d')}
周日是: {sunday.strftime('%Y-%m-%d')}"""


def get_month_info() -> str:
    """
    获取本月信息

    Returns:
        本月日期范围信息
    """
    now = datetime.now()
    first_day = now.replace(day=1)
    # 获取下个月第一天，再减一天得到本月最后一天
    if now.month == 12:
        next_month_first = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month_first = now.replace(month=now.month + 1, day=1)
    last_day = next_month_first - timedelta(days=1)

    return f"""本月: {first_day.strftime('%Y-%m')} ({first_day.strftime('%Y-%m-%d')} 至 {last_day.strftime('%Y-%m-%d')})
本月第一天: {first_day.strftime('%Y-%m-%d')}
本月最后一天: {last_day.strftime('%Y-%m-%d')}"""


# ============================================================================
# 数学计算工具
# ============================================================================

def evaluate_math_expression(expression: str) -> str:
    """
    计算简单的数学表达式

    Args:
        expression: 数学表达式，如 "2 + 2", "10 * 5"

    Returns:
        计算结果字符串

    Example:
        >>> evaluate_math_expression("2 + 2")
        '4'
    """
    try:
        # 只允许安全的数学运算
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "错误：表达式包含非法字符"

        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"


# ============================================================================
# 系统信息工具
# ============================================================================

def get_system_info() -> str:
    """
    获取系统信息

    Returns:
        系统信息字符串

    Example:
        >>> get_system_info()
        '当前时间: 2026-01-08 14:30:45\\n时区: 本地时间'
    """
    import platform
    import sys

    info = [
        f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Python版本: {sys.version.split()[0]}",
        f"操作系统: {platform.system()} {platform.release()}",
    ]
    return "\n".join(info)


# ============================================================================
# LangChain 工具集成
# ============================================================================

def get_general_tools():
    """
    获取通用工具列表（用于集成到 Agent）

    Returns:
        LangChain StructuredTool 列表
    """
    try:
        from langchain_core.tools import StructuredTool

        return [
            StructuredTool.from_function(
                func=get_date_range_info,
                name="get_date_range_info",
                description=(
                    "获取昨天、今天、明天的日期信息。"
                    "用于回答关于日期的简单查询，如'昨天的日期是什么'、'今天是几号'等。"
                    "Args: 无需参数"
                )
            ),
            StructuredTool.from_function(
                func=get_current_date,
                name="get_current_date",
                description=(
                    "获取当前日期（今天）。"
                    "返回格式：YYYY-MM-DD。"
                    "Args: 无需参数"
                )
            ),
            StructuredTool.from_function(
                func=get_current_time,
                name="get_current_time",
                description=(
                    "获取当前时间。"
                    "返回格式：YYYY-MM-DD HH:MM:SS。"
                    "Args: 无需参数"
                )
            ),
            StructuredTool.from_function(
                func=lambda days: get_relative_date(int(days)),
                name="get_relative_date",
                description=(
                    "获取相对日期（昨天、明天等）。"
                    "Args: days_offset (int) - 天数偏移量，-1表示昨天，0表示今天，1表示明天"
                )
            ),
            StructuredTool.from_function(
                func=get_week_info,
                name="get_week_info",
                description=(
                    "获取本周的日期范围信息（周一到周日）。"
                    "Args: 无需参数"
                )
            ),
            StructuredTool.from_function(
                func=get_month_info,
                name="get_month_info",
                description=(
                    "获取本月的日期范围信息（月初到月末）。"
                    "Args: 无需参数"
                )
            ),
        ]
    except ImportError:
        logger.warning("[general_tools] langchain_core 未安装，无法返回 StructuredTool")
        return []


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("通用工具测试")
    print("=" * 60)

    print("\n[Test 1] 获取日期范围信息")
    print(get_date_range_info())

    print("\n[Test 2] 获取当前日期")
    print(get_current_date())

    print("\n[Test 3] 获取当前时间")
    print(get_current_time())

    print("\n[Test 4] 获取相对日期")
    print(f"昨天: {get_relative_date(-1)}")
    print(f"今天: {get_relative_date(0)}")
    print(f"明天: {get_relative_date(1)}")
    print(f"7天后: {get_relative_date(7)}")

    print("\n[Test 5] 获取本周信息")
    print(get_week_info())

    print("\n[Test 6] 获取本月信息")
    print(get_month_info())

    print("\n[Test 7] 获取系统信息")
    print(get_system_info())

    print("\n[Test 8] 数学计算")
    print(f"2 + 2 = {evaluate_math_expression('2 + 2')}")
    print(f"10 * 5 = {evaluate_math_expression('10 * 5')}")
    print(f"100 / 4 = {evaluate_math_expression('100 / 4')}")
