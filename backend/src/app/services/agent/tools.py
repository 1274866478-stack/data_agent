"""
Agent Tools - 安全工具包装和自定义工具定义
包括 SQL 安全执行工具和文件数据源工具
"""
import os
import io
import tempfile
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool, BaseTool
import pandas as pd

from src.app.services.minio_client import minio_service

logger = logging.getLogger(__name__)

# MCP Client wrapper (set by agent_service)
_mcp_client_wrapper = None


def set_mcp_client(wrapper):
    """设置 MCP 客户端包装器"""
    global _mcp_client_wrapper
    _mcp_client_wrapper = wrapper


def sanitize_sql(sql: str) -> str:
    """清理 SQL 语句，移除 HTML、Markdown 等污染"""
    if not sql:
        return ""
    # 移除代码块标记
    sql = sql.replace("```sql", "").replace("```", "").strip()
    # 移除 HTML 标签
    import re
    sql = re.sub(r'<[^>]+>', '', sql)
    return sql.strip()


def validate_sql_safety(sql: str) -> bool:
    """验证 SQL 安全性（只允许 SELECT 查询）"""
    sql_upper = sql.upper().strip()
    # 禁止的危险关键字
    dangerous_keywords = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE',
        'EXEC', 'EXECUTE', 'CALL', 'GRANT', 'REVOKE'
    ]
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False
    # 必须包含 SELECT 或 WITH
    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
        return False
    return True


# ============================================================
# SQL Tools (使用 MCP Postgres 服务器)
# ============================================================

class ExecuteSQLInput(BaseModel):
    """SQL 执行工具输入"""
    sql: str = Field(description="SQL 查询语句（只支持 SELECT）")
    query: Optional[str] = Field(None, description="SQL 查询语句（别名）")


def execute_sql_safe_func(input_data: Dict[str, Any]) -> str:
    """安全执行 SQL 查询"""
    global _mcp_client_wrapper
    
    sql = input_data.get("sql") or input_data.get("query", "")
    if not sql:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    # 清理和验证 SQL
    sql = sanitize_sql(sql)
    if not validate_sql_safety(sql):
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    if not _mcp_client_wrapper:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    try:
        result = _mcp_client_wrapper.execute_query(sql)
        # 🔴 第一道防线：检查空数据
        if result is None or result == "" or result == "[]" or result == "{}":
            logger.warning("⚠️ [第一道防线] SQL查询返回空数据")
            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
        # 检查是否是错误信息
        if isinstance(result, str) and (result.startswith("错误") or result.startswith("Error") or "失败" in result):
            logger.warning(f"⚠️ [第一道防线] SQL查询返回错误: {result}")
            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
        return result
    except Exception as e:
        logger.error(f"⚠️ [第一道防线] SQL执行异常: {e}", exc_info=True)
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'


execute_sql_safe = StructuredTool.from_function(
    func=execute_sql_safe_func,
    name="execute_sql_safe",
    description="安全执行 SQL SELECT 查询（只支持 SELECT，禁止修改操作）",
    args_schema=ExecuteSQLInput,
)


class GetTableSchemaInput(BaseModel):
    """获取表结构工具输入"""
    table_name: str = Field(description="表名")


def get_table_schema_func(input_data: Dict[str, Any]) -> str:
    """获取表结构信息"""
    global _mcp_client_wrapper
    
    table_name = input_data.get("table_name", "")
    if not table_name:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    if not _mcp_client_wrapper:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    try:
        result = _mcp_client_wrapper.get_schema(table_name)
        # 🔴 第一道防线：检查空数据
        if result is None or result == "" or result == "[]" or result == "{}":
            logger.warning("⚠️ [第一道防线] 获取表结构返回空数据")
            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
        if isinstance(result, str) and (result.startswith("错误") or result.startswith("Error") or "失败" in result):
            logger.warning(f"⚠️ [第一道防线] 获取表结构返回错误: {result}")
            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
        return result
    except Exception as e:
        logger.error(f"⚠️ [第一道防线] 获取表结构异常: {e}", exc_info=True)
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'


