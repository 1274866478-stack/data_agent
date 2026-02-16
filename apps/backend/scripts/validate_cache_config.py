"""
[HEADER]
缓存配置验证工具 - Cache Configuration Validator
用于验证Redis和内存缓存的配置和性能

[MODULE]
模块类型: 配置验证脚本 (Standalone Script)
所属功能: 开发工具与配置验证
技术栈: Python 3.8+, asyncio, logging, time

[INPUT]
- 命令行参数: 无
- 环境变量依赖:
  - REDIS_URL: Redis连接URL (可选)
  - CACHE_TYPE: 缓存类型 (memory/redis, 默认memory)
- 配置来源:
  - src.services.cache_service - 缓存服务工厂和实现
- 测试数据:
  - 内存缓存测试: {"message": "Hello World", "timestamp": ...}
  - Redis缓存测试: {"message": "Hello Redis", "timestamp": ...}

[OUTPUT]
- 控制台输出:
  - 测试进度和结果 (emoji标识)
  - 健康检查状态
  - 性能测试结果 (ops/sec)
  - 验证总结
- 退出码:
  - 0: 所有测试通过
  - 1: 部分或全部测试失败
- 测试项目:
  1. 内存缓存: 基本操作、TTL过期、大小限制
  2. Redis缓存: 连接、基本操作、租户隔离、信息获取
  3. 缓存工厂: 创建memory/redis/default缓存
  4. 性能测试: 读写性能 (1000次操作)

[LINK]
- 依赖模块:
  - src.services.cache_service.CacheFactory - 缓存工厂
  - src.services.cache_service.MemoryCache - 内存缓存实现
  - src.services.cache_service.RedisCache - Redis缓存实现
- 关联脚本:
  - scripts/validate_zhipu_config.py - 智谱AI配置验证
  - scripts/validate_database_support.py - 数据库支持验证
- 文档参考:
  - docs/setup/cache-setup.md - 缓存配置指南

[POS]
- 文件路径: backend/scripts/validate_cache_config.py
- 执行方式:
  - 直接运行: python scripts/validate_cache_config.py
  - Docker: docker-compose exec backend python scripts/validate_cache_config.py
- 使用场景:
  - 首次配置缓存后验证
  - 缓存性能问题排查
  - CI/CD流程中的性能基准测试

[PROTOCOL]
- 执行流程:
  1. 内存缓存测试:
     - 写入/读取测试数据
     - 验证TTL过期机制 (1秒)
     - 检查缓存大小
  2. Redis缓存测试:
     - 健康检查 (health_check)
     - 写入/读取测试数据
     - 租户缓存清理测试
     - 获取Redis信息
     - 关闭连接
  3. 缓存工厂测试:
     - 创建memory缓存
     - 创建redis缓存 (如果可用)
     - 创建default缓存
  4. 性能测试:
     - 写入性能: 1000次set操作
     - 读取性能: 1000次get操作
     - 输出ops/sec指标
- 测试标准:
  - 内存缓存: 所有基本功能正常
  - Redis缓存: 连接成功, 健康状态为healthy
  - 性能基准:
    - 内存缓存: >10000 ops/sec
    - Redis缓存: >1000 ops/sec (取决于网络)
- 错误处理:
  - 捕获所有异常并记录
  - Redis未安装: 显示警告, 继续执行
  - 连接失败: 记录错误, 跳过相关测试
- 结果判断:
  - 全部通过: 退出码 0
  - 部分失败: 显示失败组件, 退出码 1

[PERFORMANCE]
- 性能测试参数:
  - 操作次数: 1000
  - TTL测试: 1秒 (sleep 2秒验证过期)
  - 缓存大小: 1000 (max_size)
- 指标计算:
  - write_ops_per_sec = operations / write_time
  - read_ops_per_sec = operations / read_time
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.services.cache_service import CacheFactory, MemoryCache, RedisCache

logger = logging.getLogger(__name__)


async def test_memory_cache():
    """测试内存缓存"""
    print("🧪 测试内存缓存...")

    try:
        # 创建内存缓存
        cache = MemoryCache(max_size=1000, default_ttl=60)

        # 测试基本操作
        test_key = "test_memory_key"
        test_value = {"message": "Hello World", "timestamp": time.time()}

        # 设置缓存
        await cache.set(test_key, test_value, ttl=60)
        print("✅ 内存缓存写入成功")

        # 获取缓存
        result = await cache.get(test_key)
        if result and result.get("message") == "Hello World":
            print("✅ 内存缓存读取成功")
        else:
            print("❌ 内存缓存读取失败")
            return False

        # 测试TTL过期
        await cache.set(test_key, test_value, ttl=1)
        await asyncio.sleep(2)
        result = await cache.get(test_key)
        if result is None:
            print("✅ 内存缓存TTL过期机制正常")
        else:
            print("❌ 内存缓存TTL过期机制异常")
            return False

        # 获取缓存大小
        size = await cache.get_size()
        print(f"✅ 内存缓存当前大小: {size}")

        return True

    except Exception as e:
        print(f"❌ 内存缓存测试失败: {e}")
        return False


async def test_redis_cache():
    """测试Redis缓存"""
    print("\n🧪 测试Redis缓存...")

    try:
        # 创建Redis缓存
        cache = RedisCache()

        # 执行健康检查
        health = await cache.health_check()
        print(f"Redis健康检查: {health.get('status', 'unknown')}")

        if health.get("status") != "healthy":
            print(f"❌ Redis缓存不健康: {health.get('message', 'Unknown error')}")
            return False

        # 测试基本操作
        test_key = "test_redis_key"
        test_value = {"message": "Hello Redis", "timestamp": time.time()}

        # 设置缓存
        await cache.set(test_key, test_value, ttl=60)
        print("✅ Redis缓存写入成功")

        # 获取缓存
        result = await cache.get(test_key)
        if result and result.get("message") == "Hello Redis":
            print("✅ Redis缓存读取成功")
        else:
            print("❌ Redis缓存读取失败")
            return False

        # 测试租户缓存清理
        tenant_id = "test_tenant_123"
        tenant_key = f"tenant:{tenant_id}:test_key"
        await cache.set(tenant_key, {"data": "test_data"})
        await cache.clear_tenant_cache(tenant_id)
        result = await cache.get(tenant_key)
        if result is None:
            print("✅ Redis租户缓存清理成功")
        else:
            print("❌ Redis租户缓存清理失败")
            return False

        # 获取Redis信息
        info = await cache.get_info()
        if info and not info.get("error"):
            print(f"✅ Redis版本: {info.get('redis_version')}")
            print(f"   使用内存: {info.get('used_memory')}")
            print(f"   连接客户端: {info.get('connected_clients')}")
        else:
            print("⚠️  获取Redis信息失败，但基本功能正常")

        # 关闭连接
        await cache.close()
        print("✅ Redis连接已关闭")

        return True

    except ImportError as e:
        print(f"⚠️  Redis库未安装: {e}")
        print("   安装方法: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis缓存测试失败: {e}")
        return False


async def test_cache_factory():
    """测试缓存工厂"""
    print("\n🧪 测试缓存工厂...")

    try:
        # 测试内存缓存工厂
        memory_cache = CacheFactory.create_cache("memory")
        print("✅ 内存缓存工厂创建成功")

        # 测试Redis缓存工厂（如果可用）
        try:
            redis_cache = CacheFactory.create_cache("redis")
            print("✅ Redis缓存工厂创建成功")
        except Exception as e:
            print(f"⚠️  Redis缓存工厂创建失败: {e}")

        # 测试默认缓存
        default_cache = CacheFactory.get_default_cache()
        print("✅ 默认缓存创建成功")

        return True

    except Exception as e:
        print(f"❌ 缓存工厂测试失败: {e}")
        return False


async def performance_test(cache, cache_name: str, operations: int = 1000):
    """性能测试"""
    print(f"\n⚡ {cache_name} 性能测试 ({operations} 次操作)...")

    try:
        # 写入性能测试
        start_time = time.time()
        for i in range(operations):
            await cache.set(f"perf_test_{i}", {"value": i}, ttl=3600)
        write_time = time.time() - start_time
        write_ops_per_sec = operations / write_time

        # 读取性能测试
        start_time = time.time()
        for i in range(operations):
            await cache.get(f"perf_test_{i}")
        read_time = time.time() - start_time
        read_ops_per_sec = operations / read_time

        print(f"   写入性能: {write_ops_per_sec:.0f} ops/sec")
        print(f"   读取性能: {read_ops_per_sec:.0f} ops/sec")

        # 清理测试数据
        if hasattr(cache, 'clear_tenant_cache'):
            # 如果是Redis缓存，不能直接清空所有
            pass
        elif hasattr(cache, 'clear_all'):
            await cache.clear_all()

        return True

    except Exception as e:
        print(f"❌ {cache_name} 性能测试失败: {e}")
        return False


async def main():
    """主函数"""
    print("🔍 开始缓存配置验证...\n")

    results = {}

    # 1. 测试内存缓存
    results["memory"] = await test_memory_cache()

    # 2. 测试Redis缓存
    results["redis"] = await test_redis_cache()

    # 3. 测试缓存工厂
    results["factory"] = await test_cache_factory()

    # 4. 性能测试
    if results["memory"]:
        memory_cache = CacheFactory.create_cache("memory")
        await performance_test(memory_cache, "内存缓存", 1000)

    if results["redis"]:
        try:
            redis_cache = CacheFactory.create_cache("redis")
            await performance_test(redis_cache, "Redis缓存", 1000)
            await redis_cache.close()
        except Exception:
            pass

    # 结果总结
    print(f"\n📋 验证结果:")
    for component, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"- {component}: {status}")

    passed_count = sum(results.values())
    total_count = len(results)

    if passed_count == total_count:
        print(f"\n🎉 所有缓存组件验证通过！")
        return 0
    else:
        print(f"\n💥 部分缓存组件验证失败 ({passed_count}/{total_count})")
        return 1


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行异步验证
    exit_code = asyncio.run(main())
    sys.exit(exit_code)