# [COMPONENTS] React组件库

## [MODULE]
**模块名称**: React组件库
**职责**: 可复用UI组件、复合组件、业务组件
**类型**: React FC (Functional Components)

## [BOUNDARY]
**输入**:
- Props (属性)
- Context (上下文)
- Store (状态)

**输出**:
- JSX/TSX元素
- 事件回调

## [PROTOCOL]
1. 函数式组件 + Hooks
2. TypeScript严格类型
3. Tailwind CSS样式
4. 组件组合模式

## [STRUCTURE]
```
components/
├── index.ts                # 组件导出索引
├── Logo.tsx                # Logo组件
├── auth/                   # 认证相关组件
│   ├── ClerkProvider.tsx
│   └── AuthContext.tsx
├── chat/                   # 聊天界面组件
├── common/                 # 通用组件
├── data-sources/           # 数据源组件
├── documents/              # 文档组件
├── forms/                  # 表单组件
├── layout/                 # 布局组件
├── tenant/                 # 租户组件
├── ui/                     # 基础UI组件
├── xai/                    # XAI可解释性组件
└── __tests__/              # 组件测试
```

## [LINK]
**上游依赖**:
- [../store/](../store/_folder.md) - 状态管理
- [../lib/](../lib/_folder.md) - 工具函数
- [../types/](../types/_folder.md) - 类型定义

**下游依赖**:
- React - 核心库
- Radix UI - 无障碍组件
- Lucide React - 图标库
- Tailwind CSS - 样式

**调用方**:
- [../app/](../app/_folder.md) - 页面使用组件
- components/内部嵌套

## [STATE]
- useState: 组件本地状态
- useContext: 上下文状态
- Zustand: 全局状态

## [THREAD-SAFE**
N/A (前端概念)

## [SIDE-EFFECTS]
- 事件处理
- API调用
- 状态更新
