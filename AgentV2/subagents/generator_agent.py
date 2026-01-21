"""
Generator Agent - 生成器

负责：
1. DSL JSON 生成 - 根据查询计划生成符合语义层规范的 DSL
2. 少样本学习 - 使用历史成功案例提升生成质量
3. 格式验证 - 确保 DSL 格式正确
"""

from typing import Dict, Any, List, Optional
import json

from .base_agent import BaseAgent


class GeneratorAgent(BaseAgent):
    """
    生成器 Agent

    输入: 查询计划 + Cube 定义 + 少样本示例（可选）
    输出: DSL JSON (符合语义层规范)
    """

    def __init__(self, name: str = "generator", llm=None):
        super().__init__(name, llm)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行生成逻辑

        Args:
            state: 当前状态，包含 query_plan, cube_schema 等

        Returns:
            更新后的状态，包含 dsl_json
        """
        query_plan = state.get("query_plan", {})
        cube_schema = state.get("cube_schema", {})
        query = state.get("query", "")
        few_shot_examples = state.get("few_shot_examples", [])

        # 生成 DSL
        dsl_json = await self._generate_dsl(
            query,
            query_plan,
            cube_schema,
            few_shot_examples
        )

        return {"dsl_json": dsl_json}

    async def _generate_dsl(
        self,
        query: str,
        query_plan: Dict[str, Any],
        cube_schema: Dict[str, Any],
        few_shot_examples: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成 DSL JSON

        Args:
            query: 原始问题
            query_plan: 查询计划
            cube_schema: Cube 定义
            few_shot_examples: 少样本示例（可选）

        Returns:
            DSL JSON
        """
        # 获取目标 Cube
        target_cubes = query_plan.get("target_cubes", [])
        if not target_cubes:
            return self._create_error_dsl("未找到目标 Cube")

        cube_name = target_cubes[0]

        # 构建 DSL
        dsl = {
            "cube": cube_name,
            "measures": query_plan.get("required_measures", []),
            "dimensions": query_plan.get("required_dimensions", [])
        }

        # 添加时间维度
        time_req = query_plan.get("time_requirements", {})
        if time_req.get("has_time_filter"):
            # 查找时间维度
            time_dimension = self._find_time_dimension(cube_name, cube_schema)
            if time_dimension:
                dsl["timeDimension"] = time_dimension
                dsl["granularity"] = time_req.get("granularity", "day")

        # 添加过滤器
        filters = query_plan.get("filters", [])
        if filters:
            # 将过滤器转换为 Cube 格式
            cube_filters = []
            for f in filters:
                cube_filters.append({
                    "member": f"{cube_name}.{f['member']}",
                    "operator": f["operator"],
                    "values": f["values"]
                })
            if cube_filters:
                dsl["filters"] = cube_filters

        # 添加排序
        if "排名" in query or "top" in query.lower():
            dsl["order"] = [{f"{cube_name}.created_at": "desc"}]
            dsl["limit"] = 10

        return dsl

    def _find_time_dimension(
        self,
        cube_name: str,
        cube_schema: Dict[str, Any]
    ) -> Optional[str]:
        """查找时间维度"""
        if cube_name not in cube_schema:
            return None

        dimensions = cube_schema[cube_name].get("dimensions", [])

        for dim in dimensions:
            dim_lower = dim.lower()
            if any(kw in dim_lower for kw in ["time", "date", "created", "updated", "时间", "日期"]):
                return f"{cube_name}.{dim}"

        return None

    def _create_error_dsl(self, error_message: str) -> Dict[str, Any]:
        """创建错误 DSL"""
        return {
            "error": error_message,
            "cube": None,
            "measures": [],
            "dimensions": []
        }

    async def generate_with_llm(
        self,
        prompt: str
    ) -> Dict[str, Any]:
        """
        使用 LLM 生成 DSL

        Args:
            prompt: 包含上下文的 Prompt

        Returns:
            DSL JSON
        """
        if not self.llm:
            return {"error": "LLM 未配置"}

        try:
            response = await self.llm.ainvoke(prompt)
            # 解析 LLM 响应
            # 这里需要根据实际的 LLM 响应格式来解析
            # 暂时返回占位符
            return {"llm_response": str(response)}
        except Exception as e:
            return {"error": f"LLM 生成失败: {str(e)}"}

    def build_prompt_with_examples(
        self,
        query: str,
        query_plan: Dict[str, Any],
        cube_schema: Dict[str, Any],
        examples: List[Dict[str, Any]] = None
    ) -> str:
        """
        构建包含少样本示例的 Prompt

        Args:
            query: 当前问题
            query_plan: 查询计划
            cube_schema: Cube 定义
            examples: 少样本示例

        Returns:
            格式化的 Prompt
        """
        # 构建示例部分
        examples_text = ""
        if examples:
            for i, ex in enumerate(examples[:3], 1):
                examples_text += f"""
## 示例 {i}
**问题**: {ex.get('original_question', '')}
**DSL**:
```json
{json.dumps(ex.get('dsl_json', {}), ensure_ascii=False, indent=2)}
```
"""

        # 构建 Cube 定义部分
        cube_def_text = self._format_cube_schema(cube_schema)

        # 构建完整 Prompt
        prompt = f"""
# 参考案例
{examples_text if examples_text else "暂无参考案例"}

# 当前任务

**用户问题**: {query}

**查询计划**:
```json
{json.dumps(query_plan, ensure_ascii=False, indent=2)}
```

# 可用的语义层定义
{cube_def_text}

# 要求
请参考上述案例，为当前问题生成符合语义层规范的 DSL JSON。

输出格式 (JSON):
```json
{{
    "cube": "CubeName",
    "measures": ["measure1", "measure2"],
    "dimensions": ["dimension1"],
    "filters": [{{"member": "field", "operator": "equals", "values": ["value"]}}],
    "timeDimension": "created_at",
    "granularity": "day"
}}
```

请直接输出 JSON，不要包含其他说明文字。
"""
        return prompt

    def _format_cube_schema(self, cube_schema: Dict[str, Any]) -> str:
        """格式化 Cube 定义"""
        lines = []
        for cube_name, cube_def in cube_schema.items():
            lines.append(f"\n### {cube_name}")
            lines.append(f"**度量**: {', '.join(cube_def.get('measures', []))}")
            lines.append(f"**维度**: {', '.join(cube_def.get('dimensions', []))}")
        return "\n".join(lines)
