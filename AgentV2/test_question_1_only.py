#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""只测试问题1的简化脚本"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "AgentV2"))

os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_FfQa08LupcxT@ep-twilight-frost-ad6vmeng-pooler.c-2.us-east-1.aws.neon.tech/ecommerce_test_db?sslmode=require'

from AgentV2.sql_agent import run_agent

QUESTION = "分析2024年1月到4月的月度销售趋势，统计每月的订单数量、总销售额和平均客单价，用折线图展示趋势变化。"

async def main():
    print("=" * 80)
    print("测试问题1: 销售趋势分析")
    print("=" * 80)
    print(f"问题: {QUESTION}")
    print("-" * 80)

    result = await run_agent(QUESTION, verbose=True)

    print("\n" + "=" * 80)
    print("测试结果")
    print("=" * 80)
    print(f"成功: {result.success if hasattr(result, 'success') else 'N/A'}")
    print(f"SQL: {result.sql if hasattr(result, 'sql') else 'N/A'}")
    print(f"回答长度: {len(result.answer) if hasattr(result, 'answer') and result.answer else 0}")
    print(f"图表类型: {result.chart.chart_type if hasattr(result, 'chart') and result.chart else 'N/A'}")

    if hasattr(result, 'answer') and result.answer:
        print(f"\n回答内容:")
        print(result.answer[:500])

if __name__ == "__main__":
    asyncio.run(main())
