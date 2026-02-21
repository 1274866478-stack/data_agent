# -*- coding: utf-8 -*-
"""
反思节点 (Reflection Node) - LangGraph 节点

这个节点在查询执行后进行反思和自修复，实现错误分析和修正建议功能。

核心功能：
    1. 分析执行结果
    2. 检测错误
    3. 生成修复建议
    4. 决定是否需要重试
    5. 触发学习循环（将错误信息传递给学习引擎）

作者: Data Agent Team
版本: 2.0.0 - 添加学习循环集成
"""

import json
import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import MessagesState

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """错误类别"""
    SQL_SYNTAX = "sql_syntax"           # SQL 语法错误
    COLUMN_NOT_FOUND = "column_not_found"  # 列不存在
    TABLE_NOT_FOUND = "table_not_found"    # 表不存在
    ASSUMED_TABLE_NAME = "assumed_table_name"  # 假设表名错误
    RELATION_ERROR = "relation_error"      # 关联错误
    TYPE_MISMATCH = "type_mismatch"        # 类型不匹配
    EMPTY_RESULT = "empty_result"          # 空结果
    PERMISSION_ERROR = "permission_error"  # 权限错误
    UNKNOWN = "unknown"                    # 未知错误


@dataclass
class ReflectionResult:
    """反思结果"""
    success: bool                        # 是否成功
    error_category: Optional[ErrorCategory] = None  # 错误类别
    error_message: str = ""               # 错误消息
    fix_suggestion: str = ""              # 修复建议
    should_retry: bool = False            # 是否应该重试
    retry_count: int = 0                  # 重试次数
    confidence: float = 1.0               # 当前置信度

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "error_category": self.error_category.value if self.error_category else None,
            "error_message": self.error_message,
            "fix_suggestion": self.fix_suggestion,
            "should_retry": self.should_retry,
            "retry_count": self.retry_count,
            "confidence": self.confidence
        }


