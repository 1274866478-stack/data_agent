#!/usr/bin/env python3
"""
XAI和融合引擎测试运行器
用于快速验证实现的正确性
"""

import asyncio
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_basic_functionality():
    """测试基础功能"""
    print("开始基础功能测试...")

    try:
        from src.app.services.fusion_service import fusion_engine
        from src.app.services.xai_service import xai_service
        from src.app.services.reasoning_service import enhanced_reasoning_engine

        print("✅ 服务导入成功")

        # 测试数据
        query = "第三季度的销售表现如何？"
        sql_results = [
            {
                "data": [
                    {"month": "July", "revenue": 45000, "growth": 0.12},
                    {"month": "August", "revenue": 52000, "growth": 0.15}
                ],
                "confidence": 0.95
            }
        ]

        rag_results = [
            {
                "content": "根据市场分析，第三季度表现超出预期，主要得益于产品创新。",
                "similarity_score": 0.88,
                "confidence": 0.85
            }
        ]

        # 测试融合引擎
        print("🔗 测试融合引擎...")
        fusion_result = await fusion_engine.fuse_multi_source_data(
            query=query,
            sql_results=sql_results,
            rag_results=rag_results,
            tenant_id="test_tenant"
        )

        assert fusion_result is not None
        assert len(fusion_result.answer) > 0
        assert fusion_result.confidence > 0
        print(f"✅ 融合引擎测试成功 - 置信度: {fusion_result.confidence:.2f}")

        # 测试XAI服务
        print("🧠 测试XAI服务...")
        xai_result = await xai_service.generate_explanation(
            query=query,
            answer=fusion_result.answer,
            sources=[
                {
                    "source_id": "test_1",
                    "source_type": "sql_query",
                    "source_name": "测试数据源",
                    "content": "测试内容",
                    "confidence": 0.9
                }
            ],
            tenant_id="test_tenant"
        )

        assert xai_result is not None
        assert len(xai_result.explanation_steps) > 0
        print(f"✅ XAI服务测试成功 - 解释质量: {xai_result.explanation_quality_score:.2f}")

        # 测试增强推理引擎
        print("🚀 测试增强推理引擎...")
        enhanced_result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=sql_results,
            rag_results=rag_results,
            tenant_id="test_tenant",
            enable_fusion=True,
            enable_xai=True
        )

        assert enhanced_result is not None
        assert enhanced_result["enhanced_answer"] is not None
        assert enhanced_result["fusion_result"] is not None
        assert enhanced_result["xai_explanation"] is not None
        print(f"✅ 增强推理引擎测试成功 - 整体质量: {enhanced_result['quality_metrics']['overall_quality']:.2f}")

        print("🎉 所有基础功能测试通过！")
        return True

    except Exception as e:
        logger.error(f"基础功能测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        return False

async def test_data_models():
    """测试数据模型"""
    print("📊 测试数据模型...")

    try:
        from src.app.data.models import (
            ExplanationLog, FusionResult, ReasoningPath,
            ExplanationLogStatus, FusionResultStatus
        )

        print("✅ 数据模型导入成功")

        # 测试枚举
        assert ExplanationLogStatus.GENERATING.value == "generating"
        assert FusionResultStatus.COMPLETED.value == "completed"
        print("✅ 枚举测试通过")

        print("📋 数据模型测试通过！")
        return True

    except Exception as e:
        logger.error(f"数据模型测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        return False

async def test_error_handling():
    """测试错误处理"""
    print("⚠️ 测试错误处理...")

    try:
        from src.app.services.enhanced_reasoning_service import enhanced_reasoning_engine

        # 测试空输入
        result = await enhanced_reasoning_engine.enhanced_reason(
            query="",
            tenant_id="error_test"
        )

        assert result is not None
        assert result["enhanced_answer"] is not None
        print("✅ 空输入处理测试通过")

        # 测试None数据源
        result2 = await enhanced_reasoning_engine.enhanced_reason(
            query="测试查询",
            sql_results=None,
            rag_results=None,
            documents=None,
            tenant_id="error_test"
        )

        assert result2 is not None
        print("✅ None数据源处理测试通过")

        print("🛡️ 错误处理测试通过！")
        return True

    except Exception as e:
        logger.error(f"错误处理测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        return False

async def test_performance():
    """测试性能"""
    print("⚡ 测试性能...")

    try:
        from src.app.services.enhanced_reasoning_service import enhanced_reasoning_engine

        # 简单性能测试
        start_time = datetime.utcnow()

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="性能测试查询",
            tenant_id="perf_test"
        )

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        assert result is not None
        assert processing_time < 10  # 应该在10秒内完成

        print(f"✅ 性能测试通过 - 处理时间: {processing_time:.2f}秒")
        return True

    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        return False

async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行XAI和融合引擎测试套件\n")

    tests = [
        ("基础功能", test_basic_functionality),
        ("数据模型", test_data_models),
        ("错误处理", test_error_handling),
        ("性能测试", test_performance)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 运行测试: {test_name}")
        print(f"{'='*50}")

        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"测试 {test_name} 执行失败: {e}")
            results.append((test_name, False))

    # 汇总结果
    print(f"\n{'='*60}")
    print("📋 测试结果汇总")
    print(f"{'='*60}")

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} : {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("🎉 所有测试都通过了！XAI和融合引擎实现正确。")
        return True
    else:
        print(f"⚠️ 有 {total - passed} 个测试失败，请检查实现。")
        return False

async def main():
    """主函数"""
    try:
        success = await run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试运行器执行失败: {e}")
        print(f"❌ 运行器失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())