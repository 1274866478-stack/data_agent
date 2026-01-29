# -*- coding: utf-8 -*-
"""
语义层增强工具 - 业务术语到语义定义的智能映射

这个模块提供了语义层的核心功能，将业务术语映射到数据库查询表达式，
避免 LLM 直接生成 SQL，提高查询的准确性和一致性。

主要功能：
1. resolve_business_term - 解析业务术语，返回匹配的语义层定义
2. get_semantic_measure - 获取特定度量的完整定义
3. suggest_related_measures - 推荐相关度量

作者: Data Agent Team
版本: 1.0.0
"""

import json
import yaml
import re
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class MeasureDefinition:
    """度量定义

    Attributes:
        cube: 所属 Cube (如 "Orders")
        name: 度量名称 (如 "total_revenue")
        display_name: 显示名称 (如 "订单总收入")
        type: 聚合类型 (sum/count/avg)
        sql_expression: SQL 表达式
        description: 描述
    """
    cube: str
    name: str
    display_name: str
    type: str
    sql_expression: str
    description: str


@dataclass
class DimensionDefinition:
    """维度定义

    Attributes:
        cube: 所属 Cube
        name: 维度名称
        display_name: 显示名称
        type: 维度类型 (time/string/number)
        enumerations: 枚举值列表（可选）
    """
    cube: str
    name: str
    display_name: str
    type: str
    enumerations: Optional[List[str]]


