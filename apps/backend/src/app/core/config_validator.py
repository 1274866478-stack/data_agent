"""
# [CONFIG VALIDATOR] 配置验证模块

## [HEADER]
**文件名**: config_validator.py
**职责**: 验证所有外部服务的连接状态和配置完整性 - 支持安全检查、服务连通性验证、环境变量验证
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 配置验证模块

## [INPUT]
### 类初始化参数
- **ConfigValidator.__init__()**: 无参数

### 验证方法参数
- **validate_secure_defaults()**: 无参数
- **validate_key_strength()**: 无参数
- **validate_security_configuration()**: 无参数
- **validate_database_connection()**: 无参数（从settings读取database_url）
- **validate_minio_connection()**: 无参数（从settings读取minio配置）
- **validate_chromadb_connection()**: 无参数（从settings读取chroma配置）
- **validate_zhipu_api()**: 无参数（从settings读取zhipuai_api_key）
- **validate_required_env_vars()**: 无参数（从settings读取环境变量）
- **validate_all_configs()**: 无参数

### 便捷函数参数
- **validate_database()**: 无参数
- **validate_minio()**: 无参数
- **validate_chromadb()**: 无参数
- **validate_zhipu()**: 无参数
- **validate_all()**: 无参数
- **validate_security()**: 无参数
- **validate_defaults()**: 无参数
- **validate_key_strength()**: 无参数

## [OUTPUT]
### ValidationResult 类
- **service_name: str** - 服务名称
- **success: bool** - 验证是否成功
- **message: str** - 验证结果消息
- **details: Dict[str, Any]** - 验证详情（错误信息、配置值等）
- **timestamp: float** - 验证时间戳
- **to_dict()**: 转换为字典格式

### ConfigValidator 类返回值
- **validate_secure_defaults()**: ValidationResult - 安全默认值验证结果
- **validate_key_strength()**: ValidationResult - 密钥强度验证结果
- **validate_security_configuration()**: ValidationResult - 综合安全配置验证结果
- **validate_database_connection()**: ValidationResult - 数据库连接验证结果
- **validate_minio_connection()**: ValidationResult - MinIO连接验证结果
- **validate_chromadb_connection()**: ValidationResult - ChromaDB连接验证结果
- **validate_zhipu_api()**: ValidationResult - 智谱API验证结果
- **validate_required_env_vars()**: ValidationResult - 环境变量验证结果
- **validate_all_configs()**: Dict[str, Any] - 全面配置验证摘要
  - **overall_status: str** - 'success' | 'partial_success' | 'failed' | 'security_issues'
  - **total_services: int** - 总服务数
  - **successful: int** - 成功服务数
  - **failed: int** - 失败服务数
  - **security_issues: int** - 安全问题数
  - **results: List[Dict]** - 所有验证结果详情
  - **security_alert: bool** - 是否有安全警告
  - **security_message: str** - 安全消息

### 全局便捷函数返回值
- **validate_database()**: ValidationResult - 数据库连接验证
- **validate_minio()**: ValidationResult - MinIO连接验证
- **validate_chromadb()**: ValidationResult - ChromaDB连接验证
- **validate_zhipu()**: ValidationResult - 智谱API验证
- **validate_all()**: Dict[str, Any] - 所有配置验证摘要
- **validate_security()**: ValidationResult - 安全配置验证
- **validate_defaults()**: ValidationResult - 安全默认值验证
- **validate_key_strength()**: ValidationResult - 密钥强度验证

## [LINK]
**上游依赖** (已读取源码):
- [src/app/core/config.py](./config.py) - 应用配置（settings对象）
- [src/app/services/zhipu_client.py](../services/zhipu_client.py) - 智谱AI服务（zhipu_service）
- [src/app/core/config_audit.py](./config_audit.py) - 配置审计（log_config_change函数）

**外部依赖**:
- [psycopg2](https://www.psycopg.org/) - PostgreSQL数据库连接库
- [minio](https://github.com/minio/minio-py) - MinIO Python SDK
- [chromadb](https://www.trychroma.com/) - ChromaDB向量数据库客户端

**下游依赖** (已读取源码):
- [src/app/api/v1/endpoints/config.py](../api/v1/endpoints/config.py) - API配置端点调用
- [src/app/main.py](../main.py) - 应用启动时配置验证

**调用方**:
- [src/app/api/v1/endpoints/config.py](../api/v1/endpoints/config.py) - API端点调用各个验证方法
- [src/app/main.py](../main.py) - 应用生命周期管理中调用validate_all_configs()

## [POS]
**路径**: backend/src/app/core/config_validator.py
**模块层级**: Level 3（Backend → src/app → core）
**依赖深度**: 直接依赖 1 层（config.py, zhipu_client.py, config_audit.py）
"""

