# Insight Agent - 智能数据分析平台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2+-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-supported-blue.svg)](https://www.docker.com/)

## 目录

- [项目概述](#项目概述)
- [架构设计](#架构设计)
- [模块/组件说明](#模块组件说明)
- [API 说明](#api-说明)
- [开发与运行指南](#开发与运行指南)
- [测试与 CI/CD](#测试与-cicd)
- [常见问题与注意事项](#常见问题与注意事项)

---

## 项目概述

### 项目名称 & 背景

**Insight Agent** 是一个基于 LangGraph 和 DeepAgents 框架的企业级智能数据分析平台。该项目旨在通过自然语言查询技术，让用户无需编写 SQL 代码即可快速分析结构化数据（如 PostgreSQL、MySQL 数据库）和非结构化数据（如 PDF、Word 文档）。

项目采用现代化的多租户 SaaS 架构，提供安全的数据隔离、智能 SQL 生成、文档 RAG（检索增强生成）、可视化图表生成等核心功能。

### 主要目标与使用场景

#### 核心目标
1. **自然语言查询**：用户使用自然语言提问，系统自动生成并执行 SQL 查询
2. **多数据源支持**：支持 PostgreSQL、MySQL、Excel 文件等多种数据源
3. **文档 RAG**：上传文档后可基于文档内容进行智能问答
4. **多租户 SaaS**：企业级多租户架构，数据完全隔离
5. **可解释性 AI**：记录完整的推理过程，提供查询结果的解释说明

#### 使用场景
- **业务数据分析**：销售人员查询订单数据、分析师查看销售趋势
- **运营报表生成**：自动生成周报、月报等业务报表
- **文档智能问答**：基于公司文档（如产品手册、技术文档）进行智能问答
- **临时数据查询**：非技术人员快速查询数据库中的数据
- **数据可视化**：自动生成图表，直观展示数据分析结果

### 技术栈列表

#### 后端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主要开发语言 |
| FastAPI | 0.115.0 | Web 框架 |
| SQLAlchemy | 2.0.34 | ORM 框架 |
| PostgreSQL | 16+ | 主数据库 |
| asyncpg | 0.29.0 | 异步 PostgreSQL 驱动 |
| LangChain | 0.3.0+ | AI 框架 |
| LangGraph | 0.2.20+ | Agent 工作流 |
| DeepSeek | - | 主 LLM 提供商 |
| ZhipuAI | 2.0.1 | 备用 LLM 提供商 |
| ChromaDB | 0.5.0+ | 向量数据库 |
| Qdrant | latest | 向量数据库（SOTA 版本） |
| MinIO | 7.2.0 | 对象存储 |
| Cube.js | latest | 语义层 |
| Sentry | 2.14.0 | 错误监控 |
| Structlog | 24.4.0 | 结构化日志 |

#### 前端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| Node.js | 20+ | 运行环境 |
| Next.js | 14.2.5 | React 框架 |
| TypeScript | 5.5.3+ | 类型系统 |
| Tailwind CSS | 3.4.6 | 样式框架 |
| Radix UI | latest | UI 组件库 |
| Zustand | 5.0.8 | 状态管理 |
| ECharts | 5.6.0 | 数据可视化 |
| Recharts | 3.6.0 | 数据可视化 |
| Clerk | - | 认证服务 |
| Playwright | 1.48.0+ | E2E 测试 |
| Jest | 29.7.0 | 单元测试 |

#### 基础设施
| 技术 | 用途 |
|------|------|
| Docker | 容器化部署 |
| Docker Compose | 多容器编排 |
| Nginx | 反向代理 |
| Redis | 缓存（可选） |

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Insight Agent 系统架构                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  前端层 (Frontend)                              │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                         Next.js 14.2.5 (TypeScript)                        │  │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐ │  │
│  │  │ Dashboard │ │   Chat    │ │ Data S...  │ │ Documents │ │Settings │ │  │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └──────────┘ │  │
│  │  ┌───────────────────────────────────────────────────────────────────────┐  │  │
│  │  │  状态管理 (Zustand) | UI 组件 (Radix UI) | 图表 (ECharts/Recharts) │  │  │
│  │  └───────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        ▲ HTTP/REST API
                                        │
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 API 网关层 (Gateway)                           │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                          FastAPI Application                                │  │
│  │  ┌───────────┐ ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ Middleware │ │  CORS | Auth (JWT/Clerk) | Rate Limiting | Logging    │ │  │
│  │  └───────────┘ └────────────────────────────────────────────────────────┘ │  │
│  │  ┌───────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                          API 路由层                                │  │  │
│  │  │  ┌─────────────────────┐  ┌─────────────────────┐                  │  │  │
│  │  │  │   API v1 (Legacy)  │  │   API v2 (DeepA..) │                  │  │  │
│  │  │  │  • /query          │  │  • /query          │                  │  │  │
│  │  │  │  • /data-sources   │  │  • /health         │                  │  │  │
│  │  │  │  • /documents      │  │  • /capabilities    │                  │  │  │
│  │  │  │  • /llm            │  │  • /cache/stats    │                  │  │  │
│  │  │  │  • /tenants        │  │                    │                  │  │  │
│  │  │  └─────────────────────┘  └─────────────────────┘                  │  │  │
│  │  └───────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               业务服务层 (Services)                              │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                      Domain Services (业务领域服务)                           │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────┐   │  │
│  │  │ QueryService │ │ DataSource   │ │ Document     │ │ TenantService │   │  │
│  │  │ (查询服务)   │ │ Service      │ │ Service      │ │ (租户服务)   │   │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────┘   │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────┐   │  │
│  │  │ LLMService   │ │ AgentService  │ │ Encryption   │ │ CacheService  │   │  │
│  │  │ (LLM服务)    │ │ (Agent服务)  │ │ Service      │ │ (缓存服务)    │   │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                   Integration Services (集成服务)                            │  │
│  │  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐  │  │
│  │  │ AgentV2 Gateway      │  │ DB Adapters          │  │ MCP Integrator  │  │  │
│  │  │ (AgentV2 网关)      │  │ (数据库适配器)       │  │ (MCP 集成)     │  │  │
│  │  └──────────────────────┘  └──────────────────────┘  └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                             Agent 智能体层 (Agents)                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                      LangGraph Agent Engine                                  │  │
│  │  ┌───────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                     LangGraph Workflow                                │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │  │  │
│  │  │  │  Router  │ │ Planner  │ │ Generator│ │  Critic  │ │ Repair │ │  │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │                   Tools (工具集)                             │  │  │  │
│  │  │  │  • execute_query      • list_tables       • get_schema       │  │  │  │
│  │  │  │  • vector_search     • document_rag     • file_processor   │  │  │  │
│  │  │  │  • chart_generator   • sql_validator     • error_memory    │  │  │  │
│  │  │  └────────────────────────────────────────────────────────────────┘  │  │  │
│  │  └───────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                     DeepAgents Framework (AgentV2)                         │  │
│  │  • SubAgent 架构  • 自愈机制  • 消歧系统  • 少样本 RAG                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              数据存储层 (Storage)                               │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │  │
│  │  │   PostgreSQL     │  │   Vector Stores   │  │   Object Storage  │  │  │
│  │  │  (主数据库)       │  │   (向量数据库)     │  │   (对象存储)       │  │  │
│  │  │  • tenants        │  │  • ChromaDB       │  │  • MinIO          │  │  │
│  │  │  • data_sources  │  │  • Qdrant         │  │  • 文件存储        │  │  │
│  │  │  • documents     │  │  • 向量嵌入        │  │  • 文档处理        │  │  │
│  │  │  • query_logs    │  │                   │  │                   │  │  │
│  │  │  • agent_logs    │  │                   │  │                   │  │  │
│  │  └───────────────────┘  └───────────────────┘  └───────────────────┘  │  │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │  │
│  │  │   Cube.js        │  │   Redis (可选)   │  │   File System    │  │  │
│  │  │  (语义层)        │  │  (分布式缓存)      │  │   (本地文件)      │  │  │
│  │  │  • Measures      │  │  • 查询缓存       │  │  • 日志存储        │  │  │
│  │  │  • Dimensions    │  │  • 会话状态       │  │                   │  │  │
│  │  │  • Aggregations  │  │                   │  │                   │  │  │
│  │  └───────────────────┘  └───────────────────┘  └───────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           外部服务集成 (External Services)                        │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  │   DeepSeek LLM    │  │   ZhipuAI LLM    │  │   Clerk Auth      │
│  │  (主 LLM 提供商)  │  │  (备用 LLM 提供商) │  │  (认证服务)        │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  │   Sentry Monitoring│  │   MCP ECharts     │  │   Custom Tools    │
│  │  (错误监控)        │  │  (图表服务)        │  │  (自定义工具)      │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 各层职责说明

#### 1. 前端层 (Frontend Layer)
- **职责**：提供用户交互界面，展示数据和可视化结果
- **技术栈**：Next.js 14 + TypeScript + Tailwind CSS + Radix UI
- **核心组件**：
  - Dashboard：数据概览和统计
  - Chat：AI 助手对话界面
  - Data Sources：数据源管理
  - Documents：文档上传和管理
  - Settings：用户设置

#### 2. API 网关层 (Gateway Layer)
- **职责**：处理 HTTP 请求，路由分发，身份认证，权限控制
- **技术栈**：FastAPI 0.115.0
- **核心功能**：
  - CORS 跨域处理
  - JWT/Clerk 身份认证
  - 速率限制
  - 请求日志记录
  - API 版本管理 (v1/v2)

#### 3. 业务服务层 (Services Layer)
- **职责**：实现业务逻辑，协调数据访问和外部服务调用
- **核心服务**：
  - QueryService：查询处理和结果返回
  - DataSourceService：数据源连接管理
  - DocumentService：文档上传和索引
  - TenantService：租户管理
  - LLMService：大模型调用
  - AgentService：Agent 智能体管理
  - EncryptionService：数据加密/解密
  - CacheService：查询缓存管理

#### 4. Agent 智能体层 (Agents Layer)
- **职责**：实现 AI 智能体，处理自然语言查询，生成 SQL，执行分析
- **框架**：LangGraph + DeepAgents
- **核心组件**：
  - Router：查询路由和消歧
  - Planner：任务分解和规划
  - Generator：DSL/SQL 生成
  - Critic：结果验证
  - Repair：错误自愈
  - Tools：工具集合（查询、文档、图表等）

#### 5. 数据存储层 (Storage Layer)
- **职责**：存储和管理各类数据
- **存储系统**：
  - PostgreSQL：结构化数据（租户、数据源、查询日志等）
  - ChromaDB/Qdrant：向量数据（文档嵌入、语义搜索）
  - MinIO：对象存储（上传文件、文档）
  - Cube.js：语义层（度量、维度、预聚合）
  - Redis：缓存和会话状态（可选）

---

## 模块/组件说明

### 目录结构概览

```
insight-agent/
├── agent/                          # LangGraph SQL Agent (独立模块)
│   ├── agent_config_module/          # Agent 配置模块
│   ├── core/                       # Agent 核心组件
│   ├── context/                    # 业务上下文和词汇表
│   ├── graphs/                     # Agent 工作流定义
│   ├── nodes/                      # Agent 节点实现
│   ├── prompts/                    # 系统 Prompt 模板
│   ├── rules/                      # 业务规则定义
│   ├── subagents/                  # 子 Agent 实现
│   ├── tools/                     # Agent 工具集合
│   └── utils/                     # 工具函数
├── apps/                          # 主应用程序
│   ├── backend/                   # FastAPI 后端
│   │   ├── src/app/
│   │   │   ├── api/              # API 端点
│   │   │   │   ├── v1/           # V1 API (Legacy)
│   │   │   │   │   └── endpoints/ # V1 端点实现
│   │   │   │   └── v2/           # V2 API (DeepAgents)
│   │   │   │       └── endpoints/ # V2 端点实现
│   │   │   ├── core/             # 核心配置
│   │   │   ├── data/             # 数据模型
│   │   │   ├── domains/          # 业务领域服务
│   │   │   ├── integrations/     # 外部服务集成
│   │   │   ├── middleware/       # 中间件
│   │   │   ├── schemas/          # Pydantic 模型
│   │   │   └── services/        # 服务层
│   │   ├── tests/                # 后端测试
│   │   ├── requirements.txt      # Python 依赖
│   │   └── Dockerfile           # 后端 Docker 镜像
│   └── frontend/                # Next.js 前端
│       ├── src/
│       │   ├── app/              # App Router 页面
│       │   ├── components/       # React 组件
│       │   ├── lib/             # 工具和配置
│       │   └── store/           # Zustand 状态
│       ├── package.json          # Node 依赖
│       ├── Dockerfile           # 前端 Docker 镜像
│       └── playwright.config.ts # E2E 测试配置
├── cube_schema/                  # Cube.js 语义层定义
│   ├── Products.yaml             # 商品语义层
│   ├── Orders.yaml               # 订单语义层
│   ├── Customers.yaml            # 客户语义层
│   └── ...                      # 其他语义层定义
├── config/                      # 配置文件
│   └── .env.example             # 环境变量模板
├── docs/                        # 项目文档
├── infrastructure/               # 基础设施
│   └── storage/                 # 文件存储目录
├── tools/                       # 开发工具
└── docker-compose.yml           # Docker 编排配置
```

### 核心模块详解

#### 1. Backend 模块

##### 1.1 API 端点

**V1 API (Legacy LangGraph)**

| 文件 | 路径前缀 | 功能描述 |
|------|-----------|----------|
| `apps/backend/src/app/api/v1/endpoints/tenants.py` | `/api/v1/tenants` | 租户管理 API |
| `apps/backend/src/app/api/v1/endpoints/data_sources.py` | `/api/v1/data-sources` | 数据源连接管理 |
| `apps/backend/src/app/api/v1/endpoints/documents.py` | `/api/v1/documents` | 文档上传和索引 |
| `apps/backend/src/app/api/v1/endpoints/query.py` | `/api/v1/query` | 自然语言查询 |
| `apps/backend/src/app/api/v1/endpoints/llm.py` | `/api/v1/llm` | LLM 对话接口 |
| `apps/backend/src/app/api/v1/endpoints/health.py` | `/api/v1/health` | 健康检查 |
| `apps/backend/src/app/api/v1/endpoints/reasoning.py` | `/api/v1/reasoning` | XAI 推理日志 |
| `apps/backend/src/app/api/v1/endpoints/logs.py` | `/api/v1/logs` | 日志查询 |
| `apps/backend/src/app/api/v1/endpoints/security.py` | `/api/v1/security` | 安全相关 API |
| `apps/backend/src/app/api/v1/endpoints/sql_error_memories.py` | `/api/v1/sql-error-memories` | SQL 错误记忆 |

**V2 API (DeepAgents)**

| 文件 | 路径前缀 | 功能描述 |
|------|-----------|----------|
| `apps/backend/src/app/api/v2/endpoints/query_v2.py` | `/api/v2/query` | AgentV2 查询接口 |
| `/api/v2/health` | - | V2 健康检查 |
| `/api/v2/capabilities` | - | V2 能力列表 |
| `/api/v2/cache/stats` | - | 缓存统计 |

##### 1.2 核心配置

**`apps/backend/src/app/core/` 模块**

| 文件 | 功能描述 |
|------|----------|
| `config.py` | 应用配置管理（从环境变量读取） |
| `encryption.py` | 数据加密/解密服务 |
| `jwt_utils.py` | JWT Token 处理 |
| `security.py` | 安全相关工具（密码哈希等） |

##### 1.3 数据模型

**`apps/backend/src/app/data/` 模块**

| 模型 | 表名 | 功能描述 |
|------|------|----------|
| `Tenant` | `tenants` | 租户信息 |
| `DataSourceConnection` | `data_source_connections` | 数据源连接 |
| `KnowledgeDocument` | `knowledge_documents` | 知识文档 |
| `QueryLog` | `query_logs` | 查询日志 |
| `ExplanationLog` | `explanation_logs` | XAI 解释日志 |
| `FusionResult` | `fusion_results` | 融合结果 |
| `ReasoningPath` | `reasoning_paths` | 推理路径 |
| `SQLErrorMemory` | `sql_error_memory` | SQL 错误记忆 |
| `SuccessfulQuery` | `successful_queries` | 成功查询历史 |
| `RepairHistory` | `repair_history` | 修复历史 |
| `AgentLog` | `agent_logs` | Agent 执行日志 |

##### 1.4 业务领域服务

**`apps/backend/src/app/domains/` 模块**

| 目录 | 功能描述 |
|------|----------|
| `query/` | 查询处理领域 |
| `rag_sql/` | RAG+SQL 融合查询 |
| `llm/` | LLM 服务封装 |
| `data_sources/` | 数据源管理 |
| `documents/` | 文档处理 |
| `tenants/` | 租户管理 |
| `xai/` | 可解释性 AI |

##### 1.5 集成服务

**`apps/backend/src/app/integrations/` 模块**

| 组件 | 功能描述 |
|--------|----------|
| `agentv2_gateway.py` | AgentV2 网关 |
| `db_adapters/` | 数据库适配器（PostgreSQL, MySQL） |
| `mcp/` | Model Context Protocol 集成 |

#### 2. Frontend 模块

##### 2.1 页面结构

**`apps/frontend/src/app/` 模块**

| 路径 | 功能描述 |
|------|----------|
| `/page.tsx` | 首页（仪表板） |
| `/chat/page.tsx` | AI 聊天界面 |
| `/data-sources/page.tsx` | 数据源管理 |
| `/documents/page.tsx` | 文档管理 |
| `/analytics/page.tsx` | 数据分析 |
| `/settings/page.tsx` | 用户设置 |
| `/users/page.tsx` | 用户管理 |

##### 2.2 组件库

**`apps/frontend/src/components/` 模块**

| 组件 | 功能描述 |
|--------|----------|
| `ui/` | 基础 UI 组件（基于 Radix UI） |
| `chat/` | 聊天界面组件 |
| `data-sources/` | 数据源管理组件 |
| `documents/` | 文档管理组件 |
| `charts/` | 图表组件 |
| `dashboard/` | 仪表板组件 |

#### 3. Agent 模块

**`agent/` 模块**

| 目录 | 功能描述 |
|------|----------|
| `core/` | Agent 核心逻辑 |
| `graphs/` | LangGraph 工作流定义 |
| `nodes/` | 图节点实现 |
| `tools/` | Agent 工具集合 |
| `prompts/` | 系统 Prompt 模板 |
| `context/` | 业务上下文 |
| `rules/` | 业务规则 |
| `subagents/` | 子 Agent 实现 |

##### 3.1 主要类/函数

**Agent 核心类**

```python
# agent/core/agent.py
class LangGraphSQLAgent:
    """LangGraph SQL 智能体"""
    def __init__(self, llm, database_url, ...)
    def invoke(self, query: str) -> AgentResponse
    def get_thread_id(self) -> str
```

**工具函数**

```python
# agent/tools/sql_tools.py
def execute_query(query: str) -> QueryResult
def list_tables() -> List[str]
def get_schema(table_name: str) -> TableSchema

# agent/tools/document_tools.py
def vector_search(query: str, top_k: int) -> List[Document]
def document_rag(query: str) -> RAGResult
```

#### 4. Cube.js 语义层

**`cube_schema/` 模块**

| 文件 | 功能描述 |
|------|----------|
| `Products.yaml` | 商品语义层（度量、维度） |
| `Orders.yaml` | 订单语义层 |
| `Customers.yaml` | 客户语义层 |
| `Categories.yaml` | 分类语义层 |
| `Inventory.yaml` | 库存语义层 |
| `OrderItems.yaml` | 订单项目语义层 |
| `Regions.yaml` | 地区语义层 |
| `SalesOrders.yaml` | 销售订单语义层 |

每个语义层定义包含：
- **Measures（度量）**：可聚合的数值字段
- **Dimensions（维度）**：用于分组和过滤的字段
- **Pre-aggregations（预聚合）**：性能优化配置

---

## API 说明

### API 端点概览

#### V1 API (Legacy LangGraph)

| 端点 | 方法 | 描述 |
|-------|------|------|
| `/api/v1/query` | POST | 执行自然语言查询 |
| `/api/v1/query/status/{query_id}` | GET | 获取查询状态 |
| `/api/v1/query/history` | GET | 获取查询历史 |
| `/api/v1/query/cache/{query_hash}` | DELETE | 清除查询缓存 |
| `/api/v1/data-sources` | GET | 获取数据源列表 |
| `/api/v1/data-sources` | POST | 创建数据源连接 |
| `/api/v1/data-sources/{id}` | GET | 获取数据源详情 |
| `/api/v1/data-sources/{id}` | PUT | 更新数据源 |
| `/api/v1/data-sources/{id}` | DELETE | 删除数据源 |
| `/api/v1/data-sources/{id}/test` | POST | 测试数据源连接 |
| `/api/v1/documents` | GET | 获取文档列表 |
| `/api/v1/documents` | POST | 上传文档 |
| `/api/v1/documents/{id}` | GET | 获取文档详情 |
| `/api/v1/documents/{id}` | DELETE | 删除文档 |
| `/api/v1/tenants` | GET | 获取租户列表 |
| `/api/v1/tenants` | POST | 创建租户 |
| `/api/v1/tenants/{id}` | GET | 获取租户详情 |
| `/api/v1/llm` | POST | LLM 对话 |
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/reasoning/{query_id}` | GET | 获取推理日志 |

#### V2 API (DeepAgents)

| 端点 | 方法 | 描述 |
|-------|------|------|
| `/api/v2/query` | POST | 执行 AgentV2 查询 |
| `/api/v2/health` | GET | V2 健康检查 |
| `/api/v2/capabilities` | GET | 获取 V2 能力列表 |
| `/api/v2/cache/stats` | GET | 获取缓存统计 |

### API 请求/响应格式

#### 1. 查询 API (V1)

**请求格式：**

```http
POST /api/v1/query
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "query": "查询销售额TOP 10的产品",
  "connection_id": "conn_123",
  "data_source_ids": ["ds1", "ds2"],
  "document_ids": ["doc1", "doc2"],
  "options": {
    "enable_cache": true,
    "force_refresh": false,
    "include_chart": true,
    "chart_type": "bar"
  }
}
```

**响应格式：**

```json
{
  "query_id": "uuid-xxx",
  "tenant_id": "tenant_123",
  "original_query": "查询销售额TOP 10的产品",
  "generated_sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10",
  "results": [
    {
      "id": 1,
      "name": "Product A",
      "sales": 1000
    }
  ],
  "row_count": 10,
  "processing_time_ms": 1234,
  "confidence_score": 0.95,
  "explanation": "查询返回了销售额最高的10个产品",
  "processing_steps": [
    {
      "step": 1,
      "title": "分析查询",
      "description": "理解用户查询意图",
      "status": "completed"
    },
    {
      "step": 2,
      "title": "生成 SQL",
      "description": "生成数据库查询语句",
      "status": "completed"
    },
    {
      "step": 3,
      "title": "执行查询",
      "description": "执行 SQL 并获取结果",
      "status": "completed"
    }
  ],
  "echarts_option": {
    "title": {
      "text": "销售额 TOP 10 产品"
    },
    "xAxis": {
      "data": ["Product A", "Product B"]
    },
    "yAxis": {},
    "series": [{
      "type": "bar",
      "data": [1000, 900]
    }]
  }
}
```

#### 2. 查询 API (V2)

**请求格式：**

```http
POST /api/v2/query
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "query": "查询销售额TOP 10的产品",
  "connection_id": "conn_123",
  "session_id": "session_abc",
  "max_results": 100,
  "include_chart": true,
  "chart_type": "bar"
}
```

**响应格式：**

```json
{
  "success": true,
  "answer": "以下是销售额最高的10个产品：...",
  "sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10",
  "data": [
    {
      "id": 1,
      "name": "Product A",
      "sales": 1000
    }
  ],
  "row_count": 10,
  "processing_steps": [
    "分析查询意图",
    "生成SQL查询",
    "执行查询",
    "生成图表"
  ],
  "subagent_calls": ["sql_agent", "chart_agent"],
  "reasoning_log": {
    "timestamp": 1234567890,
    "steps": 4,
    "query": "查询销售额TOP 10的产品",
    "answer_length": 123
  },
  "chart_config": {
    "chart_type": "bar",
    "x_field": "name",
    "y_field": "sales",
    "title": "销售额 TOP 10 产品"
  },
  "processing_time_ms": 1234,
  "tenant_id": "tenant_123",
  "session_id": "session_abc",
  "from_cache": false,
  "query_chain": [
    {
      "step": 1,
      "sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10",
      "source": "agentv2_gateway",
      "row_count": 10
    }
  ],
  "chart_validation": {
    "is_valid": true,
    "message": "图表字段与 SQL 查询结果一致"
  },
  "lineage": [],
  "insights": ["Product A 的销售额最高", "平均销售额为 500"]
}
```

#### 3. 数据源 API

**创建数据源连接：**

```http
POST /api/v1/data-sources
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "name": "生产数据库",
  "db_type": "postgresql",
  "connection_string": "postgresql://user:password@host:5432/database"
}
```

**响应格式：**

```json
{
  "id": "ds_123",
  "name": "生产数据库",
  "db_type": "postgresql",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**测试数据源连接：**

```http
POST /api/v1/data-sources/{id}/test
Authorization: Bearer <JWT_TOKEN>
```

**响应格式：**

```json
{
  "success": true,
  "message": "连接成功",
  "details": {
    "database": "postgres",
    "version": "16.0",
    "table_count": 25
  }
}
```

#### 4. 文档上传 API

**上传文档：**

```http
POST /api/v1/documents
Content-Type: multipart/form-data
Authorization: Bearer <JWT_TOKEN>

file: <PDF_FILE>
name: "产品手册.pdf"
```

**响应格式：**

```json
{
  "id": "doc_123",
  "file_name": "产品手册.pdf",
  "status": "indexing",
  "file_size": 1024000,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### 5. 健康检查 API

**V1 健康检查：**

```http
GET /api/v1/health
```

**响应格式：**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "database": "connected",
    "vector_db": "connected",
    "storage": "connected",
    "llm": "available"
  }
}
```

**V2 健康检查：**

```http
GET /api/v2/health
```

**响应格式：**

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "framework": "DeepAgents",
  "features": [
    "tenant_isolation",
    "sql_security",
    "subagent_architecture",
    "xai_logging"
  ]
}
```

---

## 开发与运行指南

### 环境要求

#### 开发环境要求

| 组件 | 要求 |
|------|------|
| Python | 3.10+ |
| Node.js | 20+ |
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| Git | 2.30+ |
| PostgreSQL | 16+ (可选，Docker 版本亦可) |
| MinIO | latest (可选，Docker 版本亦可) |

#### 推荐开发工具

- IDE：VS Code / PyCharm / WebStorm
- API 测试：Postman / Insomnia
- 数据库管理：DBeaver / pgAdmin
- Git 客户端：GitKraken / SourceTree

### 启动方式

#### 方式 1：Docker Compose（推荐）

**1. 克隆代码仓库**

```bash
git clone https://github.com/your-org/insight-agent.git
cd insight-agent
```

**2. 配置环境变量**

```bash
cp config/.env.example .env
# 编辑 .env 文件，填入实际的配置值
```

**重要环境变量说明：**

```bash
# 智谱 AI API 配置（必填）
ZHIPUAI_API_KEY=your_zhipuai_api_key_here

# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/dataagent
DATABASE_SYNC_URL=postgresql://postgres:password@localhost:5432/dataagent

# MinIO 对象存储配置
MINIO_ROOT_USER=your_strong_minio_root_user_min_32_chars
MINIO_ROOT_PASSWORD=your_strong_minio_root_password_min_64_chars
MINIO_ACCESS_KEY=your_strong_minio_access_key_min_32_chars
MINIO_SECRET_KEY=your_strong_minio_secret_key_min_64_chars

# JWT 密钥（必填，至少 64 字符）
SECRET_KEY=your-super-secret-key-generate-a-strong-one-in-production-min-64-chars

# Cube.js API 密钥（SOTA 功能使用）
CUBEJS_API_SECRET=your_cubejs_api_secret
```

**3. 生成安全密钥**

```bash
python tools/deployment/generate_keys.py
```

**4. 启动所有服务**

```bash
docker-compose up -d
```

**5. 查看服务状态**

```bash
docker-compose ps
```

**6. 查看日志**

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

**7. 停止服务**

```bash
docker-compose down
```

**8. 清理数据**

```bash
docker-compose down -v  # 删除所有数据卷
```

#### 方式 2：本地开发（手动启动）

**1. 启动基础设施服务**

```bash
# 启动 PostgreSQL, MinIO, ChromaDB, Qdrant, Cube.js
docker-compose up -d db storage vector_db qdrant cube
```

**2. 启动后端服务**

```bash
cd apps/backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../../config/.env.example .env
# 编辑 .env 文件

# 初始化数据库
alembic upgrade head

# 启动服务
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**3. 启动前端服务**

```bash
cd apps/frontend

# 安装依赖
npm install

# 配置环境变量
cp ../../.env .env.local
# 编辑 .env.local 文件

# 启动开发服务器
npm run dev
```

**4. 启动 Agent 服务（可选）**

```bash
cd agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动 Agent 服务（根据需要）
python -m agent.core.agent
```

### 配置说明

#### 后端配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|-----------|--------|------|
| 应用环境 | `ENVIRONMENT` | `development` | 环境：development, staging, production |
| 调试模式 | `DEBUG` | `true` | 是否启用调试模式 |
| 主机地址 | `HOST` | `0.0.0.0` | 服务监听地址 |
| 端口 | `PORT` | `8000` | 服务监听端口 |
| 数据库 URL | `DATABASE_URL` | - | 异步数据库连接字符串 |
| 同步数据库 URL | `DATABASE_SYNC_URL` | - | 同步数据库连接字符串 |
| MinIO 端点 | `MINIO_ENDPOINT` | `localhost:9000` | MinIO 服务地址 |
| MinIO 访问密钥 | `MINIO_ACCESS_KEY` | - | MinIO 访问密钥 |
| MinIO 密钥 | `MINIO_SECRET_KEY` | - | MinIO 秘密密钥 |
| ChromaDB 主机 | `CHROMA_HOST` | `localhost` | ChromaDB 服务地址 |
| ChromaDB 端口 | `CHROMA_PORT` | `8001` | ChromaDB 服务端口 |
| Qdrant 主机 | `QDRANT_HOST` | `qdrant` | Qdrant 服务地址 |
| Qdrant 端口 | `QDRANT_PORT` | `6333` | Qdrant 服务端口 |
| JWT 密钥 | `SECRET_KEY` | - | JWT Token 签名密钥 |
| JWT 算法 | `ALGORITHM` | `HS256` | JWT 签名算法 |
| Token 过期时间 | `ACCESS_TOKEN_EXPIRE_MINUTES` | `43200` | Token 过期时间（分钟） |
| CORS 源 | `CORS_ORIGINS` | `[]` | 允许的跨域源 |
| 日志级别 | `LOG_LEVEL` | `INFO` | 日志级别：DEBUG, INFO, WARNING, ERROR |
| Sentry DSN | `SENTRY_DSN` | - | Sentry 错误追踪 DSN |
| Redis URL | `REDIS_URL` | `redis://localhost:6379` | Redis 连接字符串 |
| 缓存类型 | `CACHE_TYPE` | `memory` | 缓存类型：memory, redis |
| SOTA Agent | `USE_SOTA_AGENT` | `false` | 是否启用 SOTA Agent |
| Cube.js URL | `CUBE_API_URL` | `http://cube:4000` | Cube.js API 地址 |

#### 前端配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|-----------|--------|------|
| API 地址 | `NEXT_PUBLIC_API_URL` | `http://localhost:8004` | 后端 API 地址 |
| MinIO 端点 | `NEXT_PUBLIC_MINIO_ENDPOINT` | `http://localhost:9000` | MinIO 服务地址 |
| MinIO 存储桶 | `NEXT_PUBLIC_MINIO_BUCKET` | `dataagent-files` | MinIO 存储桶名称 |
| Sentry DSN | `NEXT_PUBLIC_SENTRY_DSN` | - | Sentry 错误追踪 DSN |

#### Cube.js 配置

Cube.js 配置通过 `cube_schema/` 目录中的 YAML 文件定义。每个文件定义一个 Cube（语义层），包含：

1. **Measures（度量）**：可聚合的数值字段
   - `count`：计数
   - `sum`：求和
   - `avg`：平均值
   - `min/max`：最小值/最大值

2. **Dimensions（维度）**：用于分组和过滤的字段
   - `time`：时间维度
   - `string`：字符串维度
   - `number`：数值维度
   - `boolean`：布尔维度

3. **Pre-aggregations（预聚合）**：性能优化配置
   - 定义预聚合规则，减少实时查询负担

---

## 测试与 CI/CD

### 自动化测试说明

#### 后端测试

**测试框架：** Pytest

**配置文件：** `apps/backend/pytest.ini`

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=src
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

**运行测试：**

```bash
cd apps/backend

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_query.py

# 运行特定测试函数
pytest tests/test_query.py::test_create_query

# 运行并显示覆盖率
pytest --cov=src --cov-report=html

# 跳过慢速测试
pytest -m "not slow"

# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration
```

**测试类型：**

- **单元测试**：测试单个函数或类
- **集成测试**：测试多个组件的交互
- **端到端测试**：测试完整的用户流程

#### 前端测试

**单元测试：** Jest + React Testing Library

**配置文件：** `apps/frontend/jest.config.js`

**运行测试：**

```bash
cd apps/frontend

# 运行所有测试
npm test

# 运行测试并监听文件变化
npm run test:watch

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行测试（CI 环境）
npm run test:ci
```

**E2E 测试：** Playwright

**配置文件：** `apps/frontend/playwright.config.ts`

**运行测试：**

```bash
cd apps/frontend

# 运行所有 E2E 测试
npm run test:e2e

# 运行 E2E 测试并显示 UI
npm run test:e2e:ui

# 运行特定测试文件
npx playwright test chat.spec.ts
```

### 持续集成配置

#### Docker 配置

项目使用 Docker 和 Docker Compose 进行容器化部署。

**Backend Dockerfile：** `apps/backend/Dockerfile`

**Frontend Dockerfile：** `apps/frontend/Dockerfile`

**Docker Compose 配置：** `docker-compose.yml`

主要服务：
- `frontend`：Next.js 前端应用
- `backend`：FastAPI 后端应用
- `db`：PostgreSQL 数据库
- `storage`：MinIO 对象存储
- `vector_db`：ChromaDB 向量数据库
- `qdrant`：Qdrant 向量数据库
- `cube`：Cube.js 语义层
- `mcp_echarts`：MCP ECharts 服务

**部署命令：**

```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart backend
```

#### 数据库迁移

使用 Alembic 进行数据库版本管理。

**创建迁移：**

```bash
cd apps/backend

# 生成迁移脚本
alembic revision --autogenerate -m "描述变更"

# 查看迁移历史
alembic history

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

#### 监控和日志

**Sentry 错误追踪：**

项目集成了 Sentry 进行错误监控和性能追踪。

**配置：**

```bash
# 后端 Sentry 配置
SENTRY_DSN=your_sentry_dsn
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=0.1

# 前端 Sentry 配置
NEXT_PUBLIC_SENTRY_DSN=your_sentry_dsn
NEXT_PUBLIC_SENTRY_ENVIRONMENT=development
NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=0.1
```

**结构化日志：**

使用 `structlog` 进行结构化日志记录。

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("User logged in", user_id=123, tenant_id="tenant_456")
logger.error("Query failed", error="SQL syntax error", query="SELECT * FROM")
```

---

## 常见问题与注意事项

### 1. 安装和配置问题

#### Q1: Docker Compose 启动失败？

**A:** 检查以下几点：

1. 确保 Docker 和 Docker Compose 已正确安装
2. 检查端口是否被占用（8000, 3000, 5432, 9000, 6333）
3. 检查 `.env` 文件是否存在且配置正确
4. 查看详细日志：`docker-compose logs -f`

#### Q2: 后端服务无法连接数据库？

**A:** 检查数据库连接配置：

1. 确保 `DATABASE_URL` 格式正确
2. 检查数据库服务是否正常运行：`docker-compose ps db`
3. 确认数据库端口可访问：`telnet localhost 5432`
4. 检查数据库用户名和密码是否正确

#### Q3: 前端无法连接后端 API？

**A:** 检查 CORS 配置：

1. 确保 `NEXT_PUBLIC_API_URL` 指向后端服务地址
2. 检查后端 `CORS_ORIGINS` 配置是否包含前端地址
3. 确认后端服务正常运行：`docker-compose ps backend`

### 2. 运行时问题

#### Q4: 查询超时？

**A:** 可能的原因和解决方案：

1. **查询过于复杂**：简化查询条件或减少返回结果
2. **数据库性能**：检查数据库索引是否优化
3. **网络延迟**：检查网络连接是否稳定
4. **LLM 响应慢**：更换更快的 LLM 模型

```python
# 增加超时时间
QUERY_TIMEOUT = 300  # 5 分钟
```

#### Q5: SQL 生成错误？

**A:** 检查以下几点：

1. 确认数据源 schema 是否正确加载
2. 检查业务规则和词汇表是否完整
3. 查看错误日志和 SQL 错误记忆
4. 考虑使用少样本 RAG 提供更多示例

#### Q6: 文档上传失败？

**A:** 常见原因：

1. **文件大小超限**：检查文件大小限制配置
2. **格式不支持**：确保文件格式为支持的类型（PDF, DOCX 等）
3. **MinIO 连接失败**：检查 MinIO 服务状态和配置
4. **处理超时**：增加文档处理超时时间

### 3. 性能优化

#### Q7: 如何提高查询性能？

**A:** 优化建议：

1. **启用查询缓存**：设置 `ENABLE_CACHE=true`
2. **使用 Redis**：配置 Redis 作为分布式缓存
3. **启用预聚合**：在 Cube.js 中配置预聚合规则
4. **数据库优化**：添加适当的索引
5. **减少返回数据**：限制返回结果数量

#### Q8: 如何降低 LLM 调用成本？

**A:** 成本优化建议：

1. **选择合适的模型**：根据任务复杂度选择不同模型
2. **使用缓存**：避免重复调用 LLM
3. **Prompt 优化**：精简 Prompt 内容
4. **流式响应**：减少 token 使用量
5. **备选提供商**：配置多个 LLM 提供商进行负载均衡

### 4. 安全和隐私

#### Q9: 如何保护敏感数据？

**A:** 安全措施：

1. **数据加密**：连接字符串和敏感数据自动加密存储
2. **租户隔离**：强制租户级别的数据隔离
3. **API 认证**：使用 JWT Token 进行身份认证
4. **访问控制**：实现基于角色的访问控制 (RBAC)
5. **日志脱敏**：日志中不记录敏感信息

#### Q10: 如何配置生产环境？

**A:** 生产环境配置：

1. **使用强密钥**：所有密钥使用足够长度的随机字符串
2. **禁用调试模式**：设置 `DEBUG=false`
3. **启用 HTTPS**：配置 SSL/TLS 证书
4. **限制 CORS**：只允许受信任的域名访问
5. **定期备份**：配置数据库和文件备份
6. **监控告警**：配置 Sentry 和其他监控工具

### 5. 开发和调试

#### Q11: 如何启用详细日志？

**A:** 配置日志级别：

```bash
# 设置日志级别为 DEBUG
LOG_LEVEL=DEBUG

# 或在代码中设置
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

#### Q12: 如何调试 Agent？

**A:** 调试技巧：

1. **启用详细日志**：设置 `DEBUG=true`
2. **查看 Agent 日志**：查看 `agent_logs` 表中的详细记录
3. **单步调试**：使用 IDE 的调试功能
4. **打印中间结果**：在关键节点添加日志输出

```python
logger.debug("Agent step: %s", step_name, extra={
    "input": input_data,
    "output": output_data
})
```

### 6. 故障排除

#### Q13: 常见错误代码

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `HTTP_400` | 请求参数错误 | 检查请求参数格式和内容 |
| `HTTP_401` | 未授权 | 检查 JWT Token 是否有效 |
| `HTTP_403` | 禁止访问 | 检查用户权限和租户配置 |
| `HTTP_404` | 资源不存在 | 确认资源 ID 是否正确 |
| `HTTP_429` | 请求频率超限 | 减少请求频率或联系管理员 |
| `HTTP_500` | 服务器内部错误 | 查看服务器日志，联系技术支持 |
| `AGENT_UNAVAILABLE` | Agent 不可用 | 检查 Agent 服务状态 |
| `TIMEOUT_ERROR` | 查询超时 | 简化查询或增加超时时间 |

#### Q14: 如何查看日志？

**A:** 日志查看方式：

```bash
# Docker 日志
docker-compose logs -f backend
docker-compose logs -f frontend

# Agent 日志（文件）
tail -f infrastructure/storage/logs/agent.log

# 应用日志（数据库）
# 登录数据库查询 agent_logs 表
psql postgresql://postgres:password@localhost:5432/dataagent

# 查询 Agent 日志
SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT 100;
```

### 7. 升级和维护

#### Q15: 如何升级到新版本？

**A:** 升级步骤：

1. **备份数据**：备份数据库和重要文件
2. **拉取最新代码**：`git pull origin master`
3. **更新依赖**：
   ```bash
   # 后端
   pip install -r requirements.txt --upgrade

   # 前端
   npm update
   ```
4. **执行迁移**：`alembic upgrade head`
5. **重启服务**：`docker-compose restart`
6. **验证功能**：测试核心功能是否正常

#### Q16: 如何回滚到旧版本？

**A:** 回滚步骤：

1. **停止服务**：`docker-compose down`
2. **切换到旧版本**：`git checkout <commit-hash>`
3. **恢复数据库**：从备份恢复数据库
4. **启动服务**：`docker-compose up -d`
5. **验证功能**：测试核心功能是否正常

---

## 附录

### A. 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Next.js 官方文档](https://nextjs.org/docs)
- [LangChain 官方文档](https://python.langchain.com/docs)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [Cube.js 官方文档](https://cube.dev/docs)
- [ChromaDB 官方文档](https://docs.trychroma.com/)
- [Qdrant 官方文档](https://qdrant.tech/documentation/)
- [MinIO 官方文档](https://min.io/docs/minio/linux/operations/)

### B. 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

### C. 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

### D. 联系方式

- 项目主页：[https://github.com/your-org/insight-agent](https://github.com/your-org/insight-agent)
- 问题反馈：[Issues](https://github.com/your-org/insight-agent/issues)
- 邮件：support@insight-agent.com

---

**文档版本：** 1.0.0

**最后更新：** 2024-02-21
