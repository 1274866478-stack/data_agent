"""
SQLAlchemy 数据模型定义
Tenant, DataSourceConnection, KnowledgeDocument 模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, BigInteger, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
import enum

from .database import Base

# 使用通用的 JSON 类型代替 JSONB，以支持 SQLite 和 PostgreSQL
# 在 PostgreSQL 中会自动使用 JSONB
JSONB = JSON
from ..services.encryption_service import encryption_service
from ..services.database_factory import DatabaseAdapterFactory


class TenantStatus(str, enum.Enum):
    """租户状态枚举 - 继承str以便与数据库字符串值兼容"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Tenant(Base):
    """
    租户模型，存储租户基本信息
    支持Clerk用户集成和多租户SaaS架构
    """
    __tablename__ = "tenants"

    # 租户唯一标识符（来自认证服务）
    id = Column(String(255), primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)

    # 租户状态管理（Story要求）
    # 使用 values_callable 确保与数据库中的小写枚举值匹配
    status = Column(
        Enum(TenantStatus, values_callable=lambda x: [e.value for e in x]),
        default=TenantStatus.ACTIVE,
        nullable=False,
        index=True
    )

    # 租户基本信息
    display_name = Column(String(255), nullable=True)

    # 租户特定设置（Story要求的JSONB字段）
    settings = Column(JSONB, nullable=True)

    # 存储配额（Story要求）
    storage_quota_mb = Column(Integer, default=1024, nullable=False)  # 1GB默认配额

    # 时间戳（Story要求）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    data_source_connections = relationship("DataSourceConnection", back_populates="tenant")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="tenant")

    def __repr__(self):
        return f"<Tenant(id={self.id}, email='{self.email}', status={self.status.value if self.status else 'unknown'})>"

    @property
    def full_name(self) -> str:
        """获取用户显示名称"""
        return self.display_name or self.email or "Unknown User"

    def to_dict(self) -> dict:
        """转换为字典格式（Story规范）"""
        # 默认设置（如果未设置）
        default_settings = {
            "timezone": "UTC",
            "language": "en",
            "notification_preferences": {
                "email_notifications": True,
                "system_alerts": True
            },
            "ui_preferences": {
                "theme": "light",
                "dashboard_layout": "default"
            }
        }

        # 合并实际设置和默认设置
        settings = default_settings
        if self.settings:
            settings.update(self.settings)

        return {
            "id": self.id,
            "email": self.email,
            "status": self.status.value if self.status else "active",
            "display_name": self.display_name,
            "settings": settings,
            "storage_quota_mb": self.storage_quota_mb,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class DataSourceConnectionStatus(enum.Enum):
    """数据源连接状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class DocumentStatus(str, enum.Enum):
    """文档状态枚举 - Story 2.4规范
    注意：值必须为小写，与数据库中的document_status枚举类型匹配
    """
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"


class DataSourceConnection(Base):
    """
    数据源连接模型，存储数据库连接字符串（加密）
    符合Story 2.3要求的完整数据模型，实现敏感数据加密存储
    """
    __tablename__ = "data_source_connections"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    db_type = Column(String(50), nullable=False, default="postgresql")  # postgresql, mysql, etc.
    _connection_string = Column(Text, nullable=False)  # 私有字段，存储加密的连接字符串

    # 连接状态管理
    status = Column(Enum(DataSourceConnectionStatus), default=DataSourceConnectionStatus.TESTING, nullable=False, index=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    test_result = Column(JSONB, nullable=True)  # 最后测试结果详情

    # 连接配置（冗余存储，便于快速查询）
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    database_name = Column(String(100), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tenant = relationship("Tenant", back_populates="data_source_connections")

    def __repr__(self):
        # 不在repr中显示敏感信息
        return f"<DataSourceConnection(id={self.id}, name='{self.name}', type='{self.db_type}', status='{self.status.value}')>"

    @property
    def connection_string(self) -> str:
        """
        获取解密后的连接字符串（只读属性）

        Returns:
            str: 解密后的明文连接字符串
        """
        if not self._connection_string:
            return ""

        try:
            # 检查是否已加密
            if encryption_service.is_encrypted(self._connection_string):
                return encryption_service.decrypt_connection_string(self._connection_string)
            else:
                # 如果未加密（遗留数据），直接返回
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unencrypted connection string found for data source {self.id}")
                return self._connection_string
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decrypt connection string for data source {self.id}: {e}")
            raise RuntimeError("Failed to decrypt connection string")

    @connection_string.setter
    def connection_string(self, value: str):
        """
        设置连接字符串（自动加密）

        Args:
            value (str): 明文连接字符串
        """
        if not value:
            raise ValueError("Connection string cannot be empty")

        try:
            # 自动加密存储
            self._connection_string = encryption_service.encrypt_connection_string(value)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to encrypt connection string for data source {self.id}: {e}")
            raise RuntimeError("Failed to encrypt connection string")

    @property
    def is_active(self) -> bool:
        """检查连接是否处于活跃状态"""
        return self.status == DataSourceConnectionStatus.ACTIVE

    def update_test_result(self, test_result: dict):
        """更新测试结果"""
        self.test_result = test_result
        self.last_tested_at = datetime.now(timezone.utc)
        # 根据测试结果更新状态
        if test_result.get("success", False):
            self.status = DataSourceConnectionStatus.ACTIVE
        else:
            self.status = DataSourceConnectionStatus.ERROR
        self.updated_at = datetime.now(timezone.utc)

    def get_connection_info(self) -> dict:
        """
        获取安全的连接信息（不包含敏感的密码部分）

        Returns:
            dict: 包含连接类型、主机、端口等非敏感信息的字典
        """
        try:
            # 解析连接字符串以获取基本信息（不包含密码）
            conn_str = self.connection_string
            info = {
                "id": self.id,
                "name": self.name,
                "db_type": self.db_type,
                "host": self.host,
                "port": self.port,
                "database_name": self.database_name,
                "status": self.status.value,
                "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None
            }

            # 尝试从连接字符串中提取更多基本信息（安全方式）
            if self.db_type.lower() == "postgresql" and "://" in conn_str:
                # 提取主机、端口、数据库名等信息（不包含密码）
                import re
                # PostgreSQL连接字符串格式: postgresql://user:password@host:port/database
                match = re.match(r'postgresql://[^@]*@([^:/]+)(?::(\d+))?/([^?]+)', conn_str)
                if match:
                    info["parsed_host"] = match.group(1)
                    info["parsed_port"] = int(match.group(2)) if match.group(2) else 5432
                    info["parsed_database"] = match.group(3)

            return info

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to parse connection info for data source {self.id}: {e}")
            # 返回基本信息
            return {
                "id": self.id,
                "name": self.name,
                "db_type": self.db_type,
                "status": self.status.value,
                "error": "Failed to parse connection string"
            }

    def get_adapter(self):
        """
        获取对应的数据库适配器

        Returns:
            DatabaseInterface: 数据库适配器实例

        Raises:
            ValueError: 不支持的数据库类型
        """
        try:
            return DatabaseAdapterFactory.create_adapter(self.db_type)
        except ValueError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"无法为数据源 {self.id} 创建适配器: {e}")
            raise

    def get_supported_database_types(self) -> list:
        """
        获取支持的数据库类型列表

        Returns:
            list: 支持的数据库类型列表
        """
        return DatabaseAdapterFactory.get_supported_types()


class KnowledgeDocument(Base):
    """
    知识文档模型 - 完全符合Story 2.4规范
    """
    __tablename__ = "knowledge_documents"

    # Story规范: UUID主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Story规范: 租户ID外键
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)

    # Story规范: 文件基本信息
    file_name = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=False)  # MinIO 对象路径 (Story规范名称)

    # Story规范: 文件类型和大小
    file_type = Column(String(10), nullable=False)  # pdf, docx (Story规范限制长度)
    file_size = Column(BigInteger, nullable=False)  # 字节数 (Story规范使用BIGINT)
    mime_type = Column(String(100), nullable=False)  # MIME类型 (Story规范要求)

    # Story规范: 状态枚举
    # 使用values_callable确保枚举值与数据库中的document_status类型匹配
    status = Column(
        Enum(DocumentStatus, name='document_status', values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True
    )
    processing_error = Column(Text, nullable=True)  # 处理错误信息

    # Story规范: 索引时间
    indexed_at = Column(DateTime(timezone=True), nullable=True)  # 索引完成时间

    # 时间戳 (Story规范)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tenant = relationship("Tenant", back_populates="knowledge_documents")

    def __repr__(self):
        return f"<KnowledgeDocument(id={self.id}, file_name='{self.file_name}', tenant_id='{self.tenant_id}', status='{self.status.value}')>"

    def to_dict(self) -> dict:
        """转换为字典格式 - Story规范输出"""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "file_name": self.file_name,
            "storage_path": self.storage_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "status": self.status.value if self.status else None,
            "processing_error": self.processing_error,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def is_ready(self) -> bool:
        """检查文档是否已准备就绪"""
        return self.status == DocumentStatus.READY

    @property
    def is_processing(self) -> bool:
        """检查文档是否正在处理中"""
        return self.status == DocumentStatus.INDEXING

    @property
    def has_error(self) -> bool:
        """检查文档处理是否有错误"""
        return self.status == DocumentStatus.ERROR


class TenantConfig(Base):
    """
    租户配置模型，存储租户特定的配置信息
    支持API密钥、模型配置、速率限制等分层配置
    """
    __tablename__ = "tenant_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)

    # 配置类型：api_key, model_config, rate_limit, custom_settings
    config_type = Column(String(50), nullable=False, index=True)

    # 提供商：zhipu, openrouter, openai
    provider = Column(String(50), nullable=True, index=True)

    # 配置数据（JSON格式）
    config_data = Column(JSONB, nullable=False)

    # 优先级（数字越小优先级越高）
    priority = Column(Integer, default=1, nullable=False)

    # 是否激活
    is_active = Column(Boolean, default=True, nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tenant = relationship("Tenant")

    def __repr__(self):
        return f"<TenantConfig(id={self.id}, tenant_id='{self.tenant_id}', config_type='{self.config_type}', provider='{self.provider}')>"


class QueryStatus(enum.Enum):
    """查询状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class QueryType(enum.Enum):
    """查询类型枚举"""
    SQL = "sql"
    DOCUMENT = "document"
    MIXED = "mixed"


class QueryLog(Base):
    """
    查询日志模型，记录所有查询请求和响应信息
    支持租户隔离和查询分析
    """
    __tablename__ = "query_logs"

    # 查询唯一标识符
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # 租户关联（Story要求：强制租户隔离）
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)

    # 用户标识（来自JWT）
    user_id = Column(String(255), nullable=False, index=True)

    # 查询内容（Story要求）
    question = Column(Text, nullable=False)

    # 查询类型（自动分析）
    query_type = Column(Enum(QueryType), nullable=False, default=QueryType.MIXED, index=True)

    # 查询上下文（JSON格式）
    context = Column(JSONB, nullable=True)

    # 查询选项（JSON格式）
    options = Column(JSONB, nullable=True)

    # 响应摘要
    response_summary = Column(Text, nullable=True)

    # 详细响应（JSON格式，包含答案和引用）
    response_data = Column(JSONB, nullable=True)

    # XAI推理日志（Story要求：可解释性）
    explainability_log = Column(Text, nullable=True)

    # 查询哈希（用于缓存）
    query_hash = Column(String(64), nullable=True, index=True)

    # 缓存命中
    cache_hit = Column(Boolean, default=False, nullable=False)

    # 性能指标（Story要求）
    response_time_ms = Column(Integer, nullable=True)

    # 使用的token数量
    tokens_used = Column(Integer, nullable=True)

    # 查询状态（Story要求）
    status = Column(Enum(QueryStatus), default=QueryStatus.PENDING, nullable=False, index=True)

    # 错误信息
    error_message = Column(Text, nullable=True)

    # 错误代码
    error_code = Column(String(50), nullable=True)

    # 时间戳（Story要求）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tenant = relationship("Tenant")

    def to_dict(self) -> dict:
        """转换为字典格式 - Story规范输出"""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "question": self.question,
            "query_type": self.query_type.value if self.query_type else None,
            "context": self.context,
            "options": self.options,
            "response_summary": self.response_summary,
            "response_data": self.response_data,
            "explainability_log": self.explainability_log,
            "query_hash": self.query_hash,
            "cache_hit": self.cache_hit,
            "response_time_ms": self.response_time_ms,
            "tokens_used": self.tokens_used,
            "status": self.status.value if self.status else None,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def is_success(self) -> bool:
        """检查查询是否成功"""
        return self.status == QueryStatus.SUCCESS

    @property
    def is_error(self) -> bool:
        """检查查询是否有错误"""
        return self.status == QueryStatus.ERROR

    @property
    def is_processing(self) -> bool:
        """检查查询是否正在处理"""
        return self.status == QueryStatus.PROCESSING

    def __repr__(self):
        return f"<QueryLog(id={self.id}, tenant_id='{self.tenant_id}', status='{self.status.value if self.status else None}')>"


