"""Compatibility re-export shim for db adapters."""

from importlib import import_module

_modules = [
    import_module(".database_interface", __name__),
    import_module(".database_factory", __name__),
]

__all__ = []
for _module in _modules:
    __all__.extend(name for name in dir(_module) if not name.startswith("_"))

# Keep stable order while removing duplicates.
__all__ = list(dict.fromkeys(__all__))


def __getattr__(name: str):
    for _module in _modules:
        if hasattr(_module, name):
            return getattr(_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
