"""
查询上下文服务
Story 3.1: 租户隔离的查询上下文管理
包含完善的事务管理机制
"""

import asyncio
from typing import Dict, Any, Optional, List, ContextManager
from contextlib import contextmanager
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.app.data.models import Tenant, DataSourceConnection, KnowledgeDocument, QueryLog, QueryStatus
from src.app.middleware.tenant_context import get_current_tenant_id, get_current_tenant
from src.app.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()


class DatabaseTransactionManager:
    """
    数据库事务管理器
    提供完整的事务回滚机制和错误处理
    """

    def __init__(self, db: Session):
        """
        初始化事务管理器

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self._transaction_stack = []  # 事务栈，支持嵌套事务
        self._savepoints = {}        # 保存点字典

    @contextmanager
    def transaction(self, rollback_on_error: bool = True):
        """
        事务上下文管理器

        Args:
            rollback_on_error: 发生错误时是否自动回滚

        Yields:
            Session: 数据库会话

        Example:
            with transaction_manager.transaction() as db:
                # 执行数据库操作
                db.add(some_object)
                db.commit()
        """
        import uuid
        transaction_id = str(uuid.uuid4())
        self._transaction_stack.append(transaction_id)

        try:
            logger.debug(f"Transaction started: {transaction_id}")
            yield self.db

            # 如果没有异常，提交事务
            if not self.db.in_transaction():
                logger.debug(f"No active transaction to commit: {transaction_id}")
            else:
                self.db.commit()
                logger.debug(f"Transaction committed: {transaction_id}")

        except Exception as e:
            logger.error(f"Transaction failed: {transaction_id}, error: {e}")

            if rollback_on_error:
                try:
                    if self.db.in_transaction():
                        self.db.rollback()
                        logger.debug(f"Transaction rolled back: {transaction_id}")
                    else:
                        logger.warning(f"No active transaction to rollback: {transaction_id}")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed for transaction {transaction_id}: {rollback_error}")
                    raise RuntimeError(f"Transaction failed and rollback also failed: {rollback_error}")

            raise

        finally:
            # 清理事务栈
            if transaction_id in self._transaction_stack:
                self._transaction_stack.remove(transaction_id)
            logger.debug(f"Transaction context cleaned up: {transaction_id}")

    def safe_commit(self) -> bool:
        """
        安全提交事务

        Returns:
            bool: 提交是否成功
        """
        try:
            if self.db.in_transaction():
                self.db.commit()
                logger.debug("Transaction committed successfully")
                return True
            else:
                logger.warning("No active transaction to commit")
                return True  # 没有事务也算成功
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            try:
                self.db.rollback()
                logger.debug("Transaction rolled back after commit failure")
            except Exception as rollback_error:
                logger.error(f"Rollback failed after commit failure: {rollback_error}")
            return False

    def safe_rollback(self) -> bool:
        """
        安全回滚事务

        Returns:
            bool: 回滚是否成功
        """
        try:
            if self.db.in_transaction():
                self.db.rollback()
                logger.debug("Transaction rolled back successfully")
                return True
            else:
                logger.warning("No active transaction to rollback")
                return True  # 没有事务也算成功
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def is_in_transaction(self) -> bool:
        """
        检查是否在事务中

        Returns:
            bool: 是否在活跃事务中
        """
        return self.db.in_transaction()

    def get_transaction_depth(self) -> int:
        """
        获取当前事务栈深度

        Returns:
            int: 事务栈深度
        """
        return len(self._transaction_stack)


class QueryLimits:
    """查询限制配置"""

    def __init__(self, tenant_config: Optional[Dict[str, Any]] = None):
        # 默认限制（Story要求）
        self.max_queries_per_hour = tenant_config.get('max_queries_per_hour', 100) if tenant_config else 100
        self.max_concurrent_queries = tenant_config.get('max_concurrent_queries', 5) if tenant_config else 5
        self.max_query_length = tenant_config.get('max_query_length', 1000) if tenant_config else 1000
        self.query_timeout_seconds = tenant_config.get('query_timeout_seconds', 60) if tenant_config else 60


class QueryContext:
    """
    查询上下文管理器
    Story 3.1: 租户隔离的查询上下文服务
    包含完善的事务管理机制
    """

    def __init__(self, db: Session, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.tenant = self._get_tenant()
        self.transaction_manager = DatabaseTransactionManager(db)
        self.limits = QueryLimits(self.tenant.settings if self.tenant else None)

    def _get_tenant(self) -> Optional[Tenant]:
        """获取租户信息"""
        try:
            return self.db.query(Tenant).filter(
                Tenant.id == self.tenant_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get tenant {self.tenant_id}: {e}")
            return None

    def get_tenant_data_sources(self) -> List[DataSourceConnection]:
        """
        获取租户的数据源连接
        Story要求：只返回属于当前租户的活跃数据源

        Returns:
            List[DataSourceConnection]: 租户的数据源列表
        """
        try:
            data_sources = self.db.query(DataSourceConnection).filter(
                and_(
                    DataSourceConnection.tenant_id == self.tenant_id,
                    DataSourceConnection.is_active == True
                )
            ).all()

            logger.info(f"Retrieved {len(data_sources)} data sources for tenant {self.tenant_id}")
            return data_sources

        except Exception as e:
            logger.error(f"Failed to get data sources for tenant {self.tenant_id}: {e}")
            return []

    def get_tenant_documents(self) -> List[KnowledgeDocument]:
        """
        获取租户的知识文档
        Story要求：只返回属于当前租户的已就绪文档

        Returns:
            List[KnowledgeDocument]: 租户的文档列表
        """
        try:
            documents = self.db.query(KnowledgeDocument).filter(
                and_(
                    KnowledgeDocument.tenant_id == self.tenant_id,
                    KnowledgeDocument.status == 'ready'  # 只返回已就绪的文档
                )
            ).all()

            logger.info(f"Retrieved {len(documents)} documents for tenant {self.tenant_id}")
            return documents

        except Exception as e:
            logger.error(f"Failed to get documents for tenant {self.tenant_id}: {e}")
            return []

    def check_rate_limits(self) -> tuple[bool, Optional[str]]:
        """
        检查查询频率限制
        Story要求：实现租户级别的查询限流

        Returns:
            tuple[bool, Optional[str]]: (是否允许查询, 错误信息)
        """
        try:
            # 检查每小时查询限制
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_queries = self.db.query(QueryLog).filter(
                and_(
                    QueryLog.tenant_id == self.tenant_id,
                    QueryLog.created_at >= one_hour_ago
                )
            ).count()

            if recent_queries >= self.limits.max_queries_per_hour:
                error_msg = f"Query rate limit exceeded. Maximum {self.limits.max_queries_per_hour} queries per hour allowed."
                logger.warning(f"Rate limit exceeded for tenant {self.tenant_id}: {recent_queries}/{self.limits.max_queries_per_hour}")
                return False, error_msg

            # 检查并发查询限制
            active_queries = self.db.query(QueryLog).filter(
                and_(
                    QueryLog.tenant_id == self.tenant_id,
                    QueryLog.status == QueryStatus.PROCESSING
                )
            ).count()

            if active_queries >= self.limits.max_concurrent_queries:
                error_msg = f"Too many concurrent queries. Maximum {self.limits.max_concurrent_queries} concurrent queries allowed."
                logger.warning(f"Concurrent query limit exceeded for tenant {self.tenant_id}: {active_queries}/{self.limits.max_concurrent_queries}")
                return False, error_msg

            logger.info(f"Rate limit check passed for tenant {self.tenant_id}: {recent_queries}/{self.limits.max_queries_per_hour} hourly, {active_queries}/{self.limits.max_concurrent_queries} concurrent")
            return True, None

        except Exception as e:
            logger.error(f"Failed to check rate limits for tenant {self.tenant_id}: {e}")
            return False, "Failed to check rate limits"

    def log_query_request(self, query_id: str, question: str, context: Optional[Dict[str, Any]] = None,
                         options: Optional[Dict[str, Any]] = None, query_hash: Optional[str] = None) -> QueryLog:
        """
        记录查询请求（使用事务管理器）
        Story要求：完整的查询日志记录

        Args:
            query_id: 查询ID
            question: 查询问题
            context: 查询上下文
            options: 查询选项
            query_hash: 查询哈希

        Returns:
            QueryLog: 查询日志记录

        Raises:
            RuntimeError: 数据库操作失败时
        """
        with self.transaction_manager.transaction() as db:
            try:
                query_log = QueryLog(
                    id=query_id,
                    tenant_id=self.tenant_id,
                    user_id=self.user_id,
                    question=question,
                    context=context,
                    options=options,
                    query_hash=query_hash,
                    status=QueryStatus.PENDING,
                    created_at=datetime.utcnow()
                )

                db.add(query_log)
                # 事务管理器会在context manager退出时自动提交
                logger.info(f"Query request logged: {query_id} for tenant {self.tenant_id}")
                return query_log

            except Exception as e:
                logger.error(f"Failed to log query request: {e}")
                raise RuntimeError(f"Failed to log query request: {e}")

    def update_query_status(self, query_id: str, status: QueryStatus,
                           response_summary: Optional[str] = None,
                           response_data: Optional[Dict[str, Any]] = None,
                           explainability_log: Optional[str] = None,
                           response_time_ms: Optional[int] = None,
                           tokens_used: Optional[int] = None,
                           cache_hit: bool = False,
                           error_message: Optional[str] = None,
                           error_code: Optional[str] = None) -> bool:
        """
        更新查询状态
        Story要求：查询状态跟踪和结果记录

        Args:
            query_id: 查询ID
            status: 新状态
            response_summary: 响应摘要
            response_data: 响应数据
            explainability_log: 解释性日志
            response_time_ms: 响应时间
            tokens_used: token使用量
            cache_hit: 是否命中缓存
            error_message: 错误信息
            error_code: 错误代码

        Returns:
            bool: 更新是否成功
        """
        try:
            query_log = self.db.query(QueryLog).filter(
                and_(
                    QueryLog.id == query_id,
                    QueryLog.tenant_id == self.tenant_id
                )
            ).first()

            if not query_log:
                logger.warning(f"Query log not found: {query_id}")
                return False

            # 更新字段
            query_log.status = status
            query_log.updated_at = datetime.utcnow()

            if response_summary is not None:
                query_log.response_summary = response_summary
            if response_data is not None:
                query_log.response_data = response_data
            if explainability_log is not None:
                query_log.explainability_log = explainability_log
            if response_time_ms is not None:
                query_log.response_time_ms = response_time_ms
            if tokens_used is not None:
                query_log.tokens_used = tokens_used
            if error_message is not None:
                query_log.error_message = error_message
            if error_code is not None:
                query_log.error_code = error_code

            query_log.cache_hit = cache_hit

            self.db.commit()

            logger.info(f"Query status updated: {query_id} -> {status.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update query status {query_id}: {e}")
            self.db.rollback()
            return False

    def get_cached_query(self, query_hash: str) -> Optional[QueryLog]:
        """
        获取缓存的查询结果
        Story要求：查询结果缓存

        Args:
            query_hash: 查询哈希

        Returns:
            Optional[QueryLog]: 缓存的查询日志
        """
        try:
            # 获取最近的成功查询结果
            cached_query = self.db.query(QueryLog).filter(
                and_(
                    QueryLog.tenant_id == self.tenant_id,
                    QueryLog.query_hash == query_hash,
                    QueryLog.status == QueryStatus.SUCCESS,
                    QueryLog.cache_hit == False,  # 不是缓存命中的查询
                    QueryLog.created_at >= datetime.utcnow() - timedelta(hours=1)  # 1小时内的缓存
                )
            ).order_by(QueryLog.created_at.desc()).first()

            if cached_query:
                logger.info(f"Cache hit for query hash: {query_hash}")
                return cached_query

            return None

        except Exception as e:
            logger.error(f"Failed to get cached query {query_hash}: {e}")
            return None

    def get_query_history(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        获取查询历史
        Story要求：查询历史记录

        Args:
            page: 页码
            page_size: 每页大小

        Returns:
            Dict[str, Any]: 查询历史信息
        """
        try:
            # 计算偏移量
            offset = (page - 1) * page_size

            # 查询总数
            total_count = self.db.query(QueryLog).filter(
                QueryLog.tenant_id == self.tenant_id
            ).count()

            # 查询分页数据
            query_logs = self.db.query(QueryLog).filter(
                QueryLog.tenant_id == self.tenant_id
            ).order_by(QueryLog.created_at.desc()).offset(offset).limit(page_size).all()

            # 转换为字典格式
            queries = []
            for log in query_logs:
                query_dict = {
                    "query_id": str(log.id),
                    "question": log.question,
                    "status": log.status.value,
                    "response_time_ms": log.response_time_ms,
                    "cache_hit": log.cache_hit,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                queries.append(query_dict)

            return {
                "queries": queries,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }

        except Exception as e:
            logger.error(f"Failed to get query history for tenant {self.tenant_id}: {e}")
            return {
                "queries": [],
                "total_count": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

    def clear_query_cache(self, query_hash: Optional[str] = None) -> tuple[bool, str]:
        """
        清除查询缓存
        Story要求：查询缓存管理

        Args:
            query_hash: 特定查询的哈希，如果为None则清除所有缓存

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if query_hash:
                # 清除特定查询的缓存
                deleted_count = self.db.query(QueryLog).filter(
                    and_(
                        QueryLog.tenant_id == self.tenant_id,
                        QueryLog.query_hash == query_hash,
                        QueryLog.cache_hit == True
                    )
                ).delete()
                message = f"Cleared {deleted_count} cached entries for query hash {query_hash}"
            else:
                # 清除所有缓存
                deleted_count = self.db.query(QueryLog).filter(
                    and_(
                        QueryLog.tenant_id == self.tenant_id,
                        QueryLog.cache_hit == True
                    )
                ).delete()
                message = f"Cleared {deleted_count} cached entries for tenant {self.tenant_id}"

            self.db.commit()
            logger.info(message)
            return True, message

        except Exception as e:
            error_msg = f"Failed to clear query cache: {e}"
            logger.error(error_msg)
            self.db.rollback()
            return False, error_msg


# 工厂函数
def create_query_context(db: Session, tenant_id: str, user_id: str) -> QueryContext:
    """
    创建查询上下文实例

    Args:
        db: 数据库会话
        tenant_id: 租户ID
        user_id: 用户ID

    Returns:
        QueryContext: 查询上下文实例
    """
    return QueryContext(db, tenant_id, user_id)


# 依赖注入函数
def get_query_context(
    db: Session,
    tenant_id: str = None,
    user_id: str = None
) -> QueryContext:
    """
    获取查询上下文的依赖注入函数

    Args:
        db: 数据库会话
        tenant_id: 租户ID（可选，从上下文获取）
        user_id: 用户ID（可选，从上下文获取）

    Returns:
        QueryContext: 查询上下文实例
    """
    if not tenant_id:
        tenant_id = get_current_tenant_id()
    if not user_id:
        # 在实际应用中，这应该从JWT token中获取
        user_id = get_current_tenant_id()  # 临时使用tenant_id作为user_id

    return create_query_context(db, tenant_id, user_id)