# -*- coding: utf-8 -*-
"""
Backend runtime import helpers for Agent.

This module centralizes backend path discovery so Agent modules avoid
duplicated `sys.path` hacks and ad-hoc import fallbacks.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
import threading
from types import ModuleType
from pathlib import Path
from typing import Any, Optional, Sequence

logger = logging.getLogger(__name__)

_resolved_backend_src: Optional[Path] = None
_backend_resolution_failed = False
_backend_path_lock = threading.Lock()
_module_cache: dict[str, Any] = {}
_module_cache_lock = threading.Lock()


def _dedupe_paths(paths: Sequence[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _backend_src_candidates() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[2]
    candidates: list[Path] = []

    env_hint = os.getenv("BACKEND_SRC_PATH")
    if env_hint:
        candidates.append(Path(env_hint))

    # Docker compose backend container layout
    candidates.append(Path("/app/src"))

    # Local workspace layout
    candidates.append(repo_root / "apps" / "backend" / "src")

    # Legacy layout fallback
    candidates.append(repo_root / "backend" / "src")

    return _dedupe_paths(candidates)


def _module_has_required_attrs(module: ModuleType, required_attrs: Sequence[str]) -> bool:
    return all(hasattr(module, attr) for attr in required_attrs)


def ensure_backend_src_path() -> Optional[Path]:
    """
    Resolve backend src path and ensure it is importable.

    Returns:
        Resolved backend src path, or None when backend code is unavailable.
    """
    global _resolved_backend_src, _backend_resolution_failed

    if _resolved_backend_src is not None:
        return _resolved_backend_src
    if _backend_resolution_failed:
        return None

    with _backend_path_lock:
        if _resolved_backend_src is not None:
            return _resolved_backend_src
        if _backend_resolution_failed:
            return None

        for candidate in _backend_src_candidates():
            try:
                resolved = candidate.resolve()
            except Exception:
                continue
            if not resolved.exists() or not resolved.is_dir():
                continue

            resolved_str = str(resolved)
            if resolved_str not in sys.path:
                sys.path.insert(0, resolved_str)
                logger.debug("Added backend src to sys.path: %s", resolved_str)

            _resolved_backend_src = resolved
            return _resolved_backend_src

        _backend_resolution_failed = True
        logger.debug("No backend src path candidate found")
        return None


def import_backend_module(module_name: str) -> ModuleType:
    """
    Import module from backend package after ensuring backend src path.

    Raises:
        ImportError: when backend src is unavailable or module import fails.
    """
    backend_src = ensure_backend_src_path()
    if backend_src is None:
        raise ImportError("Backend src path is not available")

    with _module_cache_lock:
        cached = _module_cache.get(module_name)
        if cached is not None:
            return cached

    module = importlib.import_module(module_name)
    with _module_cache_lock:
        _module_cache[module_name] = module
    return module


def import_first_available(
    module_names: Sequence[str],
    *,
    required_attrs: Optional[Sequence[str]] = None,
) -> ModuleType:
    """
    Import the first backend module that exists and optionally exposes attrs.

    Args:
        module_names: Candidate module names ordered by preference.
        required_attrs: Optional attributes that must exist on module.

    Raises:
        ImportError: when no candidate can be imported with required attrs.
    """
    last_error: Optional[Exception] = None
    required = tuple(required_attrs or ())

    for module_name in module_names:
        try:
            module = import_backend_module(module_name)
        except Exception as exc:
            last_error = exc
            continue

        if required and not _module_has_required_attrs(module, required):
            logger.debug(
                "Backend module %s loaded but missing required attrs %s",
                module_name,
                required,
            )
            continue
        return module

    if required:
        raise ImportError(
            f"No backend module matched required attrs {required} from candidates: {module_names}"
        ) from last_error
    raise ImportError(
        f"No backend module import succeeded from candidates: {module_names}"
    ) from last_error


def _run_coro_in_isolated_thread(coro: Any, timeout_seconds: int) -> Any:
    result_container: list[Any] = []
    error_container: list[Exception] = []

    def _runner() -> None:
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result_container.append(loop.run_until_complete(coro))
        except Exception as exc:  # pragma: no cover - defensive path
            error_container.append(exc)
        finally:
            loop.close()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        raise TimeoutError(f"Async operation timed out after {timeout_seconds}s")
    if error_container:
        raise error_container[0]
    if not result_container:
        raise RuntimeError("Async operation completed without result")

    return result_container[0]


def run_async_sync(coro: Any, timeout_seconds: int = 15):
    """
    Run coroutine from sync code safely.

    - If no running loop exists in current thread: uses `asyncio.run`.
    - If a loop is already running: executes coroutine in a new daemon thread
      with an isolated event loop.
    """
    import asyncio

    try:
        running_loop = asyncio.get_running_loop()
        has_running_loop = running_loop.is_running()
    except RuntimeError:
        has_running_loop = False

    if not has_running_loop:
        return asyncio.run(coro)

    return _run_coro_in_isolated_thread(coro, timeout_seconds)
