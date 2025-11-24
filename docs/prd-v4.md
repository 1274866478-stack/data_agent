# Data Agent V4 - 产品需求文档 (PRD - SaaS MVP)

**版本**: 4.1 (Zhipu 版)  
**日期**: 2025年11月16日  
**PM**: John (BMad)  
**基于**: Project Brief V4 (SaaS MVP)

---

## 变更日志 (Change Log)

| 日期 | 版本 | 描述 | 作者 |
|:---|:---|:---|:---|
| 2025-11-15 | 4.0 | 重大转向：从 V3 本地 Demo 转向 V4 SaaS MVP | John |
| 2025-11-15 | 4.1 | 技术纠正：将核心 LLM 依赖从 DeepSeek API 切换为智谱 (Zhipu) API | John |
| 2025-11-16 | 4.1 | 合并所有 PRD 文档和分片到统一 V4 版本 | John |

---

## 第 1 部分: 目标与背景上下文 (Goals and Background Context)

### 目标 (Goals)

1. **(V4 核心)** 验证 **"BYO-Data"(自带数据)** SaaS 循环在技术上是可行且有价值的。
2. **(V4 核心)** 实现**多租户用户认证**升级为**托管认证服务**(例如 Clerk, Auth0, Firebase Auth)和**基础的数据隔离**。
3. **(V3 保留)** 建立"可解释的"信任(通过 100% 的 **XAI 推理路径**)。
4. **(V3 保留)** 保持快速响应(本地 MVP 目标 < 8 秒)。

### 背景上下文 (Background Context)

本项目旨在构建一个**云就绪 (Cloud-Ready)** 的 MVP，用于验证一个**多租户 SaaS 平台**的可行性。V4 的核心是允许"不同的用户"(租户)安全地"**导入自己的数据库和知识库**"，并查询**自己**的数据。这个 MVP 将**在本地通过 Docker Compose 运行**，以模拟云环境，并在效果验证后**部署到云服务器**。

### 核心价值主张

- **多租户架构**: 企业级数据隔离和安全性
- **自带数据 (BYO-Data)**: 用户可以连接自己的数据库和知识库
- **AI 驱动**: 基于智谱 AI 的智能数据分析和洞察生成
- **易于使用**: 直观的用户界面和交互体验
- **云就绪**: 本地验证后可快速部署到云服务器

---

## 第 2 部分: 需求 (Requirements)

### 功能性需求 (Functional Requirements)

- **FR1 (V4)**: 系统必须是**多租户**的。用户**必须**通过**托管认证服务**(例如 Clerk, Auth0)进行登录。
- **FR2 (V4)**: 登录后的用户必须能访问一个**数据源连接页面**。
- **FR3 (V4)**: 用户必须能通过该 UI 提交**外部 PostgreSQL 数据库的连接字符串**。
- **FR4 (V4)**: 用户必须能通过该 UI **上传 PDF/Word 文档**。
- **FR5 (V4)**: 所有 API(特别是 `/api/v1/query`)必须是**租户隔离**的。Agent **绝不能**查询到不属于当前登录用户的数据。
- **FR6 (V3 保留)**: 系统必须保留 **Agentic RAG-SQL** 和**自我修正**逻辑。
- **FR7 (V3 保留)**: 答案必须包含**来源追溯**。
- **FR8 (V3 保留)**: 答案必须包含**可解释性 (XAI) 推理路径**。

### 非功能性需求 (Non-Functional Requirements)

- **NFR1 (V4)**: **部署 (MVP)**: 整个系统(前后端、数据库)**必须**能通过 **Docker Compose** 在本地一键启动。
  - **环境变量 (更新)**: Docker Compose 配置必须将 `ZHIPUAI_API_KEY`(而不是 `DEEPSEEK_API_KEY`)传递给后端服务。
- **NFR2 (V4)**: **部署 (Production)**: 架构必须**为云服务器部署做好准备**(例如，使用 12-Factor App 原则)。
- **NFR3 (V4)**: **结构化数据库**: 必须使用 **PostgreSQL**(本地 MVP 中通过 Docker 运行)。
- **NFR4 (V4)**: **非结构化存储**: 必须使用**对象存储**(本地 MVP 中使用 **MinIO**)。
- **NFR5 (V4 更新)**: **LLM 依赖**: 所有语言理解和生成任务均通过 **智谱 AI (Zhipu) API (GLM)** 完成(例如 `glm-4`)。
- **NFR6 (V3 保留)**: **UI 规范**: 继续使用 "the curator." `style.md` 规范。

### 性能要求

