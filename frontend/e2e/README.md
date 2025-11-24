# E2E测试指南

Data Agent V4使用Playwright进行端到端(E2E)测试,确保应用的完整用户流程正常工作。

---

## 📋 目录

- [测试文件结构](#测试文件结构)
- [运行测试](#运行测试)
- [编写测试](#编写测试)
- [测试最佳实践](#测试最佳实践)
- [调试测试](#调试测试)
- [CI/CD集成](#cicd集成)

---

## 📁 测试文件结构

```
frontend/e2e/
├── README.md                          # 本文档
├── health-check.spec.ts               # 健康检查和基础功能测试
├── tenant-management.spec.ts          # 租户管理测试
├── data-source-management.spec.ts     # 数据源管理测试
├── document-management.spec.ts        # 文档管理测试
└── example.spec.ts                    # 示例测试(已弃用)
```

---

## 🚀 运行测试

### 前置条件

1. **启动应用服务**
   ```bash
   # 启动后端
   cd backend
   uvicorn src.app.main:app --reload --port 8004

   # 启动前端
   cd frontend
   npm run dev
   ```

2. **确保服务可访问**
   - 前端: http://localhost:3000
   - 后端: http://localhost:8004

### 运行所有测试

```bash
cd frontend
npm run test:e2e
```

### 运行特定测试文件

```bash
# 只运行健康检查测试
npx playwright test health-check.spec.ts

# 只运行租户管理测试
npx playwright test tenant-management.spec.ts
```

### 运行特定测试用例

```bash
# 运行包含"应该显示租户列表"的测试
npx playwright test -g "应该显示租户列表"
```

### UI模式运行(推荐用于开发)

```bash
npm run test:e2e:ui
```

UI模式提供:
- 可视化测试执行
- 时间旅行调试
- 测试步骤回放
- 实时DOM快照

### 调试模式

```bash
# 启用调试模式
npx playwright test --debug

# 调试特定测试
npx playwright test health-check.spec.ts --debug
```

---

## ✍️ 编写测试

### 基础测试结构

```typescript
import { test, expect } from '@playwright/test';

test.describe('功能模块名称', () => {
  test.beforeEach(async ({ page }) => {
    // 每个测试前的准备工作
    await page.goto('/');
  });

  test('应该执行某个操作', async ({ page }) => {
    // 1. 执行操作
    await page.click('button');
    
    // 2. 验证结果
    await expect(page.locator('h1')).toContainText('预期文本');
  });
});
```

### 常用操作

#### 导航

```typescript
// 访问页面
await page.goto('/dashboard');

// 等待页面加载完成
await page.waitForLoadState('networkidle');
```

#### 查找元素

```typescript
// 通过文本查找
page.locator('text=登录');
page.getByText('登录');

// 通过角色查找
page.getByRole('button', { name: '提交' });

// 通过占位符查找
page.getByPlaceholder('请输入邮箱');

// 通过CSS选择器
page.locator('.btn-primary');
page.locator('#submit-button');
```

#### 交互操作

```typescript
// 点击
await page.click('button');
await page.getByRole('button', { name: '提交' }).click();

// 填写表单
await page.fill('[name="email"]', 'user@example.com');
await page.fill('input[type="password"]', 'password123');

// 选择下拉框
await page.selectOption('select[name="type"]', 'postgresql');

// 上传文件
await page.setInputFiles('input[type="file"]', 'path/to/file.pdf');

// 勾选复选框
await page.check('input[type="checkbox"]');
```

#### 断言

```typescript
// 元素可见性
await expect(page.locator('h1')).toBeVisible();
await expect(page.locator('.error')).toBeHidden();

// 文本内容
await expect(page.locator('h1')).toContainText('欢迎');
await expect(page.locator('h1')).toHaveText('欢迎使用');

// URL
await expect(page).toHaveURL('/dashboard');
await expect(page).toHaveURL(/dashboard/);

// 属性
await expect(page.locator('input')).toHaveAttribute('type', 'password');
await expect(page.locator('button')).toBeDisabled();
```

---

## ✅ 测试最佳实践

### 1. 使用有意义的测试描述

```typescript
// ✅ 好 - 描述清晰
test('应该在提交空表单时显示验证错误', async ({ page }) => {
  ...
});

// ❌ 差 - 描述模糊
test('测试表单', async ({ page }) => {
  ...
});
```

### 2. 使用data-testid属性

```typescript
// HTML
<button data-testid="submit-button">提交</button>

// 测试
await page.click('[data-testid="submit-button"]');
```

### 3. 等待元素而不是固定时间

```typescript
// ✅ 好 - 等待元素出现
await expect(page.locator('.success-message')).toBeVisible();

// ❌ 差 - 固定等待时间
await page.waitForTimeout(3000);
```

### 4. 使用Page Object模式

```typescript
// pages/LoginPage.ts
export class LoginPage {
  constructor(private page: Page) {}

  async login(email: string, password: string) {
    await this.page.fill('[name="email"]', email);
    await this.page.fill('[name="password"]', password);
    await this.page.click('button[type="submit"]');
  }
}

// 测试中使用
const loginPage = new LoginPage(page);
await loginPage.login('user@example.com', 'password');
```

### 5. 清理测试数据

```typescript
test.afterEach(async ({ page }) => {
  // 清理测试创建的数据
  await cleanupTestData();
});
```

### 6. 使用test.skip跳过未实现的测试

```typescript
test.skip('应该支持OAuth登录', async ({ page }) => {
  // TODO: 实现OAuth登录后启用此测试
});
```

---

## 🐛 调试测试

### 1. 使用调试模式

```bash
npx playwright test --debug
```

### 2. 查看测试报告

```bash
# 生成HTML报告
npx playwright test --reporter=html

# 查看报告
npx playwright show-report
```

### 3. 截图和视频

```typescript
// 配置playwright.config.ts
use: {
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
}
```

### 4. 控制台日志

```typescript
page.on('console', msg => console.log(msg.text()));
```

### 5. 慢动作执行

```bash
npx playwright test --slow-mo=1000
```

---

## 🔄 CI/CD集成

### GitHub Actions配置

已在`.github/workflows/ci.yml`中配置:

```yaml
- name: Run E2E tests
  run: |
    npm run test:e2e
```

### 测试覆盖率

目标覆盖率:
- 关键用户流程: 100%
- 页面导航: 80%
- 表单验证: 90%
- 错误处理: 70%

当前覆盖率:
- 健康检查: 100%
- 租户管理: 0% (测试已编写但跳过)
- 数据源管理: 0% (测试已编写但跳过)
- 文档管理: 0% (测试已编写但跳过)

---

## 📚 相关资源

- [Playwright官方文档](https://playwright.dev/)
- [Playwright最佳实践](https://playwright.dev/docs/best-practices)
- [测试选择器](https://playwright.dev/docs/selectors)
- [断言API](https://playwright.dev/docs/test-assertions)

---

**最后更新:** 2025-11-17

