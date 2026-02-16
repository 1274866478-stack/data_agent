# Frontend Module - Next.js前端应用

## [MODULE]
**模块名称**: Next.js 14前端应用模块
**职责**: 提供用户界面、状态管理和用户交互功能 - 现代化的React应用，多租户SaaS架构的用户界面层
**类型**: 前端应用模块

## [BOUNDARY]
**输入**:
- 用户操作（点击、输入、导航）
- API响应数据（JSON格式）
- JWT认证令牌（Clerk）
- WebSocket推送（实时更新，可选）

**输出**:
- HTTP请求（API调用）
- 用户界面渲染
- 用户事件响应
- 状态更新

## [PROTOCOL]
1. **TypeScript严格模式**: 所有代码必须使用严格的TypeScript类型检查
2. **React Hooks最佳实践**: 遵循React Hooks规则和最佳实践
3. **API完整URL**: 所有API调用必须使用完整URL（环境变量配置）
4. **租户参数传递**: 所有业务API必须传递tenant_id和user_id参数
5. **状态管理**: 使用Zustand进行全局状态管理
6. **组件化**: 使用原子设计原则，组件高度可复用
7. **响应式设计**: 移动优先的响应式设计策略
8. **错误边界**: 使用错误边界组件捕获处理错误

## [STRUCTURE]
```
frontend/
├── src/                     # 源代码目录
│   ├── app/                # Next.js 14 App Router
│   │   ├── page.tsx        # 应用首页
│   │   ├── layout.tsx      # 根布局
│   │   ├── globals.css     # 全局样式
│   │   ├── (app)/          # 应用页面组
│   │   ├── (auth)/         # 认证页面组
│   │   ├── dev/            # 开发页面
│   │   ├── dashboard/      # 仪表板页面
│   │   ├── data-sources/   # 数据源管理页面
│   │   ├── documents/      # 文档管理页面
│   │   └── chat/           # AI对话页面
│   ├── components/         # React组件库
│   │   ├── ui/            # 基础UI组件
│   │   ├── chat/          # 聊天界面组件
│   │   ├── common/        # 通用组件
│   │   ├── data-sources/  # 数据源组件
│   │   ├── documents/     # 文档组件
│   │   ├── forms/         # 表单组件
│   │   ├── layout/        # 布局组件
│   │   ├── tenant/        # 租户组件
│   │   ├── xai/           # XAI推理组件
│   │   └── ui/            # UI组件库
│   ├── lib/               # 工具函数
│   │   ├── api.ts         # API客户端
│   │   ├── api-client.ts  # HTTP客户端
│   │   ├── auth.ts        # 认证工具
│   │   └── utils.ts       # 通用工具
│   ├── services/          # 服务层
│   │   ├── api.ts         # API服务封装
│   │   └── auth.ts        # 认证服务
│   ├── store/             # 状态管理（Zustand）
│   │   ├── authStore.ts   # 认证状态
│   │   ├── chatStore.ts   # 聊天状态
│   │   ├── dataSourceStore.ts # 数据源状态
│   │   └── index.ts       # Store导出
│   ├── types/             # TypeScript类型定义
│   └── utils/             # 工具函数
├── public/                # 静态资源
│   ├── images/           # 图片资源
│   ├── icons/            # 图标资源
│   └── fonts/            # 字体资源
├── e2e/                   # 端到端测试
│   └── specs/            # 测试规格
├── package.json          # 项目依赖
├── tsconfig.json         # TypeScript配置
├── tailwind.config.js    # Tailwind配置
├── next.config.js        # Next.js配置
└── Dockerfile           # Docker镜像
```

## [LINK]
**上游依赖**:
- [../backend/](../backend/_folder.md) - FastAPI后端服务（API数据源）
- [../Agent/](../Agent/_folder.md) - LangGraph SQL智能代理（可选集成）
- Clerk - JWT认证服务
- 外部资源（图片、字体、图标）

**下游依赖**:
- [./src/app/](./src/app/_folder.md) - Next.js App Router页面
- [./src/components/](./src/components/_folder.md) - React组件库
- [./src/lib/](./src/lib/_folder.md) - 工具函数和API客户端
- [./src/services/](./src/services/_folder.md) - 服务层封装
- [./src/store/](./src/store/_folder.md) - Zustand状态管理
- [./src/types/](./src/types/_folder.md) - TypeScript类型定义

**调用方**:
- 浏览器（用户界面渲染）
- E2E测试套件（Playwright）
- Storybook（组件开发和测试）

## [STATE]
- 用户认证状态（Zustand stores）
- 应用全局状态
- 路由状态（Next.js App Router）
- 浏览器状态（LocalStorage, SessionStorage）
- React组件状态（useState, useReducer）

## [THREAD-SAFE]
不适用（前端单线程JavaScript）

## [SIDE-EFFECTS]
- HTTP请求（API调用）
- 浏览器存储操作（LocalStorage, SessionStorage, Cookies）
- 路由导航（Next.js Router）
- 事件监听器注册和注销
- 浏览器通知（可选）
- 文件下载和上传