class SemanticLayerService:
    """语义层服务 - 解析和查询 cube_schema YAML 文件

    该服务从 cube_schema 目录读取 YAML 格式的语义定义文件，
    提供业务术语到 SQL 表达式的映射功能。

    目录结构:
        cube_schema/
        ├── Orders.yaml
        ├── Customers.yaml
        └── Products.yaml
    """

    BASE_PATH = Path(__file__).parent.parent.parent / "cube_schema"

    # 内置的业务术语映射（当 YAML 文件不存在时的回退方案）
    BUILTIN_MEASURES = {
        "总收入": {
            "cube": "Orders",
            "name": "total_revenue",
            "display_name": "订单总收入",
            "type": "sum",
            "sql": "SUM(total_amount)",
            "description": "所有订单的总金额"
        },
        "净收入": {
            "cube": "Orders",
            "name": "net_revenue",
            "display_name": "订单净收入",
            "type": "sum",
            "sql": "SUM(CASE WHEN status != 'cancelled' THEN total_amount ELSE 0 END)",
            "description": "排除取消订单后的总收入"
        },
        "销售额": {
            "cube": "Orders",
            "name": "sales_amount",
            "display_name": "销售额",
            "type": "sum",
            "sql": "SUM(total_amount)",
            "description": "销售总额"
        },
        "营收": {
            "cube": "Orders",
            "name": "revenue",
            "display_name": "营业收入",
            "type": "sum",
            "sql": "SUM(total_amount)",
            "description": "营业收入"
        },
        "订单数": {
            "cube": "Orders",
            "name": "order_count",
            "display_name": "订单数量",
            "type": "count",
            "sql": "COUNT(*)",
            "description": "订单总数"
        },
        "客户数": {
            "cube": "Customers",
            "name": "customer_count",
            "display_name": "客户数量",
            "type": "count",
            "sql": "COUNT(DISTINCT customer_id)",
            "description": "去重后的客户总数"
        },
        "平均订单金额": {
            "cube": "Orders",
            "name": "avg_order_amount",
            "display_name": "平均订单金额",
            "type": "avg",
            "sql": "AVG(total_amount)",
            "description": "每个订单的平均金额"
        },
        "商品数": {
            "cube": "Products",
            "name": "product_count",
            "display_name": "商品数量",
            "type": "count",
            "sql": "COUNT(*)",
            "description": "商品总数"
        },
        "毛利": {
            "cube": "Orders",
            "name": "gross_profit",
            "display_name": "毛利润",
            "type": "sum",
            "sql": "SUM(total_amount - cost)",
            "description": "销售收入减去成本"
        },
        "转化率": {
            "cube": "Orders",
            "name": "conversion_rate",
            "display_name": "转化率",
            "type": "ratio",
            "sql": "COUNT(DISTINCT customer_id) * 100.0 / COUNT(*)",
            "description": "访客转化为客户的百分比"
        },
    }

    # 状态值映射
    STATUS_VALUE_MAPPING = {
        "完成": {"value": "completed", "display": "已完成"},
        "已完成": {"value": "completed", "display": "已完成"},
        "进行中": {"value": "processing", "display": "进行中"},
        "已取消": {"value": "cancelled", "display": "已取消"},
        "待处理": {"value": "pending", "display": "待处理"},
        "已退款": {"value": "refunded", "display": "已退款"},
        "已发货": {"value": "shipped", "display": "已发货"},
        "活跃": {"value": "active", "display": "活跃"},
        "非活跃": {"value": "inactive", "display": "非活跃"},
    }

    def __init__(self, base_path: Optional[Path] = None):
        """初始化语义层服务

        Args:
            base_path: cube_schema 目录路径，默认使用相对路径
        """
        self.base_path = base_path or self.BASE_PATH
        self._cache: Dict[str, Any] = {}
        self._ensure_base_path_exists()

    def _ensure_base_path_exists(self):
        """确保 cube_schema 目录存在"""
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建 cube_schema 目录: {self.base_path}")

    def _load_cube_file(self, cube_name: str) -> Optional[Dict]:
        """加载指定 Cube 的 YAML 文件

        Args:
            cube_name: Cube 名称（不含扩展名）

        Returns:
            YAML 文件内容的字典，文件不存在返回 None
        """
        file_path = self.base_path / f"{cube_name}.yaml"

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载 {file_path} 失败: {e}")
            return None

    def _match_term(
        self,
        term: str,
        display_name: str,
        name: str,
        description: str
    ) -> bool:
        """术语匹配逻辑

        Args:
            term: 要匹配的业务术语
            display_name: 显示名称
            name: 内部名称
            description: 描述文本

        Returns:
            是否匹配
        """
        term_lower = term.lower().strip()

        # 1. 精确匹配 display_name
        if display_name and term_lower == display_name.lower():
            return True

        # 2. 模糊匹配 name (下划线转空格)
        name_normalized = name.replace('_', ' ').replace('-', ' ')
        if term_lower == name_normalized.lower():
            return True

        # 3. display_name 包含匹配
        if display_name and term_lower in display_name.lower():
            return True

        # 4. description 包含匹配
        if description and term_lower in description.lower():
            return True

        # 5. 模糊匹配（编辑距离近似）
        if self._fuzzy_match(term_lower, display_name):
            return True

        return False

    def _fuzzy_match(self, term: str, target: str, threshold: float = 0.7) -> bool:
        """模糊匹配（基于简单的相似度计算）

        Args:
            term: 搜索词
            target: 目标词
            threshold: 相似度阈值

        Returns:
            是否匹配
        """
        if not target:
            return False

        term = term.lower()
        target = target.lower()

        # 简单的包含匹配
        if term in target or target in term:
            return True

        # 计算简单的相似度
        common_chars = set(term) & set(target)
        similarity = len(common_chars) / max(len(set(term)), len(set(target)))

        return similarity >= threshold

    def resolve_business_term(self, term: str) -> List[Dict[str, Any]]:
        """解析业务术语，返回匹配的语义层定义

        这个方法是语义层的核心，将用户输入的业务术语（如"总收入"）
        映射到预定义的 SQL 表达式。

        Args:
            term: 业务术语，如 "总收入"、"订单数"

        Returns:
            匹配的语义层定义列表

        示例:
            输入: "总收入"
            输出: [
                {
                    "cube": "Orders",
                    "type": "measure",
                    "name": "total_revenue",
                    "display_name": "订单总收入",
                    "sql": "SUM(total_amount)",
                    "description": "所有订单的总金额"
                }
            ]
        """
        results = []

        # 1. 首先检查内置术语表
        if term in self.BUILTIN_MEASURES:
            builtin = self.BUILTIN_MEASURES[term]
            results.append({
                "source": "builtin",
                "cube": builtin["cube"],
                "type": "measure",
                "name": builtin["name"],
                "display_name": builtin["display_name"],
                "sql": builtin["sql"],
                "description": builtin["description"]
            })
            logger.info(f"从内置术语表匹配到: {term} -> {builtin['name']}")
            return results

        # 2. 模糊匹配内置术语表
        for builtin_term, definition in self.BUILTIN_MEASURES.items():
            if self._match_term(term, definition["display_name"], definition["name"], definition.get("description", "")):
                if not any(r["name"] == definition["name"] for r in results):
                    results.append({
                        "source": "builtin",
                        "cube": definition["cube"],
                        "type": "measure",
                        "name": definition["name"],
                        "display_name": definition["display_name"],
                        "sql": definition["sql"],
                        "description": definition.get("description", "")
                    })

        # 3. 从 YAML 文件中加载定义
        if self.base_path.exists():
            for yaml_file in self.base_path.glob("*.yaml"):
                try:
                    with open(yaml_file, encoding='utf-8') as f:
                        cube_def = yaml.safe_load(f)

                    if not cube_def:
                        continue

                    cube_name = cube_def.get('cube', yaml_file.stem)

                    # 匹配 measures
                    for measure in cube_def.get('measures', []):
                        if self._match_term(
                            term,
                            measure.get('display_name', measure.get('name', '')),
                            measure.get('name', ''),
                            measure.get('description', '')
                        ):
                            results.append({
                                "source": "yaml",
                                "cube": cube_name,
                                "type": "measure",
                                "name": measure.get('name', ''),
                                "display_name": measure.get('display_name', measure.get('name', '')),
                                "sql": measure.get('sql', measure.get('name', '')),
                                "description": measure.get('description', '')
                            })

                    # 匹配 dimensions
                    for dimension in cube_def.get('dimensions', []):
                        if self._match_term(
                            term,
                            dimension.get('display_name', dimension.get('name', '')),
                            dimension.get('name', ''),
                            dimension.get('description', '')
                        ):
                            # 处理维度SQL：如果sql字段使用${column}语法，需要解析
                            dim_sql = dimension.get('sql', '')
                            if dim_sql and '${' in dim_sql:
                                # 对于${column}语法，提取实际的列名
                                # 例如: ${order_date} -> order_date, ${created_at}::date -> created_at
                                match = re.search(r'\$\{([^}]+)\}', dim_sql)
                                if match:
                                    col_ref = match.group(1)
                                    # 如果有::date或::timestamp等类型转换，保留它
                                    dim_sql = dim_sql.replace('${', '').replace('}', '')

                            results.append({
                                "source": "yaml",
                                "cube": cube_name,
                                "type": "dimension",
                                "name": dimension.get('name', ''),
                                "display_name": dimension.get('display_name', dimension.get('name', '')),
                                "data_type": dimension.get('type', 'string'),
                                "enumerations": dimension.get('enumerations', []),
                                "sql": dim_sql,  # 添加sql字段用于实际查询
                                "description": dimension.get('description', '')
                            })

                except Exception as e:
                    logger.warning(f"读取 {yaml_file} 失败: {e}")

        # 4. 检查状态值映射
        if term in self.STATUS_VALUE_MAPPING:
            status_info = self.STATUS_VALUE_MAPPING[term]
            results.append({
                "source": "builtin",
                "type": "status_value",
                "original": term,
                "normalized": status_info["value"],
                "display": status_info["display"],
                "sql_template": f"status = '{status_info['value']}'",
                "description": f"状态值 '{term}' 的标准化映射"
            })

        logger.info(f"解析业务术语 '{term}'，找到 {len(results)} 个匹配结果")
        return results

    def get_semantic_measure(
        self,
        cube: str,
        measure: str
    ) -> Optional[Dict[str, Any]]:
        """获取特定度量的完整定义（包括 SQL 表达式）

        Args:
            cube: Cube 名称（如 "Orders"）
            measure: 度量名称（如 "total_revenue"）

        Returns:
            度量的完整定义，找不到返回 None
        """
        # 首先从内置表查找
        for definition in self.BUILTIN_MEASURES.values():
            if definition["cube"] == cube and definition["name"] == measure:
                return {
                    "source": "builtin",
                    **definition
                }

        # 从 YAML 文件查找
        if self.base_path.exists():
            yaml_path = self.base_path / f"{cube}.yaml"
            if yaml_path.exists():
                try:
                    with open(yaml_path, encoding='utf-8') as f:
                        cube_def = yaml.safe_load(f)

                    for measure_def in cube_def.get('measures', []):
                        if measure_def.get('name') == measure:
                            return {
                                "source": "yaml",
                                "cube": cube,
                                **measure_def
                            }
                except Exception as e:
                    logger.warning(f"读取 {yaml_path} 失败: {e}")

        return None

    def suggest_related_measures(self, term: str, limit: int = 5) -> List[Dict[str, Any]]:
        """推荐相关度量（用于模糊查询的智能推荐）

        Args:
            term: 业务术语
            limit: 返回数量限制

        Returns:
            相关度量列表
        """
        suggestions = []

        # 从内置术语表查找相似的
        for builtin_term, definition in self.BUILTIN_MEASURES.items():
            similarity = self._calculate_similarity(term, builtin_term)
            if similarity > 0.3:
                suggestions.append({
                    "term": builtin_term,
                    "definition": definition,
                    "similarity": similarity
                })

        # 从 display_name 查找相似的
        for definition in self.BUILTIN_MEASURES.values():
            similarity = self._calculate_similarity(term, definition["display_name"])
            if similarity > 0.3:
                existing = any(s["term"] == definition["display_name"] for s in suggestions)
                if not existing:
                    suggestions.append({
                        "term": definition["display_name"],
                        "definition": definition,
                        "similarity": similarity
                    })

        # 按相似度排序
        suggestions.sort(key=lambda x: x["similarity"], reverse=True)

        return suggestions[:limit]

    def _calculate_similarity(self, term1: str, term2: str) -> float:
        """计算两个术语的相似度

        Args:
            term1: 术语1
            term2: 术语2

        Returns:
            相似度 (0-1)
        """
        term1 = term1.lower().strip()
        term2 = term2.lower().strip()

        if term1 == term2:
            return 1.0

        # 包含匹配
        if term1 in term2 or term2 in term1:
            return 0.8

        # 简单的字符相似度
        common_chars = set(term1) & set(term2)
        if not common_chars:
            return 0.0

        return len(common_chars) / max(len(set(term1)), len(set(term2)))

    def list_available_cubes(self) -> List[str]:
        """列出所有可用的 Cube

        Returns:
            Cube 名称列表
        """
        cubes = set()

        # 从内置表收集
        for definition in self.BUILTIN_MEASURES.values():
            cubes.add(definition["cube"])

        # 从 YAML 文件收集
        if self.base_path.exists():
            for yaml_file in self.base_path.glob("*.yaml"):
                cubes.add(yaml_file.stem)

        return sorted(list(cubes))

    def get_cube_measures(self, cube: str) -> List[Dict[str, Any]]:
        """获取指定 Cube 的所有度量

        Args:
            cube: Cube 名称

        Returns:
            度量列表
        """
        measures = []

        # 从内置表收集
        for definition in self.BUILTIN_MEASURES.values():
            if definition["cube"] == cube:
                measures.append({
                    "source": "builtin",
                    **definition
                })

        # 从 YAML 文件收集
        if self.base_path.exists():
            yaml_path = self.base_path / f"{cube}.yaml"
            if yaml_path.exists():
                try:
                    with open(yaml_path, encoding='utf-8') as f:
                        cube_def = yaml.safe_load(f)

                    for measure_def in cube_def.get('measures', []):
                        measures.append({
                            "source": "yaml",
                            "cube": cube,
                            **measure_def
                        })
                except Exception as e:
                    logger.warning(f"读取 {yaml_path} 失败: {e}")

        return measures

    def normalize_status_value(self, status: str) -> Dict[str, Any]:
        """规范化状态值

        Args:
            status: 原始状态值

        Returns:
            规范化后的状态信息
        """
        if status in self.STATUS_VALUE_MAPPING:
            return {
                "original": status,
                "normalized": self.STATUS_VALUE_MAPPING[status]["value"],
                "display": self.STATUS_VALUE_MAPPING[status]["display"],
                "found": True
            }

        return {
            "original": status,
            "normalized": status,
            "display": status,
            "found": False
        }


