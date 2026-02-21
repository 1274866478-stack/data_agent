# -*- coding: utf-8 -*-
"""
Schema 元数据配置 - Schema Metadata Configuration
====================================================

为 AgentV2 提供表关系、列语义和智能建议功能。

核心功能:
    - TABLE_RELATIONSHIPS: 表关系配置（外键、关联关系）
    - COLUMN_SEMANTICS: 列语义配置（列的位置、描述）
    - TABLE_ALIASES: 表别名映射
    - 智能建议函数：find_column_suggestion, suggest_join_query

版本: 1.0.0
作者: BMad Master
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 表关系配置
# ============================================================================

TABLE_RELATIONSHIPS: Dict[str, Dict[str, Any]] = {
    # ========== 用户与地址关系（最重要！） ==========
    "users": {
        "primary_key": "id",
        "display_name": "用户表",
        "description": "用户基本信息表",
        "foreign_keys": {},
        "relationships": [
            {
                "related_table": "addresses",
                "join_type": "LEFT JOIN",
                "join_condition": "users.id = addresses.user_id",
                "relationship": "one_to_many",
                "description": "一个用户可以有多个地址"
            }
        ],
        "columns_not_here": {
            "province": {"in_table": "addresses", "join_via": "user_id"},
            "city": {"in_table": "addresses", "join_via": "user_id"},
            "district": {"in_table": "addresses", "join_via": "user_id"},
            "detail_address": {"in_table": "addresses", "join_via": "user_id"},
        }
    },

    "addresses": {
        "primary_key": "id",
        "display_name": "地址表",
        "description": "用户地址信息表，包含省市区",
        "foreign_keys": {
            "user_id": {
                "references": ("users", "id"),
                "relationship": "many_to_one",
                "description": "地址属于一个用户"
            }
        },
        "relationships": [
            {
                "related_table": "users",
                "join_type": "INNER JOIN",
                "join_condition": "addresses.user_id = users.id",
                "relationship": "many_to_one",
                "description": "地址属于用户"
            }
        ],
        "important_columns": ["province", "city", "district", "is_default"]
    },

    # ========== 订单与订单明细关系 ==========
    "orders": {
        "primary_key": "id",
        "display_name": "订单表",
        "description": "销售订单主表",
        "foreign_keys": {
            "user_id": {
                "references": ("users", "id"),
                "relationship": "many_to_one",
                "description": "订单属于一个用户"
            }
        },
        "relationships": [
            {
                "related_table": "users",
                "join_type": "INNER JOIN",
                "join_condition": "orders.user_id = users.id",
                "relationship": "many_to_one"
            },
            {
                "related_table": "order_items",
                "join_type": "INNER JOIN",
                "join_condition": "orders.id = order_items.order_id",
                "relationship": "one_to_many",
                "description": "一个订单可以有多个明细项"
            }
        ],
        "columns_not_here": {
            "product_name": {"in_table": "products", "join_via": "order_items"},
            "quantity": {"in_table": "order_items", "join_via": "order_id"},
            "unit_price": {"in_table": "order_items", "join_via": "order_id"},
        }
    },

    "order_items": {
        "primary_key": "id",
        "display_name": "订单明细表",
        "description": "订单明细表，包含产品购买数量和单价",
        "foreign_keys": {
            "order_id": {
                "references": ("orders", "id"),
                "relationship": "many_to_one",
                "description": "明细属于一个订单"
            },
            "product_id": {
                "references": ("products", "id"),
                "relationship": "many_to_one",
                "description": "明细关联一个产品"
            }
        },
        "relationships": [
            {
                "related_table": "orders",
                "join_condition": "order_items.order_id = orders.id"
            },
            {
                "related_table": "products",
                "join_condition": "order_items.product_id = products.id"
            }
        ]
    },

    # ========== 产品与分类关系 ==========
    "products": {
        "primary_key": "id",
        "display_name": "产品表",
        "description": "产品/商品信息表",
        "foreign_keys": {
            "category_id": {
                "references": ("categories", "id"),
                "relationship": "many_to_one",
                "description": "产品属于一个分类"
            }
        },
        "relationships": [
            {
                "related_table": "categories",
                "join_condition": "products.category_id = categories.id"
            }
        ],
        "columns_not_here": {
            "category_name": {"in_table": "categories", "join_via": "category_id"},
        }
    },

    "categories": {
        "primary_key": "id",
        "display_name": "分类表",
        "description": "产品分类信息表",
        "relationships": [
            {
                "related_table": "products",
                "join_condition": "categories.id = products.category_id"
            }
        ]
    },
}

# ========== Excel 数据源的常见表映射 ==========
EXCEL_TABLE_MAPPINGS: Dict[str, Dict[str, List[str]]] = {
    "users": {
        "excel_sheets": ["users", "用户表", "Customers", "客户表"],
        "common_columns": ["id", "username", "email", "phone"],
    },
    "addresses": {
        "excel_sheets": ["addresses", "地址表"],
        "common_columns": ["id", "user_id", "province", "city", "district"],
    },
    "orders": {
        "excel_sheets": ["orders", "订单表", "Orders", "销售订单表"],
        "common_columns": ["id", "user_id", "order_date", "total_amount"],
    },
    "products": {
        "excel_sheets": ["products", "产品表", "Products", "商品表"],
        "common_columns": ["id", "name", "price", "category_id"],
    },
    "categories": {
        "excel_sheets": ["categories", "分类表", "Categories", "产品分类"],
        "common_columns": ["id", "name", "parent_id"],
    },
    "order_items": {
        "excel_sheets": ["order_items", "订单明细", "OrderItems", "订单详情"],
        "common_columns": ["id", "order_id", "product_id", "quantity", "unit_price"],
    },
}


# ============================================================================
# 列语义配置
# ============================================================================

COLUMN_SEMANTICS: Dict[str, Dict[str, Any]] = {
    # ========== 地理位置相关 ==========
    "province": {
        "display_name": "省份",
        "location_table": "addresses",
        "description": "省份信息，如'安徽'、'北京'等",
        "related_table": "users",
        "join_key": "user_id",
        "common_values": ["北京", "上海", "广东", "浙江", "江苏", "安徽", "山东", "河南"],
        "query_patterns": ["省份", "地区", "省", "按省", "各省"]
    },
    "city": {
        "display_name": "城市",
        "location_table": "addresses",
        "description": "城市信息",
        "related_table": "users",
        "join_key": "user_id",
        "common_values": ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉"],
        "query_patterns": ["城市", "市", "按城市"]
    },
    "district": {
        "display_name": "区县",
        "location_table": "addresses",
        "description": "区县信息",
        "related_table": "users",
        "join_key": "user_id"
    },

    # ========== 时间相关 ==========
    "order_date": {
        "display_name": "订单日期",
        "location_table": "orders",
        "description": "订单创建日期",
        "query_patterns": ["日期", "时间", "年", "月", "日"]
    },
    "registration_date": {
        "display_name": "注册日期",
        "location_table": "users",
        "description": "用户注册日期"
    },

    # ========== 金额相关 ==========
    "total_amount": {
        "display_name": "订单金额",
        "location_table": "orders",
        "description": "订单总金额",
        "query_patterns": ["金额", "销售额", "总价"]
    },
    "unit_price": {
        "display_name": "单价",
        "location_table": "order_items",
        "description": "产品单价"
    },

    # ========== 数量相关 ==========
    "quantity": {
        "display_name": "数量",
        "location_table": "order_items",
        "description": "购买数量",
        "query_patterns": ["数量", "个数"]
    },
}


# ============================================================================
# 表别名映射
# ============================================================================

TABLE_ALIASES: Dict[str, List[str]] = {
    "users": ["user", "customer", "customers", "u", "用户", "用户表", "客户", "客户表"],
    "addresses": ["address", "addr", "a", "地址", "地址表"],
    "orders": ["order", "o", "订单", "订单表", "销售订单"],
    "order_items": ["order_item", "oi", "订单明细", "订单详情", "OrderItems"],
    "products": ["product", "p", "产品", "产品表", "商品", "商品表"],
    "categories": ["category", "c", "分类", "分类表", "Categories"],
}


# ============================================================================
# 智能建议函数
# ============================================================================

def find_column_suggestion(
    column_name: str,
    available_tables: Dict[str, List[str]],
    current_table: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    查找列可能在哪个表中，并提供 JOIN 建议

    Args:
        column_name: 要查找的列名（如 'province'）
        available_tables: 可用的表及其列，格式: {"表名": ["列1", "列2", ...]}
        current_table: 当前查询的表名（如果有）

    Returns:
        包含建议的字典，或 None
        {
            "found": True/False,
            "suggestion": "建议文本",
            "column_in_table": "addresses",
            "join_required": True/False,
            "join_query": "LEFT JOIN addresses ON users.id = addresses.user_id"
        }
    """
    column_lower = column_name.lower()

    # 1. 首先检查 COLUMN_SEMANTICS 配置
    if column_lower in COLUMN_SEMANTICS:
        sem_info = COLUMN_SEMANTICS[column_lower]
        location_table = sem_info.get("location_table")

        # 验证该表是否在可用表中
        if location_table and location_table in available_tables:
            related_table = sem_info.get("related_table")
            join_key = sem_info.get("join_key")

            suggestion = {
                "found": True,
                "column_name": column_name,
                "column_in_table": location_table,
                "display_name": sem_info.get("display_name", column_name),
                "description": sem_info.get("description", ""),
                "join_required": current_table != location_table,
            }

            # 如果需要 JOIN，提供 JOIN 建议
            if current_table and current_table != location_table:
                # 尝试从 TABLE_RELATIONSHIPS 获取 JOIN 条件
                join_info = _get_join_info(current_table, location_table)
                if join_info:
                    suggestion["join_query"] = join_info
                    suggestion["suggestion"] = (
                        f"'{column_name}' 列在 '{location_table}' 表中。"
                        f"请使用 {join_info} 将两个表连接起来。"
                    )
                else:
                    # 根据 COLUMN_SEMANTICS 生成简单建议
                    if related_table and join_key:
                        if current_table.lower() in ["users", "user", "u"] and related_table.lower() == "users":
                            suggestion["join_query"] = f"LEFT JOIN {location_table} ON {current_table}.id = {location_table}.{join_key}"
                            suggestion["suggestion"] = (
                                f"'{column_name}' 列在 '{location_table}' 表中。"
                                f"请使用: LEFT JOIN {location_table} ON {current_table}.id = {location_table}.{join_key}"
                            )
                        else:
                            suggestion["join_query"] = f"LEFT JOIN {location_table} ON ..."
                            suggestion["suggestion"] = f"'{column_name}' 列在 '{location_table}' 表中，需要 JOIN 查询"
                    else:
                        suggestion["suggestion"] = f"'{column_name}' 列在 '{location_table}' 表中"
            else:
                suggestion["suggestion"] = f"'{column_name}' 列在 '{location_table}' 表中，直接使用即可"

            return suggestion

    # 2. 在所有可用表中查找该列
    found_tables = []
    for table_name, columns in available_tables.items():
        for col in columns:
            if col.lower() == column_lower:
                found_tables.append(table_name)
                break

    if found_tables:
        # 找到了该列
        if current_table and current_table in found_tables:
            # 列就在当前表中
            return {
                "found": True,
                "column_name": column_name,
                "column_in_table": current_table,
                "join_required": False,
                "suggestion": f"'{column_name}' 列在当前表 '{current_table}' 中，检查拼写是否正确"
            }
        else:
            # 列在其他表中
            target_table = found_tables[0]
            join_info = _get_join_info(current_table, target_table) if current_table else None

            suggestion = {
                "found": True,
                "column_name": column_name,
                "column_in_table": target_table,
                "join_required": current_table != target_table,
            }

            if join_info:
                suggestion["join_query"] = join_info
                suggestion["suggestion"] = (
                    f"'{column_name}' 列在 '{target_table}' 表中。"
                    f"请使用 {join_info}"
                )
            else:
                suggestion["suggestion"] = f"'{column_name}' 列在 '{target_table}' 表中"

            return suggestion

    # 3. 没找到该列，尝试模糊匹配
    fuzzy_matches = _fuzzy_match_column(column_lower, available_tables)
    if fuzzy_matches:
        matches_str = ", ".join(f"'{m}'" for m in fuzzy_matches[:3])
        return {
            "found": False,
            "column_name": column_name,
            "suggestion": f"列 '{column_name}' 不存在。您是否想查询: {matches_str}?",
            "similar_columns": fuzzy_matches
        }

    # 4. 完全没找到
    return {
        "found": False,
        "column_name": column_name,
        "suggestion": f"列 '{column_name}' 不存在。请调用 get_schema() 查看可用列"
    }


