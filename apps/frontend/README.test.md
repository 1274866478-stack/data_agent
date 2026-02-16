# 前端测试指南

本文档说明如何运行和编写前端测试。

## 测试类型

### 1. 单元测试 (Jest + React Testing Library)

测试单个组件、函数和store的行为。

**运行测试:**
```bash
# 开发模式 (watch mode)
npm test

# CI模式 (单次运行)
npm run test:ci

# 生成覆盖率报告
npm run test:coverage
```

**测试文件位置:**
- `src/**/__tests__/**/*.test.ts(x)`
- `src/**/*.test.ts(x)`
- `src/**/*.spec.ts(x)`

**示例测试:**
```typescript
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  it('should render button text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('should call onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    screen.getByText('Click me').click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

### 2. E2E测试 (Playwright)

测试完整的用户流程和页面交互。

**运行测试:**
```bash
# 运行所有E2E测试
npm run test:e2e

# 运行E2E测试 (UI模式)
npm run test:e2e:ui

# 运行特定测试文件
npx playwright test e2e/example.spec.ts
```

**测试文件位置:**
- `e2e/**/*.spec.ts`

**示例测试:**
```typescript
import { test, expect } from '@playwright/test';

test('should complete data source creation flow', async ({ page }) => {
  // 1. 登录
  await page.goto('/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'password');
  await page.click('button[type="submit"]');

  // 2. 导航到数据源页面
  await page.goto('/data-sources');
  
  // 3. 创建新数据源
  await page.click('text=Add Data Source');
  await page.fill('[name="name"]', 'Test Database');
  await page.fill('[name="connectionString"]', 'postgresql://...');
  await page.click('button:has-text("Save")');

  // 4. 验证成功
  await expect(page.locator('text=Test Database')).toBeVisible();
});
```

## 测试覆盖率目标

| 类型 | 目标 | 当前 |
|------|------|------|
| 单元测试 | ≥75% | 待测量 |
| 组件测试 | ≥75% | 待测量 |
| E2E测试 | ≥70% | 待测量 |

## 测试最佳实践

### 1. 单元测试

- ✅ 测试组件的行为,不是实现细节
- ✅ 使用`screen.getByRole`等语义化查询
- ✅ 测试用户交互和边界条件
- ✅ Mock外部依赖(API调用、第三方库)
- ❌ 不要测试第三方库的功能
- ❌ 不要过度Mock

### 2. E2E测试

- ✅ 测试关键用户流程
- ✅ 使用真实的用户交互
- ✅ 验证完整的功能流程
- ✅ 测试跨页面的交互
- ❌ 不要测试每个细节(单元测试负责)
- ❌ 不要依赖测试执行顺序

### 3. Store测试

- ✅ 测试状态变化
- ✅ 测试actions的副作用
- ✅ 在每个测试前重置状态
- ✅ 测试边界条件

## 常见问题

### Q: 如何Mock API调用?

```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/v1/data-sources', (req, res, ctx) => {
    return res(ctx.json([
      { id: '1', name: 'Test DB' }
    ]));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Q: 如何测试需要认证的组件?

```typescript
import { render } from '@testing-library/react';
import { useAuthStore } from '@/store/authStore';

// Mock认证状态
beforeEach(() => {
  useAuthStore.setState({
    isAuthenticated: true,
    user: { id: '1', email: 'test@example.com' },
    token: 'mock_token',
  });
});
```

### Q: 如何运行特定测试?

```bash
# 运行特定文件
npm test -- authStore.test.ts

# 运行匹配模式的测试
npm test -- --testNamePattern="should login"
```

## 持续集成

测试在GitHub Actions中自动运行:
- 每次push到main/develop分支
- 每次创建Pull Request
- 测试失败会阻止合并

查看 `.github/workflows/ci.yml` 了解详情。