get_table_schema = StructuredTool.from_function(
    func=get_table_schema_func,
    name="get_table_schema",
    description="获取数据库表的结构信息（列名、数据类型）",
    args_schema=GetTableSchemaInput,
)


class ListTablesInput(BaseModel):
    """列出表工具输入（无参数）"""
    pass


def list_available_tables_func(input_data: Dict[str, Any]) -> str:
    """列出所有可用的表"""
    global _mcp_client_wrapper
    
    if not _mcp_client_wrapper:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    try:
        result = _mcp_client_wrapper.list_tables()
        # 🔴 第一道防线：检查空数据
        if result is None or result == "" or result == "[]" or result == "{}":
            logger.warning("⚠️ [第一道防线] 列出表返回空数据")
            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
        if isinstance(result, str) and (result.startswith("错误") or result.startswith("Error") or "失败" in result):
            logger.warning(f"⚠️ [第一道防线] 列出表返回错误: {result}")
            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
        return result
    except Exception as e:
        logger.error(f"⚠️ [第一道防线] 列出表异常: {e}", exc_info=True)
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'


list_available_tables = StructuredTool.from_function(
    func=list_available_tables_func,
    name="list_available_tables",
    description="列出数据库中所有可用的表",
    args_schema=ListTablesInput,
)


# ============================================================
# File Data Source Tools (自定义工具，处理 MinIO 文件路径)
# ============================================================

class AnalyzeDataFrameInput(BaseModel):
    """分析 DataFrame 工具输入"""
    query: str = Field(description="Pandas 查询代码（例如: df.head(), df.describe(), df.groupby(...) 等）")
    file_path: str = Field(description="文件路径（可以是 MinIO 路径 file://data-sources/... 或容器内绝对路径）")
    sheet_name: Optional[str] = Field(default=None, description="Excel工作表名称（可选，仅用于Excel文件。如果不指定，默认读取第一个工作表）")


