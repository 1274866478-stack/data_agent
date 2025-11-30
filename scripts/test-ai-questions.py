#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI助手测试脚本 - 测试多个问题"""

import requests
import time

API_BASE_URL = 'http://localhost:8004'

# 测试问题列表
test_questions = [
    # 简单查询
    ('一共有多少个客户？', '简单'),
    ('有多少个产品？', '简单'),
    ('订单有哪些状态？每个状态有多少订单？', '简单'),
    ('Sales部门有多少员工？', '简单'),
    # 中等查询
    ('哪个地区的客户最多？', '中等'),
    ('每个产品类别有多少个产品？', '中等'),
    ('2024年已完成delivered的订单总金额是多少？', '中等'),
    # 复杂查询
    ('哪个客户的订单总金额最高？', '复杂'),
    ('每个地区的销售总额是多少？按销售额排序', '复杂'),
]

def test_question(question):
    url = f'{API_BASE_URL}/api/v1/llm/chat/completions'
    payload = {
        'messages': [{'role': 'user', 'content': question}],
        'model': 'glm-4-flash',
        'temperature': 0.3,
        'stream': False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            content = result.get('content', '')
            
            has_sql = 'SELECT' in content.upper()
            has_result = '查询结果' in content or '返回行数' in content or '数据预览' in content
            has_error = '执行失败' in content
            
            return {
                'success': True,
                'content': content,
                'has_sql': has_sql,
                'has_result': has_result,
                'has_error': has_error
            }
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def extract_table_preview(content):
    """提取表格预览部分"""
    lines = content.split('\n')
    table_lines = []
    in_table = False
    for line in lines:
        if '|' in line and '---' not in line:
            in_table = True
            table_lines.append(line.strip())
        elif in_table and '|' not in line and line.strip():
            break
    return table_lines[:5]  # 只返回前5行

if __name__ == '__main__':
    print('=' * 70)
    print('  AI助手测试 - 自动化测试')
    print('=' * 70)
    print()

    results = []
    for i, (question, difficulty) in enumerate(test_questions, 1):
        print(f'[{i}/{len(test_questions)}] 测试: {question}')
        print(f'    难度: {difficulty}')
        print('    发送请求中...')
        
        result = test_question(question)
        results.append((question, difficulty, result))
        
        if result['success']:
            if result['has_result'] and not result['has_error']:
                print('    结果: ✅ 成功执行并返回结果')
                # 显示表格预览
                table = extract_table_preview(result['content'])
                for line in table:
                    print(f'      {line[:65]}')
            elif result['has_sql'] and result['has_error']:
                print('    结果: ⚠️ 生成SQL但执行失败')
            elif result['has_sql']:
                print('    结果: 🔶 生成SQL但无结果')
            else:
                print('    结果: ❓ 未生成SQL')
        else:
            print(f'    结果: ❌ 请求失败: {result.get("error", "未知")}')
        
        print()
        time.sleep(1)

    # 统计
    print('=' * 70)
    print('  测试结果汇总')
    print('=' * 70)
    print()

    success = sum(1 for _, _, r in results if r['success'] and r.get('has_result') and not r.get('has_error'))
    sql_only = sum(1 for _, _, r in results if r['success'] and r.get('has_sql') and not r.get('has_result'))
    errors = sum(1 for _, _, r in results if r['success'] and r.get('has_error'))
    failed = sum(1 for _, _, r in results if not r['success'])

    print(f'✅ 成功执行并返回结果: {success}/{len(results)}')
    print(f'🔶 生成SQL但无结果: {sql_only}/{len(results)}')
    print(f'⚠️ SQL执行错误: {errors}/{len(results)}')
    print(f'❌ 请求失败: {failed}/{len(results)}')
    print()
    print('=' * 70)

