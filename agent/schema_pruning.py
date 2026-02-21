# -*- coding: utf-8 -*-
"""
Schema Pruning 服务 - 基于向量相似度的智能 Schema 剪枝

这个模块提供基于语义相似度的 Schema 剪枝功能：
1. 将 measures 和 dimensions 向量化
2. 根据用户查询计算相似度
3. 只保留高相关的 schema 元素
4. 减少 LLM 上下文大小，提高响应质量

核心优势：
- 减少 Token 消耗：只传递相关的 schema
- 提高 LLM 理解：减少噪音干扰
- 加速响应时间：更小的上下文
- 支持大规模 schema：数百个指标也能高效处理

作者: Data Agent Team
版本: 2.0.0
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class SchemaElement:
    """Schema 元素基类

    Attributes:
        cube: 所属 Cube 名称
        name: 元素名称
        display_name: 显示名称
        description: 描述
        element_type: 元素类型 (measure/dimension)
        metadata: 额外的元数据
        embedding: 预计算的向量
        search_text: 用于搜索的文本
    """
    cube: str
    name: str
    display_name: str
    description: str
    element_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "cube": self.cube,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "element_type": self.element_type,
            "metadata": self.metadata
        }
        if include_embedding and self.embedding is not None:
            result["embedding"] = self.embedding.tolist()
        return result

    def get_search_text(self) -> str:
        """获取用于向量搜索的文本"""
        parts = [self.display_name, self.name]
        if self.description:
            parts.append(self.description)
        # 添加元数据中的关键词
        for key, value in self.metadata.items():
            if isinstance(value, str) and value:
                parts.append(value)
        return " ".join(parts)


@dataclass
class MeasureSchema(SchemaElement):
    """度量 Schema 定义"""
    aggregation_type: str = "sum"  # sum, count, avg, etc.
    sql_template: str = ""

    def __post_init__(self):
        self.element_type = "measure"


@dataclass
class DimensionSchema(SchemaElement):
    """维度 Schema 定义"""
    data_type: str = "string"  # string, time, number
    enumerations: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.element_type = "dimension"


@dataclass
class PruningResult:
    """剪枝结果

    Attributes:
        query: 原始查询
        selected_measures: 选中的度量
        selected_dimensions: 选中的维度
        selected_cubes: 选中的 Cube
        excluded_measures: 排除的度量
        excluded_dimensions: 排除的维度
        scores: 元素得分
        total_original: 原始元素总数
        total_selected: 选中元素数量
        reduction_rate: 削减比例
    """
    query: str
    selected_measures: List[MeasureSchema]
    selected_dimensions: List[DimensionSchema]
    selected_cubes: Set[str]
    excluded_measures: List[MeasureSchema]
    excluded_dimensions: List[DimensionSchema]
    scores: Dict[str, float]
    total_original: int
    total_selected: int
    reduction_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "selected_measures": [m.to_dict() for m in self.selected_measures],
            "selected_dimensions": [d.to_dict() for d in self.selected_dimensions],
            "selected_cubes": list(self.selected_cubes),
            "excluded_measures_count": len(self.excluded_measures),
            "excluded_dimensions_count": len(self.excluded_dimensions),
            "total_original": self.total_original,
            "total_selected": self.total_selected,
            "reduction_rate": f"{self.reduction_rate:.1%}"
        }


# ============================================================================
# Schema 加载器
# ============================================================================

class SchemaLoader:
    """Schema 加载器

    从 YAML 文件或 API 加载 schema 定义
    """

    def __init__(self, schema_dir: Optional[Path] = None):
        """初始化

        Args:
            schema_dir: Schema 目录路径
        """
        if schema_dir is None:
            self.schema_dir = Path(__file__).parent.parent.parent / "cube_schema"
        else:
            self.schema_dir = Path(schema_dir)

    def load_from_yaml(self) -> Tuple[List[MeasureSchema], List[DimensionSchema], Dict[str, str]]:
        """从 YAML 文件加载 Schema

        Returns:
            (度量列表, 维度列表, 表名映射字典)
            表名映射格式: {"Orders": "订单表", "Products": "产品表", ...}
        """
        measures: List[MeasureSchema] = []
        dimensions: List[DimensionSchema] = []
        table_mappings: Dict[str, str] = {}

        if not self.schema_dir.exists():
            logger.warning(f"Schema 目录不存在: {self.schema_dir}")
            return measures, dimensions, table_mappings

        for yaml_file in self.schema_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                if not data:
                    continue

                cube_name = data.get('cube', yaml_file.stem)

                # 🔥 新增：提取 Excel 工作表名映射
                excel_sheet = data.get('excel_sheet')
                if excel_sheet:
                    table_mappings[cube_name] = excel_sheet
                    logger.debug(f"表名映射: {cube_name} -> {excel_sheet}")

                # 加载度量
                for measure_data in data.get('measures', []):
                    measure = MeasureSchema(
                        cube=cube_name,
                        name=measure_data.get('name', ''),
                        display_name=measure_data.get('display_name', measure_data.get('name', '')),
                        description=measure_data.get('description', ''),
                        element_type='measure',
                        aggregation_type=measure_data.get('type', 'sum'),
                        sql_template=measure_data.get('sql', ''),
                        metadata=measure_data.get('metadata', {})
                    )
                    measures.append(measure)

                # 加载维度
                for dim_data in data.get('dimensions', []):
                    dimension = DimensionSchema(
                        cube=cube_name,
                        name=dim_data.get('name', ''),
                        display_name=dim_data.get('display_name', dim_data.get('name', '')),
                        description=dim_data.get('description', ''),
                        element_type='dimension',
                        data_type=dim_data.get('type', 'string'),
                        enumerations=dim_data.get('enumerations', []),
                        metadata=dim_data.get('metadata', {})
                    )
                    dimensions.append(dimension)

            except Exception as e:
                logger.warning(f"加载 {yaml_file} 失败: {e}")

        logger.info(f"加载了 {len(measures)} 个度量和 {len(dimensions)} 个维度，{len(table_mappings)} 个表名映射")
        return measures, dimensions, table_mappings

    def load_from_builtin(self) -> Tuple[List[MeasureSchema], List[DimensionSchema]]:
        """加载内置 Schema（作为回退方案）"""
        measures = [
            MeasureSchema(
                cube="Orders",
                name="total_revenue",
                display_name="订单总收入",
                description="所有订单的总金额，包含折扣、税费和运费",
                aggregation_type="sum",
                sql_template="SUM(total_amount)"
            ),
            MeasureSchema(
                cube="Orders",
                name="net_revenue",
                display_name="订单净收入",
                description="排除取消订单后的总收入",
                aggregation_type="sum",
                sql_template="SUM(CASE WHEN status != 'cancelled' THEN total_amount ELSE 0 END)"
            ),
            MeasureSchema(
                cube="Orders",
                name="order_count",
                display_name="订单数量",
                description="订单总数",
                aggregation_type="count",
                sql_template="COUNT(*)"
            ),
            MeasureSchema(
                cube="Orders",
                name="average_order_value",
                display_name="平均订单金额",
                description="每个订单的平均金额",
                aggregation_type="avg",
                sql_template="AVG(total_amount)"
            ),
            MeasureSchema(
                cube="Customers",
                name="customer_count",
                display_name="客户数量",
                description="去重后的客户总数",
                aggregation_type="count",
                sql_template="COUNT(DISTINCT customer_id)"
            ),
            MeasureSchema(
                cube="Products",
                name="product_count",
                display_name="商品数量",
                description="商品总数",
                aggregation_type="count",
                sql_template="COUNT(*)"
            ),
        ]

        dimensions = [
            DimensionSchema(
                cube="Orders",
                name="status",
                display_name="订单状态",
                description="订单的当前状态",
                data_type="string",
                enumerations=["pending", "processing", "completed", "cancelled", "refunded"]
            ),
            DimensionSchema(
                cube="Orders",
                name="created_at",
                display_name="创建时间",
                description="订单创建的时间戳，可用于时间分组分析",
                data_type="time"
            ),
            DimensionSchema(
                cube="Customers",
                name="city",
                display_name="城市",
                description="客户所在的城市",
                data_type="string"
            ),
            DimensionSchema(
                cube="Products",
                name="category",
                display_name="商品类别",
                description="商品所属的分类",
                data_type="string"
            ),
        ]

        return measures, dimensions


# ============================================================================
# 嵌入服务
# ============================================================================

class SimpleEmbeddingService:
    """简单的嵌入服务（不依赖外部模型）

    作为回退方案，提供基础的向量编码
    """

    def encode(self, texts: List[str]) -> np.ndarray:
        """编码文本列表"""
        embeddings = []
        for text in texts:
            embeddings.append(self._encode_single(text))
        return np.array(embeddings)

    def _encode_single(self, text: str, dim: int = 128) -> np.ndarray:
        """简单的字符级编码"""
        vector = np.zeros(dim, dtype=np.float32)

        # 字符级别特征
        for i, char in enumerate(text[:dim]):
            idx = (ord(char) * (i + 1) * 31) % dim
            vector[idx] += 1.0 / (i + 1)

        # 词元级别特征（简单按空格分割）
        words = text.lower().split()
        for word in words:
            word_hash = hash(word) % dim
            vector[word_hash] += 0.5

        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector


# ============================================================================
# Schema Pruning 服务
# ============================================================================

class SchemaPruningService:
    """Schema Pruning 服务

    根据用户查询智能剪枝 Schema，只保留相关的元素
    """

    def __init__(
        self,
        measures: Optional[List[MeasureSchema]] = None,
        dimensions: Optional[List[DimensionSchema]] = None,
        embedding_service=None,
        similarity_threshold: float = 0.3,
        max_measures: int = 10,
        max_dimensions: int = 10,
        enable_caching: bool = True
    ):
        """初始化

        Args:
            measures: 度量列表
            dimensions: 维度列表
            embedding_service: 嵌入服务
            similarity_threshold: 相似度阈值
            max_measures: 最多保留的度量数量
            max_dimensions: 最多保留的维度数量
            enable_caching: 是否启用缓存
        """
        # 加载 Schema
        loader = SchemaLoader()
        if measures is None:
            self.measures, _, _ = loader.load_from_yaml()
            if not self.measures:
                self.measures = loader.load_from_builtin()[0]
        else:
            self.measures = measures

        if dimensions is None:
            _, self.dimensions, _ = loader.load_from_yaml()
            if not self.dimensions:
                self.dimensions = loader.load_from_builtin()[1]
        else:
            self.dimensions = dimensions

        # 嵌入服务
        self.embedding_service = embedding_service or SimpleEmbeddingService()

        # 配置
        self.similarity_threshold = similarity_threshold
        self.max_measures = max_measures
        self.max_dimensions = max_dimensions
        self.enable_caching = enable_caching

        # 预计算嵌入
        self._precompute_embeddings()

    def _precompute_embeddings(self):
        """预计算所有元素的嵌入向量"""
        # 度量嵌入
        measure_texts = [m.get_search_text() for m in self.measures]
        if measure_texts:
            self._measure_embeddings = self.embedding_service.encode(measure_texts)
        else:
            self._measure_embeddings = np.array([])

        # 维度嵌入
        dimension_texts = [d.get_search_text() for d in self.dimensions]
        if dimension_texts:
            self._dimension_embeddings = self.embedding_service.encode(dimension_texts)
        else:
            self._dimension_embeddings = np.array([])

        logger.info(
            f"预计算嵌入完成: {len(self.measures)} 个度量, {len(self.dimensions)} 个维度"
        )

    def prune(
        self,
        query: str,
        include_cube: Optional[str] = None,
        force_measures: Optional[List[str]] = None,
        force_dimensions: Optional[List[str]] = None
    ) -> PruningResult:
        """执行 Schema 剪枝

        Args:
            query: 用户查询
            include_cube: 只包含指定 Cube 的元素
            force_measures: 强制包含的度量名称列表
            force_dimensions: 强制包含的维度名称列表

        Returns:
            剪枝结果
        """
        # 编码查询
        query_embedding = self.embedding_service.encode([query])[0]

        # 计算度量相似度
        measure_scores = self._compute_similarities(
            query_embedding,
            self._measure_embeddings,
            self.measures,
            include_cube
        )

        # 计算维度相似度
        dimension_scores = self._compute_similarities(
            query_embedding,
            self._dimension_embeddings,
            self.dimensions,
            include_cube
        )

        # 强制包含指定元素
        if force_measures:
            for i, m in enumerate(self.measures):
                if m.name in force_measures:
                    measure_scores[i] = 1.0

        if force_dimensions:
            for i, d in enumerate(self.dimensions):
                if d.name in force_dimensions:
                    dimension_scores[i] = 1.0

        # 选择高分元素
        selected_measures, excluded_measures = self._select_by_score(
            self.measures,
            measure_scores,
            self.max_measures
        )

        selected_dimensions, excluded_dimensions = self._select_by_score(
            self.dimensions,
            dimension_scores,
            self.max_dimensions
        )

        # 收集涉及的 Cube
        selected_cubes = set()
        for m in selected_measures:
            selected_cubes.add(m.cube)
        for d in selected_dimensions:
            selected_cubes.add(d.cube)

        # 计算得分字典
        scores = {}
        for i, m in enumerate(self.measures):
            scores[f"measure.{m.cube}.{m.name}"] = measure_scores[i]
        for i, d in enumerate(self.dimensions):
            scores[f"dimension.{d.cube}.{d.name}"] = dimension_scores[i]

        # 计算统计信息
        total_original = len(self.measures) + len(self.dimensions)
        total_selected = len(selected_measures) + len(selected_dimensions)
        reduction_rate = 1.0 - (total_selected / total_original) if total_original > 0 else 0

        return PruningResult(
            query=query,
            selected_measures=selected_measures,
            selected_dimensions=selected_dimensions,
            selected_cubes=selected_cubes,
            excluded_measures=excluded_measures,
            excluded_dimensions=excluded_dimensions,
            scores=scores,
            total_original=total_original,
            total_selected=total_selected,
            reduction_rate=reduction_rate
        )

    def _compute_similarities(
        self,
        query_embedding: np.ndarray,
        element_embeddings: np.ndarray,
        elements: List,
        include_cube: Optional[str]
    ) -> List[float]:
        """计算相似度分数"""
        if len(element_embeddings) == 0:
            return []

        # 计算余弦相似度
        similarities = []
        for i, (embedding, element) in enumerate(zip(element_embeddings, elements)):
            # 过滤 Cube
            if include_cube and element.cube != include_cube:
                similarities.append(0.0)
                continue

            # 余弦相似度
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append(similarity)

        return similarities

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def _select_by_score(
        self,
        elements: List,
        scores: List[float],
        max_count: int
    ) -> Tuple[List, List]:
        """根据分数选择元素

        Returns:
            (选中列表, 排除列表)
        """
        # 按分数排序
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        # 选择高分元素
        selected_indices = set()
        for idx, score in indexed_scores:
            if score >= self.similarity_threshold and len(selected_indices) < max_count:
                selected_indices.add(idx)
            if len(selected_indices) >= max_count:
                break

        selected = [elements[i] for i in selected_indices]
        excluded = [elements[i] for i in range(len(elements)) if i not in selected_indices]

        return selected, excluded

    def get_pruned_schema_dict(
        self,
        query: str,
        include_cube: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取剪枝后的 Schema 字典（用于注入 Prompt）

        Args:
            query: 用户查询
            include_cube: 只包含指定 Cube

        Returns:
            Schema 字典，可序列化为 JSON
        """
        result = self.prune(query, include_cube)

        # 按立方组织
        schema_dict = {
            "cubes": {}
        }

        for cube in result.selected_cubes:
            cube_measures = [m for m in result.selected_measures if m.cube == cube]
            cube_dimensions = [d for d in result.selected_dimensions if d.cube == cube]

            schema_dict["cubes"][cube] = {
                "measures": [m.to_dict() for m in cube_measures],
                "dimensions": [d.to_dict() for d in cube_dimensions]
            }

        schema_dict["summary"] = {
            "total_measures": len(result.selected_measures),
            "total_dimensions": len(result.selected_dimensions),
            "cubes_count": len(result.selected_cubes),
            "reduction_rate": result.reduction_rate
        }

        return schema_dict

    def get_pruned_prompt_text(
        self,
        query: str,
        include_cube: Optional[str] = None,
        format: str = "compact"
    ) -> str:
        """获取剪枝后的 Prompt 文本

        Args:
            query: 用户查询
            include_cube: 只包含指定 Cube
            format: 格式类型 (compact/detailed)

        Returns:
            可注入到 Prompt 的文本
        """
        result = self.prune(query, include_cube)

        lines = [
            "## 相关数据 Schema（已根据查询优化）",
            ""
        ]

        if format == "compact":
            # 紧凑格式
            for cube in sorted(result.selected_cubes):
                lines.append(f"### {cube}")
                measures = [m for m in result.selected_measures if m.cube == cube]
                dimensions = [d for d in result.selected_dimensions if d.cube == cube]

                if measures:
                    measure_list = ", ".join([m.display_name for m in measures])
                    lines.append(f"**度量**: {measure_list}")

                if dimensions:
                    dim_list = ", ".join([d.display_name for d in dimensions])
                    lines.append(f"**维度**: {dim_list}")

                lines.append("")
        else:
            # 详细格式
            for cube in sorted(result.selected_cubes):
                lines.append(f"### {cube}")
                lines.append("")

                measures = [m for m in result.selected_measures if m.cube == cube]
                if measures:
                    lines.append("**度量**:")
                    for m in measures:
                        lines.append(f"- {m.name} ({m.display_name}): {m.description}")
                    lines.append("")

                dimensions = [d for d in result.selected_dimensions if d.cube == cube]
                if dimensions:
                    lines.append("**维度**:")
                    for d in dimensions:
                        lines.append(f"- {d.name} ({d.display_name}): {d.description}")
                    lines.append("")

        lines.append(f"💡 已优化：仅显示与查询相关的 {result.total_selected} 个字段（共 {result.total_original} 个，减少 {result.reduction_rate:.0%}）")

        return "\n".join(lines)


