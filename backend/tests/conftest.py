"""
pytest 配置文件
"""

import os
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 设置测试环境变量（符合安全标准）
os.environ.setdefault('ENVIRONMENT', 'testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
os.environ.setdefault('MINIO_ACCESS_KEY', 'test_minio_access_key_for_testing_32chars')
os.environ.setdefault('MINIO_SECRET_KEY', 'test_minio_secret_key_for_testing_must_be_at_least_32_characters_long')
os.environ.setdefault('ZHIPUAI_API_KEY', 'test_zhipu_api_key_12345_for_testing_purposes')
os.environ.setdefault('CLERK_JWT_PUBLIC_KEY', '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJcds3xfn/ygWc
-----END PUBLIC KEY-----''')
os.environ.setdefault('CLERK_API_URL', 'https://test.clerk.dev')

from src.app.main import app
from src.app.data.database import get_db, Base
from src.app.core.config import settings

# 创建测试数据库（内存SQLite）
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_tenant_data():
    """示例租户数据"""
    return {
        "name": "test-tenant",
        "display_name": "Test Tenant",
        "description": "A test tenant for unit testing"
    }


@pytest.fixture
def sample_document_data():
    """示例文档数据"""
    return {
        "tenant_id": 1,
        "title": "Test Document",
        "file_name": "test.pdf",
        "file_size": 1024,
        "file_type": "pdf"
    }


@pytest.fixture
def sample_data_source_data():
    """示例数据源数据"""
    return {
        "tenant_id": 1,
        "name": "test-db-connection",
        "connection_type": "postgresql",
        "connection_string": "postgresql://user:password@localhost:5432/testdb",
        "host": "localhost",
        "port": 5432,
        "database_name": "testdb"
    }