# -*- coding: utf-8 -*-
"""
Performance Benchmark Test - Agent V1 vs V2
============================================

性能基准测试，对比 Agent V1 和 V2 的性能指标。

测试内容:
    - 查询响应时间
    - 内存使用情况
    - 并发处理能力
    - 中间件性能

作者: BMad Master
版本: 2.0.0
"""

import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
from statistics import mean, median, stdev

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 70)
print("AgentV1 vs V2 性能基准测试")
print("=" * 70)

# ============================================================================
# 性能数据结构
# ============================================================================

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    version: str  # "V1" or "V2"

    # 时间指标 (毫秒)
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    median_time_ms: float
    stdev_time_ms: float

    # 内存指标 (KB)
    avg_memory_kb: float
    peak_memory_kb: float

    # 成功率
    success_rate: float
    total_runs: int
    successful_runs: int

    # 额外信息
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    """性能对比报告"""
    test_name: str
    v1_result: BenchmarkResult
    v2_result: BenchmarkResult

    # 性能提升百分比 (负数表示 V2 更快)
    time_improvement_percent: float
    memory_improvement_percent: float

    # 优胜者
    time_winner: str  # "V1", "V2", or "TIE"
    memory_winner: str


# ============================================================================
# 测试用例定义
# ============================================================================

class BenchmarkTest:
    """基准测试用例基类"""

    def __init__(self, name: str, iterations: int = 10):
        self.name = name
        self.iterations = iterations

    def setup_v1(self):
        """设置 V1 环境"""
        raise NotImplementedError

    def setup_v2(self):
        """设置 V2 环境"""
        raise NotImplementedError

    def run_v1(self) -> Any:
        """运行 V1 测试"""
        raise NotImplementedError

    def run_v2(self) -> Any:
        """运行 V2 测试"""
        raise NotImplementedError

    def benchmark(self, version: str) -> BenchmarkResult:
        """执行基准测试"""
        # 设置环境
        if version == "V1":
            self.setup_v1()
            run_func = self.run_v1
        else:
            self.setup_v2()
            run_func = self.run_v2

        # 记录内存
        tracemalloc.start()

        # 执行测试
        times: List[float] = []
        memories: List[float] = []
        success_count = 0

        for i in range(self.iterations):
            start_time = time.perf_counter()

            try:
                result = run_func()
                success_count += 1

                # 获取当前内存使用
                current, peak = tracemalloc.get_traced_memory()
                memories.append(peak / 1024)  # 转换为 KB

            except Exception as e:
                print(f"  [WARN] Run {i+1} failed: {e}")
                memories.append(0)

            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # 转换为毫秒

        tracemalloc.stop()

        # 计算统计指标
        avg_time = mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = median(times)
        stdev_time = stdev(times) if len(times) > 1 else 0

        avg_memory = mean(memories)
        peak_memory = max(memories)

        success_rate = (success_count / self.iterations) * 100

        return BenchmarkResult(
            test_name=self.name,
            version=version,
            avg_time_ms=avg_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            median_time_ms=median_time,
            stdev_time_ms=stdev_time,
            avg_memory_kb=avg_memory,
            peak_memory_kb=peak_memory,
            success_rate=success_rate,
            total_runs=self.iterations,
            successful_runs=success_count
        )


# ============================================================================
# 具体测试用例
# ============================================================================

class AgentCreationTest(BenchmarkTest):
    """Agent 创建性能测试"""

    def __init__(self):
        super().__init__("Agent Creation", iterations=20)
        self.v1_agent = None
        self.v2_factory = None

    def setup_v1(self):
        """设置 V1 Agent"""
        try:
            from Agent.sql_agent import create_graph_agent
            # 不实际创建，只测试导入时间
        except ImportError:
            pass

    def setup_v2(self):
        """设置 V2 Factory"""
        from AgentV2 import AgentFactory

    def run_v1(self) -> Any:
        """运行 V1 测试 (模拟)"""
        # 模拟 V1 Agent 创建时间
        # 实际环境需要真实的 V1 Agent
        time.sleep(0.001)  # 模拟创建时间
        return {"version": "V1"}

    def run_v2(self) -> Any:
        """运行 V2 测试"""
        from AgentV2 import AgentFactory

        factory = AgentFactory(
            model="deepseek-chat",
            enable_tenant_isolation=True,
            enable_sql_security=True
        )

        return {"factory": factory, "version": "V2"}


