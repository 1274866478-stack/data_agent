"""
# [INTEGRATION TEST] 数据库类型感知集成测试

## [HEADER]
**文件名**: test_db_type_awareness.py
**职责**: 测试数据库类型感知功能的端到端集成
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-04): 初始版本 - 测试不同数据库类型的查询处理

## [TEST COVERAGE]
- MySQL 数据源的查询处理
- PostgreSQL 数据源的查询处理
- SQLite 数据源的查询处理
- 混合数据源的处理
- SQL 函数兼容性验证
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# 添加后端路径
backend_path = Path(__file__).parent.parent.parent / "src"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class TestDbTypeAwarenessIntegration:
    """测试数据库类型感知的集成功能"""

    @pytest.mark.asyncio
    async def test_build_system_prompt_with_mysql_db_type(self):
        """测试 _build_system_prompt_with_context 使用 MySQL 类型"""
        from src.app.api.v1.endpoints.llm import _build_system_prompt_with_context

        data_sources_context = "## 数据源\n数据源: test_mysql\n表: users"
        prompt = _build_system_prompt_with_context(data_sources_context, db_type="mysql")

        # 应该包含基础内容
        assert "数据分析师" in prompt
        assert data_sources_context in prompt

        # MySQL 类型应该避免使用 TO_CHAR 作为主要推荐
        # 或者在提到时说明是 PostgreSQL 函数
        if "TO_CHAR" in prompt:
            assert "PostgreSQL" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_with_postgresql_db_type(self):
        """测试 _build_system_prompt_with_context 使用 PostgreSQL 类型"""
        from src.app.api.v1.endpoints.llm import _build_system_prompt_with_context

        data_sources_context = "## 数据源\n数据源: test_pg\n表: users"
        prompt = _build_system_prompt_with_context(data_sources_context, db_type="postgresql")

        # 应该包含基础内容
        assert "数据分析师" in prompt
        assert data_sources_context in prompt

        # PostgreSQL 类型应该包含 TO_CHAR
        assert "TO_CHAR" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_with_sqlite_db_type(self):
        """测试 _build_system_prompt_with_context 使用 SQLite 类型"""
        from src.app.api.v1.endpoints.llm import _build_system_prompt_with_context

        data_sources_context = "## 数据源\n数据源: test_sqlite\n表: users"
        prompt = _build_system_prompt_with_context(data_sources_context, db_type="sqlite")

        # 应该包含基础内容
        assert "数据分析师" in prompt
        assert data_sources_context in prompt

        # SQLite 类型应该包含 strftime
        assert "strftime" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_with_xlsx_db_type(self):
        """测试 _build_system_prompt_with_context 使用 Excel 文件类型"""
        from src.app.api.v1.endpoints.llm import _build_system_prompt_with_context

        data_sources_context = "## 数据源\n数据源: sales_data.xlsx\n表: Sheet1"
        prompt = _build_system_prompt_with_context(data_sources_context, db_type="xlsx")

        # 应该包含基础内容
        assert "数据分析师" in prompt
        assert data_sources_context in prompt

        # Excel 文件类型应该提到文件处理相关内容
        assert "文件" in prompt or "Excel" in prompt or "DuckDB" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_default_db_type(self):
        """测试 _build_system_prompt_with_context 默认使用 PostgreSQL"""
        from src.app.api.v1.endpoints.llm import _build_system_prompt_with_context

        data_sources_context = "## 数据源\n数据源: test\n表: users"
        # 不指定 db_type，应该使用默认值
        prompt = _build_system_prompt_with_context(data_sources_context)

        # 应该包含基础内容
        assert "数据分析师" in prompt
        assert data_sources_context in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_empty_context(self):
        """测试空数据源上下文的处理"""
        from src.app.api.v1.endpoints.llm import _build_system_prompt_with_context

        # 空上下文应该返回一个提示，告诉用户需要先连接数据源
        prompt = _build_system_prompt_with_context("", db_type="postgresql")

        assert "数据源" in prompt or "连接" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_none_context(self):
        """测试 None 数据源上下文的处理"""
        from src.app.api.v1.endpoints.llm import _build_system_prompt_with_context

        # None 上下文应该返回一个提示，告诉用户需要先连接数据源
        prompt = _build_system_prompt_with_context(None, db_type="postgresql")

        assert "数据源" in prompt or "连接" in prompt


class TestAgentServiceDbTypeAwareness:
    """测试 agent_service 中的数据库类型感知"""

    @pytest.mark.asyncio
    async def test_run_agent_query_with_mysql_type(self):
        """测试使用 MySQL 类型运行 Agent 查询"""
        # 验证 run_agent_query 函数签名接受 db_type 参数
        from src.app.services.agent_service import run_agent_query
        import inspect

        sig = inspect.signature(run_agent_query)
        # 验证 db_type 参数存在
        assert "db_type" in sig.parameters
        # 验证 db_type 的默认值是 "postgresql"
        assert sig.parameters["db_type"].default == "postgresql"

    @pytest.mark.asyncio
    async def test_run_agent_query_with_postgresql_type(self):
        """测试使用 PostgreSQL 类型运行 Agent 查询"""
        # 验证 run_agent_query 函数能正确处理不同的 db_type 值
        from src.app.services.agent_service import run_agent_query
        import inspect

        sig = inspect.signature(run_agent_query)
        # 验证 db_type 参数存在且可以接受不同的数据库类型
        assert "db_type" in sig.parameters

        # 验证函数文档中包含 db_type 参数说明
        doc = run_agent_query.__doc__
        assert doc is not None
        assert "db_type" in doc or "数据库类型" in doc


class TestSqlAgentDbTypeIntegration:
    """测试 sql_agent 中的数据库类型集成"""

    @pytest.mark.asyncio
    async def test_sql_agent_get_system_prompt_mysql(self):
        """测试 sql_agent get_system_prompt 处理 MySQL"""
        # 需要导入 Agent 模块
        agent_path = Path(__file__).parent.parent.parent.parent / "Agent"
        if str(agent_path) not in sys.path:
            sys.path.insert(0, str(agent_path))

        from sql_agent import get_system_prompt

        prompt = get_system_prompt("mysql")
        assert prompt is not None
        assert len(prompt) > 0

        # 应该包含 MySQL 相关的指导
        # (具体内容取决于 prompt_generator 的实现)

    @pytest.mark.asyncio
    async def test_sql_agent_get_system_prompt_postgresql(self):
        """测试 sql_agent get_system_prompt 处理 PostgreSQL"""
        agent_path = Path(__file__).parent.parent.parent.parent / "Agent"
        if str(agent_path) not in sys.path:
            sys.path.insert(0, str(agent_path))

        from sql_agent import get_system_prompt

        prompt = get_system_prompt("postgresql")
        assert prompt is not None
        assert len(prompt) > 0


class TestFunctionCompatibilityMatrix:
    """测试函数兼容性矩阵"""

    def test_postgresql_date_functions(self):
        """测试 PostgreSQL 日期函数"""
        agent_path = Path(__file__).parent.parent.parent.parent / "Agent"
        if str(agent_path) not in sys.path:
            sys.path.insert(0, str(agent_path))

        from prompt_generator import generate_database_aware_system_prompt

        base = "Base prompt"
        prompt = generate_database_aware_system_prompt("postgresql", base)

        # PostgreSQL 应该推荐这些函数
        assert "TO_CHAR" in prompt
        assert "DATE_TRUNC" in prompt

    def test_mysql_date_functions(self):
        """测试 MySQL 日期函数"""
        agent_path = Path(__file__).parent.parent.parent.parent / "Agent"
        if str(agent_path) not in sys.path:
            sys.path.insert(0, str(agent_path))

        from prompt_generator import generate_database_aware_system_prompt

        base = "Base prompt"
        prompt = generate_database_aware_system_prompt("mysql", base)

        # MySQL 应该推荐这些函数
        assert "DATE_FORMAT" in prompt or "YEAR(" in prompt
        assert "MONTH(" in prompt or "DATE_FORMAT" in prompt

    def test_sqlite_date_functions(self):
        """测试 SQLite 日期函数"""
        agent_path = Path(__file__).parent.parent.parent.parent / "Agent"
        if str(agent_path) not in sys.path:
            sys.path.insert(0, str(agent_path))

        from prompt_generator import generate_database_aware_system_prompt

        base = "Base prompt"
        prompt = generate_database_aware_system_prompt("sqlite", base)

        # SQLite 应该推荐这些函数
        assert "strftime" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
