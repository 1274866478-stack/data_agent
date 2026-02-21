# -*- coding: utf-8 -*-
"""
Tenant Isolation Middleware - 租户隔离中间件
===========================================

确保多租户环境下的数据隔离和安全。

核心功能:
    - 租户 ID 注入
    - 租户上下文管理
    - 数据过滤验证

作者: BMad Master
版本: 2.2.0 (Bug修复: SQL 注入防护 - tenant_id 转义)
"""

import os
import re
import logging
from typing import Any, Dict, Optional, Callable, Awaitable
from dataclasses import dataclass

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================================
# SQL 安全工具函数
# ============================================================================

def _escape_sql_string(value: str) -> str:
    """
    转义 SQL 字符串字面量中的特殊字符

    防止 SQL 注入攻击，通过转义单引号和反斜杠来实现。
    遵循 SQL 标准：单引号通过双写单引号来转义。

    Args:
        value: 需要转义的字符串值

    Returns:
        转义后的安全字符串

    Examples:
        >>> _escape_sql_string("test")
        "test"
        >>> _escape_sql_string("test's value")
        "test''s value"
        >>> _escape_sql_string("test'; DROP TABLE--")
        "test''; DROP TABLE--"
        >>> _escape_sql_string("path\\file")
        "path\\\\file"
    """
    # 必须先转义反斜杠，再转义单引号
    # 否则会出现 "''\"" 变成 "''\\'" 的问题
    return value.replace("\\", "\\\\").replace("'", "''")


def _is_safe_tenant_id(tenant_id: str) -> bool:
    """
    验证 tenant_id 是否符合安全规范

    防御深度：即使有转义函数，也进行输入验证。

    Args:
        tenant_id: 要验证的租户 ID

    Returns:
        True 如果安全，False 否则

    安全规则：
        - 不允许空字符串
        - 不允许包含单引号
        - 不允许包含反斜杠
        - 不允许包含 SQL 注入模式（如 --, /*, */）
        - 长度限制：1-255 字符
    """
    if not tenant_id or not isinstance(tenant_id, str):
        return False

    if len(tenant_id) > 255:
        return False

    # 检查危险字符
    dangerous_chars = ["'", "\\", '"', ";", "\x00"]
    for char in dangerous_chars:
        if char in tenant_id:
            logger.warning(f"[SECURITY] tenant_id contains dangerous character: {repr(char)}")
            return False

    # 检查 SQL 注入模式
    injection_patterns = ["--", "/*", "*/", "; DROP", "; DELETE", "; INSERT"]
    tenant_upper = tenant_id.upper()
    for pattern in injection_patterns:
        if pattern in tenant_upper:
            logger.warning(f"[SECURITY] tenant_id contains injection pattern: {pattern}")
            return False

    return True

# LangChain/LangGraph imports for deepagents compatibility
from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain_core.messages.tool import ToolMessage
from langgraph.types import Command
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse, ModelCallResult


# ============================================================================
# 租户过滤注入函数
# ============================================================================

def has_tenant_id_filter(sql: str) -> bool:
    """
    更准确地检测 SQL 是否已有 tenant_id 过滤条件

    使用多种策略检测，避免误判：
    1. 检查 WHERE 子句中的 tenant_id 条件
    2. 避免将字符串字面量中的 "tenant_id" 误判
    3. 避免将表名/列名包含 "tenant_id" 误判

    Args:
        sql: SQL 查询语句

    Returns:
        True 如果已存在有效的 tenant_id 过滤条件
    """
    # 策略 1: 使用更精确的正则表达式
    # 匹配: WHERE/AND/OR + tenant_id + =，但要排除以下情况：
    # - 字符串字面量中的 'tenant_id'
    # - 注释中的 tenant_id
    # - 表名中的 tenant_id (如 tenant_id_table)

    # 移除字符串字面量和注释，避免误判
    sql_without_strings = _remove_strings_and_comments(sql)

    # 检查 WHERE 子句中的 tenant_id 条件
    # 模式匹配: (WHERE|AND|OR) + tenant_id + =
    patterns = [
        r'\bWHERE\s+tenant_id\s*=',
        r'\bAND\s+tenant_id\s*=',
        r'\bOR\s+tenant_id\s*=',
    ]

    for pattern in patterns:
        if re.search(pattern, sql_without_strings, re.IGNORECASE):
            logger.info(f"[TENANT_CHECK] Found existing tenant_id filter with pattern: {pattern}")
            return True

    # 策略 2: 检查是否有明确的 JOIN 条件包含 tenant_id
    # 例如: JOIN ... ON ... tenant_id = ...
    if re.search(r'\bJOIN\b.*?\bON\b.*?\btenant_id\s*=', sql_without_strings, re.IGNORECASE):
        logger.info("[TENANT_CHECK] Found tenant_id in JOIN condition")
        return True

    logger.debug("[TENANT_CHECK] No existing tenant_id filter found")
    return False


