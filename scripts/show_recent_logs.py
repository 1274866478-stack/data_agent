# -*- coding: utf-8 -*-
"""
快速查看最近日志的便捷脚本
===========================================

提供命令行快速查看后端日志的功能。

使用方式:
    # 查看指定session的日志
    python scripts/show_recent_logs.py --session <session_id>

    # 查看最近的错误日志
    python scripts/show_recent_logs.py --errors --limit 20

    # 查看最近的Agent日志
    python scripts/show_recent_logs.py --agent --limit 50

    # 查看日志摘要
    python scripts/show_recent_logs.py --summary

版本: 1.0.0
作者: Data Agent Team
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from AgentV2.tools.log_viewer_tools import (
    get_logs_by_session,
    get_recent_agent_logs,
    get_error_logs,
    get_logs_summary,
    format_log_for_display,
)


# ============================================================================
# 格式化输出
# ============================================================================

def print_header(title: str) -> None:
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_log_detail(log: dict) -> None:
    """打印日志详情"""
    print(f"\n{'─' * 50}")
    print(f"时间: {log.get('timestamp', 'N/A')}")
    print(f"级别: {log.get('level', 'N/A')}")
    print(f"节点: {log.get('node_name', 'N/A')}")
    print(f"消息类型: {log.get('message_type', 'N/A')}")
    print(f"Session: {log.get('session_id', 'N/A')}")

    if log.get('raw_message'):
        print(f"消息: {log['raw_message']}")

    content = log.get('content')
    if content and isinstance(content, dict):
        print(f"内容:")
        for key, value in content.items():
            value_str = json.dumps(value, ensure_ascii=False)[:200]
            print(f"  {key}: {value_str}")
    elif content:
        print(f"内容: {content}")


def print_summary_table(summary: dict) -> None:
    """打印摘要表格"""
    print(f"\n📊 日志摘要")
    print(f"  总日志数: {summary['total_logs']}")
    print(f"  错误数: {summary['error_count']}")
    print(f"  警告数: {summary['warning_count']}")

    if summary.get('by_node'):
        print(f"\n📍 按节点分布:")
        for node, count in sorted(summary['by_node'].items(), key=lambda x: -x[1]):
            print(f"  {node}: {count}")

    if summary.get('by_message_type'):
        print(f"\n📋 按消息类型分布:")
        for msg_type, count in sorted(summary['by_message_type'].items(), key=lambda x: -x[1]):
            print(f"  {msg_type}: {count}")

    if summary.get('log_files'):
        print(f"\n📁 日志文件:")
        for file_info in summary['log_files']:
            print(f"  {file_info['name']}: {file_info['size_mb']:.2f} MB")


# ============================================================================
# 命令处理
# ============================================================================

def cmd_session(session_id: str, limit: int) -> None:
    """查看session日志"""
    print_header(f"会话日志: {session_id}")

    logs = get_logs_by_session(session_id, limit=limit)

    if not logs:
        print(f"\n未找到 session_id={session_id} 的日志")
        return

    print(f"\n找到 {len(logs)} 条日志\n")

    for i, log in enumerate(logs, 1):
        print(f"[{i}] {format_log_for_display(log)}")

    # 询问是否显示详情
    if len(logs) > 0:
        print(f"\n使用 --detail 查看完整详情")


def cmd_errors(limit: int, detail: bool) -> None:
    """查看错误日志"""
    print_header(f"最近 {limit} 条错误日志")

    logs = get_error_logs(limit=limit)

    if not logs:
        print("\n未找到错误日志")
        return

    print(f"\n找到 {len(logs)} 条错误\n")

    if detail:
        for log in logs:
            print_log_detail(log)
    else:
        for i, log in enumerate(logs, 1):
            print(f"[{i}] {format_log_for_display(log)}")


def cmd_agent(limit: int, detail: bool) -> None:
    """查看Agent日志"""
    print_header(f"最近 {limit} 条 Agent 日志")

    logs = get_recent_agent_logs(limit=limit)

    if not logs:
        print("\n未找到Agent日志")
        return

    print(f"\n找到 {len(logs)} 条日志\n")

    if detail:
        for log in logs:
            print_log_detail(log)
    else:
        for i, log in enumerate(logs, 1):
            print(f"[{i}] {format_log_for_display(log)}")


def cmd_summary(session_id: str = None) -> None:
    """查看日志摘要"""
    title = f"日志摘要: {session_id}" if session_id else "日志摘要"
    print_header(title)

    summary = get_logs_summary(session_id=session_id)
    print_summary_table(summary)


def cmd_save(session_id: str, output: str) -> None:
    """保存日志到文件"""
    print_header(f"保存日志: {session_id}")

    logs = get_logs_by_session(session_id)

    if not logs:
        print(f"\n未找到 session_id={session_id} 的日志")
        return

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n已保存 {len(logs)} 条日志到: {output_path}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="快速查看后端日志",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --session 1770196413873-ano22u8eo
  %(prog)s --errors --limit 20
  %(prog)s --agent --limit 50 --detail
  %(prog)s --summary --session 1770196413873-ano22u8eo
  %(prog)s --save 1770196413873-ano22u8eo -o logs/session.json
        """
    )

    # 查询类型
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--session', '-s',
        help='查看指定session的日志'
    )
    group.add_argument(
        '--errors', '-e',
        action='store_true',
        help='查看错误日志'
    )
    group.add_argument(
        '--agent', '-a',
        action='store_true',
        help='查看Agent日志'
    )
    group.add_argument(
        '--summary',
        action='store_true',
        help='查看日志摘要'
    )

    # 选项
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=20,
        help='显示条数 (默认: 20)'
    )
    parser.add_argument(
        '--detail', '-d',
        action='store_true',
        help='显示详细信息'
    )
    parser.add_argument(
        '--save-session',
        metavar='SESSION_ID',
        help='保存指定session的日志'
    )
    parser.add_argument(
        '--output', '-o',
        metavar='FILE',
        help='输出文件路径'
    )

    args = parser.parse_args()

    try:
        # 处理保存命令
        if args.save_session:
            output = args.output or f"logs/{args.save_session}.json"
            cmd_save(args.save_session, output)
            return

        # 处理查询命令
        if args.session:
            cmd_session(args.session, args.limit)
        elif args.errors:
            cmd_errors(args.limit, args.detail)
        elif args.agent:
            cmd_agent(args.limit, args.detail)
        elif args.summary:
            cmd_summary(args.session)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
