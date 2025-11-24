"""
加密服务
用于敏感数据（如数据库连接字符串）的加密和解密
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
        """
        # 从环境变量获取密钥
        key = os.getenv("ENCRYPTION_KEY")
        if key:
            try:
                # Base64解码密钥
                return base64.urlsafe_b64decode(key.encode())
            except Exception as e:
                logger.warning(f"Failed to decode encryption key from environment: {e}")

        # 如果环境变量中没有，生成新的密钥
        logger.warning("No encryption key found in environment, generating new key")
        key = Fernet.generate_key()

        # 在开发环境中，记录密钥以便添加到环境变量
        if os.getenv("ENVIRONMENT", "development") == "development":
            logger.warning(f"Generated encryption key (add to .env): ENCRYPTION_KEY={base64.urlsafe_b64encode(key).decode()}")

        return key

    def encrypt_connection_string(self, connection_string: str) -> str:
        """
        加密连接字符串

        Args:
            connection_string: 明文连接字符串

        Returns:
            加密后的连接字符串（Base64编码）
        """
        if not connection_string:
            raise ValueError("Connection string cannot be empty")

        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Encryption not available, returning plain text")
            return connection_string

        try:
            # 加密数据
            encrypted_data = self.cipher_suite.encrypt(connection_string.encode('utf-8'))
            # 返回Base64编码的结果
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt connection string: {e}")
            raise RuntimeError("Failed to encrypt connection string")

    def decrypt_connection_string(self, encrypted_connection_string: str) -> str:
        """
        解密连接字符串

        Args:
            encrypted_connection_string: 加密的连接字符串（Base64编码）

        Returns:
            解密后的明文连接字符串
        """
        if not encrypted_connection_string:
            raise ValueError("Encrypted connection string cannot be empty")

        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Decryption not available, returning as-is")
            return encrypted_connection_string

        try:
            # Base64解码
            encrypted_data = base64.urlsafe_b64decode(encrypted_connection_string.encode('utf-8'))
            # 解密数据
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
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