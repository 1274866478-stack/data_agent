"""
文件上传API端点
支持CSV、Excel、SQLite等文件格式上传并创建数据源
"""

import os
import logging
import tempfile
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import pandas as pd
import sqlite3

from src.app.core.auth import get_current_user_with_tenant
from src.app.data.models import Tenant
from src.app.data.database import get_db
from src.app.services.data_source_service import data_source_service
from src.services.database_interface import PostgreSQLAdapter

logger = logging.getLogger(__name__)

router = APIRouter()

# 支持的文件类型和大小限制
SUPPORTED_FILE_TYPES = {
    '.csv': {'max_size': 100 * 1024 * 1024, 'description': 'CSV文件'},  # 100MB
    '.xlsx': {'max_size': 100 * 1024 * 1024, 'description': 'Excel文件'},  # 100MB
    '.xls': {'max_size': 100 * 1024 * 1024, 'description': 'Excel文件'},  # 100MB
    '.db': {'max_size': 500 * 1024 * 1024, 'description': 'SQLite数据库'},  # 500MB
    '.sqlite': {'max_size': 500 * 1024 * 1024, 'description': 'SQLite数据库'},  # 500MB
    '.sqlite3': {'max_size': 500 * 1024 * 1024, 'description': 'SQLite数据库'},  # 500MB
}


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename.lower())[1]


def validate_file(file: UploadFile) -> tuple[str, dict]:
    """
    验证上传的文件
    
    Returns:
        (file_extension, file_type_info)
    """
    # 检查文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    # 获取文件扩展名
    ext = get_file_extension(file.filename)
    
    # 检查文件类型
    if ext not in SUPPORTED_FILE_TYPES:
        supported = ', '.join(SUPPORTED_FILE_TYPES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。支持的类型: {supported}"
        )
    
    file_type_info = SUPPORTED_FILE_TYPES[ext]
    
    # 检查文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到文件开头
    
    if file_size > file_type_info['max_size']:
        max_size_mb = file_type_info['max_size'] / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制。最大允许: {max_size_mb}MB"
        )
    
    return ext, file_type_info


async def process_csv_file(file_path: str, table_name: str) -> pd.DataFrame:
    """处理CSV文件"""
    try:
        # 尝试不同的编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(f"成功使用编码 {encoding} 读取CSV文件")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise ValueError("无法读取CSV文件，请检查文件编码")
        
        return df
    except Exception as e:
        logger.error(f"处理CSV文件失败: {e}")
        raise HTTPException(status_code=400, detail=f"处理CSV文件失败: {str(e)}")


