"""
修复记忆服务

从历史修复中学习，优化修复策略
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.app.data.models import RepairHistory
from backend.src.app.core.database import get_db


class RepairMemory:
    """修复历史记忆服务"""

    async def find_similar_repairs(
        self,
        error_pattern: str,
        dsl_json: Dict[str, Any],
        tenant_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        查找相似的历史修复

        Args:
            error_pattern: 错误模式名称
            dsl_json: 当前 DSL
            tenant_id: 租户 ID
            limit: 返回数量限制

        Returns:
            相似修复列表
        """
        async for db in get_db():
            # 查询相同错误模式的修复历史
            stmt = select(RepairHistory).where(
                and_(
                    RepairHistory.tenant_id == tenant_id,
                    RepairHistory.error_pattern == error_pattern,
                    RepairHistory.successful == True
                )
            ).order_by(RepairHistory.created_at.desc()).limit(limit)

            result = await db.execute(stmt)
            repairs = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "original_dsl": r.original_dsl,
                    "repaired_dsl": r.repaired_dsl,
                    "error_message": r.error_message,
                    "fix_strategy": r.fix_strategy,
                    "created_at": r.created_at
                }
                for r in repairs
            ]

    async def store_repair(
        self,
        tenant_id: str,
        original_dsl: Dict[str, Any],
        repaired_dsl: Dict[str, Any],
        error_message: str,
        error_pattern: str,
        fix_strategy: str,
        successful: bool = True
    ):
        """存储修复记录"""
        async for db in get_db():
            repair = RepairHistory(
                tenant_id=tenant_id,
                original_dsl=original_dsl,
                repaired_dsl=repaired_dsl,
                error_message=error_message,
                error_pattern=error_pattern,
                fix_strategy=fix_strategy,
                successful=successful
            )

            db.add(repair)
            await db.commit()

    async def get_success_rate(
        self,
        error_pattern: str,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取修复成功率统计"""
        async for db in get_db():
            since = datetime.now() - timedelta(days=days)

            stmt = select(RepairHistory).where(
                and_(
                    RepairHistory.tenant_id == tenant_id,
                    RepairHistory.error_pattern == error_pattern,
                    RepairHistory.created_at >= since
                )
            )

            result = await db.execute(stmt)
            repairs = result.scalars().all()

            if not repairs:
                return {"success_rate": 0.0, "total_repairs": 0}

            successful = sum(1 for r in repairs if r.successful)
            return {
                "success_rate": successful / len(repairs),
                "total_repairs": len(repairs),
                "successful_repairs": successful
            }

    async def get_best_strategy(
        self,
        error_pattern: str,
        tenant_id: str
    ) -> Optional[str]:
        """获取最有效的修复策略"""
        async for db in get_db():
            stmt = select(RepairHistory).where(
                and_(
                    RepairHistory.tenant_id == tenant_id,
                    RepairHistory.error_pattern == error_pattern,
                    RepairHistory.successful == True
                )
            )

            result = await db.execute(stmt)
            repairs = result.scalars().all()

            if not repairs:
                return None

            # 统计各策略的成功次数
            strategy_counts = {}
            for r in repairs:
                strategy = r.fix_strategy
                if strategy not in strategy_counts:
                    strategy_counts[strategy] = 0
                strategy_counts[strategy] += 1

            # 返回最成功的策略
            return max(strategy_counts, key=strategy_counts.get)
