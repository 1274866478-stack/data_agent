"""
RAG Service for Data Agent V4 Backend
Main orchestration service for Retrieval-Augmented Generation
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

# Local imports
from ..models.rag_models import (
    RAGQueryRequest,
    RAGQueryResponse,
    RetrievalResult,
    RetrievalSession,
    RetrievalEntry,
    RetrievalLog,
    VectorCollection,
    ProcessingStep,
    RetrievalMode,
    DocumentStatus,
    RAGStats
)
from .rag_document_processor import DocumentProcessor
from .embedding_service import EmbeddingService
from .retrieval_service import RetrievalService, SearchConfig
from .zhipu_client import ZhipuService
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    """Main RAG processing service"""

    def __init__(self):
        # Initialize component services
        self.document_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self.retrieval_service = RetrievalService()
        self.zhipu_service = ZhipuService()

        # Session management
        self.active_sessions: Dict[str, RetrievalSession] = {}

        # Statistics
        self.stats = {
            'total_queries_processed': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_documents_processed': 0,
            'total_chunks_generated': 0,
            'average_response_time_ms': 0.0,
            'cache_hit_rate': 0.0,
            'user_satisfaction_average': 0.0
        }

        logger.info("RAG服务初始化完成")

    async def process_query(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """
        Process a RAG query end-to-end

        Args:
            request: RAG query request

        Returns:
            RAG query response
        """
        start_time = time.time()
        processing_steps = []
        entry_id = str(uuid.uuid4())

        try:
            logger.info(f"开始处理RAG查询: {request.query[:50]}...")

            # Step 1: Session management
            processing_steps.append("会话管理")
            session = await self._get_or_create_session(
                request.tenant_id,
                request.session_id,
                request.retrieval_mode,
                request.max_results,
                request.similarity_threshold,
                request.collections
            )

            # Step 2: Query embedding
            processing_steps.append("查询向量化")
            query_embedding, embedding_metadata = await self.embedding_service.generate_embedding(
                request.query,
                request.tenant_id,
                use_cache=True
            )

            # Step 3: Document retrieval
            processing_steps.append("文档检索")
            collections = await self._get_tenant_collections(request.tenant_id, request.collections)
            search_config = SearchConfig(
                max_results=request.max_results,
                similarity_threshold=request.similarity_threshold,
                context_max_tokens=request.max_context_tokens,
                include_metadata=request.include_metadata
            )

            retrieval_results, retrieval_metadata = await self.retrieval_service.retrieve_documents(
                request.query,
                request.tenant_id,
                collections,
                search_config
            )

            # Step 4: Context building
            processing_steps.append("上下文构建")
            context_text, sources, context_metadata = await self.retrieval_service.build_context(
                retrieval_results,
                request.max_context_tokens,
                request.include_metadata
            )

            # Step 5: Answer generation
            answer = None
            answer_confidence = None
            generation_time_ms = 0

            if request.generate_answer and context_text:
                processing_steps.append("答案生成")
                answer_start = time.time()

                try:
                    answer = await self._generate_answer(
                        request.query,
                        context_text,
                        request.answer_style,
                        request.temperature
                    )

                    # Estimate confidence based on context quality
                    if retrieval_results:
                        answer_confidence = sum(r.similarity_score for r in retrieval_results) / len(retrieval_results)
                    else:
                        answer_confidence = 0.0

                    generation_time_ms = int((time.time() - answer_start) * 1000)
                    processing_steps.append("答案生成完成")

                except Exception as e:
                    logger.error(f"答案生成失败: {str(e)}")
                    answer = None
                    answer_confidence = 0.0
                    generation_time_ms = int((time.time() - answer_start) * 1000)
                    processing_steps.append("答案生成失败")

            # Step 6: Create retrieval entry
            retrieval_entry = await self._create_retrieval_entry(
                entry_id=entry_id,
                session_id=session.id,
                tenant_id=request.tenant_id,
                original_query=request.query,
                processed_query=request.query,
                query_embedding=query_embedding,
                retrieval_mode=request.retrieval_mode,
                retrieved_results=[r.chunk_id for r in retrieval_results],
                retrieval_scores=[r.similarity_score for r in retrieval_results],
                context_used=[r.chunk_id for r in retrieval_results],
                generated_answer=answer,
                answer_confidence=answer_confidence,
                sources_cited=sources,
                retrieval_time_ms=retrieval_metadata.get('processing_time_ms', 0),
                generation_time_ms=generation_time_ms,
                relevance_score=sum(r.similarity_score for r in retrieval_results) / len(retrieval_results) if retrieval_results else 0.0
            )

            # Calculate processing time
            total_time_ms = int((time.time() - start_time) * 1000)

            # Update session statistics
            await self._update_session_stats(session, retrieval_entry)

            # Create response
            response = RAGQueryResponse(
                success=True,
                query=request.query,
                tenant_id=request.tenant_id,
                session_id=session.id,
                entry_id=entry_id,
                retrieval_results=retrieval_results,
                total_retrieved=len(retrieval_results),
                retrieval_time_ms=retrieval_metadata.get('processing_time_ms', 0),
                answer=answer,
                answer_confidence=answer_confidence,
                generation_time_ms=generation_time_ms,
                context_used=[r.chunk_id for r in retrieval_results],
                context_length=len(context_text),
                context_tokens=context_metadata.get('total_tokens', 0),
                processing_steps=processing_steps,
                total_time_ms=total_time_ms,
                collections_searched=[c.name for c in collections],
                average_relevance=context_metadata.get('total_tokens', 0) / len(retrieval_results) if retrieval_results else 0.0,
                query_understanding=self._generate_query_understanding(request.query, retrieval_results)
            )

            # Update global statistics
            self._update_global_stats(True, total_time_ms)

            logger.info(f"RAG查询处理完成: {len(retrieval_results)}个检索结果，耗时{total_time_ms}ms")
            return response

        except Exception as e:
            total_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)

            logger.error(f"RAG查询处理失败: {error_message}")

            # Update global statistics
            self._update_global_stats(False, total_time_ms)

            # Create error response
            return RAGQueryResponse(
                success=False,
                query=request.query,
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                entry_id=entry_id,
                retrieval_results=[],
                total_retrieved=0,
                retrieval_time_ms=0,
                answer=None,
                answer_confidence=None,
                generation_time_ms=0,
                context_used=[],
                context_length=0,
                context_tokens=0,
                processing_steps=processing_steps,
                total_time_ms=total_time_ms,
                collections_searched=[],
                error_message=error_message,
                warnings=[f"处理失败: {error_message}"]
            )

    async def process_document(
        self,
        file_content: bytes,
        file_name: str,
        file_type: str,
        document_id: int,
        tenant_id: str,
        collection_id: str,
        chunking_strategy: str = "semantic",
        chunk_size: int = 512,
        overlap_ratio: float = 0.2
    ) -> Dict[str, Any]:
        """
        Process and index a document for RAG

        Args:
            file_content: Document file content
            file_name: Original file name
            file_type: File type
            document_id: Document ID in database
            tenant_id: Tenant ID
            collection_id: Target collection ID
            chunking_strategy: Chunking strategy
            chunk_size: Target chunk size
            overlap_ratio: Overlap ratio

        Returns:
            Processing metadata
        """
        start_time = time.time()

        try:
            logger.info(f"开始处理文档: {file_name}")

            # Get collection information
            collection = await self._get_collection_by_id(collection_id, tenant_id)
            if not collection:
                raise ValueError(f"集合不存在: {collection_id}")

            # Step 1: Document processing and chunking
            chunks, processing_metadata = await self.document_processor.process_document(
                file_content=file_content,
                file_name=file_name,
                file_type=file_type,
                document_id=document_id,
                tenant_id=tenant_id,
                collection_id=collection_id,
                chunking_strategy=DocumentChunk(chunking_strategy) if isinstance(chunking_strategy, str) else chunking_strategy,
                chunk_size=chunk_size,
                overlap_ratio=overlap_ratio
            )

            # Step 2: Generate embeddings for chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings, embedding_metadata = await self.embedding_service.generate_batch_embeddings(
                texts=chunk_texts,
                tenant_id=tenant_id,
                use_cache=True
            )

            # Step 3: Store embeddings in vector database
            storage_metadata = await self.embedding_service.store_embeddings(
                chunks=chunks,
                embeddings=embeddings,
                collection=collection,
                tenant_id=tenant_id
            )

            # Calculate total processing time
            total_time_ms = int((time.time() - start_time) * 1000)

            # Prepare final metadata
            final_metadata = {
                'document_id': document_id,
                'tenant_id': tenant_id,
                'collection_id': collection_id,
                'file_name': file_name,
                'file_type': file_type,
                'chunks_created': len(chunks),
                'embeddings_generated': len(embeddings),
                'processing_time_ms': total_time_ms,
                'chunking_strategy': chunking_strategy,
                'chunk_size': chunk_size,
                'overlap_ratio': overlap_ratio,
                'processing_metadata': processing_metadata,
                'embedding_metadata': embedding_metadata,
                'storage_metadata': storage_metadata,
                'status': 'completed'
            }

            # Update global statistics
            self.stats['total_documents_processed'] += 1
            self.stats['total_chunks_generated'] += len(chunks)

            logger.info(f"文档处理完成: {file_name} -> {len(chunks)}个块，耗时{total_time_ms}ms")
            return final_metadata

        except Exception as e:
            total_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)

            logger.error(f"文档处理失败 {file_name}: {error_message}")

            return {
                'document_id': document_id,
                'tenant_id': tenant_id,
                'collection_id': collection_id,
                'file_name': file_name,
                'file_type': file_type,
                'chunks_created': 0,
                'embeddings_generated': 0,
                'processing_time_ms': total_time_ms,
                'status': 'failed',
                'error_message': error_message
            }

    async def get_session_history(
        self,
        session_id: str,
        tenant_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            if session_id not in self.active_sessions:
                return []

            session = self.active_sessions[session_id]
            if session.tenant_id != tenant_id:
                raise ValueError("会话租户不匹配")

            # In a real implementation, this would query the database
            # For now, return placeholder data
            return [{
                'entry_id': str(uuid.uuid4()),
                'query': '示例查询',
                'answer': '示例答案',
                'created_at': datetime.utcnow().isoformat(),
                'retrieval_count': 5,
                'confidence_score': 0.85
            } for _ in range(min(limit, 3))]

        except Exception as e:
            logger.error(f"获取会话历史失败: {str(e)}")
            return []

    async def update_user_feedback(
        self,
        entry_id: str,
        tenant_id: str,
        feedback_rating: int,
        feedback_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user feedback for a retrieval entry"""
        try:
            # Validate feedback rating
            if not 1 <= feedback_rating <= 5:
                raise ValueError("反馈评分必须在1-5之间")

            # In a real implementation, this would update the database
            # For now, just log the feedback
            logger.info(f"用户反馈更新: {entry_id} = {feedback_rating}星")

            # Update satisfaction statistics
            self._update_satisfaction_stats(feedback_rating)

            return {
                'entry_id': entry_id,
                'feedback_rating': feedback_rating,
                'feedback_comment': feedback_comment,
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'updated'
            }

        except Exception as e:
            logger.error(f"更新用户反馈失败: {str(e)}")
            return {
                'entry_id': entry_id,
                'error': str(e),
                'status': 'failed'
            }

    async def _get_or_create_session(
        self,
        tenant_id: str,
        session_id: Optional[str],
        retrieval_mode: RetrievalMode,
        max_results: int,
        similarity_threshold: float,
        collections: List[str]
    ) -> RetrievalSession:
        """Get existing session or create new one"""
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.updated_at = datetime.utcnow()
            session.last_query_at = datetime.utcnow()
            return session

        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        session = RetrievalSession(
            id=new_session_id,
            tenant_id=tenant_id,
            retrieval_mode=retrieval_mode,
            max_context_chunks=max_results,
            similarity_threshold=similarity_threshold,
            collections=collections,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        self.active_sessions[new_session_id] = session
        return session

    async def _get_tenant_collections(
        self,
        tenant_id: str,
        collection_ids: List[str]
    ) -> List[VectorCollection]:
        """Get tenant collections"""
        # In a real implementation, this would query the database
        # For now, return mock collections
        collections = []

        if not collection_ids:
            # Default collection
            collections.append(VectorCollection(
                id="default",
                tenant_id=tenant_id,
                name="documents",
                display_name="文档集合",
                chroma_collection_id=f"tenant_{tenant_id}_documents"
            ))
        else:
            # Get specific collections
            for collection_id in collection_ids:
                collections.append(VectorCollection(
                    id=collection_id,
                    tenant_id=tenant_id,
                    name=f"collection_{collection_id}",
                    display_name=f"集合 {collection_id}",
                    chroma_collection_id=f"tenant_{tenant_id}_{collection_id}"
                ))

        return collections

    async def _get_collection_by_id(
        self,
        collection_id: str,
        tenant_id: str
    ) -> Optional[VectorCollection]:
        """Get collection by ID"""
        # In a real implementation, this would query the database
        return VectorCollection(
            id=collection_id,
            tenant_id=tenant_id,
            name="documents",
            display_name="文档集合",
            chroma_collection_id=f"tenant_{tenant_id}_documents"
        )

    async def _generate_answer(
        self,
        query: str,
        context: str,
        answer_style: str,
        temperature: float
    ) -> str:
        """Generate answer using LLM"""
        try:
            # Construct prompt
            if answer_style == "detailed":
                prompt = f"""基于以下上下文信息，请详细回答用户的问题。要求：
1. 答案要详细和全面
2. 引用具体的上下文内容
3. 提供深入的分析和见解

上下文信息：
{context}

用户问题：{query}

详细回答："""
            elif answer_style == "creative":
                prompt = f"""基于以下上下文信息，请创造性地回答用户的问题。要求：
1. 答案要有创造性和新意
2. 可以结合上下文进行延伸思考
3. 提供独特的观点和见解

上下文信息：
{context}

用户问题：{query}

创造性回答："""
            else:  # concise (default)
                prompt = f"""基于以下上下文信息，请简洁准确地回答用户的问题。

上下文信息：
{context}

用户问题：{query}

简洁回答："""

            # Generate answer using Zhipu service
            answer = await self.zhipu_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1000
            )

            return answer.strip()

        except Exception as e:
            logger.error(f"答案生成失败: {str(e)}")
            raise

    def _generate_query_understanding(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> str:
        """Generate query understanding explanation"""
        if not results:
            return f"查询理解: '{query}' - 未找到相关文档"

        avg_relevance = sum(r.similarity_score for r in results) / len(results)
        relevant_docs = len([r for r in results if r.similarity_score > 0.8])

        understanding = f"查询理解: '{query}' - "
        understanding += f"找到{len(results)}个相关文档，"
        understanding += f"平均相关性{avg_relevance:.2f}，"
        understanding += f"{relevant_docs}个高度相关文档"

        return understanding

    async def _create_retrieval_entry(
        self,
        entry_id: str,
        session_id: str,
        tenant_id: str,
        original_query: str,
        processed_query: str,
        query_embedding: List[float],
        retrieval_mode: RetrievalMode,
        retrieved_results: List[str],
        retrieval_scores: List[float],
        context_used: List[str],
        generated_answer: Optional[str],
        answer_confidence: Optional[float],
        sources_cited: List[str],
        retrieval_time_ms: int,
        generation_time_ms: int,
        relevance_score: float
    ) -> RetrievalEntry:
        """Create a retrieval entry for logging"""
        return RetrievalEntry(
            id=entry_id,
            session_id=session_id,
            tenant_id=tenant_id,
            query_index=0,  # Would be actual index in real implementation
            original_query=original_query,
            processed_query=processed_query,
            query_embedding=query_embedding,
            retrieval_mode=retrieval_mode,
            retrieved_chunks=retrieved_results,
            retrieval_scores=retrieval_scores,
            context_used=context_used,
            generated_answer=generated_answer,
            answer_confidence=answer_confidence,
            sources_cited=sources_cited,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            total_time_ms=retrieval_time_ms + generation_time_ms,
            relevance_score=relevance_score
        )

    async def _update_session_stats(self, session: RetrievalSession, entry: RetrievalEntry):
        """Update session statistics"""
        session.query_count += 1
        session.total_retrieved_chunks += len(entry.retrieved_chunks)
        session.average_response_time_ms = (
            (session.average_response_time_ms * (session.query_count - 1) + entry.total_time_ms) /
            session.query_count
        )
        session.last_query_at = entry.created_at

    def _update_global_stats(self, success: bool, processing_time_ms: int):
        """Update global service statistics"""
        self.stats['total_queries_processed'] += 1

        if success:
            self.stats['successful_queries'] += 1
        else:
            self.stats['failed_queries'] += 1

        # Update average response time
        total_time = self.stats['average_response_time_ms'] * (self.stats['total_queries_processed'] - 1) + processing_time_ms
        self.stats['average_response_time_ms'] = total_time / self.stats['total_queries_processed']

    def _update_satisfaction_stats(self, feedback_rating: int):
        """Update user satisfaction statistics"""
        current_avg = self.stats['user_satisfaction_average']
        current_count = self.stats['successful_queries']

        # Calculate new average
        new_count = current_count + 1
        new_average = (current_avg * current_count + feedback_rating) / new_count

        self.stats['user_satisfaction_average'] = new_average

    async def get_statistics(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get service statistics"""
        component_stats = {
            'embedding_service': await self.embedding_service.get_statistics(),
            'retrieval_service': await self.retrieval_service.get_statistics(),
        }

        rag_stats = {
            **self.stats,
            'active_sessions': len(self.active_sessions),
            'component_stats': component_stats,
            'service_name': 'rag_service',
            'tenant_id': tenant_id
        }

        return rag_stats

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the RAG service"""
        try:
            # Check component services
            embedding_health = await self.embedding_service.health_check()
            retrieval_health = await self.retrieval_service.health_check()

            # Overall health
            overall_status = 'healthy'
            if (embedding_health.get('status') != 'healthy' or
                retrieval_health.get('status') != 'healthy'):
                overall_status = 'degraded'

            health_status = {
                'status': overall_status,
                'components': {
                    'embedding_service': embedding_health.get('status'),
                    'retrieval_service': retrieval_health.get('status'),
                    'document_processor': 'healthy',  # Simple service, assume healthy
                    'zhipu_service': 'healthy'  # Would check actual service
                },
                'active_sessions': len(self.active_sessions),
                'statistics': await self.get_statistics()
            }

            return health_status

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    async def cleanup(self):
        """Cleanup resources"""
        # Clear expired sessions
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if session.expires_at and session.expires_at <= current_time
        ]

        for session_id in expired_sessions:
            del self.active_sessions[session_id]

        # Cleanup component services
        await self.embedding_service.cleanup_expired_cache()

        logger.info(f"RAG服务清理完成，清理了{len(expired_sessions)}个过期会话")