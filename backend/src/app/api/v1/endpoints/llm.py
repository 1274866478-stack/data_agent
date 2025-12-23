"""
LLM API端点
提供统一的聊天完成、流式输出和多模态支持
"""

import json
import asyncio
import logging
import io
import os
import sys
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import pandas as pd

from src.app.services.llm_service import (
    llm_service,
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk
)
from src.app.core.auth import get_current_user_with_tenant
from src.app.data.models import Tenant, DataSourceConnection, DataSourceConnectionStatus
from src.app.data.database import get_db
from src.app.services.data_source_service import data_source_service
from src.app.services.minio_client import minio_service
from src.app.services.database_interface import PostgreSQLAdapter
from src.app.services.zhipu_client import zhipu_service
import re
import duckdb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM"])


def _convert_decimal_to_float(data: Any) -> Any:
    """
    递归地将数据中的 Decimal 类型转换为 float，确保 JSON 可序列化
    
    Args:
        data: 需要转换的数据（可以是 dict, list, 或其他类型）
    
    Returns:
        转换后的数据，其中所有 Decimal 都变成了 float
    """
    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: _convert_decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_decimal_to_float(item) for item in data]
    else:
        return data


# ============================================================
# 工具定义 (Tool Definitions) - OpenAI Function Calling 格式
# ============================================================

# SQL 执行工具 Schema
SQL_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_sql",
        "description": "执行 SQL SELECT 查询以获取数据库数据。只能执行 SELECT 查询，禁止执行 INSERT、UPDATE、DELETE 等修改操作。",
        "parameters": {
            "type": "object",
            "properties": {
                "sql_query": {
                    "type": "string",
                    "description": "要执行的 SQL SELECT 查询语句"
                }
            },
            "required": ["sql_query"]
        }
    }
}

# 图表生成工具 Schema
CHART_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_chart",
        "description": "根据数据生成 ECharts 图表配置。当数据包含数字、趋势或分类对比时必须调用此工具进行可视化。",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter"],
                    "description": "图表类型：bar(柱状图-分类对比), line(折线图-趋势变化), pie(饼图-占比分布), scatter(散点图-相关性)"
                },
                "title": {
                    "type": "string",
                    "description": "图表标题"
                },
                "x_data": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "X轴数据（分类名称或时间）"
                },
                "y_data": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Y轴数据（数值）"
                },
                "series_name": {
                    "type": "string",
                    "description": "数据系列名称（可选）"
                }
            },
            "required": ["chart_type", "title", "x_data", "y_data"]
        }
    }
}


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色：user, assistant, system")
    content: Union[str, List[Dict[str, Any]]] = Field(
        ...,
        description="消息内容，支持文本或多模态内容"
    )
    thinking: Optional[str] = Field(None, description="思考过程（仅assistant角色）")


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    provider: Optional[str] = Field(
        None,
        description="LLM提供商：zhipu, openrouter，不指定则自动选择"
    )
    model: Optional[str] = Field(None, description="模型名称，不指定则使用默认模型")
    max_tokens: Optional[int] = Field(None, description="最大输出tokens")
    temperature: Optional[float] = Field(None, description="温度参数(0-1)")
    stream: bool = Field(False, description="是否启用流式输出")
    enable_thinking: bool = Field(False, description="是否启用深度思考模式（仅Zhipu支持）")
    data_source_ids: Optional[List[str]] = Field(None, description="指定使用的数据源ID列表，不指定则使用所有活跃数据源")


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""
    content: str = Field(..., description="回复内容")
    thinking: Optional[str] = Field(None, description="思考过程")
    usage: Optional[Dict[str, int]] = Field(None, description="Token使用情况")
    model: Optional[str] = Field(None, description="使用的模型")
    provider: Optional[str] = Field(None, description="使用的提供商")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    created_at: Optional[str] = Field(None, description="创建时间")


class ProviderStatusResponse(BaseModel):
    """提供商状态响应模型"""
    zhipu: bool = Field(..., description="智谱AI可用性")
    openrouter: bool = Field(..., description="OpenRouter可用性")


class AvailableModelsResponse(BaseModel):
    """可用模型响应模型"""
    providers: Dict[str, List[str]] = Field(..., description="各提供商的可用模型")


def _convert_chat_messages(messages: List[ChatMessage]) -> List[LLMMessage]:
    """转换聊天消息格式"""
    llm_messages = []
    for msg in messages:
        llm_messages.append(LLMMessage(
            role=msg.role,
            content=msg.content,
            thinking=msg.thinking
        ))
    return llm_messages


def _get_column_type(dtype_str: str) -> str:
    """将pandas数据类型转换为友好的类型描述"""
    if 'int' in dtype_str:
        return 'integer'
    elif 'float' in dtype_str:
        return 'float'
    elif 'datetime' in dtype_str:
        return 'datetime'
    elif 'bool' in dtype_str:
        return 'boolean'
    else:
        return 'text'


