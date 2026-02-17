# -*- coding: utf-8 -*-
"""
实体链接服务 - 基于向量检索的智能实体匹配

这个模块提供基于向量相似度的实体链接功能，解决模糊匹配问题：
- 产品名模糊匹配: "P40" → "Huawei P40 Pro"
- 城市别名扩展: "魔都" → "上海" (与业务术语表协同)
- 业务指标缩写: "GMV" → "Gross Merchandise Volume"
- 层级实体匹配: "iPhone" → "Apple iPhone 15 Pro Max"

核心优势：
1. 基于语义相似度，而非简单的字符串匹配
2. 支持多语言（中英文混合）
3. 可扩展的实体类型
4. 与 ChromaDB 集成，支持大规模实体库

作者: Data Agent Team
版本: 2.0.0
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

class EntityType(Enum):
    """实体类型枚举"""
    PRODUCT = "product"           # 产品/商品
    CUSTOMER = "customer"         # 客户
    LOCATION = "location"         # 地理位置
    CATEGORY = "category"         # 分类
    METRIC = "metric"             # 业务指标
    DIMENSION = "dimension"       # 维度
    ORGANIZATION = "organization" # 组织
    PERSON = "person"             # 人员
    CUSTOM = "custom"             # 自定义


@dataclass
class Entity:
    """实体定义

    Attributes:
        id: 实体唯一标识
        name: 实体标准名称
        aliases: 别名列表
        entity_type: 实体类型
        description: 描述
        metadata: 额外的元数据
        embedding: 预计算的向量（可选）
        tenant_id: 租户ID（多租户隔离）
        created_at: 创建时间
    """
    id: str
    name: str
    entity_type: EntityType
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "aliases": self.aliases,
            "description": self.description,
            "metadata": self.metadata,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat()
        }

    def get_search_texts(self) -> List[str]:
        """获取用于搜索的文本列表"""
        texts = [self.name]
        texts.extend(self.aliases)
        if self.description:
            texts.append(self.description)
        return texts


@dataclass
class LinkingResult:
    """实体链接结果

    Attributes:
        query: 原始查询文本
        matched_entity: 匹配到的实体
        confidence: 匹配置信度 (0-1)
        match_type: 匹配类型 (exact/fuzzy/semantic)
        explanation: 匹配解释
    """
    query: str
    matched_entity: Optional[Entity]
    confidence: float
    match_type: str  # exact, fuzzy, semantic
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "matched_entity": self.matched_entity.to_dict() if self.matched_entity else None,
            "confidence": self.confidence,
            "match_type": self.match_type,
            "explanation": self.explanation
        }


# ============================================================================
# 向量嵌入服务接口
# ============================================================================

class EmbeddingService:
    """向量嵌入服务基类

    提供文本到向量的转换功能。支持多种后端：
    - SentenceTransformers (本地)
    - OpenAI Embeddings API
    - 智谱 AI Embeddings
    - DeepSeek Embeddings
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """初始化嵌入服务

        Args:
            model_name: 模型名称
        """
        self.model_name = model_name
        self._model = None

    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """将文本编码为向量

        Args:
            texts: 单个文本或文本列表

        Returns:
            向量或向量列表
        """
        raise NotImplementedError("子类必须实现 encode 方法")

    def encode_single(self, text: str) -> np.ndarray:
        """编码单个文本"""
        result = self.encode(text)
        if isinstance(result, list):
            return result[0]
        return result

    @lru_cache(maxsize=1000)
    def get_cached_embedding(self, text: str) -> np.ndarray:
        """获取缓存的嵌入向量"""
        return self.encode_single(text)


