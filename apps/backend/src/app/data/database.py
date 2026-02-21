"""
# [DATABASE] 数据库连接配置

## [HEADER]
**文件名**: database.py
**职责**: PostgreSQL连接池配置、会话管理和数据库连接状态检查
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现数据库连接池和会话管理

## [INPUT]
- **database_url: str** - 数据库连接字符串（从配置中获取）
- **settings: Settings** - 配置对象（连接池参数等）
- **pool_size: int** - 连接池大小
- **max_overflow: int** - 连接池最大溢出连接数
- **pool_timeout: int** - 获取连接超时时间（秒）
- **pool_recycle: int** - 连接回收时间（秒）

## [OUTPUT]
- **engine: Engine** - SQLAlchemy数据库引擎实例
- **SessionLocal: sessionmaker** - 数据库会话工厂
- **Base: DeclarativeMeta** - ORM基础模型类
- **db: Session** - 数据库会话实例（生成器）
- **connection_status: bool** - 数据库连接状态（True/False）

## [LINK]
**上游依赖** (已读取源码):
- [../core/config.py](../core/config.py) - Settings类，数据库连接配置

**下游依赖** (已读取源码):
- [./models.py](./models.py) - 数据模型定义，继承Base
- [../api/v1/endpoints/*.py](../api/v1/endpoints/) - API端点使用get_db()依赖注入
- [../main.py](../main.py) - 应用启动时检查数据库连接

**调用方**:
- 所有API端点 - 使用get_db()获取数据库会话
- 数据模型 - 继承Base类
- 健康检查端点 - 使用check_database_connection()

## [POS]
**路径**: backend/src/app/data/database.py
**模块层级**: Level 2 - 数据层核心
**依赖深度**: 直接依赖 config.py；被所有需要数据库操作的模块依赖
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

# 创建数据库引擎，根据数据库类型使用不同配置
if settings.database_url.startswith("sqlite"):
    # SQLite 配置
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL 配置，优化的连接池配置
    engine = create_engine(
        settings.database_url,
        # 连接池大小配置
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,  # 连接前检查连接有效性
        pool_timeout=settings.database_pool_timeout,  # 获取连接超时时间（秒）
        pool_recycle=settings.database_pool_recycle,  # 连接回收时间（秒），防止连接泄漏
        echo=settings.debug,
        # 连接池监控配置
        connect_args={
            "application_name": settings.app_name,
            "connect_timeout": settings.database_connect_timeout,
            "options": "-c timezone=UTC",
        },
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    检查数据库连接状态
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.debug("Database connection: OK")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def create_tables():
    """
    创建所有数据表并初始化默认数据
    """
    try:
        # 导入所有模型以确保它们被注册到 Base.metadata
        from .models import (
            Tenant, DataSourceConnection, KnowledgeDocument,
            TenantConfig, QueryLog, ExplanationLog,
            FusionResult, ReasoningPath, TenantStatus,
            SQLErrorMemory, SQLErrorType  # SQL错误记忆系统
        )
        _ = (
            DataSourceConnection,
            KnowledgeDocument,
            TenantConfig,
            QueryLog,
            ExplanationLog,
            FusionResult,
            ReasoningPath,
            SQLErrorMemory,
            SQLErrorType,
        )

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # 创建默认租户（如果不存在）
        db = SessionLocal()
        try:
            existing_tenant = db.query(Tenant).filter(Tenant.id == "default_tenant").first()
            if not existing_tenant:
                default_tenant = Tenant(
                    id="default_tenant",
                    email="admin@dataagent.local",
                    status=TenantStatus.ACTIVE,
                    display_name="Default Tenant",
                    settings={"timezone": "UTC", "language": "zh-CN"},
                    storage_quota_mb=1024
                )
                db.add(default_tenant)
                db.commit()
                logger.info("Default tenant created successfully")
            else:
                logger.info("Default tenant already exists")
        except Exception as tenant_error:
            db.rollback()
            logger.warning(f"Could not create default tenant: {tenant_error}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_pool_status() -> dict:
    """
    获取数据库连接池状态信息
    """
    try:
        # SQLite不支持连接池
        if settings.database_url.startswith("sqlite"):
            return {
                "database_type": "sqlite",
                "status": "healthy",
                "message": "SQLite does not use connection pooling",
            }

        pool = engine.pool
        # 🔥 第二步修复：兼容性修复，SQLAlchemy 1.4+中QueuePool没有invalid属性
        try:
            # 尝试获取 pool 的状态，如果不支持 invalid 属性则跳过
            pool_info = {
                "size": pool.size(),
                "checkedin": pool.checkedin(),
                "checkedout": pool.checkedout(),
                "overflow": pool.overflow()
            }
            
            # 尝试获取invalid状态（如果方法存在）
            invalid_count = 0
            if hasattr(pool, 'invalid'):
                try:
                    invalid_count = pool.invalid() if callable(pool.invalid) else pool.invalid
                except (AttributeError, TypeError):
                    # 如果invalid不可用，设为0
                    invalid_count = 0
        except Exception as e:
            logger.warning(f"无法获取详细 Pool 状态: {e}")
            pool_info = {
                "size": 0,
                "checkedin": 0,
                "checkedout": 0,
                "overflow": 0
            }
            invalid_count = 0
        
        # 尝试获取 max_overflow（SQLAlchemy 2.0 兼容性修复）
        max_overflow = 0
        try:
            if hasattr(pool, 'max_overflow'):
                max_overflow = pool.max_overflow
            elif hasattr(pool, '_max_overflow'):
                max_overflow = pool._max_overflow
            else:
                # 如果无法获取，使用配置中的值
                max_overflow = getattr(settings, 'database_max_overflow', 0)
        except (AttributeError, TypeError) as e:
            logger.warning(f"无法获取 max_overflow 属性: {e}，使用默认值 0")
            max_overflow = getattr(settings, 'database_max_overflow', 0)
        
        pool_status = {
            "database_type": "postgresql",
            "pool_size": pool_info["size"],
            "checked_in": pool_info["checkedin"],
            "checked_out": pool_info["checkedout"],
            "overflow": pool_info["overflow"],
            "invalid": invalid_count,
            "total_connections": pool_info["checkedout"] + pool_info["checkedin"],
            "pool_size_limit": pool_info["size"] + max_overflow,
            "status": "healthy",
        }

        # 检查连接池健康状态
        if pool_status["overflow"] > 0:
            pool_status["status"] = "warning"
        if pool_status["invalid"] > 0:
            pool_status["status"] = "critical"

        logger.debug(f"Database pool status: {pool_status}")
        return pool_status

    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        return {"status": "error", "error": str(e)}


def log_pool_health():
    """
    记录连接池健康状态（用于监控）
    """
    try:
        pool_status = get_pool_status()
        status_emoji = {
            "healthy": "[OK]",
            "warning": "[!]",
            "critical": "[RED]",
            "error": "[X]",
        }

        emoji = status_emoji.get(pool_status["status"], "[?]")
        if pool_status["status"] == "healthy":
            logger.debug(
                "%s Database Pool - Size: %s, Active: %s, Status: %s",
                emoji,
                pool_status.get("total_connections", "N/A"),
                pool_status.get("checked_out", "N/A"),
                pool_status["status"],
            )
        else:
            logger.warning(
                "%s Database Pool - Size: %s, Active: %s, Status: %s",
                emoji,
                pool_status.get("total_connections", "N/A"),
                pool_status.get("checked_out", "N/A"),
                pool_status["status"],
            )

    except Exception as e:
        logger.error(f"Failed to log pool health: {e}")
