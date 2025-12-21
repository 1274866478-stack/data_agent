# 修复Excel文件发现导致的AI幻觉问题

## 问题描述

当前AI代理在读取上传的Excel文件时出现幻觉（生成假数据，如"John Doe"），根本原因是：

1. **文件重命名问题**：系统将上传的文件重命名为UUID（如`5fe906...xlsx`），存储在`/app/uploads/data-sources/{tenant_id}/{file_id}{file_ext}`
2. **路径解析失败**：后端代码尝试读取用户提示中提供的固定文件名，但实际文件已被重命名，导致无法找到文件
3. **幻觉触发**：当文件找不到时，AI没有收到明确的错误信息，而是编造数据来"回答"用户问题

## 解决方案

实现**动态文件发现机制**，不依赖用户提供的具体文件名：

1. **递归搜索**：使用`glob`递归搜索`/app/uploads/`目录下的所有`.xlsx`文件
2. **智能选择**：如果找到多个文件，自动选择**最近修改**的文件
3. **严格错误处理**：如果找不到任何文件，抛出明确的`FileNotFoundError`，防止AI编造数据

## 影响范围

- `backend/src/app/services/agent/tools.py` - `inspect_file_func`和`analyze_dataframe_func`
- `backend/src/app/services/agent/path_extractor.py` - 路径解析逻辑
- 可能影响：`backend/src/app/services/agent/agent_service.py` - 文件数据源检测逻辑

## 预期效果

- ✅ AI能够自动找到上传的Excel文件，即使文件名被重命名为UUID
- ✅ 如果文件不存在，AI会收到明确的错误信息，不会编造数据
- ✅ 支持多个文件场景，自动选择最新的文件
- ✅ 保持向后兼容，如果用户提供了正确的路径，仍然优先使用

## 风险评估

- **低风险**：主要是增强现有功能，不改变核心逻辑
- **兼容性**：保持对现有路径格式的支持
- **性能**：递归搜索可能稍慢，但文件数量通常较少，影响可忽略

