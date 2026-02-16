# -*- coding: utf-8 -*-
"""
Database Query Tools - 数据库查询工具 (带缓存优化 + Excel支持)
===============================================================

为 AgentV2 提供数据库和 Excel 文件查询能力。

核心功能:
    - execute_query: 执行只读 SQL 查询（数据库和 Excel）
    - list_tables: 列出数据库表或 Excel 工作表
    - get_schema: 获取表结构或 Excel 列信息

优化特性:
    - Schema 缓存：避免重复查询表结构
    - 查询结果缓存：相同查询直接返回缓存
    - TTL 机制：缓存过期自动刷新
    - 多数据源支持：PostgreSQL, MySQL, Excel 文件

作者: BMad Master
版本: 3.0.0
"""

import os
import hashlib
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from functools import wraps
import logging

# 使用 contextvars 替代 threading.local，支持异步/多线程环境
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# ============================================================================
# 连接上下文存储 (使用 contextvars 支持异步/多线程)
# ============================================================================

_connection_id_ctx: ContextVar[Optional[str]] = ContextVar("connection_id", default=None)
_db_session_ctx: ContextVar[Optional[Any]] = ContextVar("db_session", default=None)
_tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)

def _set_connection_context(
    connection_id: Optional[str] = None,
    db_session: Optional[Any] = None,
    tenant_id: Optional[str] = None
) -> None:
    """设置连接上下文（用于工具调用）"""
    _connection_id_ctx.set(connection_id)
    _db_session_ctx.set(db_session)
    _tenant_id_ctx.set(tenant_id)
    logger.info(f"[CONTEXT_SET] connection_id={connection_id}, tenant_id={tenant_id}")


def _get_connection_context() -> Tuple[Optional[str], Optional[Any], Optional[str]]:
    """获取连接上下文"""
    connection_id = _connection_id_ctx.get()
    db_session = _db_session_ctx.get()
    tenant_id = _tenant_id_ctx.get()
    logger.info(f"[CONTEXT_GET] connection_id={connection_id}, tenant_id={tenant_id}")
    return (connection_id, db_session, tenant_id)


def _clear_connection_context() -> None:
    """清除连接上下文"""
    _connection_id_ctx.set(None)
    _db_session_ctx.set(None)
    _tenant_id_ctx.set(None)
    logger.info("[CONTEXT_CLEAR] Connection context cleared")

# ============================================================================
# 缓存管理
# ============================================================================