- 查询响应时间 < 8 秒(本地 MVP)
- 查询响应时间 < 5 秒(生产环境)
- 系统可用性 > 99.5%(生产环境)
- 支持并发用户数 > 100(MVP), > 1000(生产)

### 安全要求

- 数据加密传输(HTTPS)和存储
- JWT 身份认证和授权
- 租户数据完全隔离
- 审计日志和合规性
- 敏感信息(如数据库连接字符串)加密存储

---

## 第 3 部分: 用户界面设计目标 (User Interface Design Goals)

### 屏幕 1 (V4 新增): 登录界面 (Login Screen)

**目的**: 用户通过托管认证服务(Clerk/Auth0)登录。

**关键元素**:
- 登录表单(邮箱/密码)
- 第三方登录选项(Google, GitHub 等)
- 注册链接
- 忘记密码链接

**UI 规范**: 遵循 "the curator." `style.md` 风格。

### 屏幕 2 (V4 新增): 数据源管理 (Data Source Management)

**目的**: 用户管理自己的数据源(数据库连接和文档上传)。

**关键元素**:
- **数据库连接区域**:
  - 连接字符串输入框
  - 连接名称输入框
  - "测试连接"按钮
  - "保存连接"按钮
  - 已连接数据库列表
- **文档上传区域**:
  - 文件拖放区域
  - 文件选择按钮
  - 支持的文件类型提示(PDF, DOCX)
  - 已上传文档列表(含状态: PENDING, INDEXING, READY)

**UI 规范**: 使用 shadcn/ui 组件，Tailwind CSS 样式。

### 屏幕 3 (V3 保留): 主查询/聊天界面 (Chat Interface)

**目的**: 用户通过自然语言查询自己的数据。

**关键元素**:
- 聊天消息列表
- 查询输入框
- 发送按钮
- 加载状态指示器
- **V3 特性**:
  - XAI 推理路径展示
  - 来源追溯信息(citations)
  - Markdown 格式的答案渲染

**UI 规范**: "the curator." 风格，简洁现代。

### 屏幕 4 (V3 保留): 加载状态 (Loading State)

**目的**: 在查询处理期间提供视觉反馈。

**关键元素**:
- 加载动画
- 进度提示文本
- 可选的取消按钮

---

## 第 4 部分: 技术假设 (Technical Assumptions)

### Repository Structure (代码仓库结构)
**Monorepo (单一仓库)** (`frontend`, `backend`, `docs`)

### Service Architecture (服务架构)
**Monolith Backend Service (单体后端服务)** (FastAPI)

### Testing Requirements (测试要求)
**Unit + Integration (单元 + 集成测试)**

### Additional Technical Assumptions (其他技术假设)

**后端**:
- Python 3.10+
- FastAPI
- LangChain / LangGraph
- **后端 SDK (V4 更新)**: 必须安装 `zhipuai`(`pip install zhipuai`)

**前端**:
- Next.js 14+
- shadcn/ui
- Tailwind CSS
- Zustand (状态管理)

**数据库 (V4 升级)**:
- **PostgreSQL** (主数据库)
- **ChromaDB** (向量数据库)

**对象存储 (V4 升级)**:
- **MinIO** (本地 MVP)
- AWS S3 / Cloudflare R2 (生产环境)

**LLM API (V4 更新)**:
- **Zhipu API** (GLM-4)

**认证 (V4 升级)**:
- **Clerk** 或 **Auth0**

**部署 (MVP) (V4 升级)**:
- **Docker Compose**

---

## 第 5 部分: 史诗列表 (Epic List)

### Epic 1 (V4): 基础架构与 SaaS 环境搭建 (Docker Compose)

**目标 (Goal)**: 建立可**本地运行**的 **Docker Compose** 环境，包含 Next.js、FastAPI、**PostgreSQL** 和 **MinIO**。

**范围 (Scope)**:
- 创建项目 Monorepo 结构
- 配置 Docker Compose 编排文件
- 设置 PostgreSQL 数据库容器
- 设置 MinIO 对象存储容器
- 设置 ChromaDB 向量数据库容器
- 配置前端和后端 Dockerfile
- 环境变量管理

**成功标准**:
- `docker compose up` 一键启动所有服务
- 所有服务健康检查通过
- 前端可访问 `http://localhost:3000`
- 后端可访问 `http://localhost:8004`

### Epic 2 (V4): 多租户认证与数据源管理

**目标 (Goal)**: 集成**托管认证服务**(如 Clerk)，并构建允许用户**导入数据库连接字符串**和**上传文档**到 MinIO 的 UI 界面。