def analyze_dataframe_func(input_data: Dict[str, Any]) -> str:
    """
    使用 Pandas 分析数据文件（Excel/CSV）
    
    支持从 MinIO 下载文件到容器内临时目录，然后使用容器内绝对路径读取
    """
    query = input_data.get("query", "")
    file_path = input_data.get("file_path", "")
    sheet_name = input_data.get("sheet_name", None)
    
    if not query:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    if not file_path:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    # --- Debug Info ---
    current_dir = os.getcwd()
    logger.info(f"🔍 [Debug] Current Dir: {current_dir}")
    logger.info(f"🔍 [Debug] Input file_path: {file_path}")
    
    # --- 路径修正逻辑 ---
    # 容器内的标准数据目录（挂载了本地 scripts 目录）
    CONTAINER_DATA_DIR = "/app/data"
    CONTAINER_UPLOADS_DIR = "/app/uploads"
    
    # 解析文件路径（可能是 MinIO 路径、Windows 路径或容器内路径）
    container_file_path = None
    
    # 🔧 修复：支持多种路径格式
    # 1. 本地存储路径（local:///app/uploads/...）
    if file_path.startswith("local://"):
        # 移除 local:// 前缀，直接使用容器内路径
        container_file_path = file_path[8:]  # 移除 local:// 前缀
        logger.info(f"🔍 [Debug] 检测到本地存储路径: {container_file_path}")
        # 验证路径是否存在
        if not os.path.exists(container_file_path):
            logger.warning(f"⚠️ [第一道防线] 本地存储路径不存在: {container_file_path}")
            # 尝试在 /app/data 目录查找同名文件
            filename = os.path.basename(container_file_path)
            fallback_path = os.path.join(CONTAINER_DATA_DIR, filename)
            if os.path.exists(fallback_path):
                container_file_path = fallback_path
                logger.info(f"✅ 在 /app/data 目录找到文件: {container_file_path}")
            else:
                logger.error(f"❌ [第一道防线] 文件不存在: {container_file_path} 和 {fallback_path}")
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    # 2. 容器内绝对路径（如 /app/uploads/data-sources/...）
    elif file_path.startswith("/"):
        # 已经是容器内绝对路径
        container_file_path = file_path
        logger.info(f"🔍 [Debug] 检测到容器内绝对路径: {container_file_path}")
        # 🔥 关键修复：验证文件是否存在
        if not os.path.exists(container_file_path):
            logger.error(f"❌ [第一道防线] 容器内绝对路径不存在: {container_file_path}")
            # 尝试从MinIO下载（如果路径看起来像MinIO路径）
            if "data-sources" in container_file_path:
                # 提取相对路径
                relative_path = container_file_path.replace("/app/uploads/", "").replace("/app/data/", "")
                if relative_path.startswith("data-sources/"):
                    logger.warning(f"⚠️ 尝试从MinIO下载: {relative_path}")
                    file_data = minio_service.download_file(
                        bucket_name="data-sources",
                        object_name=relative_path
                    )
                    if file_data:
                        # 保存到指定路径
                        os.makedirs(os.path.dirname(container_file_path), exist_ok=True)
                        with open(container_file_path, "wb") as f:
                            f.write(file_data)
                        logger.info(f"✅ 从MinIO下载并保存到: {container_file_path}")
                    else:
                        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
            else:
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    # 3. MinIO 路径（file://data-sources/...）
    elif file_path.startswith("file://"):
        storage_path = file_path[7:]  # 移除 file:// 前缀
        
        # 检查是否是 MinIO 路径（data-sources/...）
        if storage_path.startswith("data-sources/"):
            logger.info(f"🔍 [Debug] 检测到 MinIO 路径，准备下载: {storage_path}")
            
            # 从 MinIO 下载文件
            file_data = minio_service.download_file(
                bucket_name="data-sources",
                object_name=storage_path
            )
            
            if not file_data:
                # 🔧 修复：MinIO下载失败时，尝试从本地文件系统读取
                logger.warning(f"⚠️ MinIO下载失败，尝试从本地文件系统读取: {storage_path}")
                
                # 尝试从本地上传目录读取
                local_paths = [
                    os.path.join(CONTAINER_UPLOADS_DIR, storage_path),  # /app/uploads/data-sources/...
                    os.path.join(CONTAINER_DATA_DIR, os.path.basename(storage_path)),  # /app/data/filename
                ]
                
                found_local = False
                for local_path in local_paths:
                    if os.path.exists(local_path):
                        container_file_path = local_path
                        found_local = True
                        logger.info(f"✅ 从本地文件系统找到文件: {container_file_path}")
                        break
                
                if not found_local:
                    # 列出当前目录文件，帮助调试
                    files_in_dir = os.listdir(current_dir) if os.path.exists(current_dir) else []
                    files_in_uploads = os.listdir(CONTAINER_UPLOADS_DIR) if os.path.exists(CONTAINER_UPLOADS_DIR) else []
                    logger.warning(f"⚠️ [第一道防线] 无法从 MinIO 或本地文件系统获取文件: {storage_path}")
                    logger.warning(f"   Files in {current_dir}: {files_in_dir}")
                    logger.warning(f"   Files in {CONTAINER_UPLOADS_DIR}: {files_in_uploads}")
                    # 🔴 第一道防线：返回特定错误字符串
                    return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
            else:
                # MinIO下载成功，保存到容器内临时目录
                temp_dir = os.getenv("TEMP", "/tmp")
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir, exist_ok=True)
                
                # 从路径提取文件名
                filename = os.path.basename(storage_path)
                container_file_path = os.path.join(temp_dir, filename)
                
                # 写入临时文件
                try:
                    with open(container_file_path, "wb") as f:
                        f.write(file_data)
                    logger.info(f"✅ 文件已从MinIO下载到容器内路径: {container_file_path}")
                except Exception as e:
                    logger.error(f"⚠️ [第一道防线] 写入临时文件失败: {e}", exc_info=True)
                    # 🔴 第一道防线：返回特定错误字符串
                    return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        else:
            # 不是 MinIO 路径，直接使用
            container_file_path = storage_path
    else:
        # 不是 file:// 前缀，可能是 Windows 路径或其他路径
        # 检查是否是 Windows 路径（C:\... 或包含反斜杠）
        if "\\" in file_path or (len(file_path) > 1 and file_path[1] == ":"):
            # Windows 路径，提取文件名并转换为容器内路径
            filename = os.path.basename(file_path)
            container_file_path = os.path.join(CONTAINER_DATA_DIR, filename)
            logger.info(f"🔄 Path Correction: Windows path '{file_path}' -> Container path '{container_file_path}'")
        else:
            # 其他路径，直接使用
            container_file_path = file_path
    
    # 检查文件是否存在
    if not os.path.exists(container_file_path):
        # 尝试在容器数据目录查找
        filename = os.path.basename(container_file_path)
        potential_paths = [
            os.path.join(CONTAINER_DATA_DIR, filename),  # /app/data/filename
            os.path.join(current_dir, filename),  # 当前目录
            container_file_path  # 原始路径
        ]
        
        # 再次列出当前目录和容器数据目录的文件，帮用户找原因
        files_in_current_dir = os.listdir(current_dir) if os.path.exists(current_dir) else []
        files_in_data_dir = os.listdir(CONTAINER_DATA_DIR) if os.path.exists(CONTAINER_DATA_DIR) else []
        logger.warning(f"⚠️ File not found at {container_file_path}")
        logger.warning(f"   Files in {current_dir}: {files_in_current_dir}")
        logger.warning(f"   Files in {CONTAINER_DATA_DIR}: {files_in_data_dir}")
        
        # 尝试所有可能的路径
        for potential_path in potential_paths:
            if os.path.exists(potential_path):
                logger.info(f"✅ Found file at: {potential_path}")
                container_file_path = potential_path
                break
        else:
            # 所有路径都不存在
            logger.warning(f"⚠️ [第一道防线] 文件不存在: {filename}")
            # 🔴 第一道防线：返回特定错误字符串
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    
    # 读取文件
    try:
        # 根据文件扩展名选择读取方式
        if container_file_path.endswith('.xlsx') or container_file_path.endswith('.xls'):
            # 🔧 增强：先验证工作表是否存在（如果指定了工作表名称）
            if sheet_name:
                try:
                    excel_file = pd.ExcelFile(container_file_path, engine='openpyxl')
                    available_sheets = excel_file.sheet_names
                    logger.info(f"📋 Excel文件可用工作表: {available_sheets}")
                    
                    if sheet_name not in available_sheets:
                        logger.error(f"❌ [第一道防线] 工作表 '{sheet_name}' 不存在！可用工作表: {available_sheets}")
                        return f'SYSTEM ERROR: Data Access Failed. Sheet "{sheet_name}" not found. Available sheets: {", ".join(available_sheets)}. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法找到指定的工作表，请检查工作表名称"。'
                    
                    logger.info(f"📋 读取Excel工作表: {sheet_name}")
                except Exception as e:
                    logger.error(f"❌ [第一道防线] 无法读取Excel文件结构: {e}", exc_info=True)
                    return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
            
            # 显式指定 engine='openpyxl' 以确保正确读取
            # 如果指定了工作表名称，使用它；否则读取第一个工作表
            read_params = {"engine": "openpyxl"}
            if sheet_name:
                read_params["sheet_name"] = sheet_name
            
            df = pd.read_excel(container_file_path, **read_params)
            logger.info(f"✅ 成功读取 Excel 文件，行数: {len(df)}, 列数: {len(df.columns)}")
            logger.info(f"📊 Excel文件列名: {list(df.columns)}")
            
            # 🔧 增强：验证查询中使用的列名是否存在
            # 检查查询代码中是否引用了不存在的列
            import re
            # 简单的列名提取（匹配 df['列名'] 或 df.列名 或 df[列名]）
            column_refs = re.findall(r"df\[['\"]([^'\"]+)['\"]\]|df\.(\w+)|df\[(\w+)\]", query)
            referenced_columns = [col for match in column_refs for col in match if col]
            
            if referenced_columns:
                missing_columns = [col for col in referenced_columns if col not in df.columns]
                if missing_columns:
                    logger.error(f"❌ [第一道防线] 查询中引用的列不存在: {missing_columns}，实际列名: {list(df.columns)}")
                    return f'SYSTEM ERROR: Data Access Failed. Columns {missing_columns} not found. Available columns: {", ".join(df.columns)}. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法找到指定的列，请检查列名"。'
        elif container_file_path.endswith('.csv'):
            df = pd.read_csv(container_file_path)
            logger.info(f"✅ 成功读取 CSV 文件，行数: {len(df)}, 列数: {len(df.columns)}")
        else:
            logger.warning(f"⚠️ [第一道防线] 不支持的文件类型: {container_file_path}")
            # 🔴 第一道防线：返回特定错误字符串
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        
        # 执行 Pandas 查询
        # 注意: query 参数应该包含有效的 Pandas 代码，例如: df.head(), df.describe() 等
        # 为了安全，我们限制只能使用 df 变量
        try:
            # 使用 eval 执行查询（限制在安全环境中）
            # 注意: 这里使用 eval 是为了支持动态 Pandas 查询，但应该在生产环境中考虑更安全的方式
            result = eval(query, {"df": df, "pd": pd, "__builtins__": {}})
            
            # 格式化结果
            if isinstance(result, pd.DataFrame):
                # 使用 tabulate 格式化输出（如果可用）
                try:
                    from tabulate import tabulate
                    result_str = tabulate(result, headers='keys', tablefmt='grid', showindex=False)
                except ImportError:
                    # 如果没有 tabulate，使用 to_string
                    result_str = result.to_string()
            elif isinstance(result, pd.Series):
                result_str = result.to_string()
            else:
                result_str = str(result)
            
            logger.info(f"✅ Pandas 查询执行成功，结果长度: {len(result_str)}")
            # 🔴 第一道防线：检查空数据
            if not result_str or result_str.strip() == "" or result_str == "Empty DataFrame\nColumns: []\nIndex: []":
                logger.warning("⚠️ [第一道防线] Pandas查询返回空数据")
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
            return result_str
            
        except Exception as e:
            logger.error(f"⚠️ [第一道防线] Pandas 查询执行失败: {e}", exc_info=True)
            # 🔴 第一道防线：返回特定错误字符串
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
            
    except ImportError as e:
        logger.error(f"❌ 缺少依赖: {e}", exc_info=True)
        logger.error(f"⚠️ [第一道防线] 缺少依赖库: {e}", exc_info=True)
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    except Exception as e:
        logger.error(f"❌ 读取文件失败: {e}", exc_info=True)
        logger.error(f"⚠️ [第一道防线] 读取文件失败: {e}", exc_info=True)
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'


analyze_dataframe = StructuredTool.from_function(
    func=analyze_dataframe_func,
    name="analyze_dataframe",
    description="使用 Pandas 分析数据文件（Excel/CSV）。支持从 MinIO 下载文件到容器内临时目录。对于Excel文件，可以使用 sheet_name 参数指定工作表名称（如 '用户表'、'orders' 等）。查询代码应使用 'df' 变量，例如: df.head(), df.describe(), df.groupby('column').sum() 等",
    args_schema=AnalyzeDataFrameInput,
)

