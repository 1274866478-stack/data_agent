"""
租户服务测试
验证Story-2.2实现的租户管理功能
"""

import pytest
from sqlalchemy.orm import Session
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.app.services.tenant_service import TenantService, TenantSetupService
from src.app.data.models import Tenant, TenantStatus, DataSourceConnection, KnowledgeDocument


class TestTenantService:
    """租户服务测试类"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def tenant_service(self, mock_db):
        """创建租户服务实例"""
        return TenantService(mock_db)

    @pytest.fixture
    def sample_tenant(self):
        """示例租户数据"""
        return Tenant(
            id="tenant_123",
            email="test@example.com",
            status=TenantStatus.ACTIVE,
            display_name="Test Tenant",
            settings={"timezone": "UTC", "language": "en"},
            storage_quota_mb=1024,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.mark.asyncio
    async def test_create_tenant_success(self, tenant_service, mock_db):
        """测试成功创建租户"""
        # 准备测试数据
        tenant_id = "new_tenant_123"
        email = "new@example.com"
        settings = {"timezone": "Asia/Shanghai"}

        # 模拟数据库查询
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 执行测试
        with patch('src.app.services.tenant_service.Tenant') as MockTenant:
            mock_tenant_instance = Mock()
            mock_tenant_instance.to_dict.return_value = {
                "id": tenant_id,
                "email": email,
                "status": "active"
            }
            MockTenant.return_value = mock_tenant_instance

            result = await tenant_service.create_tenant(tenant_id, email, settings)

            # 验证结果
            assert result is not None
            MockTenant.assert_called_once_with(
                id=tenant_id,
                email=email,
                status=TenantStatus.ACTIVE,
                settings=settings
            )
            mock_db.add.assert_called_once_with(mock_tenant_instance)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tenant_duplicate_id(self, tenant_service, mock_db, sample_tenant):
        """测试创建重复ID的租户"""
        tenant_id = "tenant_123"
        email = "test@example.com"

        # 模拟租户已存在
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tenant

        # 执行测试并验证异常
        with pytest.raises(ValueError, match="Tenant with ID .* already exists"):
            await tenant_service.create_tenant(tenant_id, email)

    @pytest.mark.asyncio
    async def test_create_tenant_duplicate_email(self, tenant_service, mock_db, sample_tenant):
        """测试创建重复邮箱的租户"""
        tenant_id = "new_tenant_123"
        email = "test@example.com"

        # 模拟邮箱已存在（分两次查询模拟）
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [None, sample_tenant]
        mock_db.query.return_value = mock_query

        # 执行测试并验证异常
        with pytest.raises(ValueError, match="Email .* is already registered"):
            await tenant_service.create_tenant(tenant_id, email)

    @pytest.mark.asyncio
    async def test_get_tenant_by_id_success(self, tenant_service, mock_db, sample_tenant):
        """测试根据ID成功获取租户"""
        tenant_id = "tenant_123"

        # 模拟数据库查询
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tenant

        # 执行测试
        result = await tenant_service.get_tenant_by_id(tenant_id)

        # 验证结果
        assert result is not None
        assert result.id == tenant_id
        assert result.email == sample_tenant.email

    @pytest.mark.asyncio
    async def test_get_tenant_by_id_not_found(self, tenant_service, mock_db):
        """测试获取不存在的租户"""
        tenant_id = "nonexistent_tenant"

        # 模拟租户不存在
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # 执行测试
        result = await tenant_service.get_tenant_by_id(tenant_id)

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tenant_by_id_deleted(self, tenant_service, mock_db):
        """测试获取已删除的租户"""
        tenant_id = "deleted_tenant"

        # 模拟已删除的租户（查询被过滤掉）
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # 执行测试
        result = await tenant_service.get_tenant_by_id(tenant_id)

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_update_tenant_success(self, tenant_service, mock_db, sample_tenant):
        """测试成功更新租户"""
        tenant_id = "tenant_123"
        update_data = {
            "display_name": "Updated Tenant",
            "settings": {"timezone": "Asia/Shanghai"},
            "storage_quota_mb": 2048
        }

        # 模拟获取租户
        tenant_service.get_tenant_by_id = AsyncMock(return_value=sample_tenant)

        # 执行测试
        result = await tenant_service.update_tenant(tenant_id, update_data)

        # 验证结果
        assert result is not None
        assert sample_tenant.display_name == "Updated Tenant"
        assert sample_tenant.storage_quota_mb == 2048
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self, tenant_service, mock_db):
        """测试更新不存在的租户"""
        tenant_id = "nonexistent_tenant"
        update_data = {"display_name": "Updated Tenant"}

        # 模拟租户不存在
        tenant_service.get_tenant_by_id = AsyncMock(return_value=None)

        # 执行测试
        result = await tenant_service.update_tenant(tenant_id, update_data)

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_update_tenant_invalid_status(self, tenant_service, mock_db, sample_tenant):
        """测试更新租户时使用无效状态"""
        tenant_id = "tenant_123"
        update_data = {"status": "invalid_status"}

        # 模拟获取租户
        tenant_service.get_tenant_by_id = AsyncMock(return_value=sample_tenant)

        # 执行测试并验证异常
        with pytest.raises(ValueError, match="Invalid status"):
            await tenant_service.update_tenant(tenant_id, update_data)

    @pytest.mark.asyncio
    async def test_delete_tenant_success(self, tenant_service, mock_db, sample_tenant):
        """测试成功删除租户（软删除）"""
        tenant_id = "tenant_123"

        # 模拟获取租户
        tenant_service.get_tenant_by_id = AsyncMock(return_value=sample_tenant)

        # 执行测试
        result = await tenant_service.delete_tenant(tenant_id)

        # 验证结果
        assert result is True
        assert sample_tenant.status == TenantStatus.DELETED
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tenant_not_found(self, tenant_service, mock_db):
        """测试删除不存在的租户"""
        tenant_id = "nonexistent_tenant"

        # 模拟租户不存在
        tenant_service.get_tenant_by_id = AsyncMock(return_value=None)

        # 执行测试
        result = await tenant_service.delete_tenant(tenant_id)

        # 验证结果
        assert result is False

    @pytest.mark.asyncio
    async def test_get_tenant_stats_success(self, tenant_service, mock_db, sample_tenant):
        """测试成功获取租户统计信息"""
        tenant_id = "tenant_123"

        # 模拟数据
        data_source_count = 5
        total_documents = 20
        processed_documents = 15
        storage_used_bytes = 1024 * 1024 * 500  # 500MB

        # 模拟数据库查询
        tenant_service.get_tenant_by_id = AsyncMock(return_value=sample_tenant)

        # 模拟数据源连接查询
        mock_ds_query = Mock()
        mock_ds_query.filter.return_value.count.return_value = data_source_count
        mock_db.query.return_value.filter.return_value.count.return_value = data_source_count

        # 模拟文档查询
        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.count.side_effect = [
            total_documents,  # 总文档数
            processed_documents,  # 已处理文档数
            storage_used_bytes  # 存储使用量
        ]
        mock_db.query.return_value.filter.return_value = mock_doc_query

        # 执行测试
        result = await tenant_service.get_tenant_stats(tenant_id)

        # 验证结果
        assert result is not None
        assert result["total_documents"] == total_documents
        assert result["total_data_sources"] == data_source_count
        assert result["processed_documents"] == processed_documents
        assert result["pending_documents"] == total_documents - processed_documents
        assert result["storage_used_mb"] == 500  # 500MB
        assert result["storage_quota_mb"] == 1024
        assert "storage_usage_percent" in result

    @pytest.mark.asyncio
    async def test_get_tenant_stats_not_found(self, tenant_service, mock_db):
        """测试获取不存在租户的统计信息"""
        tenant_id = "nonexistent_tenant"

        # 模拟租户不存在
        tenant_service.get_tenant_by_id = AsyncMock(return_value=None)

        # 执行测试
        result = await tenant_service.get_tenant_stats(tenant_id)

        # 验证结果
        assert result is None


class TestTenantSetupService:
    """租户初始化服务测试类"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def tenant_setup_service(self, mock_db):
        """创建租户初始化服务实例"""
        return TenantSetupService(mock_db)

    @pytest.mark.asyncio
    async def test_setup_new_tenant_success(self, tenant_setup_service):
        """测试成功初始化新租户"""
        # 准备测试数据
        setup_data = {
            "tenant_id": "new_tenant_123",
            "email": "new@example.com",
            "display_name": "New Tenant",
            "settings": {"timezone": "Asia/Shanghai"}
        }

        # 模拟租户服务
        mock_tenant_service = AsyncMock()
        mock_tenant = Mock()
        mock_tenant.to_dict.return_value = {
            "id": setup_data["tenant_id"],
            "email": setup_data["email"],
            "status": "active"
        }
        mock_tenant_service.create_tenant.return_value = mock_tenant
        mock_tenant_service.update_tenant.return_value = mock_tenant

        tenant_setup_service.tenant_service = mock_tenant_service

        # 执行测试
        result = await tenant_setup_service.setup_new_tenant(
            tenant_id=setup_data["tenant_id"],
            email=setup_data["email"],
            display_name=setup_data["display_name"],
            settings=setup_data["settings"]
        )

        # 验证结果
        assert result["success"] is True
        assert result["tenant_id"] == setup_data["tenant_id"]
        assert "tenant" in result
        mock_tenant_service.create_tenant.assert_called_once()
        mock_tenant_service.update_tenant.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_new_tenant_failure(self, tenant_setup_service):
        """测试初始化新租户失败"""
        # 准备测试数据
        setup_data = {
            "tenant_id": "new_tenant_123",
            "email": "invalid-email",  # 无效邮箱
        }

        # 模拟租户服务抛出异常
        mock_tenant_service = AsyncMock()
        mock_tenant_service.create_tenant.side_effect = ValueError("Invalid email format")
        tenant_setup_service.tenant_service = mock_tenant_service

        # 执行测试
        result = await tenant_setup_service.setup_new_tenant(
            tenant_id=setup_data["tenant_id"],
            email=setup_data["email"]
        )

        # 验证结果
        assert result["success"] is False
        assert "error" in result
        assert "message" in result