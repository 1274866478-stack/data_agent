"""
Reasoning domain facade.
"""

from .service import (
    reasoning_engine,
    QueryType,
    ReasoningMode,
    QueryAnalysis,
    ReasoningResult,
    conversation_manager,
    ConversationState,
    usage_monitoring_service,
    ProviderType,
    UsageType,
)

from .reasoning_service import (
    ReasoningStep,
    ReasoningSource,
    ReasoningEngine,
    reasoning_engine as reasoning_engine_impl,
    fusion_engine,
    FusionResult,
    ConflictInfo,
    xai_service,
)

__all__ = [
    "reasoning_engine",
    "QueryType",
    "ReasoningMode",
    "QueryAnalysis",
    "ReasoningResult",
    "conversation_manager",
    "ConversationState",
    "usage_monitoring_service",
    "ProviderType",
    "UsageType",
    "ReasoningStep",
    "ReasoningSource",
    "reasoning_engine_impl",
    "fusion_engine",
    "FusionResult",
    "ConflictInfo",
    "xai_service",
]
