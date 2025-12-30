# [SERVICES] 业务服务层

## [MODULE]
**模块名称**: 业务服务层
**职责**: 业务逻辑封装、外部服务集成、数据处理
**类型**: 服务类 (Service Classes)

## [BOUNDARY]
**输入**:
- API 请求数据
- 数据库模型
- 外部服务响应

**输出**:
- 业务结果对象
- 格式化响应数据
- 处理后的数据

## [PROTOCOL]
1. 服务层封装所有业务逻辑
2. 与外部服务 (MinIO, ChromaDB, 智谱AI) 交互
3. 处理数据转换和验证
4. 实现缓存和重试机制

## [STRUCTURE]
```
services/
├── __init__.py
├── agent_service.py        # Agent编排服务
├── llm_service.py          # LLM服务编排
├── zhipu_client.py         # 智谱AI客户端
├── minio_client.py         # MinIO对象存储
├── chromadb_client.py      # ChromaDB向量数据库
├── document_service.py     # 文档管理服务
├── document_processor.py   # 文档解析处理
├── data_source_service.py  # 数据源管理
├── tenant_service.py       # 租户管理
├── conversation_service.py # 对话管理
├── cache_service.py        # 缓存服务
├── encryption_service.py   # 加密服务
├── query_optimization_service.py
├── reasoning_service.py    # 推理服务
├── xai_service.py          # XAI可解释性
├── performance_monitor.py
├── database_factory.py     # 数据库工厂
├── database_interface.py   # 数据库接口
├── fusion_service.py       # 融合服务
├── multimodal_processor.py
├── query_context.py
├── query_performance_monitor.py
├── tenant_config_manager.py
├── usage_monitoring_service.py
├── connection_test_service.py
├── chunked_upload_service.py
└── agent/                  # Agent子模块
    ├── agent_service.py
    ├── data_transformer.py
    ├── models.py
    ├── path_extractor.py
    ├── prompts.py
    ├── response_formatter.py
    ├── tools.py
    ├── examples.py
    └── DIAGNOSIS.md
```

## [LINK]
**上游依赖**:
- [../core/config.py](../core/config.py) - 服务配置
- [../data/models.py](../data/models.py) - 数据模型
- [../api/](../api/_folder.md) - API路由调用服务

**下游依赖**:
- MinIO - 对象存储服务
- ChromaDB - 向量数据库
- 智谱AI API - LLM服务
- PostgreSQL - 主数据库

**调用方**:
- API端点 (endpoints/*.py)

## [STATE]
- 服务实例: 单例模式 (如 minio_service, zhipu_service)
- 缓存: 内存/Redis缓存
- 连接池: 外部服务连接

## [THREAD-SAFE]
部分 - 需要注意共享状态的并发访问

## [SIDE-EFFECTS]
- 外部API调用
- 文件系统操作
- 缓存写入
- 消息队列发送
