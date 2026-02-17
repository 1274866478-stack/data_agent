# -*- coding: utf-8 -*-
"""
日志查看工具 - 供AI助手使用
===========================================

提供便捷的后端日志查看功能，帮助AI助手分析和调试问题。

核心功能:
    - 根据session_id获取相关日志
    - 获取最近的Agent日志
    - 获取错误日志
    - 解析JSON格式日志

版本: 1.0.0
作者: Data Agent Team
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


# ============================================================================
# 日志路径配置
# ============================================================================

DEFAULT_LOG_DIR = Path("backend/logs")
AI_ACCESSIBLE_LOG = Path("logs/ai_accessible_logs.jsonl")
AGENT_KNOWLEDGE_DIR = Path("AgentV2/knowledge/logs")


# ============================================================================
# 日志解析工具
# ============================================================================

def parse_json_log_line(line: str) -> Optional[Dict[str, Any]]:
    """
    解析单行JSON日志

    Args:
        line: 日志行字符串

    Returns:
        解析后的日志字典，解析失败返回 None
    """
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def parse_agent_log_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    解析Agent日志文件

    Args:
        file_path: 日志文件路径

    Returns:
        日志条目列表
    """
    logs = []
    if not file_path.exists():
        return logs

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                log = parse_json_log_line(line)
                if log:
                    logs.append(log)
    except Exception as e:
        print(f"[ERROR] 解析日志文件失败: {e}")

    return logs


def filter_logs_by_session(
    logs: List[Dict[str, Any]],
    session_id: str
) -> List[Dict[str, Any]]:
    """
    根据session_id过滤日志

    Args:
        logs: 日志列表
        session_id: 会话ID

    Returns:
        匹配的日志列表
    """
    return [
        log for log in logs
        if log.get('session_id') == session_id
    ]


def filter_error_logs(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    过滤错误级别日志

    Args:
        logs: 日志列表

    Returns:
        错误日志列表
    """
    return [
        log for log in logs
        if log.get('level') in ('ERROR', 'error', 'CRITICAL', 'critical')
        or log.get('message_type') == 'error'
    ]


# ============================================================================
# 主要API函数
# ============================================================================

def get_logs_by_session(
    session_id: str,
    log_dir: str = "backend/logs",
    include_agent: bool = True,
    include_application: bool = True,
    include_error: bool = True,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    根据session_id获取相关日志

    Args:
        session_id: 会话ID
        log_dir: 日志目录路径
        include_agent: 是否包含Agent日志
        include_application: 是否包含应用日志
        include_error: 是否包含错误日志
        limit: 返回的日志条数限制

    Returns:
        匹配的日志列表
    """
    log_path = Path(log_dir)
    all_logs = []

    # 搜索Agent日志文件
    if include_agent:
        agent_logs = log_path.glob("agent_*.log")
        for log_file in agent_logs:
            logs = parse_agent_log_file(log_file)
            all_logs.extend(logs)

    # 搜索应用日志
    if include_application:
        app_log = log_path / "application.log"
        if app_log.exists():
            logs = parse_agent_log_file(app_log)
            all_logs.extend(logs)

    # 搜索错误日志
    if include_error:
        error_log = log_path / "error.log"
        if error_log.exists():
            logs = parse_agent_log_file(error_log)
            all_logs.extend(logs)

    # 按session_id过滤
    filtered = filter_logs_by_session(all_logs, session_id)

    # 按时间戳排序（如果有）
    filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=False)

    # 应用限制
    if limit:
        filtered = filtered[:limit]

    return filtered


