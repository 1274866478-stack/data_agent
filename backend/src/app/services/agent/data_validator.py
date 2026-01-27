"""
# Agent 数据验证器 - SQL与图表数据一致性验证

## [HEADER]
**文件名**: data_validator.py
**职责**: 验证SQL执行结果与图表配置的一致性，防止LLM幻觉导致的数据不匹配
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-27): 初始版本，实现数据一致性验证和智能字段映射

## [INPUT]
- executed_sql: str - 执行的SQL语句
- query_results: List[Dict[str, Any]] - SQL查询结果
- llm_config: Dict[str, Any] - LLM生成的图表配置（可能包含幻觉字段）

## [OUTPUT]
- ValidationResult: 包含验证结果、字段映射和建议的配置
- FieldMapping: 智能推断的X/Y轴字段映射

## [LINK]
**上游依赖**:
- [models.py](models.py) - ChartType和ChartConfig定义

**下游依赖**:
- [agent_service.py](agent_service.py) - 使用验证结果构建响应
- [data_transformer.py](data_transformer.py) - 使用字段映射转换数据

## [POS]
**路径**: backend/src/app/services/agent/data_validator.py
**模块层级**: Level 3 (Services → Agent → Data Validator)
**依赖深度**: 2 层
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel


class ColumnType(str, Enum):
    """列数据类型枚举"""
    TIME = "time"           # 时间/日期类型
    CATEGORY = "category"   # 分类/字符串类型
    NUMERIC = "numeric"     # 数值类型
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
    confidence: float = 0.0  # 0-1, 映射置信度
    reasoning: str = ""


class ChartRecommendation(BaseModel):
    """图表推荐结果"""
    chart_type: str = "table"
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    title: str = "查询结果"
    reasoning: str = ""


class DataConsistencyValidator:
    """
    数据一致性验证器

    核心功能：
    1. 验证LLM生成的字段是否真实存在于SQL结果中
    2. 智能推断X轴和Y轴应使用的字段
    3. 拒绝LLM幻觉导致的虚假字段配置
    """

    # 时间关键词列表
    TIME_KEYWORDS = [
        'date', 'time', 'month', 'year', 'day', 'quarter',
        'week', 'hour', 'minute', 'second', 'created', 'updated',
        '日期', '时间', '年', '月', '日', '季度', '周'
    ]

    # 分类关键词列表
    CATEGORY_KEYWORDS = [
        'name', 'category', 'type', 'status', 'region', 'department',
        'product', 'customer', 'supplier', 'city', 'country',
        '名称', '类别', '类型', '状态', '地区', '部门', '产品'
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
        验证SQL与数据的一致性

        Args:
            executed_sql: 执行的SQL语句
            query_results: SQL查询结果
            llm_config: LLM生成的图表配置（可能包含幻觉字段）

        Returns:
            ValidationResult: 验证结果，包含幻觉字段列表
        """
        if not query_results or len(query_results) == 0:
            return ValidationResult(
                is_valid=False,
                error_message="查询结果为空",
                actual_columns=[],
                llm_fields=[],
                hallucinated_fields=[]
            )

        # 获取实际的列名
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

        # 检测幻觉字段（LLM编造但实际不存在的字段）
        hallucinated_fields = [
            field for field in llm_fields
            if field and field not in actual_columns
        ]

        is_valid = len(hallucinated_fields) == 0
        error_message = None
        if hallucinated_fields:
            error_message = (
                f"LLM幻觉检测：字段 {hallucinated_fields} 不存在于查询结果中。"
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
            sample_data: 该列的样本数据

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
            # 检查前几个非空值
            for value in sample_data[:5]:
                if value is None or value == '':
                    continue

                # 尝试判断是否为数值
                try:
                    float(str(value).replace(',', '').strip())
                    # 如果能转换为数值，且列名不包含分类关键词，则认为是数值列
                    if not any(kw in name_lower for kw in cls.CATEGORY_KEYWORDS):
                        return ColumnType.NUMERIC
                except (ValueError, TypeError):
                    pass

                # 检查是否包含时间格式
                value_str = str(value)
                if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', value_str):
                    return ColumnType.TIME

        # 3. 默认为分类类型
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
        智能选择X轴和Y轴字段

        映射规则：
        - X轴优先级：时间列 > 分类列 > 第一列
        - Y轴优先级：数值聚合列 > 其他数值列 > 非X轴的第一列

        Args:
            query_results: SQL查询结果
            executed_sql: 执行的SQL（可选，用于辅助判断）

        Returns:
            FieldMapping: 字段映射结果
        """
        if not query_results or len(query_results) == 0:
            return FieldMapping()

        columns = list(query_results[0].keys())

        if len(columns) < 1:
            return FieldMapping()

        # 收集每列的样本数据
        column_samples = {
            col: [row.get(col) for row in query_results if row.get(col) is not None]
            for col in columns
        }

        # 推断每列的类型
        column_types = {
            col: cls.infer_column_type(col, column_samples[col])
            for col in columns
        }

        # 选择X轴字段
        x_field = None
        x_type = ColumnType.UNKNOWN

        # 优先级1: 时间列
        time_cols = [col for col in columns if column_types[col] == ColumnType.TIME]
        if time_cols:
            x_field = time_cols[0]
            x_type = ColumnType.TIME

        # 优先级2: 分类列（排除数值列）
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

        # 优先级3: 第一列
        if not x_field:
            x_field = columns[0]
            x_type = column_types[x_field]

        # 选择Y轴字段（必须与X轴不同）
        y_field = None
        y_type = ColumnType.UNKNOWN

        # 剩余列
        remaining_cols = [col for col in columns if col != x_field]

        # 优先级1: 数值聚合列
        agg_cols = [
            col for col in remaining_cols
            if any(kw in col.lower() for kw in cls.AGGREGATION_KEYWORDS) or
               column_types[col] == ColumnType.NUMERIC
        ]
        if agg_cols:
            y_field = agg_cols[0]
            y_type = column_types[y_field]

        # 优先级2: 第一个剩余列
        if not y_field and remaining_cols:
            y_field = remaining_cols[0]
            y_type = column_types[y_field]

        # 计算置信度
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
            reasoning_parts.append(f"X轴使用第一列 '{x_field}'")

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
        从SQL语句中提取SELECT的列名

        Args:
            executed_sql: SQL语句

        Returns:
            List[str]: 提取的列名（可能包含别名）
        """
        if not executed_sql:
            return []

        sql_lower = executed_sql.lower()

        # 查找SELECT和FROM之间的部分
        select_match = re.search(
            r'select\s+(.*?)\s+from',
            sql_lower,
            re.DOTALL | re.IGNORECASE
        )

        if not select_match:
            return []

        select_clause = select_match.group(1)

        # 解析列
        columns = []
        for col_part in select_clause.split(','):
            col_part = col_part.strip()

            # 处理别名: col_name AS alias 或 col_name alias
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
        根据数据特征推荐图表类型和字段映射

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

            # 趋势类 -> 折线图
            if any(kw in question_lower for kw in [
                "趋势", "变化", "时间", "月份", "年度", "季度",
                "增长", "下降", "趋势"
            ]):
                if field_mapping.x_type == ColumnType.TIME:
                    chart_type = "line"
                    reasoning.append("用户问题包含趋势关键词，且有时间列")

            # 对比类 -> 柱状图
            if any(kw in question_lower for kw in [
                "对比", "比较", "排名", "最高", "最低"
            ]):
                chart_type = "bar"
                reasoning.append("用户问题包含对比关键词")

            # 占比类 -> 饼图
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
                    reasoning.append("多个类别适合柱状图")
            else:
                chart_type = "table"
                reasoning.append("数据不适合可视化，使用表格")

        # 生成标题
        title = "查询结果"
        if question:
            if "销售" in question:
                title = "销售分析"
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


# 导出函数，方便直接调用
def validate_sql_data_consistency(
    executed_sql: str,
    query_results: List[Dict[str, Any]],
    llm_config: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """验证SQL与数据的一致性"""
    return DataConsistencyValidator.validate_sql_data_consistency(
        executed_sql, query_results, llm_config
    )


def smart_field_mapping(
    query_results: List[Dict[str, Any]],
    executed_sql: Optional[str] = None
) -> FieldMapping:
    """智能选择X轴和Y轴字段"""
    return DataConsistencyValidator.smart_field_mapping(query_results, executed_sql)


def recommend_chart(
    query_results: List[Dict[str, Any]],
    executed_sql: Optional[str] = None,
    question: Optional[str] = None
) -> ChartRecommendation:
    """推荐图表类型和字段映射"""
    return DataConsistencyValidator.recommend_chart(
        query_results, executed_sql, question
    )
