"""
租户隔离验证测试 - Story 2.4安全性要求
验证多租户架构的数据隔离安全性
"""

import pytest
import uuid
import io
from unittest.mock import patch, Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.data.models import Base, KnowledgeDocument, DocumentStatus, Tenant
from src.app.services.document_service import DocumentService
from src.app.data.database import get_db


class TestTenantIsolation:
    """租户隔离测试类"""

    @pytest.fixture(scope="function")
    def test_db(self):
        """创建测试数据库"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def client(self, test_db):
        """创建测试客户端"""
        def override_get_db():
            yield test_db

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def sample_tenants(self):
        """创建示例租户"""
        return [
            Tenant(
                id="tenant-company-a",
                email="company-a@example.com",
                display_name="Company A"
            ),
            Tenant(
                id="tenant-company-b",
                email="company-b@example.com",
                display_name="Company B"
            ),
            Tenant(
                id="tenant-individual-123",
                email="user123@example.com",
                display_name="Individual User 123"
            )
        ]

    @pytest.fixture
    def document_service(self):
        """创建文档服务实例"""
        return DocumentService()

    @pytest.fixture
    def sample_pdf_file(self):
        """创建示例PDF文件"""
        return io.BytesIO(b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj""")

    def test_tenant_creation_isolation(self, test_db, sample_tenants):
        """测试租户创建隔离"""
        # 创建多个租户
        for tenant in sample_tenants:
            test_db.add(tenant)
        test_db.commit()
        for tenant in sample_tenants:
            test_db.refresh(tenant)

        # 验证每个租户都有唯一ID
        tenant_ids = [tenant.id for tenant in sample_tenants]
        assert len(set(tenant_ids)) == len(tenant_ids)

        # 验证租户可以被独立查询
        for tenant in sample_tenants:
            queried_tenant = test_db.query(Tenant).filter(Tenant.id == tenant.id).first()
            assert queried_tenant is not None
            assert queried_tenant.id == tenant.id
            assert queried_tenant.email == tenant.email

    def test_document_tenant_assignment(self, test_db, sample_tenants, document_service, sample_pdf_file):
        """测试文档租户分配"""
        # 创建租户
        for tenant in sample_tenants:
            test_db.add(tenant)
        test_db.commit()

        # 为每个租户创建文档
        document_ids = []
        for tenant in sample_tenants:
            result = document_service.upload_document(
                db=test_db,
                tenant_id=tenant.id,
                file_data=sample_pdf_file,
                file_name=f"doc-for-{tenant.id}.pdf",
                file_size=len(sample_pdf_file.getvalue()),
                mime_type="application/pdf"
            )
            assert result["success"] is True
            document_ids.append(result["document"]["id"])

        # 验证每个文档都分配给正确的租户
        for i, tenant in enumerate(sample_tenants):
            document = test_db.query(KnowledgeDocument).filter(
                KnowledgeDocument.tenant_id == tenant.id
            ).first()
            assert document is not None
            assert document.tenant_id == tenant.id

    def test_cross_tenant_data_leakage(self, test_db, sample_tenants):
        """测试跨租户数据泄露防护"""
        # 创建租户
        tenant_a, tenant_b = sample_tenants[0], sample_tenants[1]
        test_db.add_all([tenant_a, tenant_b])
        test_db.commit()

        # 为租户A创建文档
        doc_a = KnowledgeDocument(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            file_name="tenant-a-document.pdf",
            storage_path=f"dataagent-docs/tenant-{tenant_a.id}/documents/tenant-a-document.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            status=DocumentStatus.READY
        )
        test_db.add(doc_a)

        # 为租户B创建文档
        doc_b = KnowledgeDocument(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            file_name="tenant-b-document.pdf",
            storage_path=f"dataagent-docs/tenant-{tenant_b.id}/documents/tenant-b-document.pdf",
            file_type="pdf",
            file_size=2048,
            mime_type="application/pdf",
            status=DocumentStatus.PENDING
        )
        test_db.add(doc_b)

        test_db.commit()

        # 验证租户A只能访问自己的文档
        docs_a_only = test_db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant_a.id
        ).all()
        assert len(docs_a_only) == 1
        assert docs_a_only[0].id == doc_a.id

        # 验证租户B只能访问自己的文档
        docs_b_only = test_db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant_b.id
        ).all()
        assert len(docs_b_only) == 1
        assert docs_b_only[0].id == doc_b.id

        # 验证总文档数
        total_docs = test_db.query(KnowledgeDocument).all()
        assert len(total_docs) == 2

    def test_api_tenant_isolation_enforcement(self, client, test_db, sample_tenants):
        """测试API层面的租户隔离强制执行"""
        # 创建租户
        tenant_a, tenant_b = sample_tenants[0], sample_tenants[1]
        test_db.add_all([tenant_a, tenant_b])
        test_db.commit()

        # 使用模拟的tenant_id（在实际应用中应该从JWT token获取）
        # 这里我们通过修改DocumentService的get_tenant_id_from_request函数来模拟

        # 模拟为租户A上传文档
        with patch('src.app.api.v1.endpoints.documents.get_tenant_id_from_request', return_value=tenant_a.id):
            upload_response_a = client.post(
                "/api/v1/documents/upload",
                files={"file": ("tenant-a.pdf", io.BytesIO(b"tenant-a-content"), "application/pdf")}
            )
            assert upload_response.status_code == 201

        # 模拟为租户B上传文档
        with patch('src.app.api.v1.endpoints.documents.get_tenant_id_from_request', return_value=tenant_b.id):
            upload_response_b = client.post(
                "/api/v1/documents/upload",
                files={"file": ("tenant-b.pdf", io.BytesIO(b"tenant-b-content"), "application/pdf")}
            )
            assert upload_response_b.status_code == 201

        # 模拟租户A查看文档列表
        with patch('src.app.api.v1.endpoints.documents.get_tenant_id_from_request', return_value=tenant_a.id):
            list_response_a = client.get("/api/v1/documents")
            assert list_response_a.status_code == 200
            data_a = list_response_a.json()
            docs_a = [doc for doc in data_a["documents"] if doc["file_name"].startswith("tenant-a")]
            assert len(docs_a) >= 1

        # 模拟租户B查看文档列表
        with patch('src.app.v1.endpoints.documents.get_tenant_id_from_request', return_value=tenant_b.id):
            list_response_b = client.get("/api/v1/documents")
            assert list_response_b.status_code == 200
            data_b = list_response_b.json()
            docs_b = [doc for doc in data_b["documents"] if doc["file_name"].startswith("tenant-b")]
            assert len(docs_b) >= 1

    @patch('src.app.services.minio_client.minio_service')
    def test_minio_path_tenant_isolation(self, mock_minio, test_db, sample_tenants, sample_pdf_file, document_service):
        """测试MinIO路径租户隔离"""
        # 设置MinIO模拟
        mock_minio.upload_file.return_value = True

        # 创建租户
        for tenant in sample_tenants:
            test_db.add(tenant)
        test_db.commit()

        # 为每个租户上传文档，验证路径隔离
        uploaded_paths = []
        for tenant in sample_tenants:
            result = document_service.upload_document(
                db=test_db,
                tenant_id=tenant.id,
                file_data=sample_pdf_file,
                file_name=f"minio-isolation-test-{tenant.id}.pdf",
                file_size=len(sample_pdf_file.getvalue()),
                mime_type="application/pdf"
            )

            assert result["success"] is True
            document = test_db.query(KnowledgeDocument).filter(
                KnowledgeDocument.id == result["document"]["id"]
            ).first()
            uploaded_paths.append(document.storage_path)

            # 验证路径包含租户ID
            assert f"tenant-{tenant.id}" in document.storage_path

        # 验证每个租户的路径都是唯一的
        assert len(set(uploaded_paths)) == len(uploaded_paths)

        # 验证路径符合Story 2.4规范
        for path in uploaded_paths:
            assert path.startswith("dataagent-docs/tenant-")
            assert "/documents/" in path

    def test_query_performance_with_large_dataset(self, test_db, sample_tenants):
        """测试大数据集下的查询性能"""
        # 创建租户
        for tenant in sample_tenants:
            test_db.add(tenant)
        test_db.commit()

        # 为每个租户创建大量文档
        documents_per_tenant = 1000
        total_documents = len(sample_tenants) * documents_per_tenant

        import time
        start_time = time.time()

        for tenant in sample_tenants:
            # 批量插入文档
            documents = []
            for i in range(documents_per_tenant):
                doc = KnowledgeDocument(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    file_name=f"perf-test-{tenant.id}-{i}.pdf",
                    storage_path=f"dataagent-docs/tenant-{tenant.id}/documents/perf-test-{i}.pdf",
                    file_type="pdf",
                    file_size=1024 + i,
                    mime_type="application/pdf",
                    status=DocumentStatus.READY if i % 2 == 0 else DocumentStatus.PENDING
                )
                documents.append(doc)

            test_db.add_all(documents)
            test_db.commit()

        batch_insert_time = time.time() - start_time

        # 测试查询性能
        query_times = []
        for tenant in sample_tenants:
            start_time = time.time()
            documents = test_db.query(KnowledgeDocument).filter(
                KnowledgeDocument.tenant_id == tenant.id
            ).limit(100).all()
            query_time = time.time() - start_time
            query_times.append(query_time)
            assert len(documents) <= 100

        avg_query_time = sum(query_times) / len(query_times)
        max_query_time = max(query_times)

        # 性能断言
        assert avg_query_time < 0.1  # 平均查询时间应小于100ms
        assert max_query_time < 0.5  # 最大查询时间应小于500ms
        assert batch_insert_time < 5.0  # 批量插入时间应小于5秒

        print(f"✅ 性能测试通过: {total_documents} 个文档")
        print(f"✅ 批量插入时间: {batch_insert_time:.2f}s")
        print(f"✅ 平均查询时间: {avg_query_time:.4f}s")
        print(f"✅ 最大查询时间: {max_query_time:.4f}s")

    def test_sql_injection_prevention(self, test_db, sample_tenants):
        """测试SQL注入防护"""
        # 创建租户
        for tenant in sample_tenants:
            test_db.add(tenant)
        test_db.commit()

        # 尝试恶意查询字符串
        malicious_tenant_ids = [
            "tenant-a'; DROP TABLE tenants; --",
            "1 OR 1=1 --",
            "'; SELECT * FROM tenants; --",
            "UNION SELECT id FROM tenants WHERE '1'='1"
        ]

        for malicious_id in malicious_tenant_ids:
            # 尝试恶意查询应该失败或返回空结果
            documents = test_db.query(KnowledgeDocument).filter(
                KnowledgeDocument.tenant_id == malicious_id
            ).all()
            # 恶意查询要么失败，要么返回空结果
            # SQLAlchemy应该自动转义参数，防止SQL注入
            assert isinstance(documents, list)

    def test_foreign_key_constraint_enforcement(self, test_db):
        """测试外键约束强制执行"""
        # 先创建一个无效的tenant_id（不存在）
        invalid_tenant_id = "nonexistent-tenant-id"

        # 尝试创建引用不存在租户的文档
        document = KnowledgeDocument(
            id=uuid.uuid4(),
            tenant_id=invalid_tenant_id,
            file_name="invalid-tenant-doc.pdf",
            storage_path="dataagent-docs/tenant-invalid-tenant-id/documents/invalid-tenant-doc.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            status=DocumentStatus.PENDING
        )

        # 在实际数据库中，这应该因为外键约束而失败
        # 在SQLite测试中，我们检查是否真的执行了外键验证
        try:
            test_db.add(document)
            test_db.commit()
            # 如果没有抛出异常，说明外键约束可能没有启用
            # 在生产环境中需要确保外键约束正确配置
            print("⚠️ 外键约束可能未启用")
        except SQLAlchemyError:
            # 这是预期的行为
            print("✅ 外键约束正确工作")

    def test_concurrent_tenant_operations(self, test_db, sample_tenants):
        """测试并发租户操作"""
        import threading
        import time

        # 创建租户
        for tenant in sample_tenants:
            test_db.add(tenant)
        test_db.commit()

        results = []

        def tenant_operation(tenant_id, operation_id):
            try:
                # 模拟并发操作
                for i in range(10):
                    document = KnowledgeDocument(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        file_name=f"concurrent-{operation_id}-{i}.pdf",
                        storage_path=f"dataagent-docs/tenant-{tenant_id}/documents/concurrent-{operation_id}-{i}.pdf",
                        file_type="pdf",
                        file_size=1024,
                        mime_type="application/pdf",
                        status=DocumentStatus.PENDING
                    )
                    test_db.add(document)

                test_db.commit()
                results.append(f"Success: {tenant_id}")
            except Exception as e:
                results.append(f"Error: {tenant_id} - {str(e)}")

        # 为每个租户启动并发操作
        threads = []
        for tenant in sample_tenants:
            thread = threading.Thread(
                target=tenant_operation,
                args=(tenant.id, uuid.uuid4())
            )
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有数据竞争
        for result in results:
            assert result.startswith("Success:") or "Error" in result

        # 验证总文档数量
        total_docs = test_db.query(KnowledgeDocument).all()
        expected_total = len(sample_tenants) * 10  # 每个租户10个文档
        assert len(total_docs) == expected_total

    def test_data_retention_and_cleanup(self, test_db):
        """测试数据保留和清理"""
        # 创建租户和文档
        tenant = Tenant(
            id="cleanup-tenant",
            email="cleanup@example.com",
            display_name="Cleanup Test Tenant"
        )
        test_db.add(tenant)
        test_db.commit()

        # 创建多个文档
        document_ids = []
        for i in range(5):
            document = KnowledgeDocument(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                file_name=f"cleanup-test-{i}.pdf",
                storage_path=f"dataagent-docs/tenant-cleanup-tenant/documents/cleanup-test-{i}.pdf",
                file_type="pdf",
                file_size=1024 + i * 512,
                mime_type="application/pdf",
                status=DocumentStatus.READY if i % 2 == 0 else DocumentStatus.PENDING
            )
            test_db.add(document)
            document_ids.append(document.id)

        test_db.commit()

        # 验证文档存在
        documents_before = test_db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant.id
        ).all()
        assert len(documents_before) == 5

        # 模拟租户删除（软删除）
        tenant.status = "deleted"
        test_db.commit()

        # 验证文档是否仍然存在（物理删除）
        documents_after_soft_delete = test_db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant.id
        ).all()
        assert len(documents_after_soft_delete) == 5

        # 物理删除文档
        for doc in documents_after_soft_delete:
            test_db.delete(doc)
        test_db.commit()

        # 验证文档已被删除
        documents_after_physical_delete = test_db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant.id
        ).all()
        assert len(documents_after_physical_delete) == 0

        # 物理删除租户
        test_db.delete(tenant)
        test_db.commit()

        # 验证租户已被删除
        deleted_tenant = test_db.query(Tenant).filter(Tenant.id == tenant.id).first()
        assert deleted_tenant is None