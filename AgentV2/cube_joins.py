# -*- coding: utf-8 -*-
"""
Cube Joins 解析器 - 语义层表关联支持

这个模块提供 Cube 之间的 Join 关系解析功能：
1. 从 YAML schema 加载 Joins 定义
2. 解析 Join 表达式和关系类型
3. 生成带 Join 的 SQL 查询
4. 支持 Join 链和循环检测

核心功能：
- 解析 YAML 中的 joins 配置
- 验证 Join 关系的合法性
- 生成优化的 JOIN SQL 语句
- 检测循环依赖

作者: Data Agent Team
版本: 2.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

class RelationshipType(Enum):
    """关系类型枚举

    遵循 Cube.js 规范：
    - one_to_one: 一对一 (1:1)
    - one_to_many: 一对多 (1:N)
    - many_to_one: 多对一 (N:1)
    - many_to_many: 多对多 (N:M)
    """
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class JoinType(Enum):
    """Join 类型

    - INNER: 内连接，只返回匹配的行
    - LEFT: 左连接，返回左表所有行
    - RIGHT: 右连接，返回右表所有行
    - FULL: 全连接，返回所有行
    """
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"


@dataclass
class JoinDefinition:
    """Join 定义

    Attributes:
        name: 目标 Cube 名称
        sql: Join 条件 SQL 表达式
        relationship: 关系类型
        join_type: Join 类型 (默认 INNER)
        alias: 表别名（可选）
        metadata: 额外的元数据
    """
    name: str
    sql: str
    relationship: RelationshipType
    join_type: JoinType = JoinType.INNER
    alias: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "sql": self.sql,
            "relationship": self.relationship.value,
            "join_type": self.join_type.value,
            "alias": self.alias,
            "metadata": self.metadata
        }

    def get_join_sql(
        self,
        from_cube: str,
        from_alias: str = "",
        to_alias: str = ""
    ) -> str:
        """生成 Join SQL 语句

        Args:
            from_cube: 源 Cube 名称
            from_alias: 源表别名
            to_alias: 目标表别名

        Returns:
            Join SQL 语句
        """
        # 处理别名
        actual_from_alias = from_alias or from_cube
        actual_to_alias = to_alias or self.name

        # 替换模板变量
        # {CUBE} 或 ${CUBE} → 当前 Cube
        # {TargetCube} 或 ${TargetCube} → 目标 Cube
        join_sql = self.sql

        # 替换 {CUBE} 为源表别名
        join_sql = re.sub(r'\{CUBE\}', actual_from_alias, join_sql)
        join_sql = re.sub(r'\$\{CUBE\}', actual_from_alias, join_sql)

        # 替换 {TargetCube} 为目标表别名
        target_pattern = r'\{' + self.name + r'\}'
        join_sql = re.sub(target_pattern, actual_to_alias, join_sql)
        target_pattern = r'\$\{' + self.name + r'\}'
        join_sql = re.sub(target_pattern, actual_to_alias, join_sql)

        return join_sql


@dataclass
class CubeDefinition:
    """Cube 定义

    Attributes:
        name: Cube 名称
        sql_table: 基础 SQL 表
        measures: 度量列表
        dimensions: 维度列表
        joins: Join 定义列表
        file_path: YAML 文件路径
    """
    name: str
    sql_table: str
    measures: List[Dict[str, Any]] = field(default_factory=list)
    dimensions: List[Dict[str, Any]] = field(default_factory=list)
    joins: List[JoinDefinition] = field(default_factory=list)
    file_path: Optional[Path] = None

    def get_dependencies(self) -> Set[str]:
        """获取依赖的 Cube 集合"""
        return {join.name for join in self.joins}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "sql_table": self.sql_table,
            "measures": self.measures,
            "dimensions": self.dimensions,
            "joins": [j.to_dict() for j in self.joins],
            "file_path": str(self.file_path) if self.file_path else None
        }


# ============================================================================
# Joins 解析器
# ============================================================================

class CubeJoinsParser:
    """Cube Joins 解析器

    从 YAML schema 文件中解析 Joins 定义
    """

    def __init__(self, schema_dir: Optional[Path] = None):
        """初始化解析器

        Args:
            schema_dir: Cube schema 目录路径
        """
        if schema_dir is None:
            # 默认路径
            self.schema_dir = Path(__file__).parent.parent.parent / "cube_schema"
        else:
            self.schema_dir = Path(schema_dir)

        self._cubes: Dict[str, CubeDefinition] = {}
        self._join_graph: Dict[str, Set[str]] = {}

        # 自动加载 schema
        if self.schema_dir.exists():
            self.load_schemas()

    def load_schemas(self) -> int:
        """加载目录中的所有 schema 文件

        Returns:
            加载的 Cube 数量
        """
        count = 0
        for yaml_file in self.schema_dir.glob("*.yaml"):
            try:
                cube = self._load_yaml_file(yaml_file)
                if cube:
                    self._cubes[cube.name] = cube
                    count += 1
            except Exception as e:
                logger.warning(f"加载 {yaml_file} 失败: {e}")

        # 构建依赖图
        self._build_join_graph()

        logger.info(f"加载了 {count} 个 Cube 定义")
        return count

    def _load_yaml_file(self, yaml_file: Path) -> Optional[CubeDefinition]:
        """加载单个 YAML 文件"""
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        cube_name = data.get('cube', yaml_file.stem)
        sql_table = data.get('sql_table', data.get('sql', f'"{cube_name}"'))

        # 解析 joins
        joins = []
        for join_data in data.get('joins', []):
            join = self._parse_join(join_data, cube_name)
            if join:
                joins.append(join)

        # 解析 measures
        measures = data.get('measures', [])

        # 解析 dimensions
        dimensions = data.get('dimensions', [])

        return CubeDefinition(
            name=cube_name,
            sql_table=sql_table,
            measures=measures,
            dimensions=dimensions,
            joins=joins,
            file_path=yaml_file
        )

    def _parse_join(self, join_data: Dict[str, Any], source_cube: str) -> Optional[JoinDefinition]:
        """解析 Join 定义"""
        try:
            name = join_data.get('name', join_data.get('to', ''))
            if not name:
                logger.warning("Join 定义缺少 name 字段")
                return None

            sql = join_data.get('sql', join_data.get('on', ''))
            if not sql:
                logger.warning(f"Join '{name}' 缺少 sql/on 字段")
                return None

            relationship_str = join_data.get('relationship', 'many_to_one')
            try:
                relationship = RelationshipType(relationship_str)
            except ValueError:
                logger.warning(f"无效的关系类型: {relationship_str}")
                relationship = RelationshipType.MANY_TO_ONE

            join_type_str = join_data.get('join_type', 'INNER')
            try:
                join_type = JoinType(join_type_str.upper())
            except ValueError:
                join_type = JoinType.INNER

            alias = join_data.get('alias')
            metadata = join_data.get('metadata', {})

            return JoinDefinition(
                name=name,
                sql=sql,
                relationship=relationship,
                join_type=join_type,
                alias=alias,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"解析 Join 失败: {e}")
            return None

    def _build_join_graph(self):
        """构建 Join 依赖图"""
        self._join_graph = {}
        for cube_name, cube in self._cubes.items():
            self._join_graph[cube_name] = cube.get_dependencies()

    def get_cube(self, cube_name: str) -> Optional[CubeDefinition]:
        """获取 Cube 定义"""
        return self._cubes.get(cube_name)

    def get_all_cubes(self) -> Dict[str, CubeDefinition]:
        """获取所有 Cube 定义"""
        return self._cubes.copy()

    def get_joins(
        self,
        cube_name: str,
        max_depth: int = 3
    ) -> List[Tuple[str, JoinDefinition, int]]:
        """获取 Cube 的所有 Join 关系（包括传递依赖）

        Args:
            cube_name: 起始 Cube 名称
            max_depth: 最大递归深度

        Returns:
            (目标Cube名称, Join定义, 深度) 列表
        """
        if cube_name not in self._cubes:
            return []

        results = []
        visited = set()

        def traverse(current_cube: str, depth: int):
            if depth > max_depth or current_cube in visited:
                return

            visited.add(current_cube)
            cube = self._cubes.get(current_cube)
            if not cube:
                return

            for join in cube.joins:
                if join.name not in visited:
                    results.append((join.name, join, depth))
                    traverse(join.name, depth + 1)

        traverse(cube_name, 1)
        return results

    def get_join_path(
        self,
        from_cube: str,
        to_cube: str
    ) -> Optional[List[Tuple[str, JoinDefinition]]]:
        """查找两个 Cube 之间的 Join 路径

        使用 BFS 查找最短路径

        Args:
            from_cube: 起始 Cube
            to_cube: 目标 Cube

        Returns:
            Join 路径，每项是 (中间Cube名称, Join定义)
            如果不存在路径返回 None
        """
        if from_cube not in self._cubes or to_cube not in self._cubes:
            return None

        if from_cube == to_cube:
            return []

        # BFS 查找最短路径
        from collections import deque

        queue = deque([(from_cube, [])])
        visited = {from_cube}

        while queue:
            current_cube, path = queue.popleft()

            if current_cube == to_cube:
                return path

            cube = self._cubes.get(current_cube)
            if not cube:
                continue

            for join in cube.joins:
                if join.name not in visited:
                    visited.add(join.name)
                    new_path = path + [(current_cube, join)]
                    queue.append((join.name, new_path))

        return None

    def detect_cycles(self) -> List[List[str]]:
        """检测 Join 图中的循环

        Returns:
            循环列表，每个循环是一组 Cube 名称
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(cube: str, path: List[str]):
            visited.add(cube)
            rec_stack.add(cube)
            path.append(cube)

            for neighbor in self._join_graph.get(cube, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle.copy())

            path.pop()
            rec_stack.remove(cube)

        for cube in self._cubes:
            if cube not in visited:
                dfs(cube, [])

        return cycles

    def validate_joins(self) -> Dict[str, List[str]]:
        """验证所有 Joins 定义的合法性

        Returns:
            验证结果，key 是 Cube 名称，value 是错误列表
        """
        errors = {}

        for cube_name, cube in self._cubes.items():
            cube_errors = []

            # 检查 Join 的目标 Cube 是否存在
            for join in cube.joins:
                if join.name not in self._cubes:
                    cube_errors.append(
                        f"Join 目标 '{join.name}' 不存在"
                    )

                # 检查 SQL 语法
                if not self._validate_join_sql(join.sql):
                    cube_errors.append(
                        f"Join SQL 语法可能有问题: {join.sql}"
                    )

            if cube_errors:
                errors[cube_name] = cube_errors

        return errors

    @staticmethod
    def _validate_join_sql(sql: str) -> bool:
        """简单的 Join SQL 验证"""
        sql = sql.strip()

        # 检查是否包含基本的连接符
        if not any(op in sql for op in ['=', '==', '!=', '<', '>']):
            return False

        # 检查括号是否匹配
        stack = []
        for char in sql:
            if char == '(':
                stack.append(char)
            elif char == ')':
                if not stack:
                    return False
                stack.pop()

        return len(stack) == 0


