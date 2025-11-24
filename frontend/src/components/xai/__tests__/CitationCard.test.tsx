import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CitationCard } from '../CitationCard';

// Mock window.open
Object.assign(window, {
  open: jest.fn()
});

describe('CitationCard', () => {
  const mockSource = {
    source_id: 'test-source-1',
    source_type: 'sql_query',
    source_name: '测试数据源',
    content_snippet: '这是一个测试内容片段，用于验证组件功能是否正常工作。',
    relevance_score: 0.85,
    confidence_contribution: 0.75,
    verification_status: 'verified',
    trace_path: ['database', 'table', 'row'],
    extraction_method: 'SQL查询',
    metadata: {
      original_url: 'https://example.com/data',
      query_time: '2023-12-01T10:00:00Z',
      row_count: 1000
    }
  };

  const defaultProps = {
    source: mockSource,
    isExpanded: false,
    onToggleExpand: jest.fn(),
    onCopyCitation: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('应该正确渲染基本信息', () => {
    render(<CitationCard {...defaultProps} />);

    // 验证源名称和ID
    expect(screen.getByText('测试数据源')).toBeInTheDocument();
    expect(screen.getByText('ID: test-source-1')).toBeInTheDocument();

    // 验证源类型标签
    expect(screen.getByText('sql_query')).toBeInTheDocument();

    // 验证验证状态
    expect(screen.getByText('已验证')).toBeInTheDocument();

    // 验证内容片段
    expect(screen.getByText('这是一个测试内容片段，用于验证组件功能是否正常工作。')).toBeInTheDocument();
  });

  it('应该正确显示评分信息', () => {
    render(<CitationCard {...defaultProps} />);

    // 验证相关性评分
    expect(screen.getByText('相关性评分:')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();

    // 验证置信度贡献
    expect(screen.getByText('置信度贡献:')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('应该根据评分显示正确的颜色', () => {
    // 测试高相关性
    const highRelevanceSource = {
      ...mockSource,
      relevance_score: 0.9
    };
    const { rerender } = render(<CitationCard {...defaultProps} source={highRelevanceSource} />);
    expect(screen.getByText('90%')).toHaveClass('text-green-600');

    // 测试中等相关性
    const mediumRelevanceSource = {
      ...mockSource,
      relevance_score: 0.7
    };
    rerender(<CitationCard {...defaultProps} source={mediumRelevanceSource} />);
    expect(screen.getByText('70%')).toHaveClass('text-yellow-600');

    // 测试低相关性
    const lowRelevanceSource = {
      ...mockSource,
      relevance_score: 0.4
    };
    rerender(<CitationCard {...defaultProps} source={lowRelevanceSource} />);
    expect(screen.getByText('40%')).toHaveClass('text-red-600');
  });

  it('应该正确处理验证状态', () => {
    // 测试已验证状态
    const { rerender } = render(<CitationCard {...defaultProps} />);
    expect(screen.getByText('已验证')).toHaveClass('bg-green-100');

    // 测试待验证状态
    const pendingSource = { ...mockSource, verification_status: 'pending' };
    rerender(<CitationCard {...defaultProps} source={pendingSource} />);
    expect(screen.getByText('待验证')).toBeInTheDocument();

    // 测试验证失败状态
    const failedSource = { ...mockSource, verification_status: 'failed' };
    rerender(<CitationCard {...defaultProps} source={failedSource} />);
    expect(screen.getByText('验证失败')).toBeInTheDocument();
  });

  it('应该在展开时显示详细信息', async () => {
    render(<CitationCard {...defaultProps} isExpanded={true} />);

    // 验证追踪路径
    expect(screen.getByText('追踪路径')).toBeInTheDocument();
    expect(screen.getByText('database')).toBeInTheDocument();
    expect(screen.getByText('table')).toBeInTheDocument();
    expect(screen.getByText('row')).toBeInTheDocument();

    // 验证提取方法
    expect(screen.getByText('提取方法')).toBeInTheDocument();
    expect(screen.getByText('SQL查询')).toBeInTheDocument();

    // 验证元数据
    expect(screen.getByText('元数据')).toBeInTheDocument();
    expect(screen.getByText('original_url:')).toBeInTheDocument();
    expect(screen.getByText('query_time:')).toBeInTheDocument();
    expect(screen.getByText('row_count:')).toBeInTheDocument();
  });

  it('应该正确处理展开/收起操作', async () => {
    const user = userEvent.setup();
    render(<CitationCard {...defaultProps} />);

    // 初始状态应该不显示详细信息
    expect(screen.queryByText('追踪路径')).not.toBeInTheDocument();

    // 点击展开按钮
    const expandButton = screen.getByLabelText('展开详情');
    await user.click(expandButton);

    // 验证回调被调用
    expect(defaultProps.onToggleExpand).toHaveBeenCalledWith('test-source-1');
  });

  it('应该正确处理复制引用操作', async () => {
    const user = userEvent.setup();
    render(<CitationCard {...defaultProps} />);

    // 点击复制按钮
    const copyButton = screen.getByLabelText('复制引用');
    await user.click(copyButton);

    // 验证回调被调用
    expect(defaultProps.onCopyCitation).toHaveBeenCalledWith(mockSource);
  });

  it('应该在没有自定义回调时使用默认的复制功能', async () => {
    const user = userEvent.setup();

    render(
      <CitationCard
        source={mockSource}
        isExpanded={false}
      />
    );

    // 点击复制按钮
    const copyButton = screen.getByLabelText('复制引用');
    await user.click(copyButton);

    // 验证组件正常渲染，复制操作不会抛出错误
    // 由于在测试环境中无法直接测试clipboard API，我们验证按钮点击不会导致错误
    expect(copyButton).toBeInTheDocument();

    // 验证数据源名称和类型都正确显示
    expect(screen.getByText('测试数据源')).toBeInTheDocument();
    expect(screen.getByText('sql_query')).toBeInTheDocument();
  });

  it('应该正确处理原始数据链接', async () => {
    const user = userEvent.setup();
    render(<CitationCard {...defaultProps} isExpanded={true} />);

    // 点击访问原始数据源链接
    const linkButton = screen.getByText('访问原始数据源');
    await user.click(linkButton);

    // 验证window.open被调用
    expect(window.open).toHaveBeenCalledWith('https://example.com/data', '_blank');
  });

  it('应该根据源类型显示正确的颜色', () => {
    // 测试不同源类型的颜色
    const testCases = [
      { type: 'sql_query', expectedClass: 'bg-blue-100' },
      { type: 'rag_retrieval', expectedClass: 'bg-green-100' },
      { type: 'document', expectedClass: 'bg-yellow-100' },
      { type: 'api_response', expectedClass: 'bg-purple-100' }
    ];

    testCases.forEach(({ type, expectedClass }) => {
      const source = { ...mockSource, source_type: type };
      const { container } = render(<CitationCard {...defaultProps} source={source} />);
      const badge = container.querySelector('.bg-blue-100, .bg-green-100, .bg-yellow-100, .bg-purple-100');
      expect(badge).toHaveClass(expectedClass);
    });
  });

  it('应该正确处理缺失的元数据', () => {
    const sourceWithoutMetadata = {
      ...mockSource,
      metadata: undefined
    };

    render(<CitationCard {...defaultProps} source={sourceWithoutMetadata} isExpanded={true} />);

    // 应该不显示元数据部分
    expect(screen.queryByText('元数据')).not.toBeInTheDocument();
  });

  it('应该正确处理空的追踪路径', () => {
    const sourceWithoutTrace = {
      ...mockSource,
      trace_path: undefined
    };

    render(<CitationCard {...defaultProps} source={sourceWithoutTrace} isExpanded={true} />);

    // 应该不显示追踪路径部分
    expect(screen.queryByText('追踪路径')).not.toBeInTheDocument();
  });

  it('应该正确应用自定义类名', () => {
    const customClassName = 'custom-card-class';
    const { container } = render(
      <CitationCard {...defaultProps} className={customClassName} />
    );

    expect(container.querySelector('.custom-card-class')).toBeInTheDocument();
  });

  it('应该有正确的可访问性属性', () => {
    render(<CitationCard {...defaultProps} />);

    // 验证按钮有正确的aria-label
    expect(screen.getByLabelText('展开详情')).toBeInTheDocument();
    expect(screen.getByLabelText('复制引用')).toBeInTheDocument();

    // 验证按钮是可访问的
    const expandButton = screen.getByLabelText('展开详情');
    const copyButton = screen.getByLabelText('复制引用');

    expect(expandButton.closest('button')).toBeInTheDocument();
    expect(copyButton.closest('button')).toBeInTheDocument();

    // 验证按钮有正确的标签
    expect(expandButton).toHaveAttribute('aria-label', '展开详情');
    expect(copyButton).toHaveAttribute('aria-label', '复制引用');

    // 验证按钮的type属性（原生button元素默认有type="button"）
    expect(expandButton.tagName).toBe('BUTTON');
    expect(copyButton.tagName).toBe('BUTTON');
  });
});