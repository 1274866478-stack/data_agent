from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Sequence

import yaml

from .base_agent import AgentState, BaseAgent

logger = logging.getLogger(__name__)

Issue = Dict[str, str]
RuleConfig = Dict[str, Any]


class CriticAgent(BaseAgent):
    """Validate generated DSL against schema and business rules."""

    def __init__(
        self,
        name: str = "critic",
        llm: Any = None,
        rules_path: str | None = None,
    ) -> None:
        super().__init__(name, llm)
        self.business_rules: List[RuleConfig] = self._load_rules(rules_path)

    async def execute(self, state: AgentState) -> AgentState:
        dsl_json = state.get("dsl_json", {})
        cube_schema = state.get("cube_schema", {})
        query = state.get("query", "")

        validation_result = await self._validate_dsl(dsl_json, cube_schema, query)
        return {
            "critic_report": validation_result,
            "needs_regeneration": not validation_result["valid"],
        }

    async def _validate_dsl(
        self,
        dsl_json: Dict[str, Any],
        cube_schema: Dict[str, Any],
        query: str,
    ) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[Issue] = []
        suggestions: List[str] = []

        if "error" in dsl_json:
            return {
                "valid": False,
                "errors": [str(dsl_json["error"])],
                "warnings": [],
                "suggestions": [],
                "score": 0.0,
            }

        cube_name = dsl_json.get("cube")
        if not cube_name:
            errors.append("DSL is missing required field: cube")
        elif cube_name not in cube_schema:
            available = list(cube_schema.keys())
            errors.append(f"Cube '{cube_name}' does not exist. Available cubes: {available}")

        if cube_name and cube_name in cube_schema:
            available_measures = cube_schema.get(cube_name, {}).get("measures", [])
            errors.extend(
                self._validate_members_exist(
                    members=dsl_json.get("measures", []),
                    available_members=available_measures,
                    member_label="Measure",
                    cube_name=cube_name,
                )
            )

            available_dimensions = cube_schema.get(cube_name, {}).get("dimensions", [])
            errors.extend(
                self._validate_members_exist(
                    members=dsl_json.get("dimensions", []),
                    available_members=available_dimensions,
                    member_label="Dimension",
                    cube_name=cube_name,
                )
            )

        warnings.extend(self._check_business_rules(dsl_json, query))
        warnings.extend(self._check_best_practices(dsl_json))

        score = self._calculate_score(errors, warnings)
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "score": score,
        }

    def _load_rules(self, rules_path: str | None = None) -> List[RuleConfig]:
        path = Path(rules_path) if rules_path else self._resolve_default_rules_path()
        if path is None or not path.exists():
            return []

        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning("Failed to load business rules from %s: %s", path, exc)
            return []

        rules = payload.get("rules", [])
        if isinstance(rules, list):
            return [rule for rule in rules if isinstance(rule, dict)]
        return []

    def _resolve_default_rules_path(self) -> Path | None:
        candidate = Path(__file__).resolve().parents[1] / "rules" / "business_rules.yaml"
        return candidate if candidate.exists() else None

    def _check_business_rules(self, dsl_json: Dict[str, Any], query: str) -> List[Issue]:
        _ = query
        warnings: List[Issue] = []
        dsl_text = str(dsl_json).lower()
        dsl_repr = str(dsl_json)

        for rule in self.business_rules:
            rule_name = str(rule.get("name", ""))
            pattern = rule.get("pattern")
            if pattern and str(pattern).lower() in dsl_text:
                warnings.append(
                    self._build_issue(
                        rule=rule_name,
                        issue=str(rule.get("error_message", "Business rule violation")),
                        suggestion=str(rule.get("suggestion", "")),
                    )
                )

            field = rule.get("field")
            validation = rule.get("validation")
            if field and validation and str(field) in dsl_repr:
                warnings.append(
                    self._build_issue(
                        rule=rule_name,
                        issue=f"Field '{field}' requires validation: {validation}",
                        suggestion=str(rule.get("suggestion", "")),
                    )
                )

        return warnings

    def _check_best_practices(self, dsl_json: Dict[str, Any]) -> List[Issue]:
        warnings: List[Issue] = []

        if not dsl_json.get("timeDimension") and not dsl_json.get("dimensions"):
            warnings.append(
                self._build_issue(
                    rule="best_practice",
                    issue="No time dimension is set; aggregations may be less useful.",
                    suggestion="Add a time dimension for clearer analysis.",
                )
            )

        measures = dsl_json.get("measures", [])
        if isinstance(measures, list) and len(measures) > 5:
            warnings.append(
                self._build_issue(
                    rule="best_practice",
                    issue=f"Too many measures selected ({len(measures)}).",
                    suggestion="Split the request into smaller queries.",
                )
            )

        limit = dsl_json.get("limit")
        if isinstance(limit, int) and limit > 1000:
            warnings.append(
                self._build_issue(
                    rule="best_practice",
                    issue=f"Large row limit ({limit}) may hurt performance.",
                    suggestion="Use a smaller limit or paginate.",
                )
            )

        return warnings

    def _calculate_score(self, errors: Sequence[str], warnings: Sequence[Issue]) -> float:
        score = 1.0
        score -= len(errors) * 0.5
        score -= len(warnings) * 0.1
        return max(0.0, min(1.0, score))

    @staticmethod
    def _split_member_name(member: Any) -> str:
        if not isinstance(member, str):
            return str(member)
        return member.split(".")[-1] if "." in member else member

    @staticmethod
    def _build_issue(*, rule: str, issue: str, suggestion: str) -> Issue:
        return {
            "rule": rule,
            "issue": issue,
            "suggestion": suggestion,
        }

    @staticmethod
    def _validate_members_exist(
        *,
        members: Any,
        available_members: Any,
        member_label: str,
        cube_name: str,
    ) -> List[str]:
        if not isinstance(members, list) or not isinstance(available_members, list):
            return []

        errors: List[str] = []
        for member in members:
            member_name = CriticAgent._split_member_name(member)
            if member_name not in available_members:
                errors.append(
                    f"{member_label} '{member}' does not exist in cube '{cube_name}'"
                )
        return errors


def load_default_rules() -> List[RuleConfig]:
    """Built-in fallback business rules when external yaml is missing."""
    return [
        {
            "name": "dau_must_use_distinct",
            "description": "DAU should use DISTINCT user count.",
            "pattern": "count(user_id)",
            "error_message": "DAU must use count(DISTINCT user_id)",
            "suggestion": "Use unique_users style measure.",
        },
        {
            "name": "revenue_filter_valid_range",
            "description": "Revenue filters should not allow negative values.",
            "field": "amount",
            "validation": "value >= 0",
            "error_message": "Invalid amount filter range.",
            "suggestion": "Check amount range bounds.",
        },
        {
            "name": "time_range_not_too_wide",
            "description": "Time range should stay within practical limits.",
            "check_type": "time_dimension",
            "max_days": 365,
            "error_message": "Time range is too large.",
            "suggestion": "Narrow the window or use pre-aggregation.",
        },
        {
            "name": "join_path_predefined",
            "description": "Use semantic-layer predefined joins.",
            "check_type": "multi_table",
            "error_message": "Avoid ad-hoc joins outside semantic definitions.",
            "suggestion": "Use semantic-layer join definitions.",
        },
    ]
