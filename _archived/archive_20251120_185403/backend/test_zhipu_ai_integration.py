#!/usr/bin/env python3
"""
智谱AI集成测试脚本
测试SQL生成器的智谱AI增强功能
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_zhipu_ai_integration():
    """测试智谱AI集成功能"""

    try:
        # 导入必要模块
        from services.sql_generator import SQLGenerator
        from models.rag_sql import (
            QueryIntent, DatabaseSchema, TableInfo, ColumnInfo, QueryType
        )
        from app.services.zhipu_client import zhipu_service

        logger.info("=== 开始智谱AI集成测试 ===")

        # 测试智谱AI服务连接
        logger.info("1. 测试智谱AI服务连接...")
        connection_status = await zhipu_service.check_connection()
        logger.info(f"智谱AI连接状态: {'✅ 成功' if connection_status else '❌ 失败'}")

        if not connection_status:
            logger.error("智谱AI服务连接失败，请检查API密钥配置")
            return False

        # 创建SQL生成器实例（启用AI模式）
        logger.info("2. 初始化SQL生成器...")
        sql_generator = SQLGenerator(use_ai=True)

        # 检查AI状态
        ai_status = sql_generator.get_ai_status()
        logger.info(f"AI服务状态: {ai_status}")

        # 创建测试数据库schema
        logger.info("3. 创建测试数据库schema...")
        test_schema = DatabaseSchema(
            tables={
                "products": TableInfo(
                    name="products",
                    description="产品表",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True, is_nullable=False),
                        ColumnInfo(name="name", data_type="varchar(255)", is_nullable=False),
                        ColumnInfo(name="category", data_type="varchar(100)", is_nullable=True),
                        ColumnInfo(name="price", data_type="decimal(10,2)", is_nullable=False),
                        ColumnInfo(name="created_at", data_type="timestamp", is_nullable=False),
                    ],
                    relationships=[],
                    sample_data=[
                        "1, iPhone 14, Electronics, 999.99, 2024-01-15",
                        "2, MacBook Pro, Electronics, 2499.99, 2024-01-20",
                        "3, Office Chair, Furniture, 299.99, 2024-02-01"
                    ]
                )
            }
        )

        # 测试查询意图
        test_queries = [
            {
                "natural": "显示所有电子产品",
                "intent": QueryIntent(
                    query_type=QueryType.SELECT,
                    target_tables=["products"],
                    target_columns=["*"],
                    conditions=["category = 'Electronics'"],
                    orderings=[],
                    aggregations=[],
                    groupings=[],
                    confidence_score=0.9
                )
            },
            {
                "natural": "找出最便宜的产品",
                "intent": QueryIntent(
                    query_type=QueryType.SELECT,
                    target_tables=["products"],
                    target_columns=["name", "price"],
                    conditions=[],
                    orderings=["price ASC"],
                    aggregations=[],
                    groupings=[],
                    confidence_score=0.8
                )
            }
        ]

        # 测试SQL生成
        logger.info("4. 测试SQL生成...")
        for i, test_case in enumerate(test_queries, 1):
            logger.info(f"\n测试查询 {i}: {test_case['natural']}")

            try:
                # 使用AI增强模式生成SQL
                sql_query = await sql_generator.generate_sql(
                    intent=test_case['intent'],
                    schema=test_schema,
                    natural_query=test_case['natural']
                )

                logger.info(f"✅ 生成的SQL: {sql_query.query}")
                logger.info(f"执行计划: {sql_query.execution_plan}")

            except Exception as e:
                logger.error(f"❌ SQL生成失败: {e}")
                return False

        logger.info("\n=== 智谱AI集成测试完成 ✅ ===")
        return True

    except ImportError as e:
        logger.error(f"模块导入失败: {e}")
        logger.error("请确保所有依赖模块都已正确安装")
        return False

    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return False

async def test_environment_check():
    """检查环境配置"""
    logger.info("=== 检查环境配置 ===")

    # 检查环境变量
    required_env_vars = [
        'ZHIPUAI_API_KEY',
    ]

    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            # 掩盖敏感信息
            masked_value = value[:8] + "..." if len(value) > 8 else "***"
            logger.info(f"{var}: ✅ 已配置 ({masked_value})")
        else:
            logger.warning(f"{var}: ⚠️  未配置")

    # 检查智谱AI库
    try:
        import zhipuai
        logger.info("智谱AI库: ✅ 已安装")
    except ImportError:
        logger.error("智谱AI库: ❌ 未安装")
        return False

    return True

async def main():
    """主函数"""
    logger.info("Data Agent V4 - 智谱AI集成测试")
    logger.info("=" * 50)

    # 环境检查
    if not await test_environment_check():
        logger.error("环境检查失败，退出测试")
        return

    # 智谱AI集成测试
    success = await test_zhipu_ai_integration()

    if success:
        logger.info("\n🎉 所有测试通过！智谱AI集成已成功配置")
        logger.info("\n使用方法:")
        logger.info("1. 设置环境变量 ZHIPUAI_API_KEY")
        logger.info("2. 在RAG-SQL服务中使用SQLGenerator(use_ai=True)")
        logger.info("3. 系统将自动尝试使用智谱AI生成SQL，失败时回退到模板模式")
    else:
        logger.error("\n❌ 测试失败，请检查配置和依赖")

if __name__ == "__main__":
    asyncio.run(main())