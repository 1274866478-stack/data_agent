"""
# [UPLOAD] 分块上传API端点

## [HEADER]
**文件名**: upload.py
**职责**: 提供大文件分块上传、断点续传和会话管理 - Story 2.4性能优化
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 分块上传实现

## [INPUT]
- **POST /upload/initialize**: 初始化上传会话 - UploadFile
- **POST /upload/chunk/{session_id}/{chunk_number}**: 上传分块 - chunk_data
- **POST /upload/complete/{session_id}**: 完成上传 - checksum
- **GET /upload/status/{session_id}**: 查询上传状态
- **DELETE /upload/{session_id}**: 取消上传

## [OUTPUT]
- **UploadSessionResponse**: 会话信息 - session_id, total_chunks, chunk_size
- **UploadStatusResponse**: 上传状态 - progress, uploaded_chunks
- **CompletionResponse**: 完成结果 - success, document_id

## [LINK]
**上游依赖**:
- [../../services/chunked_upload_service.py](../../services/chunked_upload_service.py)
- [../../services/document_service.py](../../services/document_service.py)
- [../../middleware/tenant_context.py](../../middleware/tenant_context.py)

**调用方**:
- 前端文件上传组件
- 大文件上传功能

## [POS]
**路径**: backend/src/app/api/v1/endpoints/upload.py
**模块层级**: Level 5
**依赖深度**: 2层
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import uuid
import io

from src.app.data.database import get_db
from src.app.middleware.tenant_context import get_current_tenant_id
from src.app.services.document_service import DocumentService
from src.app.services.chunked_upload_service import chunked_upload_service
from src.app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/initialize")
async def initialize_upload(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    初始化分块上传会话
    """
    try:
        # 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        # 读取文件数据
        file_data = await file.read()
        file_size = len(file_data)

        # 文件大小检查（最大100MB）
        max_size = 100 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超出限制，最大允许 {max_size // (1024*1024)}MB"
            )

        # 文件类型检查
        allowed_types = {
            "application/pdf": [".pdf"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
            "application/msword": [".doc"]
        }

        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file.content_type}"
            )

        # 初始化上传会话
        result = await chunked_upload_service.initialize_upload_session(
            tenant_id=tenant_id,
            file_name=file.filename,
            file_size=file_size,
            mime_type=file.content_type,
            file_data=file_data
        )

        if result["success"]:
            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "session_id": result["session_id"],
                    "file_name": file.filename,
                    "file_size": file_size,
                    "mime_type": file.content_type,
                    "total_chunks": result["total_chunks"],
                    "chunk_size": result["chunk_size"],
                    "file_checksum": result["file_checksum"]
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"初始化上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail="初始化上传失败")


@router.post("/chunk/{session_id}/{chunk_number}")
async def upload_chunk(
    session_id: str,
    chunk_number: int,
    chunk_data: bytes = File(...),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    上传单个分块
    """
    try:
        # 验证会话
        session = await chunked_upload_service.get_upload_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在")

        if session.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问此上传会话")

        # 上传分块
        result = await chunked_upload_service.upload_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            chunk_data=chunk_data
        )

        if result["success"]:
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分块上传失败: {str(e)}", extra={
            "session_id": session_id,
            "chunk_number": chunk_number
        })
        raise HTTPException(status_code=500, detail="分块上传失败")


@router.get("/status/{session_id}")
async def get_upload_status(
    session_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    获取上传状态
    """
    try:
        # 验证会话
        session = await chunked_upload_service.get_upload_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在")

        if session.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问此上传会话")

        # 获取状态
        result = await chunked_upload_service.get_upload_status(session_id)

        if result["success"]:
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取上传状态失败")


@router.post("/complete/{session_id}")
async def complete_upload(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    完成上传，合并分块
    """
    try:
        # 验证会话
        session = await chunked_upload_service.get_upload_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在")

        if session.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问此上传会话")

        # 创建DocumentService实例
        document_service = DocumentService()

        # 完成上传
        result = await chunked_upload_service.complete_upload(
            session_id=session_id,
            db=db,
            document_service=document_service
        )

        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "document": result["document"],
                    "message": "文件上传完成"
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail="完成上传失败")


@router.delete("/abort/{session_id}")
async def abort_upload(
    session_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    中止上传会话
    """
    try:
        # 验证会话
        session = await chunked_upload_service.get_upload_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在")

        if session.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问此上传会话")

        # 中止上传
        result = await chunked_upload_service.abort_upload(session_id)

        if result["success"]:
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"中止上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail="中止上传失败")


@router.get("/sessions")
async def get_active_sessions(
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    获取活跃的上传会话列表
    """
    try:
        sessions = await chunked_upload_service.get_active_sessions(tenant_id)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "sessions": sessions,
                "total": len(sessions)
            }
        )

    except Exception as e:
        logger.error(f"获取活跃会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取活跃会话失败")


@router.post("/cleanup")
async def cleanup_expired_sessions(
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    清理过期的上传会话
    """
    try:
        # 在后台任务中执行清理
        background_tasks.add_task(chunked_upload_service.cleanup_expired_sessions)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "已启动过期会话清理任务"
            }
        )

    except Exception as e:
        logger.error(f"清理过期会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清理过期会话失败")


@router.get("/chunk-info/{session_id}/{chunk_number}")
async def get_chunk_info(
    session_id: str,
    chunk_number: int,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    获取分块信息
    """
    try:
        # 验证会话
        session = await chunked_upload_service.get_upload_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在")

        if session.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="无权访问此上传会话")

        # 获取分块信息
        chunk = await chunked_upload_service.get_chunk_info(session_id, chunk_number)
        if not chunk:
            raise HTTPException(status_code=404, detail="分块信息不存在")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "chunk_number": chunk.chunk_number,
                "chunk_size": chunk.chunk_size,
                "start_byte": chunk.start_byte,
                "end_byte": chunk.end_byte,
                "status": chunk.status.value,
                "retry_count": chunk.retry_count
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分块信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分块信息失败")