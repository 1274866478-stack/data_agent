# -*- coding: utf-8 -*-
"""
后台日志监控服务
===========================================

持续监控后端日志并输出到AI可访问的文件。

核心功能:
    - 监控 backend/logs/ 目录下的日志文件
    - 将新日志追加到 logs/ai_accessible_logs.jsonl
    - 将新日志追加到 AgentV2/knowledge/logs/{date}.jsonl
    - 支持后台运行，实时更新

使用方式:
    python scripts/monitor_backend_logs.py

版本: 1.0.0
作者: Data Agent Team
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set, Optional


# ============================================================================
# 配置
# ============================================================================

BACKEND_LOG_DIR = Path("backend/logs")
AI_ACCESSIBLE_LOG = Path("logs/ai_accessible_logs.jsonl")
KNOWLEDGE_LOG_DIR = Path("AgentV2/knowledge/logs")

# 监控的日志文件
LOG_FILES = [
    "application.log",
    "error.log",
    "debug.log",
    "agent.log",
]

# 监控间隔（秒）
POLL_INTERVAL = 2

# 字节偏移记录文件
POSITION_FILE = Path("logs/.monitor_positions.json")


# ============================================================================
# 日志监控器
# ============================================================================

class LogFileMonitor:
    """单个日志文件监控器"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.last_position = 0
        self.last_size = 0

    def check_new_lines(self) -> list[str]:
        """
        检查文件是否有新内容

        Returns:
            新行的列表
        """
        if not self.file_path.exists():
            return []

        current_size = self.file_path.stat().st_size

        # 文件被截断或重置
        if current_size < self.last_size:
            self.last_position = 0
            self.last_size = 0

        # 没有新内容
        if current_size == self.last_size:
            return []

        # 读取新内容
        new_lines = []
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        new_lines.append(line)
                self.last_position = f.tell()
                self.last_size = current_size
        except Exception as e:
            print(f"[ERROR] 读取文件 {self.file_path} 失败: {e}")

        return new_lines


