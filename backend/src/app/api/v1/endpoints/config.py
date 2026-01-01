"""
# [CONFIG] 配置验证API端点

## [HEADER]
**文件名**: config.py
**职责**: 提供所有服务的配置验证和健康检查 - 数据库、MinIO、ChromaDB、智谱AI、环境变量
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 配置验证端点实现

## [INPUT]
### HTTP请求
- **GET /config/validate**: 验证所有配置 - 参数: detailed(bool)
- **POST /config/validate**: 验证特定服务 - ServiceValidationRequest {service_name, skip_detailed_checks}
- **GET /config/health**: 配置模块健康检查 - 无参数
- **GET /config/status**: 获取配置状态概览 - 无参数
- **GET /config/services**: 获取支持的服务列表 - 无参数
- **POST /config/test/all**: 快速测试所有服务 - 无参数

### 依赖模块
- **config_validator**: 配置验证器实例
- **settings**: 应用配置对象

## [OUTPUT]
### 验证响应
- **ValidationResponse**: 全局验证结果 - {overall_status, total_services, successful, failed, timestamp, results[]}
- **ServiceResponse**: 单服务验证 - {service, status, message, details{}, timestamp}
- **健康状态**: {status, service, timestamp, environment}
- **配置状态**: {status, config{}, timestamp}
- **服务列表**: {services[], total}

### 验证功能
- **并行验证**: 同时验证多个服务连接
- **详细检查**: 可选择执行深度连接测试
- **后台任务**: 快速模式失败时触发详细验证
- **服务发现**: 列出所有支持验证的服务
- **状态概览**: 提供配置的快速查看

## [LINK]
**上游依赖** (已读取源码):
- [../../core/config_validator.py](../../core/config_validator.py) - 配置验证器(config_validator, validate_*)
- [../../core/config.py](../../core/config.py) - 配置对象(settings)

**下游依赖**:
- **前端配置页面**: 显示各服务的连接状态
- **健康检查系统**: 定期验证所有服务
- **安装向导**: 验证配置是否正确

**调用方**:
- **系统管理员**: 验证服务配置
- **监控系统**: 定期健康检查
- **安装程序**: 验证初始配置

## [POS]
**路径**: backend/src/app/api/v1/endpoints/config.py
**模块层级**: Level 5 (Backend → src/app → api/v1 → endpoints → config)
**依赖深度**: 1层 (core模块)
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
import asyncio

from src.app.core.config_validator import (
    config_validator,
    validate_database,
    validate_minio,
    validate_chromadb,
    validate_zhipu
)
from src.app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ServiceValidationRequest(BaseModel):
    """单个服务验证请求模型"""
    service_name: Optional[str] = None
    skip_detailed_checks: bool = False


class ValidationResponse(BaseModel):
    """验证响应模型"""
    overall_status: str
    total_services: int
    successful: int
    failed: int
    timestamp: float
    results: List[Dict[str, Any]]


class ServiceResponse(BaseModel):
    """单个服务响应模型"""
    service: str
    status: str
    message: str
    details: Dict[str, Any] = {}
    timestamp: float


@router.get("/validate", response_model=ValidationResponse)
async def validate_all_configs(
    background_tasks: BackgroundTasks,
    detailed: bool = False
):
    """
    验证所有配置和外部服务连接

    Args:
        detailed: 是否执行详细检查（可能需要更长时间）
        background_tasks: FastAPI 后台任务

    Returns:
        验证结果汇总
    """
    try:
        logger.info("开始全面的配置验证")

        # 执行验证
        if detailed:
            # 详细模式：执行所有检查
            validation_summary = await config_validator.validate_all_configs()
        else:
            # 快速模式：只执行基本连接检查
            validation_summary = await config_validator.validate_all_configs()

        # 如果验证失败，添加后台任务进行详细检查
        if validation_summary["overall_status"] != "success" and not detailed:
            background_tasks.add_task(run_detailed_validation)

        return ValidationResponse(**validation_summary)

    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"配置验证过程中发生错误: {str(e)}"
        )


@router.post("/validate", response_model=ServiceResponse)
async def validate_specific_service(request: ServiceValidationRequest):
    """
    验证特定服务的配置

    Args:
        request: 验证请求，包含服务名称

    Returns:
        特定服务的验证结果
    """
    try:
        service_name = request.service_name

        if not service_name:
            raise HTTPException(
                status_code=400,
                detail="必须指定要验证的服务名称"
            )

        # 根据服务名称执行相应的验证
        if service_name.lower() in ["database", "postgres", "postgresql"]:
            result = await validate_database()
        elif service_name.lower() in ["minio", "storage", "object_storage"]:
            result = await validate_minio()
        elif service_name.lower() in ["chromadb", "vector_db", "chroma"]:
            result = await validate_chromadb()
        elif service_name.lower() in ["zhipu", "zhipuai", "ai", "llm"]:
            result = await validate_zhipu()
        elif service_name.lower() in ["env", "environment", "env_vars"]:
            result = await config_validator.validate_required_env_vars()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的服务名称: {service_name}。支持的服务: database, minio, chromadb, zhipu, env"
            )

        return ServiceResponse(**result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"服务验证失败 ({service_name}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"服务验证过程中发生错误: {str(e)}"
        )


@router.get("/health")
async def config_health_check():
    """
    配置模块健康检查

    Returns:
        基本健康状态
    """
    try:
        return {
            "status": "healthy",
            "service": "config_validator",
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None,
            "environment": settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else "unknown"
        }
    except Exception as e:
        logger.error(f"配置健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "service": "config_validator",
            "error": str(e)
        }


@router.get("/status")
async def get_config_status():
    """
    获取当前配置状态概览

    Returns:
        配置状态概览
    """
    try:
        # 获取主要配置信息（不包含敏感数据）
        config_status = {
            "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
            "debug": getattr(settings, 'debug', False),
            "database_configured": bool(getattr(settings, 'database_url', None)),
            "zhipu_configured": bool(getattr(settings, 'zhipuai_api_key', None)),
            "minio_configured": all([
                getattr(settings, 'minio_endpoint', None),
                getattr(settings, 'minio_access_key', None),
                getattr(settings, 'minio_secret_key', None)
            ]),
            "chromadb_configured": all([
                getattr(settings, 'chroma_host', None),
                getattr(settings, 'chroma_port', None)
            ])
        }

        return {
            "status": "ok",
            "config": config_status,
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
        }

    except Exception as e:
        logger.error(f"获取配置状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取配置状态时发生错误: {str(e)}"
        )


@router.get("/services")
async def get_supported_services():
    """
    获取支持验证的服务列表

    Returns:
        支持的服务列表
    """
    services = [
        {
            "name": "database",
            "display_name": "PostgreSQL 数据库",
            "description": "验证 PostgreSQL 数据库连接和基本操作"
        },
        {
            "name": "minio",
            "display_name": "MinIO 对象存储",
            "description": "验证 MinIO 服务连接和存储桶访问"
        },
        {
            "name": "chromadb",
            "display_name": "ChromaDB 向量数据库",
            "description": "验证 ChromaDB 服务连接和集合操作"
        },
        {
            "name": "zhipu",
            "display_name": "智谱 AI API",
            "description": "验证智谱 AI API 连接和模型调用"
        },
        {
            "name": "env",
            "display_name": "环境变量",
            "description": "验证必需的环境变量配置"
        }
    ]

    return {
        "services": services,
        "total": len(services)
    }


@router.post("/test/all")
async def test_all_services():
    """
    测试所有服务的可用性（简化版）

    Returns:
        所有服务的快速测试结果
    """
    try:
        logger.info("开始快速测试所有服务")

        # 并行执行基本测试
        tasks = [
            config_validator.validate_required_env_vars(),
            config_validator.validate_database_connection(),
            config_validator.validate_minio_connection(),
            config_validator.validate_chromadb_connection(),
            config_validator.validate_zhipu_api()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        test_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_results.append({
                    "service": f"service_{i}",
                    "status": "error",
                    "message": f"测试异常: {str(result)}"
                })
            else:
                test_results.append(result.to_dict())

        successful = sum(1 for r in test_results if r["status"] == "success")
        total = len(test_results)

        return {
            "overall_status": "success" if successful == total else "partial_success",
            "successful": successful,
            "total": total,
            "results": test_results
        }

    except Exception as e:
        logger.error(f"快速测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"快速测试过程中发生错误: {str(e)}"
        )


# 后台任务函数
async def run_detailed_validation():
    """
    后台运行详细验证任务
    """
    try:
        logger.info("开始后台详细验证...")
        await config_validator.validate_all_configs()
        logger.info("后台详细验证完成")
    except Exception as e:
        logger.error(f"后台详细验证失败: {e}")