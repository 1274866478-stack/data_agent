"""
Qdrant REST API Client

使用 requests 库直接调用 Qdrant REST API
绕过 qdrant-client 的 httpx 兼容性问题
"""

import requests
from typing import List, Dict, Any, Optional
from backend.src.app.core.config import settings


class QdrantRESTClient:
    """Qdrant REST API 客户端"""

    def __init__(self):
        self.base_url = f"http://{settings.qdrant_host or 'localhost'}:{settings.qdrant_port or 6333}"
        self.timeout = 10

    def get_collections(self) -> Dict[str, Any]:
        """获取所有集合"""
        response = requests.get(f"{self.base_url}/collections", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1536,
        distance: str = "Cosine"
    ):
        """创建集合"""
        payload = {
            "vectors": {
                "size": vector_size,
                "distance": distance
            }
        }
        response = requests.put(
            f"{self.base_url}/collections/{collection_name}",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def delete_collection(self, collection_name: str):
        """删除集合"""
        response = requests.delete(
            f"{self.base_url}/collections/{collection_name}",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ):
        """插入或更新向量点"""
        payload = {"points": points}
        response = requests.put(
            f"{self.base_url}/collections/{collection_name}/points",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def search_points(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_payload: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        payload = {
            "vector": query_vector,
            "limit": limit
        }

        if score_threshold is not None:
            payload["score_threshold"] = score_threshold

        if filter_payload is not None:
            payload["filter"] = filter_payload

        response = requests.post(
            f"{self.base_url}/collections/{collection_name}/points/search",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("result", [])

    def get_point(
        self,
        collection_name: str,
        point_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取单个点"""
        response = requests.get(
            f"{self.base_url}/collections/{collection_name}/points/{point_id}",
            timeout=self.timeout
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        result = data.get("result", [])
        return result[0] if result else None

    def delete_points(
        self,
        collection_name: str,
        point_ids: List[str]
    ):
        """删除向量点"""
        payload = {"points": point_ids}
        response = requests.post(
            f"{self.base_url}/collections/{collection_name}/points/delete",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        try:
            collections = self.get_collections()
            collection_names = [c["name"] for c in collections["result"]["collections"]]
            return collection_name in collection_names
        except:
            return False


# 兼容层：提供与 QdrantClient 类似的接口
class QdrantClientCompat:
    """QdrantClient 兼容层"""

    class Collections:
        def __init__(self, client: QdrantRESTClient):
            self.client = client
            self.collections = []

        def update_list(self):
            """更新集合列表"""
            try:
                data = self.client.get_collections()
                self.collections = [
                    type('Collection', (), {'name': c['name']})()
                    for c in data['result']['collections']
                ]
            except:
                self.collections = []

    def __init__(self):
        self.rest_client = QdrantRESTClient()
        self._collections = self.Collections(self.rest_client)

    @property
    def collections(self):
        """兼容属性"""
        self._collections.update_list()
        return self._collections

    def get_collections(self):
        """兼容方法"""
        self._collections.update_list()
        return self._collections

    def create_collection(self, collection_name: str, vectors_config: Dict[str, Any]):
        """兼容方法"""
        size = vectors_config.get("size", 1536)
        distance = vectors_config.get("distance", "Cosine")
        self.rest_client.create_collection(collection_name, size, distance)

    def upsert(self, collection_name: str, points: List[Any]):
        """兼容方法"""
        # 转换 PointStruct 到字典格式
        points_data = []
        for point in points:
            points_data.append({
                "id": point.id,
                "vector": point.vector,
                "payload": point.payload
            })
        self.rest_client.upsert_points(collection_name, points_data)

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Any]:
        """兼容方法"""
        results = self.rest_client.search_points(
            collection_name, query_vector, limit, score_threshold
        )

        # 转换为兼容格式
        class SearchResult:
            def __init__(self, data):
                self.id = data.get('id')
                self.score = data.get('score')
                self.payload = data.get('payload', {})

        return [SearchResult(r) for r in results]
