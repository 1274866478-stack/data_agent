# -*- coding: utf-8 -*-
"""
知识检索工具 - LangChain 工具集成

提供 LangChain 兼容的知识检索工具：
    - search_knowledge: 搜索静态知识库
    - search_learnings: 搜索动态学习库
    - save_validated_query: 保存验证通过的查询
    - save_learning: 保存错误学习

这些工具可以直接集成到 Agent 的工具列表中。

作者: Data Agent Team
版本: 1.0.0
"""

import json
import logging
from typing import Dict, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .knowledge_base import (
    KnowledgeBaseService,
    ErrorCategory,
    create_knowledge_base
)

logger = logging.getLogger(__name__)


# ============================================================================
# 工具参数模型
# ============================================================================

class SearchKnowledgeInput(BaseModel):
    """搜索知识库输入"""
    query: str = Field(description="查询文本，如'2023年销售趋势'")
    knowledge_type: Optional[str] = Field(
        default=None,
        description="知识类型: query_template, business_rule, schema_info, table_mapping"
    )
    n_results: int = Field(default=5, description="返回结果数量，默认5")
    min_score: float = Field(default=0.6, description="最小相似度分数，默认0.6")


class SearchLearningsInput(BaseModel):
    """搜索学习记录输入"""
    query: str = Field(description="查询文本，如'表不存在错误'")
    error_category: Optional[str] = Field(
        default=None,
        description="错误类别: sql_syntax, column_not_found, table_not_found, etc."
    )
    n_results: int = Field(default=5, description="返回结果数量，默认5")
    min_score: float = Field(default=0.5, description="最小相似度分数，默认0.5")


class SaveValidatedQueryInput(BaseModel):
    """保存验证查询输入"""
    question: str = Field(description="用户问题，如'2023年的销售趋势'")
    sql: str = Field(description="生成的SQL查询")
    tables: str = Field(description="涉及的表名，用逗号分隔，如'orders,products'")
    answer: Optional[str] = Field(default=None, description="答案描述（可选）")


class SaveLearningInput(BaseModel):
    """保存学习记录输入"""
    error_category: str = Field(description="错误类别，如'table_not_found'")
    error_message: str = Field(description="错误消息，如\"relation 'sales' does not exist\"")
    fix_suggestion: str = Field(description="修复建议")
    corrected_sql: Optional[str] = Field(default=None, description="修正后的SQL（可选）")
    original_query: Optional[str] = Field(default=None, description="原始查询（可选）")


# ============================================================================
# 全局知识库服务实例（按租户缓存）
# ============================================================================

_knowledge_bases: Dict[str, KnowledgeBaseService] = {}


def get_knowledge_base(tenant_id: str = "default_tenant") -> KnowledgeBaseService:
    """获取或创建知识库服务

    Args:
        tenant_id: 租户 ID

    Returns:
        KnowledgeBaseService 实例
    """
    if tenant_id not in _knowledge_bases:
        _knowledge_bases[tenant_id] = create_knowledge_base(tenant_id=tenant_id)
    return _knowledge_bases[tenant_id]


def clear_knowledge_base_cache():
    """清除知识库服务缓存"""
    _knowledge_bases.clear()


# ============================================================================
# 知识检索工具函数
# ============================================================================

