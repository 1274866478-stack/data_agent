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
    def validate(cls, sql: str) -> Tuple[bool, Optional[str]]:
        """
        校验 SQL 安全性

        Args:
            sql: 要校验的 SQL 语句

        Returns:
            tuple: (is_safe, error_message)
                - is_safe: True 表示安全，False 表示危险
                - error_message: 如果不安全，返回错误描述；安全则为 None
        """
        if not sql or not sql.strip():
            return True, None

        sql_upper = sql.upper().strip()

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
        raise SQLValidationError(error_msg, sql)


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
