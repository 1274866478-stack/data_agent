"""
# [DATA TRANSFORMER] SQL结果到图表数据转换模块

## [HEADER]
**文件名**: data_transformer.py
**职责**: 将SQL查询结果转换为ECharts图表数据格式 - 支持二维数组格式和MCP ECharts格式，自动推断图表类型，智能字段映射
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - SQL结果数据转换

## [INPUT]
### sql_result_to_echarts_data() 函数参数
- **sql_result: List[Dict[str, Any]]** - SQL查询返回的字典列表
- **x_field: Optional[str]** - X轴对应的字段名（可选，默认取第一列）
- **y_field: Optional[str]** - Y轴对应的字段名（可选，默认取第二列）

### sql_result_to_mcp_echarts_data() 函数参数
- **sql_result: List[Dict[str, Any]]** - SQL查询返回的字典列表
- **chart_type: str** - 图表类型（"bar", "pie", "line"等，默认"bar"）
- **x_field: Optional[str]** - X轴/分类字段名（可选）
- **y_field: Optional[str]** - Y轴/数值字段名（可选）

### infer_chart_type() 函数参数
- **sql: str** - SQL查询语句
- **data: List[Dict[str, Any]]** - 查询结果

### prepare_chart_request() 函数参数
- **sql_result: List[Dict[str, Any]]** - SQL查询结果
- **sql: str** - SQL语句
- **title: Optional[str]** - 图表标题（可选）
- **x_field: Optional[str]** - X轴字段（可选）
- **y_field: Optional[str]** - Y轴字段（可选）
- **chart_type: Optional[str]** - 图表类型（可选，不传则自动推断）

## [OUTPUT]
### sql_result_to_echarts_data() 返回值
- **Tuple[List[List[Any]], str, str]** - (data, x_field_name, y_field_name) 元组
  - data: [[x1, y1], [x2, y2], ...] 格式的二维数组
  - x_field_name: 实际使用的X字段名
  - y_field_name: 实际使用的Y字段名

### sql_result_to_mcp_echarts_data() 返回值
- **Tuple[List[Dict[str, Any]], str, str]** - (data, x_field_name, y_field_name) 元组
  - data: mcp-echarts格式（柱状图/饼图用category/value，折线图用time/value）
  - x_field_name: 实际使用的分类字段名
  - y_field_name: 实际使用的数值字段名

### infer_chart_type() 返回值
- **str** - 推荐的图表类型（"bar", "line", "pie", "table"）

### prepare_chart_request() 返回值
- **Dict[str, Any]** - 符合mcp-echarts get-chart输入格式的字典
  - type: 图表类型
  - data: 二维数组数据
  - title: 图表标题
  - seriesName: 系列名称
  - xAxisName: X轴名称
  - yAxisName: Y轴名称
  - 或 skip_chart: True（如果数据不适合图表）

## [LINK]
**上游依赖** (已读取源码):
- [python-typing](https://docs.python.org/3/library/typing.html) - 类型注解（List, Dict, Any, Tuple, Optional）

**下游依赖** (已读取源码):
- [./sql_agent.py](./sql_agent.py) - Agent主程序（使用数据转换函数）
- [./chart_service.py](./chart_service.py) - 图表服务（接收转换后的数据）

**调用方**:
- **sql_agent.py**: 在extract_tool_data()和build_visualization_response()中调用数据转换函数

## [POS]
**路径**: Agent/data_transformer.py
**模块层级**: Level 1（Agent根目录）
**依赖深度**: 无外部依赖（仅使用Python标准库）
"""
from typing import List, Dict, Any, Tuple, Optional


def sql_result_to_echarts_data(
    sql_result: List[Dict[str, Any]],
    x_field: Optional[str] = None,
    y_field: Optional[str] = None
) -> Tuple[List[List[Any]], str, str]:
    """
    将 SQL 查询结果转换为 ECharts 二维数组格式
    
    Args:
        sql_result: SQL 查询返回的字典列表
        x_field: X轴对应的字段名（可选，默认取第一列）
        y_field: Y轴对应的字段名（可选，默认取第二列）
    
    Returns:
        (data, x_field_name, y_field_name) 元组
        - data: [[x1, y1], [x2, y2], ...] 格式的数据
        - x_field_name: 实际使用的 X 字段名
        - y_field_name: 实际使用的 Y 字段名
    
    Example:
        >>> result = [{"name": "Alice", "score": 95}, {"name": "Bob", "score": 87}]
        >>> data, x, y = sql_result_to_echarts_data(result, "name", "score")
        >>> print(data)  # [["Alice", 95], ["Bob", 87]]
    """
    if not sql_result:
        return [], "", ""
    
    # 获取所有列名
    columns = list(sql_result[0].keys())
    
    if len(columns) < 2:
        # 只有一列，无法生成图表
        return [], columns[0] if columns else "", ""
    
    # 确定 X 和 Y 字段
    if x_field and x_field in columns:
        actual_x = x_field
    else:
        actual_x = columns[0]  # 默认第一列
    
    if y_field and y_field in columns:
        actual_y = y_field
    else:
        # 默认第二列，但如果第一列已被用作 X，则取第二列
        remaining = [c for c in columns if c != actual_x]
        actual_y = remaining[0] if remaining else columns[1]
    
    # 转换数据
    data = []
    for row in sql_result:
        x_val = row.get(actual_x, "")
        y_val = row.get(actual_y, 0)
        
        # 确保 Y 值是数值类型
        try:
            y_val = float(y_val) if y_val is not None else 0
        except (ValueError, TypeError):
            y_val = 0
        
        data.append([x_val, y_val])
    
    return data, actual_x, actual_y


