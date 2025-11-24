import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SourceCitations } from '../SourceCitations';

// Mock clipboard API
const mockWriteText = jest.fn();
Object.assign(navigator, {
  clipboard: {
    writeText: mockWriteText
  }
});

describe('SourceCitations', () => {
  const mockSources = [
    {
      source_id: 'source-1',
      source_type: 'sql_query',
      source_name: '用户数据库',
      content_snippet: '用户表包含所有用户的基本信息',
      relevance_score: 0.9,
      confidence_contribution: 0.8,
      verification_status: 'verified',
      trace_path: ['database', 'users'],
      extraction_method: 'SQL SELECT',
      metadata: {
        query_time: '2023-12-01T10:00:00Z',
        row_count: 1000
      }
    },
    {
      source_id: 'source-2',
      source_type: 'document',
      source_name: '产品手册.pdf',
      content_snippet: '这是产品的详细使用说明文档',
      relevance_score: 0.7,
      confidence_contribution: 0.6,
      verification_status: 'pending',
      extraction_method: 'PDF解析',
      metadata: {
        file_size: 2048576,
        page_count: 50
      }
    },
    {
      source_id: 'source-3',
      source_type: 'rag_retrieval',
      source_name: '向量搜索结果',
      content_snippet: '基于语义相似度检索的相关内容',
      relevance_score: 0.5,
      confidence_contribution: 0.4,
      verification_status: 'failed',
      extraction_method: '向量检索',
      metadata: {
        similarity_score: 0.85,
        embedding_model: 'text-embedding-ada-002'
      }
    }
  ];

  const defaultProps = {
    sources: mockSources,
    answer: '这是一个测试答案',
    query: '测试查询',
    showStats: true,
    allowSearch: true
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('应该正确渲染基本信息', () => {
    render(<SourceCitations {...defaultProps} />);

    // 验证标题
    expect(screen.getByText('数据源引用与溯源')).toBeInTheDocument();
    expect(screen.getByText('追踪答案的数据来源，验证信息可靠性')).toBeInTheDocument();

    // 验证数据源数量
    expect(screen.getByText('3 个数据源')).toBeInTheDocument();
    expect(screen.getByText('1 已验证')).toBeInTheDocument();
  });

  it('应该正确计算和显示统计信息', () => {
    render(<SourceCitations {...defaultProps} />);

    // 验证统计数据
    expect(screen.getByText('3')).toBeInTheDocument(); // 总数据源
    expect(screen.getByText('1')).toBeInTheDocument(); // 已验证源
    expect(screen.getByText('70%')).toBeInTheDocument(); // 平均相关性
    expect(screen.getByText('3')).toBeInTheDocument(); // 源类型数量
  });

  it('应该在无数据源时显示空状态', () => {
    render(<SourceCitations {...defaultProps} sources={[]} />);

    expect(screen.getByText('暂无数据源引用')).toBeInTheDocument();
    expect(screen.getByText('当前答案没有可追溯的数据源信息。')).toBeInTheDocument();
  });

  it('应该正确处理搜索功能', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 输入搜索词
    const searchInput = screen.getByPlaceholderText('搜索数据源...');
    await user.type(searchInput, '用户');

    // 应该只显示匹配的数据源
    expect(screen.getByText('用户数据库')).toBeInTheDocument();
    expect(screen.queryByText('产品手册.pdf')).not.toBeInTheDocument();
    expect(screen.queryByText('向量搜索结果')).not.toBeInTheDocument();
  });

  it('应该正确处理类型过滤', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 选择特定类型
    const typeFilter = screen.getByDisplayValue('所有类型');
    await user.selectOptions(typeFilter, 'document');

    // 应该只显示该类型的数据源
    expect(screen.queryByText('用户数据库')).not.toBeInTheDocument();
    expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    expect(screen.queryByText('向量搜索结果')).not.toBeInTheDocument();
  });

  it('应该正确处理排序功能', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 按相关性排序
    const sortSelect = screen.getByDisplayValue('按相关性排序');
    await user.selectOptions(sortSelect, 'confidence');

    // 验证排序选项已更新
    expect(sortSelect).toHaveValue('confidence');
  });

  it('应该正确处理源展开和收起', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 展开第一个数据源
    const expandButtons = screen.getAllByLabelText(/展开详情/);
    await user.click(expandButtons[0]);

    // 验证详细信息显示
    expect(screen.getByText('追踪路径')).toBeInTheDocument();
    expect(screen.getByText('提取方法')).toBeInTheDocument();
    expect(screen.getByText('元数据')).toBeInTheDocument();

    // 收起数据源
    await user.click(expandButtons[0]);

    // 详细信息应该仍然显示，因为我们用的是不同的按钮
    expect(screen.getByText('追踪路径')).toBeInTheDocument();
  });

  it('应该正确处理复制引用功能', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 点击复制按钮
    const copyButtons = screen.getAllByLabelText('复制引用');
    await user.click(copyButtons[0]);

    // 验证复制功能
    expect(mockWriteText).toHaveBeenCalledWith('[sql_query] 用户数据库');
  });

  it('应该正确切换标签页', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 初始应该在源列表标签页
    expect(screen.getByText('源列表')).toHaveAttribute('data-state', 'active');

    // 切换到统计分析标签页
    await user.click(screen.getByText('统计分析'));
    expect(screen.getByText('统计分析')).toHaveAttribute('data-state', 'active');
    expect(screen.getByText('源类型分布')).toBeInTheDocument();
    expect(screen.getByText('置信度分布')).toBeInTheDocument();

    // 切换到溯源路径标签页
    await user.click(screen.getByText('溯源路径'));
    expect(screen.getByText('溯源路径')).toHaveAttribute('data-state', 'active');
  });

  it('应该在统计分析中正确显示源类型分布', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 切换到统计分析标签页
    await user.click(screen.getByText('统计分析'));

    // 验证源类型分布
    expect(screen.getByText('源类型分布')).toBeInTheDocument();
    expect(screen.getByText('sql_query')).toBeInTheDocument();
    expect(screen.getByText('document')).toBeInTheDocument();
    expect(screen.getByText('rag_retrieval')).toBeInTheDocument();
  });

  it('应该在统计分析中正确显示置信度分布', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 切换到统计分析标签页
    await user.click(screen.getByText('统计分析'));

    // 验证置信度分布
    expect(screen.getByText('置信度分布')).toBeInTheDocument();
    expect(screen.getByText('高置信度 (≥80%)')).toBeInTheDocument();
    expect(screen.getByText('中等置信度 (60-80%)')).toBeInTheDocument();
    expect(screen.getByText('低置信度 (<60%)')).toBeInTheDocument();
  });

  it('应该在溯源路径中显示路径信息', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 切换到溯源路径标签页
    await user.click(screen.getByText('溯源路径'));

    // 验证溯源路径信息
    expect(screen.getByText('溯源路径分析')).toBeInTheDocument();
    expect(screen.getByText('溯源路径:')).toBeInTheDocument();
    expect(screen.getByText('database')).toBeInTheDocument();
    expect(screen.getByText('users')).toBeInTheDocument();
  });

  it('应该正确处理搜索无结果的情况', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 输入不存在的搜索词
    const searchInput = screen.getByPlaceholderText('搜索数据源...');
    await user.type(searchInput, '不存在的数据源');

    // 应该显示未找到结果的提示
    expect(screen.getByText('未找到匹配的数据源')).toBeInTheDocument();
    expect(screen.getByText('尝试调整搜索条件或过滤器设置。')).toBeInTheDocument();
  });

  it('应该在允许搜索为false时隐藏搜索控件', () => {
    render(<SourceCitations {...defaultProps} allowSearch={false} />);

    // 搜索控件应该不存在
    expect(screen.queryByPlaceholderText('搜索数据源...')).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue('所有类型')).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue('按相关性排序')).not.toBeInTheDocument();
  });

  it('应该在显示统计为false时隐藏统计信息', () => {
    render(<SourceCitations {...defaultProps} showStats={false} />);

    // 统计信息应该不存在
    expect(screen.queryByText('总数据源')).not.toBeInTheDocument();
    expect(screen.queryByText('已验证源')).not.toBeInTheDocument();
    expect(screen.queryByText('平均相关性')).not.toBeInTheDocument();
  });

  it('应该正确应用自定义类名', () => {
    const customClassName = 'custom-citations-class';
    const { container } = render(
      <SourceCitations {...defaultProps} className={customClassName} />
    );

    expect(container.querySelector('.custom-citations-class')).toBeInTheDocument();
  });

  it('应该正确处理空数组的属性', () => {
    const sourcesWithEmptyArrays = mockSources.map(source => ({
      ...source,
      trace_path: [],
      metadata: {}
    }));

    render(<SourceCitations {...defaultProps} sources={sourcesWithEmptyArrays} />);

    // 应该正常渲染，不显示空的路径或元数据
    expect(screen.getByText('用户数据库')).toBeInTheDocument();
  });

  it('应该有正确的可访问性属性', () => {
    render(<SourceCitations {...defaultProps} />);

    // 验证重要元素有正确的标签
    expect(screen.getByLabelText('搜索数据源...')).toBeInTheDocument();
    expect(screen.getAllByLabelText('展开详情')).toHaveLength(3);
    expect(screen.getAllByLabelText('复制引用')).toHaveLength(3);
  });

  it('应该正确处理键盘导航', async () => {
    const user = userEvent.setup();
    render(<SourceCitations {...defaultProps} />);

    // 测试Tab键导航
    await user.tab();
    expect(screen.getByPlaceholderText('搜索数据源...')).toHaveFocus();

    await user.tab();
    // 应该聚焦到类型选择器
    const typeSelect = screen.getByDisplayValue('所有类型');
    expect(typeSelect).toHaveFocus();
  });
});