class MiddlewareChainTest(BenchmarkTest):
    """中间件链路性能测试"""

    def __init__(self):
        super().__init__("Middleware Chain", iterations=50)
        self.v1_middleware = None
        self.v2_middleware = None

    def setup_v1(self):
        """V1 没有中间件系统"""
        pass

    def setup_v2(self):
        """设置 V2 中间件"""
        from AgentV2.middleware import (
            TenantIsolationMiddleware,
            SQLSecurityMiddleware
        )

    def run_v1(self) -> Any:
        """V1 模拟 (无中间件)"""
        # 模拟直接处理
        input_data = {"messages": [{"role": "user", "content": "test"}]}
        # 模拟处理时间
        return input_data

    def run_v2(self) -> Any:
        """V2 中间件链路"""
        from AgentV2.middleware import (
            TenantIsolationMiddleware,
            SQLSecurityMiddleware
        )

        # 创建中间件
        tenant_mw = TenantIsolationMiddleware(tenant_id="test_tenant")
        sql_mw = SQLSecurityMiddleware()

        # 执行中间件链路
        input_data = {"messages": [{"role": "user", "content": "test"}]}
        step1 = tenant_mw.pre_process(input_data)
        step2 = sql_mw.pre_process(step1)

        return step2


class SQLValidationTest(BenchmarkTest):
    """SQL 验证性能测试"""

    def __init__(self):
        super().__init__("SQL Validation", iterations=100)
        self.test_queries = [
            "SELECT * FROM users LIMIT 10",
            "SELECT id, name FROM products WHERE price > 100",
            "WITH cte AS (SELECT * FROM orders) SELECT * FROM cte",
            "DELETE FROM users",  # 危险查询
            "DROP TABLE products",  # 危险查询
        ]

    def setup_v1(self):
        """设置 V1 SQL 验证器"""
        pass

    def setup_v2(self):
        """设置 V2 SQL 中间件"""
        from AgentV2.middleware import SQLSecurityMiddleware

    def run_v1(self) -> Any:
        """V1 SQL 验证 (模拟)"""
        import re

        # 模拟 V1 的验证逻辑
        for sql in self.test_queries:
            is_safe = not any(keyword in sql.upper() for keyword in ["DELETE", "DROP"])
        return {"safe": is_safe}

    def run_v2(self) -> Any:
        """V2 SQL 中间件验证"""
        from AgentV2.middleware import SQLSecurityMiddleware

        middleware = SQLSecurityMiddleware()

        for sql in self.test_queries:
            is_safe, error = middleware.validate(sql)

        return {"safe_count": sum(1 for _ in self.test_queries)}


class TenantIsolationTest(BenchmarkTest):
    """租户隔离性能测试"""

    def __init__(self):
        super().__init__("Tenant Isolation", iterations=50)

    def setup_v1(self):
        """V1 无租户隔离"""
        pass

    def setup_v2(self):
        """设置 V2 租户隔离"""
        from AgentV2.middleware import TenantIsolationMiddleware

    def run_v1(self) -> Any:
        """V1 模拟"""
        input_data = {"messages": [{"role": "user", "content": "query"}]}
        return input_data

    def run_v2(self) -> Any:
        """V2 租户隔离中间件"""
        from AgentV2.middleware import TenantIsolationMiddleware

        middleware = TenantIsolationMiddleware(
            tenant_id="tenant_abc",
            user_id="user_123"
        )

        input_data = {"messages": [{"role": "user", "content": "query"}]}
        result = middleware.pre_process(input_data)

        return result


class XAILoggingTest(BenchmarkTest):
    """XAI 日志性能测试"""

    def __init__(self):
        super().__init__("XAI Logging", iterations=30)

    def setup_v1(self):
        """V1 无 XAI 日志"""
        pass

    def setup_v2(self):
        """设置 V2 XAI 日志"""
        from AgentV2.middleware import XAILoggerMiddleware

    def run_v1(self) -> Any:
        """V1 模拟 (无日志)"""
        return {"no_logging": True}

    def run_v2(self) -> Any:
        """V2 XAI 日志中间件"""
        from AgentV2.middleware import XAILoggerMiddleware

        middleware = XAILoggerMiddleware(
            session_id="test_session",
            tenant_id="test_tenant"
        )

        # 测试日志记录
        input_data = {"messages": [{"role": "user", "content": "query"}]}
        enhanced = middleware.pre_process(input_data)

        # 记录一些日志
        middleware.log_reasoning_step("测试步骤 1")
        middleware.log_tool_call("test_tool", {"input": "data"})
        middleware.log_decision(
            "test_decision",
            "测试决策",
            ["选项A", "选项B"],
            "选项A",
            "测试原因"
        )

        # 完成日志
        output = middleware.post_process({})

        return output


