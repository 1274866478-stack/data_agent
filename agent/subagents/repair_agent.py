from __future__ import annotations

import copy
import json
import logging
import re
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .base_agent import AgentState, BaseAgent

logger = logging.getLogger(__name__)

PatternConfig = Dict[str, Any]


class RepairAgent(BaseAgent):
    """Repair invalid DSL payloads using rules or LLM fallback."""
    JSON_FENCE_PATTERN = re.compile(
        r"```json\s*(.*?)\s*```",
        flags=re.IGNORECASE | re.DOTALL,
    )
    ANY_FENCE_PATTERN = re.compile(
        r"```\s*(.*?)\s*```",
        flags=re.DOTALL,
    )
    JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", flags=re.DOTALL)
    MEMBER_NOT_FOUND_PATTERNS = {
        "Measure": r"Measure '(.+?)' not found",
        "Dimension": r"Dimension '(.+?)' not found",
    }
    MEMBER_FIELDS = {
        "Measure": "measures",
        "Dimension": "dimensions",
    }

    def __init__(
        self,
        name: str = "repair",
        llm: Any = None,
        error_patterns_path: str | None = None,
    ) -> None:
        super().__init__(name, llm)
        self.error_patterns: List[PatternConfig] = self._load_error_patterns(error_patterns_path)

    async def execute(self, state: AgentState) -> AgentState:
        dsl_json = state.get("dsl_json", {})
        error_message = state.get("error_message", "")
        cube_schema = state.get("cube_schema", {})
        tenant_id = state.get("tenant_id", "")

        working_dsl = copy.deepcopy(dsl_json) if isinstance(dsl_json, dict) else {}

        matched_pattern = self._match_error_pattern(error_message)
        historical_repairs = await self._find_similar_repairs(
            tenant_id=tenant_id,
            error_pattern=matched_pattern.get("name") if matched_pattern else None,
            original_dsl=working_dsl,
        )

        if matched_pattern and matched_pattern.get("auto_fix", False):
            repaired_dsl = await self._auto_repair(
                broken_dsl=working_dsl,
                error_message=error_message,
                pattern=matched_pattern,
                cube_schema=cube_schema,
                historical_repairs=historical_repairs,
            )
        else:
            repaired_dsl = await self._llm_repair(
                broken_dsl=working_dsl,
                error_message=error_message,
                cube_schema=cube_schema,
                historical_repairs=historical_repairs,
            )

        return {
            "dsl_json": repaired_dsl,
            "repair_attempted": True,
        }

    def _load_error_patterns(self, patterns_path: str | None = None) -> List[PatternConfig]:
        path = Path(patterns_path) if patterns_path else self._resolve_default_pattern_path()
        if path is None or not path.exists():
            return self._get_default_patterns()

        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning("Failed to load error patterns from %s: %s", path, exc)
            return self._get_default_patterns()

        patterns = payload.get("patterns", [])
        if isinstance(patterns, list):
            normalized = [item for item in patterns if isinstance(item, dict)]
            if normalized:
                return normalized
        return self._get_default_patterns()

    def _resolve_default_pattern_path(self) -> Path | None:
        agent_root = Path(__file__).resolve().parents[1]
        candidates = [
            agent_root / "self_healing" / "error_patterns.yaml",
            agent_root.parent / "self_healing" / "error_patterns.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _get_default_patterns(self) -> List[PatternConfig]:
        return [
            {
                "name": "measure_not_found",
                "description": "Measure does not exist.",
                "regex": r"Measure '(.+)' not found",
                "fix_strategy": "suggest_similar_measures",
                "auto_fix": True,
            },
            {
                "name": "dimension_not_found",
                "description": "Dimension does not exist.",
                "regex": r"Dimension '(.+)' not found",
                "fix_strategy": "suggest_similar_dimensions",
                "auto_fix": True,
            },
            {
                "name": "cube_not_found",
                "description": "Cube does not exist.",
                "regex": r"Cube '(.+)' does not exist",
                "fix_strategy": "list_available_cubes",
                "auto_fix": False,
            },
            {
                "name": "invalid_join",
                "description": "Join path is invalid.",
                "regex": r"Cannot join (.+) on (.+)",
                "fix_strategy": "use_precomputed_joins",
                "auto_fix": True,
            },
            {
                "name": "missing_filter",
                "description": "Required filter is missing.",
                "regex": r"Required filter missing: (.+)",
                "fix_strategy": "infer_from_context",
                "auto_fix": True,
            },
            {
                "name": "time_range_error",
                "description": "Time range is invalid.",
                "regex": r"Time range (.+) is invalid",
                "fix_strategy": "adjust_time_range",
                "auto_fix": True,
            },
            {
                "name": "aggregation_error",
                "description": "Aggregation expression is invalid.",
                "regex": r"Cannot aggregate (.+) with (.+)",
                "fix_strategy": "change_aggregation_type",
                "auto_fix": True,
            },
        ]

    def _match_error_pattern(self, error_message: str) -> Optional[PatternConfig]:
        if not error_message:
            return None

        for pattern in self.error_patterns:
            regex_pattern = pattern.get("regex")
            if not regex_pattern:
                continue
            try:
                if re.search(str(regex_pattern), error_message, re.IGNORECASE):
                    return pattern
            except re.error:
                continue

        return None

    async def _find_similar_repairs(
        self,
        tenant_id: str,
        error_pattern: str | None,
        original_dsl: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        _ = (tenant_id, error_pattern, original_dsl)
        return []

    async def _auto_repair(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        pattern: PatternConfig,
        cube_schema: Dict[str, Any],
        historical_repairs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        _ = historical_repairs
        strategy = pattern.get("fix_strategy")
        strategy_handlers = {
            "suggest_similar_measures": lambda: self._suggest_similar_measures(
                broken_dsl,
                error_message,
                cube_schema,
            ),
            "suggest_similar_dimensions": lambda: self._suggest_similar_dimensions(
                broken_dsl,
                error_message,
                cube_schema,
            ),
            "use_precomputed_joins": lambda: self._fix_join(broken_dsl, cube_schema),
            "infer_from_context": lambda: self._infer_missing_filter(broken_dsl, error_message),
            "adjust_time_range": lambda: self._adjust_time_range(broken_dsl, error_message),
            "change_aggregation_type": lambda: self._change_aggregation_type(
                broken_dsl,
                error_message,
                cube_schema,
            ),
        }
        handler = strategy_handlers.get(strategy)
        if handler:
            return await handler()
        return broken_dsl

    async def _suggest_similar_measures(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self._suggest_similar_members(
            broken_dsl=broken_dsl,
            error_message=error_message,
            cube_schema=cube_schema,
            member_kind="Measure",
        )

    async def _suggest_similar_dimensions(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self._suggest_similar_members(
            broken_dsl=broken_dsl,
            error_message=error_message,
            cube_schema=cube_schema,
            member_kind="Dimension",
        )

    async def _suggest_similar_members(
        self,
        *,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any],
        member_kind: str,
    ) -> Dict[str, Any]:
        field_name = self.MEMBER_FIELDS.get(member_kind)
        if not field_name:
            return broken_dsl

        missing_member = self._extract_missing_member_name(error_message, member_kind)
        if not missing_member:
            return broken_dsl

        cube_name = broken_dsl.get("cube")
        if not cube_name or cube_name not in cube_schema:
            return broken_dsl

        available = self._get_cube_members(cube_schema, cube_name, field_name)
        similar = get_close_matches(missing_member, available, n=3, cutoff=0.3)
        if not similar:
            return broken_dsl

        broken_dsl[field_name] = self._replace_member_values(
            broken_dsl.get(field_name, []),
            missing_member=missing_member,
            replacement=similar[0],
        )
        return broken_dsl

    async def _fix_join(
        self,
        broken_dsl: Dict[str, Any],
        cube_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        _ = cube_schema
        broken_dsl.pop("joins", None)
        return broken_dsl

    async def _infer_missing_filter(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
    ) -> Dict[str, Any]:
        _ = error_message
        filters = broken_dsl.get("filters", [])
        if not isinstance(filters, list):
            broken_dsl["filters"] = []
            return broken_dsl

        valid_filters = [
            item
            for item in filters
            if isinstance(item, dict) and isinstance(item.get("values"), list) and len(item["values"]) > 0
        ]
        broken_dsl["filters"] = valid_filters
        return broken_dsl

    async def _adjust_time_range(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
    ) -> Dict[str, Any]:
        _ = error_message
        broken_dsl.pop("timeDimension", None)
        broken_dsl.pop("granularity", None)
        return broken_dsl

    async def _change_aggregation_type(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        _ = error_message
        cube_name = broken_dsl.get("cube")
        if not cube_name or cube_name not in cube_schema:
            return broken_dsl

        available = self._get_cube_members(cube_schema, cube_name, "measures")
        if available:
            broken_dsl["measures"] = [available[0]]
        return broken_dsl

    @classmethod
    def _extract_missing_member_name(
        cls,
        error_message: str,
        member_kind: str,
    ) -> Optional[str]:
        pattern = cls.MEMBER_NOT_FOUND_PATTERNS.get(member_kind)
        if not pattern:
            return None
        match = re.search(pattern, error_message)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _get_cube_members(
        cube_schema: Dict[str, Any],
        cube_name: str,
        field_name: str,
    ) -> List[str]:
        cube_info = cube_schema.get(cube_name, {})
        raw_members = cube_info.get(field_name, [])
        if not isinstance(raw_members, list):
            return []
        return [str(member) for member in raw_members]

    @staticmethod
    def _replace_member_values(
        items: Any,
        *,
        missing_member: str,
        replacement: str,
    ) -> List[Any]:
        if not isinstance(items, list):
            return []
        return [
            replacement if item == missing_member or str(item).split(".")[-1] == missing_member else item
            for item in items
        ]

    async def _llm_repair(
        self,
        broken_dsl: Dict[str, Any],
        error_message: str,
        cube_schema: Dict[str, Any],
        historical_repairs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        _ = historical_repairs
        if not self.llm:
            return broken_dsl

        cube_def_text = self.format_cube_schema(cube_schema)
        prompt = (
            "The following DSL failed to execute. Repair it and return JSON only.\n\n"
            f"Error: {error_message}\n\n"
            f"Current DSL:\n{json.dumps(broken_dsl, ensure_ascii=False, indent=2)}\n\n"
            f"Available semantic schema:\n{cube_def_text}\n"
        )

        try:
            response = await self.llm.ainvoke(prompt)
            parsed = self._extract_json_response(str(response).strip())
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            logger.warning("LLM repair failed: %s", exc)

        return broken_dsl

    @staticmethod
    def _extract_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
        if not raw_text:
            return None

        for candidate in RepairAgent._candidate_json_blocks(raw_text):
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed

        return None

    @staticmethod
    def _candidate_json_blocks(raw_text: str) -> List[str]:
        candidates: List[str] = []
        candidates.extend(RepairAgent.JSON_FENCE_PATTERN.findall(raw_text))
        candidates.extend(RepairAgent.ANY_FENCE_PATTERN.findall(raw_text))
        candidates.append(raw_text)

        match = RepairAgent.JSON_OBJECT_PATTERN.search(raw_text)
        if match:
            candidates.append(match.group(0))

        unique_candidates: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            stripped = candidate.strip()
            if not stripped or stripped in seen:
                continue
            seen.add(stripped)
            unique_candidates.append(stripped)
        return unique_candidates
