# 项目重构脚本

此脚本集用于将项目重构为模块化的目录结构。

## 新目录结构

```
insight-agent/
├── apps/                          # 应用层
│   ├── frontend/                  # Next.js 前端
│   └── backend/                   # FastAPI 后端
│
├── services/                      # 核心服务
│   ├── agent-v1/                  # Agent V1 (LangGraph)
│   └── agent-v2/                  # Agent V2 (多智能体)
│
├── infrastructure/                # 基础设施
│   ├── docker/                    # Docker 配置
│   ├── database/                  # 数据库迁移和脚本
│   └── storage/                   # 数据存储
│
├── tools/                         # 工具和脚本
│   ├── deployment/                # 部署脚本
│   ├── development/               # 开发工具
│   └── testing/                   # 测试工具
│
├── docs/                          # 文档
│
├── config/                        # 配置文件
│   ├── docker-compose.yml
│   └── .env.example
│
└── metadata/                      # 元数据
    ├── agent/                     # .agent
    ├── bmad/                      # .bmad-core
    └── openspec/                  # openspec
```

## 使用方法

### 1. 预览重构（推荐先执行）

```bash
python scripts/refactor/refactor.py --dry-run
```

这会显示所有将要执行的操作，但不会实际修改文件。

### 2. 执行重构

```bash
python scripts/refactor/refactor.py --execute
```

这将执行以下操作：
1. 创建备份（`.backup_refactor_<timestamp>/`）
2. 创建新目录结构
3. 移动文件和目录
4. 创建向后兼容的符号链接（Linux/Mac）
5. 更新 .gitignore

### 3. 更新 import 路径

重构完成后，需要更新代码中的 import 语句：

```bash
python scripts/refactor/update_imports.py
```

这会自动更新：
- Python import 语句
- TypeScript/JavaScript import 语句
- docker-compose.yml 中的路径
- 配置文件中的路径引用

### 4. 回滚（如果需要）

如果重构后出现问题，可以回滚到重构前的状态：

```bash
python scripts/refactor/rollback.py
```

或者指定特定的备份目录：

```bash
python scripts/refactor/rollback.py --backup .backup_refactor_20250116_120000
```

## 脚本说明

### analyze_structure.py
分析当前项目结构，生成文件移动映射表。

```bash
python scripts/refactor/analyze_structure.py
```

输出：`scripts/refactor/file_mappings.json`

### refactor.py
主重构脚本，执行目录结构重构。

```bash
# 预览
python scripts/refactor/refactor.py --dry-run

# 执行
python scripts/refactor/refactor.py --execute
```

### update_imports.py
更新代码中的 import 路径和配置文件引用。

```bash
python scripts/refactor/update_imports.py
```

### rollback.py
回滚到重构前的状态。

```bash
python scripts/refactor/rollback.py
```

## 注意事项

1. **执行前建议先提交代码**到 Git，这样可以轻松撤销所有更改
2. **先执行 --dry-run** 预览所有操作
3. **备份会自动创建**，但建议额外手动备份重要数据
4. **Windows 用户**：符号链接功能不可用，需要手动更新路径引用
5. **Docker Compose** 需要更新卷挂载路径
6. **环境变量** 可能需要更新路径配置

## 执行后检查清单

- [ ] 所有文件已正确移动
- [ ] 前端可以正常启动 (`npm run dev`)
- [ ] 后端可以正常启动 (`uvicorn src.app.main:app`)
- [ ] Docker Compose 可以正常启动 (`docker compose up -d`)
- [ ] 所有 import 语句已更新
- [ ] 配置文件路径已更新
- [ ] 测试通过

## 故障排除

### 问题：前端启动失败
检查 `frontend/package.json` 中的路径配置

### 问题：后端启动失败
检查 Python import 语句是否已更新，特别是 Agent 相关的导入

### 问题：Docker Compose 启动失败
检查 `docker-compose.yml` 中的卷挂载路径

### 问题：导入错误
运行 `python scripts/refactor/update_imports.py` 更新所有路径引用
