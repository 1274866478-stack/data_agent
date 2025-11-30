#!/usr/bin/env python3
"""
测试AI不再说"无法访问数据库"的修复效果
"""

import requests
import json
import sys

# 配置
API_BASE_URL = "http://localhost:8004"
TENANT_ID = "test_tenant_001"

def test_ai_response():
    """测试AI对数据查询问题的回复"""
    
    print("=" * 80)
    print("测试：AI是否还会说'无法访问数据库'")
    print("=" * 80)
    
    # 测试问题
    test_questions = [
        "库存最多的产品是什么？",
        "我们一共有多少客户？",
        "2024年总销售额是多少？",
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}/{len(test_questions)}: {question}")
        print(f"{'='*80}")
        
        # 调用LLM API
        url = f"{API_BASE_URL}/api/v1/llm/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": TENANT_ID
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": question
                }
            ],
            "provider": "zhipu",
            "stream": False
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                print(f"\n✅ API调用成功")
                print(f"\n📝 AI回复：")
                print("-" * 80)
                print(content)
                print("-" * 80)
                
                # 检查是否包含禁止的短语
                forbidden_phrases = [
                    "无法访问数据库",
                    "无法执行查询",
                    "当前环境不支持",
                    "我无法直接访问",
                    "请您自己执行",
                    "如果您提供查询结果"
                ]
                
                found_forbidden = []
                for phrase in forbidden_phrases:
                    if phrase in content:
                        found_forbidden.append(phrase)
                
                if found_forbidden:
                    print(f"\n❌ 检测到禁止的短语：")
                    for phrase in found_forbidden:
                        print(f"   - '{phrase}'")
                    print(f"\n⚠️  修复未完全生效，AI仍然说无法访问数据库")
                else:
                    print(f"\n✅ 未检测到禁止的短语")
                    
                    # 检查是否包含SQL代码块
                    if "```sql" in content:
                        print(f"✅ 包含SQL查询")
                        print(f"✅ 修复生效！AI正确生成了SQL查询")
                    else:
                        print(f"⚠️  未检测到SQL查询")
                
            else:
                print(f"\n❌ API调用失败")
                print(f"状态码: {response.status_code}")
                print(f"响应: {response.text}")
                
        except Exception as e:
            print(f"\n❌ 请求失败: {e}")
    
    print(f"\n{'='*80}")
    print("测试完成")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_ai_response()

