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
    - list_schema_files: 列出语义层文档
    - read_schema_file: 读取语义层文档内容
    - search_schema: 搜索语义层文档
    - SchemaFSValidator: 文件系统安全验证

优化特性:
    - Schema 缓存：避免重复查询表结构
    - 查询结果缓存：相同查询直接返回缓存
    - TTL 机制：缓存过期自动刷新
    - 多数据源支持：PostgreSQL, MySQL, Excel 文件
    - 文件系统安全访问：严格限制路径遍历
    - 🔧 智能表推荐：增强的 list_tables 返回表描述和推荐信息
    - 🔧 线程安全缓存：使用 RLock 保护并发访问

作者: BMad Master
版本: 3.3.0 (Bug修复: 线程安全缓存)
"""

import os
import hashlib
import json
import time
import threading
from typing import Optional, List, Dict, Any, Tuple
from functools import lru_cache
import logging

# 使用 contextvars 替代 threading.local，支持异步/多线程环境
from contextvars import ContextVar

try:
    from ..core.backend_runtime import import_backend_module, run_async_sync
except ImportError:
    # 兼容直接运行（非包方式）
    from core.backend_runtime import import_backend_module, run_async_sync

logger = logging.getLogger(__name__)

# 🔧 新增：导入表描述配置
try:
    from ..table_config import (
        enrich_tables_with_description,
    )
    TABLE_DESCRIPTIONS_AVAILABLE = True
    logger.debug("[database_tools] table descriptions loaded")
except ImportError:
    TABLE_DESCRIPTIONS_AVAILABLE = False
    logger.warning("[database_tools] table descriptions unavailable; using basic mode")

# 🔧 新增：导入表关系元数据（智能错误提示）
try:
    from .schema_metadata import (
        find_column_suggestion,
        suggest_join_query,
        generate_error_with_suggestion,
        get_table_relationships,
        COLUMN_SEMANTICS,
        TABLE_RELATIONSHIPS
    )
    SCHEMA_METADATA_AVAILABLE = True
    logger.debug("[database_tools] schema metadata loaded")
except ImportError:
    SCHEMA_METADATA_AVAILABLE = False
    logger.warning("[database_tools] schema metadata unavailable; advanced hints disabled")

    # 提供回退的空函数
    def find_column_suggestion(*args, **kwargs):
        return None
    def suggest_join_query(*args, **kwargs):
        return None
    def generate_error_with_suggestion(error_msg, *args, **kwargs):
        return error_msg
    def get_table_relationships(*args, **kwargs):
        return {}
    COLUMN_SEMANTICS = {}
    TABLE_RELATIONSHIPS = {}

# 🔧 新增：导入 SQL 校验和修正器
try:
    from ..sql_validator import SQLValidator
    SQL_VALIDATOR_AVAILABLE = True
    logger.debug("[database_tools] sql validator loaded")
except ImportError:
    SQL_VALIDATOR_AVAILABLE = False
    logger.warning("[database_tools] sql validator unavailable")
    SQLValidator = None

# ============================================================================
# 连接上下文存储 (使用 contextvars 支持异步/多线程)
# ============================================================================

_connection_id_ctx: ContextVar[Optional[str]] = ContextVar("connection_id", default=None)
_db_session_ctx: ContextVar[Optional[Any]] = ContextVar("db_session", default=None)
_tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)

# 🔧 新增：跟踪 list_tables 是否被调用
_list_tables_called_ctx: ContextVar[bool] = ContextVar("list_tables_called", default=False)

# 🔧 新增：跟踪原始用户查询（用于地理查询智能推荐）
_user_query_ctx: ContextVar[Optional[str]] = ContextVar("user_query", default=None)

def _set_connection_context(
    connection_id: Optional[str] = None,
    db_session: Optional[Any] = None,
    tenant_id: Optional[str] = None
) -> None:
    """设置连接上下文（用于工具调用）"""
    _connection_id_ctx.set(connection_id)
    _db_session_ctx.set(db_session)
    _tenant_id_ctx.set(tenant_id)
    logger.debug(
        "[CONTEXT_SET] connection_id=%s tenant_id=%s",
        connection_id,
        tenant_id,
    )


def _get_connection_context() -> Tuple[Optional[str], Optional[Any], Optional[str]]:
    """获取连接上下文"""
    connection_id = _connection_id_ctx.get()
    db_session = _db_session_ctx.get()
    tenant_id = _tenant_id_ctx.get()
    logger.debug(
        "[CONTEXT_GET] connection_id=%s tenant_id=%s",
        connection_id,
        tenant_id,
    )
    return (connection_id, db_session, tenant_id)


def _clear_connection_context() -> None:
    """清除连接上下文"""
    _connection_id_ctx.set(None)
    _db_session_ctx.set(None)
    _tenant_id_ctx.set(None)
    logger.debug("[CONTEXT_CLEAR] connection context cleared")


# 🔧 新增：list_tables 调用标志管理函数
def _set_list_tables_called(value: bool = True) -> None:
    """设置 list_tables 已调用标志"""
    _list_tables_called_ctx.set(value)
    logger.debug("[LIST_TABLES_FLAG] set to %s", value)


def _get_list_tables_called() -> bool:
    """获取 list_tables 已调用标志"""
    return _list_tables_called_ctx.get()


def _reset_list_tables_flag() -> None:
    """重置 list_tables 调用标志"""
    _list_tables_called_ctx.set(False)
    logger.debug("[LIST_TABLES_FLAG] reset to False")


# 🔧 新增：用户查询上下文管理函数
def _set_user_query(query: str) -> None:
    """设置当前用户查询"""
    _user_query_ctx.set(query)
    logger.debug(
        "[USER_QUERY] set: %s",
        (query[:100] + "...") if len(query) > 100 else query,
    )


def _get_user_query() -> Optional[str]:
    """获取当前用户查询"""
    return _user_query_ctx.get()


def _clear_user_query() -> None:
    """清除用户查询"""
    _user_query_ctx.set(None)
    logger.debug("[USER_QUERY] cleared")


def set_user_query_context(query: str) -> None:
    """Public wrapper for user query context setup."""
    _set_user_query(query)


def clear_user_query_context() -> None:
    """Public wrapper for user query context cleanup."""
    _clear_user_query()


# 🔧 新增：地理查询智能推荐函数
def _add_geo_table_recommendation(
    tables: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    为地理位置查询添加智能表推荐

    当检测到省份/城市相关查询时，在 addresses 表的描述中
    添加强烈推荐标记，引导 AI 使用正确的表

    Args:
        tables: 增强后的表信息列表（来自 enrich_tables_with_description）

    Returns:
        添加了地理推荐标记的表信息列表
    """
    user_query = _get_user_query()
    if not user_query:
        return tables

    # 地理位置关键词检测
    geo_keywords = [
        "省份", "省", "城市", "市", "地区", "区域",
        "安徽", "浙江", "江苏", "上海", "北京", "广东",
        "分布", "占比", "客户地址", "客户占比"
    ]

    has_geo_query = any(kw in user_query for kw in geo_keywords)

    if not has_geo_query:
        return tables

    logger.debug("[GEO_RECOMMENDATION] 检测到地理位置查询，添加 addresses 表推荐")

    # 为 addresses 表添加强烈推荐标记
    for table in tables:
        table_name = table.get("name", "").lower()
        if table_name in ["addresses", "address", "地址表"]:
            # 添加强烈推荐标记
            original_desc = table.get("description", "")
            table["description"] = (
                f"{original_desc} "
                f"[🔥 强烈推荐: 省份/城市查询的首选表，包含完整地理信息！"
                f"查询省份/城市时必须使用此表，不要使用 users 表！]"
            )
            table["priority"] = "highest"
            table["recommendation_reason"] = "检测到地理位置查询，addresses 表是最佳选择"
            table["geo_query_recommended"] = True
            logger.debug(f"[GEO_RECOMMENDATION] 已为 {table.get('name')} 表添加地理推荐标记")
            break

    return tables


# ============================================================================
# 数据类型序列化工具
# ============================================================================

def sanitize_sql_for_logging(sql: str, max_length: int = 50) -> str:
    """
    脱敏 SQL 用于日志记录

    防止日志中暴露敏感信息，如：
    - 字符串字面量中的敏感数据
    - 数字（可能是 ID、金额等）
    - UUID/哈希值

    Args:
        sql: 原始 SQL 查询
        max_length: 最大长度（截断）

    Returns:
        脱敏后的 SQL 字符串

    Examples:
        >>> sanitize_sql_for_logging("SELECT * FROM users WHERE name = 'John' AND id = 123")
        "SELECT * FROM users WHERE name = '' AND id = ***"

        >>> sanitize_sql_for_logging("INSERT INTO logs (data) VALUES ('sensitive_token_abc123')")
        "INSERT INTO logs (data) VALUES ('')"
    """
    import re

    # 移除字符串字面量中的内容
    sanitized = re.sub(r"'[^']*'", "''", sql)

    # 替换数字为 ***
    sanitized = re.sub(r'\b\d+\b', '***', sanitized)

    # 替换 UUID/哈希值模式（长十六进制字符串）
    sanitized = re.sub(r'\b[a-f0-9]{8,}\b', '***', sanitized, flags=re.IGNORECASE)

    # 截断长度
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def _serialize_value(value: Any) -> Any:
    """
    将数据库值转换为 JSON 可序列化的格式

    处理 PostgreSQL 复杂数据类型:
    - Decimal -> float
    - datetime/date -> ISO 格式字符串
    - UUID -> 字符串
    - NaN/None -> null

    Args:
        value: 数据库返回的原始值

    Returns:
        JSON 可序列化的值
    """
    import decimal
    import uuid
    from datetime import date, datetime, time
    import pandas as pd

    if value is None:
        return None
    elif isinstance(value, decimal.Decimal):
        # 保留精度，转换为 float
        return float(value)
    elif isinstance(value, (datetime, date, time)):
        # 转换为 ISO 格式字符串
        return value.isoformat()
    elif isinstance(value, uuid.UUID):
        # UUID 转字符串
        return str(value)
    elif isinstance(value, bytes):
        # 字节数组转 base64 字符串
        import base64
        return base64.b64encode(value).decode('utf-8')
    elif pd.isna(value):
        # pandas NaN 转为 None
        return None
    # 其他类型直接返回
    return value


def _serialize_row(row: tuple, columns: list = None) -> list:
    """
    序列化单行数据

    Args:
        row: 数据库行数据（元组）
        columns: 列名列表（可选）

    Returns:
        序列化后的列表
    """
    return [_serialize_value(v) for v in row]


def _serialize_rows(rows: list, columns: list = None) -> list:
    """
    序列化多行数据

    Args:
        rows: 数据库行数据列表
        columns: 列名列表（可选）

    Returns:
        序列化后的二维列表
    """
    return [_serialize_row(row, columns) for row in rows]


# ============================================================================
# 缓存管理
# ============================================================================

class SimpleCache:
    """线程安全的内存缓存，支持统计和 TTL 过期"""

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
        self._lock = threading.RLock()  # 使用可重入锁保护并发访问

    def get(self, key: str) -> Optional[Any]:
        """获取缓存（线程安全）"""
        with self._lock:
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
        """设置缓存（线程安全）"""
        with self._lock:
            expire_time = time.time() + self.ttl
            self._cache[key] = (value, expire_time)
            self._sets += 1

    def clear(self) -> None:
        """清空缓存（线程安全）"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._sets = 0

    def has(self, key: str) -> bool:
        """检查缓存是否存在且未过期（线程安全）"""
        return self.get(key) is not None

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计（线程安全）"""
        with self._lock:
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

    def delete(self, key: str) -> bool:
        """删除指定缓存（线程安全）"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False


class TenantAwareCache:
    """
    租户隔离的内存缓存，防止跨租户数据泄露

    每个租户的数据完全隔离，缓存键自动包含租户 ID。
    """

    def __init__(self, ttl: int = 300, name: str = "tenant_cache"):
        """
        初始化租户隔离缓存

        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
            name: 缓存名称（用于统计）
        """
        self._cache: Dict[str, Dict[str, tuple]] = {}  # {tenant_id: {key: (value, expire_time)}}
        self.ttl = ttl
        self.name = name
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._lock = threading.RLock()

    def _make_tenant_key(self, tenant_id: str, key: str) -> str:
        """生成租户特定的缓存键"""
        return f"{tenant_id}:{key}"

    def get(self, tenant_id: str, key: str) -> Optional[Any]:
        """
        获取缓存（线程安全 + 租户隔离）

        Args:
            tenant_id: 租户 ID
            key: 缓存键
        """
        with self._lock:
            tenant_cache = self._cache.get(tenant_id, {})
            if key in tenant_cache:
                value, expire_time = tenant_cache[key]
                if time.time() < expire_time:
                    self._hits += 1
                    return value
                else:
                    # 缓存过期，删除
                    del tenant_cache[key]
            self._misses += 1
            return None

    def set(self, tenant_id: str, key: str, value: Any) -> None:
        """
        设置缓存（线程安全 + 租户隔离）

        Args:
            tenant_id: 租户 ID
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            if tenant_id not in self._cache:
                self._cache[tenant_id] = {}
            expire_time = time.time() + self.ttl
            self._cache[tenant_id][key] = (value, expire_time)
            self._sets += 1

    def clear_tenant(self, tenant_id: str) -> None:
        """
        清除特定租户的缓存（线程安全）

        Args:
            tenant_id: 要清除的租户 ID
        """
        with self._lock:
            self._cache.pop(tenant_id, None)

    def clear(self) -> None:
        """清空所有缓存（线程安全）"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._sets = 0

    def has(self, tenant_id: str, key: str) -> bool:
        """检查缓存是否存在且未过期（线程安全 + 租户隔离）"""
        return self.get(tenant_id, key) is not None

    def get_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取缓存统计

        Args:
            tenant_id: 如果提供，只返回该租户的统计；否则返回全局统计
        """
        with self._lock:
            if tenant_id:
                tenant_cache = self._cache.get(tenant_id, {})
                return {
                    "name": f"{self.name}[{tenant_id}]",
                    "size": len(tenant_cache),
                    "tenant_id": tenant_id
                }
            else:
                total_requests = self._hits + self._misses
                hit_rate = self._hits / total_requests if total_requests > 0 else 0
                return {
                    "name": self.name,
                    "tenants": len(self._cache),
                    "total_size": sum(len(cache) for cache in self._cache.values()),
                    "hits": self._hits,
                    "misses": self._misses,
                    "sets": self._sets,
                    "hit_rate": hit_rate,
                    "ttl": self.ttl
                }

    def delete(self, tenant_id: str, key: str) -> bool:
        """删除指定租户的指定缓存（线程安全）"""
        with self._lock:
            tenant_cache = self._cache.get(tenant_id)
            if tenant_cache and key in tenant_cache:
                del tenant_cache[key]
                return True
            return False


