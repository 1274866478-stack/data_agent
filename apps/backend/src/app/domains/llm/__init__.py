"""
LLM domain facade.
"""

from .service import llm_service, LLMProvider, LLMMessage, LLMResponse, LLMStreamChunk
from .prompts import generate_database_aware_system_prompt, generate_sql_fix_prompt_with_db_type
from .multimodal import multimodal_processor
from .sql_error_memory import SQLErrorMemoryService, get_sql_error_memory_service
from .prompt_generator import (
    generate_database_aware_system_prompt as generate_database_aware_system_prompt_impl,
    generate_sql_fix_prompt_with_db_type as generate_sql_fix_prompt_with_db_type_impl,
)

__all__ = [
    "llm_service",
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "LLMStreamChunk",
    "generate_database_aware_system_prompt",
    "generate_sql_fix_prompt_with_db_type",
    "multimodal_processor",
    "SQLErrorMemoryService",
    "get_sql_error_memory_service",
    "generate_database_aware_system_prompt_impl",
    "generate_sql_fix_prompt_with_db_type_impl",
]
