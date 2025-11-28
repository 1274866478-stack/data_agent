"""
MySQL 数据库适配器测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from src.app.services.database_interface import (
    MySQLAdapter,
    DatabaseType,
    SchemaInfo,
    QueryResult,
    QueryPlan,
    ColumnInfo,
    TableInfo
)


class TestMySQLAdapter:
    """MySQL适配器测试类"""

    @pytest.fixture
    def mysql_adapter(self):
        """创建MySQL适配器实例"""
        return MySQLAdapter("mysql://user:password@localhost:3306/testdb")

    @pytest.fixture
    def mock_pool(self):
        """创建Mock连接池"""
        pool = AsyncMock()
        conn = AsyncMock()
        cursor = AsyncMock()

        # 设置cursor的description属性
        cursor.description = [('id',), ('name',), ('email',)]
        cursor.rowcount = 1

        # 设置context manager
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)

        # 设置cursor方法
        conn.cursor = MagicMock(return_value=cursor)

        # 设置pool.acquire
        pool.acquire = MagicMock(return_value=conn)

        return pool, conn, cursor

    def test_init(self, mysql_adapter):
        """测试MySQL适配器初始化"""
        assert mysql_adapter.connection_string == "mysql://user:password@localhost:3306/testdb"
        assert mysql_adapter.pool_size == 10
        assert mysql_adapter._pool is None

    def test_get_database_type(self, mysql_adapter):
        """测试获取数据库类型"""
        assert mysql_adapter.get_database_type() == DatabaseType.MYSQL

    @pytest.mark.asyncio
    async def test_connect_success(self, mysql_adapter):
        """测试成功连接MySQL"""
        mock_pool = AsyncMock()

        with patch.dict('sys.modules', {'aiomysql': MagicMock()}):
            import sys
            sys.modules['aiomysql'].create_pool = AsyncMock(return_value=mock_pool)

            result = await mysql_adapter.connect()

            assert result is True
            assert mysql_adapter._pool is mock_pool

    @pytest.mark.asyncio
    async def test_connect_failure(self, mysql_adapter):
        """测试连接MySQL失败"""
        with patch.dict('sys.modules', {'aiomysql': MagicMock()}):
            import sys
            sys.modules['aiomysql'].create_pool = AsyncMock(side_effect=Exception("Connection failed"))

            result = await mysql_adapter.connect()

            assert result is False
            assert mysql_adapter._pool is None

    @pytest.mark.asyncio
    async def test_disconnect(self, mysql_adapter, mock_pool):
        """测试断开MySQL连接"""
        pool, _, _ = mock_pool
        mysql_adapter._pool = pool

        await mysql_adapter.disconnect()

        pool.close.assert_called_once()
        pool.wait_closed.assert_called_once()
        assert mysql_adapter._pool is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mysql_adapter, mock_pool):
        """测试连接测试成功"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=(1,))

        result = await mysql_adapter.test_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_not_connected(self, mysql_adapter):
        """测试未连接时的连接测试"""
        # 测试当_pool为None时会调用connect
        with patch.object(mysql_adapter, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            # 保持_pool为None，触发connect调用
            mysql_adapter._pool = None

            result = await mysql_adapter.test_connection()

            # 由于_pool是None，应该调用connect
            mock_connect.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_execute_query_select(self, mysql_adapter, mock_pool):
        """测试执行SELECT查询"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[
            {'id': 1, 'name': 'Test', 'email': 'test@example.com'}
        ])

        result = await mysql_adapter.execute_query("SELECT * FROM users")

        assert isinstance(result, QueryResult)
        assert result.row_count == 1
        assert len(result.data) == 1
        assert result.data[0]['name'] == 'Test'

    @pytest.mark.asyncio
    async def test_execute_query_not_connected(self, mysql_adapter):
        """测试未连接时执行查询"""
        with pytest.raises(Exception, match="数据库未连接"):
            await mysql_adapter.execute_query("SELECT * FROM users")

    @pytest.mark.asyncio
    async def test_validate_query_success(self, mysql_adapter, mock_pool):
        """测试验证SQL查询成功"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()

        is_valid, error = await mysql_adapter.validate_query("SELECT * FROM users")

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_query_failure(self, mysql_adapter, mock_pool):
        """测试验证SQL查询失败"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock(side_effect=Exception("Syntax error"))

        is_valid, error = await mysql_adapter.validate_query("SELECT * FORM users")

        assert is_valid is False
        assert "Syntax error" in error

    @pytest.mark.asyncio
    async def test_get_table_sample(self, mysql_adapter, mock_pool):
        """测试获取表样本数据"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[
            {'id': 1, 'name': 'User1'},
            {'id': 2, 'name': 'User2'}
        ])

        result = await mysql_adapter.get_table_sample("users", limit=2)

        assert len(result) == 2
        assert result[0]['name'] == 'User1'
        assert result[1]['name'] == 'User2'

    @pytest.mark.asyncio
    async def test_get_table_sample_not_connected(self, mysql_adapter):
        """测试未连接时获取表样本"""
        result = await mysql_adapter.get_table_sample("users")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_table_statistics(self, mysql_adapter, mock_pool):
        """测试获取表统计信息"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        # Mock table stats query
        cursor.execute = AsyncMock()
        cursor.fetchone = AsyncMock(return_value={
            'table_name': 'users',
            'table_rows': 100,
            'data_length': 16384,
            'index_length': 8192,
            'avg_row_length': 163,
            'auto_increment': 101,
            'create_time': datetime.now(),
            'update_time': datetime.now()
        })
        cursor.fetchall = AsyncMock(return_value=[
            {'column_name': 'id', 'index_name': 'PRIMARY', 'seq_in_index': 1, 'cardinality': 100}
        ])

        result = await mysql_adapter.get_table_statistics("users")

        assert result['table_name'] == 'users'
        assert 'size_info' in result
        assert 'table_stats' in result

    def test_format_bytes(self, mysql_adapter):
        """测试字节格式化"""
        assert mysql_adapter._format_bytes(0) == "0.00 B"
        assert mysql_adapter._format_bytes(1024) == "1.00 KB"
        assert mysql_adapter._format_bytes(1024 * 1024) == "1.00 MB"
        assert mysql_adapter._format_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert mysql_adapter._format_bytes(None) == "0 B"

    @pytest.mark.asyncio
    async def test_explain_query(self, mysql_adapter, mock_pool):
        """测试获取查询执行计划"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()
        cursor.fetchone = AsyncMock(return_value={
            'EXPLAIN': '{"query_block": {"cost_info": {"query_cost": "1.00"}}}'
        })

        result = await mysql_adapter.explain_query("SELECT * FROM users")

        assert isinstance(result, QueryPlan)
        assert result.query == "SELECT * FROM users"
        assert result.plan_id.startswith("mysql_plan_")

    @pytest.mark.asyncio
    async def test_execute_query_with_params(self, mysql_adapter, mock_pool):
        """测试带参数执行查询"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[
            {'id': 1, 'name': 'Test'}
        ])

        result = await mysql_adapter.execute_query(
            "SELECT * FROM users WHERE id = %s",
            params={'id': 1}
        )

        assert isinstance(result, QueryResult)
        assert result.row_count == 1

    @pytest.mark.asyncio
    async def test_execute_query_empty_result(self, mysql_adapter, mock_pool):
        """测试执行查询返回空结果"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])

        result = await mysql_adapter.execute_query("SELECT * FROM users WHERE 1=0")

        assert isinstance(result, QueryResult)
        assert result.row_count == 0
        assert result.data == []

    @pytest.mark.asyncio
    async def test_execute_non_select_query(self, mysql_adapter, mock_pool):
        """测试执行非SELECT查询"""
        pool, conn, cursor = mock_pool
        mysql_adapter._pool = pool

        cursor.execute = AsyncMock()
        cursor.rowcount = 5

        result = await mysql_adapter.execute_query("UPDATE users SET active = 1")

        assert isinstance(result, QueryResult)
        assert result.affected_rows == 5

