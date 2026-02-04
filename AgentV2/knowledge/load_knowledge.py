# -*- coding: utf-8 -*-
"""
知识加载脚本 - 静态知识库初始化

支持从 YAML 文件加载静态知识到向量数据库：
    - 查询模板（query_templates.yaml）
    - 业务规则（business_rules.yaml）
    - Schema 信息（schema_info.yaml）
    - 表名映射（table_mappings.yaml）

使用方式:
    python -m AgentV2.knowledge.load_knowledge --tenant-id <tenant_id> --action load

作者: Data Agent Team
版本: 1.0.0
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .knowledge_base import (
    KnowledgeBaseService,
    KnowledgeType,
    create_knowledge_base
)

logger = logging.getLogger(__name__)


# ============================================================================
# 知识目录结构
# ============================================================================

KNOWLEDGE_DIR = Path(__file__).parent / "static"

# 默认知识文件
DEFAULT_KNOWLEDGE_FILES = {
    "query_templates": KNOWLEDGE_DIR / "query_templates.yaml",
    "business_rules": KNOWLEDGE_DIR / "business_rules.yaml",
    "schema_info": KNOWLEDGE_DIR / "schema_info.yaml",
    "table_mappings": KNOWLEDGE_DIR / "table_mappings.yaml",
}


# ============================================================================
# 知识加载器
# ============================================================================

class KnowledgeLoader:
    """知识加载器

    从 YAML 文件加载知识并保存到向量数据库。
    """

    def __init__(
        self,
        tenant_id: str,
        persist_directory: Optional[Path] = None
    ):
        """初始化知识加载器

        Args:
            tenant_id: 租户 ID
            persist_directory: 持久化目录
        """
        self.tenant_id = tenant_id
        self.persist_directory = persist_directory
        self.knowledge_base = create_knowledge_base(
            tenant_id=tenant_id,
            persist_directory=persist_directory
        )

    async def load_from_file(
        self,
        file_path: Path,
        knowledge_type: KnowledgeType
    ) -> int:
        """从 YAML 文件加载知识

        Args:
            file_path: YAML 文件路径
            knowledge_type: 知识类型

        Returns:
            加载的知识条目数量
        """
        if not file_path.exists():
            logger.warning(f"知识文件不存在: {file_path}")
            return 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"知识文件为空: {file_path}")
                return 0

            count = 0
            entries = data.get("entries", []) if isinstance(data, dict) else data

            for entry in entries:
                try:
                    await self._save_entry(entry, knowledge_type)
                    count += 1
                except Exception as e:
                    logger.error(f"保存知识条目失败: {e}")

            logger.info(f"从 {file_path.name} 加载了 {count} 条知识")
            return count

        except Exception as e:
            logger.error(f"加载知识文件失败: {file_path}, {e}")
            return 0

    async def load_all(self) -> Dict[str, int]:
        """加载所有知识文件

        Returns:
            各类型知识加载数量的字典
        """
        results = {}

        # 加载查询模板
        results["query_templates"] = await self.load_from_file(
            DEFAULT_KNOWLEDGE_FILES["query_templates"],
            KnowledgeType.QUERY_TEMPLATE
        )

        # 加载业务规则
        results["business_rules"] = await self.load_from_file(
            DEFAULT_KNOWLEDGE_FILES["business_rules"],
            KnowledgeType.BUSINESS_RULE
        )

        # 加载 Schema 信息
        results["schema_info"] = await self.load_from_file(
            DEFAULT_KNOWLEDGE_FILES["schema_info"],
            KnowledgeType.SCHEMA_INFO
        )

        # 加载表名映射
        results["table_mappings"] = await self.load_from_file(
            DEFAULT_KNOWLEDGE_FILES["table_mappings"],
            KnowledgeType.TABLE_MAPPING
        )

        return results

    async def _save_entry(
        self,
        entry: Dict[str, Any],
        knowledge_type: KnowledgeType
    ):
        """保存知识条目

        Args:
            entry: 知识条目数据
            knowledge_type: 知识类型
        """
        question = entry.get("question", "")
        sql = entry.get("sql", "")
        tables = entry.get("tables", [])
        answer = entry.get("answer", "")
        metadata = entry.get("metadata", {})

        await self.knowledge_base.save_validated_query(
            question=question,
            sql=sql,
            tables=tables,
            answer=answer,
            metadata={**metadata, "knowledge_type": knowledge_type.value}
        )

    async def clear_all(self) -> bool:
        """清空所有知识

        Returns:
            是否成功
        """
        try:
            # 清空静态知识库
            if self.knowledge_base._static_store:
                self.knowledge_base._static_store.clear()
            # 清空学习库
            if self.knowledge_base._learning_store:
                self.knowledge_base._learning_store.clear()
            logger.info(f"[KnowledgeLoader] 已清空租户 {self.tenant_id} 的所有知识")
            return True
        except Exception as e:
            logger.error(f"清空知识失败: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息

        Returns:
            统计信息字典
        """
        return self.knowledge_base.get_stats()