**范围 (Scope)**:
- 集成 Clerk/Auth0 认证服务
- 实现用户注册和登录流程
- 创建租户管理系统
- 实现数据库连接字符串管理
- 实现文档上传功能
- 构建数据源管理 UI

**成功标准**:
- 用户可以成功注册和登录
- 用户可以添加和管理数据库连接
- 用户可以上传 PDF/Word 文档
- 所有操作都是租户隔离的

### Epic 3 (V4): 租户隔离的 Agentic 核心 (Backend)

**目标 (Goal)**: **重构** Epic V3 的 AI 逻辑。确保 Agentic Core(RAG-SQL、自我修正、XAI)在执行时，严格使用**当前登录租户**的数据库连接和 ChromaDB 向量，并使用 **Zhipu GLM API** 进行 AI 调用。

**范围 (Scope)**:
- 实现 JWT 验证中间件
- 实现租户隔离的查询 API
- 重构 RAG-SQL 链(租户隔离版)
- 重构 RAG 链(租户隔离版)
- 集成智谱 AI API
- 实现 XAI 和融合引擎
- 确保所有数据访问都基于 tenant_id

**成功标准**:
- 租户 A 绝不能访问租户 B 的数据
- 所有查询都使用正确的租户数据源
- XAI 推理路径清晰可见
- 查询响应时间 < 8 秒

### Epic 4 (V4): V3 UI 集成与交付

**目标 (Goal)**: 保留 "the curator." 风格的聊天界面。将聊天界面连接到 V4 的**租户隔离** API 端点，并确保 XAI 和溯源功能在新架构下正常工作。

**范围 (Scope)**:
- 实现聊天界面组件
- 集成 XAI 推理路径展示
- 实现溯源信息显示
- 实现 Markdown 渲染
- 实现加载状态和错误处理
- V4 功能集成测试

**成功标准**:
- 聊天界面美观且易用
- XAI 推理路径清晰展示
- 来源追溯信息准确
- 所有 V3 功能在 V4 架构下正常工作

---

## 第 6 部分: 史诗详情 (Epic Details)

### Epic 1 详细 Story 列表

#### Story 1.1: 项目结构初始化
- 创建 Monorepo 结构
- 初始化 frontend 和 backend 项目
- 配置 Git 仓库

#### Story 1.2: Docker Compose 环境搭建
- 编写 docker-compose.yml
- 配置服务依赖关系
- 设置网络和卷

#### Story 1.3: 后端基础设施配置
- 创建 backend Dockerfile
- 配置 FastAPI 应用
- 设置数据库连接

#### Story 1.4: 前端基础设施配置
- 创建 frontend Dockerfile
- 配置 Next.js 应用
- 设置 API 客户端

#### Story 1.5: 环境变量和配置管理
- 创建 .env 模板文件
- 配置环境变量加载
- 文档化配置项

### Epic 2 详细 Story 列表

#### Story 2.1: 托管认证服务集成
- 注册 Clerk/Auth0 账号
- 配置认证提供商
- 实现登录/注册流程

#### Story 2.2: 租户管理系统
- 创建 Tenant 数据模型
- 实现租户 CRUD API
- 实现租户隔离中间件

#### Story 2.3: 数据源连接管理
- 创建 DataSourceConnection 数据模型
- 实现连接字符串加密存储
- 实现连接测试功能

#### Story 2.4: 文档上传和管理
- 集成 MinIO SDK
- 实现文件上传 API
- 实现文档索引功能

#### Story 2.5: 数据源管理界面
- 创建数据源管理页面
- 实现数据库连接 UI
- 实现文档上传 UI

### Epic 3 详细 Story 列表

#### Story 3.1: 租户隔离的查询 API
- 实现 JWT 验证依赖项
- 创建 /api/v1/query 端点
- 实现租户 ID 提取

#### Story 3.2: RAG-SQL 链(租户隔离版)
- 重构 SQL 生成逻辑
- 实现租户数据库连接获取
- 实现 SQL 执行和结果处理

#### Story 3.3: RAG 链(租户隔离版)
- 重构文档检索逻辑
- 实现租户向量过滤
- 实现文档内容提取

#### Story 3.4: 智谱 AI 集成和推理
- 安装 zhipuai SDK
- 实现 LLM 调用封装
- 实现提示词工程

#### Story 3.5: XAI 和融合引擎
- 实现推理路径记录
- 实现结果融合逻辑
- 实现溯源信息生成

### Epic 4 详细 Story 列表

#### Story 4.1: 聊天界面集成
- 创建聊天组件
- 实现消息列表渲染
- 实现查询输入和发送

#### Story 4.2: XAI 推理路径展示
- 创建 XAI 展示组件
- 实现推理步骤可视化
- 实现交互式展开/折叠

