"""
# [ENDPOINTS] API端点模块初始化

## [HEADER]
**文件名**: __init__.py
**职责**: 组织和导出API v1端点模块 - 作为API端点模块的入口点，管理和注册所有API路由
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - Endpoints模块初始化

## [INPUT]
- **所有端点模块**: 从各个端点文件（health.py, tenants.py, data_sources.py等）导入APIRouter

## [OUTPUT]
### API路由组织
- **APIRouter聚合**: 所有端点的APIRouter实例
- **路由注册**: 在../__init__.py中注册到主API路由器
- **模块组织**: 按功能分类组织端点文件

### 端点分类
- **健康检查**: health.py - /health, /ping, /database, /services
- **租户管理**: tenants.py - /tenants
- **数据源管理**: data_sources.py - /data-sources
- **文档管理**: documents.py - /documents
- **查询服务**: query.py - /query
- **LLM服务**: llm.py - /llm
- **配置管理**: config.py - /config
- **安全**: security.py - /security
- **性能监控**: performance.py, performance_enhanced.py, performance_monitoring.py
- **RAG服务**: rag.py
- **推理**: reasoning.py, reasoning_fix.py
- **文件上传**: upload.py, file_upload.py
- **测试**: test.py

## [LINK]
**上游依赖** (已读取源码):
- [./health.py](./health.py) - 健康检查端点
- [./tenants.py](./tenants.py) - 租户管理端点
- [./data_sources.py](./data_sources.py) - 数据源管理端点
- [./documents.py](./documents.py) - 文档管理端点
- [./query.py](./query.py) - 查询服务端点
- [./llm.py](./llm.py) - LLM服务端点
- [./config.py](./config.py) - 配置管理端点
- [./security.py](./security.py) - 安全端点
- [./performance.py](./performance.py) - 性能监控端点
- [./rag.py](./rag.py) - RAG服务端点
- [./reasoning.py](./reasoning.py) - 推理端点
- [./upload.py](./upload.py) - 文件上传端点
- [./test.py](./test.py) - 测试端点

**下游依赖** (已读取源码):
- [../__init__.py](../__init__.py) - API v1模块（导入并注册所有endpoint routers）
- [../../../main.py](../../../main.py) - FastAPI应用（注册API v1路由器）

**调用方**:
- **FastAPI应用**: 通过app.include_router()注册所有端点路由
- **API客户端**: 通过HTTP请求访问各个端点
- **API文档**: FastAPI自动生成OpenAPI文档

## [POS]
**路径**: backend/src/app/api/v1/endpoints/__init__.py
**模块层级**: Level 4（Backend → src/app → api/v1 → endpoints）
**依赖深度**: 直接依赖多个端点文件
"""

# 此文件作为endpoints模块的标记，不需要导入任何内容
# 所有API路由通过../__init__.py统一管理和注册
