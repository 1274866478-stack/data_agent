# 归档文件说明

**归档时间**: 2025-11-20 18:54:03

## 归档内容

本目录包含从 Data Agent V4 项目中归档的无用文件，这些文件不影响项目的正常运行。

### 归档的文件类型

1. **调试和日志文件**: debug/, logs/, backend/logs/
2. **测试文件**: backend/test_*.py, backend/run_v3_*.py
3. **临时数据**: backend/test.db, backend/uploads/
4. **构建产物**: frontend/coverage/, frontend/tsconfig.tsbuildinfo
5. **文档和报告**: docs/QA/, docs/test-reports/, docs/bugfix/

### 如何恢复

如果需要恢复某个文件，可以从本目录复制回项目根目录：

```bash
# 恢复单个文件
cp _archived/archive_20251120_185403/path/to/file /path/to/original/location

# 恢复整个目录
cp -r _archived/archive_20251120_185403/path/to/dir /path/to/original/location
```

### 安全删除

确认不再需要这些文件后，可以安全删除整个归档目录：

```bash
rm -rf _archived/archive_20251120_185403
```

## 注意事项

- ✅ 项目核心代码未被移动
- ✅ 配置文件保持不变
- ✅ Docker配置未受影响
- ✅ 依赖管理文件完整

如有疑问，请参考项目文档: CLAUDE.md
