# -*- coding: utf-8 -*-
"""
XAI Logger Middleware - 可解释性日志中间件
===========================================

记录 AI 推理过程，提供可解释性。

核心功能:
    - 记录推理步骤
    - 工具调用追踪
    - 决策点日志
    - 性能指标收集
    - 双通道写入（数据库 + 文件）

版本: 2.1.0 - 集成 AgentLogger 双通道写入
作者: BMad Master
"""

import time
import asyncio
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field

# DeepAgents 中间件接口导入
from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain_core.messages.tool import ToolMessage
from langgraph.types import Command
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse, ModelCallResult, AgentState
from langgraph.runtime import Runtime


# ============================================================================
# 日志数据结构
# ============================================================================

@dataclass
class ReasoningStep:
    """推理步骤记录"""
    step_number: int
    description: str
    tool_used: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0


@dataclass
class DecisionPoint:
    """决策点记录"""
    decision_id: str
    description: str
    options: List[str]
    selected_option: str
    reasoning: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class XAILog:
    """完整的 XAI 日志"""
    session_id: str
    tenant_id: str
    user_query: str

    # 时间线
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    decision_points: List[DecisionPoint] = field(default_factory=list)

    # 性能指标
    total_processing_time_ms: float = 0
    llm_calls: int = 0
    tool_executions: int = 0

    # 元数据
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def add_reasoning_step(
        self,
        description: str,
        tool_used: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None
    ):
        """添加推理步骤"""
        step = ReasoningStep(
            step_number=len(self.reasoning_steps) + 1,
            description=description,
            tool_used=tool_used,
            input_data=input_data,
            output_data=output_data
        )
        self.reasoning_steps.append(step)

    def add_tool_call(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """添加工具调用记录"""
        call = ToolCall(
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            success=success,
            error_message=error_message
        )
        if call.end_time:
            call.duration_ms = (call.end_time - call.start_time) * 1000
        self.tool_calls.append(call)
        self.tool_executions += 1

    def add_decision_point(
        self,
        decision_id: str,
        description: str,
        options: List[str],
        selected_option: str,
        reasoning: str
    ):
        """添加决策点记录"""
        decision = DecisionPoint(
            decision_id=decision_id,
            description=description,
            options=options,
            selected_option=selected_option,
            reasoning=reasoning
        )
        self.decision_points.append(decision)

    def finalize(self):
        """完成日志记录"""
        self.end_time = time.time()
        self.total_processing_time_ms = (self.end_time - self.start_time) * 1000


# ============================================================================
# XAILoggerMiddleware
# ============================================================================

class XAILoggerMiddleware(AgentMiddleware):
    """
    可解释性日志中间件（增强版）

    记录 AI 推理过程，提供完整的决策透明度。
    支持双通道写入：数据库 + 文件。

    使用示例:
    ```python
    from AgentV2.middleware import XAILoggerMiddleware

    middleware = XAILoggerMiddleware(
        session_id="session_123",
        tenant_id="tenant_abc",
        enable_persistence=True  # 启用持久化
    )
    ```
    """

    def __init__(
        self,
        session_id: str,
        tenant_id: str,
        enable_detailed_logging: bool = True,
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
        enable_persistence: bool = True,  # 新增：启用持久化
        user_id: Optional[str] = None
    ):
        """
        初始化 XAI 日志中间件

        Args:
            session_id: 会话 ID
            tenant_id: 租户 ID
            enable_detailed_logging: 是否启用详细日志
            log_to_file: 是否记录到文件
            log_file_path: 日志文件路径
            enable_persistence: 是否启用持久化（双通道写入）
            user_id: 用户 ID
        """
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.enable_detailed_logging = enable_detailed_logging
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path
        self.enable_persistence = enable_persistence

        # 当前日志
        self._current_log: Optional[XAILog] = None

        # 历史日志
        self._log_history: List[XAILog] = []

        # AgentLogger 实例（用于持久化）
        self._agent_logger = None

        # 初始化 AgentLogger
        if enable_persistence:
            try:
                from ..utils.agent_logger import AgentLogger
                self._agent_logger = AgentLogger(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    user_id=user_id,
                    log_to_db=True,
                    log_to_file=True
                )
            except ImportError:
                # 如果无法导入，继续使用内存日志
                pass

    # ========================================================================
    # DeepAgents 框架接口实现
    # ========================================================================

    def before_agent(self, state: AgentState, runtime: Runtime) -> Dict[str, Any] | None:
        """
        在 Agent 执行前开始日志记录（同步版本）

        这是 DeepAgents 框架的标准接口方法。

        Args:
            state: Agent 状态（包含 messages 等信息）
            runtime: 运行时上下文

        Returns:
            状态更新字典或 None
        """
        # 提取用户查询
        messages = state.get("messages", [])
        user_query = str(messages[-1]) if messages else ""

        # 创建新的日志会话
        self._current_log = XAILog(
            session_id=self.session_id,
            tenant_id=self.tenant_id,
            user_query=user_query
        )

        # 记录初始步骤
        self._current_log.add_reasoning_step(
            description="接收用户查询",
            input_data={"query": user_query}
        )

        # 🔧 同步版本：创建后台任务记录持久化日志
        if self._agent_logger:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在运行的事件循环中创建后台任务
                    asyncio.create_task(self._agent_logger.log_step(
                        step=0,
                        node="agent_start",
                        message_type="agent_start",
                        content={"user_query": user_query},
                        raw_message=f"[Agent Start] Session: {self.session_id}, Query: {user_query[:100]}"
                    ))
            except RuntimeError:
                # 没有事件循环，跳过持久化
                pass

        # 在状态中注入日志记录器引用
        return {"__xai_logger__": self}

    async def abefore_agent(
        self, state: AgentState, runtime: Runtime
    ) -> Dict[str, Any] | None:
        """
        在 Agent 执行前开始日志记录（异步版本）

        这是 DeepAgents 框架的标准接口方法。

        Args:
            state: Agent 状态
            runtime: 运行时上下文

        Returns:
            状态更新字典或 None
        """
        # 提取用户查询
        messages = state.get("messages", [])
        user_query = str(messages[-1]) if messages else ""

        # 创建新的日志会话
        self._current_log = XAILog(
            session_id=self.session_id,
            tenant_id=self.tenant_id,
            user_query=user_query
        )

        # 记录初始步骤
        self._current_log.add_reasoning_step(
            description="接收用户查询",
            input_data={"query": user_query}
        )

        # 持久化：记录开始日志
        if self._agent_logger:
            await self._agent_logger.log_step(
                step=0,
                node="agent_start",
                message_type="agent_start",
                content={"user_query": user_query},
                raw_message=f"[Agent Start] Session: {self.session_id}, Query: {user_query[:100]}"
            )

        # 在状态中注入日志记录器引用
        return {"__xai_logger__": self}

    def after_agent(self, state: AgentState, runtime: Runtime) -> Dict[str, Any] | None:
        """
        在 Agent 执行后完成日志记录（同步版本）

        这是 DeepAgents 框架的标准接口方法。

        Args:
            state: Agent 状态
            runtime: 运行时上下文

        Returns:
            状态更新字典或 None
        """
        if self._current_log:
            # 完成日志
            self._current_log.finalize()

            # 保存到历史
            self._log_history.append(self._current_log)

            # 可选：写入文件
            if self.log_to_file and self.log_file_path:
                self._write_to_file()

            # 🔧 同步版本：创建后台任务记录结束日志并关闭
            if self._agent_logger:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 记录结束日志
                        asyncio.create_task(self._agent_logger.log_step(
                            node="agent_end",
                            message_type="agent_end",
                            content=self._extract_summary(),
                            raw_message=f"[Agent End] Session: {self.session_id}, Steps: {len(self._current_log.reasoning_steps)}"
                        ))
                        # 创建关闭任务
                        asyncio.create_task(self._flush_and_close())
                except RuntimeError:
                    # 没有事件循环，忽略
                    pass

        # 返回日志摘要
        return {"__xai_log__": self._extract_summary()}

    async def aafter_agent(
        self, state: Dict[str, Any], runtime: Any
    ) -> Dict[str, Any] | None:
        """
        在 Agent 执行后完成日志记录（异步版本）

        这是 DeepAgents 框架的标准接口方法。

        Args:
            state: Agent 状态
            runtime: 运行时上下文

        Returns:
            状态更新字典或 None
        """
        if self._current_log:
            # 完成日志
            self._current_log.finalize()

            # 保存到历史
            self._log_history.append(self._current_log)

            # 可选：写入文件
            if self.log_to_file and self.log_file_path:
                self._write_to_file()

            # 🔧 异步版本：直接关闭持久化日志记录器
            if self._agent_logger:
                await self._agent_logger.log_step(
                    node="agent_end",
                    message_type="agent_end",
                    content=self._extract_summary(),
                    raw_message=f"[Agent End] Session: {self.session_id}, Steps: {len(self._current_log.reasoning_steps)}"
                )
                await self._agent_logger.close()

        # 返回日志摘要
        return {"__xai_log__": self._extract_summary()}

    async def _flush_and_close(self):
        """异步刷新并关闭日志记录器（用于后台任务）"""
        if self._agent_logger:
            try:
                await self._agent_logger.close()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"关闭AgentLogger时出错: {e}")

    # ========================================================================
    # 向后兼容的接口（保留但不使用）
    # ========================================================================

    def pre_process(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        向后兼容方法：在 Agent 执行前开始日志记录

        .. deprecated::
            请使用 before_agent/abefore_agent 代替。此方法仅为向后兼容保留。
        """
        # 创建新的日志会话
        self._current_log = XAILog(
            session_id=self.session_id,
            tenant_id=self.tenant_id,
            user_query=str(agent_input.get("messages", [{}])[-1])
        )

        # 记录初始步骤
        self._current_log.add_reasoning_step(
            description="接收用户查询",
            input_data={"query": self._current_log.user_query}
        )

        # 在输入中注入日志记录器引用
        agent_input["__xai_logger__"] = self

        return agent_input

    def post_process(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        向后兼容方法：在 Agent 执行后完成日志记录

        .. deprecated::
            请使用 after_agent/aafter_agent 代替。此方法仅为向后兼容保留。
        """
        if self._current_log:
            # 完成日志
            self._current_log.finalize()

            # 添加到输出
            agent_output["__xai_log__"] = self._extract_summary()

            # 保存到历史
            self._log_history.append(self._current_log)

            # 可选：写入文件
            if self.log_to_file and self.log_file_path:
                self._write_to_file()

            # 🔧 新增：关闭持久化日志记录器
            if self._agent_logger:
                try:
                    # 尝试异步关闭
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 创建后台任务关闭
                        asyncio.create_task(self._flush_and_close())
                    else:
                        # 没有运行的事件循环，在后台线程中关闭
                        import threading
                        def close_logger():
                            try:
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                new_loop.run_until_complete(self._agent_logger.close())
                                new_loop.close()
                            except Exception as e:
                                import logging
                                logging.getLogger(__name__).warning(f"关闭AgentLogger失败: {e}")
                        thread = threading.Thread(target=close_logger, daemon=True)
                        thread.start()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"关闭AgentLogger时出错: {e}")

        return agent_output

    def log_tool_call(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """记录工具调用（同步版本）"""
        if self._current_log and self.enable_detailed_logging:
            self._current_log.add_tool_call(
                tool_name=tool_name,
                input_data=input_data,
                output_data=output_data,
                success=success,
                error_message=error_message
            )

            # 同时记录推理步骤
            self._current_log.add_reasoning_step(
                description=f"调用工具: {tool_name}",
                tool_used=tool_name,
                input_data=input_data,
                output_data=output_data
            )

            # 持久化写入 - 创建后台任务
            if self._agent_logger:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在事件循环中运行，创建任务
                        asyncio.create_task(self._agent_logger.log_step(
                            node=tool_name,
                            message_type="tool_call",
                            content={
                                "tool_name": tool_name,
                                "input_data": input_data,
                                "output_data": output_data,
                                "success": success
                            },
                            raw_message=f"调用工具: {tool_name}",
                            metadata={"error": error_message} if error_message else None
                        ))
                except RuntimeError:
                    # 没有事件循环，忽略持久化
                    pass

    def log_reasoning_step(
        self,
        description: str,
        tool_used: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None
    ):
        """记录推理步骤（同步版本）"""
        if self._current_log and self.enable_detailed_logging:
            self._current_log.add_reasoning_step(
                description=description,
                tool_used=tool_used,
                input_data=input_data,
                output_data=output_data
            )

            # 持久化写入 - 创建后台任务
            if self._agent_logger:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._agent_logger.log_step(
                            node=tool_used or "reasoning",
                            message_type="ai_message",
                            content={
                                "description": description,
                                "tool_used": tool_used,
                                "input_data": input_data,
                                "output_data": output_data
                            },
                            raw_message=description
                        ))
                except RuntimeError:
                    pass

    def log_decision(
        self,
        decision_id: str,
        description: str,
        options: List[str],
        selected_option: str,
        reasoning: str
    ):
        """记录决策点"""
        if self._current_log and self.enable_detailed_logging:
            self._current_log.add_decision_point(
                decision_id=decision_id,
                description=description,
                options=options,
                selected_option=selected_option,
                reasoning=reasoning
            )

    def _extract_summary(self) -> Dict[str, Any]:
        """提取日志摘要"""
        if not self._current_log:
            return {}

        return {
            "session_id": self._current_log.session_id,
            "tenant_id": self._current_log.tenant_id,
            "reasoning_steps": len(self._current_log.reasoning_steps),
            "tool_calls": len(self._current_log.tool_calls),
            "decision_points": len(self._current_log.decision_points),
            "total_time_ms": self._current_log.total_processing_time_ms,
            "steps_summary": [step.description for step in self._current_log.reasoning_steps],
            "tools_used": [call.tool_name for call in self._current_log.tool_calls],
            # 🔧 新增：返回完整的推理步骤详情
            "reasoning_steps_detail": [
                {
                    "step_number": step.step_number,
                    "description": step.description,
                    "tool_used": step.tool_used,
                    "input_data": step.input_data,
                    "output_data": step.output_data,
                    "duration_ms": step.duration_ms,
                }
                for step in self._current_log.reasoning_steps
            ],
            # 🔧 新增：返回完整的工具调用详情
            "tool_calls_detail": [
                {
                    "tool_name": call.tool_name,
                    "input_data": call.input_data,
                    "output_data": call.output_data,
                    "success": call.success,
                    "error_message": call.error_message,
                    "duration_ms": call.duration_ms,
                }
                for call in self._current_log.tool_calls
            ],
        }

    def _write_to_file(self):
        """写入日志文件"""
        import json
        from pathlib import Path

        if not self.log_file_path:
            return

        try:
            log_file = Path(self.log_file_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump(self._extract_summary(), f, ensure_ascii=False, indent=2)
                f.write('\n')

        except Exception as e:
            print(f"[WARN] 写入日志文件失败: {e}")

    def get_current_log(self) -> Optional[XAILog]:
        """获取当前日志"""
        return self._current_log

    def get_log_history(self) -> List[XAILog]:
        """获取日志历史"""
        return self._log_history.copy()

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """
        包装工具调用以记录 XAI 日志（同步版本）

        这是 deepagents 中间件接口的要求。

        Args:
            request: The tool call request being processed
            handler: The handler function to call with the request

        Returns:
            The raw ToolMessage, or a Command
        """
        # 提取工具调用信息
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "unknown")
        tool_input = tool_call.get("args", {})

        # 记录工具调用开始
        if self.enable_detailed_logging:
            self.log_tool_call(
                tool_name=tool_name,
                input_data=tool_input,
                success=True,
                error_message=None
            )

        # 🔧 同步版本：创建后台任务记录工具调用开始
        if self._agent_logger:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._agent_logger.log_step(
                        node=tool_name,
                        message_type="tool_call_start",
                        content={"tool_name": tool_name, "input_data": tool_input},
                        raw_message=f"[Tool Call] {tool_name}"
                    ))
            except RuntimeError:
                pass

        # 执行工具调用
        try:
            result = handler(request)

            # 记录成功结果
            if self.enable_detailed_logging and hasattr(result, 'content'):
                if self._current_log:
                    # 更新最后一次工具调用的输出
                    if self._current_log.tool_calls:
                        self._current_log.tool_calls[-1].output_data = {"result": result.content}
                        self._current_log.tool_calls[-1].success = True

            # 🔧 同步版本：创建后台任务记录工具调用成功
            if self._agent_logger:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._agent_logger.log_step(
                            node=tool_name,
                            message_type="tool_call_success",
                            content={
                                "tool_name": tool_name,
                                "input_data": tool_input,
                                "output_data": result.content if hasattr(result, 'content') else str(result)
                            },
                            raw_message=f"[Tool Success] {tool_name}"
                        ))
                except RuntimeError:
                    pass

            return result

        except Exception as e:
            # 记录失败结果
            if self.enable_detailed_logging:
                if self._current_log and self._current_log.tool_calls:
                    self._current_log.tool_calls[-1].success = False
                    self._current_log.tool_calls[-1].error_message = str(e)

            # 🔧 同步版本：创建后台任务记录工具调用失败
            if self._agent_logger:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._agent_logger.log_step(
                            node=tool_name,
                            message_type="tool_call_error",
                            content={
                                "tool_name": tool_name,
                                "input_data": tool_input,
                                "error": str(e)
                            },
                            raw_message=f"[Tool Error] {tool_name}: {str(e)[:100]}",
                            metadata={"error_type": type(e).__name__}
                        ))
                except RuntimeError:
                    pass

            # 重新抛出异常
            raise

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """
        包装工具调用以记录 XAI 日志（异步版本）

        这是 deepagents 中间件接口的异步要求。

        Args:
            request: The tool call request being processed
            handler: The async handler function to call with the request

        Returns:
            The raw ToolMessage, or a Command
        """
        # 提取工具调用信息
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "unknown")
        tool_input = tool_call.get("args", {})

        # 记录工具调用开始
        if self.enable_detailed_logging:
            self.log_tool_call(
                tool_name=tool_name,
                input_data=tool_input,
                success=True,
                error_message=None
            )

        # 🔧 持久化：记录工具调用开始
        if self._agent_logger:
            await self._agent_logger.log_step(
                node=tool_name,
                message_type="tool_call_start",
                content={"tool_name": tool_name, "input_data": tool_input},
                raw_message=f"[Tool Call] {tool_name}"
            )

        # 执行异步工具调用
        try:
            result = await handler(request)

            # 记录成功结果
            if self.enable_detailed_logging and hasattr(result, 'content'):
                if self._current_log:
                    # 更新最后一次工具调用的输出
                    if self._current_log.tool_calls:
                        self._current_log.tool_calls[-1].output_data = {"result": result.content}
                        self._current_log.tool_calls[-1].success = True

            # 🔧 持久化：记录工具调用成功
            if self._agent_logger:
                await self._agent_logger.log_step(
                    node=tool_name,
                    message_type="tool_call_success",
                    content={
                        "tool_name": tool_name,
                        "input_data": tool_input,
                        "output_data": result.content if hasattr(result, 'content') else str(result)
                    },
                    raw_message=f"[Tool Success] {tool_name}"
                )

            return result

        except Exception as e:
            # 记录失败结果
            if self.enable_detailed_logging:
                if self._current_log and self._current_log.tool_calls:
                    self._current_log.tool_calls[-1].success = False
                    self._current_log.tool_calls[-1].error_message = str(e)

            # 🔧 持久化：记录工具调用失败
            if self._agent_logger:
                await self._agent_logger.log_step(
                    node=tool_name,
                    message_type="tool_call_error",
                    content={
                        "tool_name": tool_name,
                        "input_data": tool_input,
                        "error": str(e)
                    },
                    raw_message=f"[Tool Error] {tool_name}: {str(e)[:100]}",
                    metadata={"error_type": type(e).__name__}
                )

            # 重新抛出异常
            raise

    def wrap_model_call(self, request, handler) -> Any:
        """
        包装模型调用以记录推理步骤（同步版本）

        这是 deepagents 中间件接口的扩展方法。

        Args:
            request: The model call request
            handler: The handler function to call

        Returns:
            The model output
        """
        # 记录推理步骤
        if self.enable_detailed_logging:
            self.log_reasoning_step(
                description="LLM 模型调用",
                tool_used=None,
                input_data={"request": str(request)[:200]}  # 截断以避免日志过大
            )

        # 执行模型调用
        result = handler(request)

        # 更新 LLM 调用计数
        if self._current_log:
            self._current_log.llm_calls += 1

        return result

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelCallResult:
        """
        包装模型调用以记录推理步骤（异步版本）

        这是 deepagents 中间件接口的异步扩展方法，用于 astream/ainvoke 等异步上下文。

        Args:
            request: The model call request
            handler: The async handler function to call

        Returns:
            The model output
        """
        # 记录推理步骤
        if self.enable_detailed_logging:
            self.log_reasoning_step(
                description="LLM 模型调用 (异步)",
                tool_used=None,
                input_data={"request": str(request)[:200]}
            )

        # 执行异步模型调用
        result = await handler(request)

        # 更新 LLM 调用计数
        if self._current_log:
            self._current_log.llm_calls += 1

        return result