class ReflectionNode:
    """
    反思节点

    在工具执行后分析结果，检测错误并生成修复建议。

    功能：
        1. 分析 ToolMessage 内容
        2. 识别错误类型
        3. 生成针对性的修复建议
        4. 决定是否需要重试
        5. 触发学习循环（将错误信息传递给学习引擎）
    """

    # 错误模式匹配
    ERROR_PATTERNS = {
        ErrorCategory.COLUMN_NOT_FOUND: [
            r'column.*does not exist',
            r'column.*not found',
            r'undefined column',
            r'unknown column',
            r"column '?\w+'? does not exist"
        ],
        ErrorCategory.TABLE_NOT_FOUND: [
            r'relation.*does not exist',
            r'table.*not found',
            r'unknown table',
            r"relation '?\w+'? does not exist"
        ],
        ErrorCategory.SQL_SYNTAX: [
            r'syntax error',
            r'invalid syntax',
            r'parse error',
            r'unexpected token',
            r'near.*syntax'
        ],
        ErrorCategory.TYPE_MISMATCH: [
            r'type mismatch',
            r'cannot be applied to',
            r'argument types',
            r'no function matches',
            r'binder error'
        ],
        ErrorCategory.PERMISSION_ERROR: [
            r'permission denied',
            r'access denied',
            r'unauthorized',
            r'privilege'
        ],
    }

    # 常见假设表名（AI经常猜测的英文表名）
    COMMON_ASSUMED_TABLE_NAMES = [
        'sales', 'orders', 'users', 'customers', 'products',
        'inventory', 'categories', 'regions', 'employees',
        'order_details', 'order_items', 'sales_data'
    ]

    # 空结果指示词
    EMPTY_RESULT_INDICATORS = [
        'no data',
        'empty result',
        'no results',
        'found 0 rows',
        '[]',
        '{}',
    ]

    # 时间关键词模式（用于检测用户问题中的时间范围）
    TIME_KEYWORD_PATTERNS = [
        r'(\d{4})年',           # "2023年"、"2024年"
        r'(\d{4})-(\d{1,2})',   # "2023-05"（年月格式）
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # "2023-05-01"（完整日期）
        r'今年|去年|前年',       # 相对年份
        r'本月|上个月|下个月',   # 相对月份
        r'第一季度|第二季度|第三季度|第四季度|Q[1-4]',  # 季度
    ]

    def __init__(
        self,
        max_retries: int = 3,
        enable_logging: bool = True,
        enable_learning: bool = True,  # 新增：是否启用学习循环
        learning_threshold: float = 0.5  # 新增：触发学习的最低置信度阈值
    ):
        """初始化反思节点

        Args:
            max_retries: 最大重试次数
            enable_logging: 是否启用日志
            enable_learning: 是否启用学习循环（将错误传递给学习引擎）
            learning_threshold: 触发学习的最低置信度阈值
        """
        self.max_retries = max_retries
        self.enable_logging = enable_logging
        self.enable_learning = enable_learning
        self.learning_threshold = learning_threshold

        # 知识库服务缓存（按租户）
        self._knowledge_bases: Dict[str, Any] = {}

    def __call__(self, state: MessagesState) -> Dict[str, Any]:
        """执行反思分析

        Args:
            state: LangGraph 消息状态

        Returns:
            更新后的状态，包含反思结果
        """
        messages = state["messages"]

        # 分析最后一条消息
        reflection = self._analyze_messages(messages)

        # 记录反思结果
        if self.enable_logging:
            self._log_reflection(reflection)

        # 🆕 触发学习循环
        learning_data = None
        if self.enable_learning:
            learning_data = self._trigger_learning(state, reflection)
            if learning_data:
                logger.info("[ReflectionNode] 学习循环已触发")

        # 创建反思消息
        reflection_message = self._create_reflection_message(reflection, learning_data)

        # 更新重试计数
        retry_count = state.get("__retry_count__", 0)
        if reflection.should_retry and retry_count < self.max_retries:
            retry_count += 1

        # 构建返回状态
        # 注意：学习数据会通过 reflection_message 传递，不直接添加到状态中
        return {
            "messages": [reflection_message],
            "__reflection_result__": reflection.to_dict(),
            "__retry_count__": retry_count,
            "__should_retry__": reflection.should_retry
        }

    def _analyze_messages(self, messages: list) -> ReflectionResult:
        """分析消息，生成反思结果

        Args:
            messages: 消息列表

        Returns:
            反思结果
        """
        # 找到最后的 ToolMessage
        last_tool_message = None
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                last_tool_message = msg
                break

        if not last_tool_message:
            return ReflectionResult(success=True)

        # 提取工具返回内容
        content: str = self._extract_tool_content(last_tool_message.content)

        # 获取用户原始问题（用于时间范围验证）
        user_question = ""
        for msg in messages:
            if isinstance(msg, HumanMessage):
                msg_content = msg.content
                # 处理 content 可能是 str 或 list 的情况
                if isinstance(msg_content, str):
                    user_question = msg_content
                elif isinstance(msg_content, list) and len(msg_content) > 0:
                    # 如果是列表，提取文本内容
                    user_question = str(msg_content[0]) if isinstance(msg_content[0], str) else ""
                break

        # 首先进行时间范围合规性检查
        time_check_result = self._check_time_range_compliance(content, user_question)
        if time_check_result:
            return time_check_result

        # 🔧 新增：趋势查询聚合检查
        trend_check_result = self._check_trend_query_aggregation(messages, user_question, content)
        if trend_check_result:
            return trend_check_result

        return self._analyze_content(content)

    def _extract_tool_content(self, content) -> str:
        """从 ToolMessage.content 中提取实际文本内容

        Args:
            content: ToolMessage.content (可能是 str 或 list)

        Returns:
            提取的文本内容
        """
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            # MCP 工具返回格式: [{'type': 'text', 'text': '...'}]
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get('text', '')
                    if text:
                        text_parts.append(text)
                elif isinstance(item, str):
                    text_parts.append(item)
            return '\n'.join(text_parts) if text_parts else str(content)

        return str(content)

    def _analyze_content(self, content: str) -> ReflectionResult:
        """分析工具返回内容

        Args:
            content: 工具返回内容

        Returns:
            反思结果
        """
        content_stripped = content.strip()

        # 首先检查是否是有效的JSON响应（表示工具成功执行）
        if self._is_valid_json_response(content_stripped):
            return ReflectionResult(
                success=True,
                confidence=1.0
            )

        # 检查是否是空结果
        if self._is_empty_result(content):
            return ReflectionResult(
                success=True,
                error_category=ErrorCategory.EMPTY_RESULT,
                error_message="查询成功但没有返回数据",
                fix_suggestion="检查查询条件是否过于严格，或使用更通用的条件",
                should_retry=False,
                confidence=0.8
            )

        # 🔴 优先检查假设表名错误
        assumed_table_result = self._check_assumed_table_name(content)
        if assumed_table_result:
            return assumed_table_result

        # 检查是否是错误
        error_category = self._identify_error(content)
        if error_category:
            fix_suggestion = self._generate_fix_suggestion(error_category, content)

            return ReflectionResult(
                success=False,
                error_category=error_category,
                error_message=self._extract_error_message(content),
                fix_suggestion=fix_suggestion,
                should_retry=True,
                confidence=0.5
            )

        # 没有检测到错误
        return ReflectionResult(
            success=True,
            confidence=1.0
        )

    def _check_assumed_table_name(self, content: str) -> Optional[ReflectionResult]:
        """检查是否是假设表名错误

        当AI使用了常见英文表名（如sales, orders）但实际表中不存在时，
        识别为"假设表名"错误并给出明确指导。

        Args:
            content: 工具返回内容

        Returns:
            如果检测到假设表名错误，返回ReflectionResult；否则返回None
        """
        content_lower = content.lower()

        # 检查是否是表不存在的错误
        if not any(pattern in content_lower for pattern in ['does not exist', 'not found', 'unknown table']):
            return None

        # 检查是否使用了常见假设表名
        import re
        # 尝试从错误消息中提取表名
        # 支持格式: relation "table_name", relation 'table_name', table "table_name", from table where
        table_match = re.search(
            r'relation\s+["\']?(\w+)["\']?|table\s+["\']?(\w+)["\']?|from\s+(\w+)\s+where',
            content_lower
        )

        if table_match:
            # 获取匹配的表名
            actual_table = (table_match.group(1) or table_match.group(2) or table_match.group(3))
            if actual_table and actual_table in self.COMMON_ASSUMED_TABLE_NAMES:
                return ReflectionResult(
                    success=False,
                    error_category=ErrorCategory.ASSUMED_TABLE_NAME,
                    error_message=f"检测到假设表名错误: 使用了常见英文表名 '{actual_table}'",
                    fix_suggestion=self._generate_assumed_table_fix_suggestion(actual_table),
                    should_retry=True,
                    confidence=0.9
                )

        return None

    def _generate_assumed_table_fix_suggestion(self, assumed_table: str) -> str:
        """为假设表名错误生成修复建议

        Args:
            assumed_table: 被假设的表名

        Returns:
            修复建议
        """
        return f"""**假设表名错误！**

**问题**: 你使用了常见的英文表名 "{assumed_table}"，但数据库中可能不存在这个表。

**必须执行的步骤**：
1. **立即调用 `list_tables()`** 查看数据库中的实际表名
2. 根据返回的实际表名选择合适的表（可能是中文表名）
3. 使用 list_tables() 返回的确切表名重新查询

**示例**:
```
用户: "2023年的销售趋势"
错误: SELECT * FROM {assumed_table} WHERE ...
正确:
  1. list_tables() → 返回: ["订单表", "用户表", ...]
  2. 使用 "订单表" 而不是 "{assumed_table}"
  3. SELECT * FROM 订单表 WHERE EXTRACT(YEAR FROM 订单日期) = 2023
```

**记住**: 永远不要猜测或假设表名！"""

    def _is_valid_json_response(self, content: str) -> bool:
        """判断是否是有效的JSON响应（工具成功执行的标志）

        Args:
            content: 内容

        Returns:
            是否是有效JSON响应
        """
        content_stripped = content.strip()

        # 检查是否包含图像（图表生成成功）
        if 'image' in content_stripped.lower() and 'base64' in content_stripped:
            return True

        # 尝试解析JSON
        try:
            data = json.loads(content_stripped)
            # 如果能解析为JSON，且是dict或list，认为是有效响应
            if isinstance(data, (dict, list)):
                # 检查是否包含明显的错误信息
                content_lower = content_stripped.lower()
                error_keywords = ['error', 'failed', 'exception', 'traceback', 'syntax error']
                # 只有当JSON中不包含错误关键词时才认为是成功
                for keyword in error_keywords:
                    if keyword in content_lower and len(content_stripped) < 500:
                        # 短内容包含错误关键词可能是真正的错误
                        return False
                return True
        except (json.JSONDecodeError, ValueError):
            pass

        return False

    def _is_empty_result(self, content: str) -> bool:
        """判断是否是空结果

        Args:
            content: 内容

        Returns:
            是否是空结果
        """
        content_lower = content.lower()

        for indicator in self.EMPTY_RESULT_INDICATORS:
            if indicator in content_lower:
                return True

        # 检查空 JSON
        try:
            data = json.loads(content)
            if isinstance(data, list) and len(data) == 0:
                return True
            if isinstance(data, dict) and not data:
                return True
        except json.JSONDecodeError:
            pass

        return False

    def _check_time_range_compliance(
        self,
        content: str,
        user_question: str = ""
    ) -> Optional[ReflectionResult]:
        """检查返回数据的时间范围是否符合用户请求

        当用户问"2023年的销售"但结果包含2024年数据时，
        标记为需要修复。

        Args:
            content: 工具返回内容
            user_question: 用户原始问题（从state中获取）

        Returns:
            如果检测到时间范围问题，返回ReflectionResult；否则返回None
        """
        # 如果没有提供用户问题，无法检查
        if not user_question:
            return None

        # 提取用户问题中的时间关键词
        import re
        year_match = re.search(r'(\d{4})年', user_question)
        if not year_match:
            # 没有明确年份要求，不需要检查
            return None

        requested_year = int(year_match.group(1))

        # 尝试从JSON响应中检查数据
        try:
            data = json.loads(content.strip())
            if not isinstance(data, list) or len(data) == 0:
                return None

            # 检查数据中是否有日期/时间字段
            # 常见时间字段名
            time_fields = ['date', 'time', '日期', '时间', 'created_at',
                          'updated_at', 'order_date', 'sale_date', 'month', 'year']

            # 获取第一条记录来检查字段
            first_record = data[0]
            if not isinstance(first_record, dict):
                return None

            # 查找时间字段
            time_field = None
            for field in time_fields:
                if field in first_record:
                    time_field = field
                    break

            if not time_field:
                # 没有找到时间字段，无法验证
                return None

            # 检查数据中是否包含超出请求年份的记录
            for record in data:
                date_value = record.get(time_field, '')
                if not date_value:
                    continue

                # 从日期值中提取年份
                date_str = str(date_value)
                # 尝试匹配各种日期格式
                year_in_data = None
                if len(date_str) >= 4 and date_str[:4].isdigit():
                    year_in_data = int(date_str[:4])
                else:
                    # 尝试从完整日期中提取年份
                    match = re.search(r'(\d{4})', date_str)
                    if match:
                        year_in_data = int(match.group(1))

                if year_in_data and year_in_data != requested_year:
                    # 检测到跨年数据
                    return ReflectionResult(
                        success=False,
                        error_category=ErrorCategory.TYPE_MISMATCH,
                        error_message=f"用户请求{requested_year}年数据，但结果包含{year_in_data}年数据",
                        fix_suggestion=(
                            f"建议：\n"
                            f"1. 在WHERE子句中添加年份过滤：WHERE EXTRACT(YEAR FROM {time_field}) = {requested_year}\n"
                            f"2. 确保只返回用户指定时间范围内的数据\n"
                            f"3. 检查GROUP BY子句是否正确"
                        ),
                        should_retry=True,
                        confidence=0.7
                    )

        except (json.JSONDecodeError, ValueError, TypeError):
            # 无法解析JSON，跳过此检查
            pass

        return None

    def _check_trend_query_aggregation(
        self,
        messages: list,
        user_question: str,
        tool_content: str
    ) -> Optional[ReflectionResult]:
        """检查趋势查询是否使用了正确的聚合（GROUP BY）

        当用户问"趋势"、"变化"等分析性问题，但SQL没有使用聚合时，
        标记为需要修复。

        Args:
            messages: 消息列表
            user_question: 用户原始问题
            tool_content: 工具返回内容

        Returns:
            如果检测到趋势查询缺少聚合，返回ReflectionResult；否则返回None
        """
        # 🔧 趋势关键词模式
        trend_keywords = [
            '趋势', '变化', '增长', '下降', '时间序列', 'trend',
            '每月', '每年', '每月的', '每年的', '按月', '按年',
            '走势', '演变', '逐月', '逐年'
        ]

        # 检查用户问题是否包含趋势关键词
        has_trend_keyword = any(kw in user_question for kw in trend_keywords)
        if not has_trend_keyword:
            return None

        # 🔧 查找最近的 SQL 查询（从 AIMessage 的 tool_calls 中）
        sql_query = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') in ['query', 'execute_sql', 'sql_query']:
                        args = tc.get('args', {})
                        sql_query = args.get('query') or args.get('sql', '')
                        if sql_query:
                            break
                if sql_query:
                    break

        if not sql_query:
            return None

        # 🔧 检查 SQL 是否缺少 GROUP BY 或聚合函数
        sql_upper = sql_query.upper()

        # 检查是否有 GROUP BY
        has_group_by = 'GROUP BY' in sql_upper

        # 检查是否有聚合函数（COUNT, SUM, AVG, MAX, MIN）
        has_aggregation = any(
            agg in sql_upper
            for agg in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN(', 'COUNT (', 'SUM (', 'AVG (', 'MAX (', 'MIN (']
        )

        # 如果是趋势查询但没有聚合，返回修复建议
        # 注意：不检查 is_select_star，因为任何非聚合查询（即使指定了列）都不适合趋势分析
        if not (has_group_by or has_aggregation):
            # 尝试提取表名和可能的日期字段
            table_match = re.search(r'FROM\s+(\w+)', sql_upper, re.IGNORECASE)
            table_name = table_match.group(1) if table_match else "表名"

            return ReflectionResult(
                success=False,
                error_category=ErrorCategory.TYPE_MISMATCH,
                error_message="趋势分析查询缺少聚合，返回了原始数据而非聚合结果",
                fix_suggestion=f"""**趋势查询需要使用聚合！**

**问题**: 用户询问"{user_question[:30]}..."这类趋势分析问题，但你使用了 `SELECT *` 返回所有原始数据。

**必须执行的修改**：
1. 使用 `GROUP BY` 按时间维度分组（如按月、按年）
2. 使用聚合函数计算指标（如 SUM、COUNT、AVG）
3. 使用时间截断函数：DATE_TRUNC、EXTRACT、TO_CHAR

**正确示例**（按月统计）：
```sql
SELECT
    DATE_TRUNC('month', 时间字段) as 月份,
    SUM(金额字段) as 总金额,
    COUNT(*) as 订单数
FROM {table_name}
WHERE EXTRACT(YEAR FROM 时间字段) = 2023
GROUP BY DATE_TRUNC('month', 时间字段)
ORDER BY 月份
```

**正确示例**（按年统计）：
```sql
SELECT
    EXTRACT(YEAR FROM 时间字段) as 年份,
    SUM(金额字段) as 年度总额
FROM {table_name}
GROUP BY EXTRACT(YEAR FROM 时间字段)
ORDER BY 年份
```

**记住**：趋势分析问题必须使用 GROUP BY + 聚合函数！""",
                should_retry=True,
                confidence=0.9
            )

        # 如果有聚合但没有 GROUP BY，可能存在语法问题
        # 注意：不检查 is_select_star，因为聚合查询不可能同时是 SELECT *
        if has_aggregation and not has_group_by:
            return ReflectionResult(
                success=False,
                error_category=ErrorCategory.SQL_SYNTAX,
                error_message="SQL 查询中使用了聚合函数但缺少 GROUP BY 子句",
                fix_suggestion="使用聚合函数时必须配合 GROUP BY 子句对非聚合字段进行分组",
                should_retry=True,
                confidence=0.8
            )

        return None

    def _identify_error(self, content: str) -> Optional[ErrorCategory]:
        """识别错误类型

        Args:
            content: 错误内容

        Returns:
            错误类别，未识别返回 None
        """
        content_lower = content.lower()

        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    return category

        return ErrorCategory.UNKNOWN

    def _extract_error_message(self, content: str) -> str:
        """提取错误消息

        Args:
            content: 完整内容

        Returns:
            错误消息
        """
        # 尝试提取错误行
        lines = content.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['error', 'failed', 'exception']):
                return line.strip()

        return content[:200]  # 返回前 200 字符

    def _generate_fix_suggestion(
        self,
        error_category: ErrorCategory,
        content: str
    ) -> str:
        """生成修复建议

        Args:
            error_category: 错误类别
            content: 错误内容

        Returns:
            修复建议
        """
        suggestions = {
            ErrorCategory.COLUMN_NOT_FOUND: (
                "建议：\n"
                "1. 使用 get_schema() 查看表结构，确认正确的列名\n"
                "2. 检查列名拼写是否正确\n"
                "3. 尝试使用 resolve_business_term() 获取正确的字段名"
            ),
            ErrorCategory.TABLE_NOT_FOUND: (
                "建议：\n"
                "1. 使用 list_tables() 查看可用的表名\n"
                "2. 检查表名拼写是否正确\n"
                "3. 确认表名是否需要添加引号或双引号"
            ),
            ErrorCategory.SQL_SYNTAX: (
                "建议：\n"
                "1. 检查 SQL 语法，特别注意引号和逗号\n"
                "2. 确保 WHERE 子句在 GROUP BY 之前\n"
                "3. 检查 LIMIT 子句位置（应在最后）"
            ),
            ErrorCategory.TYPE_MISMATCH: (
                "建议：\n"
                "1. 使用 get_schema() 检查字段数据类型\n"
                "2. 对字段进行类型转换（CAST）\n"
                "3. 检查是否在数值字段上使用了字符串操作"
            ),
            ErrorCategory.RELATION_ERROR: (
                "建议：\n"
                "1. 检查 JOIN 条件是否正确\n"
                "2. 确认关联字段是否存在\n"
                "3. 尝试使用更简单的查询，逐步添加 JOIN"
            ),
            ErrorCategory.PERMISSION_ERROR: (
                "建议：\n"
                "权限不足，无法执行此操作。\n"
                "请只使用 SELECT 查询，不要尝试修改数据。"
            ),
            ErrorCategory.EMPTY_RESULT: (
                "建议：\n"
                "查询成功但没有返回数据。\n"
                "尝试放宽查询条件或检查数据是否存在。"
            ),
            ErrorCategory.UNKNOWN: (
                "建议：\n"
                "发生了未知错误。\n"
                "尝试简化查询或重新描述问题。"
            ),
        }

        return suggestions.get(
            error_category,
            "建议：请尝试重新描述问题或简化查询。"
        )

    def _trigger_learning(
        self,
        state: MessagesState,
        reflection: ReflectionResult
    ) -> Optional[Dict[str, Any]]:
        """触发学习循环

        当检测到错误时，将错误信息传递给学习引擎，
        保存到动态学习库供后续参考。

        Args:
            state: LangGraph 消息状态
            reflection: 反思结果

        Returns:
            学习数据字典，如果不触发学习则返回 None
        """
        # 只在检测到错误时触发学习
        if reflection.success or reflection.confidence > self.learning_threshold:
            return None

        try:
            # 提取租户 ID
            tenant_id = state.get("tenant_id", "default_tenant")

            # 提取用户问题和 SQL
            user_question = self._extract_user_question_from_state(state)
            sql_query = self._extract_sql_query_from_state(state)

            # 准备学习数据
            error_category = reflection.error_category or ErrorCategory.UNKNOWN
            error_message = reflection.error_message
            fix_suggestion = reflection.fix_suggestion

            # 返回学习数据（由外部决定如何处理）
            learning_data = {
                "error_category": error_category.value,
                "error_message": error_message,
                "fix_suggestion": fix_suggestion,
                "original_query": sql_query,
                "question": user_question,
                "tenant_id": tenant_id,
                "timestamp": self._get_timestamp()
            }

            logger.info(f"[ReflectionNode] 学习数据已准备: {error_category.value}")
            return learning_data

        except Exception as e:
            logger.error(f"[ReflectionNode] 触发学习失败: {e}")
            return None

    def _extract_user_question_from_state(self, state: MessagesState) -> str:
        """从状态中提取用户问题

        Args:
            state: LangGraph 消息状态

        Returns:
            用户问题
        """
        messages = state.get("messages", [])
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str):
                    return content
                elif isinstance(content, list) and len(content) > 0:
                    return str(content[0]) if isinstance(content[0], str) else ""
        return ""

    def _extract_sql_query_from_state(self, state: MessagesState) -> Optional[str]:
        """从状态中提取 SQL 查询

        Args:
            state: LangGraph 消息状态

        Returns:
            SQL 查询字符串
        """
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') in ['query', 'execute_sql', 'sql_query', 'execute_query']:
                        args = tc.get('args', {})
                        sql = args.get('query') or args.get('sql', '')
                        if sql:
                            return sql
        return None

    def _get_timestamp(self) -> str:
        """获取当前时间戳

        Returns:
            ISO 格式的时间戳字符串
        """
        from datetime import datetime
        return datetime.now().isoformat()

    def _log_reflection(self, reflection: ReflectionResult) -> None:
        """记录反思结果

        Args:
            reflection: 反思结果
        """
        if reflection.success:
            logger.info("[ReflectionNode] 执行成功")
        else:
            logger.warning(
                f"[ReflectionNode] 检测到错误: {reflection.error_category}"
            )
            logger.warning(f"  错误消息: {reflection.error_message}")
            logger.info(f"  修复建议: {reflection.fix_suggestion}")
            logger.info(f"  需要重试: {reflection.should_retry}")

    def _create_reflection_message(
        self,
        reflection: ReflectionResult,
        learning_data: Optional[Dict[str, Any]] = None
    ) -> AIMessage:
        """创建反思消息

        Args:
            reflection: 反思结果
            learning_data: 学习数据（可选）

        Returns:
            AI 消息
        """
        if reflection.success:
            content = "**执行成功**\n\n查询已成功执行，结果符合预期。"
        else:
            content = f"""**执行失败，正在进行自我修正**

**错误类型**: {reflection.error_category.value if reflection.error_category else '未知'}

**错误信息**: {reflection.error_message}

{reflection.fix_suggestion}

{'正在重新生成查询...' if reflection.should_retry else '已达到最大重试次数，请尝试重新描述问题。'}
"""

        return AIMessage(content=content)

    def should_continue(self, state: MessagesState) -> bool:
        """判断是否应该继续执行（用于路由）

        Args:
            state: 消息状态

        Returns:
            是否继续
        """
        retry_count = state.get("__retry_count__", 0)
        should_retry = state.get("__should_retry__", False)

        return should_retry and retry_count < self.max_retries


def create_reflection_node(
    max_retries: int = 3,
    enable_logging: bool = True,
    enable_learning: bool = True,  # 新增：是否启用学习循环
    learning_threshold: float = 0.5  # 新增：触发学习的最低置信度阈值
) -> ReflectionNode:
    """创建反思节点

    Args:
        max_retries: 最大重试次数
        enable_logging: 是否启用日志
        enable_learning: 是否启用学习循环（将错误传递给学习引擎）
        learning_threshold: 触发学习的最低置信度阈值

    Returns:
        ReflectionNode 实例
    """
    return ReflectionNode(
        max_retries=max_retries,
        enable_logging=enable_logging,
        enable_learning=enable_learning,
        learning_threshold=learning_threshold
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("反思节点测试")
    print("=" * 60)

    node = ReflectionNode()

    # 测试内容
    test_contents = [
        ("成功", "[]", True),
        ("列不存在", "column 'invalid_column' does not exist", False),
        ("表不存在", "relation 'unknown_table' does not exist", False),
        ("语法错误", "syntax error near 'SELECT'", False),
        ("空结果", "no data found", True),
    ]

    for name, content, expected_success in test_contents:
        print(f"\n[测试] {name}")
        result = node._analyze_content(content)
        print(f"  成功: {result.success}")
        print(f"  错误类别: {result.error_category}")
        print(f"  需要重试: {result.should_retry}")
        print(f"  置信度: {result.confidence}")
