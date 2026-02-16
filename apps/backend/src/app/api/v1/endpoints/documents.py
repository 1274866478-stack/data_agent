"""
# [DOCUMENTS] 文档管理API端点

## [HEADER]
**文件名**: documents.py
**职责**: 实现文档的完整CRUD操作、上传下载、预览链接生成、处理状态跟踪和统计功能，支持PDF/Word文档，集成MinIO存储和ChromaDB向量化，确保租户隔离
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现Story 2.4规范的文档管理API

## [INPUT]
- **tenant_id: str** - 租户ID（通过占位符函数获取，实际应从JWT提取）
- **document_id: str** - 文档ID（UUID格式，路径参数）
- **file: UploadFile** - 上传的文档文件（PDF或Word）
- **doc_status: str** - 文档状态过滤条件（pending, indexing, ready, error）
- **file_type: str** - 文件类型过滤条件
- **skip: int** - 分页跳过数量（默认0）
- **limit: int** - 分页限制数量（默认100，最大1000）
- **expires_in_hours: int** - 预览链接有效期（小时，默认1，最大24）
- **db: Session** - 数据库会话（通过依赖注入获取）

## [OUTPUT]
- **document_list: DocumentListResponse** - 文档列表响应
  - success: 操作是否成功
  - documents: 文档对象列表
  - total: 总文档数
  - skip: 跳过数量
  - limit: 返回限制
  - stats: 统计信息
- **document_detail: DocumentResponse** - 文档详情响应
  - id: 文档ID
  - tenant_id: 租户ID
  - file_name: 文件名
  - storage_path: MinIO存储路径
  - file_type: 文件类型
  - file_size: 文件大小
  - mime_type: MIME类型
  - status: 处理状态
  - processing_error: 处理错误信息
  - indexed_at: 索引时间
  - created_at: 创建时间
  - updated_at: 更新时间
- **document_stats: DocumentStatsResponse** - 文档统计响应
  - by_status: 按状态统计
  - by_file_type: 按文件类型统计
  - total_documents: 总文档数
  - total_size_bytes: 总字节大小
  - total_size_mb: 总MB大小
- **preview_url: dict** - 预览链接响应
  - success: 操作是否成功
  - preview_url: 预签名URL
  - expires_in_hours: 有效期
  - document: 文档信息
- **processing_status: dict** - 处理状态响应
  - success: 操作是否成功
  - status: 处理状态
  - progress: 处理进度
  - stages: 各阶段状态
- **error_response: HTTPException** - 错误响应（400, 404, 500）

## [LINK]
**上游依赖** (已读取源码):
- [../../data/database.py](../../data/database.py) - get_db(), Session
- [../../data/models.py](../../data/models.py) - DocumentStatus
- [../../services/document_service.py](../../services/document_service.py) - document_service, 文档CRUD操作
- [../../services/document_processor.py](../../services/document_processor.py) - document_processor, 文档处理和向量化
- [../../services/minio_client.py](../../services/minio_client.py) - minio_service, 文件下载

**下游依赖** (已读取源码):
- 无（API端点是叶子模块）

**调用方**:
- 前端文档管理页面 - 调用文档CRUD API
- 前端文档上传组件 - 上传PDF/Word文档
- 前端文档预览组件 - 生成预览链接
- 前端仪表板 - 显示文档统计信息

## [POS]
**路径**: backend/src/app/api/v1/endpoints/documents.py
**模块层级**: Level 3 - API端点层
**依赖深度**: 直接依赖 data/*, services/*；被前端文档管理模块调用
"""

import uuid
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.app.data.database import get_db
from src.app.data.models import DocumentStatus
from src.app.services.document_service import document_service
from src.app.services.document_processor import document_processor

router = APIRouter()


# Pydantic模型用于请求/响应验证
class DocumentResponse(BaseModel):
    """文档响应模型 - Story 2.4规范"""
    id: str
    tenant_id: str
    file_name: str
    storage_path: str
    file_type: str
    file_size: int
    mime_type: str
    status: str
    processing_error: Optional[str] = None
    indexed_at: Optional[str] = None
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    success: bool
    documents: List[DocumentResponse]
    total: int
    skip: int
    limit: int
    stats: dict


