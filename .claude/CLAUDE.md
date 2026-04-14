# CLAUDE.md - Data Agent V4 项目配置

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🎯 Claude Code 工作协议

### 核心原则

| 原则 | 行为 |
|------|------|
| 代码是真理 | 文档与代码不一致时，以代码为准 |
| 简洁优先 | 每个变更尽可能简单 |
| 根因修复 | 不做临时补丁，找根本原因 |
| 持续学习 | 纠正后提取规则，永不再犯 |

### 工作流

1. **Plan First** - 非平凡任务（3+步骤）必须进入 Plan 模式
2. **代码前必问** - 需求模糊时问3个澄清问题，先描述方法等待确认
3. **验证后完成** - 运行测试、检查日志、自问"Staff 工程师会批准吗？"
4. **自主修复 Bug** - 先写复现测试，再修复

### 🚫 禁止事项

- 跳过 Plan 模式
- 忽略影响范围
- 临时补丁
- 硬推出错方案

---

## 上下文工程规范

### 文件头格式（新代码采用）

```python
"""
[IDENTITY]: 核心职责（一句话）
[PURPOSE]: 存在原因

[CONTRACT]
Input: (type) 描述
Output: (type) | Error

[DEPENDS_ON]
- path [RISK: HIGH|MID|LOW]

[CALLED_BY]
- path [WHEN: 场景]
"""
```

### 风险等级

- **HIGH** → 修改前必须读完整源码
- **MID** → 读 Header，必要时读源码
- **LOW** → 仅读 Header

### 修改规则

- **修改前**: 读 Header → 读 HIGH RISK 依赖 → 校验一致性
- **修改后**: 更新 Header → 更新 [CALLED_BY] → 更新 _folder.md

---

## 任务管理

使用 `tasks/` 目录进行任务跟踪：

- `tasks/todo.md` - 当前待办任务
- `tasks/lessons.md` - 经验教训总结（被纠正后必填）

---

## 项目概述

Data Agent V4 是一个多租户 SaaS 数据智能分析平台，采用单体仓库（Monorepo）架构。

- **后端**: FastAPI + Python 3.11 (backend/)
- **前端**: Next.js 14 + TypeScript (frontend/)
- **AI Agent**: LangGraph SQL 智能代理 (backend/src/app/services/agent/)
- **数据库**: PostgreSQL + ChromaDB/Qdrant (向量数据库)
- **存储**: MinIO (对象存储)
- **语义层**: Cube.js

---

## 常用命令

### Docker 编排
```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 停止并删除数据卷 (清理数据)
docker-compose down -v

# 重启单个服务
docker-compose restart backend
docker-compose restart frontend

# 查看服务日志
docker logs dataagent-backend --tail 50
docker-compose logs -f backend  # 实时跟踪
```

### 前端开发 (frontend/)
```bash
cd frontend
npm install
npm run dev          # 开发服务器 (端口 3000)
npm run build        # 生产构建
npm run lint         # ESLint 检查
npm run type-check   # TypeScript 类型检查
npm test            # 单元测试 (Jest)
npm run test:e2e    # E2E 测试 (Playwright)
```

### 后端开发 (backend/)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8004

# 测试
pytest                              # 所有测试
pytest tests/api/v1/                # 特定目录
pytest tests/test_tenant_isolation.py -v  # 单个文件
pytest -m "not slow"              # 排除慢速测试
pytest -k "test_health"            # 匹配名称
pytest --cov=src --cov-report=html  # 覆盖率报告
```

### 数据库迁移
```bash
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
alembic downgrade -1  # 回滚一次迁移
```

---

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 3000 | Next.js 开发服务器 |
| Backend API | 8004 | FastAPI 服务 |
| API 文档 | 8004/docs | Swagger UI |
| PostgreSQL | 5432 | 数据库 |
| MinIO API | 9000 | 对象存储 API |
| MinIO Console | 9001 | 对象存储管理界面 |
| ChromaDB | 8001 | 向量数据库 |
| Cube.js | 4000 | 语义层 |
| Qdrant | 6333 | 向量数据库 (SOTA) |
| MCP ECharts | 3033 | 图表服务 |

---

## 架构要点

### 多租户隔离
所有数据操作必须包含 `tenant_id` 过滤：
```python
# 错误示例
query(select(Tenant).all())

