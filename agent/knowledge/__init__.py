# -*- coding: utf-8 -*-
"""
知识系统模块 - 双知识系统核心功能

这个模块提供基于 Dash 的自学习数据代理核心功能：
    1. 双知识系统：静态知识库（人工维护） + 动态学习库（自动发现）
    2. 自动学习循环：从成功查询提炼模式，从失败查询学习修复
    3. 知识检索增强：每次查询前自动检索相关知识

核心组件:
    - VectorStore: ChromaDB 向量存储封装
    - KnowledgeBaseService: 双知识系统核心服务
    - LearningEngine: 自动学习循环引擎
    - KnowledgeTools: LangChain 知识检索工具

作者: Data Agent Team
版本: 1.0.0
"""

from .vector_store import ChromaVectorStore, create_vector_store
from .knowledge_base import (
    KnowledgeBaseService,
    KnowledgeEntry,
    LearningEntry,
    create_knowledge_base
)
from .knowledge_tools import (
    search_knowledge,
    search_learnings,
    save_validated_query,
    save_learning
)

__all__ = [
    # 向量存储
    "ChromaVectorStore",
    "create_vector_store",

    # 知识库服务
    "KnowledgeBaseService",
    "KnowledgeEntry",
    "LearningEntry",
    "create_knowledge_base",

    # 知识检索工具
    "search_knowledge",
    "search_learnings",
    "save_validated_query",
    "save_learning",
]

__version__ = "1.0.0"
