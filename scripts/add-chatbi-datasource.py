#!/usr/bin/env python3
"""
快速添加 ChatBI 测试数据库到 Data Agent
通过 API 直接添加数据源连接
"""

import requests
import json
import sys

# 配置
API_BASE_URL = "http://localhost:8004/api/v1"
TENANT_ID = "default_tenant"  # 使用默认租户

# ChatBI 测试数据库连接信息
# 注意：后端在Docker容器内，需要使用容器网络中的主机名
DATASOURCE_CONFIG = {
    "name": "ChatBI测试数据库",
    "connection_string": "postgresql://postgres:password@db:5432/chatbi_test",
    "db_type": "postgresql"
}

def test_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    
    url = f"{API_BASE_URL}/data-sources/test"
    response = requests.post(url, json={
        "connection_string": DATASOURCE_CONFIG["connection_string"],
        "db_type": DATASOURCE_CONFIG["db_type"]
    })
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✅ 数据库连接测试成功!")
            print(f"   延迟: {result.get('latency_ms', 'N/A')}ms")
            return True
        else:
            print(f"❌ 连接测试失败: {result.get('message')}")
            return False
    else:
        print(f"❌ API请求失败: {response.status_code}")
        print(f"   {response.text}")
        return False

def create_datasource():
    """创建数据源"""
    print("\n📝 创建数据源...")
    
    url = f"{API_BASE_URL}/data-sources/?tenant_id={TENANT_ID}"
    response = requests.post(url, json=DATASOURCE_CONFIG)
    
    if response.status_code == 201:
        result = response.json()
        print("✅ 数据源创建成功!")
        print(f"   ID: {result.get('id')}")
        print(f"   名称: {result.get('name')}")
        print(f"   状态: {result.get('status')}")
        return result
    else:
        print(f"❌ 创建失败: {response.status_code}")
        print(f"   {response.text}")
        return None

def list_datasources():
    """列出所有数据源"""
    print("\n📋 当前数据源列表:")
    
    url = f"{API_BASE_URL}/data-sources/?tenant_id={TENANT_ID}"
    response = requests.get(url)
    
    if response.status_code == 200:
        datasources = response.json()
        if datasources:
            for ds in datasources:
                print(f"   - {ds.get('name')} ({ds.get('db_type')}) - {ds.get('status')}")
        else:
            print("   (无数据源)")
    else:
        print(f"❌ 获取失败: {response.status_code}")

def main():
    print("=" * 60)
    print("  ChatBI 测试数据库 - 数据源添加工具")
    print("=" * 60)
    print()
    
    # 1. 测试连接
    if not test_connection():
        print("\n⚠️  数据库连接失败，请检查:")
        print("   1. PostgreSQL 容器是否运行: docker ps | grep postgres")
        print("   2. chatbi_test 数据库是否存在")
        print("   3. 连接字符串是否正确")
        sys.exit(1)
    
    # 2. 创建数据源
    datasource = create_datasource()
    if not datasource:
        print("\n⚠️  数据源创建失败")
        sys.exit(1)
    
    # 3. 列出所有数据源
    list_datasources()
    
    print("\n" + "=" * 60)
    print("✅ 完成! 现在您可以在 AI 助手中使用这个数据源了")
    print("=" * 60)
    print()
    print("💡 使用提示:")
    print("   1. 在前端页面刷新数据源列表")
    print("   2. 在 AI 助手中提问，例如:")
    print("      - 2024年总销售额是多少?")
    print("      - 销售额最高的产品是什么?")
    print("      - 哪个地区的客户最多?")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

