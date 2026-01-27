# -*- coding: utf-8 -*-
"""
Agent 提示词 A/B 测试脚本
=====================================

用于对比极简版提示词与原版提示词的效果差异。

测试指标：
- Token 消耗
- 响应时间
- 回答成功率
- 循环次数
- SQL 正确性

使用方法:
    python AgentV2/tests/test_prompt_comparison.py

作者: BMad Master
版本: 1.0.0
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from dataclasses import dataclass


# ============================================================================
# 测试配置
# ============================================================================

# 测试问题集 - 覆盖常见查询场景
TEST_QUESTIONS = [
    # 基础查询
    "数据库有哪些表？",
    "Orders 表的结构是什么？",

    # 简单统计
    "Orders 表有多少条记录？",
    "最近30天的销售额是多少？",

    # 聚合分析
    "各城市的客户分布占比？",
    "每月的订单数量趋势？",

    # 复杂查询
    "销售额排名前3的产品有哪些？",
    "平均订单金额是多少？",
]


@dataclass
class TestResult:
    """单次测试结果"""
    question: str
    prompt_type: str  # "minimal" or "full"
    success: bool
    answer_length: int
    response_time: float
    token_count: int
    sql_query: str
    error_message: str = ""


# ============================================================================
# 测试执行器
# ============================================================================

class PromptComparisonTester:
    """提示词对比测试器"""

    def __init__(self):
        self.results: List[TestResult] = []

    async def test_prompt(
        self,
        question: str,
        prompt_type: str,
        agent_runner
    ) -> TestResult:
        """
        测试单个问题

        Args:
            question: 测试问题
            prompt_type: 提示词类型 ("minimal" or "full")
            agent_runner: Agent 运行器函数

        Returns:
            测试结果
        """
        start_time = time.time()

        try:
            # 调用 Agent
            result = await agent_runner(
                question,
                simplified=(prompt_type == "minimal"),
                verbose=False
            )

            elapsed = time.time() - start_time

            return TestResult(
                question=question,
                prompt_type=prompt_type,
                success=result.get("success", True),
                answer_length=len(result.get("answer", "")),
                response_time=elapsed,
                token_count=result.get("token_count", 0),
                sql_query=result.get("sql", ""),
                error_message=result.get("error", "")
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return TestResult(
                question=question,
                prompt_type=prompt_type,
                success=False,
                answer_length=0,
                response_time=elapsed,
                token_count=0,
                sql_query="",
                error_message=str(e)
            )

    async def run_comparison(self, agent_runner) -> Dict[str, Any]:
        """
        运行完整对比测试

        Args:
            agent_runner: Agent 运行器函数

        Returns:
            汇总统计结果
        """
        self.results = []

        print("=" * 70)
        print("Agent 提示词 A/B 测试")
        print("=" * 70)

        for i, question in enumerate(TEST_QUESTIONS, 1):
            print(f"\n[{i}/{len(TEST_QUESTIONS)}] 测试问题: {question}")
            print("-" * 70)

            # 测试极简版
            print("  测试极简版提示词...")
            minimal_result = await self.test_prompt(
                question, "minimal", agent_runner
            )
            self.results.append(minimal_result)
            print(f"    成功: {minimal_result.success}, "
                  f"耗时: {minimal_result.response_time:.2f}s, "
                  f"Token: {minimal_result.token_count}")

            # 测试完整版
            print("  测试完整版提示词...")
            full_result = await self.test_prompt(
                question, "full", agent_runner
            )
            self.results.append(full_result)
            print(f"    成功: {full_result.success}, "
                  f"耗时: {full_result.response_time:.2f}s, "
                  f"Token: {full_result.token_count}")

        return self._generate_summary()

    def _generate_summary(self) -> Dict[str, Any]:
        """生成测试摘要"""
        minimal_results = [r for r in self.results if r.prompt_type == "minimal"]
        full_results = [r for r in self.results if r.prompt_type == "full"]

        def calc_stats(results: List[TestResult]) -> Dict[str, Any]:
            success_rate = sum(1 for r in results if r.success) / len(results) * 100
            avg_time = sum(r.response_time for r in results) / len(results)
            avg_tokens = sum(r.token_count for r in results) / len(results)
            avg_answer_length = sum(r.answer_length for r in results) / len(results)

            return {
                "success_rate": success_rate,
                "avg_response_time": avg_time,
                "avg_tokens": avg_tokens,
                "avg_answer_length": avg_answer_length,
                "total_tests": len(results)
            }

        minimal_stats = calc_stats(minimal_results)
        full_stats = calc_stats(full_results)

        # 计算改善百分比
        token_improvement = (1 - minimal_stats["avg_tokens"] / full_stats["avg_tokens"]) * 100
        time_improvement = (1 - minimal_stats["avg_response_time"] / full_stats["avg_response_time"]) * 100

        summary = {
            "minimal": minimal_stats,
            "full": full_stats,
            "improvement": {
                "token_reduction_percent": token_improvement,
                "time_reduction_percent": time_improvement,
                "success_rate_delta": minimal_stats["success_rate"] - full_stats["success_rate"]
            }
        }

        # 打印摘要
        self._print_summary(summary)

        return summary

    def _print_summary(self, summary: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("测试摘要")
        print("=" * 70)

        print("\n【极简版提示词】")
        print(f"  成功率: {summary['minimal']['success_rate']:.1f}%")
        print(f"  平均响应时间: {summary['minimal']['avg_response_time']:.2f}s")
        print(f"  平均 Token 数: {summary['minimal']['avg_tokens']:.0f}")
        print(f"  平均回答长度: {summary['minimal']['avg_answer_length']:.0f} 字符")

        print("\n【完整版提示词】")
        print(f"  成功率: {summary['full']['success_rate']:.1f}%")
        print(f"  平均响应时间: {summary['full']['avg_response_time']:.2f}s")
        print(f"  平均 Token 数: {summary['full']['avg_tokens']:.0f}")
        print(f"  平均回答长度: {summary['full']['avg_answer_length']:.0f} 字符")

        print("\n【改善效果】")
        print(f"  Token 消耗降低: {summary['improvement']['token_reduction_percent']:.1f}%")
        print(f"  响应时间缩短: {summary['improvement']['time_reduction_percent']:.1f}%")
        print(f"  成功率变化: {summary['improvement']['success_rate_delta']:+.1f}%")

        print("\n" + "=" * 70)

    def save_results(self, filepath: str):
        """保存测试结果到 JSON 文件"""
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": self._generate_summary(),
            "detailed_results": [
                {
                    "question": r.question,
                    "prompt_type": r.prompt_type,
                    "success": r.success,
                    "response_time": r.response_time,
                    "token_count": r.token_count,
                    "error": r.error_message
                }
                for r in self.results
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n测试结果已保存到: {filepath}")


# ============================================================================
# Agent 运行器接口
# ============================================================================

async def mock_agent_runner(
    question: str,
    simplified: bool = True,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Agent 运行器（模拟版本，实际使用时替换为真实的 Agent 调用）

    Args:
        question: 用户问题
        simplified: 是否使用极简版提示词
        verbose: 是否输出详细信息

    Returns:
        包含以下字段的字典:
        - success: 是否成功
        - answer: 回答内容
        - sql: 生成的 SQL（如果有）
        - token_count: 消耗的 Token 数
        - error: 错误信息（如果有）
    """
    # 这里应该调用实际的 Agent
    # 目前返回模拟数据用于测试框架本身

    # 模拟延迟
    await asyncio.sleep(0.5)

    # 模拟不同提示词的 Token 消耗
    base_tokens = 500 if simplified else 3000

    # 模拟回答
    return {
        "success": True,
        "answer": f"这是对问题 '{question}' 的模拟回答。",
        "sql": "SELECT * FROM orders LIMIT 10;",
        "token_count": base_tokens + len(question) * 2,
        "error": ""
    }