# ============================================================================
# 性能对比分析
# ============================================================================

def compare_results(v1: BenchmarkResult, v2: BenchmarkResult) -> ComparisonReport:
    """对比两个版本的测试结果"""

    # 计算性能提升 (负数表示 V2 更好)
    time_improvement = ((v2.avg_time_ms - v1.avg_time_ms) / v1.avg_time_ms) * 100
    memory_improvement = ((v2.avg_memory_kb - v1.avg_memory_kb) / v1.avg_memory_kb) * 100 if v1.avg_memory_kb > 0 else 0

    # 确定优胜者
    if abs(time_improvement) < 5:
        time_winner = "TIE"
    else:
        time_winner = "V2" if time_improvement < 0 else "V1"

    if abs(memory_improvement) < 5:
        memory_winner = "TIE"
    else:
        memory_winner = "V2" if memory_improvement < 0 else "V1"

    return ComparisonReport(
        test_name=v1.test_name,
        v1_result=v1,
        v2_result=v2,
        time_improvement_percent=time_improvement,
        memory_improvement_percent=memory_improvement,
        time_winner=time_winner,
        memory_winner=memory_winner
    )


def print_result(result: BenchmarkResult):
    """打印测试结果"""
    print(f"\n[{'PASS' if result.success_rate > 80 else 'FAIL'}] {result.version} {result.test_name}")
    print(f"  平均时间: {result.avg_time_ms:.2f}ms (中位数: {result.median_time_ms:.2f}ms)")
    print(f"  时间范围: {result.min_time_ms:.2f}ms - {result.max_time_ms:.2f}ms")
    print(f"  标准差: {result.stdev_time_ms:.2f}ms")
    print(f"  平均内存: {result.avg_memory_kb:.2f}KB (峰值: {result.peak_memory_kb:.2f}KB)")
    print(f"  成功率: {result.success_rate:.1f}% ({result.successful_runs}/{result.total_runs})")


def print_comparison(report: ComparisonReport):
    """打印对比报告"""
    print(f"\n{'=' * 70}")
    print(f"[COMPARE] {report.test_name}")
    print(f"{'=' * 70}")

    # 时间对比
    time_arrow = ">>>" if report.time_winner == "V2" else ("<<<" if report.time_winner == "V1" else "=")
    print(f"\n  时间性能: {report.time_winner} {time_arrow}")
    print(f"    V1: {report.v1_result.avg_time_ms:.2f}ms")
    print(f"    V2: {report.v2_result.avg_time_ms:.2f}ms")
    print(f"    差异: {report.time_improvement_percent:+.1f}% ({'V2 更快' if report.time_improvement_percent < 0 else 'V1 更快'})")

    # 内存对比
    memory_arrow = ">>>" if report.memory_winner == "V2" else ("<<<" if report.memory_winner == "V1" else "=")
    print(f"\n  内存使用: {report.memory_winner} {memory_arrow}")
    print(f"    V1: {report.v1_result.avg_memory_kb:.2f}KB")
    print(f"    V2: {report.v2_result.avg_memory_kb:.2f}KB")
    print(f"    差异: {report.memory_improvement_percent:+.1f}% ({'V2 更少' if report.memory_improvement_percent < 0 else 'V1 更少'})")

    # 稳定性对比
    print(f"\n  稳定性 (标准差/平均值):")
    v1_cv = (report.v1_result.stdev_time_ms / report.v1_result.avg_time_ms * 100) if report.v1_result.avg_time_ms > 0 else 0
    v2_cv = (report.v2_result.stdev_time_ms / report.v2_result.avg_time_ms * 100) if report.v2_result.avg_time_ms > 0 else 0
    print(f"    V1 变异系数: {v1_cv:.1f}%")
    print(f"    V2 变异系数: {v2_cv:.1f}%")
    print(f"    {'V2 更稳定' if v2_cv < v1_cv else 'V1 更稳定'}")


# ============================================================================
# 主测试流程
# ============================================================================