async def process_excel_file(file_path: str, table_name: str) -> pd.DataFrame:
    """处理Excel文件"""
    try:
        # 读取Excel文件（默认读取第一个sheet）
        df = pd.read_excel(file_path, sheet_name=0)
        logger.info(f"成功读取Excel文件，行数: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"处理Excel文件失败: {e}")
        raise HTTPException(status_code=400, detail=f"处理Excel文件失败: {str(e)}")


async def process_sqlite_file(file_path: str) -> dict:
    """处理SQLite文件"""
    try:
        # 连接SQLite数据库
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            raise ValueError("SQLite数据库中没有表")
        
        logger.info(f"SQLite数据库包含 {len(tables)} 个表: {tables}")
        
        # 读取所有表的数据
        table_data = {}
        for table in tables:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            table_data[table] = df
        
        conn.close()
        return table_data
    except Exception as e:
        logger.error(f"处理SQLite文件失败: {e}")
        raise HTTPException(status_code=400, detail=f"处理SQLite文件失败: {str(e)}")


async def import_dataframe_to_postgres(
    df: pd.DataFrame,
    table_name: str,
    connection_string: str
) -> dict:
    """将DataFrame导入到PostgreSQL"""
    try:
        from sqlalchemy import create_engine

        # 创建数据库引擎
        engine = create_engine(connection_string)

        # 导入数据
        df.to_sql(
            table_name,
            engine,
            if_exists='replace',  # 如果表存在则替换
            index=False,
            method='multi',
            chunksize=1000
        )

        row_count = len(df)
        col_count = len(df.columns)

        logger.info(f"成功导入数据到表 {table_name}: {row_count} 行, {col_count} 列")

        return {
            'table_name': table_name,
            'row_count': row_count,
            'column_count': col_count,
            'columns': list(df.columns)
        }
    except Exception as e:
        logger.error(f"导入数据到PostgreSQL失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入数据失败: {str(e)}")


@router.post("/upload-file")
async def upload_file_and_create_datasource(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tenant_info: tuple = Depends(get_current_user_with_tenant),
    db: Session = Depends(get_db)
):
    """
    上传文件并创建数据源

    支持的文件类型:
    - CSV (.csv) - 最大100MB
    - Excel (.xlsx, .xls) - 最大100MB
    - SQLite (.db, .sqlite, .sqlite3) - 最大500MB

    文件会被导入到租户专属的PostgreSQL数据库中
    """
    user_id, tenant = tenant_info

    # 验证文件
    ext, file_type_info = validate_file(file)

    logger.info(f"租户 {tenant.id} 上传文件: {file.filename} ({file_type_info['description']})")

    # 创建临时文件
    temp_file = None
    try:
        # 保存上传的文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # 生成表名（基于文件名，去除扩展名和特殊字符）
        base_name = os.path.splitext(file.filename)[0]
        table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in base_name).lower()
        table_name = f"uploaded_{table_name}"

        # 创建租户专属数据库（如果不存在）
        tenant_db_name = f"tenant_{tenant.id}_uploads"
        tenant_connection_string = f"postgresql://dev:dev123@localhost:5432/{tenant_db_name}"

        # 创建数据库
        from sqlalchemy import create_engine, text
        master_engine = create_engine("postgresql://dev:dev123@localhost:5432/postgres")
        with master_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            # 检查数据库是否存在
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": tenant_db_name}
            )
            if not result.fetchone():
                conn.execute(text(f"CREATE DATABASE {tenant_db_name}"))
                logger.info(f"创建租户数据库: {tenant_db_name}")

        # 处理不同类型的文件
        import_results = []

        if ext == '.csv':
            df = await process_csv_file(temp_file_path, table_name)
            result = await import_dataframe_to_postgres(df, table_name, tenant_connection_string)
            import_results.append(result)

        elif ext in ['.xlsx', '.xls']:
            df = await process_excel_file(temp_file_path, table_name)
            result = await import_dataframe_to_postgres(df, table_name, tenant_connection_string)
            import_results.append(result)

        elif ext in ['.db', '.sqlite', '.sqlite3']:
            table_data = await process_sqlite_file(temp_file_path)
            for tbl_name, df in table_data.items():
                result = await import_dataframe_to_postgres(
                    df,
                    f"{table_name}_{tbl_name}",
                    tenant_connection_string
                )
                import_results.append(result)

        # 创建数据源记录
        data_source = await data_source_service.create_data_source(
            db=db,
            tenant_id=tenant.id,
            name=name,
            db_type="postgresql",
            connection_string=tenant_connection_string,
            description=description or f"从文件 {file.filename} 导入"
        )

        # 删除临时文件
        os.unlink(temp_file_path)

        return {
            "success": True,
            "message": "文件上传并导入成功",
            "data_source": {
                "id": data_source.id,
                "name": data_source.name,
                "db_type": data_source.db_type,
                "status": data_source.status
            },
            "import_results": import_results,
            "file_info": {
                "filename": file.filename,
                "type": file_type_info['description'],
                "size": len(content)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传处理失败: {e}", exc_info=True)
        # 清理临时文件
        if temp_file and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


@router.get("/supported-file-types")
async def get_supported_file_types():
    """获取支持的文件类型列表"""
    return {
        "supported_types": [
            {
                "extension": ext,
                "description": info['description'],
                "max_size_mb": info['max_size'] / (1024 * 1024)
            }
            for ext, info in SUPPORTED_FILE_TYPES.items()
        ]
    }

