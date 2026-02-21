# -*- coding: utf-8 -*-
"""
Cube query execution gateway for Agent.

This module isolates all Cube execution details so orchestration code
(`swarm_graph`) only handles control flow.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

import httpx

from .backend_runtime import import_first_available

logger = logging.getLogger(__name__)
_backend_cube_service: Any = None
_backend_cube_service_checked = False
_backend_cube_service_lock = threading.Lock()
CUBE_SERVICE_MODULE_CANDIDATES = [
    "app.integrations.cube.service",
    "app.services.semantic_layer.cube_service",
    "src.app.integrations.cube.service",
    "src.app.services.semantic_layer.cube_service",
]
OPTIONAL_QUERY_KEYS = ("limit", "offset", "order")


def _load_cube_service_class():
    module = import_first_available(
        CUBE_SERVICE_MODULE_CANDIDATES,
        required_attrs=("CubeService",),
    )
    return getattr(module, "CubeService")


def _create_backend_cube_service():
    """
    Try to build backend CubeService from current backend package layout.
    Returns None when backend package is unavailable in the runtime.
    """
    global _backend_cube_service, _backend_cube_service_checked

    if _backend_cube_service_checked:
        return _backend_cube_service

    with _backend_cube_service_lock:
        if _backend_cube_service_checked:
            return _backend_cube_service

        try:
            cube_service_cls = _load_cube_service_class()
            _backend_cube_service = cube_service_cls()
        except Exception as exc:
            logger.debug("Failed to initialize backend CubeService: %s", exc)
            _backend_cube_service = None

        _backend_cube_service_checked = True
        return _backend_cube_service


def _build_cube_query(
    *,
    dsl_json: Dict[str, Any],
    cube_name: str,
    tenant_id: Optional[str],
) -> Dict[str, Any]:
    query: Dict[str, Any] = {
        "measures": dsl_json.get("measures", []),
    }

    dimensions = dsl_json.get("dimensions", [])
    if dimensions:
        query["dimensions"] = dimensions

    time_dimension = dsl_json.get("timeDimension")
    if time_dimension:
        query["timeDimensions"] = [
            {
                "dimension": time_dimension,
                "granularity": dsl_json.get("granularity", "day"),
            }
        ]

    all_filters = _merge_filters(
        cube_name=cube_name,
        tenant_id=tenant_id,
        raw_filters=dsl_json.get("filters"),
    )

    if all_filters:
        query["filters"] = all_filters

    _copy_optional_query_keys(query=query, dsl_json=dsl_json)

    return query


def _merge_filters(
    *,
    cube_name: str,
    tenant_id: Optional[str],
    raw_filters: Any,
) -> list[Dict[str, Any]]:
    filters: list[Dict[str, Any]] = []
    if tenant_id:
        filters.append(
            {
                "member": f"{cube_name}.tenant_id",
                "operator": "equals",
                "values": [tenant_id],
            }
        )
    if isinstance(raw_filters, list):
        filters.extend(raw_filters)
    return filters


def _copy_optional_query_keys(
    *,
    query: Dict[str, Any],
    dsl_json: Dict[str, Any],
) -> None:
    for key in OPTIONAL_QUERY_KEYS:
        value = dsl_json.get(key)
        if value is not None:
            query[key] = value


async def _execute_cube_api_query(query: Dict[str, Any]) -> Dict[str, Any]:
    cube_api_url, cube_api_secret = _resolve_cube_api_config()
    headers = _build_cube_api_headers(cube_api_secret)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{cube_api_url}/cubejs-api/v1/load",
            json={"query": query},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def _resolve_cube_api_config() -> tuple[str, str]:
    cube_api_url = os.getenv("CUBE_API_URL", "http://cube:4000").rstrip("/")
    cube_api_secret = os.getenv("CUBE_API_SECRET") or os.getenv("CUBEJS_API_SECRET", "")
    return cube_api_url, cube_api_secret


def _build_cube_api_headers(cube_api_secret: str) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if cube_api_secret:
        headers["Authorization"] = f"Bearer {cube_api_secret}"
    return headers


async def execute_cube_query(
    *,
    dsl_json: Dict[str, Any],
    tenant_id: Optional[str],
) -> Dict[str, Any]:
    """
    Execute a semantic-layer query represented by DSL JSON.
    """
    cube_name = dsl_json.get("cube")
    if not cube_name:
        raise ValueError("DSL is missing cube name")

    cube_service = _create_backend_cube_service()
    if cube_service:
        service_kwargs = _build_cube_service_kwargs(
            dsl_json=dsl_json,
            cube_name=cube_name,
            tenant_id=tenant_id,
        )
        return await cube_service.execute_query(
            **service_kwargs,
        )

    query = _build_cube_query(
        dsl_json=dsl_json,
        cube_name=cube_name,
        tenant_id=tenant_id,
    )
    return await _execute_cube_api_query(query)


def _build_cube_service_kwargs(
    *,
    dsl_json: Dict[str, Any],
    cube_name: str,
    tenant_id: Optional[str],
) -> Dict[str, Any]:
    return {
        "cube_name": cube_name,
        "measures": dsl_json.get("measures", []),
        "dimensions": dsl_json.get("dimensions", []),
        "filters": dsl_json.get("filters", []),
        "time_dimension": dsl_json.get("timeDimension"),
        "granularity": dsl_json.get("granularity"),
        "tenant_id": tenant_id,
    }
