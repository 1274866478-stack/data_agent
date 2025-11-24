"""
API文档配置
自定义Swagger UI和ReDoc的样式和行为
"""

from typing import Dict, Any


def get_swagger_ui_parameters() -> Dict[str, Any]:
    """
    获取Swagger UI自定义参数
    
    Returns:
        Swagger UI配置字典
    """
    return {
        "syntaxHighlight.theme": "monokai",
        "defaultModelsExpandDepth": 3,
        "defaultModelExpandDepth": 3,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
    }


def get_openapi_schema_overrides() -> Dict[str, Any]:
    """
    获取OpenAPI Schema自定义覆盖
    
    Returns:
        OpenAPI Schema覆盖配置
    """
    return {
        "servers": [
            {
                "url": "http://localhost:8004",
                "description": "本地开发环境",
            },
            {
                "url": "https://api.dataagent.example.com",
                "description": "生产环境",
            },
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Clerk JWT Token认证。在请求头中包含: `Authorization: Bearer <token>`",
                }
            }
        },
        "security": [{"BearerAuth": []}],
    }


# API响应示例
RESPONSE_EXAMPLES = {
    "tenant_response": {
        "summary": "租户信息示例",
        "value": {
            "id": "user_2abc123def456",
            "email": "user@example.com",
            "status": "active",
            "display_name": "张三",
            "settings": {
                "timezone": "Asia/Shanghai",
                "language": "zh-CN",
                "notification_preferences": {
                    "email_notifications": True,
                    "system_alerts": True,
                },
            },
            "storage_quota_mb": 1024,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-15T12:30:00Z",
        },
    },
    "data_source_response": {
        "summary": "数据源信息示例",
        "value": {
            "id": "ds_abc123",
            "tenant_id": "user_2abc123def456",
            "name": "生产数据库",
            "db_type": "postgresql",
            "status": "active",
            "last_tested_at": "2025-01-15T12:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-15T12:00:00Z",
        },
    },
    "document_response": {
        "summary": "文档信息示例",
        "value": {
            "id": "doc_xyz789",
            "tenant_id": "user_2abc123def456",
            "filename": "产品需求文档.pdf",
            "file_size": 2048576,
            "file_type": "application/pdf",
            "status": "processed",
            "chunk_count": 42,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T10:05:00Z",
        },
    },
    "error_response": {
        "summary": "错误响应示例",
        "value": {
            "error": "Validation Error",
            "details": [
                {
                    "loc": ["body", "email"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
            "timestamp": "2025-01-15T12:30:00Z",
        },
    },
    "health_response": {
        "summary": "健康检查响应示例",
        "value": {
            "status": "healthy",
            "services": {
                "database": True,
                "minio": True,
                "chromadb": True,
                "zhipu_ai": True,
            },
            "timestamp": "2025-01-15T12:30:00Z",
            "version": "1.0.0",
        },
    },
}


# API请求示例
REQUEST_EXAMPLES = {
    "create_tenant": {
        "summary": "创建租户请求示例",
        "value": {
            "email": "newuser@example.com",
            "display_name": "新用户",
            "settings": {
                "timezone": "Asia/Shanghai",
                "language": "zh-CN",
            },
        },
    },
    "create_data_source": {
        "summary": "创建数据源请求示例",
        "value": {
            "name": "生产数据库",
            "db_type": "postgresql",
            "connection_string": "postgresql://user:password@localhost:5432/mydb",
        },
    },
    "upload_document": {
        "summary": "上传文档请求示例",
        "description": "使用multipart/form-data上传文件",
    },
}

