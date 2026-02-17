#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试问题10"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'AgentV2'))

os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_FfQa08LupcxT@ep-twilight-frost-ad6vmeng-pooler.c-2.us-east-1.aws.neon.tech/ecommerce_test_db?sslmode=require'

from AgentV2.sql_agent import run_agent

QUESTION = '分析每月商品评价的平均评分变化趋势，同时展示评价数量，用双轴图（折线+柱状）展示评分和评价数量的关系。'

async def main():
    print('=' * 60)
    print('测试问题10: 评价满意度趋势')
    print('=' * 60)
    try:
        result = await asyncio.wait_for(run_agent(QUESTION, verbose=True, thread_id='test_q10'), timeout=160)
        print(f'\n成功: {result.success}')
        sql_preview = result.sql[:200] if result.sql else "无"
        print(f'SQL: {sql_preview}...')
        print(f'回答长度: {len(result.answer) if result.answer else 0}')
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(main())
