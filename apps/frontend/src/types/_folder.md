# [TYPES] TypeScript类型定义

## [MODULE]
**模块名称**: TypeScript类型定义
**职责**: 全局类型、接口定义、类型导出
**类型**: TypeScript类型文件

## [BOUNDARY]
**输入**:
- 无 (纯类型定义)

**输出**:
- 类型/接口/枚举

## [PROTOCOL]
1. 集中管理项目类型
2. 严格类型检查
3. 类型复用和继承
4. 与后端API类型对齐

## [STRUCTURE]
```
types/
└── chat.ts                 # 聊天相关类型
    # 其他类型文件待补充
```

## [LINK]
**上游依赖**:
- 无 (类型定义层)

**下游依赖**:
- 无 (被其他模块导入)

**调用方**:
- [../lib/](../lib/_folder.md) - API类型使用
- [../store/](../store/_folder.md) - 状态类型使用
- [../components/](../components/_folder.md) - 组件Props类型

## [STATE]
无 (编译时类型)

## [THREAD-SAFE]
N/A (类型在编译时处理)

## [SIDE-EFFECTS]
无 (纯类型定义)
