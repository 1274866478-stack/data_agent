#!/usr/bin/env python3
"""
测试AI助手的SQL执行功能
"""

import requests
import json

API_BASE_URL = "http://localhost:8004"
TENANT_ID = "default_tenant"

def test_chat_with_sql():
    """测试聊天接口的SQL执行功能"""
    print("=" * 60)
    print("  测试 AI 助手 SQL 执行功能")
    print("=" * 60)
    print()
    
    # 测试问题
    question = "2024年总销售额是多少？"
    
    print(f"📝 问题: {question}")
    print()
    
    # 构建请求
    url = f"{API_BASE_URL}/api/v1/llm/chat/completions"
    payload = {
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "model": "glm-4-flash",
        "temperature": 0.3,
        "stream": False
    }
    
    print("🔄 发送请求到 AI 助手...")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ 请求成功!")
            print()
            print("=" * 60)
            print("  AI 回答")
            print("=" * 60)
            print()
            print(result.get("content", "无内容"))
            print()
            print("=" * 60)
            print()
            
            # 检查是否包含SQL和查询结果
            content = result.get("content", "")
            has_sql = "```sql" in content
            has_result = "查询结果" in content or "返回行数" in content
            
            print("📊 功能检查:")
            print(f"  - 包含SQL查询: {'✅ 是' if has_sql else '❌ 否'}")
            print(f"  - 包含查询结果: {'✅ 是' if has_result else '❌ 否'}")
            print()
            
            if has_sql and has_result:
                print("🎉 成功！AI助手正确生成并执行了SQL查询！")
            elif has_sql and not has_result:
                print("⚠️  AI生成了SQL，但可能没有执行或数据源未配置")
            else:
                print("❌ AI没有生成SQL查询，可能是数据源未配置")
            
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    print()
    success = test_chat_with_sql()
    print()
    
    if success:
        print("💡 提示:")
        print("   如果AI没有执行SQL，请确保:")
        print("   1. 已在数据源管理中添加 chatbi_test 数据库")
        print("   2. 数据源状态为'激活'")
        print("   3. 连接字符串使用 'db' 而不是 'localhost'")
        print()
        print("   添加数据源命令:")
        print("   python scripts/add-chatbi-datasource.py")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")