def get_recent_agent_logs(
    limit: int = 100,
    log_dir: str = "backend/logs"
) -> List[Dict[str, Any]]:
    """
    获取最近的Agent日志

    Args:
        limit: 返回的日志条数
        log_dir: 日志目录路径

    Returns:
        最近的日志列表
    """
    log_path = Path(log_dir)

    # 查找最新的Agent日志文件
    agent_logs = sorted(
        log_path.glob("agent_*.log"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    all_logs = []
    for log_file in agent_logs[:3]:  # 只读取最近的3个文件
        logs = parse_agent_log_file(log_file)
        all_logs.extend(logs)

    # 按时间戳排序
    all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    return all_logs[:limit]


def get_error_logs(
    limit: int = 50,
    log_dir: str = "backend/logs",
    hours: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    获取最近的错误日志

    Args:
        limit: 返回的日志条数
        log_dir: 日志目录路径
        hours: 时间范围（小时），None表示全部

    Returns:
        错误日志列表
    """
    log_path = Path(log_dir)

    # 从多个日志文件中收集错误
    all_logs = []

    # 错误日志文件
    error_log = log_path / "error.log"
    if error_log.exists():
        all_logs.extend(parse_agent_log_file(error_log))

    # 应用日志文件
    app_log = log_path / "application.log"
    if app_log.exists():
        all_logs.extend(parse_agent_log_file(app_log))

    # Agent日志文件
    for agent_log in log_path.glob("agent_*.log"):
        all_logs.extend(parse_agent_log_file(agent_log))

    # 过滤错误级别
    error_logs = filter_error_logs(all_logs)

    # 按时间戳排序
    error_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # 应用时间范围过滤（如果指定）
    if hours:
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        error_logs = [
            log for log in error_logs
            if _parse_timestamp(log.get('timestamp', '')) >= cutoff_time
        ]

    return error_logs[:limit]


def get_logs_summary(
    session_id: Optional[str] = None,
    log_dir: str = "backend/logs"
) -> Dict[str, Any]:
    """
    获取日志摘要信息

    Args:
        session_id: 可选的会话ID过滤
        log_dir: 日志目录路径

    Returns:
        日志摘要字典
    """
    log_path = Path(log_dir)

    summary = {
        "total_logs": 0,
        "error_count": 0,
        "warning_count": 0,
        "by_node": {},
        "by_message_type": {},
        "log_files": [],
        "session_id": session_id
    }

    # 收集所有日志
    all_logs = []
    if session_id:
        all_logs = get_logs_by_session(session_id, log_dir)
    else:
        all_logs = get_recent_agent_logs(limit=1000, log_dir=log_dir)

    summary["total_logs"] = len(all_logs)

    # 统计日志信息
    for log in all_logs:
        # 统计错误
        level = log.get('level', '').upper()
        if level in ('ERROR', 'CRITICAL'):
            summary["error_count"] += 1
        elif level == 'WARNING':
            summary["warning_count"] += 1

        # 按节点统计
        node = log.get('node_name', 'unknown')
        summary["by_node"][node] = summary["by_node"].get(node, 0) + 1

        # 按消息类型统计
        msg_type = log.get('message_type', 'unknown')
        summary["by_message_type"][msg_type] = summary["by_message_type"].get(msg_type, 0) + 1

    # 列出日志文件
    for log_file in log_path.glob("*.log"):
        summary["log_files"].append({
            "name": log_file.name,
            "size_mb": log_file.stat().st_size / (1024 * 1024),
            "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
        })

    return summary


# ============================================================================
# AI可访问日志写入
# ============================================================================

def append_to_ai_accessible_log(log_entries: List[Dict[str, Any]]) -> int:
    """
    将日志追加到AI可访问的日志文件

    Args:
        log_entries: 日志条目列表

    Returns:
        写入的条目数
    """
    # 确保目录存在
    AI_ACCESSIBLE_LOG.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        with open(AI_ACCESSIBLE_LOG, 'a', encoding='utf-8') as f:
            for log in log_entries:
                f.write(json.dumps(log, ensure_ascii=False) + '\n')
                written += 1
    except Exception as e:
        print(f"[ERROR] 写入AI可访问日志失败: {e}")

    return written


def write_to_knowledge_log(
    session_id: str,
    log_entries: List[Dict[str, Any]]
) -> None:
    """
    将日志写入知识库目录供AI学习

    Args:
        session_id: 会话ID
        log_entries: 日志条目列表
    """
    # 创建日期目录
    date_str = datetime.now().strftime("%Y-%m-%d")
    knowledge_dir = AGENT_KNOWLEDGE_DIR / date_str
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # 写入会话日志
    session_log_file = knowledge_dir / f"{session_id}.jsonl"
    try:
        with open(session_log_file, 'w', encoding='utf-8') as f:
            for log in log_entries:
                f.write(json.dumps(log, ensure_ascii=False, default=str) + '\n')
    except Exception as e:
        print(f"[ERROR] 写入知识库日志失败: {e}")


# ============================================================================
# 辅助函数
# ============================================================================

def _parse_timestamp(timestamp_str: str) -> float:
    """
    解析时间戳字符串

    Args:
        timestamp_str: 时间戳字符串

    Returns:
        Unix时间戳
    """
    try:
        # 尝试ISO格式
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
    except:
        pass

    try:
        # 尝试Unix时间戳
        return float(timestamp_str)
    except:
        pass

    return 0


def format_log_for_display(log: Dict[str, Any]) -> str:
    """
    格式化日志用于显示

    Args:
        log: 日志字典

    Returns:
        格式化的字符串
    """
    timestamp = log.get('timestamp', '')
    level = log.get('level', 'INFO')
    node = log.get('node_name', '')
    message_type = log.get('message_type', '')
    content = log.get('content', {})
    raw_message = log.get('raw_message', '')

    # 格式化时间
    try:
        if isinstance(timestamp, str) and 'T' in timestamp:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M:%S')
        else:
            time_str = str(timestamp)[:8]
    except:
        time_str = str(timestamp)[:8]

    # 构建输出
    parts = [f"[{time_str}]"]

    if level:
        parts.append(f"{level}")

    if node:
        parts.append(f"{node}")

    if message_type:
        parts.append(f"({message_type})")

    result = " ".join(parts)

    if raw_message:
        result += f" {raw_message}"
    elif content:
        result += f" {json.dumps(content, ensure_ascii=False)[:200]}"

    return result


# ============================================================================
# 便捷函数
# ============================================================================

def quick_view_session_logs(session_id: str, limit: int = 20) -> str:
    """
    快速查看会话日志（格式化输出）

    Args:
        session_id: 会话ID
        limit: 显示条数

    Returns:
        格式化的日志字符串
    """
    logs = get_logs_by_session(session_id, limit=limit)

    if not logs:
        return f"未找到 session_id={session_id} 的日志"

    lines = [f"=== 会话 {session_id} 的日志 (共 {len(logs)} 条) ===\n"]

    for log in logs:
        lines.append(format_log_for_display(log))

    return "\n".join(lines)


def quick_view_errors(limit: int = 10) -> str:
    """
    快速查看错误日志（格式化输出）

    Args:
        limit: 显示条数

    Returns:
        格式化的日志字符串
    """
    logs = get_error_logs(limit=limit)

    if not logs:
        return "未找到错误日志"

    lines = [f"=== 最近 {len(logs)} 条错误日志 ===\n"]

    for log in logs:
        lines.append(format_log_for_display(log))

    return "\n".join(lines)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("日志查看工具测试")
    print("=" * 60)

    # 测试获取最近日志
    print("\n[测试] 获取最近的Agent日志")
    recent_logs = get_recent_agent_logs(limit=5)
    print(f"找到 {len(recent_logs)} 条日志")
    for log in recent_logs[:3]:
        print(f"  - {format_log_for_display(log)}")

    # 测试获取错误日志
    print("\n[测试] 获取错误日志")
    error_logs = get_error_logs(limit=5)
    print(f"找到 {len(error_logs)} 条错误")

    # 测试获取摘要
    print("\n[测试] 日志摘要")
    summary = get_logs_summary()
    print(f"总日志数: {summary['total_logs']}")
    print(f"错误数: {summary['error_count']}")
    print(f"按节点分布: {summary['by_node']}")

    print("\n[PASS] 日志查看工具测试通过")
