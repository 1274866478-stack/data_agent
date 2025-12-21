# 任务清单

## 阶段1：实现动态文件发现函数

- [x] 在`backend/src/app/services/agent/path_extractor.py`中添加`get_latest_excel_file()`函数
  - [x] 实现递归搜索`/app/uploads/`目录下的所有`.xlsx`和`.xls`文件
  - [x] 实现按修改时间排序，选择最新文件
  - [x] 实现严格的错误处理：如果找不到文件，抛出`FileNotFoundError`
  - [x] 添加日志记录，记录找到的文件路径

## 阶段2：集成到文件工具

- [x] 修改`backend/src/app/services/agent/tools.py`中的`inspect_file_func`
  - [x] 在路径解析失败时，调用`get_latest_excel_file()`作为后备方案
  - [x] 确保错误信息明确，返回`SYSTEM ERROR`格式的错误消息
  - [x] 添加日志记录，记录使用的文件路径

- [x] 修改`backend/src/app/services/agent/tools.py`中的`analyze_dataframe_func`
  - [x] 在路径解析失败时，调用`get_latest_excel_file()`作为后备方案
  - [x] 确保错误信息明确，返回`SYSTEM ERROR`格式的错误消息
  - [x] 添加日志记录，记录使用的文件路径

## 阶段3：测试和验证

- [ ] 测试场景1：上传Excel文件，文件名被重命名为UUID
  - [ ] 验证AI能够找到并读取文件
  - [ ] 验证不会生成假数据

- [ ] 测试场景2：没有上传任何文件
  - [ ] 验证返回明确的错误信息
  - [ ] 验证AI不会编造数据

- [ ] 测试场景3：上传多个Excel文件
  - [ ] 验证自动选择最新的文件
  - [ ] 验证读取正确的文件

- [ ] 测试场景4：用户提供了正确的文件路径
  - [ ] 验证优先使用用户提供的路径
  - [ ] 验证动态发现作为后备方案

## 阶段4：文档和清理

- [ ] 更新代码注释，说明动态文件发现机制
- [ ] 更新系统提示（如果需要），说明文件发现逻辑
- [ ] 验证所有测试通过
- [ ] 检查日志输出，确保错误信息清晰

