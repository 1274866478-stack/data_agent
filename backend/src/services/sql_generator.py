"""
SQL Generation Service for Data Agent V4 Backend
Enhanced with ZhipuAI integration for intelligent SQL generation
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..models.rag_sql import (
    QueryIntent,
    SQLQuery,
    QueryType,
    DatabaseSchema,
    TableInfo,
    ColumnInfo,
)

logger = logging.getLogger(__name__)

# Import ZhipuAI service for intelligent SQL generation
try:
    from ..app.services.zhipu_client import zhipu_service
    ZHIPUAI_AVAILABLE = True
    logger.info("智谱AI服务已成功集成到SQL生成器")
except ImportError as e:
    ZHIPUAI_AVAILABLE = False
    logger.warning(f"智谱AI服务集成失败，将使用模板模式: {e}")
    zhipu_service = None


class SQLGenerator:
    """Service for generating SQL queries from natural language intent with AI enhancement"""

    def __init__(self, use_ai: bool = True):
        """
        Initialize SQL Generator with optional AI enhancement

        Args:
            use_ai: Whether to use ZhipuAI for intelligent SQL generation
        """
        self.use_ai = use_ai and ZHIPUAI_AVAILABLE

        # SQL templates for different query types (fallback)
        self.templates = {
            QueryType.SELECT: "SELECT {columns} FROM {table}{where}{order}{limit}",
            QueryType.AGGREGATE: "SELECT {aggregations} FROM {table}{where}{group_by}{having}{order}{limit}",
            QueryType.JOIN: "SELECT {columns} FROM {table}{joins}{where}{order}{limit}",
            QueryType.FILTER: "SELECT {columns} FROM {table}{where}{order}{limit}",
            QueryType.SORT: "SELECT {columns} FROM {table}{where}{order}{limit}"
        }

        if self.use_ai:
            logger.info("SQL生成器初始化完成，启用智谱AI增强模式")
        else:
            logger.info("SQL生成器初始化完成，使用模板模式")

        # Common SQL keywords mapping
        self.keyword_mapping = {
            'where': ['where', 'when', 'if', 'that', 'which', 'who'],
            'and': ['and', 'with', 'also', 'plus'],
            'or': ['or', 'either'],
            'like': ['containing', 'includes', 'like', 'similar'],
            'in': ['in', 'among', 'within'],
            'between': ['between', 'betwixt'],
            'order by': ['order by', 'sort by', 'arrange by'],
            'group by': ['group by', 'grouped by', 'per', 'each'],
            'having': ['having', 'with condition']
        }

    async def generate_sql(
        self,
        intent: QueryIntent,
        schema: DatabaseSchema,
        natural_query: Optional[str] = None
    ) -> SQLQuery:
        """
        Generate SQL query from analyzed intent with AI enhancement

        Args:
            intent: Analyzed query intent
            schema: Database schema
            natural_query: Original natural language query (for AI generation)

        Returns:
            SQLQuery: Generated SQL query
        """
        try:
            # Validate intent
            if not intent.target_tables:
                raise ValueError("No target tables identified")

            # Try AI generation first if available
            if self.use_ai and natural_query and zhipu_service:
                logger.info("尝试使用智谱AI生成SQL查询")
                try:
                    ai_sql = await self._generate_sql_with_ai(natural_query, intent, schema)
                    if ai_sql:
                        logger.info("智谱AI成功生成SQL查询")
                        return ai_sql
                except Exception as e:
                    logger.warning(f"智谱AI生成失败，回退到模板模式: {e}")

            # Fallback to template-based generation
            logger.info("使用模板模式生成SQL查询")
            if intent.query_type == QueryType.JOIN:
                sql_query = await self._generate_join_query(intent, schema)
            elif intent.query_type == QueryType.AGGREGATE:
                sql_query = await self._generate_aggregate_query(intent, schema)
            else:
                sql_query = await self._generate_select_query(intent, schema)

            # Post-process SQL
            formatted_sql = self._format_sql(sql_query['query'])

            return SQLQuery(
                query=formatted_sql,
                parameters=sql_query.get('parameters', []),
                query_type=intent.query_type,
                estimated_cost=sql_query.get('estimated_cost'),
                execution_plan=sql_query.get('execution_plan')
            )

        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            raise

    async def _generate_select_query(
        self,
        intent: QueryIntent,
        schema: DatabaseSchema
    ) -> Dict[str, Any]:
        """Generate SELECT query"""
        main_table = intent.target_tables[0]
        table_info = schema.tables.get(main_table)

        if not table_info:
            raise ValueError(f"Table {main_table} not found in schema")

        # Generate column list
        columns = self._generate_column_list(intent.target_columns, main_table, schema)

        # Generate WHERE clause
        where_clause = self._generate_where_clause(intent.conditions, schema)

        # Generate ORDER BY clause
        order_clause = self._generate_order_clause(intent.orderings, schema)

        # Generate LIMIT clause
        limit_clause = self._generate_limit_clause(intent.orderings)

        # Build query
        query_parts = [f"SELECT {columns}"]
        query_parts.append(f"FROM {main_table}")

        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        if order_clause:
            query_parts.append(f"ORDER BY {order_clause}")

        if limit_clause:
            query_parts.append(limit_clause)

        query = " ".join(query_parts)

        return {
            'query': query,
            'parameters': [],
            'estimated_cost': self._estimate_query_cost(intent, query)
        }

    async def _generate_join_query(
        self,
        intent: QueryIntent,
        schema: DatabaseSchema
    ) -> Dict[str, Any]:
        """Generate JOIN query"""
        if len(intent.target_tables) < 2:
            return await self._generate_select_query(intent, schema)

        main_table = intent.target_tables[0]
        join_tables = intent.target_tables[1:]

        # Generate column list with table prefixes
        columns = self._generate_join_column_list(intent.target_columns, intent.target_tables, schema)

        # Generate JOIN clauses
        join_clauses = self._generate_join_clauses(main_table, join_tables, schema)

        # Generate WHERE clause
        where_clause = self._generate_where_clause(intent.conditions, schema)

        # Generate ORDER BY clause
        order_clause = self._generate_order_clause(intent.orderings, schema)

        # Generate LIMIT clause
        limit_clause = self._generate_limit_clause(intent.orderings)

        # Build query
        query_parts = [f"SELECT {columns}"]
        query_parts.append(f"FROM {main_table}")

        for join_clause in join_clauses:
            query_parts.append(join_clause)

        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        if order_clause:
            query_parts.append(f"ORDER BY {order_clause}")

        if limit_clause:
            query_parts.append(limit_clause)

        query = " ".join(query_parts)

        return {
            'query': query,
            'parameters': [],
            'estimated_cost': self._estimate_query_cost(intent, query)
        }

    async def _generate_aggregate_query(
        self,
        intent: QueryIntent,
        schema: DatabaseSchema
    ) -> Dict[str, Any]:
        """Generate aggregate query"""
        main_table = intent.target_tables[0]

        # Generate aggregate expressions
        aggregates = self._generate_aggregate_expressions(intent.aggregations, intent.target_columns, schema)

        # Generate GROUP BY clause
        group_by_clause = self._generate_group_by_clause(intent.groupings, schema)

        # Generate HAVING clause
        having_clause = self._generate_having_clause(intent.conditions, schema)

        # Generate WHERE clause
        where_clause = self._generate_where_clause(intent.conditions, schema, exclude_having=True)

        # Generate ORDER BY clause
        order_clause = self._generate_order_clause(intent.orderings, schema)

        # Generate LIMIT clause
        limit_clause = self._generate_limit_clause(intent.orderings)

        # Build query
        query_parts = [f"SELECT {aggregates}"]
        query_parts.append(f"FROM {main_table}")

        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        if group_by_clause:
            query_parts.append(f"GROUP BY {group_by_clause}")

        if having_clause:
            query_parts.append(f"HAVING {having_clause}")

        if order_clause:
            query_parts.append(f"ORDER BY {order_clause}")

        if limit_clause:
            query_parts.append(limit_clause)

        query = " ".join(query_parts)

        return {
            'query': query,
            'parameters': [],
            'estimated_cost': self._estimate_query_cost(intent, query)
        }

    def _generate_column_list(
        self,
        target_columns: List[str],
        main_table: str,
        schema: DatabaseSchema
    ) -> str:
        """Generate column list for SELECT clause"""
        if not target_columns:
            return f"{main_table}.*"

        columns = []
        table_info = schema.tables.get(main_table)

        for column_ref in target_columns:
            if '.' in column_ref:
                table_name, column_name = column_ref.split('.', 1)
                if table_name == main_table and table_info:
                    # Verify column exists
                    if any(col.name == column_name for col in table_info.columns):
                        columns.append(f"{table_name}.{column_name}")
            else:
                # Assume column belongs to main table
                if table_info and any(col.name == column_ref for col in table_info.columns):
                    columns.append(f"{main_table}.{column_ref}")

        # Fallback to all columns if no valid columns found
        if not columns:
            return f"{main_table}.*"

        return ", ".join(columns)

    def _generate_join_column_list(
        self,
        target_columns: List[str],
        target_tables: List[str],
        schema: DatabaseSchema
    ) -> str:
        """Generate column list for JOIN query"""
        if not target_columns:
            # Return all columns from all tables
            columns = []
            for table in target_tables:
                columns.append(f"{table}.*")
            return ", ".join(columns)

        columns = []
        for column_ref in target_columns:
            if '.' in column_ref:
                table_name, column_name = column_ref.split('.', 1)
                if table_name in target_tables:
                    table_info = schema.tables.get(table_name)
                    if table_info and any(col.name == column_name for col in table_info.columns):
                        columns.append(f"{table_name}.{column_name}")
            else:
                # Try to find column in any target table
                for table in target_tables:
                    table_info = schema.tables.get(table)
                    if table_info and any(col.name == column_ref for col in table_info.columns):
                        columns.append(f"{table}.{column_ref}")
                        break

        return ", ".join(columns) if columns else "*"

    def _generate_join_clauses(
        self,
        main_table: str,
        join_tables: List[str],
        schema: DatabaseSchema
    ) -> List[str]:
        """Generate JOIN clauses"""
        join_clauses = []
        main_table_info = schema.tables.get(main_table)

        for join_table in join_tables:
            join_table_info = schema.tables.get(join_table)
            if not join_table_info:
                continue

            # Find foreign key relationships
            join_condition = self._find_join_condition(main_table_info, join_table_info)

            if join_condition:
                join_clauses.append(f"JOIN {join_table} ON {join_condition}")
            else:
                # Try to find relationship the other way
                reverse_condition = self._find_join_condition(join_table_info, main_table_info)
                if reverse_condition:
                    join_clauses.append(f"JOIN {join_table} ON {reverse_condition}")
                else:
                    # Cross join if no relationship found
                    join_clauses.append(f"CROSS JOIN {join_table}")

        return join_clauses

    def _find_join_condition(self, table1_info: TableInfo, table2_info: TableInfo) -> Optional[str]:
        """Find join condition between two tables"""
        # Look for foreign key relationships
        for column in table1_info.columns:
            if column.is_foreign_key and column.foreign_table == table2_info.name:
                return f"{table1_info.name}.{column.name} = {table2_info.name}.{column.foreign_column}"

        # Look for matching primary key names
        pk_columns_1 = [col.name for col in table1_info.columns if col.is_primary_key]
        pk_columns_2 = [col.name for col in table2_info.columns if col.is_primary_key]

        for pk1 in pk_columns_1:
            for pk2 in pk_columns_2:
                if pk1.lower() == pk2.lower() or pk1.lower().endswith(f"_{pk2.lower()}") or pk2.lower().endswith(f"_{pk1.lower()}"):
                    return f"{table1_info.name}.{pk1} = {table2_info.name}.{pk2}"

        # Look for common column names
        common_columns = set(col.name for col in table1_info.columns) & set(col.name for col in table2_info.columns)
        for column in common_columns:
            if column not in ['id', 'created_at', 'updated_at']:  # Skip generic columns
                return f"{table1_info.name}.{column} = {table2_info.name}.{column}"

        return None

    def _generate_where_clause(
        self,
        conditions: List[str],
        schema: DatabaseSchema,
        exclude_having: bool = False
    ) -> str:
        """Generate WHERE clause"""
        if not conditions:
            return ""

        where_conditions = []
        for condition in conditions:
            sql_condition = self._convert_condition_to_sql(condition, schema)
            if sql_condition:
                where_conditions.append(sql_condition)

        return " AND ".join(where_conditions) if where_conditions else ""

    def _convert_condition_to_sql(self, condition: str, schema: DatabaseSchema) -> Optional[str]:
        """Convert natural language condition to SQL condition"""
        condition_lower = condition.lower()

        # Time conditions
        if any(word in condition_lower for word in ['today', 'yesterday', 'this week', 'this month']):
            return self._convert_time_condition(condition)

        # Comparison conditions
        comparison_operators = {
            'greater than': '>',
            'more than': '>',
            'less than': '<',
            'fewer than': '<',
            'equal to': '=',
            'equals': '=',
            'not equal': '!=',
            'between': 'BETWEEN'
        }

        for operator_text, operator in comparison_operators.items():
            if operator_text in condition_lower:
                return self._convert_comparison_condition(condition, operator, schema)

        # Text matching conditions
        if any(word in condition_lower for word in ['containing', 'includes', 'like']):
            return self._convert_text_condition(condition, schema)

        # List conditions
        if 'in' in condition_lower or 'among' in condition_lower:
            return self._convert_in_condition(condition, schema)

        return None

    def _convert_time_condition(self, condition: str) -> str:
        """Convert time-based condition to SQL"""
        condition_lower = condition.lower()

        if 'today' in condition_lower:
            return "CURRENT_DATE"
        elif 'yesterday' in condition_lower:
            return "CURRENT_DATE - INTERVAL '1 day'"
        elif 'this week' in condition_lower:
            return "date_trunc('week', CURRENT_DATE)"
        elif 'this month' in condition_lower:
            return "date_trunc('month', CURRENT_DATE)"
        elif 'last week' in condition_lower:
            return "date_trunc('week', CURRENT_DATE - INTERVAL '1 week')"
        elif 'last month' in condition_lower:
            return "date_trunc('month', CURRENT_DATE - INTERVAL '1 month')"
        else:
            return "CURRENT_DATE"

    def _convert_comparison_condition(
        self,
        condition: str,
        operator: str,
        schema: DatabaseSchema
    ) -> str:
        """Convert comparison condition to SQL"""
        # Extract number and column
        number_match = re.search(r'(\d+(?:\.\d+)?)', condition)
        if number_match:
            number = number_match.group(1)
            # Try to find column name in the condition
            words = condition.lower().split()
            column_name = None

            for table_name, table_info in schema.tables.items():
                for column in table_info.columns:
                    if column.name.lower() in words:
                        column_name = f"{table_name}.{column.name}"
                        break

            if column_name:
                return f"{column_name} {operator} {number}"

        return condition

    def _convert_text_condition(self, condition: str, schema: DatabaseSchema) -> str:
        """Convert text matching condition to SQL"""
        # Try to extract column and value
        words = condition.split()
        column_name = None
        search_value = None

        for table_name, table_info in schema.tables.items():
            for column in table_info.columns:
                if column.name.lower() in condition.lower():
                    column_name = f"{table_name}.{column.name}"
                    # Find the word after the column name as search value
                    column_index = condition.lower().find(column.name.lower())
                    if column_index != -1:
                        remaining_text = condition[column_index + len(column.name):].strip()
                        search_words = remaining_text.split()
                        if search_words:
                            search_value = search_words[0].strip('.,!?')
                    break

        if column_name and search_value:
            return f"{column_name} LIKE '%{search_value}%'"

        return condition

    def _convert_in_condition(self, condition: str, schema: DatabaseSchema) -> str:
        """Convert IN condition to SQL"""
        # Extract list items
        list_match = re.search(r'\((.*?)\)', condition)
        if list_match:
            items = [item.strip() for item in list_match.group(1).split(',')]
            formatted_items = ["'" + item + "'" for item in items]
            return f"IN ({', '.join(formatted_items)})"

        return condition

    def _generate_aggregate_expressions(
        self,
        aggregations: List[str],
        target_columns: List[str],
        schema: DatabaseSchema
    ) -> str:
        """Generate aggregate expressions"""
        if not aggregations:
            return "COUNT(*)"

        expressions = []
        for agg in aggregations:
            if agg.upper() == 'COUNT':
                if target_columns:
                    column_ref = target_columns[0]
                    expressions.append(f"COUNT({column_ref})")
                else:
                    expressions.append("COUNT(*)")
            elif agg.upper() == 'SUM':
                if target_columns:
                    column_ref = target_columns[0]
                    expressions.append(f"SUM({column_ref})")
                else:
                    expressions.append("SUM(*)")
            elif agg.upper() == 'AVG':
                if target_columns:
                    column_ref = target_columns[0]
                    expressions.append(f"AVG({column_ref})")
                else:
                    expressions.append("AVG(*)")
            elif agg.upper() == 'MAX':
                if target_columns:
                    column_ref = target_columns[0]
                    expressions.append(f"MAX({column_ref})")
                else:
                    expressions.append("MAX(*)")
            elif agg.upper() == 'MIN':
                if target_columns:
                    column_ref = target_columns[0]
                    expressions.append(f"MIN({column_ref})")
                else:
                    expressions.append("MIN(*)")
            else:
                expressions.append(agg)

        return ", ".join(expressions)

    def _generate_group_by_clause(
        self,
        groupings: List[str],
        schema: DatabaseSchema
    ) -> str:
        """Generate GROUP BY clause"""
        if not groupings:
            return ""

        group_columns = []
        for grouping in groupings:
            # Try to find the full column reference
            for table_name, table_info in schema.tables.items():
                for column in table_info.columns:
                    if column.name.lower() == grouping.lower():
                        group_columns.append(f"{table_name}.{column.name}")
                        break

        return ", ".join(group_columns) if group_columns else grouping

    def _generate_having_clause(
        self,
        conditions: List[str],
        schema: DatabaseSchema
    ) -> str:
        """Generate HAVING clause"""
        # HAVING is similar to WHERE but for aggregate functions
        aggregate_conditions = []
        for condition in conditions:
            if any(agg in condition.lower() for agg in ['sum', 'count', 'avg', 'max', 'min']):
                sql_condition = self._convert_condition_to_sql(condition, schema)
                if sql_condition:
                    aggregate_conditions.append(sql_condition)

        return " AND ".join(aggregate_conditions) if aggregate_conditions else ""

    def _generate_order_clause(
        self,
        orderings: List[str],
        schema: DatabaseSchema
    ) -> str:
        """Generate ORDER BY clause"""
        if not orderings:
            return ""

        order_expressions = []
        for ordering in orderings:
            if 'LIMIT' in ordering.upper():
                continue

            # Extract column and direction
            parts = ordering.split()
            if len(parts) >= 2:
                column = parts[0]
                direction = parts[1].upper() if parts[1].upper() in ['ASC', 'DESC'] else 'ASC'

                # Try to find full column reference
                for table_name, table_info in schema.tables.items():
                    for column_info in table_info.columns:
                        if column_info.name.lower() == column.lower():
                            order_expressions.append(f"{table_name}.{column_info.name} {direction}")
                            break
            else:
                # Just a column name, default to ASC
                column = ordering
                for table_name, table_info in schema.tables.items():
                    for column_info in table_info.columns:
                        if column_info.name.lower() == column.lower():
                            order_expressions.append(f"{table_name}.{column_info.name} ASC")
                            break

        return ", ".join(order_expressions) if order_expressions else ""

    def _generate_limit_clause(self, orderings: List[str]) -> str:
        """Generate LIMIT clause"""
        for ordering in orderings:
            if 'LIMIT' in ordering.upper():
                limit_match = re.search(r'LIMIT\s+(\d+)', ordering, re.IGNORECASE)
                if limit_match:
                    return f"LIMIT {limit_match.group(1)}"

            # Check for other limit patterns
            limit_match = re.search(r'(?:top|first|show only)\s+(\d+)', ordering, re.IGNORECASE)
            if limit_match:
                return f"LIMIT {limit_match.group(1)}"

        return ""

    def _format_sql(self, sql: str) -> str:
        """Format SQL for readability"""
        # Basic formatting - can be enhanced with SQL formatter library
        formatted = sql.strip()

        # Add proper spacing around keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'ON', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 'AND', 'OR']
        for keyword in keywords:
            formatted = re.sub(rf'\b{keyword}\b', keyword.upper(), formatted, flags=re.IGNORECASE)
            formatted = re.sub(rf'(\w+){keyword}', rf'\1 {keyword}', formatted, flags=re.IGNORECASE)
            formatted = re.sub(rf'{keyword}(\w+)', rf'{keyword} \1', formatted, flags=re.IGNORECASE)

        return formatted

    def _estimate_query_cost(self, intent: QueryIntent, query: str) -> float:
        """Estimate query execution cost"""
        base_cost = 1.0

        # Add cost for each table
        table_cost = len(intent.target_tables) * 0.5

        # Add cost for joins
        join_cost = max(0, len(intent.target_tables) - 1) * 2.0

        # Add cost for aggregations
        agg_cost = len(intent.aggregations) * 1.5

        # Add cost for conditions
        condition_cost = len(intent.conditions) * 0.3

        # Add cost for order by
        order_cost = 1.0 if intent.orderings else 0

        total_cost = base_cost + table_cost + join_cost + agg_cost + condition_cost + order_cost
        return round(total_cost, 2)

    async def generate_parameterized_query(
        self,
        intent: QueryIntent,
        schema: DatabaseSchema,
        parameters: Dict[str, Any]
    ) -> SQLQuery:
        """
        Generate parameterized SQL query with provided parameters

        Args:
            intent: Analyzed query intent
            schema: Database schema
            parameters: Parameter values

        Returns:
            SQLQuery: Parameterized SQL query
        """
        # Generate basic SQL first
        sql_query = await self.generate_sql(intent, schema)

        # Convert to parameterized form if parameters are provided
        if parameters:
            param_query = self._convert_to_parameterized(sql_query.query, parameters)
            param_values = list(parameters.values())

            return SQLQuery(
                query=param_query,
                parameters=param_values,
                query_type=intent.query_type,
                estimated_cost=sql_query.estimated_cost
            )

        return sql_query

    def _convert_to_parameterized(self, query: str, parameters: Dict[str, Any]) -> str:
        """Convert query to use parameter placeholders"""
        param_query = query
        param_index = 1

        for param_name, param_value in parameters.items():
            # Replace literal values with parameter placeholders
            if isinstance(param_value, str):
                param_query = param_query.replace(f"'{param_value}'", f"${param_index}")
            else:
                param_query = param_query.replace(str(param_value), f"${param_index}")
            param_index += 1

        return param_query

    async def _generate_sql_with_ai(
        self,
        natural_query: str,
        intent: QueryIntent,
        schema: DatabaseSchema
    ) -> Optional[SQLQuery]:
        """
        Generate SQL query using ZhipuAI with enhanced understanding

        Args:
            natural_query: Original natural language query
            intent: Analyzed query intent for context
            schema: Database schema

        Returns:
            SQLQuery if AI generation succeeds, None otherwise
        """
        try:
            # Prepare schema context for AI
            schema_text = await self._prepare_schema_context(schema)

            # Enhanced prompt with intent context
            context_prompt = f"""
