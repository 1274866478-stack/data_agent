# -*- coding: utf-8 -*-
"""
表描述和推荐配置 - Table Descriptions Configuration
====================================================

为智能表推荐提供表级别的元数据，包括：
- 表描述 (description)
- 推荐用途 (recommended_for)
- 优先级 (priority)
- 包含的列/指标 (contains)

版本: 1.0.0
作者: BMad Master
"""

from typing import List, Dict, Any, Optional


# ============================================================================
# 表描述配置
# ============================================================================

TABLE_DESCRIPTIONS: Dict[str, Dict[str, Any]] = {
    # ========== 销售相关表 ==========
    "月度销售表": {
        "description": "预聚合的月度销售数据，直接支持趋势分析，包含销售额、订单数等汇总指标",
        "recommended_for": ["销售", "趋势", "收入", "月度", "年度", "汇总", "月报", "年报", "同比增长", "环比增长"],
        "priority": "high",
        "contains": ["销售额", "订单数", "月份", "年份", "地区", "产品类别"],
        "aliases": ["monthly_sales", "sales_monthly", "sales_summary", "月度销售汇总", "销售汇总表"],
        "typical_queries": [
            "2023年销售趋势",
            "月度销售额变化",
            "年度销售对比",
            "各月订单数量趋势"
        ]
    },

    "销售订单表": {
        "description": "销售订单主表，包含订单级别信息和销售金额",
        "recommended_for": ["订单", "销售", "金额", "订单金额", "销售单", "订单查询"],
        "priority": "high",
        "contains": ["订单ID", "客户ID", "订单日期", "订单金额", "状态"],
        "aliases": ["orders", "sales_orders", "订单表", "销售表"],
        "typical_queries": [
            "查询所有订单",
            "订单金额统计",
            "订单状态分布"
        ]
    },

    # ========== 客户/用户相关表 ==========
    "用户表": {
        "description": "用户/客户基本信息表",
        "recommended_for": ["客户", "用户", "会员", "用户信息", "客户信息"],
        "priority": "medium",
        "contains": ["用户ID", "用户名", "邮箱", "电话", "注册日期"],
        "aliases": ["users", "customers", "客户表", "会员表"],
        "typical_queries": [
            "查询用户信息",
            "客户数量统计",
            "用户注册时间分布"
        ]
    },

    "客户表": {
        "description": "客户详细信息表",
        "recommended_for": ["客户", "顾客", "买家"],
        "priority": "medium",
        "contains": ["客户ID", "客户名称", "联系人", "地址", "行业"],
        "aliases": ["customers", "clients"],
        "typical_queries": [
            "客户列表",
            "按行业统计客户"
        ]
    },

    # ========== 产品相关表 ==========
    "产品表": {
        "description": "产品/商品基本信息表",
        "recommended_for": ["产品", "商品", "库存", "产品信息"],
        "priority": "medium",
        "contains": ["产品ID", "产品名称", "类别", "价格", "库存"],
        "aliases": ["products", "商品表", "items"],
        "typical_queries": [
            "产品列表",
            "产品价格查询",
            "库存统计"
        ]
    },

    # ========== 订单明细相关表 ==========
    "订单明细表": {
        "description": "订单明细表，包含每笔订单的产品级别详细信息",
        "recommended_for": ["订单明细", "订单详情", "明细", "产品销售", "销售明细"],
        "priority": "medium",
        "contains": ["明细ID", "订单ID", "产品ID", "数量", "单价"],
        "aliases": ["order_details", "order_items", "订单项表"],
        "typical_queries": [
            "订单明细查询",
            "产品销售数量",
            "订单产品分布"
        ]
    },

    # ========== 地区相关表 ==========
    "地区表": {
        "description": "地区/区域信息表",
        "recommended_for": ["地区", "区域", "省份", "城市", "地理"],
        "priority": "low",
        "contains": ["地区ID", "地区名称", "上级地区", "级别"],
        "aliases": ["regions", "areas", "区域表"],
        "typical_queries": [
            "地区列表",
            "按地区统计"
        ]
    },

    # ========== 类别相关表 ==========
    "分类表": {
        "description": "产品分类信息表",
        "recommended_for": ["分类", "类别", "产品分类"],
        "priority": "low",
        "contains": ["分类ID", "分类名称", "父分类"],
        "aliases": ["categories", "product_categories"],
        "typical_queries": [
            "产品分类",
            "分类层级"
        ]
    },

    # ========== 员工相关表 ==========
    "员工表": {
        "description": "员工/人员信息表",
        "recommended_for": ["员工", "人员", "职员", "工号"],
        "priority": "medium",
        "contains": ["员工ID", "姓名", "部门", "职位", "入职日期"],
        "aliases": ["employees", "staff", "人员表"],
        "typical_queries": [
            "员工列表",
            "部门人数统计"
        ]
    },
}


# ============================================================================
# 表推荐函数
# ============================================================================