def _get_join_info(table1: str, table2: str) -> Optional[str]:
    """
    获取两个表之间的 JOIN 条件

    Args:
        table1: 第一个表名
        table2: 第二个表名

    Returns:
        JOIN 语句字符串，或 None
    """
    # 标准化表名
    t1_lower = table1.lower().replace("表", "").strip()
    t2_lower = table2.lower().replace("表", "").strip()

    # 从 TABLE_RELATIONSHIPS 查找
    for table_name, config in TABLE_RELATIONSHIPS.items():
        if "relationships" not in config:
            continue

        for rel in config["relationships"]:
            rel_table = rel["related_table"].lower()
            if (t1_lower == table_name.lower() and t2_lower == rel_table) or \
               (t2_lower == table_name.lower() and t1_lower == rel_table):
                return f"LEFT JOIN {rel['related_table']} ON {rel['join_condition']}"

    # 常见固定关系
    common_joins = {
        ("users", "addresses"): "LEFT JOIN addresses ON users.id = addresses.user_id",
        ("user", "addresses"): "LEFT JOIN addresses ON users.id = addresses.user_id",
        ("u", "addresses"): "LEFT JOIN addresses ON u.id = addresses.user_id",
        ("users", "orders"): "INNER JOIN orders ON users.id = orders.user_id",
        ("orders", "order_items"): "INNER JOIN order_items ON orders.id = order_items.order_id",
        ("order_items", "products"): "INNER JOIN products ON order_items.product_id = products.id",
        ("products", "categories"): "LEFT JOIN categories ON products.category_id = categories.id",
    }

    for (t1, t2), join_sql in common_joins.items():
        if (t1_lower in [table1.lower(), t1_lower] and t2_lower in [table2.lower(), t2_lower]) or \
           (t2_lower in [table1.lower(), t1_lower] and t1_lower in [table2.lower(), t2_lower]):
            return join_sql

    return None


