"""
Qdrant 向量数据库服务

替代 ChromaDB，提供高性能的向量检索功能。
使用 REST API 避免与 qdrant-client 的兼容性问题。
支持：
- 向量存储和检索
- 少样本 RAG
- 相似查询检索
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

# 使用 REST 客户端避免 httpx 兼容性问题
from .qdrant_rest_client import QdrantRESTClient

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("警告: openai 未安装，请运行: pip install openai")

from ...core.config import settings


class QdrantService:
    """Qdrant 向量数据库服务（使用 REST API）"""

    def __init__(self):
        # 使用 REST 客户端，避免 httpx 兼容性问题
        self.rest_client = QdrantRESTClient()
        self.collection_prefix = settings.qdrant_collection_prefix or "dataagent"
        self.embedding_dimension = settings.embedding_dimension or 1536

    def _get_collection_name(self, tenant_id: str, collection_type: str = "queries") -> str:
        """
        获取租户专属的 collection 名称

        Args:
            tenant_id: 租户ID
            collection_type: collection 类型 (queries, documents, etc.)
        """
        return f"{self.collection_prefix}_{tenant_id}_{collection_type}"

    async def ensure_collection_exists(
        self,
        tenant_id: str,
        collection_type: str = "queries",
        vector_size: Optional[int] = None
    ):
        """
        确保租户的 collection 存在

        Args:
            tenant_id: 租户ID
            collection_type: collection 类型
            vector_size: 向量维度，默认使用配置中的维度
        """
        collection_name = self._get_collection_name(tenant_id, collection_type)

        # 检查 collection 是否存在
        if not self.rest_client.collection_exists(collection_name):
            # 创建新 collection
            self.rest_client.create_collection(
                collection_name=collection_name,
                vector_size=vector_size or self.embedding_dimension,
                distance="Cosine"
            )
            print(f"[OK] 创建 Qdrant collection: {collection_name}")

    async def store_successful_query(
        self,
        tenant_id: str,
        original_question: str,
        dsl_json: Dict[str, Any],
        cube_name: str,
        execution_time_ms: int = 0,
        row_count: int = 0,
        user_rating: Optional[int] = None,
        rewritten_question: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ):
        """
        存储成功查询到向量库（用于少样本 RAG）

        Args:
            tenant_id: 租户ID
            original_question: 原始问题
            dsl_json: 生成的 DSL
            cube_name: 使用的 Cube 名称
            execution_time_ms: 执行时间（毫秒）
            row_count: 返回行数
            user_rating: 用户评分 (1-5)
            rewritten_question: 重写后的问题 (可选)
            embedding: 问题向量 (可选，如果不提供则生成)
        """
        await self.ensure_collection_exists(tenant_id, "queries")

        collection_name = self._get_collection_name(tenant_id, "queries")

        # 如果没有提供 embedding，生成一个
        if not embedding:
            embedding = await self._generate_embedding(original_question)

        # 创建点（使用字典格式适配 REST API）
        point = {
            "id": self._generate_point_id(original_question, tenant_id),
            "vector": embedding,
            "payload": {
                "original_question": original_question,
                "rewritten_question": rewritten_question,
                "dsl_json": dsl_json,
                "cube_name": cube_name,
                "execution_time_ms": execution_time_ms,
                "row_count": row_count,
                "user_rating": user_rating,
                "created_at": datetime.now().isoformat()
            }
        }

        self.rest_client.upsert_points(
            collection_name=collection_name,
            points=[point]
        )

    async def find_similar_queries(
        self,
        tenant_id: str,
        question: str,
        top_k: int = 3,
        min_rating: Optional[int] = None,
        score_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        检索相似的历史成功查询（用于少样本 RAG）

        Args:
            tenant_id: 租户ID
            question: 当前问题
            top_k: 返回前 K 个结果
            min_rating: 最低评分过滤
            score_threshold: 相似度阈值

        Returns:
            相似查询列表
        """
        await self.ensure_collection_exists(tenant_id, "queries")

        collection_name = self._get_collection_name(tenant_id, "queries")

        # 生成查询向量
        query_vector = await self._generate_embedding(question)

        # 构建过滤条件
        query_filter = None

        if min_rating is not None:
            # 只返回评分大于等于 min_rating 的结果
            query_filter = {
                "must": [
                    {
                        "key": "user_rating",
                        "range": {
                            "gte": min_rating
                        }
                    }
                ]
            }

        # 搜索
        search_result = self.rest_client.search_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )

        # 格式化结果
        results = []
        for hit in search_result:
            payload = hit.get("payload", {})
            results.append({
                "original_question": payload.get("original_question"),
                "rewritten_question": payload.get("rewritten_question"),
                "dsl_json": payload.get("dsl_json"),
                "cube_name": payload.get("cube_name"),
                "score": hit.get("score"),
                "execution_time_ms": payload.get("execution_time_ms"),
                "row_count": payload.get("row_count"),
                "user_rating": payload.get("user_rating"),
                "created_at": payload.get("created_at")
            })

        return results

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        生成文本向量

        Args:
            text: 输入文本

        Returns:
            向量列表
        """
        if not OPENAI_AVAILABLE:
            # 如果 OpenAI 不可用，返回零向量（占位）
            print("警告: OpenAI 未安装，返回零向量")
            return [0.0] * self.embedding_dimension

        try:
            from openai import AsyncOpenAI

            # 检查是否有 OpenAI API Key
            api_key = getattr(settings, 'openai_api_key', None)
            if not api_key:
                print("警告: 未配置 OPENAI_API_KEY，返回零向量")
                return [0.0] * self.embedding_dimension

            client = AsyncOpenAI(api_key=api_key)
            embedding_model = getattr(settings, 'embedding_model', 'text-embedding-3-small')

            response = await client.embeddings.create(
                model=embedding_model,
                input=text
            )

            return response.data[0].embedding

        except Exception as e:
            print(f"生成 embedding 失败: {e}，返回零向量")
            return [0.0] * self.embedding_dimension

    def _generate_point_id(self, text: str, tenant_id: str) -> str:
        """
        生成唯一的点 ID

        Args:
            text: 文本内容
            tenant_id: 租户ID

        Returns:
            唯一的点 ID (MD5 hash)
        """
        content = f"{tenant_id}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    async def delete_collection(self, tenant_id: str, collection_type: str = "queries"):
        """
        删除租户的指定 collection

        Args:
            tenant_id: 租户ID
            collection_type: collection 类型
        """
        collection_name = self._get_collection_name(tenant_id, collection_type)

        try:
            self.rest_client.delete_collection(collection_name)
            print(f"[OK] 删除 Qdrant collection: {collection_name}")
        except Exception as e:
            print(f"[ERROR] 删除 collection 失败: {e}")

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            True 如果服务可用
        """
        try:
            collections = self.rest_client.get_collections()
            return collections is not None
        except Exception:
            return False
