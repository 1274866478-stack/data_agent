# -*- coding: utf-8 -*-
"""测试数据库的简化语义层定义"""
from typing import Dict, List, Any

# 测试数据库表别名映射
TABLE_ALIASES = {
    "customers": "users",  # 语义层说customers，实际数据库是users
    "Clients": "users",
    "Users": "users",
}

# 列名映射
COLUMN_ALIASES = {
    "users": {
        "customer_id": "id",
        "client_id": "id",
        "customer_name": "username",
        "client_name": "username",
    },
    "orders": {
        "customer_id": "user_id",
        "client_id": "user_id",
    }
}

# 测试数据库的业务度量定义
TEST_MEASURES = {
    # 用户相关
    "用户数": {
        "cube": "Users",
        "name": "user_count",
        "display_name": "用户数量",
        "sql": "COUNT(*)",
        "description": "用户总数"
    },
    "VIP用户数": {
        "cube": "Users",
        "name": "vip_user_count",
        "display_name": "VIP用户数量",
        "sql": "COUNT(CASE WHEN vip_level > 0 THEN 1 END)",
        "description": "VIP等级用户数量"
    },
    "平均消费": {
        "cube": "Users",
        "name": "avg_spent",
        "display_name": "平均消费金额",
        "sql": "AVG(total_spent)",
        "description": "用户平均消费金额"
    },

    # 订单相关
    "订单数": {
        "cube": "Orders",
        "name": "order_count",
        "display_name": "订单数量",
        "sql": "COUNT(*)",
        "description": "订单总数"
    },
    "销售额": {
        "cube": "Orders",
        "name": "total_sales",
        "display_name": "销售额",
        "sql": "SUM(final_amount)",
        "description": "订单总销售额"
    },
    "平均客单价": {
        "cube": "Orders",
        "name": "avg_order_value",
        "display_name": "平均订单金额",
        "sql": "AVG(final_amount)",
        "description": "平均每单金额"
    },

    # 商品相关
    "商品数": {
        "cube": "Products",
        "name": "product_count",
        "display_name": "商品数量",
        "sql": "COUNT(*)",
        "description": "商品总数"
    },
    "平均评分": {
        "cube": "Products",
        "name": "avg_rating",
        "display_name": "商品平均评分",
        "sql": "AVG(rating)",
        "description": "商品平均评分"
    },
    "总销量": {
        "cube": "Products",
        "name": "total_sales",
        "display_name": "商品总销量",
        "sql": "SUM(sales_count)",
        "description": "商品累计销量"
    },
}

# 测试数据库的维度定义
TEST_DIMENSIONS = {
    # 用户维度
    "vip_level": {
        "cube": "Users",
        "name": "vip_level",
        "display_name": "VIP等级",
        "type": "integer",
        "sql": "vip_level"
    },
    "gender": {
        "cube": "Users",
        "name": "gender",
        "display_name": "性别",
        "type": "string",
        "sql": "gender"
    },

    # 订单维度
    "order_status": {
        "cube": "Orders",
        "name": "status",
        "display_name": "订单状态",
        "type": "string",
        "sql": "status"
    },
    "order_date": {
        "cube": "Orders",
        "name": "order_date",
        "display_name": "订单日期",
        "type": "date",
        "sql": "order_date"
    },

    # 商品维度
    "brand": {
        "cube": "Products",
        "name": "brand",
        "display_name": "品牌",
        "type": "string",
        "sql": "brand"
    },
    "category": {
        "cube": "Products",
        "name": "category_id",
        "display_name": "商品类别",
        "type": "integer",
        "sql": "category_id"
    },
    "price": {
        "cube": "Products",
        "name": "price",
        "display_name": "商品价格",
        "type": "number",
        "sql": "price"
    },

    # 评价维度
    "rating": {
        "cube": "Reviews",
        "name": "rating",
        "display_name": "评分",
        "type": "integer",
        "sql": "rating"
    },
}

def translate_sql_for_test_db(sql: str) -> str:
    """将语义层SQL转换为测试数据库SQL

    Args:
        sql: 原始SQL

    Returns:
        转换后的SQL
    """
    # 表名转换
    for old_table, new_table in TABLE_ALIASES.items():
        import re
        # 匹配单词边界，避免部分匹配
        sql = re.sub(r'\b' + old_table + r'\b', new_table, sql, flags=re.IGNORECASE)

    return sql
