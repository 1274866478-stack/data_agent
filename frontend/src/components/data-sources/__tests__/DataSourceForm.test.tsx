/**
 * DataSourceForm组件单元测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
  const mockTestConnection = jest.fn();
  const mockCreateDataSource = jest.fn();
  const mockOnSubmit = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useDataSourceStore as unknown as jest.Mock).mockReturnValue({
      testConnection: mockTestConnection,
      createDataSource: mockCreateDataSource,
    });
    (useDataSourceStore as unknown as { getState: jest.Mock }).getState = () => ({ error: null });
  });

  describe('渲染测试', () => {
    it('应该渲染表单标题', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText('添加数据源')).toBeInTheDocument();
    });

    it('编辑模式应该显示编辑标题', () => {
      render(<DataSourceForm tenantId="tenant-1" initialData={{ name: '测试' }} />);
      expect(screen.getByText('编辑数据源')).toBeInTheDocument();
    });

    it('应该渲染所有表单字段', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByLabelText('数据源名称 *')).toBeInTheDocument();
      expect(screen.getByLabelText('数据库类型 *')).toBeInTheDocument();
      expect(screen.getByLabelText('连接字符串 *')).toBeInTheDocument();
    });

    it('应该显示测试连接按钮', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText('测试连接')).toBeInTheDocument();
    });

    it('应该显示创建按钮', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText('创建数据源')).toBeInTheDocument();
    });
  });

  describe('数据库类型选项测试', () => {
    it('应该包含PostgreSQL选项', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByRole('option', { name: 'PostgreSQL' })).toBeInTheDocument();
    });

    it('应该包含MySQL选项', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByRole('option', { name: 'MySQL' })).toBeInTheDocument();
    });

    it('应该包含SQLite选项', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByRole('option', { name: 'SQLite' })).toBeInTheDocument();
    });
  });

  describe('表单验证测试', () => {
    it('连接字符串为空应该禁用测试按钮', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      const testButton = screen.getByText('测试连接');
      expect(testButton).toBeDisabled();
    });
  });

  describe('连接测试功能', () => {
    it('点击测试连接应该调用testConnection', async () => {
      const user = userEvent.setup();
      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接成功',
        response_time_ms: 100,
      });

      render(<DataSourceForm tenantId="tenant-1" />);

      const connectionInput = screen.getByLabelText('连接字符串 *');
      await user.type(connectionInput, 'postgresql://user:pass@localhost:5432/db');

      const testButton = screen.getByText('测试连接');
      await user.click(testButton);

      await waitFor(() => {
        expect(mockTestConnection).toHaveBeenCalled();
      });
    });

    it('连接成功应该显示成功状态', async () => {
      const user = userEvent.setup();
      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接成功',
        response_time_ms: 100,
      });

      render(<DataSourceForm tenantId="tenant-1" />);

      const connectionInput = screen.getByLabelText('连接字符串 *');
      await user.type(connectionInput, 'postgresql://user:pass@localhost:5432/db');

      const testButton = screen.getByText('测试连接');
      await user.click(testButton);

      await waitFor(() => {
        // 使用getAllByText因为页面上可能有多个"连接成功"文本
        const successTexts = screen.getAllByText('连接成功');
        expect(successTexts.length).toBeGreaterThan(0);
      });
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

  describe('连接字符串示例', () => {
    it('PostgreSQL应该显示正确的示例', () => {
      render(<DataSourceForm tenantId="tenant-1" />);
      expect(screen.getByText(/postgresql:\/\/username:password@localhost:5432\/database_name/)).toBeInTheDocument();
    });
  });
});

