"""
# RAG (Retrieval-Augmented Generation) API端点

## [HEADER]
**文件名**: rag.py
**职责**: 提供RAG查询、文档处理、语义检索、嵌入向量生成和会话管理的RESTful API
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本

## [INPUT]
- query: str - 用户查询文本
- request: RAGQueryRequest - RAG查询请求模型
- file: UploadFile - 上传的文档文件
- document_id: int - 文档ID
- collection_id: str - 集合ID
- chunking_strategy: str - 分块策略（semantic, fixed_size, overlap等）
- chunk_size: int - 目标分块大小
- overlap_ratio: float - 重叠比例
- retrieval_mode: str - 检索模式（semantic, keyword, hybrid, exact）
- max_results: int - 最大返回结果数
- threshold: float - 相似度阈值
- tenant_id: str - 租户ID（通过依赖注入）

## [OUTPUT]
- RAG查询响应: RAGQueryResponse（包含答案、检索结果、推理步骤）
- 文档处理结果: Dict[str, Any]（包含分块信息、向量数量）
- 语义搜索结果: Dict[str, Any]（包含检索到的文档片段）
- 嵌入向量: List[float]（文本的向量表示）
- 集合列表: List[Dict[str, Any]]
- 会话历史: List[Dict[str, Any]]
- 反馈提交结果: Dict[str, Any]
- 服务统计信息: Dict[str, Any]
- 健康检查状态: Dict[str, Any]
- 缓存状态: Dict[str, Any]
- RAG配置信息: Dict[str, Any]

## [LINK]
**上游依赖**:
- [../../core/auth.py](../../core/auth.py) - get_current_tenant_id依赖注入
- [../../core/config.py](../../core/config.py) - get_settings配置获取
- [../../services/rag_service.py](../../services/rag_service.py) - RAGService核心服务
- [../../models/rag_models.py](../../models/rag_models.py) - RAG请求/响应模型
- [../../services/embedding_service.py](../../services/embedding_service.py) - 嵌入向量生成服务

**下游依赖**:
- 无（API端点为最外层）

**调用方**:
- 前端知识库检索界面
- 文档上传处理流程
- 智能问答系统
- 语义搜索功能

## [POS]
**路径**: backend/src/app/api/v1/endpoints/rag.py
**模块层级**: Level 3（API端点层）
**依赖深度**: 2 层（依赖于services、models和core层）
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
import uuid

from ...core.auth import get_current_tenant_id
from ...core.config import get_settings
from ...services.rag_service import RAGService
from ...models.rag_models import (
    RAGQueryRequest,
    RAGQueryResponse,
    RetrievalMode,
    ChunkingStrategy
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize RAG service
rag_service = RAGService()

# Create router
router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Process a RAG query

    Args:
        request: RAG query request
        tenant_id: Tenant ID from authentication

    Returns:
        RAG query response
    """
    try:
        # Validate tenant ID
        if request.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="租户ID不匹配")

        logger.info(f"处理RAG查询，租户: {tenant_id}, 查询: {request.query[:50]}...")

        # Process query
        response = await rag_service.process_query(request)

        return response

    except Exception as e:
        logger.error(f"RAG查询处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG查询失败: {str(e)}")


