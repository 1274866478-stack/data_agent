"""
# [SQL_ERROR_MEMORY_SERVICE] SQL错误记忆服务

## [HEADER]
**文件名**: sql_error_memory_service.py
**职责**: 实现SQL错误记录、分类、检索和学习功能，让AI从错误中持续改进
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-05): 初始版本 - SQL错误记忆系统

## [INPUT]
- **tenant_id: str** - 租户ID（必需，确保租户隔离）
- **original_query: str** - 原始错误SQL
- **error_message: str** - 数据库返回的错误信息
- **fixed_query: str** - 修复后的SQL
- **table_name: Optional[str]** - 涉及的主表名
- **schema_context: Optional[Dict]** - Schema上下文
- **user_question: Optional[str]** - 用户原始问题（用于相关性检索）

## [OUTPUT]
- **SQLErrorMemory**: 错误记忆对象
- **List[SQLErrorMemory]**: 错误记忆列表
- **str**: Few-shot学习提示文本
- **Dict[str, Any]**: 统计信息

## [LINK]
**上游依赖**:
- [../data/models.py](../data/models.py) - SQLErrorMemory模型
- [../data/database.py](../data/database.py) - 数据库连接

**下游依赖**:
- [../api/v1/endpoints/sql_error_memories.py](../api/v1/endpoints/sql_error_memories.py) - API端点
- [../../Agent/sql_agent.py](../../../Agent/sql_agent.py) - SQL Agent集成
- [./llm_service.py](./llm_service.py) - LLM服务集成

**调用方**:
- SQL Agent修复SQL后记录错误
- LLM服务生成SQL时检索历史错误
- 管理API查看和管理错误记忆

## [STATE]
- **数据库会话**: 通过__init__注入
- **哈希算法**: SHA256用于生成错误模式指纹

## [SIDE-EFFECTS**
- **数据库写入**: 记录新错误或更新现有错误
- **统计更新**: 自动增加出现次数和成功次数
"""

import hashlib
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import Depends

from src.app.data.models import SQLErrorMemory, SQLErrorType
from src.app.data.database import get_db

logger = logging.getLogger(__name__)


