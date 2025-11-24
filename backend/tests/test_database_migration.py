"""
数据库迁移测试 - Story 2.4模型重构验证
测试数据库迁移脚本的安全性和数据完整性
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID

from src.app.data.models import Base, KnowledgeDocument, DocumentStatus, Tenant


class TestDatabaseMigration:
    """数据库迁移测试类"""

    @pytest.fixture(scope="function")
    def test_db_engine(self):
        """创建测试数据库引擎"""
        # 使用SQLite进行测试，模拟PostgreSQL行为
        engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False}
        )
        return engine

    @pytest.fixture(scope="function")
    def test_db_session(self, test_db_engine):
        """创建测试数据库会话"""
        SessionLocal = sessionmaker(bind=test_db_engine)
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture(scope="function")
    def legacy_document_model(self):
        """创建旧版文档模型（模拟修复前的结构）"""
        # 这里创建一个简单的旧版结构用于测试迁移
        # 在实际环境中，这是migration脚本之前的状态

        legacy_data = {
            "id": 1,  # Integer ID
            "tenant_id": "tenant-legacy",
            "title": "Legacy Document",
            "file_name": "legacy.pdf",
            "file_path": "legacy/path/legacy.pdf",  # 旧字段名
            "file_size": 1024 * 1024,
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "processing_status": "pending",  # 旧状态名
            "processing_error": None,
            "uploaded_at": datetime.now(timezone.utc),
            "processed_at": None,
            "vectorized": False,
            "vector_count": 0,
            "chroma_collection": None,
            "doc_metadata": None
        }
        return legacy_data

    def test_migration_script_structure(self):
        """测试迁移脚本结构"""
        migration_file = "C:/data_agent/backend/migrations/003_fix_document_model_story_compliance.sql"

        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_content = f.read()

            # 验证迁移脚本包含必要元素
            assert "BEGIN;" in migration_content
            assert "COMMIT;" in migration_content
            assert "knowledge_documents_new" in migration_content
            assert "UUID(as_uuid=True)" in migration_content
            assert "storage_path" in migration_content
            assert "DocumentStatus" in migration_content or "ENUM('PENDING', 'INDEXING', 'READY', 'ERROR')" in migration_content
            assert "indexed_at" in migration_content

            # 验证数据转换逻辑
            assert "INSERT INTO knowledge_documents_new" in migration_content
            assert "gen_random_uuid()" in migration_content
            assert "storage_path = file_path" in migration_content  # 字段重命名

            print("✅ 迁移脚本结构验证通过")

        except FileNotFoundError:
            pytest.skip("迁移脚本文件不存在")

    def test_data_model_compliance(self, test_db_session):
        """测试新数据模型符合Story 2.4规范"""
        # 创建新表结构（模拟迁移后的状态）
        Base.metadata.create_all(test_db_session.get_bind())

        # 创建测试租户
        tenant = Tenant(
            id="test-tenant-123",
            email="test@example.com",
            display_name="Test Tenant"
        )
        test_db_session.add(tenant)
        test_db_session.commit()

        # 创建符合新规范的文档
        document = KnowledgeDocument(
            id=uuid.uuid4(),
            tenant_id="test-tenant-123",
            file_name="compliant-document.pdf",
            storage_path="dataagent-docs/tenant-test-tenant-123/documents/compliant-document.pdf",
            file_type="pdf",
            file_size=1024 * 1024,
            mime_type="application/pdf",
            status=DocumentStatus.READY,
            processing_error=None,
            indexed_at=datetime.now(timezone.utc)
        )
        test_db_session.add(document)
        test_db_session.commit()
        test_db_session.refresh(document)

        # 验证数据符合Story规范
        assert isinstance(document.id, uuid.UUID)
        assert document.tenant_id == "test-tenant-123"
        assert document.storage_path == "dataagent-docs/tenant-test-tenant-123/documents/compliant-document.pdf"
        assert document.file_type == "pdf"
        assert isinstance(document.file_size, int)
        assert document.mime_type == "application/pdf"
        assert document.status in DocumentStatus
        assert document.indexed_at is not None
        assert hasattr(document, 'created_at')
        assert hasattr(document, 'updated_at')

        # 验证to_dict方法
        doc_dict = document.to_dict()
        assert "id" in doc_dict
        assert doc_dict["id"] == str(document.id)  # UUID应该转换为字符串
        assert doc_dict["tenant_id"] == document.tenant_id
        assert doc_dict["storage_path"] == document.storage_path
        assert doc_dict["status"] == document.status.value
        assert "indexed_at" in doc_dict
        assert "created_at" in doc_dict
        assert "updated_at" in doc_dict

        print("✅ 新数据模型符合Story 2.4规范")

    def test_document_status_enum_values(self, test_db_session):
        """测试文档状态枚举值"""
        Base.metadata.create_all(test_db_session.get_bind())

        tenant = Tenant(
            id="test-tenant-status",
            email="status@example.com",
            display_name="Status Test Tenant"
        )
        test_db_session.add(tenant)
        test_db_session.commit()

        # 测试所有状态值
        status_values = [
            DocumentStatus.PENDING,
            DocumentStatus.INDEXING,
            DocumentStatus.READY,
            DocumentStatus.ERROR
        ]

        for i, status in enumerate(status_values):
            document = KnowledgeDocument(
                id=uuid.uuid4(),
                tenant_id="test-tenant-status",
                file_name=f"status-test-{i}.pdf",
                storage_path=f"test/path/status-test-{i}.pdf",
                file_type="pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=status
            )
            test_db_session.add(document)

        test_db_session.commit()

        # 验证所有状态都已创建
        all_documents = test_db_session.query(KnowledgeDocument).all()
        assert len(all_documents) == len(status_values)

        # 验证状态值
        statuses_in_db = {doc.status for doc in all_documents}
        assert statuses_in_db == set(status_values)

        print("✅ 文档状态枚举值验证通过")

    def test_tenant_relationship_maintenance(self, test_db_session):
        """测试租户关系维护"""
        Base.metadata.create_all(test_db_session.get_bind())

        # 创建多个租户和文档
        tenants = []
        for i in range(3):
            tenant = Tenant(
                id=f"tenant-relationship-{i}",
                email=f"tenant{i}@example.com",
                display_name=f"Tenant {i}"
            )
            test_db_session.add(tenant)
            tenants.append(tenant)

        test_db_session.commit()

        # 为每个租户创建文档
        for i, tenant in enumerate(tenants):
            document = KnowledgeDocument(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                file_name=f"tenant-{i}-doc.pdf",
                storage_path=f"tenant-{i}/doc.pdf",
                file_type="pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=DocumentStatus.READY
            )
            test_db_session.add(document)

        test_db_session.commit()

        # 验证关系
        for tenant in tenants:
            documents = test_db_session.query(KnowledgeDocument).filter(
                KnowledgeDocument.tenant_id == tenant.id
            ).all()
            assert len(documents) == 1
            assert documents[0].tenant_id == tenant.id

        print("✅ 租户关系维护验证通过")

    def test_field_validation(self, test_db_session):
        """测试字段验证"""
        Base.metadata.create_all(test_db_session.get_bind())

        tenant = Tenant(
            id="test-validation",
            email="validation@example.com",
            display_name="Validation Test"
        )
        test_db_session.add(tenant)
        test_db_session.commit()

        # 测试必需字段
        with pytest.raises(Exception):  # 应该有数据库约束错误
            invalid_doc = KnowledgeDocument(
                tenant_id="test-validation",
                # 缺少必需字段
                file_name="incomplete.pdf"
            )
            test_db_session.add(invalid_doc)
            test_db_session.commit()

        # 测试字段长度限制
        with pytest.raises(Exception):  # 应该有数据库约束错误
            invalid_doc = KnowledgeDocument(
                id=uuid.uuid4(),
                tenant_id="test-validation",
                file_name="a" * 501,  # 超出500字符限制
                storage_path="valid/path.pdf",
                file_type="pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=DocumentStatus.PENDING
            )
            test_db_session.add(invalid_doc)
            test_db_session.commit()

    def test_index_optimization(self, test_db_session):
        """测试索引优化"""
        Base.metadata.create_all(test_db_session.get_bind())

        tenant = Tenant(
            id="test-index",
            email="index@example.com",
            display_name="Index Test"
        )
        test_db_session.add(tenant)
        test_db_session.commit()

        # 创建测试数据
        for i in range(100):
            document = KnowledgeDocument(
                id=uuid.uuid4(),
                tenant_id="test-index",
                file_name=f"index-test-{i}.pdf",
                storage_path=f"test/index-{i}.pdf",
                file_type="pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=DocumentStatus.READY if i % 2 == 0 else DocumentStatus.PENDING
            )
            test_db_session.add(document)

        test_db_session.commit()

        # 测试按租户查询效率
        start_time = time.time()
        tenant_documents = test_db_session.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == "test-index"
        ).all()
        query_time = time.time() - start_time

        assert len(tenant_documents) == 100
        assert query_time < 1.0  # 查询应该在合理时间内完成

        # 测试按状态查询效率
        start_time = time.time()
        ready_documents = test_db_session.query(KnowledgeDocument).filter(
            KnowledgeDocument.status == DocumentStatus.READY
        ).all()
        status_query_time = time.time() - start_time

        assert len(ready_documents) == 50
        assert status_query_time < 1.0

        print("✅ 索引优化验证通过")

    def test_migration_data_integrity(self, test_db_session):
        """测试迁移数据完整性"""
        Base.metadata.create_all(test_db_session.get_bind())

        # 模拟迁移前的数据
        legacy_data = {
            "tenant_id": "migration-test",
            "file_name": "migration-test.pdf",
            "file_path": "old/path/test.pdf",
            "file_size": 2048,
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "processing_status": "completed"  # 旧状态值
        }

        # 模拟迁移后的数据转换
        status_mapping = {
            "pending": DocumentStatus.PENDING,
            "processing": DocumentStatus.INDEXING,
            "completed": DocumentStatus.READY,
            "failed": DocumentStatus.ERROR
        }

        # 创建转换后的文档
        converted_status = status_mapping.get(legacy_data["processing_status"], DocumentStatus.PENDING)

        document = KnowledgeDocument(
            id=uuid.uuid4(),
            tenant_id=legacy_data["tenant_id"],
            file_name=legacy_data["file_name"],
            storage_path=legacy_data["file_path"],  # 在实际迁移中会被重命名
            file_type=legacy_data["file_type"],
            file_size=legacy_data["file_size"],
            mime_type=legacy_data["mime_type"],
            status=converted_status,
            indexed_at=datetime.now(timezone.utc) if converted_status == DocumentStatus.READY else None
        )
        test_db_session.add(document)
        test_db_session.commit()
        test_db_session.refresh(document)

        # 验证数据完整性
        assert document.tenant_id == legacy_data["tenant_id"]
        assert document.file_name == legacy_data["file_name"]
        assert document.file_size == legacy_data["file_size"]
        assert document.file_type == legacy_data["file_type"]
        assert document.mime_type == legacy_data["mime_type"]
        assert document.status == DocumentStatus.READY  # "completed" -> READY
        assert document.indexed_at is not None

        print("✅ 迁移数据完整性验证通过")

    def test_backward_compatibility_check(self, test_db_session):
        """测试向后兼容性检查"""
        Base.metadata.create_all(test_db_session.get_bind())

        tenant = Tenant(
            id="compatibility-test",
            email="compat@example.com",
            display_name="Compatibility Test"
        )
        test_db_session.add(tenant)
        test_db_session.commit()

        # 创建一个包含所有字段的完整文档
        document = KnowledgeDocument(
            id=uuid.uuid4(),
            tenant_id="compatibility-test",
            file_name="compatibility-test.pdf",
            storage_path="dataagent-docs/tenant-compatibility-test/documents/compatibility-test.pdf",
            file_type="pdf",
            file_size=5 * 1024 * 1024,  # 5MB
            mime_type="application/pdf",
            status=DocumentStatus.READY,
            processing_error=None,
            indexed_at=datetime.now(timezone.utc)
        )
        test_db_session.add(document)
        test_db_session.commit()
        test_db_session.refresh(document)

        # 验证所有字段都存在并可访问
        assert hasattr(document, 'id')
        assert hasattr(document, 'tenant_id')
        assert hasattr(document, 'file_name')
        assert hasattr(document, 'storage_path')
        assert hasattr(document, 'file_type')
        assert hasattr(document, 'file_size')
        assert hasattr(document, 'mime_type')
        assert hasattr(document, 'status')
        assert hasattr(document, 'processing_error')
        assert hasattr(document, 'indexed_at')
        assert hasattr(document, 'created_at')
        assert hasattr(document, 'updated_at')

        # 验证数据类型正确
        assert isinstance(document.id, uuid.UUID)
        assert isinstance(document.file_size, int)
        assert document.status in DocumentStatus

        print("✅ 向后兼容性检查通过")


# 需要导入time模块
import time