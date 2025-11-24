/**
 * MessageList组件测试
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageList } from '../MessageList'
import { useChatStore } from '@/store/chatStore'

// Mock聊天store
jest.mock('@/store/chatStore')

// Mock Markdown组件
jest.mock('@/components/ui/markdown', () => {
  return function MockMarkdown({ content, className }: { content: string; className?: string }) {
    return <div data-testid="markdown" className={className}>{content}</div>
  }
})

const mockUseChatStore = useChatStore as jest.MockedFunction<typeof useChatStore>

describe('MessageList', () => {
  const mockDeleteMessage = jest.fn()

  const defaultMockStore = {
    currentSession: null,
    deleteMessage: mockDeleteMessage,
    isLoading: false,
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseChatStore.mockReturnValue(defaultMockStore as any)
  })

  it('should render empty state when no messages', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: [] },
    } as any)

    render(<MessageList />)

    expect(screen.getByText('开始对话')).toBeInTheDocument()
    expect(screen.getByText(/我是您的AI助手/)).toBeInTheDocument()
    expect(screen.getByText('我的数据有哪些来源？')).toBeInTheDocument()
    expect(screen.getByText('分析最近的销售趋势')).toBeInTheDocument()
  })

  it('should render user messages correctly', () => {
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: '你好，AI助手',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    expect(screen.getByText('你好，AI助手')).toBeInTheDocument()
    expect(screen.getByText('10:00')).toBeInTheDocument()
  })

  it('should render assistant messages with markdown', () => {
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'assistant' as const,
        content: '# 标题\n\n这是**粗体**文本',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    expect(screen.getByTestId('markdown')).toBeInTheDocument()
    expect(screen.getByText('# 标题\n\n这是**粗体**文本')).toBeInTheDocument()
    expect(screen.getByText('10:00')).toBeInTheDocument()
  })

  it('should render system messages correctly', () => {
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'system' as const,
        content: '系统消息：连接已断开',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'error' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    expect(screen.getByText('系统消息：连接已断开')).toBeInTheDocument()
    // 系统消息不应该有删除按钮
    expect(screen.queryByText('删除')).not.toBeInTheDocument()
  })

  it('should display message status indicators correctly', () => {
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: '发送中消息',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sending' as const,
      },
      {
        id: 'msg-2',
        role: 'user' as const,
        content: '已发送消息',
        timestamp: new Date('2024-01-01T10:01:00'),
        status: 'sent' as const,
      },
      {
        id: 'msg-3',
        role: 'user' as const,
        content: '错误消息',
        timestamp: new Date('2024-01-01T10:02:00'),
        status: 'error' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    expect(screen.getByText('发送中')).toBeInTheDocument()
    expect(screen.getByText('发送中')).toBeInTheDocument()
  })

  it('should display message metadata when available', () => {
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'assistant' as const,
        content: '这是回答',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
        metadata: {
          sources: ['数据源1', '数据源2'],
          confidence: 0.85,
          reasoning: '这是推理过程',
        },
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    expect(screen.getByText('数据来源：')).toBeInTheDocument()
    expect(screen.getByText('• 数据源1')).toBeInTheDocument()
    expect(screen.getByText('• 数据源2')).toBeInTheDocument()
    expect(screen.getByText('置信度：85%')).toBeInTheDocument()
    expect(screen.getByText('推理过程')).toBeInTheDocument()
  })

  it('should delete message when delete button is clicked', async () => {
    const user = userEvent.setup()
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: '要删除的消息',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    // 悬停以显示删除按钮
    const messageContainer = screen.getByText('要删除的消息').closest('div')
    fireEvent.mouseEnter(messageContainer!)

    const deleteButton = await screen.findByText('删除')
    await user.click(deleteButton)

    expect(mockDeleteMessage).toHaveBeenCalledWith('msg-1')
  })

  it('should show loading indicator when isLoading is true', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      isLoading: true,
    } as any)

    render(<MessageList />)

    expect(screen.getByText('AI 正在思考中...')).toBeInTheDocument()
  })

  it('should allow clicking suggestion buttons in empty state', async () => {
    const user = userEvent.setup()

    // Mock textarea element
    const mockTextarea = {
      value: '',
      dispatchEvent: jest.fn(),
    }
    Object.defineProperty(document, 'querySelector', {
      value: jest.fn(() => mockTextarea),
    })

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: [] },
      isLoading: false,
    } as any)

    render(<MessageList />)

    const suggestionButton = screen.getByText('我的数据有哪些来源？')
    await user.click(suggestionButton)

    expect(mockTextarea.dispatchEvent).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'input', bubbles: true })
    )
  })

  it('should disable suggestion buttons when loading', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: [] },
      isLoading: true,
    } as any)

    render(<MessageList />)

    const suggestionButton = screen.getByText('我的数据有哪些来源？')
    expect(suggestionButton).toBeDisabled()
  })

  it('should render multiple messages in correct order', () => {
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: '第一条消息',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
      },
      {
        id: 'msg-2',
        role: 'assistant' as const,
        content: '第二条消息',
        timestamp: new Date('2024-01-01T10:01:00'),
        status: 'sent' as const,
      },
      {
        id: 'msg-3',
        role: 'user' as const,
        content: '第三条消息',
        timestamp: new Date('2024-01-01T10:02:00'),
        status: 'sent' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    const messages = screen.getAllByText(/第.*条消息/)
    expect(messages).toHaveLength(3)
    expect(messages[0]).toHaveTextContent('第一条消息')
    expect(messages[1]).toHaveTextContent('第二条消息')
    expect(messages[2]).toHaveTextContent('第三条消息')
  })

  it('should handle long messages with proper styling', () => {
    const longMessage = 'a'.repeat(1000)
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: longMessage,
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    expect(screen.getByText(longMessage)).toBeInTheDocument()
  })

  it('should have correct accessibility attributes', () => {
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: '用户消息',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    render(<MessageList />)

    // 检查删除按钮有正确的屏幕阅读器标签
    const deleteButton = screen.getByRole('button', { name: /删除/ })
    expect(deleteButton).toBeInTheDocument()
  })

  it('should scroll to bottom when new messages are added', () => {
    const { rerender } = render(<MessageList />)

    // 初始状态没有消息
    expect(screen.getByText('开始对话')).toBeInTheDocument()

    // 添加消息后应该重新渲染
    const mockMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: '新消息',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent' as const,
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: { messages: mockMessages },
    } as any)

    rerender(<MessageList />)

    expect(screen.getByText('新消息')).toBeInTheDocument()
  })
})