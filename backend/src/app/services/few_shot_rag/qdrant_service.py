"""
Qdrant 向量数据库服务

负责：
1. 存储查询向量
2. 检索相似案例
3. 多租户隔离

使用 REST API 避免与 qdrant-client 的兼容性问题
"""

from typing import List, Dict, Any, Optional

# 使用 REST 客户端避免 httpx 兼容性问题
# 从父级服务目录导入
from ..qdrant_rest_client import QdrantRESTClient

from backend.src.app.core.config import settings


class QdrantService:
    """Qdrant 向量数据库服务（使用 REST API）"""

    def __init__(self):
        # 使用 REST 客户端，避免 httpx 兼容性问题
        self.rest_client = QdrantRESTClient()
        self.collection_prefix = settings.qdrant_collection_prefix or "dataagent"

    def _get_collection_name(self, tenant_id: str) -> str:
        """获取租户专用的集合名称"""
        return f"{self.collection_prefix}_{tenant_id}_queries"

    async def ensure_collection_exists(self, tenant_id: str, vector_size: int = 1536):
        """确保租户集合存在"""
        collection_name = self._get_collection_name(tenant_id)

        # 检查 collection 是否存在
        if not self.rest_client.collection_exists(collection_name):
            # 创建新 collection
            self.rest_client.create_collection(
                collection_name=collection_name,
                vector_size=vector_size,
                distance="Cosine"
            )
            print(f"创建 Qdrant 集合: {collection_name}")

    async def store_query(
        self,
        tenant_id: str,
        query_id: str,
        question: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ):
        """存储查询向量"""
        collection_name = self._get_collection_name(tenant_id)
        await self.ensure_collection_exists(tenant_id, len(embedding))

        # 创建点（使用字典格式适配 REST API）
        point = {
            "id": query_id,
            "vector": embedding,
            "payload": {
                "question": question,
                **metadata
            }
        }

        self.rest_client.upsert_points(
            collection_name=collection_name,
            points=[point]
        )

    async def find_similar_queries(
        self,
        tenant_id: str,
        question_embedding: List[float],
        top_k: int = 3,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """检索相似查询"""
        collection_name = self._get_collection_name(tenant_id)

        # 构建过滤条件（字典格式）
        filter_payload = None
        if filters:
            must_conditions = [
                {
                    "key": key,
                    "match": {"value": value}
                }
                for key, value in filters.items()
            ]
            filter_payload = {"must": must_conditions}

        # 执行搜索
        results = self.rest_client.search_points(
            collection_name=collection_name,
            query_vector=question_embedding,
            limit=top_k,
            score_threshold=score_threshold,
            filter_payload=filter_payload
        )

        # 格式化结果
        formatted_results = []
        for r in results:
            payload = r.get("payload", {})
            formatted_results.append({
                "question": payload.get("question"),
                "score": r.get("score"),
                "metadata": {k: v for k, v in payload.items() if k != "question"}
            })

        return formatted_results

    async def delete_query(self, tenant_id: str, query_id: str):
        """删除查询向量"""
        collection_name = self._get_collection_name(tenant_id)
        self.rest_client.delete_points(
            collection_name=collection_name,
            point_ids=[query_id]
        )

    async def get_collection_stats(self, tenant_id: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        collection_name = self._get_collection_name(tenant_id)

        try:
            # 尝试获取集合信息
            collections = self.rest_client.get_collections()
            collection_list = collections.get("result", {}).get("collections", [])

            # 查找目标 collection
            for coll in collection_list:
                if coll.get("name") == collection_name:
                    return {
                        "points_count": coll.get("points_count", 0),
                        "vectors_count": coll.get("vectors_count", 0),
                        "indexed_vectors_count": coll.get("indexed_vectors_count", 0)
                    }

            # Collection 不存在
            return {"points_count": 0, "vectors_count": 0, "indexed_vectors_count": 0}
        except Exception:
            return {"points_count": 0, "vectors_count": 0, "indexed_vectors_count": 0}
