"""
# [ENCRYPTION_SERVICE] 加密服务

## [HEADER]
**文件名**: encryption_service.py
**职责**: 提供敏感数据（连接字符串）的加密解密服务，支持Fernet对称加密和PBKDF2密钥派生
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 加密服务

## [INPUT]
- **connection_string: str** - 明文连接字符串
- **encrypted_connection_string: str** - 加密的连接字符串（Fernet token）
- **value: str** - 要检查的值
- **password: str** - 密码（用于密钥派生）
- **salt: Optional[bytes]** - 盐值（16字节随机数）

## [OUTPUT]
- **str**: 加密后的连接字符串（encrypt_connection_string）
- **str**: 解密后的明文连接字符串（decrypt_connection_string）
- **bool**: 值是否已加密（is_encrypted）
- **bytes**: 派生的密钥（generate_key_from_password）

**上游依赖** (已读取源码):
- cryptography.fernet.Fernet - Fernet对称加密
- cryptography.hazmat.primitives - 哈希和KDF算法

**下游依赖** (需要反向索引分析):
- [data_source_service.py](./data_source_service.py) - 数据源服务（连接字符串加密）
- [connection_test_service.py](./connection_test_service.py) - 连接测试服务（解密后测试）

**调用方**:
- 数据源创建时加密连接字符串
- Agent查询时解密连接字符串
- 连接测试时解密连接字符串

## [STATE]
- **可选依赖**: cryptography导入失败时CRYPTOGRAPHY_AVAILABLE=False，不阻塞应用
- **密钥来源**: 优先环境变量ENCRYPTION_KEY，其次自动生成（Fernet.generate_key）
- **密钥格式**: 44字符Base64编码字符串（代表32字节密钥）
- **密钥验证**: 从环境变量加载时验证Fernet密钥格式
- **降级策略**: 加密不可用时返回明文（记录警告）
- **开发模式**: 开发环境记录生成的密钥到日志（便于添加到.env）

## [SIDE-EFFECTS]
- **环境变量读取**: os.getenv("ENCRYPTION_KEY")
- **密钥生成**: Fernet.generate_key()（环境变量未配置时）
- **加密操作**: Fernet.encrypt（UTF-8编码 → Base64 token）
- **解密操作**: Fernet.decrypt（Base64 token → UTF-8解码）
- **日志记录**: 开发环境记录生成的密钥（warning级别）
- **Base64解码**: is_encrypted中尝试验证Base64格式
- **异常抛出**: 空字符串、加密/解密失败时抛出ValueError/RuntimeError

## [POS]
**路径**: backend/src/app/services/encryption_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 外部依赖cryptography库
"""

import base64
import os
import logging
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logging.warning("cryptography package not available, encryption will be disabled")

logger = logging.getLogger(__name__)


class EncryptionService:
    """加密服务类"""

    def __init__(self):
        """初始化加密服务"""
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Encryption service initialized without encryption capabilities")
            self.encryption_key = None
            self.cipher_suite = None
            return

        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        logger.info("Encryption service initialized")

    def _get_or_create_encryption_key(self) -> bytes:
        """
        获取或创建加密密钥
        优先从环境变量获取，如果没有则创建新的

        Fernet密钥格式：44字符的Base64编码字符串（代表32字节的密钥）
        """
        # 从环境变量获取密钥
        key = os.getenv("ENCRYPTION_KEY")
        if key:
            try:
                # Fernet需要的是Base64编码的字符串（bytes类型）
                # 直接将字符串编码为bytes即可，不需要再次解码
                key_bytes = key.encode('utf-8')
                # 验证密钥格式是否正确
                Fernet(key_bytes)  # 这会验证密钥格式
                logger.info("Encryption key loaded from environment variable")
                return key_bytes
            except Exception as e:
                logger.warning(f"Failed to load encryption key from environment: {e}")

        # 如果环境变量中没有，生成新的密钥
        logger.warning("No encryption key found in environment, generating new key")
        key = Fernet.generate_key()

        # 在开发环境中，记录密钥以便添加到环境变量
        if os.getenv("ENVIRONMENT", "development") == "development":
            logger.warning(f"Generated encryption key (add to .env): ENCRYPTION_KEY={key.decode()}")

        return key

    def encrypt_connection_string(self, connection_string: str) -> str:
        """
        加密连接字符串

        Args:
            connection_string: 明文连接字符串

        Returns:
            加密后的连接字符串（Fernet token，已经是Base64编码）
        """
        if not connection_string:
            raise ValueError("Connection string cannot be empty")

        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Encryption not available, returning plain text")
            return connection_string

        try:
            # Fernet.encrypt() 返回的已经是Base64编码的bytes
            # 直接解码为字符串即可，不需要再次Base64编码
            encrypted_data = self.cipher_suite.encrypt(connection_string.encode('utf-8'))
            return encrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt connection string: {e}")
            raise RuntimeError("Failed to encrypt connection string")

    def decrypt_connection_string(self, encrypted_connection_string: str) -> str:
        """
        解密连接字符串

        Args:
            encrypted_connection_string: 加密的连接字符串（Fernet token）

        Returns:
            解密后的明文连接字符串
        """
        if not encrypted_connection_string:
            raise ValueError("Encrypted connection string cannot be empty")

        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Decryption not available, returning as-is")
            return encrypted_connection_string

        try:
            # Fernet token 已经是Base64编码的，直接传给decrypt即可
            decrypted_data = self.cipher_suite.decrypt(encrypted_connection_string.encode('utf-8'))
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt connection string: {e}")
            raise RuntimeError("Failed to decrypt connection string")

    def is_encrypted(self, value: str) -> bool:
        """
        检查值是否已加密

        Args:
            value: 要检查的值

        Returns:
            如果值已加密返回True，否则返回False
        """
        if not value:
            return False

        try:
            # 尝试Base64解码
            base64.urlsafe_b64decode(value.encode('utf-8'))
            # 如果解码成功，可能是加密的
            return True
        except Exception:
            # 解码失败，说明不是加密的
            return False

    def generate_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        从密码生成加密密钥（用于密钥派生）

        Args:
            password: 密码
            salt: 盐值（可选）

        Returns:
            派生的密钥
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key


# 全局加密服务实例
encryption_service = EncryptionService()