你是专业的SQL查询生成专家。请根据用户的自然语言查询和数据库schema，生成准确的PostgreSQL SQL语句。

用户查询: {natural_query}

查询意图分析:
- 查询类型: {intent.query_type.value}
- 目标表: {', '.join(intent.target_tables)}
- 目标列: {', '.join(intent.target_columns) if intent.target_columns else '所有列'}
- 条件: {', '.join(intent.conditions) if intent.conditions else '无'}
- 排序: {', '.join(intent.orderings) if intent.orderings else '无'}
- 聚合函数: {', '.join(intent.aggregations) if intent.aggregations else '无'}

数据库Schema:
{schema_text}

生成要求:
1. 只返回SQL语句，不要包含任何解释
2. 使用PostgreSQL语法
3. 确保生成的SQL安全且高效
4. 只使用SELECT查询，严格禁止UPDATE、DELETE、DROP、INSERT等危险操作
5. 处理NULL值和字符串转义
6. 使用适当的LIMIT子句限制结果数量（默认LIMIT 100）
7. 表名使用完整的表名（带schema前缀如果适用）
8. 如果有多表关联，使用适当的JOIN语法
9. 对于日期时间查询，使用PostgreSQL日期函数
"""

            messages = [
                {
                    "role": "system",
                    "content": context_prompt
                },
                {
                    "role": "user",
                    "content": f"请为以下查询生成SQL语句：{natural_query}"
                }
            ]

            # Call ZhipuAI with optimized parameters for SQL generation
            response = await zhipu_service.chat_completion(
                messages=messages,
                max_tokens=1500,
                temperature=0.1,  # Low temperature for accuracy
                stream=False
            )

            if response and response.get("content"):
                sql_content = response["content"].strip()

                # Clean and format the SQL
                cleaned_sql = await self._clean_ai_generated_sql(sql_content)

                if cleaned_sql:
                    logger.info(f"智谱AI生成的SQL: {cleaned_sql[:200]}...")

                    # Validate the generated SQL
                    validation_result = await self._validate_ai_generated_sql(cleaned_sql, schema)
                    if validation_result['is_valid']:
                        return SQLQuery(
                            query=validation_result['sql'],
                            parameters=[],
                            query_type=intent.query_type,
                            estimated_cost=self._estimate_query_cost(intent, cleaned_sql),
                            execution_plan={
                                'method': 'ai_generated',
                                'model': getattr(zhipu_service, 'default_model', 'unknown'),
                                'confidence': validation_result.get('confidence', 0.8)
                            }
                        )
                    else:
                        logger.warning(f"智谱AI生成的SQL验证失败: {validation_result['error']}")
                else:
                    logger.warning("智谱AI生成的内容为空或格式不正确")
            else:
                logger.warning("智谱AI未返回有效响应")

            return None

        except Exception as e:
            logger.error(f"智谱AI生成SQL时出错: {e}")
            return None

    async def _prepare_schema_context(self, schema: DatabaseSchema) -> str:
        """
        Prepare database schema context for AI understanding

        Args:
            schema: Database schema

        Returns:
            Formatted schema text
        """
        schema_parts = []

        for table_name, table_info in schema.tables.items():
            table_desc = f"\n表名: {table_name}\n"
            table_desc += f"表描述: {table_info.description or '无描述'}\n"
            table_desc += "列信息:\n"

            for column in table_info.columns:
                column_desc = f"  - {column.name}: {column.data_type}"
                if column.is_primary_key:
                    column_desc += " (主键)"
                if column.is_foreign_key:
                    column_desc += f" (外键 -> {column.foreign_key_reference})"
                if not column.is_nullable:
                    column_desc += " (非空)"
                if column.default_value:
                    column_desc += f" (默认值: {column.default_value})"
                table_desc += f"{column_desc}\n"

            if table_info.relationships:
                table_desc += "关系:\n"
                for rel in table_info.relationships:
                    table_desc += f"  - {rel.type}: {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}\n"

            if table_info.sample_data:
                table_desc += "示例数据:\n"
                for i, sample in enumerate(table_info.sample_data[:3]):  # Limit to 3 samples
                    table_desc += f"  {i+1}. {sample}\n"

            schema_parts.append(table_desc)

        return "\n".join(schema_parts)

    async def _clean_ai_generated_sql(self, sql_content: str) -> Optional[str]:
        """
        Clean and format AI-generated SQL content

        Args:
            sql_content: Raw SQL content from AI

        Returns:
            Cleaned SQL string or None if invalid
        """
        if not sql_content:
            return None

        # Remove markdown code blocks
        sql = sql_content.strip()

        # Remove ```sql and ``` markers
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]

        # Remove any explanatory text
        lines = sql.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # Skip lines that look like explanations
            if (line and
                not line.startswith('--') and
                not line.startswith('#') and
                not line.lower().startswith('note:') and
                not line.lower().startswith('explanation:') and
                not line.lower().startswith('这个查询')):
                cleaned_lines.append(line)

        cleaned_sql = '\n'.join(cleaned_lines).strip()

        # Remove extra semicolons
        cleaned_sql = cleaned_sql.rstrip(';')
        cleaned_sql += ';'

        return cleaned_sql if cleaned_sql else None

    async def _validate_ai_generated_sql(
        self,
        sql: str,
        schema: DatabaseSchema
    ) -> Dict[str, Any]:
        """
        Validate AI-generated SQL for security and correctness

        Args:
            sql: Generated SQL
            schema: Database schema

        Returns:
            Validation result with is_valid flag and error message if invalid
        """
        try:
            sql_upper = sql.upper()

            # Security checks - forbidden keywords
            forbidden_keywords = [
                'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
                'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT',
                'REVOKE', 'UNION', 'COMMIT', 'ROLLBACK'
            ]

            for keyword in forbidden_keywords:
                if keyword in sql_upper:
                    return {
                        'is_valid': False,
                        'error': f'SQL包含禁止的关键词: {keyword}',
                        'confidence': 0.0
                    }

            # Basic SQL structure check
            if not sql_upper.strip().startswith('SELECT'):
                return {
                    'is_valid': False,
                    'error': '只允许SELECT查询',
                    'confidence': 0.0
                }

            # Table name validation against schema
            table_names = schema.tables.keys()
            for table_name in table_names:
                if table_name.upper() in sql_upper:
                    break
            else:
                # If no schema tables found, be more permissive
                logger.warning("SQL中未找到schema中的表名，但可能是有效的")

            # Check for dangerous patterns
            dangerous_patterns = [
                '--', '/*', '*/', 'xp_', 'sp_', '0x', 'waitfor delay'
            ]

            for pattern in dangerous_patterns:
                if pattern in sql:
                    return {
                        'is_valid': False,
                        'error': f'SQL包含危险模式: {pattern}',
                        'confidence': 0.0
                    }

            # If all checks pass
            return {
                'is_valid': True,
                'sql': sql,
                'confidence': 0.85  # High confidence for valid SQL
            }

        except Exception as e:
            return {
                'is_valid': False,
                'error': f'SQL验证时出错: {str(e)}',
                'confidence': 0.0
            }

    def get_ai_status(self) -> Dict[str, Any]:
        """
        Get AI service status and configuration

        Returns:
            Dictionary with AI service status
        """
        return {
            'ai_available': ZHIPUAI_AVAILABLE,
            'use_ai': self.use_ai,
            'model': getattr(zhipu_service, 'default_model', 'unknown') if zhipu_service else None,
            'fallback_enabled': True,
            'supported_query_types': [qt.value for qt in QueryType]
        }