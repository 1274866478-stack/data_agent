# -*- coding: utf-8 -*-
"""
Loop Detection Middleware - 循环检测中间件
============================================

核心功能:
    - 检测重复的工具调用序列
    - 防止 Agent 陷入无限循环
    - 记录工具调用历史
    - 达到阈值时终止执行

作者: Data Agent Team
版本: 1.0.0
"""

import logging
from typing import Any, Dict, Optional, Callable, Awaitable, List
from collections import deque

from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain_core.messages.tool import ToolMessage
from langgraph.types import Command
from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)


class LoopDetectionMiddleware(AgentMiddleware):
    """
    循环检测中间件

    检测 Agent 陷入工具调用循环的情况，防止无限重试。

    检测策略:
        1. 工具调用次数限制
        2. 相同工具序列重复检测
        3. 失败重试次数限制

    使用示例:
    ```python
    from AgentV2.middleware import LoopDetectionMiddleware

    middleware = [LoopDetectionMiddleware(max_calls=10)]
    agent = create_deep_agent(model, tools, middleware)
    ```
    """

    def __init__(
        self,
        max_tool_calls: int = 15,
        loop_window_size: int = 6,
        max_same_tool_calls: int = 3,
        max_consecutive_failures: int = 3
    ):
        """
        初始化循环检测中间件

        Args:
            max_tool_calls: 单轮对话最大工具调用次数
            loop_window_size: 检测循环的滑动窗口大小
            max_same_tool_calls: 相同工具最大连续调用次数
            max_consecutive_failures: 最大连续失败次数
        """
        self.max_tool_calls = max_tool_calls
        self.loop_window_size = loop_window_size
        self.max_same_tool_calls = max_same_tool_calls
        self.max_consecutive_failures = max_consecutive_failures

        # 工具调用历史
        self._call_history: deque = deque(maxlen=loop_window_size)
        self._call_count = 0
        self._consecutive_failures = 0
        self._last_call_succeeded = True

    def _detect_loop(self) -> Optional[str]:
        """
        检测是否陷入循环

        Returns:
            检测到的循环描述，如果没有循环则返回 None
        """
        if len(self._call_history) < self.loop_window_size:
            return None

        history = list(self._call_history)

        # 1. 检测简单重复：所有调用都是同一个工具
        tool_names = [call["tool"] for call in history]
        if len(set(tool_names)) == 1:
            tool_name = tool_names[0]
            return f"检测到循环：连续 {len(history)} 次调用相同工具 '{tool_name}'"

        # 2. 检测模式重复：检测 ABABAB 或 ABCABC 模式
        # 尝试检测周期为 2, 3, 4 的模式
        for pattern_length in [2, 3, 4]:
            if len(history) >= pattern_length * 2:
                pattern = history[:pattern_length]
                is_repeating = True

                for i in range(pattern_length, len(history), pattern_length):
                    segment = history[i:i + pattern_length]
                    if len(segment) != pattern_length:
                        is_repeating = False
                        break

                    for j in range(pattern_length):
                        if pattern[j]["tool"] != segment[j]["tool"]:
                            is_repeating = False
                            break
                    if not is_repeating:
                        break

                if is_repeating:
                    pattern_str = " -> ".join([c["tool"] for c in pattern])
                    return f"检测到循环：重复执行模式 '{pattern_str}'"

        # 3. 检测 list_tables -> execute_query -> error -> list_tables 循环
        if len(history) >= 4:
            recent_tools = [call["tool"] for call in history[-4:]]
            # 检测常见的循环模式
            common_loops = [
                ["list_tables", "execute_query", "list_tables"],
                ["list_tables", "get_schema", "execute_query", "list_tables"],
            ]
            for loop_pattern in common_loops:
                if recent_tools == loop_pattern:
                    pattern_str = " -> ".join(loop_pattern)
                    return f"检测到循环：重复执行 '{pattern_str}'"

        return None

    def _check_consecutive_same_tool(self, tool_name: str) -> Optional[str]:
        """
        检查连续调用相同工具

        Args:
            tool_name: 当前工具名称

        Returns:
            如果超过阈值，返回错误消息；否则返回 None
        """
        if len(self._call_history) < self.max_same_tool_calls:
            return None

        recent_calls = list(self._call_history)[-self.max_same_tool_calls:]
        if all(call["tool"] == tool_name for call in recent_calls):
            return f"检测到循环：连续 {self.max_same_tool_calls + 1} 次调用相同工具 '{tool_name}'"
        return None

    def _check_max_calls(self) -> Optional[str]:
        """
        检查是否超过最大调用次数

        Returns:
            如果超过限制，返回错误消息；否则返回 None
        """
        if self._call_count >= self.max_tool_calls:
            return f"超过最大工具调用次数限制 ({self.max_tool_calls})，可能陷入循环"
        return None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """
        包装工具调用以检测循环（同步版本）

        Args:
            request: 工具调用请求
            handler: 处理函数

        Returns:
            ToolMessage 或 Command 对象

        Raises:
            RuntimeError: 如果检测到循环
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "unknown")
        tool_args = tool_call.get("args", {})

        # 记录调用
        self._call_count += 1
        call_info = {"tool": tool_name, "args": tool_args}

        # 检查循环
        loop_error = (
            self._check_max_calls() or
            self._check_consecutive_same_tool(tool_name) or
            self._detect_loop()
        )

        if loop_error:
            logger.warning(f"LoopDetection: {loop_error}")
            # 返回错误消息而不是抛出异常
            error_content = (
                f"⚠️ 检测到工具调用循环，已自动终止。\n"
                f"原因: {loop_error}\n\n"
                f"建议：请尝试重新表述您的问题，或提供更具体的查询要求。"
            )
            error_message = ToolMessage(
                content=error_content,
                name=tool_name,
                tool_call_id=tool_call.get("id")
            )
            return Command(update={"messages": [error_message]})

        # 添加到历史
        self._call_history.append(call_info)

        # 执行工具调用
        try:
            result = handler(request)
            self._last_call_succeeded = True
            self._consecutive_failures = 0
            return result
        except Exception as e:
            self._last_call_succeeded = False
            self._consecutive_failures += 1

            # 检查连续失败次数
            if self._consecutive_failures >= self.max_consecutive_failures:
                error_content = (
                    f"⚠️ 检测到连续 {self._consecutive_failures} 次工具调用失败，已自动终止。\n"
                    f"最后错误: {str(e)[:100]}\n\n"
                    f"建议：请检查数据源配置或尝试不同的查询方式。"
                )
                error_message = ToolMessage(
                    content=error_content,
                    name=tool_name,
                    tool_call_id=tool_call.get("id")
                )
                return Command(update={"messages": [error_message]})

            raise

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """
        包装工具调用以检测循环（异步版本）

        Args:
            request: 工具调用请求
            handler: 异步处理函数

        Returns:
            ToolMessage 或 Command 对象
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "unknown")
        tool_args = tool_call.get("args", {})

        # 记录调用
        self._call_count += 1
        call_info = {"tool": tool_name, "args": tool_args}

        # 检查循环
        loop_error = (
            self._check_max_calls() or
            self._check_consecutive_same_tool(tool_name) or
            self._detect_loop()
        )

        if loop_error:
            logger.warning(f"LoopDetection: {loop_error}")
            error_content = (
                f"⚠️ 检测到工具调用循环，已自动终止。\n"
                f"原因: {loop_error}\n\n"
                f"建议：请尝试重新表述您的问题，或提供更具体的查询要求。"
            )
            error_message = ToolMessage(
                content=error_content,
                name=tool_name,
                tool_call_id=tool_call.get("id")
            )
            return Command(update={"messages": [error_message]})

        # 添加到历史
        self._call_history.append(call_info)

        # 执行工具调用
        try:
            result = await handler(request)
            self._last_call_succeeded = True
            self._consecutive_failures = 0
            return result
        except Exception as e:
            self._last_call_succeeded = False
            self._consecutive_failures += 1

            if self._consecutive_failures >= self.max_consecutive_failures:
                error_content = (
                    f"⚠️ 检测到连续 {self._consecutive_failures} 次工具调用失败，已自动终止。\n"
                    f"最后错误: {str(e)[:100]}\n\n"
                    f"建议：请检查数据源配置或尝试不同的查询方式。"
                )
                error_message = ToolMessage(
                    content=error_content,
                    name=tool_name,
                    tool_call_id=tool_call.get("id")
                )
                return Command(update={"messages": [error_message]})

            raise

    def reset(self):
        """重置循环检测状态（用于新会话）"""
        self._call_history.clear()
        self._call_count = 0
        self._consecutive_failures = 0
        self._last_call_succeeded = True

    def get_stats(self) -> Dict[str, Any]:
        """获取当前统计信息"""
        return {
            "call_count": self._call_count,
            "consecutive_failures": self._consecutive_failures,
            "history_length": len(self._call_history),
            "recent_calls": list(self._call_history)
        }


# ============================================================================
# 便捷函数
# ============================================================================

def create_loop_detection_middleware(
    max_tool_calls: int = 15,
    loop_window_size: int = 6,
    max_same_tool_calls: int = 3,
    max_consecutive_failures: int = 3
) -> LoopDetectionMiddleware:
    """
    创建循环检测中间件的便捷函数

    Args:
        max_tool_calls: 单轮对话最大工具调用次数
        loop_window_size: 检测循环的滑动窗口大小
        max_same_tool_calls: 相同工具最大连续调用次数
        max_consecutive_failures: 最大连续失败次数

    Returns:
        LoopDetectionMiddleware 实例
    """
    return LoopDetectionMiddleware(
        max_tool_calls=max_tool_calls,
        loop_window_size=loop_window_size,
        max_same_tool_calls=max_same_tool_calls,
        max_consecutive_failures=max_consecutive_failures
    )
