# -*- coding: utf-8 -*-
"""
AgentV2 Core Module
==================

DeepAgents-based data analysis agent core.

Exports:
    - AgentFactory: Factory for creating DeepAgents instances
    - AgentFactoryV1: Legacy import alias (forwarded to AgentFactoryV2)
    - create_agent: Convenience function for quick agent creation
    - import_first_available: Backend module resolver helper
    - ResponseCache: Agent response caching
"""

from .agent_factory import AgentFactory as AgentFactoryV1
from .agent_factory_v2 import AgentFactory, create_agent, get_default_factory
from .backend_runtime import (
    ensure_backend_src_path,
    import_backend_module,
    import_first_available,
    run_async_sync,
)
from .base import IAgent
from .cube_executor import execute_cube_query
from .response_cache import ResponseCache, get_response_cache, get_cache_stats

__all__ = [
    "AgentFactory",
    "AgentFactoryV1",
    "create_agent",
    "get_default_factory",
    "IAgent",
    "ensure_backend_src_path",
    "import_backend_module",
    "import_first_available",
    "run_async_sync",
    "execute_cube_query",
    "ResponseCache",
    "get_response_cache",
    "get_cache_stats",
]
