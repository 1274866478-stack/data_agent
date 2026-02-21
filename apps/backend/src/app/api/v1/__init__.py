"""
API v1 版本路由包
"""

from fastapi import APIRouter
from .endpoints import health, tenants, documents, data_sources, config, llm, auth, upload, reasoning, file_upload
# from .endpoints import performance_monitoring  # 已删除 - 性能监控已禁用
from .endpoints import sql_error_memories
from .endpoints import logs
# 暂时禁用security端点，因为编码问题
# from .endpoints import security
# 启用query端点，Agent集成已完成
from .endpoints import query

# 创建API路由器
api_router = APIRouter()

# 注册各个端点路由
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(data_sources.router, prefix="/data-sources", tags=["Data Sources"])

# 新增配置验证端点
api_router.include_router(config.router, prefix="/config", tags=["Configuration"])

# 新增安全配置和审计端点 - 暂时禁用
# api_router.include_router(security.router, prefix="/security", tags=["Security"])

# 新增LLM服务端点
api_router.include_router(llm.router, tags=["LLM"])

# 新增认证端点
api_router.include_router(auth.router, tags=["Authentication"])

# 新增分块上传端点
api_router.include_router(upload.router, prefix="/upload", tags=["Chunked Upload"])

# 新增文件上传端点 - 数据源文件上传
api_router.include_router(file_upload.router, prefix="/file-upload", tags=["File Upload"])

# 新增推理服务端点 - Story 3.4
api_router.include_router(reasoning.router, tags=["Reasoning"])

# 新增查询端点 - Story 3.1 - Agent集成已完成，已启用
api_router.include_router(query.router, tags=["Query"])

# 新增性能监控端点 - Story 3.2 Enhancement (已删除 - 性能监控已禁用)
# api_router.include_router(performance_monitoring.router, prefix="/performance", tags=["Performance Monitoring"])

# 新增SQL错误记忆端点 - SQL Error Learning System
api_router.include_router(sql_error_memories.router, prefix="/sql-error-memories", tags=["SQL Error Memories"])

# 新增前端日志接收端点 - 全量埋点
api_router.include_router(logs.router, prefix="/logs", tags=["Logging"])
