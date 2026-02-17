"""
Repair Agent - 修复器

负责：
1. 错误模式识别 - 识别常见 DSL 错误
2. 自动修复 - 应用修复策略
3. LLM 辅助修复 - 对复杂错误使用 LLM 修复
"""

from typing import Dict, Any, List, Optional
import yaml
import os
import re
from difflib import get_close_matches

from .base_agent import BaseAgent


class RepairAgent(BaseAgent):
    """
    修复器 Agent - DSL 自愈

    职责:
    1. 分析错误模式
    2. 应用修复策略
    3. 生成修复后的 DSL
    """

    def __init__(self, name: str = "repair", llm=None, error_patterns_path: str = None):
        super().__init__(name, llm)
        self.error_patterns = self._load_error_patterns(error_patterns_path)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行修复逻辑

        Args:
            state: 当前状态，包含 dsl_json, error_message 等

        Returns:
            更新后的状态，包含修复后的 dsl_json
        """
        dsl_json = state.get("dsl_json", {})
        error_message = state.get("error_message", "")
        cube_schema = state.get("cube_schema", {})
        tenant_id = state.get("tenant_id", "")

        # 1. 匹配错误模式
        matched_pattern = self._match_error_pattern(error_message)

        # 2. 查找修复历史
        historical_repairs = await self._find_similar_repairs(
            tenant_id,
            matched_pattern.get("name") if matched_pattern else None,
            dsl_json
        )

        # 3. 尝试修复
        if matched_pattern and matched_pattern.get("auto_fix", False):
            # 自动修复
            repaired_dsl = await self._auto_repair(
                dsl_json,
                error_message,
                matched_pattern,
                cube_schema,
                historical_repairs
            )
        else:
            # LLM 辅助修复
            repaired_dsl = await self._llm_repair(
                dsl_json,
                error_message,
                cube_schema,
                historical_repairs
            )

        # 4. 记录修复历史（如果有相关服务）
        # await self._store_repair_history(...)

        return {"dsl_json": repaired_dsl, "repair_attempted": True}

    def _load_error_patterns(self, patterns_path: str = None) -> List[Dict[str, Any]]:
        """加载错误模式"""
        if patterns_path is None:
            # 尝试从默认位置加载
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "..",  # 回到 AgentV2
                "self_healing",
                "error_patterns.yaml"
            )
            if os.path.exists(default_path):
                patterns_path = default_path

        if not patterns_path or not os.path.exists(patterns_path):
            return self._get_default_patterns()

        try:
            with open(patterns_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get("patterns", [])
        except Exception as e:
            print(f"加载错误模式失败: {e}")
            return self._get_default_patterns()

    def _get_default_patterns(self) -> List[Dict[str, Any]]:
        """获取默认错误模式"""
        return [
            {
                "name": "measure_not_found",
                "description": "度量不存在",
                "regex": r"Measure '(.+)' not found",
                "fix_strategy": "suggest_similar_measures",
                "auto_fix": True
            },
            {
                "name": "dimension_not_found",
                "description": "维度不存在",
                "regex": r"Dimension '(.+)' not found",
                "fix_strategy": "suggest_similar_dimensions",
                "auto_fix": True
            },
            {
                "name": "cube_not_found",
                "description": "Cube 不存在",
                "regex": r"Cube '(.+)' does not exist",
                "fix_strategy": "list_available_cubes",
                "auto_fix": False
            },
            {
                "name": "invalid_join",
                "description": "无效的 JOIN",
                "regex": r"Cannot join (.+) on (.+)",
                "fix_strategy": "use_precomputed_joins",
                "auto_fix": True
            },
            {
                "name": "missing_filter",
                "description": "缺少必需的过滤器",
                "regex": r"Required filter missing: (.+)",
                "fix_strategy": "infer_from_context",
                "auto_fix": True
            },
            {
                "name": "time_range_error",
                "description": "时间范围错误",
                "regex": r"Time range (.+) is invalid",
                "fix_strategy": "adjust_time_range",
                "auto_fix": True
            },
            {
                "name": "aggregation_error",
                "description": "聚合错误",
                "regex": r"Cannot aggregate (.+) with (.+)",
                "fix_strategy": "change_aggregation_type",
                "auto_fix": True
            }
        ]

    def _match_error_pattern(self, error_message: str) -> Optional[Dict[str, Any]]:
        """匹配错误模式"""
        if not error_message:
            return None

        for pattern in self.error_patterns:
            regex_pattern = pattern.get("regex")
            if regex_pattern:
                try:
                    if re.search(regex_pattern, error_message, re.IGNORECASE):
                        return pattern
                except re.error:
                    continue

        return None

    async def _find_similar_repairs(
        self,
        tenant_id: str,
        error_pattern: str,
        original_dsl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """查找相似的历史修复"""
        # TODO: 从数据库查询修复历史
        # 暂时返回空列表
        return []

    async def _auto_repair(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        pattern: Dict[str, Any],
        cube_schema: Dict[str, Any],
        historical_repairs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """自动修复"""
        strategy = pattern.get("fix_strategy")

        if strategy == "suggest_similar_measures":
            return await self._suggest_similar_measures(broken_dsl, error_message, cube_schema)

        elif strategy == "suggest_similar_dimensions":
            return await self._suggest_similar_dimensions(broken_dsl, error_message, cube_schema)

        elif strategy == "use_precomputed_joins":
            return await self._fix_join(broken_dsl, cube_schema)

        elif strategy == "infer_from_context":
            return await self._infer_missing_filter(broken_dsl, error_message)

        elif strategy == "adjust_time_range":
            return await self._adjust_time_range(broken_dsl, error_message)

        elif strategy == "change_aggregation_type":
            return await self._change_aggregation_type(broken_dsl, error_message, cube_schema)

        # 默认返回原 DSL
        return broken_dsl

    async def _suggest_similar_measures(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """建议相似的度量"""
        # 提取不存在的度量名称
        match = re.search(r"Measure '(.+?)' not found", error_message)
        if not match:
            return broken_dsl

        missing_measure = match.group(1)

        # 获取可用的度量
        cube_name = broken_dsl.get("cube")
        if not cube_name or cube_name not in cube_schema:
            return broken_dsl

        available_measures = cube_schema.get(cube_name, {}).get("measures", [])

        # 查找相似的度量
        similar = get_close_matches(missing_measure, available_measures, n=3, cutoff=0.3)

        if similar:
            # 替换为最相似的度量
            new_measures = [
                similar[0] if m == missing_measure or m.split(".")[-1] == missing_measure else m
                for m in broken_dsl.get("measures", [])
            ]
            broken_dsl["measures"] = new_measures

        return broken_dsl

    async def _suggest_similar_dimensions(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """建议相似的维度"""
        match = re.search(r"Dimension '(.+?)' not found", error_message)
        if not match:
            return broken_dsl

        missing_dimension = match.group(1)

        cube_name = broken_dsl.get("cube")
        if not cube_name or cube_name not in cube_schema:
            return broken_dsl

        available_dimensions = cube_schema.get(cube_name, {}).get("dimensions", [])

        # 查找相似的维度
        similar = get_close_matches(missing_dimension, available_dimensions, n=3, cutoff=0.3)

        if similar:
            # 替换维度
            new_dimensions = [
                similar[0] if d == missing_dimension or d.split(".")[-1] == missing_dimension else d
                for d in broken_dsl.get("dimensions", [])
            ]
            broken_dsl["dimensions"] = new_dimensions

        return broken_dsl

    async def _fix_join(
        self,
        broken_dsl: Dict[str, Any],
        cube_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """修复 JOIN 问题"""
        # 简化：移除可能的自定义 join，依赖语义层预定义
        if "joins" in broken_dsl:
            del broken_dsl["joins"]
        return broken_dsl

    async def _infer_missing_filter(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """推断缺失的过滤器"""
        # 简化：移除可能有问题的过滤器
        filters = broken_dsl.get("filters", [])
        # 保留基本的过滤器，移除复杂的
        valid_filters = [
            f for f in filters
            if isinstance(f, dict) and len(f.get("values", [])) > 0
        ]
        broken_dsl["filters"] = valid_filters
        return broken_dsl

    async def _adjust_time_range(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """调整时间范围"""
        # 简化：移除时间过滤器
        if "timeDimension" in broken_dsl:
            del broken_dsl["timeDimension"]
        if "granularity" in broken_dsl:
            del broken_dsl["granularity"]
        return broken_dsl

    async def _change_aggregation_type(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更改聚合类型"""
        # 简化：使用第一个可用的度量
        measures = broken_dsl.get("measures", [])
        if measures:
            cube_name = broken_dsl.get("cube")
            if cube_name and cube_name in cube_schema:
                available_measures = cube_schema.get(cube_name, {}).get("measures", [])
                if available_measures:
                    broken_dsl["measures"] = [available_measures[0]]
        return broken_dsl

    async def _llm_repair(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any],
        historical_repairs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """使用 LLM 修复"""
        if not self.llm:
            return broken_dsl

        # 构建 Prompt
        cube_def_text = self._format_cube_schema(cube_schema)

        prompt = f"""
以下 DSL 执行出错，请修复：

错误信息: {error_message}

当前 DSL:
```json
{broken_dsl}
```

可用的语义层定义:
{cube_def_text}

请输出修复后的 DSL JSON (仅输出 JSON，不要有其他文字)。
"""

        try:
            response = await self.llm.ainvoke(prompt)
            # 尝试解析 LLM 响应
            response_str = str(response).strip()

            # 尝试提取 JSON
            if "```json" in response_str:
                json_start = response_str.find("```json") + 7
                json_end = response_str.find("```", json_start)
                json_str = response_str[json_start:json_end].strip()
            elif "```" in response_str:
                json_start = response_str.find("```") + 3
                json_end = response_str.find("```", json_start)
                json_str = response_str[json_start:json_end].strip()
            else:
                json_str = response_str

            import json
            repaired = json.loads(json_str)
            return repaired

        except Exception as e:
            print(f"LLM 修复失败: {e}")
            return broken_dsl

    def _format_cube_schema(self, cube_schema: Dict[str, Any]) -> str:
        """格式化 Cube 定义"""
        lines = []
        for cube_name, cube_def in cube_schema.items():
            lines.append(f"\n### {cube_name}")
            lines.append(f"度量: {', '.join(cube_def.get('measures', []))}")
            lines.append(f"维度: {', '.join(cube_def.get('dimensions', []))}")
        return "\n".join(lines)
