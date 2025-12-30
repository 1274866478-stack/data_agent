# [SERVICES] 前端服务层

## [MODULE]
**模块名称**: 前端服务层
**职责**: 高级业务服务、缓存服务、搜索服务
**类型**: 服务类模块

## [BOUNDARY]
**输入**:
- 用户操作
- 数据变更

**输出**:
- 处理结果
- 缓存更新

## [PROTOCOL]
1. 封装复杂业务逻辑
2. 提供缓存机制
3. 统一错误处理
4. 可复用服务

## [STRUCTURE]
```
services/
├── fileUploadService.ts    # 文件上传服务
├── messageCacheService.ts  # 消息缓存服务
├── searchService.ts        # 搜索服务
└── __tests__/              # 服务测试
```

## [LINK]
**上游依赖**:
- [../lib/api-client.ts](../lib/api-client.ts) - API调用

**下游依赖**:
- localStorage/IndexedDB - 本地存储

**调用方**:
- [../components/](../components/_folder.md) - 组件使用服务
- [../store/](../store/_folder.md) - 状态管理调用服务

## [STATE]
- 缓存数据
- 上传队列

## [THREAD-SAFE]
N/A (前端概念)

## [SIDE-EFFECTS]
- localStorage读写
- IndexedDB操作
- API调用
