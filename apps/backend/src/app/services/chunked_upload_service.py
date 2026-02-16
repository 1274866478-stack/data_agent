"""
# [CHUNKED_UPLOAD_SERVICE] 分块上传服务

## [HEADER]
**文件名**: chunked_upload_service.py
**职责**: Story 2.4性能优化 - 支持大文件分块上传、断点续传、并发上传、完整性校验
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 分块上传服务（Story 2.4）

## [INPUT]
- **tenant_id: str** - 租户ID
- **file_name: str** - 文件名
- **file_size: int** - 文件大小
- **mime_type: str** - MIME类型
- **file_data: bytes** - 文件数据
- **session_id: str** - 上传会话ID
- **chunk_number: int** - 分块编号
- **chunk_data: bytes** - 分块数据
- **db: AsyncSession** - 数据库会话
- **document_service** - 文档服务实例

## [OUTPUT]
- **Dict[str, Any]**: 初始化结果（initialize_upload_session）
  - session_id, total_chunks, chunk_size, file_checksum
- **Dict[str, Any]**: 上传结果（upload_chunk）
  - chunk_number, status, completed_chunks, total_chunks
- **Dict[str, Any]**: 状态查询结果（get_upload_status）
  - status, completed_chunks, failed_chunks, progress_percentage
- **Dict[str, Any]**: 完成结果（complete_upload）
  - document, message
- **Dict[str, Any]**: 中止结果（abort_upload）
  - message

**上游依赖** (已读取源码):
- 项目服务: minio_client（minio_service）
- 项目工具: logging（get_logger）

**下游依赖** (需要反向索引分析):
- [document_service.py](./document_service.py) - 文档服务上传完整文件

**调用方**:
- 大文件上传API初始化上传会话
- 分块上传API逐个上传分块
- 完成上传API合并分块

## [STATE]
- **分块状态**: ChunkStatus枚举（PENDING, UPLOADING, COMPLETED, FAILED）
- **会话状态**: UploadSessionStatus枚举（INITIALIZED, UPLOADING, COMPLETED, FAILED, ABORTED）
- **数据类**: ChunkInfo, UploadSession
- **默认配置**:
  - DEFAULT_CHUNK_SIZE: 5MB
  - MAX_CHUNK_SIZE: 50MB
  - MAX_CONCURRENT_CHUNKS: 3
  - MAX_RETRY_ATTEMPTS: 3
  - SESSION_TIMEOUT: 24小时
- **分块大小计算**: calculate_chunk_size（<10MB不分块, 10-100MB分5MB, 100MB-1GB分10MB, >1GB分20MB）
- **校验和算法**: 文件SHA256, 分块MD5
- **存储**: active_sessions字典, chunk_data字典（生产环境应使用Redis）
- **MinIO存储**: upload-chunks桶，路径chunks/{session_id}/chunk_####.dat
- **验证**: 分块大小验证、校验和验证
- **合并**: 完成时从MinIO下载所有分块并合并
- **清理**: cleanup_session删除MinIO分块文件和会话数据
- **过期清理**: cleanup_expired_sessions清理24小时前的会话

## [SIDE-EFFECTS]
- **校验和计算**: hashlib.sha256(file_data).hexdigest()计算文件校验和，hashlib.md5计算分块校验和
- **分块计算**: (file_size + chunk_size - 1) // chunk_size计算分块数量
- **UUID生成**: str(uuid.uuid4())生成会话ID
- **字典操作**: self.active_sessions[session_id] = session保存会话，self.chunk_data[session_id] = chunks保存分块
- **时间戳**: datetime.utcnow()记录created_at和updated_at
- **对象创建**: UploadSession和ChunkInfo创建
- **循环切片**: for i in range(total_chunks): file_data[start_byte:end_byte]分割文件
- **MinIO上传**: minio_service.upload_file上传分块到upload-chunks桶
- **状态更新**: chunk.status = ChunkStatus.UPLOADING/COMPLETED/FAILED
- **计数器更新**: session.completed_chunks += 1, session.failed_chunks += 1
- **MinIO下载**: minio_service.download_file下载分块
- **文件合并**: complete_file_data += chunk_data合并分块
- **DocumentService调用**: document_service.upload_document保存完整文件
- **字典删除**: self.active_sessions.pop(session_id)删除会话
- **异常处理**: try-except捕获所有异常，返回错误信息
- **全局单例**: chunked_upload_service全局实例

## [POS]
**路径**: backend/src/app/services/chunked_upload_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 依赖minio_client和document_service
"""

import asyncio
import uuid
import hashlib
import json
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from src.app.services.minio_client import minio_service
from src.app.core.logging import get_logger

logger = get_logger(__name__)


