# -*- coding: utf-8 -*-
"""
API v2 端点包
============

包含所有 AgentV2 (DeepAgents) 的 API 端点。

作者: BMad Master
版本: 2.0.0
"""

from .query_v2 import router as query_router

__all__ = ["query_router"]
