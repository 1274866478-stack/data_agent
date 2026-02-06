"""
# [SQL VALIDATOR] SQL 安全校验器

## [HEADER]
**文件名**: sql_validator.py
**职责**: SQL 安全校验 - 防止 LLM 生成危险的 DML/DDL 操作，提供 Python 层面的硬性安全防护
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-06): 初始版本 - 独立 SQL 安全校验模块

## [INPUT]
- **SQLValidator.validate(sql)**:
  - sql: str - 要校验的 SQL 语句

## [OUTPUT]
- **validate()**: tuple[bool, Optional[str]] - (是否安全, 错误信息)

## [LINK]
**下游依赖**:
- [./sql_agent.py](./sql_agent.py) - 在 SafeToolNode 和 should_continue 中调用

## [POS]
**路径**: Agent/sql_validator.py
**模块层级**: Level 1（Agent根目录）

## 设计原则
🔒 **为什么需要代码层面的校验？**

System Prompt 只是"君子协定"：
- LLM 可能"抽风"忽略指令
- 用户可能使用"越狱提示词"(Jailbreak Prompt)
- 恶意用户可能诱导 AI 生成危险 SQL

代码校验是"法律"：
- 不管 AI 多想执行 DELETE，Python 代码会直接拦截
- 这是多层防御策略的关键一环
"""

import re
from typing import Tuple, Optional


