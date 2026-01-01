# FractalFlow 自动化工具集

这是一套用于自动化添加和验证 FractalFlow 标准化文档的工具。

## 工具列表

### 1. analyze_dependencies.py
依赖关系分析工具，自动分析 Python 和 TypeScript 文件的导入依赖关系。

**功能**：
- 分析 Python AST 导入语句
- 解析 TypeScript import 语句
- 生成 [LINK] 字段的初稿

**使用方法**：
```bash
python analyze_dependencies.py <file_path>
```

### 2. generate_header.py
文档头部生成工具，根据模板为文件添加 FractalFlow 文档头部。

**功能**：
- 交互式收集文件元数据
- 自动填充模板
- 插入到文件头部

**使用方法**：
```bash
python generate_header.py <file_path>
```

### 3. validate_fractalflow.py
FractalFlow 规范验证工具，检查文件是否符合文档规范。

**功能**：
- 验证字段完整性
- 检查路径有效性
- 生成合规性报告

**使用方法**：
```bash
python validate_fractalflow.py <file_path>
python validate_fractalflow.py --all  # 检查所有文件
```

## 工作流程

推荐的文档添加流程：

1. **分析依赖**：`python analyze_dependencies.py path/to/file.py`
2. **生成头部**：`python generate_header.py path/to/file.py`
3. **人工审核**：检查生成的内容是否准确
4. **验证规范**：`python validate_fractalflow.py path/to/file.py`

## 模板文件

模板文件位于 `../templates/` 目录：

- `folder_md.txt` - _folder.md 文档模板
- `python_service.txt` - Python 文件头部模板
- `typescript_component.txt` - TypeScript/TSX 文件头部模板

## 注意事项

- 这些工具是辅助工具，生成的文档需要人工审核和补充
- 依赖分析可能不完全准确，特别是动态导入
- 验证工具只能检查格式，无法验证内容准确性

## 版本

**版本**: 1.0.0
**创建日期**: 2026-01-01
**维护者**: Data Agent Team