def sql_result_to_mcp_echarts_data(
    sql_result: List[Dict[str, Any]],
    chart_type: str = "bar",
    x_field: Optional[str] = None,
    y_field: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str, str]:
    """
    将 SQL 查询结果转换为 mcp-echarts 需要的格式

    Args:
        sql_result: SQL 查询返回的字典列表
        chart_type: 图表类型 ("bar", "pie", "line" 等)
        x_field: X轴/分类字段名（可选）
        y_field: Y轴/数值字段名（可选）

    Returns:
        (data, x_field_name, y_field_name) 元组
        - data: mcp-echarts 格式的数据
        - x_field_name: 实际使用的分类字段名
        - y_field_name: 实际使用的数值字段名

    Example:
        >>> result = [{"department": "技术部", "count": 45}]
        >>> data, x, y = sql_result_to_mcp_echarts_data(result, "bar")
        >>> print(data)  # [{"category": "技术部", "value": 45}]
    """
    if not sql_result:
        return [], "", ""

    # 获取所有列名
    columns = list(sql_result[0].keys())

    if len(columns) < 2:
        return [], columns[0] if columns else "", ""

    # 确定分类字段和数值字段
    if x_field and x_field in columns:
        actual_x = x_field
    else:
        actual_x = columns[0]

    if y_field and y_field in columns:
        actual_y = y_field
    else:
        remaining = [c for c in columns if c != actual_x]
        actual_y = remaining[0] if remaining else columns[1]

    # 根据图表类型转换数据格式
    data = []
    for row in sql_result:
        x_val = row.get(actual_x, "")
        y_val = row.get(actual_y, 0)

        # 确保数值类型
        try:
            y_val = float(y_val) if y_val is not None else 0
        except (ValueError, TypeError):
            y_val = 0

        if chart_type == "line":
            # 折线图使用 time/value 格式
            data.append({"time": str(x_val), "value": y_val})
        else:
            # 柱状图、饼图等使用 category/value 格式
            data.append({"category": str(x_val), "value": y_val})

    return data, actual_x, actual_y


def infer_chart_type(sql: str, data: List[Dict[str, Any]]) -> str:
    """
    根据 SQL 语句和数据特征推断合适的图表类型

    Args:
        sql: SQL 查询语句
        data: 查询结果

    Returns:
        推荐的图表类型: "bar", "line", "pie", "table"
    """
    sql_lower = sql.lower()

    # 1. 检查是否是占比类查询 -> 饼图（优先级最高）
    proportion_keywords = ["占比", "比例", "百分比", "百分之", "分布", "proportion", "ratio"]
    if any(kw in sql_lower for kw in proportion_keywords):
        if "group by" in sql_lower or "case when" in sql_lower:
            return "pie"

    # 2. 检查是否有时间相关字段 -> 折线图
    time_keywords = ["date", "time", "month", "year", "day", "week", "quarter"]
    if any(kw in sql_lower for kw in time_keywords):
        if "group by" in sql_lower:
            return "line"

    # 3. 检查是否是聚合查询 -> 饼图（少量类别）或柱状图
    if "count" in sql_lower or "sum" in sql_lower:
        if data and len(data) <= 8:  # 饼图适合少量类别
            # 检查是否有 GROUP BY
            if "group by" in sql_lower:
                return "pie"

    # 4. 检查是否是分类比较 -> 柱状图
    if "group by" in sql_lower:
        return "bar"

    # 5. 默认返回表格
    return "table"