# ============================================================================
# 默认知识文件生成
# ============================================================================

def ensure_knowledge_files():
    """确保默认知识文件存在"""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    # 创建查询模板示例
    if not DEFAULT_KNOWLEDGE_FILES["query_templates"].exists():
        default_query_templates = {
            "description": "SQL 查询模板示例",
            "entries": [
                {
                    "question": "2023年的销售趋势",
                    "sql": "SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as total FROM orders WHERE EXTRACT(YEAR FROM order_date) = 2023 GROUP BY month ORDER BY month",
                    "tables": ["orders"],
                    "answer": "按月统计2023年销售趋势，使用 GROUP BY month 聚合数据"
                },
                {
                    "question": "各城市销售额对比",
                    "sql": "SELECT city, SUM(amount) as total FROM orders GROUP BY city ORDER BY total DESC",
                    "tables": ["orders"],
                    "answer": "按城市统计销售额，使用 SUM 聚合函数"
                },
                {
                    "question": "产品库存不足预警",
                    "sql": "SELECT product_name, quantity FROM products WHERE quantity <= reorder_point ORDER BY quantity ASC",
                    "tables": ["products"],
                    "answer": "查找库存低于或等于补货点的产品"
                }
            ]
        }
        with open(DEFAULT_KNOWLEDGE_FILES["query_templates"], 'w', encoding='utf-8') as f:
            yaml.dump(default_query_templates, f, allow_unicode=True, default_flow_style=False)

    # 创建业务规则示例
    if not DEFAULT_KNOWLEDGE_FILES["business_rules"].exists():
        default_business_rules = {
            "description": "业务规则示例",
            "entries": [
                {
                    "question": "GMV（商品交易总额）计算",
                    "sql": "SELECT SUM(total_amount) as gmv FROM orders",
                    "tables": ["orders"],
                    "answer": "GMV 是所有订单的总金额，使用 SUM(total_amount) 计算"
                },
                {
                    "question": "ARPU（每用户平均收入）计算",
                    "sql": "SELECT SUM(total_amount) / COUNT(DISTINCT user_id) as arpu FROM orders",
                    "tables": ["orders"],
                    "answer": "ARPU 是总收入除以去重用户数"
                },
                {
                    "question": "复购率计算",
                    "sql": "SELECT COUNT(DISTINCT CASE WHEN order_count > 1 THEN user_id END) * 1.0 / COUNT(DISTINCT user_id) as repeat_rate FROM (SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id) t",
                    "tables": ["orders"],
                    "answer": "复购率是下单超过一次的用户数除以总用户数"
                }
            ]
        }
        with open(DEFAULT_KNOWLEDGE_FILES["business_rules"], 'w', encoding='utf-8') as f:
            yaml.dump(default_business_rules, f, allow_unicode=True, default_flow_style=False)

    # 创建 Schema 信息示例
    if not DEFAULT_KNOWLEDGE_FILES["schema_info"].exists():
        default_schema_info = {
            "description": "Schema 结构信息示例",
            "entries": [
                {
                    "question": "订单表结构",
                    "sql": "DESCRIBE orders",
                    "tables": ["orders"],
                    "answer": "订单表包含：id（主键）、user_id（用户ID）、order_date（订单日期）、total_amount（订单金额）、status（订单状态）"
                },
                {
                    "question": "用户表结构",
                    "sql": "DESCRIBE users",
                    "tables": ["users"],
                    "answer": "用户表包含：id（主键）、email（邮箱）、display_name（显示名称）、created_at（创建时间）"
                },
                {
                    "question": "产品表结构",
                    "sql": "DESCRIBE products",
                    "tables": ["products"],
                    "answer": "产品表包含：id（主键）、product_name（产品名称）、price（价格）、quantity（库存）、reorder_point（补货点）"
                }
            ]
        }
        with open(DEFAULT_KNOWLEDGE_FILES["schema_info"], 'w', encoding='utf-8') as f:
            yaml.dump(default_schema_info, f, allow_unicode=True, default_flow_style=False)

    # 创建表名映射示例
    if not DEFAULT_KNOWLEDGE_FILES["table_mappings"].exists():
        default_table_mappings = {
            "description": "表名映射示例",
            "entries": [
                {
                    "question": "订单数据查询",
                    "sql": "SELECT * FROM orders",
                    "tables": ["orders"],
                    "answer": "订单表名为 orders，包含所有订单相关信息"
                },
                {
                    "question": "用户数据查询",
                    "sql": "SELECT * FROM users",
                    "tables": ["users"],
                    "answer": "用户表名为 users，包含用户基本信息"
                },
                {
                    "question": "产品数据查询",
                    "sql": "SELECT * FROM products",
                    "tables": ["products"],
                    "answer": "产品表名为 products，包含产品库存信息"
                },
                {
                    "question": "订单明细查询",
                    "sql": "SELECT * FROM order_items",
                    "tables": ["order_items"],
                    "answer": "订单明细表名为 order_items，包含订单-产品关联信息"
                }
            ]
        }
        with open(DEFAULT_KNOWLEDGE_FILES["table_mappings"], 'w', encoding='utf-8') as f:
            yaml.dump(default_table_mappings, f, allow_unicode=True, default_flow_style=False)

    logger.info(f"默认知识文件已创建在: {KNOWLEDGE_DIR}")


