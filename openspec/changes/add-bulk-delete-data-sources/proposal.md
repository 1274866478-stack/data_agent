# 变更：为数据源管理增加批量删除能力

## Why
- 目前前端仅支持单个数据源删除，无法多选批量删除，用户需要逐个操作，效率低且易出错。
- 后端已有 `/data-sources/bulk-delete` 接口（数据库类型），但前端没有入口，功能未落地。

## What Changes
- 前端数据源管理页（数据库连接列表）新增多选与批量删除入口，客户端限制最大 50 条，呈现删除确认与部分失败提示。
- 前端调用现有 `/data-sources/bulk-delete` 接口（`item_type=database`），删除后刷新概览与列表，清空选择。
- 保留文档删除现状，不改动文档批量删除逻辑。

## Impact
- 受影响前端：`frontend/src/app/(app)/data-sources/page.tsx`、`frontend/src/components/data-sources/DataSourceList.tsx`、`frontend/src/components/data-sources/BulkOperations.tsx`、`frontend/src/store/dashboardStore.ts`。
- 受影响后端：无需接口新增，复用现有 `/data-sources/bulk-delete`。
- 规格：新增数据源管理批量删除要求。