class SQLErrorMemoryService:
    """SQL错误记忆服务 - 让AI从错误中学习"""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # 错误分类与哈希
    # ========================================================================

    def classify_error(self, error_message: str) -> SQLErrorType:
        """
        根据错误信息智能分类错误类型

        Args:
            error_message: 数据库返回的错误信息

        Returns:
            SQLErrorType: 错误类型枚举
        """
        error_lower = error_message.lower()

        # 列不存在
        if any(pattern in error_lower for pattern in [
            'column', 'does not exist', 'unknown column', 'no such column'
        ]):
            # 检查是否是歧义错误
            if 'ambiguous' in error_lower:
                return SQLErrorType.AMBIGUOUS_COLUMN
            return SQLErrorType.COLUMN_NOT_EXIST

        # 表不存在
        if any(pattern in error_lower for pattern in [
            'table', 'does not exist', 'unknown table', 'no such table', 'relation'
        ]):
            return SQLErrorType.TABLE_NOT_EXIST

        # 语法错误
        if any(pattern in error_lower for pattern in [
            'syntax error', 'syntax error at or near', 'invalid syntax'
        ]):
            return SQLErrorType.SYNTAX_ERROR

        # 类型不匹配
        if any(pattern in error_lower for pattern in [
            'type', 'cast', 'conversion', 'integer', 'text', 'cannot be cast'
        ]):
            return SQLErrorType.TYPE_MISMATCH

        # 关系/JOIN错误
        if any(pattern in error_lower for pattern in [
            'join', 'relation', 'missing from-clause', 'invalid reference'
        ]):
            return SQLErrorType.RELATION_ERROR

        # 聚合函数错误
        if any(pattern in error_lower for pattern in [
            'aggregate', 'group by', 'must appear in the group by clause'
        ]):
            if 'group by' in error_lower:
                return SQLErrorType.GROUP_BY_ERROR
            return SQLErrorType.AGGREGATE_ERROR

        return SQLErrorType.OTHER

    def generate_error_pattern_hash(
        self,
        error_type: SQLErrorType,
        table_name: Optional[str],
        error_message: str
    ) -> str:
        """
        生成错误模式哈希，用于识别相同的错误模式

        策略：
        1. 提取错误中的关键信息（列名、表名）
        2. 规范化SQL（去除具体值）
        3. 生成SHA256哈希

        Args:
            error_type: 错误类型
            table_name: 涉及的表名
            error_message: 错误信息

        Returns:
            str: SHA256哈希值（十六进制）
        """
        # 提取关键信息
        key_parts = [error_type.value]

        if table_name:
            key_parts.append(f"table:{table_name}")

        # 从错误信息中提取列名（常见模式）
        column_match = re.search(r'column ["\']?(\w+)["\']?', error_message, re.IGNORECASE)
        if column_match:
            key_parts.append(f"column:{column_match.group(1).lower()}")

        # 创建规范化的错误模式字符串
        pattern = "|".join(key_parts)

        # 生成SHA256哈希
        return hashlib.sha256(pattern.encode('utf-8')).hexdigest()

    def normalize_sql_for_hash(self, sql: str) -> str:
        """
        规范化SQL用于哈希计算（去除具体值）

        Args:
            sql: 原始SQL

        Returns:
            str: 规范化后的SQL
        """
        # 移除字符串字面量
        sql = re.sub(r"'[^']*'", "'X'", sql)
        # 移除数字字面量
        sql = re.sub(r'\b\d+\b', 'N', sql)
        # 移除多余空白
        sql = re.sub(r'\s+', ' ', sql).strip()
        return sql.lower()

    # ========================================================================
    # 错误记录
    # ========================================================================

    async def record_error(
        self,
        tenant_id: str,
        original_query: str,
        error_message: str,
        fixed_query: str,
        fix_description: Optional[str] = None,
        table_name: Optional[str] = None,
        schema_context: Optional[Dict[str, Any]] = None
    ) -> SQLErrorMemory:
        """
        记录SQL错误及其修复方案

        如果相同的错误模式已存在，则更新统计信息；
        否则创建新的错误记忆记录。

        Args:
            tenant_id: 租户ID
            original_query: 原始错误SQL
            error_message: 数据库错误信息
            fixed_query: 修复后的SQL
            fix_description: 修复说明（可选）
            table_name: 涉及的表名（可选）
            schema_context: Schema上下文（可选）

        Returns:
            SQLErrorMemory: 创建或更新的错误记忆对象
        """
        # 1. 分类错误
        error_type = self.classify_error(error_message)

        # 2. 提取表名（如果未提供）
        if not table_name:
            table_match = re.search(r'from ["\']?(\w+)["\']?', original_query, re.IGNORECASE)
            if table_match:
                table_name = table_match.group(1).lower()

        # 3. 生成错误模式哈希
        error_hash = self.generate_error_pattern_hash(error_type, table_name, error_message)

        # 4. 检查是否已存在相同错误模式
        existing = self.db.query(SQLErrorMemory).filter(
            and_(
                SQLErrorMemory.tenant_id == tenant_id,
                SQLErrorMemory.error_pattern_hash == error_hash
            )
        ).first()

        if existing:
            # 更新现有记录
            existing.increment_occurrence()
            # 如果有更好的修复方案，更新它
            if fixed_query and fixed_query != existing.fixed_query:
                existing.fixed_query = fixed_query
                existing.fix_description = fix_description or existing.fix_description
                # 更新schema上下文（如果更新）
                if schema_context:
                    existing.schema_context = schema_context

            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated existing error memory: {error_hash[:8]}... (occurrence: {existing.occurrence_count})")
            return existing

        # 5. 创建新记录
        error_memory = SQLErrorMemory(
            tenant_id=tenant_id,
            error_pattern_hash=error_hash,
            error_type=error_type,
            error_message=error_message,
            original_query=original_query,
            fixed_query=fixed_query,
            fix_description=fix_description or self._generate_fix_description(error_type, error_message),
            table_name=table_name,
            schema_context=schema_context,
            occurrence_count=1,
            last_occurrence=datetime.now(timezone.utc)
        )

        self.db.add(error_memory)
        self.db.commit()
        self.db.refresh(error_memory)

        logger.info(f"Created new error memory: {error_hash[:8]}... for tenant {tenant_id}")
        return error_memory

    def _generate_fix_description(self, error_type: SQLErrorType, error_message: str) -> str:
        """自动生成修复说明"""
        descriptions = {
            SQLErrorType.COLUMN_NOT_EXIST: "列名不存在，已更正为正确的列名",
            SQLErrorType.TABLE_NOT_EXIST: "表名不存在，已更正为正确的表名",
            SQLErrorType.SYNTAX_ERROR: "SQL语法错误，已修复语法问题",
            SQLErrorType.AMBIGUOUS_COLUMN: "列名歧义，已添加表前缀限定",
            SQLErrorType.TYPE_MISMATCH: "数据类型不匹配，已进行类型转换",
            SQLErrorType.RELATION_ERROR: "表关系错误，已修复JOIN条件",
            SQLErrorType.AGGREGATE_ERROR: "聚合函数错误，已修复",
            SQLErrorType.GROUP_BY_ERROR: "GROUP BY错误，已修复聚合列",
        }
        return descriptions.get(error_type, "SQL错误已修复")

    # ========================================================================
    # 错误检索
    # ========================================================================

    async def get_relevant_errors(
        self,
        tenant_id: str,
        user_question: str,
        table_name: Optional[str] = None,
        limit: int = 5
    ) -> List[SQLErrorMemory]:
        """
        获取与当前查询相关的历史错误

        检索策略：
        1. 如果指定表名，优先检索该表相关的错误
        2. 按出现次数降序排序（高频率错误优先）
        3. 按有效性分数降序排序（高成功率优先）

        Args:
            tenant_id: 租户ID
            user_question: 用户问题（用于语义匹配，暂未实现）
            table_name: 相关表名（可选）
            limit: 返回结果数量上限

        Returns:
            List[SQLErrorMemory]: 相关错误记忆列表
        """
        query = self.db.query(SQLErrorMemory).filter(
            SQLErrorMemory.tenant_id == tenant_id
        )

        # 如果指定表名，优先检索该表相关错误
        if table_name:
            query = query.filter(
                or_(
                    SQLErrorMemory.table_name == table_name,
                    SQLErrorMemory.table_name.is_(None)  # 也包含通用错误
                )
            )

        # 按出现次数和有效性排序
        query = query.order_by(
            SQLErrorMemory.occurrence_count.desc(),
            SQLErrorMemory.success_count.desc()
        )

        results = query.limit(limit).all()
        logger.info(f"Found {len(results)} relevant errors for tenant {tenant_id}, table {table_name}")
        return results

    async def get_errors_by_type(
        self,
        tenant_id: str,
        error_type: SQLErrorType,
        limit: int = 20
    ) -> List[SQLErrorMemory]:
        """按错误类型检索错误记忆"""
        return self.db.query(SQLErrorMemory).filter(
            and_(
                SQLErrorMemory.tenant_id == tenant_id,
                SQLErrorMemory.error_type == error_type
            )
        ).order_by(
            SQLErrorMemory.occurrence_count.desc()
        ).limit(limit).all()

    async def get_errors_by_table(
        self,
        tenant_id: str,
        table_name: str,
        limit: int = 20
    ) -> List[SQLErrorMemory]:
        """按表名检索错误记忆"""
        return self.db.query(SQLErrorMemory).filter(
            and_(
                SQLErrorMemory.tenant_id == tenant_id,
                SQLErrorMemory.table_name == table_name
            )
        ).order_by(
            SQLErrorMemory.occurrence_count.desc()
        ).limit(limit).all()

    async def get_error_by_hash(self, error_hash: str) -> Optional[SQLErrorMemory]:
        """通过哈希值获取错误记忆"""
        return self.db.query(SQLErrorMemory).filter(
            SQLErrorMemory.error_pattern_hash == error_hash
        ).first()

    async def get_all_errors(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[SQLErrorMemory]:
        """获取租户的所有错误记忆（分页）"""
        return self.db.query(SQLErrorMemory).filter(
            SQLErrorMemory.tenant_id == tenant_id
        ).order_by(
            SQLErrorMemory.occurrence_count.desc(),
            SQLErrorMemory.last_occurrence.desc()
        ).offset(skip).limit(limit).all()

    # ========================================================================
    # Few-shot学习提示生成
    # ========================================================================

    async def generate_few_shot_prompt(
        self,
        tenant_id: str,
        user_question: str,
        table_name: Optional[str] = None,
        limit: int = 3
    ) -> str:
        """
        生成Few-shot学习提示，包含历史错误示例

        Args:
            tenant_id: 租户ID
            user_question: 用户问题
            table_name: 相关表名（可选）
            limit: 包含的示例数量

        Returns:
            str: Few-shot学习提示文本
        """
        errors = await self.get_relevant_errors(tenant_id, user_question, table_name, limit)

        if not errors:
            return ""

        prompt_parts = [
            "以下是与此查询相关的历史SQL错误及修复方案（请避免重复这些错误）：\n"
        ]

        for i, error in enumerate(errors, 1):
            error_type_text = {
                SQLErrorType.COLUMN_NOT_EXIST: "列名不存在",
                SQLErrorType.TABLE_NOT_EXIST: "表不存在",
                SQLErrorType.SYNTAX_ERROR: "语法错误",
                SQLErrorType.AMBIGUOUS_COLUMN: "列名歧义",
                SQLErrorType.TYPE_MISMATCH: "类型不匹配",
                SQLErrorType.RELATION_ERROR: "关系错误",
                SQLErrorType.AGGREGATE_ERROR: "聚合函数错误",
                SQLErrorType.GROUP_BY_ERROR: "GROUP BY错误",
            }.get(error.error_type, "其他错误")

            prompt_parts.append(f"错误{i}：{error_type_text} (已出现{error.occurrence_count}次)")
            prompt_parts.append(f"- 原始SQL: {error.original_query}")
            prompt_parts.append(f"- 错误信息: {error.error_message}")
            prompt_parts.append(f"- 修复方案: {error.fixed_query}")
            if error.fix_description:
                prompt_parts.append(f"- 说明: {error.fix_description}")
            prompt_parts.append("")

        return "\n".join(prompt_parts)

    # ========================================================================
    # 统计信息
    # ========================================================================

    async def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户的错误记忆统计信息"""
        total_errors = self.db.query(SQLErrorMemory).filter(
            SQLErrorMemory.tenant_id == tenant_id
        ).count()

        # 按类型分组统计
        type_stats = {}
        for error_type in SQLErrorType:
            count = self.db.query(SQLErrorMemory).filter(
                and_(
                    SQLErrorMemory.tenant_id == tenant_id,
                    SQLErrorMemory.error_type == error_type
                )
            ).count()
            if count > 0:
                type_stats[error_type.value] = count

        # 最常出错的表
        table_stats = self.db.query(
            SQLErrorMemory.table_name,
            func.count(SQLErrorMemory.id).label('count')
        ).filter(
            and_(
                SQLErrorMemory.tenant_id == tenant_id,
                SQLErrorMemory.table_name.isnot(None)
            )
        ).group_by(SQLErrorMemory.table_name).order_by(
            func.count(SQLErrorMemory.id).desc()
        ).limit(10).all()

        return {
            "total_errors": total_errors,
            "by_type": type_stats,
            "top_tables": [{"table": t[0], "count": t[1]} for t in table_stats]
        }

    # ========================================================================
    # 管理操作
    # ========================================================================

    async def mark_success(self, error_hash: str) -> bool:
        """
        标记错误修复为成功（应用此修复后查询成功）

        Args:
            error_hash: 错误模式哈希

        Returns:
            bool: 是否成功标记
        """
        error = await self.get_error_by_hash(error_hash)
        if error:
            error.increment_success()
            self.db.commit()
            logger.info(f"Marked error {error_hash[:8]}... as success (total: {error.success_count})")
            return True
        return False

    async def delete_error(self, error_id: int, tenant_id: str) -> bool:
        """
        删除错误记忆

        Args:
            error_id: 错误记忆ID
            tenant_id: 租户ID（安全检查）

        Returns:
            bool: 是否成功删除
        """
        error = self.db.query(SQLErrorMemory).filter(
            and_(
                SQLErrorMemory.id == error_id,
                SQLErrorMemory.tenant_id == tenant_id
            )
        ).first()

        if error:
            self.db.delete(error)
            self.db.commit()
            logger.info(f"Deleted error memory {error_id} for tenant {tenant_id}")
            return True
        return False

    async def clear_old_errors(
        self,
        tenant_id: str,
        days: int = 90,
        keep_effective: bool = True
    ) -> int:
        """
        清理旧的错误记忆

        Args:
            tenant_id: 租户ID
            days: 保留天数
            keep_effective: 是否保留有效性高的记录（effectiveness_score > 0.5）

        Returns:
            int: 删除的记录数
        """
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = self.db.query(SQLErrorMemory).filter(
            and_(
                SQLErrorMemory.tenant_id == tenant_id,
                SQLErrorMemory.created_at < cutoff_date
            )
        )

        if keep_effective:
            # 保留有效的记录
            all_to_delete = query.all()
            to_delete = [e for e in all_to_delete if e.effectiveness_score < 0.5]
        else:
            to_delete = query.all()

        count = len(to_delete)
        for error in to_delete:
            self.db.delete(error)

        self.db.commit()
        logger.info(f"Cleared {count} old error memories for tenant {tenant_id}")
        return count


# 依赖注入函数
def get_sql_error_memory_service(db: Session = Depends(get_db)) -> SQLErrorMemoryService:
    """FastAPI依赖注入：获取SQL错误记忆服务实例"""
    return SQLErrorMemoryService(db)


# 导入func用于统计查询
from sqlalchemy import func