#### Story 4.3: 溯源信息显示
- 创建 Citation 组件
- 实现来源链接
- 实现页码显示

#### Story 4.4: V4 功能集成测试
- 编写端到端测试
- 执行租户隔离测试
- 性能测试和优化

---

## 第 7 部分: 检查表结果报告 (Checklist Results Report)

### 功能性需求检查

- [x] FR1: 多租户认证 ✓
- [x] FR2: 数据源连接页面 ✓
- [x] FR3: PostgreSQL 连接字符串 ✓
- [x] FR4: 文档上传 ✓
- [x] FR5: 租户隔离 API ✓
- [x] FR6: Agentic RAG-SQL ✓
- [x] FR7: 来源追溯 ✓
- [x] FR8: XAI 推理路径 ✓

### 非功能性需求检查

- [x] NFR1: Docker Compose 部署 ✓
- [x] NFR2: 云就绪架构 ✓
- [x] NFR3: PostgreSQL 数据库 ✓
- [x] NFR4: MinIO 对象存储 ✓
- [x] NFR5: Zhipu API 集成 ✓
- [x] NFR6: "the curator." UI 规范 ✓

### 技术栈验证

- [x] 前端: Next.js 14+ ✓
- [x] UI: shadcn/ui ✓
- [x] 后端: FastAPI ✓
- [x] AI: LangChain/LangGraph ✓
- [x] LLM: Zhipu GLM-4 ✓
- [x] 数据库: PostgreSQL ✓
- [x] 向量库: ChromaDB ✓
- [x] 存储: MinIO ✓
- [x] 认证: Clerk/Auth0 ✓
- [x] 部署: Docker Compose ✓

---

## 第 8 部分: 后续步骤 (Next Steps)

### Architect Prompt (架构师提示)

(V4 Zhipu 更新版) 这份 **PRD V4 (SaaS MVP)** 描述了一个**多租户、云就绪、自带数据 (BYO-Data)** 的系统。请您根据**第 4 部分：技术假设**(特别是 **Docker Compose**、**PostgreSQL**、**MinIO**、**托管认证**和 **Zhipu API**)和 **"the curator." UI 规范**，来创建一份统一的**全栈架构文档 (Fullstack Architecture Document)**。

### 开发团队准备

**前端团队**:
- 熟悉 Next.js 14+ App Router
- 学习 shadcn/ui 组件库
- 理解 "the curator." UI 规范
- 准备 Clerk/Auth0 集成

**后端团队**:
- 熟悉 FastAPI 框架
- 学习 LangChain/LangGraph
- 注册智谱 AI 账号并获取 API Key
- 理解租户隔离架构

**DevOps 团队**:
- 准备 Docker 环境
- 学习 Docker Compose
- 规划云服务器部署方案

### 项目里程碑

**Week 1-2**: Epic 1 完成
- ✅ Docker Compose 环境运行
- ✅ 所有服务健康

**Week 3-4**: Epic 2 完成
- ✅ 认证系统集成
- ✅ 数据源管理功能

**Week 5-6**: Epic 3 完成
- ✅ AI 核心功能实现
- ✅ 租户隔离验证

**Week 7-8**: Epic 4 完成
- ✅ UI 集成完成
- ✅ 所有测试通过
- ✅ 准备部署

### 风险评估

**技术风险**:
- 智谱 AI API 集成复杂性 - **中等**
- 租户隔离实现难度 - **中等**
- 性能优化挑战 - **低**

**业务风险**:
- 用户接受度 - **低**(MVP 验证)
- 市场竞争 - **中等**

### 成功指标

**技术指标**:
- 系统稳定性 > 99%
- 查询响应时间 < 8 秒
- 租户隔离 100% 有效
- 测试覆盖率 > 80%

**业务指标**:
- MVP 功能完整性 100%
- 用户体验满意度 > 4/5
- 准备好云部署

---

## 附录: 相关文档

### 核心文档
- [架构文档 V4](./architecture-v4.md)
- [UI 设计规范](./style.md)
- [Story 文档](./stories/)

### 外部资源
- [智谱 AI 文档](https://open.bigmodel.cn/dev/api)
- [Clerk 文档](https://clerk.com/docs)
- [Next.js 文档](https://nextjs.org/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

---

**文档版本**: V4.1 (合并版)
**创建日期**: 2025-11-16
**最后更新**: 2025-11-16
**产品经理**: John (BMad)
**状态**: ✅ 已批准，准备架构设计

---

*本文档整合了 prd.md、prd-v4.md 和所有 prd-shards 的内容，形成统一的 V4 产品需求文档。*

