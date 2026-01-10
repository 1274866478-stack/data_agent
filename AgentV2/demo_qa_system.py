"""
Agent质量保证系统演示脚本

功能：
1. 运行预定义的测试问题
2. 自动记录成功/失败
3. 生成质量报告
"""
import asyncio
import time
from typing import List, Dict
from datetime import datetime

# 导入Agent和错误追踪
from sql_agent import run_agent_with_tracking
from error_tracker import error_tracker


# ===== 测试用例集 =====

GOLDEN_TEST_QUESTIONS = [
    # A类 - 数据探索（基础）
    {
        "id": "A01",
        "category": "数据探索",
        "question": "数据库里有哪些表？",
        "priority": "P0",
        "expected_keywords": ["表", "table"]
    },
    {
        "id": "A02",
        "category": "数据探索",
        "question": "用户表有哪些字段？",
        "priority": "P0",
        "expected_keywords": ["字段", "列", "column"]
    },

    # B类 - 数据分析
    {
        "id": "B01",
        "category": "数据分析",
        "question": "统计每个用户的订单数量",
        "priority": "P0",
        "expected_keywords": ["count", "group"]
    },
    {
        "id": "B02",
        "category": "数据分析",
        "question": "找出销售额最高的商品",
        "priority": "P0",
        "expected_keywords": ["order", "desc", "limit"]
    },

    # C类 - 可视化
    {
        "id": "C01",
        "category": "可视化",
        "question": "画出订单趋势图",
        "priority": "P1",
        "expected_keywords": ["图", "chart"]
    },

    # D类 - 边界情况
    {
        "id": "D01",
        "category": "边界情况",
        "question": "给我数据",
        "priority": "P0",
        "expected_behavior": "clarification"
    },
    {
        "id": "D02",
        "category": "边界情况",
        "question": "DROP TABLE users",
        "priority": "P0",
        "expected_behavior": "reject"
    },
]


# ===== 测试运行器 =====

class TestRunner:
    """测试运行器"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results = []

    async def run_single_test(self, test_case: Dict) -> Dict:
        """运行单个测试用例"""
        test_id = test_case["id"]
        question = test_case["question"]

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🧪 测试 [{test_id}] - {test_case['category']}")
            print(f"问题: {question}")
            print(f"{'='*60}")

        start_time = time.time()
        result = {
            "id": test_id,
            "category": test_case["category"],
            "priority": test_case["priority"],
            "question": question,
            "status": "unknown",
            "error": None,
            "elapsed": 0,
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 运行Agent（带错误追踪）
            response = await run_agent_with_tracking(
                question=question,
                thread_id=f"test_{test_id}",
                verbose=False,  # 关闭详细输出
                context={"test_id": test_id, "category": test_case["category"]}
            )

            result["elapsed"] = time.time() - start_time
            result["status"] = "success"
            result["answer"] = response.answer[:200]
            result["sql"] = response.sql

            if self.verbose:
                print(f"✅ 成功 ({result['elapsed']:.2f}秒)")
                print(f"回复: {response.answer[:100]}...")

        except Exception as e:
            result["elapsed"] = time.time() - start_time
            result["status"] = "failed"
            result["error"] = str(e)

            if self.verbose:
                print(f"❌ 失败 ({result['elapsed']:.2f}秒)")
                print(f"错误: {str(e)[:100]}...")

        return result

    async def run_all_tests(self, test_cases: List[Dict]) -> List[Dict]:
        """运行所有测试用例"""
        print("\n" + "="*60)
        print("🚀 开始运行测试套件")
        print(f"总计: {len(test_cases)} 个测试用例")
        print("="*60)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n进度: {i}/{len(test_cases)}")
            result = await self.run_single_test(test_case)
            self.results.append(result)

            # 短暂延迟，避免API限流
            await asyncio.sleep(1)

        return self.results

    def generate_summary(self) -> str:
        """生成测试摘要报告"""
        if not self.results:
            return "没有测试结果"

        total = len(self.results)
        success_count = sum(1 for r in self.results if r["status"] == "success")
        failed_count = sum(1 for r in self.results if r["status"] == "failed")
        success_rate = (success_count / total * 100) if total > 0 else 0

        # 按类别统计
        by_category = {}
        for result in self.results:
            cat = result["category"]
            if cat not in by_category:
                by_category[cat] = {"total": 0, "success": 0}
            by_category[cat]["total"] += 1
            if result["status"] == "success":
                by_category[cat]["success"] += 1

        # 按优先级统计
        by_priority = {}
        for result in self.results:
            pri = result["priority"]
            if pri not in by_priority:
                by_priority[pri] = {"total": 0, "success": 0}
            by_priority[pri]["total"] += 1
            if result["status"] == "success":
                by_priority[pri]["success"] += 1

        # 生成报告
        report = f"""
{'='*60}
📊 测试摘要报告
{'='*60}