# ============================================================================
# LangChain 工具函数
# ============================================================================

def resolve_business_term(term: str) -> str:
    """解析业务术语 - 供 LLM 调用

    这是一个 LangChain 工具函数，可以被 LLM 调用来解析业务术语。

    Args:
        term: 业务术语，如 "总收入"、"订单数"

    Returns:
        JSON 格式的匹配结果

    示例:
        >>> resolve_business_term("总收入")
        '[{"cube": "Orders", "type": "measure", "name": "total_revenue", ...}]'
    """
    service = SemanticLayerService()
    results = service.resolve_business_term(term)
    return json.dumps(results, ensure_ascii=False, indent=2)


def get_semantic_measure(cube: str, measure: str) -> str:
    """获取度量定义 - 供 LLM 调用

    Args:
        cube: Cube 名称
        measure: 度量名称

    Returns:
        JSON 格式的度量定义
    """
    service = SemanticLayerService()
    result = service.get_semantic_measure(cube, measure)

    if result:
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        return json.dumps({
            "error": f"度量 '{measure}' 在 Cube '{cube}' 中未找到"
        }, ensure_ascii=False)


def list_available_cubes() -> str:
    """列出所有可用的 Cube - 供 LLM 调用

    Returns:
        JSON 格式的 Cube 列表
    """
    service = SemanticLayerService()
    cubes = service.list_available_cubes()
    return json.dumps({
        "cubes": cubes,
        "count": len(cubes)
    }, ensure_ascii=False, indent=2)


