"""
ChromaDB 客户端配置
向量数据库连接、集合操作
"""

from typing import List, Dict, Any, Optional
import logging

from src.app.core.config import settings

logger = logging.getLogger(__name__)

# 可选导入chromadb,避免依赖问题导致整个应用无法启动
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ChromaDB未安装或导入失败: {e}. 向量数据库功能将不可用")
    chromadb = None
    ChromaSettings = None
    embedding_functions = None
    CHROMADB_AVAILABLE = False


class ChromaDBService:
    """
    ChromaDB 向量数据库服务类
    """

    def __init__(self):
        # 延迟初始化客户端，避免启动时连接失败
        self._client = None
        if CHROMADB_AVAILABLE and embedding_functions:
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        else:
            self.embedding_function = None

    @property
    def client(self):
        """延迟初始化ChromaDB客户端"""
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("ChromaDB未安装,无法使用向量数据库功能")
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port
            )
        return self._client

    def check_connection(self) -> bool:
        """
        检查ChromaDB连接状态
        """
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB未安装,跳过连接检查")
            return False
        try:
            # 尝试获取heartbeat来验证连接
            heartbeat = self.client.heartbeat()
            if heartbeat:
                logger.info("ChromaDB connection: OK")
                return True
            else:
                logger.error("ChromaDB connection failed: No heartbeat")
                return False
        except Exception as e:
            logger.error(f"ChromaDB connection failed: {e}")
            return False

    def create_collection(self, collection_name: str, tenant_id: Optional[str] = None) -> bool:
        """
        创建新的向量集合
        """
        try:
            # 为多租户环境，使用tenant_id作为集合名的一部分
            full_collection_name = f"{collection_name}_{tenant_id}" if tenant_id else collection_name

            # 检查集合是否已存在
            try:
                self.client.get_collection(name=full_collection_name)
                logger.info(f"Collection '{full_collection_name}' already exists")
                return True
            except Exception:
                # 集合不存在，创建新集合
                pass

            collection = self.client.create_collection(
                name=full_collection_name,
                embedding_function=self.embedding_function,
                metadata={"tenant_id": tenant_id} if tenant_id else {}
            )

            logger.info(f"Collection '{full_collection_name}' created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            return False

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        向集合添加文档
        """
        try:
            full_collection_name = f"{collection_name}_{tenant_id}" if tenant_id else collection_name

            collection = self.client.get_collection(name=full_collection_name)

            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(documents)} documents to collection '{full_collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to add documents to collection '{collection_name}': {e}")
            return False

    def query_documents(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        在集合中查询文档
        """
        try:
            full_collection_name = f"{collection_name}_{tenant_id}" if tenant_id else collection_name

            collection = self.client.get_collection(name=full_collection_name)

            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where
            )

            logger.info(f"Query executed on collection '{full_collection_name}', found {len(results['ids'][0])} results")
            return results
        except Exception as e:
            logger.error(f"Failed to query collection '{collection_name}': {e}")
            return None

    def delete_documents(
        self,
        collection_name: str,
        ids: List[str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        从集合中删除文档
        """
        try:
            full_collection_name = f"{collection_name}_{tenant_id}" if tenant_id else collection_name

            collection = self.client.get_collection(name=full_collection_name)

            collection.delete(ids=ids)

            logger.info(f"Deleted {len(ids)} documents from collection '{full_collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from collection '{collection_name}': {e}")
            return False

    def get_collection_info(self, collection_name: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取集合信息
        """
        try:
            full_collection_name = f"{collection_name}_{tenant_id}" if tenant_id else collection_name

            collection = self.client.get_collection(name=full_collection_name)

            # 获取集合统计信息
            count = collection.count()

            info = {
                "name": full_collection_name,
                "count": count,
                "metadata": collection.metadata
            }

            return info
        except Exception as e:
            logger.error(f"Failed to get info for collection '{collection_name}': {e}")
            return None

    def list_collections(self) -> List[str]:
        """
        列出所有集合
        """
        try:
            collections = self.client.list_collections()
            return [collection.name for collection in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []


# 全局ChromaDB服务实例
chromadb_service = ChromaDBService()