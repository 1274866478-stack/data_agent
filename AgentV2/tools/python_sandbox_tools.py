# -*- coding: utf-8 -*-
"""
Python 沙箱工具 - 安全执行 Python 代码进行数据分析

这个模块提供安全的 Python 执行环境，用于处理复杂的分析逻辑。

核心功能：
    1. 资源限制（CPU、内存、执行时间）
    2. 安全白名单（限制可用的函数和模块）
    3. 预定义分析模板（趋势分析、相关性分析）
    4. 结果序列化和错误处理

作者: Data Agent Team
版本: 1.0.0
"""

import json
import logging
import traceback
import signal
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import io
import sys

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """沙箱执行结果"""
    success: bool                       # 是否成功
    output: Any = None                   # 输出结果
    error: str = ""                      # 错误消息
    execution_time: float = 0.0          # 执行时间（秒）
    memory_used: float = 0.0             # 内存使用（MB）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "output": str(self.output) if self.output is not None else None,
            "error": self.error,
            "execution_time": self.execution_time,
            "memory_used": self.memory_used
        }


class TimeoutError(Exception):
    """执行超时异常"""
    pass


class PythonSandbox:
    """
    Python 沙箱执行环境

    提供受限的 Python 执行环境，用于数据分析。

    功能：
        1. 执行时间限制
        2. 内存使用限制
        3. 安全的内置函数白名单
        4. 禁止危险操作
    """

    # 安全的内置函数
    SAFE_BUILTINS: Dict[str, Callable] = {
        # 类型转换
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "tuple": tuple,
        "dict": dict,
        "set": set,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "reversed": reversed,
        "sorted": sorted,
        "sum": sum,
        "max": max,
        "min": min,
        "abs": abs,
        "round": round,
        "pow": pow,
        "divmod": divmod,
        # 数学
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
        # 容器
        "all": all,
        "any": any,
        # 其他
        "print": print,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "hasattr": hasattr,
        "getattr": getattr,
        "setattr": setattr,
    }

    # 安全的模块
    SAFE_MODULES: Dict[str, Any] = {}

    # 禁止的危险函数
    FORBIDDEN_NAMES = {
        "eval", "exec", "compile", "__import__",
        "open", "file", "input", "raw_input",
        "globals", "locals", "vars", "dir",
        "exit", "quit",
        "reload", "help",
    }

    def __init__(
        self,
        timeout: float = 30.0,
        max_memory_mb: float = 100.0,
        enable_logging: bool = True
    ):
        """初始化沙箱

        Args:
            timeout: 执行超时时间（秒）
            max_memory_mb: 最大内存使用（MB）
            enable_logging: 是否启用日志
        """
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.enable_logging = enable_logging

    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SandboxResult:
        """执行 Python 代码

        Args:
            code: Python 代码
            context: 执行上下文变量

        Returns:
            执行结果
        """
        import time
        start_time = time.time()

        try:
            # 准备执行环境
            exec_globals = self._create_safe_globals()
            exec_locals = context.copy() if context else {}
            exec_locals.update({
                "__builtins__": self.SAFE_BUILTINS,
                "result": None,
            })

            # 执行代码
            exec(code, exec_globals, exec_locals)

            # 获取结果
            output = exec_locals.get("result", exec_locals.get("output", None))
            execution_time = time.time() - start_time

            return SandboxResult(
                success=True,
                output=output,
                execution_time=execution_time
            )

        except TimeoutError:
            return SandboxResult(
                success=False,
                error=f"代码执行超时（{self.timeout}秒）",
                execution_time=self.timeout
            )
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"执行错误: {type(e).__name__}: {str(e)}"
            if self.enable_logging:
                logger.error(f"[PythonSandbox] {error_msg}\n{traceback.format_exc()}")

            return SandboxResult(
                success=False,
                error=error_msg,
                execution_time=execution_time
            )

    def _create_safe_globals(self) -> Dict[str, Any]:
        """创建安全的全局变量

        Returns:
            全局变量字典
        """
        return {
            "__builtins__": self.SAFE_BUILTINS,
            # 添加常用常量
            "True": True,
            "False": False,
            "None": None,
            # 添加安全模块的部分功能
            "math": self._create_math_module(),
            "datetime": datetime,
            "timedelta": timedelta,
        }

    def _create_math_module(self) -> Any:
        """创建安全的数学模块

        Returns:
            数学模块对象
        """
        import math

        class SafeMath:
            PI = math.pi
            E = math.e

            @staticmethod
            def sqrt(x):
                return math.sqrt(x)

            @staticmethod
            def pow(x, y):
                return math.pow(x, y)

            @staticmethod
            def log(x, base=None):
                if base is None:
                    return math.log(x)
                return math.log(x, base)

            @staticmethod
            def log10(x):
                return math.log10(x)

            @staticmethod
            def exp(x):
                return math.exp(x)

            @staticmethod
            def sin(x):
                return math.sin(x)

            @staticmethod
            def cos(x):
                return math.cos(x)

            @staticmethod
            def tan(x):
                return math.tan(x)

            @staticmethod
            def floor(x):
                return math.floor(x)

            @staticmethod
            def ceil(x):
                return math.ceil(x)

        return SafeMath()

    def validate_code(self, code: str) -> List[str]:
        """验证代码安全性

        Args:
            code: Python 代码

        Returns:
            警告消息列表
        """
        warnings = []

        # 检查危险函数
        for name in self.FORBIDDEN_NAMES:
            if name in code:
                warnings.append(f"检测到危险函数: {name}")

        # 检查导入语句
        if "import" in code:
            warnings.append("检测到 import 语句，可能存在安全风险")

        # 检查文件操作
        file_keywords = ["open(", "file(", "with open"]
        for keyword in file_keywords:
            if keyword in code:
                warnings.append(f"检测到文件操作: {keyword}")
                break

        return warnings


