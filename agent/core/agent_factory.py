# -*- coding: utf-8 -*-
"""
Compatibility shim for legacy AgentFactory imports.

This module preserves the historical import path:
    `agent.core.agent_factory`

and forwards all behavior to AgentFactoryV2 so runtime stays AgentV2-only.
"""

from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.tools import BaseTool

from .agent_factory_v2 import (
    AgentFactory as AgentFactoryV2,
    create_agent as create_agent_v2,
    get_default_factory as get_default_factory_v2,
)


class AgentFactory(AgentFactoryV2):
    """
    Legacy-compatible facade over AgentFactoryV2.

    Supported legacy constructor args:
    - enable_filesystem
    - enable_subagents
    - enable_skills

    Unsupported legacy toggles are accepted but ignored.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        enable_filesystem: bool = True,  # kept for compatibility
        enable_subagents: bool = True,
        enable_skills: bool = True,  # kept for compatibility
        **kwargs: Any,
    ) -> None:
        # NOTE:
        # - `enable_filesystem` and `enable_skills` are legacy toggles from V1.
        # - AgentFactoryV2 middleware stack no longer uses those switches directly.
        _ = enable_filesystem
        _ = enable_skills
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_subagents=enable_subagents,
            **kwargs,
        )


def get_default_factory() -> AgentFactoryV2:
    """Return the global AgentFactoryV2 instance."""
    return get_default_factory_v2()


def create_agent(
    tenant_id: str = "default_tenant",
    tools: Optional[List[BaseTool]] = None,
    model: Optional[str] = None,
):
    """
    Legacy convenience wrapper.
    """
    return create_agent_v2(
        tenant_id=tenant_id,
        tools=tools,
        model=model,
    )


__all__ = [
    "AgentFactory",
    "create_agent",
    "get_default_factory",
]
