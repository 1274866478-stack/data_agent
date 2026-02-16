/**
 * DataSourceForm组件单元测试
 * 现仅测试文件上传功能
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataSourceForm } from '../DataSourceForm';
import { useDataSourceStore } from '@/store/dataSourceStore';

// Mock store
jest.mock('@/store/dataSourceStore', () => ({
  useDataSourceStore: Object.assign(jest.fn(), {
    getState: () => ({ error: null }),
  }),
}));

describe('DataSourceForm', () => {
  const mockCreateDataSource = jest.fn();
  const mockOnSubmit = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useDataSourceStore as unknown as jest.Mock).mockReturnValue({
      createDataSource: mockCreateDataSource,
      isLoading: false,
      error: null,
    });
    (useDataSourceStore as unknown as { getState: jest.Mock }).getState = () => ({ error: null });
  });

  describe('渲染测试', () => {
    it('应该渲染表单标题', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText('上传数据文件')).toBeInTheDocument();
    });

    it('编辑模式应该显示编辑标题', () => {
      render(<DataSourceForm tenantId="tenant-1" initialData={{ name: '测试' }} />);
      expect(screen.getByText('编辑数据源')).toBeInTheDocument();
    });

    it('应该显示文件上传描述', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText('上传 CSV、Excel 或 SQLite 数据库文件')).toBeInTheDocument();
    });

    it('应该显示数据源名称输入框', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByLabelText('数据源名称 *')).toBeInTheDocument();
    });

    it('应该显示文件拖拽上传区域', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText(/点击选择文件/)).toBeInTheDocument();
    });

    it('应该显示上传按钮', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText('上传文件')).toBeInTheDocument();
    });
  });

  describe('取消按钮测试', () => {
    it('应该渲染取消按钮', () => {
      render(<DataSourceForm tenantId="tenant-1" onCancel={mockOnCancel} />);
      expect(screen.getByText('取消')).toBeInTheDocument();
    });

    it('点击取消应该调用onCancel', async () => {
      const user = userEvent.setup();
      render(<DataSourceForm tenantId="tenant-1" onCancel={mockOnCancel} />);

      await user.click(screen.getByText('取消'));
      expect(mockOnCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe('支持的文件类型', () => {
    it('应该显示支持的文件类型说明', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText(/CSV/)).toBeInTheDocument();
    });
  });
});
