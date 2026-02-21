"""
# [CHROMADB_CLIENT] ChromaDB向量数据库客户端

## [HEADER]
**文件名**: chromadb_client.py
**职责**: 提供ChromaDB向量数据库连接、集合管理、文档增删改查和向量检索功能，支持多租户集合隔离和RAG功能开关
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - ChromaDB向量数据库服务

## [INPUT]
- **collection_name: str** - 集合名称
- **documents: List[str]** - 文档文本列表
- **metadatas: List[Dict[str, Any]]** - 文档元数据列表
- **ids: List[str]** - 文档唯一ID列表
- **query_texts: List[str]** - 查询文本列表
- **n_results: int** - 返回结果数量（默认10）
- **where: Optional[Dict[str, Any]]** - 元数据过滤条件
- **tenant_id: Optional[str]** - 租户ID（用于多租户集合隔离）

## [OUTPUT]
- **bool**: 操作成功/失败（create_collection, add_documents, delete_documents）
- **bool**: 连接状态（check_connection）
- **Optional[Dict[str, Any]]**: 查询结果（query_documents, get_collection_info）
  - ids: List[List[str]] - 文档ID列表
  - documents: List[List[str]] - 文档内容列表
  - metadatas: List[List[Dict]] - 元数据列表
  - distances: List[List[float]] - 距离列表
- **List[str]**: 集合名称列表（list_collections）

**上游依赖** (已读取源码):
- [./core/config.py](./core/config.py) - 配置管理（ChromaDB host、port、enable_rag开关）

**下游依赖** (需要反向索引分析):
- [document_service.py](./document_service.py) - 文档服务（调用向量化）
- [rag_service.py](./rag_service.py) - RAG服务（调用向量检索）
- [xai_service.py](./xai_service.py) - XAI服务（可能调用）

**调用方**:
- [document_service.py](./document_service.py) - 文档上传后向量化
- [../api/v1/endpoints/documents.py](../api/v1/endpoints/documents.py) - 文档API端点（间接）
- RAG检索流程

## [STATE]
- **延迟初始化**: _client属性在首次使用时初始化（避免启动时连接失败）
- **RAG功能开关**: 基于settings.enable_rag控制服务可用性
- **可选依赖**: chromadb导入失败时设置CHROMADB_AVAILABLE=False，不阻塞应用启动
- **多租户隔离**: 集合命名格式为"{collection_name}_{tenant_id}"
- **嵌入函数**: 使用DefaultEmbeddingFunction生成向量
- **全局实例**: chromadb_service单例供全局使用

## [SIDE-EFFECTS]
- **HTTP连接**: 连接ChromaDB服务（settings.chroma_host:chroma_port）
- **异常处理**:
  - RAG禁用时抛出RuntimeError
  - 连接失败时记录警告并返回False/None
  - 不阻塞应用启动（可选导入）
- **日志记录**: 详细记录集合操作、连接状态、错误信息
- **向量计算**: 自动计算文本嵌入向量（通过DefaultEmbeddingFunction）

## [POS]
**路径**: backend/src/app/services/chromadb_client.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 core.config
"""

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
        # 🔥 第一步修复：检查是否启用RAG
        if not getattr(settings, 'enable_rag', False):
            raise RuntimeError("RAG功能已禁用，无法使用ChromaDB")
            
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("ChromaDB未安装,无法使用向量数据库功能")
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port
                )
            except Exception as e:
                logger.warning(f"ChromaDB客户端初始化失败: {e}，RAG功能将不可用")
                raise RuntimeError(f"ChromaDB连接失败: {e}")
        return self._client

    def check_connection(self) -> bool:
        """
        检查ChromaDB连接状态
        """
        # 🔥 第一步修复：检查是否启用RAG
        if not getattr(settings, 'enable_rag', False):
            logger.debug("RAG功能已禁用，跳过ChromaDB连接检查")
            return False
            
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB未安装,跳过连接检查")
            return False
        try:
            # 🔥 第一步修复：直接尝试连接，失败时记录警告并返回False，不阻塞
            # 注意：如果ChromaDB服务不可用，这里可能会稍微延迟，但不会无限等待
            # 因为HttpClient通常有默认超时设置
            heartbeat = self.client.heartbeat()
            if heartbeat:
                logger.debug("ChromaDB connection: OK")
                return True
            else:
                logger.warning("ChromaDB connection failed: No heartbeat")
                return False
        except Exception as e:
            # 🔥 第一步修复：连接失败时记录警告并返回False，不抛出异常
            logger.warning(f"ChromaDB连接失败（服务可能不可用）: {e}，跳过连接检查")
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

            self.client.create_collection(
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
        # 🔥 第一步修复：检查是否启用RAG，如果未启用则直接返回空结果
        if not getattr(settings, 'enable_rag', False):
            logger.debug("RAG功能已禁用，返回空查询结果")
            return None
            
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
            # 🔥 第一步修复：连接失败时记录警告并返回None，不抛出异常
            logger.warning(f"ChromaDB查询失败（连接可能不可用）: {e}，返回空结果")
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
