# -*- coding: utf-8 -*-
"""
向量存储封装 - ChromaDB 向量存储

提供基于 ChromaDB 的向量存储封装，支持：
    - 租户隔离的集合命名
    - 文本添加和相似度搜索
    - 元数据过滤
    - 持久化存储

复用项目现有的 ChromaDB 配置（参考 entity_linking.py）

作者: Data Agent Team
版本: 1.0.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@dataclass
class VectorStoreConfig:
    """向量存储配置"""
    persist_directory: Path = field(default_factory=lambda: Path("./data/chroma_db"))
    collection_name: str = "default_collection"
    tenant_id: Optional[str] = None
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    distance_metric: str = "cosine"  # cosine, l2, ip


class ChromaVectorStore:
    """
    ChromaDB 向量存储封装

    提供：
    1. 租户隔离的集合命名（tenant_id + collection_name）
    2. 文本添加和批量操作
    3. 相似度搜索和混合检索
    4. 元数据过滤
    """

    # 类级别缓存：{(tenant_id, collection_name): ChromaVectorStore}
    _instances: Dict[tuple, 'ChromaVectorStore'] = {}
    _client = None  # 共享的 ChromaDB 客户端

    def __init__(
        self,
        tenant_id: str,
        collection_name: str,
        persist_directory: Optional[Path] = None,
        embedding_service=None
    ):
        """初始化向量存储

        Args:
            tenant_id: 租户 ID
            collection_name: 集合名称
            persist_directory: 持久化目录
            embedding_service: 向量嵌入服务（可选，使用默认服务）
        """
        self.tenant_id = tenant_id
        self.collection_name = self._get_tenant_aware_collection_name(tenant_id, collection_name)
        self.persist_directory = persist_directory or Path("./data/chroma_db")
        self._embedding_service = embedding_service
        self._collection = None

        # 初始化 ChromaDB 客户端和集合
        self._init_chromadb()

    @staticmethod
    def _get_tenant_aware_collection_name(tenant_id: str, collection_name: str) -> str:
        """获取租户隔离的集合名称

        Args:
            tenant_id: 租户 ID
            collection_name: 原始集合名称

        Returns:
            租户隔离的集合名称
        """
        # 租户隔离命名: {tenant_id}__{collection_name}
        # 使用双下划线分隔以避免冲突
        return f"{tenant_id}__{collection_name}"

    def _init_chromadb(self):
        """初始化 ChromaDB 客户端和集合"""
        try:
            import chromadb

            # 使用类级别的共享客户端
            if ChromaVectorStore._client is None:
                # 确保持久化目录存在
                self.persist_directory.mkdir(parents=True, exist_ok=True)
                ChromaVectorStore._client = chromadb.PersistentClient(
                    path=str(self.persist_directory)
                )
                logger.info(f"ChromaDB 客户端初始化完成，持久化目录: {self.persist_directory}")

            # 获取或创建集合
            self._collection = ChromaVectorStore._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine", "tenant_id": self.tenant_id}
            )

            logger.info(f"ChromaDB 集合初始化完成: {self.collection_name}")

        except ImportError:
            logger.warning("chromadb 未安装")
            raise ImportError("请安装 chromadb: pip install chromadb")
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    def _get_embedding_service(self):
        """获取或创建嵌入服务"""
        if self._embedding_service is None:
            # 复用 entity_linking 模块的嵌入服务
            try:
                from ..entity_linking import SentenceTransformerEmbedding
                self._embedding_service = SentenceTransformerEmbedding()
            except ImportError:
                # 回退到简单实现
                logger.warning("无法导入 SentenceTransformerEmbedding，使用简单实现")
                self._embedding_service = self._create_simple_embedding_service()

        return self._embedding_service

    def _create_simple_embedding_service(self):
        """创建简单的嵌入服务（回退方案）"""
        class SimpleEmbeddingService:
            def encode_texts(self, texts: List[str]) -> List[List[float]]:
                """简单字符级编码"""
                embeddings = []
                for text in texts:
                    # 简单的字符哈希编码
                    vector = self._char_to_vector(text, dim=384)
                    embeddings.append(vector.tolist())
                return embeddings

            def _char_to_vector(self, text: str, dim: int = 384):
                import numpy as np
                vector = np.zeros(dim, dtype=np.float32)
                for i, char in enumerate(text[:dim]):
                    idx = (ord(char) * (i + 1)) % dim
                    vector[idx] += 1.0 / (i + 1)
                # 归一化
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
                return vector

        return SimpleEmbeddingService()

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """添加文本到向量存储

        Args:
            texts: 文本列表
            metadatas: 元数据列表
            ids: 可选的 ID 列表

        Returns:
            添加的文档 ID 列表
        """
        if not texts:
            return []

        # 生成嵌入向量
        embedding_service = self._get_embedding_service()
        embeddings = embedding_service.encode_texts(texts)

        # 生成 ID（如果未提供）
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in texts]

        # 准备元数据
        if metadatas is None:
            metadatas = [{} for _ in texts]

        # 添加租户 ID 和时间戳
        for metadata in metadatas:
            metadata["tenant_id"] = self.tenant_id
            metadata["created_at"] = datetime.now().isoformat()

        # 添加到 ChromaDB
        try:
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"添加 {len(texts)} 个文档到集合 {self.collection_name}")
            return ids

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return []

    async def add_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """添加单个文本

        Args:
            text: 文本内容
            metadata: 元数据
            doc_id: 可选的文档 ID

        Returns:
            文档 ID
        """
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        await self.add_texts([text], [metadata or {}], [doc_id])
        return doc_id

    async def similarity_search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[Document]:
        """相似度搜索

        Args:
            query: 查询文本
            n_results: 返回结果数量
            where: 元数据过滤条件
            min_score: 最小相似度分数

        Returns:
            匹配的文档列表
        """
        # 生成查询向量
        embedding_service = self._get_embedding_service()
        query_embedding = embedding_service.encode_texts([query])[0]

        # 构建过滤条件（自动添加租户 ID）
        filter_where = {"tenant_id": self.tenant_id}
        if where:
            filter_where.update(where)

        # 查询 ChromaDB
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results * 2,  # 获取更多结果以支持过滤
                where=filter_where
            )

            if not results or not results["ids"][0]:
                return []

            # 转换为 Document 对象
            documents = []
            for i, doc_id in enumerate(results["ids"][0]):
                # ChromaDB 返回距离，需要转换为相似度
                # cosine 距离 = 1 - 相似度
                distance = results["distances"][0][i]
                similarity = 1 - distance

                if similarity < min_score:
                    continue

                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                metadata["similarity_score"] = similarity
                metadata["doc_id"] = doc_id

                doc = Document(
                    page_content=results["documents"][0][i] if results["documents"] else "",
                    metadata=metadata
                )
                documents.append(doc)

            # 按相似度排序
            documents.sort(key=lambda d: d.metadata.get("similarity_score", 0), reverse=True)
            return documents[:n_results]

        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []

    async def similarity_search_with_score(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """相似度搜索（带分数）

        Args:
            query: 查询文本
            n_results: 返回结果数量
            where: 元数据过滤条件

        Returns:
            (Document, 相似度分数) 元组列表
        """
        docs = await self.similarity_search(query, n_results, where)
        return [(doc, doc.metadata.get("similarity_score", 0.0)) for doc in docs]

    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        """根据 ID 获取文档

        Args:
            doc_id: 文档 ID

        Returns:
            文档对象，不存在则返回 None
        """
        try:
            results = self._collection.get(ids=[doc_id])
            if not results or not results["ids"]:
                return None

            metadata = results["metadatas"][0] if results["metadatas"] else {}
            return Document(
                page_content=results["documents"][0] if results["documents"] else "",
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None

    async def delete(self, doc_ids: List[str]) -> bool:
        """删除文档

        Args:
            doc_ids: 文档 ID 列表

        Returns:
            是否成功
        """
        try:
            self._collection.delete(ids=doc_ids)
            logger.info(f"删除 {len(doc_ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    async def update(
        self,
        doc_ids: List[str],
        texts: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """更新文档

        Args:
            doc_ids: 文档 ID 列表
            texts: 新的文本内容（可选）
            metadatas: 新的元数据（可选）

        Returns:
            是否成功
        """
        try:
            update_kwargs = {"ids": doc_ids}

            if texts:
                # 重新生成嵌入
                embedding_service = self._get_embedding_service()
                embeddings = embedding_service.encode_texts(texts)
                update_kwargs["embeddings"] = embeddings
                update_kwargs["documents"] = texts

            if metadatas:
                # 确保租户 ID 和时间戳
                for metadata in metadatas:
                    metadata["tenant_id"] = self.tenant_id
                    metadata["updated_at"] = datetime.now().isoformat()
                update_kwargs["metadatas"] = metadatas

            self._collection.update(**update_kwargs)
            logger.info(f"更新 {len(doc_ids)} 个文档")
            return True

        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            return False

    def count(self) -> int:
        """统计文档数量

        Returns:
            文档总数
        """
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"统计文档数量失败: {e}")
            return 0

    def clear(self) -> bool:
        """清空集合

        Returns:
            是否成功
        """
        try:
            # 删除并重建集合
            ChromaVectorStore._client.delete_collection(self.collection_name)
            self._collection = ChromaVectorStore._client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine", "tenant_id": self.tenant_id}
            )
            logger.info(f"清空集合: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"清空集合失败: {e}")
            return False

    @classmethod
    def get_or_create_store(
        cls,
        tenant_id: str,
        collection_name: str,
        persist_directory: Optional[Path] = None
    ) -> 'ChromaVectorStore':
        """获取或创建向量存储（单例模式）

        Args:
            tenant_id: 租户 ID
            collection_name: 集合名称
            persist_directory: 持久化目录

        Returns:
            ChromaVectorStore 实例
        """
        cache_key = (tenant_id, collection_name)

        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls(
                tenant_id=tenant_id,
                collection_name=collection_name,
                persist_directory=persist_directory
            )

        return cls._instances[cache_key]

    @classmethod
    def clear_cache(cls):
        """清除所有缓存的实例"""
        cls._instances.clear()


# ============================================================================
# 便捷函数
# ============================================================================

def create_vector_store(
    tenant_id: str,
    collection_name: str,
    persist_directory: Optional[Path] = None
) -> ChromaVectorStore:
    """创建向量存储

    Args:
        tenant_id: 租户 ID
        collection_name: 集合名称
        persist_directory: 持久化目录

    Returns:
        ChromaVectorStore 实例
    """
    return ChromaVectorStore.get_or_create_store(
        tenant_id=tenant_id,
        collection_name=collection_name,
        persist_directory=persist_directory
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test_vector_store():
        print("=" * 60)
        print("向量存储测试")
        print("=" * 60)

        # 创建向量存储
        store = create_vector_store(
            tenant_id="test_tenant",
            collection_name="test_collection"
        )

        # 添加文本
        print("\n[测试] 添加文本")
        texts = [
            "销售数据分析需要关注订单表",
            "用户信息存储在用户表中",
            "产品信息包含产品名称、价格和库存"
        ]
        ids = await store.add_texts(texts)
        print(f"  添加了 {len(ids)} 个文档")

        # 相似度搜索
        print("\n[测试] 相似度搜索")
        query = "如何查询销售数据"
        results = await store.similarity_search(query, n_results=2)
        print(f"  查询: {query}")
        for i, doc in enumerate(results, 1):
            print(f"    {i}. {doc.page_content}")
            print(f"       相似度: {doc.metadata.get('similarity_score', 0):.2f}")

        # 统计文档数量
        print(f"\n[测试] 文档总数: {store.count()}")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    asyncio.run(test_vector_store())