# ============================================================================
# CLI 接口
# ============================================================================

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="知识库加载工具")
    parser.add_argument("--tenant-id", required=True, help="租户 ID")
    parser.add_argument("--action", choices=["load", "clear", "stats", "init"], default="load", help="操作类型")
    parser.add_argument("--persist-dir", help="持久化目录路径")

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if args.action == "init":
        print("[KnowledgeLoader] 初始化默认知识文件...")
        ensure_knowledge_files()
        print(f"[KnowledgeLoader] 知识文件已创建在: {KNOWLEDGE_DIR}")
        return

    loader = KnowledgeLoader(
        tenant_id=args.tenant_id,
        persist_directory=Path(args.persist_dir) if args.persist_dir else None
    )

    if args.action == "load":
        print(f"[KnowledgeLoader] 开始加载知识，租户: {args.tenant_id}")

        # 确保知识文件存在
        ensure_knowledge_files()

        results = await loader.load_all()

        print("\n[KnowledgeLoader] 加载完成:")
        for key, count in results.items():
            print(f"  {key}: {count} 条")

        stats = loader.get_stats()
        print(f"\n[KnowledgeLoader] 知识库统计:")
        print(f"  静态知识: {stats['static_knowledge_count']} 条")
        print(f"  学习记录: {stats['learning_count']} 条")

    elif args.action == "clear":
        print(f"[KnowledgeLoader] 清空知识，租户: {args.tenant_id}")
        success = await loader.clear_all()
        if success:
            print("[KnowledgeLoader] 清空完成")
        else:
            print("[KnowledgeLoader] 清空失败")

    elif args.action == "stats":
        stats = loader.get_stats()
        print(f"[KnowledgeLoader] 知识库统计 (租户: {args.tenant_id}):")
        print(f"  静态知识: {stats['static_knowledge_count']} 条")
        print(f"  学习记录: {stats['learning_count']} 条")


if __name__ == "__main__":
    asyncio.run(main())
