#!/usr/bin/env python3
"""
Redis缓存集成测试脚本
测试Redis分布式缓存功能
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_cache_service(cache_type: str = "memory"):
    """测试缓存服务"""
    try:
        from services.cache_service import CacheFactory, TenantCacheKeyGenerator

        logger.info(f"=== 测试 {cache_type} 缓存 ===")

        # 创建缓存实例
        cache = CacheFactory.create_cache(cache_type)
        logger.info(f"✅ {cache_type} 缓存创建成功")

        # 测试基本操作
        test_data = {
            "query": "SELECT * FROM products WHERE price > 100",
            "result": [{"id": 1, "name": "iPhone", "price": 999}],
            "timestamp": datetime.utcnow().isoformat()
        }

        # 设置缓存
        test_key = f"test:query_{cache_type}"
        await cache.set(test_key, test_data, ttl=60)
        logger.info(f"✅ 缓存设置成功: {test_key}")

        # 获取缓存
        retrieved_data = await cache.get(test_key)
        if retrieved_data:
            logger.info(f"✅ 缓存获取成功: {type(retrieved_data)}")
        else:
            logger.error("❌ 缓存获取失败")
            return False

        # 检查存在性
        exists = await cache.exists(test_key)
        logger.info(f"✅ 缓存存在性检查: {exists}")

        # 租户缓存测试
        tenant_id = "test_tenant"
        connection_id = 1
        query = "SELECT COUNT(*) FROM users"

        # 生成租户缓存键
        query_key = TenantCacheKeyGenerator.query_result(tenant_id, connection_id, query)
        await cache.set(query_key, {"count": 100}, ttl=300)
        logger.info(f"✅ 租户缓存设置成功: {query_key}")

        # 获取租户缓存
        tenant_result = await cache.get(query_key)
        if tenant_result:
            logger.info(f"✅ 租户缓存获取成功: {tenant_result}")

        # 测试缓存大小
        cache_size = await cache.get_size()
        logger.info(f"✅ 缓存大小: {cache_size}")

        # 清理测试数据
        await cache.clear_tenant_cache(tenant_id)
        await cache.delete(test_key)
        logger.info("✅ 测试数据清理完成")

        # Redis特有测试
        if cache_type == "redis" and hasattr(cache, 'health_check'):
            health = await cache.health_check()
            logger.info(f"✅ Redis健康检查: {health}")

            info = await cache.get_info()
            logger.info(f"✅ Redis信息: {info}")

        return True

    except Exception as e:
        logger.error(f"{cache_type} 缓存测试失败: {e}")
        return False

async def test_cache_factory():
    """测试缓存工厂"""
    logger.info("=== 测试缓存工厂 ===")

    try:
        from services.cache_service import CacheFactory

        # 测试内存缓存
        memory_cache = CacheFactory.create_cache("memory")
        logger.info("✅ 内存缓存创建成功")

        # 测试Redis缓存（如果可用）
        try:
            redis_cache = CacheFactory.create_cache("redis")
            logger.info("✅ Redis缓存创建成功")

            # 简单测试
            await redis_cache.set("test", {"value": "redis_test"})
            result = await redis_cache.get("test")
            if result and result.get("value") == "redis_test":
                logger.info("✅ Redis缓存基本功能正常")
            else:
                logger.warning("⚠️ Redis缓存基本功能异常")

        except Exception as e:
            logger.warning(f"⚠️ Redis缓存不可用: {e}")

        # 测试单例模式
        cache1 = CacheFactory.create_cache("memory")
        cache2 = CacheFactory.create_cache("memory")
        if cache1 is cache2:
            logger.info("✅ 缓存工厂单例模式正常")
        else:
            logger.error("❌ 缓存工厂单例模式异常")

        return True

    except Exception as e:
        logger.error(f"缓存工厂测试失败: {e}")
        return False

async def test_performance_comparison():
    """测试缓存性能对比"""
    logger.info("=== 缓存性能测试 ===")

    try:
        from services.cache_service import CacheFactory
        import time

        # 测试数据
        test_data = {
            "large_data": "x" * 1000,  # 1KB数据
            "nested": {
                "level1": {
                    "level2": {"level3": "deep_value"}}
                },
                "array": list(range(100))
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        cache_types = ["memory"]

        # 如果Redis可用，也测试Redis
        try:
            redis_cache = CacheFactory.create_cache("redis")
            await redis_cache.set("perf_test", test_data)
            await redis_cache.get("perf_test")
            await redis_cache.delete("perf_test")
            cache_types.append("redis")
        except:
            pass

        results = {}

        for cache_type in cache_types:
            cache = CacheFactory.create_cache(cache_type)
            logger.info(f"测试 {cache_type} 缓存性能...")

            # 写入性能测试
            write_times = []
            for i in range(100):
                start_time = time.time()
                await cache.set(f"perf_test_{i}", test_data, ttl=60)
                write_times.append(time.time() - start_time)

            # 读取性能测试
            read_times = []
            for i in range(100):
                start_time = time.time()
                await cache.get(f"perf_test_{i}")
                read_times.append(time.time() - start_time)

            # 计算统计信息
            avg_write = sum(write_times) / len(write_times)
            avg_read = sum(read_times) / len(read_times)
            max_write = max(write_times)
            max_read = max(read_times)

            results[cache_type] = {
                "avg_write_ms": round(avg_write * 1000, 3),
                "avg_read_ms": round(avg_read * 1000, 3),
                "max_write_ms": round(max_write * 1000, 3),
                "max_read_ms": round(max_read * 1000, 3)
            }

            # 清理测试数据
            for i in range(100):
                await cache.delete(f"perf_test_{i}")

        # 输出性能对比结果
        logger.info("📊 性能测试结果:")
        for cache_type, metrics in results.items():
            logger.info(f"{cache_type.upper()} 缓存:")
            logger.info(f"  平均写入: {metrics['avg_write_ms']}ms")
            logger.info(f"  平均读取: {metrics['avg_read_ms']}ms")
            logger.info(f"  最大写入: {metrics['max_write_ms']}ms")
            logger.info(f"  最大读取: {metrics['max_read_ms']}ms")

        return True

    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        return False

async def test_cache_integration():
    """测试缓存集成到RAG-SQL服务"""
    logger.info("=== 测试缓存集成 ===")

    try:
        from services.rag_sql_service import RAGSQLService

        # 测试内存缓存模式
        rag_sql_memory = RAGSQLService(cache_type="memory", use_ai=False)
        logger.info("✅ RAG-SQL内存缓存模式初始化成功")

        # 测试Redis缓存模式（如果可用）
        try:
            rag_sql_redis = RAGSQLService(cache_type="redis", use_ai=False)
            logger.info("✅ RAG-SQL Redis缓存模式初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ RAG-SQL Redis缓存模式不可用: {e}")

        return True

    except Exception as e:
        logger.error(f"缓存集成测试失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("Data Agent V4 - Redis缓存集成测试")
    logger.info("=" * 50)

    success = True

    # 基础缓存测试
    success &= await test_cache_service("memory")

    # Redis缓存测试
    success &= await test_cache_service("redis")

    # 缓存工厂测试
    success &= await test_cache_factory()

    # 性能测试
    success &= await test_performance_comparison()

    # 集成测试
    success &= await test_cache_integration()

    if success:
        logger.info("\n🎉 所有缓存测试通过！")
        logger.info("\n使用方法:")
        logger.info("1. 内存缓存 (默认): 设置 CACHE_TYPE=memory 或不设置")
        logger.info("2. Redis缓存: 设置 CACHE_TYPE=redis 并配置 REDIS_URL")
        logger.info("3. 环境变量示例:")
        logger.info("   CACHE_TYPE=redis")
        logger.info("   REDIS_URL=redis://localhost:6379/0")
        logger.info("   REDIS_MAX_CONNECTIONS=10")
        logger.info("   REDIS_TIMEOUT=5")
    else:
        logger.error("\n❌ 部分缓存测试失败")

if __name__ == "__main__":
    asyncio.run(main())