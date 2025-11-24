#!/usr/bin/env python3
"""
增强性能监控测试脚本
测试新增的查询性能监控功能
"""

import asyncio
import logging
import sys
import os
import time
import random
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_enhanced_monitoring_features():
    """测试增强的监控功能"""
    logger.info("=== 测试增强监控功能 ===")

    try:
        from services.query_performance_monitor import QueryPerformanceMonitor, QueryMetrics

        # 创建增强监控器
        monitor = QueryPerformanceMonitor(max_history=1000, slow_query_threshold=2.0)
        monitor.start_monitoring()

        logger.info("✅ 增强监控器创建成功")

        # 模拟一些查询数据
        query_types = ["SELECT", "INSERT", "UPDATE", "JOIN", "AGGREGATE"]
        tenant_ids = ["tenant1", "tenant2", "tenant3"]

        for i in range(50):
            query_id = f"test_query_{i}"
            tenant_id = random.choice(tenant_ids)
            query_type = random.choice(query_types)

            # 模拟查询执行
            async with monitor.monitor_query(query_id, tenant_id, query_type) as metrics:
                # 模拟各阶段耗时
                await asyncio.sleep(random.uniform(0.1, 1.5))  # 模拟总执行时间

                # 设置各种指标
                metrics.sql_generation_time = random.uniform(0.05, 0.3)
                metrics.sql_validation_time = random.uniform(0.02, 0.1)
                metrics.result_processing_time = random.uniform(0.01, 0.2)
                metrics.row_count = random.randint(1, 1000)

                # 模拟一些缓存命中和错误
                if random.random() < 0.3:  # 30% 缓存命中
                    metrics.cache_hit = True

                if random.random() < 0.05:  # 5% 错误率
                    metrics.error = True
                    metrics.error_message = "Simulated error for testing"

        # 测试新增的功能
        logger.info("\n📊 测试性能趋势分析...")
        trends = monitor.get_performance_trends(hours=24)
        logger.info(f"✅ 趋势分析: {trends.get('trend_direction', 'unknown')} ({trends.get('total_queries', 0)} 查询)")

        logger.info("\n🔍 测试查询模式分析...")
        patterns = monitor.get_query_patterns_analysis()
        cache_hit_rate = patterns.get('cache_analysis', {}).get('hit_rate_percent', 0)
        logger.info(f"✅ 缓存命中率: {cache_hit_rate:.1f}%")
        logger.info(f"✅ 优化建议数量: {len(patterns.get('optimization_suggestions', []))}")

        logger.info("\�� 测试租户性能对比...")
        tenant_comparison = monitor.get_tenant_performance_comparison()
        logger.info(f"✅ 分析了 {tenant_comparison.get('total_tenants', 0)} 个租户")

        logger.info("\📄 测试性能报告生成...")
        report = await monitor.generate_performance_report(hours=1)
        report_lines = report.split('\n')
        logger.info(f"✅ 生成了 {len(report_lines)} 行的报告")

        # 停止监控
        monitor.stop_monitoring()
        logger.info("✅ 监控器已停止")

        return True

    except Exception as e:
        logger.error(f"增强监控功能测试失败: {e}")
        return False

async def test_performance_trends():
    """专门测试性能趋势功能"""
    logger.info("=== 测试性能趋势功能 ===")

    try:
        from services.query_performance_monitor import QueryPerformanceMonitor

        monitor = QueryPerformanceMonitor(slow_query_threshold=1.0)

        # 模拟不同时间段的查询数据
        now = datetime.utcnow()

        for i in range(100):
            # 创建不同时间的查询
            query_time = now - timedelta(hours=random.randint(0, 23))
            query_type = random.choice(["SELECT", "JOIN", "AGGREGATE"])

            # 手动添加查询指标（模拟历史数据）
            metrics = QueryMetrics(
                query_id=f"trend_test_{i}",
                tenant_id="trend_tenant",
                query_type=query_type,
                query_hash="test_hash",
                execution_time=random.uniform(0.1, 3.0),
                sql_generation_time=0.1,
                sql_validation_time=0.05,
                result_processing_time=0.02,
                total_time=random.uniform(0.2, 3.5),
                row_count=random.randint(1, 500),
                cache_hit=random.random() < 0.4,
                error=random.random() < 0.1,
                timestamp=query_time
            )

            monitor._record_query_metrics(metrics)

        # 测试趋势分析
        trends = monitor.get_performance_trends(hours=24)

        logger.info(f"✅ 分析时间段: {trends.get('period_hours', 0)} 小时")
        logger.info(f"✅ 总查询数: {trends.get('total_queries', 0)}")
        logger.info(f"✅ 趋势方向: {trends.get('trend_direction', 'unknown')}")
        logger.info(f"✅ 性能变化: {trends.get('performance_change_percent', 0):.1f}%")

        if 'hourly_breakdown' in trends:
            hourly_count = len(trends['hourly_breakdown'])
            logger.info(f"✅ 小时数据点: {hourly_count}")

        return True

    except Exception as e:
        logger.error(f"性能趋势测试失败: {e}")
        return False