class SentenceTransformerEmbedding(EmbeddingService):
    """基于 SentenceTransformers 的本地嵌入服务"""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """初始化

        Args:
            model_name: SentenceTransformers 模型名称
                       推荐的多语言模型:
                       - paraphrase-multilingual-MiniLM-L12-v2 (快速, 多语言)
                       - distiluse-base-multilingual-cased-v2 (中等, 多语言)
                       - paraphrase-multilingual-mpnet-base-v2 (高精度, 多语言)
        """
        super().__init__(model_name)
        self._load_model()

    def _load_model(self):
        """延迟加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"加载嵌入模型: {self.model_name}")
        except ImportError:
            logger.warning("sentence_transformers 未安装，使用简单词频嵌入")
            self._model = None
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {e}")
            self._model = None

    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """编码文本"""
        if self._model is None:
            # 回退到简单词频嵌入
            return self._simple_encode(texts)

        if isinstance(texts, str):
            texts = [texts]

        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        if len(texts) == 1:
            return embeddings[0]
        return embeddings

    def _simple_encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """简单的词频编码（回退方案）"""
        if isinstance(texts, str):
            texts = [texts]

        def char_to_vector(text: str, dim: int = 384) -> np.ndarray:
            """字符级别的简单编码"""
            # 使用字符频率和位置信息
            vector = np.zeros(dim, dtype=np.float32)
            for i, char in enumerate(text[:dim]):
                # 简单的字符哈希
                idx = (ord(char) * (i + 1)) % dim
                vector[idx] += 1.0 / (i + 1)
            # 归一化
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector

        embeddings = [char_to_vector(text) for text in texts]

        if len(texts) == 1:
            return embeddings[0]
        return embeddings


# ============================================================================
# 实体存储后端
# ============================================================================

class EntityStore:
    """实体存储后端基类"""

    def add(self, entity: Entity) -> bool:
        """添加实体"""
        raise NotImplementedError

    def add_batch(self, entities: List[Entity]) -> int:
        """批量添加实体"""
        count = 0
        for entity in entities:
            if self.add(entity):
                count += 1
        return count

    def search(
        self,
        query: str,
        top_k: int = 5,
        entity_type: Optional[EntityType] = None,
        tenant_id: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Tuple[Entity, float]]:
        """搜索实体

        Returns:
            (实体, 相似度分数) 列表，按相似度降序排列
        """
        raise NotImplementedError

    def get(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        raise NotImplementedError

    def delete(self, entity_id: str) -> bool:
        """删除实体"""
        raise NotImplementedError

    def clear(self, tenant_id: Optional[str] = None):
        """清空存储"""
        raise NotImplementedError

    def count(self, tenant_id: Optional[str] = None) -> int:
        """统计实体数量"""
        raise NotImplementedError


class InMemoryEntityStore(EntityStore):
    """内存实体存储（用于测试和小规模场景）"""

    def __init__(self, embedding_service: EmbeddingService):
        """初始化

        Args:
            embedding_service: 向量嵌入服务
        """
        self.embedding_service = embedding_service
        self._entities: Dict[str, Entity] = {}
        self._embeddings: Dict[str, np.ndarray] = {}

    def add(self, entity: Entity) -> bool:
        """添加实体"""
        if entity.id in self._entities:
            return False

        self._entities[entity.id] = entity

        # 计算并缓存嵌入向量
        search_texts = " ".join(entity.get_search_texts())
        embedding = self.embedding_service.encode_single(search_texts)
        self._embeddings[entity.id] = embedding

        return True

    def search(
        self,
        query: str,
        top_k: int = 5,
        entity_type: Optional[EntityType] = None,
        tenant_id: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Tuple[Entity, float]]:
        """搜索实体"""
        if not self._entities:
            return []

        # 编码查询
        query_embedding = self.embedding_service.encode_single(query)

        # 计算相似度
        results = []
        for entity_id, entity in self._entities.items():
            # 过滤实体类型
            if entity_type and entity.entity_type != entity_type:
                continue
            # 过滤租户
            if tenant_id and entity.tenant_id != tenant_id:
                continue

            # 计算余弦相似度
            entity_embedding = self._embeddings.get(entity_id)
            if entity_embedding is not None:
                similarity = self._cosine_similarity(query_embedding, entity_embedding)
                if similarity >= min_score:
                    results.append((entity, similarity))

        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        return self._entities.get(entity_id)

    def delete(self, entity_id: str) -> bool:
        """删除实体"""
        if entity_id in self._entities:
            del self._entities[entity_id]
            self._embeddings.pop(entity_id, None)
            return True
        return False

    def clear(self, tenant_id: Optional[str] = None):
        """清空存储"""
        if tenant_id:
            to_delete = [
                eid for eid, entity in self._entities.items()
                if entity.tenant_id == tenant_id
            ]
            for eid in to_delete:
                self.delete(eid)
        else:
            self._entities.clear()
            self._embeddings.clear()

    def count(self, tenant_id: Optional[str] = None) -> int:
        """统计实体数量"""
        if tenant_id:
            return sum(
                1 for entity in self._entities.values()
                if entity.tenant_id == tenant_id
            )
        return len(self._entities)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))


class ChromaDBEntityStore(EntityStore):
    """基于 ChromaDB 的实体存储（生产环境推荐）"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        collection_name: str = "entity_linking",
        persist_directory: Optional[Path] = None
    ):
        """初始化

        Args:
            embedding_service: 向量嵌入服务
            collection_name: ChromaDB 集合名称
            persist_directory: 持久化目录
        """
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._client = None
        self._collection = None
        self._init_chromadb()

    def _init_chromadb(self):
        """初始化 ChromaDB"""
        try:
            import chromadb

            if self.persist_directory:
                self.persist_directory.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_directory)
                )
            else:
                self._client = chromadb.Client()

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            logger.info(f"ChromaDB 集合初始化完成: {self.collection_name}")

        except ImportError:
            logger.warning("chromadb 未安装，回退到内存存储")
            raise
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    def add(self, entity: Entity) -> bool:
        """添加实体"""
        # 准备搜索文本
        search_texts = " ".join(entity.get_search_texts())

        # 生成嵌入
        embedding = self.embedding_service.encode_single(search_texts)

        # 准备元数据
        metadata = {
            "name": entity.name,
            "entity_type": entity.entity_type.value,
            "description": entity.description or "",
            "aliases": json.dumps(entity.aliases, ensure_ascii=False),
            **entity.metadata
        }
        if entity.tenant_id:
            metadata["tenant_id"] = entity.tenant_id

        # 添加到 ChromaDB
        try:
            self._collection.add(
                ids=[entity.id],
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                documents=[search_texts]
            )
            return True
        except Exception as e:
            logger.error(f"添加实体失败: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        entity_type: Optional[EntityType] = None,
        tenant_id: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Tuple[Entity, float]]:
        """搜索实体"""
        # 编码查询
        query_embedding = self.embedding_service.encode_single(query)

        # 构建过滤条件
        where = {}
        if entity_type:
            where["entity_type"] = entity_type.value
        if tenant_id:
            where["tenant_id"] = tenant_id

        # 查询 ChromaDB
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k * 2,  # 获取更多结果以支持过滤
                where=where if where else None
            )

            if not results or not results["ids"][0]:
                return []

            # 转换结果
            entities_with_scores = []
            for i, entity_id in enumerate(results["ids"][0]):
                distance = 1 - results["distances"][0][i]  # 转换为相似度
                if distance < min_score:
                    continue

                metadata = results["metadatas"][0][i]
                entity = Entity(
                    id=entity_id,
                    name=metadata.get("name", ""),
                    entity_type=EntityType(metadata.get("entity_type", "custom")),
                    aliases=json.loads(metadata.get("aliases", "[]")),
                    description=metadata.get("description", ""),
                    metadata={k: v for k, v in metadata.items()
                             if k not in ["name", "entity_type", "description", "aliases", "tenant_id"]},
                    tenant_id=metadata.get("tenant_id")
                )
                entities_with_scores.append((entity, distance))

            # 按相似度排序
            entities_with_scores.sort(key=lambda x: x[1], reverse=True)
            return entities_with_scores[:top_k]

        except Exception as e:
            logger.error(f"搜索实体失败: {e}")
            return []

    def get(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        try:
            results = self._collection.get(ids=[entity_id])
            if not results or not results["ids"]:
                return None

            metadata = results["metadatas"][0]
            return Entity(
                id=entity_id,
                name=metadata.get("name", ""),
                entity_type=EntityType(metadata.get("entity_type", "custom")),
                aliases=json.loads(metadata.get("aliases", "[]")),
                description=metadata.get("description", ""),
                metadata={k: v for k, v in metadata.items()
                         if k not in ["name", "entity_type", "description", "aliases", "tenant_id"]},
                tenant_id=metadata.get("tenant_id")
            )
        except Exception as e:
            logger.error(f"获取实体失败: {e}")
            return None

    def delete(self, entity_id: str) -> bool:
        """删除实体"""
        try:
            self._collection.delete(ids=[entity_id])
            return True
        except Exception as e:
            logger.error(f"删除实体失败: {e}")
            return False

    def clear(self, tenant_id: Optional[str] = None):
        """清空存储"""
        try:
            if tenant_id:
                # 获取该租户的所有实体ID
                results = self._collection.get(where={"tenant_id": tenant_id})
                if results and results["ids"]:
                    self._collection.delete(ids=results["ids"])
            else:
                # 删除并重建集合
                self._client.delete_collection(self.collection_name)
                self._collection = self._client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
        except Exception as e:
            logger.error(f"清空存储失败: {e}")

    def count(self, tenant_id: Optional[str] = None) -> int:
        """统计实体数量"""
        try:
            if tenant_id:
                results = self._collection.get(where={"tenant_id": tenant_id})
                return len(results["ids"]) if results else 0
            else:
                return self._collection.count()
        except Exception as e:
            logger.error(f"统计实体数量失败: {e}")
            return 0


# ============================================================================
# 实体链接服务
# ============================================================================

class EntityLinkingService:
    """实体链接服务

    提供智能实体匹配功能：
    1. 精确匹配 - 名称或别名完全匹配
    2. 模糊匹配 - 基于编辑距离的相似度匹配
    3. 语义匹配 - 基于向量相似度的语义匹配
    """

    def __init__(
        self,
        entity_store: Optional[EntityStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        enable_exact_match: bool = True,
        enable_fuzzy_match: bool = True,
        enable_semantic_match: bool = True,
        fuzzy_threshold: float = 0.6,
        semantic_threshold: float = 0.5
    ):
        """初始化实体链接服务

        Args:
            entity_store: 实体存储后端
            embedding_service: 向量嵌入服务
            enable_exact_match: 是否启用精确匹配
            enable_fuzzy_match: 是否启用模糊匹配
            enable_semantic_match: 是否启用语义匹配
            fuzzy_threshold: 模糊匹配阈值
            semantic_threshold: 语义匹配阈值
        """
        # 初始化嵌入服务
        self.embedding_service = embedding_service or SentenceTransformerEmbedding()

        # 初始化存储后端
        if entity_store is None:
            try:
                entity_store = ChromaDBEntityStore(
                    embedding_service=self.embedding_service,
                    persist_directory=Path("./data/entity_linking")
                )
            except Exception:
                entity_store = InMemoryEntityStore(
                    embedding_service=self.embedding_service
                )

        self.entity_store = entity_store

        # 配置
        self.enable_exact_match = enable_exact_match
        self.enable_fuzzy_match = enable_fuzzy_match
        self.enable_semantic_match = enable_semantic_match
        self.fuzzy_threshold = fuzzy_threshold
        self.semantic_threshold = semantic_threshold

        # 加载内置实体
        self._load_builtin_entities()

    def _load_builtin_entities(self):
        """加载内置实体"""
        builtin_entities = self._get_builtin_entities()
        count = self.entity_store.add_batch(builtin_entities)
        logger.info(f"加载 {count} 个内置实体")

    def _get_builtin_entities(self) -> List[Entity]:
        """获取内置实体列表"""
        entities = []

        # 产品实体示例
        products = [
            {
                "id": "prod_huawei_p40_pro",
                "name": "Huawei P40 Pro",
                "aliases": ["P40 Pro", "P40", "华为P40", "华为 P40 Pro", "华为P40 Pro"],
                "description": "华为旗舰智能手机，搭载麒麟990 5G芯片",
                "metadata": {"brand": "Huawei", "category": "Smartphone"}
            },
            {
                "id": "prod_iphone_15_pro",
                "name": "Apple iPhone 15 Pro",
                "aliases": ["iPhone 15 Pro", "iPhone15 Pro", "苹果 15 Pro", "苹果15 Pro"],
                "description": "苹果旗舰智能手机，搭载A17 Pro芯片",
                "metadata": {"brand": "Apple", "category": "Smartphone"}
            },
            {
                "id": "prod_xiaomi_mi14",
                "name": "Xiaomi Mi 14",
                "aliases": ["小米14", "Mi 14", "小米Mi14", "小米 Mi 14"],
                "description": "小米旗舰智能手机，搭载骁龙8 Gen3芯片",
                "metadata": {"brand": "Xiaomi", "category": "Smartphone"}
            },
        ]

        for p in products:
            entities.append(Entity(
                id=p["id"],
                name=p["name"],
                entity_type=EntityType.PRODUCT,
                aliases=p["aliases"],
                description=p.get("description", ""),
                metadata=p.get("metadata", {})
            ))

        # 位置实体示例
        locations = [
            {
                "id": "loc_beijing",
                "name": "北京",
                "aliases": ["Beijing", "Peking", "首都", "帝都"],
                "description": "中国首都，直辖市",
                "metadata": {"level": "municipality", "region": "North China"}
            },
            {
                "id": "loc_shanghai",
                "name": "上海",
                "aliases": ["Shanghai", "申城", "魔都"],
                "description": "中国直辖市，经济中心",
                "metadata": {"level": "municipality", "region": "East China"}
            },
            {
                "id": "loc_shenzhen",
                "name": "深圳",
                "aliases": ["Shenzhen", "鹏城"],
                "description": "中国广东省副省级市，科技中心",
                "metadata": {"level": "city", "province": "Guangdong", "region": "South China"}
            },
        ]

        for loc in locations:
            entities.append(Entity(
                id=loc["id"],
                name=loc["name"],
                entity_type=EntityType.LOCATION,
                aliases=loc["aliases"],
                description=loc.get("description", ""),
                metadata=loc.get("metadata", {})
            ))

        # 业务指标实体
        metrics = [
            {
                "id": "metric_gmv",
                "name": "GMV",
                "aliases": ["Gross Merchandise Volume", "商品交易总额", "成交总额"],
                "description": "一定时间段内的成交商品金额总和",
                "metadata": {"category": "financial"}
            },
            {
                "id": "metric_arpu",
                "name": "ARPU",
                "aliases": ["Average Revenue Per User", "每用户平均收入"],
                "description": "平均每用户收入",
                "metadata": {"category": "financial"}
            },
        ]

        for m in metrics:
            entities.append(Entity(
                id=m["id"],
                name=m["name"],
                entity_type=EntityType.METRIC,
                aliases=m["aliases"],
                description=m.get("description", ""),
                metadata=m.get("metadata", {})
            ))

        return entities

    def link(
        self,
        query: str,
        entity_type: Optional[EntityType] = None,
        tenant_id: Optional[str] = None,
        top_k: int = 3
    ) -> List[LinkingResult]:
        """执行实体链接

        Args:
            query: 查询文本
            entity_type: 限制实体类型
            tenant_id: 租户ID
            top_k: 返回结果数量

        Returns:
            链接结果列表，按置信度降序排列
        """
        results = []

        # 1. 精确匹配
        if self.enable_exact_match:
            exact_results = self._exact_match(query, entity_type, tenant_id)
            results.extend(exact_results)

        # 2. 模糊匹配（如果精确匹配未找到足够结果）
        if self.enable_fuzzy_match and len(results) < top_k:
            fuzzy_results = self._fuzzy_match(
                query,
                entity_type,
                tenant_id,
                min_score=self.fuzzy_threshold
            )
            # 去重
            for fr in fuzzy_results:
                if not any(r.matched_entity.id == fr.matched_entity.id for r in results):
                    results.append(fr)

        # 3. 语义匹配（如果仍未找到足够结果）
        if self.enable_semantic_match and len(results) < top_k:
            semantic_results = self._semantic_match(
                query,
                entity_type,
                tenant_id,
                top_k=top_k,
                min_score=self.semantic_threshold
            )
            # 去重
            for sr in semantic_results:
                if not any(r.matched_entity.id == sr.matched_entity.id for r in results):
                    results.append(sr)

        # 按置信度排序并限制结果数量
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:top_k]

    def _exact_match(
        self,
        query: str,
        entity_type: Optional[EntityType],
        tenant_id: Optional[str]
    ) -> List[LinkingResult]:
        """精确匹配"""
        results = []

        # 这里需要遍历所有实体进行精确匹配
        # 对于大规模场景，应该建立名称索引
        # 简化实现：使用语义搜索获取候选，然后验证精确匹配

        search_results = self.entity_store.search(
            query,
            top_k=10,
            entity_type=entity_type,
            tenant_id=tenant_id,
            min_score=0.8  # 高相似度阈值作为候选
        )

        query_lower = query.lower().strip()

        for entity, similarity in search_results:
            # 检查名称精确匹配
            if entity.name.lower() == query_lower:
                results.append(LinkingResult(
                    query=query,
                    matched_entity=entity,
                    confidence=1.0,
                    match_type="exact",
                    explanation=f"名称完全匹配: {entity.name}"
                ))
                continue

            # 检查别名精确匹配
            for alias in entity.aliases:
                if alias.lower() == query_lower:
                    results.append(LinkingResult(
                        query=query,
                        matched_entity=entity,
                        confidence=0.95,
                        match_type="exact",
                        explanation=f"别名 '{alias}' 完全匹配: {entity.name}"
                    ))
                    break

        return results

    def _fuzzy_match(
        self,
        query: str,
        entity_type: Optional[EntityType],
        tenant_id: Optional[str],
        min_score: float
    ) -> List[LinkingResult]:
        """模糊匹配"""
        results = []

        # 获取候选实体
        search_results = self.entity_store.search(
            query,
            top_k=20,
            entity_type=entity_type,
            tenant_id=tenant_id,
            min_score=min_score
        )

        for entity, similarity in search_results:
            # 计算编辑距离相似度
            name_score = self._levenshtein_similarity(query, entity.name)
            max_alias_score = name_score
            best_alias = entity.name

            for alias in entity.aliases:
                alias_score = self._levenshtein_similarity(query, alias)
                if alias_score > max_alias_score:
                    max_alias_score = alias_score
                    best_alias = alias

            if max_alias_score >= min_score:
                # 综合语义相似度和编辑距离相似度
                combined_score = (similarity + max_alias_score) / 2
                results.append(LinkingResult(
                    query=query,
                    matched_entity=entity,
                    confidence=combined_score,
                    match_type="fuzzy",
                    explanation=f"模糊匹配: '{best_alias}' → {entity.name} "
                              f"(相似度: {combined_score:.2f})"
                ))

        return results

    def _semantic_match(
        self,
        query: str,
        entity_type: Optional[EntityType],
        tenant_id: Optional[str],
        top_k: int,
        min_score: float
    ) -> List[LinkingResult]:
        """语义匹配"""
        results = []

        search_results = self.entity_store.search(
            query,
            top_k=top_k,
            entity_type=entity_type,
            tenant_id=tenant_id,
            min_score=min_score
        )

        for entity, similarity in search_results:
            results.append(LinkingResult(
                query=query,
                matched_entity=entity,
                confidence=similarity,
                match_type="semantic",
                explanation=f"语义匹配: {entity.name} (相似度: {similarity:.2f})"
            ))

        return results

    @staticmethod
    def _levenshtein_similarity(s1: str, s2: str) -> float:
        """计算编辑距离相似度"""
        s1_lower = s1.lower()
        s2_lower = s2.lower()

        if s1_lower == s2_lower:
            return 1.0

        # 简化的编辑距离计算
        len1, len2 = len(s1_lower), len(s2_lower)
        max_len = max(len1, len2)

        if max_len == 0:
            return 0.0

        # 使用包含关系快速判断
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return min(len1, len2) / max_len

        # 动态规划计算编辑距离
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1_lower[i - 1] == s2_lower[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],
                        dp[i][j - 1],
                        dp[i - 1][j - 1]
                    )

        distance = dp[len1][len2]
        return 1.0 - (distance / max_len)

    def add_entity(self, entity: Entity) -> bool:
        """添加实体"""
        return self.entity_store.add(entity)

    def add_entities(self, entities: List[Entity]) -> int:
        """批量添加实体"""
        return self.entity_store.add_batch(entities)

    def add_entity_from_dict(self, entity_dict: Dict[str, Any]) -> bool:
        """从字典添加实体"""
        try:
            entity = Entity(
                id=entity_dict["id"],
                name=entity_dict["name"],
                entity_type=EntityType(entity_dict.get("entity_type", "custom")),
                aliases=entity_dict.get("aliases", []),
                description=entity_dict.get("description", ""),
                metadata=entity_dict.get("metadata", {}),
                tenant_id=entity_dict.get("tenant_id")
            )
            return self.add_entity(entity)
        except Exception as e:
            logger.error(f"从字典添加实体失败: {e}")
            return False

    def import_from_json(self, json_path: Union[str, Path], tenant_id: Optional[str] = None) -> int:
        """从 JSON 文件导入实体

        JSON 格式:
        {
            "entities": [
                {
                    "id": "unique_id",
                    "name": "Standard Name",
                    "entity_type": "product|location|...",
                    "aliases": ["alias1", "alias2"],
                    "description": "Description",
                    "metadata": {"key": "value"}
                }
            ]
        }
        """
        json_file = Path(json_path)
        if not json_file.exists():
            logger.warning(f"实体文件不存在: {json_path}")
            return 0

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            entities = []
            for entity_dict in data.get("entities", []):
                if tenant_id:
                    entity_dict["tenant_id"] = tenant_id
                entity = Entity(
                    id=entity_dict["id"],
                    name=entity_dict["name"],
                    entity_type=EntityType(entity_dict.get("entity_type", "custom")),
                    aliases=entity_dict.get("aliases", []),
                    description=entity_dict.get("description", ""),
                    metadata=entity_dict.get("metadata", {}),
                    tenant_id=entity_dict.get("tenant_id")
                )
                entities.append(entity)

            return self.add_entities(entities)

        except Exception as e:
            logger.error(f"导入实体失败: {e}")
            return 0


