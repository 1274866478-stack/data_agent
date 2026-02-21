"""Agent helpers for query domain."""

from importlib import import_module

from .path_extractor import resolve_file_path_with_fallback, extract_file_path_from_config
from .tools import (
    list_available_tables,
    get_table_schema,
    execute_sql_safe,
    sanitize_sql,
    validate_sql_safety,
    validate_time_aggregation_sql,
)
from .data_transformer import convert_simple_chart_to_echarts, extract_simple_charts_from_text

_optional_modules = [
    import_module('.models', __name__),
    import_module('.data_validator', __name__),
    import_module('.response_formatter', __name__),
]

__all__ = [
    'resolve_file_path_with_fallback',
    'extract_file_path_from_config',
    'list_available_tables',
    'get_table_schema',
    'execute_sql_safe',
    'sanitize_sql',
    'validate_sql_safety',
    'validate_time_aggregation_sql',
    'convert_simple_chart_to_echarts',
    'extract_simple_charts_from_text',
]

for _module in _optional_modules:
    for _name in dir(_module):
        if not _name.startswith('_') and _name not in __all__:
            __all__.append(_name)


def __getattr__(name: str):
    for _module in _optional_modules:
        if hasattr(_module, name):
            return getattr(_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
