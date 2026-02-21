# -*- coding: utf-8 -*-
"""
语义层增强管道 - 统一的中间件集成

这个模块将所有语义层增强功能集成到一个管道中：
1. 向量检索 Entity Linking
2. 业务术语表解析
3. Schema Pruning 智能剪枝
4. Cube Joins 支持

使用方式：
    pipeline = SemanticEnhancementPipeline()
    enhanced_input = pipeline.process_agent_input({
        "query": "P40 的销售额是多少",
        "tenant_id": "xxx"
    })

作者: Data Agent Team
版本: 2.0.0
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .entity_linking import (
    EntityLinkingService,
    EntityLinkingMiddleware,
)
from .context.business_glossary import BusinessGlossary
from .schema_pruning import (
    SchemaPruningService,
    SchemaPruningMiddleware
)
from .cube_joins import (
    CubeJoinsMiddleware,
)

logger = logging.getLogger(__name__)


@dataclass
class EnhancementResult:
    """增强结果

    Attributes:
        original_query: 原始查询
        normalized_query: 规范化后的查询
        linked_entities: 链接的实体
        glossary_terms: 识别的业务术语
        pruned_schema: 剪枝后的 schema
        join_suggestions: Join 建议
        prompt_injection: 注入到 Prompt 的文本
        metadata: 额外的元数据
    """
    original_query: str
    normalized_query: str
    linked_entities: List[Dict[str, Any]] = field(default_factory=list)
    glossary_terms: List[Dict[str, Any]] = field(default_factory=list)
    pruned_schema: Dict[str, Any] = field(default_factory=dict)
    join_suggestions: List[str] = field(default_factory=list)
    prompt_injection: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "linked_entities": self.linked_entities,
            "glossary_terms": self.glossary_terms,
            "pruned_schema": self.pruned_schema,
            "join_suggestions": self.join_suggestions,
            "prompt_injection": self.prompt_injection,
            "metadata": self.metadata
        }


class SemanticEnhancementPipeline:
    """语义层增强管道

    集成所有语义层增强功能的统一入口
    """

    def __init__(
        self,
        enable_entity_linking: bool = True,
        enable_glossary: bool = True,
        enable_schema_pruning: bool = True,
        enable_joins: bool = True,
        embedding_service=None,
        schema_dir: Optional[Path] = None,
        glossary_path: Optional[str] = None
    ):
        """初始化管道

        Args:
            enable_entity_linking: 是否启用实体链接
            enable_glossary: 是否启用业务术语表
            enable_schema_pruning: 是否启用 Schema 剪枝
            enable_joins: 是否启用 Joins 支持
            embedding_service: 向量嵌入服务
            schema_dir: Schema 目录
            glossary_path: 术语表文件路径
        """
        # 实体链接服务
        self.enable_entity_linking = enable_entity_linking
        if enable_entity_linking:
            self.entity_linking_service = EntityLinkingService(
                embedding_service=embedding_service
            )
            self.entity_linking_middleware = EntityLinkingMiddleware(
                linking_service=self.entity_linking_service
            )

        # 业务术语表
        self.enable_glossary = enable_glossary
        if enable_glossary:
            self.glossary = BusinessGlossary(
                custom_glossary_path=glossary_path,
                enable_hot_reload=True
            )

        # Schema 剪枝
        self.enable_schema_pruning = enable_schema_pruning
        if enable_schema_pruning:
            self.schema_pruning_service = SchemaPruningService(
                embedding_service=embedding_service
            )
            self.schema_pruning_middleware = SchemaPruningMiddleware(
                pruning_service=self.schema_pruning_service
            )

        # Joins 支持
        self.enable_joins = enable_joins
        if enable_joins:
            self.joins_middleware = CubeJoinsMiddleware(
                schema_dir=schema_dir
            )

    def process_agent_input(
        self,
        agent_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理 Agent 输入，应用所有增强功能

        Args:
            agent_input: 原始 Agent 输入
                - query: 用户查询
                - tenant_id: 租户ID（可选）
                - 其他字段...

        Returns:
            增强后的 Agent 输入
        """
        query = agent_input.get("query", "")
        tenant_id = agent_input.get("tenant_id")

        if not query:
            return agent_input

        # 创建增强结果
        result = EnhancementResult(
            original_query=query,
            normalized_query=query
        )

        # 1. 实体链接
        if self.enable_entity_linking:
            linking_results = self.entity_linking_service.link(
                query,
                tenant_id=tenant_id,
                top_k=3
            )
            result.linked_entities = [r.to_dict() for r in linking_results]

            # 规范化查询（替换实体名称）
            for r in linking_results:
                if r.matched_entity and r.confidence > 0.8:
                    result.normalized_query = result.normalized_query.replace(
                        r.query,
                        r.matched_entity.name
                    )

        # 2. 业务术语表解析
        if self.enable_glossary:
            # 热更新检查
            self.glossary.reload_if_needed()

            # 注入术语表
            glossary_injection = self.glossary.inject_glossary_to_prompt(query)
            if glossary_injection:
                agent_input["__glossary_injection__"] = glossary_injection

            # 规范化查询
            normalized = self.glossary.normalize_query(result.normalized_query)
            result.normalized_query = normalized

            # 收集识别的术语
            terms = self._extract_glossary_terms(query)
            result.glossary_terms = terms

        # 3. Schema 剪枝
        if self.enable_schema_pruning:
            pruned_schema = self.schema_pruning_service.get_pruned_schema_dict(
                result.normalized_query
            )
            result.pruned_schema = pruned_schema

            agent_input["__pruned_schema__"] = pruned_schema

        # 4. Joins 建议
        if self.enable_joins:
            suggestions = self._get_join_suggestions(result)
            result.join_suggestions = suggestions

        # 5. 生成统一的 Prompt 注入
        result.prompt_injection = self._generate_prompt_injection(result)

        # 注入到 Agent 输入
        agent_input["__semantic_enhancement__"] = result.to_dict()
        agent_input["__enhanced_prompt__"] = result.prompt_injection
        agent_input["normalized_query"] = result.normalized_query

        logger.info(
            f"语义层增强完成: "
            f"{len(result.linked_entities)} 实体, "
            f"{len(result.glossary_terms)} 术语, "
            f"削减率 {result.pruned_schema.get('summary', {}).get('reduction_rate', '0%')}"
        )

        return agent_input

    def _extract_glossary_terms(self, query: str) -> List[Dict[str, Any]]:
        """从查询中提取业务术语"""
        terms = []

        # 检查城市别名
        for alias, city in self.glossary.CITY_ALIASES.items():
            if alias in query:
                terms.append({
                    "type": "city_alias",
                    "original": alias,
                    "normalized": city
                })

        # 检查业务指标
        for acronym, definition in self.glossary.BUSINESS_METRIC_ALIASES.items():
            if acronym in query:
                terms.append({
                    "type": "business_metric",
                    "original": acronym,
                    "normalized": definition["target"],
                    "description": definition.get("description", "")
                })

        # 检查时间表达式
        for expr, sql in self.glossary.TIME_EXPRESSIONS.items():
            if expr in query:
                terms.append({
                    "type": "time_expression",
                    "original": expr,
                    "normalized": sql
                })

        return terms

    def _get_join_suggestions(self, result: EnhancementResult) -> List[str]:
        """获取 Join 建议"""
        suggestions = []

        # 从 pruned_schema 获取涉及的 Cube
        cubes = result.pruned_schema.get("cubes", {}).keys()
        cubes = list(cubes)

        if len(cubes) > 1:
            # 多 Cube 查询，需要 Join
            suggestions.append(f"需要关联的 Cube: {', '.join(cubes)}")

            # 验证 Join 可行性
            if self.enable_joins and len(cubes) >= 2:
                primary = cubes[0]
                for target in cubes[1:]:
                    validation = self.joins_middleware.validate_join_feasibility(
                        primary, target
                    )
                    if validation.get("feasible"):
                        suggestions.append(
                            f"✓ {primary} → {target}: 可通过 {validation['depth']} 层 Join 连接"
                        )
                    else:
                        suggestions.append(
                            f"✗ {primary} → {target}: {validation.get('error', '无法连接')}"
                        )

        return suggestions

    def _generate_prompt_injection(self, result: EnhancementResult) -> str:
        """生成注入到 Prompt 的文本"""
        lines = []

        # 标题
        lines.append("## 语义层增强")
        lines.append("")

        # 实体链接结果
        if result.linked_entities:
            lines.append("### 实体链接")
            for entity_dict in result.linked_entities:
                entity = entity_dict.get("matched_entity")
                if entity:
                    lines.append(
                        f"- **{entity['name']}** (置信度: {entity_dict['confidence']:.1%})"
                    )
                    if entity.get("description"):
                        lines.append(f"  - {entity['description']}")
            lines.append("")

        # 业务术语
        if result.glossary_terms:
            lines.append("### 术语规范化")
            for term in result.glossary_terms:
                lines.append(
                    f"- {term['original']} → {term['normalized']} ({term['type']})"
                )
            lines.append("")

        # Schema 剪枝结果
        if result.pruned_schema:
            summary = result.pruned_schema.get("summary", {})
            lines.append(f"### 相关 Schema（已优化 {summary.get('reduction_rate', '0%')}）")
            for cube_name, cube_data in result.pruned_schema.get("cubes", {}).items():
                measures = cube_data.get("measures", [])
                dimensions = cube_data.get("dimensions", [])

                line_parts = [f"**{cube_name}**:"]
                if measures:
                    measure_names = [m.get("display_name", m.get("name")) for m in measures]
                    line_parts.append(f"度量: {', '.join(measure_names[:5])}")
                if dimensions:
                    dim_names = [d.get("display_name", d.get("name")) for d in dimensions]
                    line_parts.append(f"维度: {', '.join(dim_names[:5])}")

                lines.append(" - ".join(line_parts))
            lines.append("")

        # Join 建议
        if result.join_suggestions:
            lines.append("### Join 建议")
            for suggestion in result.join_suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")

        return "\n".join(lines)

    def enhance_system_prompt(
        self,
        base_prompt: str,
        query: str,
        tenant_id: Optional[str] = None
    ) -> str:
        """增强系统提示词

        Args:
            base_prompt: 基础系统提示词
            query: 用户查询
            tenant_id: 租户ID

        Returns:
            增强后的系统提示词
        """
        # 处理输入
        agent_input = {"query": query, "tenant_id": tenant_id}
        enhanced = self.process_agent_input(agent_input)

        # 获取注入文本
        injection = enhanced.get("__enhanced_prompt__", "")

        if not injection:
            return base_prompt

        return f"""{base_prompt}

{injection}

---
💡 提示：以上内容已根据用户查询进行语义增强，请使用标准化的术语和 Schema 进行查询。
"""

    def get_statistics(self) -> Dict[str, Any]:
        """获取管道统计信息"""
        stats = {
            "enabled_features": {
                "entity_linking": self.enable_entity_linking,
                "glossary": self.enable_glossary,
                "schema_pruning": self.enable_schema_pruning,
                "joins": self.enable_joins
            }
        }

        if self.enable_entity_linking:
            stats["entity_count"] = self.entity_linking_service.entity_store.count()

        if self.enable_glossary:
            stats["glossary_summary"] = self.glossary.get_glossary_summary()

        if self.enable_schema_pruning:
            stats["schema_count"] = {
                "measures": len(self.schema_pruning_service.measures),
                "dimensions": len(self.schema_pruning_service.dimensions)
            }

        if self.enable_joins:
            cubes = self.joins_middleware.parser.get_all_cubes()
            stats["cube_count"] = len(cubes)

        return stats


