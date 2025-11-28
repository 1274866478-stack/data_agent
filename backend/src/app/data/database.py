"""
数据库连接配置模块
PostgreSQL 连接池配置、会话管理
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
        logger.info("Database connection: OK")
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
            FusionResult, ReasoningPath, TenantStatus
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
        pool_status = {
            "database_type": "postgresql",
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "total_connections": pool.checkedout() + pool.checkedin(),
            "pool_size_limit": pool.size() + pool.max_overflow,
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
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "🔴",
            "error": "❌",
        }

        emoji = status_emoji.get(pool_status["status"], "❓")
        logger.info(
            "%s Database Pool - Size: %s, Active: %s, Status: %s",
            emoji,
            pool_status.get("total_connections", "N/A"),
            pool_status.get("checked_out", "N/A"),
            pool_status["status"],
        )

    except Exception as e:
        logger.error(f"Failed to log pool health: {e}")
