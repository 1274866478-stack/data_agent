# 项目重构计划

## 概述

将 Data Agent V4 项目从当前的扁平化结构重构为模块化的目录结构，按功能组织代码。

## 当前结构

```
insight-agent/
├── frontend/          # Next.js 前端
├── backend/           # FastAPI 后端
├── Agent/             # Agent V1
├── AgentV2/           # Agent V2
├── scripts/           # 各种脚本混杂
├── data_storage/      # 数据存储
├── docs/              # 文档
├── docker-compose.yml # 配置文件在根目录
└── ...
```

## 目标结构

```
insight-agent/
├── apps/                          # 应用层
│   ├── frontend/                  # Next.js 前端
│   └── backend/                   # FastAPI 后端
│
├── services/                      # 核心服务（AI Agent）
│   ├── agent-v1/                  # Agent V1 (LangGraph)
│   └── agent-v2/                  # Agent V2 (多智能体)
│
├── infrastructure/                # 基础设施
│   ├── docker/                    # Docker 配置（通过 config 目录）
│   ├── database/                  # 数据库迁移和脚本
│   └── storage/                   # 数据存储
│
├── tools/                         # 工具和脚本
│   ├── deployment/                # 部署相关脚本
│   ├── development/               # 开发工具
│   └── testing/                   # 测试工具
│
├── docs/                          # 文档（保持不变）
│   ├── architecture/
│   ├── api/
│   ├── user-guides/
│   └── qa/
│
├── config/                        # 配置文件
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml.example
│   ├── .env.example
│   └── .mcp.json
│
└── metadata/                      # 元数据和配置管理
    ├── agent/                     # .agent
    ├── bmad/                      # .bmad-core
    ├── openspec/                  # openspec
    └── github/                    # .github
```

## 预览结果

根据 `refactor.py --dry-run` 的执行结果，将执行以下操作：

### 1. 创建新目录结构

```
✓ apps/
  ✓ apps/frontend/
  ✓ apps/backend/
✓ services/
  ✓ services/agent-v1/
  ✓ services/agent-v2/
✓ infrastructure/
  ✓ infrastructure/docker/
  ✓ infrastructure/database/
  ✓ infrastructure/storage/
✓ tools/
  ✓ tools/deployment/
  ✓ tools/development/
  ✓ tools/testing/
✓ config/
✓ metadata/
  ✓ metadata/agent/
  ✓ metadata/bmad/
  ✓ metadata/openspec/
  ✓ metadata/github/
```

### 2. 移动文件和目录

| 原路径 | 新路径 |
|--------|--------|
| frontend/ | apps/frontend/ |
| backend/ | apps/backend/ |
| Agent/ | services/agent-v1/ |
| AgentV2/ | services/agent-v2/ |
| docker-compose.yml | config/docker-compose.yml |
| .env.example | config/.env.example |
| scripts/setup.sh | tools/deployment/setup.sh |
| scripts/docker-start.sh | tools/deployment/docker-start.sh |
| scripts/docker-stop.sh | tools/deployment/docker-stop.sh |
| scripts/security_audit.py | tools/development/security_audit.py |
| data_storage/ | infrastructure/storage/data_storage/ |
| backend/migrations/ | infrastructure/database/migrations/ |
| .agent/ | metadata/agent/.agent/ |
| .bmad-core/ | metadata/bmad/.bmad-core/ |

### 3. 其他操作

- ✓ 跳过符号链接创建（Windows 系统）
- ✓ 更新 .gitignore

## 重构步骤

### 步骤 1: 预览重构（已完成）

```bash
python scripts/refactor/refactor.py
```

### 步骤 2: 执行重构

```bash
python scripts/refactor/refactor.py --execute
```

这将：
- 创建备份到 `.backup_refactor_<timestamp>/`
- 移动所有文件到新位置
- 更新 .gitignore

### 步骤 3: 更新 import 路径

```bash
python scripts/refactor/update_imports.py
```

这将更新：
- Python import 语句
- TypeScript/JavaScript import 语句
- docker-compose.yml 中的路径引用
- 配置文件中的路径

### 步骤 4: 手动更新（可能需要）

- 更新 `docker-compose.yml` 中的 Python 路径设置
- 更新前端 `package.json` 中的脚本路径
- 更新任何硬编码的文件路径

### 步骤 5: 验证

- 启动前端：`cd apps/frontend && npm run dev`
- 启动后端：`cd apps/backend && uvicorn src.app.main:app`
- 启动 Docker：`docker compose up -d`（从 config 目录）

## 回滚计划

如果出现问题，可以使用回滚脚本：

```bash
python scripts/refactor/rollback.py
```

这将：
- 删除新的目录结构
- 从备份恢复原始文件
- 清理重构产生的文件

## 注意事项

1. **Git 状态**：建议先提交当前代码到 Git
2. **备份**：脚本会自动创建备份
3. **运行服务**：重构前需要停止所有运行的服务
4. **IDE 重新加载**：重构后需要重新加载项目

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Import 路径错误 | 高 | update_imports.py 自动更新 + 手动检查 |
| 配置文件路径错误 | 高 | 需要手动更新 docker-compose.yml |
| IDE 配置失效 | 中 | 重新加载项目 |
| Git 历史混乱 | 低 | 使用 git mv 保持历史 |

## 执行前检查清单

- [ ] 已提交当前代码到 Git
- [ ] 已停止所有运行的服务
- [ ] 已备份重要数据（如果有）
- [ ] 已阅读本文档
- [ ] 已预览重构结果（--dry-run）

## 执行后验证清单

- [ ] 新目录结构已创建
- [ ] 所有文件已正确移动
- [ ] Import 路径已更新
- [ ] 配置文件已更新
- [ ] 前端可以启动
- [ ] 后端可以启动
- [ ] Docker Compose 可以启动
- [ ] 所有测试通过

## 决策

是否执行重构？

- **选项 A**: 执行重构 → 运行 `python scripts/refactor/refactor.py --execute`
- **选项 B**: 暂不执行 → 保持当前结构
- **选项 C**: 修改计划 → 调整 `refactor.py` 中的映射规则

---

*文档生成时间: 2025-02-16*
