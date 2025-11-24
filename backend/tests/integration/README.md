# 集成测试 (Integration Tests)

本目录包含后端服务的集成测试。

## 测试范围

- API端点测试
- 数据库集成测试
- 外部服务集成测试 (MinIO, ChromaDB)
- 认证流程测试

## 运行测试

```bash
# 启动测试环境
docker-compose up -d db storage vector_db

# 运行所有集成测试
pytest tests/integration/ -v

# 运行特定测试文件
pytest tests/integration/test_tenant_api.py -v

# 运行测试并生成覆盖率报告
pytest tests/integration/ -v --cov=src/app/api --cov-report=html
```

## 测试覆盖率目标

- **目标覆盖率**: ≥80%
- **当前覆盖率**: 待测量

## 测试环境要求

- PostgreSQL数据库
- MinIO对象存储
- ChromaDB向量数据库

## 示例

```python
import pytest
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

class TestTenantAPI:
    def test_get_tenant_me_success(self, auth_headers):
        """测试获取当前租户信息成功"""
        response = client.get("/api/v1/tenants/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
    
    def test_get_tenant_me_unauthorized(self):
        """测试未认证访问返回401"""
        response = client.get("/api/v1/tenants/me")
        assert response.status_code == 401
```

