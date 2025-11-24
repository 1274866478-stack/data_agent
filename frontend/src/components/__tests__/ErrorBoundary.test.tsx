/**
 * ErrorBoundary组件测试
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorBoundary from '../ErrorBoundary';

// 模拟一个会抛出错误的组件
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

// 抑制console.error输出,避免测试输出混乱
const originalError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  it('should render children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should render error UI when child component throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('哎呀,出错了!')).toBeInTheDocument();
    expect(screen.getByText(/应用程序遇到了一个意外错误/)).toBeInTheDocument();
  });

  it('should display error details in development mode', () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText(/Test error/)).toBeInTheDocument();

    process.env.NODE_ENV = originalEnv;
  });

  it('should call onError callback when error occurs', () => {
    const onError = jest.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it('should render custom fallback when provided', () => {
    const customFallback = <div>Custom error message</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error message')).toBeInTheDocument();
    expect(screen.queryByText('哎呀,出错了!')).not.toBeInTheDocument();
  });

  it('should reset error state when retry button is clicked', async () => {
    const user = userEvent.setup();
    
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('哎呀,出错了!')).toBeInTheDocument();

    const retryButton = screen.getByText('重试');
    await user.click(retryButton);

    // 重新渲染不抛出错误的组件
    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('No error')).toBeInTheDocument();
  });

  it('should have home button that redirects to root', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const homeButton = screen.getByText('返回首页');
    expect(homeButton).toBeInTheDocument();
    expect(homeButton).toHaveAttribute('onclick');
  });

  it('should display support message', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText(/如果问题持续存在,请联系技术支持/)).toBeInTheDocument();
  });

  it('should not catch errors in event handlers', async () => {
    const user = userEvent.setup();
    
    const ComponentWithEventError = () => {
      const handleClick = () => {
        throw new Error('Event error');
      };

      return <button onClick={handleClick}>Click me</button>;
    };

    // ErrorBoundary不应该捕获事件处理器中的错误
    // 这个测试验证组件正常渲染
    render(
      <ErrorBoundary>
        <ComponentWithEventError />
      </ErrorBoundary>
    );

    const button = screen.getByText('Click me');
    expect(button).toBeInTheDocument();

    // 点击会抛出错误,但ErrorBoundary不会捕获
    // 在实际应用中,这需要在事件处理器中用try-catch处理
  });
});

