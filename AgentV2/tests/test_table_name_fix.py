# -*- coding: utf-8 -*-
"""
测试：AI 假设表名 bug 修复验证
==============================

测试目标：
1. 验证 agent_factory_v2.py 的 prompt 包含正确的 list_tables() 规则
2. 验证 reflection_node.py 能检测假设表名错误
3. 验证表名缓存机制正常工作

版本: 1.0.0
"""

import sys
import os
from pathlib import Path

# 添加 AgentV2 到路径
agentv2_path = Path(__file__).resolve().parent.parent
if str(agentv2_path) not in sys.path:
    sys.path.insert(0, str(agentv2_path))

import unittest


class TestTableNameFix(unittest.TestCase):
    """测试表名修复功能"""

    def setUp(self):
        """测试前准备"""
        self.tenant_id = "test_tenant"
        self.connection_id = "test_connection"

    def test_agent_factory_prompt_has_list_tables_rule(self):
        """测试 agent_factory_v2.py 的 prompt 包含正确的 list_tables() 规则"""
        from AgentV2.core.agent_factory_v2 import AgentFactory

        factory = AgentFactory()
        tool_names = ["list_tables", "get_schema", "execute_query"]

        prompt = factory._build_system_prompt(
            tool_names=tool_names,
            connection_id=self.connection_id,
            tenant_id=self.tenant_id
        )

        # 验证 prompt 包含关键规则
        self.assertIn("list_tables()", prompt, "Prompt should include list_tables()")
        self.assertIn("必须按以下顺序执行", prompt, "Prompt should include execution order")
        self.assertIn("禁止猜测或假设表名", prompt, "Prompt should prohibit guessing table names")
        self.assertIn("禁止跳过list_tables()", prompt, "Prompt should prohibit skipping list_tables()")

        # 验证 prompt 不包含错误规则
        self.assertNotIn("DO NOT use list_tables", prompt, "Prompt should not contain 'DO NOT use list_tables'")
        self.assertNotIn("MUST use execute_query", prompt, "Prompt should not contain 'MUST use execute_query'")

        print("[OK] Test passed: agent_factory_v2.py prompt has correct list_tables() rule")

    def test_reflection_node_detects_assumed_table_name(self):
        """测试 reflection_node.py 能检测假设表名错误"""
        from AgentV2.nodes.reflection_node import ReflectionNode, ErrorCategory

        node = ReflectionNode()

        # 模拟 "sales" 表不存在的错误
        error_content = "ERROR: relation 'sales' does not exist"
        result = node._check_assumed_table_name(error_content)

        self.assertIsNotNone(result, "Should detect assumed table name error")
        self.assertEqual(result.error_category, ErrorCategory.ASSUMED_TABLE_NAME)
        self.assertIn("sales", result.error_message)
        self.assertIn("list_tables()", result.fix_suggestion)

        print("[OK] Test passed: reflection_node.py detects assumed table name error")

    def test_reflection_node_ignores_non_assumed_tables(self):
        """测试 reflection_node.py 忽略非假设表名的错误"""
        from AgentV2.nodes.reflection_node import ReflectionNode

        node = ReflectionNode()

        # 模拟一个非假设表名的错误
        error_content = "ERROR: relation '订单表' does not exist"
        result = node._check_assumed_table_name(error_content)

        # 中文的"订单表"不在常见假设表名列表中，所以不应该被检测为假设表名错误
        self.assertIsNone(result, "Should not detect as assumed table name error")

        print("[OK] Test passed: reflection_node.py ignores non-assumed table name errors")

    def test_table_cache_middleware(self):
        """测试表名缓存中间件"""
        from AgentV2.middleware.table_cache_middleware import TableCacheMiddleware

        # 测试设置和获取缓存
        table_names = ["订单表", "用户表", "产品表"]
        TableCacheMiddleware.set_cached_tables(
            tenant_id=self.tenant_id,
            table_names=table_names,
            connection_id=self.connection_id
        )

        cached = TableCacheMiddleware.get_cached_tables(
            tenant_id=self.tenant_id,
            connection_id=self.connection_id
        )

        self.assertEqual(cached, table_names, "Cached table names should match")

        # 测试清除缓存
        TableCacheMiddleware.clear_cache(
            tenant_id=self.tenant_id,
            connection_id=self.connection_id
        )

        cached_after_clear = TableCacheMiddleware.get_cached_tables(
            tenant_id=self.tenant_id,
            connection_id=self.connection_id
        )

        self.assertIsNone(cached_after_clear, "Cache should be empty after clear")

        print("[OK] Test passed: table cache middleware works correctly")

    def test_enhanced_prompt_with_cached_tables(self):
        """测试带缓存表名的增强 prompt"""
        from AgentV2.core.agent_factory_v2 import AgentFactory

        table_names = ["订单表", "用户表", "产品表"]

        # 设置缓存
        AgentFactory.set_cached_table_names(
            tenant_id=self.tenant_id,
            table_names=table_names,
            connection_id=self.connection_id
        )

        base_prompt = "You are a data analyst."
        enhanced_prompt = AgentFactory.get_enhanced_prompt_with_cached_tables(
            base_prompt=base_prompt,
            tenant_id=self.tenant_id,
            connection_id=self.connection_id
        )

        # 验证增强后的 prompt 包含缓存信息
        self.assertIn("已缓存的表名列表", enhanced_prompt)
        self.assertIn("订单表", enhanced_prompt)
        self.assertIn("用户表", enhanced_prompt)
        self.assertIn("产品表", enhanced_prompt)

        print("[OK] Test passed: enhanced prompt with cached tables works correctly")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Test: AI Assumed Table Name Bug Fix Verification")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTableNameFix)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("[SUCCESS] All tests passed!")
    else:
        print("[FAILED] Some tests failed")
        if result.failures:
            print(f"Failures: {len(result.failures)}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
