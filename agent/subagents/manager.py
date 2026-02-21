# -*- coding: utf-8 -*-
"""Subagent registry and lifecycle helpers."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .config import (
    SubAgentConfig,
    create_chart_expert_subagent,
    create_file_expert_subagent,
    create_sql_expert_subagent,
)


class SubAgentManager:
    """Registry for reusable subagent profiles."""

    def __init__(self, default_model: str = "deepseek-chat") -> None:
        self.default_model = default_model
        self._subagents: Dict[str, SubAgentConfig] = {}

    def register_subagent(self, config: SubAgentConfig) -> None:
        self._subagents[config.name] = config

    def get_subagent(self, name: str) -> Optional[SubAgentConfig]:
        return self._subagents.get(name)

    def list_subagents(self) -> List[str]:
        return list(self._subagents.keys())

    def _register_if_tools(
        self,
        *,
        tools: Optional[List[Any]],
        config_factory: Callable[[], SubAgentConfig],
    ) -> None:
        if tools:
            self.register_subagent(config_factory())

    def _default_config_specs(
        self,
        *,
        postgres_tools: Optional[List[Any]],
        echarts_tools: Optional[List[Any]],
        file_tools: Optional[List[Any]],
    ) -> List[tuple[Optional[List[Any]], Callable[[], SubAgentConfig]]]:
        return [
            (
                postgres_tools,
                lambda: create_sql_expert_subagent(
                    postgres_tools=postgres_tools or [],
                    model=self.default_model,
                ),
            ),
            (
                echarts_tools,
                lambda: create_chart_expert_subagent(
                    echarts_tools=echarts_tools or [],
                    model=self.default_model,
                ),
            ),
            (
                file_tools,
                lambda: create_file_expert_subagent(
                    file_tools=file_tools or [],
                    model=self.default_model,
                ),
            ),
        ]

    def create_default_subagents(
        self,
        postgres_tools: Optional[List[Any]] = None,
        echarts_tools: Optional[List[Any]] = None,
        file_tools: Optional[List[Any]] = None,
    ) -> None:
        for tools, config_factory in self._default_config_specs(
            postgres_tools=postgres_tools,
            echarts_tools=echarts_tools,
            file_tools=file_tools,
        ):
            self._register_if_tools(tools=tools, config_factory=config_factory)


def create_subagent_manager(default_model: str = "deepseek-chat") -> SubAgentManager:
    """Create a subagent manager with default model binding."""
    return SubAgentManager(default_model=default_model)


__all__ = [
    "SubAgentManager",
    "create_subagent_manager",
]
