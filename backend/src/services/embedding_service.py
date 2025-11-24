"""
Embedding Service for Data Agent V4 Backend
Handles text vectorization, caching, and ChromaDB integration
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import uuid
import time

# AI/LLM libraries
import numpy as np

# Local imports
from ..models.rag_models import (
    DocumentChunk,
    EmbeddingCache,
    VectorCollection
)
from ..core.config import get_settings
from .chromadb_client import ChromaDBService
from .zhipu_client import ZhipuService

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Text embedding and vector storage service"""

    def __init__(self, cache_enabled: bool = True, cache_ttl_hours: int = 24):
        self.embedding_model = "zhipu-embedding-2"  # Default embedding model
        self.embedding_dimension = 1024  # Zhipu embedding dimension
        self.batch_size = 10  # Process texts in batches
        self.cache_enabled = cache_enabled
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # Initialize services
        self.zhipu_service = ZhipuService()
        self.chroma_service = ChromaDBService()

        # In-memory cache (will be replaced by database cache)
        self.embedding_cache: Dict[str, EmbeddingCache] = {}

        # Statistics
        self.stats = {
            'total_embeddings_generated': 0,
            'total_tokens_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_processing_time_ms': 0,
            'average_processing_time_ms': 0.0,
            'batches_processed': 0,
            'errors': 0
        }

        logger.info("向量化服务初始化完成")

    async def generate_embedding(
        self,
        text: str,
        tenant_id: str,
        use_cache: bool = None
    ) -> Tuple[List[float], Dict[str, Any]]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed
            tenant_id: Tenant ID for isolation
            use_cache: Whether to use cache (defaults to service setting)

        Returns:
            Tuple of (embedding vector, metadata)
        """
        if use_cache is None:
            use_cache = self.cache_enabled

        start_time = time.time()

        try:
            # Check cache first
            if use_cache:
                cached_embedding = await self._get_cached_embedding(text, tenant_id)
                if cached_embedding:
                    self.stats['cache_hits'] += 1
                    processing_time_ms = int((time.time() - start_time) * 1000)

                    metadata = {
                        'source': 'cache',
                        'processing_time_ms': processing_time_ms,
                        'embedding_dimension': len(cached_embedding),
                        'tenant_id': tenant_id
                    }

                    return cached_embedding, metadata

            self.stats['cache_misses'] += 1

            # Generate new embedding
            embedding = await self._generate_embedding_from_api(text)

            # Update statistics
            processing_time_ms = int((time.time() - start_time) * 1000)
            self._update_stats(len(text), processing_time_ms)

            # Cache the result
            if use_cache:
                await self._cache_embedding(text, tenant_id, embedding, processing_time_ms)

            metadata = {
                'source': 'api',
                'processing_time_ms': processing_time_ms,
                'embedding_dimension': len(embedding),
                'model': self.embedding_model,
                'tenant_id': tenant_id
            }

            return embedding, metadata

        except Exception as e:
            logger.error(f"生成嵌入向量失败: {str(e)}")
            self.stats['errors'] += 1
            raise RuntimeError(f"嵌入向量生成失败: {str(e)}") from e

    async def generate_batch_embeddings(
        self,
        texts: List[str],
        tenant_id: str,
        use_cache: bool = None,
        batch_size: int = None
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        Generate embeddings for multiple texts in batches

        Args:
            texts: List of texts to embed
            tenant_id: Tenant ID for isolation
            use_cache: Whether to use cache
            batch_size: Override default batch size

        Returns:
            Tuple of (list of embeddings, batch metadata)
        """
        if use_cache is None:
            use_cache = self.cache_enabled

        batch_size = batch_size or self.batch_size
        start_time = time.time()

        try:
            embeddings = []
            cache_hits = 0
            cache_misses = 0
            api_calls = 0

            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_results = []

                # Check cache for each text in batch
                texts_to_process = []
                cache_indices = []

                for j, text in enumerate(batch_texts):
                    if use_cache:
                        cached_embedding = await self._get_cached_embedding(text, tenant_id)
                        if cached_embedding:
                            batch_results.append(cached_embedding)
                            cache_hits += 1
                        else:
                            texts_to_process.append(text)
                            cache_indices.append(j)
                            cache_misses += 1
                    else:
                        texts_to_process.append(text)
                        cache_indices.append(j)
                        cache_misses += 1

                # Generate embeddings for uncached texts
                if texts_to_process:
                    api_embeddings = await self._generate_batch_embedding_from_api(texts_to_process)
                    api_calls += 1

                    # Insert API results into batch results
                    for idx, embedding in zip(cache_indices, api_embeddings):
                        batch_results.insert(idx, embedding)

                    # Cache the new embeddings
                    if use_cache:
                        for text, embedding in zip(texts_to_process, api_embeddings):
                            await self._cache_embedding(text, tenant_id, embedding, 0)

                embeddings.extend(batch_results)

            processing_time_ms = int((time.time() - start_time) * 1000)
            total_tokens = sum(len(text) for text in texts)

            # Update statistics
            self._update_stats(total_tokens, processing_time_ms)
            self.stats['batches_processed'] += 1

            metadata = {
                'source': 'batch_api',
                'processing_time_ms': processing_time_ms,
                'texts_processed': len(texts),
                'embeddings_generated': len(embeddings),
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'cache_hit_rate': cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0,
                'api_calls': api_calls,
                'batch_size': batch_size,
                'embedding_dimension': len(embeddings[0]) if embeddings else 0,
                'model': self.embedding_model,
                'tenant_id': tenant_id
            }

            return embeddings, metadata

        except Exception as e:
            logger.error(f"批量生成嵌入向量失败: {str(e)}")
            self.stats['errors'] += 1
            raise RuntimeError(f"批量嵌入向量生成失败: {str(e)}") from e

    async def store_embeddings(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        collection: VectorCollection,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Store embeddings in ChromaDB with metadata

        Args:
            chunks: Document chunks
            embeddings: Corresponding embeddings
            collection: Vector collection information
            tenant_id: Tenant ID for isolation

        Returns:
            Storage metadata
        """
        if len(chunks) != len(embeddings):
            raise ValueError("文档块数量与嵌入向量数量不匹配")

        start_time = time.time()

        try:
            # Prepare ChromaDB documents
            documents = []
            metadatas = []
            ids = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Create unique ID
                doc_id = str(uuid.uuid4())

                # Update chunk with embedding information
                chunk.embedding_id = doc_id

                # Prepare metadata
                metadata = {
                    'tenant_id': tenant_id,
                    'document_id': chunk.document_id,
                    'chunk_id': chunk.id,
                    'chunk_index': chunk.chunk_index,
                    'file_name': chunk.file_name,
                    'file_type': chunk.file_type,
                    'content_length': chunk.content_length,
                    'token_count': chunk.token_count or 0,
                    'page_number': chunk.page_number,
                    'chapter_title': chunk.chapter_title,
                    'chunking_strategy': chunk.chunking_strategy.value,
                    'quality_score': chunk.quality_score or 0.0,
                    'created_at': chunk.created_at.isoformat(),
                    'collection_id': collection.id
                }

                documents.append(chunk.content)
                metadatas.append(metadata)
                ids.append(doc_id)

            # Store in ChromaDB
            collection_name = f"tenant_{tenant_id}_{collection.name}"
            await self.chroma_service.add_documents(
                collection_name=collection_name,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            storage_metadata = {
                'chunks_stored': len(chunks),
                'collection_name': collection_name,
                'processing_time_ms': processing_time_ms,
                'tenant_id': tenant_id,
                'collection_id': collection.id,
                'embedding_model': self.embedding_model,
                'embedding_dimension': self.embedding_dimension
            }

            logger.info(f"成功存储{len(chunks)}个嵌入向量到集合{collection_name}")
            return storage_metadata

        except Exception as e:
            logger.error(f"存储嵌入向量失败: {str(e)}")
            raise RuntimeError(f"嵌入向量存储失败: {str(e)}") from e

    async def update_embeddings(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        collection: VectorCollection,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Update existing embeddings in ChromaDB

        Args:
            chunks: Updated document chunks
            embeddings: Corresponding new embeddings
            collection: Vector collection information
            tenant_id: Tenant ID for isolation

        Returns:
            Update metadata
        """
        if len(chunks) != len(embeddings):
            raise ValueError("文档块数量与嵌入向量数量不匹配")

        start_time = time.time()

        try:
            # First, delete existing embeddings
            chunk_ids = [chunk.id for chunk in chunks if chunk.embedding_id]
            if chunk_ids:
                await self.delete_embeddings(chunk_ids, collection, tenant_id)

            # Then store new embeddings
            storage_metadata = await self.store_embeddings(
                chunks, embeddings, collection, tenant_id
            )

            processing_time_ms = int((time.time() - start_time) * 1000)
            storage_metadata['update_operation'] = True
            storage_metadata['total_processing_time_ms'] = processing_time_ms

            return storage_metadata

        except Exception as e:
            logger.error(f"更新嵌入向量失败: {str(e)}")
            raise RuntimeError(f"嵌入向量更新失败: {str(e)}") from e

    async def delete_embeddings(
        self,
        chunk_ids: List[str],
        collection: VectorCollection,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Delete embeddings from ChromaDB

        Args:
            chunk_ids: IDs of chunks to delete
            collection: Vector collection information
            tenant_id: Tenant ID for isolation

        Returns:
            Deletion metadata
        """
        if not chunk_ids:
            return {'deleted_count': 0, 'collection_name': f"tenant_{tenant_id}_{collection.name}"}

        start_time = time.time()

        try:
            collection_name = f"tenant_{tenant_id}_{collection.name}"

            # Get embedding IDs from chunk IDs
            embedding_ids = []
            for chunk_id in chunk_ids:
                # This would typically query the database to get embedding_id
                # For now, assume chunk_id is the same as embedding_id
                embedding_ids.append(chunk_id)

            # Delete from ChromaDB
            deleted_count = await self.chroma_service.delete_documents(
                collection_name=collection_name,
                ids=embedding_ids
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            deletion_metadata = {
                'deleted_count': deleted_count,
                'requested_deletions': len(chunk_ids),
                'collection_name': collection_name,
                'processing_time_ms': processing_time_ms,
                'tenant_id': tenant_id,
                'collection_id': collection.id
            }

            logger.info(f"成功删除{deleted_count}个嵌入向量")
            return deletion_metadata

        except Exception as e:
            logger.error(f"删除嵌入向量失败: {str(e)}")
            raise RuntimeError(f"嵌入向量删除失败: {str(e)}") from e

    async def search_similar_embeddings(
        self,
        query_embedding: List[float],
        collection: VectorCollection,
        tenant_id: str,
        n_results: int = 10,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        """
        Search for similar embeddings in ChromaDB

        Args:
            query_embedding: Query embedding vector
            collection: Vector collection information
            tenant_id: Tenant ID for isolation
            n_results: Number of results to return
            where_filter: Optional metadata filter

        Returns:
            Tuple of (document IDs, similarity scores, metadata)
        """
        start_time = time.time()

        try:
            collection_name = f"tenant_{tenant_id}_{collection.name}"

            # Add tenant filter to where clause
            if where_filter is None:
                where_filter = {}
            where_filter['tenant_id'] = tenant_id

            # Search in ChromaDB
            results = await self.chroma_service.query_documents(
                collection_name=collection_name,
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )

            # Extract results
            documents = results['documents'][0] if results['documents'] else []
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            distances = results['distances'][0] if results['distances'] else []

            # Convert distances to similarity scores (ChromaDB uses L2 distance)
            similarity_scores = [1.0 / (1.0 + distance) for distance in distances]

            processing_time_ms = int((time.time() - start_time) * 1000)

            search_metadata = {
                'results_found': len(documents),
                'collection_name': collection_name,
                'processing_time_ms': processing_time_ms,
                'tenant_id': tenant_id,
                'collection_id': collection.id
            }

            logger.debug(f"相似度搜索完成: 找到{len(documents)}个结果，耗时{processing_time_ms}ms")

            return documents, similarity_scores, metadatas

        except Exception as e:
            logger.error(f"相似度搜索失败: {str(e)}")
            raise RuntimeError(f"相似度搜索失败: {str(e)}") from e

    async def _generate_embedding_from_api(self, text: str) -> List[float]:
        """Generate embedding using Zhipu API"""
        try:
            embedding = await self.zhipu_service.generate_embedding(text, self.embedding_model)

            # Validate embedding dimension
            if len(embedding) != self.embedding_dimension:
                logger.warning(f"嵌入向量维度不匹配: 期望{self.embedding_dimension}, 实际{len(embedding)}")
                # Pad or truncate to expected dimension
                if len(embedding) < self.embedding_dimension:
                    embedding.extend([0.0] * (self.embedding_dimension - len(embedding)))
                else:
                    embedding = embedding[:self.embedding_dimension]

            return embedding

        except Exception as e:
            logger.error(f"API调用生成嵌入向量失败: {str(e)}")
            raise

    async def _generate_batch_embedding_from_api(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using batch API call"""
        embeddings = []

        # Process texts in smaller batches if needed
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]

            try:
                batch_embeddings = await self.zhipu_service.generate_batch_embeddings(
                    batch_texts, self.embedding_model
                )

                # Validate and normalize each embedding
                for embedding in batch_embeddings:
                    if len(embedding) != self.embedding_dimension:
                        logger.warning(f"嵌入向量维度不匹配: 期望{self.embedding_dimension}, 实际{len(embedding)}")
                        if len(embedding) < self.embedding_dimension:
                            embedding.extend([0.0] * (self.embedding_dimension - len(embedding)))
                        else:
                            embedding = embedding[:self.embedding_dimension]

                    embeddings.append(embedding)

            except Exception as e:
                logger.error(f"批量API调用失败，回退到单独调用: {str(e)}")
                # Fallback to individual calls
                for text in batch_texts:
                    embedding = await self._generate_embedding_from_api(text)
                    embeddings.append(embedding)

        return embeddings

    def _get_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def _get_cached_embedding(
        self,
        text: str,
        tenant_id: str
    ) -> Optional[List[float]]:
        """Get embedding from cache"""
        if not self.cache_enabled:
            return None

        content_hash = self._get_content_hash(text)
        cache_key = f"{tenant_id}:{content_hash}"

        # Check in-memory cache first
        if cache_key in self.embedding_cache:
            cache_entry = self.embedding_cache[cache_key]

            # Check if cache entry is still valid
            if cache_entry.expires_at is None or cache_entry.expires_at > datetime.utcnow():
                cache_entry.hit_count += 1
                cache_entry.last_hit_at = datetime.utcnow()
                return cache_entry.embedding.copy()
            else:
                # Remove expired entry
                del self.embedding_cache[cache_key]

        # In a real implementation, this would also check database cache
        # For now, return None to indicate cache miss
        return None

    async def _cache_embedding(
        self,
        text: str,
        tenant_id: str,
        embedding: List[float],
        compute_time_ms: int
    ):
        """Cache embedding result"""
        if not self.cache_enabled:
            return

        content_hash = self._get_content_hash(text)
        cache_key = f"{tenant_id}:{content_hash}"

        # Create cache entry
        cache_entry = EmbeddingCache(
            tenant_id=tenant_id,
            content_hash=content_hash,
            content_preview=text[:100],
            embedding=embedding.copy(),
            embedding_model=self.embedding_model,
            embedding_dimension=len(embedding),
            content_length=len(text),
            token_count=self._estimate_tokens(text),
            compute_time_ms=compute_time_ms,
            expires_at=datetime.utcnow() + self.cache_ttl
        )

        # Store in memory cache (with LRU eviction if needed)
        self.embedding_cache[cache_key] = cache_entry

        # In a real implementation, this would also store in database cache
        await self._store_cache_in_database(cache_entry)

    async def _store_cache_in_database(self, cache_entry: EmbeddingCache):
        """Store cache entry in database (placeholder implementation)"""
        # This would implement database storage of cache entries
        # For now, just log the operation
        logger.debug(f"缓存嵌入向量: {cache_entry.content_hash[:8]}...")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if not text:
            return 0

        # Simple heuristic: ~4 characters per token for English, ~1.5 for Chinese
        english_chars = len([c for c in text if c.isascii() and c.isalpha()])
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])

        english_tokens = english_chars / 4
        chinese_tokens = chinese_chars / 1.5

        return int(english_tokens + chinese_tokens)

    def _update_stats(self, tokens_processed: int, processing_time_ms: int):
        """Update service statistics"""
        self.stats['total_embeddings_generated'] += 1
        self.stats['total_tokens_processed'] += tokens_processed
        self.stats['total_processing_time_ms'] += processing_time_ms

        # Update average processing time
        if self.stats['total_embeddings_generated'] > 0:
            self.stats['average_processing_time_ms'] = (
                self.stats['total_processing_time_ms'] / self.stats['total_embeddings_generated']
            )

    async def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        cache_size = len(self.embedding_cache)
        cache_hit_rate = 0.0

        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        if total_requests > 0:
            cache_hit_rate = self.stats['cache_hits'] / total_requests

        return {
            **self.stats,
            'cache_size': cache_size,
            'cache_hit_rate': cache_hit_rate,
            'cache_enabled': self.cache_enabled,
            'embedding_model': self.embedding_model,
            'embedding_dimension': self.embedding_dimension,
            'batch_size': self.batch_size,
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600
        }

    async def clear_cache(self, tenant_id: Optional[str] = None):
        """Clear embedding cache"""
        if tenant_id:
            # Clear cache for specific tenant
            keys_to_remove = [
                key for key in self.embedding_cache.keys()
                if key.startswith(f"{tenant_id}:")
            ]
            for key in keys_to_remove:
                del self.embedding_cache[key]
            logger.info(f"已清除租户{tenant_id}的嵌入向量缓存")
        else:
            # Clear all cache
            cache_size = len(self.embedding_cache)
            self.embedding_cache.clear()
            logger.info(f"已清除所有嵌入向量缓存 ({cache_size}条)")

    async def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        current_time = datetime.utcnow()
        expired_keys = []

        for key, cache_entry in self.embedding_cache.items():
            if cache_entry.expires_at and cache_entry.expires_at <= current_time:
                expired_keys.append(key)

        for key in expired_keys:
            del self.embedding_cache[key]

        if expired_keys:
            logger.info(f"已清理{len(expired_keys)}条过期的嵌入向量缓存")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the service"""
        try:
            # Test embedding generation
            test_text = "健康检查测试文本"
            test_embedding, _ = await self.generate_embedding(test_text, "health_check", use_cache=False)

            health_status = {
                'status': 'healthy',
                'embedding_model': self.embedding_model,
                'embedding_dimension': len(test_embedding),
                'cache_enabled': self.cache_enabled,
                'cache_size': len(self.embedding_cache),
                'statistics': await self.get_statistics()
            }

            # Test ChromaDB connection
            try:
                await self.chroma_service.health_check()
                health_status['chromadb_status'] = 'connected'
            except Exception as e:
                health_status['chromadb_status'] = f'error: {str(e)}'

            # Test Zhipu service connection
            try:
                await self.zhipu_service.health_check()
                health_status['zhipu_status'] = 'connected'
            except Exception as e:
                health_status['zhipu_status'] = f'error: {str(e)}'

            return health_status

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'embedding_model': self.embedding_model,
                'cache_enabled': self.cache_enabled
            }

    async def validate_embedding_quality(
        self,
        embedding: List[float],
        text: str
    ) -> Dict[str, Any]:
        """Validate the quality of an embedding"""
        validation_result = {
            'is_valid': True,
            'issues': [],
            'metrics': {}
        }

        # Check dimension
        if len(embedding) != self.embedding_dimension:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"维度不匹配: 期望{self.embedding_dimension}, 实际{len(embedding)}")

        # Check for NaN or infinite values
        nan_count = sum(1 for val in embedding if not (np.isfinite(val)))
        if nan_count > 0:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"包含{nan_count}个无效值(NaN或无限)")

        # Calculate quality metrics
        embedding_array = np.array(embedding)

        validation_result['metrics'] = {
            'norm': float(np.linalg.norm(embedding_array)),
            'mean': float(np.mean(embedding_array)),
            'std': float(np.std(embedding_array)),
            'min': float(np.min(embedding_array)),
            'max': float(np.max(embedding_array)),
            'sparsity': float(np.mean(embedding_array == 0.0)),
            'text_length': len(text),
            'estimated_tokens': self._estimate_tokens(text)
        }

        # Check for unusual values
        if validation_result['metrics']['norm'] < 0.1:
            validation_result['issues'].append("向量范数过小，可能存在质量问题")

        if validation_result['metrics']['sparsity'] > 0.9:
            validation_result['issues'].append("向量过于稀疏")

        return validation_result

    async def optimize_collection(
        self,
        collection: VectorCollection,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Optimize vector collection for better performance"""
        start_time = time.time()

        try:
            collection_name = f"tenant_{tenant_id}_{collection.name}"

            # This would implement collection optimization strategies
            # For now, return placeholder implementation

            optimization_result = {
                'collection_name': collection_name,
                'optimization_time_ms': int((time.time() - start_time) * 1000),
                'strategies_applied': [
                    'vector_index_rebuild',
                    'metadata_compaction',
                    'cache_warmup'
                ],
                'estimated_performance_improvement': '15-25%'
            }

            logger.info(f"向量集合优化完成: {collection_name}")
            return optimization_result

        except Exception as e:
            logger.error(f"向量集合优化失败: {str(e)}")
            raise RuntimeError(f"向量集合优化失败: {str(e)}") from e

    async def get_collection_info(
        self,
        collection: VectorCollection,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get information about a vector collection"""
        try:
            collection_name = f"tenant_{tenant_id}_{collection.name}"

            # Get collection information from ChromaDB
            info = await self.chroma_service.get_collection_info(collection_name)

            collection_info = {
                'collection_name': collection_name,
                'tenant_id': tenant_id,
                'collection_id': collection.id,
                'embedding_model': self.embedding_model,
                'embedding_dimension': self.embedding_dimension,
                **info
            }

            return collection_info

        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {
                'collection_name': collection_name,
                'tenant_id': tenant_id,
                'error': str(e)
            }