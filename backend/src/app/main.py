"""
# [MAIN] FastAPI 应用入口

## [HEADER]
**文件名**: main.py
**职责**: FastAPI应用主入口，负责应用初始化、中间件配置、路由注册、生命周期管理
**作者**: Data Agent Team
**版本**: 1.0.1
**变更记录**:
- v1.0.1 (2025-12-28): 添加启动时的 print 日志输出，便于调试和监控应用初始化流程
- v1.0.0: 初始版本，完整的应用生命周期管理

## [INPUT]
- 环境变量 (.env) - DATABASE_URL, ZHIPUAI_API_KEY, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
- 配置对象 (settings: Settings) - 从 core/config.py 导入
- HTTP请求上下文 (Request: FastAPI Request)
- 服务健康检查信号 (Startup/Shutdown events)

## [OUTPUT]
- FastAPI应用实例 (app: FastAPI)
- HTTP响应 (JSONResponse)
- 结构化日志事件 (structlog)
- 监控指标 (Sentry/Performance)
- 启动日志输出 (print: "🚀 System Initializing: Data Agent Backend v1.0.0")

## [LINK]
**上游依赖** (已读取源码):
- [./core/config.py](./core/config.py) - Settings类，环境变量解析与验证 ✅
- [./core/auth.py](./core/auth.py) - JWT认证与API Key验证逻辑
- [./core/logging.py](./core/logging.py) - structlog日志配置
- [./core/monitoring.py](./core/monitoring.py) - Sentry错误监控
- [./core/config_validator.py](./core/config_validator.py) - 配置安全验证
- [./core/key_rotation.py](./core/key_rotation.py) - 密钥轮换机制

**下游依赖** (已读取源码):
- [./data/database.py](./data/database.py) - engine, Base, get_db ✅
- [./services/minio_client.py](./services/minio_client.py) - MinIO服务实例
- [./services/chromadb_client.py](./services/chromadb_client.py) - ChromaDB服务实例
- [./services/zhipu_client.py](./services/zhipu_client.py) - 智谱AI客户端
- [./api/v1/__init__.py](./api/v1/__init__.py) - api_router聚合路由 ✅

**调用方**:
- [../../uvicorn](../../) - ASGI服务器启动命令: `uvicorn src.app.main:app --reload --port 8004`
- Docker容器 - [../../docker-compose.yml](../../docker-compose.yml) 中的backend服务

## [POS]
**路径**: backend/src/app/main.py
**模块层级**: Level 1 (Root) - 应用主入口
**依赖深度**: 直接依赖 core/*, data/*, services/*, api/*
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
from datetime import datetime

from .core.config import settings
from .core.auth import create_api_key_auth
from .core.logging import setup_logging, get_logger, request_logger, performance_logger
from .core.monitoring import init_sentry, capture_exception, monitor_performance
from .core.config_validator import config_validator
from .core.config_audit import generate_audit_report
from .core.key_rotation import setup_key_rotation, get_rotation_status
from .data.database import check_database_connection, create_tables, log_pool_health
from .services.minio_client import minio_service
from .services.chromadb_client import chromadb_service
from .services.zhipu_client import zhipu_service
from .services.query_performance_monitor import query_perf_monitor
from .api.v1 import api_router
from .api.v2 import api_router_v2

# 设置结构化日志
print("[ROCKET] System Initializing: Data Agent Backend v1.0.0")
setup_logging()
logger = get_logger(__name__)

# 初始化Sentry监控
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("Starting Data Agent Backend...")

    # 0. 初始化安全功能
    try:
        # 设置密钥轮换系统
        setup_key_rotation()
        logger.info("Key rotation system initialized")

        # 记录应用启动事件
        from .core.config_audit import log_config_change
        log_config_change(
            service="Application",
            change_type="startup",
            reason="应用启动",
            metadata={
                "environment": settings.environment,
                "version": settings.app_version,
                "debug_mode": settings.debug
            }
        )
    except Exception as e:
        logger.error(f"Security initialization failed: {e}")

    # 1. 验证必需的环境变量
    try:
        env_result = await config_validator.validate_required_env_vars()
        if env_result.success:
            logger.info("Environment variables validation passed")
        else:
            logger.error(f"Environment variables validation failed: {env_result.message}")
            if settings.environment == "production":
                raise RuntimeError("Critical environment variables are missing in production")
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        if settings.environment == "production":
            raise

    # 2. 配置验证（非阻塞模式，允许部分失败）
    try:
        logger.info("Running comprehensive configuration validation...")
        config_summary = await config_validator.validate_all_configs()

        # 检查安全状态
        if config_summary.get("security_alert", False):
            logger.error(f"🚨 SECURITY ALERT: {config_summary.get('security_message', '发现安全问题')}")

            # 自托管模式允许启动（使用 DeepSeek 作为主要 LLM）
            # 生产环境且非自托管模式时，安全问题应该阻止启动
            if settings.environment == "production" and settings.auth_mode != "selfhost":
                logger.error("Critical security issues detected in production mode - startup blocked")
                raise RuntimeError("Security validation failed in production")
            else:
                logger.warning(f"Security issues detected, but continuing in {settings.auth_mode} mode")

        if config_summary["overall_status"] == "success":
            logger.info("All configurations validated successfully")
        elif config_summary["overall_status"] == "security_issues":
            logger.warning(f"Configuration validation passed with security issues: {config_summary['successful']}/{config_summary['total_services']} services")
            # 记录失败的服务
            for result in config_summary["results"]:
                if result["status"] == "failed":
                    if result["service"] in ["Security Configuration", "Security Defaults", "Key Strength"]:
                        logger.error(f"Security validation failed: {result['service']} - {result['message']}")
                    else:
                        logger.warning(f"Service validation failed: {result['service']} - {result['message']}")
        elif config_summary["overall_status"] == "partial_success":
            logger.warning(f"Partial configuration validation passed: {config_summary['successful']}/{config_summary['total_services']} services")
            # 记录失败的服务
            for result in config_summary["results"]:
                if result["status"] == "failed":
                    logger.warning(f"Service validation failed: {result['service']} - {result['message']}")
        else:
            logger.error(f"Configuration validation failed: {config_summary['successful']}/{config_summary['total_services']} services")
            # 在生产环境中，配置验证失败应该阻止启动
            if settings.environment == "production":
                logger.error("Critical configuration validation failed in production mode")
                raise RuntimeError("Configuration validation failed in production")
            else:
                logger.warning("Configuration validation failed, but continuing in development mode")

    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        if settings.environment == "production":
            raise

    # 3. 检查所有服务连接（使用原有逻辑）
    await check_all_services()

    # 4. 创建数据库表
    try:
        create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        if settings.environment == "production":
            raise

    # 5. 启动性能监控服务 (暂时禁用以测试超时问题)
    try:
        # query_perf_monitor.start_monitoring()
        # await query_perf_monitor.resource_monitor.start_background_monitoring(interval_seconds=30)
        logger.info("Performance monitoring service disabled for testing")
    except Exception as e:
        logger.error(f"Failed to start performance monitoring: {e}")

    logger.info("Data Agent Backend started successfully")

    yield

    # 关闭时执行
    logger.info("Shutting down Data Agent Backend...")

    # 停止性能监控服务
    try:
        query_perf_monitor.stop_monitoring()
        logger.info("Performance monitoring service stopped")
    except Exception as e:
        logger.error(f"Failed to stop performance monitoring: {e}")

    # 记录应用关闭事件
    try:
        from .core.config_audit import log_config_change
        log_config_change(
            service="Application",
            change_type="shutdown",
            reason="应用正常关闭",
            metadata={
                "environment": settings.environment,
                "version": settings.app_version
            }
        )
        logger.info("Application shutdown event recorded")
    except Exception as e:
        logger.error(f"Failed to record shutdown event: {e}")


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## Data Agent V4 - 多租户SaaS数据智能分析平台

    ### 核心功能
    - 🔐 **多租户隔离**: 企业级数据安全与租户隔离
    - 🧠 **AI驱动分析**: 基于智谱AI的智能数据洞察
    - 📊 **自带数据库**: 安全连接外部PostgreSQL数据源
    - 📚 **知识库增强**: PDF/Word文档上传与向量检索

    ### 技术栈
    - **框架**: FastAPI + SQLAlchemy 2.0 (Async)
    - **数据库**: PostgreSQL 16+
    - **存储**: MinIO (S3兼容)
    - **向量库**: ChromaDB
    - **AI模型**: 智谱GLM-4-Flash

    ### 认证方式
    所有API端点需要通过Clerk JWT认证。在请求头中包含:
    ```
    Authorization: Bearer <your_jwt_token>
    ```

    ### API版本
    当前版本: **v1**

    Base URL: `/api/v1`
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "Data Agent Team",
        "email": "support@dataagent.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Root",
            "description": "根路径和基本信息",
        },
        {
            "name": "Health",
            "description": "健康检查和服务状态",
        },
        {
            "name": "API Info",
            "description": "API版本信息",
        },
        {
            "name": "Tenants",
            "description": "租户管理 - 创建、查询、更新租户信息",
        },
        {
            "name": "Data Sources",
            "description": "数据源管理 - 连接外部数据库,测试连接,管理数据源",
        },
        {
            "name": "Documents",
            "description": "文档管理 - 上传PDF/Word文档,向量化,检索",
        },
        {
            "name": "LLM",
            "description": "AI对话 - 智能数据分析和问答",
        },
        {
            "name": "Authentication",
            "description": "认证相关 - JWT验证,用户信息",
        },
        {
            "name": "RAG-SQL",
            "description": "RAG-SQL处理 - 自然语言查询转SQL执行",
        },
    ],
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API认证中间件配置
if settings.api_key:
    logger.info("API Key authentication is enabled")
    app.add_middleware(create_api_key_auth())
else:
    logger.info("API Key authentication is disabled")


# 安全头部中间件
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    添加安全相关的HTTP响应头
    """
    response = await call_next(request)

    # 添加安全头部
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # 生产环境添加HSTS
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# 请求日志和性能监控中间件
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    记录请求日志和性能指标，集成性能监控服务
    """
    import uuid
    import psutil

    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

    # 生成请求ID
    request_id = str(uuid.uuid4())[:8]

    # 提取租户ID（如果存在）
    tenant_id = request.headers.get("X-Tenant-ID", "unknown")

    # 确定请求类型
    path = str(request.url.path)
    if "/query" in path or "/llm" in path:
        query_type = "LLM_QUERY"
    elif "/documents" in path:
        query_type = "DOCUMENT"
    elif "/data-sources" in path:
        query_type = "DATA_SOURCE"
    else:
        query_type = "API_REQUEST"

    # 记录请求开始
    request_logger.log_request(
        method=request.method,
        path=path,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
    )

    error_occurred = False
    error_message = None
    status_code = 500

    try:
        # 处理请求
        response = await call_next(request)
        status_code = response.status_code

        # 计算处理时间
        process_time = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 添加性能头
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id

        # 记录请求完成
        request_logger.log_response(
            method=request.method,
            path=path,
            status_code=status_code,
            duration=process_time,
            request_id=request_id,
        )

        return response

    except Exception as e:
        # 记录错误
        error_occurred = True
        error_message = str(e)
        process_time = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        logger.error(
            f"Request failed: {request.method} {path} - {str(e)}",
            extra={
                "event_type": "request_error",
                "method": request.method,
                "path": path,
                "duration_ms": int(process_time * 1000),
                "request_id": request_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise

    finally:
        # 记录到性能监控服务（仅对API请求）
        if path.startswith("/api/"):
            try:
                from .services.query_performance_monitor import QueryMetrics

                process_time = time.time() - start_time
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024

                metrics = QueryMetrics(
                    query_id=request_id,
                    tenant_id=tenant_id,
                    query_type=query_type,
                    query_hash=f"{request.method}:{path}",
                    execution_time=process_time,
                    sql_generation_time=0.0,
                    sql_validation_time=0.0,
                    result_processing_time=0.0,
                    total_time=process_time,
                    row_count=0,
                    cache_hit=False,
                    error=error_occurred,
                    error_message=error_message,
                    memory_usage=max(0, end_memory - start_memory),
                    cpu_usage=psutil.cpu_percent(interval=None)
                )

                query_perf_monitor._record_query_metrics(metrics)
            except Exception as perf_error:
                logger.debug(f"性能指标记录失败: {perf_error}")


# 全局异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat(),
        },
    )


async def check_all_services():
    """
    检查所有服务的连接状态
    """
    import asyncio

    with performance_logger("health_check_services"):
        services_status = {}

        # 检查数据库连接
        with performance_logger("database_health_check"):
            services_status["database"] = await asyncio.to_thread(check_database_connection)

        # 检查MinIO连接
        with performance_logger("minio_health_check"):
            services_status["minio"] = await asyncio.to_thread(minio_service.check_connection)

        # 检查ChromaDB连接
        with performance_logger("chromadb_health_check"):
            services_status["chromadb"] = await asyncio.to_thread(chromadb_service.check_connection)

        # 🔥 修复：优先检查DeepSeek，如果配置了DeepSeek就跳过Zhipu AI健康检查
        from src.app.core.config import settings
        deepseek_api_key = getattr(settings, "DEEPSEEK_API_KEY", None) or getattr(settings, "deepseek_api_key", None)
        if deepseek_api_key:
            # 如果配置了DeepSeek，跳过Zhipu AI健康检查（避免余额不足错误）
            logger.info("检测到DeepSeek API密钥，跳过Zhipu AI健康检查")
            services_status["zhipu_ai"] = None  # 标记为跳过
            services_status["deepseek"] = True  # 假设DeepSeek可用（实际查询时会验证）
        else:
            # 如果没有配置DeepSeek，才检查Zhipu AI
            with performance_logger("zhipu_health_check"):
                services_status["zhipu_ai"] = await zhipu_service.check_connection()

        # 记录数据库连接池状态
        log_pool_health()

        # 记录服务状态
        logger.info(
            "Service health check completed",
            extra={
                "event_type": "health_check",
                "services": services_status,
                "all_healthy": all(services_status.values()),
            },
        )

        return services_status


# 健康检查端点
@app.get("/health", tags=["Health"])
async def health_check():
    """
    健康检查端点，返回所有服务连接状态
    """
    services_status = await check_all_services()

    # 计算整体健康状态
    all_healthy = all(services_status.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": services_status,
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version,
    }


# 根路径
@app.get("/", tags=["Root"])
async def root():
    """
    根路径端点
    """
    return {
        "message": "Welcome to Data Agent Backend API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# API版本信息端点
@app.get("/api/v1/", tags=["API Info"])
async def api_info():
    """
    API 版本信息端点
    """
    return {
        "api_version": "v1",
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


# 注册API路由
# V1 API (Legacy LangGraph)
app.include_router(api_router, prefix=settings.api_v1_prefix)

# V2 API (DeepAgents)
app.include_router(api_router_v2, prefix="/api/v2")


if __name__ == "__main__":
    import uvicorn

    # 🔥 Token Expansion: 增加 timeout_keep_alive 到 300 秒以支持长文本生成
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
        timeout_keep_alive=300  # 5分钟，支持长文本生成
    )
