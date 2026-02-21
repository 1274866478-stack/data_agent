"""
# [LLM] LLM服务API端点

## [HEADER]
**文件名**: llm.py
**职责**: 提供统一的LLM聊天完成、流式输出、SQL查询和多模态支持API，集成智谱AI和DeepSeek服务，支持数据源连接和自然语言查询，确保租户隔离
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现LLM服务API端点

## [INPUT]
- **tenant: Tenant** - 租户对象（通过依赖注入获取）
- **user_with_tenant: dict** - 用户和租户信息（从JWT token中提取）
- **chat_request: ChatRequest** - 聊天请求模型（Pydantic模型）
  - messages: 消息列表
  - model: 模型名称
  - temperature: 温度参数
  - max_tokens: 最大token数
  - stream: 是否流式输出
- **sql_query_request: SQLQueryRequest** - SQL查询请求模型
  - query: 自然语言查询
  - connection_id: 数据源连接ID
  - data_source_id: 数据源ID
- **data_source_id: str** - 数据源ID（路径参数）
- **db: Session** - 数据库会话（通过依赖注入获取）

## [OUTPUT]
- **chat_response: LLMResponse** - LLM聊天响应
  - content: 生成内容
  - role: 角色名称
  - usage: token使用统计
  - model: 模型名称
- **stream_response: StreamingResponse** - 流式响应
  - 分块返回生成的文本
- **sql_query_result: dict** - SQL查询结果
  - success: 查询是否成功
  - sql: 生成的SQL语句
  - results: 查询结果数据
  - row_count: 结果行数
  - error: 错误信息（如果失败）
- **data_source_info: dict** - 数据源信息
  - id: 数据源ID
  - name: 数据源名称
  - db_type: 数据库类型
  - status: 连接状态
- **error_response: HTTPException** - 错误响应（400, 404, 500）

## [LINK]
**上游依赖** (已读取源码):
- [../../data/database.py](../../data/database.py) - get_db(), Session
- [../../data/models.py](../../data/models.py) - Tenant, DataSourceConnection, DataSourceConnectionStatus
- [../../services/llm_service.py](../../services/llm_service.py) - llm_service, LLMProvider, LLMMessage, LLMResponse
- [../../services/data_source_service.py](../../services/data_source_service.py) - data_source_service, 数据源服务
- [../../services/minio_client.py](../../services/minio_client.py) - minio_service, 对象存储
- [../../services/zhipu_client.py](../../services/zhipu_client.py) - zhipu_service, 智谱AI服务
- [../../services/database_interface.py](../../services/database_interface.py) - PostgreSQLAdapter, 数据库适配器
- [../../core/auth.py](../../core/auth.py) - get_current_user_with_tenant, 用户认证

**下游依赖** (已读取源码):
- 无（API端点是叶子模块）

**调用方**:
- 前端聊天界面 - LLM对话交互
- 前端SQL查询工具 - 自然语言生成SQL
- 前端数据分析模块 - 智能数据查询
- 流式响应客户端 - 实时文本生成

## [POS]
**路径**: backend/src/app/api/v1/endpoints/llm.py
**模块层级**: Level 3 - API端点层
**依赖深度**: 直接依赖 data/*, services/*, core/*；被前端聊天和查询模块调用
"""

import json
import asyncio
import logging
import io
import os
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import pandas as pd

from src.app.domains.llm.service import (
    llm_service,
    LLMProvider,
    LLMMessage,
    LLMResponse,
)
from src.app.core.auth import get_current_user_with_tenant
from src.app.data.models import Tenant
from src.app.data.database import get_db
from src.app.domains.data_sources.service import data_source_service
from src.app.integrations.storage_minio.client import minio_service
from src.app.integrations.db_adapters.database_interface import PostgreSQLAdapter
from src.app.domains.llm.sql_error_memory import SQLErrorMemoryService
import re
import duckdb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM"])


def _strip_sql_comments_and_check_select(sql: str) -> tuple[str, bool, str]:
    """
    去除SQL开头的注释，并检查是否是SELECT/WITH查询
    
    Args:
        sql: 原始SQL查询
    
    Returns:
        tuple: (去除注释后的SQL, 是否为SELECT查询, 调试信息)
    """
    sql_for_check = sql.strip()
    original_len = len(sql_for_check)
    debug_info = []
    
    # 循环去除开头的注释（单行和多行都要处理）
    max_iterations = 100  # 防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        made_change = False
        
        # 去除单行注释 (-- ...)
        while sql_for_check.startswith('--'):
            newline_pos = sql_for_check.find('\n')
            if newline_pos != -1:
                removed = sql_for_check[:newline_pos + 1]
                sql_for_check = sql_for_check[newline_pos + 1:].strip()
                debug_info.append(f"去除单行注释: {repr(removed[:30])}")
                made_change = True
            else:
                # 整行都是注释，没有换行符，说明SQL只是一个注释
                debug_info.append(f"SQL只是注释: {repr(sql_for_check[:50])}")
                break
        
        # 去除多行注释 (/* ... */)
        while sql_for_check.startswith('/*'):
            end_pos = sql_for_check.find('*/')
            if end_pos != -1:
                removed = sql_for_check[:end_pos + 2]
                sql_for_check = sql_for_check[end_pos + 2:].strip()
                debug_info.append(f"去除多行注释: {repr(removed[:30])}")
                made_change = True
            else:
                debug_info.append("未闭合的多行注释")
                break
        
        # 如果这次循环没有变化，退出
        if not made_change:
            break
    
    # 检查是否是SELECT查询
    sql_upper = sql_for_check.upper().strip()
    is_select = sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
    
    debug_msg = f"原始长度={original_len}, 处理后长度={len(sql_for_check)}, " \
                f"迭代次数={iteration}, 是SELECT={is_select}"
    if debug_info:
        debug_msg += f", 处理过程: {'; '.join(debug_info)}"
    debug_msg += f", 处理后前50字符: {repr(sql_for_check[:50])}"
    
    return sql_for_check, is_select, debug_msg


def _split_multiple_sql_statements(sql_block: str) -> List[str]:
    """
    拆分一个SQL代码块中可能包含的多个SQL语句
    
    AI有时会在一个代码块中返回多个用分号分隔的SQL语句，
    PostgreSQL的prepared statement不支持同时执行多个命令，
    因此需要拆分后逐个执行。
    
    Args:
        sql_block: 可能包含多个SQL语句的代码块内容
        
    Returns:
        List[str]: 拆分后的SQL语句列表（过滤掉空语句和纯注释）
    """
    # 按分号拆分，但要注意分号可能出现在字符串内部
    # 使用简单策略：按分号拆分，然后过滤空语句
    statements = []
    
    # 首先尝试按分号分隔
    raw_statements = sql_block.split(';')
    
    for stmt in raw_statements:
        stmt = stmt.strip()
        if not stmt:
            continue
            
        # 检查是否只是注释（去除注释后是否还有内容）
        sql_cleaned, is_select, _ = _strip_sql_comments_and_check_select(stmt)
        
        # 如果去除注释后还有内容，且是SELECT/WITH查询，保留它
        if sql_cleaned and is_select:
            statements.append(stmt)
    
    # 如果没有拆分出任何有效语句，但原始块非空，可能是没有分号的单个查询
    if not statements and sql_block.strip():
        sql_cleaned, is_select, _ = _strip_sql_comments_and_check_select(sql_block)
        if sql_cleaned and is_select:
            statements.append(sql_block.strip())
    
    return statements


def _remove_database_name_prefix(sql: str, database_name: str) -> str:
    """
    去除SQL中多余的数据库名前缀
    
    PostgreSQL不支持跨数据库引用，当已连接到数据库时，
    SQL中不应该包含 "数据库名.schema.表名" 这样的格式。
    AI有时会错误地生成这种格式，需要自动修正。
    
    例如：
    - "test_ecommerce_100k.information_schema.tables" -> "information_schema.tables"
    - "test_ecommerce_100k.public.users" -> "public.users"
    
    Args:
        sql: 原始SQL语句
        database_name: 当前连接的数据库名
        
    Returns:
        str: 去除数据库名前缀后的SQL
    """
    if not database_name:
        return sql
    
    # 构建要替换的模式：数据库名后跟一个点
    # 需要处理大小写不敏感的情况
    import re
    
    # 匹配 数据库名. 的模式（后面必须跟着有效的标识符）
    # 使用单词边界确保精确匹配
    pattern = re.compile(
        r'\b' + re.escape(database_name) + r'\.',
        re.IGNORECASE
    )
    
    original_sql = sql
    sql = pattern.sub('', sql)
    
    if sql != original_sql:
        logger.debug(f"[SQL预处理] 去除数据库名前缀 '{database_name}.': {original_sql[:100]}... -> {sql[:100]}...")
    
    return sql


def _extract_table_name_from_sql(sql: str) -> Optional[str]:
    """
    从SQL语句中提取主表名

    Args:
        sql: SQL语句

    Returns:
        提取的表名，如果无法提取则返回None
    """
    try:
        # 移除注释
        clean_sql = sql
        # 移除单行注释
        clean_sql = re.sub(r'--.*$', '', clean_sql, flags=re.MULTILINE)
        # 移除多行注释
        clean_sql = re.sub(r'/\*.*?\*/', '', clean_sql, flags=re.DOTALL)

        # 查找 FROM 或 JOIN 子句
        # 优先匹配 FROM (主表)
        from_match = re.search(r'\bFROM\s+["\']?([a-zA-Z_][a-zA-Z0-9_]*)', clean_sql, re.IGNORECASE)
        if from_match:
            return from_match.group(1).lower()

        # 如果没有FROM，尝试JOIN
        join_match = re.search(r'\bJOIN\s+["\']?([a-zA-Z_][a-zA-Z0-9_]*)', clean_sql, re.IGNORECASE)
        if join_match:
            return join_match.group(1).lower()

        return None
    except Exception:
        return None


def _convert_decimal_to_float(data: Any) -> Any:
    """
    递归地将数据中的 Decimal 和 datetime 类型转换为 JSON 可序列化的格式
    
    Args:
        data: 需要转换的数据（可以是 dict, list, 或其他类型）
    
    Returns:
        转换后的数据，其中：
        - Decimal -> float
        - datetime/date -> ISO 格式字符串
    """
    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, date):
        return data.isoformat()
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
        from src.app.domains.query.agent_path import resolve_file_path_with_fallback
        
        # 首先尝试解析路径（包含本地回退逻辑）
        local_file_path = resolve_file_path_with_fallback(connection_string)
        file_data = None
        use_local_file = False
        
        # 如果找到本地文件，直接使用
        if local_file_path and os.path.exists(local_file_path):
            logger.debug(f"从本地文件系统读取文件: {local_file_path}")
            use_local_file = True
            file_path_for_read = local_file_path
        else:
            # 尝试从MinIO下载
            storage_path = connection_string[7:] if connection_string.startswith("file://") else connection_string
            logger.debug(f"尝试从MinIO下载文件: {storage_path}")
            file_data = minio_service.download_file(
                bucket_name="data-sources",
                object_name=storage_path
            )
            
            if not file_data:
                logger.warning(f"无法从MinIO获取文件: {storage_path}")
                # 最后尝试本地回退
                if local_file_path:
                    logger.debug(f"尝试使用解析的本地路径: {local_file_path}")
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
            logger.debug(f"Excel文件包含 {len(sheet_names)} 个Sheet: {sheet_names}")

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
                    logger.debug(f"Sheet '{sheet_name}': {len(df)}行, {len(df.columns)}列")
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
        logger.debug(f"成功获取文件schema: {len(tables)}个表, 共{total_rows}行")
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
                logger.debug(f"尝试从MinIO获取文件: {path}")
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
                        logger.debug(f"备选方案: Excel包含 {len(sheet_names)} 个Sheet: {sheet_names}")

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
                        logger.debug(f"备选方案成功获取schema: {len(tables)}个表, 共{total_rows}行")
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
        logger.debug(perf_msg)

        if not data_sources:
            return ""

        # 如果指定了数据源ID，则只获取指定的数据源
        if data_source_ids:
            original_count = len(data_sources)
            data_sources = [ds for ds in data_sources if ds.id in data_source_ids]
            logger.debug(f"🎯 [数据源筛选] 指定数据源: {data_source_ids}, 从 {original_count} 个中筛选出 {len(data_sources)} 个匹配的数据源")
            for ds in data_sources:
                logger.debug(f"  ✅ 使用数据源: {ds.name} (ID: {ds.id}, 类型: {ds.db_type})")
            if not data_sources:
                logger.warning(f"⚠️ [数据源筛选] 未找到匹配的数据源！请求的ID: {data_source_ids}")
                return ""
        else:
            logger.warning(f"⚠️ [数据源筛选] 未指定 data_source_ids，将使用所有 {len(data_sources)} 个活跃数据源:")
            for ds in data_sources:
                logger.debug(f"  📦 活跃数据源: {ds.name} (ID: {ds.id}, 类型: {ds.db_type})")

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
                    logger.debug(f"[PERF] get_decrypted_connection_string for {ds.name} took {time.time() - t2:.2f}s")
                except Exception as decrypt_error:
                    logger.warning(f"[PERF] 解密数据源 {ds.name} 连接字符串失败: {decrypt_error}")
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
                        
                        # 🔧 新增：自动检测枚举字段并获取其实际值
                        # 常见的枚举字段名模式
                        enum_field_patterns = [
                            'status', 'state', 'type', 'category', 'level', 'role',
                            'gender', 'priority', 'payment_method', 'payment_status',
                            'order_status', 'shipping_status', 'user_type'
                        ]
                        
                        # 用于存储每个表的枚举值
                        enum_values_cache = {}
                        
                        for table in schema_result.tables.values():
                            table_enum_values = {}
                            for col in table.columns:
                                col_lower = col.name.lower()
                                # 检查是否是可能的枚举字段
                                is_enum_field = any(pattern in col_lower for pattern in enum_field_patterns)
                                # 也检查字符串类型的短字段（可能是枚举）
                                is_short_varchar = (
                                    col.data_type in ['character varying', 'varchar', 'text'] and
                                    col.max_length and col.max_length <= 50
                                )
                                
                                if is_enum_field or (is_short_varchar and col_lower.endswith(('_type', '_status', '_state'))):
                                    try:
                                        # 查询该字段的distinct值（限制10个，避免太多）
                                        distinct_query = f"""
                                            SELECT DISTINCT "{col.name}" 
                                            FROM "{table.name}" 
                                            WHERE "{col.name}" IS NOT NULL 
                                            LIMIT 10
                                        """
                                        distinct_result = await adapter.execute_query(distinct_query)
                                        if distinct_result and distinct_result.data:
                                            values = [row[col.name] for row in distinct_result.data if row.get(col.name)]
                                            if values and len(values) <= 10:  # 只保留合理数量的枚举值
                                                table_enum_values[col.name] = values
                                    except Exception as enum_err:
                                        logger.debug(f"获取枚举值失败 {table.name}.{col.name}: {enum_err}")
                            
                            if table_enum_values:
                                enum_values_cache[table.name] = table_enum_values
                        
                        # 将SchemaInfo对象转换为字典格式，并包含枚举值
                        schema_info = {
                            "database_type": schema_result.database_type.value if schema_result.database_type else "postgresql",
                            "tables": [
                                {
                                    "name": table.name,
                                    "columns": [
                                        {
                                            "name": col.name,
                                            "type": col.data_type,
                                            "nullable": col.is_nullable,
                                            # 添加枚举值（如果有）
                                            "enum_values": enum_values_cache.get(table.name, {}).get(col.name)
                                        }
                                        for col in table.columns
                                    ]
                                }
                                for table in schema_result.tables.values()
                            ] if schema_result.tables else []
                        }
                    finally:
                        await adapter.disconnect()
                    logger.debug(f"[PERF] PostgreSQL get_schema for {ds.name} took {time.time() - t3:.2f}s")

                elif ds.db_type in ["xlsx", "xls", "csv"]:
                    # 🔧 修复：从connection_config或connection_string提取文件路径
                    file_path = connection_string
                    if hasattr(ds, 'connection_config') and ds.connection_config:
                        # 如果存在connection_config字段，优先使用它
                        from src.app.domains.query.agent_path import extract_file_path_from_config
                        extracted_path = extract_file_path_from_config(ds.connection_config, connection_string)
                        if extracted_path:
                            file_path = extracted_path
                    
                    if file_path:
                        # 文件类型数据源：从文件读取并解析schema
                        t4 = time.time()
                        schema_info = await _get_file_schema(file_path, ds.db_type, ds.name)
                        logger.debug(f"[PERF] _get_file_schema for {ds.name} took {time.time() - t4:.2f}s")
                    else:
                        # 连接字符串获取失败，尝试备选方案
                        logger.debug(f"[PERF] 尝试备选方案获取数据源 {ds.name} 的schema")
                        schema_info = await _try_get_file_schema_fallback(tenant_id, ds.id, ds.db_type, ds.name)

                logger.debug(f"[PERF] Total processing for data source {ds.name} took {time.time() - ds_start:.2f}s")

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
                                # 🔧 新增：显示枚举值
                                enum_values = col.get("enum_values")
                                if enum_values:
                                    enum_str = ", ".join([f"'{v}'" for v in enum_values[:8]])  # 最多显示8个
                                    if len(enum_values) > 8:
                                        enum_str += ", ..."
                                    col_info.append(f"  - {col_name} ({col_type}, {nullable}) **可选值: [{enum_str}]**")
                                else:
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
        logger.debug("[PERF] _get_data_sources_context TOTAL took %.2fs", total_time)
        return "\n".join(context_parts)

    except Exception as e:
        logger.error(f"获取数据源上下文失败: {e}")
        return ""