async def real_agent_runner(
    question: str,
    simplified: bool = True,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    真实的 Agent 运行器

    使用实际的 sql_agent 运行查询。

    注意：需要根据实际的 Agent 实现进行调整。
    """
    try:
        # 导入 Agent 模块
        import sys
        from pathlib import Path

        # 添加 AgentV2 到路径
        agentv2_path = Path(__file__).parent.parent
        sys.path.insert(0, str(agentv2_path))

        from sql_agent import run_agent

        # 调用 Agent
        result = await run_agent(
            question,
            simplified_prompt=simplified,
            verbose=verbose
        )

        return {
            "success": result.get("success", True),
            "answer": result.get("answer", ""),
            "sql": result.get("sql", ""),
            "token_count": result.get("tokens_used", 0),
            "error": result.get("error", "")
        }

    except Exception as e:
        return {
            "success": False,
            "answer": "",
            "sql": "",
            "token_count": 0,
            "error": str(e)
        }


# ============================================================================
# 主入口
# ============================================================================

async def main():
    """主函数"""
    tester = PromptComparisonTester()

    # 使用模拟 Agent 进行测试
    # 实际使用时替换为 real_agent_runner
    await tester.run_comparison(mock_agent_runner)

    # 保存结果
    output_dir = Path(__file__).parent.parent / "test_results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"prompt_comparison_{int(time.time())}.json"
    tester.save_results(str(output_file))


if __name__ == "__main__":
    asyncio.run(main())
