# -*- coding: utf-8 -*-
"""
AgentV2 Config Module - 配置模块
==================================
"""

from .table_descriptions import (
    TABLE_DESCRIPTIONS,
    get_recommended_tables,
    get_table_description,
    find_table_by_alias,
    get_all_high_priority_tables,
    enrich_tables_with_description,
    get_tables_by_term,
    TERM_TO_TABLE_MAPPING
)

__all__ = [
    "TABLE_DESCRIPTIONS",
    "get_recommended_tables",
    "get_table_description",
    "find_table_by_alias",
    "get_all_high_priority_tables",
    "enrich_tables_with_description",
    "get_tables_by_term",
    "TERM_TO_TABLE_MAPPING"
]
