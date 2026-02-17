# -*- coding: utf-8 -*-
"""
AgentLogger - 统一日志收集器
=============================

双通道日志写入：
    - 数据库 (PostgreSQL agent_logs 表)
    - 文件 (logs/agent_YYYY-MM-DD.log)

核心功能:
    - 记录 Agent 执行的每一步
    - 记录工具调用和 AI 推理过程
    - 异步批量写入，降低性能影响

作者: BMad Master
版本: 1.0.0
"""

import json
import asyncio
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class AgentLogger:
    """
    统一日志收集器 - 双通道写入

    支持将 Agent 执行日志同时写入数据库和文件。

    使用示例:
    ```python
    agent_logger = AgentLogger(
        tenant_id="tenant_123",
        session_id="session_abc",
        user_id="user_456"
    )

    await agent_logger.log_step(
        step=1,
        node="sql_generator",
        message_type="ai_message",
        content={"query": "SELECT * FROM users"},
        raw_message="生成SQL查询",
        metadata={"tokens": 100}
    )

    await agent_logger.close()
    ```
    """

    # 批量写入阈值
    DB_BATCH_SIZE = 10
    FILE_BATCH_SIZE = 10

    def __init__(
        self,
        tenant_id: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        log_to_db: bool = True,
        log_to_file: bool = True,
        log_dir: str = "logs"
    ):
        """
        初始化 AgentLogger

        Args:
            tenant_id: 租户 ID
            session_id: 会话 ID (可选，自动生成)
            user_id: 用户 ID (可选)
            log_to_db: 是否写入数据库
            log_to_file: 是否写入文件
            log_dir: 日志文件目录
        """
        self.tenant_id = tenant_id
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.log_to_db = log_to_db
        self.log_to_file = log_to_file
        self.log_dir = Path(log_dir)

        # 缓存当前步骤计数
        self._step_counter = 0

        # 文件写入缓冲区
        self._file_buffer: List[str] = []

        # 数据库写入缓冲区
        self._db_buffer: List[Dict[str, Any]] = []

        # 数据库会话 (延迟获取)
        self._db_session = None

        # 是否已关闭
        self._closed = False

    def _get_db_session(self):
        """获取数据库会话（延迟导入）"""
        if self._db_session is None:
            try:
                import sys
                from pathlib import Path

                # 添加 backend/src 到路径
                backend_src = Path(__file__).resolve().parent.parent.parent / "backend" / "src"
                if str(backend_src) not in sys.path:
                    sys.path.insert(0, str(backend_src))

                from app.data.database import get_db
                # 获取生成器
                db_gen = get_db()
                self._db_session = next(db_gen)
            except Exception as e:
                logger.warning(f"[AgentLogger] 无法获取数据库会话: {e}")
                self._db_session = False  # 标记为失败

        return self._db_session if self._db_session is not False else None

    async def log_step(
        self,
        step: Optional[int] = None,
        node: str = "unknown",
        message_type: str = "info",
        content: Optional[Dict[str, Any]] = None,
        raw_message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录一步执行

        Args:
            step: 步骤编号 (可选，自动递增)
            node: 节点名称
            message_type: 消息类型 (ai_message, tool_call, error 等)
            content: 结构化数据
            raw_message: 人类可读文本
            metadata: 扩展字段（耗时、token等）
        """
        if self._closed:
            logger.warning("[AgentLogger] 尝试写入已关闭的日志记录器")
            return

        # 自动递增步骤
        if step is None:
            self._step_counter += 1
            step = self._step_counter
        else:
            self._step_counter = max(self._step_counter, step)

        # 构建日志条目
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "step_number": step,
            "node_name": node,
            "message_type": message_type,
            "content": content or {},
            "raw_message": raw_message,
            "metadata": metadata or {}
        }

        # 保持原有 print 输出
        print(f"🔹 [{node}] {raw_message}")

        # 双通道写入
        tasks = []
        if self.log_to_db:
            tasks.append(self._write_to_db(log_entry))
        if self.log_to_file:
            tasks.append(self._write_to_file(log_entry))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _write_to_db(self, entry: dict):
        """异步批量写入数据库"""
        if not self.log_to_db:
            return

        self._db_buffer.append(entry)

        if len(self._db_buffer) >= self.DB_BATCH_SIZE:
            await self._flush_db()

    async def _write_to_file(self, entry: dict):
        """写入文件日志"""
        if not self.log_to_file:
            return

        log_line = json.dumps(entry, ensure_ascii=False)
        self._file_buffer.append(log_line)

        if len(self._file_buffer) >= self.FILE_BATCH_SIZE:
            await self._flush_file()

    async def _flush_db(self):
        """刷新数据库缓冲区"""
        if not self._db_buffer:
            return

        entries = self._db_buffer.copy()
        self._db_buffer.clear()

        try:
            db_session = self._get_db_session()
            if db_session is None:
                # 数据库不可用，写入备用文件
                self._write_to_backup_file(entries)
                return

            # 导入模型
            try:
                import sys
                from pathlib import Path

                backend_src = Path(__file__).resolve().parent.parent.parent / "backend" / "src"
                if str(backend_src) not in sys.path:
                    sys.path.insert(0, str(backend_src))

                from app.data.models import AgentLog

                for entry in entries:
                    log_record = AgentLog(
                        tenant_id=entry["tenant_id"],
                        session_id=entry["session_id"],
                        user_id=entry["user_id"],
                        step_number=entry["step_number"],
                        node_name=entry["node_name"],
                        message_type=entry["message_type"],
                        content=entry["content"],
                        raw_message=entry["raw_message"],
                        log_metadata=entry.get("metadata")  # 使用 log_metadata 参数
                    )
                    db_session.add(log_record)

                db_session.commit()
                logger.debug(f"[AgentLogger] 已写入 {len(entries)} 条日志到数据库")

            except Exception as e:
                logger.error(f"[AgentLogger] 数据库写入失败: {e}")
                self._write_to_backup_file(entries)

        except Exception as e:
            logger.error(f"[AgentLogger] 刷新数据库缓冲区失败: {e}")
            self._write_to_backup_file(entries)

    def _write_to_backup_file(self, entries: List[Dict[str, Any]]):
        """写入备用文件（当数据库不可用时）"""
        try:
            backup_dir = self.log_dir / "backup"
            backup_dir.mkdir(parents=True, exist_ok=True)

            date_str = datetime.now().strftime('%Y-%m-%d')
            backup_file = backup_dir / f"agent_backup_{date_str}.jsonl"

            with open(backup_file, 'a', encoding='utf-8') as f:
                for entry in entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')

            logger.info(f"[AgentLogger] 已写入 {len(entries)} 条日志到备用文件: {backup_file}")
        except Exception as e:
            logger.error(f"[AgentLogger] 写入备用文件失败: {e}")

    async def _flush_file(self):
        """刷新文件缓冲区"""
        if not self._file_buffer:
            return

        lines = self._file_buffer.copy()
        self._file_buffer.clear()

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            date_str = datetime.now().strftime('%Y-%m-%d')
            log_path = self.log_dir / f"agent_{date_str}.log"

            with open(log_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')

        except Exception as e:
            logger.error(f"[AgentLogger] 写入文件失败: {e}")

    async def close(self):
        """关闭时刷新缓冲区"""
        if self._closed:
            return

        self._closed = True

        # 刷新所有缓冲区
        await self._flush_db()
        await self._flush_file()

        # 关闭数据库会话
        if self._db_session and hasattr(self._db_session, 'close'):
            try:
                self._db_session.close()
            except Exception as e:
                logger.warning(f"[AgentLogger] 关闭数据库会话失败: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    def get_session_id(self) -> str:
        """获取会话 ID"""
        return self.session_id

    def get_step_count(self) -> int:
        """获取当前步骤数"""
        return self._step_counter


# ============================================================================
# 便捷函数
# ============================================================================

_logger_cache: Dict[str, AgentLogger] = {}


def get_agent_logger(
    tenant_id: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    log_to_db: bool = True,
    log_to_file: bool = True
) -> AgentLogger:
    """
    获取或创建 AgentLogger 实例

    Args:
        tenant_id: 租户 ID
        session_id: 会话 ID
        user_id: 用户 ID
        log_to_db: 是否写入数据库
        log_to_file: 是否写入文件

    Returns:
        AgentLogger 实例
    """
    cache_key = f"{tenant_id}_{session_id or 'new'}_{user_id or 'none'}"

    if cache_key not in _logger_cache:
        _logger_cache[cache_key] = AgentLogger(
            tenant_id=tenant_id,
            session_id=session_id,
            user_id=user_id,
            log_to_db=log_to_db,
            log_to_file=log_to_file
        )

    return _logger_cache[cache_key]


def clear_logger_cache():
    """清除日志记录器缓存"""
    _logger_cache.clear()


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_logger():
        """测试 AgentLogger"""
        print("=" * 60)
        print("AgentLogger 测试")
        print("=" * 60)

        # 创建日志记录器
        async with AgentLogger(
            tenant_id="test_tenant",
            user_id="test_user",
            log_to_db=False,  # 测试时不写数据库
            log_to_file=True
        ) as logger:
            # 记录一些步骤
            await logger.log_step(
                step=1,
                node="sql_generator",
                message_type="ai_message",
                content={"query": "SELECT * FROM users"},
                raw_message="生成SQL查询"
            )

            await logger.log_step(
                step=2,
                node="database_executor",
                message_type="tool_call",
                content={"tool": "execute_query", "rows": 10},
                raw_message="执行查询，返回10行",
                metadata={"duration_ms": 150}
            )

            await logger.log_step(
                step=3,
                node="response_formatter",
                message_type="ai_message",
                content={"answer": "查询成功，找到10个用户"},
                raw_message="格式化响应"
            )

        print("\n[PASS] AgentLogger 测试完成")
        print(f"日志文件: logs/agent_{datetime.now().strftime('%Y-%m-%d')}.log")

    asyncio.run(test_logger())
