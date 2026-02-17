# -*- coding: utf-8 -*-
"""
清空日志脚本
===========================================

清空所有日志文件，释放存储空间。

使用方式:
    python scripts/clear_logs.py

版本: 1.0.0
作者: Data Agent Team
"""

import argparse
from datetime import datetime
from pathlib import Path


# 日志目录配置
BACKEND_LOG_DIR = Path("backend/logs")
AI_ACCESSIBLE_LOG = Path("logs/ai_accessible_logs.jsonl")
KNOWLEDGE_LOG_DIR = Path("AgentV2/knowledge/logs")
POSITION_FILE = Path("logs/.monitor_positions.json")


def get_file_size_mb(file_path: Path) -> float:
    """获取文件大小（MB）"""
    if file_path.exists():
        return file_path.stat().st_size / (1024 * 1024)
    return 0


def clear_backend_logs() -> int:
    """清空后端日志文件"""
    cleared = 0
    size_before = 0

    for log_file in BACKEND_LOG_DIR.glob("*.log"):
        size_before += get_file_size_mb(log_file)
        try:
            log_file.write_text("")
            cleared += 1
            print(f"  [已清空] {log_file.name}")
        except Exception as e:
            print(f"  [失败] {log_file.name}: {e}")

    return cleared, size_before


def clear_ai_accessible_log() -> bool:
    """清空AI可访问日志"""
    try:
        if AI_ACCESSIBLE_LOG.exists():
            size = get_file_size_mb(AI_ACCESSIBLE_LOG)
            AI_ACCESSIBLE_LOG.write_text("")
            print(f"  [已清空] ai_accessible_logs.jsonl ({size:.2f} MB)")
            return True
        return False
    except Exception as e:
        print(f"  [失败] ai_accessible_logs.jsonl: {e}")
        return False


def clear_knowledge_logs() -> int:
    """清空知识库日志目录"""
    if not KNOWLEDGE_LOG_DIR.exists():
        return 0

    count = 0
    size_before = 0

    for date_dir in KNOWLEDGE_LOG_DIR.iterdir():
        if date_dir.is_dir():
            size = sum(f.stat().st_size for f in date_dir.glob("*") if f.is_file()) / (1024 * 1024)
            size_before += size
            try:
                for file in date_dir.glob("*"):
                    file.unlink()
                date_dir.rmdir()
                count += 1
                print(f"  [已删除] {date_dir.name}/ ({size:.2f} MB)")
            except Exception as e:
                print(f"  [失败] {date_dir.name}: {e}")

    return count, size_before


def clear_monitor_positions() -> bool:
    """清空监控位置记录"""
    try:
        if POSITION_FILE.exists():
            POSITION_FILE.unlink()
            print(f"  [已清空] 监控位置记录")
            return True
        return False
    except Exception as e:
        print(f"  [失败] 监控位置记录: {e}")
        return False


def list_log_files() -> None:
    """列出当前日志文件"""
    print("\n📁 当前日志文件:")
    total_size = 0

    # 后端日志
    if BACKEND_LOG_DIR.exists():
        for log_file in BACKEND_LOG_DIR.glob("*.log"):
            size = get_file_size_mb(log_file)
            total_size += size
            print(f"  backend/logs/{log_file.name}: {size:.2f} MB")

    # AI可访问日志
    if AI_ACCESSIBLE_LOG.exists():
        size = get_file_size_mb(AI_ACCESSIBLE_LOG)
        total_size += size
        print(f"  logs/ai_accessible_logs.jsonl: {size:.2f} MB")

    # 知识库日志
    if KNOWLEDGE_LOG_DIR.exists():
        for date_dir in KNOWLEDGE_LOG_DIR.iterdir():
            if date_dir.is_dir():
                size = sum(f.stat().st_size for f in date_dir.glob("*") if f.is_file()) / (1024 * 1024)
                total_size += size
                print(f"  AgentV2/knowledge/logs/{date_dir.name}/: {size:.2f} MB")

    print(f"\n  总计: {total_size:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="清空日志文件")
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='只列出日志文件，不清空'
    )
    parser.add_argument(
        '--backend-only', '-b',
        action='store_true',
        help='只清空后端日志'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='清空所有日志（默认）'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("  Data Agent 日志清理工具")
    print("=" * 50)

    # 列出当前日志
    list_log_files()

    if args.list:
        return

    print("\n确认要清空日志吗？这将会删除所有日志数据。")
    confirm = input("输入 'yes' 确认: ")

    if confirm.lower() != 'yes':
        print("已取消")
        return

    print("\n开始清理...")

    # 清空后端日志
    print("\n📝 清空后端日志:")
    count, size = clear_backend_logs()
    print(f"  清理了 {count} 个文件，释放 {size:.2f} MB")

    # 如果不是只清空后端日志
    if not args.backend_only:
        # 清空AI可访问日志
        print("\n🤖 清空AI可访问日志:")
        clear_ai_accessible_log()

        # 清空知识库日志
        print("\n📚 清空知识库日志:")
        count, size = clear_knowledge_logs()
        print(f"  删除了 {count} 个日期目录，释放 {size:.2f} MB")

        # 清空监控位置
        print("\n⚙️  清空监控位置:")
        clear_monitor_positions()

    print("\n✅ 日志清理完成！")


if __name__ == "__main__":
    main()