# ============================================================================
# 工具函数
# ============================================================================

def create_default_pipeline() -> SemanticEnhancementPipeline:
    """创建默认配置的语义层增强管道"""
    return SemanticEnhancementPipeline(
        enable_entity_linking=True,
        enable_glossary=True,
        enable_schema_pruning=True,
        enable_joins=True
    )


def enhance_query(
    query: str,
    tenant_id: Optional[str] = None
) -> str:
    """增强查询 - 简单调用接口

    Args:
        query: 用户查询
        tenant_id: 租户ID

    Returns:
        JSON 格式的增强结果
    """
    pipeline = create_default_pipeline()
    agent_input = pipeline.process_agent_input({"query": query, "tenant_id": tenant_id})
    result = agent_input.get("__semantic_enhancement__", {})

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
    print("语义层增强管道测试")
    print("=" * 60)

    # 创建管道
    pipeline = create_default_pipeline()

    # 显示统计信息
    stats = pipeline.get_statistics()
    print("\n[统计信息]")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    # 测试查询
    test_queries = [
        "魔都的 P40 手机销售额是多少",
        "按城市统计本月的 GMV",
        "iPhone 的订单完成率怎么样",
        "分析最近一周的客户分布趋势",
    ]

    for query in test_queries:
        print(f"\n[测试] 查询: {query}")
        print("-" * 40)

        agent_input = pipeline.process_agent_input({"query": query})

        enhancement = agent_input.get("__semantic_enhancement__", {})
        print(f"规范化查询: {enhancement.get('normalized_query', query)}")
        print(f"实体链接: {len(enhancement.get('linked_entities', []))} 个")
        print(f"术语识别: {len(enhancement.get('glossary_terms', []))} 个")

        summary = enhancement.get('pruned_schema', {}).get('summary', {})
        print(f"Schema 削减率: {summary.get('reduction_rate', '0%')}")

        print("\n生成的 Prompt 注入:")
        print(agent_input.get("__enhanced_prompt__", ""))

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
