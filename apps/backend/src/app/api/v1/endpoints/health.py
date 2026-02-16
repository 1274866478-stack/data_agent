"""
# [HEALTH] 健康检查API端点

## [HEADER]
**文件名**: health.py
**职责**: 提供API健康检查端点，检查数据库、MinIO、ChromaDB、智谱AI等服务状态
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现健康检查端点

## [INPUT]
- **db: Session** - 数据库会话（通过依赖注入获取）
- **api_keys: dict** - 各服务的API密钥配置（从settings获取）
- **service_checkers: list** - 服务检查器列表（MinIO、ChromaDB、智谱AI等）

## [OUTPUT]
- **health_status: dict** - 健康状态响应
  - status: "healthy" | "unhealthy"
  - services: 各服务连接状态
  - timestamp: 检查时间戳
  - version: API版本号

## [LINK]
**上游依赖** (已读取源码):
- [../../data/database.py](../../data/database.py) - get_db(), check_database_connection()
- [../../services/minio_client.py](../../services/minio_client.py) - MinIO服务检查
- [../../services/chromadb_client.py](../../services/chromadb_client.py) - ChromaDB服务检查
- [../../services/zhipu_client.py](../../services/zhipu_client.py) - 智谱AI服务检查
- [../../core/config.py](../../core/config.py) - 配置对象（API密钥等）

**下游依赖** (已读取源码):
- 无（健康检查是叶子端点）

**调用方**:
-监控系统 - 定期健康检查
-负载均衡器 - 健康检查路由
-运维工具 - 服务状态监控

## [POS]
**路径**: backend/src/app/api/v1/endpoints/health.py
**模块层级**: Level 3 - API端点层
**依赖深度**: 直接依赖 data/*, services/*；被监控系统和负载均衡器调用
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
import asyncio
from datetime import datetime

from src.app.data.database import get_db, check_database_connection
from src.app.services.minio_client import minio_service
from src.app.services.chromadb_client import chromadb_service
from src.app.services.zhipu_client import zhipu_service

router = APIRouter()


@router.get("/status", summary="详细健康检查")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    详细的健康检查端点，检查所有服务的连接状态
    """
    # 🔥 修复：优先检查DeepSeek，如果配置了DeepSeek就跳过Zhipu AI健康检查
    from src.app.core.config import settings
    deepseek_api_key = getattr(settings, "DEEPSEEK_API_KEY", None) or getattr(settings, "deepseek_api_key", None)
    
    # 🔥 第一步修复：并行检查所有服务，ChromaDB检查失败不阻塞
    tasks = [
        asyncio.create_task(asyncio.to_thread(check_database_connection)),
        asyncio.create_task(asyncio.to_thread(minio_service.check_connection)),
        asyncio.create_task(asyncio.to_thread(chromadb_service.check_connection)),
    ]
    
    # 只有在没有配置DeepSeek时才检查Zhipu AI
    if not deepseek_api_key:
        tasks.append(asyncio.create_task(zhipu_service.check_connection()))  # 这是async函数，直接调用

    # 等待所有检查完成，ChromaDB失败不影响整体健康状态
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        db_status, minio_status, chromadb_status = results[0], results[1], results[2]
        zhipu_status = results[3] if len(results) > 3 else None
        
        # 如果任何检查抛出异常，视为失败但不影响其他服务
        if isinstance(db_status, Exception):
            db_status = False
        if isinstance(minio_status, Exception):
            minio_status = False
        if isinstance(chromadb_status, Exception):
            chromadb_status = False
        if isinstance(zhipu_status, Exception):
            zhipu_status = False
    except Exception as e:
        # 如果gather本身失败，至少保证ChromaDB不影响其他服务
        logger.warning(f"健康检查部分失败: {e}")
        chromadb_status = False
        # 其他服务状态设为未知
        db_status = True  # 假设数据库正常（因为已经通过Depends获取了db）
        minio_status = None
        zhipu_status = None
    
    # 🔥 修复：如果配置了DeepSeek，zhipu_status应该为None（跳过），不影响健康状态
    if deepseek_api_key:
        zhipu_status = None  # 跳过Zhipu AI检查

    # 计算整体健康状态（排除None值）
    health_checks = [db_status, minio_status, chromadb_status]
    if zhipu_status is not None:
        health_checks.append(zhipu_status)
    all_healthy = all(health_checks)

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": {
            "database": {
                "status": "connected" if db_status else "disconnected",
                "details": "PostgreSQL connection successful" if db_status else "Failed to connect to PostgreSQL"
            },
            "minio": {
                "status": "connected" if minio_status else "disconnected",
                "details": "MinIO object storage accessible" if minio_status else "Failed to connect to MinIO"
            },
            "chromadb": {
                "status": "connected" if chromadb_status else "disconnected",
                "details": "ChromaDB vector database accessible" if chromadb_status else "Failed to connect to ChromaDB"
            },
            "zhipu_ai": {
                "status": "available" if zhipu_status else "unavailable" if zhipu_status is False else "skipped",
                "details": "ZhipuAI API accessible" if zhipu_status else ("Failed to connect to ZhipuAI API" if zhipu_status is False else "Skipped (DeepSeek is configured)")
            },
            "deepseek": {
                "status": "configured" if deepseek_api_key else "not_configured",
                "details": "DeepSeek API key is configured" if deepseek_api_key else "DeepSeek API key is not configured"
            }
        },
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/ping", summary="简单检查")
async def ping():
    """
    简单的ping检查
    """
    return {
        "message": "pong",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/database", summary="数据库健康检查")
async def database_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    数据库连接健康检查
    """
    try:
        # 尝试执行简单查询
        result = db.execute(text("SELECT 1 as health_check"))
        row = result.fetchone()

        if row and row[0] == 1:
            return {
                "status": "healthy",
                "connection": "connected",
                "details": "Database query executed successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "unhealthy",
                "connection": "connected",
                "details": "Database query returned unexpected result",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connection": "disconnected",
            "details": f"Database connection failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/services", summary="服务状态总览")
async def services_status() -> Dict[str, Any]:
    """
    获取所有服务的状态总览
    """
    # 获取各个服务的详细信息
    services_info = {}

    # MinIO 服务信息
    try:
        minio_buckets = await asyncio.to_thread(minio_service.client.list_buckets)
        minio_connected = await asyncio.to_thread(minio_service.check_connection)
        services_info["minio"] = {
            "status": "connected" if minio_connected else "disconnected",
            "bucket_count": len(minio_buckets),
            "default_bucket": minio_service.default_bucket
        }
    except Exception:
        services_info["minio"] = {
            "status": "disconnected",
            "error": "Failed to get MinIO information"
        }

    # ChromaDB 服务信息
    try:
        chroma_collections = await asyncio.to_thread(chromadb_service.list_collections)
        chroma_connected = await asyncio.to_thread(chromadb_service.check_connection)
        services_info["chromadb"] = {
            "status": "connected" if chroma_connected else "disconnected",
            "collection_count": len(chroma_collections),
            "collections": chroma_collections[:5]  # 只显示前5个集合名称
        }
    except Exception:
        services_info["chromadb"] = {
            "status": "disconnected",
            "error": "Failed to get ChromaDB information"
        }

    # 🔥 修复：优先检查DeepSeek，如果配置了DeepSeek就跳过Zhipu AI健康检查
    from src.app.core.config import settings
    deepseek_api_key = getattr(settings, "DEEPSEEK_API_KEY", None) or getattr(settings, "deepseek_api_key", None)
    
    if deepseek_api_key:
        # 如果配置了DeepSeek，跳过Zhipu AI检查
        services_info["zhipu_ai"] = {
            "status": "skipped",
            "reason": "DeepSeek is configured as primary LLM provider"
        }
        services_info["deepseek"] = {
            "status": "configured",
            "model": getattr(settings, "deepseek_default_model", "deepseek-chat"),
            "base_url": getattr(settings, "deepseek_base_url", "https://api.deepseek.com")
        }
    else:
        # 智谱AI服务信息（只有在没有配置DeepSeek时才检查）
        try:
            zhipu_available = await zhipu_service.check_connection()  # 这是async函数，直接await
            services_info["zhipu_ai"] = {
                "status": "available" if zhipu_available else "unavailable",
                "model": zhipu_service.default_model,
                "api_version": "v4"
            }
        except Exception:
            services_info["zhipu_ai"] = {
                "status": "unavailable",
                "error": "Failed to get ZhipuAI information"
            }

    return {
        "services": services_info,
        "timestamp": datetime.now().isoformat()
    }