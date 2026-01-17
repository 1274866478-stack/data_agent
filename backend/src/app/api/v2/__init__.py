# -*- coding: utf-8 -*-
"""
API v2 版本路由包
======================

基于 AgentV2 (DeepAgents) 的新版 API 端点。

特性:
    - 租户隔离
    - SQL 安全验证
    - SubAgent 委派
    - 可解释性日志
    - 错误追踪

作者: BMad Master
版本: 2.0.0
"""

from fastapi import APIRouter
from .endpoints import query_v2, query_stream_v2

# 创建API v2路由器
api_router_v2 = APIRouter()

# 注册各个端点路由
api_router_v2.include_router(query_v2.router, tags=["Query V2"])
api_router_v2.include_router(query_stream_v2.router, tags=["Query V2 Stream"])

__all__ = ["api_router_v2"]
