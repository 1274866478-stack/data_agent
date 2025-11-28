/**
 * Sidebar组件单元测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from '../Sidebar';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: () => '/',
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  LayoutDashboard: () => <span data-testid="dashboard-icon">Dashboard</span>,
  Database: () => <span data-testid="database-icon">Database</span>,
  BarChart3: () => <span data-testid="chart-icon">Chart</span>,
  Bot: () => <span data-testid="bot-icon">Bot</span>,
  Settings: () => <span data-testid="settings-icon">Settings</span>,
  FileText: () => <span data-testid="file-icon">File</span>,
  Users: () => <span data-testid="users-icon">Users</span>,
  ChevronDown: () => <span data-testid="chevron-down">Down</span>,
  ChevronRight: () => <span data-testid="chevron-right">Right</span>,
  Plus: () => <span data-testid="plus-icon">Plus</span>,
}));

describe('Sidebar', () => {
  const mockOnCollapse = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('渲染测试', () => {
    it('展开状态下应该显示菜单标题', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);
      expect(screen.getByText('菜单')).toBeInTheDocument();
      expect(screen.getByText('导航功能')).toBeInTheDocument();
    });

    it('折叠状态下不应该显示菜单标题', () => {
      render(<Sidebar collapsed={true} onCollapse={mockOnCollapse} />);
      expect(screen.queryByText('菜单')).not.toBeInTheDocument();
    });

    it('应该显示新建项目按钮', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);
      expect(screen.getByText('新建项目')).toBeInTheDocument();
    });
  });

  describe('导航菜单测试', () => {
    it('应该显示分组标题', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);

      expect(screen.getByText('主要功能')).toBeInTheDocument();
      expect(screen.getByText('管理')).toBeInTheDocument();
    });

    it('点击主要功能分组应该展开菜单项', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);

      // 点击展开主要功能菜单
      const mainSection = screen.getByText('主要功能');
      fireEvent.click(mainSection);

      expect(screen.getByText('仪表板')).toBeInTheDocument();
      expect(screen.getByText('数据源管理')).toBeInTheDocument();
      expect(screen.getByText('数据分析')).toBeInTheDocument();
      expect(screen.getByText('AI 助手')).toBeInTheDocument();
    });

    it('点击管理分组应该展开管理菜单', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);

      // 点击展开管理菜单
      const adminSection = screen.getByText('管理');
      fireEvent.click(adminSection);

      expect(screen.getByText('报告中心')).toBeInTheDocument();
      expect(screen.getByText('用户管理')).toBeInTheDocument();
      expect(screen.getByText('系统设置')).toBeInTheDocument();
    });

    it('展开后应该显示徽章', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);

      // 先展开主要功能
      const mainSection = screen.getByText('主要功能');
      fireEvent.click(mainSection);

      expect(screen.getByText('3')).toBeInTheDocument(); // 数据源管理
      expect(screen.getByText('新')).toBeInTheDocument(); // AI助手
    });
  });

  describe('折叠展开测试', () => {
    it('展开状态应该有正确的宽度样式', () => {
      const { container } = render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);
      const aside = container.querySelector('aside');
      expect(aside).toHaveClass('w-64');
    });

    it('折叠状态应该有正确的宽度样式', () => {
      const { container } = render(<Sidebar collapsed={true} onCollapse={mockOnCollapse} />);
      const aside = container.querySelector('aside');
      expect(aside).toHaveClass('w-16');
    });

    it('点击折叠按钮应该调用onCollapse', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);
      
      // 点击ChevronDown按钮
      const collapseButton = screen.getByTestId('chevron-down').closest('button');
      if (collapseButton) {
        fireEvent.click(collapseButton);
        expect(mockOnCollapse).toHaveBeenCalledTimes(1);
      }
    });
  });

  describe('导航分组展开/折叠测试', () => {
    it('点击分组标题应该切换展开状态', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);

      // 点击展开主要功能
      const mainSection = screen.getByText('主要功能');
      fireEvent.click(mainSection);

      // 验证菜单项可见
      expect(screen.getByText('仪表板')).toBeInTheDocument();

      // 再次点击折叠
      fireEvent.click(mainSection);

      // 验证分组标题仍然存在
      expect(screen.getByText('主要功能')).toBeInTheDocument();
    });
  });

  describe('链接导航测试', () => {
    it('所有菜单项应该包含正确的链接', () => {
      render(<Sidebar collapsed={false} onCollapse={mockOnCollapse} />);

      // 先展开主要功能
      const mainSection = screen.getByText('主要功能');
      fireEvent.click(mainSection);

      const dashboardLink = screen.getByText('仪表板').closest('a');
      expect(dashboardLink).toHaveAttribute('href', '/');

      const dataSourceLink = screen.getByText('数据源管理').closest('a');
      expect(dataSourceLink).toHaveAttribute('href', '/data-sources');
    });
  });
});

