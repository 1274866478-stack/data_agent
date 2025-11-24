# 第5部分：史诗列表 (Epic List)

*(YOLO 模式：此列表与上一版本 保持一致，但实施细节将引用 Zhipu 而不是 DeepSeek。)*

## 史诗概述

### Epic 1 (V4): 基础架构与 SaaS 环境搭建 (Docker Compose)
* **目标 (Goal):** 建立可**本地运行** 的 **Docker Compose** 升级为 **Docker Compose**。] 环境，包含 Next.js、FastAPI、**PostgreSQL** 升级为 **PostgreSQL**（通过 Docker 在本地 MVP 中运行）。] 和 **MinIO** 升级为**对象存储**（例如，在本地 MVP 中使用 **MinIO**）。]。

### Epic 2 (V4): 多租户认证与数据源管理
* **目标 (Goal):** 集成**托管认证服务**（如 Clerk） 升级为**托管认证服务**（例如 Clerk, Auth0, Firebase Auth）。]，并构建允许用户**导入数据库连接字符串** 和**上传文档** 到 MinIO 升级为**对象存储**（例如，在本地 MVP 中使用 **MinIO**）。] 的 UI 界面。

### Epic 3 (V4): 租户隔离的 Agentic 核心 (Backend)
* **目标 (Goal):** **重构** Epic V3 的 AI 逻辑。确保 Agentic Core（RAG-SQL 和**自我修正** 逻辑。]、XAI。]）在执行时，严格使用**当前登录租户**的数据库连接 和 ChromaDB 向量，并使用 **Zhipu GLM API** 进行 AI 调用。

### Epic 4 (V4): V3 UI 集成与交付
* **目标 (Goal):** 保留 "the curator." 风格 规范。] 的聊天界面, "the curator." `style.md`。]。将聊天界面连接到 V4 的**租户隔离** API 端点，并确保 XAI。] 和溯源。] 功能在新架构下正常工作。

---
*来源文档：`doc/prd.md`*