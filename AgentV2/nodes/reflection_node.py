# -*- coding: utf-8 -*-
"""
反思节点 (Reflection Node) - LangGraph 节点

这个节点在查询执行后进行反思和自修复，实现错误分析和修正建议功能。

核心功能：
    1. 分析执行结果
    2. 检测错误
    3. 生成修复建议
    4. 决定是否需要重试

作者: Data Agent Team
版本: 1.0.0
"""

import json
import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Literal
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import MessagesState

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """错误类别"""
    SQL_SYNTAX = "sql_syntax"           # SQL 语法错误
    COLUMN_NOT_FOUND = "column_not_found"  # 列不存在
    TABLE_NOT_FOUND = "table_not_found"    # 表不存在
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

    # 空结果指示词
    EMPTY_RESULT_INDICATORS = [
        'no data',
        'empty result',
        'no results',
        'found 0 rows',
        '[]',
        '{}',
    ]

    def __init__(
        self,
        max_retries: int = 3,
        enable_logging: bool = True
    ):
        """初始化反思节点

        Args:
            max_retries: 最大重试次数
            enable_logging: 是否启用日志
        """
        self.max_retries = max_retries
        self.enable_logging = enable_logging

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

        # 创建反思消息
        reflection_message = self._create_reflection_message(reflection)

        # 更新重试计数
        retry_count = state.get("__retry_count__", 0)
        if reflection.should_retry and retry_count < self.max_retries:
            retry_count += 1

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
        content = self._extract_tool_content(last_tool_message.content)
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
        content_lower = content.lower()
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

    def _log_reflection(self, reflection: ReflectionResult) -> None:
        """记录反思结果

        Args:
            reflection: 反思结果
        """
        if reflection.success:
            logger.info("[ReflectionNode] ✅ 执行成功")
        else:
            logger.warning(
                f"[ReflectionNode] ❌ 检测到错误: {reflection.error_category}"
            )
            logger.warning(f"  错误消息: {reflection.error_message}")
            logger.info(f"  修复建议: {reflection.fix_suggestion}")
            logger.info(f"  需要重试: {reflection.should_retry}")

    def _create_reflection_message(self, reflection: ReflectionResult) -> AIMessage:
        """创建反思消息

        Args:
            reflection: 反思结果

        Returns:
            AI 消息
        """
        if reflection.success:
            content = "✅ **执行成功**\n\n查询已成功执行，结果符合预期。"
        else:
            content = f"""🔄 **执行失败，正在进行自我修正**

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
    enable_logging: bool = True
) -> ReflectionNode:
    """创建反思节点

    Args:
        max_retries: 最大重试次数
        enable_logging: 是否启用日志

    Returns:
        ReflectionNode 实例
    """
    return ReflectionNode(
        max_retries=max_retries,
        enable_logging=enable_logging
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