@router.post("/query/simple")
async def rag_query_simple(
    query: str = Form(...),
    session_id: Optional[str] = Form(None),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Simple RAG query endpoint for form data

    Args:
        query: Query text
        session_id: Optional session ID
        tenant_id: Tenant ID from authentication

    Returns:
        RAG query response
    """
    try:
        # Create RAG request
        request = RAGQueryRequest(
            query=query,
            tenant_id=tenant_id,
            session_id=session_id,
            retrieval_mode=RetrievalMode.SEMANTIC,
            max_results=5,
            similarity_threshold=0.7,
            collections=[],
            max_context_tokens=2000,
            include_metadata=True,
            generate_answer=True,
            answer_style="concise",
            temperature=0.3
        )

        response = await rag_service.process_query(request)
        return response

    except Exception as e:
        logger.error(f"简单RAG查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/documents/{document_id}/process")
async def process_document(
    document_id: int,
    file: UploadFile = File(...),
    collection_id: str = Form(...),
    chunking_strategy: str = Form(default="semantic"),
    chunk_size: int = Form(default=512),
    overlap_ratio: float = Form(default=0.2),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Process and index a document for RAG

    Args:
        document_id: Document ID
        file: Uploaded file
        collection_id: Target collection ID
        chunking_strategy: Chunking strategy
        chunk_size: Target chunk size
        overlap_ratio: Overlap ratio
        tenant_id: Tenant ID from authentication

    Returns:
        Processing metadata
    """
    try:
        # Validate file type
        file_type = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_type not in ['pdf', 'docx', 'txt']:
            raise HTTPException(status_code=400, detail="不支持的文件类型")

        # Read file content
        file_content = await file.read()

        # Validate chunking strategy
        try:
            chunk_strategy_enum = ChunkingStrategy(chunking_strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的分块策略")

        logger.info(f"开始处理文档: {file.filename}, 租户: {tenant_id}")

        # Process document
        result = await rag_service.process_document(
            file_content=file_content,
            file_name=file.filename,
            file_type=file_type,
            document_id=document_id,
            tenant_id=tenant_id,
            collection_id=collection_id,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            overlap_ratio=overlap_ratio
        )

        return {
            "success": True,
            "message": "文档处理完成",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.get("/search")
async def search_documents(
    query: str = Query(...),
    mode: str = Query(default="semantic"),
    max_results: int = Query(default=10, ge=1, le=50),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0),
    collections: Optional[str] = Query(None),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Search documents without generating answers

    Args:
        query: Search query
        mode: Retrieval mode (semantic, keyword, hybrid, exact)
        max_results: Maximum results
        threshold: Similarity threshold
        collections: Comma-separated collection IDs
        tenant_id: Tenant ID from authentication

    Returns:
        Search results
    """
    try:
        # Validate retrieval mode
        try:
            retrieval_mode = RetrievalMode(mode)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的检索模式")

        # Parse collections
        collection_list = collections.split(',') if collections else []

        # Create RAG query request (no answer generation)
        request = RAGQueryRequest(
            query=query,
            tenant_id=tenant_id,
            retrieval_mode=retrieval_mode,
            max_results=max_results,
            similarity_threshold=threshold,
            collections=collection_list,
            generate_answer=False
        )

        response = await rag_service.process_query(request)

        return {
            "success": True,
            "query": query,
            "total_results": response.total_retrieved,
            "retrieval_time_ms": response.retrieval_time_ms,
            "results": [
                {
                    "rank": result.rank,
                    "content": result.content,
                    "content_preview": result.content_preview,
                    "similarity_score": result.similarity_score,
                    "source": {
                        "document_id": result.document_id,
                        "document_title": result.document_title,
                        "file_name": result.file_name,
                        "file_type": result.file_type,
                        "page_number": result.page_number,
                        "chapter_title": result.chapter_title
                    },
                    "metadata": result.metadata
                }
                for result in response.retrieval_results
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/embedding")
async def generate_embedding(
    text: str = Form(...),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Generate embedding for text

    Args:
        text: Text to embed
        tenant_id: Tenant ID from authentication

    Returns:
        Embedding vector and metadata
    """
    try:
        from ...services.embedding_service import EmbeddingService

        embedding_service = EmbeddingService()
        embedding, metadata = await embedding_service.generate_embedding(text, tenant_id)

        return {
            "success": True,
            "text_length": len(text),
            "embedding_dimension": len(embedding),
            "metadata": metadata,
            "embedding": embedding  # Note: In production, you might not want to return the full embedding
        }

    except Exception as e:
        logger.error(f"嵌入向量生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"嵌入向量生成失败: {str(e)}")


@router.get("/collections")
async def get_collections(tenant_id: str = Depends(get_current_tenant_id)):
    """
    Get available collections for tenant

    Args:
        tenant_id: Tenant ID from authentication

    Returns:
        List of collections
    """
    try:
        # In a real implementation, this would query the database
        # For now, return mock data
        collections = [
            {
                "id": "default",
                "name": "documents",
                "display_name": "文档集合",
                "description": "默认文档集合",
                "document_count": 0,
                "chunk_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
        ]

        return {
            "success": True,
            "tenant_id": tenant_id,
            "collections": collections
        }

    except Exception as e:
        logger.error(f"获取集合列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取集合列表失败: {str(e)}")


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get conversation history for a session

    Args:
        session_id: Session ID
        limit: Maximum number of entries
        tenant_id: Tenant ID from authentication

    Returns:
        Session history
    """
    try:
        history = await rag_service.get_session_history(session_id, tenant_id, limit)

        return {
            "success": True,
            "session_id": session_id,
            "history": history,
            "total_entries": len(history)
        }

    except Exception as e:
        logger.error(f"获取会话历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话历史失败: {str(e)}")


@router.post("/feedback/{entry_id}")
async def submit_feedback(
    entry_id: str,
    rating: int = Form(..., ge=1, le=5),
    comment: Optional[str] = Form(None),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Submit user feedback for a retrieval entry

    Args:
        entry_id: Retrieval entry ID
        rating: Feedback rating (1-5)
        comment: Optional feedback comment
        tenant_id: Tenant ID from authentication

    Returns:
        Feedback submission result
    """
    try:
        result = await rag_service.update_user_feedback(
            entry_id=entry_id,
            tenant_id=tenant_id,
            feedback_rating=rating,
            feedback_comment=comment
        )

        return {
            "success": True,
            "message": "反馈提交成功",
            "data": result
        }

    except Exception as e:
        logger.error(f"反馈提交失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")


@router.get("/statistics")
async def get_statistics(tenant_id: str = Depends(get_current_tenant_id)):
    """
    Get RAG service statistics

    Args:
        tenant_id: Tenant ID from authentication

    Returns:
        Service statistics
    """
    try:
        stats = await rag_service.get_statistics(tenant_id)

        return {
            "success": True,
            "tenant_id": tenant_id,
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@router.get("/health")
async def health_check(tenant_id: str = Depends(get_current_tenant_id)):
    """
    Health check for RAG service

    Args:
        tenant_id: Tenant ID from authentication

    Returns:
        Health status
    """
    try:
        health = await rag_service.health_check()

        return {
            "success": True,
            "service": "rag",
            "tenant_id": tenant_id,
            "health": health,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "success": False,
            "service": "rag",
            "tenant_id": tenant_id,
            "health": {
                "status": "unhealthy",
                "error": str(e)
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/cache/status")
async def get_cache_status(tenant_id: str = Depends(get_current_tenant_id)):
    """
    Get embedding cache status

    Args:
        tenant_id: Tenant ID from authentication

    Returns:
        Cache status
    """
    try:
        from ...services.embedding_service import EmbeddingService

        embedding_service = EmbeddingService()
        stats = await embedding_service.get_statistics()

        return {
            "success": True,
            "tenant_id": tenant_id,
            "cache_status": {
                "enabled": stats.get('cache_enabled', False),
                "size": stats.get('cache_size', 0),
                "hit_rate": stats.get('cache_hit_rate', 0.0),
                "ttl_hours": stats.get('cache_ttl_hours', 24)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"获取缓存状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存状态失败: {str(e)}")


@router.delete("/cache")
async def clear_cache(
    tenant_id: str = Depends(get_current_tenant_id),
    confirm: bool = Query(default=False)
):
    """
    Clear embedding cache

    Args:
        tenant_id: Tenant ID from authentication
        confirm: Confirmation flag

    Returns:
        Cache clearance result
    """
    try:
        if not confirm:
            raise HTTPException(status_code=400, detail="需要确认标志")

        from ...services.embedding_service import EmbeddingService

        embedding_service = EmbeddingService()
        await embedding_service.clear_cache(tenant_id)

        return {
            "success": True,
            "message": f"租户{tenant_id}的缓存已清除",
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")


@router.get("/config")
async def get_rag_config(tenant_id: str = Depends(get_current_tenant_id)):
    """
    Get RAG configuration

    Args:
        tenant_id: Tenant ID from authentication

    Returns:
        RAG configuration
    """
    try:
        config = {
            "tenant_id": tenant_id,
            "retrieval_modes": [
                {"value": "semantic", "label": "语义搜索"},
                {"value": "keyword", "label": "关键词搜索"},
                {"value": "hybrid", "label": "混合搜索"},
                {"value": "exact", "label": "精确搜索"}
            ],
            "chunking_strategies": [
                {"value": "semantic", "label": "语义分块"},
                {"value": "fixed_size", "label": "固定大小分块"},
                {"value": "overlap", "label": "重叠分块"},
                {"value": "paragraph", "label": "段落分块"},
                {"value": "sentence", "label": "句子分块"}
            ],
            "answer_styles": [
                {"value": "concise", "label": "简洁"},
                {"value": "detailed", "label": "详细"},
                {"value": "creative", "label": "创造性"}
            ],
            "default_config": {
                "retrieval_mode": "semantic",
                "max_results": 5,
                "similarity_threshold": 0.7,
                "max_context_tokens": 2000,
                "chunk_size": 512,
                "overlap_ratio": 0.2,
                "answer_style": "concise",
                "temperature": 0.3
            },
            "limits": {
                "max_query_length": 2000,
                "max_results": 20,
                "max_context_tokens": 8000,
                "max_file_size_mb": 50
            }
        }

        return {
            "success": True,
            "config": config,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"获取RAG配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取RAG配置失败: {str(e)}")