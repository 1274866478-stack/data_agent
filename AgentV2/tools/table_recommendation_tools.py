# -*- coding: utf-8 -*-
"""
Table Recommendation Tools - 智能表推荐工具
==========================================

基于查询内容智能推荐最相关的数据表。

核心功能:
    - get_recommended_tables: 基于查询内容推荐表
    - get_table_description_by_name: 获取指定表的描述信息
    - explain_table_selection: 解释为什么推荐某个表

版本: 1.0.0
作者: BMad Master
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 导入表描述配置
try:
    from ..table_config.table_descriptions import (
        TABLE_DESCRIPTIONS,
        get_recommended_tables,
        get_table_description,
        get_all_high_priority_tables,
        TERM_TO_TABLE_MAPPING
    )
    TABLE_CONFIG_AVAILABLE = True
    logger.info("✅ [table_recommendation_tools] 表描述配置加载成功")
except ImportError as e:
    TABLE_CONFIG_AVAILABLE = False
    logger.warning(f"⚠️ [table_recommendation_tools] 表描述配置未找到: {e}")


# ============================================================================
# 智能表推荐工具
# ============================================================================

def get_recommended_tables_for_query(query: str) -> str:
    """
    基于查询内容推荐最相关的表（使用实际表名）

    这是给 AI Agent 调用的主要工具函数。

    Args:
        query: 用户查询，如 "2023年销售趋势"

    Returns:
        推荐的表列表及理由（JSON 字符串），返回实际表名而非预设表名

    Example:
        >>> get_recommended_tables_for_query("2023年销售趋势")
        {
            "query": "2023年销售趋势",
            "recommended_tables": [
                {
                    "table_name": "Sales_2023",  # 🔧 实际表名
                    "description": "预聚合的月度销售数据，直接支持趋势分析",
                    "priority": "high",
                    "match_score": 0.85,
                    "matched_keywords": ["销售", "趋势"]
                }
            ],
            "total_count": 1
        }
    """
    if not TABLE_CONFIG_AVAILABLE:
        return json.dumps({
            "error": "表描述配置未加载",
            "error_type": "config_not_available",
            "query": query
        }, ensure_ascii=False)

    try:
        # 🔧 新增：首先获取实际表名
        from ..tools.database_tools import list_tables

        # 获取实际表列表（connection_id 会从上下文中获取）
        list_tables_result = json.loads(list_tables())
        actual_tables = list_tables_result.get("tables", [])
        enhanced_tables = list_tables_result.get("tables_enhanced", [])

        # 🔧 关键修改：基于实际表名进行推荐
        # 如果有增强表信息，直接使用；否则使用原始表名
        if enhanced_tables:
            # 根据查询关键词匹配增强表信息
            query_lower = query.lower()
            recommendations = []

            for table_info in enhanced_tables:
                table_name = table_info["name"]
                # 🔧 修复：显式处理 None 值，即使字段显式设置为 None 也会被转换为空列表
                recommended_for = table_info.get("recommended_for") or []
                priority = table_info.get("priority", "medium")

                # 计算匹配分数
                matched_keywords = [kw for kw in recommended_for if kw in query_lower]
                if matched_keywords:
                    # 🔧 修复：添加 or [] 防止 len(None) 错误
                    safe_recommended_for = recommended_for or []
                    match_score = len(matched_keywords) / len(safe_recommended_for) if safe_recommended_for else 0

                    # 优先级加分
                    priority_boost = {"high": 0.3, "medium": 0.15, "low": 0}.get(priority, 0)
                    total_score = min(match_score + priority_boost, 1.0)

                    recommendations.append({
                        "table_name": table_name,  # 🔧 使用实际表名
                        "description": table_info.get("description", ""),
                        "priority": priority,
                        "match_score": total_score,
                        "matched_keywords": matched_keywords
                    })

            # 按分数排序
            recommendations.sort(key=lambda x: -x["match_score"])

            return json.dumps({
                "query": query,
                "recommended_tables": recommendations[:5],  # 返回前5个
                "total_count": len(recommendations)
            }, ensure_ascii=False, indent=2)
        else:
            # 没有增强信息，返回空结果（让 LLM 使用 list_tables）
            return json.dumps({
                "query": query,
                "recommended_tables": [],
                "message": "没有可用的表推荐，请使用 list_tables() 获取实际表名"
            }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"get_recommended_tables_for_query error: {e}")
        return json.dumps({
            "error": str(e),
            "error_type": "execution_error",
            "query": query
        }, ensure_ascii=False)


def get_table_description_by_name(table_name: str) -> str:
    """
    获取指定表的详细描述信息

    Args:
        table_name: 表名

    Returns:
        表的详细描述（JSON 字符串）

    Example:
        >>> get_table_description_by_name("月度销售表")
        {
            "table_name": "月度销售表",
            "description": "预聚合的月度销售数据...",
            "recommended_for": ["销售", "趋势", ...],
            "priority": "high",
            "contains": ["销售额", "订单数", ...],
            "aliases": ["monthly_sales", ...],
            "typical_queries": [...]
        }
    """
    if not TABLE_CONFIG_AVAILABLE:
        return json.dumps({
            "error": "表描述配置未加载",
            "error_type": "config_not_available"
        }, ensure_ascii=False)

    try:
        config = get_table_description(table_name)

        if config is None:
            return json.dumps({
                "error": f"表 '{table_name}' 的描述信息未找到",
                "error_type": "table_not_found_in_config",
                "table_name": table_name,
                "available_tables": list(TABLE_DESCRIPTIONS.keys())
            }, ensure_ascii=False)

        result = {
            "table_name": table_name,
            "description": config.get("description", ""),
            "recommended_for": config.get("recommended_for", []),
            "priority": config.get("priority", "medium"),
            "contains": config.get("contains", []),
            "aliases": config.get("aliases", []),
            "typical_queries": config.get("typical_queries", [])
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"get_table_description_by_name error: {e}")
        return json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)


def explain_table_selection(query: str, table_name: str) -> str:
    """
    解释为什么选择某个表来回答查询

    Args:
        query: 用户查询
        table_name: 被选择的表名

    Returns:
        选择理由说明（JSON 字符串）
    """
    if not TABLE_CONFIG_AVAILABLE:
        return json.dumps({
            "error": "表描述配置未加载",
            "error_type": "config_not_available"
        }, ensure_ascii=False)

    try:
        config = get_table_description(table_name)

        if config is None:
            return json.dumps({
                "error": f"表 '{table_name}' 的描述信息未找到",
                "error_type": "table_not_found_in_config"
            }, ensure_ascii=False)

        # 分析查询与表的相关性
        query_lower = query.lower()
        matched_keywords = []
        for kw in config.get("recommended_for", []):
            if kw in query_lower:
                matched_keywords.append(kw)

        result = {
            "query": query,
            "selected_table": table_name,
            # 🔧 修复：添加 or [] 防止 len(None) 错误
            "match_score": len(matched_keywords) / len(config.get("recommended_for") or [1]),
            "matched_keywords": matched_keywords,
            "explanation": {
                "why_this_table": config.get("description", ""),
                "best_for": config.get("recommended_for", []),
                "priority": config.get("priority", "medium")
            },
            "suggested_columns": config.get("contains", [])
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"explain_table_selection error: {e}")
        return json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)


def list_high_priority_tables() -> str:
    """
    列出所有高优先级的表

    这些表通常是预聚合的汇总表或核心业务表，
    对于大多数查询来说是最佳选择。

    Returns:
        高优先级表列表（JSON 字符串）
    """
    if not TABLE_CONFIG_AVAILABLE:
        return json.dumps({
            "error": "表描述配置未加载",
            "error_type": "config_not_available"
        }, ensure_ascii=False)

    try:
        high_priority = get_all_high_priority_tables()

        # 获取每个表的详细信息
        tables_with_details = []
        for table in high_priority:
            config = get_table_description(table)
            if config:
                tables_with_details.append({
                    "table_name": table,
                    "description": config.get("description", ""),
                    "recommended_for": config.get("recommended_for", []),
                    "aliases": config.get("aliases", [])
                })

        return json.dumps({
            "high_priority_tables": tables_with_details,
            "count": len(tables_with_details)
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"list_high_priority_tables error: {e}")
        return json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)


# ============================================================================
# 工具包装器（用于集成到 Agent）
# ============================================================================

def get_table_recommendation_tools():
    """
    获取所有表推荐工具的 LangChain Tool 列表

    Returns:
        LangChain StructuredTool 列表
    """
    from langchain_core.tools import StructuredTool

    return [
        StructuredTool.from_function(
            func=get_recommended_tables_for_query,
            name="get_recommended_tables",
            description=(
                "🎯 智能表推荐工具 - 基于查询内容推荐最相关的数据表\n\n"
                "**使用场景**：\n"
                "- 当你需要查询数据但不确定使用哪个表时\n"
                "- 当查询涉及多个可能的表时，找出最合适的表\n"
                "- 快速找到高优先级（预聚合、核心业务）表\n\n"
                "**参数**：\n"
                "- query (str): 用户查询，如 '2023年销售趋势'\n\n"
                "**返回**：\n"
                "- 推荐的表列表，包含表名、描述、优先级、匹配理由\n"
                "- 建议的 SQL 查询示例\n\n"
                "**示例**：\n"
                "输入: '2023年销售趋势'\n"
                "输出: 推荐使用 '月度销售表'（高优先级，包含预聚合的销售趋势数据）"
            )
        ),
        StructuredTool.from_function(
            func=get_table_description_by_name,
            name="get_table_description",
            description=(
                "获取指定表的详细描述信息\n\n"
                "**参数**：\n"
                "- table_name (str): 表名\n\n"
                "**返回**：\n"
                "- 表描述、推荐用途、包含的列、别名等信息"
            )
        ),
        StructuredTool.from_function(
            func=list_high_priority_tables,
            name="list_high_priority_tables",
            description=(
                "列出所有高优先级的数据表\n\n"
                "这些表通常是预聚合的汇总表或核心业务表，\n"
                "对于大多数查询来说是最佳选择。\n\n"
                "**参数**: 无\n\n"
                "**返回**：高优先级表列表及其描述"
            )
        )
    ]


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("表推荐工具测试")
    print("=" * 60)

    # 测试 1: 查询推荐
    print("\n[测试 1] 查询 '2023年销售趋势' 的推荐表")
    result = get_recommended_tables_for_query("2023年销售趋势")
    print(result)

    # 测试 2: 获取表描述
    print("\n[测试 2] 获取 '月度销售表' 的描述")
    result = get_table_description_by_name("月度销售表")
    print(result)

    # 测试 3: 列出高优先级表
    print("\n[测试 3] 列出所有高优先级表")
    result = list_high_priority_tables()
    print(result)
