#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电商数据可视化10问题测试脚本
逐一测试10个问题，确保每个问题都有完整的SQL、可视化和分析结果
"""
import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "AgentV2"))

# 修改配置使用测试数据库
# 使用Neon云数据库（支持SSL）
backend_db_url = os.getenv('DATABASE_URL', '')
if backend_db_url and 'neon' in backend_db_url.lower():
    # 如果环境变量是Neon数据库，直接使用
    test_db_url = backend_db_url
else:
    # 否则使用硬编码的Neon测试数据库
    test_db_url = 'postgresql://neondb_owner:npg_FfQa08LupcxT@ep-twilight-frost-ad6vmeng-pooler.c-2.us-east-1.aws.neon.tech/ecommerce_test_db?sslmode=require'

os.environ['DATABASE_URL'] = test_db_url

# 导入AgentV2模块
import AgentV2
from AgentV2.sql_agent import run_agent
from AgentV2.config import config

# 强制使用测试数据库
config.database_url = test_db_url

print(f"Using database: {config.database_url.rsplit('/', 1)[-1]}")
print(f"Using model: {config.deepseek_model}")
print("=" * 80)

# 10个测试问题
TEST_QUESTIONS = [
    {
        "id": 1,
        "name": "销售趋势分析",
        "question": "分析2024年1月到4月的月度销售趋势，统计每月的订单数量、总销售额和平均客单价，用折线图展示趋势变化。",
        "expected_tables": ["orders"],
        "expected_chart": "折线图",
        "min_analysis_words": 200
    },
    {
        "id": 2,
        "name": "用户VIP等级分布",
        "question": "统计不同VIP等级用户的数量分布，以及各等级用户的平均消费金额，用饼图展示用户数量分布，柱状图对比平均消费。",
        "expected_tables": ["users"],
        "expected_chart": "饼图+柱状图",
        "min_analysis_words": 200
    },
    {
        "id": 3,
        "name": "商品类别销售排行",
        "question": "按商品类别统计销售额和销量排行，分析哪个类别最受欢迎，用横向柱状图展示Top类别。",
        "expected_tables": ["products", "categories", "order_items"],
        "expected_chart": "横向柱状图",
        "min_analysis_words": 200
    },
    {
        "id": 4,
        "name": "商品价格与销量关系分析",
        "question": "分析商品价格与销量的关系，找出高销量低价和高价低销的商品，用散点图展示价格vs销量分布。",
        "expected_tables": ["products"],
        "expected_chart": "散点图",
        "min_analysis_words": 200
    },
    {
        "id": 5,
        "name": "地区销售分布",
        "question": "按用户收货地址的省份统计销售分布，展示各省份的订单数量和销售额，用柱状图展示。",
        "expected_tables": ["users", "addresses", "orders"],
        "expected_chart": "柱状图",
        "min_analysis_words": 200
    },
    {
        "id": 6,
        "name": "订单状态转化漏斗",
        "question": "分析订单从待付款到完成的状态流转情况，统计各状态订单数量，用漏斗图展示订单转化率。",
        "expected_tables": ["orders"],
        "expected_chart": "漏斗图",
        "min_analysis_words": 200
    },
    {
        "id": 7,
        "name": "商品评分与销量关联分析",
        "question": "分析商品评分与销量的关系，用散点图展示评分vs销量，并标注高评分高销量的明星产品。",
        "expected_tables": ["products", "reviews"],
        "expected_chart": "散点图",
        "min_analysis_words": 200
    },
    {
        "id": 8,
        "name": "用户复购行为分析",
        "question": "统计每个用户的下单次数，分析复购用户占比，用直方图展示用户订单数量分布。",
        "expected_tables": ["orders"],
        "expected_chart": "直方图",
        "min_analysis_words": 200
    },
    {
        "id": 9,
        "name": "品牌市场份额分析",
        "question": "按品牌统计商品销售额和销量，计算各品牌的市场份额，用饼图或环形图展示品牌占比。",
        "expected_tables": ["products", "order_items"],
        "expected_chart": "饼图/环形图",
        "min_analysis_words": 200
    },
    {
        "id": 10,
        "name": "评价满意度趋势",
        "question": "分析每月商品评价的平均评分变化趋势，同时展示评价数量，用双轴图（折线+柱状）展示评分和评价数量的关系。",
        "expected_tables": ["reviews", "orders"],
        "expected_chart": "双轴图",
        "min_analysis_words": 200
    },
]

async def test_single_question(q_data, timeout=120):
    """测试单个问题"""
    print(f"\n{'=' * 80}")
    print(f"问题 {q_data['id']}: {q_data['name']}")
    print(f"{'=' * 80}")
    print(f"问题: {q_data['question']}")
    print(f"期望图表: {q_data['expected_chart']}")
    print(f"涉及表: {', '.join(q_data['expected_tables'])}")
    print("-" * 80)

    start_time = datetime.now()

    try:
        # 🔧 为每个问题使用独立的 thread_id，避免对话历史累积
        result = await asyncio.wait_for(
            run_agent(q_data['question'], verbose=True, thread_id=f"test_q{q_data['id']}"),
            timeout=timeout
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        # 分析结果
        analysis = {
            "question_id": q_data['id'],
            "question_name": q_data['name'],
            "success": result.success if hasattr(result, 'success') else True,
            "has_sql": bool(result.sql) if hasattr(result, 'sql') else False,
            "has_chart": bool(result.chart) if hasattr(result, 'chart') else False,
            "answer_length": len(result.answer) if hasattr(result, 'answer') and result.answer else 0,
            "elapsed_seconds": elapsed,
            "answer": result.answer if hasattr(result, 'answer') else "",
            "sql": result.sql if hasattr(result, 'sql') else "",
            "chart_type": str(result.chart.chart_type) if hasattr(result, 'chart') and result.chart and hasattr(result.chart, 'chart_type') else None,
        }

        # 打印结果摘要
        print(f"\n结果摘要:")
        print(f"  成功: {analysis['success']}")
        print(f"  有SQL: {analysis['has_sql']}")
        print(f"  有图表: {analysis['has_chart']}")
        print(f"  图表类型: {analysis['chart_type']}")
        print(f"  回答字数: {analysis['answer_length']}")
        print(f"  耗时: {elapsed:.1f}秒")

        # 检查分析字数是否达标
        if analysis['answer_length'] < q_data['min_analysis_words']:
            print(f"  ⚠️ 警告: 分析字数不足 ({analysis['answer_length']} < {q_data['min_analysis_words']})")
        else:
            print(f"  ✓ 分析字数达标")

        # 打印SQL（如果有）
        if analysis['has_sql']:
            print(f"\n生成的SQL:")
            print(f"  {analysis['sql'][:200]}...")
        else:
            print(f"\n⚠️ 警告: 没有生成SQL")

        # 打印分析（前500字）
        if analysis['answer']:
            print(f"\n分析内容:")
            print(f"  {analysis['answer'][:500]}...")

        return analysis

    except asyncio.TimeoutError:
        print(f"\n❌ 超时! 超过{timeout}秒未完成")
        return {
            "question_id": q_data['id'],
            "question_name": q_data['name'],
            "success": False,
            "error": "timeout",
            "elapsed_seconds": timeout
        }
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            "question_id": q_data['id'],
            "question_name": q_data['name'],
            "success": False,
            "error": str(e),
            "elapsed_seconds": (datetime.now() - start_time).total_seconds()
        }

async def main():
    """主测试函数"""
    print(f"开始测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"共 {len(TEST_QUESTIONS)} 个问题需要测试\n")

    results = []

    for i, q_data in enumerate(TEST_QUESTIONS, 1):
        print(f"\n进度: [{i}/{len(TEST_QUESTIONS)}]")

        # 🔧 重置Agent以避免SSL连接问题累积
        from AgentV2.sql_agent import reset_agent
        await reset_agent()

        # 🔧 添加延迟，让MCP服务器完全关闭
        import asyncio
        await asyncio.sleep(2)

        result = await test_single_question(q_data)
        results.append(result)

        # 保存中间结果
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    # 打印总结
    print(f"\n{'=' * 80}")
    print(f"测试总结")
    print(f"{'=' * 80}")

    success_count = sum(1 for r in results if r.get('success', False))
    has_sql_count = sum(1 for r in results if r.get('has_sql', False))
    has_chart_count = sum(1 for r in results if r.get('has_chart', False))
    words_ok_count = sum(1 for r in results if r.get('answer_length', 0) >= 200)

    print(f"总问题数: {len(results)}")
    print(f"执行成功: {success_count}")
    print(f"生成SQL: {has_sql_count}")
    print(f"生成图表: {has_chart_count}")
    print(f"分析达标: {words_ok_count}")

    print(f"\n详细结果:")
    for r in results:
        status = "✓" if r.get('success', False) else "✗"
        print(f"  {status} 问题{r['question_id']}: {r['question_name']}")

    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结果已保存到: test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
