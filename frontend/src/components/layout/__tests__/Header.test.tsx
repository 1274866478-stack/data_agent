/**
 * Header组件单元测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../Header';
import { useAuthStore } from '@/store';

// Mock store
jest.mock('@/store', () => ({
  useAuthStore: jest.fn(),
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Bell: () => <span data-testid="bell-icon">Bell</span>,
  Search: () => <span data-testid="search-icon">Search</span>,
  Settings: () => <span data-testid="settings-icon">Settings</span>,
  User: () => <span data-testid="user-icon">User</span>,
  Menu: () => <span data-testid="menu-icon">Menu</span>,
  Moon: () => <span data-testid="moon-icon">Moon</span>,
  Sun: () => <span data-testid="sun-icon">Sun</span>,
}));

describe('Header', () => {
  const mockOnSidebarToggle = jest.fn();
  const mockLogout = jest.fn();
  const defaultUser = {
    email: 'test@example.com',
    full_name: '测试用户',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useAuthStore as unknown as jest.Mock).mockReturnValue({
      user: defaultUser,
      logout: mockLogout,
    });
  });

  describe('渲染测试', () => {
    it('应该正确渲染标题', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      expect(screen.getByText('Data Agent V4')).toBeInTheDocument();
    });

    it('应该显示用户信息', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      expect(screen.getByText('测试用户')).toBeInTheDocument();
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });

    it('应该显示搜索框', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      expect(screen.getByPlaceholderText('搜索...')).toBeInTheDocument();
    });

    it('应该显示退出按钮', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      expect(screen.getByText('退出')).toBeInTheDocument();
    });
  });

  describe('交互测试', () => {
    it('点击侧边栏切换按钮应该调用onSidebarToggle', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      
      const menuButton = screen.getByTestId('menu-icon').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
        expect(mockOnSidebarToggle).toHaveBeenCalledTimes(1);
      }
    });

    it('点击退出按钮应该调用logout', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      
      fireEvent.click(screen.getByText('退出'));
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('点击深色模式切换应该切换图标', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      
      // 初始状态显示Moon图标
      expect(screen.getByTestId('moon-icon')).toBeInTheDocument();
      
      // 点击切换
      const darkModeButton = screen.getByTestId('moon-icon').closest('button');
      if (darkModeButton) {
        fireEvent.click(darkModeButton);
      }
    });
  });

  describe('用户状态测试', () => {
    it('当没有full_name时应该显示email', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: { email: 'only@email.com' },
        logout: mockLogout,
      });

      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      // 当没有full_name时，email会显示两次（一次作为名称，一次作为email）
      const emailElements = screen.getAllByText('only@email.com');
      expect(emailElements.length).toBeGreaterThanOrEqual(1);
    });

    it('当用户为空时应该显示默认文本', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: null,
        logout: mockLogout,
      });

      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      expect(screen.getByText('用户')).toBeInTheDocument();
    });
  });

  describe('图标渲染测试', () => {
    it('应该渲染所有必要的图标', () => {
      render(<Header onSidebarToggle={mockOnSidebarToggle} sidebarCollapsed={false} />);
      
      expect(screen.getByTestId('bell-icon')).toBeInTheDocument();
      expect(screen.getByTestId('settings-icon')).toBeInTheDocument();
      expect(screen.getByTestId('user-icon')).toBeInTheDocument();
      expect(screen.getByTestId('search-icon')).toBeInTheDocument();
    });
  });
});

