#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试问题9"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'AgentV2'))

os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_FfQa08LupcxT@ep-twilight-frost-ad6vmeng-pooler.c-2.us-east-1.aws.neon.tech/ecommerce_test_db?sslmode=require'

from AgentV2.sql_agent import run_agent

QUESTION = '按品牌统计商品销售额和销量，计算各品牌的市场份额，用饼图展示品牌占比。'

async def main():
    print('=' * 60)
    print('测试问题9: 品牌市场份额分析')
    print('=' * 60)
    try:
        result = await asyncio.wait_for(run_agent(QUESTION, verbose=False, thread_id='test_q9'), timeout=160)
        print(f'成功: {result.success}')
        sql_preview = result.sql[:200] if result.sql else "无"
        print(f'SQL: {sql_preview}...')
        print(f'回答长度: {len(result.answer) if result.answer else 0}')
    except Exception as e:
        print(f'错误: {e}')

asyncio.run(main())