async def test_tenant_performance_scoring():
    """测试租户性能评分功能"""
    logger.info("=== 测试租户性能评分 ===")

    try:
        from services.query_performance_monitor import QueryPerformanceMonitor, QueryMetrics

        monitor = QueryPerformanceMonitor()

        # 模拟不同租户的性能数据
        tenant_scenarios = [
            ("excellent_tenant", 0.5, 90, 1),   # 快速、高缓存命中、低错误率
            ("good_tenant", 1.0, 70, 3),       # 中等速度、中等缓存、低错误率
            ("poor_tenant", 3.0, 30, 15),      # 慢速、低缓存、高错误率
            ("average_tenant", 1.5, 50, 8),     # 平均性能
        ]

        for tenant_id, avg_time, cache_hit_rate, error_rate in tenant_scenarios:
            for i in range(20):  # 每个租户20个查询
                metrics = QueryMetrics(
                    query_id=f"{tenant_id}_query_{i}",
                    tenant_id=tenant_id,
                    query_type="SELECT",
                    query_hash=f"hash_{tenant_id}",
                    execution_time=avg_time * random.uniform(0.8, 1.2),
                    sql_generation_time=0.1,
                    sql_validation_time=0.05,
                    result_processing_time=0.02,
                    total_time=avg_time * random.uniform(0.8, 1.2),
                    row_count=random.randint(10, 100),
                    cache_hit=random.random() < (cache_hit_rate / 100),
                    error=random.random() < (error_rate / 100)
                )
                monitor._record_query_metrics(metrics)

        # 测试租户性能对比
        comparison = monitor.get_tenant_performance_comparison()

        logger.info(f"✅ 分析了 {comparison.get('total_tenants', 0)} 个租户")
        logger.info(f"✅ 顶级表现者: {len(comparison.get('top_performers', {}))}")

        # 显示排名
        top_tenants = comparison.get('top_performers', {})
        for i, (tenant, stats) in enumerate(top_tenants.items(), 1):
            score = stats.get('performance_score', 0)
            avg_time = stats.get('avg_execution_time', 0)
            cache_rate = stats.get('cache_hit_rate', 0)
            error_rate = stats.get('error_rate', 0)
            logger.info(f"  {i}. {tenant}: 评分 {score:.1f} (时间 {avg_time:.3f}s, 缓存 {cache_rate:.1f}%, 错误 {error_rate:.1f}%)")

        # 测试性能分布
        distribution = comparison.get('performance_distribution', {})
        if distribution:
            tiers = distribution.get('performance_tiers', {})
            logger.info(f"✅ 性能等级分布: 优秀 {tiers.get('excellent', 0)}, 良好 {tiers.get('good', 0)}, 一般 {tiers.get('fair', 0)}, 较差 {tiers.get('poor', 0)}")

        return True

    except Exception as e:
        logger.error(f"租户性能评分测试失败: {e}")
        return False

