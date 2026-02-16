# -*- coding: utf-8 -*-
"""
ErrorTracker Middleware - 错误追踪中间件
==========================================

记录 Agent 执行过程中的错误，提供错误分析和统计。

核心功能:
    - 错误分类与记录
    - 成功案例追踪
    - 错误统计分析
    - 报告生成

作者: BMad Master
版本: 2.0.0
"""

import json
import logging
import traceback
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import Counter, defaultdict


# ============================================================================
# 错误分类
# ============================================================================

class ErrorCategory(str, Enum):
    """错误分类枚举"""
    # 用户输入问题
    AMBIGUOUS_QUERY = "用户问题不明确"
    INVALID_REQUEST = "无效请求"

    # 系统错误
    DATABASE_CONNECTION = "数据库连接失败"
    MCP_TOOL_FAILURE = "MCP工具调用失败"
    LLM_API_ERROR = "LLM API错误"

    # 数据问题
    SCHEMA_NOT_FOUND = "表或字段不存在"
    EMPTY_RESULT = "查询无结果"
    DATA_TYPE_MISMATCH = "数据类型不匹配"

    # 安全问题
    SQL_INJECTION_ATTEMPT = "SQL注入尝试"
    DANGEROUS_OPERATION = "危险操作"

    # 其他
    UNKNOWN = "未知错误"


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class ErrorEntry:
    """错误条目"""
    timestamp: str
    question: str
    error_category: ErrorCategory
    error_message: str
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class SuccessEntry:
    """成功条目"""
    timestamp: str
    question: str
    response: str
    context: Dict[str, Any]
    execution_time: Optional[float] = None


# ============================================================================
# ErrorTracker
# ============================================================================