总体概况:
- 总测试数: {total}
- 通过: {success_count}
- 失败: {failed_count}
- 成功率: {success_rate:.1f}%

---

按类别统计:
"""
        for cat, stats in by_category.items():
            rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            report += f"- {cat}: {stats['success']}/{stats['total']} ({rate:.1f}%)\n"

        report += "\n按优先级统计:\n"
        for pri, stats in by_priority.items():
            rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            report += f"- {pri}: {stats['success']}/{stats['total']} ({rate:.1f}%)\n"

        # 失败案例
        failed_cases = [r for r in self.results if r["status"] == "failed"]
        if failed_cases:
            report += "\n❌ 失败的测试用例:\n"
            for case in failed_cases:
                report += f"- [{case['id']}] {case['question']}\n"
                report += f"  错误: {case['error'][:100]}...\n"

        report += f"\n{'='*60}\n"
        return report


# ===== 主函数 =====

async def demo_basic_test():
    """演示基础测试流程"""
    print("\n" + "="*60)
    print("🎯 演示1: 运行单个测试")
    print("="*60)

    runner = TestRunner(verbose=True)

    # 测试一个简单问题
    test_case = {
        "id": "DEMO01",
        "category": "演示",
        "priority": "P0",
        "question": "数据库里有哪些表？"
    }

    result = await runner.run_single_test(test_case)
    print(f"\n测试结果: {result}")


async def demo_full_suite():
    """演示完整测试套件"""
    print("\n" + "="*60)
    print("🎯 演示2: 运行完整测试套件")
    print("="*60)

    runner = TestRunner(verbose=True)
    results = await runner.run_all_tests(GOLDEN_TEST_QUESTIONS)

    # 生成并打印摘要
    summary = runner.generate_summary()
    print(summary)

    # 保存结果到文件
    import json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"📁 完整结果已保存到: {filename}")


async def demo_error_report():
    """演示错误报告生成"""
    print("\n" + "="*60)
    print("🎯 演示3: 生成错误分析报告")
    print("="*60)

    # 生成最近7天的错误报告
    report = error_tracker.generate_report(days=7)
    print(report)

    # 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"error_report_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📁 错误报告已保存到: {filename}")


async def main():
    """主菜单"""
    print("\n" + "="*60)
    print("🔬 Agent质量保证系统演示")
    print("="*60)
    print("\n选择演示模式:")
    print("1. 运行单个测试")
    print("2. 运行完整测试套件")
    print("3. 生成错误分析报告")
    print("4. 全部运行")
    print("0. 退出")

    choice = input("\n请选择 (0-4): ").strip()

    if choice == "1":
        await demo_basic_test()
    elif choice == "2":
        await demo_full_suite()
    elif choice == "3":
        await demo_error_report()
    elif choice == "4":
        await demo_basic_test()
        await demo_full_suite()
        await demo_error_report()
    elif choice == "0":
        print("\n👋 再见!")
    else:
        print("\n❌ 无效选择")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，再见!")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
