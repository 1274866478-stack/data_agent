## Project Brief: “Data Agent” (V4 - SaaS MVP)


**版本：4.0**
**日期：2025 年 11 月 15 日**
**作者：BMad Master Orchestrator**

---

### 1. 执行摘要 (Executive Summary)


Data Agent V4 是一个**多租户 (Multi-Tenant) SaaS 平台**，旨在使企业能够将其孤立的数据源（数据库和文档） 转变为一个可交互、可解释的智能洞察引擎。

V4 的核心是**个性化和安全性**：它允许**“不同的用户”**（即租户）安全地“**导入自己的数据库和知识库**”，并通过一个统一的自然语言聊天界面 查询**自己**的数据。

**V4 MVP (最小可行产品)** 的目标是**在本地运行** 一个**云就绪 (Cloud-Ready)** 的架构（使用 Docker Compose），以验证“用户自带数据 (BYO-Data)” 这一核心的 SaaS 循环。

---

### 2. 问题陈述 (Problem Statement)


* **数据孤岛 (SaaS 层面)：** 不同的公司和团队无法利用他们**自己**的数据进行 AI 查询，因为缺乏一个安全的、易于集成的平台来“**导入自己的数据库和知识库**”。
* **技术壁垒 (SaaS 层面)：** 对于没有专业 DevOps 团队的公司来说，部署和维护一个 AI 代理系统过于复杂。他们需要一个**“零配置”**的 SaaS 解决方案。
* **信任与安全 (SaaS 层面)：** 用户不敢上传他们的专有数据（如 `product_sales` 表），因为他们担心数据会与其他租户混合或泄露。
* **黑盒信任危机：** （继承自 V3）用户不信任 AI 的复杂分析结果，因为他们不知道 AI **为什么**会选择特定的数据源或表格。

---

### 3. 拟议解决方案 (Proposed Solution)


Data Agent V4 将是一个**云原生的多租户 SaaS 平台**。MVP 将专注于以下核心解决方案：

1.  **多租户认证 (Multi-Tenant Authentication)：**
    * **放弃** V3 的单一 API 密钥 方案。
    * V4 MVP 必须实施**完整的用户认证**（例如 Auth0, Clerk, Firebase Auth），以区分“不同的用户”（租户）。
2.  **自助式数据导入工作流 (Self-Serve Data Import Workflow)：**
    * V4 MVP 必须提供一个 UI 界面，允许登录的用户安全地“**导入自己的数据库和知识库**”。
    * **数据库导入：** 提供一个表单，让用户输入他们**自己的数据库连接字符串**（例如，外部 PostgreSQL）。
    * **知识库导入：** 提供一个**文件上传器**（例如，上传 PDF/Word 文档）。
3.  **租户隔离的 Agentic 核心 (Tenant-Context Agent Core)：**
    * 保留 V3 的核心 AI 逻辑（RAG-SQL、自我修正、XAI，解释其*为什么*选择了特定的数据源。]）。
    * **关键升级：** Agentic Core 必须在**特定租户的上下文**中运行，确保它**只**查询该用户导入的数据库 和向量存储。

---

#### 4. 目标用户 (Target Users)


* **核心用户 (Primary Users)：** **中小型企业 (SMBs) 或企业部门**，他们拥有自己的数据库（如 `product_sales`）和文档，但缺乏资源来构建自己的 AI 代理。
* **用户角色：** 业务分析师、产品经理、销售团队，他们需要一个**“零配置”**的工具来查询他们**团队自己的数据**。

---

#### 5. 目标与成功指标 (Goals & Success Metrics)


* **V4 业务目标 (V4 Goal):** 验证 **“BYO-Data”（自带数据）** SaaS 循环在技术上是可行且有价值的。
    * **KPI:** 新用户在注册后，成功连接一个**外部数据库** 并成功上传**一份文档** 的比例达到 80%。
