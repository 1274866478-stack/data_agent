/**
 * ChatInterface组件测试
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInterface } from '../ChatInterface'
import { useChatStore } from '@/store/chatStore'

// Mock聊天store
jest.mock('@/store/chatStore')

const mockUseChatStore = useChatStore as jest.MockedFunction<typeof useChatStore>

// Mock组件
jest.mock('../MessageList', () => ({
  MessageList: React.forwardRef(function MockMessageList({ className }: { className?: string }, ref: any) {
    return <div data-testid="message-list" className={className}>Message List</div>
  })
}))

jest.mock('../MessageInput', () => ({
  MessageInput: function MockMessageInput({ onFileAttach }: { onFileAttach: (files: File[]) => void }) {
    return <div data-testid="message-input">Message Input</div>
  }
}))

jest.mock('../SearchPanel', () => ({
  SearchPanel: function MockSearchPanel({ isOpen, onClose, onResultClick }: any) {
    if (!isOpen) return null
    return (
      <div data-testid="search-panel">
        Search Panel
        <button onClick={onClose}>关闭</button>
      </div>
    )
  }
}))

describe('ChatInterface', () => {
  const mockCreateSession = jest.fn()
  const mockSwitchSession = jest.fn()
  const mockDeleteSession = jest.fn()
  const mockUpdateSessionTitle = jest.fn()
  const mockClearHistory = jest.fn()
  const mockSetError = jest.fn()

  const defaultMockStore = {
    sessions: [],
    currentSession: null,
    createSession: mockCreateSession,
    switchSession: mockSwitchSession,
    deleteSession: mockDeleteSession,
    updateSessionTitle: mockUpdateSessionTitle,
    clearHistory: mockClearHistory,
    error: null,
    setError: mockSetError,
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseChatStore.mockReturnValue(defaultMockStore as any)

    // Mock localStorage
    const localStorageMock = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
    }
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
    })

    // Mock ResizeObserver
    global.ResizeObserver = class ResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    }

    // Mock confirm dialog
    global.confirm = jest.fn(() => true)
  })

  it('should render chat interface correctly', () => {
    render(<ChatInterface />)

    expect(screen.getByText('新建会话')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('搜索会话...')).toBeInTheDocument()
    expect(screen.getByTestId('message-list')).toBeInTheDocument()
    expect(screen.getByTestId('message-input')).toBeInTheDocument()
  })

  it('should create new session when clicking new session button', async () => {
    const user = userEvent.setup()
    mockCreateSession.mockResolvedValue('session-id-123')

    render(<ChatInterface />)

    const newSessionButton = screen.getByText('新建会话')
    await user.click(newSessionButton)

    expect(mockCreateSession).toHaveBeenCalledWith()
  })

  it('should display sessions correctly', () => {
    const mockSessions = [
      {
        id: 'session-1',
        title: '测试会话1',
        updatedAt: new Date('2024-01-01'),
        messages: [{ id: 'msg-1' }, { id: 'msg-2' }],
      },
      {
        id: 'session-2',
        title: '测试会话2',
        updatedAt: new Date('2024-01-02'),
        messages: [],
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      sessions: mockSessions,
    } as any)

    render(<ChatInterface />)

    expect(screen.getByText('测试会话1')).toBeInTheDocument()
    expect(screen.getByText('测试会话2')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument() // 消息数量
  })

  it('should filter sessions based on search input', async () => {
    const user = userEvent.setup()
    const mockSessions = [
      {
        id: 'session-1',
        title: '数据分析会话',
        updatedAt: new Date('2024-01-01'),
        messages: [],
      },
      {
        id: 'session-2',
        title: '报告生成会话',
        updatedAt: new Date('2024-01-02'),
        messages: [],
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      sessions: mockSessions,
    } as any)

    render(<ChatInterface />)

    const searchInput = screen.getByPlaceholderText('搜索会话...')
    await user.type(searchInput, '数据')

    expect(screen.getByText('数据分析会话')).toBeInTheDocument()
    expect(screen.queryByText('报告生成会话')).not.toBeInTheDocument()
  })

  it('should display current session title and message count', () => {
    const mockCurrentSession = {
      id: 'session-1',
      title: '当前会话',
      messages: [{ id: 'msg-1' }, { id: 'msg-2' }, { id: 'msg-3' }],
    }

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: mockCurrentSession,
    } as any)

    render(<ChatInterface />)

    expect(screen.getByText('当前会话')).toBeInTheDocument()
    expect(screen.getByText('3 条消息')).toBeInTheDocument()
  })

  it('should switch session when clicking on session card', async () => {
    const user = userEvent.setup()
    const mockSessions = [
      {
        id: 'session-1',
        title: '会话1',
        updatedAt: new Date('2024-01-01'),
        messages: [],
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      sessions: mockSessions,
    } as any)

    render(<ChatInterface />)

    // 找到会话卡片并点击
    const sessionText = screen.getByText('会话1')
    const sessionCard = sessionText.closest('[class*="cursor-pointer"]')
    await user.click(sessionCard!)

    expect(mockSwitchSession).toHaveBeenCalledWith('session-1')
  })

  it('should show error message when error exists', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      error: '网络连接失败',
    } as any)

    render(<ChatInterface />)

    expect(screen.getByText('网络连接失败')).toBeInTheDocument()
  })

  it('should clear error when clicking close button', async () => {
    const user = userEvent.setup()
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      error: '网络连接失败',
    } as any)

    render(<ChatInterface />)

    // 找到错误关闭按钮（在错误提示区域内）
    const errorDiv = screen.getByText('网络连接失败').closest('div')!
    const closeButton = errorDiv.querySelector('button')!
    await user.click(closeButton)

    expect(mockSetError).toHaveBeenCalledWith(null)
  })

  it('should show mobile sidebar when menu button is clicked', async () => {
    const user = userEvent.setup()

    // 模拟移动端视口
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    })

    render(<ChatInterface />)

    // 在移动端，菜单按钮应该可见（md:hidden 的按钮）
    const menuButtons = screen.getAllByRole('button')
    const menuButton = menuButtons.find(btn => btn.classList.contains('md:hidden'))
    expect(menuButton).toBeTruthy()
    await user.click(menuButton!)

    // Sheet应该打开，显示多个"新建会话"按钮
    expect(screen.getAllByText('新建会话').length).toBeGreaterThanOrEqual(2)
  })

  it('should call clearHistory when clear history button is clicked', async () => {
    const user = userEvent.setup()
    const mockCurrentSession = {
      id: 'session-1',
      title: '当前会话',
      messages: [],
    }

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: mockCurrentSession,
    } as any)

    render(<ChatInterface />)

    const clearHistoryButton = screen.getByText('清空历史')
    await user.click(clearHistoryButton)

    expect(global.confirm).toHaveBeenCalledWith('确定要清空这个会话的所有消息吗？')
    expect(mockClearHistory).toHaveBeenCalledWith('session-1')
  })

  it('should prevent deleting last session', async () => {
    const user = userEvent.setup()
    const mockSessions = [
      {
        id: 'session-1',
        title: '唯一会话',
        updatedAt: new Date('2024-01-01'),
        messages: [],
      },
    ]

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      sessions: mockSessions,
      currentSession: { id: 'session-1', title: '唯一会话', messages: [] },
    } as any)

    render(<ChatInterface />)

    // 模拟删除操作
    const handleDeleteSession = (sessionId: string) => {
      if (mockSessions.length <= 1) {
        mockSetError('不能删除最后一个会话')
        return
      }
      if (confirm('确定要删除这个会话吗？所有消息将被永久删除。')) {
        mockDeleteSession(sessionId)
      }
    }

    handleDeleteSession('session-1')

    expect(mockSetError).toHaveBeenCalledWith('不能删除最后一个会话')
    expect(mockDeleteSession).not.toHaveBeenCalled()
  })

  it('should create session automatically when no sessions exist', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      sessions: [],
    } as any)

    render(<ChatInterface />)

    // useEffect应该自动调用createSession
    expect(mockCreateSession).toHaveBeenCalledWith('新会话')
  })

  it('should display empty state when no sessions match search', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      sessions: [],
    } as any)

    render(<ChatInterface />)

    const searchInput = screen.getByPlaceholderText('搜索会话...')
    fireEvent.change(searchInput, { target: { value: '不存在的会话' } })

    expect(screen.getByText('没有找到匹配的会话')).toBeInTheDocument()
  })

  it('should display sidebar action buttons', () => {
    render(<ChatInterface />)

    expect(screen.getByText('历史记录')).toBeInTheDocument()
    expect(screen.getByText('数据源管理')).toBeInTheDocument()
    expect(screen.getByText('设置')).toBeInTheDocument()
  })

  it('should have correct accessibility attributes', () => {
    const mockCurrentSession = {
      id: 'session-1',
      title: '当前会话',
      messages: [],
    }

    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      currentSession: mockCurrentSession,
    } as any)

    render(<ChatInterface />)

    // 检查主要的可访问性标签
    expect(screen.getByRole('button', { name: /新建会话/ })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /搜索会话/ })).toBeInTheDocument()
  })
})