def _fuzzy_match_column(column_name: str, available_tables: Dict[str, List[str]]) -> List[str]:
    """
    模糊匹配列名

    Args:
        column_name: 要查找的列名（小写）
        available_tables: 可用的表及其列

    Returns:
        匹配的列名列表
    """
    matches = []
    for table_name, columns in available_tables.items():
        for col in columns:
            col_lower = col.lower()
            # 包含匹配
            if column_name in col_lower or col_lower in column_name:
                matches.append(f"{table_name}.{col}")
            # 编辑距离匹配（简单版：首字母相同且长度相近）
            elif column_name[0] == col_lower[0] and abs(len(column_name) - len(col_lower)) <= 2:
                matches.append(f"{table_name}.{col}")

    return matches[:5]  # 最多返回5个匹配


def suggest_join_query(
    from_table: str,
    want_columns: List[str],
    available_tables: Dict[str, List[str]]
) -> Optional[Dict[str, Any]]:
    """
    根据想要的列，建议完整的 JOIN 查询

    Args:
        from_table: 主表名
        want_columns: 想要查询的列列表
        available_tables: 可用的表及其列

    Returns:
        建议的查询信息，或 None
        {
            "sql": "完整的 SQL 模板",
            "joins": ["JOIN 语句列表"],
            "columns": ["完整的列名列表"],
            "suggestion": "文字说明"
        }
    """
    if not want_columns:
        return None

    # 收集需要的表
    needed_tables = {from_table}
    join_clauses = []
    qualified_columns = []

    for col in want_columns:
        suggestion = find_column_suggestion(col, available_tables, from_table)

        if suggestion and suggestion.get("found"):
            target_table = suggestion["column_in_table"]

            if target_table not in needed_tables:
                needed_tables.add(target_table)

                # 获取 JOIN 条件
                join_sql = _get_join_info(from_table, target_table)
                if join_sql:
                    join_clauses.append(join_sql)
                else:
                    # 尝试通用 JOIN
                    join_clauses.append(f"LEFT JOIN {target_table} ON {from_table}.id = {target_table}.{from_table}_id")

            # 添加列名
            qualified_columns.append(f"{target_table}.{col}")
        else:
            # 列可能在当前表中
            qualified_columns.append(f"{from_table}.{col}")

    # 构建 SQL
    if join_clauses:
        columns_str = ",\n    ".join(qualified_columns)
        joins_str = "\n    ".join(join_clauses)

        sql_template = f"""SELECT
    {columns_str}
FROM {from_table}
    {joins_str}"""

        return {
            "sql": sql_template,
            "joins": join_clauses,
            "tables": list(needed_tables),
            "columns": qualified_columns,
            "suggestion": f"需要 JOIN {len(join_clauses)} 个表来获取所有列"
        }

    return None


