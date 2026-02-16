# [CORE] 核心配置与安全

## [MODULE]
**模块名称**: 核心配置与安全
**职责**: 应用配置、认证授权、日志监控、安全验证
**类型**: 配置与工具模块

## [BOUNDARY]
**输入**:
- 环境变量 (.env)
- 配置文件 (config.yaml)
- 请求上下文 (Request Context)

**输出**:
- Settings 对象
- JWT Token
- Logger 实例
- 验证结果

## [PROTOCOL]
1. 配置通过 Pydantic Settings 管理
2. JWT 认证基于 Clerk 公钥验证
3. 日志使用 structlog 结构化记录
4. 启动时进行配置验证和审计

## [STRUCTURE]
```
core/
├── config.py              # 应用配置 (Settings类)
├── auth.py                # JWT认证逻辑
├── logging.py             # 日志配置
├── monitoring.py          # Sentry监控
├── config_validator.py    # 配置验证
├── config_audit.py        # 配置变更审计
├── key_rotation.py        # 密钥轮换
├── jwt_utils.py           # JWT工具函数
├── security_monitor.py    # 安全监控
├── performance_optimizer.py
└── api_docs.py            # API文档配置
```

## [LINK]
**上游依赖**:
- [.env](../../.env) - 环境变量配置
- [../../.env.example](../../.env.example) - 配置模板

**下游依赖**:
- [../api/](../api/_folder.md) - API路由 (使用config/auth)
- [../services/](../services/_folder.md) - 服务层 (使用logger)
- [../data/database.py](../data/database.py) - 数据库 (使用config)

**调用方**:
- 所有模块依赖 core 配置和日志

## [STATE]
- Settings: 单例模式，应用启动时初始化
- Logger: 按模块名创建的命名实例
- JWT验证器: 缓存的公钥实例

## [THREAD-SAFE]
是 - 只读配置，线程安全

## [SIDE-EFFECTS]
- 日志写入文件/控制台
- Sentry事件上报
- 配置变更审计日志
