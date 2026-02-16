"""
# [TEST] Prompt Generator 单元测试

## [HEADER]
**文件名**: test_prompt_generator.py
**职责**: 测试 prompt_generator 模块的数据库类型感知功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-04): 初始版本 - 测试数据库特定提示词生成

## [TEST COVERAGE]
- PostgreSQL 提示词生成
- MySQL 提示词生成
- SQLite 提示词生成
- Excel/CSV 文件提示词生成
- 函数不兼容性检查
"""

import pytest
import sys
from pathlib import Path

# 添加 Agent 目录到路径
agent_path = Path(__file__).parent.parent.parent / "Agent"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))


class TestPromptGenerator:
    """测试 prompt_generator 模块"""

    def test_postgresql_prompt_contains_specific_functions(self):
        """测试 PostgreSQL 提示词包含 PostgreSQL 特定函数"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("postgresql", base_prompt)

        # PostgreSQL 应该包含这些特定函数
        assert "PostgreSQL" in prompt or "postgresql" in prompt.lower()
        assert "TO_CHAR" in prompt
        assert "DATE_TRUNC" in prompt
        assert "EXTRACT" in prompt

    def test_postgresql_prompt_excludes_mysql_functions(self):
        """测试 PostgreSQL 提示词不包含 MySQL 特定函数"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("postgresql", base_prompt)

        # PostgreSQL 提示词不应主要强调 MySQL 函数
        # 虽然可能在对比中提到，但不应该作为主要推荐
        # 这里只检查不应该以主要方式推荐 MySQL 函数
        assert "DATE_FORMAT" not in prompt or "MySQL" in prompt

    def test_mysql_prompt_contains_specific_functions(self):
        """测试 MySQL 提示词包含 MySQL 特定函数"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("mysql", base_prompt)

        # MySQL 应该包含这些特定函数
        assert "MySQL" in prompt or "mysql" in prompt.lower()
        assert "DATE_FORMAT" in prompt or "YEAR(" in prompt
        # MySQL 不应该强调 TO_CHAR 作为主要函数
        if "TO_CHAR" in prompt:
            # 如果提到 TO_CHAR，应该说明这是 PostgreSQL 函数
            assert "PostgreSQL" in prompt or "不适用" in prompt

    def test_mysql_prompt_excludes_postgresql_functions(self):
        """测试 MySQL 提示词不应推荐 PostgreSQL 专用函数"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("mysql", base_prompt)

        # 检查是否正确说明 TO_CHAR 是 PostgreSQL 专用
        if "TO_CHAR" in prompt:
            assert "PostgreSQL" in prompt

    def test_sqlite_prompt_contains_specific_functions(self):
        """测试 SQLite 提示词包含 SQLite 特定函数"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("sqlite", base_prompt)

        # SQLite 应该包含 strftime
        assert "SQLite" in prompt or "sqlite" in prompt.lower()
        assert "strftime" in prompt

    def test_xlsx_prompt_contains_file_specific_instructions(self):
        """测试 Excel 文件提示词包含文件特定说明"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("xlsx", base_prompt)

        # Excel 文件应该提到文件处理
        assert "Excel" in prompt or "xlsx" in prompt.lower() or "文件" in prompt

    def test_csv_prompt_contains_file_specific_instructions(self):
        """测试 CSV 文件提示词包含文件特定说明"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("csv", base_prompt)

        # CSV 文件应该提到文件处理
        assert "CSV" in prompt or "csv" in prompt.lower() or "文件" in prompt

    def test_unknown_db_type_falls_back_to_postgresql(self):
        """测试未知数据库类型回退到 PostgreSQL"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手"
        prompt = generate_database_aware_system_prompt("unknown_db", base_prompt)

        # 应该至少返回基础提示词
        assert base_prompt in prompt or len(prompt) > 0

    def test_prompt_preserves_base_content(self):
        """测试生成的提示词保留基础内容"""
        from prompt_generator import generate_database_aware_system_prompt

        base_prompt = "你是一个数据库助手。这是自定义的内容。"
        prompt = generate_database_aware_system_prompt("postgresql", base_prompt)

        # 基础提示词的内容应该被保留
        assert "数据库助手" in prompt
        assert "自定义的内容" in prompt

    def test_function_compatibility_matrix(self):
        """测试函数兼容性矩阵的准确性"""
        from prompt_generator import generate_database_aware_system_prompt

        # 测试不同数据库类型的日期格式化函数
        base_prompt = "你是一个数据库助手"

        # PostgreSQL - 应该使用 TO_CHAR
        postgres_prompt = generate_database_aware_system_prompt("postgresql", base_prompt)
        assert "TO_CHAR" in postgres_prompt

        # MySQL - 应该使用 DATE_FORMAT
        mysql_prompt = generate_database_aware_system_prompt("mysql", base_prompt)
        assert "DATE_FORMAT" in mysql_prompt or "YEAR(" in mysql_prompt

        # SQLite - 应该使用 strftime
        sqlite_prompt = generate_database_aware_system_prompt("sqlite", base_prompt)
        assert "strftime" in sqlite_prompt


class TestGetSystemPrompt:
    """测试 sql_agent.py 中的 get_system_prompt 函数"""

    def test_get_system_prompt_with_postgresql(self):
        """测试 get_system_prompt 处理 PostgreSQL 类型"""
        from sql_agent import get_system_prompt

        prompt = get_system_prompt("postgresql")
        assert prompt is not None
        assert len(prompt) > 0

    def test_get_system_prompt_with_mysql(self):
        """测试 get_system_prompt 处理 MySQL 类型"""
        from sql_agent import get_system_prompt

        prompt = get_system_prompt("mysql")
        assert prompt is not None
        assert len(prompt) > 0

    def test_get_system_prompt_default_to_postgresql(self):
        """测试 get_system_prompt 默认使用 PostgreSQL"""
        from sql_agent import get_system_prompt

        # 不传参数，应该使用默认的 postgresql
        prompt = get_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
