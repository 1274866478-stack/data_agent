/**
 * MessageInput组件测试
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageInput } from '../MessageInput'
import { useChatStore } from '@/store/chatStore'

// Mock聊天store
jest.mock('@/store/chatStore')

const mockUseChatStore = useChatStore as jest.MockedFunction<typeof useChatStore>

describe('MessageInput', () => {
  const mockSendMessage = jest.fn()
  const mockOnFileAttach = jest.fn()

  const defaultMockStore = {
    sendMessage: mockSendMessage,
    isLoading: false,
    isTyping: false,
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseChatStore.mockReturnValue(defaultMockStore as any)
  })

  it('should render input field with placeholder', () => {
    render(<MessageInput />)

    expect(screen.getByPlaceholderText('输入您的问题...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /发送消息/ })).toBeInTheDocument()
  })

  it('should render custom placeholder', () => {
    render(<MessageInput placeholder="自定义占位符" />)

    expect(screen.getByPlaceholderText('自定义占位符')).toBeInTheDocument()
  })

  it('should type text into input', async () => {
    const user = userEvent.setup()
    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    await user.type(textarea, 'Hello AI')

    expect(textarea).toHaveValue('Hello AI')
  })

  it('should send message when clicking send button', async () => {
    const user = userEvent.setup()
    mockSendMessage.mockResolvedValue(undefined)

    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    await user.type(textarea, 'Test message')

    const sendButton = screen.getByRole('button', { name: /发送消息/ })
    await user.click(sendButton)

    expect(mockSendMessage).toHaveBeenCalledWith('Test message')
    expect(textarea).toHaveValue('')
  })

  it('should send message when pressing Enter', async () => {
    const user = userEvent.setup()
    mockSendMessage.mockResolvedValue(undefined)

    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    await user.type(textarea, 'Test message{enter}')

    expect(mockSendMessage).toHaveBeenCalledWith('Test message')
    expect(textarea).toHaveValue('')
  })

  it('should not send message when pressing Shift+Enter', async () => {
    const user = userEvent.setup()
    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    await user.type(textarea, 'Line 1{shift>}{enter}{/shift}')

    expect(mockSendMessage).not.toHaveBeenCalled()
    expect(textarea).toHaveValue('Line 1\n')
  })

  it('should clear input when pressing Escape', async () => {
    const user = userEvent.setup()
    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    await user.type(textarea, 'Some text{escape}')

    expect(textarea).toHaveValue('')
  })

  it('should disable send button when input is empty', () => {
    render(<MessageInput />)

    const sendButton = screen.getByRole('button', { name: /发送消息/ })
    expect(sendButton).toBeDisabled()
  })

  it('should disable send button when loading', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      isLoading: true,
    } as any)

    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    fireEvent.change(textarea, { target: { value: 'Test message' } })

    const sendButton = screen.getByRole('button', { name: /发送消息/ })
    expect(sendButton).toBeDisabled()
  })

  it('should show stop button when loading', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      isLoading: true,
    } as any)

    render(<MessageInput />)

    expect(screen.getByRole('button', { name: /停止生成/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /发送消息/ })).not.toBeInTheDocument()
  })

  it('should show file attach button when onFileAttach is provided', () => {
    render(<MessageInput onFileAttach={mockOnFileAttach} />)

    expect(screen.getByRole('button', { name: '' })).toBeInTheDocument()
  })

  it('should open file dialog when attach button is clicked', async () => {
    const user = userEvent.setup()

    // Mock document.createElement
    const mockInput = {
      type: '',
      multiple: false,
      click: jest.fn(),
      onchange: null,
    }
    const mockCreateElement = jest.fn(() => mockInput)
    Object.defineProperty(document, 'createElement', {
      value: mockCreateElement,
    })

    render(<MessageInput onFileAttach={mockOnFileAttach} />)

    const attachButton = screen.getByRole('button', { name: '' })
    await user.click(attachButton)

    expect(mockCreateElement).toHaveBeenCalledWith('input')
    expect(mockInput.type).toBe('file')
    expect(mockInput.multiple).toBe(true)
    expect(mockInput.click).toHaveBeenCalled()
  })

  it('should handle file drop', async () => {
    const mockFiles = [new File(['content'], 'test.txt', { type: 'text/plain' })]

    render(<MessageInput onFileAttach={mockOnFileAttach} />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')

    // 模拟文件拖拽
    const dragEvent = {
      preventDefault: jest.fn(),
      stopPropagation: jest.fn(),
      dataTransfer: {
        files: mockFiles,
      },
    }

    fireEvent.dragOver(textarea, dragEvent)
    fireEvent.drop(textarea, dragEvent)

    expect(mockOnFileAttach).toHaveBeenCalledWith(mockFiles)
  })

  it('should display character count when maxLength is provided', () => {
    render(<MessageInput maxLength={100} />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    fireEvent.change(textarea, { target: { value: 'Hello' } })

    expect(screen.getByText('5/100')).toBeInTheDocument()
  })

  it('should show typing indicator when isTyping is true', () => {
    mockUseChatStore.mockReturnValue({
      ...defaultMockStore,
      isTyping: true,
    } as any)

    render(<MessageInput />)

    expect(screen.getByText('AI 正在输入...')).toBeInTheDocument()
  })

  it('should display keyboard shortcuts help', () => {
    render(<MessageInput />)

    expect(screen.getByText('按')).toBeInTheDocument()
    expect(screen.getByText('Enter')).toBeInTheDocument()
    expect(screen.getByText('发送，')).toBeInTheDocument()
    expect(screen.getByText('Shift + Enter')).toBeInTheDocument()
    expect(screen.getByText('换行，')).toBeInTheDocument()
    expect(screen.getByText('Escape')).toBeInTheDocument()
    expect(screen.getByText('清空')).toBeInTheDocument()
  })

  it('should not send empty or whitespace-only messages', async () => {
    const user = userEvent.setup()
    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')

    // 测试空消息
    await user.type(textarea, '{enter}')
    expect(mockSendMessage).not.toHaveBeenCalled()

    // 测试只有空格的消息
    await user.type(textarea, '   {enter}')
    expect(mockSendMessage).not.toHaveBeenCalled()
  })

  it('should trim whitespace from messages', async () => {
    const user = userEvent.setup()
    mockSendMessage.mockResolvedValue(undefined)

    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    await user.type(textarea, '  Hello AI  {enter}')

    expect(mockSendMessage).toHaveBeenCalledWith('Hello AI')
  })

  it('should auto-resize textarea', () => {
    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...') as HTMLTextAreaElement

    // 添加长文本
    fireEvent.change(textarea, {
      target: {
        value: 'This is a very long message that should cause the textarea to expand in height to accommodate all the text content properly without needing vertical scrolling within the textarea component itself.'
      }
    })

    // 检查是否设置了高度
    expect(textarea.style.height).not.toBe('auto')
  })

  it('should limit textarea height', () => {
    render(<MessageInput />)

    const textarea = screen.getByPlaceholderText('输入您的问题...') as HTMLTextAreaElement

    // 添加非常长的文本
    fireEvent.change(textarea, {
      target: {
        value: 'a'.repeat(1000)
      }
    })

    // 高度应该被限制在最大值（120px）
    const height = parseInt(textarea.style.height)
    expect(height).toBeLessThanOrEqual(120)
  })

  it('should handle disabled state', () => {
    render(<MessageInput disabled />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    expect(textarea).toBeDisabled()

    const sendButton = screen.getByRole('button', { name: /发送消息/ })
    expect(sendButton).toBeDisabled()
  })

  it('should have correct accessibility attributes', () => {
    render(<MessageInput />)

    const sendButton = screen.getByRole('button', { name: /发送消息/ })
    expect(sendButton).toHaveAttribute('aria-label', expect.stringContaining('发送消息'))

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    expect(textarea).toHaveAttribute('maxLength', '2000')
  })

  it('should respect custom maxLength', () => {
    render(<MessageInput maxLength={50} />)

    const textarea = screen.getByPlaceholderText('输入您的问题...')
    expect(textarea).toHaveAttribute('maxLength', '50')
  })
})