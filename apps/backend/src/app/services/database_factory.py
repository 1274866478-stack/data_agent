"""Compatibility re-export shim."""

from importlib import import_module

_target = import_module("src.app.integrations.db_adapters.database_factory")
__all__ = [name for name in dir(_target) if not name.startswith("_")]


def __getattr__(name: str):
    if name in __all__:
        return getattr(_target, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
