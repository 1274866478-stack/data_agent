"""
数据库类型规范模块
为每种数据库类型提供方言特定的配置

此模块定义了不同数据库类型的函数映射和语法特性，
用于 AI 生成数据库特定的 SQL 查询。
"""
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """支持的数据库类型枚举"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"  # 用于 Excel/CSV 查询
    MSSQL = "mssql"
    ORACLE = "oracle"


@dataclass
class DatabaseSpec:
    """数据库规范配置"""
    db_type: DatabaseType
    display_name: str
    description: str
    date_functions: Dict[str, str]  # 功能描述 → SQL函数
    aggregation_functions: Dict[str, str]
    string_functions: Dict[str, str]
    syntax_notes: List[str]
    common_functions_example: str
    type_constraints: List[str] = None  # 列类型使用约束 (可选)


# 数据库规范映射表
DATABASE_SPECS: Dict[DatabaseType, DatabaseSpec] = {
    DatabaseType.POSTGRESQL: DatabaseSpec(
        db_type=DatabaseType.POSTGRESQL,
        display_name="PostgreSQL",
        description="开源对象关系数据库系统",
        date_functions={
            "年份提取": "EXTRACT(YEAR FROM date_column)",
            "月份提取": "EXTRACT(MONTH FROM date_column)",
            "日期格式化": "TO_CHAR(date_column, 'YYYY-MM-DD')",
            "年月格式化": "TO_CHAR(date_column, 'YYYY-MM')",
            "日期截断到月": "DATE_TRUNC('month', date_column)",
            "字符串转日期": "date_string::date",
            "字符串转时间戳": "TO_TIMESTAMP(date_string, 'YYYY-MM-DD')",
            "当前时间": "NOW()",
            "当前日期": "CURRENT_DATE",
            "日期加减": "date_column + INTERVAL '1 day'",
            "日期差": "date_column1 - date_column2",
        },
        aggregation_functions={
            "求和": "SUM(column)",
            "平均": "AVG(column)",
            "计数": "COUNT(*)",
            "去重计数": "COUNT(DISTINCT column)",
            "最大值": "MAX(column)",
            "最小值": "MIN(column)",
        },
        string_functions={
            "字符串连接": "string1 || string2",
            "字符串转大写": "UPPER(string)",
            "字符串转小写": "LOWER(string)",
            "子字符串": "SUBSTRING(string FROM start FOR length)",
            "字符串长度": "LENGTH(string)",
            "去除空格": "TRIM(string)",
        },
        syntax_notes=[
            "支持 CTE (WITH 语)",
            "支持窗口函数 (OVER)",
            "支持 JSON 操作符 ->> 和 ->",
            "支持 FULL OUTER JOIN",
            "字符串连接使用 || 而非 CONCAT()",
        ],
        common_functions_example="""
-- 年份提取
SELECT EXTRACT(YEAR FROM order_date) as year FROM orders;

-- 日期格式化
SELECT TO_CHAR(order_date, 'YYYY-MM-DD') as formatted_date FROM orders;