# ============================================================================
# 便捷函数
# ============================================================================

def create_xai_logger(
    session_id: str,
    tenant_id: str,
    enable_detailed_logging: bool = True
) -> XAILoggerMiddleware:
    """
    创建 XAI 日志中间件的便捷函数

    Args:
        session_id: 会话 ID
        tenant_id: 租户 ID
        enable_detailed_logging: 是否启用详细日志

    Returns:
        XAILoggerMiddleware 实例
    """
    return XAILoggerMiddleware(
        session_id=session_id,
        tenant_id=tenant_id,
        enable_detailed_logging=enable_detailed_logging
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("XAI Logger 中间件测试")
    print("=" * 60)

    # 创建日志中间件
    middleware = create_xai_logger(
        session_id="test_session",
        tenant_id="test_tenant"
    )

    # 模拟 Agent 执行
    agent_input = {"messages": [{"role": "user", "content": "查询数据"}]}
    enhanced_input = middleware.pre_process(agent_input)

    print("[INFO] 日志会话已创建")

    # 模拟推理过程
    middleware.log_reasoning_step(
        description="解析用户查询意图",
        tool_used=None
    )

    middleware.log_tool_call(
        tool_name="get_schema",
        input_data={"table": "users"},
        output_data={"columns": ["id", "name", "email"]}
    )

    middleware.log_decision(
        decision_id="chart_type",
        description="选择图表类型",
        options=["bar", "line", "pie"],
        selected_option="bar",
        reasoning="数据是分类比较，柱状图最合适"
    )

    # 模拟 Agent 输出
    agent_output = {"messages": [{"role": "assistant", "content": "查询完成"}]}
    final_output = middleware.post_process(agent_output)

    # 显示日志摘要
    if "__xai_log__" in final_output:
        print("[INFO] XAI 日志摘要:")
        summary = final_output["__xai_log__"]
        print(f"  - 推理步骤: {summary['reasoning_steps']}")
        print(f"  - 工具调用: {summary['tool_calls']}")
        print(f"  - 决策点: {summary['decision_points']}")
        print(f"  - 总耗时: {summary['total_time_ms']:.2f}ms")

    print("\n[PASS] XAI 日志中间件测试通过")
