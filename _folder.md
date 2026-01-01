# Data Agent V4 - 根目录

## [MODULE]
**模块名称**: Data Agent V4 项目根目录
**职责**: 多租户SaaS数据智能分析平台的顶层入口 - 项目组织、模块协调、文档管理、配置管理
**类型**: 项目根目录

## [BOUNDARY]
**输入**:
- 用户需求（数据分析、查询、可视化）
- 开发者需求（功能开发、代码维护）
- 运维需求（部署、监控）

**输出**:
- 完整的数据分析平台
- 文档和规范
- 部署配置
- 开发工具

## [PROTOCOL]
1. **FractalFlow协议**: 所有代码文件必须遵循FractalFlow文档规范
2. **OpenSpec流程**: 重大变更需要通过OpenSpec提案
3. **多租户优先**: 所有模块必须支持租户隔离
4. **配置管理**: 敏感配置通过环境变量，禁止硬编码
5. **文档同步**: 代码变更必须同步更新文档

## [STRUCTURE]
```
data_agent/
├── backend/                 # FastAPI后端服务
│   ├── src/                # 源代码
│   ├── tests/              # 测试文件
│   ├── data/               # 测试数据
│   ├── logs/               # 日志输出
│   ├── migrations/         # 数据库迁移
│   └── scripts/            # 后端脚本
├── frontend/               # Next.js前端应用
│   ├── src/                # 源代码
│   ├── public/             # 静态资源
│   └── e2e/                # 端到端测试
├── Agent/                  # LangGraph SQL智能代理
│   ├── sql_agent.py        # 主程序
│   ├── config.py           # 配置
│   ├── models.py           # 数据模型
│   ├── chart_service.py    # 图表服务
│   ├── data_transformer.py # 数据转换
│   ├── terminal_viz.py     # 终端可视化
│   └── charts/             # 图表输出
├── data_storage/           # 本地数据库存储
├── docs/                   # 项目文档
├── scripts/                # 自动化脚本
├── openspec/               # OpenSpec变更管理
├── .github/                # GitHub配置
├── docker-compose.yml      # Docker编排
├── CLAUDE.md              # 项目AI上下文
├── .claudecode.md         # Claude Code协议
├── .env.example           # 环境变量模板
└── README.md              # 项目说明
```

## [LINK]
**上游依赖**:
- 无（项目根目录）

**下游依赖**:
- [./backend/](./backend/_folder.md) - FastAPI后端服务（API、业务逻辑、数据层）
- [./frontend/](./frontend/_folder.md) - Next.js前端应用（用户界面、状态管理）
- [./Agent/](./Agent/_folder.md) - LangGraph SQL智能代理（独立服务）
- [./docs/](./docs/_folder.md) - 项目文档（PRD、架构设计、用户故事）
- [./scripts/](./scripts/_folder.md) - 自动化脚本（Docker管理、配置验证）
- [./openspec/](./openspec/_folder.md) - OpenSpec变更管理（提案、规格）

**调用方**:
- 开发者（代码开发、维护）
- 运维人员（部署、监控）
- 项目管理者（需求管理、进度跟踪）

## [STATE]
- 项目配置文件（.env.example, docker-compose.yml）
- FractalFlow规范文档
- OpenSpec变更记录
- 开发工具和脚本

## [THREAD-SAFE]
不适用（项目目录结构）

## [SIDE-EFFECTS]
- 项目结构变更影响所有子模块
- 配置变更影响部署和运行
- 文档变更影响开发流程