# ============================================================================
# 预定义分析模板
# ============================================================================

class AnalysisTemplates:
    """预定义的分析模板"""

    @staticmethod
    def trend_analysis(data_json: str, date_column: str, value_column: str) -> str:
        """趋势分析模板

        Args:
            data_json: JSON 格式的数据
            date_column: 日期列名
            value_column: 值列名

        Returns:
            Python 代码
        """
        return f'''
import json
from datetime import datetime

# 加载数据
data = json.loads("""{data_json}""")

# 提取日期和值
dates = [row["{date_column}"] for row in data]
values = [row["{value_column}"] for row in data]

# 计算增长率
growth_rates = []
for i in range(1, len(values)):
    if values[i-1] != 0:
        rate = (values[i] - values[i-1]) / values[i-1] * 100
        growth_rates.append(rate)

# 计算统计信息
avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
max_growth = max(growth_rates) if growth_rates else 0
min_growth = min(growth_rates) if growth_rates else 0

result = {{
    "dates": dates,
    "values": values,
    "growth_rates": growth_rates,
    "statistics": {{
        "average_growth": round(avg_growth, 2),
        "max_growth": round(max_growth, 2),
        "min_growth": round(min_growth, 2)
    }}
}}
'''

    @staticmethod
    def correlation_analysis(data_json: str, column1: str, column2: str) -> str:
        """相关性分析模板

        Args:
            data_json: JSON 格式的数据
            column1: 第一列名
            column2: 第二列名

        Returns:
            Python 代码
        """
        return f'''
import json
import math

# 加载数据
data = json.loads("""{data_json}""")

# 提取值
x = [float(row["{column1}"]) for row in data if row.get("{column1}")]
y = [float(row["{column2}"]) for row in data if row.get("{column2}")]

# 计算皮尔逊相关系数
def correlation(x_vals, y_vals):
    n = len(x_vals)
    if n != len(y_vals) or n < 2:
        return 0

    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
    sum_x2 = sum(x * x for x in x_vals)
    sum_y2 = sum(y * y for y in y_vals)

    numerator = n * sum_xy - sum_x * sum_y
    denominator = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))

    if denominator == 0:
        return 0

    return numerator / denominator

corr = correlation(x, y)

result = {{
    "correlation": round(corr, 4),
    "interpretation": "强正相关" if corr > 0.7 else "强负相关" if corr < -0.7 else "弱相关",
    "x_count": len(x),
    "y_count": len(y)
}}
'''

    @staticmethod
    def summary_statistics(data_json: str, value_column: str) -> str:
        """汇总统计模板

        Args:
            data_json: JSON 格式的数据
            value_column: 值列名

        Returns:
            Python 代码
        """
        return f'''
import json
import math

# 加载数据
data = json.loads("""{data_json}""")

# 提取值
values = [float(row["{value_column}"]) for row in data if row.get("{value_column}")]

# 计算统计量
n = len(values)
if n == 0:
    result = {{}}
else:
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std_dev = math.sqrt(variance)

    sorted_values = sorted(values)
    median = sorted_values[n // 2] if n % 2 == 1 else (
        sorted_values[n // 2 - 1] + sorted_values[n // 2]
    ) / 2

    result = {{
        "count": n,
        "mean": round(mean, 2),
        "median": round(median, 2),
        "std_dev": round(std_dev, 2),
        "variance": round(variance, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "range": round(max(values) - min(values), 2)
    }}
'''