# 全局缓存实例 (使用租户隔离缓存)
_schema_cache = TenantAwareCache(ttl=600, name="schema_cache")  # Schema 缓存 10 分钟
_query_cache = TenantAwareCache(ttl=300, name="query_cache")    # 查询结果缓存 5 分钟 (延长 TTL)


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
    """
    生成缓存键（自动包含租户 ID）

    注意：租户隔离现在由 TenantAwareCache 处理，
    这个函数只负责生成内容哈希键
    """
    # 如果参数包含 SQL，先标准化
    if args and 'select' in str(args[0]).lower():
        args = (_normalize_sql(args[0]),) + args[1:]

    key_str = json.dumps([args, kwargs], sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cache_key_with_tenant() -> str:
    """
    生成包含租户信息的缓存键前缀

    从当前上下文获取 tenant_id，生成唯一键
    """
    _, _, tenant_id = _get_connection_context()
    return tenant_id or "default_tenant"


def get_cache_stats() -> Dict[str, Any]:
    """获取所有缓存统计信息"""
    return {
        "schema_cache": _schema_cache.get_stats(),
        "query_cache": _query_cache.get_stats()
    }


def _import_data_source_connection_model():
    """导入后端 DataSourceConnection 模型（按需）。"""
    models_module = import_backend_module("app.data.models")
    model = getattr(models_module, "DataSourceConnection", None)
    if model is None:
        raise ImportError("DataSourceConnection not found in app.data.models")
    return model


def _import_data_source_service():
    """导入后端 data_source_service（按需）。"""
    service_module = import_backend_module("app.domains.data_sources.service")
    service = getattr(service_module, "data_source_service", None)
    if service is None:
        raise ImportError("data_source_service not found in app.domains.data_sources.service")
    return service

# ============================================================================
# 数据库连接管理
# ============================================================================

def get_database_url(
    connection_id: Optional[str] = None
) -> Tuple[str, Optional[Any]]:
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

    default_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/data_agent",
    )

    # 如果没有提供 connection_id，尝试获取租户的默认活跃数据源
    if not connection_id:
        if db_session and tenant_id:
            try:
                DataSourceConnection = _import_data_source_connection_model()

                # 查询租户的第一个活跃数据源
                connection = db_session.query(DataSourceConnection).filter(
                    DataSourceConnection.tenant_id == tenant_id,
                    DataSourceConnection.status == "active"
                ).first()

                if connection:
                    connection_id = str(connection.id)
                    logger.debug(f"自动获取租户 {tenant_id} 的默认数据源: {connection.name} (ID: {connection_id})")
                else:
                    logger.warning(f"租户 {tenant_id} 没有配置活跃数据源，使用系统元数据库")
                    return default_url, None
            except ImportError as e:
                logger.error(f"Failed to import DataSourceConnection model: {e}")
                return default_url, None
            except Exception as e:
                logger.error(f"Failed to query default data source: {e}")
                return default_url, None
        else:
            # 没有数据库会话，使用环境变量中的默认数据库
            return default_url, None

    # 从这里开始有 connection_id
    if not db_session or not tenant_id:
        logger.warning(
            f"connection_id provided but db_session/tenant_id not available. "
            f"Using default database. connection_id={connection_id}"
        )
        return default_url, None

    try:
        data_source_service = _import_data_source_service()
        connection_info = run_async_sync(
            data_source_service.get_data_source_connection_info(
                connection_id=connection_id,
                tenant_id=tenant_id,
                db=db_session,
            )
        )
        logger.debug(
            "Retrieved connection_info: connection_id=%s tenant_id=%s type=%s",
            connection_id,
            tenant_id,
            getattr(connection_info, "connection_type", ""),
        )

        # 根据数据源类型返回不同的连接信息
        if connection_info.connection_type == "excel":
            # Excel 文件：返回特殊标记和文件信息
            logger.debug(f"Using Excel data source: {connection_info.file_path}, sheets={connection_info.sheets}")
            return f"excel://{connection_info.file_path}", connection_info
        else:
            # 数据库：返回解密后的连接字符串
            logger.debug(f"Using database data source: type={connection_info.connection_type}")
            return connection_info.connection_string, connection_info

    except ImportError as e:
        logger.error(f"Failed to import data_source_service: {e}")
        return default_url, None
    except Exception as e:
        logger.error(f"Failed to get connection info for {connection_id}: {e}")
        return default_url, None


def _is_excel_connection(database_url: str) -> bool:
    """检查是否是 Excel 连接"""
    return database_url.startswith("excel://")


def _infer_db_type_from_url(database_url: str) -> str:
    """从连接方式推断数据库类型"""
    if not database_url:
        return ""
    url = database_url.lower()
    if url.startswith("excel://") or url.startswith("duckdb://"):
        return "duckdb"
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return "postgres"
    if url.startswith("mysql://") or url.startswith("mariadb://"):
        return "mysql"
    if url.startswith("sqlite://") or url.startswith("sqlite3://"):
        return "sqlite"
    return ""


def _has_subquery(query: str) -> bool:
    """
    检测 SQL 查询是否包含子查询

    Excel 数据源不支持子查询，需要在执行前检测并拒绝。

    Args:
        query: SQL 查询语句

    Returns:
        True 如果包含子查询，False 否则
    """
    import re
    query_upper = query.upper()

    # 检测 IN (SELECT ...), EXISTS (SELECT ...) 等子查询模式
    subquery_patterns = [
        r'\bIN\s*\(\s*SELECT\s',
        r'\bEXISTS\s*\(\s*SELECT\s',
        r'\bNOT\s+IN\s*\(\s*SELECT\s',
        r'\b=\s*\(\s*SELECT\s',
        r'\b!=\s*\(\s*SELECT\s',
        r'\b<>\s*\(\s*SELECT\s',
        r'\bANY\s*\(\s*SELECT\s',
        r'\bALL\s*\(\s*SELECT\s',
    ]

    for pattern in subquery_patterns:
        if re.search(pattern, query_upper):
            logger.debug(f"[子查询检测] 检测到子查询模式: {pattern}")
            return True

    return False


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
        logger.debug(f"Creating SQLite connection: {db_path}")
        return sqlite3.connect(db_path)
    else:
        # PostgreSQL 连接
        import psycopg2
        logger.debug("Creating PostgreSQL connection")
        return psycopg2.connect(database_url)


def _get_excel_file_path(database_url: str) -> str:
    """从 Excel 连接 URL 中提取文件路径"""
    return database_url[8:]  # 去掉 "excel://" 前缀
def _get_excel_engine(file_path: str) -> str:
    """Choose pandas engine by Excel extension."""
    return "xlrd" if str(file_path).lower().endswith(".xls") else "openpyxl"


def _open_excel_file(file_path: str):
    """Open Excel file with extension-aware engine."""
    import pandas as pd
    return pd.ExcelFile(file_path, engine=_get_excel_engine(file_path))


def _read_excel_file(file_path: str, **kwargs):
    """Read Excel with extension-aware engine."""
    import pandas as pd
    return pd.read_excel(file_path, engine=_get_excel_engine(file_path), **kwargs)


# ============================================================================
# 表名映射工具（Excel 工作表名映射）
# ============================================================================

# 备用工作表名称配置
SHEET_ALTERNATIVES = {
    "Products": ["产品表", "商品表", "products", "Products"],
    "Customers": ["customers", "Customers", "用户表", "客户表"],
    "Orders": ["订单表", "orders", "Orders"],
    "Categories": ["分类表", "categories", "Categories"],
    "OrderDetails": ["订单明细", "order_details", "OrderDetails", "订单详情"],
}


def _sheet_exists(file_path: str, sheet_name: str) -> bool:
    """验证工作表是否存在于 Excel 文件中

    Args:
        file_path: Excel 文件路径
        sheet_name: 工作表名称

    Returns:
        工作表是否存在
    """
    try:
        import pandas as pd
        xl = pd.ExcelFile(file_path)
        return sheet_name in xl.sheet_names
    except Exception as e:
        logger.warning(f"验证工作表失败: {e}")
        return False


@lru_cache(maxsize=32)
def _get_excel_sheet_mapping_cached(english_table: str) -> Optional[str]:
    """缓存版本的表名映射（不含 file_path 参数，避免缓存键污染）

    从语义层 YAML 文件读取 excel_sheet 配置，实现英文表名到中文工作表名的映射。
    当主映射的工作表不存在时，自动尝试备用名称。

    🔧 修复：添加大小写不敏感查找，解决 "orders" 无法匹配 "Orders" 的问题

    Args:
        english_table: 英文表名（如 "Orders", "Products", "Customers"）

    Returns:
        映射后的工作表名，如果未找到映射则返回 None

    示例:
        _get_excel_sheet_mapping_cached("Orders") -> "订单表"
        _get_excel_sheet_mapping_cached("orders") -> "订单表"  # 🔧 大小写不敏感
        _get_excel_sheet_mapping_cached("Products") -> "商品表" 或 "产品表"
        _get_excel_sheet_mapping_cached("Customers") -> "customers"
    """
    try:
        # 动态导入 SchemaLoader，避免循环导入
        try:
            from ..schema_pruning import SchemaLoader
        except ImportError:
            # 兼容本地直接运行（非包方式）
            from schema_pruning import SchemaLoader

        loader = SchemaLoader()
        _, _, yaml_mappings = loader.load_from_yaml()

        # 🔧 修复 1: 从 YAML 获取主映射（添加大小写不敏感查找）
        primary = yaml_mappings.get(english_table)
        if not primary:
            # 尝试大小写不敏感匹配
            for key, value in yaml_mappings.items():
                if key.lower() == english_table.lower():
                    primary = value
                    logger.debug(f"表名映射（大小写不敏感）: {english_table} -> {key} -> {primary}")
                    break

        # 🔧 修复 1: 构建候选列表（主映射 + 备用名称，支持大小写不敏感）
        candidates = [primary] if primary else []
        alt = SHEET_ALTERNATIVES.get(english_table, [])
        if not alt:
            # 尝试大小写不敏感匹配 SHEET_ALTERNATIVES
            for key, value in SHEET_ALTERNATIVES.items():
                if key.lower() == english_table.lower():
                    alt = value
                    logger.debug(f"SHEET_ALTERNATIVES 映射（大小写不敏感）: {english_table} -> {key} -> {alt}")
                    break
        candidates.extend(alt)

        # 3. 去重并保持顺序
        seen = set()
        unique_candidates = [x for x in candidates if x and x not in seen and not seen.add(x)]

        # 4. 返回主映射或第一个候选（缓存版本不验证工作表存在性）
        return primary if primary else (unique_candidates[0] if unique_candidates else None)

    except Exception as e:
        logger.warning(f"获取表名映射失败: {e}，使用原表名")
        return None


def _clear_excel_sheet_mapping_cache() -> None:
    """清除表名映射缓存
    
    当 YAML 配置文件更新时，需要调用此函数清除缓存。
    也可以在映射验证失败时自动调用，以获取最新的配置。
    """
    _get_excel_sheet_mapping_cached.cache_clear()
    logger.debug("已清除 Excel 表名映射缓存")


def _get_excel_sheet_mapping(english_table: str, file_path: str = None) -> Optional[str]:
    """将英文表名映射到 Excel 工作表名（支持备用名称回退）

    从语义层 YAML 文件读取 excel_sheet 配置，实现英文表名到中文工作表名的映射。
    当主映射的工作表不存在时，自动尝试备用名称。

    🔧 修复 2: 分离缓存逻辑，避免 file_path 参数污染 LRU 缓存
    🔧 修复 5: 验证失败时清除缓存并重试，确保获取最新配置

    Args:
        english_table: 英文表名（如 "Orders", "Products", "Customers"）
        file_path: Excel 文件路径（可选，用于验证工作表存在性）

    Returns:
        映射后的工作表名，如果未找到映射则返回 None

    示例:
        _get_excel_sheet_mapping("Orders", "path/to/file.xlsx") -> "orders"
        _get_excel_sheet_mapping("orders", "path/to/file.xlsx") -> "orders"  # 🔧 大小写不敏感
        _get_excel_sheet_mapping("Products", "path/to/file.xlsx") -> "products"
    """
    def try_mapping(clear_cache: bool = False) -> Optional[str]:
        """尝试获取映射（内部函数，支持清除缓存重试）"""
        if clear_cache:
            _clear_excel_sheet_mapping_cache()
        
        # 1. 先调用缓存版本获取主映射
        primary = _get_excel_sheet_mapping_cached(english_table)

        if primary:
            # 2. 如果有 file_path，验证工作表存在性并支持备用名称回退
            if file_path:
                # 构建候选列表（主映射 + 备用名称）
                candidates = [primary]
                alt = SHEET_ALTERNATIVES.get(english_table, [])
                if not alt:
                    # 尝试大小写不敏感匹配 SHEET_ALTERNATIVES
                    for key, value in SHEET_ALTERNATIVES.items():
                        if key.lower() == english_table.lower():
                            alt = value
                            break
                candidates.extend(alt)

                # 去重并保持顺序
                seen = set()
                unique_candidates = [x for x in candidates if x and x not in seen and not seen.add(x)]

                # 返回第一个存在的工作表
                for name in unique_candidates:
                    if _sheet_exists(file_path, name):
                        logger.debug(f"表名映射（验证存在）: {english_table} -> {name}")
                        return name

                # 所有候选都不存在
                return None

            # 3. 没有 file_path，直接返回主映射
            return primary

        return None
    
    try:
        # 首次尝试
        result = try_mapping(clear_cache=False)
        
        # 如果验证失败且有 file_path，清除缓存后重试一次
        if result is None and file_path:
            logger.debug(f"表名映射验证失败，清除缓存后重试: {english_table}")
            result = try_mapping(clear_cache=True)
        
        return result

    except Exception as e:
        logger.warning(f"获取表名映射失败: {e}，使用原表名")
        return None


# ============================================================================
# 省份/城市简称映射（智能模糊匹配）
# ============================================================================

# 省份简称到完整名称的映射表
PROVINCE_ALIAS_MAP: dict[str, str] = {
    # 华北地区
    '北京': '北京市', '天津': '天津市', '河北': '河北省', '山西': '山西省', '内蒙古': '内蒙古自治区',
    # 华东地区
    '上海': '上海市', '江苏': '江苏省', '浙江': '浙江省', '安徽': '安徽省',
    '福建': '福建省', '江西': '江西省', '山东': '山东省',
    # 华南地区
    '广东': '广东省', '广西': '广西壮族自治区', '海南': '海南省',
    # 华中地区
    '河南': '河南省', '湖北': '湖北省', '湖南': '湖南省',
    # 西南地区
    '重庆': '重庆市', '四川': '四川省', '贵州': '贵州省', '云南': '云南省', '西藏': '西藏自治区',
    # 西北地区
    '陕西': '陕西省', '甘肃': '甘肃省', '青海': '青海省', '宁夏': '宁夏回族自治区', '新疆': '新疆维吾尔自治区',
    # 东北地区
    '辽宁': '辽宁省', '吉林': '吉林省', '黑龙江': '黑龙江省',
    # 特殊映射：副省级城市/计划单列市 → 所属省份
    '深圳': '广东省', '广州': '广东省', '东莞': '广东省', '佛山': '广东省',
    '杭州': '浙江省', '宁波': '浙江省', '南京': '江苏省', '苏州': '江苏省',
    '成都': '四川省', '武汉': '湖北省', '西安': '陕西省', '青岛': '山东省',
}

