"""
Retrieval Service for Data Agent V4 Backend
Handles similarity search, result filtering, and context building
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
import heapq
import math

# AI/ML libraries
import numpy as np

# Local imports
from ..models.rag_models import (
    DocumentChunk,
    RetrievalResult,
    RetrievalMode,
    VectorCollection,
    RetrievalEntry
)
from .embedding_service import EmbeddingService
from .chromadb_client import ChromaDBService

logger = logging.getLogger(__name__)


@dataclass
class SearchConfig:
    """Configuration for retrieval search"""
    max_results: int = 10
    similarity_threshold: float = 0.7
    diversity_threshold: float = 0.8
    context_max_tokens: int = 2000
    include_metadata: bool = True
    rerank_results: bool = True
    boost_recent: bool = True
    boost_quality: bool = True


class RetrievalService:
    """Document retrieval and context building service"""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.chroma_service = ChromaDBService()

        # Statistics
        self.stats = {
            'total_queries': 0,
            'total_retrievals': 0,
            'average_results_per_query': 0.0,
            'average_query_time_ms': 0.0,
            'cache_hits': 0,
            'diversity_rejections': 0,
            'quality_filtered': 0
        }

        logger.info("检索服务初始化完成")

    async def retrieve_documents(
        self,
        query: str,
        tenant_id: str,
        collections: List[VectorCollection],
        search_config: Optional[SearchConfig] = None
    ) -> Tuple[List[RetrievalResult], Dict[str, Any]]:
        """
        Retrieve relevant documents for a query

        Args:
            query: Search query
            tenant_id: Tenant ID for isolation
            collections: List of collections to search in
            search_config: Search configuration options

        Returns:
            Tuple of (retrieval results, search metadata)
        """
        if search_config is None:
            search_config = SearchConfig()

        start_time = time.time()

        try:
            logger.info(f"开始文档检索: {query[:50]}...")

            # Generate query embedding
            query_embedding, embedding_metadata = await self.embedding_service.generate_embedding(
                query, tenant_id, use_cache=True
            )

            # Search across collections
            all_results = []
            collection_results = {}

            for collection in collections:
                try:
                    collection_name = f"tenant_{tenant_id}_{collection.name}"

                    # Search in ChromaDB
                    documents, scores, metadatas = await self.embedding_service.search_similar_embeddings(
                        query_embedding=query_embedding,
                        collection=collection,
                        tenant_id=tenant_id,
                        n_results=search_config.max_results * 2,  # Get more for filtering
                        where_filter={'tenant_id': tenant_id}
                    )

                    # Convert to RetrievalResult objects
                    collection_specific_results = []
                    for doc, score, metadata in zip(documents, scores, metadatas):
                        if score >= search_config.similarity_threshold:
                            result = RetrievalResult(
                                chunk_id=metadata.get('chunk_id', str(uuid.uuid4())),
                                content=doc,
                                content_preview=doc[:200],
                                document_id=metadata.get('document_id', 0),
                                document_title=metadata.get('file_name', 'Unknown'),
                                file_name=metadata.get('file_name', 'unknown'),
                                file_type=metadata.get('file_type', 'unknown'),
                                page_number=metadata.get('page_number'),
                                chapter_title=metadata.get('chapter_title'),
                                similarity_score=score,
                                rank=0,  # Will be set after sorting
                                content_length=metadata.get('content_length', len(doc)),
                                token_count=metadata.get('token_count', 0),
                                chunk_index=metadata.get('chunk_index', 0),
                                metadata=metadata,
                                tags=[]
                            )

                            collection_specific_results.append(result)

                    collection_results[collection.name] = collection_specific_results
                    all_results.extend(collection_specific_results)

                except Exception as e:
                    logger.error(f"检索集合{collection.name}失败: {str(e)}")
                    continue

            # Apply filters and re-ranking
            filtered_results = await self._filter_and_rerank_results(
                all_results, query, search_config
            )

            # Select final results with diversity
            final_results = await self._select_diverse_results(
                filtered_results, search_config
            )

            # Assign ranks
            for i, result in enumerate(final_results):
                result.rank = i + 1

            processing_time_ms = int((time.time() - start_time) * 1000)

            search_metadata = {
                'query': query,
                'tenant_id': tenant_id,
                'collections_searched': [c.name for c in collections],
                'total_results_before_filtering': len(all_results),
                'results_after_filtering': len(filtered_results),
                'final_results': len(final_results),
                'processing_time_ms': processing_time_ms,
                'embedding_time_ms': embedding_metadata.get('processing_time_ms', 0),
                'search_config': {
                    'max_results': search_config.max_results,
                    'similarity_threshold': search_config.similarity_threshold,
                    'retrieval_mode': 'semantic'
                },
                'collection_results': {name: len(results) for name, results in collection_results.items()},
                'average_similarity': sum(r.similarity_score for r in final_results) / len(final_results) if final_results else 0
            }

            # Update statistics
            self._update_stats(len(final_results), processing_time_ms)

            logger.info(f"检索完成: 找到{len(final_results)}个结果，耗时{processing_time_ms}ms")
            return final_results, search_metadata

        except Exception as e:
            logger.error(f"文档检索失败: {str(e)}")
            raise RuntimeError(f"文档检索失败: {str(e)}") from e

    async def retrieve_hybrid(
        self,
        query: str,
        tenant_id: str,
        collections: List[VectorCollection],
        search_config: Optional[SearchConfig] = None
    ) -> Tuple[List[RetrievalResult], Dict[str, Any]]:
        """
        Hybrid retrieval combining semantic and keyword search

        Args:
            query: Search query
            tenant_id: Tenant ID for isolation
            collections: List of collections to search in
            search_config: Search configuration options

        Returns:
            Tuple of (retrieval results, search metadata)
        """
        if search_config is None:
            search_config = SearchConfig()

        start_time = time.time()

        try:
            logger.info(f"开始混合检索: {query[:50]}...")

            # Semantic search
            semantic_results, semantic_metadata = await self.retrieve_documents(
                query, tenant_id, collections, search_config
            )

            # Keyword search (simplified implementation)
            keyword_results = await self._keyword_search(query, tenant_id, collections, search_config)

            # Combine and re-rank results
            combined_results = await self._combine_search_results(
                semantic_results, keyword_results, search_config
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            hybrid_metadata = {
                'query': query,
                'tenant_id': tenant_id,
                'semantic_results': len(semantic_results),
                'keyword_results': len(keyword_results),
                'combined_results': len(combined_results),
                'processing_time_ms': processing_time_ms,
                'semantic_metadata': semantic_metadata,
                'retrieval_mode': 'hybrid'
            }

            logger.info(f"混合检索完成: 最终{len(combined_results)}个结果")
            return combined_results, hybrid_metadata

        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            raise RuntimeError(f"混合检索失败: {str(e)}") from e

    async def build_context(
        self,
        results: List[RetrievalResult],
        max_tokens: int = 2000,
        include_metadata: bool = True
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Build context from retrieval results

        Args:
            results: Retrieval results
            max_tokens: Maximum context tokens
            include_metadata: Whether to include source metadata

        Returns:
            Tuple of (context text, source references, context metadata)
        """
        if not results:
            return "", [], {"total_tokens": 0, "sources_used": 0}

        context_parts = []
        sources = []
        total_tokens = 0

        for result in results:
            # Check token limit
            result_tokens = result.token_count or self._estimate_tokens(result.content)
            if total_tokens + result_tokens > max_tokens:
                break

            # Add to context
            if include_metadata:
                source_ref = f"{result.file_name}"
                if result.page_number:
                    source_ref += f" (第{result.page_number}页)"
                if result.chapter_title:
                    source_ref += f" - {result.chapter_title}"

                context_parts.append(f"[来源: {source_ref}]\n{result.content}")
                sources.append(source_ref)
            else:
                context_parts.append(result.content)

            total_tokens += result_tokens

        context_text = "\n\n".join(context_parts)

        context_metadata = {
            'total_tokens': total_tokens,
            'sources_used': len(sources),
            'results_used': len(context_parts),
            'max_tokens': max_tokens,
            'truncated': total_tokens >= max_tokens
        }

        return context_text, sources, context_metadata

    async def _filter_and_rerank_results(
        self,
        results: List[RetrievalResult],
        query: str,
        config: SearchConfig
    ) -> List[RetrievalResult]:
        """Filter and re-rank retrieval results"""
        if not results:
            return results

        filtered_results = []

        for result in results:
            # Quality filtering
            if config.boost_quality and result.metadata.get('quality_score', 0) < 0.3:
                self.stats['quality_filtered'] += 1
                continue

            # Duplicate detection (simple content similarity)
            if self._is_duplicate(result, filtered_results):
                continue

            filtered_results.append(result)

        # Re-ranking if enabled
        if config.rerank_results:
            filtered_results = await self._rerank_results(filtered_results, query)

        return filtered_results

    async def _select_diverse_results(
        self,
        results: List[RetrievalResult],
        config: SearchConfig
    ) -> List[RetrievalResult]:
        """Select diverse results using Maximal Marginal Relevance"""
        if not results or len(results) <= config.max_results:
            return results[:config.max_results]

        # Sort by similarity score first
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        selected = [results[0]]  # Always include the best result
        candidates = results[1:]

        while len(selected) < config.max_results and candidates:
            # Find candidate with maximal marginal relevance
            best_candidate = None
            best_mmr = -float('inf')

            for candidate in candidates:
                # Calculate marginal relevance
                max_similarity = max(
                    self._calculate_content_similarity(candidate.content, selected_item.content)
                    for selected_item in selected
                )

                # MMR = λ * similarity - (1-λ) * max_similarity
                mmr = (config.diversity_threshold * candidate.similarity_score -
                       (1 - config.diversity_threshold) * max_similarity)

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_candidate = candidate

            if best_candidate:
                selected.append(best_candidate)
                candidates.remove(best_candidate)
            else:
                break

        # Sort selected results by final score
        selected.sort(key=lambda x: x.similarity_score, reverse=True)

        return selected

    async def _keyword_search(
        self,
        query: str,
        tenant_id: str,
        collections: List[VectorCollection],
        config: SearchConfig
    ) -> List[RetrievalResult]:
        """Simple keyword-based search"""
        # Extract keywords from query
        keywords = self._extract_keywords(query.lower())

        keyword_results = []

        for collection in collections:
            try:
                collection_name = f"tenant_{tenant_id}_{collection.name}"

                # This is a simplified keyword search
                # In a real implementation, this would use a proper text search engine
                results = await self.chroma_service.keyword_search(
                    collection_name=collection_name,
                    keywords=keywords,
                    tenant_id=tenant_id,
                    limit=config.max_results
                )

                for result in results:
                    if result['score'] >= config.similarity_threshold:
                        retrieval_result = RetrievalResult(
                            chunk_id=result.get('id', str(uuid.uuid4())),
                            content=result.get('content', ''),
                            content_preview=result.get('content', '')[:200],
                            document_id=result.get('document_id', 0),
                            document_title=result.get('file_name', 'Unknown'),
                            file_name=result.get('file_name', 'unknown'),
                            file_type=result.get('file_type', 'unknown'),
                            page_number=result.get('page_number'),
                            chapter_title=result.get('chapter_title'),
                            similarity_score=result['score'],
                            rank=0,
                            content_length=result.get('content_length', 0),
                            token_count=result.get('token_count', 0),
                            chunk_index=result.get('chunk_index', 0),
                            metadata=result.get('metadata', {}),
                            tags=[]
                        )
                        keyword_results.append(retrieval_result)

            except Exception as e:
                logger.warning(f"关键词搜索失败: {str(e)}")
                continue

        return keyword_results

    async def _combine_search_results(
        self,
        semantic_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult],
        config: SearchConfig
    ) -> List[RetrievalResult]:
        """Combine semantic and keyword search results"""
        # Create a dictionary to store combined results by chunk_id
        combined_dict = {}

        # Add semantic results
        for result in semantic_results:
            combined_dict[result.chunk_id] = {
                'result': result,
                'semantic_score': result.similarity_score,
                'keyword_score': 0.0
            }

        # Add keyword results and combine scores
        for result in keyword_results:
            if result.chunk_id in combined_dict:
                combined_dict[result.chunk_id]['keyword_score'] = result.similarity_score
            else:
                combined_dict[result.chunk_id] = {
                    'result': result,
                    'semantic_score': 0.0,
                    'keyword_score': result.similarity_score
                }

        # Calculate combined scores
        combined_results = []
        for chunk_id, data in combined_dict.items():
            result = data['result']

            # Weighted combination: 70% semantic, 30% keyword
            combined_score = (0.7 * data['semantic_score'] + 0.3 * data['keyword_score'])
            result.similarity_score = combined_score

            combined_results.append(result)

        # Sort by combined score
        combined_results.sort(key=lambda x: x.similarity_score, reverse=True)

        return combined_results[:config.max_results]

    async def _rerank_results(
        self,
        results: List[RetrievalResult],
        query: str
    ) -> List[RetrievalResult]:
        """Re-rank results based on additional criteria"""
        if not results:
            return results

        query_terms = set(query.lower().split())

        for result in results:
            # Boost for recent content
            if result.metadata.get('created_at'):
                try:
                    created_date = datetime.fromisoformat(result.metadata['created_at'])
                    days_ago = (datetime.utcnow() - created_date).days
                    recency_boost = max(0, 1 - days_ago / 365)  # Year decay
                    result.similarity_score *= (1 + 0.1 * recency_boost)
                except:
                    pass

            # Boost for query term coverage
            content_lower = result.content.lower()
            term_coverage = len([term for term in query_terms if term in content_lower]) / len(query_terms)
            result.similarity_score *= (1 + 0.1 * term_coverage)

        # Re-sort by updated scores
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        return results

    def _is_duplicate(
        self,
        result: RetrievalResult,
        existing_results: List[RetrievalResult]
    ) -> bool:
        """Check if result is too similar to existing results"""
        threshold = 0.9  # Similarity threshold for duplicate detection

        for existing in existing_results:
            if (result.document_id == existing.document_id and
                abs(result.chunk_index - existing.chunk_index) <= 1):
                return True

            similarity = self._calculate_content_similarity(
                result.content, existing.content
            )
            if similarity > threshold:
                return True

        return False

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content pieces"""
        if not content1 or not content2:
            return 0.0

        # Simple Jaccard similarity on words
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        # Simple keyword extraction
        # Remove common stop words and return remaining words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     '的', '是', '在', '有', '和', '与', '或', '但是', '在', '到', '为了'}

        words = query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 1]

        return keywords

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if not text:
            return 0

        # Simple heuristic
        return len(text.split()) * 1.3  # Approximate tokens

    def _update_stats(self, result_count: int, processing_time_ms: int):
        """Update service statistics"""
        self.stats['total_queries'] += 1
        self.stats['total_retrievals'] += result_count

        if self.stats['total_queries'] > 0:
            self.stats['average_results_per_query'] = (
                self.stats['total_retrievals'] / self.stats['total_queries']
            )

        total_time = self.stats['average_query_time_ms'] * (self.stats['total_queries'] - 1) + processing_time_ms
        self.stats['average_query_time_ms'] = total_time / self.stats['total_queries']

    async def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            **self.stats,
            'service_name': 'retrieval_service',
            'cache_enabled': True,
            'supported_modes': ['semantic', 'keyword', 'hybrid', 'exact']
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the service"""
        try:
            # Test embedding service
            embedding_health = await self.embedding_service.health_check()

            # Test ChromaDB service
            chroma_health = await self.chroma_service.health_check()

            health_status = {
                'status': 'healthy' if embedding_health['status'] == 'healthy' and chroma_health else 'unhealthy',
                'embedding_service': embedding_health['status'],
                'chromadb_service': 'connected' if chroma_health else 'disconnected',
                'statistics': await self.get_statistics()
            }

            return health_status

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }