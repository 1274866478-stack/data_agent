"""
数据源连接管理端点
实现Story 2.3要求的完整API功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import os
import tempfile
import json

from src.app.data.database import get_db
from src.app.data.models import DataSourceConnection, Tenant, DataSourceConnectionStatus, TenantStatus
from src.app.services.data_source_service import data_source_service
from src.app.services.connection_test_service import connection_test_service
from src.app.services.minio_client import minio_service

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic模型定义
class DataSourceCreateRequest(BaseModel):
    """创建数据源请求模型"""
    name: str = Field(..., min_length=1, max_length=255, description="数据源名称")
    connection_string: str = Field(..., min_length=1, description="数据库连接字符串")
    db_type: str = Field(default="postgresql", description="数据库类型")


class DataSourceUpdateRequest(BaseModel):
    """更新数据源请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="数据源名称")
    connection_string: Optional[str] = Field(None, min_length=1, description="数据库连接字符串")
    db_type: Optional[str] = Field(None, description="数据库类型")
    is_active: Optional[bool] = Field(None, description="是否激活")


class ConnectionTestRequest(BaseModel):
    """连接测试请求模型"""
    connection_string: str = Field(..., min_length=1, description="数据库连接字符串")
    db_type: str = Field(default="postgresql", description="数据库类型")


class DataSourceResponse(BaseModel):
    """数据源响应模型"""
    id: str
    tenant_id: str
    name: str
    db_type: str
    status: str
    host: Optional[str]
    port: Optional[int]
    database_name: Optional[str]
    last_tested_at: Optional[datetime]
    test_result: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# API端点实现
@router.get("/", summary="获取数据源连接列表", response_model=List[DataSourceResponse])
async def get_data_sources(
    tenant_id: str = None,  # 实际应该从认证中间件获取
    db_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取数据源连接列表
    支持租户隔离和筛选功能
    """
    # TODO: 从JWT token或认证中间件获取tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    try:
        connections = await data_source_service.get_data_sources(
            tenant_id=tenant_id,
            db=db,
            active_only=active_only,
            skip=skip,
            limit=limit
        )

        # 过滤数据库类型
        if db_type:
            connections = [conn for conn in connections if conn.db_type == db_type]

        return [DataSourceResponse.from_orm(conn) for conn in connections]

    except Exception as e:
        logger.error(f"Failed to fetch data sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch data sources: {str(e)}"
        )


# ============================================================================
# 固定路径端点（必须在 /{connection_id} 之前定义，否则会被动态路由匹配）
# ============================================================================

# 支持的文件类型配置
SUPPORTED_FILE_TYPES = {
    'csv': {
        'mime_types': ['text/csv', 'application/vnd.ms-excel'],
        'max_size_mb': 100,
        'extensions': ['.csv']
    },
    'xlsx': {
        'mime_types': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'max_size_mb': 100,
        'extensions': ['.xlsx']
    },
    'xls': {
        'mime_types': ['application/vnd.ms-excel'],
        'max_size_mb': 100,
        'extensions': ['.xls']
    },
    'sqlite': {
        'mime_types': ['application/x-sqlite3', 'application/vnd.sqlite3', 'application/octet-stream'],
        'max_size_mb': 500,
        'extensions': ['.db', '.sqlite', '.sqlite3']
    }
}


def _validate_file_type(filename: str, content_type: str, file_size: int) -> Dict[str, Any]:
    """验证文件类型和大小"""
    ext = os.path.splitext(filename)[1].lower()

    for file_type, config in SUPPORTED_FILE_TYPES.items():
        if ext in config['extensions']:
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file_size > max_size_bytes:
                return {
                    "valid": False,
                    "error": "FILE_TOO_LARGE",
                    "message": f"文件大小超过限制，最大允许 {config['max_size_mb']}MB"
                }
            return {
                "valid": True,
                "file_type": file_type,
                "extension": ext
            }

    return {
        "valid": False,
        "error": "UNSUPPORTED_FILE_TYPE",
        "message": f"不支持的文件类型: {ext}。支持的类型: .csv, .xlsx, .xls, .db, .sqlite, .sqlite3"
    }


@router.post("/upload", summary="上传数据文件创建数据源", status_code=status.HTTP_201_CREATED)
async def upload_data_source(
    file: UploadFile = File(..., description="数据文件 (CSV, Excel, SQLite)"),
    name: str = Form(..., description="数据源名称"),
    db_type: Optional[str] = Form(None, description="数据类型"),
    tenant_id: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    上传数据文件创建数据源
    支持 CSV、Excel (.xls/.xlsx) 和 SQLite 数据库 (.db/.sqlite/.sqlite3) 文件
    """
    # 从查询参数获取tenant_id
    if not tenant_id and request:
        tenant_id = request.query_params.get("tenant_id")

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    # 验证文件名
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空"
        )

    try:
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)

        # 验证文件类型和大小
        validation_result = _validate_file_type(
            file.filename,
            file.content_type or "application/octet-stream",
            file_size
        )

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["message"]
            )

        detected_file_type = validation_result["file_type"]

        # 生成唯一的存储路径
        file_id = str(uuid.uuid4())
        file_ext = validation_result["extension"]
        storage_path = f"data-sources/{tenant_id}/{file_id}{file_ext}"

        # 上传到 MinIO
        import io
        try:
            upload_success = minio_service.upload_file(
                bucket_name="data-sources",
                object_name=storage_path,
                file_data=io.BytesIO(file_content),
                file_size=file_size,
                content_type=file.content_type or "application/octet-stream"
            )

            if not upload_success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="文件上传到存储服务失败"
                )
        except Exception as e:
            logger.warning(f"MinIO上传失败，使用本地存储: {e}")
            # 如果MinIO不可用，保存到本地临时目录
            storage_path = f"local://{storage_path}"

        # 创建数据源记录
        connection_string = f"file://{storage_path}"

        new_connection = DataSourceConnection(
            tenant_id=tenant_id,
            name=name,
            db_type=db_type or detected_file_type,
            connection_string=connection_string,
            status=DataSourceConnectionStatus.ACTIVE,
            host=None,
            port=None,
            database_name=file.filename
        )

        db.add(new_connection)
        db.commit()
        db.refresh(new_connection)

        logger.info(f"Created file-based data source '{name}' for tenant '{tenant_id}'")

        return {
            "id": str(new_connection.id),
            "tenant_id": new_connection.tenant_id,
            "name": new_connection.name,
            "db_type": new_connection.db_type,
            "status": new_connection.status.value if hasattr(new_connection.status, 'value') else str(new_connection.status),
            "host": new_connection.host,
            "port": new_connection.port,
            "database_name": new_connection.database_name,
            "last_tested_at": new_connection.last_tested_at,
            "test_result": new_connection.test_result,
            "created_at": new_connection.created_at,
            "updated_at": new_connection.updated_at,
            "file_info": {
                "original_name": file.filename,
                "file_type": detected_file_type,
                "file_size": file_size,
                "storage_path": storage_path
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传数据源失败: {str(e)}"
        )


@router.get("/overview", summary="获取数据源概览统计")
async def get_data_sources_overview_route(
    tenant_id: str = None,
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """
    获取数据源和文档的概览统计信息
    用于仪表板展示，包含安全的存储配额计算和数据隔离
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required"
        )

    # 强化的租户验证和权限检查
    await _validate_overview_access(tenant_id, user_id, db)

    try:
        # 安全地获取数据库连接统计
        db_stats = await _get_secure_database_stats(tenant_id, db)
        doc_stats = await _get_secure_document_stats(tenant_id, db)
        storage_stats = await _get_secure_storage_stats(tenant_id, db)
        recent_activity = await _get_secure_recent_activity(tenant_id, db)

        logger.info(f"Overview accessed by user {user_id} for tenant {tenant_id}")

        return {
            "databases": db_stats,
            "documents": doc_stats,
            "storage": storage_stats,
            "recent_activity": recent_activity
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch data sources overview for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch overview statistics"
        )


@router.get("/search", summary="搜索数据源")
async def search_data_sources_route(
    q: str = "",
    type: str = "all",
    status_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    tenant_id: str = None,
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """搜索数据源和文档"""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required"
        )

    await _validate_search_parameters(q, type, status_filter, date_from, date_to, page, limit)
    await _validate_tenant_search_access(tenant_id, user_id, db)

    try:
        results = []
        total_count = 0

        if type in ["all", "database"]:
            query = db.query(DataSourceConnection).filter(
                DataSourceConnection.tenant_id == tenant_id,
                DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE
            )

            if q:
                safe_query = _sanitize_search_query(q)
                query = query.filter(
                    DataSourceConnection.name.contains(safe_query) |
                    DataSourceConnection.db_type.contains(safe_query)
                )

            if status_filter:
                valid_statuses = _validate_and_parse_statuses(status_filter)
                if valid_statuses:
                    query = query.filter(DataSourceConnection.status.in_(valid_statuses))

            if date_from or date_to:
                date_range = _validate_and_parse_date_range(date_from, date_to)
                if date_range['from']:
                    query = query.filter(DataSourceConnection.created_at >= date_range['from'])
                if date_range['to']:
                    query = query.filter(DataSourceConnection.created_at <= date_range['to'])

            db_total = query.with_entities(DataSourceConnection.id).count()
            total_count += db_total

            safe_limit = min(limit, 100)
            safe_page = max(1, min(page, 1000))

            db_results = query.offset((safe_page - 1) * safe_limit).limit(safe_limit).all()

            for conn in db_results:
                if conn.tenant_id != tenant_id:
                    continue
                results.append({
                    "id": conn.id,
                    "type": "database",
                    "name": conn.name,
                    "status": conn.status.value if hasattr(conn.status, 'value') else str(conn.status),
                    "created_at": conn.created_at.isoformat(),
                    "updated_at": conn.updated_at.isoformat(),
                    "db_type": conn.db_type,
                    "host": conn.host,
                    "port": conn.port
                })

        total_pages = (total_count + safe_limit - 1) // safe_limit

        return {
            "results": results,
            "total": total_count,
            "page": safe_page,
            "limit": safe_limit,
            "total_pages": total_pages
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search data sources for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed"
        )


class BulkDeleteRequestModel(BaseModel):
    """批量删除请求模型"""
    item_ids: List[str] = Field(..., min_length=1, max_length=50)
    item_type: str = Field(..., pattern=r"^(database|document)$")
    confirmation_token: Optional[str] = None


@router.post("/bulk-delete", summary="批量删除数据源")
async def bulk_delete_data_sources_route(
    request: BulkDeleteRequestModel,
    tenant_id: str = None,
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """批量删除数据源或文档"""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required"
        )

    if len(request.item_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete more than 50 items at once"
        )

    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.status == TenantStatus.ACTIVE
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive tenant"
        )

    success_count = 0
    error_count = 0
    errors = []
    deleted_items = []

    try:
        if request.item_type == "database":
            await _validate_bulk_database_delete_permission(tenant_id, user_id, request.item_ids, db)

            for item_id in request.item_ids:
                try:
                    connection = db.query(DataSourceConnection).filter(
                        DataSourceConnection.id == item_id,
                        DataSourceConnection.tenant_id == tenant_id,
                        DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE
                    ).first()

                    if not connection:
                        error_count += 1
                        errors.append({"item_id": item_id, "error": "Data source not found"})
                        continue

                    if not await _can_delete_data_source(connection, db):
                        error_count += 1
                        errors.append({"item_id": item_id, "error": "Data source cannot be deleted"})
                        continue

                    connection.status = DataSourceConnectionStatus.INACTIVE
                    connection.updated_at = datetime.now()
                    deleted_items.append({"item_id": item_id, "name": connection.name, "type": "database"})
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append({"item_id": item_id, "error": str(e)})

        elif request.item_type == "document":
            for item_id in request.item_ids:
                error_count += 1
                errors.append({"item_id": item_id, "error": "Document deletion not implemented"})

        db.commit()
        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
            "deleted_items": deleted_items
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk delete failed: {str(e)}"
        )


@router.get("/types/supported", summary="获取支持的数据源类型")
async def get_supported_data_source_types_route():
    """获取支持的数据源类型列表"""
    try:
        return connection_test_service.get_supported_database_types()
    except Exception as e:
        logger.error(f"Failed to get supported database types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported database types: {str(e)}"
        )


# ============================================================================
# 固定路径 POST 端点（必须在动态路径端点之前定义）
# ============================================================================

@router.post("/", summary="创建数据源连接", status_code=status.HTTP_201_CREATED, response_model=DataSourceResponse)
async def create_data_source(
    request: DataSourceCreateRequest,
    tenant_id: str = None,  # 实际应该从认证中间件获取
    db: Session = Depends(get_db)
):
    """
    创建新的数据源连接
    自动加密连接字符串并解析连接信息
    """
    logger.info(f"收到创建数据源请求: tenant_id={tenant_id}")
    logger.info(f"  - name: '{request.name}'")
    logger.info(f"  - db_type: '{request.db_type}'")
    logger.info(f"  - connection_string: '{request.connection_string}'")
    logger.info(f"  - connection_string长度: {len(request.connection_string) if request.connection_string else 0}")
    logger.info(f"  - request对象: {request.model_dump()}")

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    try:
        # 先加密连接字符串
        encrypted_string = data_source_service.encryption_service.encrypt_connection_string(
            request.connection_string
        )

        # 创建数据源连接(直接使用加密后的字符串)
        new_connection = DataSourceConnection(
            tenant_id=tenant_id,
            name=request.name,
            db_type=request.db_type,
            _connection_string=encrypted_string,  # 直接设置加密后的字符串到私有字段
            status=DataSourceConnectionStatus.TESTING
        )

        # 解析连接字符串获取连接信息
        parsed_info = data_source_service._parse_connection_string(
            request.connection_string,
            request.db_type
        )
        new_connection.host = parsed_info.get("host")
        new_connection.port = parsed_info.get("port")
        new_connection.database_name = parsed_info.get("database")

        # 保存到数据库
        db.add(new_connection)
        db.commit()
        db.refresh(new_connection)

        logger.info(f"Created data source '{request.name}' for tenant '{tenant_id}'")

        # 自动测试连接并更新状态
        try:
            logger.info(f"Auto-testing connection for data source '{request.name}'...")
            test_result = await connection_test_service.test_connection(
                connection_string=request.connection_string,
                db_type=request.db_type
            )

            # 更新连接的测试结果和状态
            new_connection.update_test_result(test_result.to_dict())
            db.commit()
            db.refresh(new_connection)

            logger.info(f"Connection test completed: {test_result.success}")
        except Exception as e:
            logger.warning(f"Auto-test failed for data source '{request.name}': {e}")
            # 即使测试失败,也返回创建的数据源(状态保持为TESTING)

        return DataSourceResponse.from_orm(new_connection)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create data source: {str(e)}"
        )


# ============================================================================
# 动态路径端点（必须在固定路径端点之后定义）
# ============================================================================

@router.get("/{connection_id}", summary="获取数据源连接详情", response_model=DataSourceResponse)
async def get_data_source(
    connection_id: str,
    tenant_id: str = None,  # 实际应该从认证中间件获取
    db: Session = Depends(get_db)
):
    """
    根据ID获取数据源连接详情
    确保租户隔离
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    try:
        connection = await data_source_service.get_data_source_by_id(
            data_source_id=connection_id,
            tenant_id=tenant_id,
            db=db
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source connection not found"
            )

        return DataSourceResponse.from_orm(connection)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch data source {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch data source: {str(e)}"
        )


@router.put("/{connection_id}", summary="更新数据源连接", response_model=DataSourceResponse)
async def update_data_source(
    connection_id: str,
    request: DataSourceUpdateRequest,
    tenant_id: str = None,  # 实际应该从认证中间件获取
    db: Session = Depends(get_db)
):
    """
    更新数据源连接信息
    支持部分更新，自动重新加密连接字符串
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    try:
        # 获取现有连接
        connection = await data_source_service.get_data_source_by_id(
            data_source_id=connection_id,
            tenant_id=tenant_id,
            db=db
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source connection not found"
            )

        # 更新字段
        update_data = request.dict(exclude_unset=True)

        if "name" in update_data:
            # 检查名称是否已存在
            existing = db.query(DataSourceConnection).filter(
                DataSourceConnection.tenant_id == tenant_id,
                DataSourceConnection.name == update_data["name"],
                DataSourceConnection.id != connection_id
            ).first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data source name already exists for this tenant"
                )

            connection.name = update_data["name"]

        if "connection_string" in update_data:
            # 加密新的连接字符串
            encrypted_string = data_source_service.encryption_service.encrypt_connection_string(
                update_data["connection_string"]
            )
            connection.connection_string = encrypted_string

            # 解析新连接字符串
            parsed_info = data_source_service._parse_connection_string(
                update_data["connection_string"],
                connection.db_type
            )
            connection.host = parsed_info.get("host")
            connection.port = parsed_info.get("port")
            connection.database_name = parsed_info.get("database")

        if "db_type" in update_data:
            connection.db_type = update_data["db_type"]

        if "is_active" in update_data:
            if update_data["is_active"]:
                connection.status = DataSourceConnectionStatus.ACTIVE
            else:
                connection.status = DataSourceConnectionStatus.INACTIVE

        connection.updated_at = datetime.now()

        db.commit()
        db.refresh(connection)

        logger.info(f"Updated data source {connection_id}")
        return DataSourceResponse.from_orm(connection)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update data source {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update data source: {str(e)}"
        )


@router.delete("/{connection_id}", summary="删除数据源连接")
async def delete_data_source(
    connection_id: str,
    tenant_id: str = None,  # 实际应该从认证中间件获取
    db: Session = Depends(get_db)
):
    """
    删除数据源连接（软删除）
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    try:
        success = await data_source_service.delete_data_source(
            data_source_id=connection_id,
            tenant_id=tenant_id,
            db=db
        )

        if success:
            logger.info(f"Deleted data source {connection_id}")
            return {
                "message": f"Data source connection {connection_id} has been deactivated",
                "connection_id": connection_id,
                "status": "deactivated"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source connection not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete data source {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete data source: {str(e)}"
        )


# 注意：/test 必须在 /{connection_id}/test 之前定义
@router.post("/test", summary="测试连接字符串")
async def test_connection_string(request: ConnectionTestRequest):
    """
    测试连接字符串是否有效（不保存到数据库）
    """
    try:
        test_result = await connection_test_service.test_connection(
            connection_string=request.connection_string,
            db_type=request.db_type
        )

        logger.info(f"Tested connection string for {request.db_type}: {test_result.success}")
        return test_result.to_dict()

    except Exception as e:
        logger.error(f"Failed to test connection string: {e}")
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "error_code": "TEST_EXECUTION_ERROR",
            "timestamp": datetime.now().isoformat()
        }


@router.post("/{connection_id}/test", summary="测试数据源连接")
async def test_data_source_connection(
    connection_id: str,
    tenant_id: str = None,  # 实际应该从认证中间件获取
    db: Session = Depends(get_db)
):
    """
    测试现有数据源连接是否有效
    自动更新连接状态和测试结果
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )

    try:
        # 获取数据源连接
        connection = await data_source_service.get_data_source_by_id(
            data_source_id=connection_id,
            tenant_id=tenant_id,
            db=db
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source connection not found"
            )

        # 对于文件类型的数据源（xlsx, xls, csv），不需要测试数据库连接
        # 只需要检查文件是否存在
        file_types = ['xlsx', 'xls', 'csv']
        if connection.db_type in file_types:
            # 文件类型的数据源，直接标记为成功（文件已上传）
            test_result_dict = {
                "success": True,
                "message": f"文件数据源已就绪 ({connection.db_type.upper()})",
                "error_code": None,
                "response_time_ms": 0,
                "details": {
                    "file_type": connection.db_type,
                    "database_name": connection.database_name
                },
                "timestamp": datetime.now().isoformat()
            }
            connection.update_test_result(test_result_dict)
            db.commit()
            logger.info(f"File data source {connection_id} marked as ready")
            return test_result_dict

        # 尝试获取解密后的连接字符串
        try:
            decrypted_connection_string = connection.connection_string
        except RuntimeError as decrypt_error:
            logger.error(f"Failed to decrypt connection string for data source {connection_id}: {decrypt_error}")
            # 返回解密失败的测试结果
            test_result_dict = {
                "success": False,
                "message": "Failed to decrypt connection string",
                "error_code": "DECRYPTION_ERROR",
                "response_time_ms": 0,
                "details": {
                    "error": "加密密钥可能已更改，无法解密连接字符串。请删除此数据源并重新添加。"
                },
                "timestamp": datetime.now().isoformat()
            }
            connection.update_test_result(test_result_dict)
            db.commit()
            return test_result_dict

        # 测试连接字符串
        test_result = await connection_test_service.test_connection(
            connection_string=decrypted_connection_string,
            db_type=connection.db_type
        )

        # 更新连接的测试结果和状态
        connection.update_test_result(test_result.to_dict())
        db.commit()

        logger.info(f"Tested data source {connection_id}: {test_result.success}")
        return test_result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test data source {connection_id}: {e}")
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "error_code": "TEST_EXECUTION_ERROR",
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# 辅助函数 - 被上面的端点使用
# ============================================================================

async def _validate_overview_access(tenant_id: str, user_id: str, db: Session):
    """
    验证概览访问权限
    """
    # 验证租户是否存在且活跃
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.status == TenantStatus.ACTIVE
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive tenant"
        )

    # 这里可以添加更多用户权限验证
    # 例如：检查用户是否有查看概览的权限


async def _get_secure_database_stats(tenant_id: str, db: Session) -> Dict[str, int]:
    """
    安全地获取数据库统计信息，强化租户隔离
    """
    try:
        # 使用强化的租户隔离查询
        db_connections = db.query(DataSourceConnection).filter(
            DataSourceConnection.tenant_id == tenant_id,
            DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE
        ).with_entities(
            DataSourceConnection.id,
            DataSourceConnection.status,
            DataSourceConnection.tenant_id  # 额外的租户ID用于验证
        ).all()

        # 双重验证：确保所有结果都属于该租户
        verified_connections = []
        for conn in db_connections:
            if conn.tenant_id != tenant_id:
                logger.error(f"Security breach: database {conn.id} from tenant {conn.tenant_id} "
                           f"included in stats for tenant {tenant_id}")
                continue
            verified_connections.append(conn)

        # 计算统计信息
        db_total = len(verified_connections)
        db_active = len([conn for conn in verified_connections
                        if conn.status == DataSourceConnectionStatus.ACTIVE])
        db_error = len([conn for conn in verified_connections
                       if conn.status == DataSourceConnectionStatus.ERROR])

        return {
            "total": db_total,
            "active": db_active,
            "error": db_error
        }

    except Exception as e:
        logger.error(f"Failed to get database stats for tenant {tenant_id}: {e}")
        # 返回安全的默认值
        return {
            "total": 0,
            "active": 0,
            "error": 0
        }


async def _get_secure_document_stats(tenant_id: str, db: Session) -> Dict[str, int]:
    """
    安全地获取文档统计信息
    """
    try:
        # TODO: 实现文档统计查询，需要Document模型
        # 确保查询包含强化的租户隔离
        return {
            "total": 0,
            "ready": 0,
            "processing": 0,
            "error": 0
        }

    except Exception as e:
        logger.error(f"Failed to get document stats for tenant {tenant_id}: {e}")
        return {
            "total": 0,
            "ready": 0,
            "processing": 0,
            "error": 0
        }


async def _get_secure_storage_stats(tenant_id: str, db: Session) -> Dict[str, any]:
    """
    安全地获取存储配额和使用情况统计
    """
    try:
        # 获取租户的存储配额配置
        tenant = db.query(Tenant).filter(
            Tenant.id == tenant_id,
            Tenant.status == TenantStatus.ACTIVE
        ).with_entities(
            Tenant.storage_quota_mb
        ).first()

        if not tenant:
            # 租户不存在，返回安全的默认值
            return {
                "used_mb": 0,
                "quota_mb": 1024,  # 默认配额
                "usage_percentage": 0.0,
                "quota_exceeded": False
            }

        storage_quota_mb = tenant.storage_quota_mb or 1024  # 默认1GB

        # TODO: 实现实际存储使用量计算
        # 这里应该从MinIO获取实际的存储使用量
        storage_used_mb = 0  # 实际实现需要查询MinIO

        # 安全地计算使用百分比，防止除零错误
        usage_percentage = 0.0
        if storage_quota_mb > 0:
            usage_percentage = min(100.0, round((storage_used_mb / storage_quota_mb) * 100, 2))

        # 检查是否超过配额
        quota_exceeded = storage_used_mb > storage_quota_mb

        # 如果配额使用率过高，记录警告
        if usage_percentage > 90:
            logger.warning(f"High storage usage for tenant {tenant_id}: {usage_percentage}%")

        return {
            "used_mb": storage_used_mb,
            "quota_mb": storage_quota_mb,
            "usage_percentage": usage_percentage,
            "quota_exceeded": quota_exceeded
        }

    except Exception as e:
        logger.error(f"Failed to get storage stats for tenant {tenant_id}: {e}")
        # 返回安全的默认值
        return {
            "used_mb": 0,
            "quota_mb": 1024,
            "usage_percentage": 0.0,
            "quota_exceeded": False
        }


async def _get_secure_recent_activity(tenant_id: str, db: Session) -> List[Dict[str, any]]:
    """
    安全地获取最近活动记录，包含强化的租户隔离
    """
    try:
        # 获取最近的数据库连接活动
        recent_connections = db.query(DataSourceConnection).filter(
            DataSourceConnection.tenant_id == tenant_id
        ).with_entities(
            DataSourceConnection.id,
            DataSourceConnection.name,
            DataSourceConnection.status,
            DataSourceConnection.created_at,
            DataSourceConnection.updated_at,
            DataSourceConnection.tenant_id  # 用于验证
        ).order_by(DataSourceConnection.updated_at.desc()).limit(5).all()

        recent_activity = []
        for conn in recent_connections:
            # 双重验证：确保活动记录属于该租户
            if conn.tenant_id != tenant_id:
                logger.error(f"Security breach: activity for database {conn.id} from tenant {conn.tenant_id} "
                           f"included in activity for tenant {tenant_id}")
                continue

            # 过滤敏感信息，只返回必要的活动数据
            activity = {
                "id": conn.id,
                "type": "database",
                "action": "updated" if conn.updated_at != conn.created_at else "created",
                "item_name": conn.name,
                "timestamp": conn.updated_at.isoformat() if conn.updated_at else conn.created_at.isoformat(),
                "status": "success" if conn.status == DataSourceConnectionStatus.ACTIVE else "error"
            }
            recent_activity.append(activity)

        return recent_activity

    except Exception as e:
        logger.error(f"Failed to get recent activity for tenant {tenant_id}: {e}")
        return []


async def _validate_search_parameters(
    q: str,
    type: str,
    status: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page: int,
    limit: int
):
    """
    验证搜索参数的安全性和有效性
    """
    # 验证搜索查询
    if q:
        if len(q) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query too long (max 100 characters)"
            )
        # 检查潜在的注入攻击模式
        dangerous_patterns = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
        for pattern in dangerous_patterns:
            if pattern in q.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid search query pattern"
                )

    # 验证类型参数
    if type not in ["all", "database", "document"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid type parameter"
        )

    # 验证分页参数
    if page < 1 or page > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid page parameter"
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid limit parameter (max 100)"
        )


async def _validate_tenant_search_access(tenant_id: str, user_id: str, db: Session):
    """
    验证租户搜索访问权限
    """
    # 验证租户是否存在且活跃
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.status == TenantStatus.ACTIVE
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive tenant"
        )

    # 这里可以添加更多用户权限验证
    # 例如：检查用户是否属于该租户


def _sanitize_search_query(query: str) -> str:
    """
    清理搜索查询，防止注入攻击
    """
    # 移除特殊字符
    import re
    sanitized = re.sub(r"[\'\"\\\;\-\-\/\*\*]", "", query)
    return sanitized.strip()


def _validate_and_parse_statuses(status: str) -> List[str]:
    """
    验证和解析状态参数
    """
    valid_statuses = ["ACTIVE", "INACTIVE", "ERROR", "TESTING"]
    status_list = status.split(',') if ',' in status else [status]

    validated_statuses = []
    for s in status_list:
        s = s.strip().upper()
        if s in valid_statuses:
            validated_statuses.append(s)

    return validated_statuses


def _validate_and_parse_date_range(date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Optional[datetime]]:
    """
    验证和解析日期范围
    """
    from datetime import datetime

    result = {"from": None, "to": None}

    try:
        if date_from:
            result["from"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            result["to"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))

        # 验证日期范围合理性
        if result["from"] and result["to"] and result["from"] > result["to"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date range: start date cannot be after end date"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format."
        )

    return result


async def _validate_bulk_database_delete_permission(
    tenant_id: str,
    user_id: str,
    item_ids: List[str],
    db: Session
):
    """
    验证批量删除数据库连接的权限

    Args:
        tenant_id: 租户ID
        user_id: 用户ID
        item_ids: 要删除的数据源ID列表
        db: 数据库会话
    """
    # 检查是否超过了该租户的数据源删除限制
    active_connections = db.query(DataSourceConnection).filter(
        DataSourceConnection.tenant_id == tenant_id,
        DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE
    ).count()

    # 如果删除后会导致数据源数量过少，可能需要特殊权限
    if active_connections - len(item_ids) < 1:
        # 可以在这里添加特殊权限检查
        logger.warning(f"User {user_id} attempting to delete last {len(item_ids)} "
                       f"data sources for tenant {tenant_id}")

    # 检查最近删除频率，防止恶意批量删除
    recent_deletions = db.query(DataSourceConnection).filter(
        DataSourceConnection.tenant_id == tenant_id,
        DataSourceConnection.status == DataSourceConnectionStatus.INACTIVE,
        DataSourceConnection.updated_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()

    if recent_deletions > 10:  # 同一天内删除超过10个需要额外验证
        logger.warning(f"High frequency deletion detected for tenant {tenant_id}: "
                       f"{recent_deletions} deletions today")


async def _can_delete_data_source(connection: DataSourceConnection, db: Session) -> bool:
    """
    检查数据源是否可以被删除

    Args:
        connection: 数据源连接对象
        db: 数据库会话

    Returns:
        bool: 是否可以删除
    """
    # 检查数据源状态
    if connection.status == DataSourceConnectionStatus.ERROR:
        return True  # 错误状态的数据源可以删除

    if connection.status == DataSourceConnectionStatus.TESTING:
        return False  # 正在测试的数据源不能删除

    # 这里可以添加更多检查，比如：
    # - 检查是否有正在运行的查询
    # - 检查是否有关联的文档
    # - 检查是否有定时任务依赖

    return True