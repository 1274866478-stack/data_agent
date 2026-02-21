from __future__ import annotations

"""Generator agent for turning query plans into semantic-layer DSL payloads."""

import json
from typing import Any, Dict, List, Optional

from .base_agent import AgentState, BaseAgent


class GeneratorAgent(BaseAgent):
    """Generate semantic-layer DSL JSON from planning output."""
    RANKING_KEYWORDS = ["排名", "top", "排行"]
    TIME_DIMENSION_TOKENS = ["time", "date", "created", "updated", "时间", "日期"]

    def __init__(self, name: str = "generator", llm: Any = None) -> None:
        super().__init__(name, llm)

    @staticmethod
    def _normalize_cube_filters(
        *,
        cube_name: str,
        filters: Any,
    ) -> List[Dict[str, Any]]:
        if not isinstance(filters, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in filters:
            normalized_filter = GeneratorAgent._to_cube_filter(cube_name, item)
            if normalized_filter is None:
                continue
            normalized.append(normalized_filter)
        return normalized

    @staticmethod
    def _to_cube_filter(cube_name: str, item: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None
        member = item.get("member")
        operator = item.get("operator")
        values = item.get("values")
        if not member or not operator or not isinstance(values, list):
            return None
        return {
            "member": f"{cube_name}.{member}",
            "operator": operator,
            "values": values,
        }

    async def execute(self, state: AgentState) -> AgentState:
        query_plan = state.get("query_plan", {})
        cube_schema = state.get("cube_schema", {})
        query = state.get("query", "")
        few_shot_examples = state.get("few_shot_examples", [])

        dsl_json = await self._generate_dsl(
            query=query,
            query_plan=query_plan,
            cube_schema=cube_schema,
            few_shot_examples=few_shot_examples,
        )
        return {"dsl_json": dsl_json}

    async def _generate_dsl(
        self,
        query: str,
        query_plan: Dict[str, Any],
        cube_schema: Dict[str, Any],
        few_shot_examples: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        _ = few_shot_examples
        target_cubes = query_plan.get("target_cubes", [])
        if not target_cubes:
            return self._create_error_dsl("No target cube identified")

        cube_name = target_cubes[0]
        dsl: Dict[str, Any] = {
            "cube": cube_name,
            "measures": query_plan.get("required_measures", []),
            "dimensions": query_plan.get("required_dimensions", []),
        }

        time_requirements = query_plan.get("time_requirements", {})
        if time_requirements.get("has_time_filter"):
            time_dimension = self._find_time_dimension(cube_name, cube_schema)
            if time_dimension:
                dsl["timeDimension"] = time_dimension
                dsl["granularity"] = time_requirements.get("granularity", "day")

        cube_filters = self._normalize_cube_filters(
            cube_name=cube_name,
            filters=query_plan.get("filters", []),
        )
        if cube_filters:
            dsl["filters"] = cube_filters

        if self._has_ranking_intent(query):
            dsl["order"] = [{f"{cube_name}.created_at": "desc"}]
            dsl["limit"] = 10

        return dsl

    def _has_ranking_intent(self, query: str) -> bool:
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.RANKING_KEYWORDS)

    def _find_time_dimension(
        self,
        cube_name: str,
        cube_schema: Dict[str, Any],
    ) -> Optional[str]:
        if cube_name not in cube_schema:
            return None

        dimensions = cube_schema[cube_name].get("dimensions", [])
        for dimension in dimensions:
            dimension_lower = str(dimension).lower()
            if any(token in dimension_lower for token in self.TIME_DIMENSION_TOKENS):
                return f"{cube_name}.{dimension}"

        return None

    def _create_error_dsl(self, error_message: str) -> Dict[str, Any]:
        return {
            "error": error_message,
            "cube": None,
            "measures": [],
            "dimensions": [],
        }

    async def generate_with_llm(self, prompt: str) -> Dict[str, Any]:
        if not self.llm:
            return {"error": "LLM is not configured"}

        try:
            response = await self.llm.ainvoke(prompt)
            return {"llm_response": str(response)}
        except Exception as exc:
            return {"error": f"LLM generation failed: {exc}"}

    def build_prompt_with_examples(
        self,
        query: str,
        query_plan: Dict[str, Any],
        cube_schema: Dict[str, Any],
        examples: List[Dict[str, Any]] | None = None,
    ) -> str:
        example_sections: List[str] = []
        for index, example in enumerate((examples or [])[:3], start=1):
            example_sections.append(
                f"\n## Example {index}\n"
                f"Question: {example.get('original_question', '')}\n"
                "DSL:\n"
                f"{json.dumps(example.get('dsl_json', {}), ensure_ascii=False, indent=2)}\n"
            )
        examples_text = "".join(example_sections)

        cube_def_text = self.format_cube_schema(cube_schema)
        prompt = (
            "Generate semantic-layer DSL JSON for the following user request.\n\n"
            f"Examples:\n{examples_text or 'No examples available.'}\n\n"
            f"Query: {query}\n\n"
            "Query plan:\n"
            f"{json.dumps(query_plan, ensure_ascii=False, indent=2)}\n\n"
            f"Available schema:\n{cube_def_text}\n\n"
            "Return JSON only."
        )
        return prompt
