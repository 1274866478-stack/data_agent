"""
Agent错误追踪与分析工具
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum
from collections import Counter, defaultdict


class ErrorCategory(str, Enum):
    """错误分类"""
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


class ErrorTracker:
    """错误追踪器"""

    def __init__(self, log_file: str = "agent_errors.jsonl"):
        """
        初始化错误追踪器

        Args:
            log_file: 错误日志文件路径
        """
        self.log_file = Path(log_file)
        self.logger = logging.getLogger(__name__)

        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_error(
        self,
        question: str,
        error_category: ErrorCategory,
        error_message: str,
        context: Optional[Dict] = None,
        stack_trace: Optional[str] = None
    ):
        """
        记录错误

        Args:
            question: 用户问题
            error_category: 错误类别
            error_message: 错误消息
            context: 上下文信息（用户ID、租户ID等）
            stack_trace: 堆栈跟踪
        """
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "error_category": error_category.value,
            "error_message": error_message,
            "context": context or {},
            "stack_trace": stack_trace,
            "resolved": False
        }

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")

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
        """
        记录成功案例（用于统计成功率）

        Args:
            question: 用户问题
            response: 系统响应
            context: 上下文信息
            execution_time: 执行时间（秒）
        """
        success_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response[:500],  # 限制长度
            "context": context or {},
            "execution_time": execution_time,
            "status": "success"
        }

        success_file = self.log_file.parent / "agent_success.jsonl"

        try:
            with open(success_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(success_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.exception(f"Failed to log success: {e}")

    def get_errors(
        self,
        days: int = 7,
        category: Optional[ErrorCategory] = None
    ) -> List[Dict]:
        """
        获取最近N天的错误记录

        Args:
            days: 天数
            category: 错误类别过滤

        Returns:
            错误记录列表
        """
        if not self.log_file.exists():
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        errors = []

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_date = datetime.fromisoformat(entry["timestamp"])

                        if entry_date >= cutoff_date:
                            if category is None or entry["error_category"] == category.value:
                                errors.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            self.logger.exception(f"Failed to read errors: {e}")

        return errors

    def get_error_stats(self, days: int = 7) -> Dict:
        """
        获取错误统计

        Args:
            days: 统计天数

        Returns:
            统计结果字典
        """
        errors = self.get_errors(days=days)

        # 按类别统计
        category_counts = Counter(e["error_category"] for e in errors)

        # 按日期统计
        date_counts = defaultdict(int)
        for error in errors:
            date = datetime.fromisoformat(error["timestamp"]).date().isoformat()
            date_counts[date] += 1

        # 高频问题
        question_counts = Counter(e["question"] for e in errors)
        top_questions = question_counts.most_common(10)

        # 计算成功率
        success_file = self.log_file.parent / "agent_success.jsonl"
        success_count = 0
        if success_file.exists():
            success_count = sum(1 for _ in open(success_file, "r", encoding="utf-8"))

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
        """
        生成可读的错误报告

        Args:
            days: 统计天数

        Returns:
            报告文本
        """
        stats = self.get_error_stats(days=days)

        report = f"""
# Agent错误分析报告

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

    def mark_as_resolved(self, question: str):
        """
        标记某个问题已解决

        Args:
            question: 问题文本
        """
        # 这个实现比较简单，实际可能需要更复杂的匹配逻辑
        if not self.log_file.exists():
            return

        lines = []
        updated = 0

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry["question"] == question and not entry.get("resolved"):
                            entry["resolved"] = True
                            entry["resolved_at"] = datetime.now().isoformat()
                            updated += 1
                        lines.append(json.dumps(entry, ensure_ascii=False))
                    except json.JSONDecodeError:
                        lines.append(line.strip())

            # 重写文件
            with open(self.log_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")

            self.logger.info(f"Marked {updated} errors as resolved for question: {question}")

        except Exception as e:
            self.logger.exception(f"Failed to mark as resolved: {e}")


# ===== 全局错误追踪器实例 =====
error_tracker = ErrorTracker()


# ===== 便捷函数 =====

def log_agent_error(
    question: str,
    error: Exception,
    category: Optional[ErrorCategory] = None,
    context: Optional[Dict] = None
):
    """
    便捷函数：记录Agent错误

    Args:
        question: 用户问题
        error: 异常对象
        category: 错误类别（如果为None则自动推断）
        context: 上下文信息
    """
    import traceback

    # 自动推断错误类别
    if category is None:
        category = _infer_error_category(error)

    error_tracker.log_error(
        question=question,
        error_category=category,
        error_message=str(error),
        context=context,
        stack_trace=traceback.format_exc()
    )


def _infer_error_category(error: Exception) -> ErrorCategory:
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


# ===== 使用示例 =====

if __name__ == "__main__":
    # 示例：记录一些错误
    tracker = ErrorTracker("test_errors.jsonl")

    # 记录错误
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

    # 记录成功
    tracker.log_success(
        question="列出所有表",
        response="数据库中有：users, orders, products",
        execution_time=0.5
    )

    # 生成报告
    report = tracker.generate_report(days=7)
    print(report)

    # 清理测试文件
    import os
    if os.path.exists("test_errors.jsonl"):
        os.remove("test_errors.jsonl")
