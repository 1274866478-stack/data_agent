# [DATA] 数据持久化层

## [MODULE]
**模块名称**: 数据持久化层
**职责**: ORM模型定义、数据库连接、会话管理
**类型**: SQLAlchemy ORM

## [BOUNDARY]
**输入**:
- 连接字符串 (DATABASE_URL)
- 模型查询 (Query)
- 事务操作 (Transaction)

**输出**:
- 模型实例 (Model Instances)
- 查询结果 (Query Results)
- 数据库会话 (Session)

## [PROTOCOL]
1. 使用 SQLAlchemy 2.0 async 模式
2. 所有数据库操作必须异步 (async/await)
3. 租户隔离通过 tenant_id 过滤实现
4. 使用连接池管理数据库连接

## [STRUCTURE]
```
data/
├── __init__.py
├── database.py             # 数据库连接与会话管理
└── models.py               # SQLAlchemy ORM 模型定义
    ├── Tenant              # 租户模型
    ├── DataSourceConnection
    └── KnowledgeDocument
```

## [LINK]
**上游依赖**:
- [../core/config.py](../core/config.py) - 数据库配置

**下游依赖**:
- [../services/](../services/_folder.md) - 服务层使用模型进行数据操作

**关联表**:
- tenants (主表)
- data_source_connections (租户子表)
- knowledge_documents (租户子表)

## [STATE]
- engine: SQLAlchemy 异步引擎 (单例)
- AsyncSession: 每个请求独立会话
- Base: 声明式基类 (模型注册)

## [THREAD-SAFE]
是 - AsyncSession 每个请求独立

## [SIDE-EFFECTS]
- 数据库读写操作
- 事务提交/回滚
- 连接池状态变化
