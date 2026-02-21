# -*- coding: utf-8 -*-
"""
学习节点 (Learning Node) - LangGraph 节点

自动学习循环节点，实现双知识系统的核心功能：
    1. 处理成功查询 → 提炼知识 → 保存到静态知识库
    2. 处理失败查询 → 学习修复方案 → 保存到动态学习库
    3. 增强 Schema 内省 → 自动发现表结构知识

与 ReflectionNode 配合使用，实现完整的自学习循环。

作者: Data Agent Team
版本: 1.0.0
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import MessagesState

from ..knowledge.knowledge_base import (
    KnowledgeBaseService,
    create_knowledge_base,
    ErrorCategory
)

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

class LearningOutcome(str, Enum):
    """学习结果类型"""
    SUCCESS_TEMPLATE_SAVED = "success_template_saved"       # 成功查询已保存
    ERROR_LEARNING_SAVED = "error_learning_saved"           # 错误学习已保存
    NO_LEARNING_NEEDED = "no_learning_needed"              # 无需学习
    LEARNING_FAILED = "learning_failed"                     # 学习失败


@dataclass
class LearningResult:
    """学习结果"""
    outcome: LearningOutcome
    entry_id: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "outcome": self.outcome.value,
            "entry_id": self.entry_id,
            "message": self.message,
            "metadata": self.metadata or {},
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# 学习节点
# ============================================================================

class LearningNode:
    """
    学习节点 - 自动学习循环的核心

    在查询执行后进行学习：
    1. 如果查询成功，提炼查询模板并保存到静态知识库
    2. 如果查询失败，记录错误和修复方案到动态学习库
    3. 自动发现和记录表结构知识

    配置选项:
        - enable_success_learning: 是否从成功查询学习
        - enable_error_learning: 是否从错误学习
        - enable_schema_introspection: 是否启用 Schema 内省
        - min_success_rate: 保存成功查询的最小成功率阈值
    """

    def __init__(
        self,
        enable_success_learning: bool = True,
        enable_error_learning: bool = True,
        enable_schema_introspection: bool = True,
        min_success_rate: float = 0.8,
        enable_logging: bool = True
    ):
        """初始化学习节点

        Args:
            enable_success_learning: 是否从成功查询学习
            enable_error_learning: 是否从错误学习
            enable_schema_introspection: 是否启用 Schema 内省
            min_success_rate: 保存成功查询的最小成功率阈值
            enable_logging: 是否启用日志
        """
        self.enable_success_learning = enable_success_learning
        self.enable_error_learning = enable_error_learning
        self.enable_schema_introspection = enable_schema_introspection
        self.min_success_rate = min_success_rate
        self.enable_logging = enable_logging

        # 知识库服务缓存（按租户）
        self._knowledge_bases: Dict[str, KnowledgeBaseService] = {}

    def __call__(self, state: MessagesState) -> Dict[str, Any]:
        """执行学习分析

        Args:
            state: LangGraph 消息状态

        Returns:
            更新后的状态，包含学习结果
        """
        messages = state["messages"]

        # 提取租户 ID
        tenant_id = self._extract_tenant_id(state)

        # 分析执行结果
        learning_result = self._analyze_and_learn(messages, tenant_id)

        # 记录学习结果
        if self.enable_logging:
            self._log_learning(learning_result)

        # 创建学习消息
        learning_message = self._create_learning_message(learning_result)

        return {
            "messages": [learning_message],
            "__learning_result__": learning_result.to_dict()
        }

    def _extract_tenant_id(self, state: MessagesState) -> str:
        """从状态中提取租户 ID

        Args:
            state: LangGraph 消息状态

        Returns:
            租户 ID
        """
        # 从状态中获取租户 ID
        return state.get("tenant_id", "default_tenant")

    def _get_knowledge_base(self, tenant_id: str) -> KnowledgeBaseService:
        """获取或创建知识库服务

        Args:
            tenant_id: 租户 ID

        Returns:
            KnowledgeBaseService 实例
        """
        if tenant_id not in self._knowledge_bases:
            self._knowledge_bases[tenant_id] = create_knowledge_base(tenant_id=tenant_id)
        return self._knowledge_bases[tenant_id]

    def _analyze_and_learn(
        self,
        messages: list,
        tenant_id: str
    ) -> LearningResult:
        """分析消息并执行学习

        Args:
            messages: 消息列表
            tenant_id: 租户 ID

        Returns:
            学习结果
        """
        # 获取反思结果
        reflection_result = self._get_reflection_result(messages)

        # 获取用户问题和 SQL
        user_question = self._extract_user_question(messages)
        sql_query = self._extract_sql_query(messages)
        tables_used = self._extract_tables_used(messages, sql_query)

        # 根据反思结果决定学习策略
        if reflection_result:
            if reflection_result.get("success", False):
                return self._process_success_learning(
                    user_question, sql_query, tables_used, tenant_id, messages
                )
            else:
                return self._process_error_learning(
                    user_question, sql_query, reflection_result, tenant_id
                )
        else:
            # 没有反思结果，尝试从消息内容判断
            return self._infer_and_learn(
                messages, user_question, sql_query, tables_used, tenant_id
            )

    def _get_reflection_result(self, messages: list) -> Optional[Dict[str, Any]]:
        """从状态中获取反思结果

        Args:
            messages: 消息列表

        Returns:
            反思结果字典，如果不存在则返回 None
        """
        # 反思结果通常存储在消息的附加字段中
        # 这里我们检查最后一条消息是否包含反思信息
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # 检查是否是反思消息
                content = msg.content
                if isinstance(content, str) and "自我修正" in content:
                    # 尝试从工具调用中提取错误信息
                    return self._parse_reflection_from_message(msg)
        return None

    def _parse_reflection_from_message(self, message: AIMessage) -> Optional[Dict[str, Any]]:
        """从 AI 消息中解析反思结果

        Args:
            message: AI 消息

        Returns:
            反思结果字典
        """
        # 尝试从消息内容中提取错误信息
        content = message.content
        if not isinstance(content, str):
            return None

        # 检查是否包含错误信息
        if "执行失败" in content or "错误" in content:
            # 简单的错误分类
            error_category = self._classify_error_from_content(content)
            return {
                "success": False,
                "error_category": error_category,
                "error_message": content[:500],  # 前 500 字符
                "fix_suggestion": ""
            }

        return {"success": True}

    def _classify_error_from_content(self, content: str) -> str:
        """从内容中分类错误类型

        Args:
            content: 错误内容

        Returns:
            错误类别字符串
        """
        content_lower = content.lower()

        if "column" in content_lower and ("does not exist" in content_lower or "not found" in content_lower):
            return ErrorCategory.COLUMN_NOT_FOUND.value
        elif "relation" in content_lower and "does not exist" in content_lower:
            return ErrorCategory.TABLE_NOT_FOUND.value
        elif "syntax error" in content_lower:
            return ErrorCategory.SQL_SYNTAX.value
        elif "假设表名" in content:
            return ErrorCategory.ASSUMED_TABLE_NAME.value
        else:
            return ErrorCategory.UNKNOWN.value

    async def _process_success_learning(
        self,
        question: str,
        sql: str,
        tables: List[str],
        tenant_id: str,
        messages: list
    ) -> LearningResult:
        """处理成功查询的学习

        Args:
            question: 用户问题
            sql: SQL 查询
            tables: 涉及的表
            tenant_id: 租户 ID
            messages: 消息列表

        Returns:
            学习结果
        """
        if not self.enable_success_learning:
            return LearningResult(
                outcome=LearningOutcome.NO_LEARNING_NEEDED,
                message="成功查询学习已禁用"
            )

        if not sql or not tables:
            return LearningResult(
                outcome=LearningOutcome.NO_LEARNING_NEEDED,
                message="缺少必要的学习数据（SQL 或表名）"
            )

        try:
            kb = self._get_knowledge_base(tenant_id)

            # 生成答案描述
            answer = self._generate_answer_description(question, sql, tables, messages)

            # 保存到知识库
            entry_id = await kb.save_validated_query(
                question=question,
                sql=sql,
                tables=tables,
                answer=answer
            )

            logger.info(f"[LearningNode] 成功查询已学习: {entry_id}")

            return LearningResult(
                outcome=LearningOutcome.SUCCESS_TEMPLATE_SAVED,
                entry_id=entry_id,
                message=f"成功查询已保存为模板: {question[:50]}...",
                metadata={
                    "question": question,
                    "sql": sql,
                    "tables": tables
                }
            )

        except Exception as e:
            logger.error(f"[LearningNode] 成功查询学习失败: {e}")
            return LearningResult(
                outcome=LearningOutcome.LEARNING_FAILED,
                message=f"学习失败: {str(e)}"
            )

    async def _process_error_learning(
        self,
        question: str,
        sql: str,
        reflection_result: Dict[str, Any],
        tenant_id: str
    ) -> LearningResult:
        """处理错误查询的学习

        Args:
            question: 用户问题
            sql: SQL 查询
            reflection_result: 反思结果
            tenant_id: 租户 ID

        Returns:
            学习结果
        """
        if not self.enable_error_learning:
            return LearningResult(
                outcome=LearningOutcome.NO_LEARNING_NEEDED,
                message="错误查询学习已禁用"
            )

        try:
            kb = self._get_knowledge_base(tenant_id)

            # 提取错误信息
            error_category_str = reflection_result.get("error_category", ErrorCategory.UNKNOWN.value)
            error_message = reflection_result.get("error_message", "")
            fix_suggestion = reflection_result.get("fix_suggestion", "")

            # 转换错误类别
            try:
                error_category = ErrorCategory(error_category_str)
            except ValueError:
                error_category = ErrorCategory.UNKNOWN

            # 生成修复建议（如果未提供）
            if not fix_suggestion:
                fix_suggestion = self._generate_fix_suggestion(error_category, error_message)

            # 保存到学习库
            learning_id = await kb.save_learning(
                error_category=error_category,
                error_message=error_message,
                fix_suggestion=fix_suggestion,
                original_query=sql,
                metadata={"question": question} if question else {}
            )

            logger.info(f"[LearningNode] 错误学习已保存: {learning_id}")

            return LearningResult(
                outcome=LearningOutcome.ERROR_LEARNING_SAVED,
                entry_id=learning_id,
                message=f"错误学习已保存: {error_category.value}",
                metadata={
                    "error_category": error_category.value,
                    "error_message": error_message[:100] if error_message else ""
                }
            )

        except Exception as e:
            logger.error(f"[LearningNode] 错误学习失败: {e}")
            return LearningResult(
                outcome=LearningOutcome.LEARNING_FAILED,
                message=f"学习失败: {str(e)}"
            )

    def _infer_and_learn(
        self,
        messages: list,
        question: str,
        sql: str,
        tables: List[str],
        tenant_id: str
    ) -> LearningResult:
        """推断执行结果并学习

        当没有反思结果时，从消息内容推断执行结果

        Args:
            messages: 消息列表
            question: 用户问题
            sql: SQL 查询
            tables: 涉及的表
            tenant_id: 租户 ID

        Returns:
            学习结果
        """
        # 查找最后一条工具消息
        last_tool_message = None
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                last_tool_message = msg
                break

        if not last_tool_message:
            return LearningResult(
                outcome=LearningOutcome.NO_LEARNING_NEEDED,
                message="无工具执行结果，跳过学习"
            )

        # 检查工具返回内容
        content = self._extract_tool_content(last_tool_message.content)

        # 判断是否成功
        if self._is_successful_result(content):
            return self._process_success_learning(question, sql, tables, tenant_id, messages)
        else:
            # 提取错误信息
            error_message = content[:500]
            error_category = self._classify_error_from_content(error_message)

            reflection_result = {
                "success": False,
                "error_category": error_category,
                "error_message": error_message
            }

            return self._process_error_learning(question, sql, reflection_result, tenant_id)

    def _extract_tool_content(self, content) -> str:
        """从 ToolMessage.content 中提取实际文本内容

        Args:
            content: ToolMessage.content

        Returns:
            提取的文本内容
        """
        if isinstance(content, str):
            return content

        if isinstance(content, list):
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

    def _is_successful_result(self, content: str) -> bool:
        """判断是否是成功的执行结果

        Args:
            content: 工具返回内容

        Returns:
            是否成功
        """
        content_stripped = content.strip()

        # 检查是否是有效的 JSON 响应
        try:
            data = json.loads(content_stripped)
            if isinstance(data, (dict, list)):
                # 检查是否包含错误关键词
                content_lower = content_stripped.lower()
                error_keywords = ['error', 'failed', 'exception', 'traceback']
                for keyword in error_keywords:
                    if keyword in content_lower and len(content_stripped) < 500:
                        return False
                return True
        except json.JSONDecodeError:
            pass

        # 检查是否包含错误关键词
        content_lower = content.lower()
        error_indicators = [
            'error:', 'error:', 'failed:', 'exception:', 'traceback',
            'does not exist', 'syntax error', 'permission denied'
        ]

        for indicator in error_indicators:
            if indicator in content_lower:
                return False

        return True

    def _generate_answer_description(
        self,
        question: str,
        sql: str,
        tables: List[str],
        messages: list
    ) -> str:
        """生成答案描述

        Args:
            question: 用户问题
            sql: SQL 查询
            tables: 涉及的表
            messages: 消息列表

        Returns:
            答案描述
        """
        # 尝试从 AI 消息中提取答案
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and isinstance(msg.content, str):
                content = msg.content
                # 简单提取：取前 200 字符作为答案
                if "执行成功" in content or "查询成功" in content:
                    # 提取答案部分
                    lines = content.split('\n')
                    answer_lines = []
                    for line in lines:
                        if line.strip() and not line.startswith('**') and not line.startswith('[CHART'):
                            answer_lines.append(line.strip())
                        if len(answer_lines) >= 3:
                            break
                    if answer_lines:
                        return ' '.join(answer_lines)[:200]

        # 默认答案描述
        return f"使用 SQL 查询 {', '.join(tables)} 表获取数据"

    def _generate_fix_suggestion(
        self,
        error_category: ErrorCategory,
        error_message: str
    ) -> str:
        """生成修复建议

        Args:
            error_category: 错误类别
            error_message: 错误消息

        Returns:
            修复建议
        """
        suggestions = {
            ErrorCategory.COLUMN_NOT_FOUND: (
                "建议：使用 get_schema() 查看表结构，确认正确的列名；"
                "检查列名拼写是否正确。"
            ),
            ErrorCategory.TABLE_NOT_FOUND: (
                "建议：使用 list_tables() 查看可用的表名；"
                "检查表名拼写是否正确。"
            ),
            ErrorCategory.ASSUMED_TABLE_NAME: (
                "建议：不要使用假设的英文表名，使用 list_tables() 获取实际的表名。"
            ),
            ErrorCategory.SQL_SYNTAX: (
                "建议：检查 SQL 语法，特别注意引号和逗号的位置；"
                "确保 LIMIT 子句在最后。"
            ),
            ErrorCategory.TYPE_MISMATCH: (
                "建议：使用 get_schema() 检查字段数据类型；"
                "对字段进行类型转换（CAST）。"
            ),
        }

        base = suggestions.get(error_category, "建议：请检查查询并重试。")

        # 如果有具体错误信息，添加到建议中
        if error_message:
            return f"{base}\n具体错误: {error_message[:200]}"

        return base

    def _extract_user_question(self, messages: list) -> str:
        """从消息列表中提取用户问题

        Args:
            messages: 消息列表

        Returns:
            用户问题
        """
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str):
                    return content
                elif isinstance(content, list) and len(content) > 0:
                    return str(content[0]) if isinstance(content[0], str) else ""
        return ""

    def _extract_sql_query(self, messages: list) -> Optional[str]:
        """从消息列表中提取 SQL 查询

        Args:
            messages: 消息列表

        Returns:
            SQL 查询字符串
        """
        # 查找最近的 SQL 查询（从 AIMessage 的 tool_calls 中）
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') in ['query', 'execute_sql', 'sql_query', 'execute_query']:
                        args = tc.get('args', {})
                        sql = args.get('query') or args.get('sql', '')
                        if sql:
                            return sql
        return None

    def _extract_tables_used(
        self,
        messages: list,
        sql: Optional[str]
    ) -> List[str]:
        """从消息和 SQL 中提取使用的表名

        Args:
            messages: 消息列表
            sql: SQL 查询

        Returns:
            表名列表
        """
        tables = []

        # 从 SQL 中提取表名
        if sql:
            import re
            # 简单的 FROM 子句提取
            from_matches = re.findall(r'FROM\s+["`\'"]?([a-zA-Z0-9_\u4e00-\u9fa5]+)["`\'"]?', sql, re.IGNORECASE)
            tables.extend(from_matches)

            # JOIN 子句提取
            join_matches = re.findall(r'JOIN\s+["`\'"]?([a-zA-Z0-9_\u4e00-\u9fa5]+)["`\'"]?', sql, re.IGNORECASE)
            tables.extend(join_matches)

        # 去重
        return list(set(tables))

    def _log_learning(self, result: LearningResult) -> None:
        """记录学习结果

        Args:
            result: 学习结果
        """
        if result.outcome == LearningOutcome.SUCCESS_TEMPLATE_SAVED:
            logger.info(f"[LearningNode] 成功查询已保存: {result.entry_id}")
        elif result.outcome == LearningOutcome.ERROR_LEARNING_SAVED:
            logger.info(f"[LearningNode] 错误学习已保存: {result.entry_id}")
        elif result.outcome == LearningOutcome.NO_LEARNING_NEEDED:
            logger.debug(f"[LearningNode] 跳过学习: {result.message}")
        else:
            logger.warning(f"[LearningNode] 学习失败: {result.message}")

    def _create_learning_message(self, result: LearningResult) -> AIMessage:
        """创建学习消息

        Args:
            result: 学习结果

        Returns:
            AI 消息
        """
        if result.outcome == LearningOutcome.SUCCESS_TEMPLATE_SAVED:
            content = "**学习完成**\n\n查询模板已保存到知识库，供后续相似查询参考。"
        elif result.outcome == LearningOutcome.ERROR_LEARNING_SAVED:
            content = "**学习完成**\n\n错误修复方案已保存到学习库。"
        elif result.outcome == LearningOutcome.NO_LEARNING_NEEDED:
            content = f"**无需学习**\n\n{result.message}"
        else:
            content = f"**学习失败**\n\n{result.message}"

        return AIMessage(content=content)


# ============================================================================
# 工厂函数
# ============================================================================

def create_learning_node(
    enable_success_learning: bool = True,
    enable_error_learning: bool = True,
    enable_schema_introspection: bool = True,
    min_success_rate: float = 0.8,
    enable_logging: bool = True
) -> LearningNode:
    """创建学习节点

    Args:
        enable_success_learning: 是否从成功查询学习
        enable_error_learning: 是否从错误学习
        enable_schema_introspection: 是否启用 Schema 内省
        min_success_rate: 保存成功查询的最小成功率阈值
        enable_logging: 是否启用日志

    Returns:
        LearningNode 实例
    """
    return LearningNode(
        enable_success_learning=enable_success_learning,
        enable_error_learning=enable_error_learning,
        enable_schema_introspection=enable_schema_introspection,
        min_success_rate=min_success_rate,
        enable_logging=enable_logging
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 模拟测试
    print("=" * 60)
    print("学习节点测试")
    print("=" * 60)

    node = create_learning_node()

    # 模拟成功查询的状态
    print("\n[测试] 处理成功查询")
    success_result = node._process_success_learning(
        question="2023年的销售趋势",
        sql="SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as total FROM orders WHERE EXTRACT(YEAR FROM order_date) = 2023 GROUP BY month ORDER BY month",
        tables=["orders"],
        tenant_id="test_tenant",
        messages=[]
    )
    print(f"  结果: {success_result.outcome.value}")
    print(f"  消息: {success_result.message}")

    # 模拟错误查询的学习
    print("\n[测试] 处理错误查询")
    error_result = node._process_error_learning(
        question="显示销售数据",
        sql="SELECT * FROM sales",
        reflection_result={
            "success": False,
            "error_category": "table_not_found",
            "error_message": "relation 'sales' does not exist"
        },
        tenant_id="test_tenant"
    )
    print(f"  结果: {error_result.outcome.value}")
    print(f"  消息: {error_result.message}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
