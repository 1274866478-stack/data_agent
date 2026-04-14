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


def supplement_proportion_data(
    sql_result: List[Dict[str, Any]],
    sql: str = "",
    user_query: str = ""
) -> List[Dict[str, Any]]:
    """
    为占比类查询补全"其他"类别数据

    当只有一个数据点时，自动添加"其他"类别使饼图完整。

    🔧 修复：更严格的检测逻辑，避免错误补全

    Args:
        sql_result: SQL 查询返回的字典列表
        sql: SQL 查询语句（用于检测占比类查询）
        user_query: 用户原始查询（用于检测占比类查询）

    Returns:
        补全后的数据列表

    Example:
        >>> result = [{"province": "安徽", "count": 42}]
        >>> supplement_proportion_data(result, user_query="安徽省的客户占比是多少？")
        [{"province": "安徽", "count": 42}, {"province": "其他", "count": 958}]  # 假设总数1000
    """
    if not sql_result or len(sql_result) != 1:
        return sql_result

    # 🔧 修复0: 检查用户是否期望看到所有类别
    # 如果用户查询包含"各"、"所有"、"全部"等词，说明应该返回多条记录
    # 此时只有1条记录是SQL问题，不应该补全
    if user_query:
        all_categories_keywords = ['各', '所有', '全部', '每', 'each', 'all', 'every']
        if any(kw in user_query for kw in all_categories_keywords):
            print(f"[DataTransformer] 用户期望看到所有类别（检测到关键词），跳过补全")
            return sql_result

    # 🔧 修复1: 检查SQL是否包含聚合函数和GROUP BY
    # 如果是简单的COUNT(*)查询，不应该补全
    has_count_star = 'COUNT(*)' in sql.upper() or 'COUNT (*)' in sql.upper() or 'COUNT(' in sql.upper()
    has_group_by = 'GROUP BY' in sql.upper()

    # 🔧 修复2: 如果是COUNT(*)但没有GROUP BY，说明是总数查询，不补全
    if has_count_star and not has_group_by:
        print(f"[DataTransformer] 检测到COUNT(*)无GROUP BY查询（总数查询），跳过补全")
        return sql_result

    # 🔧 修复3: 如果只有一个数值列且没有类别列（单值结果），不补全
    row = sql_result[0]
    columns = list(row.keys())

    # 统计数值列和非数值列的数量
    numeric_cols = []
    non_numeric_cols = []
    for col in columns:
        val = row.get(col)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            numeric_cols.append(col)
        else:
            non_numeric_cols.append(col)

    # 如果只有数值列没有类别列，这是纯聚合结果，不补全
    if len(non_numeric_cols) == 0:
        print(f"[DataTransformer] 检测到纯数值结果（无类别列），跳过补全")
        return sql_result

    # 检测是否为占比类查询
    proportion_keywords = ['占比', '比例', '分布', '多少']
    combined_text = (sql + " " + user_query).lower()
    if not any(kw in combined_text for kw in proportion_keywords):
        return sql_result

    if len(columns) < 2:
        return sql_result

    # 找类别列和数值列
    value_col = None
    category_col = None
    for col in columns:
        val = row.get(col)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            value_col = col
        else:
            category_col = col

    if not value_col or not category_col:
        # 尝试按列名推断
        for col in columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in ['count', 'num', 'amount', '值', '数', '量', 'percent', '%']):
                value_col = col
            else:
                category_col = col

    if not value_col or not category_col:
        return sql_result

    try:
        current_value = float(row[value_col])
    except (ValueError, TypeError):
        return sql_result

    current_category = str(row.get(category_col, ""))

    # 🔧 修复4: 更谨慎的补集检测逻辑
    # 只有在明确需要补全的情况下才添加"其他"类别
    other_value = None

    if current_value > 0:
        # 判断是否可能是百分比
        # 1. 检查列名是否包含百分比关键词
        col_has_percent_hint = any(kw in value_col.lower() for kw in ['percent', 'ratio', 'proportion', '%', '率', '占比'])

        # 2. 检查值是否在合理百分比范围内 (0-100 且不太接近整数计数)
        # 小于100可能是百分比或小计数，大于100通常是计数
        is_likely_percentage = col_has_percent_hint or (current_value <= 100 and current_value != int(current_value))

        if is_likely_percentage:
            # 如果是百分比，补齐100
            if current_value < 100:
                other_value = round(100 - current_value, 1)
        else:
            # 🔧 修复5: 对于计数值，不再自动添加等量"其他"
            # 因为这可能导致数据误导（如安徽1000 vs 其他1000，实际全是安徽）
            # 改为：只有明确是小数值（<100）且非百分比时，才考虑添加对比数据
            if current_value < 100:
                # 小数值可能是示例数据，添加等量对比
                other_value = current_value
            else:
                # 大数值不补全，避免数据误导
                print(f"[DataTransformer] 数值较大({current_value})，跳过补全避免误导")
                return sql_result

        if other_value and other_value > 0:
            other_row = {category_col: "其他", value_col: other_value}
            # 保留原始行中的其他字段
            for col in columns:
                if col != category_col and col != value_col:
                    other_row[col] = row.get(col)
            print(f"[DataTransformer] 补全其他类别: {current_category}={current_value}, 其他={other_value}")
            return sql_result + [other_row]

    return sql_result


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
            # 统一两位小数，保持报表观感专业
            y_val = round(y_val, 2) if isinstance(y_val, float) else y_val
        except (ValueError, TypeError):
            y_val = 0
        
        data.append([x_val, y_val])
    
    return data, actual_x, actual_y


