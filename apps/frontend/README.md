# Data Agent V4 - Frontend

多租户 SaaS 数据智能平台的前端应用，基于 Next.js 14+ 构建。

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI 组件**: shadcn/ui + Radix UI
- **样式**: Tailwind CSS + The Curator 主题
- **状态管理**: Zustand
- **类型检查**: TypeScript
- **代码质量**: ESLint
- **图标**: Lucide React

## 功能特性

### ✅ 已实现功能

1. **基础架构**
   - Next.js 14+ App Router 配置
   - TypeScript 和 ESLint 配置
   - 路由保护中间件

2. **UI 组件系统**
   - shadcn/ui 组件库集成
   - The Curator 设计主题
   - 响应式布局
   - 暗色模式支持

3. **路由结构**
   - 认证路由：`/sign-in`, `/sign-up`
   - 应用路由：`/`, `/data-sources`
   - 路由保护和权限控制

4. **状态管理**
   - Zustand store 配置
   - 用户认证状态管理
   - 应用全局状态管理

5. **布局组件**
   - 主布局 (Layout)
   - 顶部导航栏 (Header)
   - 侧边栏 (Sidebar)

6. **UI 组件**
   - 加载状态组件
   - 错误消息组件
   - 表单组件

## 项目结构

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/            # 认证路由（公共）
│   │   │   ├── layout.tsx
│   │   │   ├── sign-in/
│   │   │   └── sign-up/
│   │   ├── (app)/             # 应用路由（受保护）
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── data-sources/
│   │   ├── layout.tsx         # 根布局
│   │   ├── page.tsx           # 首页
│   │   └── globals.css        # 全局样式
│   ├── components/            # 可复用组件
│   │   ├── layout/            # 布局组件
│   │   └── ui/                # UI 组件
│   ├── lib/                   # 工具库
│   │   ├── api.ts            # API 客户端
│   │   └── utils.ts          # 工具函数
│   └── store/                # Zustand 状态管理
├── public/                   # 静态资源
└── package.json
```

## 开发指南

### 环境要求

- Node.js 18+
- npm 或 yarn

### 快速开始

1. 安装依赖：
```bash
npm install
```

2. 配置环境变量：
```bash
cp .env.example .env.local
```

3. 启动开发服务器：
```bash
npm run dev
```

4. 访问应用：http://localhost:3000

### 可用脚本

- `npm run dev` - 启动开发服务器
- `npm run build` - 构建生产版本
- `npm run start` - 启动生产服务器
- `npm run lint` - 运行 ESLint 检查
- `npm run type-check` - 运行 TypeScript 类型检查

### 环境变量

```env
# API 配置
NEXT_PUBLIC_API_URL=http://localhost:8004/api/v1

# 应用配置
NEXT_PUBLIC_APP_NAME=Data Agent V4

# 环境
NODE_ENV=development
```

## 设计系统

### The Curator 主题

基于 The Curator 设计规范，采用以下设计原则：

- **主色调**: 纯黑色 (#000000)
- **辅助色**: 灰色 (#666666)
- **强调色**: 珊瑚红 (#FF6B6B)
- **背景色**: 纯白色 (#FFFFFF)
- **字体**: Inter 字体族
- **圆角**: 8px 标准圆角

### 组件库

使用 shadcn/ui 作为基础组件库，结合自定义主题和样式扩展。

## 开发规范

### 代码规范

- 使用 TypeScript 进行类型安全
- 遵循 ESLint 规则
- 组件使用 PascalCase 命名
- 文件名使用 camelCase 或 kebab-case

### Git 提交规范

- `feat:` 新功能
- `fix:` 修复问题
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

## 部署

### 生产构建

```bash
npm run build
npm start
```

### Docker 部署

```bash
docker build -t data-agent-v4-frontend .
docker run -p 3000:3000 data-agent-v4-frontend
```

## 状态

- **开发状态**: ✅ 完成
- **测试状态**: ⏳ 待添加
- **文档状态**: ✅ 完成
- **部署状态**: ⏳ 待配置

## 下一步计划

1. 添加单元测试
2. 集成真实后端 API
3. 完善错误处理
4. 添加性能监控
5. 实现可访问性优化

## 贡献

欢迎提交 Issue 和 Pull Request！

---

*最后更新: 2025-11-16*