class SimpleCache:
    """增强的内存缓存，支持统计"""

    def __init__(self, ttl: int = 300, name: str = "cache"):
        """
        初始化缓存

        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
            name: 缓存名称（用于统计）
        """
        self._cache: Dict[str, tuple] = {}  # key -> (value, expire_time)
        self.ttl = ttl
        self.name = name
        self._hits = 0
        self._misses = 0
        self._sets = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                self._hits += 1
                return value
            else:
                # 缓存过期，删除
                del self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存"""
        expire_time = time.time() + self.ttl
        self._cache[key] = (value, expire_time)
        self._sets += 1

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._sets = 0

    def has(self, key: str) -> bool:
        """检查缓存是否存在且未过期"""
        return self.get(key) is not None

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        return {
            "name": self.name,
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "hit_rate": hit_rate,
            "ttl": self.ttl
        }


# 全局缓存实例
_schema_cache = SimpleCache(ttl=600, name="schema_cache")  # Schema 缓存 10 分钟
_query_cache = SimpleCache(ttl=300, name="query_cache")    # 查询结果缓存 5 分钟 (延长 TTL)


def _normalize_sql(sql: str) -> str:
    """
    标准化 SQL 查询用于缓存键生成

    处理:
        - 转换为小写
        - 移除多余空格
        - 移除注释
        - 统一分号使用

    Args:
        sql: 原始 SQL 查询

    Returns:
        标准化后的 SQL
    """
    import re

    # 转换为小写
    normalized = sql.lower().strip()

    # 移除注释
    normalized = re.sub(r'--.*$', '', normalized, flags=re.MULTILINE)
    normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)

    # 移除多余空格和换行
    normalized = ' '.join(normalized.split())

    # 确保以分号结尾
    if not normalized.endswith(';'):
        normalized += ';'

    return normalized


def _make_cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    # 如果参数包含 SQL，先标准化
    if args and 'select' in str(args[0]).lower():
        args = (_normalize_sql(args[0]),) + args[1:]

    key_str = json.dumps([args, kwargs], sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cache_stats() -> Dict[str, Any]:
    """获取所有缓存统计信息"""
    return {
        "schema_cache": _schema_cache.get_stats(),
        "query_cache": _query_cache.get_stats()
    }

# ============================================================================
# 数据库连接管理
# ============================================================================

def get_database_url(
    connection_id: Optional[str] = None
) -> Tuple[str, Optional["DataSourceConnectionInfo"]]:
    """
    获取数据库连接 URL 或 Excel 文件路径

    Args:
        connection_id: 可选的数据源连接 ID

    Returns:
        (connection_url, connection_info) 元组
        - connection_url: 连接字符串（数据库用 URL，Excel 用 "excel://" 前缀）
        - connection_info: 数据源详细信息（如果从数据库获取）
    """
    # 从连接上下文获取数据库会话和租户 ID
    _, db_session, tenant_id = _get_connection_context()

    # 如果没有提供 connection_id，尝试获取租户的默认活跃数据源
    if not connection_id:
        if db_session and tenant_id:
            try:
                # Docker 环境路径设置（确保 /app/src 在 sys.path 开头）
                import sys
                if "/app/src" in sys.path:
                    sys.path.remove("/app/src")
                sys.path.insert(0, "/app/src")
                logger.debug("Ensured /app/src is at sys.path[0] for default data source query")

                from app.data.models import DataSourceConnection

                # 查询租户的第一个活跃数据源
                connection = db_session.query(DataSourceConnection).filter(
                    DataSourceConnection.tenant_id == tenant_id,
                    DataSourceConnection.status == "active"
                ).first()

                if connection:
                    connection_id = str(connection.id)
                    logger.info(f"自动获取租户 {tenant_id} 的默认数据源: {connection.name} (ID: {connection_id})")
                else:
                    logger.warning(f"租户 {tenant_id} 没有配置活跃数据源，使用系统元数据库")
                    return os.environ.get("DATABASE_URL"), None
            except ImportError as e:
                logger.error(f"Failed to import DataSourceConnection model: {e}")
                return os.environ.get("DATABASE_URL"), None
            except Exception as e:
                logger.error(f"Failed to query default data source: {e}")
                return os.environ.get("DATABASE_URL"), None
        else:
            # 没有数据库会话，使用环境变量中的默认数据库
            return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/data_agent"), None

    # 从这里开始有 connection_id
    if not db_session or not tenant_id:
        logger.warning(
            f"connection_id provided but db_session/tenant_id not available. "
            f"Using default database. connection_id={connection_id}"
        )
        return os.environ.get("DATABASE_URL"), None

    try:
        # 导入数据源服务（Docker 环境使用 /app 路径）
        import sys

        # 详细的调试日志
        logger.info(f"BEFORE: /app/src in sys.path = {('/app/src' in sys.path)}")
        logger.info(f"BEFORE: os.path.exists('/app/src') = {os.path.exists('/app/src')}")
        logger.info(f"BEFORE: os.path.exists('/app/src/app/services') = {os.path.exists('/app/src/app/services')}")
        logger.info(f"BEFORE: sys.path[0] = {sys.path[0]}")

        # 确保 /app/src 在 sys.path 的最前面（因为 app 包在 /app/src/app/...）
        # Python 导入 app.services 时，会在 sys.path 中查找 app/ 目录
        if "/app/src" in sys.path:
            sys.path.remove("/app/src")
        sys.path.insert(0, "/app/src")
        logger.info("ACTION: Ensured /app/src is at sys.path[0]")

        logger.info(f"AFTER: sys.path[0] = {sys.path[0]}")

        # 检查 /app/src/app 目录内容
        if os.path.exists("/app/src/app"):
            all_files = os.listdir("/app/src/app")
            logger.info(f"Files in /app/src/app (total {len(all_files)}): {all_files}")
            # 检查 services 是否存在
            if "services" in all_files:
                logger.info("✓ services directory found in /app/src/app")
                # 检查 __init__.py 文件
                init_files = []
                for pyc_init in ["/app/src/app/__init__.py", "/app/src/app/services/__init__.py"]:
                    if os.path.exists(pyc_init):
                        init_files.append(pyc_init + " ✓")
                    else:
                        init_files.append(pyc_init + " ✗")
                logger.info(f"__init__.py files: {init_files}")
            else:
                logger.error("✗ services directory NOT found in /app/src/app")
        else:
            logger.error(f"Directory /app/src/app does not exist!")

        # 检查是否能直接访问 services 目录
        if os.path.exists("/app/src/app/services/data_source_service.py"):
            logger.info("✓ data_source_service.py file exists")
        else:
            logger.error("✗ data_source_service.py file NOT found at /app/src/app/services/")

        # 清除可能的陈旧导入缓存（包括 app 模块本身）
        stale_keys = [k for k in sys.modules.keys() if k.startswith("app.")]
        if stale_keys:
            logger.info(f"Removing stale imports from sys.modules: {stale_keys}")
            for key in stale_keys:
                del sys.modules[key]
        # 确保删除 app 模块本身（可能是命名空间包）
        if "app" in sys.modules:
            logger.info(f"Removing 'app' module from sys.modules (was: {type(sys.modules['app'])})")
            del sys.modules["app"]

        # 尝试导入
        logger.info("Attempting to import app.services.data_source_service...")
        try:
            from app.services.data_source_service import data_source_service
            from app.services.data_source_service import DataSourceConnectionInfo
            logger.info("Successfully imported data_source_service")
        except ImportError as e:
            # 添加更详细的错误信息
            logger.error(f"ImportError: {e}")
            logger.error(f"sys.path[0:3] = {sys.path[0:3]}")
            # 检查 app 模块是否在 sys.modules 中
            if "app" in sys.modules:
                logger.error(f"app module already in sys.modules: {sys.modules['app']}")
            if "app.services" in sys.modules:
                logger.error(f"app.services already in sys.modules: {sys.modules['app.services']}")
            raise

        # 同步包装：因为 data_source_service 是异步的
        import asyncio

        def get_connection_info():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                logger.info(f"Calling data_source_service.get_data_source_connection_info(connection_id={connection_id}, tenant_id={tenant_id})")
                result = loop.run_until_complete(
                    data_source_service.get_data_source_connection_info(
                        connection_id=connection_id,
                        tenant_id=tenant_id,
                        db=db_session
                    )
                )
                logger.info(f"data_source_service returned: {result}")
                return result
            except Exception as e:
                logger.error(f"Error in get_connection_info: {e}", exc_info=True)
                raise
            finally:
                loop.close()

        connection_info = get_connection_info()
        logger.info(f"Retrieved connection_info: type={connection_info.connection_type}, file_path={connection_info.file_path}")

        # 根据数据源类型返回不同的连接信息
        if connection_info.connection_type == "excel":
            # Excel 文件：返回特殊标记和文件信息
            logger.info(f"Using Excel data source: {connection_info.file_path}, sheets={connection_info.sheets}")
            return f"excel://{connection_info.file_path}", connection_info
        else:
            # 数据库：返回解密后的连接字符串
            logger.info(f"Using database data source: type={connection_info.connection_type}")
            return connection_info.connection_string, connection_info

    except ImportError as e:
        logger.error(f"Failed to import data_source_service: {e}")
        return os.environ.get("DATABASE_URL"), None
    except Exception as e:
        logger.error(f"Failed to get connection info for {connection_id}: {e}")
        return os.environ.get("DATABASE_URL"), None


def _is_excel_connection(database_url: str) -> bool:
    """检查是否是 Excel 连接"""
    return database_url.startswith("excel://")


def _is_sqlite_connection(database_url: str) -> bool:
    """检查是否是 SQLite 连接"""
    return database_url.startswith("sqlite:///")


def create_db_connection(database_url: str):
    """
    创建数据库连接（支持 PostgreSQL 和 SQLite）

    Args:
        database_url: 数据库连接 URL

    Returns:
        数据库连接对象
    """
    if _is_sqlite_connection(database_url):
        import sqlite3
        # SQLite 连接格式: sqlite:///path/to/database.db
        db_path = database_url.replace("sqlite:///", "")
        logger.info(f"Creating SQLite connection: {db_path}")
        return sqlite3.connect(db_path)
    else:
        # PostgreSQL 连接
        import psycopg2
        logger.info(f"Creating PostgreSQL connection")
        return psycopg2.connect(database_url)


def _get_excel_file_path(database_url: str) -> str:
    """从 Excel 连接 URL 中提取文件路径"""
    return database_url[8:]  # 去掉 "excel://" 前缀


# ============================================================================
# Excel 查询工具
# ============================================================================

def execute_excel_query(
    query: str,
    file_path: str,
    sheet_name: Optional[str] = None
) -> str:
    """
    执行 Excel 文件查询（使用 pandas）

    Args:
        query: 类似 SQL 的查询或 pandas 代码
        file_path: Excel 文件路径
        sheet_name: 工作表名称（可选）

    Returns:
        查询结果的 JSON 字符串
    """
    import json
    import pandas as pd

    try:
        # 读取 Excel 文件
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
        else:
            # 读取第一个工作表
            df = pd.read_excel(file_path, engine='openpyxl')
            sheet_name = "Sheet1"

        logger.info(f"Excel file loaded: {file_path}, sheet: {sheet_name}, shape: {df.shape}")

        # 简单的 SQL 解析和转换
        result_df = _parse_sql_to_pandas(query, df)

        # 转换为结果格式
        columns = result_df.columns.tolist()
        rows = result_df.values.tolist()

        # 处理 NaN 值
        rows = [[None if pd.isna(v) else v for v in row] for row in rows]

        result = {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "success": True,
            "data_source": "excel",
            "sheet_name": sheet_name
        }

        logger.info(f"Excel query executed: {len(rows)} rows returned")
        return json.dumps(result, ensure_ascii=False, default=str)

    except FileNotFoundError:
        logger.error(f"Excel file not found: {file_path}")
        return json.dumps({
            "error": f"Excel file not found: {file_path}",
            "error_type": "file_not_found"
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Excel query error: {e}")
        return json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)


def _parse_sql_to_pandas(query: str, df: "Any") -> "Any":
    """
    简单的 SQL 到 pandas 转换

    支持的基本 SQL 语法:
    - SELECT col1, col2 FROM table
    - SELECT * FROM table
    - SELECT ... FROM table WHERE col = value
    - SELECT ... FROM table WHERE col LIKE value
    - SELECT ... FROM table ORDER BY col
    - SELECT ... FROM table LIMIT n

    Args:
        query: SQL 查询语句
        df: pandas DataFrame

    Returns:
        过滤后的 DataFrame
    """
    import re

    query_upper = query.upper().strip()
    result_df = df.copy()

    # 提取 SELECT 列
    select_match = re.search(r'SELECT\s+(.+?)\s+FROM', query_upper)
    if select_match:
        columns_str = select_match.group(1).strip()
        if columns_str != '*':
            # 解析列名（处理逗号分隔的列）
            columns = [col.strip().lower() for col in columns_str.split(',')]
            # 匹配实际列名（不区分大小写）
            actual_columns = {col.lower(): col for col in df.columns}
            selected_columns = []
            for col in columns:
                if col in actual_columns:
                    selected_columns.append(actual_columns[col])
            if selected_columns:
                result_df = result_df[selected_columns]

    # 提取 WHERE 条件
    where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+LIMIT|;|$)', query_upper)
    if where_match:
        where_clause = where_match.group(1).strip()
        result_df = _apply_where_clause(result_df, where_clause)

    # 提取 ORDER BY
    order_match = re.search(r'ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?', query_upper)
    if order_match:
        col_name = order_match.group(1).lower()
        direction = order_match.group(2) if order_match.group(2) else 'ASC'

        # 匹配实际列名
        actual_columns = {col.lower(): col for col in result_df.columns}
        if col_name in actual_columns:
            actual_col = actual_columns[col_name]
            ascending = direction == 'ASC'
            result_df = result_df.sort_values(by=actual_col, ascending=ascending)

    # 提取 LIMIT
    limit_match = re.search(r'LIMIT\s+(\d+)', query_upper)
    if limit_match:
        limit = int(limit_match.group(1))
        result_df = result_df.head(limit)

    return result_df


def _apply_where_clause(df: "Any", where_clause: str) -> "Any":
    """
    应用 WHERE 条件到 DataFrame

    支持的条件:
    - col = value
    - col LIKE value
    - col > value, col < value, col >= value, col <= value
    - col AND col
    - col OR col

    Args:
        df: pandas DataFrame
        where_clause: WHERE 子句

    Returns:
        过滤后的 DataFrame
    """
    import re

    result_df = df.copy()

    # 分割 AND/OR 条件
    conditions = re.split(r'\s+(AND|OR)\s+', where_clause, flags=re.IGNORECASE)
    current_op = 'AND'

    for i, cond in enumerate(conditions):
        cond = cond.strip()
        if cond.upper() in ('AND', 'OR'):
            current_op = cond.upper()
            continue

        # 解析条件 - 🔧 修复：将更长的操作符放在前面
        match = re.match(
            r'(\w+)\s*(>=|<=|<>|=|LIKE|>|<)\s*[\'"]?([^\'"]+)[\'"]?',
            cond,
            re.IGNORECASE
        )
        if match:
            col_name = match.group(1).lower()
            operator = match.group(2).upper()
            value = match.group(3).strip()

            # 匹配实际列名
            actual_columns = {col.lower(): col for col in result_df.columns}
            if col_name not in actual_columns:
                continue

            actual_col = actual_columns[col_name]

            # 应用条件
            mask = None
            if operator == '=':
                # 尝试转换为数字
                try:
                    value_num = float(value)
                    mask = result_df[actual_col] == value_num
                except ValueError:
                    mask = result_df[actual_col].astype(str) == value
            elif operator == 'LIKE':
                mask = result_df[actual_col].astype(str).str.contains(
                    value.replace('%', ''),
                    case=False,
                    na=False
                )
            elif operator == '>':
                try:
                    value_num = float(value)
                    mask = result_df[actual_col] > value_num
                except ValueError:
                    mask = result_df[actual_col].astype(str) > value
            elif operator == '<':
                try:
                    value_num = float(value)
                    mask = result_df[actual_col] < value_num
                except ValueError:
                    mask = result_df[actual_col].astype(str) < value
            elif operator == '>=':
                try:
                    value_num = float(value)
                    mask = result_df[actual_col] >= value_num
                except ValueError:
                    mask = result_df[actual_col].astype(str) >= value
            elif operator == '<=':
                try:
                    value_num = float(value)
                    mask = result_df[actual_col] <= value_num
                except ValueError:
                    mask = result_df[actual_col].astype(str) <= value
            elif operator == '<>':
                # 不等于
                try:
                    value_num = float(value)
                    mask = result_df[actual_col] != value_num
                except ValueError:
                    mask = result_df[actual_col].astype(str) != value

            if mask is not None:
                if i == 0 or current_op == 'AND':
                    result_df = result_df[mask]
                else:  # OR
                    result_df = pd.concat([result_df, df[mask]]).drop_duplicates()

    return result_df


# ============================================================================
# 数据库查询工具
# ============================================================================

# 注意：这些函数不再使用 @tool 装饰器，而是在 get_database_tools 中手动创建 StructuredTool
def execute_query(query: str, connection_id: Optional[str] = None) -> str:
    """
    执行数据查询 (支持数据库和 Excel 文件)

    这个工具用于执行只读的数据查询，获取数据。
    自动检测数据源类型并使用相应的查询方法。

    Args:
        query: SQL SELECT 查询语句（或用于 Excel 的类 SQL 查询）
        connection_id: 数据源连接 ID (可选)

    Returns:
        查询结果的 JSON 字符串，包含列信息和行数据

    Example:
        >>> execute_query("SELECT * FROM users LIMIT 10")
        '{"columns": ["id", "name"], "rows": [[1, "Alice"], [2, "Bob"]], "row_count": 2}'
    """
    import json
    import re
    import threading

    # 安全检查：只允许 SELECT 查询
    query_upper = query.upper().strip()

    # 检查危险关键字
    dangerous_keywords = [
        "DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE",
        "ALTER", "CREATE", "GRANT", "REVOKE"
    ]

    for keyword in dangerous_keywords:
        if re.search(rf"\b{keyword}\b", query_upper):
            return json.dumps({
                "error": f"Security Alert: {keyword} operations are not allowed",
                "error_type": "forbidden_operation"
            }, ensure_ascii=False)

    # 检查是否以 SELECT 或其他允许的关键字开头
    allowed_starts = ["SELECT", "WITH", "SHOW", "EXPLAIN", "DESCRIBE", "DESC"]
    if not any(query_upper.startswith(start) for start in allowed_starts):
        return json.dumps({
            "error": "Query must start with SELECT, WITH, SHOW, EXPLAIN, or DESCRIBE",
            "error_type": "invalid_query_type"
        }, ensure_ascii=False)

    # 清理和修复 SQL
    cleaned_query = clean_and_validate_sql(query)
    if cleaned_query != query:
        logger.info(f"SQL cleaned: {query[:50]}... -> {cleaned_query[:50]}...")

    # 从 thread-local 获取 connection_id（如果未通过参数传递）
    # Agent 调用工具时不会传递 connection_id，需要从连接上下文获取
    if connection_id is None:
        connection_id, _, _ = _get_connection_context()

    # 检查查询结果缓存 (使用标准化的 SQL 作为缓存键)
    cache_key = _make_cache_key(cleaned_query, connection_id)
    cached_result = _query_cache.get(cache_key)
    if cached_result is not None:
        logger.info(f"Query result cache HIT: {cleaned_query[:50]}...")
        return cached_result
    else:
        logger.info(f"Query result cache MISS: {cleaned_query[:50]}...")

    # 获取数据源连接信息
    database_url, connection_info = get_database_url(connection_id)
    logger.info(f"Using connection: connection_id={connection_id}, url_type={'excel' if _is_excel_connection(database_url) else 'database'}")

    # 如果是 Excel 连接，使用 Excel 查询
    if _is_excel_connection(database_url):
        logger.info(f"Detected Excel data source, using Excel query")
        file_path = _get_excel_file_path(database_url)
        
        # 🔥 修复：从 SQL 查询中解析表名，而不是使用固定的 table_name
        # 尝试从 SQL 中提取表名
        extracted_table_name = _extract_table_name_from_query(cleaned_query)
        
        # 如果成功提取表名，使用它；否则回退到 connection_info.table_name
        if extracted_table_name:
            sheet_name = extracted_table_name
            logger.info(f"Using extracted table name from SQL: '{sheet_name}'")
        else:
            sheet_name = connection_info.table_name if connection_info else None
            logger.warning(f"Could not extract table name from SQL, using default: '{sheet_name}'")

        result = execute_excel_query(cleaned_query, file_path, sheet_name)

        # 存储到缓存
        _query_cache.set(cache_key, result)
        return result

    # 数据库查询（原有逻辑）
    # 查询结果和错误容器
    result_container = {"result": None, "error": None}

    def execute_with_timeout():
        """在单独的线程中执行查询"""
        try:
            # 创建数据库连接
            conn = create_db_connection(database_url)
            cursor = conn.cursor()

            # 设置语句超时（PostgreSQL statement_timeout）
            # SQLite 不支持此语句，需要跳过
            if not _is_sqlite_connection(database_url):
                cursor.execute("SET statement_timeout = 30000")  # 30秒

            # 执行查询
            cursor.execute(cleaned_query)

            # 获取结果
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            # 关闭连接
            cursor.close()
            conn.close()

            # 构建结果
            result_container["result"] = {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "success": True
            }

            logger.info(f"Query executed successfully: {len(rows)} rows returned")

        except Exception as e:
            result_container["error"] = e

    # 使用线程执行查询，30秒超时
    query_thread = threading.Thread(target=execute_with_timeout)
    query_thread.daemon = True
    query_thread.start()
    query_thread.join(timeout=30)

    # 检查结果
    if query_thread.is_alive():
        # 查询超时
        logger.error("Query execution timeout (30s)")
        return json.dumps({
            "error": "Query execution timeout after 30 seconds",
            "error_type": "timeout_error",
            "query": cleaned_query[:100]
        }, ensure_ascii=False)

    if result_container["error"] is not None:
        error = result_container["error"]
        logger.error(f"Query execution error: {error}")
        logger.error(f"Failed query: {cleaned_query[:200]}")
        return json.dumps({
            "error": str(error),
            "error_type": "execution_error",
            "query": cleaned_query[:100],  # 截断查询
            "suggestion": get_query_suggestion(str(error), cleaned_query)
        }, ensure_ascii=False)

    if result_container["result"] is not None:
        result_json = json.dumps(result_container["result"], ensure_ascii=False, default=str)

        # 存储到缓存 (缓存 5 分钟)
        _query_cache.set(cache_key, result_json)
        logger.info(f"Query result cached: {cleaned_query[:50]}...")

        return result_json

    # 未知的错误
    return json.dumps({
        "error": "Unknown error during query execution",
        "error_type": "unknown_error"
    }, ensure_ascii=False)


def clean_and_validate_sql(query: str) -> str:
    """
    清理和验证 SQL 查询

    修复常见的 LLM 生成错误：
    - LIMIT 子句后的错误内容（WHERE, AND, OR 等）
    - tenants 表的 tenant_id 列错误（应使用 id）
    - 多余的分号
    - 不完整的查询

    Args:
        query: 原始 SQL 查询

    Returns:
        清理后的 SQL 查询
    """
    import re

    # 移除前后空格
    sql = query.strip()

    # 修复 0: tenants 表的 tenant_id → id 自动替换（常见错误）
    # 匹配 FROM tenants ... WHERE tenant_id 或 JOIN tenants ... WHERE tenant_id
    if re.search(r'\btenants\b', sql, re.IGNORECASE):
        # 替换 tenants 表上的 tenant_id 为 id
        # 匹配 WHERE tenant_id = 或 AND tenant_id = 等
        sql = re.sub(
            r'(WHERE|AND|OR)\s+tenant_id\s*=',
            r'\1 id =',
            sql,
            flags=re.IGNORECASE
        )
        # 如果修改了 SQL，记录日志
        if 'tenant_id' in query.lower() and 'tenant_id' not in sql.lower():
            logger.info("Auto-fixed: tenants.tenant_id → tenants.id")

    # 修复 1: 移除 LIMIT 后面的任何内容（LLM 常见错误）
    # 匹配 LIMIT 子句，然后截断，移除后面的 WHERE, AND, OR 等
    # 这个正则匹配 LIMIT 数字，然后后面不能有 WHERE/AND/OR/GROUP/ORDER/HAVING
    limit_pattern = r'\bLIMIT\s+(\d+)'
    match = re.search(limit_pattern, sql, re.IGNORECASE)
    if match:
        # 找到 LIMIT 子句，截断到数字结束的地方
        # 需要找到 LIMIT 后面的数字
        limit_end = match.end()
        # 检查 LIMIT 后面是否还有其他子句（WHERE, AND, OR, GROUP BY, HAVING 等）
        # 如果有，截断它们
        remaining_sql = sql[limit_end:].strip()
        # 如果剩余内容以 WHERE, AND, OR, GROUP, HAVING 开头，说明是错误的
        if re.match(r'^(WHERE|AND|OR|GROUP BY|HAVING)', remaining_sql, re.IGNORECASE):
            # 截断到 LIMIT 数字结束的地方
            sql = sql[:limit_end].rstrip()
            logger.info(f"Removed content after LIMIT: {remaining_sql[:50]}...")

    # 修复 2: 移除末尾的分号（如果有多个）
    sql = re.sub(r';+$', '', sql)

    # 修复 3: 确保查询以分号结尾（对于单条查询）
    if not sql.endswith(';'):
        sql += ';'

    # 修复 4: 移除注释后的危险命令（额外安全检查）
    # 移除 -- 后面的内容到行尾
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    # 移除 /* */ 块注释
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # 修复 5: 清理多余的空格
    sql = ' '.join(sql.split())

    return sql


def _extract_table_name_from_query(query: str) -> Optional[str]:
    """
    从 SQL 查询中提取 FROM 子句的表名

    支持简单的 SELECT 查询，提取第一个 FROM 后面的表名。
    支持带emoji、中文、特殊字符的表名。

    Args:
        query: SQL 查询语句

    Returns:
        提取的表名，如果无法解析则返回 None
    """
    import re

    try:
        # 移除注释和换行符，简化解析
        cleaned = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = ' '.join(cleaned.split())

        # 🔧 修复：优先匹配双引号内的表名（支持emoji、中文、空格）
        # 模式：FROM "table name" 或 FROM "表名"
        double_quote_pattern = r'\bFROM\s+"([^"]+)"'
        match = re.search(double_quote_pattern, cleaned, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            logger.info(f"Extracted table name (double-quoted) from query: '{table_name}'")
            return table_name

        # 🔧 匹配单引号内的表名
        single_quote_pattern = r"\bFROM\s+'([^']+)'"
        match = re.search(single_quote_pattern, cleaned, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            logger.info(f"Extracted table name (single-quoted) from query: '{table_name}'")
            return table_name

        # 🔧 最后：匹配不带引号的表名（支持emoji和中文，但不能有空格）
        # 使用 Unicode 属性匹配任何单词字符（包括中文、emoji等）
        unquoted_pattern = r'\bFROM\s+([^\s;]+?)(?:\s+WHERE|\s+ORDER|\s+GROUP|\s+LIMIT|\s+HAVING|;|$)'
        match = re.search(unquoted_pattern, cleaned, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            logger.info(f"Extracted table name (unquoted) from query: '{table_name}'")
            return table_name

        logger.warning(f"Could not extract table name from query: {query[:100]}...")
        return None
    except Exception as e:
        logger.warning(f"Error extracting table name: {e}")
        return None


def get_query_suggestion(error_msg: str, query: str) -> Optional[str]:
    """
    根据错误信息提供查询建议

    Args:
        error_msg: 错误信息
        query: 原始查询

    Returns:
        建议信息
    """
    import re

    error_lower = error_msg.lower()

    if 'limit' in error_lower and 'and' in error_lower:
        return "LIMIT 子句后不应有 AND 条件。请将 LIMIT 放在查询最后。"

    if 'column' in error_lower and 'does not exist' in error_lower:
        # 提取不存在的列名
        match = re.search(r'column "(.*?)" does not exist', error_msg)
        if match:
            col = match.group(1)
            return f"列 '{col}' 不存在。请使用 list_tables 和 get_schema 查看可用的表和列。"

    if 'relation' in error_lower and 'does not exist' in error_lower:
        match = re.search(r'relation "(.*?)" does not exist', error_msg)
        if match:
            table = match.group(1)
            return f"表 '{table}' 不存在。请使用 list_tables 查看可用的表。"

    if 'syntax error' in error_lower:
        return "SQL 语法错误。请确保查询格式正确，建议使用简单的 SELECT 语句。"

    return None


# 注意：这些函数不再使用 @tool 装饰器，而是在 get_database_tools 中手动创建 StructuredTool
def list_tables(connection_id: Optional[str] = None) -> str:
    """
    列出数据库中的所有表或 Excel 文件中的所有工作表

    Args:
        connection_id: 数据源连接 ID (可选)

    Returns:
        表列表的 JSON 字符串

    Example:
        >>> list_tables()
        '{"tables": ["users", "orders", "products"], "table_count": 3}'
    """
    import json

    # 从 thread-local 获取 connection_id（如果未通过参数传递）
    if connection_id is None:
        connection_id, _, _ = _get_connection_context()

    logger.info(f"list_tables: connection_id={connection_id}")

    # 清除旧缓存以确保使用新的连接信息
    if connection_id:
        _schema_cache.clear()

    # 检查缓存
    cache_key = _make_cache_key("list_tables", connection_id)
    cached = _schema_cache.get(cache_key)
    if cached is not None:
        logger.info("list_tables: 返回缓存结果")
        return cached

    # 获取数据源连接信息
    database_url, connection_info = get_database_url(connection_id)

    # 如果是 Excel 连接，返回工作表列表
    if _is_excel_connection(database_url):
        logger.info("list_tables: Detected Excel data source, listing sheets")
        try:
            file_path = _get_excel_file_path(database_url)
            import pandas as pd

            excel_file = pd.ExcelFile(file_path, engine='openpyxl')
            sheets = excel_file.sheet_names

            result = {
                "tables": sheets,
                "table_count": len(sheets),
                "success": True,
                "data_source": "excel",
                "file_path": file_path
            }

            result_str = json.dumps(result, ensure_ascii=False)
            _schema_cache.set(cache_key, result_str)
            logger.info(f"list_tables: Excel 文件，{len(sheets)} 个工作表: {sheets}")

            return result_str

        except Exception as e:
            logger.error(f"List Excel sheets error: {e}")
            error_str = json.dumps({
                "error": str(e),
                "error_type": "execution_error"
            }, ensure_ascii=False)
            return error_str

    # 数据库查询（原有逻辑）
    try:
        conn = create_db_connection(database_url)
        cursor = conn.cursor()

        # PostgreSQL 查询所有表
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        tables = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        result = {
            "tables": tables,
            "table_count": len(tables),
            "success": True
        }

        result_str = json.dumps(result, ensure_ascii=False)
        # 存入缓存
        _schema_cache.set(cache_key, result_str)
        logger.info(f"list_tables: 查询成功，缓存结果 ({len(tables)} 个表)")

        return result_str

    except Exception as e:
        logger.error(f"List tables error: {e}")
        error_str = json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)
        return error_str


# 注意：这些函数不再使用 @tool 装饰器，而是在 get_database_tools 中手动创建 StructuredTool
def get_schema(table_name: str, connection_id: Optional[str] = None) -> str:
    """
    获取表的结构信息或 Excel 工作表的列信息

    Args:
        table_name: 表名或工作表名
        connection_id: 数据源连接 ID (可选)

    Returns:
        表结构的 JSON 字符串，包含列名、类型、是否可空等信息

    Example:
        >>> get_schema("users")
        '{"table_name": "users", "columns": [{"name": "id", "type": "integer", "nullable": false}], "column_count": 1}'
    """
    import json

    # 从 thread-local 获取 connection_id（如果未通过参数传递）
    if connection_id is None:
        connection_id, _, _ = _get_connection_context()

    # 检查缓存
    cache_key = _make_cache_key("get_schema", table_name, connection_id)
    cached = _schema_cache.get(cache_key)
    if cached is not None:
        logger.info(f"get_schema({table_name}): 返回缓存结果")
        return cached

    # 获取数据源连接信息
    database_url, connection_info = get_database_url(connection_id)

    # 如果是 Excel 连接，返回列信息
    if _is_excel_connection(database_url):
        logger.info(f"get_schema({table_name}): Detected Excel data source, getting columns")
        try:
            file_path = _get_excel_file_path(database_url)
            import pandas as pd

            # 读取 Excel 工作表
            df = pd.read_excel(file_path, sheet_name=table_name, engine='openpyxl', nrows=0)

            # 获取列信息
            columns = []
            for col in df.columns:
                # 推断数据类型
                dtype_str = str(df[col].dtype)
                # 简化类型名称
                if dtype_str.startswith('int'):
                    col_type = 'integer'
                elif dtype_str.startswith('float'):
                    col_type = 'float'
                elif dtype_str == 'bool':
                    col_type = 'boolean'
                elif dtype_str.startswith('datetime'):
                    col_type = 'datetime'
                else:
                    col_type = 'text'

                columns.append({
                    "name": col,
                    "type": col_type,
                    "nullable": True  # Excel 不强制 NOT NULL
                })

            result = {
                "table_name": table_name,
                "columns": columns,
                "column_count": len(columns),
                "success": True,
                "data_source": "excel"
            }

            result_str = json.dumps(result, ensure_ascii=False)
            _schema_cache.set(cache_key, result_str)
            logger.info(f"get_schema({table_name}): Excel 工作表，{len(columns)} 列")

            return result_str

        except Exception as e:
            logger.error(f"Get Excel schema error: {e}")
            error_str = json.dumps({
                "error": str(e),
                "error_type": "execution_error"
            }, ensure_ascii=False)
            return error_str

    # 数据库查询（原有逻辑）
    try:
        conn = create_db_connection(database_url)
        cursor = conn.cursor()

        # PostgreSQL 查询表结构
        cursor.execute("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """, (table_name,))

        columns = []
        for row in cursor.fetchall():
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3]
            })

        cursor.close()
        conn.close()

        result = {
            "table_name": table_name,
            "columns": columns,
            "column_count": len(columns),
            "success": True
        }

        result_str = json.dumps(result, ensure_ascii=False)
        # 存入缓存
        _schema_cache.set(cache_key, result_str)
        logger.info(f"get_schema({table_name}): 查询成功，缓存结果 ({len(columns)} 列)")

        return result_str

    except Exception as e:
        logger.error(f"Get schema error: {e}")
        error_str = json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)
        return error_str


