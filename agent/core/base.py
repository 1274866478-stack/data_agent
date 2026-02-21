# -*- coding: utf-8 -*-
"""Core agent interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict


class IAgent(ABC):
    """Minimal async contract for agent runtime implementations."""

    @abstractmethod
    async def query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a non-streaming query."""

    @abstractmethod
    async def stream_query(self, query: str, context: Dict[str, Any]) -> AsyncIterator[str]:
        """Execute a streaming query."""

    @abstractmethod
    async def reset(self) -> None:
        """Reset agent runtime state."""