# ============================================================================
# 中间件集成
# ============================================================================

class EntityLinkingMiddleware:
    """实体链接中间件

    在 Agent 执行前拦截查询，进行实体链接，
    并将链接结果注入到 Agent 上下文中。
    """

    def __init__(
        self,
        linking_service: Optional[EntityLinkingService] = None,
        enable_auto_link: bool = True,
        injection_mode: str = "prompt"  # prompt, context, both
    ):
        """初始化

        Args:
            linking_service: 实体链接服务
            enable_auto_link: 是否启用自动链接
            injection_mode: 注入模式
                - prompt: 注入到系统提示词
                - context: 注入到用户上下文
                - both: 同时注入
        """
        self.linking_service = linking_service or EntityLinkingService()
        self.enable_auto_link = enable_auto_link
        self.injection_mode = injection_mode

    def before_agent_execution(
        self,
        agent_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """在 Agent 执行前处理

        Args:
            agent_input: Agent 输入

        Returns:
            增强后的 Agent 输入
        """
        if not self.enable_auto_link:
            return agent_input

        query = agent_input.get("query", "")
        if not query:
            return agent_input

        tenant_id = agent_input.get("tenant_id")

        # 执行实体链接
        linking_results = self.linking_service.link(query, tenant_id=tenant_id)

        if not linking_results:
            return agent_input

        # 生成链接文本
        injection_text = self._generate_injection_text(linking_results)

        # 注入到 Agent 输入
        if self.injection_mode in ("prompt", "both"):
            agent_input["__entity_linking_prompt__"] = injection_text

        if self.injection_mode in ("context", "both"):
            agent_input["__entity_linking_context__"] = {
                "linked_entities": [r.to_dict() for r in linking_results],
                "query": query
            }

        agent_input["__linked_entities__"] = linking_results

        return agent_input

    def _generate_injection_text(self, results: List[LinkingResult]) -> str:
        """生成注入文本"""
        if not results:
            return ""

        lines = [
            "## 实体链接结果",
            f"检测到 {len(results)} 个相关实体：",
            ""
        ]

        for i, result in enumerate(results, 1):
            entity = result.matched_entity
            lines.append(f"{i}. **{entity.name}** (置信度: {result.confidence:.1%})")
            if entity.description:
                lines.append(f"   - 描述: {entity.description}")
            if entity.aliases:
                lines.append(f"   - 别名: {', '.join(entity.aliases[:5])}")
            if entity.metadata:
                lines.append(f"   - 元数据: {json.dumps(entity.metadata, ensure_ascii=False)}")
            lines.append("")

        return "\n".join(lines)

    def enhance_system_prompt(self, base_prompt: str, query: str, tenant_id: Optional[str] = None) -> str:
        """增强系统提示词"""
        if not self.enable_auto_link:
            return base_prompt

        linking_results = self.linking_service.link(query, tenant_id=tenant_id)

        if not linking_results:
            return base_prompt

        injection_text = self._generate_injection_text(linking_results)

        return f"""{base_prompt}

{injection_text}

💡 提示：用户查询中的实体可能指向上面的标准名称，请使用标准名称进行查询和展示。
"""


# ============================================================================
# 工具函数
# ============================================================================

def link_entities(
    query: str,
    entity_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
    top_k: int = 3
) -> str:
    """链接实体 - 供 LLM 调用

    Args:
        query: 查询文本
        entity_type: 限制实体类型
        tenant_id: 租户ID
        top_k: 返回结果数量

    Returns:
        JSON 格式的链接结果
    """
    service = EntityLinkingService()

    et = EntityType(entity_type) if entity_type else None
    results = service.link(query, entity_type=et, tenant_id=tenant_id, top_k=top_k)

    return json.dumps({
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results)
    }, ensure_ascii=False, indent=2)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import sys

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("实体链接服务测试")
    print("=" * 60)

    # 创建服务
    service = EntityLinkingService()

    # 测试查询
    test_queries = [
        "P40",
        "华为 P40 Pro",
        "魔都",
        "iPhone",
        "小米手机",
        "GMV 是多少",
    ]

    for query in test_queries:
        print(f"\n[测试] 查询: {query}")

        results = service.link(query, top_k=3)

        if results:
            print(f"  找到 {len(results)} 个匹配结果:")
            for i, result in enumerate(results, 1):
                entity = result.matched_entity
                print(f"    {i}. {entity.name}")
                print(f"       类型: {result.match_type}, 置信度: {result.confidence:.2f}")
                print(f"       说明: {result.explanation}")
        else:
            print("  未找到匹配结果")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
