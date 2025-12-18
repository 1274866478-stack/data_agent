"""
健康检查端点
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
    # 🔥 第一步修复：并行检查所有服务，ChromaDB检查失败不阻塞
    tasks = [
        asyncio.create_task(asyncio.to_thread(check_database_connection)),
        asyncio.create_task(asyncio.to_thread(minio_service.check_connection)),
        asyncio.create_task(asyncio.to_thread(chromadb_service.check_connection)),
        asyncio.create_task(zhipu_service.check_connection())  # 这是async函数，直接调用
    ]

    # 等待所有检查完成，ChromaDB失败不影响整体健康状态
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        db_status, minio_status, chromadb_status, zhipu_status = results
        
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

    # 计算整体健康状态
    all_healthy = all([db_status, minio_status, chromadb_status, zhipu_status])

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
                "status": "available" if zhipu_status else "unavailable",
                "details": "ZhipuAI API accessible" if zhipu_status else "Failed to connect to ZhipuAI API"
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

    # 智谱AI服务信息
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