# Frontend Scripts

这个目录包含了前端项目的辅助脚本。

## 可用脚本

### cleanup.sh / cleanup.bat
清理前端项目中不必要的文件和缓存。

**使用方法：**
```bash
# Linux/Mac
./scripts/cleanup.sh

# Windows
scripts\cleanup.bat
```

**清理内容：**
- Next.js 构建缓存 (`.next/`)
- Node.js 模块缓存 (`node_modules/.cache/`)
- 测试覆盖率报告 (`coverage/`)
- TypeScript 构建输出 (`dist/`, `build/`)
- 日志文件 (`*.log`)
- 系统临时文件 (`.DS_Store`, `Thumbs.db`)

## 注意事项

- 清理后如果遇到依赖问题，请运行 `npm install`
- 清理后需要重新构建项目，请运行 `npm run build`
- 建议在以下情况使用清理脚本：
  - 项目构建出现未知错误
  - 需要释放磁盘空间
  - 准备打包发布前