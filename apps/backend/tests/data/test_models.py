"""
数据库模型测试
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.data.models import Tenant, DataSourceConnection, KnowledgeDocument
from src.app.data.database import Base


class TestDatabaseModels:
    """数据库模型测试类"""

    @pytest.fixture(scope="function")
    def db_session(self):
        """创建测试数据库会话"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)

    def test_create_tenant(self, db_session):
        """测试创建租户模型"""
        tenant = Tenant(
            id="test-tenant-123",
            email="test@example.com",
            display_name="Test Tenant"
        )

        db_session.add(tenant)
        db_session.commit()
        db_session.refresh(tenant)

        assert tenant.id == "test-tenant-123"
        assert tenant.email == "test@example.com"
        assert tenant.display_name == "Test Tenant"
        assert tenant.status.value == "active"
        assert tenant.created_at is not None
        assert tenant.updated_at is not None

    def test_tenant_repr(self, db_session):
        """测试租户模型的字符串表示"""
        tenant = Tenant(
            id="test-tenant-123",
            email="test@example.com",
            display_name="Test Tenant"
        )

        db_session.add(tenant)
        db_session.commit()

        repr_str = repr(tenant)
        assert "test-tenant-123" in repr_str
        assert "test@example.com" in repr_str

    def test_create_data_source_connection(self, db_session):
        """测试创建数据源连接模型"""
        # 先创建租户
        tenant = Tenant(
            id="test-tenant-123",
            email="test@example.com",
            display_name="Test Tenant"
        )
        db_session.add(tenant)
        db_session.commit()

        # 创建数据源连接
        connection = DataSourceConnection(
            tenant_id=tenant.id,
            name="test-db",
            connection_type="postgresql",
            connection_string="postgresql://user:password@localhost:5432/testdb",
            host="localhost",
            port=5432,
            database_name="testdb",
            is_active=True
        )

        db_session.add(connection)
        db_session.commit()
        db_session.refresh(connection)

        assert connection.id is not None
        assert connection.tenant_id == tenant.id
        assert connection.name == "test-db"
        assert connection.connection_type == "postgresql"
        assert connection.host == "localhost"
        assert connection.port == 5432
        assert connection.database_name == "testdb"
        assert connection.created_at is not None
        assert connection.updated_at is not None

    def test_data_source_connection_repr(self, db_session):
        """测试数据源连接模型的字符串表示"""
        tenant = Tenant(id="test-tenant-123", email="test@example.com", display_name="Test Tenant")
        db_session.add(tenant)
        db_session.commit()

        connection = DataSourceConnection(
            tenant_id=tenant.id,
            name="test-db",
            connection_type="postgresql",
            connection_string="postgresql://user:password@localhost:5432/testdb"
        )
        db_session.add(connection)
        db_session.commit()

        repr_str = repr(connection)
        assert "test-db" in repr_str
        assert "postgresql" in repr_str

    def test_create_knowledge_document(self, db_session):
        """测试创建知识文档模型"""
        # 先创建租户
        tenant = Tenant(
            id="test-tenant-123",
            email="test@example.com",
            display_name="Test Tenant"
        )
        db_session.add(tenant)
        db_session.commit()

        # 创建知识文档
        document = KnowledgeDocument(
            tenant_id=tenant.id,
            title="Test Document",
            file_name="test.pdf",
            file_path="tenant-1/documents/test.pdf",
            file_size=1024,
            file_type="pdf",
            mime_type="application/pdf",
            processing_status="pending",
            vectorized=False,
            vector_count=0
        )

        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)

        assert document.id is not None
        assert document.tenant_id == tenant.id
        assert document.title == "Test Document"
        assert document.file_name == "test.pdf"
        assert document.file_size == 1024
        assert document.file_type == "pdf"
        assert document.processing_status == "pending"
        assert document.vectorized is False
        assert document.vector_count == 0
        assert document.uploaded_at is not None
        assert document.processed_at is None

    def test_knowledge_document_repr(self, db_session):
        """测试知识文档模型的字符串表示"""
        tenant = Tenant(id="test-tenant-123", email="test@example.com", display_name="Test Tenant")
        db_session.add(tenant)
        db_session.commit()

        document = KnowledgeDocument(
            tenant_id=tenant.id,
            title="Test Document",
            file_name="test.pdf",
            file_path="tenant-1/documents/test.pdf",
            file_size=1024,
            file_type="pdf",
            processing_status="pending"
        )
        db_session.add(document)
        db_session.commit()

        repr_str = repr(document)
        assert "Test Document" in repr_str
        assert "pending" in repr_str

    def test_tenant_relationships(self, db_session):
        """测试租户与数据源连接和文档的关系"""
        # 创建租户
        tenant = Tenant(
            name="test-tenant",
            display_name="Test Tenant"
        )
        db_session.add(tenant)
        db_session.commit()

        # 创建数据源连接
        connection = DataSourceConnection(
            tenant_id=tenant.id,
            name="test-db",
            connection_type="postgresql",
            connection_string="postgresql://user:password@localhost:5432/testdb"
        )
        db_session.add(connection)

        # 创建知识文档
        document = KnowledgeDocument(
            tenant_id=tenant.id,
            title="Test Document",
            file_name="test.pdf",
            file_path="tenant-1/documents/test.pdf",
            file_size=1024,
            file_type="pdf",
            processing_status="pending"
        )
        db_session.add(document)
        db_session.commit()

        # 验证关系
        db_session.refresh(tenant)
        assert len(tenant.data_source_connections) == 1
        assert len(tenant.knowledge_documents) == 1
        assert tenant.data_source_connections[0].name == "test-db"
        assert tenant.knowledge_documents[0].title == "Test Document"

    def test_model_validations(self, db_session):
        """测试模型字段验证"""
        # 测试必需字段
        with pytest.raises(Exception):  # SQLAlchemy会抛出异常
            tenant = Tenant()  # 缺少必需的id和email
            db_session.add(tenant)
            db_session.commit()

        # 测试字段长度限制
        long_email = "a" * 256  # 超过255字符限制
        with pytest.raises(Exception):
            tenant = Tenant(
                id="test-tenant",
                email=long_email
            )
            db_session.add(tenant)
            db_session.commit()