async def search_knowledge(
    query: str,
    knowledge_type: Optional[str] = None,
    n_results: int = 5,
    min_score: float = 0.6,
    tenant_id: str = "default_tenant"
) -> str:
    """搜索静态知识库

    从静态知识库中检索相关知识，包括：
    - 查询模板：成功的 SQL 查询模式
    - 业务规则：业务逻辑和计算规则
    - Schema 信息：表结构和字段说明
    - 表名映射：表名和别名的关系

    Args:
        query: 查询文本，如'2023年销售趋势'
        knowledge_type: 知识类型 (query_template, business_rule, schema_info, table_mapping)
        n_results: 返回结果数量，默认5
        min_score: 最小相似度分数，默认0.6
        tenant_id: 租户 ID

    Returns:
        JSON 格式的检索结果

    Example:
        >>> result = await search_knowledge("2023年销售趋势")
        >>> print(result)
        {
            "query": "2023年销售趋势",
            "count": 2,
            "results": [
                {
                    "question": "2023年的销售趋势",
                    "sql": "SELECT ...",
                    "tables": ["orders"],
                    "similarity_score": 0.95
                }
            ]
        }
    """
    try:
        kb = get_knowledge_base(tenant_id)

        # 转换知识类型
        from .knowledge_base import KnowledgeType
        kt = None
        if knowledge_type:
            try:
                kt = KnowledgeType(knowledge_type)
            except ValueError:
                logger.warning(f"无效的知识类型: {knowledge_type}")

        # 执行搜索
        entries = await kb.search_knowledge(
            query=query,
            knowledge_type=kt,
            n_results=n_results,
            min_score=min_score
        )

        # 格式化结果
        results = []
        for entry in entries:
            results.append({
                "id": entry.id,
                "question": entry.question,
                "answer": entry.answer,
                "sql": entry.sql,
                "tables": entry.tables or [],
                "knowledge_type": entry.knowledge_type.value,
                "usage_count": entry.usage_count,
                "success_rate": entry.success_rate,
                "similarity_score": entry.metadata.get("similarity_score", 0.0)
            })

        return json.dumps({
            "query": query,
            "count": len(results),
            "results": results
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"搜索知识库失败: {e}")
        return json.dumps({
            "query": query,
            "count": 0,
            "results": [],
            "error": str(e)
        }, ensure_ascii=False, indent=2)


async def search_learnings(
    query: str,
    error_category: Optional[str] = None,
    n_results: int = 5,
    min_score: float = 0.5,
    tenant_id: str = "default_tenant"
) -> str:
    """搜索动态学习库

    从动态学习库中检索相似错误的修复方案。

    Args:
        query: 查询文本（错误信息或问题描述）
        error_category: 错误类别 (sql_syntax, column_not_found, table_not_found, etc.)
        n_results: 返回结果数量，默认5
        min_score: 最小相似度分数，默认0.5
        tenant_id: 租户 ID

    Returns:
        JSON 格式的检索结果

    Example:
        >>> result = await search_learnings("表不存在错误")
        >>> print(result)
        {
            "query": "表不存在错误",
            "count": 1,
            "results": [
                {
                    "error_category": "table_not_found",
                    "error_message": "relation 'sales' does not exist",
                    "fix_suggestion": "使用 list_tables() 查看实际表名",
                    "corrected_sql": "SELECT * FROM 订单表",
                    "applied_count": 5,
                    "success_rate": 0.8
                }
            ]
        }
    """
    try:
        kb = get_knowledge_base(tenant_id)

        # 转换错误类别
        ec = None
        if error_category:
            try:
                ec = ErrorCategory(error_category)
            except ValueError:
                logger.warning(f"无效的错误类别: {error_category}")

        # 执行搜索
        entries = await kb.search_learnings(
            query=query,
            error_category=ec,
            n_results=n_results,
            min_score=min_score
        )

        # 格式化结果
        results = []
        for entry in entries:
            results.append({
                "id": entry.id,
                "error_category": entry.error_category.value,
                "error_message": entry.error_message,
                "fix_suggestion": entry.fix_suggestion,
                "corrected_sql": entry.corrected_sql,
                "original_query": entry.original_query,
                "applied_count": entry.applied_count,
                "success_rate": entry.success_rate,
                "similarity_score": entry.metadata.get("similarity_score", 0.0)
            })

        return json.dumps({
            "query": query,
            "count": len(results),
            "results": results
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"搜索学习记录失败: {e}")
        return json.dumps({
            "query": query,
            "count": 0,
            "results": [],
            "error": str(e)
        }, ensure_ascii=False, indent=2)


async def save_validated_query(
    question: str,
    sql: str,
    tables: str,
    answer: Optional[str] = None,
    tenant_id: str = "default_tenant"
) -> str:
    """保存验证通过的查询到静态知识库

    当查询成功执行后，将问题和对应的 SQL 保存到知识库，
    供后续相似查询参考。

    Args:
        question: 用户问题
        sql: 生成的 SQL
        tables: 涉及的表名（逗号分隔）
        answer: 答案描述（可选）
        tenant_id: 租户 ID

    Returns:
        JSON 格式的保存结果

    Example:
        >>> result = await save_validated_query(
        ...     question="2023年的销售趋势",
        ...     sql="SELECT ...",
        ...     tables="orders"
        ... )
        >>> print(result)
        {
            "success": true,
            "id": "uuid",
            "message": "查询模板已保存"
        }
    """
    try:
        kb = get_knowledge_base(tenant_id)

        # 解析表名
        table_list = [t.strip() for t in tables.split(",") if t.strip()]

        # 保存查询
        entry_id = await kb.save_validated_query(
            question=question,
            sql=sql,
            tables=table_list,
            answer=answer
        )

        return json.dumps({
            "success": True,
            "id": entry_id,
            "message": "查询模板已保存",
            "question": question,
            "tables": table_list
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"保存查询失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


async def save_learning(
    error_category: str,
    error_message: str,
    fix_suggestion: str,
    corrected_sql: Optional[str] = None,
    original_query: Optional[str] = None,
    tenant_id: str = "default_tenant"
) -> str:
    """保存错误学习到动态学习库

    当查询失败后，将错误信息和修复方案保存到学习库，
    供后续相似错误自动应用修复。

    Args:
        error_category: 错误类别
        error_message: 错误消息
        fix_suggestion: 修复建议
        corrected_sql: 修正后的 SQL（可选）
        original_query: 原始查询（可选）
        tenant_id: 租户 ID

    Returns:
        JSON 格式的保存结果

    Example:
        >>> result = await save_learning(
        ...     error_category="table_not_found",
        ...     error_message="relation 'sales' does not exist",
        ...     fix_suggestion="使用 list_tables() 查看实际表名",
        ...     corrected_sql="SELECT * FROM 订单表"
        ... )
        >>> print(result)
        {
            "success": true,
            "id": "uuid",
            "message": "学习记录已保存"
        }
    """
    try:
        kb = get_knowledge_base(tenant_id)

        # 转换错误类别
        ec = ErrorCategory(error_category)

        # 保存学习
        learning_id = await kb.save_learning(
            error_category=ec,
            error_message=error_message,
            fix_suggestion=fix_suggestion,
            corrected_sql=corrected_sql,
            original_query=original_query
        )

        return json.dumps({
            "success": True,
            "id": learning_id,
            "message": "学习记录已保存",
            "error_category": error_category
        }, ensure_ascii=False, indent=2)

    except ValueError:
        logger.error(f"无效的错误类别: {error_category}")
        return json.dumps({
            "success": False,
            "error": f"无效的错误类别: {error_category}"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存学习失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


# ============================================================================
# LangChain 工具工厂函数
# ============================================================================

def create_knowledge_tools(tenant_id: str = "default_tenant") -> list:
    """创建知识检索工具列表

    这些工具可以直接添加到 Agent 的工具列表中。

    Args:
        tenant_id: 租户 ID

    Returns:
        LangChain 工具列表
    """
    tools = []

    # 创建带租户上下文的工具函数
    def make_search_knowledge():
        async def _search(query: str, knowledge_type: Optional[str] = None,
                         n_results: int = 5, min_score: float = 0.6) -> str:
            return await search_knowledge(query, knowledge_type, n_results, min_score, tenant_id)
        return _search

    def make_search_learnings():
        async def _search(query: str, error_category: Optional[str] = None,
                         n_results: int = 5, min_score: float = 0.5) -> str:
            return await search_learnings(query, error_category, n_results, min_score, tenant_id)
        return _search

    def make_save_validated_query():
        async def _save(question: str, sql: str, tables: str,
                       answer: Optional[str] = None) -> str:
            return await save_validated_query(question, sql, tables, answer, tenant_id)
        return _save

    def make_save_learning():
        async def _save(error_category: str, error_message: str, fix_suggestion: str,
                       corrected_sql: Optional[str] = None, original_query: Optional[str] = None) -> str:
            return await save_learning(error_category, error_message, fix_suggestion,
                                     corrected_sql, original_query, tenant_id)
        return _save

    # 搜索知识工具
    tools.append(StructuredTool.from_function(
        func=make_search_knowledge(),
        name="search_knowledge",
        description=(
            "搜索静态知识库，查找历史查询模板、业务规则和Schema信息。"
            "使用场景：当用户问题与历史查询相似时，可以先搜索知识库获取参考。"
            "参数：query (必填) - 查询文本；"
            "knowledge_type (可选) - 知识类型 (query_template/business_rule/schema_info/table_mapping)；"
            "n_results (可选) - 返回结果数量，默认5；"
            "min_score (可选) - 最小相似度分数，默认0.6"
        )
    ))

    # 搜索学习记录工具
    tools.append(StructuredTool.from_function(
        func=make_search_learnings(),
        name="search_learnings",
        description=(
            "搜索动态学习库，查找相似错误的修复方案。"
            "使用场景：当发生错误时，可以搜索学习库获取历史修复方案。"
            "参数：query (必填) - 查询文本（错误信息或问题描述）；"
            "error_category (可选) - 错误类别 (sql_syntax/column_not_found/table_not_found等)；"
            "n_results (可选) - 返回结果数量，默认5；"
            "min_score (可选) - 最小相似度分数，默认0.5"
        )
    ))

    # 保存验证查询工具
    tools.append(StructuredTool.from_function(
        func=make_save_validated_query(),
        name="save_validated_query",
        description=(
            "保存验证通过的查询到静态知识库。"
            "使用场景：当查询成功执行后，将问题和对应的SQL保存到知识库供后续参考。"
            "参数：question (必填) - 用户问题；"
            "sql (必填) - 生成的SQL；"
            "tables (必填) - 涉及的表名（逗号分隔）；"
            "answer (可选) - 答案描述"
        )
    ))

    # 保存学习记录工具
    tools.append(StructuredTool.from_function(
        func=make_save_learning(),
        name="save_learning",
        description=(
            "保存错误学习到动态学习库。"
            "使用场景：当查询失败后，将错误信息和修复方案保存到学习库。"
            "参数：error_category (必填) - 错误类别；"
            "error_message (必填) - 错误消息；"
            "fix_suggestion (必填) - 修复建议；"
            "corrected_sql (可选) - 修正后的SQL；"
            "original_query (可选) - 原始查询"
        )
    ))

    logger.info(f"创建 {len(tools)} 个知识工具，租户: {tenant_id}")
    return tools


# ============================================================================
# 同步版本的包装器（用于某些需要同步函数的场景）
# ============================================================================

def search_knowledge_sync(
    query: str,
    knowledge_type: Optional[str] = None,
    n_results: int = 5,
    min_score: float = 0.6,
    tenant_id: str = "default_tenant"
) -> str:
    """搜索静态知识库（同步版本）

    这是一个同步包装器，内部使用 asyncio.run 调用异步函数。
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果在已有事件循环中，使用 create_task
            import threading

            result_container = []

            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(
                        search_knowledge(query, knowledge_type, n_results, min_score, tenant_id)
                    )
                    result_container.append(result)
                finally:
                    new_loop.close()

            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join(timeout=10)

            if result_container:
                return result_container[0]
            else:
                return json.dumps({"error": "Timeout"}, ensure_ascii=False)
        else:
            return loop.run_until_complete(
                search_knowledge(query, knowledge_type, n_results, min_score, tenant_id)
            )
    except RuntimeError:
        return asyncio.run(
            search_knowledge(query, knowledge_type, n_results, min_score, tenant_id)
        )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test_knowledge_tools():
        print("=" * 60)
        print("知识工具测试")
        print("=" * 60)

        tenant_id = "test_tenant"

        # 创建 LangChain 工具
        print("\n[测试] 创建 LangChain 工具")
        tools = create_knowledge_tools(tenant_id)
        print(f"  创建了 {len(tools)} 个工具")
        for tool in tools:
            print(f"    - {tool.name}: {tool.description[:50]}...")

        # 测试保存查询
        print("\n[测试] 保存验证查询")
        result = await save_validated_query(
            question="2023年的销售趋势",
            sql="SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as total FROM orders WHERE EXTRACT(YEAR FROM order_date) = 2023 GROUP BY month ORDER BY month",
            tables="orders",
            tenant_id=tenant_id
        )
        print(f"  结果: {result[:200]}...")

        # 测试搜索知识
        print("\n[测试] 搜索知识")
        result = await search_knowledge("销售数据2023", tenant_id=tenant_id)
        print(f"  结果: {result[:200]}...")

        # 测试保存学习
        print("\n[测试] 保存学习记录")
        result = await save_learning(
            error_category="table_not_found",
            error_message="relation 'sales' does not exist",
            fix_suggestion="使用 list_tables() 查看实际表名",
            corrected_sql="SELECT * FROM 订单表",
            tenant_id=tenant_id
        )
        print(f"  结果: {result[:200]}...")

        # 测试搜索学习
        print("\n[测试] 搜索学习记录")
        result = await search_learnings("表不存在", tenant_id=tenant_id)
        print(f"  结果: {result[:200]}...")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    asyncio.run(test_knowledge_tools())
