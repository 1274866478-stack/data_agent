"""
# [SQL_ERROR_MEMORIES] SQL错误记忆API端点

## [HEADER]
**文件名**: sql_error_memories.py
**职责**: 提供SQL错误记忆的CRUD接口和统计查询
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-05): 初始版本 - SQL错误记忆API端点

## [INPUT]
- **tenant_id: str** - 租户ID（从JWT token中提取）
- **error_id: int** - 错误记忆ID
- **record_request: SQLErrorRecordRequest** - 记录错误请求
- **db: Session** - 数据库会话（通过依赖注入获取）

## [OUTPUT]
- **error_memory: dict** - 错误记忆字典
- **error_memories: list** - 错误记忆列表
- **stats: dict** - 统计信息
- **few_shot_prompt: str** - Few-shot学习提示

## [LINK]
**上游依赖**:
- [../../data/database.py](../../data/database.py) - get_db(), Session
- [../../data/models.py](../../data/models.py) - SQLErrorMemory模型
- [../../services/sql_error_memory_service.py](../../services/sql_error_memory_service.py) - 错误记忆服务
- [../../middleware/tenant_context.py](../../middleware/tenant_context.py) - get_current_tenant_id

**下游依赖**:
- 无（API端点是叶子模块）

**调用方**:
- 前端管理页面 - 查看和管理错误记忆
- 前端调试工具 - 查看错误统计
- 内部服务 - 记录和检索错误

## [POS]
**路径**: backend/src/app/api/v1/endpoints/sql_error_memories.py
**模块层级**: Level 3 - API端点层
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.app.data.database import get_db
from src.app.data.models import SQLErrorMemory, SQLErrorType
from src.app.services.sql_error_memory_service import (
    get_sql_error_memory_service,
    SQLErrorMemoryService
)
from src.app.middleware.tenant_context import get_current_tenant_id

router = APIRouter()


# ========================================================================
# Pydantic模型用于请求/响应验证
# ========================================================================

class SQLErrorRecordRequest(BaseModel):
    """记录SQL错误请求模型"""
    original_query: str
    error_message: str
    fixed_query: str
    fix_description: Optional[str] = None
    table_name: Optional[str] = None
    schema_context: Optional[Dict[str, Any]] = None


class SQLErrorUpdateRequest(BaseModel):
    """更新SQL错误记忆请求模型"""
    fixed_query: Optional[str] = None
    fix_description: Optional[str] = None


class SQLErrorMemoryResponse(BaseModel):
    """SQL错误记忆响应模型"""
    id: int
    tenant_id: str
    error_pattern_hash: str
    error_type: str
    error_message: str
    original_query: str
    fixed_query: str
    fix_description: Optional[str]
    table_name: Optional[str]
    schema_context: Optional[Dict[str, Any]]
    occurrence_count: int
    last_occurrence: Optional[str]
    success_count: int
    effectiveness_score: float
    created_at: Optional[str]
    updated_at: Optional[str]

    @classmethod
    def from_model(cls, error: SQLErrorMemory) -> "SQLErrorMemoryResponse":
        """从数据库模型转换为响应模型"""
        return cls(
            id=error.id,
            tenant_id=error.tenant_id,
            error_pattern_hash=error.error_pattern_hash,
            error_type=error.error_type.value,
            error_message=error.error_message,
            original_query=error.original_query,
            fixed_query=error.fixed_query,
            fix_description=error.fix_description,
            table_name=error.table_name,
            schema_context=error.schema_context,
            occurrence_count=error.occurrence_count,
            last_occurrence=error.last_occurrence.isoformat() if error.last_occurrence else None,
            success_count=error.success_count,
            effectiveness_score=error.effectiveness_score,
            created_at=error.created_at.isoformat() if error.created_at else None,
            updated_at=error.updated_at.isoformat() if error.updated_at else None
        )


# ========================================================================
# API端点
# ========================================================================

@router.post("/", summary="记录SQL错误", response_model=SQLErrorMemoryResponse)
async def record_sql_error(
    request: SQLErrorRecordRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    service: SQLErrorMemoryService = Depends(get_sql_error_memory_service)
) -> SQLErrorMemoryResponse:
    """
    记录SQL错误及其修复方案

    如果相同的错误模式已存在，则更新统计信息；
    否则创建新的错误记忆记录。
    """
    try:
        error_memory = await service.record_error(
            tenant_id=tenant_id,
            original_query=request.original_query,
            error_message=request.error_message,
            fixed_query=request.fixed_query,
            fix_description=request.fix_description,
            table_name=request.table_name,
            schema_context=request.schema_context
        )
        return SQLErrorMemoryResponse.from_model(error_memory)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record SQL error: {str(e)}"
        )


@router.get("/", summary="获取错误记忆列表", response_model=List[SQLErrorMemoryResponse])
async def get_error_memories(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回的记录数"),
    error_type: Optional[str] = Query(None, description="按错误类型筛选"),
    table_name: Optional[str] = Query(None, description="按表名筛选"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    service: SQLErrorMemoryService = Depends(get_sql_error_memory_service)
) -> List[SQLErrorMemoryResponse]:
    """
    获取当前租户的SQL错误记忆列表

    支持分页和按错误类型/表名筛选。
    """
    try:
        # 如果指定了筛选条件
        if error_type:
            try:
                error_type_enum = SQLErrorType(error_type)
                errors = await service.get_errors_by_type(tenant_id, error_type_enum, limit)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid error_type: {error_type}"
                )
        elif table_name:
            errors = await service.get_errors_by_table(tenant_id, table_name, limit)
        else:
            errors = await service.get_all_errors(tenant_id, skip, limit)

        return [SQLErrorMemoryResponse.from_model(e) for e in errors]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error memories: {str(e)}"
        )


@router.get("/stats", summary="获取错误统计信息")
async def get_error_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    service: SQLErrorMemoryService = Depends(get_sql_error_memory_service)
) -> Dict[str, Any]:
    """
    获取当前租户的SQL错误统计信息

    包括总数、按类型分组、最常出错的表等。
    """
    try:
        stats = await service.get_stats(tenant_id)
        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error stats: {str(e)}"
        )


@router.get("/few-shot", summary="获取Few-shot学习提示")
async def get_few_shot_prompt(
    user_question: str = Query(..., description="用户问题"),
    table_name: Optional[str] = Query(None, description="相关表名"),
    limit: int = Query(3, ge=1, le=10, description="返回的示例数量"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    service: SQLErrorMemoryService = Depends(get_sql_error_memory_service)
) -> Dict[str, Any]:
    """
    获取Few-shot学习提示，包含历史错误示例

    用于在生成SQL时注入到Prompt中。
    """
    try:
        prompt = await service.generate_few_shot_prompt(
            tenant_id=tenant_id,
            user_question=user_question,
            table_name=table_name,
            limit=limit
        )

        return {
            "prompt": prompt,
            "has_examples": len(prompt) > 0,
            "example_count": prompt.count("错误") if prompt else 0
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate few-shot prompt: {str(e)}"
        )


@router.get("/{error_id}", summary="获取单个错误记忆", response_model=SQLErrorMemoryResponse)
async def get_error_memory(
    error_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> SQLErrorMemoryResponse:
    """获取指定ID的错误记忆详情"""
    try:
        error = db.query(SQLErrorMemory).filter(
            SQLErrorMemory.id == error_id,
            SQLErrorMemory.tenant_id == tenant_id
        ).first()

        if not error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error memory with id {error_id} not found"
            )

        return SQLErrorMemoryResponse.from_model(error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error memory: {str(e)}"
        )


@router.put("/{error_id}", summary="更新错误记忆", response_model=SQLErrorMemoryResponse)
async def update_error_memory(
    error_id: int,
    request: SQLErrorUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> SQLErrorMemoryResponse:
    """
    更新指定ID的错误记忆

    只允许更新修复方案和说明。
    """
    try:
        error = db.query(SQLErrorMemory).filter(
            SQLErrorMemory.id == error_id,
            SQLErrorMemory.tenant_id == tenant_id
        ).first()

        if not error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error memory with id {error_id} not found"
            )

        # 更新允许的字段
        if request.fixed_query is not None:
            error.fixed_query = request.fixed_query
        if request.fix_description is not None:
            error.fix_description = request.fix_description

        error.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(error)

        return SQLErrorMemoryResponse.from_model(error)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update error memory: {str(e)}"
        )


@router.delete("/{error_id}", summary="删除错误记忆")
async def delete_error_memory(
    error_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    service: SQLErrorMemoryService = Depends(get_sql_error_memory_service)
) -> Dict[str, Any]:
    """删除指定ID的错误记忆"""
    try:
        success = await service.delete_error(error_id, tenant_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error memory with id {error_id} not found"
            )

        return {
            "success": True,
            "message": f"Error memory {error_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete error memory: {str(e)}"
        )


@router.post("/{error_id}/mark-success", summary="标记修复成功")
async def mark_error_success(
    error_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    service: SQLErrorMemoryService = Depends(get_sql_error_memory_service)
) -> Dict[str, Any]:
    """
    标记错误修复为成功

    应用此修复方案后查询成功，增加成功计数。
    """
    try:
        # 先获取错误以获取哈希
        error = db.query(SQLErrorMemory).filter(
            SQLErrorMemory.id == error_id,
            SQLErrorMemory.tenant_id == tenant_id
        ).first()

        if not error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error memory with id {error_id} not found"
            )

        success = await service.mark_success(error.error_pattern_hash)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark error as success"
            )

        return {
            "success": True,
            "message": f"Error memory {error_id} marked as successful",
            "success_count": error.success_count + 1
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark error success: {str(e)}"
        )


@router.delete("/clear-old", summary="清理旧错误记忆")
async def clear_old_errors(
    days: int = Query(90, ge=1, le=365, description="保留天数"),
    keep_effective: bool = Query(True, description="是否保留有效性高的记录"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    service: SQLErrorMemoryService = Depends(get_sql_error_memory_service)
) -> Dict[str, Any]:
    """
    清理旧的错误记忆

    删除指定天数之前的错误记录，可选择保留有效性高的记录。
    """
    try:
        deleted_count = await service.clear_old_errors(
            tenant_id=tenant_id,
            days=days,
            keep_effective=keep_effective
        )

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleared {deleted_count} old error memories"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear old errors: {str(e)}"
        )


# 导入timezone
from datetime import timezone
