"""
数据库支持验证工具
验证不同数据库类型的支持和配置
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.services.database_adapters import DatabaseAdapterFactory, DatabaseType, DatabaseCapability

logger = logging.getLogger(__name__)


async def test_database_adapter(connection_string: str, tenant_id: str = "test_tenant"):
    """测试数据库适配器"""
    print(f"🧪 测试数据库适配器: {connection_string[:50]}...")

    try:
        # 创建适配器
        adapter = DatabaseAdapterFactory.create_adapter(connection_string, tenant_id)
        print(f"✅ 数据库类型检测: {adapter.db_type}")
        print(f"✅ 数据库方言: {adapter.capability.get_dialect()}")

        # 测试连接
        connection = await adapter.get_connection()
        print("✅ 数据库连接成功")

        # 获取数据库能力
        capability = adapter.capability
        print(f"✅ 支持的功能: {len(capability.features)} 项")
        for feature in capability.features:
            print(f"   - {feature}")

        # 测试基本查询
        test_queries = [
            "SELECT 1 as test_value",
            "SELECT version() as db_version",
            "SELECT current_database() as db_name"
        ]

        for query in test_queries:
            try:
                result = await adapter.execute_query(query)
                if result["success"]:
                    print(f"✅ 测试查询成功: {query[:30]}...")
                else:
                    print(f"⚠️  测试查询失败: {query[:30]}... - {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"⚠️  测试查询异常: {query[:30]}... - {e}")

        # 测试schema获取
        try:
            schema = await adapter.get_schema_info()
            tables_count = len(schema.get("tables", []))
            columns_count = len(schema.get("columns", []))
            print(f"✅ 获取数据库结构: {tables_count} 个表, {columns_count} 个列")
        except Exception as e:
            print(f"⚠️  获取数据库结构失败: {e}")

        # 关闭连接
        await adapter.close_connection(connection)
        print("✅ 数据库连接已关闭")

        return True

    except Exception as e:
        print(f"❌ 数据库适配器测试失败: {e}")
        return False


async def test_database_features():
    """测试数据库功能支持"""
    print("\n🔍 测试数据库功能支持...")

    supported_databases = DatabaseAdapterFactory.get_supported_databases()

    for db_info in supported_databases:
        print(f"\n📊 {db_info['name']} ({db_info['type']})")
        print(f"   状态: {db_info['status']}")
        print(f"   描述: {db_info['description']}")
        print(f"   支持功能: {len(db_info['features'])} 项")

        if db_info['status'] == 'fully_supported':
            capability = DatabaseCapability(db_info['type'])
            for feature in sorted(capability.features):
                print(f"     ✅ {feature}")
        else:
            for feature in sorted(db_info['features']):
                print(f"     🔄 {feature}")


async def test_sql_dialects():
    """测试SQL方言差异"""
    print("\n🔤 测试SQL方言差异...")

    test_cases = [
        {
            "name": "LIMIT查询",
            "type": "limit",
            "params": {"limit": 10, "offset": 20}
        },
        {
            "name": "JSON聚合",
            "type": "json_agg",
            "params": {"column": "data", "alias": "result"}
        },
        {
            "name": "UPSERT操作",
            "type": "upsert",
            "params": {
                "table": "test_table",
                "columns": ["id", "name", "value"],
                "values": [1, "test", 100],
                "conflict_columns": ["id"]
            }
        }
    ]

    databases = [DatabaseType.POSTGRESQL, DatabaseType.MYSQL, DatabaseType.SQLITE]

    for test_case in test_cases:
        print(f"\n📝 {test_case['name']}:")

        for db_type in databases:
            capability = DatabaseCapability(db_type)
            try:
                sql = capability.get_dialect_specific_sql(
                    test_case["type"],
                    **test_case["params"]
                )
                if sql:
                    print(f"   {db_type}: {sql}")
                else:
                    print(f"   {db_type}: 不支持或需要特殊处理")
            except Exception as e:
                print(f"   {db_type}: 生成失败 - {e}")


def validate_connection_string_format(connection_string: str) -> Dict[str, Any]:
    """验证连接字符串格式"""
    result = {
        "valid": False,
        "database_type": None,
        "issues": []
    }

    # PostgreSQL格式检查
    if connection_string.startswith(("postgresql://", "postgresql+asyncpg://")):
        result["database_type"] = "postgresql"
        if "://user:password@host:port/database" not in connection_string and len(connection_string) < 20:
            result["issues"].append("连接字符串可能不完整")

        result["valid"] = True

    # MySQL格式检查
    elif connection_string.startswith("mysql://"):
        result["database_type"] = "mysql"
        if "://user:password@host:port/database" not in connection_string and len(connection_string) < 15:
            result["issues"].append("连接字符串可能不完整")

        result["valid"] = True

    # SQLite格式检查
    elif connection_string.startswith("sqlite://"):
        result["database_type"] = "sqlite"
        if len(connection_string) <= len("sqlite://"):
            result["issues"].append("SQLite路径为空")

        result["valid"] = True

    else:
        result["issues"].append("不支持的数据库类型或格式")

    return result


async def test_connection_validation():
    """测试连接字符串验证"""
    print("\n🔗 测试连接字符串验证...")

    test_strings = [
        "postgresql://user:pass@localhost:5432/mydb",
        "postgresql+asyncpg://user:pass@localhost:5432/mydb",
        "mysql://user:pass@localhost:3306/mydb",
        "sqlite:///path/to/database.db",
        "invalid://format",
        "postgresql://",  # 不完整
        ""  # 空字符串
    ]

    for conn_str in test_strings:
        if conn_str:
            print(f"\n📋 测试: {conn_str}")
        else:
            print(f"\n📋 测试: <空字符串>")

        validation = validate_connection_string_format(conn_str)
        status = "✅ 有效" if validation["valid"] else "❌ 无效"
        print(f"   状态: {status}")
        print(f"   数据库类型: {validation.get('database_type', '未知')}")

        if validation["issues"]:
            for issue in validation["issues"]:
                print(f"   ⚠️  {issue}")


async def main():
    """主函数"""
    print("🔍 开始数据库支持验证...\n")

    # 1. 测试数据库功能支持
    await test_database_features()

    # 2. 测试SQL方言
    await test_sql_dialects()

    # 3. 测试连接字符串验证
    await test_connection_validation()

    # 4. 测试实际数据库连接（如果提供了连接字符串）
    test_connections = [
        # 可以添加测试用的连接字符串
        # "postgresql://user:pass@localhost:5432/testdb"
    ]

    if test_connections:
        print(f"\n🧪 测试实际数据库连接 ({len(test_connections)} 个)...")
        success_count = 0

        for conn_str in test_connections:
            if await test_database_adapter(conn_str):
                success_count += 1

        print(f"\n📊 连接测试结果: {success_count}/{len(test_connections)} 成功")

    print("\n🎉 数据库支持验证完成！")

    # 输出支持的数据库总结
    supported = DatabaseAdapterFactory.get_supported_databases()
    fully_supported = [db for db in supported if db['status'] == 'fully_supported']
    planned = [db for db in supported if db['status'] == 'planned']

    print(f"\n📋 支持总结:")
    print(f"   完全支持: {len(fully_supported)} 个")
    for db in fully_supported:
        print(f"     - {db['name']} ({db['type']})")

    print(f"   计划支持: {len(planned)} 个")
    for db in planned:
        print(f"     - {db['name']} ({db['type']})")


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行异步验证
    asyncio.run(main())