class ChunkStatus(str, Enum):
    """分块状态枚举"""
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadSessionStatus(str, Enum):
    """上传会话状态"""
    INITIALIZED = "initialized"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ChunkInfo:
    """分块信息"""
    chunk_number: int
    chunk_size: int
    start_byte: int
    end_byte: int
    checksum: str
    status: ChunkStatus = ChunkStatus.PENDING
    upload_id: Optional[str] = None
    retry_count: int = 0


@dataclass
class UploadSession:
    """上传会话"""
    session_id: str
    tenant_id: str
    file_name: str
    file_size: int
    mime_type: str
    total_chunks: int
    chunk_size: int
    file_checksum: str
    status: UploadSessionStatus = UploadSessionStatus.INITIALIZED
    created_at: datetime = None
    updated_at: datetime = None
    completed_chunks: int = 0
    failed_chunks: int = 0


class ChunkedUploadService:
    """分块上传服务"""

    def __init__(self):
        # 默认配置
        self.DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
        self.MAX_CHUNK_SIZE = 50 * 1024 * 1024     # 50MB
        self.MAX_CONCURRENT_CHUNKS = 3
        self.MAX_RETRY_ATTEMPTS = 3
        self.SESSION_TIMEOUT = timedelta(hours=24)  # 24小时

        # 内存存储上传会话信息（生产环境应使用Redis）
        self.active_sessions: Dict[str, UploadSession] = {}
        self.chunk_data: Dict[str, Dict[int, ChunkInfo]] = {}

    def calculate_chunk_size(self, file_size: int) -> int:
        """计算最优分块大小"""
        if file_size < 10 * 1024 * 1024:  # 小于10MB，不分块
            return file_size
        elif file_size < 100 * 1024 * 1024:  # 10-100MB，5MB分块
            return self.DEFAULT_CHUNK_SIZE
        elif file_size < 1024 * 1024 * 1024:  # 100MB-1GB，10MB分块
            return 10 * 1024 * 1024
        else:  # 大于1GB，20MB分块
            return min(20 * 1024 * 1024, self.MAX_CHUNK_SIZE)

    def calculate_file_checksum(self, file_data: bytes) -> str:
        """计算文件校验和"""
        return hashlib.sha256(file_data).hexdigest()

    def calculate_chunk_checksum(self, chunk_data: bytes) -> str:
        """计算分块校验和"""
        return hashlib.md5(chunk_data).hexdigest()

    async def initialize_upload_session(
        self,
        tenant_id: str,
        file_name: str,
        file_size: int,
        mime_type: str,
        file_data: bytes
    ) -> Dict[str, Any]:
        """初始化上传会话"""
        try:
            # 计算文件校验和
            file_checksum = self.calculate_file_checksum(file_data)

            # 计算分块大小和数量
            chunk_size = self.calculate_chunk_size(file_size)
            total_chunks = (file_size + chunk_size - 1) // chunk_size

            # 创建上传会话
            session_id = str(uuid.uuid4())
            session = UploadSession(
                session_id=session_id,
                tenant_id=tenant_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                total_chunks=total_chunks,
                chunk_size=chunk_size,
                file_checksum=file_checksum,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # 保存会话信息
            self.active_sessions[session_id] = session

            # 准备分块信息
            chunks = {}
            for i in range(total_chunks):
                start_byte = i * chunk_size
                end_byte = min(start_byte + chunk_size, file_size)
                chunk_data = file_data[start_byte:end_byte]

                chunk = ChunkInfo(
                    chunk_number=i,
                    chunk_size=len(chunk_data),
                    start_byte=start_byte,
                    end_byte=end_byte,
                    checksum=self.calculate_chunk_checksum(chunk_data)
                )
                chunks[i] = chunk

            self.chunk_data[session_id] = chunks

            logger.info(
                f"初始化上传会话成功",
                extra={
                    "session_id": session_id,
                    "tenant_id": tenant_id,
                    "file_name": file_name,
                    "file_size": file_size,
                    "total_chunks": total_chunks,
                    "chunk_size": chunk_size
                }
            )

            return {
                "success": True,
                "session_id": session_id,
                "total_chunks": total_chunks,
                "chunk_size": chunk_size,
                "file_checksum": file_checksum
            }

        except Exception as e:
            logger.error(f"初始化上传会话失败: {str(e)}")
            return {
                "success": False,
                "error": "UPLOAD_SESSION_INIT_FAILED",
                "message": "初始化上传会话失败"
            }

    async def get_upload_session(self, session_id: str) -> Optional[UploadSession]:
        """获取上传会话"""
        return self.active_sessions.get(session_id)

    async def get_chunk_info(self, session_id: str, chunk_number: int) -> Optional[ChunkInfo]:
        """获取分块信息"""
        if session_id not in self.chunk_data:
            return None
        return self.chunk_data[session_id].get(chunk_number)

    async def upload_chunk(
        self,
        session_id: str,
        chunk_number: int,
        chunk_data: bytes
    ) -> Dict[str, Any]:
        """上传单个分块"""
        try:
            # 验证会话
            session = await self.get_upload_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": "SESSION_NOT_FOUND",
                    "message": "上传会话不存在"
                }

            # 验证分块
            chunk = await self.get_chunk_info(session_id, chunk_number)
            if not chunk:
                return {
                    "success": False,
                    "error": "CHUNK_NOT_FOUND",
                    "message": "分块信息不存在"
                }

            # 验证分块数据
            if len(chunk_data) != chunk.chunk_size:
                return {
                    "success": False,
                    "error": "CHUNK_SIZE_MISMATCH",
                    "message": "分块大小不匹配"
                }

            # 验证校验和
            chunk_checksum = self.calculate_chunk_checksum(chunk_data)
            if chunk_checksum != chunk.checksum:
                return {
                    "success": False,
                    "error": "CHUNK_CHECKSUM_MISMATCH",
                    "message": "分块校验和不匹配"
                }

            # 更新分块状态
            chunk.status = ChunkStatus.UPLOADING
            chunk.retry_count += 1

            # 构造分块对象名
            chunk_object_name = f"chunks/{session.session_id}/chunk_{chunk_number:04d}"

            # 上传到MinIO
            upload_result = minio_service.upload_file(
                bucket_name="upload-chunks",
                object_name=chunk_object_name,
                file_data=chunk_data,
                file_size=len(chunk_data),
                content_type="application/octet-stream"
            )

            if upload_result:
                chunk.status = ChunkStatus.COMPLETED
                chunk.upload_id = chunk_object_name
                session.completed_chunks += 1
                session.updated_at = datetime.utcnow()

                # 检查是否所有分块都已完成
                if session.completed_chunks == session.total_chunks:
                    session.status = UploadSessionStatus.COMPLETED

                logger.info(
                    f"分块上传成功",
                    extra={
                        "session_id": session_id,
                        "chunk_number": chunk_number,
                        "completed_chunks": session.completed_chunks,
                        "total_chunks": session.total_chunks
                    }
                )

                return {
                    "success": True,
                    "chunk_number": chunk_number,
                    "status": "completed",
                    "completed_chunks": session.completed_chunks,
                    "total_chunks": session.total_chunks
                }
            else:
                chunk.status = ChunkStatus.FAILED
                session.failed_chunks += 1
                session.updated_at = datetime.utcnow()

                return {
                    "success": False,
                    "error": "CHUNK_UPLOAD_FAILED",
                    "message": "分块上传失败"
                }

        except Exception as e:
            logger.error(f"分块上传失败: {str(e)}", extra={
                "session_id": session_id,
                "chunk_number": chunk_number
            })

            # 更新分块状态
            if chunk:
                chunk.status = ChunkStatus.FAILED
                session.failed_chunks += 1

            return {
                "success": False,
                "error": "CHUNK_UPLOAD_ERROR",
                "message": f"分块上传出错: {str(e)}"
            }

    async def get_upload_status(self, session_id: str) -> Dict[str, Any]:
        """获取上传状态"""
        session = await self.get_upload_session(session_id)
        if not session:
            return {
                "success": False,
                "error": "SESSION_NOT_FOUND",
                "message": "上传会话不存在"
            }

        chunks = self.chunk_data.get(session_id, {})
        chunk_statuses = []

        for i in range(session.total_chunks):
            chunk = chunks.get(i)
            if chunk:
                chunk_statuses.append({
                    "chunk_number": i,
                    "status": chunk.status.value,
                    "retry_count": chunk.retry_count
                })

        return {
            "success": True,
            "session_id": session_id,
            "status": session.status.value,
            "total_chunks": session.total_chunks,
            "completed_chunks": session.completed_chunks,
            "failed_chunks": session.failed_chunks,
            "progress_percentage": (session.completed_chunks / session.total_chunks * 100) if session.total_chunks > 0 else 0,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "chunks": chunk_statuses
        }

    async def complete_upload(
        self,
        session_id: str,
        db: AsyncSession,
        document_service
    ) -> Dict[str, Any]:
        """完成上传，合并分块"""
        try:
            session = await self.get_upload_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": "SESSION_NOT_FOUND",
                    "message": "上传会话不存在"
                }

            if session.status != UploadSessionStatus.COMPLETED:
                return {
                    "success": False,
                    "error": "UPLOAD_NOT_COMPLETED",
                    "message": "文件上传未完成，无法完成合并"
                }

            # 获取所有分块
            chunks = self.chunk_data.get(session_id, {})
            sorted_chunks = [chunks[i] for i in range(session.total_chunks) if chunks[i]]

            # 合并分块数据
            complete_file_data = b""
            for chunk in sorted_chunks:
                chunk_object_name = chunk.upload_id
                if chunk_object_name:
                    chunk_data = minio_service.download_file(
                        bucket_name="upload-chunks",
                        object_name=chunk_object_name
                    )
                    if chunk_data:
                        complete_file_data += chunk_data
                    else:
                        raise Exception(f"无法下载分块 {chunk.chunk_number}")
                else:
                    raise Exception(f"分块 {chunk.chunk_number} 未上传")

            # 验证合并后的文件校验和
            merged_checksum = self.calculate_file_checksum(complete_file_data)
            if merged_checksum != session.file_checksum:
                return {
                    "success": False,
                    "error": "FILE_CHECKSUM_MISMATCH",
                    "message": "文件校验和不匹配，可能数据损坏"
                }

            # 通过DocumentService保存完整文件
            import io
            file_data = io.BytesIO(complete_file_data)

            result = await document_service.upload_document(
                db=db,
                tenant_id=session.tenant_id,
                file_data=file_data,
                file_name=session.file_name,
                file_size=session.file_size,
                mime_type=session.mime_type
            )

            if result["success"]:
                # 清理分块数据
                await self.cleanup_session(session_id)

                logger.info(
                    f"文件上传完成",
                    extra={
                        "session_id": session_id,
                        "tenant_id": session.tenant_id,
                        "file_name": session.file_name,
                        "document_id": result["document"]["id"]
                    }
                )

                return {
                    "success": True,
                    "document": result["document"],
                    "message": "文件上传并合并完成"
                }
            else:
                return {
                    "success": False,
                    "error": "DOCUMENT_SAVE_FAILED",
                    "message": "保存文档失败"
                }

        except Exception as e:
            logger.error(f"完成上传失败: {str(e)}", extra={
                "session_id": session_id
            })

            return {
                "success": False,
                "error": "UPLOAD_COMPLETION_FAILED",
                "message": f"完成上传失败: {str(e)}"
            }

    async def abort_upload(self, session_id: str) -> Dict[str, Any]:
        """中止上传会话"""
        try:
            session = await self.get_upload_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": "SESSION_NOT_FOUND",
                    "message": "上传会话不存在"
                }

            # 更新会话状态
            session.status = UploadSessionStatus.ABORTED
            session.updated_at = datetime.utcnow()

            # 清理会话数据
            await self.cleanup_session(session_id)

            logger.info(
                f"上传会话已中止",
                extra={
                    "session_id": session_id,
                    "tenant_id": session.tenant_id
                }
            )

            return {
                "success": True,
                "message": "上传会话已中止"
            }

        except Exception as e:
            logger.error(f"中止上传会话失败: {str(e)}")
            return {
                "success": False,
                "error": "ABORT_UPLOAD_FAILED",
                "message": "中止上传失败"
            }

    async def cleanup_session(self, session_id: str):
        """清理上传会话数据"""
        try:
            # 清理MinIO中的分块文件
            chunks = self.chunk_data.get(session_id, {})
            for chunk in chunks.values():
                if chunk.upload_id:
                    try:
                        minio_service.delete_file(
                            bucket_name="upload-chunks",
                            object_name=chunk.upload_id
                        )
                    except Exception as e:
                        logger.warning(f"清理分块文件失败: {e}")

            # 清理会话数据
            self.active_sessions.pop(session_id, None)
            self.chunk_data.pop(session_id, None)

        except Exception as e:
            logger.error(f"清理会话数据失败: {str(e)}")

    async def get_active_sessions(self, tenant_id: str = None) -> List[Dict[str, Any]]:
        """获取活跃的上传会话"""
        sessions = []
        for session_id, session in self.active_sessions.items():
            if tenant_id is None or session.tenant_id == tenant_id:
                sessions.append({
                    "session_id": session_id,
                    "tenant_id": session.tenant_id,
                    "file_name": session.file_name,
                    "file_size": session.file_size,
                    "status": session.status.value,
                    "progress_percentage": (session.completed_chunks / session.total_chunks * 100) if session.total_chunks > 0 else 0,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                })

        return sessions

    async def cleanup_expired_sessions(self):
        """清理过期的上传会话"""
        current_time = datetime.utcnow()
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            if session.created_at and (current_time - session.created_at) > self.SESSION_TIMEOUT:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.abort_upload(session_id)

        if expired_sessions:
            logger.info(f"清理了 {len(expired_sessions)} 个过期的上传会话")


# 创建全局分块上传服务实例
chunked_upload_service = ChunkedUploadService()