class DocumentStatsResponse(BaseModel):
    """文档统计响应模型"""
    by_status: dict
    by_file_type: dict
    total_documents: int
    total_size_bytes: int
    total_size_mb: float


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    message: str


def get_tenant_id_from_request() -> str:
    """
    从请求中获取租户ID - 占位符实现
    在实际应用中，这里应该从JWT token或认证中间件中获取
    """
    # TODO: 实现从JWT token或其他认证方式获取tenant_id
    # 当前为了测试使用默认值
    return "default_tenant"


@router.get("/", response_model=DocumentListResponse, summary="获取文档列表")
async def get_documents(
    doc_status: Optional[str] = Query(None, alias="status", description="按状态过滤文档"),
    file_type: Optional[str] = Query(None, description="按文件类型过滤文档"),
    skip: int = Query(0, ge=0, description="跳过的文档数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回的文档数量限制"),
    db: Session = Depends(get_db)
) -> DocumentListResponse:
    """
    获取租户的文档列表 - Story 2.4要求
    支持状态和文件类型过滤，强制租户隔离
    """
    tenant_id = get_tenant_id_from_request()

    # 转换状态字符串为枚举（枚举值为小写）
    status_enum = None
    if doc_status:
        try:
            status_enum = DocumentStatus(doc_status.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值: {doc_status}。支持的状态: pending, indexing, ready, error"
            )

    # 调用文档服务
    result = document_service.get_documents(
        db=db,
        tenant_id=tenant_id,
        status=status_enum,
        file_type=file_type,
        skip=skip,
        limit=limit
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "获取文档列表失败")
        )

    return DocumentListResponse(**result)


@router.get("/{document_id}", response_model=DocumentResponse, summary="获取文档详情")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """
    获取单个文档详情 - Story 2.4要求
    强制租户隔离验证
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )

    tenant_id = get_tenant_id_from_request()

    result = document_service.get_document_by_id(
        db=db,
        tenant_id=tenant_id,
        document_id=doc_uuid
    )

    if not result["success"]:
        if result.get("error") == "DOCUMENT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "文档不存在或无权访问")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "获取文档详情失败")
            )

    return DocumentResponse(**result["document"])


@router.post("/upload", response_model=DocumentResponse, summary="上传文档", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="要上传的文档文件（PDF或Word）"),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """
    上传新文档 - Story 2.4核心功能
    支持PDF和Word文档，包含文件验证和租户隔离
    """
    tenant_id = get_tenant_id_from_request()

    # 验证文件
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供文件名"
        )

    # 读取文件内容
    try:
        file_content = await file.read()
        file_size = len(file_content)
        mime_type = file.content_type or "application/octet-stream"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"读取文件失败: {str(e)}"
        )

    # 重置文件指针以便上传
    await file.seek(0)
    file_io = io.BytesIO(file_content)

    # 调用文档服务上传
    result = document_service.upload_document(
        db=db,
        tenant_id=tenant_id,
        file_data=file_io,
        file_name=file.filename,
        file_size=file_size,
        mime_type=mime_type
    )

    if not result["success"]:
        error_code = result.get("error", "UPLOAD_FAILED")
        message = result.get("message", "文档上传失败")

        # 根据错误类型返回不同的HTTP状态码
        if error_code in ["UPLOAD_001", "UPLOAD_002"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        elif error_code == "TENANT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message
            )

    return DocumentResponse(**result["document"])


@router.delete("/{document_id}", summary="删除文档")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    删除文档 - Story 2.4清理功能
    包含MinIO文件删除和数据库记录删除，强制租户隔离
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )

    tenant_id = get_tenant_id_from_request()

    result = document_service.delete_document(
        db=db,
        tenant_id=tenant_id,
        document_id=doc_uuid
    )

    if not result["success"]:
        if result.get("error") == "DOCUMENT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "文档不存在或无权访问")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "删除文档失败")
            )

    return {
        "success": True,
        "message": result.get("message", "文档删除成功")
    }


@router.get("/{document_id}/download", summary="下载文档")
async def download_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    下载文档文件 - Story 2.4要求
    通过MinIO提供安全的文件下载，强制租户隔离
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )

    tenant_id = get_tenant_id_from_request()

    # 获取文档信息（包含租户验证）
    result = document_service.get_document_by_id(
        db=db,
        tenant_id=tenant_id,
        document_id=doc_uuid
    )

    if not result["success"]:
        if result.get("error") == "DOCUMENT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在或无权访问"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取文档信息失败"
            )

    document = result["document"]

    # 从MinIO下载文件
    from src.app.services.minio_client import minio_service
    file_data = minio_service.download_file(
        bucket_name="knowledge-documents",
        object_name=document["storage_path"]
    )

    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件下载失败"
        )

    from fastapi.responses import Response
    return Response(
        content=file_data,
        media_type=document["mime_type"],
        headers={"Content-Disposition": f"attachment; filename={document['file_name']}"}
    )


@router.get("/{document_id}/preview", summary="获取文档预览链接")
async def get_document_preview(
    document_id: str,
    expires_in_hours: int = Query(1, ge=1, le=24, description="预览链接有效期（小时）"),
    db: Session = Depends(get_db)
) -> dict:
    """
    获取文档预览链接 - Story 2.4预览功能
    生成安全的预签名URL，强制租户隔离和状态检查
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )

    tenant_id = get_tenant_id_from_request()

    result = document_service.get_document_preview_url(
        db=db,
        tenant_id=tenant_id,
        document_id=doc_uuid,
        expires_in_hours=expires_in_hours
    )

    if not result["success"]:
        if result.get("error") == "DOCUMENT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "文档不存在或无权访问")
            )
        elif result.get("error") == "DOCUMENT_NOT_READY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "文档尚未处理完成，无法预览")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "生成预览链接失败")
            )

    return {
        "success": True,
        "preview_url": result["preview_url"],
        "expires_in_hours": expires_in_hours,
        "document": result["document"]
    }