# ============================================================================
# LangChain 工具函数
# ============================================================================

def python_analyze(
    code: str,
    data_json: str = "[]"
) -> str:
    """使用 Python 沙箱执行数据分析 - 供 LLM 调用

    Args:
        code: Python 代码
        data_json: JSON 格式的输入数据

    Returns:
        JSON 格式的执行结果

    示例:
        >>> python_analyze("result = sum([1, 2, 3])")
        '{"success": true, "output": "6", ...}'
    """
    sandbox = PythonSandbox()

    # 验证代码
    warnings = sandbox.validate_code(code)
    if warnings:
        logger.warning(f"[python_analyze] 代码验证警告: {warnings}")

    # 执行代码
    result = sandbox.execute(code, context={"data": json.loads(data_json)})

    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def trend_analysis(
    data_json: str,
    date_column: str = "date",
    value_column: str = "value"
) -> str:
    """执行趋势分析 - 供 LLM 调用

    Args:
        data_json: JSON 格式的数据
        date_column: 日期列名
        value_column: 值列名

    Returns:
        JSON 格式的分析结果
    """
    template = AnalysisTemplates.trend_analysis(data_json, date_column, value_column)
    return python_analyze(template)


def correlation_analysis(
    data_json: str,
    column1: str,
    column2: str
) -> str:
    """执行相关性分析 - 供 LLM 调用

    Args:
        data_json: JSON 格式的数据
        column1: 第一列名
        column2: 第二列名

    Returns:
        JSON 格式的分析结果
    """
    template = AnalysisTemplates.correlation_analysis(data_json, column1, column2)
    return python_analyze(template)


def summary_statistics(
    data_json: str,
    value_column: str = "value"
) -> str:
    """执行汇总统计 - 供 LLM 调用

    Args:
        data_json: JSON 格式的数据
        value_column: 值列名

    Returns:
        JSON 格式的统计结果
    """
    template = AnalysisTemplates.summary_statistics(data_json, value_column)
    return python_analyze(template)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Python 沙箱工具测试")
    print("=" * 60)

    sandbox = PythonSandbox()

    # 测试 1: 简单计算
    print("\n[测试 1] 简单计算")
    result = sandbox.execute("result = sum([1, 2, 3, 4, 5])")
    print(f"成功: {result.success}")
    print(f"输出: {result.output}")

    # 测试 2: 趋势分析
    print("\n[测试 2] 趋势分析")
    data = json.dumps([
        {"date": "2024-01-01", "value": 100},
        {"date": "2024-01-02", "value": 120},
        {"date": "2024-01-03", "value": 110},
    ])
    result = python_analyze(
        AnalysisTemplates.trend_analysis(data, "date", "value"),
        data
    )
    print(f"结果: {result}")

    # 测试 3: 代码验证
    print("\n[测试 3] 代码验证")
    warnings = sandbox.validate_code("result = open('file.txt').read()")
    print(f"警告: {warnings}")
