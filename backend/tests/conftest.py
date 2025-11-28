"""
pytest 配置文件
"""

import os
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 设置测试环境变量（符合安全标准）
os.environ.setdefault('ENVIRONMENT', 'testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
os.environ.setdefault('MINIO_ACCESS_KEY', 'test_minio_access_key_for_testing_32chars')
os.environ.setdefault('MINIO_SECRET_KEY', 'test_minio_secret_key_for_testing_must_be_at_least_32_characters_long')
os.environ.setdefault('ZHIPUAI_API_KEY', 'test_zhipu_api_key_12345_for_testing_purposes')
os.environ.setdefault('CLERK_JWT_PUBLIC_KEY', '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJcds3xfn/ygWc
-----END PUBLIC KEY-----''')
os.environ.setdefault('CLERK_API_URL', 'https://test.clerk.dev')

from src.app.main import app
from src.app.data.database import get_db, Base
from src.app.core.config import settings

# 创建测试数据库（内存SQLite）
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_tenant_data():
    """示例租户数据"""
    return {
        "name": "test-tenant",
        "display_name": "Test Tenant",
        "description": "A test tenant for unit testing"
    }


@pytest.fixture
def sample_document_data():
    """示例文档数据"""
    return {
        "tenant_id": 1,
        "title": "Test Document",
        "file_name": "test.pdf",
        "file_size": 1024,
        "file_type": "pdf"
    }


@pytest.fixture
def sample_data_source_data():
    """示例数据源数据"""
    return {
        "tenant_id": 1,
        "name": "test-db-connection",
        "connection_type": "postgresql",
        "connection_string": "postgresql://user:password@localhost:5432/testdb",
        "host": "localhost",
        "port": 5432,
        "database_name": "testdb"
    }


# ============ LLM服务集成测试 Fixtures ============

@pytest.fixture
def mock_zhipu_response():
    """模拟智谱AI标准响应"""
    from unittest.mock import Mock
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "这是智谱AI的测试响应"
    response.choices[0].message.role = "assistant"
    response.choices[0].finish_reason = "stop"
    response.usage = Mock()
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 20
    response.usage.total_tokens = 30
    response.model = "glm-4-flash"
    response.created = 1700000000
    return response


@pytest.fixture
def mock_zhipu_thinking_response():
    """模拟智谱AI思考模式响应"""
    from unittest.mock import Mock
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "最终回答：机器学习是人工智能的核心分支"
    response.choices[0].message.reasoning_content = "让我分析这个问题...\n首先考虑定义...\n然后分析应用领域..."
    response.choices[0].message.role = "assistant"
    response.choices[0].finish_reason = "stop"
    response.usage = Mock()
    response.usage.prompt_tokens = 15
    response.usage.completion_tokens = 50
    response.usage.total_tokens = 65
    response.model = "glm-4-flash"
    response.created = 1700000000
    return response


@pytest.fixture
def mock_zhipu_stream_chunks():
    """模拟智谱AI流式响应块"""
    from unittest.mock import Mock

    chunks = []
    # 思考过程块
    for thinking_part in ["让我思考一下...", "分析问题的关键点...", "整理答案..."]:
        chunk = Mock()
        chunk.choices = [Mock()]
        chunk.choices[0].delta = Mock()
        chunk.choices[0].delta.reasoning_content = thinking_part
        chunk.choices[0].delta.content = None
        chunks.append(chunk)

    # 内容块
    for content_part in ["人工智能", "是一种", "模拟人类智能的技术。"]:
        chunk = Mock()
        chunk.choices = [Mock()]
        chunk.choices[0].delta = Mock()
        chunk.choices[0].delta.reasoning_content = None
        chunk.choices[0].delta.content = content_part
        chunks.append(chunk)

    return chunks


@pytest.fixture
def mock_zhipu_embedding_response():
    """模拟智谱AI嵌入向量响应"""
    from unittest.mock import Mock
    response = Mock()
    mock_data1 = Mock()
    mock_data1.embedding = [0.1] * 1024  # 1024维向量
    mock_data2 = Mock()
    mock_data2.embedding = [0.2] * 1024
    response.data = [mock_data1, mock_data2]
    return response


@pytest.fixture
def sample_chat_messages():
    """示例聊天消息"""
    return [
        {"role": "system", "content": "你是一个专业的AI助手"},
        {"role": "user", "content": "请解释什么是机器学习？"}
    ]


@pytest.fixture
def sample_multi_turn_messages():
    """示例多轮对话消息"""
    return [
        {"role": "system", "content": "你是一个专业的AI助手"},
        {"role": "user", "content": "什么是机器学习？"},
        {"role": "assistant", "content": "机器学习是人工智能的一个分支..."},
        {"role": "user", "content": "它有哪些主要应用场景？"},
        {"role": "assistant", "content": "主要应用场景包括图像识别、自然语言处理..."},
        {"role": "user", "content": "请详细解释自然语言处理"}
    ]


@pytest.fixture
def sample_rag_context():
    """示例RAG上下文"""
    return {
        "documents": [
            {
                "content": "机器学习是一种人工智能技术，它使计算机能够从数据中学习。",
                "source": "ai_basics.pdf",
                "score": 0.95
            },
            {
                "content": "深度学习是机器学习的一个子集，使用神经网络进行特征学习。",
                "source": "deep_learning.pdf",
                "score": 0.88
            }
        ],
        "query": "什么是机器学习？",
        "tenant_id": "test-tenant"
    }


@pytest.fixture
def mock_chromadb_results():
    """模拟ChromaDB查询结果"""
    return {
        "ids": [["doc1", "doc2", "doc3"]],
        "documents": [[
            "机器学习基础知识文档",
            "深度学习入门指南",
            "自然语言处理技术概述"
        ]],
        "metadatas": [[
            {"source": "ml_basics.pdf", "page": 1},
            {"source": "dl_intro.pdf", "page": 5},
            {"source": "nlp_overview.pdf", "page": 3}
        ]],
        "distances": [[0.1, 0.2, 0.3]]
    }


# ============ RAG-SQL集成测试 Fixtures ============

@pytest.fixture
def sample_database_schema():
    """示例数据库Schema"""
    from datetime import datetime
    from src.models.rag_sql import DatabaseSchema, TableInfo, ColumnInfo

    return DatabaseSchema(
        tenant_id="test_tenant",
        connection_id=1,
        database_name="test_db",
        tables={
            "users": TableInfo(
                name="users",
                columns=[
                    ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
                    ColumnInfo(name="name", data_type="VARCHAR", is_nullable=False),
                    ColumnInfo(name="email", data_type="VARCHAR", is_nullable=False),
                    ColumnInfo(name="created_at", data_type="TIMESTAMP", is_nullable=True),
                ]
            ),
            "orders": TableInfo(
                name="orders",
                columns=[
                    ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
                    ColumnInfo(name="user_id", data_type="INTEGER", is_nullable=False, is_foreign_key=True, foreign_table="users"),
                    ColumnInfo(name="amount", data_type="DECIMAL", is_nullable=False),
                    ColumnInfo(name="order_date", data_type="DATE", is_nullable=False),
                ]
            )
        },
        discovered_at=datetime.utcnow()
    )


@pytest.fixture
def sample_query_execution_result():
    """示例SQL执行结果"""
    from src.models.rag_sql import QueryExecutionResult

    return QueryExecutionResult(
        execution_time_ms=100,
        row_count=3,
        columns=[
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "string"},
            {"name": "total_orders", "type": "integer"}
        ],
        data=[
            {"id": 1, "name": "用户A", "total_orders": 15},
            {"id": 2, "name": "用户B", "total_orders": 10},
            {"id": 3, "name": "用户C", "total_orders": 5},
        ],
        has_more=False
    )


@pytest.fixture
def mock_llm_sql_analysis_response():
    """模拟LLM SQL分析响应"""
    from unittest.mock import Mock
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = '{"query_type": "SELECT", "target_tables": ["users"], "columns": ["*"], "conditions": []}'
    response.choices[0].message.role = "assistant"
    response.choices[0].finish_reason = "stop"
    return response


@pytest.fixture
def mock_llm_sql_generation_response():
    """模拟LLM SQL生成响应"""
    from unittest.mock import Mock
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "SELECT id, name, email FROM users WHERE created_at > '2024-01-01'"
    response.choices[0].message.role = "assistant"
    response.choices[0].finish_reason = "stop"
    return response


@pytest.fixture
def mock_llm_result_explanation_response():
    """模拟LLM结果解释响应"""
    from unittest.mock import Mock
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = (
        "根据查询结果分析：\n"
        "1. 共有3位用户有订单记录\n"
        "2. 用户A订单数最多（15单），是最活跃的客户\n"
        "3. 建议关注用户C的活跃度提升"
    )
    response.choices[0].message.role = "assistant"
    response.choices[0].finish_reason = "stop"
    return response


# ============ 通用测试工具 Fixtures ============

@pytest.fixture
def mock_async_generator():
    """创建异步生成器Mock的工厂函数"""
    async def create_async_generator(items):
        for item in items:
            yield item
    return create_async_generator


@pytest.fixture
def tenant_context():
    """租户上下文"""
    return {
        "tenant_id": "test-tenant-001",
        "user_id": "user-001",
        "api_key": "test-api-key-12345"
    }