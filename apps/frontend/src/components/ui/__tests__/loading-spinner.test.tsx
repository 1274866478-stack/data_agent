/**
 * LoadingSpinner组件单元测试
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../loading-spinner';

describe('LoadingSpinner', () => {
  describe('渲染测试', () => {
    it('应该正确渲染加载指示器', () => {
      const { container } = render(<LoadingSpinner />);
      const spinner = container.firstChild;
      expect(spinner).toBeInTheDocument();
      expect(spinner).toHaveClass('animate-spin');
    });
  });

  describe('尺寸测试', () => {
    it('默认应该是md尺寸', () => {
      const { container } = render(<LoadingSpinner />);
      const spinner = container.firstChild;
      expect(spinner).toHaveClass('h-6', 'w-6');
    });

    it('应该应用sm尺寸', () => {
      const { container } = render(<LoadingSpinner size="sm" />);
      const spinner = container.firstChild;
      expect(spinner).toHaveClass('h-4', 'w-4');
    });

    it('应该应用md尺寸', () => {
      const { container } = render(<LoadingSpinner size="md" />);
      const spinner = container.firstChild;
      expect(spinner).toHaveClass('h-6', 'w-6');
    });

    it('应该应用lg尺寸', () => {
      const { container } = render(<LoadingSpinner size="lg" />);
      const spinner = container.firstChild;
      expect(spinner).toHaveClass('h-8', 'w-8');
    });
  });

  describe('样式测试', () => {
    it('应该有正确的基础样式', () => {
      const { container } = render(<LoadingSpinner />);
      const spinner = container.firstChild;
      expect(spinner).toHaveClass('rounded-full');
      expect(spinner).toHaveClass('border-2');
      expect(spinner).toHaveClass('border-primary');
      expect(spinner).toHaveClass('border-t-transparent');
    });

    it('应该合并自定义className', () => {
      const { container } = render(<LoadingSpinner className="my-custom-class" />);
      const spinner = container.firstChild;
      expect(spinner).toHaveClass('my-custom-class');
      expect(spinner).toHaveClass('animate-spin');
    });
  });
});

