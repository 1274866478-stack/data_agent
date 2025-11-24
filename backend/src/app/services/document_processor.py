"""
文档处理服务 - Story 2.4规范实现
文档解析、文本提取、元数据处理、状态更新
为后续RAG功能做准备
"""

import uuid
import io
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import json

from ..data.models import KnowledgeDocument, DocumentStatus
from .minio_client import minio_service
from .document_service import document_service

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    文档处理服务 - Story 2.4要求的异步文档处理
    负责文档的完整处理流程，为后续RAG做准备
    """

    def __init__(self):
        self.processing_timeout = 300  # 5分钟处理超时

    def process_document_async(
        self,
        db: Session,
        tenant_id: str,
        document_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        异步处理文档 - Story 2.4核心处理流程
        1. 验证文件格式和完整性
        2. 提取文档文本内容
        3. 处理文档元数据
        4. 准备向量化（为后续RAG做准备）
        5. 更新文档状态
        """
        try:
            logger.info(f"Starting document processing: {document_id}")

            # 步骤1: 验证文档存在和权限
            validation_result = self._validate_document_for_processing(db, tenant_id, document_id)
            if not validation_result["success"]:
                return validation_result

            document = validation_result["document"]

            # 步骤2: 更新状态为处理中
            self._update_processing_status(db, document, DocumentStatus.INDEXING)

            # 步骤3: 验证文件格式和完整性
            file_validation = self._validate_file_integrity(document)
            if not file_validation["valid"]:
                self._update_processing_status(
                    db, document, DocumentStatus.ERROR, file_validation["error"]
                )
                return {
                    "success": False,
                    "error": "FILE_VALIDATION_FAILED",
                    "message": file_validation["error"]
                }

            # 步骤4: 提取文档文本内容
            text_extraction = self._extract_text_from_document(document)
            if not text_extraction["success"]:
                self._update_processing_status(
                    db, document, DocumentStatus.ERROR, text_extraction["error"]
                )
                return {
                    "success": False,
                    "error": "TEXT_EXTRACTION_FAILED",
                    "message": text_extraction["error"]
                }

            extracted_text = text_extraction["text"]
            metadata = text_extraction["metadata"]

            # 步骤5: 处理文档元数据
            processed_metadata = self._process_document_metadata(document, extracted_text, metadata)

            # 步骤6: 准备向量化（为后续RAG做准备）
            # 当前MVP版本只记录元数据，不实际向量化
            vector_preparation = self._prepare_for_vectorization(document, extracted_text)

            # 步骤7: 更新文档状态为完成
            self._update_processing_status(db, document, DocumentStatus.READY)

            logger.info(f"Document processing completed successfully: {document_id}")

            return {
                "success": True,
                "document_id": str(document_id),
                "processing_result": {
                    "text_length": len(extracted_text),
                    "metadata": processed_metadata,
                    "vector_preparation": vector_preparation,
                    "processing_time_seconds": self._calculate_processing_time(document)
                },
                "message": "文档处理完成，已准备就绪"
            }

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            try:
                db.rollback()
                # 尝试更新文档状态为错误
                document = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.id == document_id
                ).first()
                if document:
                    self._update_processing_status(
                        db, document, DocumentStatus.ERROR, str(e)
                    )
            except:
                pass

            return {
                "success": False,
                "error": "PROCESSING_ERROR",
                "message": f"文档处理过程中发生错误: {str(e)}"
            }

    def _validate_document_for_processing(
        self,
        db: Session,
        tenant_id: str,
        document_id: uuid.UUID
    ) -> Dict[str, Any]:
        """验证文档是否可以处理"""
        try:
            document = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.tenant_id == tenant_id
            ).first()

            if not document:
                return {
                    "success": False,
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "文档不存在或无权访问"
                }

            if document.status != DocumentStatus.PENDING:
                return {
                    "success": False,
                    "error": "DOCUMENT_ALREADY_PROCESSED",
                    "message": f"文档已处理或正在处理中，当前状态: {document.status.value}"
                }

            return {
                "success": True,
                "document": document
            }

        except Exception as e:
            return {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": f"文档验证失败: {str(e)}"
            }

    def _update_processing_status(
        self,
        db: Session,
        document: KnowledgeDocument,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> None:
        """更新文档处理状态"""
        try:
            document.status = status
            if error_message:
                document.processing_error = error_message
            elif status == DocumentStatus.READY:
                document.processing_error = None
                document.indexed_at = datetime.now(timezone.utc)

            db.commit()
            logger.info(f"Document {document.id} status updated to: {status.value}")

        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")
            db.rollback()

    def _validate_file_integrity(self, document: KnowledgeDocument) -> Dict[str, Any]:
        """验证文件格式和完整性"""
        try:
            # 从MinIO获取文件
            file_data = minio_service.download_file(
                bucket_name="knowledge-documents",
                object_name=document.storage_path
            )

            if not file_data:
                return {
                    "valid": False,
                    "error": "文件在MinIO中不存在或无法访问"
                }

            # 检查文件大小
            if len(file_data) != document.file_size:
                return {
                    "valid": False,
                    "error": f"文件大小不匹配，预期: {document.file_size}, 实际: {len(file_data)}"
                }

            # 基于文件类型进行格式验证
            if document.file_type == "pdf":
                return self._validate_pdf_integrity(file_data)
            elif document.file_type == "docx":
                return self._validate_docx_integrity(file_data)
            else:
                return {
                    "valid": False,
                    "error": f"不支持的文件类型: {document.file_type}"
                }

        except Exception as e:
            return {
                "valid": False,
                "error": f"文件完整性验证失败: {str(e)}"
            }

    def _validate_pdf_integrity(self, file_data: bytes) -> Dict[str, Any]:
        """验证PDF文件完整性"""
        try:
            # 简单的PDF文件头验证
            if not file_data.startswith(b'%PDF'):
                return {
                    "valid": False,
                    "error": "文件不是有效的PDF格式"
                }

            return {
                "valid": True
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"PDF验证失败: {str(e)}"
            }

    def _validate_docx_integrity(self, file_data: bytes) -> Dict[str, Any]:
        """验证DOCX文件完整性"""
        try:
            # 简单的DOCX文件头验证（ZIP格式）
            if not file_data.startswith(b'PK\x03\x04'):
                return {
                    "valid": False,
                    "error": "文件不是有效的DOCX格式"
                }

            return {
                "valid": True
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"DOCX验证失败: {str(e)}"
            }

    def _extract_text_from_document(self, document: KnowledgeDocument) -> Dict[str, Any]:
        """提取文档文本内容"""
        try:
            # 从MinIO获取文件
            file_data = minio_service.download_file(
                bucket_name="knowledge-documents",
                object_name=document.storage_path
            )

            if not file_data:
                return {
                    "success": False,
                    "error": "无法从MinIO获取文件"
                }

            # 根据文件类型提取文本
            if document.file_type == "pdf":
                return self._extract_text_from_pdf(file_data)
            elif document.file_type == "docx":
                return self._extract_text_from_docx(file_data)
            else:
                return {
                    "success": False,
                    "error": f"不支持的文件类型: {document.file_type}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"文本提取失败: {str(e)}"
            }

    def _extract_text_from_pdf(self, file_data: bytes) -> Dict[str, Any]:
        """从PDF提取文本（简化实现）"""
        try:
            # 注意：这是一个简化实现，生产环境应该使用PyPDF2或pdfplumber
            # 当前实现只是模拟，返回基本信息

            file_size = len(file_data)
            text = f"[PDF文档内容 - 文件大小: {file_size} 字节]"

            # 模拟提取的元数据
            metadata = {
                "page_count": "未知",
                "title": "从PDF元数据提取",
                "author": "从PDF元数据提取",
                "creation_date": "从PDF元数据提取"
            }

            return {
                "success": True,
                "text": text,
                "metadata": metadata
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"PDF文本提取失败: {str(e)}"
            }

    def _extract_text_from_docx(self, file_data: bytes) -> Dict[str, Any]:
        """从DOCX提取文本（简化实现）"""
        try:
            # 注意：这是一个简化实现，生产环境应该使用python-docx
            # 当前实现只是模拟，返回基本信息

            file_size = len(file_data)
            text = f"[DOCX文档内容 - 文件大小: {file_size} 字节]"

            # 模拟提取的元数据
            metadata = {
                "paragraph_count": "未知",
                "word_count": "未知",
                "title": "从DOCX属性提取",
                "author": "从DOCX属性提取",
                "creation_date": "从DOCX属性提取"
            }

            return {
                "success": True,
                "text": text,
                "metadata": metadata
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"DOCX文本提取失败: {str(e)}"
            }

    def _process_document_metadata(
        self,
        document: KnowledgeDocument,
        extracted_text: str,
        file_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理文档元数据"""
        try:
            # 合并各种元数据
            processed_metadata = {
                "file_info": {
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "file_size": document.file_size,
                    "mime_type": document.mime_type
                },
                "extraction_metadata": file_metadata,
                "text_analysis": {
                    "character_count": len(extracted_text),
                    "word_count": len(extracted_text.split()),
                    "line_count": extracted_text.count('\n') + 1,
                    "language_detected": "zh-CN"  # 简化实现
                },
                "processing_info": {
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "processor_version": "1.0.0",
                    "processing_stage": "MVP_READY_FOR_RAG"
                }
            }

            return processed_metadata

        except Exception as e:
            logger.error(f"Failed to process document metadata: {str(e)}")
            return {}

    def _prepare_for_vectorization(
        self,
        document: KnowledgeDocument,
        extracted_text: str
    ) -> Dict[str, Any]:
        """
        准备向量化 - Story 2.4要求
        当前MVP版本只准备数据，不实际向量化
        """
        try:
            # 文本预处理（为向量化做准备）
            text_chunks = self._split_text_into_chunks(extracted_text)

            vector_preparation = {
                "status": "ready_for_vectorization",
                "text_chunks_count": len(text_chunks),
                "total_characters": len(extracted_text),
                "estimated_tokens": len(extracted_text.split()),
                "collection_name": f"tenant_{document.tenant_id}_docs",
                "preparation_timestamp": datetime.now(timezone.utc).isoformat(),
                "next_step": "等待ChromaDB集成进行实际向量化"
            }

            # 在未来版本中，这里会调用ChromaDB服务进行实际的向量化
            # 当前只是记录准备信息

            return vector_preparation

        except Exception as e:
            logger.error(f"Failed to prepare for vectorization: {str(e)}")
            return {
                "status": "preparation_failed",
                "error": str(e)
            }

    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """将文本分割为块，为向量化做准备"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())

        return chunks

    def _calculate_processing_time(self, document: KnowledgeDocument) -> float:
        """计算处理时间（秒）"""
        try:
            if document.indexed_at and document.created_at:
                time_diff = document.indexed_at - document.created_at
                return time_diff.total_seconds()
            return 0.0
        except:
            return 0.0

    def get_processing_status(
        self,
        db: Session,
        tenant_id: str,
        document_id: uuid.UUID
    ) -> Dict[str, Any]:
        """获取文档处理状态"""
        try:
            document = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.tenant_id == tenant_id
            ).first()

            if not document:
                return {
                    "success": False,
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "文档不存在或无权访问"
                }

            return {
                "success": True,
                "document_id": str(document_id),
                "status": document.status.value,
                "processing_error": document.processing_error,
                "indexed_at": document.indexed_at.isoformat() if document.indexed_at else None,
                "created_at": document.created_at.isoformat() if document.created_at else None
            }

        except Exception as e:
            return {
                "success": False,
                "error": "STATUS_QUERY_ERROR",
                "message": f"查询处理状态失败: {str(e)}"
            }

    def batch_process_documents(
        self,
        db: Session,
        tenant_id: str,
        document_ids: List[uuid.UUID]
    ) -> Dict[str, Any]:
        """批量处理文档"""
        results = []
        success_count = 0
        error_count = 0

        for doc_id in document_ids:
            try:
                result = self.process_document_async(db, tenant_id, doc_id)
                results.append({
                    "document_id": str(doc_id),
                    "result": result
                })

                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                results.append({
                    "document_id": str(doc_id),
                    "result": {
                        "success": False,
                        "error": "BATCH_PROCESSING_ERROR",
                        "message": str(e)
                    }
                })
                error_count += 1

        return {
            "success": True,
            "batch_results": results,
            "summary": {
                "total_documents": len(document_ids),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": f"{(success_count / len(document_ids) * 100):.1f}%" if document_ids else "0%"
            }
        }


# 全局文档处理器实例
document_processor = DocumentProcessor()