def get_table_relationships(table_name: str) -> Dict[str, Any]:
    """
    获取指定表的关系信息

    Args:
        table_name: 表名

    Returns:
        表关系信息
    """
    # 尝试直接匹配
    if table_name in TABLE_RELATIONSHIPS:
        return TABLE_RELATIONSHIPS[table_name]

    # 尝试模糊匹配
    table_lower = table_name.lower().replace("表", "").strip()
    for name, config in TABLE_RELATIONSHIPS.items():
        if name.lower().replace("表", "").strip() == table_lower:
            return config

    return {}


def get_column_semantics(column_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定列的语义信息

    Args:
        column_name: 列名

    Returns:
        列语义信息
    """
    column_lower = column_name.lower()
    if column_lower in COLUMN_SEMANTICS:
        return COLUMN_SEMANTICS[column_lower]
    return None


def resolve_table_alias(alias: str) -> Optional[str]:
    """
    解析表别名到实际表名

    Args:
        alias: 表别名（如 'u', 'user', 'customers'）

    Returns:
        实际表名，或 None
    """
    alias_lower = alias.lower()

    for table_name, aliases in TABLE_ALIASES.items():
        if alias_lower in [a.lower() for a in aliases]:
            return table_name

    return None


# ============================================================================
# 错误消息生成
# ============================================================================

def generate_error_with_suggestion(
    error_message: str,
    column_name: str,
    available_tables: Dict[str, List[str]],
    current_table: Optional[str] = None
) -> str:
    """
    生成带有智能建议的错误消息

    Args:
        error_message: 原始错误消息
        column_name: 错误的列名
        available_tables: 可用的表及其列
        current_table: 当前查询的表

    Returns:
        增强后的错误消息
    """
    suggestion = find_column_suggestion(column_name, available_tables, current_table)

    if not suggestion:
        return error_message

    enhanced_error = f"❌ {error_message}\n\n💡 **建议**: {suggestion.get('suggestion', '')}"

    if suggestion.get("join_query"):
        enhanced_error += f"\n\n**推荐查询**:\n```sql\nSELECT *\nFROM {current_table or 'table'}\n{suggestion['join_query']}\n```"

    return enhanced_error


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    # 测试表关系配置
    print("=" * 60)
    print("表关系配置测试")
    print("=" * 60)

    # 测试数据
    test_tables = {
        "users": ["id", "username", "email", "phone", "registration_date"],
        "addresses": ["id", "user_id", "province", "city", "district", "detail_address"],
        "orders": ["id", "user_id", "order_date", "total_amount"],
        "products": ["id", "name", "price", "category_id"],
    }

    # 测试 1: 查找 province 列
    print("\n测试1: 查找 'province' 列")
    result = find_column_suggestion("province", test_tables, "users")
    print(f"  结果: {result}")

    # 测试 2: 查找不存在的列
    print("\n测试2: 查找 'invalid_column' 列")
    result = find_column_suggestion("invalid_column", test_tables, "users")
    print(f"  结果: {result}")

    # 测试 3: 建议 JOIN 查询
    print("\n测试3: 建议多列 JOIN 查询")
    result = suggest_join_query("users", ["province", "city"], test_tables)
    if result:
        print(f"  SQL:\n{result['sql']}")
    else:
        print("  无建议")

    # 测试 4: 解析表别名
    print("\n测试4: 解析表别名")
    for alias in ["u", "user", "customers", "addr", "order_items"]:
        resolved = resolve_table_alias(alias)
        print(f"  '{alias}' -> '{resolved}'")