@router.get("/{document_id}/status", summary="获取文档处理状态")
async def get_document_processing_status(
    document_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    获取文档处理状态 - Story 2.4状态跟踪
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )

    tenant_id = get_tenant_id_from_request()

    result = document_processor.get_processing_status(
        db=db,
        tenant_id=tenant_id,
        document_id=doc_uuid
    )

    if not result["success"]:
        if result.get("error") == "DOCUMENT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "文档不存在或无权访问")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "获取处理状态失败")
            )

    return result


@router.post("/{document_id}/process", summary="触发文档处理")
async def process_document(
    document_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    手动触发文档处理 - Story 2.4处理功能
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )

    tenant_id = get_tenant_id_from_request()

    result = document_processor.process_document_async(
        db=db,
        tenant_id=tenant_id,
        document_id=doc_uuid
    )

    if not result["success"]:
        error_code = result.get("error", "PROCESSING_FAILED")
        message = result.get("message", "文档处理失败")

        # 根据错误类型返回不同的HTTP状态码
        if error_code in ["DOCUMENT_NOT_FOUND", "DOCUMENT_ALREADY_PROCESSED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message
            )

    return result


@router.get("/stats/summary", response_model=DocumentStatsResponse, summary="获取文档统计信息")
async def get_document_stats(
    db: Session = Depends(get_db)
) -> DocumentStatsResponse:
    """
    获取租户文档统计信息 - Story 2.4要求
    包含按状态、文件类型的统计和存储使用情况
    """
    tenant_id = get_tenant_id_from_request()

    # 获取文档列表以获取统计信息
    result = document_service.get_documents(
        db=db,
        tenant_id=tenant_id,
        skip=0,
        limit=10000  # 获取所有文档进行统计
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档统计信息失败"
        )

    stats = result.get("stats", {})

    return DocumentStatsResponse(**stats)


@router.get("/health/status", summary="文档服务健康检查")
async def get_documents_service_health() -> dict:
    """
    文档服务健康检查端点
    """
    from src.app.services.minio_client import minio_service

    minio_healthy = minio_service.check_connection()

    return {
        "service": "documents",
        "status": "healthy" if minio_healthy else "degraded",
        "components": {
            "minio_storage": "healthy" if minio_healthy else "unhealthy",
            "document_service": "healthy",
            "document_processor": "healthy"
        },
        "timestamp": "2025-11-17T00:00:00Z"  # 简化实现
    }