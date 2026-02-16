"""
# Agent 数据验证�?- SQL与图表数据一致性验�?

## [HEADER]
**文件�?*: data_validator.py
**职责**: 验证SQL执行结果与图表配置的一致性，防止LLM幻觉导致的数据不匹配
**作�?*: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-27): 初始版本，实现数据一致性验证和智能字段映射

## [INPUT]
- executed_sql: str - 执行的SQL语句
- query_results: List[Dict[str, Any]] - SQL查询结果
- llm_config: Dict[str, Any] - LLM生成的图表配置（可能包含幻觉字段�?

## [OUTPUT]
- ValidationResult: 包含验证结果、字段映射和建议的配�?
- FieldMapping: 智能推断的X/Y轴字段映�?

## [LINK]
**上游依赖**:
- [models.py](models.py) - ChartType和ChartConfig定义

**下游依赖**:
- [agent_service.py](agent_service.py) - 使用验证结果构建响应
- [data_transformer.py](data_transformer.py) - 使用字段映射转换数据

## [POS]
**路径**: backend/src/app/services/agent/data_validator.py
**模块层级**: Level 3 (Services �?Agent �?Data Validator)
**依赖深度**: 2 �?
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel


class ColumnType(str, Enum):
    """列数据类型枚�?""
    TIME = "time"           # 时间/日期类型
    CATEGORY = "category"   # 分类/字符串类�?
    NUMERIC = "numeric"     # 数值类�?
    UNKNOWN = "unknown"     # 未知类型


class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool = False
    error_message: Optional[str] = None
    actual_columns: List[str] = []
    llm_fields: List[str] = []
    hallucinated_fields: List[str] = []  # LLM编造但实际不存在的字段


class FieldMapping(BaseModel):
    """字段映射结果"""
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    x_type: ColumnType = ColumnType.UNKNOWN
    y_type: ColumnType = ColumnType.UNKNOWN
    confidence: float = 0.0  # 0-1, 映射置信�?
    reasoning: str = ""


class ChartRecommendation(BaseModel):
    """图表推荐结果"""
    chart_type: str = "table"
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    title: str = "查询结果"
    reasoning: str = ""


class ChartFieldValidation(BaseModel):
    """图表字段一致性验证（对外用实际查询和SQL SELECT�?"""
    is_valid: bool = False
    required_fields: List[str] = []
    select_fields: List[str] = []
    data_fields: List[str] = []
    missing_in_select: List[str] = []
    missing_in_data: List[str] = []
    message: Optional[str] = None

