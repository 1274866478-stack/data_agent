# Scripts - 自动化脚本模块

## [MODULE]
**模块名称**: 自动化脚本模块
**职责**: 提供Docker管理、环境检查、测试数据生成等自动化工具 - 跨平台开发运维脚本集合
**类型**: 自动化工具集

## [BOUNDARY]
**输入**:
- 命令行参数
- 配置文件（.env, docker-compose.yml）
- 系统环境信息

**输出**:
- 命令行输出
- 日志文件
- 测试数据
- 状态报告

## [PROTOCOL]
1. **跨平台优先**: Python脚本优先，Shell/Batch作为补充
2. **错误处理**: 完善的错误处理和用户提示
3. **日志记录**: 所有脚本输出到logs目录
4. **幂等性**: 脚本可重复执行，不会产生副作用
5. **非破坏性**: 默认使用dry-run模式，明确提示危险操作

## [STRUCTURE]
```
scripts/
├── tools/                  # FractalFlow工具
│   ├── analyze_dependencies.py  # 依赖分析器
│   ├── generate_header.py       # 头部生成器
│   ├── validate_fractalflow.py  # 规范检查器
│   └── *_PROGRESS.md            # 进度报告
├── check-*.py              # Python环境检查脚本
├── check-*.sh              # Shell环境检查脚本
├── docker-*.sh             # Docker启动/停止脚本
├── docker-*.bat            # Docker Windows批处理
├── generate_*.py           # 测试数据生成
├── validate-*.py           # 配置验证脚本
├── verify-*.py             # 集成验证脚本
├── test-all-features.*     # 功能测试脚本
├── setup.sh                # 项目初始化脚本
└── README.md               # 脚本使用说明
```

## [LINK]
**上游依赖**:
- [../.env.example](../.env.example) - 环境变量模板
- [../docker-compose.yml](../docker-compose.yml) - Docker配置
- [../backend/](../backend/_folder.md) - 后端服务（启动、检查）
- [../frontend/](../frontend/_folder.md) - 前端服务（启动、检查）

**下游依赖**:
- Python 3.8+ - Python脚本运行环境
- Docker & Docker Compose - 容器管理
- Node.js & npm - 前端依赖管理
- PostgreSQL - 数据库连接检查

**调用方**:
- 开发者（本地开发）
- CI/CD系统（自动化部署）
- 运维人员（系统维护）

## [STATE]
- Docker服务状态（运行/停止）
- 环境配置状态
- 数据库连接状态
- 测试数据状态

## [THREAD-SAFE]
部分 - 脚本通常顺序执行，避免并发运行

## [SIDE-EFFECTS]
- Docker容器启动/停止
- 数据库数据修改（测试数据）
- 文件系统操作（日志、临时文件）
- 网络请求（健康检查）
