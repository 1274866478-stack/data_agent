from __future__ import annotations

"""Base class and shared types for subagents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

AgentState = Dict[str, Any]


class BaseAgent(ABC):
    """Abstract base contract for all subagents."""

    def __init__(self, name: str, llm: Any = None) -> None:
        self.name = name
        self.llm = llm

    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the agent with current workflow state."""
        raise NotImplementedError

    def _build_prompt(self, template: str, **kwargs: Any) -> str:
        return template.format(**kwargs)

    @staticmethod
    def format_cube_schema(cube_schema: Dict[str, Any]) -> str:
        lines: List[str] = []
        for cube_name, cube_def in cube_schema.items():
            measures = ", ".join(cube_def.get("measures", []))
            dimensions = ", ".join(cube_def.get("dimensions", []))
            lines.append(f"- {cube_name}: measures=[{measures}] dimensions=[{dimensions}]")
        return "\n".join(lines)

    def get_name(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