def get_recommended_tables(
    query: str,
    available_tables: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    基于查询内容推荐最相关的表

    Args:
        query: 用户查询，如 "2023年销售趋势"
        available_tables: 可用的表名列表，如果为 None 则使用所有配置的表

    Returns:
        推荐的表列表，按优先级排序，每个元素包含:
        - table_name: 表名
        - description: 表描述
        - priority: 优先级
        - match_score: 匹配分数 (0-1)
        - matched_keywords: 匹配的关键词

    Example:
        >>> get_recommended_tables("2023年销售趋势")
        [
            {
                "table_name": "月度销售表",
                "description": "预聚合的月度销售数据...",
                "priority": "high",
                "match_score": 1.0,
                "matched_keywords": ["销售", "趋势"]
            }
        ]
    """
    if available_tables is None:
        available_tables = list(TABLE_DESCRIPTIONS.keys())

    query_lower = query.lower()
    recommendations = []

    for table, config in TABLE_DESCRIPTIONS.items():
        # 跳过不在可用表列表中的表
        if table not in available_tables:
            continue

        # 计算匹配分数
        matched_keywords = []
        for keyword in config.get("recommended_for", []):
            if keyword in query_lower:
                matched_keywords.append(keyword)

        # 如果有匹配关键词，计算匹配分数
        if matched_keywords:
            match_score = len(matched_keywords) / len(config.get("recommended_for", []))

            # 优先级加分
            priority_boost = {
                "high": 0.3,
                "medium": 0.15,
                "low": 0.0
            }.get(config.get("priority", "low"), 0.0)

            recommendations.append({
                "table_name": table,
                "description": config.get("description", ""),
                "priority": config.get("priority", "low"),
                "match_score": min(match_score + priority_boost, 1.0),
                "matched_keywords": matched_keywords
            })

    # 按匹配分数和优先级排序
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(
        key=lambda x: (
            -x["match_score"],  # 匹配分数降序
            priority_order.get(x["priority"], 99)  # 优先级升序
        )
    )

    return recommendations


def get_table_description(table_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定表的描述信息

    Args:
        table_name: 表名

    Returns:
        表描述配置，如果不存在则返回 None
    """
    return TABLE_DESCRIPTIONS.get(table_name)


def find_table_by_alias(alias: str) -> Optional[str]:
    """
    根据别名查找实际表名

    Args:
        alias: 表别名（如 "orders", "sales_orders"）

    Returns:
        实际表名，如果未找到则返回 None
    """
    alias_lower = alias.lower()

    for table_name, config in TABLE_DESCRIPTIONS.items():
        # 检查直接表名匹配
        if table_name.lower() == alias_lower:
            return table_name

        # 检查别名匹配
        for table_alias in config.get("aliases", []):
            if table_alias.lower() == alias_lower:
                return table_name

    return None


def get_all_high_priority_tables() -> List[str]:
    """
    获取所有高优先级的表名

    Returns:
        高优先级表名列表
    """
    return [
        table for table, config in TABLE_DESCRIPTIONS.items()
        if config.get("priority") == "high"
    ]


def enrich_tables_with_description(
    tables: List[str],
    include_all: bool = False
) -> List[Dict[str, Any]]:
    """
    为表列表添加描述信息

    Args:
        tables: 表名列表
        include_all: 是否包含所有表（即使没有配置描述）

    Returns:
        增强后的表信息列表
    """
    result = []

    for table in tables:
        config = TABLE_DESCRIPTIONS.get(table, {})

        if config or include_all:
            result.append({
                "name": table,
                "description": config.get("description", ""),
                "recommended_for": config.get("recommended_for", []),
                "priority": config.get("priority", "medium"),
                "has_config": bool(config)
            })

    return result


# ============================================================================
# 业务术语到表的映射
# ============================================================================

TERM_TO_TABLE_MAPPING: Dict[str, List[str]] = {
    "销售": ["月度销售表", "销售订单表"],
    "订单": ["销售订单表", "订单明细表"],
    "客户": ["用户表", "客户表"],
    "产品": ["产品表"],
    "库存": ["产品表"],
    "趋势": ["月度销售表"],
    "汇总": ["月度销售表"],
    "明细": ["订单明细表"],
}


def get_tables_by_term(term: str) -> List[str]:
    """
    根据业务术语获取相关表

    Args:
        term: 业务术语

    Returns:
        相关表名列表
    """
    term_lower = term.lower()

    # 直接匹配
    if term_lower in TERM_TO_TABLE_MAPPING:
        return TERM_TO_TABLE_MAPPING[term_lower]

    # 模糊匹配
    result = []
    for key, tables in TERM_TO_TABLE_MAPPING.items():
        if key in term_lower or term_lower in key:
            result.extend(tables)

    return list(set(result))


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    # 测试推荐功能
    print("=" * 60)
    print("表推荐测试")
    print("=" * 60)

    test_queries = [
        "2023年销售趋势",
        "查询所有客户信息",
        "产品库存统计",
        "订单明细查询",
        "月度销售汇总"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        recommendations = get_recommended_tables(query)
        for rec in recommendations:
            print(f"  - {rec['table_name']} ({rec['priority']}) - 匹配度: {rec['match_score']:.2f}")
            print(f"    描述: {rec['description'][:50]}...")
            print(f"    匹配关键词: {rec['matched_keywords']}")