class SQLValidator:
    """
    SQL 安全校验器 - 防止 LLM 生成危险的 DML/DDL 操作

    使用示例:
    ```python
    from sql_validator import SQLValidator

    sql = "DELETE FROM users WHERE id = 1"
    is_safe, error_msg = SQLValidator.validate(sql)
    if not is_safe:
        print(f"拦截: {error_msg}")
    ```
    """

    # 允许的起始关键字 (包括 CTE、SHOW、EXPLAIN 等只读操作)
    ALLOWED_STARTS = r"^\s*(SELECT|WITH|VALUES|SHOW|EXPLAIN|DESCRIBE|DESC)\b"

    # 危险关键字黑名单 (不区分大小写，必须是完整单词)
    # 包含数据修改、结构变更、权限管理等
    FORBIDDEN_PATTERNS = [
        r"\bUPDATE\b",      # 更新数据
        r"\bDELETE\b",      # 删除数据
        r"\bINSERT\b",      # 插入数据
        r"\bDROP\b",        # 删除表/数据库
        r"\bTRUNCATE\b",    # 清空表
        r"\bALTER\b",       # 修改结构
        r"\bGRANT\b",       # 授权
        r"\bREVOKE\b",      # 撤销权限
        r"\bCREATE\b",      # 创建对象
        r"\bREPLACE\s+INTO\b",  # REPLACE INTO 语句 (MySQL/SQLite UPSERT, DANGEROUS)
                                # 注意: REPLACE() 字符串函数是安全的,不被此规则阻止
        r"\bRENAME\b",      # 重命名
        r"\bCOMMENT\b",     # 添加注释（DDL）
        r"\bLOCK\b",        # 锁表
        r"\bUNLOCK\b",      # 解锁
        r"\bEXEC\b",        # 执行存储过程
        r"\bEXECUTE\b",     # 执行
        r"\bCALL\b",        # 调用过程
        r"\bMERGE\b",       # 合并（UPSERT）
        r"\bCOPY\b",        # PostgreSQL COPY（可写文件）
        r"\bPG_READ_FILE\b",  # PostgreSQL 读文件
        r"\bPG_WRITE_FILE\b", # PostgreSQL 写文件
        r"\bLO_IMPORT\b",   # 大对象导入
        r"\bLO_EXPORT\b",   # 大对象导出
    ]

    # 危险函数黑名单（PostgreSQL 特有的危险函数）
    DANGEROUS_FUNCTIONS = [
        r"\bpg_read_file\s*\(",
        r"\bpg_write_file\s*\(",
        r"\bpg_ls_dir\s*\(",
        r"\bpg_execute_server_program\s*\(",
        r"\bdblink\s*\(",
        r"\bdblink_exec\s*\(",
    ]

    @classmethod
    def validate(cls, sql: str, user_query: str = "") -> Tuple[bool, Optional[str]]:
        """
        校验 SQL 安全性

        Args:
            sql: 要校验的 SQL 语句
            user_query: 原始用户查询（用于检测占比类问题）

        Returns:
            tuple: (is_safe, error_message)
                - is_safe: True 表示安全，False 表示危险
                - error_message: 如果不安全，返回错误描述；安全则为 None
        """
        if not sql or not sql.strip():
            return True, None

        sql_upper = sql.upper().strip()

        # 🔧 新增：检测占比类查询的错误模式
        proportion_keywords = ['占比', '比例', '分布', '多少', '百分比']
        is_proportion = any(kw in user_query for kw in proportion_keywords)

        # 检测：SELECT COUNT(*) FROM table WHERE ... (没有 GROUP BY)
        # 但如果有 LIMIT 或者是复杂查询，则不强制要求 GROUP BY
        if is_proportion:
            has_count = 'COUNT(' in sql_upper
            has_group_by = 'GROUP BY' in sql_upper
            has_where = 'WHERE' in sql_upper
            has_limit = 'LIMIT' in sql_upper

            # 如果是 COUNT 查询，有 WHERE，但没有 GROUP BY，且没有 LIMIT
            # 这很可能是占比类查询的错误模式
            if has_count and has_where and not has_group_by and not has_limit:
                # 检查是否是简单的 COUNT(*) FROM ... WHERE 模式
                simple_count_pattern = r"SELECT\s+COUNT\s*\([^)]+\)\s+FROM\s+\w+\s+WHERE\s+\w+\s*(?:=|LIKE)\s*\S+"
                if re.match(simple_count_pattern, sql, re.IGNORECASE):
                    return False, (
                        "占比类查询必须使用 GROUP BY 获取完整分布，"
                        "请使用: SELECT CASE WHEN...END as category, COUNT(*) as value FROM table GROUP BY category\n"
                        "示例：\n"
                        "  SELECT\n"
                        "    CASE WHEN region = '安徽' THEN '安徽' ELSE '其他' END as category,\n"
                        "    COUNT(*) as value\n"
                        "  FROM customers\n"
                        "  GROUP BY category;"
                    )

        # 1. 检查是否以允许的关键字开头
        if not re.match(cls.ALLOWED_STARTS, sql_upper, re.IGNORECASE):
            first_word = sql_upper.split()[0] if sql_upper.split() else "UNKNOWN"
            return False, (
                f"Security Alert: Query must start with SELECT, WITH, SHOW, or EXPLAIN. "
                f"Found: '{first_word}'"
            )

        # 2. 检查黑名单关键字
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, sql_upper):
                keyword = pattern.replace(r'\b', '').strip()
                return False, (
                    f"Security Alert: Forbidden keyword detected: {keyword}. "
                    f"Only read-only queries are allowed."
                )

        # 3. 检查危险函数
        for pattern in cls.DANGEROUS_FUNCTIONS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                func_name = pattern.split(r'\(')[0].replace(r'\b', '').replace(r'\s*', '').strip()
                return False, (
                    f"Security Alert: Dangerous function detected: {func_name}(). "
                    f"This function is not allowed for security reasons."
                )

        # 4. 检查 SQL 注入常见模式
        injection_patterns = [
            r";\s*(UPDATE|DELETE|INSERT|DROP|ALTER|TRUNCATE|CREATE)\b",  # 多语句注入
            r"--\s*(UPDATE|DELETE|INSERT|DROP)",  # 注释后的危险命令
            r"/\*.*?(UPDATE|DELETE|INSERT|DROP).*?\*/",  # 块注释中的危险命令
        ]
        for pattern in injection_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE | re.DOTALL):
                return False, (
                    "Security Alert: Potential SQL injection detected. "
                    "Multi-statement or comment-based attack pattern found."
                )

        # 5. 可选：强制 LIMIT 检查 (防止内存溢出)
        # 如果启用，取消下面的注释
        # if "LIMIT" not in sql_upper and "COUNT(" not in sql_upper:
        #     return False, "Performance Alert: Query must include a LIMIT clause."

        return True, None

    @classmethod
    def validate_table_selection(
        cls,
        sql: str,
        user_query: str = ""
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        验证表选择是否正确（地理查询专用）

        检测用户查询包含省份/城市关键词时，是否错误地使用了 users 表
        而不是 addresses 表。

        Args:
            sql: 要校验的 SQL 语句
            user_query: 原始用户查询

        Returns:
            tuple: (is_valid, error_message, suggested_sql)
                - is_valid: True 表示表选择正确，False 表示需要修正
                - error_message: 错误描述（如果不正确）
                - suggested_sql: 建议的 SQL（可选）
        """
        if not sql or not sql.strip():
            return True, None, None

        sql_lower = sql.lower()

        # 地理位置关键词检测
        geo_keywords = [
            "省份", "省", "城市", "市",
            "安徽", "浙江", "江苏", "上海", "北京", "广东",
            "分布", "占比", "客户地址", "客户占比"
        ]

        has_geo_query = any(kw in user_query for kw in geo_keywords)

        if not has_geo_query:
            return True, None, None

        # 检测是否错误使用了 users 表
        if "users" in sql_lower or "user" in sql_lower:
            # 检查是否有 province/城市相关条件
            has_geo_condition = (
                "province" in sql_lower or
                "city" in sql_lower or
                "district" in sql_lower
            )

            if has_geo_condition:
                # 提取查询条件中的省份/城市值
                province_match = re.search(r"province\s*=\s*['\"]([^'\"]+)['\"]", sql, re.IGNORECASE)
                city_match = re.search(r"city\s*=\s*['\"]([^'\"]+)['\"]", sql, re.IGNORECASE)

                target_location = None
                if province_match:
                    target_location = province_match.group(1)
                elif city_match:
                    target_location = city_match.group(1)

                # 建议使用 addresses 表的 SQL
                suggested_sql = None
                if target_location:
                    suggested_sql = (
                        f"SELECT province, COUNT(*) as count\n"
                        f"FROM addresses\n"
                        f"GROUP BY province\n"
                        f"ORDER BY count DESC;"
                    )

                return False, (
                    "⚠️ 检测到省份/城市查询使用了 users 表。"
                    "addresses 表包含完整的地理信息，请使用 addresses 表。\n\n"
                    f"原因：users 表的 province/city 字段可能为空或不完整，"
                    f"addresses 表才是地理位置查询的正确选择。\n\n"
                    f"建议流程：\n"
                    f"1. 调用 get_schema('addresses') 查看表结构\n"
                    f"2. 使用一次 GROUP BY 查询获取所有省份/城市分布"
                ), suggested_sql

        # 检查是否正确使用了 addresses 表（给出正面反馈）
        if "addresses" in sql_lower:
            logger = __import__('logging').getLogger(__name__)
            logger.info(f"[TABLE_SELECTION] ✅ 正确使用 addresses 表进行地理查询")

        return True, None, None

    @classmethod
    def fix_proportion_sql(cls, sql: str, user_query: str = "") -> str:
        """
        修正占比类查询的 SQL

        检测条件：
        1. 用户查询包含占比/分布关键词
        2. SQL 包含 WHERE province/city = 'XX' 但没有 GROUP BY

        修正策略：
        - 将 WHERE province = 'XX' 改为 GROUP BY province
        - 添加 SELECT province, COUNT(*) ...
        - 保留其他条件（如额外的过滤条件）

        Args:
            sql: 原始 SQL 语句
            user_query: 用户查询（用于判断是否为占比类查询）

        Returns:
            str: 修正后的 SQL（如果需要），否则返回原始 SQL
        """
        if not sql or not sql.strip():
            return sql

        # 获取 logger
        logger = __import__('logging').getLogger(__name__)

        # 检测是否为占比查询
        proportion_keywords = ['占比', '比例', '分布', '多少', '百分比']
        is_proportion = any(kw in user_query for kw in proportion_keywords)

        if not is_proportion:
            return sql  # 不是占比查询，不修正

        sql_upper = sql.upper().strip()

        # 检查是否已经包含 GROUP BY（已经正确）
        if 'GROUP BY' in sql_upper:
            return sql  # 已经有 GROUP BY，不需要修正

        # 错误模式1: SELECT COUNT(*) FROM table WHERE province = 'XX'
        pattern1 = r"SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM\s+(\w+)\s+WHERE\s+province\s*=\s*'([^']+)'"
        match1 = re.search(pattern1, sql, re.IGNORECASE)

        if match1:
            table_name = match1.group(1)
            province_value = match1.group(2)
            fixed_sql = (
                f"SELECT province, COUNT(*) as count\n"
                f"FROM {table_name}\n"
                f"GROUP BY province\n"
                f"ORDER BY count DESC"
            )
            logger.warning(
                f"[SQL修正] 占比查询SQL已修正:\n"
                f"  原始: {sql}\n"
                f"  修正: {fixed_sql}\n"
                f"  原因: 检测到 'WHERE province = \"{province_value}\"'，"
                f"占比查询应使用 GROUP BY 获取所有省份分布"
            )
            return fixed_sql

        # 错误模式2: SELECT COUNT(*) FROM table WHERE city = 'XX'
        pattern2 = r"SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM\s+(\w+)\s+WHERE\s+city\s*=\s*'([^']+)'"
        match2 = re.search(pattern2, sql, re.IGNORECASE)

        if match2:
            table_name = match2.group(1)
            city_value = match2.group(2)
            fixed_sql = (
                f"SELECT city, COUNT(*) as count\n"
                f"FROM {table_name}\n"
                f"GROUP BY city\n"
                f"ORDER BY count DESC"
            )
            logger.warning(
                f"[SQL修正] 占比查询SQL已修正:\n"
                f"  原始: {sql}\n"
                f"  修正: {fixed_sql}\n"
                f"  原因: 检测到 'WHERE city = \"{city_value}\"'，"
                f"占比查询应使用 GROUP BY 获取所有城市分布"
            )
            return fixed_sql

        # 错误模式3: SELECT COUNT(*) FROM table WHERE province IN (...)
        pattern3 = r"SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM\s+(\w+)\s+WHERE\s+province\s+IN\s*\("
        match3 = re.search(pattern3, sql, re.IGNORECASE)

        if match3:
            table_name = match3.group(1)
            fixed_sql = (
                f"SELECT province, COUNT(*) as count\n"
                f"FROM {table_name}\n"
                f"GROUP BY province\n"
                f"ORDER BY count DESC"
            )
            logger.warning(
                f"[SQL修正] 占比查询SQL已修正:\n"
                f"  原始: {sql}\n"
                f"  修正: {fixed_sql}\n"
                f"  原因: 检测到 WHERE province IN 模式，"
                f"占比查询应使用 GROUP BY 获取所有省份分布"
            )
            return fixed_sql

        # 错误模式4: 通用检测 - 任何带 WHERE 的 COUNT(*) 查询但没有 GROUP BY
        # 更宽松的模式，用于捕获更多情况
        sql_lower = sql.lower()
        if ('COUNT(' in sql_upper and
            'WHERE' in sql_upper and
            'FROM' in sql_upper and
            'LIMIT' not in sql_upper):

            # 尝试提取表名
            from_match = re.search(r"FROM\s+(\w+)", sql, re.IGNORECASE)
            if from_match:
                table_name = from_match.group(1)

                # 检查 WHERE 条件中是否包含 province 或 city
                has_geo_condition = (
                    'province' in sql_lower or
                    'city' in sql_lower
                )

                if has_geo_condition:
                    # 确定分组列
                    group_column = 'province' if 'province' in sql_lower else 'city'

                    fixed_sql = (
                        f"SELECT {group_column}, COUNT(*) as count\n"
                        f"FROM {table_name}\n"
                        f"GROUP BY {group_column}\n"
                        f"ORDER BY count DESC"
                    )
                    logger.warning(
                        f"[SQL修正] 占比查询SQL已修正（通用模式）:\n"
                        f"  原始: {sql}\n"
                        f"  修正: {fixed_sql}\n"
                        f"  原因: 检测到占比类查询但缺少 GROUP BY"
                    )
                    return fixed_sql

        return sql

    @classmethod
    def sanitize_for_logging(cls, sql: str, max_length: int = 200) -> str:
        """
        清理 SQL 用于日志记录（截断过长的查询）

        Args:
            sql: 原始 SQL
            max_length: 最大长度

        Returns:
            str: 截断后的 SQL（如果超长会添加 ...）
        """
        sql_clean = ' '.join(sql.split())  # 移除多余空白
        if len(sql_clean) > max_length:
            return sql_clean[:max_length] + "..."
        return sql_clean


class SQLValidationError(Exception):
    """SQL 安全校验失败异常"""

    def __init__(self, message: str, sql: str = ""):
        self.message = message
        self.sql = sql
        super().__init__(self.message)

    def __str__(self):
        if self.sql:
            sanitized = SQLValidator.sanitize_for_logging(self.sql)
            return f"{self.message}\nSQL: {sanitized}"
        return self.message


# 便捷函数，供外部直接调用
def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """
    校验 SQL 安全性的便捷函数

    Args:
        sql: 要校验的 SQL 语句

    Returns:
        tuple: (is_safe, error_message)
    """
    return SQLValidator.validate(sql)


def assert_sql_safe(sql: str) -> None:
    """
    断言 SQL 安全，不安全则抛出异常

    Args:
        sql: 要校验的 SQL 语句

    Raises:
        SQLValidationError: 如果 SQL 不安全
    """
    is_safe, error_msg = SQLValidator.validate(sql)
    if not is_safe:
        raise SQLValidationError(error_msg or "Unknown SQL validation error", sql)


# 测试代码
if __name__ == "__main__":
    test_cases = [
        # 安全的查询
        ("SELECT * FROM users LIMIT 10", True),
        ("WITH cte AS (SELECT 1) SELECT * FROM cte", True),
        ("EXPLAIN SELECT * FROM orders", True),
        ("SHOW TABLES", True),
        # REPLACE() 字符串函数是安全的 (PostgreSQL/MySQL)
        ("SELECT REPLACE(name, 'old', 'new') FROM users", True),
        ("SELECT REPLACE(product_name, '2023', '2024'), COUNT(*) FROM sales GROUP BY 1", True),

        # 危险的查询
        ("DELETE FROM users WHERE id = 1", False),
        ("DROP TABLE users", False),
        ("UPDATE users SET name = 'hacked'", False),
        ("INSERT INTO users VALUES (1, 'test')", False),
        ("SELECT * FROM users; DELETE FROM users", False),
        ("SELECT * FROM users -- DELETE FROM users", True),  # 注释不会执行，但要警惕
        ("TRUNCATE TABLE logs", False),
        ("ALTER TABLE users ADD COLUMN hacked INT", False),
        ("CREATE TABLE malicious (id INT)", False),
        ("GRANT ALL ON users TO public", False),
        # REPLACE INTO 语句是危险的 (MySQL/SQLite UPSERT)
        ("REPLACE INTO users VALUES (1, 'hacker')", False),
    ]

    print("=" * 60)
    print("SQL Validator 测试")
    print("=" * 60)

    for sql, expected_safe in test_cases:
        is_safe, error_msg = SQLValidator.validate(sql)
        status = "✅ PASS" if is_safe == expected_safe else "❌ FAIL"
        result = "SAFE" if is_safe else f"BLOCKED: {error_msg}"
        print(f"{status} | {sql[:50]:<50} | {result}")

    print("=" * 60)