* **V3 用户目标 (Kept from V3):** 建立“可解释的”信任。
    * **KPI:** **XAI 覆盖率**：100% 的融合答案都附带“推理路径” (Explainability Log)，解释其*为什么*选择了特定的数据源。]。

---

#### 6. MVP 范围 (MVP Scope)


该 MVP 专注于交付一个可运行的、端到端的 SaaS 体验，验证“用户自助导入数据” 的核心循环。

* **核心功能 (Must Have):**
    * **V4 认证：** 必须实现**多租户用户认证**（例如，使用 Clerk 或 Auth0）。
    * **V4 数据导入 UI：** 必须提供一个**数据源连接页面**，允许用户：
        * 1. 输入外部 PostgreSQL 数据库的连接字符串。
        * 2. 上传 PDF/Word 文档（例如，到本地 MinIO 或云 S3）。
    * **V4 租户隔离后端：**
        * **API：** 必须**重构** `/api/v1/query`，使其在**经过身份验证的租户上下文**中运行。
        * **数据隔离：** 必须实现**基础的多租户数据隔离**（例如，ChromaDB 中按 `tenant_id` 过滤元数据，SQL 查询中按 `tenant_id` 注入 `WHERE` 子句）。
    * **V3 AI 核心 (保留)：**
        * 必须保留 Agentic Core、RAG-SQL 和 XAI 融合 逻辑。
    * **V3 UI (保留)：**
        * 保留 "the curator." `style.md` 风格的聊天界面。

* **V4 范围外 (Out of Scope - 暂不考虑):**
    * **(V3 降级)** V3 多模态 RAG（图表/表格查询） 文档中**图表和表格** 内容的查询。]。
    * **(V3 降级)** V3 主动洞察智能体 能够（通过模拟触发）**主动**向用户推送关于 `product_sales` 指标异常的分析警报。]。
    * **(V1 保留)** 完整的 AI 功能（Embedding, Reranker, OCR）仍使用占位符。
    * **(V4 新增)** 复杂的租户管理、RBAC（角色权限控制）、计费系统。

---

#### 7. 技术考量 (Technical Considerations)


* **(V4 升级)** **部署 (MVP)：** 必须从“本地 Windows 运行” 升级为 **Docker Compose**。
* **(V4 升级)** **部署 (Production)：** 目标是部署到**云服务器**（例如 AWS ECS/Lambda, Vercel）。
* **(V4 升级)** **结构化数据库：** 必须从 SQLite 升级为 **PostgreSQL**（通过 Docker 在本地 MVP 中运行）。
* **(V4 升级)** **非结构化存储：** 必须从“本地文件夹” 升级为**对象存储**（例如，在本地 MVP 中使用 **MinIO**）。
* **(V4 升级)** **认证：** 必须从“API 密钥” 升级为**托管认证服务**（例如 Clerk, Auth0, Firebase Auth）。
* **(保留)** **UI：** Next.js, "the curator." `style.md`。
* **(保留)** **AI 核心：** LangChain, DeepSeek API。

---

#### 8. 风险与开放性问题 (Risks & Open Questions)

* **风险 1 (SaaS 安全)：** **数据隔离失败**。如果租户 A 的 Agent 意外查询到了租户 B 的数据，将导致灾难性的安全漏洞。
* **风险 2 (集成)：** **数据库内省 (Introspection)** 失败。如果用户的数据库 Schema 过于庞大或复杂，我们的 Agent 可能无法正确生成 `schema_annotations`。
* **风险 3 (成本)：** DeepSeek API 和云基础设施的成本可能会随着用户查询量的增加而失控。
* **开放性问题：** 我们将如何处理用户数据库连接的**凭证加密和安全存储**？

---

#### 9. 后续步骤 (Next Steps)

* **(PM Handoff)** 将这份 **Project Brief V4** 移交给 **产品经理 (PM) - John**，以创建一份全新的 **PRD V4**，其中必须包含用于**认证**和**数据导入工作流** 的新 Epic 和 Story。