def prepare_chart_request(
    sql_result: List[Dict[str, Any]],
    sql: str,
    title: Optional[str] = None,
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    chart_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    准备 ECharts MCP 的请求参数
    
    Args:
        sql_result: SQL 查询结果
        sql: SQL 语句
        title: 图表标题（可选）
        x_field: X轴字段（可选）
        y_field: Y轴字段（可选）
        chart_type: 图表类型（可选，不传则自动推断）
    
    Returns:
        符合 mcp-echarts get-chart 输入格式的字典
    """
    # 转换数据
    data, actual_x, actual_y = sql_result_to_echarts_data(sql_result, x_field, y_field)
    
    # 推断图表类型
    if not chart_type or chart_type in ("table", "none"):
        chart_type = infer_chart_type(sql, sql_result)
    
    # 如果还是 table，就不生成图表
    if chart_type == "table":
        return {"skip_chart": True, "reason": "数据更适合表格展示"}
    
    return {
        "type": chart_type,
        "data": data,
        "title": title or "查询结果",
        "seriesName": actual_y,
        "xAxisName": actual_x,
        "yAxisName": actual_y,
    }


# ============================================================
# 多系列与双Y轴支持
# ============================================================

def should_use_dual_axis(
    data: List[Dict[str, Any]],
    columns: List[str],
    ratio_threshold: float = 10.0
) -> Dict[str, Any]:
    """
    检测数据是否需要双Y轴展示

    判断条件：
    1. 有多个数值列（>2个列，其中>1个是数值）
    2. 数值列的量级差异大（最大值/最小值 > ratio_threshold）

    Args:
        data: 查询结果数据
        columns: 列名列表
        ratio_threshold: 量级差异阈值，默认10倍

    Returns:
        {
            "need_dual": bool,         # 是否需要双Y轴
            "left_columns": List[str], # 左Y轴列名
            "right_columns": List[str],# 右Y轴列名
            "x_column": str,           # X轴列名
            "reason": str              # 原因说明
        }
    """
    if len(columns) < 3:
        return {"need_dual": False, "reason": "列数不足（需要至少3列）"}

    # 识别数值列
    numeric_columns = []
    for col in columns:
        # 检查前10行数据，判断是否为数值类型
        for row in data[:10]:
            val = row.get(col)
            if val is not None and isinstance(val, (int, float)):
                numeric_columns.append(col)
                break

    if len(numeric_columns) < 2:
        return {"need_dual": False, "reason": "数值列不足（需要至少2个数值列）"}

    # 计算每个数值列的量级
    column_max_values = {}
    for col in numeric_columns:
        values = []
        for row in data:
            val = row.get(col)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        if values:
            column_max_values[col] = max(values)

    if len(column_max_values) < 2:
        return {"need_dual": False, "reason": "有效数值列不足"}

    # 按量级排序
    sorted_cols = sorted(column_max_values.items(), key=lambda x: x[1], reverse=True)
    max_val = sorted_cols[0][1]
    min_val = sorted_cols[-1][1]

    if min_val > 0:
        ratio = max_val / min_val
        if ratio > ratio_threshold:
            # 量级差异大，需要双Y轴
            x_column = next((c for c in columns if c not in numeric_columns), columns[0])
            return {
                "need_dual": True,
                "left_columns": [sorted_cols[0][0]],      # 大量级 → 左Y轴
                "right_columns": [col for col, _ in sorted_cols[1:]],  # 小量级 → 右Y轴
                "x_column": x_column,
                "reason": f"数值量级差异{ratio:.1f}倍（{sorted_cols[0][0]}={max_val:.0f}, {sorted_cols[-1][0]}={min_val:.0f}）"
            }

    return {"need_dual": False, "reason": f"量级差异不足（当前比例{max_val/min_val if min_val>0 else 0:.1f}倍）"}


def determine_y_axis_allocation(series_data: Dict[str, List[float]]) -> Dict[str, int]:
    """
    自动分配系列到Y轴

    算法：
    1. 按关键词预分配（金额类→左Y轴，数量类→右Y轴）
    2. 按量级分配（大量级→左Y轴0，小量级→右Y轴1）

    Args:
        series_data: 系列名→数值列表的映射

    Returns:
        {系列名: Y轴索引} 的映射，0=左Y轴, 1=右Y轴
    """
    allocation = {}

    # 计算每个系列的统计信息
    stats = {}
    for name, values in series_data.items():
        valid_values = [v for v in values if v is not None]
        if valid_values:
            stats[name] = {
                "max": max(valid_values),
                "mean": sum(valid_values) / len(valid_values)
            }

    # 按关键词预分配
    left_keywords = ["金额", "价格", "销售额", "收入", "元", "$", "revenue", "sales", "amount"]
    right_keywords = ["数量", "件数", "次数", "count", "订单", "order"]

    for name in stats:
        name_lower = name.lower()
        # 优先按关键词分配
        if any(kw in name_lower for kw in left_keywords):
            allocation[name] = 0
        elif any(kw in name_lower for kw in right_keywords):
            allocation[name] = 1
        else:
            # 按量级分配：平均量>1000的放左轴，否则放右轴
            allocation[name] = 0 if stats[name]["mean"] > 1000 else 1

    return allocation


def build_multi_series_echarts_config(
    data: List[Dict[str, Any]],
    x_column: str,
    series_config: List[Dict[str, Any]],
    title: str = "数据可视化"
) -> Dict[str, Any]:
    """
    构建多系列双Y轴 ECharts 配置

    Args:
        data: 查询结果数据
        x_column: X轴字段名
        series_config: 系列配置列表
            [{"column": "sales", "yAxisIndex": 0, "type": "line", "unit": "元"}]
        title: 图表标题

    Returns:
        完整的 ECharts option 配置
    """
    # 提取X轴数据
    x_data = [str(row.get(x_column, "")) for row in data]

    # 构建系列数据
    series = []
    y_axis_names = {0: "", 1: ""}  # 记录每个Y轴的名称

    for config in series_config:
        col = config["column"]
        y_index = config.get("yAxisIndex", 0)
        chart_type = config.get("type", "line")

        # 提取系列数据
        series_data = []
        for row in data:
            val = row.get(col, 0)
            try:
                series_data.append(float(val) if val is not None else 0)
            except (ValueError, TypeError):
                series_data.append(0)

        # 记录Y轴单位
        unit = config.get("unit", "")
        if unit:
            y_axis_names[y_index] = unit

        series.append({
            "name": col,
            "type": chart_type,
            "data": series_data,
            "yAxisIndex": y_index,
            "smooth": chart_type == "line"  # 折线图平滑
        })

    # 构建Y轴配置
    has_dual_axis = any(s.get("yAxisIndex", 0) == 1 for s in series_config)
    if has_dual_axis:
        yAxis = [
            {
                "type": "value",
                "name": y_axis_names.get(0, ""),
                "position": "left",
                "axisLabel": {"formatter": "{value}"}
            },
            {
                "type": "value",
                "name": y_axis_names.get(1, ""),
                "position": "right",
                "axisLabel": {"formatter": "{value}"}
            }
        ]
    else:
        yAxis = [{"type": "value", "name": y_axis_names.get(0, "")}]

    return {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"data": [s["name"] for s in series], "top": 30},
        "xAxis": {"type": "category", "data": x_data},
        "yAxis": yAxis,
        "series": series
    }


def analyze_and_build_multi_series_chart(
    data: List[Dict[str, Any]],
    title: str = "数据分析"
) -> Dict[str, Any]:
    """
    自动分析数据并构建多系列图表配置

    这是主入口函数，自动检测是否需要双Y轴，并生成配置

    Args:
        data: SQL查询结果（字典列表）
        title: 图表标题

    Returns:
        ECharts配置字典，包含是否需要双Y轴的判断结果
    """
    if not data:
        return {"error": "数据为空"}

    columns = list(data[0].keys())

    # 检测是否需要双Y轴
    dual_check = should_use_dual_axis(data, columns)

    if not dual_check["need_dual"]:
        # 单系列，使用原有逻辑
        return {
            "is_multi_series": False,
            "reason": dual_check["reason"],
            "suggestion": "使用单系列图表"
        }

    # 需要双Y轴，构建配置
    x_column = dual_check["x_column"]

    # 构建系列配置
    series_config = []
    for col in dual_check["left_columns"]:
        series_config.append({
            "column": col,
            "type": "line",  # 大量级用折线图
            "yAxisIndex": 0,
            "unit": col
        })
    for col in dual_check["right_columns"]:
        series_config.append({
            "column": col,
            "type": "bar",  # 小量级用柱状图
            "yAxisIndex": 1,
            "unit": col
        })

    # 自动优化Y轴分配
    series_data = {}
    for col in dual_check["left_columns"] + dual_check["right_columns"]:
        values = []
        for row in data:
            val = row.get(col)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        series_data[col] = values

    allocation = determine_y_axis_allocation(series_data)

    # 根据分配结果调整series_config
    for config in series_config:
        col = config["column"]
        if col in allocation:
            config["yAxisIndex"] = allocation[col]
            # 根据Y轴位置调整图表类型
            config["type"] = "line" if allocation[col] == 0 else "bar"

    return build_multi_series_echarts_config(data, x_column, series_config, title)


# 测试
if __name__ == "__main__":
    # 模拟 SQL 查询结果
    test_data = [
        {"department": "技术部", "count": 45},
        {"department": "销售部", "count": 30},
        {"department": "市场部", "count": 25},
        {"department": "人事部", "count": 15},
    ]
    
    # 转换
    data, x, y = sql_result_to_echarts_data(test_data)
    print(f"X字段: {x}, Y字段: {y}")
    print(f"ECharts 数据: {data}")
    
    # 准备请求
    request = prepare_chart_request(
        test_data,
        "SELECT department, COUNT(*) as count FROM employees GROUP BY department",
        title="各部门人数分布"
    )
    print(f"\n图表请求: {request}")

