# 第4部分：技术假设 (Technical Assumptions)

## 基础架构
* **Repository Structure (代码仓库结构):** **Monorepo (单一仓库)** (`frontend`, `backend`, `docs`)
* **Service Architecture (服务架构):** **Monolith Backend Service (单体后端服务)** (FastAPI)
* **Testing Requirements (测试要求):** **Unit + Integration (单元 + 集成测试)**

## 技术栈详细说明
* **后端：** Python 3.10+, FastAPI, LangChain
* **后端 SDK (V4 更新):** 必须安装 `zhipuai`（`pip install zhipuai`）
* **前端：** Next.js 14+, shadcn/ui, Tailwind CSS, Zustand
* **数据库 (V4 升级):** **PostgreSQL** 升级为 **PostgreSQL**（通过 Docker 在本地 MVP 中运行）。], **ChromaDB**
* **对象存储 (V4 升级):** **MinIO** 升级为**对象存储**（例如，在本地 MVP 中使用 **MinIO**）。]
* **LLM API (V4 更新):** **Zhipu API** (GLM-4)
* **认证 (V4 升级):** **Clerk** 或 **Auth0** 升级为**托管认证服务**（例如 Clerk, Auth0, Firebase Auth）。]
* **部署 (MVP) (V4 升级):** **Docker Compose** 升级为 **Docker Compose**。]

---
*来源文档：`doc/prd.md`*