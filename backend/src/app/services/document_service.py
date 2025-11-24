"""
文档管理服务 - Story 2.4规范实现
文档CRUD操作、状态管理、租户隔离、文件验证
"""

import uuid
from typing import List, Optional, Dict, Any, BinaryIO
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, func
import logging

from ..data.models import KnowledgeDocument, DocumentStatus, Tenant
from ..data.database import get_db
from .minio_client import minio_service
from .query_optimization_service import query_optimization_service
from ..core.config import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """
    文档管理核心服务 - 完全符合Story 2.4规范
    提供文档的完整生命周期管理功能
    """

    def __init__(self):
        self.supported_file_types = {
            'pdf': {
                'mime_types': ['application/pdf'],
                'max_size_mb': 50,
                'extensions': ['.pdf']
            },
            'docx': {
                'mime_types': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                'max_size_mb': 25,
                'extensions': ['.docx']
            }
        }

    def _generate_storage_path(self, tenant_id: str, document_id: uuid.UUID, file_name: str) -> str:
        """
        生成符合Story 2.4规范的MinIO存储路径
        格式: dataagent-docs/tenant-{tenant_id}/documents/{document_id}/{file_name}
        """
        return f"dataagent-docs/tenant-{tenant_id}/documents/{document_id}/{file_name}"

    def _validate_file(self, file_name: str, file_size: int, mime_type: str) -> Dict[str, Any]:
        """
        验证文件是否符合Story 2.4要求
        """
        # 获取文件扩展名
        file_extension = None
        for ext in ['.pdf', '.docx']:
            if file_name.lower().endswith(ext):
                file_extension = ext[1:]  # 移除点号
                break

        if not file_extension:
            return {
                "valid": False,
                "error": "UPLOAD_001",
                "message": "不支持的文件格式，仅支持PDF和Word文档",
                "supported_formats": ['pdf', 'docx']
            }

        # 检查文件类型规范
        if file_extension not in self.supported_file_types:
            return {
                "valid": False,
                "error": "UPLOAD_001",
                "message": f"不支持的文件格式: {file_extension}",
                "supported_formats": list(self.supported_file_types.keys())
            }

        file_spec = self.supported_file_types[file_extension]

        # 检查MIME类型
        if mime_type not in file_spec['mime_types']:
            return {
                "valid": False,
                "error": "UPLOAD_001",
                "message": f"文件MIME类型不匹配: {mime_type}",
                "expected_mime_types": file_spec['mime_types']
            }

        # 检查文件大小
        max_size_bytes = file_spec['max_size_mb'] * 1024 * 1024
        if file_size > max_size_bytes:
            return {
                "valid": False,
                "error": "UPLOAD_002",
                "message": f"文件大小超出限制，最大允许{file_spec['max_size_mb']}MB",
                "file_size_mb": file_size / (1024 * 1024),
                "max_size_mb": file_spec['max_size_mb']
            }

        return {
            "valid": True,
            "file_type": file_extension,
            "max_size_mb": file_spec['max_size_mb']
        }

    def upload_document(
        self,
        db: Session,
        tenant_id: str,
        file_data: BinaryIO,
        file_name: str,
        file_size: int,
        mime_type: str
    ) -> Dict[str, Any]:
        """
        上传文档 - Story 2.4核心功能
        包含文件验证、MinIO存储、数据库记录
        """
        try:
            # 验证租户存在
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                return {
                    "success": False,
                    "error": "TENANT_NOT_FOUND",
                    "message": "租户不存在"
                }

            # 文件验证
            validation_result = self._validate_file(file_name, file_size, mime_type)
            if not validation_result["valid"]:
                return validation_result

            file_type = validation_result["file_type"]

            # 创建文档记录
            document_id = uuid.uuid4()
            storage_path = self._generate_storage_path(tenant_id, document_id, file_name)

            document = KnowledgeDocument(
                id=document_id,
                tenant_id=tenant_id,
                file_name=file_name,
                storage_path=storage_path,
                file_type=file_type,
                file_size=file_size,
                mime_type=mime_type,
                status=DocumentStatus.PENDING
            )

            # 保存到数据库
            db.add(document)
            db.commit()
            db.refresh(document)

            # 上传到MinIO
            upload_success = minio_service.upload_file(
                bucket_name="knowledge-documents",
                object_name=storage_path,
                file_data=file_data,
                file_size=file_size,
                content_type=mime_type
            )

            if not upload_success:
                # 回滚数据库操作
                db.delete(document)
                db.commit()
                return {
                    "success": False,
                    "error": "UPLOAD_004",
                    "message": "文件上传失败，请检查网络连接并重试"
                }

            logger.info(f"Document uploaded successfully: {document_id} by tenant {tenant_id}")

            return {
                "success": True,
                "document": document.to_dict(),
                "message": "文档上传成功，正在处理中"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Document upload failed: {str(e)}")
            return {
                "success": False,
                "error": "UPLOAD_004",
                "message": f"上传过程中发生错误: {str(e)}"
            }

    def get_documents(
        self,
        db: Session,
        tenant_id: str,
        status: Optional[DocumentStatus] = None,
        file_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        获取租户的文档列表 - Story 2.4要求
        支持状态和文件类型过滤
        """
        try:
            # 构建查询条件（强制租户隔离）
            query = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.tenant_id == tenant_id
            )

            # 添加状态过滤
            if status:
                query = query.filter(KnowledgeDocument.status == status)

            # 添加文件类型过滤
            if file_type:
                query = query.filter(KnowledgeDocument.file_type == file_type)

            # 按创建时间倒序排列
            query = query.order_by(desc(KnowledgeDocument.created_at))

            # 获取总数
            total = query.count()

            # 分页
            documents = query.offset(skip).limit(limit).all()

            # 转换为字典格式
            document_dicts = [doc.to_dict() for doc in documents]

            # 统计信息
            stats = self._get_document_stats(db, tenant_id)

            return {
                "success": True,
                "documents": document_dicts,
                "total": total,
                "skip": skip,
                "limit": limit,
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Failed to get documents for tenant {tenant_id}: {str(e)}")
            return {
                "success": False,
                "error": "QUERY_ERROR",
                "message": f"查询文档列表失败: {str(e)}"
            }

    def get_document_by_id(
        self,
        db: Session,
        tenant_id: str,
        document_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        获取单个文档详情 - Story 2.4要求
        强制租户隔离验证
        """
        try:
            document = db.query(KnowledgeDocument).filter(
                and_(
                    KnowledgeDocument.id == document_id,
                    KnowledgeDocument.tenant_id == tenant_id
                )
            ).first()

            if not document:
                return {
                    "success": False,
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "文档不存在或无权访问"
                }

            return {
                "success": True,
                "document": document.to_dict()
            }

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {str(e)}")
            return {
                "success": False,
                "error": "QUERY_ERROR",
                "message": f"查询文档详情失败: {str(e)}"
            }

    def update_document_status(
        self,
        db: Session,
        tenant_id: str,
        document_id: uuid.UUID,
        status: DocumentStatus,
        processing_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新文档状态 - Story 2.4状态管理
        """
        try:
            document = db.query(KnowledgeDocument).filter(
                and_(
                    KnowledgeDocument.id == document_id,
                    KnowledgeDocument.tenant_id == tenant_id
                )
            ).first()

            if not document:
                return {
                    "success": False,
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "文档不存在或无权访问"
                }

            # 更新状态
            old_status = document.status
            document.status = status

            # 处理错误信息
            if processing_error:
                document.processing_error = processing_error
            elif status == DocumentStatus.READY:
                document.processing_error = None
                document.indexed_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(document)

            logger.info(f"Document {document_id} status updated: {old_status.value} -> {status.value}")

            return {
                "success": True,
                "document": document.to_dict(),
                "old_status": old_status.value,
                "new_status": status.value
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update document status: {str(e)}")
            return {
                "success": False,
                "error": "UPDATE_ERROR",
                "message": f"更新文档状态失败: {str(e)}"
            }

    def delete_document(
        self,
        db: Session,
        tenant_id: str,
        document_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        删除文档 - Story 2.4清理功能
        包含MinIO文件删除和数据库记录删除
        """
        try:
            document = db.query(KnowledgeDocument).filter(
                and_(
                    KnowledgeDocument.id == document_id,
                    KnowledgeDocument.tenant_id == tenant_id
                )
            ).first()

            if not document:
                return {
                    "success": False,
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "文档不存在或无权访问"
                }

            storage_path = document.storage_path

            # 从MinIO删除文件
            minio_delete_success = minio_service.delete_file(
                bucket_name="knowledge-documents",
                object_name=storage_path
            )

            if not minio_delete_success:
                logger.warning(f"Failed to delete file from MinIO: {storage_path}")
                # 继续删除数据库记录，但记录警告

            # 从数据库删除记录
            db.delete(document)
            db.commit()

            logger.info(f"Document deleted successfully: {document_id}")

            return {
                "success": True,
                "message": "文档删除成功",
                "deleted_document": document.to_dict()
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return {
                "success": False,
                "error": "DELETE_ERROR",
                "message": f"删除文档失败: {str(e)}"
            }

    def get_document_preview_url(
        self,
        db: Session,
        tenant_id: str,
        document_id: uuid.UUID,
        expires_in_hours: int = 1
    ) -> Dict[str, Any]:
        """
        生成文档预览URL - Story 2.4预览功能
        """
        try:
            document = db.query(KnowledgeDocument).filter(
                and_(
                    KnowledgeDocument.id == document_id,
                    KnowledgeDocument.tenant_id == tenant_id
                )
            ).first()

            if not document:
                return {
                    "success": False,
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "文档不存在或无权访问"
                }

            # 检查文档状态
            if document.status != DocumentStatus.READY:
                return {
                    "success": False,
                    "error": "DOCUMENT_NOT_READY",
                    "message": "文档尚未处理完成，无法预览",
                    "status": document.status.value
                }

            # 生成预签名URL
            from datetime import timedelta
            preview_url = minio_service.get_presigned_url(
                bucket_name="knowledge-documents",
                object_name=document.storage_path,
                expires=timedelta(hours=expires_in_hours)
            )

            if not preview_url:
                return {
                    "success": False,
                    "error": "PREVIEW_URL_FAILED",
                    "message": "生成预览链接失败"
                }

            return {
                "success": True,
                "preview_url": preview_url,
                "expires_in_hours": expires_in_hours,
                "document": document.to_dict()
            }

        except Exception as e:
            logger.error(f"Failed to generate preview URL for document {document_id}: {str(e)}")
            return {
                "success": False,
                "error": "PREVIEW_ERROR",
                "message": f"生成预览链接失败: {str(e)}"
            }

    def _get_document_stats(self, db: Session, tenant_id: str) -> Dict[str, Any]:
        """
        获取文档统计信息 - Story 2.4要求
        """
        try:
            # 按状态统计
            status_counts = db.query(
                KnowledgeDocument.status,
                func.count(KnowledgeDocument.id)
            ).filter(
                KnowledgeDocument.tenant_id == tenant_id
            ).group_by(KnowledgeDocument.status).all()

            # 按文件类型统计
            type_counts = db.query(
                KnowledgeDocument.file_type,
                func.count(KnowledgeDocument.id)
            ).filter(
                KnowledgeDocument.tenant_id == tenant_id
            ).group_by(KnowledgeDocument.file_type).all()

            # 总存储大小
            total_size = db.query(
                func.sum(KnowledgeDocument.file_size)
            ).filter(
                KnowledgeDocument.tenant_id == tenant_id
            ).scalar() or 0

            # 转换为字典格式
            stats = {
                "by_status": {status.value: count for status, count in status_counts},
                "by_file_type": {file_type: count for file_type, count in type_counts},
                "total_documents": sum(count for _, count in status_counts),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get document stats: {str(e)}")
            return {}

    # 新增：性能优化的异步方法
    async def get_documents_optimized(
        self,
        db: AsyncSession,
        tenant_id: str,
        status: Optional[DocumentStatus] = None,
        file_type: Optional[str] = None,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        使用查询优化服务的文档列表获取
        """
        try:
            result = await query_optimization_service.get_documents_optimized(
                db=db,
                tenant_id=tenant_id,
                status=status,
                file_type=file_type,
                search_query=search_query,
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order
            )

            if result.success:
                return {
                    "success": True,
                    "documents": result.data,
                    "total": result.total,
                    "skip": skip,
                    "limit": limit,
                    "query_time_ms": result.query_time_ms,
                    "cached": result.cached
                }
            else:
                return {
                    "success": False,
                    "error": "QUERY_FAILED",
                    "message": result.error or "查询失败"
                }

        except Exception as e:
            logger.error(f"Optimized get_documents failed: {str(e)}")
            return {
                "success": False,
                "error": "QUERY_ERROR",
                "message": f"查询出错: {str(e)}"
            }

    async def get_document_stats_optimized(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        使用查询优化服务的文档统计获取
        """
        try:
            result = await query_optimization_service.get_document_stats_optimized(
                db=db,
                tenant_id=tenant_id
            )

            if result.success:
                return {
                    "success": True,
                    "stats": result.data,
                    "query_time_ms": result.query_time_ms,
                    "cached": result.cached
                }
            else:
                return {
                    "success": False,
                    "error": "STATS_QUERY_FAILED",
                    "message": result.error or "统计查询失败"
                }

        except Exception as e:
            logger.error(f"Optimized get_document_stats failed: {str(e)}")
            return {
                "success": False,
                "error": "STATS_QUERY_ERROR",
                "message": f"统计查询出错: {str(e)}"
            }

    async def search_documents_optimized(
        self,
        db: AsyncSession,
        tenant_id: str,
        search_term: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        使用查询优化服务的文档搜索
        """
        try:
            result = await query_optimization_service.search_documents_optimized(
                db=db,
                tenant_id=tenant_id,
                search_term=search_term,
                limit=limit
            )

            if result.success:
                return {
                    "success": True,
                    "documents": result.data,
                    "total": result.total,
                    "query_time_ms": result.query_time_ms,
                    "cached": result.cached
                }
            else:
                return {
                    "success": False,
                    "error": "SEARCH_FAILED",
                    "message": result.error or "搜索失败"
                }

        except Exception as e:
            logger.error(f"Optimized search_documents failed: {str(e)}")
            return {
                "success": False,
                "error": "SEARCH_ERROR",
                "message": f"搜索出错: {str(e)}"
            }

    async def get_tenant_summary_optimized(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        使用查询优化服务的租户摘要获取
        """
        try:
            result = await query_optimization_service.get_tenant_summary_optimized(
                db=db,
                tenant_id=tenant_id
            )

            if result.success:
                return {
                    "success": True,
                    "summary": result.data,
                    "query_time_ms": result.query_time_ms,
                    "cached": result.cached
                }
            else:
                return {
                    "success": False,
                    "error": "SUMMARY_FAILED",
                    "message": result.error or "获取租户摘要失败"
                }

        except Exception as e:
            logger.error(f"Optimized get_tenant_summary failed: {str(e)}")
            return {
                "success": False,
                "error": "SUMMARY_ERROR",
                "message": f"获取租户摘要出错: {str(e)}"
            }

    # 缓存管理方法
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        """
        return {
            "cache_stats": query_optimization_service.get_cache_stats(),
            "query_stats": query_optimization_service.get_query_stats()
        }

    async def clear_cache(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """
        清理缓存
        """
        try:
            from .query_optimization_service import QueryType

            query_type = None
            if cache_type:
                try:
                    query_type = QueryType(cache_type)
                except ValueError:
                    return {
                        "success": False,
                        "error": "INVALID_CACHE_TYPE",
                        "message": f"无效的缓存类型: {cache_type}"
                    }

            result = await query_optimization_service.clear_cache(query_type)
            return result

        except Exception as e:
            logger.error(f"Clear cache failed: {str(e)}")
            return {
                "success": False,
                "error": "CACHE_CLEAR_FAILED",
                "message": f"清理缓存失败: {str(e)}"
            }


# 全局文档服务实例
document_service = DocumentService()