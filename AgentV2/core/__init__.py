# -*- coding: utf-8 -*-
"""
AgentV2 Core Module
==================

DeepAgents-based data analysis agent core.

Exports:
    - AgentFactory: Factory for creating DeepAgents instances
    - create_agent: Convenience function for quick agent creation
    - ResponseCache: Agent response caching
"""

from .agent_factory import AgentFactory as AgentFactoryV1
from .agent_factory_v2 import AgentFactory, create_agent, get_default_factory
from .response_cache import ResponseCache, get_response_cache, get_cache_stats

__all__ = [
    "AgentFactory",
    "AgentFactoryV1",
    "create_agent",
    "get_default_factory",
    "ResponseCache",
    "get_response_cache",
    "get_cache_stats",
]