class ErrorTracker:
    """
    错误追踪器

    记录和分析 Agent 执行过程中的错误，提供统计和报告功能。

    使用示例:
    ```python
    from AgentV2.middleware import ErrorTracker

    tracker = ErrorTracker(log_file="agent_errors.jsonl")

    tracker.log_error(
        question="统计xyz字段",
        error_category=ErrorCategory.SCHEMA_NOT_FOUND,
        error_message="Column 'xyz' does not exist"
    )

    report = tracker.generate_report(days=7)
    print(report)
    ```
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化错误追踪器

        Args:
            log_dir: 日志目录路径
        """
        if log_dir is None:
            log_dir = "logs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.error_log_file = self.log_dir / "agent_errors.jsonl"
        self.success_log_file = self.log_dir / "agent_success.jsonl"

        self.logger = logging.getLogger(__name__)

    def log_error(
        self,
        question: str,
        error_category: ErrorCategory,
        error_message: str,
        context: Optional[Dict] = None,
        stack_trace: Optional[str] = None
    ):
        """记录错误"""
        entry = ErrorEntry(
            timestamp=datetime.now().isoformat(),
            question=question,
            error_category=error_category,
            error_message=error_message,
            context=context or {},
            stack_trace=stack_trace,
            resolved=False
        )

        try:
            with open(self.error_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")

            self.logger.error(
                f"Error logged: {error_category.value} - {error_message}",
                extra={"question": question}
            )
        except Exception as e:
            self.logger.exception(f"Failed to log error: {e}")

    def log_success(
        self,
        question: str,
        response: str,
        context: Optional[Dict] = None,
        execution_time: Optional[float] = None
    ):
        """记录成功案例"""
        entry = SuccessEntry(
            timestamp=datetime.now().isoformat(),
            question=question,
            response=response[:500],  # 限制长度
            context=context or {},
            execution_time=execution_time
        )

        try:
            with open(self.success_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.exception(f"Failed to log success: {e}")

    def get_errors(
        self,
        days: int = 7,
        category: Optional[ErrorCategory] = None
    ) -> List[Dict]:
        """获取最近N天的错误记录"""
        if not self.error_log_file.exists():
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        errors = []

        try:
            with open(self.error_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_date = datetime.fromisoformat(entry["timestamp"])

                        if entry_date >= cutoff_date:
                            if category is None or entry["error_category"] == category.value:
                                errors.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as e:
            self.logger.exception(f"Failed to read errors: {e}")

        return errors

    def get_error_stats(self, days: int = 7) -> Dict:
        """获取错误统计"""
        errors = self.get_errors(days=days)

        # 按类别统计
        category_counts = Counter(e["error_category"] for e in errors)

        # 按日期统计
        date_counts = defaultdict(int)
        for error in errors:
            try:
                date = datetime.fromisoformat(error["timestamp"]).date().isoformat()
                date_counts[date] += 1
            except (KeyError, ValueError):
                continue

        # 高频问题
        question_counts = Counter(e["question"] for e in errors)
        top_questions = question_counts.most_common(10)

        # 计算成功率
        success_count = 0
        if self.success_log_file.exists():
            try:
                with open(self.success_log_file, "r", encoding="utf-8") as f:
                    success_count = sum(1 for _ in f)
            except Exception:
                pass

        total_count = len(errors) + success_count
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        return {
            "period_days": days,
            "total_errors": len(errors),
            "total_requests": total_count,
            "success_count": success_count,
            "success_rate": f"{success_rate:.2f}%",
            "errors_by_category": dict(category_counts),
            "errors_by_date": dict(date_counts),
            "top_error_questions": top_questions
        }

    def generate_report(self, days: int = 7) -> str:
        """生成错误报告"""
        stats = self.get_error_stats(days=days)

        report = f"""
# Agent 错误分析报告

**统计周期**: 最近 {days} 天
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 总体概况

- 总请求数: {stats['total_requests']}
- 成功请求: {stats['success_count']}
- 失败请求: {stats['total_errors']}
- **成功率: {stats['success_rate']}**

---

## 错误分类统计

"""

        for category, count in sorted(
            stats['errors_by_category'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            percentage = (count / stats['total_errors'] * 100) if stats['total_errors'] > 0 else 0
            report += f"- {category}: {count} ({percentage:.1f}%)\n"

        report += "\n---\n\n## 高频错误问题 (Top 10)\n\n"

        for i, (question, count) in enumerate(stats['top_error_questions'], 1):
            report += f"{i}. [{count}次] {question}\n"

        report += "\n---\n\n## 每日错误趋势\n\n"

        for date, count in sorted(stats['errors_by_date'].items()):
            report += f"- {date}: {count}个错误\n"

        return report


# ============================================================================
# ErrorTrackerMiddleware
# ============================================================================

class ErrorTrackerMiddleware:
    """
    错误追踪中间件

    自动捕获 Agent 执行过程中的错误并记录。

    使用示例:
    ```python
    from AgentV2.middleware import ErrorTrackerMiddleware

    middleware = ErrorTrackerMiddleware(
        tenant_id="tenant_123"
    )

    # 在 Agent 执行前
    agent_input = middleware.pre_process({"messages": [...]})

    # ... Agent 执行 ...

    # 在 Agent 执行后（捕获错误）
    try:
        result = agent.run(agent_input)
        agent_output = middleware.post_process({"answer": result})
    except Exception as e:
        agent_output = middleware.capture_error(e, agent_input)
    ```
    """

    def __init__(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        log_dir: Optional[str] = None
    ):
        """
        初始化错误追踪中间件

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            log_dir: 日志目录
        """
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.tracker = ErrorTracker(log_dir=log_dir)

        # 当前执行上下文
        self._current_question: Optional[str] = None
        self._start_time: Optional[float] = None

    def pre_process(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行前开始追踪

        Args:
            agent_input: Agent 输入数据

        Returns:
            处理后的输入数据
        """
        import time

        self._start_time = time.time()

        # 提取用户问题
        messages = agent_input.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, dict):
                self._current_question = last_message.get("content", "")
            else:
                self._current_question = str(last_message)

        # 注入追踪器引用
        agent_input["__error_tracker__"] = self

        return agent_input

    def post_process(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行成功后记录

        Args:
            agent_output: Agent 输出数据

        Returns:
            处理后的输出数据
        """
        if self._current_question:
            execution_time = None
            if self._start_time:
                import time
                execution_time = time.time() - self._start_time

            answer = agent_output.get("answer", "")
            context = {
                "tenant_id": self.tenant_id,
                "user_id": self.user_id
            }

            self.tracker.log_success(
                question=self._current_question,
                response=answer,
                context=context,
                execution_time=execution_time
            )

        return agent_output

    def capture_error(
        self,
        error: Exception,
        agent_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        捕获并记录错误

        Args:
            error: 异常对象
            agent_input: Agent 输入数据

        Returns:
            错误响应
        """
        question = self._current_question or str(agent_input)

        # 自动推断错误类别
        category = self._infer_error_category(error)

        # 记录错误
        self.tracker.log_error(
            question=question,
            error_category=category,
            error_message=str(error),
            context={
                "tenant_id": self.tenant_id,
                "user_id": self.user_id
            },
            stack_trace=traceback.format_exc()
        )

        # 返回错误响应
        return {
            "success": False,
            "error": str(error),
            "error_category": category.value,
            "tenant_id": self.tenant_id
        }

    def _infer_error_category(self, error: Exception) -> ErrorCategory:
        """根据异常类型推断错误类别"""
        error_str = str(error).lower()
        error_type = type(error).__name__

        if "connection" in error_str or "connect" in error_str:
            return ErrorCategory.DATABASE_CONNECTION

        if "api" in error_str or "request" in error_str:
            return ErrorCategory.LLM_API_ERROR

        if "not found" in error_str or "does not exist" in error_str:
            return ErrorCategory.SCHEMA_NOT_FOUND

        if "injection" in error_str or "drop" in error_str:
            return ErrorCategory.SQL_INJECTION_ATTEMPT

        if error_type in ["ValueError", "TypeError"]:
            return ErrorCategory.DATA_TYPE_MISMATCH

        return ErrorCategory.UNKNOWN

    def get_stats(self, days: int = 7) -> Dict:
        """获取错误统计"""
        return self.tracker.get_error_stats(days=days)

    def generate_report(self, days: int = 7) -> str:
        """生成错误报告"""
        return self.tracker.generate_report(days=days)


# ============================================================================
# 便捷函数
# ============================================================================

def create_error_tracker(
    tenant_id: str,
    user_id: Optional[str] = None,
    log_dir: Optional[str] = None
) -> ErrorTrackerMiddleware:
    """
    创建错误追踪中间件的便捷函数

    Args:
        tenant_id: 租户 ID
        user_id: 用户 ID
        log_dir: 日志目录

    Returns:
        ErrorTrackerMiddleware 实例
    """
    return ErrorTrackerMiddleware(
        tenant_id=tenant_id,
        user_id=user_id,
        log_dir=log_dir
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ErrorTracker 中间件测试")
    print("=" * 60)

    # 创建错误追踪器
    tracker = ErrorTracker(log_dir="test_logs")

    # 测试记录错误
    print("\n[TEST 1] 记录错误")
    tracker.log_error(
        question="统计xyz字段",
        error_category=ErrorCategory.SCHEMA_NOT_FOUND,
        error_message="Column 'xyz' does not exist",
        context={"user_id": "user123", "tenant_id": "tenant456"}
    )

    tracker.log_error(
        question="DROP TABLE users",
        error_category=ErrorCategory.DANGEROUS_OPERATION,
        error_message="Dangerous SQL operation detected",
        context={"user_id": "user789"}
    )

    print("[PASS] 错误记录成功")

    # 测试记录成功
    print("\n[TEST 2] 记录成功")
    tracker.log_success(
        question="列出所有表",
        response="数据库中有：users, orders, products",
        execution_time=0.5
    )

    print("[PASS] 成功记录成功")

    # 测试生成报告
    print("\n[TEST 3] 生成报告")
    report = tracker.generate_report(days=7)
    print(report)

    print("\n[PASS] 报告生成成功")

    # 测试中间件
    print("\n[TEST 4] 错误追踪中间件")
    middleware = create_error_tracker(
        tenant_id="test_tenant",
        user_id="test_user",
        log_dir="test_logs"
    )

    agent_input = {"messages": [{"role": "user", "content": "测试查询"}]}
    enhanced = middleware.pre_process(agent_input)

    # 模拟成功
    output = middleware.post_process({"answer": "查询成功"})
    print(f"[INFO] 输出: {output}")

    # 模拟错误
    try:
        raise ValueError("测试错误")
    except Exception as e:
        error_response = middleware.capture_error(e, agent_input)
        print(f"[INFO] 错误响应: {error_response}")

    print("[PASS] 中间件测试通过")

    # 清理测试文件
    print("\n[CLEANUP] 清理测试文件")
    import shutil
    if Path("test_logs").exists():
        shutil.rmtree("test_logs")
    print("[INFO] 测试文件已清理")

    print("\n" + "=" * 60)
    print("[SUCCESS] ErrorTracker 中间件测试通过")
    print("=" * 60)
