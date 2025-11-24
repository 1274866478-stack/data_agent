/**
 * 搜索面板组件测试
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchPanel } from '../SearchPanel'
import { useChatStore } from '@/store/chatStore'

// Mock 子组件
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, className, ...props }: any) => (
    <button onClick={onClick} className={className} {...props}>
      {children}
    </button>
  )
}))

jest.mock('@/components/ui/input', () => ({
  Input: ({ value, onChange, placeholder, className, ...props }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={className}
      {...props}
    />
  )
}))

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardContent: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardHeader: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardTitle: ({ children, className }: any) => <div className={className}>{children}</div>
}))

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className }: any) => <span className={className}>{children}</span>
}))

jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, className }: any) => <div className={className}>{children}</div>
}))

// Mock 搜索服务
jest.mock('@/services/searchService', () => ({
  searchSessions: jest.fn(),
  getSearchSuggestions: jest.fn(),
  getPopularKeywords: jest.fn(),
  groupResultsBySession: jest.fn(),
  SearchResult: {} as any,
  SearchOptions: {} as any
}))

// Mock store
jest.mock('@/store/chatStore', () => ({
  useChatStore: jest.fn()
}))

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Search: ({ className }: any) => <div className={className}>SearchIcon</div>,
  Clock: ({ className }: any) => <div className={className}>ClockIcon</div>,
  TrendingUp: ({ className }: any) => <div className={className}>TrendingUpIcon</div>,
  X: ({ className }: any) => <div className={className}>XIcon</div>
}))

import { searchSessions, getSearchSuggestions, getPopularKeywords, groupResultsBySession } from '@/services/searchService'

const mockSearchSessions = searchSessions as jest.MockedFunction<typeof searchSessions>
const mockGetSearchSuggestions = getSearchSuggestions as jest.MockedFunction<typeof getSearchSuggestions>
const mockGetPopularKeywords = getPopularKeywords as jest.MockedFunction<typeof getPopularKeywords>
const mockGroupResultsBySession = groupResultsBySession as jest.MockedFunction<typeof groupResultsBySession>

// Mock 测试数据
const mockSessions = [
  {
    id: 'session-1',
    title: '数据分析讨论',
    createdAt: new Date(),
    updatedAt: new Date(),
    messages: [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: '请帮我分析销售数据的趋势',
        timestamp: new Date(),
        status: 'sent' as const
      }
    ],
    isActive: true
  }
]

describe('SearchPanel', () => {
  const mockOnClose = jest.fn()
  const mockOnResultClick = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()

    // Mock store
    ;(useChatStore as jest.Mock).mockReturnValue({
      sessions: mockSessions
    })

    // Mock 搜索服务
    mockGetPopularKeywords.mockReturnValue([
      { keyword: '数据分析', count: 5 },
      { keyword: '销售趋势', count: 3 }
    ])

    mockSearchSessions.mockReturnValue({
      results: [],
      stats: {
        totalResults: 0,
        sessionResults: 0,
        messageResults: 0,
        searchTime: 10
      }
    })

    mockGetSearchSuggestions.mockReturnValue([])
    mockGroupResultsBySession.mockReturnValue({})
  })

  it('当 isOpen 为 false 时不应该渲染', () => {
    render(
      <SearchPanel
        isOpen={false}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    expect(screen.queryByText('搜索对话')).not.toBeInTheDocument()
  })

  it('当 isOpen 为 true 时应该正确渲染', () => {
    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    expect(screen.getByText('搜索对话')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('搜索对话内容...')).toBeInTheDocument()
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('会话')).toBeInTheDocument()
    expect(screen.getByText('消息')).toBeInTheDocument()
    expect(screen.getByText('模糊搜索')).toBeInTheDocument()
    expect(screen.getByText('显示上下文')).toBeInTheDocument()
  })

  it('应该显示热门关键词', () => {
    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    expect(screen.getByText('热门搜索')).toBeInTheDocument()
    expect(screen.getByText('数据分析')).toBeInTheDocument()
    expect(screen.getByText('销售趋势')).toBeInTheDocument()
  })

  it('应该调用 onClose 当点击关闭按钮时', async () => {
    const user = userEvent.setup()

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const closeButton = screen.getAllByText('XIcon')[0] // 关闭按钮
    await user.click(closeButton)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('应该执行搜索当输入查询时', async () => {
    const user = userEvent.setup()

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数据')

    // 等待防抖完成
    await waitFor(() => {
      expect(mockSearchSessions).toHaveBeenCalledWith(
        mockSessions,
        expect.objectContaining({
          query: '数据',
          type: 'all',
          fuzzySearch: true,
          includeContext: false,
          limit: 20
        })
      )
    }, { timeout: 400 })
  })

  it('应该显示搜索建议', async () => {
    const user = userEvent.setup()

    mockGetSearchSuggestions.mockReturnValue(['数据分析', '数据库', '数据挖掘'])

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数')
    await user.click(searchInput) // 触发焦点

    await waitFor(() => {
      expect(screen.getByText('搜索建议')).toBeInTheDocument()
      expect(screen.getByText('数据分析')).toBeInTheDocument()
      expect(screen.getByText('数据库')).toBeInTheDocument()
      expect(screen.getByText('数据挖掘')).toBeInTheDocument()
    })
  })

  it('应该点击建议项时填充搜索框', async () => {
    const user = userEvent.setup()

    mockGetSearchSuggestions.mockReturnValue(['数据分析'])

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数')
    await user.click(searchInput)

    await waitFor(() => {
      expect(screen.getByText('数据分析')).toBeInTheDocument()
    })

    const suggestionButton = screen.getByText('数据分析')
    await user.click(suggestionButton)

    expect(searchInput).toHaveValue('数据分析')
  })

  it('应该点击热门关键词时填充搜索框', async () => {
    const user = userEvent.setup()

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const keywordButton = screen.getByText('数据分析')
    await user.click(keywordButton)

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    expect(searchInput).toHaveValue('数据分析')
  })

  it('应该显示搜索结果', async () => {
    const user = userEvent.setup()

    mockSearchSessions.mockReturnValue({
      results: [
        {
          type: 'session' as const,
          sessionId: 'session-1',
          id: 'session-1',
          title: '数据分析讨论',
          content: '数据分析讨论',
          timestamp: new Date(),
          score: 100,
          highlights: ['数据分析']
        }
      ],
      stats: {
        totalResults: 1,
        sessionResults: 1,
        messageResults: 0,
        searchTime: 15
      }
    })

    mockGroupResultsBySession.mockReturnValue({
      'session-1': [
        {
          type: 'session' as const,
          sessionId: 'session-1',
          id: 'session-1',
          title: '数据分析讨论',
          content: '数据分析讨论',
          timestamp: new Date(),
          score: 100,
          highlights: ['数据分析']
        }
      ]
    })

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数据')

    await waitFor(() => {
      expect(screen.getByText(/找到 1 个结果/)).toBeInTheDocument()
      expect(screen.getByText('(1 个会话, 0 条消息)')).toBeInTheDocument()
      expect(screen.getByText('数据分析讨论')).toBeInTheDocument()
      expect(screen.getByText('1 个结果')).toBeInTheDocument()
    })
  })

  it('应该显示无结果状态', async () => {
    const user = userEvent.setup()

    mockSearchSessions.mockReturnValue({
      results: [],
      stats: {
        totalResults: 0,
        sessionResults: 0,
        messageResults: 0,
        searchTime: 5
      }
    })

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '不存在的关键词')

    await waitFor(() => {
      expect(screen.getByText('没有找到匹配的内容')).toBeInTheDocument()
      expect(screen.getByText('尝试使用不同的关键词或调整搜索选项')).toBeInTheDocument()
    })
  })

  it('应该点击搜索结果时调用 onResultClick', async () => {
    const user = userEvent.setup()

    const mockResult = {
      type: 'session' as const,
      sessionId: 'session-1',
      id: 'session-1',
      title: '数据分析讨论',
      content: '数据分析讨论',
      timestamp: new Date(),
      score: 100,
      highlights: ['数据分析']
    }

    mockSearchSessions.mockReturnValue({
      results: [mockResult],
      stats: {
        totalResults: 1,
        sessionResults: 1,
        messageResults: 0,
        searchTime: 15
      }
    })

    mockGroupResultsBySession.mockReturnValue({
      'session-1': [mockResult]
    })

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数据')

    await waitFor(() => {
      expect(screen.getByText('数据分析讨论')).toBeInTheDocument()
    })

    const resultElement = screen.getByText('数据分析讨论')
    await user.click(resultElement)

    expect(mockOnResultClick).toHaveBeenCalledWith('session-1', undefined)
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('应该切换搜索类型', async () => {
    const user = userEvent.setup()

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数据')

    await waitFor(() => {
      expect(mockSearchSessions).toHaveBeenCalledWith(
        mockSessions,
        expect.objectContaining({ type: 'all' })
      )
    }, { timeout: 400 })

    const selectElement = screen.getByDisplayValue('全部')
    await user.selectOptions(selectElement, 'sessions')

    await waitFor(() => {
      expect(mockSearchSessions).toHaveBeenCalledWith(
        mockSessions,
        expect.objectContaining({ type: 'sessions' })
      )
    })
  })

  it('应该切换模糊搜索选项', async () => {
    const user = userEvent.setup()

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数据')

    await waitFor(() => {
      expect(mockSearchSessions).toHaveBeenCalledWith(
        mockSessions,
        expect.objectContaining({ fuzzySearch: true })
      )
    }, { timeout: 400 })

    const fuzzyCheckbox = screen.getByLabelText('模糊搜索')
    await user.click(fuzzyCheckbox)

    await waitFor(() => {
      expect(mockSearchSessions).toHaveBeenCalledWith(
        mockSessions,
        expect.objectContaining({ fuzzySearch: false })
      )
    })
  })

  it('应该切换上下文选项', async () => {
    const user = userEvent.setup()

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数据')

    await waitFor(() => {
      expect(mockSearchSessions).toHaveBeenCalledWith(
        mockSessions,
        expect.objectContaining({ includeContext: false })
      )
    }, { timeout: 400 })

    const contextCheckbox = screen.getByLabelText('显示上下文')
    await user.click(contextCheckbox)

    await waitFor(() => {
      expect(mockSearchSessions).toHaveBeenCalledWith(
        mockSessions,
        expect.objectContaining({ includeContext: true })
      )
    })
  })

  it('应该清空搜索当点击清空按钮时', async () => {
    const user = userEvent.setup()

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '数据')

    // 等待输入完成
    await waitFor(() => {
      expect(searchInput).toHaveValue('数据')
    })

    // 点击清空按钮
    const clearButton = screen.getAllByText('XIcon')[1] // 清空按钮
    await user.click(clearButton)

    expect(searchInput).toHaveValue('')
  })

  it('应该显示消息类型的结果', async () => {
    const user = userEvent.setup()

    const mockMessageResult = {
      type: 'message' as const,
      sessionId: 'session-1',
      id: 'msg-1',
      title: '数据分析讨论',
      content: '请帮我分析销售数据的趋势',
      timestamp: new Date(),
      score: 90,
      highlights: ['销售数据']
    }

    mockSearchSessions.mockReturnValue({
      results: [mockMessageResult],
      stats: {
        totalResults: 1,
        sessionResults: 0,
        messageResults: 1,
        searchTime: 12
      }
    })

    mockGroupResultsBySession.mockReturnValue({
      'session-1': [mockMessageResult]
    })

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    const searchInput = screen.getByPlaceholderText('搜索对话内容...')
    await user.type(searchInput, '销售')

    await waitFor(() => {
      expect(screen.getByText('请帮我分析销售数据的趋势')).toBeInTheDocument()
      expect(screen.getByText('1 个结果')).toBeInTheDocument()
    })
  })

  it('应该处理空会话列表', () => {
    ;(useChatStore as jest.Mock).mockReturnValue({
      sessions: []
    })

    render(
      <SearchPanel
        isOpen={true}
        onClose={mockOnClose}
        onResultClick={mockOnResultClick}
      />
    )

    expect(screen.getByText('搜索对话')).toBeInTheDocument()
    expect(screen.queryByText('热门搜索')).not.toBeInTheDocument()
  })
})