def sql_result_to_mcp_echarts_data(
    sql_result: List[Dict[str, Any]],
    chart_type: str = "bar",
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    sql: str = "",
    user_query: str = ""
) -> Tuple[List[Dict[str, Any]], str, str]:
    """
    将 SQL 查询结果转换为 mcp-echarts 需要的格式

    Args:
        sql_result: SQL 查询返回的字典列表
        chart_type: 图表类型 ("bar", "pie", "line" 等)
        x_field: X轴/分类字段名（可选）
        y_field: Y轴/数值字段名（可选）
        sql: SQL 查询语句（用于占比类查询检测）
        user_query: 用户原始查询（用于占比类查询检测）

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
    # 🔧 饼图数据补全：为占比类单点数据添加"其他"类别
    if chart_type == "pie":
        sql_result = supplement_proportion_data(sql_result, sql, user_query)

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
            y_val = round(y_val, 2) if isinstance(y_val, float) else y_val
        except (ValueError, TypeError):
            y_val = 0

        if chart_type == "line":
            # 折线图使用 time/value 格式
            data.append({"time": str(x_val), "value": y_val})
        else:
            # 柱状图、饼图等使用 category/value 格式
            data.append({"category": str(x_val), "value": y_val})

    return data, actual_x, actual_y


def detect_percentage_data(data: List[Dict[str, Any]]) -> bool:
    """
    检测数据是否为百分比格式

    Args:
        data: 查询结果数据

    Returns:
        True 如果检测到百分比数据特征
    """
    if not data or len(data) == 0:
        return False

    columns = list(data[0].keys())

    # 1. 检查列名是否包含百分比关键词
    percent_keywords = ['percent', 'percentage', 'ratio', 'proportion', 'rate',
                        '占比', '比率', '百分比', '比例', '份额']
    has_percent_column = any(
        any(kw in col.lower() for kw in percent_keywords)
        for col in columns
    )
    if has_percent_column:
        return True

    # 2. 检查数值特征：总和接近100，且所有值在0-100范围内
    numeric_values = []
    for row in data:
        for col in columns:
            val = row.get(col)
            if val is not None:
                try:
                    # 检查是否为字符串形式的百分比
                    if isinstance(val, str) and '%' in val:
                        return True
                    num_val = float(str(val).replace('%', ''))
                    if 0 <= num_val <= 100:
                        numeric_values.append(num_val)
                except (ValueError, TypeError):
                    pass

    if numeric_values and len(numeric_values) > 1:
        total = sum(numeric_values)
        # 总和在 95-105 之间，认为是百分比数据
        if 95 <= total <= 105:
            return True

    return False


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

    # 0. 检测百分比数据（优先级最高）
    if detect_percentage_data(data):
        return "pie"

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