def _build_system_prompt_with_context(
    data_sources_context: str,
    db_type: str = "postgresql"  # 新增参数：数据库类型
) -> str:
    """
    构建包含数据源上下文的系统提示词（使用 SQL 代码块格式）

    Args:
        data_sources_context: 数据源上下文信息
        db_type: 数据库类型（postgresql, mysql, sqlite, xlsx, csv等）

    Returns:
        系统提示词
    """
    if data_sources_context:
        # 基础系统提示词
        base_prompt = f"""你是一个专业的数据分析师。你的任务是根据用户的问题，查询数据库并给出分析结果。

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

## 🔴 查询表列表的正确方式（重要！）

**如果用户问"有哪些表"、"数据库里有什么表"等问题：**

1. **优先使用上方 Schema 信息回答**：上方已经列出了所有可用的表和列信息，直接根据这些信息回答用户
2. **对于 Excel/CSV 文件数据源**：表名就是 Excel 的 Sheet 名称或 CSV 文件名，已经在上方 Schema 中列出
3. **如果需要执行 SQL 查询表列表**：
   - ✅ 正确语法：`SHOW TABLES;`
   - ❌ 错误语法：`SELECT name FROM sqlite_master WHERE type='table'`（这是 SQLite 语法，不适用于本系统）
   - ❌ 错误语法：`SELECT table_name FROM information_schema.tables`（PostgreSQL 语法，对于文件数据源不适用）

**注意**：本系统的文件数据源使用 DuckDB 引擎执行 SQL，请确保使用兼容的语法。

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

## 🧠 模糊查询智能推断规则（重要！）

当用户问**模糊问题**（如"最近生意怎么样"、"销售如何"、"业绩好不好"）时，你必须：

### 1️⃣ 默认时间范围
| 用户说 | 应理解为 | SQL条件示例 |
|--------|----------|-------------|
| "最近" | 最近30天 | `WHERE date_column >= '2023-12-08'`（用当前日期减30天）|
| "最近一周" | 最近7天 | `WHERE date_column >= '2024-01-01'`（用当前日期减7天）|
| "最近一月" | 最近30天 | `WHERE date_column >= '2023-12-08'` |
| "本月" | 当月1日至今 | `WHERE date_column LIKE '2024-01%'` |
| "上月" | 上月整月 | `WHERE date_column LIKE '2023-12%'` |

### 2️⃣ 默认业务指标
| 用户说 | 应理解为 | 优先查询指标 |
|--------|----------|--------------|
| "生意"、"销售"、"业绩" | 订单量和销售额 | COUNT(*) 订单数, SUM(amount) 销售额 |
| "客户"、"用户" | 客户数量 | COUNT(DISTINCT customer_id) 客户数 |
| "收入"、"钱" | 金额 | SUM(amount), AVG(amount) |
| "趋势"、"变化" | 时间序列数据 | 按日期/月份分组统计 |

### 3️⃣ 🔴 模糊查询必须生成时间序列数据（用于图表）！

**关键规则**：
- 查询时必须**按日期分组**（如按天或按月），这样才能画出趋势图
- 不要只查总数，要查**时间序列数据**用于图表
- 必须调用 `generate_chart` 工具生成可视化图表

**SQL查询示例（错误 vs 正确）**：
```sql
-- ❌ 错误：只查总数，无法画图
SELECT COUNT(*), SUM(amount) FROM 订单表 WHERE created_at LIKE '2023%';
-- 只返回一行，无法生成趋势图

-- ✅ 正确：按日期分组，可生成趋势图
SELECT
    SUBSTRING(created_at, 1, 7) as 月份,
    COUNT(*) as 订单数,
    SUM(final_amount) as 销售额
FROM 订单表
WHERE SUBSTRING(created_at, 1, 4) = '2023'
GROUP BY SUBSTRING(created_at, 1, 7)
ORDER BY 月份;
-- 返回多行数据，每行是一个月份的数据
```

### 4️⃣ 关键要求
- 🔴 **模糊时间必须使用默认值**（"最近"默认30天，不要问用户"多久"）
- 🔴 **查询必须按日期分组**（生成时间序列数据用于画图）
- 🔴 **必须调用 `generate_chart` 工具**生成折线图或柱状图
- 🔴 **主动找表**（通过上方Schema信息智能推断表名）

### 5️⃣ 🔴 图表生成规则（必须遵守）

**当查询结果包含统计数据时（时间序列、对比数据、趋势分析），你必须：**

1. **调用 `generate_chart` 工具**生成图表，工具格式：
```json
{{
  "chart_type": "line",
  "title": "标题",
  "x_data": ["2023-01", "2023-02", ...],
  "y_data": [1000, 1200, ...],
  "series_name": "销售额"
}}
```

2. **图表类型选择**：
   - 包含"趋势"、"变化"、"时间" → `chart_type: "line"` (折线图)
   - 包含"对比"、"比较"、"排名" → `chart_type: "bar"` (柱状图)
   - 包含"占比"、"分布"、"比例" → `chart_type: "pie"` (饼图)

3. **回答格式**：先解释你的分析思路 → 提供SQL查询 → 调用generate_chart工具生成图表

---

**记住：只需要在回答中写 SQL 代码块，系统会自动执行查询并返回结果！对于数据查询，必须调用 generate_chart 工具生成可视化图表！**"""

        # 使用数据库特定的提示词生成器
        try:
            from src.app.domains.llm.prompts import generate_database_aware_system_prompt
            result = generate_database_aware_system_prompt(db_type, base_prompt)
            logger.debug("[LLM endpoint] using db-aware prompt generator, db_type=%s", db_type)
            return result
        except ImportError as e:
            logger.warning(f"⚠️ 无法导入 prompt_generator: {e}，使用默认提示词")
            return base_prompt
        except Exception as e:
            logger.warning(f"⚠️ 生成数据库特定提示词失败: {e}，使用默认提示词")
            return base_prompt
    else:
        # 没有数据源时的提示
        return """你是一个数据分析助手。

当前系统中还没有连接任何数据源。

如果用户询问数据相关问题，请告诉他们需要先在"数据源管理"页面添加数据库连接。

不要假设或猜测数据库结构，不要生成任何SQL查询。"""


def _get_default_fix_prompt(
    original_sql: str,
    error_message: str,
    schema_context: str,
    original_question: str,
    error_details: dict
) -> str:
    """
    获取默认的SQL修复提示词（回退方案，当动态生成失败时使用）
    主要针对PostgreSQL，但也可以处理基本的函数不兼容错误
    """
    # 检查是否是函数不兼容错误（如 TO_CHAR 不存在）
    if "does not exist" in error_message and ("to_char" in error_message.lower() or "date_trunc" in error_message.lower()):
        # 添加函数不兼容的特定提示
        db_hint = """
## 🔴 函数不兼容错误

你使用的函数在当前数据库中不存在。请检查并替换为兼容的函数：

- **TO_CHAR()**: PostgreSQL专用，MySQL中用DATE_FORMAT()，SQLite中用strftime()
- **DATE_TRUNC()**: PostgreSQL专用，MySQL中用DATE_FORMAT()，SQLite中用strftime()
- **EXTRACT()**: PostgreSQL支持，MySQL可用YEAR()/MONTH()，SQLite用strftime()

请根据错误信息和上述说明，替换不兼容的函数。
"""
    else:
        db_hint = f"""
## 数据库提示
{error_details.get('hint', '无提示')}
"""

    return f"""你是一个SQL专家。用户的查询执行失败了，请帮助修复SQL语句。

# 用户原始问题
{original_question}

# 失败的SQL查询
```sql
{original_sql}
```

# 错误信息
{error_details['main_error']}

{db_hint}

# 🔴🔴🔴 数据库Schema信息（必须使用这里的实际表名和列名）
{schema_context}

# 🔥🔥🔥 修复要求（必须严格遵守）

## 第1步：理解错误
- **主要错误**: {error_details['main_error']}

## 第2步：查找正确的表名/列名
**🔴 核心问题：SQL中使用了不存在的表名或列名，或者使用了不兼容的函数！**

1. **如果错误是"函数不存在"**：
   - 检查并替换为数据库兼容的函数
   - PostgreSQL: TO_CHAR(), DATE_TRUNC(), EXTRACT()
   - MySQL: DATE_FORMAT(), YEAR(), MONTH()
   - SQLite: strftime(), CAST(strftime() AS INTEGER)

2. **如果错误是"Table does not exist"**：
   - 必须从上面的Schema信息中找到实际存在的表名

3. **如果错误是"Column does not exist"**：
   - 在Schema中找到正确的列名

## 第3步：修复SQL
1. 检查并替换所有不兼容的函数
2. 仔细阅读Schema信息，找到对应的**实际表名和列名**
3. 确保SQL语法正确
4. 只使用SELECT查询
5. 🔴 极值查询必须使用 LIMIT 1

## 第4步：返回结果
- **只返回修复后的SQL语句** - 不要包含任何解释或markdown标记
- **如果Schema中没有相关的表或列** - 返回"CANNOT_FIX"
- **不要添加```sql标记** - 直接返回纯SQL语句

现在请修复上述失败的SQL查询，直接返回修复后的SQL语句："""


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
    original_question: str,
    db_type: str = "postgresql",  # 数据库类型参数
    tenant_id: str = "default_tenant"  # 租户ID，用于llm_service
) -> Optional[str]:
    """
    使用AI修复失败的SQL查询（优先使用DeepSeek）

    Args:
        original_sql: 原始SQL查询
        error_message: 错误信息
        schema_context: 数据库schema上下文
        original_question: 用户原始问题
        db_type: 数据库类型（postgresql, mysql, sqlite, xlsx, csv等）
        tenant_id: 租户ID

    Returns:
        修复后的SQL，如果无法修复则返回None
    """
    try:
        # 尝试使用动态生成的数据库特定修复提示词
        try:
            from src.app.domains.llm.prompts import generate_sql_fix_prompt_with_db_type
            fix_prompt = generate_sql_fix_prompt_with_db_type(
                original_sql=original_sql,
                error_message=error_message,
                schema_context=schema_context,
                original_question=original_question,
                db_type=db_type
            )
        except ImportError as e:
            logger.warning(f"无法导入 prompt_generator: {e}，使用默认PostgreSQL修复提示")
            # 回退到原有的硬编码提示词（仅针对函数不兼容错误）
            error_details = _parse_sql_error(error_message)
            fix_prompt = _get_default_fix_prompt(
                original_sql, error_message, schema_context, original_question, error_details
            )
        except Exception as e:
            logger.warning(f"生成动态修复提示词失败: {e}，使用默认PostgreSQL修复提示")
            # 回退到原有的硬编码提示词
            error_details = _parse_sql_error(error_message)
            fix_prompt = _get_default_fix_prompt(
                original_sql, error_message, schema_context, original_question, error_details
            )

        # 更新 system prompt 以反映数据库类型
        system_content = f"你是一个专业的SQL修复专家，擅长根据错误信息和schema修复{db_type.upper()}数据库的SQL查询。"

        # 使用 LLMMessage 格式，通过 llm_service 调用（优先使用 DeepSeek）
        messages = [
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=fix_prompt)
        ]

        # 调用 llm_service 修复SQL（自动优先使用 DeepSeek，回退到 Zhipu）
        logger.debug(f"使用 llm_service 修复SQL (tenant_id={tenant_id})")
        response = await llm_service.chat_completion(
            tenant_id=tenant_id,
            messages=messages,
            max_tokens=1000,
            temperature=0.1,  # 低温度确保准确性
            stream=False
        )

        if response and response.content:
            fixed_sql = response.content.strip()

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

            logger.debug(f"AI成功修复SQL: {fixed_sql[:100]}...")
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
                logger.debug(f"直接使用本地文件: {file_path}")
                try:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                except Exception as e:
                    logger.warning(f"读取本地文件失败: {e}，尝试从 MinIO 下载")
                    file_data = None
            else:
                logger.debug(f"本地文件不存在: {file_path}，尝试从 MinIO 下载")
        
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
            
            logger.debug(f"从MinIO下载文件用于SQL执行: bucket=data-sources, object_name={object_name}")
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
            logger.debug(f"Excel包含 {len(sheet_names)} 个Sheet: {sheet_names}")

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
                    logger.debug(f"注册表 '{clean_table_name}' (来自Sheet '{sheet_name}'): {len(df)}行")

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

        logger.debug(f"成功注册 {len(registered_tables)} 个表: {registered_tables}")

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

        logger.debug(f"文件数据源SQL执行成功，返回 {len(data)} 行")

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

        # 拆分每个代码块中可能包含的多个SQL语句，并去重
        seen_sqls = set()
        unique_sql_matches = []
        for sql_block in sql_matches:
            # 拆分一个代码块中的多个SQL语句
            individual_statements = _split_multiple_sql_statements(sql_block)
            logger.debug(f"从代码块中拆分出 {len(individual_statements)} 个SQL语句")
            
            for sql in individual_statements:
                normalized_sql = sql.strip().upper()  # 标准化比较
                if normalized_sql not in seen_sqls:
                    seen_sqls.add(normalized_sql)
                    unique_sql_matches.append(sql)
                else:
                    logger.warning(f"检测到重复SQL，已跳过: {sql[:50]}...")

        sql_matches = unique_sql_matches
        logger.debug(f"检测到 {len(sql_matches)} 个唯一SQL查询，准备执行")

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
                logger.debug(f"使用指定的数据源: {data_source.name} ({data_source.id})")
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

            # 🔥 时间聚合强制修正：年度/按月趋势查询必须按月分组
            try:
                from src.app.domains.query.agent_tools import validate_time_aggregation_sql

                is_valid, corrected_sql, error_msg = validate_time_aggregation_sql(
                    current_sql,
                    user_question=original_question,
                    db_type=data_source.db_type
                )
                if not is_valid:
                    logger.warning(f"⚠️ {error_msg}")
                    current_sql = corrected_sql
            except Exception as e:
                logger.warning(f"时间聚合修正失败: {e}")

            while retry_count <= max_retries and not execution_success:
                try:
                    # 安全检查：只允许SELECT查询（包括WITH...SELECT的CTE查询）
                    # 使用统一的注释去除和检查函数
                    sql_for_check, is_select, debug_msg = _strip_sql_comments_and_check_select(current_sql)
                    logger.debug(f"SQL检测结果: {debug_msg}")
                    
                    if not is_select:
                        logger.warning(f"跳过非SELECT查询: {current_sql[:100]}")
                        logger.warning(f"检测详情: {debug_msg}")
                        break

                    # 根据数据源类型选择执行方式
                    if data_source.db_type in ["xlsx", "xls", "csv"]:
                        # 文件类型数据源：使用duckdb执行
                        logger.debug(f"使用duckdb执行文件数据源查询: {data_source.db_type}")
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
                        # 预处理：去除AI可能错误添加的数据库名前缀
                        if data_source.database_name:
                            current_sql = _remove_database_name_prefix(current_sql, data_source.database_name)
                        
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

                        # 🔧 新增：记录SQL错误到错误记忆系统
                        try:
                            error_memory_service = SQLErrorMemoryService(db)
                            await error_memory_service.record_error(
                                tenant_id=tenant_id,
                                original_query=sql_query,
                                error_message=last_error,
                                fixed_query=current_sql,
                                table_name=_extract_table_name_from_sql(sql_query),
                                schema_context=None  # 可选：可以传递schema上下文
                            )
                            logger.debug("SQL错误已记录到错误记忆系统")
                        except Exception as record_error:
                            logger.warning(f"记录SQL错误失败: {record_error}")
                    else:
                        # 没有重试，直接将结果插入到SQL代码块后面
                        sql_block = f"```sql\n{sql_query}\n```"
                        enhanced_content = enhanced_content.replace(
                            sql_block,
                            sql_block + result_text
                        )

                    logger.debug(f"SQL查询执行成功，返回 {len(result.get('data', []))} 行")
                    execution_success = True

                except Exception as e:
                    last_error = str(e)
                    logger.error(f"执行SQL查询失败 (尝试 {retry_count + 1}/{max_retries + 1}): {e}")

                    # 如果还有重试机会，尝试用AI修复SQL
                    if retry_count < max_retries:
                        logger.debug("尝试使用AI修复SQL...")
                        fixed_sql = await _fix_sql_with_ai(
                            original_sql=current_sql,
                            error_message=last_error,
                            schema_context=schema_context,
                            original_question=original_question,
                            db_type=data_source.db_type,  # 传递数据库类型
                            tenant_id=tenant_id  # 传递租户ID用于llm_service
                        )

                        if fixed_sql:
                            logger.debug(f"AI修复成功，准备重试。修复后的SQL: {fixed_sql[:100]}...")
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
            
            # 安全检查：只允许SELECT查询（使用统一的检测函数处理注释）
            _, is_select, debug_msg = _strip_sql_comments_and_check_select(sql_query)
            logger.debug(f"execute_sql SQL检测: {debug_msg}")
            if not is_select:
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
                    # 预处理：去除AI可能错误添加的数据库名前缀
                    processed_sql = sql_query
                    if data_source.database_name:
                        processed_sql = _remove_database_name_prefix(sql_query, data_source.database_name)
                    
                    adapter = PostgreSQLAdapter(connection_string)
                    try:
                        await adapter.connect()
                        query_result = await adapter.execute_query(processed_sql)
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
                
                logger.debug(f"生成图表: type={chart_type}, title={title}, x_data_len={len(x_data)}, y_data_len={len(y_data)}")
                
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


