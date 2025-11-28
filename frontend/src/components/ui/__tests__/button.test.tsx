/**
 * Button组件单元测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../button';

describe('Button', () => {
  describe('渲染测试', () => {
    it('应该正确渲染按钮文本', () => {
      render(<Button>点击我</Button>);
      expect(screen.getByRole('button', { name: '点击我' })).toBeInTheDocument();
    });

    it('应该正确渲染children内容', () => {
      render(
        <Button>
          <span data-testid="icon">🔥</span>
          按钮
        </Button>
      );
      expect(screen.getByTestId('icon')).toBeInTheDocument();
      expect(screen.getByText('按钮')).toBeInTheDocument();
    });
  });

  describe('变体测试', () => {
    it('应该应用default变体样式', () => {
      render(<Button variant="default">Default</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-primary');
    });

    it('应该应用destructive变体样式', () => {
      render(<Button variant="destructive">删除</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-destructive');
    });

    it('应该应用outline变体样式', () => {
      render(<Button variant="outline">Outline</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('border');
    });

    it('应该应用ghost变体样式', () => {
      render(<Button variant="ghost">Ghost</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:bg-accent');
    });

    it('应该应用link变体样式', () => {
      render(<Button variant="link">Link</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('underline-offset-4');
    });
  });

  describe('尺寸测试', () => {
    it('应该应用default尺寸', () => {
      render(<Button size="default">Default Size</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-9');
    });

    it('应该应用sm尺寸', () => {
      render(<Button size="sm">Small</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-8');
    });

    it('应该应用lg尺寸', () => {
      render(<Button size="lg">Large</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-10');
    });

    it('应该应用icon尺寸', () => {
      render(<Button size="icon">🔍</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('w-9');
    });
  });

  describe('交互测试', () => {
    it('点击时应该调用onClick处理函数', () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>点击</Button>);

      fireEvent.click(screen.getByRole('button'));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('禁用状态下不应该响应点击', () => {
      const handleClick = jest.fn();
      render(<Button disabled onClick={handleClick}>禁用</Button>);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      fireEvent.click(button);
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('禁用状态应该有正确的样式', () => {
      render(<Button disabled>禁用</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('disabled:pointer-events-none');
      expect(button).toHaveClass('disabled:opacity-50');
    });
  });

  describe('asChild属性测试', () => {
    it('当asChild为true时应该渲染为Slot', () => {
      render(
        <Button asChild>
          <a href="/test">链接按钮</a>
        </Button>
      );
      const link = screen.getByRole('link', { name: '链接按钮' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/test');
    });
  });

  describe('自定义className测试', () => {
    it('应该合并自定义className', () => {
      render(<Button className="my-custom-class">自定义</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('my-custom-class');
    });
  });

  describe('ref转发测试', () => {
    it('应该正确转发ref', () => {
      const ref = React.createRef<HTMLButtonElement>();
      render(<Button ref={ref}>Ref Test</Button>);
      expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    });
  });
});