# ============================================================================
# XAI 和融合引擎相关数据模型 (Story 3.5)
# ============================================================================

class ExplanationLogStatus(enum.Enum):
    """解释日志状态枚举"""
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class FusionResultStatus(enum.Enum):
    """融合结果状态枚举"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICTS_DETECTED = "conflicts_detected"


class ExplanationLog(Base):
    """
    XAI解释日志模型
    存储查询的详细解释、推理路径和溯源信息
    """
    __tablename__ = "explanation_logs"

    # 基本标识信息
    id = Column(BigInteger, primary_key=True, index=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)

    # 关联查询信息
    query_id = Column(UUID(as_uuid=True), ForeignKey("query_logs.id"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    # 解释状态
    status = Column(Enum(ExplanationLogStatus), default=ExplanationLogStatus.GENERATING, nullable=False, index=True)

    # 解释步骤和推理路径
    explanation_steps = Column(JSONB, nullable=True)  # 存储解释步骤列表
    reasoning_path = Column(JSONB, nullable=True)     # 存储推理路径
    decision_tree = Column(JSONB, nullable=True)      # 存储决策树结构

    # 源数据追踪
    source_traces = Column(JSONB, nullable=True)      # 存储源数据追踪信息
    source_citations = Column(JSONB, nullable=True)   # 存储源引用信息

    # 置信度和不确定性
    confidence_explanation = Column(JSONB, nullable=True)
    uncertainty_quantification = Column(JSONB, nullable=True)

    # 替代答案
    alternative_answers = Column(JSONB, nullable=True)

    # 质量评估
    explanation_quality_score = Column(Integer, default=0)  # 0-100
    confidence_score = Column(Integer, default=0)           # 0-100
    completeness_score = Column(Integer, default=0)         # 0-100

    # 可视化数据
    visualization_data = Column(JSONB, nullable=True)

    # 处理信息
    processing_time_ms = Column(BigInteger, default=0)
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tenant = relationship("Tenant", back_populates="explanation_logs")
    query = relationship("QueryLog", back_populates="explanation_logs")

    def __repr__(self):
        return f"<ExplanationLog(id={self.id}, tenant_id='{self.tenant_id}', status='{self.status.value}')>"


class FusionResult(Base):
    """
    融合结果模型
    存储多源数据融合的结果和元数据
    """
    __tablename__ = "fusion_results"

    # 基本标识信息
    id = Column(BigInteger, primary_key=True, index=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)

    # 关联查询信息
    query_id = Column(UUID(as_uuid=True), ForeignKey("query_logs.id"), nullable=True, index=True)
    explanation_log_id = Column(BigInteger, ForeignKey("explanation_logs.id"), nullable=True, index=True)
    original_query = Column(Text, nullable=False)

    # 融合状态和结果
    status = Column(Enum(FusionResultStatus), default=FusionResultStatus.PROCESSING, nullable=False, index=True)
    fused_answer = Column(Text, nullable=False)

    # 融合元数据
    fusion_metadata = Column(JSONB, nullable=True)  # 存储融合过程的详细元数据
    processing_pipeline = Column(JSONB, nullable=True)  # 存储处理管道信息

    # 数据源信息
    source_data_count = Column(Integer, default=0)
    source_types = Column(JSONB, nullable=True)  # 存储数据源类型分布
    source_details = Column(JSONB, nullable=True)  # 存储详细的数据源信息

    # 冲突信息
    conflicts_detected = Column(Integer, default=0)
    conflict_details = Column(JSONB, nullable=True)  # 存储冲突详情
    resolution_strategies = Column(JSONB, nullable=True)

    # 质量和置信度
    fusion_confidence_score = Column(Integer, default=0)  # 0-100
    answer_quality_score = Column(Integer, default=0)    # 0-100
    consistency_score = Column(Integer, default=0)        # 0-100
    completeness_score = Column(Integer, default=0)      # 0-100

    # 融合算法信息
    fusion_algorithm_used = Column(String(100), nullable=True)
    algorithm_parameters = Column(JSONB, nullable=True)

    # 性能指标
    processing_time_ms = Column(BigInteger, default=0)
    memory_usage_mb = Column(Integer, default=0)

    # 错误信息
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tenant = relationship("Tenant", back_populates="fusion_results")
    query = relationship("QueryLog", back_populates="fusion_results")
    explanation_log = relationship("ExplanationLog", back_populates="fusion_results")

    def is_successful(self) -> bool:
        """检查融合是否成功"""
        return self.status == FusionResultStatus.COMPLETED

    def has_conflicts(self) -> bool:
        """检查是否有冲突"""
        return self.conflicts_detected > 0

    def get_overall_quality_score(self) -> int:
        """获取综合质量分数"""
        scores = [
            self.fusion_confidence_score,
            self.answer_quality_score,
            self.consistency_score,
            self.completeness_score
        ]
        valid_scores = [s for s in scores if s is not None and s > 0]
        return int(sum(valid_scores) / len(valid_scores)) if valid_scores else 0

    def __repr__(self):
        return f"<FusionResult(id={self.id}, tenant_id='{self.tenant_id}', status='{self.status.value}')>"


class ReasoningPath(Base):
    """
    推理路径模型
    存储详细的推理步骤和逻辑链
    """
    __tablename__ = "reasoning_paths"

    # 基本标识信息
    id = Column(BigInteger, primary_key=True, index=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)

    # 关联信息
    query_id = Column(UUID(as_uuid=True), ForeignKey("query_logs.id"), nullable=True, index=True)
    explanation_log_id = Column(BigInteger, ForeignKey("explanation_logs.id"), nullable=True, index=True)
    fusion_result_id = Column(BigInteger, ForeignKey("fusion_results.id"), nullable=True, index=True)

    # 推理路径内容
    path_name = Column(String(200), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False)  # e.g., "analysis", "synthesis", "validation"

    # 推理步骤内容
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)

    # 证据和支持
    evidence = Column(JSONB, nullable=True)           # 支持该步骤的证据
    confidence = Column(Integer, default=0)           # 0-100，该步骤的置信度
    supporting_data = Column(JSONB, nullable=True)    # 支持该步骤的数据

    # 决策因素
    decision_factors = Column(JSONB, nullable=True)   # 影响决策的因素
    assumptions = Column(JSONB, nullable=True)        # 该步骤的假设
    limitations = Column(JSONB, nullable=True)        # 该步骤的限制

    # 关联关系
    parent_step_id = Column(BigInteger, nullable=True, index=True)
    child_step_ids = Column(JSONB, nullable=True)     # 子步骤ID列表

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tenant = relationship("Tenant", back_populates="reasoning_paths")
    query = relationship("QueryLog", back_populates="reasoning_paths")
    explanation_log = relationship("ExplanationLog", back_populates="reasoning_paths")
    fusion_result = relationship("FusionResult", back_populates="reasoning_paths")

    def __repr__(self):
        return f"<ReasoningPath(id={self.id}, step_number={self.step_number}, title='{self.title}')>"


# 添加反向关系到Tenant模型
if hasattr(Tenant, '__table__'):
    # 动态添加反向关系，避免循环导入
    Tenant.explanation_logs = relationship("ExplanationLog", back_populates="tenant", cascade="all, delete-orphan")
    Tenant.fusion_results = relationship("FusionResult", back_populates="tenant", cascade="all, delete-orphan")
    Tenant.reasoning_paths = relationship("ReasoningPath", back_populates="tenant", cascade="all, delete-orphan")

# 添加反向关系到QueryLog模型
if hasattr(QueryLog, '__table__'):
    QueryLog.explanation_logs = relationship("ExplanationLog", back_populates="query", cascade="all, delete-orphan")
    QueryLog.fusion_results = relationship("FusionResult", back_populates="query", cascade="all, delete-orphan")
    QueryLog.reasoning_paths = relationship("ReasoningPath", back_populates="query", cascade="all, delete-orphan")

# 添加反向关系到ExplanationLog模型
if hasattr(ExplanationLog, '__table__'):
    ExplanationLog.fusion_results = relationship("FusionResult", back_populates="explanation_log", cascade="all, delete-orphan")
    ExplanationLog.reasoning_paths = relationship("ReasoningPath", back_populates="explanation_log", cascade="all, delete-orphan")

# 添加反向关系到FusionResult模型
if hasattr(FusionResult, '__table__'):
    FusionResult.reasoning_paths = relationship("ReasoningPath", back_populates="fusion_result", cascade="all, delete-orphan")