# 城市别名的额外映射（可能有多个完整名称的城市）
CITY_ALIAS_MAP: dict[str, list[str]] = {
    # 可以扩展城市级别的别名映射
}


def _expand_province_condition(value: str, col_name: str) -> list[str]:
    """
    扩展省份/城市查询条件，支持简称匹配

    当用户查询使用简称（如"安徽"）时，返回可能的完整名称列表（如["安徽省"]）。

    Args:
        value: 查询值（可能是简称）
        col_name: 列名（用于判断是省份还是城市）

    Returns:
        可能的完整名称列表，包括原始值和映射后的完整名称

    Examples:
        >>> _expand_province_condition("安徽", "province")
        ["安徽", "安徽省"]

        >>> _expand_province_condition("安徽省", "province")
        ["安徽省"]

        >>> _expand_province_condition("深圳", "province")
        ["深圳", "广东省"]
    """
    result = [value]

    # 判断是省份列还是城市列
    col_lower = col_name.lower()
    is_province_col = 'province' in col_lower or '省' in col_name
    is_city_col = 'city' in col_lower or '市' in col_name or '地区' in col_name

    # 省份映射
    if is_province_col and value in PROVINCE_ALIAS_MAP:
        full_name = PROVINCE_ALIAS_MAP[value]
        if full_name not in result:
            result.append(full_name)

    # 城市映射（可以扩展）
    if is_city_col and value in CITY_ALIAS_MAP:
        for alias in CITY_ALIAS_MAP[value]:
            if alias not in result:
                result.append(alias)

    return result


# ============================================================================
# Excel 查询工具
# ============================================================================