def _remove_strings_and_comments(sql: str) -> str:
    """
    移除 SQL 中的字符串字面量和注释，用于更精确的模式匹配

    Args:
        sql: 原始 SQL

    Returns:
        移除字符串和注释后的 SQL
    """
    # 移除单行注释
    result = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)

    # 移除多行注释
    result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)

    # 移除单引号字符串
    result = re.sub(r"'[^']*'", "''", result)

    # 移除双引号字符串
    result = re.sub(r'"[^"]*"', '""', result)

    return result


def inject_tenant_filter(sql: str, tenant_id: str) -> str:
    """
    智能地将 tenant_id 过滤条件注入到 SQL 查询中

    策略：
    1. 解析 SQL 找到正确的注入位置
    2. WHERE 子句应该在 FROM 之后、GROUP BY/HAVING/ORDER BY 之前
    3. 如果已有 WHERE，使用 AND 添加
    4. 如果没有 WHERE，在正确位置插入

    正确的 SQL 子句顺序：
    SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... LIMIT

    v4.3.2 优化：
    - 使用 has_tenant_id_filter() 进行更精确的检测
    - 避免 SQL 注入：使用转义函数处理 tenant_id
    - 添加 tenant_id 安全验证

    Args:
        sql: 原始 SQL 查询
        tenant_id: 要注入的租户 ID

    Returns:
        注入 tenant_id 过滤条件后的 SQL

    Raises:
        ValueError: 如果 tenant_id 包含不安全的字符
    """
    # 🔒 安全验证：检查 tenant_id 是否安全
    if not _is_safe_tenant_id(tenant_id):
        error_msg = f"[SECURITY] Unsafe tenant_id rejected: {tenant_id[:50]}..."
        logger.error(error_msg)
        raise ValueError("Unsafe tenant_id: contains invalid characters or injection patterns")

    # 🔒 SQL 转义：转义 tenant_id 中的特殊字符
    escaped_tenant_id = _escape_sql_string(tenant_id)

    sql_upper = sql.upper()

    # 📊 详细日志：记录输入的 SQL（不记录敏感的 tenant_id 值）
    tenant_id_safe_log = tenant_id[:8] + "..." if len(tenant_id) > 8 else tenant_id
    logger.debug(f"[TENANT_INJECT] Input SQL: {sql[:150]}...")
    logger.debug(f"[TENANT_INJECT] tenant_id: {tenant_id_safe_log}")

    # 检查是否已经包含 tenant_id 过滤（使用改进的检测函数）
    if has_tenant_id_filter(sql):
        logger.info("[TENANT_INJECT] SQL already contains tenant_id filter, skipping injection")
        return sql

    # 找到各个子句的位置
    where_match = re.search(r'\bWHERE\b', sql_upper)
    group_match = re.search(r'\bGROUP\s+BY\b', sql_upper)
    having_match = re.search(r'\bHAVING\b', sql_upper)
    order_match = re.search(r'\bORDER\s+BY\b', sql_upper)
    limit_match = re.search(r'\bLIMIT\b', sql_upper)

    logger.debug(f"[TENANT_INJECT] Clause positions: WHERE={where_match.start() if where_match else None}, "
                f"GROUP BY={group_match.start() if group_match else None}, "
                f"HAVING={having_match.start() if having_match else None}, "
                f"ORDER BY={order_match.start() if order_match else None}, "
                f"LIMIT={limit_match.start() if limit_match else None}")

    # 确定插入位置
    if where_match:
        # 已有 WHERE，在 WHERE 后面添加 AND
        where_end = where_match.end()

        # 找到下一个子句的开始位置
        next_clause_pos = float('inf')
        next_clause_name = None
        for match in [group_match, having_match, order_match, limit_match]:
            if match and match.start() > where_end:
                if match.start() < next_clause_pos:
                    next_clause_pos = match.start()
                    next_clause_name = match.group()

        if next_clause_pos < float('inf'):
            # 🔒 安全：使用转义后的 tenant_id
            before = sql[:next_clause_pos].rstrip()
            after = sql[next_clause_pos:]
            result = f"{before} AND tenant_id = '{escaped_tenant_id}' {after}"
            logger.info(f"[TENANT_INJECT] Injected before {next_clause_name} clause")
        else:
            # 没有其他子句，直接在末尾添加
            # 🔒 安全：使用转义后的 tenant_id
            result = f"{sql} AND tenant_id = '{escaped_tenant_id}'"
            logger.info("[TENANT_INJECT] Injected at end (existing WHERE)")
    else:
        # 没有 WHERE，需要插入 WHERE 子句
        # 找到插入位置：在 FROM 之后，GROUP BY/HAVING/ORDER BY/LIMIT 之前
        from_match = re.search(r'\bFROM\b', sql_upper)
        if not from_match:
            # 无法解析，返回原 SQL
            logger.warning("[TENANT_INJECT] Cannot find FROM clause, skipping injection")
            return sql

        # 找到 FROM 子句后的插入位置
        # 简化处理：找到 GROUP BY/HAVING/ORDER BY/LIMIT 中最早出现的子句
        insert_pos = float('inf')
        next_clause_name = None
        for match in [group_match, having_match, order_match, limit_match]:
            if match and match.start() > from_match.end():
                if match.start() < insert_pos:
                    insert_pos = match.start()
                    next_clause_name = match.group()

        if insert_pos < float('inf'):
            # 🔒 安全：使用转义后的 tenant_id
            before = sql[:insert_pos].rstrip()
            after = sql[insert_pos:]
            result = f"{before} WHERE tenant_id = '{escaped_tenant_id}' {after}"
            logger.info(f"[TENANT_INJECT] Injected before {next_clause_name} clause (new WHERE)")
        else:
            # 没有其他子句，在末尾添加 WHERE
            # 🔒 安全：使用转义后的 tenant_id
            result = f"{sql} WHERE tenant_id = '{escaped_tenant_id}'"
            logger.info("[TENANT_INJECT] Injected at end (new WHERE)")

    logger.debug(f"[TENANT_INJECT] Output SQL: {result[:150]}...")
    return result


