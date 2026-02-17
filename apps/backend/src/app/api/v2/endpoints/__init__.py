# -*- coding: utf-8 -*-
"""
API v2 端点包
============

包含所有 AgentV2 (DeepAgents) 的 API 端点。

作者: BMad Master
版本: 2.0.0
"""

from .query_v2 import router as query_router

# 暂时禁用 query_stream_v2，因为文件有编码损坏问题
# from .query_stream_v2 import router as query_stream_router

__all__ = ["query_router"]  # 暂时只导出 query_router