def _build_table_schema(df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
    """从DataFrame构建单个表的schema信息"""
    columns = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        columns.append({
            "name": str(col),
            "type": _get_column_type(dtype),
            "nullable": df[col].isnull().any()
        })

    # 获取示例数据（前5行）
    sample_rows = []
    for _, row in df.head(5).iterrows():
        row_data = {}
        for col in df.columns[:10]:  # 限制列数
            value = row[col]
            if pd.isna(value):
                row_data[str(col)] = None
            else:
                row_data[str(col)] = str(value)
        sample_rows.append(row_data)

    return {
        "table_info": {
            "name": table_name,
            "columns": columns,
            "row_count": len(df)
        },
        "sample_data": {
            "columns": [str(c) for c in df.columns[:10]],
            "data": sample_rows
        }
    }


async def _get_file_schema(connection_string: str, db_type: str, data_source_name: str) -> Dict[str, Any]:
    """
    从文件数据源获取schema信息（支持Excel多Sheet）

    Args:
        connection_string: 文件存储路径（格式: file://data-sources/{tenant_id}/{file_id}.xlsx 或 /app/uploads/...）
        db_type: 文件类型（xlsx, csv, xls等）
        data_source_name: 数据源名称

    Returns:
        schema信息字典，包含所有表（Sheet）的列名、类型和示例数据
    """
    try:
        # 🔧 修复：使用新的路径解析逻辑，优先尝试本地文件系统
        from src.app.services.agent.path_extractor import resolve_file_path_with_fallback
        
        # 首先尝试解析路径（包含本地回退逻辑）
        local_file_path = resolve_file_path_with_fallback(connection_string)
        file_data = None
        use_local_file = False
        
        # 如果找到本地文件，直接使用
        if local_file_path and os.path.exists(local_file_path):
            logger.info(f"从本地文件系统读取文件: {local_file_path}")
            use_local_file = True
            file_path_for_read = local_file_path
        else:
            # 尝试从MinIO下载
            storage_path = connection_string[7:] if connection_string.startswith("file://") else connection_string
            logger.info(f"尝试从MinIO下载文件: {storage_path}")
            file_data = minio_service.download_file(
                bucket_name="data-sources",
                object_name=storage_path
            )
            
            if not file_data:
                logger.warning(f"无法从MinIO获取文件: {storage_path}")
                # 最后尝试本地回退
                if local_file_path:
                    logger.info(f"尝试使用解析的本地路径: {local_file_path}")
                    if os.path.exists(local_file_path):
                        use_local_file = True
                        file_path_for_read = local_file_path
                    else:
                        return {}
                else:
                    return {}

        tables = []
        sample_data = {}

        if db_type in ["xlsx", "xls"]:
            # 读取所有Sheet
            try:
                if use_local_file:
                    # 从本地文件读取
                    excel_file = pd.ExcelFile(file_path_for_read, engine='openpyxl')
                else:
                    # 从MinIO下载的数据读取
                    excel_file = pd.ExcelFile(io.BytesIO(file_data), engine='openpyxl')
            except ImportError as e:
                logger.error(f"System Error: Missing dependency 'openpyxl'. {str(e)}")
                return {}
            except Exception as e:
                logger.error(f"Execution Error: Failed to read Excel file. {str(e)}")
                return {}
            
            sheet_names = excel_file.sheet_names
            logger.info(f"Excel文件包含 {len(sheet_names)} 个Sheet: {sheet_names}")

            for sheet_name in sheet_names:
                try:
                    # 显式指定 engine='openpyxl'
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
                    if df.empty:
                        logger.debug(f"跳过空Sheet: {sheet_name}")
                        continue

                    # 使用Sheet名称作为表名
                    table_schema = _build_table_schema(df, sheet_name)
                    tables.append(table_schema["table_info"])
                    sample_data[sheet_name] = table_schema["sample_data"]
                    logger.info(f"Sheet '{sheet_name}': {len(df)}行, {len(df.columns)}列")
                except Exception as e:
                    logger.warning(f"读取Sheet '{sheet_name}' 失败: {e}")
                    continue

        elif db_type == "csv":
            # CSV文件只有一个表
            df = None
            if use_local_file:
                # 从本地文件读取
                for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                    try:
                        df = pd.read_csv(file_path_for_read, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
            else:
                # 从MinIO下载的数据读取
                for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_data), encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue

            if df is not None:
                table_schema = _build_table_schema(df, data_source_name)
                tables.append(table_schema["table_info"])
                sample_data[data_source_name] = table_schema["sample_data"]

        if not tables:
            path_info = file_path_for_read if use_local_file else (connection_string[7:] if connection_string.startswith("file://") else connection_string)
            logger.warning(f"无法从文件解析任何表: {path_info}")
            return {}

        schema_info = {
            "tables": tables,
            "sample_data": sample_data
        }

        total_rows = sum(t.get("row_count", 0) for t in tables)
        logger.info(f"成功获取文件schema: {len(tables)}个表, 共{total_rows}行")
        return schema_info

    except Exception as e:
        logger.error(f"获取文件schema失败: {e}")
        return {}


async def _try_find_file_in_minio(tenant_id: str, data_source_id: str, db_type: str) -> Optional[str]:
    """
    尝试在MinIO中查找数据源对应的文件

    Args:
        tenant_id: 租户ID
        data_source_id: 数据源ID
        db_type: 文件类型

    Returns:
        文件路径（如果找到）
    """
    try:
        # 构建可能的文件路径模式
        prefix = f"{tenant_id}/{data_source_id}"
        ext = f".{db_type}"

        # 列出MinIO中的文件
        objects = minio_service.list_files(
            bucket_name="data-sources",
            prefix=prefix
        )

        for obj in objects:
            obj_name = obj.object_name if hasattr(obj, 'object_name') else str(obj)
            if obj_name.endswith(ext):
                return f"file://{obj_name}"

        logger.warning(f"在MinIO中未找到数据源 {data_source_id} 的文件")
        return None

    except Exception as e:
        logger.error(f"在MinIO中搜索文件失败: {e}")
        return None


async def _try_get_file_schema_fallback(tenant_id: str, data_source_id: str, db_type: str, data_source_name: str) -> Dict[str, Any]:
    """
    备选方案：尝试从MinIO直接获取文件schema（支持Excel多Sheet）

    Args:
        tenant_id: 租户ID
        data_source_id: 数据源ID
        db_type: 文件类型
        data_source_name: 数据源名称

    Returns:
        schema信息字典
    """
    try:
        # 构建可能的文件路径
        ext = f".{db_type}"
        possible_paths = [
            f"{tenant_id}/{data_source_id}{ext}",
            f"{tenant_id}/{data_source_name}{ext}",
        ]

        for path in possible_paths:
            try:
                logger.info(f"尝试从MinIO获取文件: {path}")
                file_data = minio_service.download_file(
                    bucket_name="data-sources",
                    object_name=path
                )

                if file_data:
                    tables = []
                    sample_data = {}

                    if db_type in ["xlsx", "xls"]:
                        # 读取所有Sheet
                        try:
                            # 显式指定 engine='openpyxl' 以确保正确读取
                            excel_file = pd.ExcelFile(io.BytesIO(file_data), engine='openpyxl')
                        except ImportError as e:
                            logger.error(f"System Error: Missing dependency 'openpyxl'. {str(e)}")
                            continue  # 尝试下一个路径
                        except Exception as e:
                            logger.error(f"Execution Error: Failed to read Excel file. {str(e)}")
                            continue  # 尝试下一个路径
                        
                        sheet_names = excel_file.sheet_names
                        logger.info(f"备选方案: Excel包含 {len(sheet_names)} 个Sheet: {sheet_names}")

                        for sheet_name in sheet_names:
                            try:
                                # 显式指定 engine='openpyxl'
                                df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
                                if df.empty:
                                    continue
                                table_schema = _build_table_schema(df, sheet_name)
                                tables.append(table_schema["table_info"])
                                sample_data[sheet_name] = table_schema["sample_data"]
                            except Exception as e:
                                logger.debug(f"读取Sheet '{sheet_name}' 失败: {e}")
                                continue

                    elif db_type == "csv":
                        df = None
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                            try:
                                df = pd.read_csv(io.BytesIO(file_data), encoding=encoding)
                                break
                            except UnicodeDecodeError:
                                continue

                        if df is not None:
                            table_schema = _build_table_schema(df, data_source_name)
                            tables.append(table_schema["table_info"])
                            sample_data[data_source_name] = table_schema["sample_data"]

                    if tables:
                        total_rows = sum(t.get("row_count", 0) for t in tables)
                        logger.info(f"备选方案成功获取schema: {len(tables)}个表, 共{total_rows}行")
                        return {
                            "tables": tables,
                            "sample_data": sample_data
                        }

            except Exception as e:
                logger.debug(f"尝试路径 {path} 失败: {e}")
                continue

        logger.warning(f"备选方案未能获取数据源 {data_source_name} 的schema")
        return {}

    except Exception as e:
        logger.error(f"备选方案获取schema失败: {e}")
        return {}


async def _get_data_sources_context(tenant_id: str, db: Session, data_source_ids: Optional[List[str]] = None) -> str:
    """
    获取租户数据源的上下文信息（包括schema）

    Args:
        tenant_id: 租户ID
        db: 数据库会话
        data_source_ids: 指定的数据源ID列表，如果为None则获取所有活跃数据源

    Returns:
        数据源上下文字符串
    """
    start_time = time.time()
    try:
        # 获取租户的所有活跃数据源
        t1 = time.time()
        data_sources = await data_source_service.get_data_sources(
            tenant_id=tenant_id,
            db=db,
            active_only=True
        )
        perf_msg = f"[PERF] get_data_sources took {time.time() - t1:.2f}s, found {len(data_sources) if data_sources else 0} sources"
        print(perf_msg)  # 直接打印到控制台
        logger.info(perf_msg)

        if not data_sources:
            return ""

        # 如果指定了数据源ID，则只获取指定的数据源
        if data_source_ids:
            original_count = len(data_sources)
            data_sources = [ds for ds in data_sources if ds.id in data_source_ids]
            logger.info(f"🎯 [数据源筛选] 指定数据源: {data_source_ids}, 从 {original_count} 个中筛选出 {len(data_sources)} 个匹配的数据源")
            for ds in data_sources:
                logger.info(f"  ✅ 使用数据源: {ds.name} (ID: {ds.id}, 类型: {ds.db_type})")
            if not data_sources:
                logger.warning(f"⚠️ [数据源筛选] 未找到匹配的数据源！请求的ID: {data_source_ids}")
                return ""
        else:
            logger.warning(f"⚠️ [数据源筛选] 未指定 data_source_ids，将使用所有 {len(data_sources)} 个活跃数据源:")
            for ds in data_sources:
                logger.info(f"  📦 活跃数据源: {ds.name} (ID: {ds.id}, 类型: {ds.db_type})")

        context_parts = []
        context_parts.append("## 可用数据源\n")

        for ds in data_sources:
            try:
                ds_start = time.time()
                schema_info = None
                connection_string = None

                # 尝试获取解密后的连接字符串
                try:
                    t2 = time.time()
                    connection_string = await data_source_service.get_decrypted_connection_string(
                        data_source_id=ds.id,
                        tenant_id=tenant_id,
                        db=db
                    )
                    print(f"[PERF] get_decrypted_connection_string for {ds.name} took {time.time() - t2:.2f}s")
                except Exception as decrypt_error:
                    print(f"[PERF] 解密数据源 {ds.name} 连接字符串失败: {decrypt_error}")
                    # 对于文件类型数据源，尝试从MinIO直接搜索文件
                    if ds.db_type in ["xlsx", "xls", "csv"]:
                        connection_string = await _try_find_file_in_minio(tenant_id, ds.id, ds.db_type)

                # 根据数据源类型获取schema
                if ds.db_type == "postgresql" and connection_string:
                    t3 = time.time()
                    adapter = PostgreSQLAdapter(connection_string)
                    try:
                        await adapter.connect()
                        schema_result = await adapter.get_schema_info()
                        # 将SchemaInfo对象转换为字典格式
                        schema_info = {
                            "database_type": schema_result.database_type.value if schema_result.database_type else "postgresql",
                            "tables": [
                                {
                                    "name": table.name,
                                    "columns": [
                                        {
                                            "name": col.name,
                                            "type": col.data_type,
                                            "nullable": col.is_nullable
                                        }
                                        for col in table.columns
                                    ]
                                }
                                for table in schema_result.tables.values()
                            ] if schema_result.tables else []
                        }
                    finally:
                        await adapter.disconnect()
                    print(f"[PERF] PostgreSQL get_schema for {ds.name} took {time.time() - t3:.2f}s")

                elif ds.db_type in ["xlsx", "xls", "csv"]:
                    # 🔧 修复：从connection_config或connection_string提取文件路径
                    file_path = connection_string
                    if hasattr(ds, 'connection_config') and ds.connection_config:
                        # 如果存在connection_config字段，优先使用它
                        from src.app.services.agent.path_extractor import extract_file_path_from_config
                        extracted_path = extract_file_path_from_config(ds.connection_config, connection_string)
                        if extracted_path:
                            file_path = extracted_path
                    
                    if file_path:
                        # 文件类型数据源：从文件读取并解析schema
                        t4 = time.time()
                        schema_info = await _get_file_schema(file_path, ds.db_type, ds.name)
                        print(f"[PERF] _get_file_schema for {ds.name} took {time.time() - t4:.2f}s")
                    else:
                        # 连接字符串获取失败，尝试备选方案
                        print(f"[PERF] 尝试备选方案获取数据源 {ds.name} 的schema")
                        schema_info = await _try_get_file_schema_fallback(tenant_id, ds.id, ds.db_type, ds.name)

                print(f"[PERF] Total processing for data source {ds.name} took {time.time() - ds_start:.2f}s")

                if schema_info and schema_info.get("tables"):
                    context_parts.append(f"\n### 数据源: {ds.name}")
                    context_parts.append(f"- 类型: {ds.db_type}")
                    context_parts.append(f"- 文件/数据库: {ds.database_name or '未知'}")

                    # 添加表信息
                    context_parts.append("\n#### 表结构:")
                    for table in schema_info["tables"][:20]:  # 限制表数量避免token过多
                        table_name = table.get("name", "unknown")
                        row_count = table.get("row_count", "未知")
                        context_parts.append(f"\n**表: {table_name}** (共{row_count}行)")

                        columns = table.get("columns", [])
                        if columns:
                            col_info = []
                            for col in columns[:30]:  # 限制列数量
                                col_name = col.get("name", "unknown")
                                col_type = col.get("type", "unknown")
                                nullable = "可空" if col.get("nullable") else "非空"
                                col_info.append(f"  - {col_name} ({col_type}, {nullable})")
                            context_parts.append("\n".join(col_info))

                        # 添加主键信息
                        if table.get("primary_key"):
                            context_parts.append(f"  - 主键: {', '.join(table['primary_key'])}")

                        # 添加外键信息
                        if table.get("foreign_keys"):
                            for fk in table["foreign_keys"]:
                                context_parts.append(
                                    f"  - 外键: {fk['column']} -> {fk['references_table']}.{fk['references_column']}"
                                )

                    # 添加表关系信息（外键关联）
                    relationships = schema_info.get("relationships", [])
                    if relationships:
                        context_parts.append("\n#### 表关系（外键）:")
                        context_parts.append("**重要：** 以下是表之间的关联关系，查询时必须通过这些外键进行JOIN：")
                        for rel in relationships:
                            from_table = rel.get("from_table", "unknown")
                            from_column = rel.get("from_column", "unknown")
                            to_table = rel.get("to_table", "unknown")
                            to_column = rel.get("to_column", "unknown")
                            context_parts.append(
                                f"  - {from_table}.{from_column} -> {to_table}.{to_column}"
                            )

                    # 添加示例数据
                    sample_data = schema_info.get("sample_data", {})
                    if sample_data:
                        context_parts.append("\n#### 示例数据:")
                        for table_name, samples in list(sample_data.items())[:5]:  # 限制表数量
                            if samples.get("data"):
                                context_parts.append(f"\n**{table_name}** (前5行):")
                                for row in samples["data"][:3]:  # 限制行数
                                    row_str = ", ".join([f"{k}={v}" for k, v in list(row.items())[:5]])
                                    context_parts.append(f"  {row_str}")
                else:
                    # 其他数据库类型暂时只显示基本信息
                    context_parts.append(f"\n### 数据源: {ds.name}")
                    context_parts.append(f"- 类型: {ds.db_type}")
                    context_parts.append(f"- 数据库: {ds.database_name or '未知'}")
                    context_parts.append("- 注: 此数据库类型的schema发现功能开发中")

            except Exception as e:
                logger.warning(f"获取数据源 {ds.name} 的schema失败: {e}")
                context_parts.append(f"\n### 数据源: {ds.name}")
                context_parts.append(f"- 类型: {ds.db_type}")
                context_parts.append(f"- 注: 无法获取schema信息 ({str(e)[:50]})")

        total_time = time.time() - start_time
        logger.info(f"[PERF] _get_data_sources_context TOTAL took {total_time:.2f}s")
        return "\n".join(context_parts)

    except Exception as e:
        logger.error(f"获取数据源上下文失败: {e}")
        return ""


def _build_system_prompt_with_context(data_sources_context: str) -> str:
    """
    构建包含数据源上下文的系统提示词（使用 SQL 代码块格式）

    Args:
        data_sources_context: 数据源上下文信息

    Returns:
        系统提示词
    """
    if data_sources_context:
        # 有数据源时的完整提示，要求使用 ```sql 代码块格式
        return f"""你是一个专业的数据分析师。你的任务是根据用户的问题，查询数据库并给出分析结果。

## 🔴 重要规则 🔴

**你必须使用 SQL 代码块来查询数据，格式如下：**

```sql
SELECT * FROM 表名 WHERE 条件;
```

**禁止使用任何工具调用或函数调用格式！只需要在回答中直接写 SQL 代码块即可。**

---

## 工作流程

### 步骤 1: 分析问题
- 理解用户想要查询什么数据
- 根据下方的数据库 Schema 确定需要查询的表和字段

### 步骤 2: 生成 SQL
- 在回答中使用 ```sql ... ``` 代码块格式输出 SQL 查询语句
- 必须使用下方 Schema 中的**实际表名和列名**，禁止猜测
- 系统会自动执行你的 SQL 并返回结果

### 步骤 3: 分析结果（可选）
- 如果你已经知道数据特征，可以简要说明预期的分析方向
- 例如："让我查询一下各产品的销量数据..."

---

## 数据库 Schema

{data_sources_context}

---

## 🔥 日期处理重要说明（针对 Excel/CSV 文件数据源）

**对于 Excel/CSV 文件数据源，日期字段通常存储为文本格式，请使用以下方式处理：**

### 方式1：使用 CAST 转换后比较（推荐）
```sql
SELECT * FROM 订单表 
WHERE CAST(created_at AS DATE) >= '2023-01-01' 
  AND CAST(created_at AS DATE) < '2024-01-01';
```

### 方式2：使用 LIKE 进行文本匹配
```sql
-- 筛选2023年的数据
SELECT * FROM 订单表 WHERE created_at LIKE '2023%';

-- 筛选2023年某月的数据
SELECT * FROM 订单表 WHERE created_at LIKE '2023-06%';
```

### 方式3：按年月分组统计
```sql
-- 使用 strftime 需要先转换为日期类型
SELECT 
    strftime(CAST(created_at AS DATE), '%Y-%m') as 月份,
    COUNT(*) as 订单数量
FROM 订单表 
WHERE created_at LIKE '2023%'
GROUP BY strftime(CAST(created_at AS DATE), '%Y-%m')
ORDER BY 月份;
```

### 方式4：使用 SUBSTRING 提取年月（更通用）
```sql
SELECT 
    SUBSTRING(created_at, 1, 7) as 月份,
    COUNT(*) as 订单数量,
    SUM(final_amount) as 总销售额
FROM 订单表 
WHERE SUBSTRING(created_at, 1, 4) = '2023'
GROUP BY SUBSTRING(created_at, 1, 7)
ORDER BY 月份;
```

---

## SQL 格式示例

用户问："列出所有用户"
你的回答：
让我帮你查询所有用户信息：

```sql
SELECT * FROM 用户表;
```

用户问："哪个产品卖得最好？"
你的回答：
让我查询各产品的销量排名：

```sql
SELECT 产品名称, SUM(销量) as 总销量 
FROM 订单表 
GROUP BY 产品名称 
ORDER BY 总销量 DESC 
LIMIT 10;
```

用户问："2023年的销售趋势如何？"
你的回答：
让我查询2023年按月的销售趋势：

```sql
SELECT 
    SUBSTRING(created_at, 1, 7) as 月份,
    COUNT(*) as 订单数量,
    SUM(final_amount) as 总销售额
FROM 订单表 
WHERE SUBSTRING(created_at, 1, 4) = '2023'
GROUP BY SUBSTRING(created_at, 1, 7)
ORDER BY 月份;
```

---

**记住：只需要在回答中写 SQL 代码块，系统会自动执行查询并返回结果！**"""
    else:
        # 没有数据源时的提示
        return """你是一个数据分析助手。

当前系统中还没有连接任何数据源。

如果用户询问数据相关问题，请告诉他们需要先在"数据源管理"页面添加数据库连接。

不要假设或猜测数据库结构，不要生成任何SQL查询。"""


def _parse_sql_error(error_message: str) -> Dict[str, str]:
    """
    解析SQL错误信息，提取关键信息

    Args:
        error_message: 完整的错误信息

    Returns:
        包含main_error, hint, suggestion的字典
    """
    result = {
        'main_error': error_message,
        'hint': None,
        'suggestion': None
    }

    try:
        # 提取主要错误信息
        lines = error_message.split('\n')

        # 首先尝试从完整错误信息中提取列/表不存在的错误
        column_match = re.search(r'column "([^"]+)" does not exist', error_message, re.IGNORECASE)
        table_match = re.search(r'table "([^"]+)" does not exist', error_message, re.IGNORECASE)
        relation_match = re.search(r'relation "([^"]+)" does not exist', error_message, re.IGNORECASE)

        if column_match:
            wrong_column = column_match.group(1)
            result['main_error'] = f'column "{wrong_column}" does not exist'
        elif table_match:
            wrong_table = table_match.group(1)
            result['main_error'] = f'table "{wrong_table}" does not exist'
        elif relation_match:
            wrong_relation = relation_match.group(1)
            result['main_error'] = f'relation "{wrong_relation}" does not exist'
        else:
            # 如果没有找到特定错误，尝试提取第一行有意义的错误信息
            for line in lines:
                if 'psycopg2.errors' in line:
                    # 提取括号后的内容
                    match = re.search(r'\)\s*(.+?)(?:\n|$)', line)
                    if match:
                        result['main_error'] = match.group(1).strip()
                        break
                elif line.strip() and not line.startswith('LINE') and not line.startswith('[SQL') and not line.startswith('HINT'):
                    result['main_error'] = line.strip()
                    break

        # 提取HINT信息
        hint_match = re.search(r'HINT:\s*(.+?)(?:\n|$)', error_message, re.IGNORECASE)
        if hint_match:
            result['hint'] = hint_match.group(1).strip()

            # 根据HINT生成建议
            if 'Perhaps you meant to reference the column' in result['hint']:
                # 提取建议的列名
                column_match = re.search(r'column "([^"]+)"', result['hint'])
                if column_match:
                    suggested_column = column_match.group(1)
                    # 提取简单列名（去掉表名前缀）
                    simple_column = suggested_column.split('.')[-1] if '.' in suggested_column else suggested_column
                    result['suggestion'] = f"请使用列名 `{simple_column}` 而不是错误的列名。"

        # 如果是列不存在错误但没有HINT建议
        if column_match and not result['suggestion']:
            wrong_column = column_match.group(1)
            result['suggestion'] = f"列 `{wrong_column}` 不存在，请检查schema中的实际列名。"

        # 如果是表不存在错误
        if table_match and not result['suggestion']:
            wrong_table = table_match.group(1)
            result['suggestion'] = f"表 `{wrong_table}` 不存在，请检查schema中的实际表名。"

        # 如果是relation不存在错误（PostgreSQL的表不存在错误）
        if relation_match and not result['suggestion']:
            wrong_relation = relation_match.group(1)
            result['suggestion'] = f"表 `{wrong_relation}` 不存在，请检查schema中的实际表名。"

    except Exception as e:
        logger.warning(f"解析SQL错误信息失败: {e}")

    return result


async def _fix_sql_with_ai(
    original_sql: str,
    error_message: str,
    schema_context: str,
    original_question: str
) -> Optional[str]:
    """
    使用AI修复失败的SQL查询

    Args:
        original_sql: 原始SQL查询
        error_message: 错误信息
        schema_context: 数据库schema上下文
        original_question: 用户原始问题

    Returns:
        修复后的SQL，如果无法修复则返回None
    """
    try:
        # 解析错误信息，提取关键信息
        error_details = _parse_sql_error(error_message)

        # 构建更精确的修复提示
        fix_prompt = f"""你是一个SQL专家。用户的查询执行失败了，请帮助修复SQL语句。

# 用户原始问题
{original_question}

# 失败的SQL查询
```sql
{original_sql}
```

# 错误信息
{error_details['main_error']}

# PostgreSQL数据库提示
{error_details.get('hint', '无')}

# 🔴🔴🔴 数据库Schema信息（必须使用这里的实际表名和列名）
{schema_context}

# 🔥🔥🔥 修复要求（必须严格遵守）

## 第1步：理解错误
- **主要错误**: {error_details['main_error']}
- **数据库提示**: {error_details.get('hint', '无提示')}

## 第2步：查找正确的表名/列名
**🔴 核心问题：SQL中使用了不存在的表名或列名！**

1. **如果错误是"Table does not exist"**：
   - 这通常意味着SQL中使用了错误的表名（可能是用户想象的中文名）
   - 必须从上面的Schema信息中找到实际存在的表名
   - 例如：用户说"客户"，但Schema中实际的表可能叫 `customers`
   - 例如：用户说"订单"，但Schema中实际的表可能叫 `orders`

2. **如果错误是"Column does not exist"**：
   - 查看PostgreSQL的HINT提示
   - 在Schema中找到正确的列名

3. **常见错误模式（中文表名→英文实际表名）：**
   - ❌ `FROM 客户` → ✅ `FROM customers`（或Schema中的实际表名）
   - ❌ `FROM 订单` → ✅ `FROM orders`（或Schema中的实际表名）
   - ❌ `FROM 产品` → ✅ `FROM products`（或Schema中的实际表名）
   - ❌ `FROM 员工` → ✅ `FROM employees`（或Schema中的实际表名）

## 第3步：修复SQL
1. 仔细阅读上面的Schema信息，找到对应的**实际表名和列名**
2. 将SQL中错误的表名/列名替换为Schema中的实际名称
3. 确保SQL语法正确
4. 只使用SELECT查询
5. 🔴 极值查询必须使用 LIMIT 1：如果原始问题涉及"最大"、"最小"、"最长"、"最短"等极值，确保SQL使用 ORDER BY + LIMIT 1

## 第4步：返回结果
- **只返回修复后的SQL语句** - 不要包含任何解释或markdown标记
- **如果Schema中没有相关的表或列** - 返回"CANNOT_FIX"
- **不要添加```sql标记** - 直接返回纯SQL语句

# 修复示例

**错误SQL:**
```sql
SELECT 客户.name, SUM(订单.total_amount) FROM 客户 JOIN 订单 ON 客户.id = 订单.customer_id
```

**错误信息:**
Table with name 客户 does not exist

**Schema信息中显示实际表名是：customers, orders**

**修复后的SQL:**
SELECT customers.name, SUM(orders.total_amount) as total_spent FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY customers.name

---

现在请修复上述失败的SQL查询，直接返回修复后的SQL语句："""

        messages = [
            {"role": "system", "content": "你是一个专业的SQL修复专家，擅长根据错误信息和schema修复SQL查询。"},
            {"role": "user", "content": fix_prompt}
        ]

        # 调用智谱AI修复SQL（跳过安全检查，因为这是内部调用）
        response = await zhipu_service.chat_completion(
            messages=messages,
            max_tokens=1000,
            temperature=0.1,  # 低温度确保准确性
            stream=False,
            skip_security_check=True  # 内部SQL修复调用，跳过安全检查
        )

        if response and response.get("content"):
            fixed_sql = response["content"].strip()

            # 清理返回的SQL
            # 移除可能的markdown代码块标记
            fixed_sql = re.sub(r'```sql\s*', '', fixed_sql)
            fixed_sql = re.sub(r'```\s*', '', fixed_sql)
            fixed_sql = fixed_sql.strip()

            # 检查是否无法修复
            if "CANNOT_FIX" in fixed_sql.upper():
                logger.warning("AI表示无法修复此SQL")
                return None

            # 验证是否是SELECT查询
            if not fixed_sql.upper().startswith('SELECT'):
                logger.warning("修复后的SQL不是SELECT查询")
                return None

            logger.info(f"AI成功修复SQL: {fixed_sql[:100]}...")
            return fixed_sql

        return None

    except Exception as e:
        logger.error(f"AI修复SQL失败: {e}")
        return None


async def _execute_sql_on_file_datasource(
    connection_string: str,
    db_type: str,
    sql_query: str,
    data_source_name: str
) -> Dict[str, Any]:
    """
    在文件类型数据源上执行SQL查询（使用duckdb，支持Excel多Sheet）

    Args:
        connection_string: 文件存储路径
        db_type: 文件类型（xlsx, csv, xls）
        sql_query: SQL查询语句
        data_source_name: 数据源名称（用于表名）

    Returns:
        查询结果字典
    """
    try:
        # 解析存储路径
        if connection_string.startswith("file://"):
            storage_path = connection_string[7:]
        else:
            storage_path = connection_string

        file_data = None
        file_path = None

        # 🔧 修复：优先使用本地文件，只有本地不存在时才从 MinIO 下载
        # 检查是否是本地文件路径（通常在 /app/uploads/ 目录下）
        if storage_path.startswith("/app/uploads/") or storage_path.startswith("/app/data/"):
            file_path = storage_path
            if os.path.exists(file_path):
                logger.info(f"直接使用本地文件: {file_path}")
                try:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                except Exception as e:
                    logger.warning(f"读取本地文件失败: {e}，尝试从 MinIO 下载")
                    file_data = None
            else:
                logger.info(f"本地文件不存在: {file_path}，尝试从 MinIO 下载")
        
        # 如果本地文件不存在或读取失败，从 MinIO 下载
        if not file_data:
            # 从路径中提取正确的 object_name（去掉 /app/uploads/ 前缀）
            if storage_path.startswith("/app/uploads/"):
                # 提取相对于 uploads 的路径作为 object_name
                object_name = storage_path.replace("/app/uploads/", "", 1)
            elif storage_path.startswith("/app/data/"):
                # 提取相对于 data 的路径作为 object_name
                object_name = storage_path.replace("/app/data/", "", 1)
            else:
                # 如果路径不包含 /app/uploads/ 或 /app/data/，直接使用原路径
                object_name = storage_path.lstrip("/")
            
            logger.info(f"从MinIO下载文件用于SQL执行: bucket=data-sources, object_name={object_name}")
            try:
                file_data = minio_service.download_file(
                    bucket_name="data-sources",
                    object_name=object_name
                )
            except Exception as e:
                logger.error(f"从MinIO下载文件失败: {e}")
                file_data = None

        if not file_data:
            return {
                "success": False,
                "error": f"无法获取文件: {storage_path} (本地路径: {file_path if file_path else 'N/A'})",
                "data": [],
                "columns": [],
                "row_count": 0
            }

        # 创建duckdb连接
        conn = duckdb.connect(':memory:')
        registered_tables = []

        if db_type in ["xlsx", "xls"]:
            # 读取所有Sheet并注册为不同的表
            try:
                # 显式指定 engine='openpyxl' 以确保正确读取
                excel_file = pd.ExcelFile(io.BytesIO(file_data), engine='openpyxl')
            except ImportError as e:
                conn.close()
                return {
                    "success": False,
                    "error": f"System Error: Missing dependency 'openpyxl'. Please install it: pip install openpyxl. Original error: {str(e)}",
                    "data": [],
                    "columns": [],
                    "row_count": 0
                }
            except Exception as e:
                conn.close()
                return {
                    "success": False,
                    "error": f"Execution Error: Failed to read Excel file. {str(e)}",
                    "data": [],
                    "columns": [],
                    "row_count": 0
                }
            
            sheet_names = excel_file.sheet_names
            logger.info(f"Excel包含 {len(sheet_names)} 个Sheet: {sheet_names}")

            for sheet_name in sheet_names:
                try:
                    # 显式指定 engine='openpyxl'
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
                    if df.empty:
                        logger.debug(f"跳过空Sheet: {sheet_name}")
                        continue

                    # 使用Sheet名称作为表名（清理特殊字符）
                    # 保留中文字符，因为DuckDB支持中文表名
                    clean_table_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', sheet_name)
                    if not clean_table_name or clean_table_name[0].isdigit():
                        clean_table_name = f"sheet_{clean_table_name}"

                    conn.register(clean_table_name, df)
                    registered_tables.append(clean_table_name)
                    logger.info(f"注册表 '{clean_table_name}' (来自Sheet '{sheet_name}'): {len(df)}行")

                    # 同时用原始Sheet名注册（如果不同）
                    if sheet_name != clean_table_name:
                        try:
                            conn.register(sheet_name, df)
                            registered_tables.append(sheet_name)
                        except Exception:
                            pass  # 如果原名注册失败，忽略

                except Exception as e:
                    logger.warning(f"读取Sheet '{sheet_name}' 失败: {e}")
                    continue

            # 如果第一个Sheet存在，也用数据源名称注册（向后兼容）
            if sheet_names:
                try:
                    # 显式指定 engine='openpyxl'
                    first_df = pd.read_excel(excel_file, sheet_name=0, engine='openpyxl')
                    if not first_df.empty:
                        ds_table_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', data_source_name)
                        if ds_table_name not in registered_tables:
                            conn.register(ds_table_name, first_df)
                            registered_tables.append(ds_table_name)
                except Exception as e:
                    logger.warning(f"注册数据源名称表失败: {e}")
                    pass

        elif db_type == "csv":
            # CSV文件只有一个表
            df = None
            for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                try:
                    df = pd.read_csv(io.BytesIO(file_data), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if df is not None:
                table_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', data_source_name)
                if not table_name or table_name[0].isdigit():
                    table_name = f"data_{table_name}"
                conn.register(table_name, df)
                registered_tables.append(table_name)
                # 同时注册为 'data' 作为备用
                conn.register('data', df)

        if not registered_tables:
            conn.close()
            return {
                "success": False,
                "error": f"无法从文件读取任何数据: {storage_path}",
                "data": [],
                "columns": [],
                "row_count": 0
            }

        logger.info(f"成功注册 {len(registered_tables)} 个表: {registered_tables}")

        # 执行SQL查询
        try:
            result_df = conn.execute(sql_query).fetchdf()
        except Exception as sql_error:
            error_msg = str(sql_error)
            logger.warning(f"SQL执行失败: {error_msg}")
            # 提供更友好的错误信息，包含可用的表名
            conn.close()
            return {
                "success": False,
                "error": f"SQL执行失败: {error_msg}\n\n可用的表: {', '.join(registered_tables)}",
                "data": [],
                "columns": [],
                "row_count": 0
            }

        conn.close()

        # 转换结果为字典列表
        columns = list(result_df.columns)
        data = result_df.to_dict('records')

        logger.info(f"文件数据源SQL执行成功，返回 {len(data)} 行")

        return {
            "success": True,
            "data": data,
            "columns": columns,
            "row_count": len(data)
        }

    except Exception as e:
        logger.error(f"文件数据源SQL执行失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "columns": [],
            "row_count": 0
        }


async def _execute_sql_if_needed(
    content: str,
    tenant_id: str,
    db: Session,
    original_question: str = "",
    data_source_ids: Optional[List[str]] = None
) -> str:
    """
    检测AI回复中的SQL查询并执行，将结果插入回复中（带智能重试）

    Args:
        content: AI生成的回复内容
        tenant_id: 租户ID
        db: 数据库会话
        original_question: 用户原始问题（用于SQL修复）
        data_source_ids: 指定的数据源ID列表，如果为None则使用第一个活跃数据源

    Returns:
        增强后的回复内容（包含查询结果）
    """
    try:
        # 检测SQL代码块
        sql_pattern = r'```sql\s*(.*?)\s*```'
        sql_matches = re.findall(sql_pattern, content, re.DOTALL | re.IGNORECASE)

        if not sql_matches:
            return content

        # 去重：如果有多个相同的SQL，只保留第一个
        seen_sqls = set()
        unique_sql_matches = []
        for sql in sql_matches:
            normalized_sql = sql.strip().upper()  # 标准化比较
            if normalized_sql not in seen_sqls:
                seen_sqls.add(normalized_sql)
                unique_sql_matches.append(sql)
            else:
                logger.warning(f"检测到重复SQL，已跳过: {sql[:50]}...")

        sql_matches = unique_sql_matches
        logger.info(f"检测到 {len(sql_matches)} 个唯一SQL查询，准备执行")

        # 获取租户的活跃数据源
        data_sources = await data_source_service.get_data_sources(
            tenant_id=tenant_id,
            db=db,
            active_only=True
        )

        if not data_sources:
            logger.warning("没有找到活跃的数据源，无法执行SQL")
            return content + "\n\n⚠️ **注意**: 未找到已连接的数据源，无法执行SQL查询。请先在数据源管理中添加数据库连接。"

        # 如果指定了数据源ID，使用指定的第一个；否则使用第一个活跃数据源
        if data_source_ids:
            matching_sources = [ds for ds in data_sources if ds.id in data_source_ids]
            if matching_sources:
                data_source = matching_sources[0]
                logger.info(f"使用指定的数据源: {data_source.name} ({data_source.id})")
            else:
                data_source = data_sources[0]
                logger.warning(f"未找到指定的数据源，使用第一个活跃数据源: {data_source.name}")
        else:
            data_source = data_sources[0]

        # 获取解密的连接字符串
        connection_string = await data_source_service.get_decrypted_connection_string(
            data_source_id=data_source.id,
            tenant_id=tenant_id,
            db=db
        )

        # 获取schema上下文（用于SQL修复）
        schema_context = await _get_data_sources_context(tenant_id, db, data_source_ids)

        # 执行每个SQL查询
        enhanced_content = content
        for sql_query in sql_matches:
            current_sql = sql_query.strip()
            retry_count = 0
            max_retries = 2
            last_error = None
            execution_success = False

            while retry_count <= max_retries and not execution_success:
                try:
                    # 安全检查：只允许SELECT查询（包括WITH...SELECT的CTE查询）
                    sql_upper = current_sql.upper().strip()
                    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
                        logger.warning(f"跳过非SELECT查询: {current_sql[:50]}")
                        break

                    # 根据数据源类型选择执行方式
                    if data_source.db_type in ["xlsx", "xls", "csv"]:
                        # 文件类型数据源：使用duckdb执行
                        logger.info(f"使用duckdb执行文件数据源查询: {data_source.db_type}")
                        result = await _execute_sql_on_file_datasource(
                            connection_string=connection_string,
                            db_type=data_source.db_type,
                            sql_query=current_sql,
                            data_source_name=data_source.name
                        )
                        if not result.get("success", False) and result.get("error"):
                            raise Exception(result["error"])
                    else:
                        # 数据库类型数据源：使用PostgreSQLAdapter
                        adapter = PostgreSQLAdapter(connection_string)
                        try:
                            await adapter.connect()
                            query_result = await adapter.execute_query(current_sql)
                            # 将QueryResult对象转换为字典格式
                            result = {
                                "data": query_result.data,
                                "columns": query_result.columns,
                                "row_count": query_result.row_count
                            }
                        finally:
                            await adapter.disconnect()

                    # 格式化结果 - 简洁版
                    row_count = len(result.get("data", []))

                    if result.get("data") and row_count > 0:
                        # 获取列名：优先使用columns字段，否则从数据中提取
                        columns = result.get("columns") or list(result["data"][0].keys())
                        # 构建简洁的Markdown表格
                        result_text = "\n\n| " + " | ".join(columns) + " |\n"
                        result_text += "|" + "|".join(["---" for _ in columns]) + "|\n"

                        for row in result["data"][:10]:
                            row_values = [str(row.get(col, "")) for col in columns]
                            result_text += "| " + " | ".join(row_values) + " |\n"

                        # 只有当返回行数超过10行时才显示提示
                        if row_count > 10:
                            result_text += f"\n*（共{row_count}行，仅显示前10行）*\n"
                    else:
                        result_text = "\n\n*查询未返回数据*\n"

                    # 如果经过了重试，替换为修复后的SQL和结果
                    if retry_count > 0:
                        result_text += f"\n*✅ SQL已自动修复（重试{retry_count}次后成功）*\n"
                        # 完全替换原始SQL块为修复后的SQL和结果
                        sql_block = f"```sql\n{sql_query}\n```"
                        fixed_sql_block = f"**🔧 原始SQL有误，已自动修复为：**\n```sql\n{current_sql}\n```"
                        enhanced_content = enhanced_content.replace(
                            sql_block,
                            fixed_sql_block + result_text
                        )
                    else:
                        # 没有重试，直接将结果插入到SQL代码块后面
                        sql_block = f"```sql\n{sql_query}\n```"
                        enhanced_content = enhanced_content.replace(
                            sql_block,
                            sql_block + result_text
                        )

                    logger.info(f"SQL查询执行成功，返回 {len(result.get('data', []))} 行")
                    execution_success = True

                except Exception as e:
                    last_error = str(e)
                    logger.error(f"执行SQL查询失败 (尝试 {retry_count + 1}/{max_retries + 1}): {e}")

                    # 如果还有重试机会，尝试用AI修复SQL
                    if retry_count < max_retries:
                        logger.info("尝试使用AI修复SQL...")
                        fixed_sql = await _fix_sql_with_ai(
                            original_sql=current_sql,
                            error_message=last_error,
                            schema_context=schema_context,
                            original_question=original_question
                        )

                        if fixed_sql:
                            logger.info(f"AI修复成功，准备重试。修复后的SQL: {fixed_sql[:100]}...")
                            current_sql = fixed_sql
                            retry_count += 1
                        else:
                            logger.warning("AI无法修复SQL，停止重试")
                            break
                    else:
                        # 已达到最大重试次数
                        logger.error(f"已达到最大重试次数 ({max_retries})，放弃执行")
                        break

            # 如果所有重试都失败了，显示错误信息
            if not execution_success and last_error:
                # 解析错误信息，提取关键信息
                error_details = _parse_sql_error(last_error)

                # 构建错误信息
                error_text = f"\n\n❌ **查询执行失败**: {error_details['main_error']}\n"

                # 如果有HINT信息，显示它
                if error_details.get('hint'):
                    error_text += f"\n💡 **提示**: {error_details['hint']}\n"

                # 如果经过了重试，显示最后尝试的SQL
                if retry_count > 0:
                    error_text += f"\n*已尝试自动修复 {retry_count} 次，但仍然失败*\n"
                    error_text += f"\n**最后尝试的SQL：**\n```sql\n{current_sql}\n```\n"

                # 添加建议
                if error_details.get('suggestion'):
                    error_text += f"\n💡 **建议**: {error_details['suggestion']}\n"
                else:
                    error_text += "\n💡 **建议**: 请检查表名和列名是否正确，或查看数据源的schema信息。\n"

                # 替换原始SQL块
                sql_block = f"```sql\n{sql_query}\n```"
                if retry_count > 0:
                    # 如果经过重试，完全替换为错误信息（不显示原始SQL）
                    enhanced_content = enhanced_content.replace(
                        sql_block,
                        f"**⚠️ 原始SQL有误，尝试修复后仍然失败：**\n{error_text}"
                    )
                else:
                    # 没有重试，在原始SQL后添加错误信息
                    enhanced_content = enhanced_content.replace(
                        sql_block,
                        sql_block + error_text
                    )

        return enhanced_content

    except Exception as e:
        logger.error(f"SQL执行处理失败: {e}")
        return content


def _convert_response(response: LLMResponse) -> ChatCompletionResponse:
    """转换响应格式"""
    return ChatCompletionResponse(
        content=response.content,
        thinking=response.thinking,
        usage=response.usage,
        model=response.model,
        provider=response.provider,
        finish_reason=response.finish_reason,
        created_at=response.created_at
    )


async def _execute_tool_call(
    tool_call: Dict[str, Any],
    tenant_id: str,
    db: Session,
    data_source_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    执行工具调用（目前只支持 execute_sql）
    
    Returns:
        Dict with keys: success, result, error
    """
    try:
        tool_name = tool_call.get("function", {}).get("name", "")
        tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
        
        # 解析工具参数
        try:
            tool_args = json.loads(tool_args_str)
        except json.JSONDecodeError:
            return {
                "success": False,
                "result": None,
                "error": f"无法解析工具参数: {tool_args_str}"
            }
        
        if tool_name == "execute_sql":
            sql_query = tool_args.get("sql_query", "")
            if not sql_query:
                return {
                    "success": False,
                    "result": None,
                    "error": "SQL查询语句为空"
                }
            
            # 安全检查：只允许SELECT查询
            if not sql_query.strip().upper().startswith('SELECT'):
                return {
                    "success": False,
                    "result": None,
                    "error": "只允许执行 SELECT 查询，禁止执行修改操作"
                }
            
            # 获取数据源
            data_sources = await data_source_service.get_data_sources(
                tenant_id=tenant_id,
                db=db,
                active_only=True
            )
            
            if not data_sources:
                return {
                    "success": False,
                    "result": None,
                    "error": "未找到活跃的数据源"
                }
            
            # 选择数据源
            if data_source_ids:
                matching_sources = [ds for ds in data_sources if ds.id in data_source_ids]
                if matching_sources:
                    data_source = matching_sources[0]
                else:
                    data_source = data_sources[0]
            else:
                data_source = data_sources[0]
            
            # 获取连接字符串
            connection_string = await data_source_service.get_decrypted_connection_string(
                data_source_id=data_source.id,
                tenant_id=tenant_id,
                db=db
            )
            
            # 执行SQL
            try:
                if data_source.db_type in ["xlsx", "xls", "csv"]:
                    # 文件类型数据源
                    result = await _execute_sql_on_file_datasource(
                        connection_string=connection_string,
                        db_type=data_source.db_type,
                        sql_query=sql_query,
                        data_source_name=data_source.name
                    )
                    if not result.get("success", False):
                        return {
                            "success": False,
                            "result": None,
                            "error": result.get("error", "执行失败")
                        }
                else:
                    # 数据库类型数据源
                    adapter = PostgreSQLAdapter(connection_string)
                    try:
                        await adapter.connect()
                        query_result = await adapter.execute_query(sql_query)
                        result = {
                            "data": query_result.data,
                            "columns": query_result.columns,
                            "row_count": query_result.row_count
                        }
                    finally:
                        await adapter.disconnect()
                
                # 格式化结果为JSON字符串
                result_json = json.dumps(result, ensure_ascii=False, default=str)
                return {
                    "success": True,
                    "result": result_json,
                    "error": None
                }
            except Exception as e:
                logger.error(f"执行SQL失败: {e}", exc_info=True)
                return {
                    "success": False,
                    "result": None,
                    "error": str(e)
                }
        
        elif tool_name == "generate_chart":
            # 处理图表生成工具调用
            try:
                chart_type = tool_args.get("chart_type", "bar")
                title = tool_args.get("title", "数据图表")
                x_data = tool_args.get("x_data", [])
                y_data = tool_args.get("y_data", [])
                series_name = tool_args.get("series_name", "数据")
                
                logger.info(f"生成图表: type={chart_type}, title={title}, x_data_len={len(x_data)}, y_data_len={len(y_data)}")
                
                # 根据图表类型生成 ECharts 配置
                if chart_type == "pie":
                    # 饼图需要特殊的数据格式
                    pie_data = [{"name": x, "value": y} for x, y in zip(x_data, y_data)]
                    echarts_option = {
                        "title": {"text": title, "left": "center"},
                        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                        "legend": {"orient": "vertical", "left": "left"},
                        "series": [{
                            "type": "pie",
                            "radius": "50%",
                            "data": pie_data,
                            "emphasis": {
                                "itemStyle": {
                                    "shadowBlur": 10,
                                    "shadowOffsetX": 0,
                                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                                }
                            }
                        }]
                    }
                else:
                    # 柱状图、折线图、散点图
                    echarts_option = {
                        "title": {"text": title, "left": "center"},
                        "tooltip": {"trigger": "axis"},
                        "xAxis": {"type": "category", "data": x_data},
                        "yAxis": {"type": "value"},
                        "series": [{
                            "name": series_name,
                            "type": chart_type,
                            "data": y_data,
                            "smooth": True if chart_type == "line" else False
                        }]
                    }
                
                # 返回 ECharts 配置
                result = {
                    "chart_generated": True,
                    "echarts_option": echarts_option
                }
                
                return {
                    "success": True,
                    "result": json.dumps(result, ensure_ascii=False),
                    "error": None,
                    "echarts_option": echarts_option  # 额外返回配置，方便直接使用
                }
            except Exception as e:
                logger.error(f"生成图表失败: {e}", exc_info=True)
                return {
                    "success": False,
                    "result": None,
                    "error": f"图表生成失败: {str(e)}"
                }
        
        else:
            return {
                "success": False,
                "result": None,
                "error": f"未知的工具: {tool_name}"
            }
    except Exception as e:
        logger.error(f"执行工具调用失败: {e}", exc_info=True)
        return {
            "success": False,
            "result": None,
            "error": str(e)
        }


async def _stream_response_generator(
    stream_generator,
    tenant_id: str,
    db: Session,
    original_question: str = "",
    data_source_ids: Optional[List[str]] = None,
    initial_messages: Optional[List[LLMMessage]] = None
):
    """
    流式响应生成器（方案B：SQL 代码块检测模式）
    
    不使用 Function Calling，而是检测 AI 输出中的 ```sql ... ``` 代码块，
    自动执行 SQL 查询并进行第二次 LLM 调用。
    """
    try:
        # 收集完整的响应内容
        full_content = ""
        thinking_content = ""
        
        # 消息历史（用于二次调用）
        messages = initial_messages or []

        async for chunk in stream_generator:
            # 处理普通内容
            if chunk.type == "content":
                # 发送原始chunk
                chunk_data = {
                    "type": chunk.type,
                    "content": chunk.content,
                    "provider": chunk.provider,
                    "finished": chunk.finished,
                    "tenant_id": tenant_id
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                full_content += chunk.content
            
            elif chunk.type == "thinking":
                thinking_content += chunk.content
                # 发送thinking chunk
                chunk_data = {
                    "type": chunk.type,
                    "content": chunk.content,
                    "provider": chunk.provider,
                    "finished": chunk.finished,
                    "tenant_id": tenant_id
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            # 如果流结束，检测并执行 SQL（方案B）
            if chunk.finished:
                logger.info(f"流式响应完成，检测SQL查询。内容长度: {len(full_content)}")

                # 检测SQL代码块
                sql_pattern = r'```sql\s*(.*?)\s*```'
                sql_matches = re.findall(sql_pattern, full_content, re.DOTALL | re.IGNORECASE)

                if sql_matches:
                    # 去重：如果有多个相同的SQL，只保留第一个
                    seen_sqls = set()
                    unique_sql_matches = []
                    for sql in sql_matches:
                        normalized_sql = sql.strip().upper()  # 标准化比较
                        if normalized_sql not in seen_sqls:
                            seen_sqls.add(normalized_sql)
                            unique_sql_matches.append(sql)
                        else:
                            logger.warning(f"流式响应：检测到重复SQL，已跳过: {sql[:50]}...")

                    sql_matches = unique_sql_matches
                    logger.info(f"检测到 {len(sql_matches)} 个唯一SQL查询，准备执行")

                    # 获取租户的活跃数据源
                    data_sources = await data_source_service.get_data_sources(
                        tenant_id=tenant_id,
                        db=db,
                        active_only=True
                    )

                    if data_sources:
                        # 如果指定了数据源ID，使用指定的第一个；否则使用第一个活跃数据源
                        if data_source_ids:
                            matching_sources = [ds for ds in data_sources if ds.id in data_source_ids]
                            if matching_sources:
                                data_source = matching_sources[0]
                                logger.info(f"流式响应：使用指定的数据源: {data_source.name} ({data_source.id})")
                            else:
                                data_source = data_sources[0]
                                logger.warning(f"流式响应：未找到指定的数据源，使用第一个活跃数据源: {data_source.name}")
                        else:
                            data_source = data_sources[0]

                        # 获取解密的连接字符串
                        connection_string = await data_source_service.get_decrypted_connection_string(
                            data_source_id=data_source.id,
                            tenant_id=tenant_id,
                            db=db
                        )

                        # 获取schema上下文（用于SQL修复）
                        schema_context = await _get_data_sources_context(tenant_id, db, data_source_ids)

                        # 执行每个SQL查询（带智能重试）
                        for sql_query in sql_matches:
                            current_sql = sql_query.strip()
                            retry_count = 0
                            max_retries = 2
                            last_error = None
                            execution_success = False

                            while retry_count <= max_retries and not execution_success:
                                try:
                                    # 安全检查：只允许SELECT查询（包括WITH...SELECT的CTE查询）
                                    sql_upper = current_sql.upper().strip()
                                    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
                                        logger.warning(f"跳过非SELECT查询: {current_sql[:50]}")
                                        break

                                    # 根据数据源类型选择执行方式
                                    if data_source.db_type in ["xlsx", "xls", "csv"]:
                                        # 文件类型数据源：使用duckdb执行
                                        logger.info(f"流式响应：使用duckdb执行文件数据源查询: {data_source.db_type}")
                                        result = await _execute_sql_on_file_datasource(
                                            connection_string=connection_string,
                                            db_type=data_source.db_type,
                                            sql_query=current_sql,
                                            data_source_name=data_source.name
                                        )
                                        if not result.get("success", False) and result.get("error"):
                                            raise Exception(result["error"])
                                    else:
                                        # 数据库类型数据源：使用PostgreSQLAdapter
                                        adapter = PostgreSQLAdapter(connection_string)
                                        try:
                                            await adapter.connect()
                                            query_result = await adapter.execute_query(current_sql)
                                            # 将QueryResult对象转换为字典格式
                                            result = {
                                                "data": query_result.data,
                                                "columns": query_result.columns,
                                                "row_count": query_result.row_count
                                            }
                                        finally:
                                            await adapter.disconnect()

                                    # 格式化结果 - 简洁版
                                    row_count = result.get('row_count', 0)

                                    if result.get('data'):
                                        data = result['data'][:10]
                                        if data:
                                            headers = list(data[0].keys())
                                            # 构建简洁的Markdown表格
                                            result_text = "\n\n| " + " | ".join(headers) + " |\n"
                                            result_text += "|" + "|".join(["---"] * len(headers)) + "|\n"

                                            for row in data:
                                                values = [str(row.get(h, '')) for h in headers]
                                                result_text += "| " + " | ".join(values) + " |\n"

                                            # 只有当返回行数超过10行时才显示提示
                                            if row_count > 10:
                                                result_text += f"\n*（共{row_count}行，仅显示前10行）*\n"
                                        else:
                                            result_text = "\n\n*查询未返回数据*\n"
                                    else:
                                        result_text = "\n\n*查询未返回数据*\n"

                                    # 如果经过了重试，发送修复说明
                                    if retry_count > 0:
                                        result_text += f"\n*✅ SQL已自动修复（重试{retry_count}次后成功）*\n"
                                        # 发送修复后的SQL
                                        fix_info = f"\n\n**🔧 原始SQL有误，已自动修复为：**\n```sql\n{current_sql}\n```\n"
                                        fix_chunk = {
                                            "type": "content",
                                            "content": fix_info,
                                            "provider": chunk.provider,
                                            "finished": False,
                                            "tenant_id": tenant_id
                                        }
                                        yield f"data: {json.dumps(fix_chunk, ensure_ascii=False)}\n\n"

                                    # 发送查询结果作为新的content chunk
                                    result_chunk = {
                                        "type": "content",
                                        "content": result_text,
                                        "provider": chunk.provider,
                                        "finished": False,
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(result_chunk, ensure_ascii=False)}\n\n"

                                    logger.info(f"SQL查询执行成功，返回 {result.get('row_count', 0)} 行")
                                    execution_success = True
                                    
                                    # 🔧 方案B增强：二次LLM调用，分析数据并生成图表
                                    if execution_success and result.get('data'):
                                        logger.info("开始二次LLM调用：分析数据并生成图表")
                                        
                                        # --- 🧠 数据特征分析与决策注入 ---
                                        data_for_analysis = result['data'][:20]  # 最多取20行用于分析
                                        analysis_row_count = len(result['data'])
                                        
                                        # 获取列信息
                                        columns = result.get('columns', [])
                                        if not columns and data_for_analysis:
                                            columns = list(data_for_analysis[0].keys())
                                        col_count = len(columns)
                                        
                                        # 简单的类型推断：检查列名是否包含时间关键词
                                        col_names_str = " ".join([str(c).lower() for c in columns])
                                        has_time_col = any(k in col_names_str for k in ['date', 'time', 'year', 'month', 'day', 'quarter', 'week', '日期', '时间', '年', '月', '日'])
                                        has_metric_col = col_count >= 2  # 假设除了维度还有指标
                                        
                                        analysis_directive = ""
                                        
                                        # 规则 1: 单行数据或纯文本 -> 禁止画图
                                        if analysis_row_count <= 1:
                                            analysis_directive = (
                                                "🛑 **CONSTRAINT**: The result contains only 1 row.\n"
                                                "- **DO NOT** call `generate_chart`. Visualization is useless for a single number.\n"
                                                "- Focus on explaining the value directly."
                                            )
                                        elif not has_metric_col and analysis_row_count < 50:
                                            analysis_directive = (
                                                "🛑 **CONSTRAINT**: This appears to be a text list without numerical metrics.\n"
                                                "- **DO NOT** call `generate_chart`.\n"
                                                "- Summarize the list content (e.g., total count, examples)."
                                            )
                                        # 规则 2: 大数据量 -> 强制 Top N
                                        elif analysis_row_count > 20 and not has_time_col:
                                            analysis_directive = (
                                                f"⚠️ **CONSTRAINT**: The result has {analysis_row_count} rows, which is too many for a clean chart.\n"
                                                "- **ACTION**: Use `generate_chart` but ONLY include the **Top 10** data points in the `data` parameter.\n"
                                                "- In your text analysis, mention that you are showing the top performers."
                                            )
                                        # 规则 3: 时间序列 -> 强制折线图
                                        elif has_time_col and analysis_row_count > 1:
                                            analysis_directive = (
                                                "✅ **STRATEGY**: This is time-series data.\n"
                                                "- **ACTION**: You MUST call `generate_chart` with `chart_type='line'`.\n"
                                                "- **Analysis**: Focus on the trend (upward/downward), seasonality, or spikes."
                                            )
                                        # 规则 4: 分类对比 -> 建议柱状图或饼图
                                        else:
                                            chart_suggestion = "pie" if analysis_row_count <= 8 else "bar"
                                            analysis_directive = (
                                                f"✅ **STRATEGY**: This is categorical comparison data.\n"
                                                f"- **ACTION**: You SHOULD call `generate_chart` with `chart_type='{chart_suggestion}'`.\n"
                                                "- **Analysis**: Compare the magnitudes. Identify the leader and the laggard."
                                            )
                                        
                                        logger.info(f"数据特征分析: rows={analysis_row_count}, cols={col_count}, has_time={has_time_col}, has_metric={has_metric_col}")
                                        
                                        # 构建分析提示（包含决策指令）
                                        # 将 Decimal 类型转换为 float，避免 JSON 序列化失败
                                        serializable_data = _convert_decimal_to_float(data_for_analysis)
                                        data_json = json.dumps(serializable_data, ensure_ascii=False, indent=2)
                                        
                                        analysis_prompt = f"""你刚刚查询了数据，结果如下：

```json
{data_json}
```

--- ANALYSIS INSTRUCTIONS ---
{analysis_directive}

请完成以下任务：

1. **数据分析**：用 2-3 句话分析数据的关键洞察，解释数据的商业含义（不要只重复数字）

2. **生成 ECharts 图表配置**（如果上述指令允许）：
   
   ⚠️ **格式要求（必须严格遵守）**：
   - 必须使用 `[CHART_START]` 开始，`[CHART_END]` 结束
   - 中间是**标准 ECharts JSON 配置**（不是自定义格式！）
   - 不要使用 markdown 代码块包裹 JSON
   
   ✅ **正确示例（柱状图）**：
[CHART_START]
{{"title":{{"text":"商品库存排名"}},"tooltip":{{"trigger":"axis"}},"xAxis":{{"type":"category","data":["华为MateBook","iPhone 15","小米电视"]}},"yAxis":{{"type":"value","name":"库存数量"}},"series":[{{"name":"库存","type":"bar","data":[100,80,50]}}]}}
[CHART_END]

   ✅ **正确示例（饼图）**：
[CHART_START]
{{"title":{{"text":"销售占比"}},"tooltip":{{"trigger":"item"}},"series":[{{"name":"销售额","type":"pie","radius":"50%","data":[{{"value":1048,"name":"产品A"}},{{"value":735,"name":"产品B"}}]}}]}}
[CHART_END]

   ❌ **错误格式（不要这样写）**：
   - {{"chartType": "bar", "xAxis": {{"field": "name"}}}} ← 这不是 ECharts 格式！

请直接输出分析和图表："""

                                        # 构建专家数据分析师的系统提示
                                        expert_system_prompt = (
                                            "你是一位专业的数据分析师。你的任务是从数据中提取洞察并有效地可视化它们。\n\n"
                                            "**核心协议：**\n"
                                            "1. **遵循指令**：系统会分析数据形态并给出具体约束（如'禁止画图'或'只画 Top 10'）。你必须严格遵守。\n"
                                            "2. **数据分析**：不要只重复数字。解释数据的意义（例如，不要说'A是100，B是50'，而要说'A的表现是B的2倍'）。\n"
                                            "3. **图表格式**：当需要生成图表时，必须使用标准的 ECharts JSON 配置格式，用 [CHART_START] 和 [CHART_END] 标记包裹。\n\n"
                                            "**重要提醒：**\n"
                                            "- 图表配置必须是标准 ECharts 格式，包含 title、xAxis、yAxis、series 等字段\n"
                                            "- 不要使用自定义的简化格式如 {chartType: 'bar', xAxis: {field: 'name'}}\n"
                                            "- 直接输出 JSON，不要用 markdown 代码块包裹"
                                        )
                                        
                                        # 构建消息历史
                                        analysis_messages = [
                                            LLMMessage(role="system", content=expert_system_prompt),
                                            LLMMessage(role="user", content=original_question),
                                            LLMMessage(role="assistant", content=f"让我查询相关数据：\n\n```sql\n{current_sql}\n```\n\n{result_text}"),
                                            LLMMessage(role="user", content=analysis_prompt)
                                        ]
                                        
                                        # 获取provider实例
                                        provider_instance = llm_service.get_provider(tenant_id, LLMProvider.DEEPSEEK)
                                        if provider_instance:
                                            try:
                                                # 发送分析状态
                                                analysis_status = {
                                                    "type": "content",
                                                    "content": "\n\n📊 **数据分析中...**\n\n",
                                                    "provider": chunk.provider,
                                                    "finished": False,
                                                    "tenant_id": tenant_id
                                                }
                                                yield f"data: {json.dumps(analysis_status, ensure_ascii=False)}\n\n"
                                                
                                                # 二次调用LLM（流式）
                                                analysis_stream = await provider_instance.chat_completion(
                                                    messages=analysis_messages,
                                                    model=None,
                                                    max_tokens=2000,
                                                    temperature=0.7,
                                                    stream=True,
                                                    tools=None
                                                )
                                                
                                                # 流式输出分析结果
                                                analysis_content = ""
                                                async for analysis_chunk in analysis_stream:
                                                    if analysis_chunk.type == "content" and analysis_chunk.content:
                                                        analysis_content += analysis_chunk.content
                                                        analysis_data = {
                                                            "type": "content",
                                                            "content": analysis_chunk.content,
                                                            "provider": analysis_chunk.provider,
                                                            "finished": False,
                                                            "tenant_id": tenant_id
                                                        }
                                                        yield f"data: {json.dumps(analysis_data, ensure_ascii=False)}\n\n"
                                                
                                                logger.info(f"二次LLM调用完成，分析内容长度: {len(analysis_content)}")
                                                
                                                # 检测并提取图表配置
                                                chart_pattern = r'\[CHART_START\](.*?)\[CHART_END\]'
                                                chart_match = re.search(chart_pattern, analysis_content, re.DOTALL)
                                                
                                                if chart_match:
                                                    try:
                                                        chart_json_str = chart_match.group(1).strip()
                                                        echarts_option = json.loads(chart_json_str)
                                                        logger.info(f"✅ 成功提取 ECharts 配置: {list(echarts_option.keys())}")
                                                        
                                                        # 发送图表配置事件
                                                        chart_event = {
                                                            "type": "chart_config",
                                                            "data": {"echarts_option": echarts_option},
                                                            "provider": "deepseek",
                                                            "finished": False,
                                                            "tenant_id": tenant_id
                                                        }
                                                        yield f"data: {json.dumps(chart_event, ensure_ascii=False)}\n\n"
                                                    except json.JSONDecodeError as e:
                                                        logger.warning(f"解析 ECharts JSON 失败: {e}")
                                                
                                            except Exception as e:
                                                logger.error(f"二次LLM调用失败: {e}")

                                except Exception as e:
                                    last_error = str(e)
                                    logger.error(f"执行SQL查询失败 (尝试 {retry_count + 1}/{max_retries + 1}): {e}")

                                    # 如果还有重试机会，尝试用AI修复SQL
                                    if retry_count < max_retries:
                                        logger.info("尝试使用AI修复SQL...")
                                        fixed_sql = await _fix_sql_with_ai(
                                            original_sql=current_sql,
                                            error_message=last_error,
                                            schema_context=schema_context,
                                            original_question=original_question
                                        )

                                        if fixed_sql:
                                            logger.info(f"AI修复成功，准备重试。修复后的SQL: {fixed_sql[:100]}...")
                                            current_sql = fixed_sql
                                            retry_count += 1
                                        else:
                                            logger.warning("AI无法修复SQL，停止重试")
                                            break
                                    else:
                                        # 已达到最大重试次数
                                        logger.error(f"已达到最大重试次数 ({max_retries})，放弃执行")
                                        break

                            # 如果所有重试都失败了，发送错误信息
                            if not execution_success and last_error:
                                # 解析错误信息，提取关键信息
                                error_details = _parse_sql_error(last_error)

                                error_text = f"\n\n❌ **查询执行失败**: {error_details['main_error']}\n"

                                # 如果有HINT信息，显示它
                                if error_details.get('hint'):
                                    error_text += f"\n💡 **提示**: {error_details['hint']}\n"

                                # 如果经过了重试，显示最后尝试的SQL
                                if retry_count > 0:
                                    error_text += f"\n*已尝试自动修复 {retry_count} 次，但仍然失败*\n"
                                    error_text += f"\n**最后尝试的SQL：**\n```sql\n{current_sql}\n```\n"

                                # 添加建议
                                if error_details.get('suggestion'):
                                    error_text += f"\n💡 **建议**: {error_details['suggestion']}\n"
                                else:
                                    error_text += "\n💡 **建议**: 请检查表名和列名是否正确，或查看数据源的schema信息。\n"

                                error_chunk = {
                                    "type": "content",
                                    "content": error_text,
                                    "provider": chunk.provider,
                                    "finished": False,
                                    "tenant_id": tenant_id
                                }
                                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                    else:
                        logger.warning("没有找到活跃的数据源，无法执行SQL")
                        warning_text = "\n\n⚠️ **注意**: 未找到已连接的数据源，无法执行SQL查询。请先在数据源管理中添加数据库连接。\n"

                        warning_chunk = {
                            "type": "content",
                            "content": warning_text,
                            "provider": chunk.provider,
                            "finished": False,
                            "tenant_id": tenant_id
                        }
                        yield f"data: {json.dumps(warning_chunk, ensure_ascii=False)}\n\n"

        # 🔧 恢复图表生成功能：检测并提取 [CHART_START]...[CHART_END] 标记中的 ECharts 配置
        chart_pattern = r'\[CHART_START\](.*?)\[CHART_END\]'
        chart_match = re.search(chart_pattern, full_content, re.DOTALL)
        
        if chart_match:
            try:
                chart_json_str = chart_match.group(1).strip()
                # 解析 JSON
                echarts_option = json.loads(chart_json_str)
                logger.info(f"✅ 成功提取 ECharts 配置: {list(echarts_option.keys())}")
                
                # 发送图表配置事件
                chart_chunk = {
                    "type": "chart_config",
                    "data": {
                        "echarts_option": echarts_option
                    },
                    "provider": "deepseek",
                    "finished": False,
                    "tenant_id": tenant_id
                }
                yield f"data: {json.dumps(chart_chunk, ensure_ascii=False)}\n\n"
                
                # 可选：从最终内容中移除图表标记（前端可能已经显示了）
                # 这里我们保留标记，让前端自己决定是否显示
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ 解析 ECharts JSON 失败: {e}")
                logger.warning(f"原始内容: {chart_json_str[:200]}...")
            except Exception as e:
                logger.error(f"❌ 提取 ECharts 配置时发生错误: {e}")

        # 发送结束标记
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"流式响应生成器错误: {e}")
        error_data = {
            "type": "error",
            "content": f"Stream error: {str(e)}",
            "provider": "unknown",
            "finished": True,
            "tenant_id": tenant_id
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completion(
    request: ChatCompletionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant),
    db: Session = Depends(get_db)
):
    """
    聊天完成接口
    支持多提供商、多模态和流式输出
    自动获取用户数据源信息并添加到上下文
    """
    try:
        # 获取tenant_id，支持开发环境下的默认租户
        tenant_id = getattr(current_user, 'tenant_id', None) or current_user.get('tenant_id', 'default_tenant')
        logger.info(f"Chat completion request for tenant: {tenant_id}, stream={request.stream}, data_source_ids={request.data_source_ids}")
        print(f"[DEBUG] Chat completion request - stream={request.stream}, data_source_ids={request.data_source_ids}")
        # 强制输出到日志文件
        import sys
        print(f"[DEBUG] Chat completion request - stream={request.stream}, data_source_ids={request.data_source_ids}", file=sys.stderr)

        # 转换提供商
        provider = None
        if request.provider:
            try:
                provider = LLMProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {request.provider}"
                )

        # 获取数据源上下文，如果指定了数据源ID则只获取指定的数据源
        print(f"[DEBUG] Starting _get_data_sources_context for tenant: {tenant_id}, data_source_ids: {request.data_source_ids}")
        import time as _time
        _ctx_start = _time.time()
        data_sources_context = await _get_data_sources_context(tenant_id, db, request.data_source_ids)
        print(f"[DEBUG] _get_data_sources_context took {_time.time() - _ctx_start:.2f}s")
        if data_sources_context:
            logger.info(f"Data sources context retrieved for tenant {tenant_id}, length: {len(data_sources_context)}")
            # 调试日志：打印数据源上下文的前1000个字符
            logger.debug(f"Data sources context content (first 1000 chars): {data_sources_context[:1000]}")
        else:
            logger.info(f"No data sources found for tenant {tenant_id}")

        # 转换消息格式
        messages = _convert_chat_messages(request.messages)

        # 检查是否已有system消息，如果没有则添加包含数据源上下文的system消息
        has_system_message = any(msg.role == "system" for msg in messages)
        if not has_system_message:
            system_prompt = _build_system_prompt_with_context(data_sources_context)
            system_message = LLMMessage(role="system", content=system_prompt)
            messages.insert(0, system_message)
            logger.info("Added system message with data sources context")
        elif data_sources_context:
            # 如果已有system消息，替换为完整的数据分析系统提示（包含SQL生成指令）
            # 这样确保AI知道如何正确生成SQL查询
            full_system_prompt = _build_system_prompt_with_context(data_sources_context)
            for i, msg in enumerate(messages):
                if msg.role == "system":
                    messages[i] = LLMMessage(role="system", content=full_system_prompt, thinking=msg.thinking)
                    logger.info("Replaced existing system message with full data sources context and SQL instructions")
                    break

        # 提取用户的最后一条消息作为原始问题
        original_question = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                original_question = msg.content
                break

        # 调用LLM服务
        if request.stream:
            # 流式响应
            # 注意：chat_completion 是异步函数，需要 await 来获取 AsyncGenerator
            logger.info(f"[STREAM] Starting stream request for tenant {tenant_id}")
            print(f"[STREAM] Starting stream request for tenant {tenant_id}", file=sys.stderr)
            
            # 方案 B: 不使用 Function Calling，改用 SQL 代码块检测
            # DeepSeek 不支持标准的 OpenAI Function Calling 协议
            # 所以我们让 AI 直接在回答中输出 ```sql ... ``` 代码块，然后自动检测并执行
            logger.info(f"[STREAM] 使用 SQL 代码块检测模式（方案B）")
            
            response_generator = await llm_service.chat_completion(
                tenant_id=tenant_id,
                messages=messages,
                provider=provider,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=request.stream,
                enable_thinking=request.enable_thinking,
                tools=None  # 不传递工具定义，使用 SQL 代码块检测
            )
            
            logger.info(f"[STREAM] Stream generator created, starting response")
            return StreamingResponse(
                _stream_response_generator(
                    response_generator, 
                    tenant_id, 
                    db, 
                    original_question, 
                    request.data_source_ids,
                    initial_messages=messages  # 传递初始消息历史
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )
        else:
            # 非流式响应
            llm_start = time.time()
            response = await llm_service.chat_completion(
                tenant_id=tenant_id,
                messages=messages,
                provider=provider,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=request.stream,
                enable_thinking=request.enable_thinking
            )
            logger.info(f"[PERF] llm_service.chat_completion took {time.time() - llm_start:.2f}s")

            if isinstance(response, LLMResponse):
                # 检测并执行SQL查询（使用之前提取的原始问题和指定的数据源）
                enhanced_content = await _execute_sql_if_needed(
                    response.content,
                    tenant_id,
                    db,
                    original_question,
                    request.data_source_ids
                )

                # 更新响应内容
                response.content = enhanced_content

                return _convert_response(response)
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response type from LLM service"
                )

    except Exception as e:
        logger.error(f"Chat completion failed for tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat completion failed: {str(e)}"
        )


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取LLM提供商状态
    """
    try:
        tenant_id = current_user.tenant_id
        status = await llm_service.validate_providers(tenant_id)

        return ProviderStatusResponse(
            zhipu=status.get("zhipu", False),
            openrouter=status.get("openrouter", False)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider status: {str(e)}"
        )


@router.get("/models", response_model=AvailableModelsResponse)
async def get_available_models(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取可用模型列表
    """
    try:
        tenant_id = current_user.tenant_id
        models = await llm_service.get_available_models(tenant_id)

        return AvailableModelsResponse(providers=models)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available models: {str(e)}"
        )


@router.post("/test")
async def test_llm_service(
    provider: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    测试LLM服务
    """
    try:
        tenant_id = current_user.tenant_id

        # 转换提供商
        llm_provider = None
        if provider:
            try:
                llm_provider = LLMProvider(provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {provider}"
                )

        # 创建测试消息
        test_messages = [
            LLMMessage(
                role="user",
                content="你好，请回复一条简短的测试消息"
            )
        ]

        # 调用LLM服务
        response = await llm_service.chat_completion(
            tenant_id=tenant_id,
            messages=test_messages,
            provider=llm_provider,
            max_tokens=50
        )

        if isinstance(response, LLMResponse):
            return {
                "success": True,
                "response": _convert_response(response).dict(),
                "message": "LLM service test successful"
            }
        else:
            return {
                "success": False,
                "message": "Unexpected response type"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"LLM service test failed: {str(e)}"
        }


@router.post("/test/multimodal")
async def test_multimodal(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    测试多模态功能（需要OpenRouter）
    """
    try:
        tenant_id = current_user.tenant_id

        # 创建多模态测试消息
        multimodal_content = [
            {
                "type": "text",
                "text": "请描述这张图片中的内容"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                }
            }
        ]

        test_messages = [
            LLMMessage(
                role="user",
                content=multimodal_content
            )
        ]

        # 优先使用OpenRouter进行多模态测试
        response = await llm_service.chat_completion(
            tenant_id=tenant_id,
            messages=test_messages,
            provider=LLMProvider.OPENROUTER,
            max_tokens=200
        )

        if isinstance(response, LLMResponse):
            return {
                "success": True,
                "response": _convert_response(response).dict(),
                "message": "Multimodal test successful"
            }
        else:
            return {
                "success": False,
                "message": "Unexpected response type"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Multimodal test failed: {str(e)}"
        }


# ===== 新增的高级LLM功能测试端点 =====

@router.get("/test/stream-thinking")
async def test_stream_thinking(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试流式输出和思考模式
    """
    try:
        from src.app.services.llm_service import LLMMessage

        messages = [
            LLMMessage(
                role="user",
                content="请详细分析机器学习的核心概念和实际应用场景"
            )
        ]

        async def stream_generator():
            try:
                # 必须先 await 获取 AsyncGenerator 对象
                response_generator = await llm_service.chat_completion(
                    tenant_id=current_user.id,
                    messages=messages,
                    stream=True,
                    enable_thinking=None  # 自动判断
                )
                # 然后才能使用 async for 迭代生成器
                async for chunk in response_generator:
                    yield f"data: {json.dumps(chunk.dict(), ensure_ascii=False)}\n\n"

                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {{'type': 'error', 'content': '{str(e)}'}}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream thinking test failed: {str(e)}")


@router.get("/test/intelligent-params")
async def test_intelligent_params(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试智能参数调整功能
    """
    try:
        from src.app.services.llm_service import LLMMessage

        # 测试不同复杂度的问题
        test_cases = [
            {
                "name": "简单问题",
                "messages": [LLMMessage(role="user", content="你好")]
            },
            {
                "name": "复杂问题",
                "messages": [LLMMessage(
                    role="user",
                    content="请详细分析深度学习在计算机视觉领域的应用，包括卷积神经网络的原理、常见的架构设计、训练技巧以及在实际项目中的部署策略，并讨论当前面临的挑战和未来发展方向。"
                )]
            },
            {
                "name": "需要思考的问题",
                "messages": [LLMMessage(
                    role="user",
                    content="为什么Transformer架构能够超越传统的RNN模型？请从注意力机制、并行计算能力、长期依赖处理等多个角度进行深入分析。"
                )]
            }
        ]

        results = []

        for case in test_cases:
            complexity = llm_service.analyze_conversation_complexity(case["messages"])

            # 使用智能参数调用
            response = await llm_service.chat_completion(
                tenant_id=current_user.id,
                messages=case["messages"],
                enable_thinking=None,  # 自动判断
                temperature=complexity.get("recommend_temperature", 0.7),
                max_tokens=complexity.get("recommend_max_tokens", getattr(settings, "llm_max_output_tokens", 8192))
            )

            results.append({
                "case_name": case["name"],
                "complexity_analysis": complexity,
                "response_type": type(response).__name__,
                "success": response is not None
            })

        return {
            "success": True,
            "message": "Intelligent parameter adjustment test completed",
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intelligent params test failed: {str(e)}")


@router.get("/test/multimodal-upload")
async def test_multimodal_upload(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试多模态内容处理和MinIO上传
    """
    try:
        from src.app.services.llm_service import LLMMessage
        from src.app.services.multimodal_processor import multimodal_processor

        # 构建包含图片URL的测试消息
        test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"

        messages = [
            LLMMessage(
                role="user",
                content=[
                    {
                        "type": "text",
                        "text": "请描述这张图片的内容"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": test_image_url
                        }
                    }
                ]
            )
        ]

        # 测试多模态处理
        processed_content = await multimodal_processor.process_content_list(
            messages[0].content,
            current_user.id
        )

        # 尝试调用OpenRouter（支持多模态）
        response = await llm_service.chat_completion(
            tenant_id=current_user.id,
            messages=messages,
            provider=LLMProvider.OPENROUTER,
            stream=False
        )

        return {
            "success": True,
            "message": "Multimodal upload test completed",
            "original_content_count": len(messages[0].content),
            "processed_content_count": len(processed_content),
            "response_received": response is not None,
            "processed_sample": processed_content[:2] if processed_content else []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multimodal upload test failed: {str(e)}")


@router.get("/test/tenant-isolation")
async def test_tenant_isolation(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试租户隔离功能
    """
    try:
        from src.app.services.tenant_config_manager import tenant_config_manager, ProviderType

        # 测试租户配置获取
        test_tenant_id = current_user.id
        providers = []

        for provider in [ProviderType.ZHIPU, ProviderType.OPENROUTER]:
            api_key = await tenant_config_manager.get_tenant_api_key(
                test_tenant_id, provider, use_global_fallback=True
            )
            if api_key:
                providers.append(provider.value)

        # 测试模型配置获取
        model_configs = {}
        for provider in [ProviderType.ZHIPU, ProviderType.OPENROUTER]:
            config = await tenant_config_manager.get_tenant_model_config(test_tenant_id, provider)
            model_configs[provider.value] = config

        # 验证租户配置
        validation_results = await tenant_config_manager.validate_tenant_config(test_tenant_id)

        return {
            "success": True,
            "message": "Tenant isolation test completed",
            "tenant_id": test_tenant_id,
            "available_providers": providers,
            "model_configs": model_configs,
            "validation_results": validation_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant isolation test failed: {str(e)}")


@router.get("/test/data-sources-context")
async def test_data_sources_context(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant),
    db: Session = Depends(get_db)
):
    """
    测试数据源上下文获取
    """
    tenant_id = current_user.get("tenant_id", "")
    context = await _get_data_sources_context(tenant_id, db)
    return {
        "tenant_id": tenant_id,
        "context_length": len(context),
        "context": context
    }


@router.get("/test/all-features")
async def test_all_features(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    综合功能测试端点
    """
    try:
        from src.app.services.llm_service import LLMMessage

        # 构建复杂的测试场景
        messages = [
            LLMMessage(
                role="user",
                content="作为一个AI专家，请分析和评估当前大语言模型技术的发展现状，包括技术架构、应用场景、优势和挑战，并预测未来的发展趋势。请提供详细的分析和具体的建议。"
            )
        ]

        # 获取对话复杂度分析
        complexity_analysis = llm_service.analyze_conversation_complexity(messages)

        # 调用聊天完成（启用智能思考模式）
        response = await llm_service.chat_completion(
            tenant_id=current_user.id,
            messages=messages,
            stream=False,
            enable_thinking=None,  # 自动启用思考模式
            temperature=complexity_analysis.get("recommend_temperature", 0.7),
            max_tokens=complexity_analysis.get("recommend_max_tokens", getattr(settings, "llm_max_output_tokens", 8192))
        )

        # 获取可用模型列表
        available_models = await llm_service.get_available_models(current_user.id)

        # 验证提供商状态
        provider_status = await llm_service.validate_providers(current_user.id)

        return {
            "success": True,
            "message": "Comprehensive LLM features test completed",
            "complexity_analysis": complexity_analysis,
            "response_received": response is not None,
            "available_models": available_models,
            "provider_status": provider_status,
            "features_tested": [
                "智能思考模式",
                "复杂度分析",
                "智能参数调整",
                "多提供商支持",
                "租户隔离"
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive test failed: {str(e)}")