def get_cube_measures(cube: str) -> str:
    """获取指定 Cube 的所有度量 - 供 LLM 调用

    Args:
        cube: Cube 名称

    Returns:
        JSON 格式的度量列表
    """
    service = SemanticLayerService()
    measures = service.get_cube_measures(cube)
    return json.dumps({
        "cube": cube,
        "measures": measures,
        "count": len(measures)
    }, ensure_ascii=False, indent=2)


def normalize_status_value(status: str) -> str:
    """规范化状态值 - 供 LLM 调用

    Args:
        status: 原始状态值

    Returns:
        JSON 格式的规范化结果
    """
    service = SemanticLayerService()
    result = service.normalize_status_value(status)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("语义层工具测试")
    print("=" * 60)

    service = SemanticLayerService()

    # 测试 1: 解析业务术语
    print("\n[测试 1] 解析业务术语: '总收入'")
    result = service.resolve_business_term("总收入")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 测试 2: 获取度量定义
    print("\n[测试 2] 获取度量定义: Orders.total_revenue")
    result = service.get_semantic_measure("Orders", "total_revenue")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 测试 3: 列出可用的 Cube
    print("\n[测试 3] 列出可用的 Cube")
    cubes = service.list_available_cubes()
    print(f"可用的 Cube: {cubes}")

    # 测试 4: 推荐
    print("\n[测试 4] 推荐: '收入'")
    suggestions = service.suggest_related_measures("收入")
    for s in suggestions:
        print(f"  - {s['term']} (相似度: {s['similarity']:.2f})")

    # 测试 5: 状态值规范化
    print("\n[测试 5] 状态值规范化: '已完成'")
    result = service.normalize_status_value("已完成")
    print(json.dumps(result, ensure_ascii=False, indent=2))
