"""
[HEADER]
数据库支持验证工具 - Database Support Validator
验证不同数据库类型的适配器支持、方言差异和连接能力

[MODULE]
模块类型: 配置验证脚本 (Standalone Script)
所属功能: 开发工具与数据库适配器验证
技术栈: Python 3.8+, asyncio, logging, typing

[INPUT]
- 命令行参数: 无
- 配置来源:
  - src.services.database_adapters.DatabaseAdapterFactory - 适配器工厂
  - src.services.database_adapters.DatabaseType - 数据库类型枚举
  - src.services.database_adapters.DatabaseCapability - 数据库能力
- 测试连接: 可在代码中添加 test_connections 列表进行实际连接测试
- 测试用例: 内置SQL方言测试用例 (LIMIT, JSON_AGG, UPSERT)

[OUTPUT]
- 控制台输出:
  - 支持的数据库列表 (状态、描述、功能)
  - SQL方言差异对比
  - 连接字符串验证结果
  - 实际数据库连接测试 (如果提供)
  - 支持总结统计
- 退出码:
  - 0: 验证成功
  - 1: 验证失败 (脚本默认不检查测试结果)
- 验证项目:
  1. 数据库功能支持列表
  2. SQL方言差异 (LIMIT, JSON_AGG, UPSERT等)
  3. 连接字符串格式验证
  4. 实际数据库连接 (可选)

[LINK]
- 依赖模块:
  - src.services.database_adapters - 数据库适配器系统
  - src.services.database_adapters.postgresql_adapter - PostgreSQL适配器
  - src.services.database_adapters.mysql_adapter - MySQL适配器
  - src.services.database_adapters.sqlite_adapter - SQLite适配器
- 关联脚本:
  - scripts/validate_zhipu_config.py - 智谱AI配置验证
  - scripts/validate_cache_config.py - 缓存配置验证
- 文档参考:
  - docs/database/database-support.md - 数据库支持文档

[POS]
- 文件路径: backend/scripts/validate_database_support.py
- 执行方式:
  - 直接运行: python scripts/validate_database_support.py
  - Docker: docker-compose exec backend python scripts/validate_database_support.py
- 使用场景:
  - 验证新增数据库类型的支持
  - SQL方言差异对比学习
  - 连接字符串格式验证
  - CI/CD流程中的数据库兼容性检查

[PROTOCOL]
- 执行流程:
  1. 测试数据库功能支持:
     - 获取所有支持的数据库类型
     - 显示每个数据库的状态和功能列表
  2. 测试SQL方言差异:
     - LIMIT查询: PostgreSQL/MySQL/SQLite对比
     - JSON聚合: JSON_AGG实现差异
     - UPSERT操作: INSERT ON CONFLICT vs ON DUPLICATE KEY UPDATE
  3. 测试连接字符串验证:
     - 测试有效格式 (postgresql://, mysql://, sqlite://)
     - 测试无效格式 (不完整、不支持的类型)
  4. 测试实际连接 (可选):
     - 如果提供 test_connections, 执行实际连接测试
     - 测试连接、schema获取、基本查询
- 验证标准:
  - 完全支持 (fully_supported): 所有功能可用
  - 计划支持 (planned): 部分功能或开发中
- 连接字符串规则:
  - PostgreSQL: postgresql://或postgresql+asyncpg://开头
  - MySQL: mysql://开头
  - SQLite: sqlite://开头, 路径不能为空
- 错误处理:
  - 捕获所有异常并记录
  - SQL生成失败: 显示"不支持或需要特殊处理"

[EXAMPLES]
- 连接字符串示例:
  - PostgreSQL: postgresql://user:pass@localhost:5432/mydb
  - MySQL: mysql://user:pass@localhost:3306/mydb
  - SQLite: sqlite:///path/to/database.db
- SQL方言输出示例:
  - LIMIT查询:
    - PostgreSQL: SELECT ... LIMIT 10 OFFSET 20
    - MySQL: SELECT ... LIMIT 20, 10
    - SQLite: SELECT ... LIMIT 10 OFFSET 20
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