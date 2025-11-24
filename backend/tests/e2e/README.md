# 端到端测试 (E2E Tests)

本目录包含后端服务的端到端测试。

## 测试范围

- 完整用户流程测试
- 多租户隔离验证
- 数据源连接完整流程
- 文档上传和处理流程

## 运行测试

```bash
# 启动完整测试环境
docker-compose up -d

# 运行所有E2E测试
pytest tests/e2e/ -v

# 运行特定测试文件
pytest tests/e2e/test_document_integration_e2e.py -v
```

## 测试覆盖率目标

- **目标覆盖率**: ≥70%
- **当前覆盖率**: 待测量

## 测试环境要求

- 完整Docker环境 (所有5个服务)
- 测试数据准备
- 测试文件准备

## 示例

```python
import pytest
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

class TestDocumentUploadE2E:
    def test_complete_document_upload_flow(self, auth_headers, test_pdf_file):
        """测试完整的文档上传流程"""
        # 1. 上传文档
        files = {"file": ("test.pdf", test_pdf_file, "application/pdf")}
        response = client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200
        document_id = response.json()["id"]
        
        # 2. 验证文档存在
        response = client.get(
            f"/api/v1/documents/{document_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 3. 验证MinIO存储
        # 4. 验证ChromaDB向量化
        # 5. 删除文档
```