# ============================================================================
# Join SQL 生成器
# ============================================================================

class JoinSQLGenerator:
    """Join SQL 生成器

    根据解析的 Joins 定义生成带 JOIN 的 SQL 查询
    """

    def __init__(self, parser: CubeJoinsParser):
        """初始化

        Args:
            parser: Cube Joins 解析器
        """
        self.parser = parser

    def generate_join_clause(
        self,
        primary_cube: str,
        required_cubes: List[str],
        use_aliases: bool = True
    ) -> Tuple[str, Dict[str, str]]:
        """生成 JOIN 子句

        Args:
            primary_cube: 主 Cube 名称
            required_cubes: 需要关联的 Cube 列表
            use_aliases: 是否使用表别名

        Returns:
            (JOIN 子句, 别名映射字典)
        """
        if not required_cubes:
            return "", {}

        alias_map: Dict[str, str] = {}
        join_clauses: List[str] = []
        visited = {primary_cube}

        if use_aliases:
            alias_map[primary_cube] = "t0"

        for required_cube in required_cubes:
            if required_cube == primary_cube:
                continue

            # 查找路径
            path = self.parser.get_join_path(primary_cube, required_cube)
            if not path:
                logger.warning(f"找不到从 {primary_cube} 到 {required_cube} 的 Join 路径")
                continue

            # 生成 JOIN 子句
            for i, (from_cube, join) in enumerate(path, start=1):
                if join.name in visited:
                    continue

                from_alias = alias_map.get(from_cube, f"t{i-1}")
                to_alias = f"t{i}" if use_aliases else ""

                join_sql = join.get_join_sql(
                    from_cube=from_cube,
                    from_alias=from_alias,
                    to_alias=to_alias
                )

                join_clause = f"{join.join_type.value} JOIN {join.name}"
                if to_alias:
                    join_clause += f" AS {to_alias}"
                join_clause += f" ON {join_sql}"

                join_clauses.append(join_clause)
                alias_map[join.name] = to_alias or join.name
                visited.add(join.name)

        return " ".join(join_clauses), alias_map

    def generate_full_query(
        self,
        primary_cube: str,
        select_columns: Dict[str, List[str]],
        where_clause: str = "",
        group_by: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """生成完整的带 Join 的查询

        Args:
            primary_cube: 主 Cube
            select_columns: 选择列，格式 {cube_name: [columns]}
            where_clause: WHERE 条件
            group_by: GROUP BY 列
            order_by: ORDER BY 表达式
            limit: LIMIT 数量

        Returns:
            完整的 SQL 查询
        """
        cube = self.parser.get_cube(primary_cube)
        if not cube:
            raise ValueError(f"Cube '{primary_cube}' 不存在")

        # 收集需要关联的 Cube
        required_cubes = [
            c for c in select_columns.keys()
            if c != primary_cube
        ]

        # 生成 JOIN 子句
        join_clause, alias_map = self.generate_join_clause(
            primary_cube,
            required_cubes
        )

        # 生成 SELECT 子句
        select_parts = []
        for cube_name, columns in select_columns.items():
            alias = alias_map.get(cube_name, cube_name)
            for col in columns:
                if alias:
                    select_parts.append(f"{alias}.{col}")
                else:
                    select_parts.append(f"{cube_name}.{col}")

        if not select_parts:
            select_parts = [f"{alias_map.get(primary_cube, primary_cube)}.*"]

        select_clause = ", ".join(select_parts)

        # 构建查询
        query_parts = [
            "SELECT",
            "  " + select_clause.replace(", ", ",\n  "),
            f"FROM {cube.sql_table} AS {alias_map.get(primary_cube, primary_cube)}"
        ]

        if join_clause:
            query_parts.append("  " + join_clause.replace(" JOIN ", "\n  JOIN "))

        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        if group_by:
            gb_columns = [alias_map.get(c.split('.')[0], c) for c in group_by]
            query_parts.append(f"GROUP BY {', '.join(gb_columns)}")

        if order_by:
            query_parts.append(f"ORDER BY {order_by}")

        if limit:
            query_parts.append(f"LIMIT {limit}")

        return "\n".join(query_parts)

    def get_available_columns(
        self,
        cube_name: str,
        include_joined: bool = True,
        max_depth: int = 2
    ) -> Dict[str, List[Dict[str, Any]]]:
        """获取 Cube 可用的列（包括通过 Join 关联的列）

        Args:
            cube_name: Cube 名称
            include_joined: 是否包含关联的 Cube
            max_depth: Join 深度

        Returns:
            列信息字典 {cube_name: [column_info]}
        """
        result = {}

        cube = self.parser.get_cube(cube_name)
        if not cube:
            return result

        # 添加主 Cube 的列
        result[cube_name] = self._get_cube_columns(cube)

        if include_joined:
            joins = self.parser.get_joins(cube_name, max_depth=max_depth)

            for target_cube, join, depth in joins:
                target = self.parser.get_cube(target_cube)
                if target:
                    result[target_cube] = self._get_cube_columns(target)

        return result

    @staticmethod
    def _get_cube_columns(cube: CubeDefinition) -> List[Dict[str, Any]]:
        """获取 Cube 的列信息"""
        columns = []

        # 添加度量列
        for measure in cube.measures:
            columns.append({
                "name": measure.get('name'),
                "type": measure.get('type'),
                "category": "measure",
                "description": measure.get('description', '')
            })

        # 添加维度列
        for dimension in cube.dimensions:
            columns.append({
                "name": dimension.get('name'),
                "type": dimension.get('type'),
                "category": "dimension",
                "description": dimension.get('description', '')
            })

        return columns


# ============================================================================
# 中间件集成
# ============================================================================

class CubeJoinsMiddleware:
    """Cube Joins 中间件

    为语义层工具提供 Join 支持
    """

    def __init__(
        self,
        schema_dir: Optional[Path] = None,
        enable_auto_detect: bool = True
    ):
        """初始化

        Args:
            schema_dir: Schema 目录
            enable_auto_detect: 是否自动检测 Join 需求
        """
        self.parser = CubeJoinsParser(schema_dir)
        self.generator = JoinSQLGenerator(self.parser)
        self.enable_auto_detect = enable_auto_detect

    def enhance_semantic_query(
        self,
        query_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """增强语义查询，添加 Join 支持

        Args:
            query_info: 查询信息，包含 cubes, measures, dimensions 等

        Returns:
            增强后的查询信息，包含 join_clause, alias_map 等
        """
        cubes = query_info.get('cubes', [])
        if not cubes:
            return query_info

        primary_cube = cubes[0]
        required_cubes = cubes[1:] if len(cubes) > 1 else []

        # 生成 JOIN 子句
        join_clause, alias_map = self.generator.generate_join_clause(
            primary_cube=primary_cube,
            required_cubes=required_cubes
        )

        if join_clause:
            query_info['join_clause'] = join_clause
            query_info['alias_map'] = alias_map

        return query_info

    def get_join_suggestions(
        self,
        measures: List[str],
        dimensions: List[str]
    ) -> List[str]:
        """根据请求的度量和维度建议需要 Join 的 Cube

        Args:
            measures: 请求的度量列表，格式 [cube.measure]
            dimensions: 请求的维度列表

        Returns:
            建议的 Cube 列表
        """
        suggested = set()

        # 解析度量
        for measure in measures:
            if '.' in measure:
                cube_name = measure.split('.')[0]
                suggested.add(cube_name)

        # 解析维度
        for dimension in dimensions:
            if '.' in dimension:
                cube_name = dimension.split('.')[0]
                suggested.add(cube_name)

        return list(suggested)

    def validate_join_feasibility(
        self,
        from_cube: str,
        to_cube: str
    ) -> Dict[str, Any]:
        """验证 Join 的可行性

        Args:
            from_cube: 源 Cube
            to_cube: 目标 Cube

        Returns:
            验证结果
        """
        result = {
            "feasible": False,
            "path": None,
            "depth": None,
            "error": None
        }

        if from_cube not in self.parser._cubes:
            result["error"] = f"源 Cube '{from_cube}' 不存在"
            return result

        if to_cube not in self.parser._cubes:
            result["error"] = f"目标 Cube '{to_cube}' 不存在"
            return result

        path = self.parser.get_join_path(from_cube, to_cube)
        if path is None:
            result["error"] = f"找不到从 '{from_cube}' 到 '{to_cube}' 的 Join 路径"
            return result

        result["feasible"] = True
        result["path"] = [(c, j.name) for c, j in path]
        result["depth"] = len(path)

        return result


# ============================================================================
# 工具函数
# ============================================================================

def get_cube_joins(cube_name: str) -> str:
    """获取 Cube 的 Joins 定义 - 供 LLM 调用

    Args:
        cube_name: Cube 名称

    Returns:
        JSON 格式的 Joins 定义
    """
    parser = CubeJoinsParser()
    cube = parser.get_cube(cube_name)

    if not cube:
        return json.dumps({
            "error": f"Cube '{cube_name}' 不存在"
        }, ensure_ascii=False)

    joins = [j.to_dict() for j in cube.joins]

    # 获取传递 Join
    transitive_joins = parser.get_joins(cube_name, max_depth=2)
    transitive = [
        {"target": target, "join": j.to_dict(), "depth": depth}
        for target, j, depth in transitive_joins
        if target != cube_name
    ]

    return json.dumps({
        "cube": cube_name,
        "direct_joins": joins,
        "transitive_joins": transitive,
        "total_count": len(joins)
    }, ensure_ascii=False, indent=2)


def validate_join_path(from_cube: str, to_cube: str) -> str:
    """验证两个 Cube 之间是否可以 Join - 供 LLM 调用

    Args:
        from_cube: 源 Cube
        to_cube: 目标 Cube

    Returns:
        JSON 格式的验证结果
    """
    middleware = CubeJoinsMiddleware()
    result = middleware.validate_join_feasibility(from_cube, to_cube)

    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import json

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("Cube Joins 解析器测试")
    print("=" * 60)

    # 创建解析器
    parser = CubeJoinsParser()

    # 列出所有 Cube
    print("\n[1] 所有 Cube:")
    for name, cube in parser.get_all_cubes().items():
        print(f"  - {name}: {len(cube.joins)} joins, 依赖: {cube.get_dependencies()}")

    # 测试特定 Cube 的 Joins
    test_cube = "Orders"
    cube = parser.get_cube(test_cube)
    if cube:
        print(f"\n[2] {test_cube} 的 Joins:")
        for join in cube.joins:
            print(f"  - {join.name} ({join.relationship.value}): {join.sql}")

    # 测试 Join 路径
    print("\n[3] Join 路径测试:")
    test_paths = [
        ("Orders", "Customers"),
        ("Orders", "Products"),
    ]
    for from_c, to_c in test_paths:
        path = parser.get_join_path(from_c, to_c)
        if path:
            path_str = " → ".join([f"{c}({j.name})" for c, j in path])
            print(f"  {from_c} → {to_c}: {path_str}")
        else:
            print(f"  {from_c} → {to_c}: 无路径")

    # 检测循环
    cycles = parser.detect_cycles()
    print(f"\n[4] 循环检测: 发现 {len(cycles)} 个循环")
    for cycle in cycles:
        print(f"  - {' → '.join(cycle)}")

    # 验证 Joins
    errors = parser.validate_joins()
    print(f"\n[5] Joins 验证: {len(errors)} 个 Cube 有错误")
    for cube_name, cube_errors in errors.items():
        print(f"  - {cube_name}:")
        for error in cube_errors:
            print(f"    • {error}")

    # 测试 SQL 生成
    generator = JoinSQLGenerator(parser)
    print("\n[6] 生成 JOIN SQL:")
    if cube:
        join_clause, alias_map = generator.generate_join_clause(
            primary_cube="Orders",
            required_cubes=["Customers"],
            use_aliases=True
        )
        print(f"  JOIN 子句: {join_clause}")
        print(f"  别名映射: {alias_map}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
