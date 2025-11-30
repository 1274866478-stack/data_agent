#!/usr/bin/env python3
"""测试schema获取功能"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, '/app')

from src.services.database_interface import PostgreSQLAdapter


async def test_schema():
    """测试schema获取"""
    adapter = PostgreSQLAdapter()
    connection_string = 'postgresql://postgres:postgres@db:5432/chatbi_test'
    
    print("=" * 60)
    print("测试 PostgreSQLAdapter.get_schema()")
    print("=" * 60)
    
    try:
        schema = await adapter.get_schema(connection_string)
        
        print(f"\n数据库类型: {schema.get('database_type')}")
        print(f"表数量: {len(schema.get('tables', []))}")
        
        for table in schema.get('tables', []):
            table_name = table.get('name', 'unknown')
            columns = table.get('columns', [])
            pk = table.get('primary_key', [])
            fk = table.get('foreign_keys', [])
            
            print(f"\n表: {table_name}")
            print(f"  列数: {len(columns)}")
            print(f"  主键: {pk}")
            print(f"  外键: {len(fk)} 个")
            
            print("  列信息:")
            for col in columns:
                col_name = col.get('name', 'unknown')
                col_type = col.get('type', 'unknown')
                nullable = "可空" if col.get('nullable') else "非空"
                print(f"    - {col_name} ({col_type}, {nullable})")
        
        print("\n" + "=" * 60)
        print("Schema获取成功!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_schema())

