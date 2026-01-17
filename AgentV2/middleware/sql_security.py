# -*- coding: utf-8 -*-
"""
SQL Security Middleware - SQL 安全校验中间件
============================================

从 Agent V1 的 sql_validator.py 迁移到 DeepAgents 中间件架构。

核心功能:
    - pre_process: 在 Agent 执行前验证 SQL 安全性
    - 拦截危险关键字 (DROP, DELETE, INSERT, UPDATE, etc.)
    - 防止 SQL 注入攻击
    - 只允许只读查询 (SELECT, WITH, SHOW, EXPLAIN)

作者: BMad Master
版本: 2.0.0 (基于 V1 sql_validator.py)
"""

import re
from typing import Any, Dict, Optional, Callable, Awaitable
from pathlib import Path

# LangChain/LangGraph imports for deepagents compatibility
from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain_core.messages.tool import ToolMessage
from langgraph.types import Command
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse, ModelCallResult

# ============================================================================
# SQLSecurityMiddleware
# ============================================================================

class SQLSecurityMiddleware(AgentMiddleware):
    """
    SQL 安全校验中间件

    集成到 DeepAgents 管道中，自动拦截危险的 SQL 操作。

    使用示例:
    ```python
    from deepagents import create_deep_agent
    from AgentV2.middleware import SQLSecurityMiddleware

    middleware = [SQLSecurityMiddleware()]
    agent = create_deep_agent(model, tools, middleware)
    ```
    """

    # 允许的起始关键字 (包括 CTE、SHOW、EXPLAIN 等只读操作)
    ALLOWED_STARTS = r"^\s*(SELECT|WITH|VALUES|SHOW|EXPLAIN|DESCRIBE|DESC)\b"

    # 危险关键字黑名单 (不区分大小写，必须是完整单词)
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

    def __init__(
        self,
        strict_mode: bool = True,
        allow_limitless: bool = True,
        log_violations: bool = True
    ):
        """
        初始化 SQL 安全中间件

        Args:
            strict_mode: 严格模式，拒绝任何不安全的查询
            allow_limitless: 允许无 LIMIT 的查询
            log_violations: 记录安全违规
        """
        self.strict_mode = strict_mode
        self.allow_limitless = allow_limitless
        self.log_violations = log_violations

        # 违规记录
        self._violations: list = []

    def validate(self, sql: str) -> tuple[bool, Optional[str]]:
        """
        校验 SQL 安全性

        Args:
            sql: 要校验的 SQL 语句

        Returns:
            tuple: (is_safe, error_message)
        """
        if not sql or not sql.strip():
            return True, None

        sql_upper = sql.upper().strip()

        # 1. 检查是否以允许的关键字开头
        if not re.match(self.ALLOWED_STARTS, sql_upper, re.IGNORECASE):
            first_word = sql_upper.split()[0] if sql_upper.split() else "UNKNOWN"
            return False, (
                f"Security Alert: Query must start with SELECT, WITH, SHOW, or EXPLAIN. "
                f"Found: '{first_word}'"
            )

        # 2. 检查黑名单关键字
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, sql_upper):
                keyword = pattern.replace(r'\b', '').strip()
                return False, (
                    f"Security Alert: Forbidden keyword detected: {keyword}. "
                    f"Only read-only queries are allowed."
                )

        # 3. 检查危险函数
        for pattern in self.DANGEROUS_FUNCTIONS:
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
        if not self.allow_limitless:
            if "LIMIT" not in sql_upper and "COUNT(" not in sql_upper:
                return False, (
                    "Performance Alert: Query must include a LIMIT clause "
                    "to prevent excessive result sets."
                )

        return True, None

    def pre_process(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行前处理输入

        Args:
            agent_input: Agent 输入数据

        Returns:
            处理后的输入数据

        Raises:
            ValueError: 如果检测到不安全的 SQL
        """
        # 提取并验证 SQL
        # 注意：具体实现取决于 Agent 输入格式
        # 这里提供一个通用框架

        # 尝试从 messages 中提取 SQL
        messages = agent_input.get("messages", [])
        if messages:
            # 检查最后一条消息
            last_message = messages[-1] if isinstance(messages, list) else messages
            content = getattr(last_message, "content", str(last_message))

            # 简单启发式：查找可能的 SQL 语句
            # 实际实现需要更精确的解析
            if content and isinstance(content, str):
                # 尝试提取 SQL (这里需要根据实际格式调整)
                is_safe, error_msg = self._check_content_for_sql(content)
                if not is_safe:
                    if self.strict_mode:
                        # 记录违规
                        if self.log_violations:
                            self._violations.append({
                                "sql": content[:100],  # 截断
                                "error": error_msg,
                                "timestamp": None  # TODO: 添加时间戳
                            })
                        raise ValueError(f"SQL Security Violation: {error_msg}")

        return agent_input

    def _check_content_for_sql(self, content: str) -> tuple[bool, Optional[str]]:
        """
        检查内容中的 SQL 语句

        Args:
            content: 要检查的内容

        Returns:
            (is_safe, error_message)
        """
        # 简单启发式：查找 SQL 关键字
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE"]
        content_upper = content.upper()

        for keyword in sql_keywords:
            if keyword in content_upper:
                # 找到可能的 SQL，进行验证
                # 这里简化处理，实际需要更精确的提取
                return self.validate(content)

        return True, None

    def post_process(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行后处理输出

        Args:
            agent_output: Agent 输出数据

        Returns:
            处理后的输出数据
        """
        # 可以在这里添加额外的安全检查
        # 例如：检查返回的数据量、敏感字段等

        return agent_output

    def get_violations(self) -> list:
        """获取安全违规记录"""
        return self._violations.copy()

    def clear_violations(self):
        """清除违规记录"""
        self._violations.clear()

    def sanitize_for_logging(self, sql: str, max_length: int = 200) -> str:
        """
        清理 SQL 用于日志记录（截断过长的查询）

        Args:
            sql: 原始 SQL
            max_length: 最大长度

        Returns:
            str: 截断后的 SQL
        """
        sql_clean = ' '.join(sql.split())  # 移除多余空白
        if len(sql_clean) > max_length:
            return sql_clean[:max_length] + "..."
        return sql_clean

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """
        包装工具调用以验证 SQL 安全性

        这是 deepagents 中间件接口的要求。

        Args:
            request: The tool call request being processed
            handler: The handler function to call with the modified request

        Returns:
            The raw ToolMessage, or a Command

        Raises:
            ValueError: 如果检测到不安全的 SQL
        """
        # 获取工具输入
        tool_call = request.tool_call
        tool_input = tool_call.get("args", {})

        # 如果工具输入包含查询，验证 SQL
        if "query" in tool_input and isinstance(tool_input["query"], str):
            is_safe, error_msg = self.validate(tool_input["query"])
            if not is_safe:
                if self.log_violations:
                    self._violations.append({
                        "tool": tool_call.get("name", "unknown"),
                        "sql": self.sanitize_for_logging(tool_input["query"]),
                        "error": error_msg,
                        "timestamp": None  # TODO: 添加时间戳
                    })
                raise ValueError(f"SQL Security Violation: {error_msg}")

        # 调用处理器
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """
        包装工具调用以检查 SQL 安全性（异步版本）

        这是 deepagents 中间件接口的异步要求。

        Args:
            request: The tool call request being processed
            handler: The async handler function to call with the modified request

        Returns:
            The raw ToolMessage, or a Command
        """
        # 获取工具调用信息
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")
        tool_input = tool_call.get("args", {})

        # 只对 SQL 相关工具进行检查
        if "sql" in tool_name.lower() or "query" in tool_name.lower():
            query = tool_input.get("query") or tool_input.get("sql", "")

            if query:
                # 检查危险关键字
                dangerous_patterns = {
                    "DROP\\s+TABLE": "删除表操作",
                    "DELETE\\s+FROM": "删除数据操作",
                    "TRUNCATE": "清空表操作",
                    "ALTER\\s+TABLE": "修改表结构",
                    "CREATE\\s+TABLE": "创建表操作",
                }

                for pattern, error_msg in dangerous_patterns.items():
                    if re.search(pattern, query, re.IGNORECASE):
                        # 返回错误信息
                        error_response = ToolMessage(
                            content=f"SQL Security Violation: {error_msg}",
                            name=tool_name,
                            tool_call_id=tool_call.get("id")
                        )
                        return Command(update={"messages": [error_response]})

        # 调用异步处理器
        return await handler(request)

    def wrap_model_call(self, request, handler) -> Any:
        """
        包装模型调用以检查 SQL 安全性

        正确的 deepagents 中间件接口实现。

        Args:
            request: ModelRequest 对象
            handler: 处理函数

        Returns:
            ModelResponse 对象
        """
        # TODO: 正确实现 SQL 安全检查
        # 目前暂时直接调用 handler，不做任何检查
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelCallResult:
        """
        包装模型调用以检查 SQL 安全性（异步版本）

        Args:
            request: ModelRequest 对象
            handler: 异步处理函数

        Returns:
            ModelCallResult 对象
        """
        # TODO: 正确实现 SQL 安全检查
        # 目前暂时直接调用 handler，不做任何检查
        return await handler(request)


# ============================================================================
# 便捷函数
# ============================================================================

def validate_sql(sql: str) -> tuple[bool, Optional[str]]:
    """
    校验 SQL 安全性的便捷函数

    Args:
        sql: 要校验的 SQL 语句

    Returns:
        tuple: (is_safe, error_message)
    """
    middleware = SQLSecurityMiddleware()
    return middleware.validate(sql)


def assert_sql_safe(sql: str) -> None:
    """
    断言 SQL 安全，不安全则抛出异常

    Args:
        sql: 要校验的 SQL 语句

    Raises:
        ValueError: 如果 SQL 不安全
    """
    is_safe, error_msg = validate_sql(sql)
    if not is_safe:
        raise ValueError(f"SQL Security Violation: {error_msg}")


# ============================================================================
# 测试代码
# ============================================================================

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
        ("TRUNCATE TABLE logs", False),
        ("ALTER TABLE users ADD COLUMN hacked INT", False),
        # REPLACE INTO 语句是危险的 (MySQL/SQLite UPSERT)
        ("REPLACE INTO users VALUES (1, 'hacker')", False),
    ]

    print("=" * 60)
    print("SQL Security Middleware 测试")
    print("=" * 60)

    middleware = SQLSecurityMiddleware()

    for sql, expected_safe in test_cases:
        is_safe, error_msg = middleware.validate(sql)
        status = "[PASS]" if is_safe == expected_safe else "[FAIL]"
        result = "SAFE" if is_safe else f"BLOCKED: {error_msg}"
        print(f"{status} | {sql[:45]:<45} | {result}")

    print("=" * 60)