-- 按月分组
SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) FROM orders GROUP BY 1;
"""
    ),

    DatabaseType.MYSQL: DatabaseSpec(
        db_type=DatabaseType.MYSQL,
        display_name="MySQL",
        description="流行的开源关系数据库",
        date_functions={
            "年份提取": "YEAR(date_column)",
            "月份提取": "MONTH(date_column)",
            "日期格式化": "DATE_FORMAT(date_column, '%Y-%m-%d')",
            "年月格式化": "DATE_FORMAT(date_column, '%Y-%m')",
            "日期截断到月": "DATE_FORMAT(date_column, '%Y-%m-01')",
            "当前时间": "NOW()",
            "当前日期": "CURDATE()",
            "日期加减": "DATE_ADD(date_column, INTERVAL 1 day)",
            "日期差": "DATEDIFF(date_column1, date_column2)",
        },
        aggregation_functions={
            "求和": "SUM(column)",
            "平均": "AVG(column)",
            "计数": "COUNT(*)",
            "去重计数": "COUNT(DISTINCT column)",
            "最大值": "MAX(column)",
            "最小值": "MIN(column)",
        },
        string_functions={
            "字符串连接": "CONCAT(string1, string2)",
            "字符串转大写": "UPPER(string)",
            "字符串转小写": "LOWER(string)",
            "子字符串": "SUBSTRING(string, start, length)",
            "字符串长度": "LENGTH(string)",
            "去除空格": "TRIM(string)",
        },
        syntax_notes=[
            "MySQL 8.0+ 支持 CTE (WITH 语)",
            "不支持 FULL OUTER JOIN",
            "字符串连接使用 CONCAT() 而不是 ||",
            "日期时间函数区分大小写",
            "LIMIT 子句在最后",
        ],
        common_functions_example="""
-- 年份提取
SELECT YEAR(order_date) as year FROM orders;

-- 日期格式化
SELECT DATE_FORMAT(order_date, '%Y-%m-%d') as formatted_date FROM orders;

-- 按月分组
SELECT DATE_FORMAT(order_date, '%Y-%m-01') as month, SUM(amount) FROM orders GROUP BY 1;
"""
    ),

    DatabaseType.SQLITE: DatabaseSpec(
        db_type=DatabaseType.SQLITE,
        display_name="SQLite",
        description="轻量级嵌入式数据库",
        date_functions={
            "年份提取": "CAST(strftime('%Y', date_column) AS INTEGER)",
            "月份提取": "CAST(strftime('%m', date_column) AS INTEGER)",
            "日期格式化": "strftime('%Y-%m-%d', date_column)",
            "年月格式化": "strftime('%Y-%m', date_column)",
            "日期截断到月": "strftime('%Y-%m-01', date_column)",
            "当前时间": "datetime('now')",
            "当前日期": "date('now')",
            "日期加减": "datetime(date_column, '+1 day')",
            "日期差": "julianday(date_column1) - julianday(date_column2)",
        },
        aggregation_functions={
            "求和": "SUM(column)",
            "平均": "AVG(column)",
            "计数": "COUNT(*)",
            "去重计数": "COUNT(DISTINCT column)",
            "最大值": "MAX(column)",
            "最小值": "MIN(column)",
        },
        string_functions={
            "字符串连接": "string1 || string2",
            "字符串转大写": "UPPER(string)",
            "字符串转小写": "LOWER(string)",
            "子字符串": "SUBSTRING(string, start, length)",
            "字符串长度": "LENGTH(string)",
            "去除空格": "TRIM(string)",
        },
        syntax_notes=[
            "不支持 RIGHT OUTER JOIN",
            "日期时间作为字符串存储",
            "字符串连接使用 ||",
            "LIMIT 子句在最后",
            "不支持 ALTER TABLE 的某些功能",
        ],
        common_functions_example="""
-- 年份提取
SELECT CAST(strftime('%Y', order_date) AS INTEGER) as year FROM orders;

-- 日期格式化
SELECT strftime('%Y-%m-%d', order_date) as formatted_date FROM orders;

