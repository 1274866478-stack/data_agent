# -*- coding: utf-8 -*-
"""
知识注入中间件 - Knowledge Injection Middleware

在 Agent 执行前自动检索相关知识并注入到上下文中。

核心功能:
    1. 从用户查询中提取关键词
    2. 检索相关的静态知识（查询模板、业务规则）
    3. 检索相关的学习记录（错误修复方案）
    4. 将知识注入到系统提示词中

使用场景:
    - 用户提问前自动检索相关知识
    - 为 Agent 提供历史查询参考
    - 避免重复错误

作者: Data Agent Team
版本: 1.0.0
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..knowledge.knowledge_base import (
    KnowledgeBaseService,
    create_knowledge_base
)

logger = logging.getLogger(__name__)


class KnowledgeInjectionMiddleware:
    """
    知识注入中间件

    在 Agent 执行前检索相关知识并注入到系统提示词中。

    工作流程:
        1. 接收用户查询
        2. 使用知识库检索相关知识和学习记录
        3. 将检索结果注入到系统提示词
        4. Agent 基于增强的提示词执行查询
    """

    def __init__(
        self,
        tenant_id: str,
        enable_static_knowledge: bool = True,
        enable_dynamic_learning: bool = True,
        knowledge_top_k: int = 3,
        learning_top_k: int = 2,
        knowledge_threshold: float = 0.6,
        learning_threshold: float = 0.5,
        persist_directory: Optional[Path] = None,
        enable_logging: bool = True
    ):
        """初始化知识注入中间件

        Args:
            tenant_id: 租户 ID
            enable_static_knowledge: 是否启用静态知识检索
            enable_dynamic_learning: 是否启用动态学习检索
            knowledge_top_k: 静态知识返回数量
            learning_top_k: 学习记录返回数量
            knowledge_threshold: 静态知识相似度阈值
            learning_threshold: 学习记录相似度阈值
            persist_directory: 持久化目录
            enable_logging: 是否启用日志
        """
        self.tenant_id = tenant_id
        self.enable_static_knowledge = enable_static_knowledge
        self.enable_dynamic_learning = enable_dynamic_learning
        self.knowledge_top_k = knowledge_top_k
        self.learning_top_k = learning_top_k
        self.knowledge_threshold = knowledge_threshold
        self.learning_threshold = learning_threshold
        self.enable_logging = enable_logging
        self.persist_directory = persist_directory

        # 获取知识库服务
        self.knowledge_base: KnowledgeBaseService = create_knowledge_base(
            tenant_id=tenant_id,
            persist_directory=persist_directory
        )

    async def before_execution(
        self,
        query: str,
        system_prompt: Optional[str] = None
    ) -> tuple[str, Dict[str, Any]]:
        """在 Agent 执行前处理

        检索相关知识并注入到系统提示词中。

        Args:
            query: 用户查询
            system_prompt: 原始系统提示词

        Returns:
            (增强后的系统提示词, 检索到的知识数据)
        """
        if not query:
            return system_prompt or "", {}

        knowledge_data = {
            "static_knowledge": [],
            "learnings": []
        }

        # 1. 检索静态知识
        if self.enable_static_knowledge:
            try:
                knowledge_entries = await self.knowledge_base.search_knowledge(
                    query=query,
                    n_results=self.knowledge_top_k,
                    min_score=self.knowledge_threshold
                )
                knowledge_data["static_knowledge"] = [e.to_dict() for e in knowledge_entries]

                if self.enable_logging and knowledge_entries:
                    logger.info(f"[KnowledgeInjection] 检索到 {len(knowledge_entries)} 条静态知识")
            except Exception as e:
                logger.error(f"[KnowledgeInjection] 静态知识检索失败: {e}")

        # 2. 检索学习记录
        if self.enable_dynamic_learning:
            try:
                learning_entries = await self.knowledge_base.search_learnings(
                    query=query,
                    n_results=self.learning_top_k,
                    min_score=self.learning_threshold
                )
                knowledge_data["learnings"] = [e.to_dict() for e in learning_entries]

                if self.enable_logging and learning_entries:
                    logger.info(f"[KnowledgeInjection] 检索到 {len(learning_entries)} 条学习记录")
            except Exception as e:
                logger.error(f"[KnowledgeInjection] 学习记录检索失败: {e}")

        # 3. 注入到系统提示词
        enhanced_prompt = self._inject_knowledge_to_prompt(
            base_prompt=system_prompt or "",
            knowledge_data=knowledge_data
        )

        return enhanced_prompt, knowledge_data

    def _inject_knowledge_to_prompt(
        self,
        base_prompt: str,
        knowledge_data: Dict[str, List]
    ) -> str:
        """将知识注入到系统提示词

        Args:
            base_prompt: 基础系统提示词
            knowledge_data: 检索到的知识数据

        Returns:
            增强后的系统提示词
        """
        if not knowledge_data.get("static_knowledge") and not knowledge_data.get("learnings"):
            return base_prompt

        injection_parts = []

        # 注入静态知识
        static_knowledge = knowledge_data.get("static_knowledge", [])
        if static_knowledge:
            injection_parts.append("## 📚 相关查询模板")
            injection_parts.append(f"找到 {len(static_knowledge)} 条相关查询模板：")
            for i, entry in enumerate(static_knowledge[:3], 1):  # 最多显示3条
                injection_parts.append(f"\n{i}. **问题**: {entry['question']}")
                if entry.get('sql'):
                    injection_parts.append(f"   **SQL**: ```sql\n{entry['sql']}\n```")
                if entry.get('answer'):
                    injection_parts.append(f"   **说明**: {entry['answer']}")

        # 注入学习记录（错误修复方案）
        learnings = knowledge_data.get("learnings", [])
        if learnings:
            injection_parts.append("\n## 🛠️ 相关错误修复方案")
            injection_parts.append(f"找到 {len(learnings)} 条相关错误修复方案：")
            for i, entry in enumerate(learnings[:2], 1):  # 最多显示2条
                injection_parts.append(f"\n{i}. **错误类型**: {entry['error_category']}")
                injection_parts.append(f"   **修复建议**: {entry['fix_suggestion']}")
                if entry.get('corrected_sql'):
                    injection_parts.append(f"   **修正SQL**: ```sql\n{entry['corrected_sql']}\n```")

        # 组合提示词
        if injection_parts:
            knowledge_section = "\n".join(injection_parts)
            return f"""{base_prompt}