# ============================================================================
# 中间件集成
# ============================================================================

class SchemaPruningMiddleware:
    """Schema Pruning 中间件

    在 Agent 执行前自动剪枝 Schema
    """

    def __init__(
        self,
        pruning_service: Optional[SchemaPruningService] = None,
        enable_auto_prune: bool = True,
        injection_mode: str = "context"  # prompt, context, both
    ):
        """初始化

        Args:
            pruning_service: 剪枝服务
            enable_auto_prune: 是否启用自动剪枝
            injection_mode: 注入模式
        """
        self.pruning_service = pruning_service or SchemaPruningService()
        self.enable_auto_prune = enable_auto_prune
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
        if not self.enable_auto_prune:
            return agent_input

        query = agent_input.get("query", "")
        if not query:
            return agent_input

        # 执行剪枝
        schema_dict = self.pruning_service.get_pruned_schema_dict(query)

        # 注入到 Agent 输入
        if self.injection_mode in ("prompt", "both"):
            prompt_text = self.pruning_service.get_pruned_prompt_text(query)
            agent_input["__pruned_schema_prompt__"] = prompt_text

        if self.injection_mode in ("context", "both"):
            agent_input["__pruned_schema_context__"] = schema_dict

        agent_input["__schema_pruning_summary__"] = schema_dict.get("summary", {})

        return agent_input

    def enhance_system_prompt(self, base_prompt: str, query: str) -> str:
        """增强系统提示词"""
        if not self.enable_auto_prune:
            return base_prompt

        pruned_text = self.pruning_service.get_pruned_prompt_text(query)

        return f"""{base_prompt}

{pruned_text}
"""