def _create_processing_step(
    step: int,
    title: str,
    description: str,
    status: str = "running",
    duration: int = None,
    details: str = None,
    tenant_id: str = None,
    content_type: str = None,
    content_data: dict = None
) -> str:
    """
    创建处理步骤事件的JSON字符串

    Args:
        step: 步骤编号
        title: 步骤标题
        description: 步骤描述
        status: 步骤状态 (pending/running/completed/error)
        duration: 耗时（毫秒）
        details: 详情文本（向后兼容）
        tenant_id: 租户ID
        content_type: 内容类型 (sql/table/chart/error)
        content_data: 内容数据字典

    Returns:
        str: SSE格式的JSON字符串
    """
    step_data = {
        "type": "processing_step",
        "step": {
            "step": step,
            "title": title,
            "description": description,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        },
        "tenant_id": tenant_id
    }
    if duration is not None:
        step_data["step"]["duration"] = duration
    if details:
        step_data["step"]["details"] = details
    # 新增：支持富内容类型
    if content_type:
        step_data["step"]["content_type"] = content_type
    if content_data:
        step_data["step"]["content_data"] = content_data

    # 添加日志确认步骤发送
    logger.debug(f"📤 发送处理步骤 {step}: {title} [{status}]")
    if content_type:
        logger.debug(f"   └─ content_type: {content_type}")
    return f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"


