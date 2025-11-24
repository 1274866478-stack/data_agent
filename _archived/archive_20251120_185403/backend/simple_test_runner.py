#!/usr/bin/env python3
"""
简化的XAI和融合引擎测试运行器
"""

import asyncio
import logging
import sys
import os

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_imports():
    """测试导入"""
    print("测试模块导入...")

    try:
        from src.app.services.fusion_service import fusion_engine
        from src.app.services.xai_service import xai_service
        from src.app.services.reasoning_service import enhanced_reasoning_engine
        print("所有模块导入成功")
        return True
    except Exception as e:
        print(f"导入失败: {e}")
        return False

async def test_basic_fusion():
    """测试基本融合功能"""
    print("测试融合引擎...")

    try:
        from src.app.services.fusion_service import fusion_engine

        query = "测试查询"
        sql_results = [
            {
                "data": [{"value": 100}],
                "confidence": 0.9
            }
        ]

        result = await fusion_engine.fuse_multi_source_data(
            query=query,
            sql_results=sql_results,
            tenant_id="test"
        )

        if result and result.answer:
            print(f"融合引擎测试成功 - 答案长度: {len(result.answer)}")
            return True
        else:
            print("融合引擎返回空结果")
            return False

    except Exception as e:
        print(f"融合引擎测试失败: {e}")
        return False

async def test_basic_xai():
    """测试基本XAI功能"""
    print("测试XAI服务...")

    try:
        from src.app.services.xai_service import xai_service

        result = await xai_service.generate_explanation(
            query="测试查询",
            answer="测试答案",
            tenant_id="test"
        )

        if result and result.explanation_steps:
            print(f"XAI服务测试成功 - 解释步骤数: {len(result.explanation_steps)}")
            return True
        else:
            print("XAI服务返回空结果")
            return False

    except Exception as e:
        print(f"XAI服务测试失败: {e}")
        return False

async def test_enhanced_reasoning():
    """测试增强推理引擎"""
    print("测试增强推理引擎...")

    try:
        from src.app.services.enhanced_reasoning_service import enhanced_reasoning_engine

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="测试查询",
            tenant_id="test"
        )

        if result and result["enhanced_answer"]:
            print(f"增强推理引擎测试成功 - 答案长度: {len(result['enhanced_answer'])}")
            return True
        else:
            print("增强推理引擎返回空结果")
            return False

    except Exception as e:
        print(f"增强推理引擎测试失败: {e}")
        return False

async def test_data_models():
    """测试数据模型"""
    print("测试数据模型...")

    try:
        from src.app.data.models import ExplanationLog, FusionResult, ReasoningPath
        print("数据模型导入成功")
        return True
    except Exception as e:
        print(f"数据模型测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("=" * 50)
    print("开始XAI和融合引擎测试")
    print("=" * 50)

    tests = [
        ("模块导入", test_imports),
        ("数据模型", test_data_models),
        ("融合引擎", test_basic_fusion),
        ("XAI服务", test_basic_xai),
        ("增强推理引擎", test_enhanced_reasoning)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                print(f"✓ {test_name} - 通过")
            else:
                print(f"✗ {test_name} - 失败")
        except Exception as e:
            print(f"✗ {test_name} - 异常: {e}")
            results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:20} : {status}")

    print(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("\n所有测试都通过了！")
        return True
    else:
        print(f"\n{total - passed} 个测试失败")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"测试运行失败: {e}")
        sys.exit(1)