class BackendLogMonitor:
    """后端日志监控服务"""

    def __init__(self):
        self.monitors: Dict[str, LogFileMonitor] = {}
        self.running = False
        self.session_filter: Optional[Set[str]] = None
        self.output_file = AI_ACCESSIBLE_LOG
        self.knowledge_dir = KNOWLEDGE_LOG_DIR

        # 创建输出目录
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        # 加载之前的位置
        self.load_positions()

    def load_positions(self) -> None:
        """加载之前的文件位置"""
        if POSITION_FILE.exists():
            try:
                with open(POSITION_FILE, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                    for file_name, position in positions.items():
                        file_path = BACKEND_LOG_DIR / file_name
                        if file_path.exists():
                            monitor = LogFileMonitor(file_path)
                            monitor.last_position = position
                            self.monitors[file_name] = monitor
                            print(f"[INFO] 恢复 {file_name} 位置: {position}")
            except Exception as e:
                print(f"[WARN] 加载位置文件失败: {e}")

    def save_positions(self) -> None:
        """保存当前文件位置"""
        positions = {
            name: monitor.last_position
            for name, monitor in self.monitors.items()
        }
        try:
            with open(POSITION_FILE, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2)
        except Exception as e:
            print(f"[WARN] 保存位置文件失败: {e}")

    def setup_monitors(self) -> None:
        """设置所有日志文件监控器"""
        # 监控指定的日志文件
        for log_file in LOG_FILES:
            file_path = BACKEND_LOG_DIR / log_file
            if file_path.exists():
                if log_file not in self.monitors:
                    self.monitors[log_file] = LogFileMonitor(file_path)
                    print(f"[INFO] 开始监控: {log_file}")

        # 监控所有 Agent 日期日志
        for agent_log in BACKEND_LOG_DIR.glob("agent_*.log"):
            file_name = agent_log.name
            if file_name not in self.monitors:
                self.monitors[file_name] = LogFileMonitor(agent_log)
                print(f"[INFO] 开始监控: {file_name}")

        print(f"[INFO] 共监控 {len(self.monitors)} 个日志文件")

    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        解析日志行

        Args:
            line: 日志行字符串

        Returns:
            解析后的日志字典
        """
        # 尝试JSON解析
        try:
            log_data = json.loads(line)
            # 添加监控时间戳
            log_data['_monitored_at'] = datetime.now().isoformat()
            return log_data
        except json.JSONDecodeError:
            pass

        # 非JSON日志，转换为简单格式
        return {
            "raw_message": line,
            "timestamp": datetime.now().isoformat(),
            "_monitored_at": datetime.now().isoformat(),
        }

    def process_log(self, log_data: Dict[str, Any]) -> bool:
        """
        处理单条日志

        Args:
            log_data: 日志数据

        Returns:
            是否写入
        """
        # 应用session过滤
        if self.session_filter:
            session_id = log_data.get('session_id')
            if session_id not in self.session_filter:
                return False

        return True

    def write_logs(self, logs: list[Dict[str, Any]]) -> int:
        """
        将日志写入输出文件

        Args:
            logs: 日志列表

        Returns:
            写入的条目数
        """
        if not logs:
            return 0

        written = 0
        try:
            # 写入AI可访问日志
            with open(self.output_file, 'a', encoding='utf-8') as f:
                for log in logs:
                    f.write(json.dumps(log, ensure_ascii=False, default=str) + '\n')
                    written += 1

            # 写入知识库（按日期和session分组）
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_dir = self.knowledge_dir / date_str
            date_dir.mkdir(parents=True, exist_ok=True)

            # 按session_id分组
            session_groups: Dict[str, list] = {}
            for log in logs:
                session_id = log.get('session_id', 'unknown')
                if session_id not in session_groups:
                    session_groups[session_id] = []
                session_groups[session_id].append(log)

            # 写入各session的日志文件
            for session_id, session_logs in session_groups.items():
                session_file = date_dir / f"{session_id}.jsonl"
                try:
                    with open(session_file, 'a', encoding='utf-8') as f:
                        for log in session_logs:
                            f.write(json.dumps(log, ensure_ascii=False, default=str) + '\n')
                except Exception as e:
                    print(f"[ERROR] 写入session日志失败: {e}")

        except Exception as e:
            print(f"[ERROR] 写入日志失败: {e}")
            return 0

        return written

    def check_and_process(self) -> int:
        """
        检查并处理所有新日志

        Returns:
            处理的日志条数
        """
        total_processed = 0
        all_new_logs = []

        for file_name, monitor in self.monitors.items():
            new_lines = monitor.check_new_lines()
            if new_lines:
                print(f"[INFO] {file_name}: 发现 {len(new_lines)} 条新日志")

                for line in new_lines:
                    log_data = self.parse_log_line(line)
                    if log_data and self.process_log(log_data):
                        all_new_logs.append(log_data)

        # 批量写入
        if all_new_logs:
            total_processed = self.write_logs(all_new_logs)

        return total_processed

    def run_once(self) -> None:
        """运行一次检查"""
        self.setup_monitors()
        count = self.check_and_process()
        if count > 0:
            print(f"[INFO] 处理了 {count} 条新日志")
        self.save_positions()

    def run(self, interval: int = POLL_INTERVAL) -> None:
        """
        持续运行监控

        Args:
            interval: 检查间隔（秒）
        """
        print(f"[INFO] 后台日志监控服务启动")
        print(f"[INFO] 监控目录: {BACKEND_LOG_DIR}")
        print(f"[INFO] 输出文件: {self.output_file}")
        print(f"[INFO] 检查间隔: {interval}秒")
        print(f"[INFO] 按 Ctrl+C 停止")

        self.running = True
        self.setup_monitors()

        try:
            while self.running:
                count = self.check_and_process()
                if count > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 处理了 {count} 条新日志")
                    self.save_positions()

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[INFO] 收到停止信号")
        finally:
            self.save_positions()
            print("[INFO] 后台日志监控服务已停止")


# ============================================================================
# 便捷启动脚本
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="后台日志监控服务 - 持续监控后端日志并输出到AI可访问的位置"
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=POLL_INTERVAL,
        help=f'检查间隔（秒），默认 {POLL_INTERVAL}'
    )
    parser.add_argument(
        '--once', '-1',
        action='store_true',
        help='只运行一次检查'
    )
    parser.add_argument(
        '--session', '-s',
        action='append',
        help='只监控指定session的日志'
    )

    args = parser.parse_args()

    # 创建监控器
    monitor = BackendLogMonitor()

    # 设置session过滤
    if args.session:
        monitor.session_filter = set(args.session)
        print(f"[INFO] 只监控 session: {args.session}")

    # 运行
    if args.once:
        print("[INFO] 单次运行模式")
        monitor.run_once()
    else:
        monitor.run(interval=args.interval)


if __name__ == "__main__":
    main()
