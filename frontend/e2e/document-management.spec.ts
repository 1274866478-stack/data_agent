import { test, expect } from '@playwright/test';
import path from 'path';

/**
 * 文档管理E2E测试
 * 测试文档上传、查看、删除流程
 */

test.describe('文档管理', () => {
  test.skip('应该显示文档列表', async ({ page }) => {
    await page.goto('/documents');
    
    // 验证页面标题
    await expect(page.locator('h1')).toContainText(/文档|Document/i);
    
    // 验证列表容器存在
    const list = page.locator('[role="list"], table, .document-list');
    await expect(list).toBeVisible();
  });

  test.skip('应该能够上传PDF文档', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击上传按钮
    await page.click('button:has-text("上传"), button:has-text("Upload")');
    
    // 选择文件
    const fileInput = page.locator('input[type="file"]');
    
    // 创建测试文件路径
    const testFilePath = path.join(__dirname, '../test-fixtures/sample.pdf');
    
    // 上传文件
    await fileInput.setInputFiles(testFilePath);
    
    // 填写文档信息
    await page.fill('[name="title"]', 'Test PDF Document');
    await page.fill('[name="description"]', 'This is a test document');
    
    // 提交上传
    await page.click('button[type="submit"]');
    
    // 验证上传成功
    await expect(page.locator('text=/上传成功|Uploaded successfully/i')).toBeVisible({
      timeout: 15000
    });
    
    // 验证文档出现在列表中
    await expect(page.locator('text=Test PDF Document')).toBeVisible();
  });

  test.skip('应该能够上传Word文档', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击上传按钮
    await page.click('button:has-text("上传"), button:has-text("Upload")');
    
    // 选择文件
    const fileInput = page.locator('input[type="file"]');
    const testFilePath = path.join(__dirname, '../test-fixtures/sample.docx');
    
    await fileInput.setInputFiles(testFilePath);
    
    // 填写文档信息
    await page.fill('[name="title"]', 'Test Word Document');
    
    // 提交上传
    await page.click('button[type="submit"]');
    
    // 验证上传成功
    await expect(page.locator('text=/上传成功|Uploaded successfully/i')).toBeVisible({
      timeout: 15000
    });
  });

  test.skip('应该拒绝不支持的文件类型', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击上传按钮
    await page.click('button:has-text("上传"), button:has-text("Upload")');
    
    // 尝试上传不支持的文件类型
    const fileInput = page.locator('input[type="file"]');
    const testFilePath = path.join(__dirname, '../test-fixtures/sample.exe');
    
    await fileInput.setInputFiles(testFilePath);
    
    // 验证错误消息
    await expect(page.locator('text=/不支持|not supported|invalid file type/i')).toBeVisible();
  });

  test.skip('应该限制文件大小', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击上传按钮
    await page.click('button:has-text("上传"), button:has-text("Upload")');
    
    // 尝试上传超大文件
    const fileInput = page.locator('input[type="file"]');
    const testFilePath = path.join(__dirname, '../test-fixtures/large-file.pdf');
    
    await fileInput.setInputFiles(testFilePath);
    
    // 验证错误消息
    await expect(page.locator('text=/文件过大|file too large|size limit/i')).toBeVisible();
  });

  test.skip('应该能够查看文档详情', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击第一个文档
    await page.click('[role="list"] > *:first-child, table tbody tr:first-child');
    
    // 验证详情页面
    await expect(page.locator('h1, h2')).toContainText(/详情|Detail/i);
    
    // 验证文档信息显示
    await expect(page.locator('text=/标题|Title/i')).toBeVisible();
    await expect(page.locator('text=/大小|Size/i')).toBeVisible();
    await expect(page.locator('text=/上传时间|Upload/i')).toBeVisible();
  });

  test.skip('应该能够下载文档', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击下载按钮
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("下载"), button:has-text("Download")');
    
    // 验证下载开始
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBeTruthy();
  });

  test.skip('应该能够删除文档', async ({ page }) => {
    await page.goto('/documents');
    
    // 获取删除前的文档数量
    const countBefore = await page.locator('[role="list"] > *, table tbody tr').count();
    
    // 点击删除按钮
    await page.click('button:has-text("删除"), button:has-text("Delete")');
    
    // 确认删除
    await page.click('button:has-text("确认"), button:has-text("Confirm")');
    
    // 验证成功消息
    await expect(page.locator('text=/删除成功|Deleted successfully/i')).toBeVisible({
      timeout: 5000
    });
    
    // 验证文档数量减少
    const countAfter = await page.locator('[role="list"] > *, table tbody tr').count();
    expect(countAfter).toBe(countBefore - 1);
  });

  test.skip('应该显示上传进度', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击上传按钮
    await page.click('button:has-text("上传"), button:has-text("Upload")');
    
    // 选择大文件
    const fileInput = page.locator('input[type="file"]');
    const testFilePath = path.join(__dirname, '../test-fixtures/large-document.pdf');
    
    await fileInput.setInputFiles(testFilePath);
    
    // 提交上传
    await page.click('button[type="submit"]');
    
    // 验证进度条显示
    await expect(page.locator('[role="progressbar"], .progress')).toBeVisible();
  });

  test.skip('应该支持批量上传', async ({ page }) => {
    await page.goto('/documents');
    
    // 点击上传按钮
    await page.click('button:has-text("上传"), button:has-text("Upload")');
    
    // 选择多个文件
    const fileInput = page.locator('input[type="file"]');
    const testFiles = [
      path.join(__dirname, '../test-fixtures/sample1.pdf'),
      path.join(__dirname, '../test-fixtures/sample2.pdf'),
    ];
    
    await fileInput.setInputFiles(testFiles);
    
    // 提交上传
    await page.click('button[type="submit"]');
    
    // 验证上传成功
    await expect(page.locator('text=/上传成功|Uploaded successfully/i')).toBeVisible({
      timeout: 20000
    });
  });

  test.skip('应该支持搜索文档', async ({ page }) => {
    await page.goto('/documents');
    
    // 输入搜索关键词
    await page.fill('[placeholder*="搜索"], [placeholder*="Search"]', 'test');
    
    // 等待搜索结果
    await page.waitForTimeout(500);
    
    // 验证结果包含搜索关键词
    const items = page.locator('[role="list"] > *, table tbody tr');
    const count = await items.count();
    
    if (count > 0) {
      const firstItem = items.first();
      const text = await firstItem.textContent();
      expect(text?.toLowerCase()).toContain('test');
    }
  });

  test.skip('应该支持按类型过滤', async ({ page }) => {
    await page.goto('/documents');
    
    // 选择文件类型过滤
    await page.selectOption('[name="fileType"]', 'pdf');
    
    // 等待过滤结果
    await page.waitForTimeout(500);
    
    // 验证所有结果都是PDF
    const items = page.locator('[role="list"] > *, table tbody tr');
    const count = await items.count();
    
    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const text = await item.textContent();
      expect(text?.toLowerCase()).toContain('.pdf');
    }
  });
});

