# -*- coding: utf-8 -*-
"""
通用工具 - 处理不需要数据库的简单查询

这个模块提供了一些通用工具函数，用于处理那些不需要访问数据库的简单查询，
例如：
- 日期查询（今天、昨天、明天的日期）
- 数学计算
- 系统信息查询

作者: Data Agent Team
版本: 1.0.0
"""

import logging
import sys

# Windows GBK编码兼容
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def get_current_date() -> str:
    """
    获取当前日期

    返回当前日期的字符串表示，格式：YYYY-MM-DD

    Returns:
        当前日期字符串

    Example:
        >>> get_current_date()
        '2025-01-29'
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
        '2025-01-29 14:30:45'
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
        '2025-01-28'
        >>> get_relative_date(0)
        '2025-01-29'
        >>> get_relative_date(1)
        '2025-01-30'
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
        '昨天: 2025-01-28\\n今天: 2025-01-29\\n明天: 2025-01-30'
    """
    from datetime import datetime, timedelta

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    return f"""昨天: {yesterday.strftime('%Y-%m-%d')}
今天: {today.strftime('%Y-%m-%d')}
明天: {tomorrow.strftime('%Y-%m-%d')}"""


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


def get_system_info() -> str:
    """
    获取系统信息

    Returns:
        系统信息字符串

    Example:
        >>> get_system_info()
        '当前时间: 2025-01-29 14:30:45\\n时区: 本地时间'
    """
    import platform
    import sys

    info = [
        f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Python版本: {sys.version.split()[0]}",
        f"操作系统: {platform.system()} {platform.release()}",
    ]
    return "\n".join(info)


def get_general_tools():
    """
    获取通用工具列表（用于集成到Agent）

    Returns:
        LangChain StructuredTool 列表
    """
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
    ]


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

    print("\n[Test 5] 获取系统信息")
    print(get_system_info())