# ============================================================================
# 工具集合
# ============================================================================

def get_database_tools(
    connection_id: Optional[str] = None,
    db_session: Optional[Any] = None,
    tenant_id: Optional[str] = None
) -> List:
    """
    获取所有数据库工具（支持 Excel 和数据库）

    Args:
        connection_id: 数据源连接 ID（可选）
        db_session: 数据库会话（用于查询数据源配置）
        tenant_id: 租户 ID

    Returns:
        LangChain Tool 列表
    """
    # 设置连接上下文供工具使用（虽然之后会使用闭包，但保留设置以兼容）
    _set_connection_context(connection_id, db_session, tenant_id)

    # 🔧 新方案：使用闭包预绑定 connection_id
    # 同时在包装函数中设置 context 变量，确保 _get_connection_context() 能够获取到正确的值

    from langchain_core.tools import StructuredTool

    # 创建包装函数，预绑定 connection_id 并设置 context
    def make_execute_query(fixed_connection_id, fixed_db_session, fixed_tenant_id):
        def wrapped(query: str) -> str:
            # 设置 context 变量，确保 get_database_url 能够获取到正确的值
            _set_connection_context(fixed_connection_id, fixed_db_session, fixed_tenant_id)
            return execute_query(query, fixed_connection_id)
        wrapped.__name__ = "execute_query"
        wrapped.__doc__ = execute_query.__doc__
        return wrapped

    def make_list_tables(fixed_connection_id, fixed_db_session, fixed_tenant_id):
        def wrapped() -> str:
            # 设置 context 变量
            _set_connection_context(fixed_connection_id, fixed_db_session, fixed_tenant_id)
            return list_tables(fixed_connection_id)
        wrapped.__name__ = "list_tables"
        wrapped.__doc__ = list_tables.__doc__
        return wrapped

    def make_get_schema(fixed_connection_id, fixed_db_session, fixed_tenant_id):
        def wrapped(table_name: str) -> str:
            # 设置 context 变量
            _set_connection_context(fixed_connection_id, fixed_db_session, fixed_tenant_id)
            return get_schema(table_name, fixed_connection_id)
        wrapped.__name__ = "get_schema"
        wrapped.__doc__ = get_schema.__doc__
        return wrapped

    # 创建带预绑定 connection_id 的包装函数
    bound_execute_query = make_execute_query(connection_id, db_session, tenant_id)
    bound_list_tables = make_list_tables(connection_id, db_session, tenant_id)
    bound_get_schema = make_get_schema(connection_id, db_session, tenant_id)

    # 创建 StructuredTool 对象
    tools = [
        StructuredTool.from_function(
            func=bound_execute_query,
            name="execute_query",
            description=execute_query.__doc__
        ),
        StructuredTool.from_function(
            func=bound_list_tables,
            name="list_tables",
            description=list_tables.__doc__
        ),
        StructuredTool.from_function(
            func=bound_get_schema,
            name="get_schema",
            description=get_schema.__doc__
        )
    ]

    logger.info(f"[get_database_tools] Created {len(tools)} tools with connection_id={connection_id}")
    return tools


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("Database Tools 测试")
    print("=" * 60)

    # 测试 1: 列出表
    print("\n[TEST 1] 列出数据库表")
    result = list_tables.invoke({})
    print(f"结果: {result}")

    # 测试 2: 获取表结构
    print("\n[TEST 2] 获取表结构")
    result = get_schema.invoke({"table_name": "tenants"})
    print(f"结果: {result}")

    # 测试 3: 执行查询
    print("\n[TEST 3] 执行查询")
    result = execute_query.invoke({"query": "SELECT * FROM tenants LIMIT 1"})
    print(f"结果: {result}")