{knowledge_section}

---
💡 提示：以上是相关的历史查询模板和错误修复方案，供你参考。
"""

        return base_prompt

    async def after_execution(
        self,
        query: str,
        result: Any,
        knowledge_data: Dict[str, List]
    ):
        """在 Agent 执行后处理

        更新知识使用统计。

        Args:
            query: 用户查询
            result: 执行结果
            knowledge_data: 之前检索的知识数据
        """
        # 更新静态知识的使用计数
        for entry in knowledge_data.get("static_knowledge", []):
            try:
                entry_id = entry.get("id")
                if entry_id:
                    await self.knowledge_base.increment_usage_count(entry_id)
            except Exception as e:
                logger.error(f"[KnowledgeInjection] 更新使用计数失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息

        Returns:
            统计信息字典
        """
        return self.knowledge_base.get_stats()


# ============================================================================
# 工厂函数
# ============================================================================

def create_knowledge_middleware(
    tenant_id: str,
    enable_static_knowledge: bool = True,
    enable_dynamic_learning: bool = True,
    knowledge_top_k: int = 3,
    learning_top_k: int = 2,
    knowledge_threshold: float = 0.6,
    learning_threshold: float = 0.5,
    persist_directory: Optional[Path] = None,
    enable_logging: bool = True
) -> KnowledgeInjectionMiddleware:
    """创建知识注入中间件

    Args:
        tenant_id: 租户 ID
        enable_static_knowledge: 是否启用静态知识检索
        enable_dynamic_learning: 是否启用动态学习检索
        knowledge_top_k: 静态知识返回数量
        learning_top_k: 学习记录返回数量
        knowledge_threshold: 静态知识相似度阈值
        learning_threshold: 学习记录相似度阈值
        persist_directory: 持久化目录
        enable_logging: 是否启用日志

    Returns:
        KnowledgeInjectionMiddleware 实例
    """
    return KnowledgeInjectionMiddleware(
        tenant_id=tenant_id,
        enable_static_knowledge=enable_static_knowledge,
        enable_dynamic_learning=enable_dynamic_learning,
        knowledge_top_k=knowledge_top_k,
        learning_top_k=learning_top_k,
        knowledge_threshold=knowledge_threshold,
        learning_threshold=learning_threshold,
        persist_directory=persist_directory,
        enable_logging=enable_logging
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test_knowledge_middleware():
        print("=" * 60)
        print("知识注入中间件测试")
        print("=" * 60)

        middleware = create_knowledge_middleware(tenant_id="test_tenant")

        # 模拟用户查询
        query = "2023年的销售趋势"

        # 执行前处理
        print("\n[测试] 知识检索")
        enhanced_prompt, knowledge_data = await middleware.before_execution(
            query=query,
            system_prompt="你是一个数据分析助手。"
        )

        print(f"  查询: {query}")
        print(f"  检索到静态知识: {len(knowledge_data['static_knowledge'])} 条")
        print(f"  检索到学习记录: {len(knowledge_data['learnings'])} 条")

        # 显示增强的提示词
        print("\n[测试] 增强提示词")
        print("=" * 60)
        print(enhanced_prompt)
        print("=" * 60)

        print("\n[测试] 完成")

    asyncio.run(test_knowledge_middleware())
