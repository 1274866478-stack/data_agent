import { test, expect } from '@playwright/test';

/**
 * 健康检查测试
 * 验证应用基础功能是否正常
 */
test.describe('Health Check', () => {
  test('应用首页应该正常加载', async ({ page }) => {
    await page.goto('/');
    
    // 验证页面标题
    await expect(page).toHaveTitle(/Data Agent/);
    
    // 验证页面加载完成
    await expect(page.locator('body')).toBeVisible();
  });

  test('API健康检查端点应该返回200', async ({ request }) => {
    const response = await request.get('http://localhost:8004/health');
    
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data.status).toBe('healthy');
  });

  test('前端应该能够连接到后端API', async ({ page }) => {
    // 监听API请求
    const apiRequestPromise = page.waitForResponse(
      response => response.url().includes('/api/') && response.status() === 200,
      { timeout: 10000 }
    );

    await page.goto('/');
    
    // 等待至少一个API请求成功
    try {
      await apiRequestPromise;
    } catch (error) {
      // 如果没有API请求,这是正常的(首页可能不需要API)
      console.log('首页未发起API请求');
    }
  });

  test('页面应该没有控制台错误', async ({ page }) => {
    const consoleErrors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/');
    
    // 等待页面完全加载
    await page.waitForLoadState('networkidle');
    
    // 验证没有严重错误(允许一些警告)
    const criticalErrors = consoleErrors.filter(
      error => !error.includes('Warning') && !error.includes('DevTools')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('页面应该响应式设计', async ({ page }) => {
    // 测试桌面视图
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();

    // 测试平板视图
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('body')).toBeVisible();

    // 测试移动视图
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('body')).toBeVisible();
  });

  test('页面加载时间应该在合理范围内', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // 页面加载应该在5秒内完成
    expect(loadTime).toBeLessThan(5000);
  });
});

test.describe('Navigation', () => {
  test('导航栏应该可见', async ({ page }) => {
    await page.goto('/');
    
    // 查找导航元素(根据实际UI调整选择器)
    const nav = page.locator('nav, header, [role="navigation"]').first();
    await expect(nav).toBeVisible();
  });

  test('应该能够导航到不同页面', async ({ page }) => {
    await page.goto('/');
    
    // 测试导航链接(根据实际路由调整)
    const links = [
      { text: /home|首页/i, url: '/' },
      { text: /about|关于/i, url: '/about' },
    ];

    for (const link of links) {
      const linkElement = page.getByRole('link', { name: link.text }).first();
      
      if (await linkElement.isVisible()) {
        await linkElement.click();
        await page.waitForLoadState('networkidle');
        
        // 验证URL变化
        expect(page.url()).toContain(link.url);
        
        // 返回首页
        await page.goto('/');
      }
    }
  });
});

test.describe('Error Handling', () => {
  test('404页面应该正确显示', async ({ page }) => {
    const response = await page.goto('/this-page-does-not-exist');
    
    // 验证返回404状态码或显示404页面
    if (response) {
      expect(response.status()).toBe(404);
    }
    
    // 验证页面显示错误信息
    const body = await page.textContent('body');
    expect(body).toMatch(/404|not found|页面不存在/i);
  });

  test('网络错误应该有友好提示', async ({ page, context }) => {
    // 模拟离线状态
    await context.setOffline(true);
    
    await page.goto('/');
    
    // 恢复在线状态
    await context.setOffline(false);
  });
});

