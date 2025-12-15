## ADDED Requirements

### Requirement: 批量删除数据库数据源
系统应支持在数据源管理页对多个数据库数据源进行批量删除操作，复用现有后端 `/data-sources/bulk-delete` 接口。

#### Scenario: 确认并限制数量
- **WHEN** 用户在数据源列表中选择多个数据库数据源并点击批量删除
- **THEN** 系统显示确认提示，告知操作不可恢复
- **AND** 当选择数量超过 50 时，前端拒绝提交并提示数量限制

#### Scenario: 批量删除成功与刷新
- **WHEN** 用户确认删除且选择数量不超过 50
- **THEN** 前端调用 `/data-sources/bulk-delete`，参数 `item_type=database`
- **AND** 删除完成后刷新数据源概览和列表，并清空当前选中项

#### Scenario: 部分失败反馈
- **WHEN** 后端返回部分删除失败
- **THEN** 前端提示失败项信息（数量或摘要），仍刷新列表并清空选中项

