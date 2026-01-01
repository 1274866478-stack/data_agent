"""
# Agent Tools - 安全工具包装与自定义工具

## [HEADER]
**文件名**: tools.py
**职责**: 定义LangGraph Agent的工具集，包括SQL安全执行、文件分析、数据查询等
**作者**: Data Agent Team
**版本**: 1.5.0
**变更记录**:
- v1.5.0 (2026-01-01): 增强路径解析和动态文件发现
- v1.0.0 (2025-12-01): 初始版本，基础工具定义

## [INPUT]
- SQL查询: str - SELECT查询语句
- 文件路径: str - Excel/CSV文件路径
- Pandas查询: str - Python/Pandas分析代码
- 表名: str - 数据库表名

## [OUTPUT]
- 查询结果: str - JSON格式的查询返回数据
- 错误消息: str - 标准化的错误信息

## [LINK]
**上游依赖**:
- [minio_client.py](../minio_client.py) - MinIO对象存储服务
- [path_extractor.py](path_extractor.py) - 路径解析工具

**下游依赖**:
- [agent_service.py](agent_service.py) - Agent工具注册

**调用方**:
- LangGraph Agent - MCP工具调用
- LangChain ToolExecutor - 工具执行器

## [POS]
**路径**: backend/src/app/services/agent/tools.py
**模块层级**: Level 3 (Services → Agent → Tools)
**依赖深度**: 2 层
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
from src.app.services.agent.path_extractor import resolve_file_path_with_fallback, get_latest_excel_file

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


def execute_sql_safe_func(sql: str = None, query: str = None, input_data: Dict[str, Any] = None) -> str:
    """安全执行 SQL 查询"""
    global _mcp_client_wrapper
    
    # 处理参数：StructuredTool.from_function可能直接传递关键字参数，也可能传递input_data字典
    if sql:
        pass  # 使用sql参数
    elif query:
        sql = query
    elif input_data:
        # 处理字典输入
        if not isinstance(input_data, dict):
            # 如果是BaseModel对象，转换为dict
            if hasattr(input_data, 'dict'):
                input_data = input_data.dict()
            elif hasattr(input_data, '__dict__'):
                input_data = input_data.__dict__
            else:
                input_data = {}
        sql = input_data.get("sql") or input_data.get("query", "")
    else:
        sql = ""
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
        
        # 🔥 上下文管理：限制返回数据长度
        MAX_RESULT_LENGTH = 5000  # 与agent_service.py中的MAX_TOOL_RESULT_LENGTH保持一致
        if isinstance(result, str) and len(result) > MAX_RESULT_LENGTH:
            # 尝试解析JSON，如果是JSON数组，只保留前N条记录
            try:
                import json
                data = json.loads(result)
                if isinstance(data, list) and len(data) > 0:
                    # 保留前10条记录
                    truncated_data = data[:10]
                    truncated_result = json.dumps(truncated_data, ensure_ascii=False, indent=2)
                    truncated_result += f"\n\n[数据已截断：共 {len(data)} 条记录，仅显示前 10 条]"
                    logger.warning(f"⚠️ [上下文管理] SQL查询返回数据过长 ({len(result)} 字符)，已截断至前10条记录")
                    return truncated_result
            except (json.JSONDecodeError, Exception):
                # 如果不是JSON或解析失败，直接截断字符串
                truncated_result = result[:MAX_RESULT_LENGTH] + f"\n\n[数据已截断，原始长度: {len(result)} 字符]"
                logger.warning(f"⚠️ [上下文管理] SQL查询返回数据过长 ({len(result)} 字符)，已截断至 {MAX_RESULT_LENGTH} 字符")
                return truncated_result
        
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


def get_table_schema_func(table_name: str = None, input_data: Dict[str, Any] = None) -> str:
    """获取表结构信息"""
    global _mcp_client_wrapper
    
    # 处理参数：StructuredTool.from_function可能直接传递关键字参数，也可能传递input_data字典
    if not table_name:
        if input_data:
            # 处理字典输入
            if not isinstance(input_data, dict):
                # 如果是BaseModel对象，转换为dict
                if hasattr(input_data, 'dict'):
                    input_data = input_data.dict()
                elif hasattr(input_data, '__dict__'):
                    input_data = input_data.__dict__
                else:
                    input_data = {}
            table_name = input_data.get("table_name", "")
        else:
            table_name = ""
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


def list_available_tables_func(input_data: Dict[str, Any] = None) -> str:
    """列出所有可用的表"""
    global _mcp_client_wrapper
    
    # 处理空输入或不同类型的输入（LangChain可能传递BaseModel对象）
    if input_data is None:
        input_data = {}
    elif not isinstance(input_data, dict):
        # 如果是BaseModel对象，转换为dict
        if hasattr(input_data, 'dict'):
            input_data = input_data.dict()
        elif hasattr(input_data, '__dict__'):
            input_data = input_data.__dict__
        else:
            input_data = {}
    
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
        
        # 🔥 修复：排除系统表，只返回用户数据表
        # 系统表列表（需要排除的表）
        system_tables = {
            'api_keys', 'audit_logs', 'data_source_connections', 
            'sessions', 'users', 'tenants', 'queries', 'query_results',
            'migrations', 'schema_migrations', 'pg_', 'information_schema',
            'pg_catalog', 'pg_toast', 'pg_temp'
        }
        
        # 如果结果是字符串，尝试解析并过滤
        if isinstance(result, str):
            # 尝试解析 JSON 格式的表列表
            import json
            try:
                tables_data = json.loads(result)
                if isinstance(tables_data, list):
                    # 过滤掉系统表
                    filtered_tables = [
                        table for table in tables_data 
                        if not any(sys_table in str(table).lower() for sys_table in system_tables)
                    ]
                    if filtered_tables:
                        result = json.dumps(filtered_tables, ensure_ascii=False)
                    else:
                        # 如果没有用户表，返回空列表
                        result = "[]"
                elif isinstance(tables_data, dict):
                    # 如果是字典格式，尝试过滤
                    filtered_data = {
                        k: v for k, v in tables_data.items()
                        if not any(sys_table in str(k).lower() for sys_table in system_tables)
                    }
                    if filtered_data:
                        result = json.dumps(filtered_data, ensure_ascii=False)
                    else:
                        result = "{}"
            except (json.JSONDecodeError, TypeError):
                # 如果不是 JSON 格式，尝试简单的字符串过滤
                lines = result.split('\n')
                filtered_lines = [
                    line for line in lines
                    if not any(sys_table in line.lower() for sys_table in system_tables)
                ]
                result = '\n'.join(filtered_lines) if filtered_lines else "未找到用户数据表"
        elif isinstance(result, (list, dict)):
            # 如果结果是列表或字典，直接过滤
            import json
            if isinstance(result, list):
                filtered_result = [
                    item for item in result
                    if not any(sys_table in str(item).lower() for sys_table in system_tables)
                ]
                result = json.dumps(filtered_result, ensure_ascii=False) if filtered_result else "[]"
            else:
                filtered_result = {
                    k: v for k, v in result.items()
                    if not any(sys_table in str(k).lower() for sys_table in system_tables)
                }
                result = json.dumps(filtered_result, ensure_ascii=False) if filtered_result else "{}"
        
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

class InspectFileInput(BaseModel):
    """检查文件工具输入"""
    file_path: str = Field(description="🚨 文件路径（必填！必须使用用户问题或系统提示中提供的实际文件路径，如 file://data-sources/... 或 /app/data/... 或 local:///app/uploads/...。绝对不要使用示例路径或猜测路径！）")


def inspect_file_func(input_data: Dict[str, Any] = None, file_path: str = None) -> str:
    """
    检查文件结构（Excel/CSV）
    
    对于Excel文件，返回所有工作表名称和基本信息
    对于CSV文件，返回列信息和前几行数据
    """
    # 处理参数：StructuredTool.from_function可能直接传递关键字参数，也可能传递input_data字典
    if file_path:
        pass  # 使用file_path参数
    elif input_data:
        # 处理字典输入
        if not isinstance(input_data, dict):
            # 如果是BaseModel对象，转换为dict
            if hasattr(input_data, 'dict'):
                input_data = input_data.dict()
            elif hasattr(input_data, '__dict__'):
                input_data = input_data.__dict__
            else:
                input_data = {}
        file_path = input_data.get("file_path", "")
    else:
        file_path = ""
    
    if not file_path:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    
    # --- Debug Info ---
    current_dir = os.getcwd()
    logger.info(f"🔍 [Debug] Current Dir: {current_dir}")
    logger.info(f"🔍 [Debug] Input file_path: {file_path}")
    
    # 🔥 修复：强制使用动态文件发现（仅对Excel文件）
    # 对于Excel文件，直接使用动态文件发现，忽略用户提供的路径（因为文件可能被重命名为UUID）
    is_excel_file = file_path and (file_path.endswith('.xlsx') or file_path.endswith('.xls') or '.xlsx' in file_path.lower() or '.xls' in file_path.lower())
    
    if is_excel_file:
        # 🔥 强制使用动态文件发现
        try:
            logger.info(f"🔥 [强制动态文件发现] 检测到Excel文件，使用动态文件发现: {file_path}")
            container_file_path = get_latest_excel_file("/app/uploads")
            logger.info(f"✅ [强制动态文件发现] 成功发现Excel文件: {container_file_path}")
        except FileNotFoundError as e:
            logger.error(f"❌ [第一道防线] 动态文件发现失败: {e}")
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        except Exception as e:
            logger.error(f"❌ [第一道防线] 动态文件发现异常: {e}", exc_info=True)
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    else:
        # 对于非Excel文件（如CSV），使用原有的路径解析逻辑
        # 🔧 修复：使用新的路径提取和解析函数
        container_file_path = resolve_file_path_with_fallback(file_path)
        
        # 如果路径解析失败，尝试从MinIO下载（仅当路径是file://格式时）
        if not container_file_path and file_path.startswith("file://"):
            storage_path = file_path[7:]  # 移除 file:// 前缀
            if storage_path.startswith("data-sources/"):
                logger.info(f"🔍 [Debug] 尝试从MinIO下载: {storage_path}")
                file_data = minio_service.download_file(
                    bucket_name="data-sources",
                    object_name=storage_path
                )
                
                if file_data:
                    # MinIO下载成功，保存到容器内临时目录
                    temp_dir = os.getenv("TEMP", "/tmp")
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir, exist_ok=True)
                    
                    filename = os.path.basename(storage_path)
                    container_file_path = os.path.join(temp_dir, filename)
                    
                    try:
                        with open(container_file_path, "wb") as f:
                            f.write(file_data)
                        logger.info(f"✅ 文件已从MinIO下载到容器内路径: {container_file_path}")
                    except Exception as e:
                        logger.error(f"⚠️ [第一道防线] 写入临时文件失败: {e}", exc_info=True)
                        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        
        # 最终检查：如果仍然没有找到文件
        if not container_file_path or not os.path.exists(container_file_path):
            logger.error(f"❌ [第一道防线] 无法找到或访问文件: {file_path}")
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    
    # 读取文件信息
    try:
        if container_file_path.endswith('.xlsx') or container_file_path.endswith('.xls'):
            # Excel文件：返回工作表列表和基本信息
            try:
                excel_file = pd.ExcelFile(container_file_path, engine='openpyxl')
                sheet_names = excel_file.sheet_names
                logger.info(f"📋 Excel文件可用工作表: {sheet_names}")
                
                # 读取第一个工作表获取列信息
                first_sheet_df = pd.read_excel(container_file_path, sheet_name=sheet_names[0], engine='openpyxl', nrows=0)
                columns = list(first_sheet_df.columns)
                
                result = f"文件类型: Excel\n"
                result += f"工作表列表: {', '.join(sheet_names)}\n"
                result += f"第一个工作表 '{sheet_names[0]}' 的列: {', '.join(columns)}\n"
                result += f"总工作表数: {len(sheet_names)}"
                
                logger.info(f"✅ 成功读取Excel文件信息: {len(sheet_names)}个工作表")
                return result
            except Exception as e:
                logger.error(f"❌ [第一道防线] 无法读取Excel文件结构: {e}", exc_info=True)
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        elif container_file_path.endswith('.csv'):
            # CSV文件：返回列信息和前几行
            try:
                df = pd.read_csv(container_file_path, nrows=5)  # 只读取前5行用于预览
                columns = list(df.columns)
                
                result = f"文件类型: CSV\n"
                result += f"列名: {', '.join(columns)}\n"
                result += f"总列数: {len(columns)}\n"
                result += f"预览数据（前5行）:\n{df.to_string()}"
                
                logger.info(f"✅ 成功读取CSV文件信息: {len(columns)}列")
                return result
            except Exception as e:
                logger.error(f"❌ [第一道防线] 无法读取CSV文件: {e}", exc_info=True)
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        else:
            logger.warning(f"⚠️ [第一道防线] 不支持的文件类型: {container_file_path}")
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    except Exception as e:
        logger.error(f"❌ 读取文件失败: {e}", exc_info=True)
        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'


inspect_file = StructuredTool.from_function(
    func=inspect_file_func,
    name="inspect_file",
    description="检查文件结构（Excel/CSV）。对于Excel文件，返回所有工作表名称和列信息；对于CSV文件，返回列信息和预览数据。🚨 必须使用用户问题或系统提示中提供的实际文件路径，绝对不要使用示例路径或猜测路径！",
    args_schema=InspectFileInput,
)


class AnalyzeDataFrameInput(BaseModel):
    """分析 DataFrame 工具输入"""
    query: str = Field(description="Pandas 查询代码（例如: df.head(), df.describe(), df.groupby(...) 等）")
    file_path: str = Field(description="🚨 文件路径（必填！必须使用用户问题或系统提示中提供的实际文件路径，如 file://data-sources/... 或 /app/data/... 或 local:///app/uploads/...。绝对不要使用示例路径或猜测路径！）")
    sheet_name: Optional[str] = Field(default=None, description="Excel工作表名称（可选，仅用于Excel文件。⚠️ 必须使用 inspect_file 工具返回的实际工作表名称，不能猜测！如果不指定，默认读取第一个工作表）")


def analyze_dataframe_func(input_data: Dict[str, Any] = None, query: str = None, file_path: str = None, sheet_name: Optional[str] = None) -> str:
    """
    使用 Pandas 分析数据文件（Excel/CSV）
    
    支持从 MinIO 下载文件到容器内临时目录，然后使用容器内绝对路径读取
    """
    # 处理参数：StructuredTool.from_function可能直接传递关键字参数，也可能传递input_data字典
    if query is not None:
        pass  # 使用query参数
    elif file_path is not None:
        pass  # 使用file_path参数
    elif input_data is not None:
        # 处理字典输入
        if not isinstance(input_data, dict):
            # 如果是BaseModel对象，转换为dict
            if hasattr(input_data, 'dict'):
                input_data = input_data.dict()
            elif hasattr(input_data, '__dict__'):
                input_data = input_data.__dict__
            else:
                input_data = {}
        
        # 从字典中提取参数
        if query is None:
            query = input_data.get("query", "")
        if file_path is None:
            file_path = input_data.get("file_path", "")
        if sheet_name is None:
            sheet_name = input_data.get("sheet_name", None)
    else:
        query = ""
        file_path = ""
        sheet_name = None
    
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
    
    # 🔥 修复：强制使用动态文件发现（仅对Excel文件）
    # 对于Excel文件，直接使用动态文件发现，忽略用户提供的路径（因为文件可能被重命名为UUID）
    is_excel_file = file_path and (file_path.endswith('.xlsx') or file_path.endswith('.xls') or '.xlsx' in file_path.lower() or '.xls' in file_path.lower())
    
    if is_excel_file:
        # 🔥 强制使用动态文件发现
        try:
            logger.info(f"🔥 [强制动态文件发现] 检测到Excel文件，使用动态文件发现: {file_path}")
            container_file_path = get_latest_excel_file("/app/uploads")
            logger.info(f"✅ [强制动态文件发现] 成功发现Excel文件: {container_file_path}")
        except FileNotFoundError as e:
            logger.error(f"❌ [第一道防线] 动态文件发现失败: {e}")
            # 列出当前目录和标准目录的文件，帮助调试
            CONTAINER_UPLOADS_DIR = "/app/uploads"
            CONTAINER_DATA_DIR = "/app/data"
            files_in_current_dir = os.listdir(current_dir) if os.path.exists(current_dir) else []
            files_in_data_dir = os.listdir(CONTAINER_DATA_DIR) if os.path.exists(CONTAINER_DATA_DIR) else []
            files_in_uploads_dir = os.listdir(CONTAINER_UPLOADS_DIR) if os.path.exists(CONTAINER_UPLOADS_DIR) else []
            logger.warning(f"   Files in {current_dir}: {files_in_current_dir}")
            logger.warning(f"   Files in {CONTAINER_DATA_DIR}: {files_in_data_dir}")
            logger.warning(f"   Files in {CONTAINER_UPLOADS_DIR}: {files_in_uploads_dir}")
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        except Exception as e:
            logger.error(f"❌ [第一道防线] 动态文件发现异常: {e}", exc_info=True)
            return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
    else:
        # 对于非Excel文件（如CSV），使用原有的路径解析逻辑
        # 🔧 修复：使用新的路径提取和解析函数
        container_file_path = resolve_file_path_with_fallback(file_path)
        
        # 如果路径解析失败，尝试从MinIO下载（仅当路径是file://格式时）
        if not container_file_path and file_path.startswith("file://"):
            storage_path = file_path[7:]  # 移除 file:// 前缀
            if storage_path.startswith("data-sources/"):
                logger.info(f"🔍 [Debug] 尝试从MinIO下载: {storage_path}")
                file_data = minio_service.download_file(
                    bucket_name="data-sources",
                    object_name=storage_path
                )
                
                if file_data:
                    # MinIO下载成功，保存到容器内临时目录
                    temp_dir = os.getenv("TEMP", "/tmp")
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir, exist_ok=True)
                    
                    filename = os.path.basename(storage_path)
                    container_file_path = os.path.join(temp_dir, filename)
                    
                    try:
                        with open(container_file_path, "wb") as f:
                            f.write(file_data)
                        logger.info(f"✅ 文件已从MinIO下载到容器内路径: {container_file_path}")
                    except Exception as e:
                        logger.error(f"⚠️ [第一道防线] 写入临时文件失败: {e}", exc_info=True)
                        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
        
        # 最终检查：如果仍然没有找到文件
        if not container_file_path or not os.path.exists(container_file_path):
            logger.error(f"❌ [第一道防线] 无法找到或访问文件: {file_path}")
            # 列出当前目录和标准目录的文件，帮助调试
            CONTAINER_UPLOADS_DIR = "/app/uploads"
            CONTAINER_DATA_DIR = "/app/data"
            files_in_current_dir = os.listdir(current_dir) if os.path.exists(current_dir) else []
            files_in_data_dir = os.listdir(CONTAINER_DATA_DIR) if os.path.exists(CONTAINER_DATA_DIR) else []
            files_in_uploads_dir = os.listdir(CONTAINER_UPLOADS_DIR) if os.path.exists(CONTAINER_UPLOADS_DIR) else []
            logger.warning(f"   Files in {current_dir}: {files_in_current_dir}")
            logger.warning(f"   Files in {CONTAINER_DATA_DIR}: {files_in_data_dir}")
            logger.warning(f"   Files in {CONTAINER_UPLOADS_DIR}: {files_in_uploads_dir}")
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
            
            # 🔥 修复：定义 Pandas 方法/属性白名单，避免误判为列名
            PANDAS_WHITELIST = {
                'head', 'tail', 'shape', 'columns', 'index', 'dtypes', 'info', 
                'describe', 'iloc', 'loc', 'groupby', 'value_counts', 'sort_values',
                'mean', 'sum', 'count', 'max', 'min', 'apply', 'lambda', 'len',
                'str', 'dt', 'unique', 'nunique', 'isnull', 'notnull', 'dropna', 'fillna',
                'astype', 'copy', 'reset_index', 'set_index', 'merge', 'join', 'concat',
                'agg', 'aggregate', 'transform', 'filter', 'sample', 'drop', 'rename',
                'fillna', 'replace', 'map', 'round', 'abs', 'std', 'var', 'median',
                'quantile', 'corr', 'cov', 'pivot', 'pivot_table', 'melt', 'stack', 'unstack'
            }
            
            if referenced_columns:
                # 过滤掉白名单中的 Pandas 方法和数字（用于 iloc）
                real_missing_columns = [
                    col for col in referenced_columns 
                    if col not in PANDAS_WHITELIST 
                    and not col.isdigit()  # 忽略数字（用于 iloc，如 df.iloc[0]）
                    and col not in df.columns
                ]
                
                if real_missing_columns:
                    logger.error(f"❌ [第一道防线] 查询中引用的列不存在: {real_missing_columns}，实际列名: {list(df.columns)}")
                    return f'SYSTEM ERROR: Data Access Failed. Columns {real_missing_columns} not found. Available columns: {", ".join(df.columns)}. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法找到指定的列，请检查列名"。'
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
        
        # 🔥 修复：定义格式化结果的内部函数，便于重用
        def format_result(result):
            """格式化查询结果"""
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
            return result_str
        
        # 🔥 修复：定义执行查询的内部函数，支持赋值语句
        def execute_query(query_str, scope):
            """执行查询并返回结果（支持赋值语句）"""
            # 判断是简单表达式还是复杂查询（包含换行或赋值）
            if "=" in query_str or "\n" in query_str:
                # 复杂查询：使用 exec() 执行（支持赋值语句）
                # 记录执行前的变量，以便找出新定义的变量
                vars_before = set(scope.keys())
                
                # 直接执行，不自动包装（避免破坏赋值语句）
                exec(query_str, {}, scope)
                
                # 智能结果捕获：
                # 1. 如果代码定义了名为 'result' 的变量，优先使用它
                if 'result' in scope:
                    result = scope['result']
                # 2. 否则，查找最后定义的新变量（排除默认变量）
                else:
                    # 找出新定义的变量（保持顺序）
                    # 遍历 scope 字典（Python 3.7+ 保持插入顺序），找出新定义的变量
                    filtered_vars = []
                    for key in scope.keys():
                        if key not in vars_before and key not in ['df', 'pd', '__builtins__'] and not key.startswith('_'):
                            filtered_vars.append(key)
                    
                    if filtered_vars:
                        # 使用最后定义的变量（通常是 Agent 想要的结果）
                        # 由于字典保持插入顺序，最后一个就是最后定义的
                        last_var = filtered_vars[-1]
                        result = scope[last_var]
                        logger.debug(f"🔍 [执行逻辑] 捕获变量 '{last_var}' 作为结果")
                    else:
                        # 如果没有新变量，返回成功消息
                        result = "✅ Code executed successfully (No output variable captured)."
                        logger.warning("⚠️ [执行逻辑] 查询执行后未找到输出变量")
                
                return result
            else:
                # 简单表达式：使用 eval() 执行（如 df.head()）
                return eval(query_str, {}, scope)
        
        try:
            # 🔥 修复：使用更健壮的 exec/eval 混合方法，支持中文和复杂查询
            # 准备本地作用域，包含 pandas 和 dataframe
            local_scope = {"df": df, "pd": pd, "__builtins__": {}}
            
            # 清理查询字符串：移除前后空白、代码块标记等
            query_clean = query.strip()
            # 移除代码块标记（可能有多层）
            while query_clean.startswith("```"):
                query_clean = query_clean[3:].strip()
            while query_clean.endswith("```"):
                query_clean = query_clean[:-3].strip()
            # 移除反引号
            query_clean = query_clean.strip('`').strip()
            # 移除可能的语言标记（如 "python"）
            if query_clean.lower().startswith("python"):
                query_clean = query_clean[6:].strip()
            # 确保最终清理
            query_clean = query_clean.strip()
            
            # 记录清理后的查询（用于调试）
            logger.debug(f"🔍 [执行逻辑] 清理后的查询: {query_clean[:200]}...")  # 只记录前200字符
            
            # 执行查询
            result = execute_query(query_clean, local_scope)
            
            # 格式化结果
            result_str = format_result(result)
            
            logger.info(f"✅ Pandas 查询执行成功，结果长度: {len(result_str)}")
            # 🔴 第一道防线：检查空数据
            if not result_str or result_str.strip() == "" or result_str == "Empty DataFrame\nColumns: []\nIndex: []":
                logger.warning("⚠️ [第一道防线] Pandas查询返回空数据")
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
            return result_str
            
        except SyntaxError as e:
            # 🔥 修复：对语法错误提供更详细的诊断信息
            logger.error(f"❌ [执行逻辑] 查询语法错误: {e}")
            logger.error(f"   查询内容: {query_clean[:500]}")  # 记录前500字符
            logger.error(f"   错误位置: {e.lineno if hasattr(e, 'lineno') else 'unknown'}")
            
            # 尝试修复常见的引号问题（如果查询中包含中文引号）
            if '''' in query_clean or ''' in query_clean or '"' in query_clean or '"' in query_clean:
                logger.warning("⚠️ [执行逻辑] 检测到中文引号，尝试修复...")
                query_fixed = query_clean.replace(''', "'").replace(''', "'").replace('"', '"').replace('"', '"')
                try:
                    # 重新执行修复后的查询
                    result = execute_query(query_fixed, local_scope)
                    
                    # 如果修复成功，继续执行格式化逻辑
                    logger.info("✅ [执行逻辑] 引号修复成功，继续执行")
                    result_str = format_result(result)
                    
                    # 检查空数据
                    if not result_str or result_str.strip() == "" or result_str == "Empty DataFrame\nColumns: []\nIndex: []":
                        logger.warning("⚠️ [第一道防线] Pandas查询返回空数据")
                        return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
                    
                    logger.info(f"✅ [执行逻辑] 修复后查询执行成功，结果长度: {len(result_str)}")
                    return result_str
                except Exception as fix_error:
                    logger.error(f"❌ [执行逻辑] 引号修复后仍失败: {fix_error}")
            
            # 🔴 第一道防线：返回特定错误字符串
            return f'SYSTEM ERROR: Data Access Failed. Query syntax error: {str(e)}. Please check your query syntax. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "查询语法错误，请检查查询语句"。'
        except Exception as e:
            logger.error(f"❌ [执行逻辑] Pandas 查询执行失败: {e}", exc_info=True)
            query_content = query_clean[:500] if 'query_clean' in locals() else query[:500]
            logger.error(f"   查询内容: {query_content}")
            
            # 🔥 修复：返回详细的错误信息，让 Agent 能够重试
            # 对于执行错误（非语法错误），返回错误详情以便 Agent 调整查询
            error_msg = f"SYSTEM ERROR: Pandas Execution Failed. Error: {str(e)}"
            if "query_clean" in locals():
                error_msg += f"\nQuery: {query_clean[:200]}..."
            return error_msg
            
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

