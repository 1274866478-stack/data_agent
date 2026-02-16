import { test, expect } from '@playwright/test';

/**
 * 数据源管理E2E测试
 * 测试数据源连接、查询、管理流程
 */

test.describe('数据源管理', () => {
  test.skip('应该显示数据源列表', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 验证页面标题
    await expect(page.locator('h1')).toContainText(/数据源|Data Source/i);
    
    // 验证列表容器存在
    const list = page.locator('[role="list"], table, .data-source-list');
    await expect(list).toBeVisible();
  });

  test.skip('应该能够添加PostgreSQL数据源', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 点击添加按钮
    await page.click('button:has-text("添加"), button:has-text("Add")');
    
    // 选择数据库类型
    await page.selectOption('[name="dbType"]', 'postgresql');
    
    // 填写连接信息
    await page.fill('[name="name"]', 'Test PostgreSQL');
    await page.fill('[name="host"]', 'localhost');
    await page.fill('[name="port"]', '5432');
    await page.fill('[name="database"]', 'testdb');
    await page.fill('[name="username"]', 'testuser');
    await page.fill('[name="password"]', 'testpass');
    
    // 提交表单
    await page.click('button[type="submit"]');
    
    // 验证成功消息
    await expect(page.locator('text=/添加成功|Added successfully/i')).toBeVisible({
      timeout: 10000
    });
  });

  test.skip('应该能够测试数据源连接', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 点击添加按钮
    await page.click('button:has-text("添加"), button:has-text("Add")');
    
    // 填写连接信息
    await page.fill('[name="connectionString"]', 'postgresql://user:pass@localhost:5432/db');
    
    // 点击测试连接按钮
    await page.click('button:has-text("测试连接"), button:has-text("Test Connection")');
    
    // 等待测试结果
    await expect(
      page.locator('text=/连接成功|Connection successful|连接失败|Connection failed/i')
    ).toBeVisible({ timeout: 10000 });
  });

  test.skip('应该能够查看数据源详情', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 点击第一个数据源
    await page.click('[role="list"] > *:first-child, table tbody tr:first-child');
    
    // 验证详情页面
    await expect(page.locator('h1, h2')).toContainText(/详情|Detail/i);
    
    // 验证连接信息显示
    await expect(page.locator('text=/主机|Host/i')).toBeVisible();
    await expect(page.locator('text=/端口|Port/i')).toBeVisible();
    await expect(page.locator('text=/数据库|Database/i')).toBeVisible();
  });

  test.skip('应该能够编辑数据源', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 点击编辑按钮
    await page.click('button:has-text("编辑"), button:has-text("Edit")');
    
    // 修改名称
    const newName = `Updated Data Source ${Date.now()}`;
    await page.fill('[name="name"]', newName);
    
    // 保存更改
    await page.click('button:has-text("保存"), button:has-text("Save")');
    
    // 验证成功消息
    await expect(page.locator('text=/更新成功|Updated successfully/i')).toBeVisible({
      timeout: 5000
    });
  });

  test.skip('应该能够删除数据源', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 点击删除按钮
    await page.click('button:has-text("删除"), button:has-text("Delete")');
    
    // 确认删除
    await page.click('button:has-text("确认"), button:has-text("Confirm")');
    
    // 验证成功消息
    await expect(page.locator('text=/删除成功|Deleted successfully/i')).toBeVisible({
      timeout: 5000
    });
  });

  test.skip('应该验证连接字符串格式', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 点击添加按钮
    await page.click('button:has-text("添加"), button:has-text("Add")');
    
    // 填写无效的连接字符串
    await page.fill('[name="connectionString"]', 'invalid-connection-string');
    
    // 提交表单
    await page.click('button[type="submit"]');
    
    // 验证错误消息
    await expect(page.locator('text=/格式错误|Invalid format/i')).toBeVisible();
  });

  test.skip('应该能够查询数据源', async ({ page }) => {
    await page.goto('/data-sources/1/query');
    
    // 输入SQL查询
    await page.fill('[name="query"], textarea', 'SELECT * FROM users LIMIT 10');
    
    // 执行查询
    await page.click('button:has-text("执行"), button:has-text("Execute"), button:has-text("运行")');
    
    // 验证结果显示
    await expect(page.locator('table, [role="table"]')).toBeVisible({ timeout: 10000 });
    
    // 验证有数据行
    const rows = page.locator('table tbody tr, [role="row"]');
    expect(await rows.count()).toBeGreaterThan(0);
  });

  test.skip('应该显示查询错误', async ({ page }) => {
    await page.goto('/data-sources/1/query');
    
    // 输入错误的SQL查询
    await page.fill('[name="query"], textarea', 'SELECT * FROM non_existent_table');
    
    // 执行查询
    await page.click('button:has-text("执行"), button:has-text("Execute")');
    
    // 验证错误消息
    await expect(page.locator('text=/错误|Error|失败|Failed/i')).toBeVisible({
      timeout: 10000
    });
  });

  test.skip('应该支持导出查询结果', async ({ page }) => {
    await page.goto('/data-sources/1/query');
    
    // 执行查询
    await page.fill('[name="query"], textarea', 'SELECT * FROM users LIMIT 10');
    await page.click('button:has-text("执行"), button:has-text("Execute")');
    
    // 等待结果
    await expect(page.locator('table')).toBeVisible({ timeout: 10000 });
    
    // 点击导出按钮
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("导出"), button:has-text("Export")');
    
    // 验证下载开始
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.csv|\.xlsx|\.json/);
  });
});

test.describe('数据源安全性', () => {
  test.skip('密码字段应该被隐藏', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 点击添加按钮
    await page.click('button:has-text("添加"), button:has-text("Add")');
    
    // 验证密码字段类型
    const passwordInput = page.locator('[name="password"]');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test.skip('连接字符串中的密码应该被脱敏', async ({ page }) => {
    await page.goto('/data-sources');
    
    // 查看数据源详情
    await page.click('[role="list"] > *:first-child, table tbody tr:first-child');
    
    // 验证连接字符串中的密码被隐藏
    const connectionString = page.locator('text=/postgresql:\\/\\//');
    const text = await connectionString.textContent();
    
    // 密码应该被替换为 ***
    expect(text).toMatch(/\*\*\*|\[hidden\]|\[masked\]/i);
  });
});