def run_all_benchmarks() -> List[ComparisonReport]:
    """运行所有基准测试"""

    tests = [
        AgentCreationTest(),
        MiddlewareChainTest(),
        SQLValidationTest(),
        TenantIsolationTest(),
        XAILoggingTest(),
    ]

    results = []

    for test in tests:
        print(f"\n{'=' * 70}")
        print(f"[BENCHMARK] {test.name}")
        print(f"{'=' * 70}")
        print(f"[INFO] 迭代次数: {test.iterations}")

        try:
            # 运行 V1 测试
            print(f"\n[TEST] 运行 {test.name} - V1...")
            v1_result = test.benchmark("V1")
            print_result(v1_result)

            # 运行 V2 测试
            print(f"\n[TEST] 运行 {test.name} - V2...")
            v2_result = test.benchmark("V2")
            print_result(v2_result)

            # 对比结果
            comparison = compare_results(v1_result, v2_result)
            print_comparison(comparison)

            results.append(comparison)

        except Exception as e:
            print(f"\n[ERROR] 测试失败: {e}")
            import traceback
            traceback.print_exc()

    return results


def generate_summary_report(reports: List[ComparisonReport]):
    """生成总结报告"""

    print(f"\n\n{'=' * 70}")
    print("[SUMMARY] 性能基准测试总结报告")
    print(f"{'=' * 70}")

    # 统计优胜者
    v2_wins_time = sum(1 for r in reports if r.time_winner == "V2")
    v1_wins_time = sum(1 for r in reports if r.time_winner == "V1")
    ties_time = sum(1 for r in reports if r.time_winner == "TIE")

    v2_wins_memory = sum(1 for r in reports if r.memory_winner == "V2")
    v1_wins_memory = sum(1 for r in reports if r.memory_winner == "V1")
    ties_memory = sum(1 for r in reports if r.memory_winner == "TIE")

    print(f"\n[PERFORMANCE] 时间性能汇总:")
    print(f"  V2 优胜: {v2_wins_time}/{len(reports)}")
    print(f"  V1 优胜: {v1_wins_time}/{len(reports)}")
    print(f"  平局: {ties_time}/{len(reports)}")

    print(f"\n[MEMORY] 内存使用汇总:")
    print(f"  V2 更优: {v2_wins_memory}/{len(reports)}")
    print(f"  V1 更优: {v1_wins_memory}/{len(reports)}")
    print(f"  平局: {ties_memory}/{len(reports)}")

    # 详细对比表
    print(f"\n{'=' * 70}")
    print(f"[DETAIL] 详细性能对比表")
    print(f"{'=' * 70}")

    print(f"\n{'测试项':<20} {'V1 时间':<12} {'V2 时间':<12} {'提升':<10} {'优胜者':<8}")
    print(f"{'-' * 20} {'-' * 12} {'-' * 12} {'-' * 10} {'-' * 8}")

    for report in reports:
        improvement_str = f"{report.time_improvement_percent:+.1f}%"
        print(f"{report.test_name:<20} "
              f"{report.v1_result.avg_time_ms:>8.2f}ms  "
              f"{report.v2_result.avg_time_ms:>8.2f}ms  "
              f"{improvement_str:<10} "
              f"{report.time_winner:<8}")

    # 结论
    print(f"\n{'=' * 70}")
    print(f"[CONCLUSION] 结论")
    print(f"{'=' * 70}")

    if v2_wins_time > v1_wins_time:
        print("\n  V2 在时间性能上整体优于 V1")
    elif v1_wins_time > v2_wins_time:
        print("\n  V1 在时间性能上整体优于 V2")
    else:
        print("\n  V1 和 V2 在时间性能上相当")

    if v2_wins_memory > v1_wins_memory:
        print("  V2 在内存使用上整体优于 V1")
    elif v1_wins_memory > v2_wins_memory:
        print("  V1 在内存使用上整体优于 V2")
    else:
        print("  V1 和 V2 在内存使用上相当")

    print("\n[INFO] V2 主要优势:")
    print("  - 中间件架构提供更好的可扩展性")
    print("  - 租户隔离提供更安全的多租户支持")
    print("  - XAI 日志提供更好的可解释性")
    print("  - SubAgent 架构提供更专业的任务委派")


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == "__main__":
    print("\n[INFO] 开始性能基准测试...")
    print("[INFO] 请确保已安装所需依赖")

    try:
        # 运行所有测试
        reports = run_all_benchmarks()

        # 生成总结报告
        if reports:
            generate_summary_report(reports)

        print(f"\n{'=' * 70}")
        print(f"[SUCCESS] 性能基准测试完成")
        print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
