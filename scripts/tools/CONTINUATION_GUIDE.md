# FractalFlow 实施延续指南

**版本**: 1.0.0
**最后更新**: 2026-01-01

---

## 📋 项目状态

Data Agent V4 项目的核心 FractalFlow 文档化工作已完成（190个文件，100%覆盖）。

本指南面向需要继续维护或扩展文档的团队成员。

---

## 🎯 常见任务

### 任务1: 为新文件添加文档

**场景**: 添加新的业务逻辑文件

**步骤**:
```bash
# 1. 分析依赖关系
cd scripts/tools
python analyze_dependencies.py path/to/new_file.py

# 2. 生成文档头部
python generate_header.py path/to/new_file.py

# 3. 人工审核并补充
# - 检查 [INPUT] 字段是否完整
# - 检查 [OUTPUT] 字段是否准确
# - 补充 [LINK] 字段的下游依赖
# - 添加调用方信息

# 4. 验证规范
python validate_fractalflow.py path/to/new_file.py
```

**预计时间**: 10-15 分钟/文件

---

### 任务2: 批量文档化新模块

**场景**: 新增一个功能模块，需要为多个文件添加文档

**步骤**:
```bash
# 1. 创建待处理文件列表
find new_module -type f -name "*.py" > files_to_process.txt

# 2. 批量处理
while read file; do
    python scripts/tools/analyze_dependencies.py "$file"
    python scripts/tools/generate_header.py "$file"
done < files_to_process.txt

# 3. 批量验证
python scripts/tools/validate_fractalflow.py --all
```

**预计时间**: 5-10 分钟/文件（批量处理）

---

### 任务3: 更新依赖关系

**场景**: 代码重构导致依赖关系变化

**步骤**:
```bash
# 1. 重新分析依赖
python scripts/tools/analyze_dependencies.py path/to/refactored_file.py

# 2. 对比现有 [LINK] 字段
# 打开文件，检查 [LINK] 字段是否需要更新

# 3. 手动更新文档
# 编辑文件，更新上游依赖、下游依赖和调用方
```

**注意事项**:
- 修改上游模块时，记得更新所有下游模块的 [LINK]
- 使用 IDE 的"查找引用"功能辅助更新

---

### 任务4: 文档合规性检查

**场景**: PR 前检查文档规范性

**步骤**:
```bash
# 检查单个文件
python scripts/tools/validate_fractalflow.py path/to/file.py

# 检查所有修改的文件
git diff --name-only | grep -E '\.(py|ts|tsx)$' | while read file; do
    python scripts/tools/validate_fractalflow.py "$file"
done
```

---

## 🔧 工具使用技巧

### analyze_dependencies.py

**高级用法**:
```bash
# 分析多个文件
python analyze_dependencies.py file1.py file2.py file3.py

# 输出到文件
python analyze_dependencies.py file.py > dependencies.txt
```

**限制**:
- 只能分析静态导入
- 动态导入（如 `__import__()`）需要手动补充
- 相对路径需要转换为绝对路径

### generate_header.py

**建议流程**:
1. 准备好模块的基本信息（名称、职责、版本）
2. 运行工具生成初稿
3. 立即打开文件人工审核
4. 补充完整的 [INPUT]、[OUTPUT]、[LINK] 字段

**注意事项**:
- 工具不会覆盖现有文档（需手动确认）
- 备份重要文件后再使用

### validate_fractalflow.py

**输出解读**:
- ✅ **合规**: 所有必需字段存在且格式正确
- ❌ **错误**: 缺少必需字段或格式错误（必须修复）
- ⚠️ **警告**: 字段内容为空或不完整（建议修复）

---

## 📝 文档模板自定义

### 修改现有模板

模板文件位于 `scripts/templates/`：

1. **python_service.txt** - Python 文件模板
2. **typescript_component.txt** - TypeScript/TSX 模板
3. **folder_md.txt** - 目录文档模板

**自定义步骤**:
1. 备份原模板
2. 编辑模板文件
3. 测试新模板（使用 `generate_header.py`）
4. 提交更改并通知团队

### 创建新模板

**场景**: 需要为新的文件类型创建模板

**步骤**:
1. 参考现有模板格式
2. 创建新的 `.txt` 文件
3. 更新 `generate_header.py` 以支持新类型
4. 测试并验证

---

## 🐛 常见问题

### Q1: 依赖分析不准确

**问题**: `analyze_dependencies.py` 遗漏了某些导入

**原因**:
- 动态导入无法分析
- 条件导入（if/else）中的导入
- 间接依赖（通过中间模块）

**解决方案**:
- 人工补充遗漏的依赖
- 在文档中标注"部分依赖手动补充"

### Q2: 工具无法识别文件类型

**问题**: `generate_header.py` 提示"不支持的文件类型"

**原因**: 文件扩展名不在支持列表中

**解决方案**:
- 修改 `get_template()` 函数添加新扩展名
- 或手动复制模板内容

### Q3: 文档头部被破坏

**问题**: 编辑后文档格式混乱

**原因**: 手动编辑时的格式错误

**解决方案**:
- 使用验证工具检查：`validate_fractalflow.py file.py`
- 参考模板重新格式化
- 从 Git 恢复并重新编辑

---

## 🚀 最佳实践

### 1. 文档与代码同步

**原则**: 修改代码时同步更新文档

**检查清单**:
- [ ] 签名变更 → 更新 [INPUT]/[OUTPUT]
- [ ] 新增依赖 → 更新 [LINK] 上游
- [ ] 被新模块依赖 → 更新 [LINK] 下游

### 2. 定期维护

**频率**: 每月一次

**任务**:
- 运行 `validate_fractalflow.py --all`
- 随机抽查 10% 的文件
- 更新过时的依赖关系
- 优化模板内容

### 3. 团队协作

**规范**:
- PR 必须通过文档验证
- 新文件必须包含 FractalFlow 文档
- 定期分享文档维护经验

---

## 📞 获取帮助

**资源**:
- README.md - 工具使用说明
- FINAL_SUMMARY.md - 项目总结
- 项目根目录 CLAUDE.md - 开发规范

**联系**:
- Data Agent Team
- 创建 GitHub Issue

---

**祝您文档工作顺利！** 🎉
