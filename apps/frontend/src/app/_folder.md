# [APP] Next.js App Router 页面

## [MODULE]
**模块名称**: Next.js App Router 页面层
**职责**: 路由页面、布局配置、全局样式
**类型**: Next.js App Router

## [BOUNDARY]
**输入**:
- URL路由
- URL参数
- Cookie/Headers

**输出**:
- React组件树
- HTML响应
- 元数据

## [PROTOCOL]
1. 使用 Next.js 14 App Router 约定
2. 文件系统路由 (file-based routing)
3. 服务端组件优先 (RSC)
4. 布局嵌套 (layout.tsx)

## [STRUCTURE]
```
app/
├── layout.tsx              # 根布局 (认证提供者)
├── page.tsx                # 首页
├── globals.css             # 全局样式
├── (app)/                  # 应用页面组
│   └── dashboard/          # 仪表板等页面
├── (auth)/                 # 认证页面组
│   ├── login/
│   └── register/
└── dev/                    # 开发工具页面
```

## [LINK]
**上游依赖**:
- [../components/](../components/_folder.md) - UI组件
- [../store/](../store/_folder.md) - 状态管理
- [../lib/](../lib/_folder.md) - 工具函数

**下游依赖**:
- Next.js - 框架核心
- Clerk - 认证服务

**调用方**:
- 浏览器导航

## [STATE]
- 服务端: 无状态 (每次请求新实例)
- 客户端: React组件状态

## [THREAD-SAFE]
N/A (前端概念)

## [SIDE-EFFECTS]
- 导航跳转
- Cookie设置
- localStorage操作