async def _stream_general_chat_generator(
    stream_generator,
    tenant_id: str,
    original_question: str = "",
    has_data_source: bool = False
):
    """
    普通对话的流式响应生成器（动态步骤流程）

    根据问题类型动态生成不同的步骤：
    - 简单问候（你好、谢谢）: 2步
    - Schema查询（有哪些表）: 3步
    - 数据查询: 5步
    - 可视化需求: 6步
    - 普通对话（默认）: 6步

    Args:
        stream_generator: LLM流式输出生成器
        tenant_id: 租户ID
        original_question: 用户原始问题
        has_data_source: 是否有可用的数据源
    """
    from src.app.domains.query.processing_steps import (
        ProcessingStepBuilder,
        classify_question,
    )

    # 1. 分类问题类型
    question_type = classify_question(original_question, has_data_source)
    logger.debug(f"[DYNAMIC_STEPS] Question type: {question_type.value}, has_data_source: {has_data_source}")

    # 2. 构建动态步骤
    builder = ProcessingStepBuilder()
    steps_config = builder.build_dynamic_steps(
        question_type=question_type,
        question=original_question,
        has_context=False
    )

    # ========== 发送连接初始化事件 ==========
    init_event = {
        "type": "connection_init",
        "message": "Stream connection established",
        "tenant_id": tenant_id
    }
    yield f"data: {json.dumps(init_event, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.05)

    # ========== 动态发送步骤 ==========
    # 发送除最后一个步骤外的所有步骤（标记为已完成）
    step_count = len(steps_config)
    for i, step_cfg in enumerate(steps_config):
        if i < step_count - 1:
            # 前面的步骤标记为已完成
            yield _create_processing_step(
                step=step_cfg.step,
                title=step_cfg.title,
                description=step_cfg.description,
                status="completed",
                duration=step_cfg.duration or 100,
                tenant_id=tenant_id
            )
            await asyncio.sleep(0.05)
        else:
            # 最后一个步骤标记为运行中（LLM生成中）
            last_step_number = step_cfg.step
            yield _create_processing_step(
                step=last_step_number,
                title=step_cfg.title,
                description=step_cfg.description,
                status="running",
                tenant_id=tenant_id
            )
            await asyncio.sleep(0.05)
            break  # 开始LLM生成

    # ========== 收集LLM输出 ==========
    full_content = ""
    llm_start_time = time.time()

    # 用于累积和更新最后步骤的内容预览
    last_step_content_preview = ""
    last_update_time = time.time()

    async for chunk in stream_generator:
        if chunk.type == "content":
            full_content += chunk.content

            # 实时发送content delta到前端
            content_delta = {
                "type": "content_delta",
                "delta": chunk.content,
                "provider": chunk.provider,
                "tenant_id": tenant_id
            }
            yield f"data: {json.dumps(content_delta, ensure_ascii=False)}\n\n"

            # 定期更新最后步骤的描述，显示内容预览
            last_step_content_preview += chunk.content
            current_time = time.time()
            if current_time - last_update_time >= 0.1:  # 100ms间隔
                # 生成内容预览（限制长度）
                preview_text = last_step_content_preview[-150:] if len(last_step_content_preview) > 150 else last_step_content_preview
                # 清理预览文本
                preview_text = preview_text.replace("\n", " ").strip()

                step_update = {
                    "type": "step_update",
                    "step": last_step_number,
                    "description": f"正在生成回复... {len(last_step_content_preview)} 字符",
                    "content_preview": preview_text,
                    "tenant_id": tenant_id
                }
                yield f"data: {json.dumps(step_update, ensure_ascii=False)}\n\n"
                last_update_time = current_time

        elif chunk.type == "thinking":
            # 发送thinking事件
            chunk_data = {
                "type": "thinking",
                "delta": chunk.content,
                "provider": chunk.provider,
                "finished": chunk.finished,
                "tenant_id": tenant_id
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        elif chunk.type == "error":
            error_data = {
                "type": "error",
                "message": chunk.content,
                "tenant_id": tenant_id
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    llm_duration = int((time.time() - llm_start_time) * 1000)

    # ========== 内容生成完成，完成最后一个步骤 ==========
    # 获取最后一个步骤配置
    last_step_cfg = steps_config[-1]
    yield _create_processing_step(
        step=last_step_number,
        title=last_step_cfg.title,
        description="回复已完成",
        status="completed",
        duration=llm_duration,
        content_type="text",
        content_data={"text": full_content},
        tenant_id=tenant_id
    )
    await asyncio.sleep(0.05)

    # ========== 发送完成信号 ==========
    done_event = {"type": "done", "tenant_id": tenant_id}
    yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"


async def _stream_response_generator(
    stream_generator,
    tenant_id: str,
    db: Session,
    original_question: str = "",
    data_source_ids: Optional[List[str]] = None,
    initial_messages: Optional[List[LLMMessage]] = None,
    schema_info: Optional[dict] = None,  # Schema获取信息
    question_type: Optional[Any] = None  # 🔧 新增：问题类型，用于决定是否生成图表
):
    """
    流式响应生成器（方案B：SQL 代码块检测模式）
    
    不使用 Function Calling，而是检测 AI 输出中的 ```sql ... ``` 代码块，
    自动执行 SQL 查询并进行第二次 LLM 调用。
    
    完整的6个步骤：
    1. 理解用户问题
    2. 获取数据库Schema
    3. 构建AI Prompt
    4. AI生成SQL
    5. 提取SQL语句
    6. 执行SQL查询
    """
    try:
        # 🔧 导入QuestionType用于判断是否需要图表
        from src.app.domains.query.processing_steps import QuestionType

        # 🔧 判断是否需要生成图表（只有VISUALIZATION类型需要图表）
        # DATA_QUERY: 5步，不生成图表
        # VISUALIZATION: 6-8步，生成图表
        # SCHEMA_QUERY: 3步，不生成图表
        should_generate_chart = question_type == QuestionType.VISUALIZATION

        logger.debug(f"[_stream_response_generator] question_type={question_type.value if question_type else 'None'}, should_generate_chart={should_generate_chart}")

        # 🔧🔧🔧 检测图表拆分请求（重要！）
        # 当用户说"把图分开"、"拆分"、"分别显示"等关键词时，需要特殊处理
        CHART_SPLIT_KEYWORDS = ["分开", "拆分", "分别显示", "单独展示", "单独显示", "各自显示", "拆成", "单独画", "各自画"]
        is_split_request = False
        chart_count = None  # 🔴 用户指定的图表数量
        if original_question:
            is_split_request = any(keyword in original_question for keyword in CHART_SPLIT_KEYWORDS)

            # 🔴🔴🔴 检测用户指定的图表数量
            if is_split_request:
                # re 模块已在文件顶部导入，无需重复导入
                number_patterns = [
                    r'拆(?:分)?(?:成)?([一二三四五六七八九十\d]+)个',
                    r'分成([一二三四五六七八九十\d]+)个',
                    r'分[别成]([一二三四五六七八九十\d]+)个',
                    r'分别显示([一二三四五六七八九十\d]+)个',
                    r'单独展示([一二三四五六七八九十\d]+)个',
                ]
                for pattern in number_patterns:
                    match = re.search(pattern, original_question)
                    if match:
                        num_str = match.group(1)
                        cn_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                                  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
                                  '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
                                  '6': 6, '7': 7, '8': 8, '9': 9, '10': 10}
                        chart_count = cn_nums.get(num_str, int(num_str) if num_str.isdigit() else None)
                        if chart_count:
                            logger.debug(f"🔍 [图表数量检测] 匹配值: {num_str} → {chart_count} 个图表")
                            break

        if is_split_request:
            count_info = f", 要求生成 {chart_count} 个图表" if chart_count else ""
            logger.debug(f"🔧🔧🔧 检测到图表拆分请求{count_info}！original_question={original_question[:50]}")
        else:
            logger.debug(f"未检测到拆分请求，original_question={original_question[:50]}")

        # 收集完整的响应内容
        full_content = ""
        thinking_content = ""
        
        # 消息历史（用于二次调用）
        messages = initial_messages or []
        
        # ========== 首先发送连接初始化事件 ==========
        # 这个事件确保 SSE 连接完全建立后再发送重要数据
        init_event = {
            "type": "connection_init",
            "message": "Stream connection established",
            "tenant_id": tenant_id
        }
        yield f"data: {json.dumps(init_event, ensure_ascii=False)}\n\n"
        # 给前端足够时间处理连接建立
        await asyncio.sleep(0.05)
        
        # ========== Step 1: 理解用户问题 ==========
        logger.debug(f"🚀 开始发送步骤1-4，original_question={original_question[:30] if original_question else 'None'}")
        step_start_time = time.time()
        yield _create_processing_step(
            step=1,
            title="理解用户问题",
            description=f"分析问题: {original_question[:50]}..." if len(original_question) > 50 else f"分析问题: {original_question}",
            status="completed",
            duration=int((time.time() - step_start_time) * 1000),
            details=f"用户问题: {original_question}",
            tenant_id=tenant_id
        )
        # 确保事件被刷新到客户端
        await asyncio.sleep(0.05)

        # ========== Step 2: 获取数据库Schema ==========
        if schema_info:
            schema_duration = schema_info.get("duration_ms", 0)
            schema_length = schema_info.get("length", 0)
            schema_tables = schema_info.get("tables", [])
            data_source_name = schema_info.get("data_source_name", "未知")
            
            tables_preview = ", ".join(schema_tables[:5])
            if len(schema_tables) > 5:
                tables_preview += f" 等{len(schema_tables)}个表"
            
            yield _create_processing_step(
                step=2,
                title="获取数据库Schema",
                description=f"从 {data_source_name} 获取到 {len(schema_tables)} 个表结构",
                status="completed",
                duration=schema_duration,
                details=f"数据源: {data_source_name}\n表: {tables_preview}\nSchema大小: {schema_length} 字符",
                tenant_id=tenant_id
            )
        else:
            yield _create_processing_step(
                step=2,
                title="获取数据库Schema",
                description="已获取数据库结构信息",
                status="completed",
                tenant_id=tenant_id
            )
        # 确保事件被刷新到客户端
        await asyncio.sleep(0.05)

        # ========== Step 3: 构建AI Prompt ==========
        prompt_start_time = time.time()
        system_msg_content = ""
        for msg in messages:
            if msg.role == "system":
                system_msg_content = msg.content  # 显示完整内容，不截断
                break
        
        yield _create_processing_step(
            step=3,
            title="构建AI Prompt",
            description="将Schema注入系统提示词",
            status="completed",
            duration=int((time.time() - prompt_start_time) * 1000),
            details=f"System Prompt:\n{system_msg_content}",
            tenant_id=tenant_id
        )
        # 确保事件被刷新到客户端
        await asyncio.sleep(0.05)

        # ========== Step 4: AI生成SQL ==========
        ai_start_time = time.time()
        yield _create_processing_step(
            step=4,
            title="AI生成SQL",
            description="正在根据数据库Schema生成SQL查询...",
            status="running",
            tenant_id=tenant_id
        )
        # 确保事件被刷新到客户端
        await asyncio.sleep(0.05)

        # 🔧 新增：用于累积和更新步骤4的内容预览
        step4_content_preview = ""
        last_update_time = time.time()

        async for chunk in stream_generator:
            # 处理普通内容
            if chunk.type == "content":
                full_content += chunk.content

                # 🔧 新增：实时发送content delta到前端
                # 使用content_delta事件类型，避免与最终content冲突
                content_delta = {
                    "type": "content_delta",
                    "delta": chunk.content,
                    "provider": chunk.provider,
                    "tenant_id": tenant_id
                }
                yield f"data: {json.dumps(content_delta, ensure_ascii=False)}\n\n"

                # 🔧 新增：定期更新步骤4的描述，显示内容预览
                # 每100ms更新一次预览，避免过于频繁
                step4_content_preview += chunk.content
                current_time = time.time()
                if current_time - last_update_time >= 0.1:  # 100ms间隔
                    # 生成内容预览（限制长度）
                    preview_text = step4_content_preview[-200:] if len(step4_content_preview) > 200 else step4_content_preview
                    # 清理预览文本，移除markdown代码块标记等
                    preview_text = preview_text.replace("```sql", "").replace("```", "").strip()

                    step_update = {
                        "type": "step_update",
                        "step": 4,
                        "description": f"正在生成SQL... {len(step4_content_preview)} 字符",
                        "content_preview": preview_text,
                        "tenant_id": tenant_id
                    }
                    yield f"data: {json.dumps(step_update, ensure_ascii=False)}\n\n"
                    last_update_time = current_time

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
                logger.debug(f"流式响应完成，检测SQL查询。内容长度: {len(full_content)}")

                # 检测SQL代码块（提前检测，用于步骤4的content_data）
                sql_pattern = r'```sql\s*(.*?)\s*```'
                sql_matches = re.findall(sql_pattern, full_content, re.DOTALL | re.IGNORECASE)

                # ========== Step 4完成: AI生成SQL ==========
                # 准备SQL的content_data
                sql_content_data = None
                if sql_matches:
                    sql_content_data = {"sql": sql_matches[0].strip()}

                yield _create_processing_step(
                    step=4,
                    title="AI生成SQL",
                    description="SQL查询已生成",
                    status="completed",
                    duration=int((time.time() - ai_start_time) * 1000),
                    details=f"AI回复长度: {len(full_content)} 字符",
                    tenant_id=tenant_id,
                    content_type="sql" if sql_content_data else None,
                    content_data=sql_content_data
                )

                # 🔧 修复：在外层初始化图表生成标志，确保fallback路径可以访问
                chart_already_generated = False

                if sql_matches:
                    # ========== Step 5: 提取SQL语句 ==========
                    yield _create_processing_step(
                        step=5,
                        title="提取SQL语句",
                        description="正在从AI回复中提取SQL代码块...",
                        status="running",
                        tenant_id=tenant_id
                    )
                    
                    # 拆分每个代码块中可能包含的多个SQL语句，并去重
                    seen_sqls = set()
                    unique_sql_matches = []
                    for sql_block in sql_matches:
                        # 拆分一个代码块中的多个SQL语句
                        individual_statements = _split_multiple_sql_statements(sql_block)
                        logger.debug(f"流式响应：从代码块中拆分出 {len(individual_statements)} 个SQL语句")
                        
                        for sql in individual_statements:
                            normalized_sql = sql.strip().upper()  # 标准化比较
                            if normalized_sql not in seen_sqls:
                                seen_sqls.add(normalized_sql)
                                unique_sql_matches.append(sql)
                            else:
                                logger.warning(f"流式响应：检测到重复SQL，已跳过: {sql[:50]}...")

                    sql_matches = unique_sql_matches
                    logger.debug(f"检测到 {len(sql_matches)} 个唯一SQL查询，准备执行")
                    
                    # ========== Step 5完成: 提取SQL语句 ==========
                    # 格式化SQL预览
                    sql_preview = sql_matches[0].strip()
                    if len(sql_preview) > 300:
                        sql_preview = sql_preview[:300] + "\n..."
                    
                    yield _create_processing_step(
                        step=5,
                        title="提取SQL语句",
                        description=f"成功提取 {len(sql_matches)} 个SQL查询",
                        status="completed",
                        details=f"SQL语句:\n{sql_preview}",
                        tenant_id=tenant_id
                    )

                    # ========== Step 6: 执行SQL查询（或返回结果，取决于是否需要图表）==========
                    step6_title = "执行SQL查询" if should_generate_chart else "返回结果"
                    step6_desc = "正在连接数据源并执行查询..." if should_generate_chart else "正在整理查询结果..."
                    yield _create_processing_step(
                        step=6,
                        title=step6_title,
                        description=step6_desc,
                        status="running",
                        tenant_id=tenant_id
                    )
                    
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
                                logger.debug(f"流式响应：使用指定的数据源: {data_source.name} ({data_source.id})")
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

                        # 更新Step 6进度
                        exec_start_time = time.time()
                        step6_title = "执行SQL查询" if should_generate_chart else "返回结果"
                        step6_desc = f"已连接 {data_source.name}，正在执行 {len(sql_matches)} 个查询..." if should_generate_chart else f"已从 {data_source.name} 获取查询结果..."
                        yield _create_processing_step(
                            step=6,
                            title=step6_title,
                            description=step6_desc,
                            status="running",
                            details=f"数据源: {data_source.name}\n类型: {data_source.db_type}",
                            tenant_id=tenant_id
                        )

                        # 执行每个SQL查询（带智能重试）
                        total_rows = 0
                        # 🔧 修复：收集所有SQL执行结果，只在全部失败时显示错误
                        all_sql_results = []  # 存储每个SQL的执行结果 {'success': bool, 'sql': str, 'result': dict, 'error': str}
                        any_sql_success = False  # 标记是否有任何SQL成功
                        # 🔧 重构：收集所有成功的SQL结果，用于循环结束后统一生成图表
                        successful_query_results = []  # 存储成功的查询结果 [{'sql': str, 'result': dict, 'columns': list}]

                        # 🔧 新增：第6步流式输出 - 用于记录执行进度
                        step6_query_index = 0
                        step6_total_queries = len(sql_matches)

                        for sql_query in sql_matches:
                            current_sql = sql_query.strip()
                            retry_count = 0
                            max_retries = 2
                            last_error = None
                            execution_success = False
                            step6_query_index += 1

                            while retry_count <= max_retries and not execution_success:
                                try:
                                    # 🔧 流式输出：正在验证SQL语句
                                    step6_update = {
                                        "type": "step_update",
                                        "step": 6,
                                        "description": f"正在验证SQL语句 ({step6_query_index}/{step6_total_queries})...",
                                        "content_preview": current_sql[:100] + ("..." if len(current_sql) > 100 else ""),
                                        "streaming": True,
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(step6_update, ensure_ascii=False)}\n\n"

                                    # 安全检查：只允许SELECT查询（包括WITH...SELECT的CTE查询）
                                    # 使用统一的注释去除和检查函数
                                    sql_for_check, is_select, debug_msg = _strip_sql_comments_and_check_select(current_sql)
                                    logger.debug(f"[流式SQL检测] {debug_msg}")

                                    if not is_select:
                                        logger.warning(f"跳过非SELECT查询: {current_sql[:100]}")
                                        logger.warning(f"检测详情: {debug_msg}")
                                        break

                                    # 🔧 流式输出：正在建立数据库连接
                                    step6_update = {
                                        "type": "step_update",
                                        "step": 6,
                                        "description": f"正在连接 {data_source.name}...",
                                        "content_preview": f"数据源类型: {data_source.db_type}",
                                        "streaming": True,
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(step6_update, ensure_ascii=False)}\n\n"

                                    # 🔧 流式输出：正在执行查询
                                    step6_update = {
                                        "type": "step_update",
                                        "step": 6,
                                        "description": f"正在执行查询 ({step6_query_index}/{step6_total_queries})...",
                                        "content_preview": f"执行 {data_source.db_type.upper()} 查询中...",
                                        "streaming": True,
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(step6_update, ensure_ascii=False)}\n\n"

                                    # 根据数据源类型选择执行方式
                                    if data_source.db_type in ["xlsx", "xls", "csv"]:
                                        # 文件类型数据源：使用duckdb执行
                                        logger.debug(f"流式响应：使用duckdb执行文件数据源查询: {data_source.db_type}")
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
                                        # 预处理：去除AI可能错误添加的数据库名前缀
                                        if data_source.database_name:
                                            current_sql = _remove_database_name_prefix(current_sql, data_source.database_name)

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

                                    # 🔧 流式输出：正在处理结果集
                                    row_count_preview = result.get('row_count', 0)
                                    step6_update = {
                                        "type": "step_update",
                                        "step": 6,
                                        "description": "正在处理结果集...",
                                        "content_preview": f"已获取 {row_count_preview} 行数据，正在格式化...",
                                        "streaming": True,
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(step6_update, ensure_ascii=False)}\n\n"

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

                                        # 🔧 新增：记录SQL错误到错误记忆系统
                                        logger.debug(f"[SQL错误记忆] 准备记录SQL错误！retry_count={retry_count}, tenant_id={tenant_id[:20] if tenant_id else None}")
                                        try:
                                            error_memory_service = SQLErrorMemoryService(db)
                                            await error_memory_service.record_error(
                                                tenant_id=tenant_id,
                                                original_query=sql_query,
                                                error_message=last_error,
                                                fixed_query=current_sql,
                                                table_name=_extract_table_name_from_sql(sql_query),
                                                schema_context=None
                                            )
                                            logger.debug("[流式生成] SQL错误已记录到错误记忆系统")
                                        except Exception as record_error:
                                            logger.warning(f"[流式生成] 记录SQL错误失败: {record_error}")

                                    # 🔧 修复：不再发送 result_text 作为 content，避免与 ProcessingSteps 步骤6重复
                                    # 表格数据将通过步骤6 (content_type: 'table') 显示
                                    # result_chunk = {
                                    #     "type": "content",
                                    #     "content": result_text,
                                    #     "provider": chunk.provider,
                                    #     "finished": False,
                                    #     "tenant_id": tenant_id
                                    # }
                                    # yield f"data: {json.dumps(result_chunk, ensure_ascii=False)}\n\n"

                                    logger.debug(f"SQL查询执行成功，返回 {result.get('row_count', 0)} 行")
                                    total_rows += row_count
                                    execution_success = True
                                    any_sql_success = True  # 🔧 标记有SQL成功执行

                                    # 🔧 重构：收集成功的SQL结果，用于后续统一生成图表
                                    successful_query_results.append({
                                        'sql': current_sql,
                                        'result': result,
                                        'columns': result.get('columns', []),
                                        'row_count': row_count
                                    })

                                    # ========== Step 6完成: 执行SQL查询 ==========
                                    # 准备表格数据的content_data
                                    table_content_data = None
                                    if result.get('data') and result.get('columns'):
                                        # 限制最多50行用于前端显示
                                        rows_for_display = result['data'][:50]
                                        table_content_data = {
                                            "table": {
                                                "columns": result['columns'],
                                                "rows": rows_for_display,
                                                "row_count": row_count
                                            }
                                        }

                                    yield _create_processing_step(
                                        step=6,
                                        title="返回结果" if not should_generate_chart else "执行SQL查询",
                                        description=f"✅ 查询完成，返回 {row_count} 行数据",
                                        status="completed",
                                        duration=int((time.time() - exec_start_time) * 1000),
                                        details=f"数据源: {data_source.name}\n返回行数: {row_count}\n执行耗时: {int((time.time() - exec_start_time) * 1000)}ms",
                                        tenant_id=tenant_id,
                                        content_type="table" if table_content_data else None,
                                        content_data=table_content_data
                                    )

                                    # 🔧 重构：二次LLM调用移到循环结束后统一处理
                                    # 这里不再做任何处理，等待所有SQL执行完毕后统一生成图表
                                    # 旧代码（已废弃）：只对第一个成功的SQL生成图表
                                    if False:  # 🔧 禁用循环内的二次LLM调用
                                        logger.debug("开始二次LLM调用：分析数据并生成图表")
                                        
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
                                        
                                        # 检测层级结构数据：parent_id, 一级/二级分类, level等关键词
                                        has_hierarchy_col = any(k in col_names_str for k in [
                                            'parent', 'child', 'level', 'depth', 'hierarchy', 
                                            '一级', '二级', '三级', '父', '子', '层级', '分类', 'category',
                                            'parent_id', 'parent_name', 'subcategory', '子类', '结构'
                                        ])
                                        
                                        # 检测排名类数据：Top N、最高/最低 N 个、排名等
                                        original_question_lower = original_question.lower() if original_question else ""
                                        sql_lower = current_sql.lower() if current_sql else ""
                                        is_ranking_query = any(k in original_question_lower for k in [
                                            'top', '最高', '最低', '最多', '最少', '排名', '前几', '前5', '前10',
                                            '评分最高', '评分最低', '销量最高', '销量最低', '排行', '排序'
                                        ]) or ('order by' in sql_lower and 'limit' in sql_lower)
                                        
                                        analysis_directive = ""
                                        supplementary_stats = ""

                                        # 🔧 修复：如果问题类型不需要图表（如SCHEMA_QUERY），强制禁止生成图表
                                        if not should_generate_chart:
                                            analysis_directive = (
                                                "🛑 **CONSTRAINT**: Schema查询不需要图表.\n"
                                                "- **DO NOT** generate any chart.\n"
                                                "- **DO NOT** explain why you are not generating a chart. Just skip it silently.\n\n"
                                                "- Focus on listing the tables and their structure clearly.\n"
                                            )
                                        # 规则 1: 单行数据（聚合结果）-> 禁止画图，但要展示计算过程
                                        elif analysis_row_count <= 1:
                                            # 🔧 执行补充查询获取统计信息
                                            try:
                                                # 从SQL中提取表名
                                                table_match = re.search(r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', current_sql, re.IGNORECASE)
                                                if table_match:
                                                    table_name = table_match.group(1)
                                                    # 构建统计查询
                                                    stats_sql = f"SELECT COUNT(*) as 总记录数 FROM {table_name}"
                                                    
                                                    # 检测原SQL中使用的金额/数量字段
                                                    amount_match = re.search(r'SUM\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', current_sql, re.IGNORECASE)
                                                    if amount_match:
                                                        amount_field = amount_match.group(1)
                                                        stats_sql = f"""SELECT 
                                                            COUNT(*) as 总记录数, 
                                                            MIN({amount_field}) as 最小值, 
                                                            MAX({amount_field}) as 最大值, 
                                                            ROUND(AVG({amount_field})::numeric, 2) as 平均值
                                                        FROM {table_name}"""
                                                    
                                                    logger.debug(f"执行补充统计查询: {stats_sql}")
                                                    
                                                    # 执行统计查询
                                                    if data_source.db_type in ["xlsx", "xls", "csv"]:
                                                        stats_result = await _execute_sql_on_file_datasource(
                                                            connection_string=connection_string,
                                                            db_type=data_source.db_type,
                                                            sql_query=stats_sql,
                                                            data_source_name=data_source.name
                                                        )
                                                    else:
                                                        stats_adapter = PostgreSQLAdapter(connection_string)
                                                        try:
                                                            await stats_adapter.connect()
                                                            stats_query_result = await stats_adapter.execute_query(stats_sql)
                                                            stats_result = {
                                                                "data": stats_query_result.data,
                                                                "columns": stats_query_result.columns
                                                            }
                                                        finally:
                                                            await stats_adapter.disconnect()
                                                    
                                                    # 格式化统计信息
                                                    if stats_result.get('data') and len(stats_result['data']) > 0:
                                                        stats_data = stats_result['data'][0]
                                                        stats_parts = []
                                                        for key, value in stats_data.items():
                                                            if value is not None:
                                                                # 格式化数字
                                                                if isinstance(value, (int, float)):
                                                                    formatted_value = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
                                                                else:
                                                                    formatted_value = str(value)
                                                                stats_parts.append(f"{key}: {formatted_value}")
                                                        supplementary_stats = " | ".join(stats_parts)
                                                        logger.debug(f"补充统计信息: {supplementary_stats}")
                                            except Exception as stats_error:
                                                logger.warning(f"获取补充统计信息失败: {stats_error}")
                                            
                                            # 构建带有统计信息的分析指令
                                            stats_context = ""
                                            if supplementary_stats:
                                                stats_context = f"\n\n📊 **补充统计数据**（已自动查询）:\n{supplementary_stats}\n请在回答中引用这些数据来展示计算过程。"
                                            
                                            analysis_directive = (
                                                "🛑 **CONSTRAINT**: The result contains only 1 row (aggregated result like SUM, COUNT, AVG).\n"
                                                "- **DO NOT** generate any chart.\n"
                                                "- **DO NOT** explain why you are not generating a chart. Just skip it silently.\n\n"
                                                "📊 **IMPORTANT - 展示计算过程**:\n"
                                                "- 在给出最终结果之前，先用补充统计数据说明计算依据\n"
                                                "- 格式要求：\n"
                                                "  📋 **计算依据**：共 X 条记录\n"
                                                "  💰 **数据范围**：最小值 ¥X ~ 最大值 ¥X（平均 ¥X）\n"
                                                "  📈 **最终结果**：¥X,XXX,XXX"
                                                f"{stats_context}"
                                            )
                                        elif not has_metric_col and analysis_row_count < 50:
                                            analysis_directive = (
                                                "🛑 **CONSTRAINT**: This appears to be a text list without numerical metrics.\n"
                                                "- **DO NOT** generate any chart.\n"
                                                "- **DO NOT** explain why you are not generating a chart. Just skip it silently.\n"
                                                "- Summarize the list content (e.g., total count, examples)."
                                            )
                                        # 规则 2: 层级结构数据 -> 使用树状图
                                        elif has_hierarchy_col:
                                            analysis_directive = (
                                                "✅ **STRATEGY**: This is hierarchical/tree-structured data (parent-child relationship).\n"
                                                "- **ACTION**: You MUST call `generate_chart` with `chart_type='tree'`.\n"
                                                "- The tree chart is perfect for showing category structures, organizational hierarchies, etc.\n"
                                                "- **Analysis**: Describe the hierarchy structure, levels, and distribution."
                                            )
                                        # 规则 2.5: 排名类数据 -> 强制使用柱状图（不用饼图）
                                        elif is_ranking_query and analysis_row_count > 1:
                                            # 找到最可能的名称列和数值列
                                            name_col = None
                                            value_col = None
                                            for col in columns:
                                                col_lower = str(col).lower()
                                                if col_lower in ['name', 'product_name', '名称', '产品名', '商品名', 'title']:
                                                    name_col = col
                                                elif col_lower in ['count', 'total', 'sum', 'amount', 'quantity', 'review_count', 'sales', '数量', '金额', '销量', '评价数']:
                                                    value_col = col
                                            
                                            chart_hint = ""
                                            if name_col and value_col:
                                                chart_hint = f"\n- **Hint**: Use '{name_col}' for X-axis labels and '{value_col}' for Y-axis values."
                                            elif name_col:
                                                chart_hint = f"\n- **Hint**: Use '{name_col}' for X-axis labels. Find a numeric column for Y-axis."
                                            
                                            analysis_directive = (
                                                "✅ **STRATEGY**: This is RANKING data (Top N, highest/lowest).\n"
                                                "- **ACTION**: You MUST generate a bar chart using [CHART_START]...[CHART_END] format.\n"
                                                "- ⚠️ DO NOT skip chart generation! This ranking data NEEDS visualization.\n"
                                                "- ⚠️ DO NOT use pie chart! Ranking data shows absolute values, not proportions.\n"
                                                f"{chart_hint}\n"
                                                "- **Analysis**: Compare the values, highlight the leader and gaps between ranks."
                                            )
                                        # 规则 3: 大数据量 -> 强制 Top N 柱状图
                                        elif analysis_row_count > 20 and not has_time_col:
                                            analysis_directive = (
                                                f"⚠️ **CONSTRAINT**: The result has {analysis_row_count} rows, which is too many for a clean chart.\n"
                                                "- **ACTION**: You MUST generate a bar chart using [CHART_START]...[CHART_END] format.\n"
                                                "- ⚠️ DO NOT skip chart generation! Only include the **Top 10** data points.\n"
                                                "- In your text analysis, mention that you are showing the top performers."
                                            )
                                        # 规则 4: 时间序列 -> 强制折线图
                                        elif has_time_col and analysis_row_count > 1:
                                            analysis_directive = (
                                                "✅ **STRATEGY**: This is time-series data (trend analysis).\n"
                                                "- **ACTION**: You MUST generate a line chart using [CHART_START]...[CHART_END] format.\n"
                                                "- ⚠️ DO NOT skip chart generation! Time-series data ALWAYS needs a trend chart.\n"
                                                "- Use 'line' chart type to show the trend over time.\n"
                                                "- **Analysis**: Focus on the trend (upward/downward), seasonality, or spikes."
                                            )
                                        # 规则 5: 分类对比或其他多行数据 -> 默认生成图表
                                        else:
                                            chart_suggestion = "pie" if analysis_row_count <= 5 else "bar"
                                            analysis_directive = (
                                                f"✅ **STRATEGY**: This data has {analysis_row_count} rows and can be visualized.\n"
                                                f"- **ACTION**: You MUST generate a chart using [CHART_START]...[CHART_END] format.\n"
                                                f"- ⚠️ DO NOT skip chart generation! Use '{chart_suggestion}' chart type.\n"
                                                "- **Analysis**: Compare the magnitudes. Identify the leader and the laggard."
                                            )
                                        
                                        logger.debug(f"数据特征分析: rows={analysis_row_count}, cols={col_count}, has_time={has_time_col}, has_metric={has_metric_col}")
                                        
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
   - 中间是**纯JSON格式的ECharts配置**
   - 不要使用 markdown 代码块包裹 JSON
   - **禁止使用JavaScript函数**！formatter只能用字符串模板，如 "{{b}}: {{c}}"
   
   ✅ **正确示例（折线图）**：
[CHART_START]
{{"title":{{"text":"月度销售趋势","left":"center"}},"tooltip":{{"trigger":"axis","formatter":"{{b}}: {{c}}元"}},"xAxis":{{"type":"category","data":["1月","2月","3月"]}},"yAxis":{{"type":"value","name":"销售额"}},"series":[{{"name":"销售额","type":"line","data":[12000,15000,18000]}}]}}
[CHART_END]

   ✅ **正确示例（柱状图）**：
[CHART_START]
{{"title":{{"text":"商品库存排名"}},"tooltip":{{"trigger":"axis"}},"xAxis":{{"type":"category","data":["华为MateBook","iPhone 15","小米电视"]}},"yAxis":{{"type":"value","name":"库存数量"}},"series":[{{"name":"库存","type":"bar","data":[100,80,50]}}]}}
[CHART_END]

   ✅ **正确示例（树状图 - 适用于层级/分类结构数据）**：
[CHART_START]
{{"title":{{"text":"产品类别结构","left":"center"}},"tooltip":{{"trigger":"item"}},"series":[{{"type":"tree","data":[{{"name":"全部类别","children":[{{"name":"电子产品","children":[{{"name":"手机通讯","value":3}},{{"name":"电脑办公","value":2}},{{"name":"数码配件","value":5}}]}},{{"name":"服装鞋包","children":[{{"name":"男装","value":4}},{{"name":"女装","value":6}}]}},{{"name":"家居生活","value":8}}]}}],"top":"5%","left":"10%","bottom":"5%","right":"10%","symbol":"circle","symbolSize":10,"orient":"TB","label":{{"position":"top","fontSize":12}},"leaves":{{"label":{{"position":"bottom"}}}},"expandAndCollapse":false,"animationDuration":550}}]}}
[CHART_END]

   ❌ **错误格式（绝对禁止）**：
   - "formatter": function(params) {{...}} ← **禁止使用JavaScript函数！**
   - {{"chartType": "bar"}} ← 这不是 ECharts 格式！

请直接输出分析和图表："""

                                        # 构建专家数据分析师的系统提示
                                        expert_system_prompt = (
                                            "你是一位专业的数据分析师。你的任务是从数据中提取洞察并有效地可视化它们。\n\n"
                                            "**核心原则 - 默认生成图表：**\n"
                                            "⚠️ 除非明确被告知'禁止画图'，否则你必须生成图表！数据可视化对用户理解数据非常重要。\n\n"
                                            "**核心协议：**\n"
                                            "1. **积极可视化**：只要数据有多行，就应该生成图表。图表是数据分析的核心产出！\n"
                                            "2. **遵循指令**：系统给出的约束（如'禁止画图'或'使用柱状图'）必须严格遵守。\n"
                                            "3. **数据分析**：不要只重复数字。解释数据的意义（例如，不要说'A是100，B是50'，而要说'A的表现是B的2倍'）。\n"
                                            "4. **图表格式**：必须使用标准的 ECharts JSON 配置格式，用 [CHART_START] 和 [CHART_END] 标记包裹。\n"
                                            "5. **不解释跳过图表的原因**：当不需要生成图表时，直接不生成，不要解释为什么不生成图表。\n"
                                            "6. **层级结构用树状图**：当数据包含层级/分类结构（如一级分类→二级分类）时，使用 type='tree' 的树状图展示。\n\n"
                                            "**图表类型选择：**\n"
                                            "- 时间序列/趋势数据 → 折线图 (line)\n"
                                            "- 排名/对比数据 → 柱状图 (bar)\n"
                                            "- 占比/分布数据 → 饼图 (pie)\n"
                                            "- 层级/分类结构 → 树状图 (tree)\n\n"
                                            "**重要提醒（必须严格遵守）：**\n"
                                            "- 图表配置必须是**纯JSON格式**，包含 title、xAxis、yAxis、series 等字段\n"
                                            "- **绝对禁止使用JavaScript函数！** 例如禁止: \"formatter\": function(params){...}\n"
                                            "- tooltip的formatter只能用字符串模板，如: \"formatter\": \"{b}: {c}元\"\n"
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
                                                # 🔧 修复：不再发送"数据分析中..."状态，避免与 ProcessingSteps 重复
                                                # analysis_status = {
                                                #     "type": "content",
                                                #     "content": "\n\n📊 **数据分析中...**\n\n",
                                                #     "provider": chunk.provider,
                                                #     "finished": False,
                                                #     "tenant_id": tenant_id
                                                # }
                                                # yield f"data: {json.dumps(analysis_status, ensure_ascii=False)}\n\n"
                                                
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
                                                        # 🔧 修复：不再发送 content 事件，避免与 ProcessingSteps 步骤8重复
                                                        # 分析内容将通过步骤8 (processing_step) 发送
                                                        # analysis_data = {
                                                        #     "type": "content",
                                                        #     "content": analysis_chunk.content,
                                                        #     "provider": analysis_chunk.provider,
                                                        #     "finished": False,
                                                        #     "tenant_id": tenant_id
                                                        # }
                                                        # yield f"data: {json.dumps(analysis_data, ensure_ascii=False)}\n\n"
                                                
                                                logger.debug(f"二次LLM调用完成，分析内容长度: {len(analysis_content)}")
                                                
                                                # 检测并提取图表配置
                                                chart_pattern = r'\[CHART_START\](.*?)\[CHART_END\]'
                                                chart_match = re.search(chart_pattern, analysis_content, re.DOTALL)
                                                
                                                if chart_match:
                                                    try:
                                                        chart_json_str = chart_match.group(1).strip()
                                                        logger.debug(f"📊 提取到的ECharts JSON (前500字符): {chart_json_str[:500]}")
                                                        
                                                        # 尝试修复常见的JSON格式问题
                                                        # 1. 移除可能的markdown代码块标记
                                                        if chart_json_str.startswith('```'):
                                                            lines = chart_json_str.split('\n')
                                                            # 移除第一行(```json)和最后一行(```)
                                                            if lines[0].startswith('```'):
                                                                lines = lines[1:]
                                                            if lines and lines[-1].strip() == '```':
                                                                lines = lines[:-1]
                                                            chart_json_str = '\n'.join(lines)
                                                        
                                                        # 2. 移除JavaScript函数（AI有时仍会生成）
                                                        # 匹配 "formatter": function(...){...} 等模式
                                                        import re as regex_module
                                                        # 简单的函数替换：将 function(...){...} 替换为字符串
                                                        chart_json_str = regex_module.sub(
                                                            r'"formatter":\s*function\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}',
                                                            '"formatter": "{b}: {c}"',
                                                            chart_json_str
                                                        )
                                                        
                                                        # 3. 确保JSON字符串是完整的
                                                        chart_json_str = chart_json_str.strip()
                                                        
                                                        echarts_option = json.loads(chart_json_str)
                                                        logger.debug(f"✅ 成功提取 ECharts 配置: {list(echarts_option.keys())}")
                                                        
                                                        # 发送图表配置事件
                                                        chart_event = {
                                                            "type": "chart_config",
                                                            "data": {"echarts_option": echarts_option},
                                                            "provider": "deepseek",
                                                            "finished": False,
                                                            "tenant_id": tenant_id
                                                        }
                                                        yield f"data: {json.dumps(chart_event, ensure_ascii=False)}\n\n"

                                                        # ========== Step 7: 生成数据可视化 ==========
                                                        # 推断图表类型
                                                        chart_type = "图表"
                                                        series_list = echarts_option.get("series", [])
                                                        if series_list and len(series_list) > 0:
                                                            series_type = series_list[0].get("type", "")
                                                            if series_type:
                                                                chart_type = {
                                                                    "bar": "柱状图", "line": "折线图", "pie": "饼图",
                                                                    "scatter": "散点图", "effectScatter": "气泡图",
                                                                    "tree": "树图", "treemap": "矩形树图",
                                                                    "sunburst": "旭日图", "funnel": "漏斗图",
                                                                    "gauge": "仪表盘"
                                                                }.get(series_type, series_type)

                                                        chart_content_data = {
                                                            "chart": {
                                                                "echarts_option": echarts_option,
                                                                "chart_type": chart_type
                                                            }
                                                        }

                                                        yield _create_processing_step(
                                                            step=7,
                                                            title="生成数据可视化",
                                                            description=f"创建 {chart_type} 展示分析结果",
                                                            status="completed",
                                                            duration=int((time.time() - ai_start_time) * 1000 * 0.3),
                                                            tenant_id=tenant_id,
                                                            content_type="chart",
                                                            content_data=chart_content_data
                                                        )
                                                        # 🔧 修复：标记图表已生成，避免fallback路径重复
                                                        chart_already_generated = True

                                                        # ========== Step 8: 数据分析总结 ==========
                                                        # 移除图表标记，提取纯文本分析
                                                        clean_analysis = re.sub(chart_pattern, '', analysis_content, flags=re.DOTALL).strip()
                                                        # 移除多余的空行
                                                        clean_analysis = re.sub(r'\n{3,}', '\n\n', clean_analysis)

                                                        if clean_analysis:
                                                            yield _create_processing_step(
                                                                step=8,
                                                                title="数据分析总结",
                                                                description="AI对查询结果的分析和解读",
                                                                status="completed",
                                                                duration=int((time.time() - ai_start_time) * 1000 * 0.2),
                                                                tenant_id=tenant_id,
                                                                content_type="text",
                                                                content_data={"text": clean_analysis}
                                                            )
                                                    except json.JSONDecodeError as e:
                                                        logger.warning(f"解析 ECharts JSON 失败: {e}")
                                                        logger.warning(f"失败的JSON内容 (前300字符): {chart_json_str[:300] if chart_json_str else 'None'}")

                                                else:
                                                    # ========== Step 8: 数据分析总结（无图表情况）==========
                                                    # 没有图表时，直接使用分析内容作为总结
                                                    clean_analysis = analysis_content.strip()
                                                    # 移除多余的空行
                                                    clean_analysis = re.sub(r'\n{3,}', '\n\n', clean_analysis)

                                                    if clean_analysis:
                                                        yield _create_processing_step(
                                                            step=8,
                                                            title="数据分析总结",
                                                            description="AI对查询结果的分析和解读",
                                                            status="completed",
                                                            duration=int((time.time() - ai_start_time) * 1000 * 0.2),
                                                            tenant_id=tenant_id,
                                                            content_type="text",
                                                            content_data={"text": clean_analysis}
                                                        )

                                            except Exception as e:
                                                logger.error(f"二次LLM调用失败: {e}")
                                    elif execution_success and result.get('data') and chart_already_generated:
                                        # 🔧 修复：跳过后续SQL的图表生成，避免多个图表叠加
                                        logger.debug("🔧 跳过此SQL的图表生成，图表已通过之前的SQL结果生成")

                                except Exception as e:
                                    last_error = str(e)
                                    logger.error(f"执行SQL查询失败 (尝试 {retry_count + 1}/{max_retries + 1}): {e}")

                                    # 🔧 流式输出：SQL执行失败通知
                                    error_preview = str(e)[:100] + ("..." if len(str(e)) > 100 else "")
                                    step6_error = {
                                        "type": "step_update",
                                        "step": 6,
                                        "description": f"❌ SQL执行失败 (尝试 {retry_count + 1}/{max_retries + 1})",
                                        "content_preview": f"错误: {error_preview}",
                                        "streaming": True,
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(step6_error, ensure_ascii=False)}\n\n"

                                    # 如果还有重试机会，尝试用AI修复SQL
                                    if retry_count < max_retries:
                                        # 🔧 流式输出：正在使用AI修复SQL
                                        step6_fixing = {
                                            "type": "step_update",
                                            "step": 6,
                                            "description": f"🔧 正在使用AI修复SQL... (第 {retry_count + 1} 次重试)",
                                            "content_preview": "分析错误原因并生成修复方案",
                                            "streaming": True,
                                            "tenant_id": tenant_id
                                        }
                                        yield f"data: {json.dumps(step6_fixing, ensure_ascii=False)}\n\n"

                                        logger.debug("尝试使用AI修复SQL...")
                                        fixed_sql = await _fix_sql_with_ai(
                                            original_sql=current_sql,
                                            error_message=last_error,
                                            schema_context=schema_context,
                                            original_question=original_question,
                                            db_type=data_source.db_type,  # 传递数据库类型
                                            tenant_id=tenant_id  # 传递租户ID用于llm_service
                                        )

                                        if fixed_sql:
                                            logger.debug(f"AI修复成功，准备重试。修复后的SQL: {fixed_sql[:100]}...")

                                            # 🔧 流式输出：AI修复成功通知
                                            step6_fixed = {
                                                "type": "step_update",
                                                "step": 6,
                                                "description": "✅ AI修复成功，准备重试",
                                                "content_preview": fixed_sql[:100] + ("..." if len(fixed_sql) > 100 else ""),
                                                "streaming": True,
                                                "tenant_id": tenant_id
                                            }
                                            yield f"data: {json.dumps(step6_fixed, ensure_ascii=False)}\n\n"

                                            current_sql = fixed_sql
                                            retry_count += 1
                                        else:
                                            logger.warning("AI无法修复SQL，停止重试")

                                            # 🔧 流式输出：AI修复失败通知
                                            step6_fix_failed = {
                                                "type": "step_update",
                                                "step": 6,
                                                "description": "❌ AI无法修复SQL，停止重试",
                                                "content_preview": "建议检查SQL语法或数据源结构",
                                                "streaming": True,
                                                "tenant_id": tenant_id
                                            }
                                            yield f"data: {json.dumps(step6_fix_failed, ensure_ascii=False)}\n\n"
                                            break
                                    else:
                                        # 已达到最大重试次数
                                        logger.error(f"已达到最大重试次数 ({max_retries})，放弃执行")

                                        # 🔧 流式输出：达到最大重试次数通知
                                        step6_max_retries = {
                                            "type": "step_update",
                                            "step": 6,
                                            "description": f"❌ 已达到最大重试次数 ({max_retries})，放弃执行",
                                            "content_preview": "所有尝试均失败",
                                            "streaming": True,
                                            "tenant_id": tenant_id
                                        }
                                        yield f"data: {json.dumps(step6_max_retries, ensure_ascii=False)}\n\n"
                                        break

                            # 🔧 修复：如果此SQL的所有重试都失败了，收集错误信息（不立即发送）
                            if not execution_success and last_error:
                                # 解析错误信息，提取关键信息
                                error_details = _parse_sql_error(last_error)

                                # 收集错误信息，稍后统一处理
                                all_sql_results.append({
                                    'success': False,
                                    'sql': current_sql,
                                    'error': last_error,
                                    'error_details': error_details,
                                    'retry_count': retry_count
                                })
                                logger.debug("🔧 收集SQL执行错误信息（暂不发送），等待其他SQL结果")

                        # 🔧 修复：for循环结束后，统一处理错误信息
                        # 只有当所有SQL都失败时才显示错误
                        if not any_sql_success and all_sql_results:
                            logger.warning(f"🔧 所有 {len(all_sql_results)} 个SQL查询都失败了，显示错误信息")

                            # 显示最后一个失败SQL的错误信息（通常是最相关的）
                            last_failed = all_sql_results[-1]
                            error_details = last_failed['error_details']
                            retry_count = last_failed['retry_count']
                            current_sql = last_failed['sql']

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
                        elif any_sql_success and all_sql_results:
                            # 有SQL成功，但也有失败的，只记录日志不显示错误
                            failed_count = len([r for r in all_sql_results if not r['success']])
                            if failed_count > 0:
                                logger.debug(f"🔧 有 {failed_count} 个SQL失败但至少1个成功，不显示错误信息")

                        # ========== 🔧 重构：统一图表生成逻辑（循环结束后） ==========
                        # 收集所有成功的SQL结果，一次性调用LLM生成分析和图表（支持多图表）
                        # 🔧 修复：根据问题类型决定是否生成图表
                        if successful_query_results:
                            logger.debug(f"🔧 开始统一数据分析和图表生成：共有 {len(successful_query_results)} 个成功的SQL结果, should_generate_chart={should_generate_chart}")

                            # 🔧 如果不需要图表（如SCHEMA_QUERY），跳过图表生成，直接发送数据
                            if not should_generate_chart:
                                logger.debug("🔧 跳过图表生成，直接返回查询结果")
                                # 构建 JSON 数据摘要
                                all_results_summary = []
                                for idx, query_result in enumerate(successful_query_results, 1):
                                    result_data = query_result['result']
                                    data_for_analysis = result_data.get('data', [])[:20]
                                    row_count = query_result['row_count']
                                    columns = query_result['columns']
                                    serializable_data = _convert_decimal_to_float(data_for_analysis)

                                    result_summary = {
                                        'query_index': idx,
                                        'sql': query_result['sql'][:200] + '...' if len(query_result['sql']) > 200 else query_result['sql'],
                                        'columns': columns,
                                        'row_count': row_count,
                                        'data_preview': serializable_data
                                    }
                                    all_results_summary.append(result_summary)

                                # 直接返回数据结果
                                for idx, query_result in enumerate(successful_query_results, 1):
                                    result_data = query_result['result']
                                    table_content_data = {
                                        "table": {
                                            "columns": query_result['columns'],
                                            "rows": result_data.get('data', [])[:50],  # 限制50行
                                            "row_count": query_result['row_count']
                                        }
                                    }
                                    # 发送表格数据
                                    table_event = {
                                        "type": "content_delta",
                                        "delta": f"\n\n## 查询结果 {idx}/{len(successful_query_results)}\n\n",
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(table_event, ensure_ascii=False)}\n\n"

                                    # 发送表格内容事件
                                    table_event = {
                                        "type": "table_data",
                                        "data": table_content_data,
                                        "tenant_id": tenant_id
                                    }
                                    yield f"data: {json.dumps(table_event, ensure_ascii=False)}\n\n"

                                # 跳过后续的图表生成逻辑
                                chart_already_generated = True
                            else:
                                # 🔧 需要生成图表的情况：构建包含所有查询结果的数据摘要
                                all_results_summary = []
                                for idx, query_result in enumerate(successful_query_results, 1):
                                    result_data = query_result['result']
                                    data_for_analysis = result_data.get('data', [])[:20]  # 每个结果最多20行
                                    row_count = query_result['row_count']
                                    columns = query_result['columns']

                                    # 将 Decimal 转换为 float
                                    serializable_data = _convert_decimal_to_float(data_for_analysis)

                                    result_summary = {
                                        'query_index': idx,
                                        'sql': query_result['sql'][:200] + '...' if len(query_result['sql']) > 200 else query_result['sql'],
                                        'columns': columns,
                                        'row_count': row_count,
                                        'data_preview': serializable_data
                                    }
                                    all_results_summary.append(result_summary)

                                # 数据特征分析
                                total_queries = len(successful_query_results)
                                total_rows = sum(r['row_count'] for r in successful_query_results)

                                # 分析每个结果集的特征
                                analysis_hints = []
                                for idx, query_result in enumerate(successful_query_results, 1):
                                    result_data = query_result['result']
                                    columns = query_result['columns']
                                    row_count = query_result['row_count']

                                    col_names_str = " ".join([str(c).lower() for c in columns])
                                    has_time_col = any(k in col_names_str for k in ['date', 'time', 'year', 'month', 'day', '日期', '时间', '年', '月'])

                                    if row_count <= 1:
                                        analysis_hints.append(f"查询{idx}: 聚合结果（1行），不需要图表")
                                    elif has_time_col and row_count > 1:
                                        analysis_hints.append(f"查询{idx}: 时间序列数据（{row_count}行），适合折线图")
                                    elif row_count > 1:
                                        analysis_hints.append(f"查询{idx}: 分类数据（{row_count}行），适合柱状图或饼图")

                                analysis_hints_text = "\n".join(analysis_hints)

                                # 构建多结果分析prompt
                                multi_result_json = json.dumps(all_results_summary, ensure_ascii=False, indent=2)

                                # 🔧 根据是否为拆分请求，添加不同的指令
                                # 🔴🔴🔴 关键修复：根据用户指定的图表数量生成不同的指令
                                if is_split_request and chart_count:
                                    # 用户明确指定了图表数量
                                    split_instruction = f"""
**🚨🚨🚨 图表拆分要求（用户明确要求生成 {chart_count} 个独立图表）！**

用户刚刚说"拆成{chart_count}个"或类似表达，**你必须生成恰好 {chart_count} 个图表配置！**

🔴 **关键规则（必须严格遵守）**：
1. 识别SQL结果中有哪些可度量指标（数值列）
2. 如果指标数量 < {chart_count}，用不同图表类型展示同一指标：
   - 同一指标可以生成：折线图 + 柱状图 + 饼图（如果是占比数据）
   - 例如：2个指标要生成4个图 → 指标1折线图 + 指标1柱状图 + 指标2折线图 + 指标2柱状图
3. 每个图表使用独立的 [CHART_START]...[CHART_END] 标记
4. **必须生成恰好 {chart_count} 个图表，不能多也不能少！**

🔴 **示例：生成 {chart_count} 个图表**
假设有2个指标（销售额、订单数），用户要求 {chart_count} 个图表：
第1个图表：销售额折线图
[CHART_START]
{{"title":{{"text":"销售额趋势"}},"series":[{{"type":"line"}}]}}
[CHART_END]

第2个图表：销售额柱状图
[CHART_START]
{{"title":{{"text":"销售额对比"}},"series":[{{"type":"bar"}}]}}
[CHART_END]

... 继续生成直到 {chart_count} 个图表 ...
"""
                                elif is_split_request:
                                    # 用户只说拆分，没有指定数量
                                    split_instruction = """
**🚨🚨🚨 图表拆分要求（用户明确请求将图表拆分）！**

用户要求将组合图表拆分成多个独立图表。你必须：
1. 识别每个SQL结果中有哪些可度量指标（数值列）
2. 为每个指标生成一个独立的图表配置
3. 每个图表只包含一个指标的数据
4. 例如：如果结果有"员工人数"和"平均薪资"两列，生成两个独立图表

🔴 **拆分后图表示例**：
第一个图表（员工人数柱状图）：
[CHART_START]
{"title":{"text":"各部门员工人数"},"xAxis":{"type":"category","data":["技术部","销售部"]},"yAxis":{"type":"value","name":"人数"},"series":[{"type":"bar","data":[10,8]}]}
[CHART_END]

第二个图表（平均薪资柱状图）：
[CHART_START]
{"title":{"text":"各部门平均薪资"},"xAxis":{"type":"category","data":["技术部","销售部"]},"yAxis":{"type":"value","name":"薪资(元)"},"series":[{"type":"bar","data":[15000,12000]}]}
[CHART_END]
"""
                                else:
                                    split_instruction = ""

                                multi_analysis_prompt = f"""你刚刚执行了 {total_queries} 个SQL查询，所有结果如下：

```json
{multi_result_json}
```

--- 数据特征分析 ---
{analysis_hints_text}

{split_instruction}

--- 任务要求 ---

1. **数据分析**：综合分析所有查询结果，用2-3句话解释数据的商业含义

2. **生成图表**（如果需要多个图表，请分别生成）：

   ⚠️ **重要规则**：
   - 每个需要可视化的数据集，使用独立的 [CHART_START]...[CHART_END] 标记
   - 如果有多个数据集都需要图表，就生成多个图表配置
   - 聚合结果（只有1行）不需要生成图表
   - 时间序列数据用折线图，分类比较用柱状图，占比用饼图

   ✅ **多图表示例**（2个数据集各自生成图表）：

   第一个图表展示销售趋势：
[CHART_START]
{{"title":{{"text":"月度销售趋势"}},"xAxis":{{"type":"category","data":["1月","2月","3月"]}},"yAxis":{{"type":"value"}},"series":[{{"type":"line","data":[100,200,150]}}]}}
[CHART_END]

   第二个图表展示类别分布：
[CHART_START]
{{"title":{{"text":"商品类别占比"}},"series":[{{"type":"pie","data":[{{"name":"电子产品","value":60}},{{"name":"服装","value":40}}]}}]}}
[CHART_END]

   ❌ **禁止**：
   - 不要使用JavaScript函数
   - 不要用markdown代码块包裹JSON
   - 不要把多个图表合并到一个配置里

请直接输出分析和图表："""

                                # 构建系统提示
                                # 图表拆分指令（当用户请求拆分时添加）
                                split_instruction_prompt = ""
                                if is_split_request and chart_count:
                                    # 用户明确指定了图表数量
                                    split_instruction_prompt = (
                                        f"**🚨🚨🚨 用户请求将图表拆分成 {chart_count} 个独立图表！**\n"
                                        f"你必须生成恰好 {chart_count} 个图表配置！\n"
                                        f"如果指标数量少于 {chart_count}，用不同图表类型（折线图、柱状图、饼图）展示同一指标。\n"
                                        f"使用多个[CHART_START]...[CHART_END]标记，每个标记一个图表！\n\n"
                                    )
                                elif is_split_request:
                                    split_instruction_prompt = (
                                        "**🚨🚨🚨 用户请求将图表拆分！**\n"
                                        "如果SQL结果包含多个指标（如员工人数和平均薪资），你必须：\n"
                                        "1. 为每个指标生成独立的图表配置\n"
                                        "2. 每个图表只包含一个指标的数据\n"
                                        "3. 使用多个[CHART_START]...[CHART_END]标记\n"
                                        "4. 不要把多个指标放在同一个图表里！\n\n"
                                    )

                                multi_chart_system_prompt = (
                                    "你是专业的数据分析师。你的任务是分析多个SQL查询结果并生成可视化图表。\n\n"
                                    "**核心原则**：\n"
                                    "1. 每个有意义的数据集都应该有自己的图表\n"
                                    "2. 多个数据集 = 多个独立的图表配置\n"
                                    "3. 聚合结果（1行数据）不生成图表\n"
                                    "4. 使用标准ECharts JSON格式，用[CHART_START]...[CHART_END]标记\n"
                                    "5. 禁止使用JavaScript函数\n\n"
                                    + split_instruction_prompt +
                                    "**图表类型选择**：\n"
                                    "- 时间序列 → 折线图 (line)\n"
                                    "- 排名/对比 → 柱状图 (bar)\n"
                                    "- 占比/分布 → 饼图 (pie)"
                                )

                                # 构建消息
                                multi_analysis_messages = [
                                    LLMMessage(role="system", content=multi_chart_system_prompt),
                                    LLMMessage(role="user", content=original_question),
                                    LLMMessage(role="user", content=multi_analysis_prompt)
                                ]

                                # 获取provider实例并调用
                                provider_instance = llm_service.get_provider(tenant_id, LLMProvider.DEEPSEEK)
                                if provider_instance:
                                    try:
                                        logger.debug("🔧 开始统一LLM调用：分析数据并生成多图表")

                                        # 🔧 流式输出：发送 Step 7/8 的 running 状态
                                        yield _create_processing_step(
                                            step=7,
                                            title="生成数据可视化",
                                            description="正在分析数据结构...",
                                            status="running",
                                            tenant_id=tenant_id
                                        )
                                        await asyncio.sleep(0.05)

                                        yield _create_processing_step(
                                            step=8,
                                            title="数据分析总结",
                                            description="正在分析查询结果...",
                                            status="running",
                                            tenant_id=tenant_id
                                        )
                                        await asyncio.sleep(0.05)

                                        analysis_stream = await provider_instance.chat_completion(
                                            messages=multi_analysis_messages,
                                            model=None,
                                            max_tokens=3000,  # 增加token限制以支持多图表
                                            temperature=0.7,
                                            stream=True,
                                            tools=None
                                        )

                                        # 🔧 流式输出：收集分析内容并实时发送step_update事件
                                        analysis_content = ""
                                        last_step7_update = time.time()
                                        last_step8_update = time.time()
                                        step7_phase_idx = 0
                                        step7_phases = ["正在分析数据结构...", "选择合适的图表类型...", "正在生成图表配置..."]
                                        chart_detected = False

                                        async for analysis_chunk in analysis_stream:
                                            if analysis_chunk.type == "content" and analysis_chunk.content:
                                                analysis_content += analysis_chunk.content
                                                current_time = time.time()

                                                # Step 7: 多阶段状态更新（每800ms切换阶段）
                                                if "[CHART_START]" in analysis_content and not chart_detected:
                                                    chart_detected = True
                                                    step_update_event = {
                                                        "type": "step_update",
                                                        "step": 7,
                                                        "description": "正在生成图表配置...",
                                                        "tenant_id": tenant_id
                                                    }
                                                    yield f"data: {json.dumps(step_update_event, ensure_ascii=False)}\n\n"
                                                elif not chart_detected and current_time - last_step7_update >= 0.8:
                                                    if step7_phase_idx < 2:
                                                        step7_phase_idx += 1
                                                        step_update_event = {
                                                            "type": "step_update",
                                                            "step": 7,
                                                            "description": step7_phases[step7_phase_idx],
                                                            "tenant_id": tenant_id
                                                        }
                                                        yield f"data: {json.dumps(step_update_event, ensure_ascii=False)}\n\n"
                                                    last_step7_update = current_time

                                                # Step 8: 流式打字机效果（每100ms更新预览）
                                                if current_time - last_step8_update >= 0.1:
                                                    # 提取非图表部分作为分析预览
                                                    clean_preview = re.sub(r'\[CHART_START\].*?\[CHART_END\]', '', analysis_content, flags=re.DOTALL)
                                                    clean_preview = re.sub(r'\n{3,}', '\n\n', clean_preview).strip()

                                                    if clean_preview:
                                                        step8_update_event = {
                                                            "type": "step_update",
                                                            "step": 8,
                                                            "description": f"正在分析... ({len(clean_preview)} 字符)",
                                                            "content_preview": clean_preview,
                                                            "streaming": True,
                                                            "tenant_id": tenant_id
                                                        }
                                                        yield f"data: {json.dumps(step8_update_event, ensure_ascii=False)}\n\n"
                                                    last_step8_update = current_time

                                        logger.debug(f"🔧 统一LLM调用完成，内容长度: {len(analysis_content)}")

                                        # 提取所有图表配置（支持多个）
                                        chart_pattern = r'\[CHART_START\](.*?)\[CHART_END\]'
                                        chart_matches = re.findall(chart_pattern, analysis_content, re.DOTALL)

                                        logger.debug(f"🔧 提取到 {len(chart_matches)} 个图表配置")

                                        # 为每个图表生成step=7事件
                                        for chart_idx, chart_json_str in enumerate(chart_matches, 1):
                                            try:
                                                chart_json_str = chart_json_str.strip()

                                                # 移除可能的markdown代码块
                                                if chart_json_str.startswith('```'):
                                                    lines = chart_json_str.split('\n')
                                                    if lines[0].startswith('```'):
                                                        lines = lines[1:]
                                                    if lines and lines[-1].strip() == '```':
                                                        lines = lines[:-1]
                                                    chart_json_str = '\n'.join(lines)

                                                # 移除JavaScript函数
                                                chart_json_str = re.sub(
                                                    r'"formatter":\s*function\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}',
                                                    '"formatter": "{b}: {c}"',
                                                    chart_json_str
                                                )

                                                # 尝试解析为 ECharts 配置
                                                parsed_data = json.loads(chart_json_str.strip())

                                                # 🔧 检测是否为简化格式（包含 x_data 和 y_data）
                                                if "x_data" in parsed_data and "y_data" in parsed_data:
                                                    # 转换简化格式为完整 ECharts 配置
                                                    from src.app.domains.query.agent_transformer import convert_simple_chart_to_echarts
                                                    echarts_option = convert_simple_chart_to_echarts(parsed_data)
                                                    if echarts_option:
                                                        logger.debug(f"✅ 成功转换简化格式图表{chart_idx}")
                                                    else:
                                                        logger.warning(f"⚠️ 简化格式转换失败，跳过图表{chart_idx}")
                                                        continue
                                                else:
                                                    # 已经是完整的 ECharts 配置
                                                    echarts_option = parsed_data
                                                    logger.debug(f"✅ 成功解析图表{chart_idx}: {list(echarts_option.keys())}")

                                                # 发送图表配置事件
                                                chart_event = {
                                                    "type": "chart_config",
                                                    "data": {"echarts_option": echarts_option, "chart_index": chart_idx},
                                                    "provider": "deepseek",
                                                    "finished": False,
                                                    "tenant_id": tenant_id
                                                }
                                                yield f"data: {json.dumps(chart_event, ensure_ascii=False)}\n\n"

                                                # 推断图表类型
                                                chart_type = "图表"
                                                series_list = echarts_option.get("series", [])
                                                if series_list and len(series_list) > 0:
                                                    series_type = series_list[0].get("type", "")
                                                    if series_type:
                                                        chart_type = {
                                                            "bar": "柱状图", "line": "折线图", "pie": "饼图",
                                                            "scatter": "散点图", "tree": "树图"
                                                        }.get(series_type, series_type)

                                                # 获取图表标题
                                                chart_title = echarts_option.get("title", {}).get("text", f"图表{chart_idx}")

                                                chart_content_data = {
                                                    "chart": {
                                                        "echarts_option": echarts_option,
                                                        "chart_type": chart_type,
                                                        "chart_index": chart_idx
                                                    }
                                                }

                                                yield _create_processing_step(
                                                    step=7,
                                                    title=f"生成数据可视化 ({chart_idx}/{len(chart_matches)})",
                                                    description=f"{chart_title} - {chart_type}",
                                                    status="completed",
                                                    duration=int((time.time() - ai_start_time) * 1000 * 0.3 / len(chart_matches)),
                                                    tenant_id=tenant_id,
                                                    content_type="chart",
                                                    content_data=chart_content_data
                                                )

                                                chart_already_generated = True

                                            except json.JSONDecodeError as e:
                                                logger.warning(f"解析图表{chart_idx} JSON失败: {e}")
                                                logger.warning(f"失败的JSON (前200字符): {chart_json_str[:200]}")

                                        # 生成数据分析总结（step=8）
                                        clean_analysis = re.sub(chart_pattern, '', analysis_content, flags=re.DOTALL).strip()
                                        clean_analysis = re.sub(r'\n{3,}', '\n\n', clean_analysis)

                                        if clean_analysis:
                                            yield _create_processing_step(
                                                step=8,
                                                title="数据分析总结",
                                                description="AI对查询结果的分析和解读",
                                                status="completed",
                                                duration=int((time.time() - ai_start_time) * 1000 * 0.2),
                                                tenant_id=tenant_id,
                                                content_type="text",
                                                content_data={"text": clean_analysis}
                                            )

                                    except Exception as e:
                                        logger.error(f"🔧 统一LLM调用失败: {e}")
                                else:
                                    logger.warning("🔧 无法获取LLM provider实例")

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
        # 🔧 修复：检查是否需要生成图表，以及是否已通过二次LLM调用生成图表
        chart_pattern = r'\[CHART_START\](.*?)\[CHART_END\]'
        chart_match = re.search(chart_pattern, full_content, re.DOTALL)

        # 🔧 只有当问题类型需要图表时才从full_content中提取图表（fallback路径）
        if chart_match and should_generate_chart and not chart_already_generated:
            try:
                chart_json_str = chart_match.group(1).strip()
                # 解析 JSON
                parsed_data = json.loads(chart_json_str)

                # 🔧 检测是否为简化格式（包含 x_data 和 y_data）
                if "x_data" in parsed_data and "y_data" in parsed_data:
                    # 转换简化格式为完整 ECharts 配置
                    from src.app.domains.query.agent_transformer import convert_simple_chart_to_echarts
                    echarts_option = convert_simple_chart_to_echarts(parsed_data)
                    if not echarts_option:
                        logger.warning("⚠️ 简化格式转换失败，跳过图表显示")
                        raise json.JSONDecodeError("转换失败", chart_json_str, 0)
                else:
                    echarts_option = parsed_data

                logger.debug(f"✅ 成功提取 ECharts 配置: {list(echarts_option.keys())}")

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

                # ========== Step 7: 生成数据可视化（fallback路径） ==========
                # 推断图表类型
                chart_type = "图表"
                series_list = echarts_option.get("series", [])
                if series_list and len(series_list) > 0:
                    series_type = series_list[0].get("type", "")
                    if series_type:
                        chart_type = {
                            "bar": "柱状图", "line": "折线图", "pie": "饼图",
                            "scatter": "散点图", "effectScatter": "气泡图",
                            "tree": "树图", "treemap": "矩形树图",
                            "sunburst": "旭日图", "funnel": "漏斗图",
                            "gauge": "仪表盘"
                        }.get(series_type, series_type)

                chart_content_data = {
                    "chart": {
                        "echarts_option": echarts_option,
                        "chart_type": chart_type
                    }
                }

                yield _create_processing_step(
                    step=7,
                    title="生成数据可视化",
                    description=f"创建 {chart_type} 展示分析结果",
                    status="completed",
                    duration=200,  # 估算耗时
                    tenant_id=tenant_id,
                    content_type="chart",
                    content_data=chart_content_data
                )

                # 可选：从最终内容中移除图表标记（前端可能已经显示了）
                # 这里我们保留标记，让前端自己决定是否显示

            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ 解析 ECharts JSON 失败: {e}")
                logger.warning(f"原始内容: {chart_json_str[:200]}...")
            except Exception as e:
                logger.error(f"❌ 提取 ECharts 配置时发生错误: {e}")
        elif chart_match and chart_already_generated:
            # 🔧 修复：跳过fallback路径，因为图表已通过二次LLM调用生成
            logger.debug("🔧 跳过fallback图表生成路径，图表已通过二次LLM调用生成")
        elif should_generate_chart and not chart_already_generated:
            # 🔧 新增：尝试从 markdown 代码块中提取简化格式的图表
            # AI 可能没有使用 [CHART_START]...[CHART_END] 标记
            logger.debug("🔧 未找到 [CHART_START] 标记，尝试从 markdown 代码块提取简化格式图表...")
            from src.app.domains.query.agent_transformer import extract_simple_charts_from_text
            simple_charts = extract_simple_charts_from_text(full_content)

            if simple_charts:
                logger.debug(f"✅ 从 markdown 代码块提取到 {len(simple_charts)} 个简化格式图表")

                for chart_idx, echarts_option in enumerate(simple_charts, 1):
                    try:
                        # 发送图表配置事件
                        chart_chunk = {
                            "type": "chart_config",
                            "data": {
                                "echarts_option": echarts_option,
                                "chart_index": chart_idx
                            },
                            "provider": "deepseek",
                            "finished": False,
                            "tenant_id": tenant_id
                        }
                        yield f"data: {json.dumps(chart_chunk, ensure_ascii=False)}\n\n"

                        # 推断图表类型
                        chart_type = "图表"
                        series_list = echarts_option.get("series", [])
                        if series_list and len(series_list) > 0:
                            series_type = series_list[0].get("type", "")
                            if series_type:
                                chart_type = {
                                    "bar": "柱状图", "line": "折线图", "pie": "饼图",
                                    "scatter": "散点图", "effectScatter": "气泡图",
                                    "tree": "树图", "treemap": "矩形树图",
                                    "sunburst": "旭日图", "funnel": "漏斗图",
                                    "gauge": "仪表盘"
                                }.get(series_type, series_type)

                        # 获取图表标题
                        chart_title = echarts_option.get("title", {}).get("text", f"图表{chart_idx}")

                        # 创建 processing step
                        chart_content_data = {
                            "chart": {
                                "echarts_option": echarts_option,
                                "chart_type": chart_type,
                                "chart_index": chart_idx
                            }
                        }

                        yield _create_processing_step(
                            step=7,
                            title=f"生成数据可视化 ({chart_idx}/{len(simple_charts)})",
                            description=f"{chart_title} - {chart_type}",
                            status="completed",
                            duration=200,
                            tenant_id=tenant_id,
                            content_type="chart",
                            content_data=chart_content_data
                        )

                    except Exception as e:
                        logger.error(f"❌ 处理简化格式图表{chart_idx}失败: {e}")
            else:
                logger.debug("🔧 未从 markdown 代码块中提取到简化格式图表")

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
        logger.debug(f"Chat completion request for tenant: {tenant_id}, stream={request.stream}, data_source_ids={request.data_source_ids}")
        logger.debug(f"Chat completion request debug - stream={request.stream}, data_source_ids={request.data_source_ids}")
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
        logger.debug(f"Starting _get_data_sources_context for tenant: {tenant_id}, data_source_ids: {request.data_source_ids}")
        import time as _time
        _ctx_start = _time.time()
        data_sources_context = await _get_data_sources_context(tenant_id, db, request.data_source_ids)
        schema_duration_ms = int((_time.time() - _ctx_start) * 1000)
        logger.debug(f"_get_data_sources_context took {_time.time() - _ctx_start:.2f}s")
        
        # 收集Schema信息用于前端展示
        schema_info = None
        if data_sources_context:
            logger.debug(f"Data sources context retrieved for tenant {tenant_id}, length: {len(data_sources_context)}")
            # 调试日志：打印数据源上下文的前1000个字符
            logger.debug(f"Data sources context content (first 1000 chars): {data_sources_context[:1000]}")
            
            # 解析Schema信息
            tables = []
            data_source_name = "未知"
            # 简单提取表名（从Schema文本中解析）
            import re as _re
            table_matches = _re.findall(r'表:\s*(\w+)', data_sources_context)
            if table_matches:
                tables = table_matches
            # 提取数据源名
            ds_name_match = _re.search(r'数据源:\s*(\S+)', data_sources_context)
            if ds_name_match:
                data_source_name = ds_name_match.group(1)
            
            schema_info = {
                "duration_ms": schema_duration_ms,
                "length": len(data_sources_context),
                "tables": tables,
                "data_source_name": data_source_name
            }
        else:
            logger.debug(f"No data sources found for tenant {tenant_id}")

        # 转换消息格式
        messages = _convert_chat_messages(request.messages)

        # ============================================================
        # 🔧 [修复] 获取数据源类型，用于生成数据库特定的提示词
        # ============================================================
        db_type = "postgresql"  # 默认值
        if request.data_source_ids and len(request.data_source_ids) == 1:
            # 单个数据源，获取其 db_type
            try:
                data_sources = await data_source_service.get_data_sources(
                    tenant_id=tenant_id,
                    db=db,
                    active_only=True
                )
                # 筛选出指定的数据源
                matching_sources = [ds for ds in data_sources if ds.id in request.data_source_ids]
                if matching_sources:
                    db_type = matching_sources[0].db_type
                    logger.debug(f"🔍 [LLM端点] 检测到单个数据源，db_type={db_type}")
            except Exception as e:
                logger.warning(f"⚠️ 获取数据源类型失败: {e}，使用默认 db_type=postgresql")
        elif request.data_source_ids and len(request.data_source_ids) > 1:
            # 多个数据源，检查它们是否是同一类型
            try:
                data_sources = await data_source_service.get_data_sources(
                    tenant_id=tenant_id,
                    db=db,
                    active_only=True
                )
                matching_sources = [ds for ds in data_sources if ds.id in request.data_source_ids]
                if matching_sources:
                    db_types = set(ds.db_type for ds in matching_sources)
                    if len(db_types) == 1:
                        db_type = db_types.pop()
                        logger.debug(f"🔍 [LLM端点] 多个数据源但类型一致，db_type={db_type}")
                    else:
                        logger.debug(f"🔍 [LLM端点] 多个数据源类型不同: {db_types}，使用默认 postgresql")
                        db_type = "postgresql"  # 多种类型时使用默认
            except Exception as e:
                logger.warning(f"⚠️ 获取数据源类型失败: {e}，使用默认 db_type=postgresql")
        # ============================================================

        # 检查是否已有system消息，如果没有则添加包含数据源上下文的system消息
        has_system_message = any(msg.role == "system" for msg in messages)
        if not has_system_message:
            system_prompt = _build_system_prompt_with_context(data_sources_context, db_type)
            system_message = LLMMessage(role="system", content=system_prompt)
            messages.insert(0, system_message)
            logger.debug("Added system message with data sources context")
        elif data_sources_context:
            # 如果已有system消息，替换为完整的数据分析系统提示（包含SQL生成指令）
            # 这样确保AI知道如何正确生成SQL查询
            full_system_prompt = _build_system_prompt_with_context(data_sources_context, db_type)
            for i, msg in enumerate(messages):
                if msg.role == "system":
                    messages[i] = LLMMessage(role="system", content=full_system_prompt, thinking=msg.thinking)
                    logger.debug("Replaced existing system message with full data sources context and SQL instructions")
                    break

        # 提取用户的最后一条消息作为原始问题
        original_question = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                original_question = msg.content
                break

        # ============================================================
        # SQL错误记忆注入 - 从历史错误中学习，避免重复错误
        # ============================================================
        try:
            error_memory_service = SQLErrorMemoryService(db)
            # 尝试从问题或上下文中提取表名
            table_name = None
            if data_sources_context:
                # 从第一个数据源中提取可能的表名
                for ds in data_sources_context:
                    if ds.get("schema_info") and ds["schema_info"].get("tables"):
                        # 获取第一个表名作为相关表
                        tables = list(ds["schema_info"]["tables"].keys())
                        if tables:
                            table_name = tables[0].lower()
                            break

            # 获取历史错误提示
            few_shot_prompt = await error_memory_service.generate_few_shot_prompt(
                tenant_id=tenant_id,
                user_question=original_question,
                table_name=table_name,
                limit=3  # 最多3个历史错误示例
            )

            if few_shot_prompt:
                # 将历史错误注入到system消息中
                for i, msg in enumerate(messages):
                    if msg.role == "system":
                        # 在原有提示后追加历史错误示例
                        enhanced_prompt = msg.content + "\n\n" + few_shot_prompt
                        messages[i] = LLMMessage(role="system", content=enhanced_prompt, thinking=msg.thinking)
                        logger.debug(f"✅ [SQL错误记忆] 已注入{few_shot_prompt.count('错误')}个历史错误示例到Prompt")
                        break
        except Exception as error_inject_error:
            logger.warning(f"⚠️ [SQL错误记忆] 注入历史错误失败: {error_inject_error}")
        # ============================================================

        # 调用LLM服务
        if request.stream:
            # 流式响应
            # 注意：chat_completion 是异步函数，需要 await 来获取 AsyncGenerator
            logger.debug(f"[STREAM] Starting stream request for tenant {tenant_id}")
            logger.debug(f"[STREAM] Starting stream request for tenant {tenant_id}")
            
            # 方案 B: 不使用 Function Calling，改用 SQL 代码块检测
            # DeepSeek 不支持标准的 OpenAI Function Calling 协议
            # 所以我们让 AI 直接在回答中输出 ```sql ... ``` 代码块，然后自动检测并执行
            logger.debug("[STREAM] 使用 SQL 代码块检测模式（方案B）")
            
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
            
            logger.debug("[STREAM] Stream generator created, starting response")

            # ========== 🔧 修复：先分类问题，再决定使用哪个生成器 ==========
            # 导入问题分类器
            from src.app.domains.query.processing_steps import classify_question, QuestionType

            # 判断是否为Agent模式（有数据源）
            is_agent_mode = request.data_source_ids and len(request.data_source_ids) > 0

            # 🔧 关键修复：先分类问题，再决定使用哪个生成器
            # 即使有数据源，如果是简单对话也应使用动态步骤流程
            question_type = classify_question(original_question, has_data_source=is_agent_mode)
            logger.debug(f"[STREAM] Question classified as: {question_type.value}, is_agent_mode={is_agent_mode}")

            # 判断是否需要使用SQL流程（只有真正需要查询数据时才使用）
            # 🔧 修复：SCHEMA_QUERY不需要SQL流程，Agent直接回答schema信息即可
            needs_sql_flow = question_type in [
                QuestionType.DATA_QUERY,
                QuestionType.VISUALIZATION
                # 🔧 SCHEMA_QUERY已移除 - schema查询不需要SQL，直接让Agent回答
            ] and is_agent_mode

            if needs_sql_flow:
                # Agent SQL查询模式：6-8步流程（仅在真正需要数据查询时使用）
                logger.debug(f"[STREAM] Using Agent SQL mode for data query, question_type={question_type.value}")
                return StreamingResponse(
                    _stream_response_generator(
                        response_generator,
                        tenant_id,
                        db,
                        original_question,
                        request.data_source_ids,
                        initial_messages=messages,  # 传递初始消息历史
                        schema_info=schema_info,  # 传递Schema获取信息
                        question_type=question_type  # 🔧 传递问题类型
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
                # 🔧 修复：普通对话模式（包括简单问候）使用动态步骤流程
                # 即使有数据源，如果是简单对话也走这里
                logger.debug(f"[STREAM] Using General Chat mode (dynamic steps: {question_type.value})")
                return StreamingResponse(
                    _stream_general_chat_generator(
                        response_generator,
                        tenant_id,
                        original_question,
                        has_data_source=is_agent_mode  # 传递实际的数据源状态
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
            logger.debug(f"[PERF] llm_service.chat_completion took {time.time() - llm_start:.2f}s")

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
        from src.app.domains.llm.service import LLMMessage

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
        from src.app.domains.llm.service import LLMMessage

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
                max_tokens=complexity.get("recommend_max_tokens", 8192)
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
        from src.app.domains.llm.service import LLMMessage
        from src.app.domains.llm.multimodal import multimodal_processor

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
        from src.app.domains.tenants.config_manager import tenant_config_manager, ProviderType

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
        from src.app.domains.llm.service import LLMMessage

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
            max_tokens=complexity_analysis.get("recommend_max_tokens", 8192)
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