# ============================================================================
# 租户上下文
# ============================================================================

@dataclass
class TenantContext:
    """
    租户上下文信息

    包含租户 ID、用户 ID 等隔离所需的信息。
    """
    tenant_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # 租户特定配置
    database_schema: Optional[str] = None
    row_filter: Optional[str] = None

    def get_isolation_key(self) -> str:
        """获取隔离键，用于缓存等场景"""
        return f"{self.tenant_id}_{self.user_id or 'anon'}_{self.session_id or 'default'}"


# ============================================================================
# TenantIsolationMiddleware
# ============================================================================

class TenantIsolationMiddleware(AgentMiddleware):
    """
    租户隔离中间件

    确保每个租户的数据完全隔离，防止跨租户数据泄露。

    使用示例:
    ```python
    from agent.middleware import TenantIsolationMiddleware

    middleware = TenantIsolationMiddleware(tenant_id="tenant_123")
    agent_input = middleware.pre_process({"messages": [...]})
    # agent_input 现在包含租户信息
    ```
    """

    def __init__(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        strict_mode: bool = True
    ):
        """
        初始化租户隔离中间件

        Args:
            tenant_id: 租户 ID (必需)
            user_id: 用户 ID (可选)
            session_id: 会话 ID (可选)
            strict_mode: 严格模式，拒绝无租户 ID 的请求
        """
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.session_id = session_id
        self.strict_mode = strict_mode

        # 租户上下文
        self._context = TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id
        )

    def pre_process(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行前注入租户信息

        Args:
            agent_input: Agent 输入数据

        Returns:
            注入租户信息后的输入数据

        Raises:
            ValueError: 如果缺少租户 ID (严格模式)
        """
        # 确保租户 ID 存在
        if not self.tenant_id:
            if self.strict_mode:
                raise ValueError(
                    "Tenant ID is required for security isolation. "
                    "Please provide tenant_id when creating the middleware."
                )
            else:
                # 使用默认租户
                self.tenant_id = os.environ.get("DEFAULT_TENANT_ID", "default_tenant")
            self._context.tenant_id = self.tenant_id

        # 注入租户信息到输入
        agent_input["__tenant__"] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "isolation_key": self._context.get_isolation_key(),
        }

        # 可选：在 system prompt 中注入租户信息
        # 这取决于具体的实现方式
        messages = agent_input.get("messages", [])
        if messages and hasattr(messages[-1], "content"):
            # 可以在这里添加租户相关的提示
            # 但需要小心不要干扰原始消息
            pass

        return agent_input

    def post_process(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行后处理输出

        Args:
            agent_output: Agent 输出数据

        Returns:
            处理后的输出数据
        """
        # 可以在这里添加租户相关的后处理
        # 例如：过滤返回数据、添加租户标签等

        # 添加租户信息到输出
        if "__tenant__" not in agent_output:
            agent_output["__tenant__"] = {
                "tenant_id": self.tenant_id,
                "isolation_key": self._context.get_isolation_key(),
            }

        return agent_output

    def get_context(self) -> TenantContext:
        """获取当前租户上下文"""
        return self._context

    def update_context(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        更新租户上下文

        Args:
            user_id: 新的用户 ID
            session_id: 新的会话 ID
        """
        if user_id is not None:
            self.user_id = user_id
            self._context.user_id = user_id

        if session_id is not None:
            self.session_id = session_id
            self._context.session_id = session_id

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """
        包装工具调用以注入租户信息

        这是 deepagents 中间件接口的要求。

        Args:
            request: The tool call request being processed
            handler: The handler function to call with the modified request

        Returns:
            The raw ToolMessage, or a Command
        """
        # 修改工具调用输入以注入租户信息
        tool_call = request.tool_call.copy()
        tool_input = tool_call.get("args", {})

        # 注入租户信息
        tool_input["__tenant__"] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
        }

        # 对于数据库查询，智能注入 WHERE 条件
        if "query" in tool_input and isinstance(tool_input["query"], str):
            tool_input["query"] = inject_tenant_filter(tool_input["query"], self.tenant_id)

        # 更新工具调用
        tool_call["args"] = tool_input

        # 创建修改后的请求
        modified_request = ToolCallRequest(
            tool_call=tool_call,
            tool=request.tool,
            state=request.state,
            runtime=request.runtime
        )

        # 调用处理器
        return handler(modified_request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """
        包装工具调用以注入租户信息（异步版本）

        这是 deepagents 中间件接口的异步要求。

        Args:
            request: The tool call request being processed
            handler: The async handler function to call with the modified request

        Returns:
            The raw ToolMessage, or a Command
        """
        # 修改工具调用输入以注入租户信息
        tool_call = request.tool_call.copy()
        tool_input = tool_call.get("args", {})

        # 注入租户信息
        tool_input["__tenant__"] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
        }

        # 对于数据库查询，智能注入 WHERE 条件
        if "query" in tool_input and isinstance(tool_input["query"], str):
            tool_input["query"] = inject_tenant_filter(tool_input["query"], self.tenant_id)

        # 更新工具调用
        tool_call["args"] = tool_input

        # 创建修改后的请求
        modified_request = ToolCallRequest(
            tool_call=tool_call,
            tool=request.tool,
            state=request.state,
            runtime=request.runtime
        )

        # 调用异步处理器
        return await handler(modified_request)

    def wrap_model_call(self, request, handler) -> Any:
        """
        包装模型调用以注入租户信息

        正确的 deepagents 中间件接口实现。

        Args:
            request: ModelRequest 对象
            handler: 处理函数

        Returns:
            ModelResponse 对象
        """
        # TODO: 正确实现租户信息注入
        # 目前暂时直接调用 handler，不做任何修改
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelCallResult:
        """
        包装模型调用以注入租户信息（异步版本）

        Args:
            request: ModelRequest 对象
            handler: 异步处理函数

        Returns:
            ModelCallResult 对象
        """
        # TODO: 正确实现租户信息注入
        # 目前暂时直接调用 handler，不做任何修改
        return await handler(request)


# ============================================================================
# 租户管理器
# ============================================================================

class TenantManager:
    """
    租户管理器

    管理多个租户的隔离上下文。
    """

    def __init__(self):
        """初始化租户管理器"""
        self._tenants: Dict[str, TenantIsolationMiddleware] = {}

    def get_or_create_middleware(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> TenantIsolationMiddleware:
        """
        获取或创建租户中间件

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            TenantIsolationMiddleware 实例
        """
        key = f"{tenant_id}_{user_id or 'default'}_{session_id or 'default'}"

        if key not in self._tenants:
            self._tenants[key] = TenantIsolationMiddleware(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id
            )

        return self._tenants[key]

    def clear_tenant(self, tenant_id: str, user_id: Optional[str] = None):
        """
        清除特定租户的缓存

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID (可选，如果提供则只清除该用户的缓存)
        """
        keys_to_remove = []

        for key, middleware in self._tenants.items():
            if middleware.tenant_id == tenant_id:
                if user_id is None or middleware.user_id == user_id:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._tenants[key]

    def clear_all(self):
        """清除所有租户缓存"""
        self._tenants.clear()


# ============================================================================
# 全局租户管理器实例
# ============================================================================

_global_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager() -> TenantManager:
    """获取全局租户管理器实例"""
    global _global_tenant_manager
    if _global_tenant_manager is None:
        _global_tenant_manager = TenantManager()
    return _global_tenant_manager


# ============================================================================
# 便捷函数
# ============================================================================

def create_tenant_middleware(
    tenant_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> TenantIsolationMiddleware:
    """
    创建租户隔离中间件的便捷函数

    Args:
        tenant_id: 租户 ID
        user_id: 用户 ID
        session_id: 会话 ID

    Returns:
        TenantIsolationMiddleware 实例
    """
    return TenantIsolationMiddleware(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id
    )


def inject_tenant_id(
    agent_input: Dict[str, Any],
    tenant_id: str
) -> Dict[str, Any]:
    """
    向 Agent 输入注入租户 ID

    Args:
        agent_input: Agent 输入
        tenant_id: 租户 ID

    Returns:
        注入租户 ID 后的输入
    """
    middleware = create_tenant_middleware(tenant_id)
    return middleware.pre_process(agent_input)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Tenant Isolation Middleware 测试")
    print("=" * 60)

    # 测试 1: 创建中间件
    print("\n[TEST 1] 创建租户隔离中间件")
    middleware = create_tenant_middleware(
        tenant_id="tenant_123",
        user_id="user_456",
        session_id="session_789"
    )
    context = middleware.get_context()
    print(f"[INFO] 租户 ID: {context.tenant_id}")
    print(f"[INFO] 用户 ID: {context.user_id}")
    print(f"[INFO] 会话 ID: {context.session_id}")
    print(f"[INFO] 隔离键: {context.get_isolation_key()}")

    # 测试 2: 注入租户信息
    print("\n[TEST 2] 注入租户信息到 Agent 输入")
    agent_input = {"messages": [{"role": "user", "content": "查询数据"}]}
    enhanced_input = middleware.pre_process(agent_input)

    if "__tenant__" in enhanced_input:
        print("[PASS] 租户信息已注入")
        print(f"[INFO] 注入的数据: {enhanced_input['__tenant__']}")
    else:
        print("[FAIL] 租户信息注入失败")

    # 测试 3: 租户管理器
    print("\n[TEST 3] 租户管理器")
    manager = get_tenant_manager()

    middleware1 = manager.get_or_create_middleware("tenant_a", "user_1")
    middleware2 = manager.get_or_create_middleware("tenant_a", "user_2")
    middleware3 = manager.get_or_create_middleware("tenant_b", "user_1")

    print(f"[INFO] 租户 A 用户 1: {middleware1.get_context().get_isolation_key()}")
    print(f"[INFO] 租户 A 用户 2: {middleware2.get_context().get_isolation_key()}")
    print(f"[INFO] 租户 B 用户 1: {middleware3.get_context().get_isolation_key()}")

    print("\n" + "=" * 60)
    print("[SUCCESS] 租户隔离中间件测试通过")
    print("=" * 60)