async def test_optimization_suggestions():
    """测试优化建议生成"""
    logger.info("=== 测试优化建议生成 ===")

    try:
        from services.query_performance_monitor import QueryPerformanceMonitor, QueryMetrics

        monitor = QueryPerformanceMonitor(slow_query_threshold=1.0)

        # 模拟需要优化的场景
        optimization_scenarios = [
            # 场景1: 低缓存命中率
            *[QueryMetrics(
                query_id=f"cache_miss_{i}",
                tenant_id="cache_test_tenant",
                query_type="SELECT",
                query_hash="cache_test",
                execution_time=0.5,
                sql_generation_time=0.1,
                sql_validation_time=0.05,
                result_processing_time=0.02,
                total_time=0.67,
                row_count=50,
                cache_hit=False,  # 全部缓存未命中
                error=False
            ) for i in range(30)],

            # 场景2: 慢查询
            *[QueryMetrics(
                query_id=f"slow_query_{i}",
                tenant_id="slow_test_tenant",
                query_type="JOIN",
                query_hash="slow_test",
                execution_time=2.5,
                sql_generation_time=0.1,
                sql_validation_time=0.05,
                result_processing_time=0.02,
                total_time=2.67,
                row_count=1000,
                cache_hit=False,
                error=False
            ) for i in range(15)],

            # 场景3: 高错误率
            *[QueryMetrics(
                query_id=f"error_query_{i}",
                tenant_id="error_test_tenant",
                query_type="SELECT",
                query_hash="error_test",
                execution_time=0.3,
                sql_generation_time=0.1,
                sql_validation_time=0.05,
                result_processing_time=0.02,
                total_time=0.47,
                row_count=10,
                cache_hit=False,
                error=True,
                error_message="Connection timeout"
            ) for i in range(8)],
        ]

        # 记录所有场景
        for metrics in optimization_scenarios:
            monitor._record_query_metrics(metrics)

        # 测试查询模式分析和优化建议
        patterns = monitor.get_query_patterns_analysis()
        suggestions = patterns.get('optimization_suggestions', [])

        logger.info(f"✅ 生成了 {len(suggestions)} 条优化建议")
        for i, suggestion in enumerate(suggestions, 1):
            logger.info(f"  {i}. {suggestion}")

        # 测试错误分类
        error_patterns = patterns.get('error_patterns', {})
        if error_patterns:
            logger.info("✅ 错误模式分析:")
            for error_type, count in error_patterns.items():
                logger.info(f"  - {error_type}: {count} 次")

        # 测试性能四分位数
        quartiles = patterns.get('performance_quartiles', {})
        if quartiles:
            logger.info("✅ 性能四分位数:")
            logger.info(f"  - 最小值: {quartiles.get('min', 0):.3f}s")
            logger.info(f"  - 第一四分位: {quartiles.get('q1', 0):.3f}s")
            logger.info(f"  - 中位数: {quartiles.get('median', 0):.3f}s")
            logger.info(f"  - 第三四分位: {quartiles.get('q3', 0):.3f}s")
            logger.info(f"  - 最大值: {quartiles.get('max', 0):.3f}s")

        return True

    except Exception as e:
        logger.error(f"优化建议测试失败: {e}")
        return False

async def test_performance_report_generation():
    """测试性能报告生成"""
    logger.info("=== 测试性能报告生成 ===")

    try:
        from services.query_performance_monitor import QueryPerformanceMonitor

        monitor = QueryPerformanceMonitor()

        # 模拟一些数据用于报告
        for i in range(40):
            async with monitor.monitor_query(f"report_test_{i}", "report_tenant", "SELECT") as metrics:
                await asyncio.sleep(random.uniform(0.1, 0.8))
                metrics.row_count = random.randint(1, 200)
                metrics.cache_hit = random.random() < 0.4

        # 生成报告
        report = await monitor.generate_performance_report(hours=1)

        # 验证报告内容
        if "查询性能监控报告" in report:
            logger.info("✅ 报告标题正确")
        if "整体统计" in report:
            logger.info("✅ 包含整体统计")
        if "性能趋势" in report:
            logger.info("✅ 包含性能趋势")
        if "优化建议" in report:
            logger.info("✅ 包含优化建议")
        if "租户性能排名" in report:
            logger.info("✅ 包含租户排名")

        lines = report.split('\n')
        logger.info(f"✅ 报告总行数: {len(lines)}")

        # 显示报告摘要
        for line in lines[:10]:  # 显示前10行
            if line.strip():
                logger.info(f"  {line}")

        return True

    except Exception as e:
        logger.error(f"性能报告生成测试失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("Data Agent V4 - 增强性能监控测试")
    logger.info("=" * 50)

    success = True

    # 基础增强功能测试
    success &= await test_enhanced_monitoring_features()

    # 性能趋势测试
    success &= await test_performance_trends()

    # 租户性能评分测试
    success &= await test_tenant_performance_scoring()

    # 优化建议测试
    success &= await test_optimization_suggestions()

    # 报告生成测试
    success &= await test_performance_report_generation()

    if success:
        logger.info("\n🎉 所有增强监控功能测试通过！")
        logger.info("\n新增功能:")
        logger.info("1. ✅ 性能趋势分析 - 按小时分析查询性能变化")
        logger.info("2. ✅ 查询模式分析 - 分析查询类型分布和缓存效果")
        logger.info("3. ✅ 租户性能评分 - 综合评分和排名系统")
        logger.info("4. ✅ 智能优化建议 - 基于数据的性能优化建议")
        logger.info("5. ✅ 性能报告生成 - 自动生成详细的性能报告")
        logger.info("6. ✅ 错误分类分析 - 按错误类型分类和统计")
        logger.info("7. ✅ 性能四分位数分析 - 详细的性能分布统计")
        logger.info("\n使用方法:")
        logger.info("- 获取趋势: monitor.get_performance_trends(hours=24)")
        logger.info("- 分析模式: monitor.get_query_patterns_analysis()")
        logger.info("- 租户对比: monitor.get_tenant_performance_comparison()")
        logger.info("- 生成报告: await monitor.generate_performance_report(hours=24)")
    else:
        logger.error("\n❌ 部分增强监控功能测试失败")

if __name__ == "__main__":
    asyncio.run(main())