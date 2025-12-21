## Context

Agent 服务依赖于 MCP (Model Context Protocol) 来提供数据库查询和图表生成功能。MCP PostgreSQL 服务器需要通过 Node.js 的 `npx` 命令启动。当前后端 Docker 容器基于 `python:3.11-slim` 镜像，没有安装 Node.js，导致 MCP 客户端初始化失败。

## Goals

1. 确保 MCP PostgreSQL 服务器可以正常启动
2. 提供清晰的错误信息，当依赖不可用时
3. 支持优雅降级机制（禁用 MCP，使用自定义工具）

## Non-Goals

- 不改变 MCP 的工作方式
- 不改变 Agent 的核心架构
- 不强制要求所有部署都使用 MCP（支持通过环境变量禁用）

## Decisions

### Decision 1: 在 Dockerfile 中安装 Node.js

**选择**: 在 `backend/Dockerfile` 的 base 阶段安装 Node.js LTS 版本

**理由**:
- MCP PostgreSQL 服务器是 Agent 功能的核心依赖
- 安装 Node.js 是最直接的解决方案
- 使用官方 Node.js 仓库确保稳定性和安全性

**实施细节**:
```dockerfile
# 在系统依赖安装部分添加
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*
```

**替代方案考虑**:
1. **使用多阶段构建**: 从 Node.js 基础镜像开始，再安装 Python（增加复杂度）
2. **通过 apt 安装旧版本**: 可能版本过旧，不推荐
3. **不安装，强制禁用 MCP**: 失去 Agent 核心功能，不可行

### Decision 2: 添加 npx 可用性检查

**选择**: 在 `get_mcp_config()` 函数中添加 `npx` 命令可用性检查，并提供清晰的错误信息

**理由**:
- 早期检测问题，避免运行时失败
- 提供明确的错误信息，便于调试
- 支持优雅降级

**实施细节**:
```python
import shutil

def get_mcp_config(database_url: str, enable_echarts: bool = False) -> Dict[str, Any]:
    # 检查 npx 是否可用
    npx_path = shutil.which("npx")
    if not npx_path:
        logger.error(
            "❌ npx 命令不可用。MCP PostgreSQL 服务器需要 Node.js/npm。"
            "请安装 Node.js 或设置 DISABLE_MCP_TOOLS=true 使用自定义工具。"
        )
        raise RuntimeError("npx command not found. Node.js is required for MCP servers.")
    
    npx_command = "npx.cmd" if sys.platform == "win32" else "npx"
    # ... rest of config
```

### Decision 3: 改进错误处理和日志

**选择**: 在 `build_agent()` 和 `_get_or_create_agent()` 中添加详细的错误处理和日志

**理由**:
- 帮助快速定位问题
- 提供明确的故障排查指引
- 支持调试和监控

**实施细节**:
- 在 MCP 客户端初始化时捕获 `FileNotFoundError`
- 记录详细的错误信息（命令路径、环境变量等）
- 提供用户友好的错误消息

### Decision 4: 保持 DISABLE_MCP_TOOLS 环境变量支持

**选择**: 保留现有的 `DISABLE_MCP_TOOLS` 环境变量机制，作为降级方案

**理由**:
- 提供灵活性，允许在特殊情况下禁用 MCP
- 支持开发和测试环境的不同配置
- 作为故障恢复的备选方案

## Risks / Trade-offs

### 风险 1: Docker 镜像大小增加

**风险**: 安装 Node.js 会增加 Docker 镜像大小（约 100-200MB）

**缓解措施**:
- 使用 `slim` 版本的 Node.js（如果可用）
- 清理 apt 缓存
- 考虑多阶段构建（如果大小成为问题）

**权衡**: 功能完整性 > 镜像大小

### 风险 2: Node.js 版本冲突

**风险**: 如果系统已安装 Node.js，可能版本不兼容

**缓解措施**:
- 使用官方 NodeSource 仓库安装 LTS 版本
- 明确文档说明 Node.js 版本要求
- 在 Dockerfile 中固定版本

**权衡**: 使用最新 LTS 版本，平衡稳定性和功能

### 风险 3: 构建时间增加

**风险**: 安装 Node.js 会增加 Docker 构建时间

**缓解措施**:
- 利用 Docker 层缓存
- 将 Node.js 安装放在单独的 RUN 指令中，便于缓存

**权衡**: 构建时间略微增加是可以接受的

## Migration Plan

### 步骤 1: 更新 Dockerfile
- 在 base 阶段添加 Node.js 安装
- 验证安装成功

### 步骤 2: 改进错误处理
- 添加 npx 可用性检查
- 改进错误日志
- 测试错误场景

### 步骤 3: 测试验证
- 构建新的 Docker 镜像
- 验证 MCP 服务器可以启动
- 测试 Agent 查询功能
- 验证错误处理逻辑

### 步骤 4: 文档更新
- 更新 README，说明 Node.js 依赖
- 添加故障排查指南
- 说明 DISABLE_MCP_TOOLS 使用方法

### 回滚计划
- 如果出现问题，可以临时设置 `DISABLE_MCP_TOOLS=true`
- 恢复到之前的 Dockerfile 版本
- 使用自定义工具作为备选方案

## Open Questions

1. **Node.js 版本选择**: 是否应该固定特定 LTS 版本，还是始终使用最新 LTS？
   - **建议**: 使用 20.x LTS 版本，提供稳定性和新特性支持

2. **是否需要验证 npx 在运行时可用**:
   - **建议**: 在启动时检查，但不需要在每次请求时检查（性能考虑）

3. **是否应该支持通过环境变量指定 npx 路径**:
   - **建议**: 当前不需要，但如果未来有复杂部署需求可以考虑