import asyncio
import logging
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
import psycopg2
from psycopg2 import OperationalError

# 条件导入依赖
try:
    from minio import Minio, S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from src.app.core.config import settings
from src.app.services.zhipu_client import zhipu_service
from src.app.core.config_audit import log_config_change

logger = logging.getLogger(__name__)


class ValidationResult:
    """验证结果类"""

    def __init__(self, service_name: str, success: bool, message: str = "", details: Dict[str, Any] = None):
        self.service_name = service_name
        self.success = success
        self.message = message
        self.details = details or {}
        self.timestamp = asyncio.get_event_loop().time() if asyncio.get_event_loop() else None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "service": self.service_name,
            "status": "success" if self.success else "failed",
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ConfigValidator:
    """配置验证器类"""

    def __init__(self):
        self.validation_results: List[ValidationResult] = []

    def validate_secure_defaults(self) -> ValidationResult:
        """验证安全默认值配置"""
        try:
            logger.info("正在验证安全默认值配置")

            security_issues = []

            # 检查MinIO默认密钥
            if settings.minio_access_key == "minioadmin":
                security_issues.append("检测到MinIO使用默认访问密钥 'minioadmin'")

            if settings.minio_secret_key == "minioadmin":
                security_issues.append("检测到MinIO使用默认秘密密钥 'minioadmin'")

            # 检查弱密码
            weak_passwords = ["admin", "password", "123456", "root", "test"]
            if any(settings.minio_access_key.lower() == pwd for pwd in weak_passwords):
                security_issues.append(f"MinIO访问密钥过于简单: {settings.minio_access_key}")

            if any(settings.minio_secret_key.lower() == pwd for pwd in weak_passwords):
                security_issues.append(f"MinIO秘密密钥过于简单: {settings.minio_secret_key}")

            details = {
                "security_issues": security_issues,
                "minio_access_key_is_default": settings.minio_access_key == "minioadmin",
                "minio_secret_key_is_default": settings.minio_secret_key == "minioadmin",
                "security_level": "unsafe" if security_issues else "safe"
            }

            if security_issues:
                return ValidationResult(
                    service_name="Security Defaults",
                    success=False,
                    message=f"发现 {len(security_issues)} 个安全风险: {'; '.join(security_issues)}",
                    details=details
                )

            return ValidationResult(
                service_name="Security Defaults",
                success=True,
                message="安全默认值检查通过",
                details=details
            )

        except Exception as e:
            error_msg = f"安全默认值验证异常: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="Security Defaults",
                success=False,
                message=error_msg
            )

    def validate_key_strength(self) -> ValidationResult:
        """验证密钥强度"""
        try:
            logger.info("正在验证密钥强度")

            strength_issues = []

            def check_password_strength(password: str, name: str) -> List[str]:
                """检查密码强度"""
                issues = []

                if len(password) < 8:
                    issues.append(f"{name}: 长度不足8位")

                if not re.search(r'[A-Z]', password):
                    issues.append(f"{name}: 缺少大写字母")

                if not re.search(r'[a-z]', password):
                    issues.append(f"{name}: 缺少小写字母")

                if not re.search(r'\d', password):
                    issues.append(f"{name}: 缺少数字")

                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    issues.append(f"{name}: 缺少特殊字符")

                return issues

            # 检查MinIO密钥强度
            minio_access_issues = check_password_strength(settings.minio_access_key, "MinIO访问密钥")
            minio_secret_issues = check_password_strength(settings.minio_secret_key, "MinIO秘密密钥")

            strength_issues.extend(minio_access_issues)
            strength_issues.extend(minio_secret_issues)

            # 检查API密钥长度
            if len(settings.zhipuai_api_key) < 20:
                strength_issues.append("智谱API密钥长度不足20位")

            details = {
                "strength_issues": strength_issues,
                "minio_access_key_length": len(settings.minio_access_key),
                "minio_secret_key_length": len(settings.minio_secret_key),
                "zhipu_api_key_length": len(settings.zhipuai_api_key),
                "security_strength": "weak" if strength_issues else "strong"
            }

            if strength_issues:
                return ValidationResult(
                    service_name="Key Strength",
                    success=False,
                    message=f"发现 {len(strength_issues)} 个密钥强度问题: {'; '.join(strength_issues)}",
                    details=details
                )

            return ValidationResult(
                service_name="Key Strength",
                success=True,
                message="密钥强度检查通过",
                details=details
            )

        except Exception as e:
            error_msg = f"密钥强度验证异常: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="Key Strength",
                success=False,
                message=error_msg
            )

    def log_config_change(self, service: str, change_type: str, details: Dict[str, Any],
                        old_value: Any = None, new_value: Any = None, reason: str = None) -> None:
        """记录配置变更日志"""
        try:
            # 使用新的审计系统
            log_config_change(
                service=service,
                change_type=change_type,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                metadata=details
            )

            logger.info(f"配置变更已记录: {service} - {change_type}")

        except Exception as e:
            logger.error(f"记录配置变更失败: {str(e)}")

    async def validate_security_configuration(self) -> ValidationResult:
        """综合安全配置验证"""
        try:
            logger.info("正在进行综合安全配置验证")

            # 执行各项安全检查
            defaults_result = self.validate_secure_defaults()
            strength_result = self.validate_key_strength()

            all_issues = []

            if not defaults_result.success:
                all_issues.extend(defaults_result.details.get("security_issues", []))

            if not strength_result.success:
                all_issues.extend(strength_result.details.get("strength_issues", []))

            # 记录安全验证日志
            self.log_config_change(
                service="Security Validation",
                change_type="security_check",
                details={
                    "defaults_check": defaults_result.success,
                    "strength_check": strength_result.success,
                    "total_issues": len(all_issues)
                }
            )

            details = {
                "security_issues": all_issues,
                "defaults_validation": defaults_result.to_dict(),
                "strength_validation": strength_result.to_dict(),
                "overall_security_level": "unsafe" if all_issues else "safe"
            }

            if all_issues:
                return ValidationResult(
                    service_name="Security Configuration",
                    success=False,
                    message=f"发现 {len(all_issues)} 个安全问题需要修复",
                    details=details
                )

            return ValidationResult(
                service_name="Security Configuration",
                success=True,
                message="安全配置验证全部通过",
                details=details
            )

        except Exception as e:
            error_msg = f"安全配置验证异常: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="Security Configuration",
                success=False,
                message=error_msg
            )

    async def validate_database_connection(self) -> ValidationResult:
        """验证数据库连接"""
        try:
            logger.info(f"正在验证数据库连接: {settings.database_url}")

            # 解析数据库URL
            parsed_url = urlparse(settings.database_url)

            # 连接数据库
            conn = psycopg2.connect(
                host=parsed_url.hostname,
                port=parsed_url.port or 5432,
                database=parsed_url.path[1:],  # 移除开头的 /
                user=parsed_url.username,
                password=parsed_url.password,
                connect_timeout=settings.database_connect_timeout
            )

            # 测试查询
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                db_version = cursor.fetchone()[0]

            conn.close()

            details = {
                "host": parsed_url.hostname,
                "port": parsed_url.port or 5432,
                "database": parsed_url.path[1:],
                "version": db_version,
                "connection_timeout": settings.database_connect_timeout
            }

            return ValidationResult(
                service_name="PostgreSQL",
                success=True,
                message="数据库连接成功",
                details=details
            )

        except OperationalError as e:
            error_msg = f"数据库连接失败: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="PostgreSQL",
                success=False,
                message=error_msg,
                details={"error_code": getattr(e, 'pgcode', 'UNKNOWN')}
            )
        except Exception as e:
            error_msg = f"数据库验证异常: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="PostgreSQL",
                success=False,
                message=error_msg
            )

    async def validate_minio_connection(self) -> ValidationResult:
        """验证 MinIO 连接"""
        if not MINIO_AVAILABLE:
            return ValidationResult(
                service_name="MinIO",
                success=False,
                message="MinIO 依赖包未安装",
                details={"suggestion": "请安装 minio 包: pip install minio"}
            )

        try:
            logger.info(f"正在验证 MinIO 连接: {settings.minio_endpoint}")

            # 解析端点
            endpoint_parts = settings.minio_endpoint.split(':')
            host = endpoint_parts[0]
            port = int(endpoint_parts[1]) if len(endpoint_parts) > 1 else 9000

            # 创建 MinIO 客户端
            client = Minio(
                endpoint=f"{host}:{port}",
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure
            )

            # 检查连接状态
            buckets = client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]

            details = {
                "endpoint": settings.minio_endpoint,
                "access_key": "***REDACTED***",  # 完全隐藏
                "secure": settings.minio_secure,
                "bucket_count": len(bucket_names),
                "buckets": bucket_names
            }

            return ValidationResult(
                service_name="MinIO",
                success=True,
                message="MinIO 连接成功",
                details=details
            )

        except Exception as e:
            error_msg = f"MinIO 验证异常: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="MinIO",
                success=False,
                message=error_msg
            )

    async def validate_chromadb_connection(self) -> ValidationResult:
        """验证 ChromaDB 连接"""
        if not CHROMADB_AVAILABLE:
            return ValidationResult(
                service_name="ChromaDB",
                success=False,
                message="ChromaDB 依赖包未安装",
                details={"suggestion": "请安装 chromadb 包: pip install chromadb"}
            )

        try:
            logger.info(f"正在验证 ChromaDB 连接: {settings.chroma_host}:{settings.chroma_port}")

            # 创建 ChromaDB 客户端
            client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port
            )

            # 获取集合列表
            collections = client.list_collections()
            collection_names = [collection.name for collection in collections]

            # 测试创建临时集合
            test_collection_name = "test_collection_validation"
            try:
                test_collection = client.create_collection(name=test_collection_name)
                client.delete_collection(name=test_collection_name)
                test_result = True
            except Exception as test_e:
                test_result = False
                logger.warning(f"ChromaDB 集合创建测试失败: {test_e}")

            details = {
                "host": settings.chroma_host,
                "port": settings.chroma_port,
                "collection_count": len(collection_names),
                "collections": collection_names,
                "create_collection_test": test_result
            }

            return ValidationResult(
                service_name="ChromaDB",
                success=True,
                message="ChromaDB 连接成功",
                details=details
            )

        except Exception as e:
            error_msg = f"ChromaDB 连接失败: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="ChromaDB",
                success=False,
                message=error_msg
            )

    async def validate_zhipu_api(self) -> ValidationResult:
        """验证智谱 API 连接"""
        try:
            logger.info("正在验证智谱 API 连接")

            # 使用已有的智谱服务进行连接测试
            is_connected = zhipu_service.check_connection()

            if is_connected:
                details = {
                    "api_key_prefix": settings.zhipuai_api_key[:8] + "***",
                    "default_model": "glm-4",
                    "connection_test": "passed"
                }

                return ValidationResult(
                    service_name="ZhipuAI",
                    success=True,
                    message="智谱 API 连接成功",
                    details=details
                )
            else:
                return ValidationResult(
                    service_name="ZhipuAI",
                    success=False,
                    message="智谱 API 连接测试失败"
                )

        except Exception as e:
            error_msg = f"智谱 API 验证异常: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="ZhipuAI",
                success=False,
                message=error_msg
            )

    async def validate_required_env_vars(self) -> ValidationResult:
        """验证必需的环境变量"""
        try:
            logger.info("正在验证必需的环境变量")

            required_vars = {
                "DATABASE_URL": settings.database_url,
                "ZHIPUAI_API_KEY": settings.zhipuai_api_key,
                "MINIO_ACCESS_KEY": settings.minio_access_key,
                "MINIO_SECRET_KEY": settings.minio_secret_key
            }

            missing_vars = []
            invalid_vars = []

            for var_name, var_value in required_vars.items():
                if not var_value:
                    missing_vars.append(var_name)
                elif var_name.endswith("_API_KEY") and len(var_value) < 10:
                    invalid_vars.append(f"{var_name} (长度不足)")

            details = {
                "total_required": len(required_vars),
                "missing": missing_vars,
                "invalid": invalid_vars
            }

            if missing_vars or invalid_vars:
                message_parts = []
                if missing_vars:
                    message_parts.append(f"缺少变量: {', '.join(missing_vars)}")
                if invalid_vars:
                    message_parts.append(f"无效变量: {', '.join(invalid_vars)}")

                return ValidationResult(
                    service_name="Environment Variables",
                    success=False,
                    message="; ".join(message_parts),
                    details=details
                )

            return ValidationResult(
                service_name="Environment Variables",
                success=True,
                message="所有必需环境变量已正确设置",
                details=details
            )

        except Exception as e:
            error_msg = f"环境变量验证异常: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                service_name="Environment Variables",
                success=False,
                message=error_msg
            )

    async def validate_all_configs(self) -> Dict[str, Any]:
        """验证所有配置"""
        logger.info("开始全面配置验证")

        # 首先进行安全配置验证（同步方法）
        security_result = self.validate_security_configuration()

        validation_tasks = [
            self.validate_required_env_vars(),
            self.validate_database_connection(),
            self.validate_minio_connection(),
            self.validate_chromadb_connection(),
            self.validate_zhipu_api()
        ]

        # 并行执行所有验证
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)

        # 添加安全验证结果
        results.insert(0, security_result)

        # 处理结果
        validation_results = []
        failed_count = 0
        security_issues_count = 0

        for result in results:
            if isinstance(result, Exception):
                # 处理异常
                error_result = ValidationResult(
                    service_name="Unknown",
                    success=False,
                    message=f"验证过程中发生异常: {str(result)}"
                )
                validation_results.append(error_result)
                failed_count += 1
            else:
                validation_results.append(result)
                if not result.success:
                    failed_count += 1
                    if result.service_name in ["Security Configuration", "Security Defaults", "Key Strength"]:
                        security_issues_count += 1

        success_count = len(validation_results) - failed_count
        total_count = len(validation_results)

        # 根据是否有安全问题确定整体状态
        if security_issues_count > 0:
            overall_status = "security_issues"
        elif failed_count == 0:
            overall_status = "success"
        elif success_count > 0:
            overall_status = "partial_success"
        else:
            overall_status = "failed"

        summary = {
            "overall_status": overall_status,
            "total_services": total_count,
            "successful": success_count,
            "failed": failed_count,
            "security_issues": security_issues_count,
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None,
            "results": [result.to_dict() for result in validation_results],
            "security_alert": security_issues_count > 0,
            "security_message": f"发现 {security_issues_count} 个安全问题需要立即处理" if security_issues_count > 0 else "安全配置检查通过"
        }

        logger.info(f"配置验证完成: {success_count}/{total_count} 成功，安全 issues: {security_issues_count}")

        # 记录配置验证完成日志
        self.log_config_change(
            service="Configuration Validation",
            change_type="full_validation",
            details={
                "overall_status": overall_status,
                "total_services": total_count,
                "successful": success_count,
                "failed": failed_count,
                "security_issues": security_issues_count
            }
        )

        return summary


# 全局配置验证器实例
config_validator = ConfigValidator()


# 便捷函数
async def validate_database() -> ValidationResult:
    """验证数据库连接的便捷函数"""
    return await config_validator.validate_database_connection()


async def validate_minio() -> ValidationResult:
    """验证MinIO连接的便捷函数"""
    return await config_validator.validate_minio_connection()


async def validate_chromadb() -> ValidationResult:
    """验证ChromaDB连接的便捷函数"""
    return await config_validator.validate_chromadb_connection()


async def validate_zhipu() -> ValidationResult:
    """验证智谱API的便捷函数"""
    return await config_validator.validate_zhipu_api()


async def validate_all() -> Dict[str, Any]:
    """验证所有配置的便捷函数"""
    return await config_validator.validate_all_configs()


async def validate_security() -> ValidationResult:
    """验证安全配置的便捷函数"""
    return config_validator.validate_security_configuration()


def validate_defaults() -> ValidationResult:
    """验证安全默认值的便捷函数"""
    return config_validator.validate_secure_defaults()


def validate_key_strength() -> ValidationResult:
    """验证密钥强度的便捷函数"""
    return config_validator.validate_key_strength()