class DataConsistencyValidator:
    """
    数据一致性验证器

    核心功能�?
    1. 验证LLM生成的字段是否真实存在于SQL结果�?
    2. 智能推断X轴和Y轴应使用的字�?
    3. 拒绝LLM幻觉导致的虚假字段配�?
    """

    # 时间关键词列�?
    TIME_KEYWORDS = [
        'date', 'time', 'month', 'year', 'day', 'quarter',
        'week', 'hour', 'minute', 'second', 'created', 'updated',
        '日期', '时间', '�?, '�?, '�?, '季度', '�?
    ]

    # 分类关键词列�?
    CATEGORY_KEYWORDS = [
        'name', 'category', 'type', 'status', 'region', 'department',
        'product', 'customer', 'supplier', 'city', 'country',
        '名称', '类别', '类型', '状�?, '地区', '部门', '产品'
    ]

    # 数值聚合关键词
    AGGREGATION_KEYWORDS = [
        'sum', 'count', 'avg', 'average', 'max', 'min', 'total',
        'amount', 'quantity', 'price', 'sales', 'revenue', 'profit',
        '总和', '数量', '平均', '总计', '销售额', '收入', '利润'
    ]

    @classmethod
    def validate_sql_data_consistency(
        cls,
        executed_sql: str,
        query_results: List[Dict[str, Any]],
        llm_config: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        验证SQL与数据的一致�?

        Args:
            executed_sql: 执行的SQL语句
            query_results: SQL查询结果
            llm_config: LLM生成的图表配置（可能包含幻觉字段�?

        Returns:
            ValidationResult: 验证结果，包含幻觉字段列�?
        """
        if not query_results or len(query_results) == 0:
            return ValidationResult(
                is_valid=False,
                error_message="查询结果为空",
                actual_columns=[],
                llm_fields=[],
                hallucinated_fields=[]
            )

        # 获取实际的列�?
        actual_columns = list(query_results[0].keys())

        # 提取LLM配置中的字段
        llm_fields = []
        if llm_config:
            x_field = llm_config.get('x_field')
            y_field = llm_config.get('y_field')
            if x_field:
                llm_fields.append(x_field)
            if y_field:
                llm_fields.append(y_field)

        # 检测幻觉字段（LLM编造但实际不存在的字段�?
        hallucinated_fields = [
            field for field in llm_fields
            if field and field not in actual_columns
        ]

        is_valid = len(hallucinated_fields) == 0
        error_message = None
        if hallucinated_fields:
            error_message = (
                f"LLM幻觉检测：字段 {hallucinated_fields} 不存在于查询结果中�?
                f"实际字段: {actual_columns}"
            )

        return ValidationResult(
            is_valid=is_valid,
            error_message=error_message,
            actual_columns=actual_columns,
            llm_fields=llm_fields,
            hallucinated_fields=hallucinated_fields
        )

    @classmethod
    def infer_column_type(
        cls,
        column_name: str,
        sample_data: List[Any]
    ) -> ColumnType:
        """
        推断列的数据类型

        Args:
            column_name: 列名
            sample_data: 该列的样本数�?

        Returns:
            ColumnType: 推断的列类型
        """
        name_lower = column_name.lower()

        # 1. 首先根据列名判断
        if any(kw in name_lower for kw in cls.TIME_KEYWORDS):
            return ColumnType.TIME
        if any(kw in name_lower for kw in cls.AGGREGATION_KEYWORDS):
            return ColumnType.NUMERIC

        # 2. 根据样本数据判断
        if sample_data and len(sample_data) > 0:
            # 检查前几个非空�?
            for value in sample_data[:5]:
                if value is None or value == '':
                    continue

                # 尝试判断是否为数�?
                try:
                    float(str(value).replace(',', '').strip())
                    # 如果能转换为数值，且列名不包含分类关键词，则认为是数值列
                    if not any(kw in name_lower for kw in cls.CATEGORY_KEYWORDS):
                        return ColumnType.NUMERIC
                except (ValueError, TypeError):
                    pass

                # 检查是否包含时间格�?
                value_str = str(value)
                if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', value_str):
                    return ColumnType.TIME

        # 3. 默认为分类类�?
        if any(kw in name_lower for kw in cls.CATEGORY_KEYWORDS):
            return ColumnType.CATEGORY

        return ColumnType.UNKNOWN

    @classmethod
    def smart_field_mapping(
        cls,
        query_results: List[Dict[str, Any]],
        executed_sql: Optional[str] = None
    ) -> FieldMapping:
        """
        智能选择X轴和Y轴字�?

        映射规则�?
        - X轴优先级：时间列 > 分类�?> 第一�?
        - Y轴优先级：数值聚合列 > 其他数值列 > 非X轴的第一�?

        Args:
            query_results: SQL查询结果
            executed_sql: 执行的SQL（可选，用于辅助判断�?

        Returns:
            FieldMapping: 字段映射结果
        """
        if not query_results or len(query_results) == 0:
            return FieldMapping()

        columns = list(query_results[0].keys())

        if len(columns) < 1:
            return FieldMapping()

        # 收集每列的样本数�?
        column_samples = {
            col: [row.get(col) for row in query_results if row.get(col) is not None]
            for col in columns
        }

        # 推断每列的类�?
        column_types = {
            col: cls.infer_column_type(col, column_samples[col])
            for col in columns
        }

        # 选择X轴字�?
        x_field = None
        x_type = ColumnType.UNKNOWN

        # 优先�?: 时间�?
        time_cols = [col for col in columns if column_types[col] == ColumnType.TIME]
        if time_cols:
            x_field = time_cols[0]
            x_type = ColumnType.TIME

        # 优先�?: 分类列（排除数值列�?
        if not x_field:
            category_cols = [
                col for col in columns
                if column_types[col] == ColumnType.CATEGORY or
                   (column_types[col] == ColumnType.UNKNOWN and
                    any(kw in col.lower() for kw in cls.CATEGORY_KEYWORDS))
            ]
            if category_cols:
                x_field = category_cols[0]
                x_type = ColumnType.CATEGORY

        # 优先�?: 第一�?
        if not x_field:
            x_field = columns[0]
            x_type = column_types[x_field]

        # 选择Y轴字段（必须与X轴不同）
        y_field = None
        y_type = ColumnType.UNKNOWN

        # 剩余�?
        remaining_cols = [col for col in columns if col != x_field]

        # 优先�?: 数值聚合列
        agg_cols = [
            col for col in remaining_cols
            if any(kw in col.lower() for kw in cls.AGGREGATION_KEYWORDS) or
               column_types[col] == ColumnType.NUMERIC
        ]
        if agg_cols:
            y_field = agg_cols[0]
            y_type = column_types[y_field]

        # 优先�?: 第一个剩余列
        if not y_field and remaining_cols:
            y_field = remaining_cols[0]
            y_type = column_types[y_field]

        # 计算置信�?
        confidence = 0.5
        if x_type == ColumnType.TIME and y_type == ColumnType.NUMERIC:
            confidence = 0.95
        elif x_type == ColumnType.CATEGORY and y_type == ColumnType.NUMERIC:
            confidence = 0.9
        elif x_type != ColumnType.UNKNOWN and y_type == ColumnType.NUMERIC:
            confidence = 0.8
        elif x_type != ColumnType.UNKNOWN and y_type != ColumnType.UNKNOWN:
            confidence = 0.7

        # 生成推理说明
        reasoning_parts = []
        if x_type == ColumnType.TIME:
            reasoning_parts.append(f"X轴使用时间列 '{x_field}'")
        elif x_type == ColumnType.CATEGORY:
            reasoning_parts.append(f"X轴使用分类列 '{x_field}'")
        else:
            reasoning_parts.append(f"X轴使用第一�?'{x_field}'")

        if y_type == ColumnType.NUMERIC:
            reasoning_parts.append(f"Y轴使用数值列 '{y_field}'")
        else:
            reasoning_parts.append(f"Y轴使用列 '{y_field}'")

        reasoning = ", ".join(reasoning_parts)

        return FieldMapping(
            x_field=x_field,
            y_field=y_field,
            x_type=x_type,
            y_type=y_type,
            confidence=confidence,
            reasoning=reasoning
        )

    @classmethod
    def extract_sql_columns(cls, executed_sql: str) -> List[str]:
        """
        从SQL语句中提取SELECT的列�?

        Args:
            executed_sql: SQL语句

        Returns:
            List[str]: 提取的列名（可能包含别名�?
        """
        if not executed_sql:
            return []

        sql_lower = executed_sql.lower()

        # 查找SELECT和FROM之间的部�?
        select_match = re.search(
            r'select\s+(.*?)\s+from',
            sql_lower,
            re.DOTALL | re.IGNORECASE
        )

        if not select_match:
            return []

        select_clause = select_match.group(1)

        # 解析�?
        columns = []
        for col_part in select_clause.split(','):
            col_part = col_part.strip()

            # 处理别名: col_name AS alias �?col_name alias
            as_match = re.search(r'(\w+)\s+(?:as\s+)?(\w+)$', col_part, re.IGNORECASE)
            if as_match:
                columns.append(as_match.group(2))  # 使用别名
            else:
                # 去掉表名前缀 table.column -> column
                col_name = col_part.split('.')[-1]
                # 去掉函数调用
                col_name = re.sub(r'\(.*?\)', 'agg', col_name)
                columns.append(col_name)

        return columns

    @classmethod
    def recommend_chart(
        cls,
        query_results: List[Dict[str, Any]],
        executed_sql: Optional[str] = None,
        question: Optional[str] = None
    ) -> ChartRecommendation:
        """
        根据数据特征推荐图表类型和字段映�?

        Args:
            query_results: SQL查询结果
            executed_sql: 执行的SQL（可选）
            question: 用户问题（可选）

        Returns:
            ChartRecommendation: 图表推荐结果
        """
        if not query_results or len(query_results) == 0:
            return ChartRecommendation()

        # 获取字段映射
        field_mapping = cls.smart_field_mapping(query_results, executed_sql)

        # 根据用户问题推断图表类型
        chart_type = "table"
        reasoning = []

        if question:
            question_lower = question.lower()

            # 趋势�?-> 折线�?
            if any(kw in question_lower for kw in [
                "趋势", "变化", "时间", "月份", "年度", "季度",
                "增长", "下降", "趋势"
            ]):
                if field_mapping.x_type == ColumnType.TIME:
                    chart_type = "line"
                    reasoning.append("用户问题包含趋势关键词，且有时间�?)

            # 对比�?-> 柱状�?
            if any(kw in question_lower for kw in [
                "对比", "比较", "排名", "最�?, "最�?
            ]):
                chart_type = "bar"
                reasoning.append("用户问题包含对比关键�?)

            # 占比�?-> 饼图
            if any(kw in question_lower for kw in [
                "占比", "分布", "比例", "份额"
            ]):
                if len(query_results) <= 8:
                    chart_type = "pie"
                    reasoning.append("用户问题包含占比关键词，且类别数量适中")

        # 如果没有从问题推断出来，根据数据特征推断
        if chart_type == "table":
            if field_mapping.x_type == ColumnType.TIME and len(query_results) >= 3:
                chart_type = "line"
                reasoning.append("检测到时间序列数据")
            elif field_mapping.y_type == ColumnType.NUMERIC:
                if len(query_results) <= 8:
                    chart_type = "pie"
                    reasoning.append("类别数量适中，适合饼图")
                else:
                    chart_type = "bar"
                    reasoning.append("多个类别适合柱状�?)
            else:
                chart_type = "table"
                reasoning.append("数据不适合可视化，使用表格")

        # 生成标题
        title = "查询结果"
        if question:
            if "销�? in question:
                title = "销售分�?
            elif "收入" in question:
                title = "收入分析"
            elif "趋势" in question:
                title = "趋势分析"
            elif "对比" in question or "比较" in question:
                title = "对比分析"
            elif "占比" in question or "分布" in question:
                title = "分布分析"

        return ChartRecommendation(
            chart_type=chart_type,
            x_field=field_mapping.x_field,
            y_field=field_mapping.y_field,
            title=title,
            reasoning="; ".join(reasoning) if reasoning else field_mapping.reasoning
        )


# 导出函数，方便直接调�?
def validate_sql_data_consistency(
    executed_sql: str,
    query_results: List[Dict[str, Any]],
    llm_config: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """验证SQL与数据的一致�?""
    return DataConsistencyValidator.validate_sql_data_consistency(
        executed_sql, query_results, llm_config
    )


def smart_field_mapping(
    query_results: List[Dict[str, Any]],
    executed_sql: Optional[str] = None
) -> FieldMapping:
    """智能选择X轴和Y轴字�?""
    return DataConsistencyValidator.smart_field_mapping(query_results, executed_sql)


def recommend_chart(
    query_results: List[Dict[str, Any]],
    executed_sql: Optional[str] = None,
    question: Optional[str] = None
) -> ChartRecommendation:
    """推荐图表类型和字段映�?""
    return DataConsistencyValidator.recommend_chart(
        query_results, executed_sql, question
    )


def validate_chart_fields_in_sql(
    executed_sql: str,
    query_results: List[Dict[str, Any]],
    required_fields: Optional[List[Optional[str]]] = None
) -> ChartFieldValidation:
    """
    图表指定字段是否�?SQL SELECT 及数据结果中存在的解�?    """
    required_fields = required_fields or []
    return DataConsistencyValidator.validate_chart_fields_in_sql(
        executed_sql=executed_sql,
        required_fields=[f for f in required_fields if f],
        query_results=query_results,
    )


def build_cell_lineage(
    executed_sql: Optional[str],
    query_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    生成表格分布描述，包含这个字段的原始关键字段和分组信�?    """
    if not query_results:
        return []

    lineage: List[Dict[str, Any]] = []
    columns = list(query_results[0].keys())

    # 分析字段类型，由后续描述价格判断回调描述
    def _is_numeric(val: Any) -> bool:
        try:
            float(val)
            return True
        except Exception:
            return False

    # 检测本次命名（sum/count�?）规�?    agg_map: Dict[str, str] = {}
    if executed_sql:
        lowered = executed_sql.lower()
        for col in columns:
            pattern = rf"(sum|count|avg|min|max)\s*\([^)]*?{re.escape(col.lower())}[^)]*?\)\s*(?:as\s+{re.escape(col.lower())})?"
            if re.search(pattern, lowered, re.IGNORECASE):
                agg_map[col] = re.search(pattern, lowered, re.IGNORECASE).group(1).upper()

    for row_idx, row in enumerate(query_results):
        if not isinstance(row, dict):
            try:
                row = {c: row[i] for i, c in enumerate(columns)}
            except Exception:
                continue
        dims = {k: v for k, v in row.items() if not _is_numeric(v)}
        for col, val in row.items():
            if not _is_numeric(val):
                continue
            agg = agg_map.get(col)
            dim_desc = ", ".join([f"{k}={v}" for k, v in dims.items()]) if dims else "信息缺少"
            explanation = f"字段 '{col}' 就是实际查询结果，按 {dim_desc} 分组"
            if agg:
                explanation += f"，备�? {agg} 合并"
            lineage.append({
                "row": row_idx,
                "column": col,
                "value": val,
                "explanation": explanation,
                "group_keys": dims,
                "agg": agg,
            })

    return lineage


def generate_insights_from_rows(
    rows: List[Dict[str, Any]],
    question: Optional[str] = None
) -> List[str]:
    """
    从字典列表数据出现，业务有关的纯指示
    """
    if not rows:
        return []
    insights: List[str] = []
    columns = list(rows[0].keys())

    # 分析时间成本数值、收入半价，由于没有pandas，用简单秄�?    time_col = next((c for c in columns if any(k in c.lower() for k in ['month', 'date', 'time', 'year', '�?', '�?', '�?'])), None)
    metric_col = next((c for c in columns if c != time_col and isinstance(rows[0].get(c), (int, float))), None)
    price_col = next((c for c in columns if 'price' in c.lower() or '�?' in c), None)

    # ȱʧ�·�/�?    if time_col and metric_col:
        from datetime import datetime
        def parse_dt(v):
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y-%m', '%Y/%m', '%Y��%m��'):
                try:
                    return datetime.strptime(str(v), fmt)
                except Exception:
                    continue
            return None
        parsed = [(parse_dt(r.get(time_col)), r.get(metric_col)) for r in rows if parse_dt(r.get(time_col))]
        parsed = [(d, v) for d, v in parsed if isinstance(v, (int, float))]
        if parsed:
            parsed.sort(key=lambda x: x[0])
            months = [d.replace(day=1) for d, _ in parsed]
            full = []
            cur = months[0]
            last = months[-1]
            while cur <= last:
                full.append(cur)
                cur = (cur.replace(day=28) + __import__('datetime').timedelta(days=4)).replace(day=1)
            missing = [m for m in full if m not in months]
            if missing:
                label = "��".join(sorted({m.strftime('%Y-%m') for m in missing}))
                insights.append(f"清除提示�? {label} 无销�?")
            # 流最算法：计算现期持续质（不包含任次�?�?            growth = []
            for i in range(1, len(parsed)):
                prev = parsed[i-1][1]
                cur_val = parsed[i][1]
                if prev and isinstance(prev, (int, float)) and prev != 0:
                    growth_rate = (cur_val - prev) / prev
                    growth.append((parsed[i][0], growth_rate))
            if growth:
                spike = [g for g in growth if g[1] >= 0.5]
                if spike:
                    top = spike[-1]
                    insights.append(f"{top[0].strftime('%Y-%m')} 深水�? {(top[1]*100):.0f}%��零长更容�?")

    if price_col:
        prices = [r.get(price_col) for r in rows if isinstance(r.get(price_col), (int, float, float))]
        if prices:
            if max(prices) == min(prices):
                insights.append(f"单位�?({price_col}) 不变，导致只能差用眉单曲价，请试试试成功价所有容�?")
    return insights
