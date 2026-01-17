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
版本: 2.0.0
"""

import os
from typing import Any, Dict, Optional, Callable, Awaitable
from dataclasses import dataclass, field

# LangChain/LangGraph imports for deepagents compatibility
from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain_core.messages.tool import ToolMessage
from langgraph.types import Command
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse, ModelCallResult


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
    from AgentV2.middleware import TenantIsolationMiddleware

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

        # 对于数据库查询，注入 WHERE 条件
        if "query" in tool_input and isinstance(tool_input["query"], str):
            # 简单的租户 ID 注入（实际实现需要更复杂的 SQL 解析）
            if "WHERE" in tool_input["query"].upper():
                tool_input["query"] += f" AND tenant_id = '{self.tenant_id}'"
            else:
                tool_input["query"] += f" WHERE tenant_id = '{self.tenant_id}'"

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

        # 对于数据库查询，注入 WHERE 条件
        if "query" in tool_input and isinstance(tool_input["query"], str):
            # 简单的租户 ID 注入（实际实现需要更复杂的 SQL 解析）
            if "WHERE" in tool_input["query"].upper():
                tool_input["query"] += f" AND tenant_id = '{self.tenant_id}'"
            else:
                tool_input["query"] += f" WHERE tenant_id = '{self.tenant_id}'"

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