def _find_sheets_with_column(file_path: str, column_name: str) -> list[str]:
    """
    在 Excel 文件的所有工作表中查找包含指定列的工作表

    Args:
        file_path: Excel 文件路径
        column_name: 要查找的列名（不区分大小写）

    Returns:
        包含该列的工作表名称列表
    """
    import pandas as pd

    try:
        excel_file = _open_excel_file(file_path)
        column_lower = column_name.lower()

        matching_sheets = []
        for sheet in excel_file.sheet_names:
            try:
                df_sample = _read_excel_file(file_path, sheet_name=sheet, nrows=0)
                columns_lower = [col.lower() for col in df_sample.columns]
                if column_lower in columns_lower:
                    matching_sheets.append(sheet)
            except Exception:
                continue

        return matching_sheets
    except Exception as e:
        logger.warning(f"查找工作表时出错: {e}")
        return []


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
        logger.debug(f"Excel 查询开始: query={query}, file_path={file_path}, sheet_name={sheet_name}")

        # 读取 Excel 文件
        if sheet_name:
            df = _read_excel_file(file_path, sheet_name=sheet_name)
        else:
            # 读取第一个工作表
            df = _read_excel_file(file_path)
            sheet_name = "Sheet1"

        logger.debug(f"Excel 文件已读取: shape={df.shape}, columns={list(df.columns)}")

        logger.debug(f"Excel file loaded: {file_path}, sheet: {sheet_name}, shape: {df.shape}")

        # 🔧 预检查：验证 WHERE 条件中的列是否存在（增强版：智能建议）
        import re
        query_upper = query.upper()
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+GROUP|\s+ORDER|\s+LIMIT|;|$)', query_upper)
        if where_match:
            where_clause = where_match.group(1).strip()
            # 提取 WHERE 中的列名（匹配 col =, col >, col <, col LIKE 等模式）
            col_matches = re.findall(r'(\w+)\s*(?:=|>=|<=|<>|>|<|LIKE)\s', where_clause, re.IGNORECASE)
            available_cols_lower = {c.lower(): c for c in df.columns}
            for col in col_matches:
                col_lower = col.lower()
                if col_lower not in available_cols_lower:
                    available_cols = ", ".join(f'"{c}"' for c in df.columns)
                    logger.error(f"列 '{col}' 不存在于工作表 '{sheet_name}'")

                    # 🆕 增强版智能建议（修复点 4）
                    suggestion_parts = []

                    # 1. 识别常见跨表字段
                    location_fields = ["province", "city", "district", "address", "region"]
                    product_fields = ["product_name", "category_name", "product_id"]
                    user_fields = ["user_name", "customer_name", "email"]

                    if col_lower in location_fields:
                        # 🆕 智能查找包含该列的其他工作表
                        suggested_sheets = _find_sheets_with_column(file_path, col)

                        suggestion_text = (
                            f"🚨 列 '{col}' 不在工作表 '{sheet_name}' 中！\n\n"
                            f"💡 **分析**: '{col}' 是地理位置字段，通常在地址/区域相关的工作表中\n\n"
                        )

                        if suggested_sheets:
                            sheets_formatted = ', '.join(f'"{s}"' for s in suggested_sheets)
                            suggestion_text += (
                                f"🎯 **发现**: '{col}' 字段存在于以下工作表: {sheets_formatted}\n\n"
                                f"🔧 **建议**: 直接查询包含该字段的工作表：\n\n"
                                f"```sql\n"
                                f"SELECT {col}, COUNT(*) as count\n"
                                f'FROM "{suggested_sheets[0]}"\n'
                                f"WHERE {col} = '目标值'\n"
                                f"GROUP BY {col}\n"
                                f"```\n\n"
                            )
                        else:
                            suggestion_text += (
                                f"⚠️ **未找到**: 在其他工作表中也未找到 '{col}' 字段\n\n"
                                f"🔧 **操作步骤**:\n"
                                f"1. 调用 list_tables() 查看所有可用工作表\n"
                                f"2. 调用 get_schema() 查看各工作表的列信息\n"
                                f"3. 确认正确的列名\n\n"
                            )

                        suggestion_text += (
                            f"⚠️ **重要提示**: Excel 数据源不支持 JOIN 和子查询\n"
                            f"永远不要尝试跨表查询，必须直接查询包含目标字段的工作表\n\n"
                            f"📋 当前工作表可用列: {available_cols}"
                        )

                        suggestion_parts.append(suggestion_text)
                    elif col_lower in product_fields:
                        suggestion_parts.append(
                            f"🚨 列 '{col}' 不在工作表 '{sheet_name}' 中！\n\n"
                            f"💡 **分析**: '{col}' 是产品相关字段，通常在产品/商品工作表中\n\n"
                            f"⚠️ **重要提示**: Excel 数据源不支持 JOIN 查询\n"
                            f"如需查询产品信息，请直接查询产品工作表\n\n"
                            f"🔧 **操作步骤**:\n"
                            f"1. 调用 list_tables() 查看所有可用工作表\n"
                            f"2. 查找产品相关的工作表（如：Products、产品表、商品表等）\n"
                            f"3. 对该工作表执行查询\n\n"
                            f"📋 当前工作表可用列: {available_cols}"
                        )
                    elif col_lower in user_fields:
                        suggestion_parts.append(
                            f"🚨 列 '{col}' 不在工作表 '{sheet_name}' 中！\n\n"
                            f"💡 **分析**: '{col}' 是用户/客户字段，可能需要查询其他工作表\n\n"
                            f"⚠️ **重要提示**: Excel 数据源不支持 JOIN 查询\n\n"
                            f"🔧 **操作步骤**:\n"
                            f"1. 调用 list_tables() 查看所有可用工作表\n"
                            f"2. 查找用户/客户相关的工作表\n"
                            f"3. 对该工作表执行查询\n\n"
                            f"📋 当前工作表可用列: {available_cols}"
                        )
                    else:
                        # 使用模糊匹配查找相似列名
                        similar_cols = [c for c in df.columns if col_lower in c.lower() or c.lower() in col_lower]
                        similar_text = ""
                        if similar_cols:
                            similar_cols_formatted = ', '.join(f'"{c}"' for c in similar_cols[:3])
                            similar_text = f"💡 您是否想查询: {similar_cols_formatted}?\n\n"

                        suggestion_parts.append(
                            f"🚨 列 '{col}' 不存在于工作表 '{sheet_name}'！\n\n"
                            f"{similar_text}"
                            f"⚠️ **重要提示**: Excel 数据源不支持 JOIN 查询\n"
                            f"如需跨表查询，请分别查询各个工作表后手动合并结果\n\n"
                            f"📋 当前工作表可用列: {available_cols}"
                        )

                    suggestion_text = "\n".join(suggestion_parts)

                    return json.dumps({
                        "error": f"列 '{col}' 不存在于工作表 '{sheet_name}'",
                        "error_type": "column_not_found",
                        "data_source": "excel",
                        "missing_column": col,
                        "current_sheet": sheet_name,
                        "available_columns": list(df.columns),
                        "suggestion": suggestion_text
                    }, ensure_ascii=False)

        # 简单的 SQL 解析和转换
        result_df = _parse_sql_to_pandas(query, df)

        logger.debug(f"_parse_sql_to_pandas 返回: shape={result_df.shape}, columns={list(result_df.columns)}")

        # 转换为结果格式
        columns = result_df.columns.tolist()
        rows = result_df.values.tolist()

        # 🔧 使用序列化函数处理所有数据类型
        rows = _serialize_rows(rows, columns)

        result = {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "success": True,
            "data_source": "excel",
            "sheet_name": sheet_name
        }

        logger.debug(f"Excel query executed: {len(rows)} rows returned")
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
    SQL 到 pandas 转换（支持聚合查询）

    支持的 SQL 语法:
    - SELECT col1, col2 FROM table
    - SELECT * FROM table
    - SELECT ... FROM table WHERE col = value
    - SELECT ... FROM table WHERE col LIKE value
    - SELECT ... FROM table ORDER BY col [ASC|DESC]
    - SELECT ... FROM table LIMIT n
    - SELECT ... FROM table GROUP BY col  # 🆕 新增
    - SELECT SUM(col), COUNT(col) ... GROUP BY col  # 🆕 新增
    - SELECT DATE_FORMAT(col, format) ... GROUP BY col  # 🆕 新增
    - SELECT YEAR(col), MONTH(col) ... GROUP BY col  # 🆕 新增

    Args:
        query: SQL 查询语句
        df: pandas DataFrame

    Returns:
        处理后的 DataFrame（支持聚合结果）
    """
    import re
    import pandas as pd

    # 调试日志
    logger.debug(f"Excel SQL 解析开始: query={query}")
    logger.debug(f"DataFrame 形状: {df.shape}, 列: {list(df.columns)}")

    # 保存原始查询（大小写敏感的版本用于别名提取）
    query_original = query
    query_upper = query.upper().strip()
    result_df = df.copy()

    # ========================================
    # 🆕 检测聚合函数和 GROUP BY
    # ========================================

    # 提取完整的 SELECT 子句（使用原始大小写）
    select_match = re.search(r'SELECT\s+(.+?)\s+FROM', query_original, re.IGNORECASE)
    select_clause = select_match.group(1).strip() if select_match else '*'

    # 检测 GROUP BY
    group_match = re.search(r'GROUP\s+BY\s+(.+?)(?:\s+ORDER\s+BY|\s+LIMIT|;|$)', query_upper)
    has_group_by = group_match is not None

    # 检测 SELECT 中的聚合函数
    has_aggregation = bool(re.search(
        r'(SUM|COUNT|AVG|MAX|MIN)\s*\(\s*\*|\s*\w+\s*\)',
        select_clause, re.IGNORECASE
    ))

    # ========================================
    # 🆕 解析 SELECT 列（支持别名和聚合函数）
    # ========================================

    def parse_select_columns(select_str: str) -> list:
        """解析 SELECT 子句，返回列定义列表"""
        columns = []
        # 分割逗号（注意括号内的逗号不应分割）
        parts = []
        current = []
        paren_level = 0
        for char in select_str:
            if char == '(':
                paren_level += 1
                current.append(char)
            elif char == ')':
                paren_level -= 1
                current.append(char)
            elif char == ',' and paren_level == 0:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            parts.append(''.join(current).strip())

        for part in parts:
            col_def = {
                'raw': part,
                'alias': None,
                'func': None,
                'arg': None,
                'is_aggregation': False,
                'is_time_func': False,
                'time_format': None
            }

            part_upper = part.upper()

            # 检测 AS 别名
            alias_match = re.search(r'\s+AS\s+["\']?(\w+)["\']?$', part, re.IGNORECASE)
            if alias_match:
                col_def['alias'] = alias_match.group(1)

            # 检测聚合函数
            agg_match = re.search(r'(SUM|COUNT|AVG|MAX|MIN)\s*\(\s*(\*|\w+)\s*\)', part_upper)
            if agg_match:
                col_def['func'] = agg_match.group(1)
                col_def['arg'] = agg_match.group(2)
                col_def['is_aggregation'] = True

            # 检测时间函数 DATE_FORMAT(col, 'format')
            date_format_match = re.search(r'DATE_FORMAT\s*\(\s*(\w+)\s*,\s*["\']([^"\']+)["\']\s*\)', part, re.IGNORECASE)
            if date_format_match:
                col_def['func'] = 'DATE_FORMAT'
                col_def['arg'] = date_format_match.group(1)
                col_def['time_format'] = date_format_match.group(2)
                col_def['is_time_func'] = True
                if not col_def['alias']:
                    col_def['alias'] = f"{date_format_match.group(1)}_formatted"

            # 检测时间函数 YEAR(col), MONTH(col)
            year_month_match = re.search(r'(YEAR|MONTH)\s*\(\s*(\w+)\s*\)', part_upper)
            if year_month_match:
                col_def['func'] = year_month_match.group(1)
                col_def['arg'] = year_month_match.group(2)
                col_def['is_time_func'] = True
                if not col_def['alias']:
                    col_def['alias'] = f"{year_month_match.group(2)}_{year_month_match.group(1).lower()}"

            # 普通列名
            if not col_def['func'] and not col_def['is_time_func']:
                col_name = part.strip().strip('"').strip("'")
                col_def['arg'] = col_name
                col_def['alias'] = col_name

            columns.append(col_def)

        return columns

    select_columns = parse_select_columns(select_clause)

    # ========================================
    # 🆕 应用 WHERE 条件（在 GROUP BY 之前）
    # ========================================
    where_match = re.search(r'WHERE\s+(.+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|;|$)', query_upper)
    if where_match:
        where_clause = where_match.group(1).strip()
        result_df = _apply_where_clause(result_df, where_clause)
    
    # ========================================
    # 🆕 处理 GROUP BY 和聚合
    # ========================================
    if has_group_by or has_aggregation:
        # 提取 GROUP BY 列
        if group_match:
            group_by_str = group_match.group(1).strip()
            group_columns = [col.strip().lower() for col in group_by_str.split(',')]
        else:
            group_columns = []
        
        # 构建分组键（支持时间函数和别名）
        group_by_keys = []
        group_by_display_names = []
        
        for col_def in select_columns:
            # 🔧 修复：支持按别名分组（如 GROUP BY month，其中 month 是别名）
            alias_lower = (col_def['alias'] or '').lower()
            arg_lower = (col_def['arg'] or '').lower()
            
            # 检查是否是分组列（通过别名或参数名匹配）
            is_group_column = (
                col_def['is_time_func'] or  # 时间函数总是分组列
                (not col_def['is_aggregation'] and col_def['arg'])  # 非聚合列可能是分组列
            )
            
            should_include = False
            if is_group_column:
                if alias_lower in group_columns:
                    # 按别名分组
                    should_include = True
                elif arg_lower in group_columns:
                    # 按原始列名分组
                    should_include = True
                elif not group_columns:
                    # 没有 GROUP BY 子句，默认所有非聚合列都是分组列
                    should_include = True
            
            if should_include:
                group_by_keys.append(col_def)
                group_by_display_names.append(col_def['alias'] or col_def['arg'])
        
        # 如果没有明确的分组列，使用 GROUP BY 子句中的列
        if not group_by_keys and group_columns:
            for group_col in group_columns:
                # 匹配实际列名
                actual_columns = {col.lower(): col for col in result_df.columns}
                if group_col in actual_columns:
                    group_by_keys.append({
                        'arg': actual_columns[group_col],
                        'alias': actual_columns[group_col],
                        'func': None,
                        'is_time_func': False
                    })
                    group_by_display_names.append(actual_columns[group_col])
        
        # 应用时间函数转换（如果使用了 DATE_FORMAT、YEAR、MONTH）
        temp_df = result_df.copy()
        for col_def in group_by_keys:
            if col_def.get('is_time_func'):
                original_col = col_def['arg']
                alias = col_def['alias']
                func = col_def.get('func')
                
                if original_col not in temp_df.columns:
                    # 尝试大小写不敏感匹配
                    actual_columns = {col.lower(): col for col in temp_df.columns}
                    original_col = actual_columns.get(original_col.lower(), original_col)
                
                if original_col in temp_df.columns:
                    # 确保是日期类型
                    try:
                        temp_df[original_col] = pd.to_datetime(temp_df[original_col], errors='coerce')
                    except:
                        pass
                    
                    if func == 'DATE_FORMAT':
                        fmt = col_def.get('time_format', '%Y-%m')
                        # 转换 MySQL 格式到 Python 格式
                        fmt_mapping = {
                            '%Y-%m': '%Y-%m',
                            '%Y': '%Y',
                            '%m': '%m',
                            '%Y-%m-%d': '%Y-%m-%d',
                        }
                        python_fmt = fmt_mapping.get(fmt, fmt)
                        temp_df[alias] = temp_df[original_col].dt.strftime(python_fmt)
                    elif func == 'YEAR':
                        temp_df[alias] = temp_df[original_col].dt.year.astype(str)
                    elif func == 'MONTH':
                        temp_df[alias] = temp_df[original_col].dt.month.astype(str).str.zfill(2)
        
        # 构建聚合字典
        agg_dict = {}
        result_columns = []

        logger.debug(f"has_aggregation={has_aggregation}, has_group_by={has_group_by}")
        logger.debug(f"select_columns={select_columns}")

        for col_def in select_columns:
            alias = col_def['alias'] or col_def['arg']
            result_columns.append(alias)
            
            if col_def['is_aggregation']:
                original_col = col_def['arg']
                
                # 特殊处理 COUNT(*)
                if col_def['func'] == 'COUNT' and original_col == '*':
                    # COUNT(*) 使用任意列计数
                    if temp_df.columns.size > 0:
                        agg_dict[temp_df.columns[0]] = [(col_def['func'], alias)]
                elif original_col and original_col != '*':
                    # 尝试大小写不敏感匹配
                    actual_columns = {col.lower(): col for col in temp_df.columns}
                    actual_col = actual_columns.get(original_col.lower(), original_col)
                    
                    if actual_col in temp_df.columns:
                        if actual_col not in agg_dict:
                            agg_dict[actual_col] = []
                        agg_dict[actual_col].append((col_def['func'], alias))

        logger.debug(f"构建的 agg_dict: {agg_dict}")
        logger.debug(f"result_columns: {result_columns}")

        # 执行分组聚合
        if group_by_keys:
            group_by_actual_cols = []
            for col_def in group_by_keys:
                alias = col_def['alias']
                arg = col_def.get('arg', '')

                # 首先尝试精确匹配
                if alias in temp_df.columns:
                    group_by_actual_cols.append(alias)
                elif arg in temp_df.columns:
                    group_by_actual_cols.append(arg)
                else:
                    # 🔧 增强：支持大小写不敏感匹配和模糊匹配
                    # 解决问题：LLM 可能生成 order_id，但实际列名是 id
                    df_columns_lower = {c.lower(): c for c in temp_df.columns}
                    alias_lower = alias.lower() if alias else ''
                    arg_lower = arg.lower() if arg else ''

                    matched = False
                    # 尝试大小写不敏感匹配
                    if alias_lower and alias_lower in df_columns_lower:
                        group_by_actual_cols.append(df_columns_lower[alias_lower])
                        matched = True
                        logger.debug(f"GROUP BY 列名大小写不敏感匹配: {alias} -> {df_columns_lower[alias_lower]}")
                    elif arg_lower and arg_lower in df_columns_lower:
                        group_by_actual_cols.append(df_columns_lower[arg_lower])
                        matched = True
                        logger.debug(f"GROUP BY 列名大小写不敏感匹配: {arg} -> {df_columns_lower[arg_lower]}")

                    if not matched:
                        # 尝试模糊匹配（包含关系）
                        for df_col in temp_df.columns:
                            df_col_lower = df_col.lower()
                            if alias_lower and (alias_lower in df_col_lower or df_col_lower in alias_lower):
                                group_by_actual_cols.append(df_col)
                                logger.debug(f"GROUP BY 列名模糊匹配: {alias} -> {df_col}")
                                matched = True
                                break
                            elif arg_lower and (arg_lower in df_col_lower or df_col_lower in arg_lower):
                                group_by_actual_cols.append(df_col)
                                logger.debug(f"GROUP BY 列名模糊匹配: {arg} -> {df_col}")
                                matched = True
                                break

                    if not matched:
                        logger.warning(f"GROUP BY 列无法匹配: alias={alias}, arg={arg}, 可用列={list(temp_df.columns)}")
            
            if group_by_actual_cols:
                # 执行分组
                grouped = temp_df.groupby(group_by_actual_cols, as_index=False, dropna=False)
                
                # 应用聚合
                agg_result_list = []
                for _, group_df in grouped:
                    row_data = {}
                    
                    # 添加分组列
                    for col_name in group_by_actual_cols:
                        row_data[col_name] = group_df[col_name].iloc[0]
                    
                    # 应用聚合函数
                    for actual_col, aggs in agg_dict.items():
                        if not isinstance(aggs, list):
                            logger.warning(f"agg_dict[{actual_col}] 不是列表，跳过。aggs={aggs}, type={type(aggs)}")
                            continue
                        for agg_item in aggs:
                            if isinstance(agg_item, (list, tuple)) and len(agg_item) == 2:
                                func_name, result_alias = agg_item
                            else:
                                logger.warning(f"聚合项格式错误: {agg_item}，跳过")
                                continue

                            if func_name == 'SUM':
                                row_data[result_alias] = group_df[actual_col].sum()
                            elif func_name == 'COUNT':
                                row_data[result_alias] = group_df[actual_col].count()
                            elif func_name == 'AVG':
                                row_data[result_alias] = group_df[actual_col].mean()
                            elif func_name == 'MAX':
                                row_data[result_alias] = group_df[actual_col].max()
                            elif func_name == 'MIN':
                                row_data[result_alias] = group_df[actual_col].min()
                    
                    agg_result_list.append(row_data)
                
                result_df = pd.DataFrame(agg_result_list)
                
                # 确保列顺序与 SELECT 一致
                ordered_cols = [c for c in result_columns if c in result_df.columns]
                if ordered_cols:
                    result_df = result_df[ordered_cols]
            else:
                # 无法分组，返回空结果
                logger.warning(f"无法解析 GROUP BY 列: {group_by_keys}")
                result_df = pd.DataFrame(columns=result_columns)
        elif agg_dict:
            # 只有聚合没有分组（单行结果）
            row_data = {}
            for actual_col, aggs in agg_dict.items():
                if not isinstance(aggs, list):
                    logger.warning(f"agg_dict[{actual_col}] 不是列表，跳过。aggs={aggs}, type={type(aggs)}")
                    continue
                for agg_item in aggs:
                    if isinstance(agg_item, (list, tuple)) and len(agg_item) == 2:
                        func_name, result_alias = agg_item
                    else:
                        logger.warning(f"聚合项格式错误: {agg_item}，跳过")
                        continue

                    if func_name == 'SUM':
                        row_data[result_alias] = temp_df[actual_col].sum()
                    elif func_name == 'COUNT':
                        row_data[result_alias] = temp_df[actual_col].count()
                    elif func_name == 'AVG':
                        row_data[result_alias] = temp_df[actual_col].mean()
                    elif func_name == 'MAX':
                        row_data[result_alias] = temp_df[actual_col].max()
                    elif func_name == 'MIN':
                        row_data[result_alias] = temp_df[actual_col].min()
            result_df = pd.DataFrame([row_data])
    
    else:
        # ========================================
        # 原有逻辑（非聚合查询）
        # ========================================
        
        if select_match:
            columns_str = select_match.group(1).strip()
            if columns_str != '*':
                columns = [col.strip().lower() for col in columns_str.split(',')]
                actual_columns = {col.lower(): col for col in df.columns}
                selected_columns = []
                for col in columns:
                    if col in actual_columns:
                        selected_columns.append(actual_columns[col])
                if selected_columns:
                    result_df = result_df[selected_columns]
    
    # ========================================
    # 提取 ORDER BY
    # ========================================
    order_match = re.search(r'ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?', query_upper)
    if order_match:
        col_name = order_match.group(1).lower()
        direction = order_match.group(2) if order_match.group(2) else 'ASC'
        
        # 匹配实际列名（优先使用别名）
        actual_columns = {col.lower(): col for col in result_df.columns}
        if col_name in actual_columns:
            actual_col = actual_columns[col_name]
            ascending = direction == 'ASC'
            result_df = result_df.sort_values(by=actual_col, ascending=ascending)
    
    # ========================================
    # 提取 LIMIT
    # ========================================
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
    import pandas as pd

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
                # 🔴 修复：列不存在时抛出错误，而不是跳过条件（会导致返回全部数据）
                available_cols = ", ".join(f'"{c}"' for c in result_df.columns)

                # 🔧 新增：智能建议
                error_msg = f"列 '{col_name}' 不存在于表/工作表中。可用列: {available_cols}"

                if SCHEMA_METADATA_AVAILABLE:
                    # 检查是否是常见的跨表列
                    if col_name in ["province", "city", "district"]:
                        error_msg = (
                            f"🚨 列 '{col_name}' 不存在于当前工作表中！\n\n"
                            f"💡 **可能原因**: '{col_name}' 列通常在 'addresses' 表中\n\n"
                            f"🔧 **建议操作**:\n"
                            f"1. 调用 list_tables() 查看所有可用工作表\n"
                            f"2. 如果有 'addresses' 表，使用 JOIN 查询:\n"
                            f"   SELECT u.*, a.{col_name}\n"
                            f"   FROM users u\n"
                            f"   LEFT JOIN addresses a ON u.id = a.user_id\n"
                            f"   WHERE a.{col_name} = '目标值'\n\n"
                            f"📋 当前工作表可用列: {available_cols}"
                        )
                    elif col_name in ["product_name", "category_name"]:
                        error_msg = (
                            f"🚨 列 '{col_name}' 不存在！\n\n"
                            f"💡 '{col_name}' 可能需要从关联表获取\n\n"
                            f"🔧 **建议**: 调用 list_tables() 查看所有可用工作表\n\n"
                            f"📋 当前工作表可用列: {available_cols}"
                        )
                    else:
                        # 模糊匹配
                        similar_cols = [c for c in result_df.columns if col_name in c.lower() or c.lower() in col_name]
                        if similar_cols:
                            # 预先格式化相似列名（避免在 f-string 中使用反斜杠）
                            similar_cols_formatted = ', '.join(f'"{c}"' for c in similar_cols[:3])
                            error_msg = (
                                f"🚨 列 '{col_name}' 不存在！\n\n"
                                f"💡 您是否想查询: {similar_cols_formatted}?\n\n"
                                f"📋 当前工作表可用列: {available_cols}"
                            )

                raise ValueError(error_msg)

            actual_col = actual_columns[col_name]

            # 应用条件
            mask = None
            if operator == '=':
                # 🔧 新增：省份/城市智能模糊匹配
                # 如果是省份或城市列，尝试扩展简称到完整名称
                is_location_col = (
                    'province' in col_name or '省' in actual_col or
                    'city' in col_name or '市' in actual_col or
                    'region' in col_name or '区' in actual_col
                )

                if is_location_col:
                    # 扩展查询条件，支持简称匹配
                    expanded_values = _expand_province_condition(value, actual_col)
                    logger.debug(f"[省份智能匹配] 列 '{actual_col}' 值 '{value}' 扩展为: {expanded_values}")

                    # 构建模糊匹配掩码
                    combined_mask = None
                    for expanded_value in expanded_values:
                        value_mask = result_df[actual_col].astype(str) == expanded_value
                        if combined_mask is None:
                            combined_mask = value_mask
                        else:
                            combined_mask |= value_mask
                    mask = combined_mask
                else:
                    # 非地理位置列，使用原有逻辑
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

    # 🟡 改为警告级别：不强制检查 list_tables 是否被调用
    # 原因：ContextVar 在异步环境中可能导致检查失效，且 LLM 已通过提示词了解正确流程
    # 仅记录日志，不阻止执行
    if not _get_list_tables_called():
        logger.debug(f"execute_query called without prior list_tables call (query: {query[:50]}...)")
        # 注意：不再返回错误，允许执行继续
        # 依赖提示词指导 LLM 按正确顺序调用工具

    # 🔥 重要：移除 LLM 手动添加的 tenant_id 条件
    # LLM 有时会在 SQL 中手动添加 tenant_id，但位置可能不正确
    # 系统会由租户隔离中间件自动注入正确的 tenant_id 过滤条件
    query_with_tenant_removed = _remove_llm_added_tenant_id(query)
    if query_with_tenant_removed != query:
        logger.debug(f"Removed LLM-added tenant_id: {query[:50]}... -> {query_with_tenant_removed[:50]}...")

    # 清理和修复 SQL
    cleaned_query = clean_and_validate_sql(query_with_tenant_removed)
    if cleaned_query != query_with_tenant_removed:
        logger.debug(f"SQL cleaned: {query_with_tenant_removed[:50]}... -> {cleaned_query[:50]}...")

    user_query = _get_user_query() or ""

    # 从 thread-local 获取 connection_id 和 tenant_id（如果未通过参数传递）
    # Agent 调用工具时不会传递 connection_id，需要从连接上下文获取
    if connection_id is None:
        connection_id, _, tenant_id = _get_connection_context()
    else:
        _, _, tenant_id = _get_connection_context()

    # 🔧 尽早获取数据库连接信息，以便后续修正器使用
    database_url, connection_info = get_database_url(connection_id)
    db_type = _infer_db_type_from_url(database_url)

    # 🔧 月度聚合修正（主要方案：工具层拦截）
    # 统一日志格式：[月度聚合修正] session=... changed=True ...
    if SQL_VALIDATOR_AVAILABLE and SQLValidator is not None:
        # 1. 先修正占比查询
        fixed_query = SQLValidator.fix_proportion_sql(cleaned_query, user_query)
        if fixed_query != cleaned_query:
            logger.warning("[月度聚合修正] 占比查询SQL已自动修正")
            cleaned_query = fixed_query

        # 2. 再修正时间聚合（年度趋势查询）
        # 传递 db_type 以正确选择月表达式语法
        fixed_query = SQLValidator.fix_time_aggregation_sql(
            cleaned_query,
            user_query,
            db_type=db_type
        )
        if fixed_query != cleaned_query:
            connection_id_for_log = connection_id or "unknown"
            logger.warning(
                f"[月度聚合修正] "
                f"connection_id={connection_id_for_log} "
                f"tenant_id={tenant_id or 'unknown'} "
                f"changed=True "
                f"reason='年度趋势查询缺少月度聚合' "
                f"db_type={db_type} "
                f"sql_before={cleaned_query[:100] if len(cleaned_query) > 100 else cleaned_query}... "
                f"sql_after={fixed_query[:100] if len(fixed_query) > 100 else fixed_query}..."
            )
            cleaned_query = fixed_query

    # 🔧 保留原有的占比检测作为后盾
    proportion_error = _check_invalid_proportion_query_pattern(cleaned_query)
    if proportion_error:
        logger.warning("[占比类查询错误] 检测到错误的占比查询模式，返回错误")
        return proportion_error

    # 确保有租户 ID 用于缓存隔离
    cache_tenant_id = tenant_id or "default_tenant"

    # 检查查询结果缓存 (使用租户隔离的缓存)
    cache_key = _make_cache_key(cleaned_query, connection_id)
    cached_result = _query_cache.get(cache_tenant_id, cache_key)
    if cached_result is not None:
        # 🔧 只使用缓存的成功结果，不缓存/返回错误结果
        try:
            cached_json = json.loads(cached_result)
            if "error" in cached_json:
                logger.debug(f"Query result cache HIT but contains error, ignoring: {cleaned_query[:50]}...")
                # 继续执行查询，不返回缓存的错误
            else:
                logger.debug(f"Query result cache HIT (success): {cleaned_query[:50]}...")
                return cached_result
        except json.JSONDecodeError:
            # 如果解析失败，不使用缓存
            logger.warning(f"Query result cache HIT but invalid JSON, ignoring: {cleaned_query[:50]}...")
    logger.debug(f"Query result cache MISS (tenant={cache_tenant_id}): {cleaned_query[:50]}...")

    # 获取数据源连接信息
    if database_url is None:
        database_url, connection_info = get_database_url(connection_id)
    logger.debug(f"Using connection: connection_id={connection_id}, url_type={'excel' if _is_excel_connection(database_url) else 'database'}")

    # 如果是 Excel 连接，使用 Excel 查询
    if _is_excel_connection(database_url):
        logger.debug("Detected Excel data source, using Excel query")
        file_path = _get_excel_file_path(database_url)

        # 🆕 检测子查询（Excel 数据源不支持子查询）
        if _has_subquery(cleaned_query):
            logger.warning("[Excel 子查询] 检测到 Excel 查询包含子查询，返回错误")
            return json.dumps({
                "error": "Excel 数据源不支持子查询（Subquery）",
                "error_type": "subquery_not_supported",
                "query_snippet": cleaned_query[:100] if len(cleaned_query) > 100 else cleaned_query,
                "suggestion": (
                    "🚨 **Excel 数据源不支持子查询**\n\n"
                    "💡 **原因**: 您的查询包含 `IN (SELECT ...)` 或 `EXISTS (SELECT ...)` 子查询，"
                    "Excel 解析器无法处理这种复杂查询。\n\n"
                    "🔧 **建议方案**:\n"
                    "1. 简化查询，只查询单个工作表\n"
                    "2. 使用 GROUP BY 聚合数据\n"
                    "3. 将数据导入数据库后使用子查询\n\n"
                    "❌ 请重新表述您的查询，不要使用子查询。"
                )
            }, ensure_ascii=False)

        # 🆕 检测 JOIN 关键字（修复点 1：Excel JOIN 查询智能拆分）
        join_keywords = ['JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN']
        query_upper = cleaned_query.upper()
        has_join = any(keyword in query_upper for keyword in join_keywords)

        if has_join:
            logger.warning("[Excel JOIN] 检测到 Excel 查询包含 JOIN，尝试智能拆分")
            # 尝试智能拆分 JOIN 查询
            split_result = _try_split_join_query(cleaned_query, file_path)
            if split_result:
                # 拆分成功，返回拆分后的结果
                logger.debug("[Excel JOIN] ✅ 拆分成功，返回结果")
                return split_result
            else:
                # 拆分失败，返回详细错误和建议
                tables = _extract_all_tables_from_query(cleaned_query)

                # 获取可用工作表
                available_sheets = []
                try:
                    import pandas as pd
                    excel_file = _open_excel_file(file_path)
                    available_sheets = excel_file.sheet_names
                except Exception:
                    pass

                error_result = {
                    "error": "Excel JOIN 查询拆分失败",
                    "error_type": "excel_join_not_supported",
                    "detected_tables": tables,
                    "available_sheets": available_sheets,
                    "suggestion": (
                        f"🚨 **Excel 数据源不支持 JOIN 查询**\n\n"
                        f"📊 检测到以下表：{', '.join(tables) if tables else '未知'}\n\n"
                        f"💡 **建议方案**:\n"
                        f"1. 简化查询，只查询单个工作表\n"
                        f"2. 将数据导入数据库后使用 JOIN\n"
                        f"3. 分别查询各个工作表后手动合并\n\n"
                        f"📋 可用工作表: {', '.join(available_sheets) if available_sheets else '无法获取'}"
                    )
                }
                return json.dumps(error_result, ensure_ascii=False)

        # 🔥 修复：从 SQL 查询中解析表名，而不是使用固定的 table_name
        # 尝试从 SQL 中提取表名
        extracted_table_name = _extract_table_name_from_query(cleaned_query)

        # 🔧 修复 3/4: 改进错误处理和添加详细日志
        # 首先获取 Excel 文件中的所有有效工作表名
        valid_sheets = []
        try:
            import pandas as pd
            excel_file = _open_excel_file(file_path)
            valid_sheets = excel_file.sheet_names
            logger.debug(f"Excel 文件包含工作表: {valid_sheets}")
        except Exception as e:
            logger.error(f"无法读取 Excel 文件工作表列表: {e}")
            return json.dumps({
                "error": f"无法读取 Excel 文件: {e}",
                "error_type": "file_read_error"
            }, ensure_ascii=False)

        # 处理表名映射和工作表验证
        if extracted_table_name:
            logger.debug(f"从 SQL 提取表名: '{extracted_table_name}'")

            # 检查提取的表名是否直接存在于 Excel 文件
            if extracted_table_name not in valid_sheets:
                logger.debug(f"表名 '{extracted_table_name}' 不在有效工作表列表中，尝试映射...")

            # 🔥 应用表名映射（英文表名 -> Excel 工作表名）
            # 传递 file_path 以便验证工作表存在并支持备用名称回退
            mapped_sheet = _get_excel_sheet_mapping(extracted_table_name, file_path)

            if mapped_sheet:
                sheet_name = mapped_sheet
                logger.debug(f"✅ 表名映射成功: '{extracted_table_name}' -> '{sheet_name}'")
            else:
                # 🔧 修复 3: 映射失败时，检查原始表名是否存在于 Excel 文件
                if extracted_table_name in valid_sheets:
                    sheet_name = extracted_table_name
                    logger.debug(f"✅ 使用原始表名（无映射但存在）: '{sheet_name}'")
                else:
                    # 映射失败且原始表名也不存在，返回详细错误
                    available_sheets = ", ".join(f'"{s}"' for s in valid_sheets)
                    logger.error(f"❌ 表名映射失败且原始表名不存在: '{extracted_table_name}' (可用: {valid_sheets})")

                    return json.dumps({
                        "error": f"表 '{extracted_table_name}' 不存在，也无法映射到有效工作表",
                        "error_type": "table_not_found",
                        "suggestion": (
                            f"🚨 表名 '{extracted_table_name}' 无法映射到任何有效工作表！\n\n"
                            f"📋 可用的工作表: {available_sheets}\n\n"
                            f"🔴 修复步骤：\n"
                            f"1. 使用上述确切的工作表名\n"
                            f"2. SQL 中工作表名需要用双引号包裹\n"
                            f"   例如: SELECT * FROM \"订单表\"\n\n"
                            f"💡 提示：请先调用 list_tables() 查看所有可用工作表"
                        )
                    }, ensure_ascii=False)
        else:
            # 回退到 connection_info.table_name 或默认值
            sheet_name = connection_info.table_name if connection_info else None
            logger.warning(f"⚠️ 无法从 SQL 提取表名，使用默认值: '{sheet_name}'")

            # 验证默认值是否存在
            if sheet_name and sheet_name not in valid_sheets:
                available_sheets = ", ".join(f'"{s}"' for s in valid_sheets)
                logger.error(f"❌ 默认表名 '{sheet_name}' 不存在于 Excel 文件 (可用: {valid_sheets})")
                return json.dumps({
                    "error": f"默认表名 '{sheet_name}' 不存在",
                    "error_type": "table_not_found",
                    "suggestion": f"可用的工作表: {available_sheets}"
                }, ensure_ascii=False)

        # 🔧 修复 4: 添加详细日志
        logger.debug(f"🚀 执行 Excel 查询: file_path={file_path}, sheet_name='{sheet_name}', query={cleaned_query[:100]}...")
        result = execute_excel_query(cleaned_query, file_path, sheet_name)

        # 记录查询结果摘要
        try:
            result_json = json.loads(result)
            if "error" not in result_json:
                logger.debug(f"✅ Excel 查询成功: columns={result_json.get('columns')}, row_count={result_json.get('row_count')}")
            else:
                logger.error(f"❌ Excel 查询失败: {result_json.get('error')}")
        except:
            logger.debug("Excel 查询完成（结果无法解析为 JSON）")

        # 存储到租户隔离的缓存
        _query_cache.set(cache_tenant_id, cache_key, result)
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
            raw_rows = cursor.fetchall()

            # 🔧 使用序列化函数处理所有数据类型（PostgreSQL Decimal, UUID, datetime 等）
            rows = _serialize_rows(raw_rows, columns)

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

            logger.debug(f"Query executed successfully: {len(rows)} rows returned")

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

        # 🔧 清除该查询的缓存条目（如果存在）
        try:
            _query_cache.delete(cache_tenant_id, cache_key)
            logger.debug(f"Cleared timeout cache entry for query: {cleaned_query[:50]}...")
        except Exception as cache_error:
            logger.warning(f"Failed to clear cache entry: {cache_error}")

        return json.dumps({
            "error": "Query execution timeout after 30 seconds",
            "error_type": "timeout_error",
            "query": sanitize_sql_for_logging(cleaned_query, max_length=100)  # 🔒 脱敏查询
        }, ensure_ascii=False)

    if result_container["error"] is not None:
        error = result_container["error"]
        logger.error(f"Query execution error: {error}")
        # 🔒 使用脱敏函数记录 SQL，防止暴露敏感信息
        logger.error(f"Failed query: {sanitize_sql_for_logging(cleaned_query)}")

        # 🔧 清除该查询的缓存条目（如果存在），确保下次查询会重新执行
        try:
            _query_cache.delete(cache_tenant_id, cache_key)
            logger.debug(f"Cleared error cache entry for query: {cleaned_query[:50]}...")
        except Exception as cache_error:
            logger.warning(f"Failed to clear cache entry: {cache_error}")

        return json.dumps({
            "error": str(error),
            "error_type": "execution_error",
            "query": sanitize_sql_for_logging(cleaned_query, max_length=100),  # 🔒 脱敏查询
            "suggestion": get_query_suggestion(str(error), cleaned_query)
        }, ensure_ascii=False)

    if result_container["result"] is not None:
        result_json = json.dumps(result_container["result"], ensure_ascii=False, default=str)

        # 🔧 只缓存成功的结果，不缓存错误结果
        if "error" not in result_container["result"]:
            _query_cache.set(cache_tenant_id, cache_key, result_json)
            logger.debug(f"Query result cached (tenant={cache_tenant_id}): {cleaned_query[:50]}...")
        else:
            logger.debug(f"Query result contains error, NOT caching (tenant={cache_tenant_id}): {cleaned_query[:50]}...")

        return result_json

    # 未知的错误
    return json.dumps({
        "error": "Unknown error during query execution",
        "error_type": "unknown_error"
    }, ensure_ascii=False)


def _remove_llm_added_tenant_id(query: str) -> str:
    """
    移除 LLM 手动添加的 tenant_id 条件

    LLM 有时会在 SQL 中手动添加 tenant_id 过滤条件，但位置可能不正确
    （如在 GROUP BY/ORDER BY 之后）。这个函数会移除所有 LLM 手动添加的
    tenant_id 条件，让租户隔离中间件在正确的位置重新注入。

    Args:
        query: 原始 SQL 查询

    Returns:
        移除 LLM 添加的 tenant_id 后的 SQL
    """
    import re

    sql = query.strip()
    original_sql = sql

    # 模式 1: 移除 WHERE tenant_id = 'xxx' （作为独立 WHERE 条件）
    # 匹配: WHERE tenant_id = 'xxx' 后面跟着其他内容或结束
    pattern1 = r'\bWHERE\s+tenant_id\s*=\s*\'[^\']*\'(\s+|$)'
    if re.search(pattern1, sql, re.IGNORECASE):
        # 如果 WHERE 子句只有 tenant_id，直接移除整个 WHERE
        sql = re.sub(
            r'\bWHERE\s+tenant_id\s*=\s*\'[^\']*\'(\s*(?:GROUP BY|ORDER BY|LIMIT|HAVING|;|$))?',
            lambda m: '' if not m.group(1) or m.group(1).strip() in ('GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING', ';') else ' AND ',
            sql,
            flags=re.IGNORECASE
        )
        # 清理可能残留的 AND
        sql = re.sub(r'\bAND\s+(GROUP BY|ORDER BY|LIMIT|HAVING)', r'\1', sql, flags=re.IGNORECASE)

    # 模式 2: 移除 AND tenant_id = 'xxx' （作为 AND 条件）
    sql = re.sub(
        r'\bAND\s+tenant_id\s*=\s*\'[^\']*\'(\s+|$)',
        '',
        sql,
        flags=re.IGNORECASE
    )

    # 模式 3: 移除 OR tenant_id = 'xxx' （作为 OR 条件）
    sql = re.sub(
        r'\bOR\s+tenant_id\s*=\s*\'[^\']*\'(\s+|$)',
        '',
        sql,
        flags=re.IGNORECASE
    )

    # 模式 4: 移除 WHERE 子句中间的 tenant_id 条件
    # 例如: WHERE status = 'active' AND tenant_id = 'xxx' AND other = 'value'
    # 变成: WHERE status = 'active' AND other = 'value'
    sql = re.sub(
        r'\bAND\s+tenant_id\s*=\s*\'[^\']*\'(\s+(AND|OR))?',
        r'\1',
        sql,
        flags=re.IGNORECASE
    )
    sql = re.sub(
        r'\bAND\s+tenant_id\s*=\s*\'[^\']*\'\s*,',
        ',',
        sql,
        flags=re.IGNORECASE
    )

    # 模式 5: 处理 WHERE 开头就是 tenant_id 的情况
    # 例如: WHERE tenant_id = 'xxx' AND status = 'active'
    # 变成: WHERE status = 'active'
    sql = re.sub(
        r"\bWHERE\s+tenant_id\s*=\s*'[^']*'\s+AND\s+",
        'WHERE ',
        sql,
        flags=re.IGNORECASE
    )

    # 清理多余的空格
    sql = ' '.join(sql.split())

    if sql != original_sql and 'tenant_id' in original_sql.lower():
        logger.debug("Removed LLM-added tenant_id conditions")

    return sql


def _check_invalid_proportion_query_pattern(sql: str) -> Optional[str]:
    """
    🔧 检测错误的占比查询模式，返回强制错误（v4 修复）

    当检测到以下模式时，返回错误信息：
    1. 单一 SELECT COUNT(*) FROM table WHERE condition
    2. 没有 GROUP BY 子句
    3. WHERE 条件是简单的等值比较（如 province = '安徽'）

    这种模式是占比类问题的错误写法，应该用 GROUP BY 替代。

    Args:
        sql: 清理后的 SQL

    Returns:
        如果检测到错误的占比查询模式，返回错误信息 JSON 字符串；否则返回 None
    """
    import re
    import json

    # 跳过非 COUNT 查询
    if 'COUNT(' not in sql.upper():
        return None

    # 跳过已有 GROUP BY 的查询（已正确处理）
    if 'GROUP BY' in sql.upper():
        return None

    # 跳过有 LIMIT 的查询（可能只是检查是否存在）
    if 'LIMIT' in sql.upper():
        return None

    # 检测模式：SELECT COUNT(*) FROM table WHERE single_condition
    # 这种模式通常是占比类问题的错误写法

    # 提取 SELECT 和 FROM 之间的内容
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE)
    if not select_match:
        return None

    select_clause = select_match.group(1).strip()

    # 检查是否是简单的 COUNT(*) 或 COUNT(列名)
    is_simple_count = re.match(r'^COUNT\s*\(\s*\*?\s*\)$', select_clause, re.IGNORECASE)
    if not is_simple_count:
        return None

    # 检查是否有 WHERE 子句
    where_match = re.search(r'WHERE\s+([^;]+)', sql, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1).strip()

        # 检查 WHERE 条件是否是简单的等值比较
        # 如果 WHERE 条件包含 LIKE、IN、多个 AND/OR，可能是正确的查询
        complex_patterns = ['LIKE', 'IN', 'OR', '>=', '<=', '>', '<', 'BETWEEN']
        has_complex_condition = any(pattern in where_clause.upper() for pattern in complex_patterns)

        if not has_complex_condition:
            # 简单等值条件，可能是占比查询的错误模式
            # 检查条件形式：column = 'value' 或 column = value
            if re.search(r'\w+\s*=\s*', where_clause):
                # 提取表名
                from_match = re.search(r'FROM\s+"?([\w\u4e00-\u9fff]+)"?', sql, re.IGNORECASE)
                table_name = from_match.group(1) if from_match else "table"

                # 检测是否是省份/城市相关的查询
                is_province_city_query = any(
                    keyword in where_clause.upper()
                    for keyword in ['PROVINCE', 'CITY', '省', '市', '地区']
                )

                if is_province_city_query:
                    logger.warning(
                        f"🚨 [占比类查询错误] 检测到错误的省份/城市占比查询模式！\n"
                        f"   当前SQL: SELECT COUNT(*) FROM {table_name} WHERE {where_clause}\n"
                    )

                    return json.dumps({
                        "error": "⚠️ 检测到错误的占比查询模式",
                        "error_type": "invalid_proportion_query_pattern",
                        "query_snippet": sql[:100] if len(sql) > 100 else sql,
                        "suggestion": """
