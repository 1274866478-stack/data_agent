# 🤝 贡献指南

感谢你对 Data Agent V4 项目的关注!我们欢迎所有形式的贡献,包括但不限于:

- 🐛 报告Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- ✨ 实现新功能

---

## 📋 目录

- [行为准则](#行为准则)
- [开始之前](#开始之前)
- [开发环境设置](#开发环境设置)
- [开发工作流](#开发工作流)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [Pull Request流程](#pull-request流程)
- [测试要求](#测试要求)
- [文档要求](#文档要求)

---

## 📜 行为准则

### 我们的承诺

为了营造一个开放和友好的环境,我们承诺:

- ✅ 尊重不同的观点和经验
- ✅ 优雅地接受建设性批评
- ✅ 关注对社区最有利的事情
- ✅ 对其他社区成员表示同理心

### 不可接受的行为

- ❌ 使用性化的语言或图像
- ❌ 人身攻击或侮辱性评论
- ❌ 公开或私下骚扰
- ❌ 未经许可发布他人的私人信息

---

## 🚀 开始之前

### 1. 搜索现有Issue

在创建新Issue之前,请先搜索[现有Issue](https://github.com/your-org/data-agent/issues),避免重复。

### 2. 选择合适的Issue模板

我们提供以下Issue模板:

- **Bug报告**: 报告项目中的错误
- **功能请求**: 建议新功能或改进
- **文档改进**: 文档相关的问题
- **性能问题**: 性能相关的问题

### 3. 查看项目路线图

查看[项目路线图](./docs/ROADMAP.md)了解项目的发展方向。

---

## 💻 开发环境设置

### 前置要求

- **Node.js**: 18.x 或更高版本
- **Python**: 3.8 或更高版本
- **Docker**: 20.x 或更高版本
- **Git**: 2.x 或更高版本

### 克隆仓库

```bash
# 克隆你的fork
git clone https://github.com/YOUR_USERNAME/data-agent.git
cd data-agent

# 添加上游仓库
git remote add upstream https://github.com/your-org/data-agent.git
```

### 安装依赖

```bash
# 后端依赖
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 前端依赖
cd ../frontend
npm install
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件,设置必需的环境变量
# 特别注意: ZHIPUAI_API_KEY, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
```

### 启动开发环境

```bash
# 检查端口冲突
python scripts/check-ports.py

# 启动Docker服务
docker-compose up -d

# 验证服务状态
docker-compose ps
curl http://localhost:8004/health
```

---

## 🔄 开发工作流

### 1. 创建功能分支

```bash
# 更新主分支
git checkout main
git pull upstream main

# 创建功能分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 2. 进行开发

```bash
# 后端开发
cd backend
uvicorn src.app.main:app --reload --port 8004

# 前端开发
cd frontend
npm run dev
```

### 3. 运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v --cov

# 前端测试
cd frontend
npm test
npm run test:e2e
```

### 4. 代码检查

```bash
# 后端代码检查
cd backend
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/

# 前端代码检查
cd frontend
npm run lint
npm run type-check
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/your-feature-name
```

---

## 📏 代码规范

### 后端 (Python)

**代码风格:**
- 使用 **Black** 格式化代码
- 使用 **isort** 排序导入
- 遵循 **PEP 8** 规范
- 使用 **Google风格** docstring

**示例:**
```python
def calculate_total(items: List[Item]) -> Decimal:
    """
    计算商品总价
    
    Args:
        items: 商品列表
        
    Returns:
        总价金额
        
    Raises:
        ValueError: 当商品列表为空时
    """
    if not items:
        raise ValueError("商品列表不能为空")
    
    return sum(item.price for item in items)
```

**类型注解:**
- 所有函数必须包含类型注解
- 使用 `mypy` 进行类型检查

**异步代码:**
- 后端服务全程使用 `async/await`
- 数据库操作使用异步ORM

### 前端 (TypeScript)

**代码风格:**
- 使用 **ESLint** + **Prettier**
- 遵循 **Airbnb** 风格指南
- 使用 **strict TypeScript** 模式

**示例:**
```typescript
interface User {
  id: string;
  email: string;
  displayName: string | null;
}

const fetchUser = async (userId: string): Promise<User> => {
  const response = await fetch(`/api/users/${userId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch user');
  }
  return response.json();
};
```

**组件规范:**
- 使用函数式组件
- 使用 Hooks 管理状态
- Props 必须定义接口

---

## 📝 提交规范

### Commit Message格式

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type类型:**
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式(不影响代码运行)
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链相关

**示例:**
```bash
feat(tenant): add tenant quota management

- Add storage quota tracking
- Implement quota enforcement
- Add quota exceeded error handling

Closes #123
```

---

## 🔀 Pull Request流程

### 1. 创建Pull Request

- 填写PR模板中的所有必需信息
- 关联相关的Issue
- 添加适当的标签

### 2. PR检查清单

- [ ] 代码通过所有测试
- [ ] 代码通过linting检查
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] Commit message符合规范
- [ ] 没有合并冲突

### 3. Code Review

- 至少需要1个维护者的批准
- 解决所有review评论
- 保持PR专注于单一功能

### 4. 合并

- 使用 **Squash and Merge**
- 确保commit message清晰
- 删除功能分支

---

## ✅ 测试要求

### 测试覆盖率目标

- **后端**: ≥80%
- **前端**: ≥75%
- **关键路径**: 100%

### 测试类型

**后端:**
```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# E2E测试
pytest tests/e2e/ -v
```

**前端:**
```bash
# 单元测试
npm test

# E2E测试
npm run test:e2e
```

### 测试最佳实践

- ✅ 每个新功能必须包含测试
- ✅ Bug修复必须包含回归测试
- ✅ 测试应该独立且可重复
- ✅ 使用有意义的测试名称

---

## 📚 文档要求

### 必需文档

1. **代码注释**: 复杂逻辑必须注释
2. **API文档**: 新API端点必须在Swagger中文档化
3. **README更新**: 新功能需要更新README
4. **变更日志**: 重要变更记录在CHANGELOG.md

### 文档风格

- 使用清晰简洁的语言
- 提供代码示例
- 包含使用场景
- 保持文档与代码同步

---

## 🆘 获取帮助

### 资源

- **文档**: [docs/](./docs/)
- **API文档**: http://localhost:8004/docs
- **Issue讨论**: [GitHub Issues](https://github.com/your-org/data-agent/issues)

### 联系方式

- **Email**: support@dataagent.example.com
- **Discord**: [加入我们的Discord](https://discord.gg/dataagent)

---

## 📄 许可证

通过贡献代码,你同意你的贡献将在 [MIT License](./LICENSE) 下授权。

---

**感谢你的贡献! 🎉**

