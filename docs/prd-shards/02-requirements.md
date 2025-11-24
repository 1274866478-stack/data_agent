# 第2部分：需求 (Requirements)

## 功能性需求 (Functional Requirements)
* **FR1 (V4):** 系统必须是**多租户**的。用户**必须**通过**托管认证服务**（例如 Clerk, Auth0 升级为**托管认证服务**（例如 Clerk, Auth0, Firebase Auth）。]）进行登录。
* **FR2 (V4):** 登录后的用户必须能访问一个**数据源连接页面**。
* **FR3 (V4):** 用户必须能通过该 UI 提交**外部 PostgreSQL 数据库的连接字符串**。
* **FR4 (V4):** 用户必须能通过该 UI **上传 PDF/Word 文档**。
* **FR5 (V4):** 所有 API（特别是 `/api/v1/query`）必须是**租户隔离**的。Agent **绝不能**查询到不属于当前登录用户的数据。
* **FR6 (V3 保留):** 系统必须保留 **Agentic RAG-SQL** 和**自我修正** 逻辑。
* **FR7 (V3 保留):** 答案必须包含**来源追溯**。
* **FR8 (V3 保留):** 答案必须包含**可解释性 (XAI) 推理路径**。]。

## 非功能性需求 (Non-Functional Requirements)
* **NFR1 (V4):** **部署 (MVP)：** 整个系统（前后端、数据库）**必须**能通过 **Docker Compose** 在本地一键启动 升级为 **Docker Compose**。]。
    * **环境变量 (更新):** Docker Compose 配置必须将 `ZHIPUAI_API_KEY`（而不是 `DEEPSEEK_API_KEY`）传递给后端服务。
* **NFR2 (V4):** **部署 (Production)：** 架构必须**为云服务器部署做好准备**（例如，使用 12-Factor App 原则）。
* **NFR3 (V4):** **结构化数据库：** 必须使用 **PostgreSQL** 升级为 **PostgreSQL**（通过 Docker 在本地 MVP 中运行）。]（本地 MVP 中通过 Docker 运行）。
* **NFR4 (V4):** **非结构化存储：** 必须使用**对象存储**（本地 MVP 中使用 **MinIO** 升级为**对象存储**（例如，在本地 MVP 中使用 **MinIO**）。]）。
* **NFR5 (V4 更新):** **LLM 依赖：** 所有语言理解和生成任务均通过 **智谱 AI (Zhipu) API (GLM)** 完成（例如 `glm-4`）。
* **NFR6 (V3 保留):** **UI 规范：** 继续使用 "the curator." `style.md` 规范。

---
*来源文档：`doc/prd.md`*