# 正确示例
query(select(Tenant).where(Tenant.tenant_id == current_tenant_id).all()
```

### 前端 API 调用规范
**禁止使用相对路径**，必须使用完整 URL：
```typescript
// 错误
fetch('/api/v1/data-sources')

// 正确
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
fetch(`${API_URL}/data-sources`)
```

### 后端异步模式
所有服务函数必须使用 async/await：
```python
# 服务层
async def create_tenant(db: AsyncSession, tenant_data: TenantCreate):
    stmt = insert(Tenant).values(**tenant_data.dict())
    result = await db.execute(stmt)
    await db.commit()
```

### FastAPI 路由顺序
固定路径必须在动态路径之前注册：
```python
@router.get("/health")      # 固定路径在前
@router.get("/{tenant_id}")   # 动态路径在后
```

### 变量命名规避
避免与模块名冲突的变量名：
```python
# 错误 - status 是模块名
def get_status(status: str):

# 正确
def get_status(status_code: str):
def get_connection_status(status_val: str):
```

### 编码规范要点
- **Python**: Black 格式化、isort 排序导入、flake8 检查、mypy 类型检查
- **TypeScript**: 严格模式、camelCase 变量、PascalCase 组件/类
- **Git 提交**: `<type>(<scope>): <description>` 格式

---

## 目录结构

```
data_agent/
├── frontend/              # Next.js 前端
│   ├── src/
│   │   ├── app/         # App Router 页面
│   │   ├── components/  # React 组件
│   │   └── lib/         # 工具函数 (api.ts 是 API 客户端)
│   └── package.json
│
├── backend/              # FastAPI 后端
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/v1/endpoints/  # API 路由
│   │   │   ├── core/    # 配置 (config.py)
│   │   │   ├── data/    # 数据模型 (models.py)
│   │   │   └── services/ # 业务逻辑
│   │   │       ├── agent/  # LangGraph Agent 服务
│   │   │       │   ├── agent_service.py  # 主编排服务
│   │   │       │   ├── prompts.py       # 系统提示词
│   │   │       │   ├── tools.py        # SQL 工具集
│   │   │       │   └── models.py       # 数据模型
│   │   └── tests/       # 测试
│   ├── pytest.ini        # 测试配置
│   └── requirements.txt
│
├── Agent/               # LangGraph SQL Agent (V1 独立模块)
└── docker-compose.yml    # 服务编排
```

---

## AI Agent 架构

### LangGraph 工作流
1. **Planning**: 理解查询意图，制定执行计划
2. **SQL Generation**: 生成安全的 SQL 查询
3. **Execution**: 执行查询并获取结果
4. **Visualization**: 自动生成图表
5. **Reflection**: 验证结果质量
6. **Clarification**: 需要时请求用户澄清

### Agent 服务位置
核心 Agent 服务位于 `backend/src/app/services/agent/`，通过以下端点调用：
- `/api/v1/query` - 自然语言 SQL 查询
- `/api/v1/llm/chat` - AI 对话接口

### Agent 模块导入
容器内 `PYTHONPATH=/app:/` 使以下导入有效：
```python
from Agent.sql_agent import SQLAgent
```

---

## LLM 提供商配置

- **默认**: DeepSeek (`DEEPSEEK_API_KEY`)
- **备用**: 智谱 GLM (`ZHIPUAI_API_KEY`)
- **扩展**: OpenRouter

优先级: DeepSeek → 智谱 → OpenRouter

---

## 环境配置

### 环境变量分层
- 根目录 `.env` - 全局配置
- `backend/.env` - 后端专用配置
- `frontend/.env.local` - 前端配置

### 安全密钥生成
```bash
python scripts/generate_keys.py --save
python scripts/security_audit.py  # 验证密钥强度
```

---

## 开发环境特性

- **无需认证**: 开发模式自动使用开发 token
- **热重载**: 前后端都支持热重载
- **API 文档**: http://localhost:8004/docs
- **调试面板**: 前端输入框上方显示黄色调试信息

---

## 测试策略

- **后端**: pytest + pytest-asyncio，覆盖率要求 80%
- **前端**: Jest (单元) + Playwright (E2E)
- **集成测试**: Docker 环境下运行完整流程

---

## 常见问题

### 聊天发送按钮无响应
- 确认前端调试面板显示 "开发环境：使用开发token"
- 检查浏览器控制台是否有 401 错误

### 后端容器 unhealthy
```bash
docker logs dataagent-backend --tail 50
docker-compose restart backend
```

### Agent 模块导入错误
确认 `docker-compose.yml` 中 `PYTHONPATH=/app:/` 和卷挂载正确。

### pytest 测试失败
```bash
# 查看详细错误信息
pytest tests/test_file.py -vv

# 只运行失败的测试
pytest --lf

# 进入调试模式
pytest --pdb
```

---

## 相关文档

- [README.md](README.md) - 项目主文档
- [frontend/CLAUDE.md](frontend/CLAUDE.md) - 前端详细文档
- [backend/CLAUDE.md](backend/CLAUDE.md) - 后端详细文档
- [Agent/README.md](Agent/README.md) - Agent 文档
- [docs/](docs/) - 详细架构和 PRD 文档