-- 按月分组
SELECT strftime('%Y-%m-01', order_date) as month, SUM(amount) FROM orders GROUP BY 1;
"""
    ),

    DatabaseType.DUCKDB: DatabaseSpec(
        db_type=DatabaseType.DUCKDB,
        display_name="DuckDB",
        description="用于分析的高性能 OLAP 数据库（Excel/CSV查询）",
        date_functions={
            "年份提取": "EXTRACT(YEAR FROM date_column)",
            "月份提取": "EXTRACT(MONTH FROM date_column)",
            "日期格式化": "strftime(date_column, '%Y-%m-%d')",
            "年月格式化": "strftime(date_column, '%Y-%m')",
            "日期截断到月": "DATE_TRUNC('month', date_column)",
            "当前时间": "NOW()",
            "当前日期": "CURRENT_DATE",
            "日期加减": "date_column + INTERVAL '1 day'",
        },
        aggregation_functions={
            "求和": "SUM(column)",
            "平均": "AVG(column)",
            "计数": "COUNT(*)",
            "去重计数": "COUNT(DISTINCT column)",
            "最大值": "MAX(column)",
            "最小值": "MIN(column)",
        },
        string_functions={
            "字符串连接": "string1 || string2",
            "字符串转大写": "UPPER(string)",
            "字符串转小写": "LOWER(string)",
            "子字符串": "SUBSTRING(string, start, length)",
            "字符串长度": "LENGTH(string)",
            "去除空格": "TRIM(string)",
        },
        syntax_notes=[
            "类似 PostgreSQL 语法",
            "强大的 CSV/Parquet 文件查询能力",
            "支持向量化执行",
            "支持 CTE (WITH 语)",
            "支持窗口函数",
        ],
        common_functions_example="""
-- 年份提取
SELECT EXTRACT(YEAR FROM order_date) as year FROM orders;

-- 日期格式化
SELECT strftime(order_date, '%Y-%m-%d') as formatted_date FROM orders;

-- 按月分组
SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) FROM orders GROUP BY 1;
""",
        type_constraints=[
            "🚫 TIMESTAMP/DATE 类型禁用: SUBSTRING(), LEFT(), RIGHT(), CONCAT()",
            "✅ TIMESTAMP/DATE 类型必须使用: EXTRACT(), strftime(), DATE_TRUNC()",
            "💡 如需对日期做字符串操作，先用 CAST(col AS VARCHAR) 转换",
        ]
    ),
}


def get_database_spec(db_type_str: str) -> DatabaseSpec:
    """
    根据 db_type 字符串获取数据库规范

    Args:
        db_type_str: 数据库类型字符串（如 "postgresql", "mysql", "xlsx", "csv"）

    Returns:
        DatabaseSpec: 数据库规范配置
    """
    # 规范化输入
    if not db_type_str:
        logger.warning("db_type_str is empty, defaulting to PostgreSQL")
        return DATABASE_SPECS[DatabaseType.POSTGRESQL]

    db_type_str = db_type_str.lower().strip()

    # 映射规则
    type_mapping = {
        "postgresql": DatabaseType.POSTGRESQL,
        "postgres": DatabaseType.POSTGRESQL,
        "postgres_db": DatabaseType.POSTGRESQL,
        "mysql": DatabaseType.MYSQL,
        "sqlite": DatabaseType.SQLITE,
        "sqlite3": DatabaseType.SQLITE,
        "xlsx": DatabaseType.DUCKDB,  # Excel 文件使用 DuckDB
        "xls": DatabaseType.DUCKDB,
        "csv": DatabaseType.DUCKDB,
        "duckdb": DatabaseType.DUCKDB,
        "excel": DatabaseType.DUCKDB,
    }

    db_type = type_mapping.get(db_type_str, DatabaseType.POSTGRESQL)  # 默认 PostgreSQL

    if db_type not in DATABASE_SPECS:
        logger.warning(f"Database type {db_type} not found in specs, using PostgreSQL as default")
        return DATABASE_SPECS[DatabaseType.POSTGRESQL]

    return DATABASE_SPECS[db_type]


def get_supported_db_types() -> List[str]:
    """
    获取所有支持的数据库类型列表

    Returns:
        List[str]: 数据库类型字符串列表
    """
    return [db_type.value for db_type in DatabaseType]


def is_supported_db_type(db_type_str: str) -> bool:
    """
    检查数据库类型是否支持

    Args:
        db_type_str: 数据库类型字符串

    Returns:
        bool: 是否支持
    """
    supported = get_supported_db_types()
    return db_type_str.lower() in supported
