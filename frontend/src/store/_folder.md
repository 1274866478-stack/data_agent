# [STORE] 状态管理

## [MODULE]
**模块名称**: Zustand状态管理
**职责**: 全局状态、状态持久化、状态订阅
**类型**: Zustand Stores

## [BOUNDARY]
**输入**:
- Action调用
- State更新

**输出**:
- 当前状态
- 状态选择器

## [PROTOCOL]
1. 使用Zustand轻量状态管理
2. 模块化Store设计
3. 支持持久化
4. 细粒度订阅

## [STRUCTURE]
```
store/
├── index.ts                # Store聚合导出
├── appStore.ts             # 应用全局状态
├── authStore.ts            # 认证状态
├── chatStore.ts            # 聊天状态
├── dashboardStore.ts       # 仪表板状态
├── dataSourceStore.ts      # 数据源状态
├── documentStore.ts        # 文档状态
├── tenantStore.ts          # 租户状态
└── __tests__/              # Store测试
```

## [LINK]
**上游依赖**:
- [../lib/api-client.ts](../lib/api-client.ts) - API调用

**下游依赖**:
- Zustand - 状态管理库
- zustand/persist - 持久化中间件

**调用方**:
- [../components/](../components/_folder.md) - 组件订阅状态
- [../app/](../app/_folder.md) - 页面使用状态

## [STATE]
- 各Store的状态对象
- 持久化存储 (localStorage)

## [THREAD-SAFE]
N/A (前端概念)

## [SIDE-EFFECTS**
- localStorage读写
- API请求触发