# ============================================================================
# 工具函数
# ============================================================================

def get_relevant_schema(query: str, max_results: int = 10) -> str:
    """获取与查询相关的 Schema - 供 LLM 调用

    Args:
        query: 用户查询
        max_results: 最大结果数量

    Returns:
        JSON 格式的相关 Schema
    """
    service = SchemaPruningService(
        max_measures=max_results,
        max_dimensions=max_results
    )

    result = service.get_pruned_schema_dict(query)

    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("Schema Pruning 服务测试")
    print("=" * 60)

    # 创建服务
    service = SchemaPruningService()

    print(f"\n[初始化] 加载了 {len(service.measures)} 个度量, {len(service.dimensions)} 个维度")

    # 测试查询
    test_queries = [
        "订单总收入是多少",
        "按城市统计客户数量",
        "分析最近一个月的销售趋势",
        "iPhone 的销量如何",
        "各个商品类别的平均价格",
    ]

    for query in test_queries:
        print(f"\n[测试] 查询: {query}")
        print("-" * 40)

        result = service.prune(query)

        print(f"选中了 {len(result.selected_measures)} 个度量:")
        for m in result.selected_measures:
            score = result.scores.get(f"measure.{m.cube}.{m.name}", 0)
            print(f"  - {m.display_name} ({m.cube}.{m.name}) - 相似度: {score:.2f}")

        print(f"选中了 {len(result.selected_dimensions)} 个维度:")
        for d in result.selected_dimensions:
            score = result.scores.get(f"dimension.{d.cube}.{d.name}", 0)
            print(f"  - {d.display_name} ({d.cube}.{d.name}) - 相似度: {score:.2f}")

        print(f"涉及 Cube: {', '.join(sorted(result.selected_cubes))}")
        print(f"削减率: {result.reduction_rate:.1%}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