## 🔧 错误分析

您正在查询占比类问题（如"XX的客户占比"），但使用了错误的查询模式。

## ❌ 当前错误模式
```sql
SELECT COUNT(*) FROM table WHERE condition
```

**问题**：这种模式只能获取单一数值，无法生成完整的分布饼图。

## ✅ 正确模式：使用一次 GROUP BY 查询
```sql
SELECT
    province,
    COUNT(*) as customer_count
FROM "addresses"
GROUP BY province
ORDER BY customer_count DESC;
```

## 📋 正确查询步骤
1. 先调用 `list_tables()` 查看可用表
2. 再调用 `get_schema("表名")` 查看字段和数据格式
3. 使用 **一次 GROUP BY 查询** 获取所有分类数据
4. 在回答中计算占比百分比

## ⚠️ 重要提示
- **必须使用完整省份名称**：`WHERE province = '安徽省'` 而不是 `'安徽'`
- **永远使用 GROUP BY**：占比查询必须使用 GROUP BY
- **一次查询完成**：不要多次 COUNT 查询
"""
                    }, ensure_ascii=False)

    # 如果完全没有 WHERE 子句，检查是否是 COUNT(*) 总数查询
    else:
        # 这可能是一个总数查询，记录警告但不返回错误
        logger.warning(
            f"⚠️ [占比类查询检测] 检测到不带 WHERE 的 COUNT(*) 查询\n"
            f"   当前SQL: {sql[:100]}...\n"
            f"   提示: 如果这是占比/分布类问题，请确保使用 GROUP BY 获取所有分类的数据"
        )

    return None


def _warn_suspicious_count_pattern(sql: str, original_sql: str) -> None:
    """
    🔧 检测可疑的 COUNT(*) 查询模式（占比类问题检测）

    当检测到以下模式时，记录警告：
    1. 单一 SELECT COUNT(*) 查询
    2. 包含 WHERE 条件，但 WHERE 条件中只有一个简单的等值比较
    3. 没有 GROUP BY 子句

    这种模式通常应该用 GROUP BY 替代，以获取完整的分布数据。

    Args:
        sql: 清理后的 SQL
        original_sql: 原始 SQL（用于更详细的检测）
    """
    import re

    # 跳过非 COUNT 查询
    if 'COUNT(' not in sql.upper():
        return

    # 跳过已有 GROUP BY 的查询（已正确处理）
    if 'GROUP BY' in sql.upper():
        return

    # 跳过有 LIMIT 的查询（可能只是检查是否存在）
    if 'LIMIT' in sql.upper():
        return

    # 检测模式：SELECT COUNT(*) FROM table WHERE single_condition
    # 这种模式通常是占比类问题的错误写法

    # 提取 SELECT 和 FROM 之间的内容
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE)
    if not select_match:
        return

    select_clause = select_match.group(1).strip()

    # 检查是否是简单的 COUNT(*) 或 COUNT(列名)
    is_simple_count = re.match(r'^COUNT\s*\(\s*\*?\s*\)$', select_clause, re.IGNORECASE)
    if not is_simple_count:
        return

    # 检查是否有 WHERE 子句
    where_match = re.search(r'WHERE\s+([^;]+)', sql, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1).strip()

        # 检查 WHERE 条件是否是简单的等值比较
        # 如果 WHERE 条件包含 LIKE、IN、多个 AND/OR，可能是正确的查询
        complex_patterns = ['LIKE', 'IN', 'OR', '>=', '<=', '>', '<', 'BETWEEN']
        has_complex_condition = any(pattern in where_clause.upper() for pattern in complex_patterns)

        if not has_complex_condition:
            # 简单等值条件，可能是占比查询的错误模式
            # 检查条件形式：column = 'value' 或 column = value
            if re.search(r'\w+\s*=\s*', where_clause):
                # 提取表名
                from_match = re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE)
                table_name = from_match.group(1) if from_match else "table"

                logger.warning(
                    f"⚠️ [占比类查询检测] 检测到可能是错误的 COUNT 模式！\n"
                    f"   当前SQL: SELECT COUNT(*) FROM {table_name} WHERE {where_clause}\n"
                    f"   问题: 如果这是占比类查询（如'XX的占比'），应该使用 GROUP BY 获取完整分布\n"
                    f"   建议: 使用 GROUP BY 查询，例如:\n"
                    f"         SELECT CASE WHEN ... END as category, COUNT(*) as value\n"
                    f"         FROM {table_name} GROUP BY category;\n"
                    f"   后果: 否则饼图将只有一个数据点，变成'独眼实心圆'"
                )

    # 如果完全没有 WHERE 子句，也记录警告（可能需要 GROUP BY）
    else:
        logger.warning(
            f"⚠️ [占比类查询检测] 检测到不带 WHERE 的 COUNT(*) 查询\n"
            f"   当前SQL: {sql[:100]}...\n"
            f"   提示: 如果这是占比/分布类问题，请确保使用 GROUP BY 获取所有分类的数据"
        )


def clean_and_validate_sql(query: str) -> str:
    """
    清理和验证 SQL 查询

    修复常见的 LLM 生成错误：
    - LIMIT 子句后的错误内容（WHERE, AND, OR 等）
    - tenants 表的 tenant_id 列错误（应使用 id）
    - ORDER BY/GROUP BY 后面错误跟 AND/OR 条件
    - WHERE 子句位置错误（在 GROUP BY/ORDER BY 之后）
    - 多余的分号
    - 不完整的查询

    v4.3.0 优化：添加详细日志记录，方便调试 SQL 清理过程

    Args:
        query: 原始 SQL 查询

    Returns:
        清理后的 SQL 查询
    """
    import re

    # 移除前后空格
    sql = query.strip()
    original_sql = sql  # 保存原始 SQL 用于日志比较

    # 📊 详细日志：记录输入的 SQL
    logger.debug(f"[SQL_CLEAN] Input SQL: {sql[:200]}...")

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
        if 'tenant_id' in original_sql.lower() and 'tenant_id' not in sql.lower():
            logger.debug("Auto-fixed: tenants.tenant_id → tenants.id")

    # 修复 1: 移除 ORDER BY/GROUP BY 后面错误跟的 AND/OR/WHERE 条件
    # 错误示例: SELECT ... ORDER BY year AND tenant_id = '...'
    # 错误示例: SELECT ... ORDER BY year WHERE tenant_id = '...'
    # 错误示例: SELECT ... GROUP BY year OR tenant_id = '...'
    # 错误示例: SELECT ... GROUP BY col WHERE tenant_id = '...'
    for keyword in ['ORDER BY', 'GROUP BY']:
        # 匹配: keyword + 字段名 (+ 可选 ASC/DESC) + 空白 + (AND|OR|WHERE)
        # 模式: 关键字 + 空白 + 字段名 (+ 可选 ASC/DESC) + 空白 + (AND|OR|WHERE)
        pattern = rf'\b{keyword}\s+([^\s]+(?:\s+(?:ASC|DESC))?)\s+(AND|OR|WHERE)\b'
        match = re.search(pattern, sql, re.IGNORECASE)
        if match:
            # 找到 AND/OR/WHERE 的位置
            clause_start = match.start(2)
            # 截断到 AND/OR/WHERE 之前
            before_clause = sql[:clause_start].rstrip()
            remaining = sql[clause_start:]
            # 移除错误条件到下一个关键字或结尾
            # 找到 AND/OR/WHERE 后面的下一个子句（LIMIT, HAVING, ;）
            next_clause_match = re.search(r'\b(LIMIT|HAVING|;)\b', remaining, re.IGNORECASE)
            if next_clause_match:
                # 保留 LIMIT 等子句
                after_clause = remaining[next_clause_match.start():]
                sql = before_clause + after_clause
            else:
                # 没有其他子句，直接截断
                sql = before_clause
            logger.debug(f"Removed incorrect {match.group(2)} clause after {keyword}: {match.group(0)[:50]}...")

    # 修复 2: 检测并修复 WHERE 子句位置错误
    # 错误示例: SELECT ... GROUP BY year ORDER BY year WHERE tenant_id = '...'
    # WHERE 必须在 GROUP BY/ORDER BY 之前
    #
    # 使用基于位置的解析方法：
    # 1. 找到所有关键字位置
    # 2. 检查 WHERE 是否在 GROUP BY/ORDER BY 之后
    # 3. 如果是，重新排列 SQL
    keywords_found = {}
    for kw in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']:
        match = re.search(rf'\b{kw}\b', sql, re.IGNORECASE)
        if match:
            keywords_found[kw] = {'start': match.start(), 'end': match.end()}

    # 如果存在 WHERE 和 (GROUP BY 或 ORDER BY)
    if 'WHERE' in keywords_found and ('GROUP BY' in keywords_found or 'ORDER BY' in keywords_found):
        where_pos = keywords_found['WHERE']['start']
        group_pos = keywords_found.get('GROUP BY', {'start': float('inf')})['start']
        order_pos = keywords_found.get('ORDER BY', {'start': float('inf')})['start']

        # 检查 WHERE 是否在 GROUP BY 或 ORDER BY 之后
        if where_pos > group_pos or where_pos > order_pos:
            logger.debug("Detected WHERE after GROUP BY/ORDER BY, fixing...")

            # 使用基于位置的子句提取（更可靠）
            # 找出所有子句的起始和结束位置
            clauses = {}
            for kw in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT']:
                if kw in keywords_found:
                    start = keywords_found[kw]['start']
                    kw_end = keywords_found[kw]['end']
                    # 找到下一个关键字的起始位置作为当前子句的结束位置
                    next_start = float('inf')
                    for other_kw in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']:
                        if other_kw in keywords_found and keywords_found[other_kw]['start'] > kw_end:
                            next_start = min(next_start, keywords_found[other_kw]['start'])
                    # 如果没有下一个关键字，使用分号位置或字符串结尾
                    if next_start == float('inf'):
                        semicolon_pos = sql.rfind(';')
                        if semicolon_pos > kw_end:
                            next_start = semicolon_pos
                        else:
                            next_start = len(sql)
                    clauses[kw] = sql[start:next_start].strip()

            # 重新构建 SQL（正确顺序）
            new_sql_parts = []
            order = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT']
            for kw in order:
                if kw in clauses:
                    new_sql_parts.append(clauses[kw])

            # 组合成新的 SQL
            if new_sql_parts:
                sql = ' '.join(new_sql_parts)
                # 确保以分号结尾
                if not sql.endswith(';'):
                    sql += ';'
                logger.debug(f"Rebuilt SQL with correct clause order: {sql[:80]}...")

    # 修复 3: 移除 LIMIT 后面的任何内容（LLM 常见错误）
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
            logger.debug(f"Removed content after LIMIT: {remaining_sql[:50]}...")

    # 修复 4: 移除末尾的分号（如果有多个）
    sql = re.sub(r';+$', '', sql)

    # 修复 5: 确保查询以分号结尾（对于单条查询）
    if not sql.endswith(';'):
        sql += ';'

    # 修复 6: 移除注释后的危险命令（额外安全检查）
    # 移除 -- 后面的内容到行尾
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    # 移除 /* */ 块注释
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # 修复 7: 清理多余的空格
    sql = ' '.join(sql.split())

    # 🔧 新增：占比类查询检测（Fix for "独眼实心圆"问题）
    # 检测单一的 COUNT(*) 查询模式，可能需要用 GROUP BY 替代
    _warn_suspicious_count_pattern(sql, original_sql)

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
            logger.debug(f"Extracted table name (double-quoted) from query: '{table_name}'")
            return table_name

        # 🔧 匹配单引号内的表名
        single_quote_pattern = r"\bFROM\s+'([^']+)'"
        match = re.search(single_quote_pattern, cleaned, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            logger.debug(f"Extracted table name (single-quoted) from query: '{table_name}'")
            return table_name

        # 🔧 最后：匹配不带引号的表名（支持emoji和中文，但不能有空格）
        # 使用 Unicode 属性匹配任何单词字符（包括中文、emoji等）
        unquoted_pattern = r'\bFROM\s+([^\s;]+?)(?:\s+WHERE|\s+ORDER|\s+GROUP|\s+LIMIT|\s+HAVING|;|$)'
        match = re.search(unquoted_pattern, cleaned, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            logger.debug(f"Extracted table name (unquoted) from query: '{table_name}'")
            return table_name

        logger.warning(f"Could not extract table name from query: {query[:100]}...")
        return None
    except Exception as e:
        logger.warning(f"Error extracting table name: {e}")
        return None


def _extract_all_tables_from_query(query: str) -> list[str]:
    """
    从 SQL 查询中提取所有表名（包括 JOIN 的表）

    Args:
        query: SQL 查询语句

    Returns:
        表名列表
    """
    import re

    tables = []

    try:
        # 移除注释和换行符，简化解析
        cleaned = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = ' '.join(cleaned.split())

        # 提取 FROM 后的表名
        from_match = re.search(r'\bFROM\s+"?([^\s";]+)"?', cleaned, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))

        # 提取所有 JOIN 后的表名
        join_pattern = r'\b(?:INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+|CROSS\s+)?JOIN\s+"?([^\s";]+)"?'
        for match in re.finditer(join_pattern, cleaned, re.IGNORECASE):
            tables.append(match.group(1))

        logger.debug(f"从查询中提取到表名: {tables}")
        return tables
    except Exception as e:
        logger.warning(f"提取表名时出错: {e}")
        return []


def _try_split_join_query(query: str, file_path: str) -> Optional[str]:
    """
    尝试将 JOIN 查询拆分为对单个工作表的查询

    支持的拆分场景：
    1. LEFT JOIN 中只有 WHERE 条件引用了右表的字段 -> 拆分为对右表的查询
    2. 简单的计数/聚合查询 -> 尝试在包含目标字段的工作表上执行

    Args:
        query: 原始 SQL 查询
        file_path: Excel 文件路径

    Returns:
        拆分后查询的执行结果（JSON 字符串），如果无法拆分则返回 None
    """
    import pandas as pd
    import re

    try:
        logger.debug(f"[JOIN拆分] 尝试拆分 JOIN 查询: {query[:100]}...")

        # 加载 Excel 文件获取所有工作表
        excel_file = _open_excel_file(file_path)
        available_sheets = excel_file.sheet_names
        logger.debug(f"[JOIN拆分] Excel 工作表: {available_sheets}")

        # 提取 SELECT 子句
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM', query, re.IGNORECASE)
        select_clause = select_match.group(1) if select_match else '*'

        # 提取 WHERE 子句中的字段引用
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+GROUP|\s+ORDER|\s+LIMIT|;|$)', query, re.IGNORECASE)
        if not where_match:
            logger.debug("[JOIN拆分] 未找到 WHERE 子句，无法拆分")
            return None

        where_clause = where_match.group(1)

        # 提取字段名（如 a.province 中的 province）
        # 匹配: alias.column 或 column
        column_refs = re.findall(r'\b(\w+)\.(\w+)\b|\b(\w+)\s*=', where_clause)

        target_columns = []
        for match in column_refs:
            if match[1]:  # alias.column 格式
                target_columns.append(match[1].lower())
            elif match[2]:  # column 格式
                target_columns.append(match[2].lower())

        if not target_columns:
            logger.debug("[JOIN拆分] 未找到目标列，无法拆分")
            return None

        logger.debug(f"[JOIN拆分] 目标列: {target_columns}")

        # 找出包含目标字段的工作表
        target_sheet = None
        sheet_columns_map = {}  # 记录每个工作表的列

        for sheet in available_sheets:
            df = _read_excel_file(file_path, sheet_name=sheet, nrows=0)
            columns_lower = [col.lower() for col in df.columns]
            sheet_columns_map[sheet] = list(df.columns)

            for col in target_columns:
                if col in columns_lower:
                    target_sheet = sheet
                    target_column_actual = [c for c in df.columns if c.lower() == col][0]
                    logger.debug(f"[JOIN拆分] 找到目标列 '{col}' 在工作表 '{sheet}' 中，实际列名: '{target_column_actual}'")
                    break

            if target_sheet:
                break

        if not target_sheet:
            logger.debug("[JOIN拆分] 未找到包含目标列的工作表")
            return None

        # 构建新的查询：针对目标工作表
        # 简化 WHERE 子句（移除表别名前缀）
        simplified_where = re.sub(r'\w+\.', '', where_clause)

        # 构建新查询
        new_query = f"SELECT {select_clause} FROM \"{target_sheet}\" WHERE {simplified_where}"
        logger.debug(f"[JOIN拆分] 构建新查询: {new_query}")

        # 执行新查询
        df = _read_excel_file(file_path, sheet_name=target_sheet)

        # 使用现有的 SQL 解析逻辑
        result_df = _parse_sql_to_pandas(new_query, df)

        # 转换为 JSON 格式返回
        columns = result_df.columns.tolist()
        rows = result_df.values.tolist()

        # 序列化数据
        rows = _serialize_rows(rows, columns)

        result = {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "success": True,
            "data_source": "excel",
            "sheet_name": target_sheet,
            "_join_split": True,  # 标记这是拆分后的查询
            "_original_query": query,
            "_split_note": f"原查询包含 JOIN，已自动拆分为对工作表 '{target_sheet}' 的查询"
        }

        logger.debug(f"[JOIN拆分] ✅ 拆分成功: {len(rows)} 行")
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        logger.warning(f"[JOIN拆分] 拆分查询执行失败: {e}")
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

            # 🔧 新增：解析列名格式，支持 "table.column" 格式
            if '.' in col:
                # 可能是 "table.column" 格式
                parts = col.rsplit('.', 1)
                if len(parts) == 2:
                    table_part, column_part = parts
                    return (f"🚨 列 '{col}' 不存在！\n\n"
                            f"📋 问题分析：\n"
                            f"• 引用的表名：'{table_part}'\n"
                            f"• 引用的列名：'{column_part}'\n\n"
                            f"🔴 修复步骤：\n"
                            f"1. 先调用 list_tables() 查看所有可用的表名\n"
                            f"2. 对正确的表调用 get_schema('表名') 查看可用的列名\n"
                            f"3. 使用正确的表名和列名重新查询\n\n"
                            f"💡 常见错误原因：\n"
                            f"• 表名拼写错误 - 确保使用 list_tables() 返回的确切表名\n"
                            f"• 列名拼写错误 - 某些数据库区分大小写\n"
                            f"• 表名与列名混淆 - 检查 FROM 子句后的表名是否正确\n"
                            f"• 使用了不存在的字段 - 可能需要查询其他表获取此信息")
                else:
                    return f"列 '{col}' 不存在。请使用 get_schema() 查看可用的列。"
            else:
                # 单纯的列名错误
                return (f"🚨 列 '{col}' 不存在！\n\n"
                        f"🔴 修复步骤：\n"
                        f"1. 调用 list_tables() 确认表名\n"
                        f"2. 调用 get_schema('表名') 查看该表的所有列名\n"
                        f"3. 使用正确的列名重新查询")

    if 'relation' in error_lower and 'does not exist' in error_lower:
        match = re.search(r'relation "(.*?)" does not exist', error_msg)
        if match:
            table = match.group(1)
            return (f"🚨 表 '{table}' 不存在！\n\n"
                    f"🔴 必须执行以下步骤重试：\n"
                    f"1. 立即调用 list_tables() 查看所有可用表\n"
                    f"2. 根据业务语义选择相关表（例如：sales→订单表/销售表）\n"
                    f"3. 使用 list_tables() 返回的确切表名重新查询\n\n"
                    f"📋 业务术语映射（仅供参考，实际表名以list_tables()为准）：\n"
                    f"• 销售/销售额 → 订单表、销售表、orders、sales\n"
                    f"• 客户/用户 → 用户表、客户表、users、customers\n"
                    f"• 产品/商品 → 产品表、商品表、products\n"
                    f"• 订单 → 订单表、订单明细、orders")

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

    # 从 thread-local 获取 connection_id 和 tenant_id（如果未通过参数传递）
    if connection_id is None:
        connection_id, _, tenant_id = _get_connection_context()
    else:
        _, _, tenant_id = _get_connection_context()

    # 确保有租户 ID 用于缓存隔离
    cache_tenant_id = tenant_id or "default_tenant"

    logger.debug(f"list_tables: connection_id={connection_id}, tenant_id={cache_tenant_id}")

    # 清除旧缓存以确保使用新的连接信息
    if connection_id:
        _schema_cache.clear_tenant(cache_tenant_id)

    # 检查租户隔离的缓存
    cache_key = _make_cache_key("list_tables", connection_id)
    cached = _schema_cache.get(cache_tenant_id, cache_key)
    if cached is not None:
        logger.debug(f"list_tables: 返回缓存结果 (tenant={cache_tenant_id})")
        return cached

    # 获取数据源连接信息
    database_url, connection_info = get_database_url(connection_id)

    # 如果是 Excel 连接，返回工作表列表
    if _is_excel_connection(database_url):
        logger.debug("list_tables: Detected Excel data source, listing sheets")
        try:
            file_path = _get_excel_file_path(database_url)
            import pandas as pd

            excel_file = _open_excel_file(file_path)
            sheets = excel_file.sheet_names

            # 🔧 新增：为 Excel 工作表也添加描述（如果配置中存在）
            if TABLE_DESCRIPTIONS_AVAILABLE:
                enhanced_sheets = enrich_tables_with_description(sheets, include_all=True)

                # 🔧 新增：为地理位置查询添加智能表推荐
                enhanced_sheets = _add_geo_table_recommendation(enhanced_sheets)

                result = {
                    "tables": sheets,  # 原始表名列表
                    "tables_enhanced": enhanced_sheets,  # 增强表信息列表
                    "table_count": len(sheets),
                    "success": True,
                    "data_source": "excel",
                    "file_path": file_path,
                    "has_descriptions": True
                }
            else:
                result = {
                    "tables": sheets,
                    "table_count": len(sheets),
                    "success": True,
                    "data_source": "excel",
                    "file_path": file_path,
                    "has_descriptions": False
                }

            result_str = json.dumps(result, ensure_ascii=False, indent=2)
            _schema_cache.set(cache_tenant_id, cache_key, result_str)
            logger.debug(f"list_tables: Excel 文件，{len(sheets)} 个工作表: {sheets} (tenant={cache_tenant_id})")

            # 🔧 设置标志，表示 list_tables 已被调用
            _set_list_tables_called(True)

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

        # 🔧 新增：增强表信息，添加描述和推荐
        if TABLE_DESCRIPTIONS_AVAILABLE:
            enhanced_tables = enrich_tables_with_description(tables, include_all=True)

            # 🔧 新增：为地理位置查询添加智能表推荐
            enhanced_tables = _add_geo_table_recommendation(enhanced_tables)

            # 分类返回：高优先级表优先显示
            high_priority_tables = [t for t in enhanced_tables if t.get("priority") == "high"]
            medium_priority_tables = [t for t in enhanced_tables if t.get("priority") == "medium"]
            low_priority_tables = [t for t in enhanced_tables if t.get("priority") == "low"]
            no_config_tables = [t for t in enhanced_tables if not t.get("has_config")]

            result = {
                "tables": tables,  # 原始表名列表（保持向后兼容）
                "tables_enhanced": enhanced_tables,  # 增强表信息列表
                "high_priority": [t["name"] for t in high_priority_tables],
                "medium_priority": [t["name"] for t in medium_priority_tables],
                "low_priority": [t["name"] for t in low_priority_tables],
                "no_config": [t["name"] for t in no_config_tables],
                "table_count": len(tables),
                "success": True,
                "has_descriptions": True
            }
        else:
            result = {
                "tables": tables,
                "table_count": len(tables),
                "success": True,
                "has_descriptions": False
            }

        result_str = json.dumps(result, ensure_ascii=False, indent=2)
        # 存入租户隔离的缓存
        _schema_cache.set(cache_tenant_id, cache_key, result_str)
        logger.debug(f"list_tables: 查询成功，缓存结果 ({len(tables)} 个表) (tenant={cache_tenant_id})")

        # 🔧 设置标志，表示 list_tables 已被调用
        _set_list_tables_called(True)

        return result_str

    except Exception as e:
        logger.error(f"List tables error: {e}")
        error_str = json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)
        return error_str


# 注意：这些函数不再使用 @tool 装饰器，而是在 get_database_tools 中手动创建 StructuredTool
# ============================================================================
# 表推荐机制 - 针对占比类查询（解决跨表口径不一致问题）
# ============================================================================

def _get_table_recommendation_for_query(
    table_name: str,
    columns: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    根据表名和字段信息推荐合适的表，用于占比类查询

    解决问题：当用户询问"XX的客户占比"、"XX地区客户数量"时，
    AI 可能在 users 和 addresses 表之间跳跃，导致分子分母数据口径不一致。

    Args:
        table_name: 当前查询的表名
        columns: 表的列信息列表

    Returns:
        推荐信息字典，如果无需推荐则返回 None
    """
    # 地理位置字段到推荐表的映射
    # addresses 表包含完整的省份/城市信息，users 表的 province 字段可能为空
    geo_field_table_map = {
        "province": {
            "recommended_table": "addresses",
            "reason": "省份信息在 addresses 表中更完整（users 表的 province 字段可能为空）",
            "note": "查询省份占比时，应使用 addresses 表并坚持使用它，避免跨表查询"
        },
        "city": {
            "recommended_table": "addresses",
            "reason": "城市信息在 addresses 表中更完整",
            "note": "查询城市占比时，应使用 addresses 表并坚持使用它"
        },
        "district": {
            "recommended_table": "addresses",
            "reason": "区县信息只在 addresses 表中存在",
            "note": "查询区县信息必须使用 addresses 表"
        }
    }

    # 检查当前表是否为 users，且包含地理位置字段
    if table_name.lower() in ["users", "user", "customers", "customer"]:
        column_names = [col.get("name", "").lower() for col in columns]
        for geo_field, recommendation in geo_field_table_map.items():
            if geo_field in column_names:
                logger.debug(f"[表推荐] 检测到 {geo_field} 字段在 {table_name} 表中，"
                           f"建议使用 {recommendation['recommended_table']} 表")
                return {
                    "current_table": table_name,
                    "has_geo_field": geo_field,
                    "recommended_table": recommendation["recommended_table"],
                    "reason": recommendation["reason"],
                    "note": recommendation["note"]
                }

    # 如果是 addresses 表，确认它是地理位置查询的正确表
    if table_name.lower() in ["addresses", "address"]:
        column_names = [col.get("name", "").lower() for col in columns]
        geo_fields = [f for f in ["province", "city", "district"] if f in column_names]
        if geo_fields:
            logger.debug(f"[表推荐] {table_name} 表是地理位置查询的正确表，包含: {geo_fields}")
            return {
                "current_table": table_name,
                "is_recommended": True,
                "geo_fields": geo_fields,
                "note": "这是地理位置查询的正确表，请坚持使用此表完成所有相关查询"
            }

    return None


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

    # 从 thread-local 获取 connection_id 和 tenant_id（如果未通过参数传递）
    if connection_id is None:
        connection_id, _, tenant_id = _get_connection_context()
    else:
        _, _, tenant_id = _get_connection_context()

    # 确保有租户 ID 用于缓存隔离
    cache_tenant_id = tenant_id or "default_tenant"

    # 检查租户隔离的缓存
    cache_key = _make_cache_key("get_schema", table_name, connection_id)
    cached = _schema_cache.get(cache_tenant_id, cache_key)
    if cached is not None:
        logger.debug(f"get_schema({table_name}): 返回缓存结果 (tenant={cache_tenant_id})")
        return cached

    # 获取数据源连接信息
    database_url, connection_info = get_database_url(connection_id)

    # 如果是 Excel 连接，返回列信息
    if _is_excel_connection(database_url):
        logger.debug(f"get_schema({table_name}): Detected Excel data source, getting columns")
        try:
            file_path = _get_excel_file_path(database_url)
            import pandas as pd

            # 读取 Excel 工作表
            df = _read_excel_file(file_path, sheet_name=table_name, nrows=0)

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
                "primary_key": None,  # Excel 没有传统主键
                "primary_keys": [],  # Excel 没有传统主键
                "success": True,
                "data_source": "excel"
            }

            result_str = json.dumps(result, ensure_ascii=False)
            _schema_cache.set(cache_tenant_id, cache_key, result_str)
            logger.debug(f"get_schema({table_name}): Excel 工作表，{len(columns)} 列 (tenant={cache_tenant_id})")

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

        # 🔧 新增：查询主键信息
        cursor.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
            AND i.indisprimary
        """, (table_name,))
        primary_key_rows = cursor.fetchall()
        primary_keys = [row[0] for row in primary_key_rows] if primary_key_rows else []

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
            col_name = row[0]
            is_primary_key = col_name in primary_keys
            columns.append({
                "name": col_name,
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
                "is_primary_key": is_primary_key  # 🔧 新增：标注主键
            })

        cursor.close()
        conn.close()

        # 🔧 新增：返回主键信息
        result = {
            "table_name": table_name,
            "columns": columns,
            "column_count": len(columns),
            "primary_key": primary_keys[0] if primary_keys else None,  # 主键列名
            "primary_keys": primary_keys,  # 所有主键列（支持复合主键）
            "success": True
        }

        # 🔧 新增：表推荐机制（仅记录日志，不返回给 AI）
        # 避免因返回值格式改变导致 AI 陷入循环
        recommendation = _get_table_recommendation_for_query(table_name, columns)
        if recommendation:
            # 仅记录日志，不添加到返回结果（避免 AI 陷入循环）
            logger.warning(f"[表推荐] {table_name} 表检测到地理位置字段，建议使用 addresses 表")

        result_str = json.dumps(result, ensure_ascii=False)
        # 存入租户隔离的缓存
        _schema_cache.set(cache_tenant_id, cache_key, result_str)
        logger.debug(f"get_schema({table_name}): 查询成功，缓存结果 ({len(columns)} 列) (tenant={cache_tenant_id})")

        return result_str

    except Exception as e:
        logger.error(f"Get schema error: {e}")
        error_str = json.dumps({
            "error": str(e),
            "error_type": "execution_error"
        }, ensure_ascii=False)
        return error_str


# ============================================================================
# 语义层文件系统工具 (Schema FS Tools)
# ============================================================================

from pathlib import Path

class SchemaFSValidator:
    """cube_schema 文件系统访问验证器"""
    
    # 指向 c:\data_agent\cube_schema
    # 计算方式：当前文件 (c:\data_agent\AgentV2\tools\database_tools.py) 的上级(tools)的上级(AgentV2)的上级(data_agent) / "cube_schema"
    ALLOWED_BASE_PATH = Path(__file__).parent.parent.parent / "cube_schema"

    @classmethod
    def validate_path(cls, path: Path) -> bool:
        """严格验证路径，防止路径遍历攻击"""
        try:
            resolved = path.resolve()
            base = cls.ALLOWED_BASE_PATH.resolve()
            # 检查 resolved 是否以 base 开头
            return str(resolved).startswith(str(base))
        except (ValueError, RuntimeError, Exception) as e:
            logger.warning(f"Path validation failed: {e}")
            return False

    @classmethod
    def sanitize_content(cls, content: str, max_length: int = 5000) -> str:
        """限制返回内容大小，避免 Token 爆炸"""
        if len(content) > max_length:
            return content[:max_length] + "\n... (内容过长，已截断)"
        return content

def list_schema_files() -> str:
    """
    列出 cube_schema 目录下可用的语义层文档

    返回格式：JSON 数组，包含 filename, description, measures, dimensions

    使用场景：
    - 回答"数据库有哪些表？"
    - 了解数据结构概览
    """
    base_path = SchemaFSValidator.ALLOWED_BASE_PATH

    if not base_path.exists():
        logger.warning(f"Schema directory not found: {base_path}")
        return json.dumps({"error": "Schema directory not found"}, ensure_ascii=False)

    files_info = []
    try:
        # 查找 yaml 文件
        for yaml_file in sorted(base_path.glob("*.yaml")):
            files_info.append({
                "filename": yaml_file.name,
                "size": yaml_file.stat().st_size,
                "modified": time.ctime(yaml_file.stat().st_mtime)
            })
        
        # 查找 markdown 文档
        for md_file in sorted(base_path.glob("*.md")):
            files_info.append({
                "filename": md_file.name,
                "size": md_file.stat().st_size,
                "modified": time.ctime(md_file.stat().st_mtime)
            })
            
    except Exception as e:
        logger.error(f"Error listing schema files: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    return json.dumps(files_info, ensure_ascii=False, indent=2)


def read_schema_file(filename: str, section: Optional[str] = None) -> str:
    """
    读取 cube_schema 中指定文件的内容

    参数：
    - filename: 文件名（如 "Orders.yaml"）
    - section: 可选，只读取特定部分（measures/dimensions/description/sql_table）

    返回：文件内容（可被截断以控制 Token）

    使用场景：
    - 查看 Orders 表有哪些度量
    - 查看某个字段的数据类型
    - 了解表之间的关联关系
    """
    base_path = SchemaFSValidator.ALLOWED_BASE_PATH
    file_path = base_path / filename

    # 安全验证
    if not SchemaFSValidator.validate_path(file_path):
        return "错误：不允许访问该文件（路径非法）"

    if not file_path.exists():
        return f"错误：文件 {filename} 不存在"

    try:
        # 读取内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 可选：只返回特定部分 (针对 YAML 文件)
        if section and filename.endswith('.yaml'):
            lines = content.split('\n')
            in_section = False
            filtered_lines = []
            
            # 简单的文本分块逻辑 (根据缩进和冒号判断)
            found_section = False
            
            # 找到顶级键的缩进模式
            for line in lines:
                stripped = line.strip()
                
                # 检查是否是主要部分标题 (如 "measures:", "dimensions:")
                if stripped.startswith(f"{section}:"):
                    in_section = True
                    found_section = True
                    filtered_lines.append(line)
                    continue
                
                # 如果遇到下一个主要部分（顶级键），则停止
                # 假设顶级键可能没有缩进或缩进很少，这里使用简单的启发式
                if in_section and line and ':' in line and not line.strip().startswith('-') and not line.strip().startswith(' '):
                     # 如果这行看起来像是一个新的顶级key（例如 "dimensions:"），且不是当前section
                     if not stripped.startswith(f"{section}:") and not line.strip().startswith('#'):
                         # 这是一个新的顶级 section，结束当前 section
                         in_section = False
                
                if in_section:
                    filtered_lines.append(line)
            
            if found_section:
                content = '\n'.join(filtered_lines)
            else:
                 # 未找到 section，如果请求的是常见部分，提示未找到
                 if section in ["measures", "dimensions", "sql_table", "joins", "description"]:
                     content = f"未在文件 {filename} 中找到 '{section}' 部分。"

        # 限制大小
        return SchemaFSValidator.sanitize_content(content)
        
    except Exception as e:
        logger.error(f"Error reading schema file {filename}: {e}")
        return f"读取文件失败: {str(e)}"


def search_schema(keyword: str) -> str:
    """
    在所有 cube_schema 文件中搜索关键词

    参数：
    - keyword: 搜索关键词（如表名、字段名、度量名）

    返回：匹配的文件和内容片段

    使用场景：
    - 查找包含"收入"的所有度量
    - 搜索"customer_id"字段在哪些表中
    - 查找所有与"库存"相关的维度
    """
    base_path = SchemaFSValidator.ALLOWED_BASE_PATH

    if not base_path.exists():
        return "错误：cube_schema 目录不存在"

    results = []
    keyword_lower = keyword.lower()

    try:
        # 搜索 yaml 和 md 文件
        files = list(base_path.glob("*.yaml")) + list(base_path.glob("*.md"))
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if keyword_lower in content.lower():
                    # 提取匹配的行（上下文）
                    lines = content.split('\n')
                    matches = []
                    for i, line in enumerate(lines):
                        if keyword_lower in line.lower():
                            # 上下文：前后各2行
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            
                            # 构建上下文片段
                            context_lines = []
                            for j in range(start, end):
                                prefix = "> " if j == i else "  "
                                context_lines.append(f"{prefix}{lines[j]}")
                                
                            matches.append('\n'.join(context_lines))
                            
                            # 限制每个文件的匹配数，避免过多
                            if len(matches) >= 3:
                                break
                    
                    if matches:
                        results.append({
                            "file": file_path.name,
                            "matches": matches
                        })
            except Exception as e:
                logger.warning(f"读取文件 {file_path.name} 失败: {e}")

        if not results:
            return f"未找到包含 '{keyword}' 的内容"

        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"搜索出错: {str(e)}"


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

    # 创建 StructuredTool 对象 - 数据库工具
    tools = [
        StructuredTool.from_function(
            func=bound_execute_query,
            name="execute_query",
            description=(
                "✅ Execute SQL to get ACTUAL DATA from tables (NOT table names). "
                ""
                "🔴 CRITICAL: You MUST call list_tables() FIRST to get the actual table names! "
                "Use the EXACT table names returned by list_tables() - do not guess or translate. "
                ""
                "Table Name Rules: "
                "- If list_tables() returns Chinese names (销售订单表), use Chinese "
                "- If list_tables() returns English names (orders), use English "
                "- Do NOT assume table names - always check with list_tables() first "
                ""
                "Examples of questions that need THIS tool (after calling list_tables): "
                "- '有哪些地区？' → execute_query('SELECT * FROM 地区表') "
                "- 'what users exist' → execute_query('SELECT * FROM 用户表 LIMIT 100') "
                ""
                "Returns results in JSON format with columns and rows. "
                "Args: query (str): The SQL SELECT query to execute"
            )
        ),
        StructuredTool.from_function(
            func=bound_list_tables,
            name="list_tables",
            description=(
                "🔴 CRITICAL: List all TABLE NAMES in the database (NOT the data within tables). "
                ""
                "📋 MANDATORY: You MUST call this tool BEFORE any execute_query call to get the correct table names! "
                ""
                "Usage Rules: "
                "- ALWAYS call list_tables() first when you need to query data "
                "- Use the EXACT table names returned by list_tables() in your SQL "
                "- Do NOT guess table names - they may be Chinese (销售订单表) or English (orders) "
                ""
                "Returns meta-information like ['销售订单表', '用户表', 'orders'] (actual table names). "
                ""
                "📋 NEXT STEP: Call get_schema('table_name') to get COLUMN NAMES and TYPES! "
                "This is REQUIRED to understand what columns are available before querying. "
                ""
                "Args: None"
            )
        ),
        StructuredTool.from_function(
            func=bound_get_schema,
            name="get_schema",
            description=(
                "📋 Get the SCHEMA (COLUMN NAMES and DATA TYPES) for a specific table or Excel sheet. "
                ""
                "🔴 CRITICAL: Call this AFTER list_tables() to understand table structure before querying! "
                ""
                "**What it returns**: "
                "- table_name: The name of the table "
                "- columns: Array of column objects with: "
                "  - name: Column name (e.g., 'province', 'city', 'amount') "
                "  - type: Data type (text, integer, float, datetime, boolean) "
                "  - nullable: Whether null values are allowed "
                "- column_count: Total number of columns "
                ""
                "**Usage**: "
                "- Call get_schema('table_name') AFTER list_tables() to see available columns "
                "- Use the returned column names to build accurate SQL queries "
                "- Works for BOTH database tables AND Excel sheets "
                ""
                "**Example**: "
                "- list_tables() returns ['addresses'] "
                "- get_schema('addresses') returns columns: ['id', 'province', 'city', 'address'] "
                "- Now you can query: SELECT * FROM addresses WHERE province = '安徽' "
                ""
                "Args: table_name (str): The exact table/sheet name from list_tables()"
            )
        )
    ]

    # 🔥 新增：语义层文件系统工具（Schema FS Tools）
    # 这些工具不需要 connection_id，直接读取 cube_schema 目录
    tools.extend([
        StructuredTool.from_function(
            func=list_schema_files,
            name="list_schema_files",
            description=(
                "List all available semantic layer documents (YAML/MD files) in the cube_schema directory. "
                "Use this to answer questions like 'What tables are documented?' or 'What semantic layers are available?'. "
                "Returns a JSON array with filename, size, and modified time. "
                "Args: None"
            )
        ),
        StructuredTool.from_function(
            func=read_schema_file,
            name="read_schema_file",
            description=(
                "Read the content of a specific semantic layer document (YAML/MD file) from cube_schema. "
                "Use this to get detailed information about table structure, measures, dimensions, and business logic. "
                "Args: filename (str): The name of the file (e.g., 'Orders.yaml'); "
                "section (str, optional): Filter to specific section like 'measures', 'dimensions', 'sql_table'"
            )
        ),
        StructuredTool.from_function(
            func=search_schema,
            name="search_schema",
            description=(
                "Search for a keyword across all semantic layer documents in cube_schema. "
                "Use this to find which tables contain specific measures, dimensions, or business concepts. "
                "Args: keyword (str): The search keyword (e.g., 'revenue', 'customer_id')"
            )
        )
    ])

    logger.debug(
        "[get_database_tools] created %s tools with connection_id=%s",
        len(tools),
        connection_id,
    )
    return tools


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
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
