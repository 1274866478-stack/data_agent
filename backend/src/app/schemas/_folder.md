# [SCHEMAS] 数据验证模式

## [MODULE]
**模块名称**: 数据验证模式
**职责**: 请求/响应数据验证、类型定义
**类型**: Pydantic Models

## [BOUNDARY]
**输入**:
- 原始请求数据 (dict/json)
- 查询参数

**输出**:
- 验证后的模型实例
- 序列化的响应数据

## [PROTOCOL]
1. 使用 Pydantic V2 进行数据验证
2. 定义所有API的请求/响应模型
3. 自动类型转换和验证
4. 详细的错误提示

## [STRUCTURE]
```
schemas/
├── __init__.py
└── query.py                # 查询相关模式
```

## [LINK]
**上游依赖**:
- [../api/](../api/_folder.md) - API端点使用schemas验证请求

**下游依赖**:
- pydantic - 核心验证库

**调用方**:
- API端点 (endpoints/*.py)

## [STATE]
无状态 - 纯数据验证

## [THREAD-SAFE]
是 - 不可变模型实例

## [SIDE-EFFECTS]
无 (纯验证逻辑)
