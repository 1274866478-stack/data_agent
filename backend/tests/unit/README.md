# 单元测试 (Unit Tests)

本目录包含后端服务的单元测试。

## 测试范围

- 服务层函数测试
- 工具函数测试
- 数据模型测试
- 配置验证测试

## 运行测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试文件
pytest tests/unit/test_encryption_service.py -v

# 运行测试并生成覆盖率报告
pytest tests/unit/ -v --cov=src/app/services --cov-report=html
```

## 测试覆盖率目标

- **目标覆盖率**: ≥85%
- **当前覆盖率**: 待测量

## 测试命名规范

- 测试文件: `test_<module_name>.py`
- 测试类: `Test<ClassName>`
- 测试函数: `test_<function_name>_<scenario>`

## 示例

```python
import pytest
from src.app.services.encryption_service import EncryptionService

class TestEncryptionService:
    def test_encrypt_connection_string_success(self):
        """测试连接字符串加密成功"""
        service = EncryptionService()
        connection_string = "postgresql://user:pass@localhost/db"
        encrypted = service.encrypt_connection_string(connection_string)
        assert encrypted != connection_string
        assert len(encrypted) > 0
    
    def test_decrypt_connection_string_success(self):
        """测试连接字符串解密成功"""
        service = EncryptionService()
        original = "postgresql://user:pass@localhost/db"
        encrypted = service.encrypt_connection_string(original)
        decrypted = service.decrypt_connection_string(encrypted)
        assert decrypted == original
```

