/**
 * XAI组件集成测试
 * 测试组件间的交互、错误处理和性能表现
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import { EvidenceChain, ReasoningQualityScore } from '../..'

// Mock the necessary dependencies
jest.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div data-testid="card-content">{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="card-description">{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div data-testid="card-header">{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="card-title">{children}</div>,
}))

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className }: { children: React.ReactNode; className?: string }) =>
    <span data-testid="badge" className={className}>{children}</span>
}))

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, ...props }: any) =>
    <button onClick={onClick} {...props}>{children}</button>
}))

jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: { value: number }) =>
    <div data-testid="progress" style={{ width: `${value}%` }}></div>
}))

jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs">{children}</div>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-content">{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children, value, onClick }: { children: React.ReactNode; value: string; onClick?: () => void }) =>
    <button onClick={onClick} data-value={value}>{children}</button>
}))

jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children, open, onOpenChange }: { children: React.ReactNode; open: boolean; onOpenChange: () => void }) =>
    <div data-testid="collapsible" data-open={open} onClick={onOpenChange}>{children}</div>,
  CollapsibleContent: ({ children }: { children: React.ReactNode }) => <div data-testid="collapsible-content">{children}</div>,
  CollapsibleTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) =>
    asChild ? <div>{children}</div> : <button>{children}</button>
}))

jest.mock('@/components/ui/alert', () => ({
  Alert: ({ children }: { children: React.ReactNode }) => <div data-testid="alert">{children}</div>,
  AlertDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-description">{children}</div>,
  AlertTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-title">{children}</div>,
}))

// Mock Lucide icons
jest.mock('lucide-react', () => ({
  CheckCircle2: () => <div data-testid="check-circle-icon"></div>,
  AlertTriangle: () => <div data-testid="alert-triangle-icon"></div>,
  Clock: () => <div data-testid="clock-icon"></div>,
  Search: () => <div data-testid="search-icon"></div>,
  FileText: () => <div data-testid="file-text-icon"></div>,
  Database: () => <div data-testid="database-icon"></div>,
  Brain: () => <div data-testid="brain-icon"></div>,
  GitBranch: () => <div data-testid="git-branch-icon"></div>,
  ChevronDown: () => <div data-testid="chevron-down-icon"></div>,
  ChevronUp: () => <div data-testid="chevron-up-icon"></div>,
  BarChart3: () => <div data-testid="bar-chart-icon"></div>,
  Info: () => <div data-testid="info-icon"></div>,
  Link: () => <div data-testid="link-icon"></div>,
  Star: () => <div data-testid="star-icon"></div>,
  TrendingUp: () => <div data-testid="trending-up-icon"></div>,
  Award: () => <div data-testid="award-icon"></div>,
  Target: () => <div data-testid="target-icon"></div>,
  PieChart: () => <div data-testid="pie-chart-icon"></div>,
  LineChart: () => <div data-testid="line-chart-icon"></div>,
  Download: () => <div data-testid="download-icon"></div>,
  RefreshCw: () => <div data-testid="refresh-cw-icon"></div>,
  Eye: () => <div data-testid="eye-icon"></div>,
  EyeOff: () => <div data-testid="eye-off-icon"></div>,
}))

// Mock performance API
Object.defineProperty(window, 'performance', {
  value: {
    now: jest.fn(() => Date.now()),
    mark: jest.fn(),
    measure: jest.fn(),
  },
  writable: true,
})

describe('XAI组件集成测试', () => {
  const mockEvidenceNodes = {
    'node-1': {
      id: 'node-1',
      source_type: 'document' as const,
      source_name: '测试文档',
      content: '这是测试内容',
      confidence_score: 0.9,
      verification_status: 'verified' as const,
      timestamp: '2024-01-01T10:00:00Z',
      child_nodes: ['node-2']
    },
    'node-2': {
      id: 'node-2',
      source_type: 'database' as const,
      source_name: '测试数据库',
      content: '这是数据库内容',
      confidence_score: 0.85,
      verification_status: 'pending' as const,
      timestamp: '2024-01-01T10:01:00Z',
      child_nodes: []
    }
  }

  const mockChains = [
    {
      chain_id: 'chain-1',
      chain_name: '测试证据链',
      chain_type: 'linear' as const,
      description: '这是一个测试证据链',
      evidence_count: 2,
      verified_count: 1,
      created_at: '2024-01-01T10:00:00Z'
    }
  ]

  beforeEach(() => {
    jest.clearAllMocks()
    // Mock console.error to avoid test output noise
    jest.spyOn(console, 'error').mockImplementation(() => {})
    jest.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  describe('组件集成与交互', () => {
    it('应该能够同时渲染EvidenceChain和ReasoningQualityScore组件', () => {
      const TestComponent = () => (
        <div>
          <EvidenceChain
            chains={mockChains}
            evidenceNodes={mockEvidenceNodes}
            query="测试查询"
            answer="测试回答"
          />
          <ReasoningQualityScore
            query="测试查询"
            answer="测试回答"
          />
        </div>
      )

      render(<TestComponent />)

      expect(screen.getByText('证据链分析')).toBeInTheDocument()
      expect(screen.getByText('推理质量评分系统')).toBeInTheDocument()
    })

    it('应该能够处理大量数据的场景', async () => {
      // 生成大量测试数据
      const largeEvidenceNodes: Record<string, any> = {}
      for (let i = 0; i < 100; i++) {
        largeEvidenceNodes[`node-${i}`] = {
          id: `node-${i}`,
          source_type: 'document' as const,
          source_name: `文档 ${i}`,
          content: `内容 ${i}`,
          confidence_score: 0.8 + Math.random() * 0.2,
          verification_status: 'verified' as const,
          timestamp: new Date().toISOString(),
          child_nodes: i < 99 ? [`node-${i + 1}`] : []
        }
      }

      const startTime = performance.now()

      render(
        <EvidenceChain
          chains={mockChains}
          evidenceNodes={largeEvidenceNodes}
          maxNodes={50}
          maxDepth={3}
        />
      )

      const endTime = performance.now()
      const renderTime = endTime - startTime

      // 渲染时间应该在合理范围内
      expect(renderTime).toBeLessThan(100) // 100ms

      // 应该显示节点数量限制信息
      expect(screen.getByText(/显示限制/)).toBeInTheDocument()
    })

    it('应该在组件错误时正确处理和恢复', async () => {
      // 创建一个会导致错误的组件
      const FailingComponent = () => {
        throw new Error('测试错误')
      }

      const TestComponent = () => (
        <div>
          <EvidenceChain
            chains={mockChains}
            evidenceNodes={mockEvidenceNodes}
          />
          <div data-testid="failing-component">
            <FailingComponent />
          </div>
        </div>
      )

      // 使用错误边界包装
      const { container } = render(
        <React.ErrorBoundary
          fallback={
            <div data-testid="error-fallback">组件错误</div>
          }
        >
          <TestComponent />
        </React.ErrorBoundary>
      )

      // 正常组件应该继续工作
      expect(screen.getByText('证据链分析')).toBeInTheDocument()
      // 错误应该被捕获
      expect(screen.getByTestId('error-fallback')).toBeInTheDocument()
    })
  })

  describe('性能测试', () => {
    it('应该能够快速切换视图模式', () => {
      render(
        <EvidenceChain
          chains={mockChains}
          evidenceNodes={mockEvidenceNodes}
        />
      )

      const tabsTrigger = screen.getAllByTestId('tabs-list')[0]

      // 切换到关系图谱视图
      fireEvent.click(tabsTrigger.querySelectorAll('button')[1])

      expect(screen.getByText('证据链图形化视图')).toBeInTheDocument()

      // 切换到时间线视图
      fireEvent.click(tabsTrigger.querySelectorAll('button')[2])

      expect(screen.getByText('证据链时间线')).toBeInTheDocument()
    })

    it('应该能够处理频繁的节点展开/折叠操作', () => {
      render(
        <EvidenceChain
          chains={mockChains}
          evidenceNodes={mockEvidenceNodes}
        />
      )

      // 模拟频繁的节点展开/折叠
      for (let i = 0; i < 10; i++) {
        const expandButtons = screen.getAllByRole('button')
        expandButtons.forEach(button => {
          if (button.textContent && button.textContent.includes('展开')) {
            fireEvent.click(button)
          }
        })
      }

      // 组件应该仍然正常工作
      expect(screen.getByText('证据链分析')).toBeInTheDocument()
    })
  })

  describe('数据流测试', () => {
    it('应该正确处理props变化', () => {
      const { rerender } = render(
        <EvidenceChain
          chains={[]}
          evidenceNodes={{}}
        />
      )

      // 初始状态应该显示无数据
      expect(screen.getByText('暂无证据链数据')).toBeInTheDocument()

      // 重新渲染新数据
      rerender(
        <EvidenceChain
          chains={mockChains}
          evidenceNodes={mockEvidenceNodes}
        />
      )

      // 应该显示新的数据
      expect(screen.getByText('证据链分析')).toBeInTheDocument()
      expect(screen.getByText('测试证据链')).toBeInTheDocument()
    })

    it('应该能够处理无效的数据格式', () => {
      const invalidNodes = {
        'invalid-node': {
          // 缺少必要字段
          id: 'invalid-node',
          source_type: 'invalid' as any,
          confidence_score: 1.5, // 超出范围
          verification_status: 'invalid' as any
        }
      }

      render(
        <EvidenceChain
          chains={mockChains}
          evidenceNodes={invalidNodes}
        />
      )

      // 组件应该仍然渲染，不崩溃
      expect(screen.getByText('证据链分析')).toBeInTheDocument()
    })
  })

  describe('内存泄漏测试', () => {
    it('应该在组件卸载时清理资源', () => {
      const { unmount } = render(
        <EvidenceChain
          chains={mockChains}
          evidenceNodes={mockEvidenceNodes}
        />
      )

      // 执行一些交互
      const expandButtons = screen.getAllByRole('button')
      if (expandButtons.length > 0) {
        fireEvent.click(expandButtons[0])
      }

      // 卸载组件
      expect(() => unmount()).not.toThrow()

      // 验证没有内存泄漏（通过检查是否还有DOM元素）
      expect(document.querySelector('[data-testid="card"]')).not.toBeInTheDocument()
    })
  })

  describe('错误恢复测试', () => {
    it('应该能够从渲染错误中恢复', async () => {
      const TestComponent = () => {
        const [shouldError, setShouldError] = React.useState(false)

        if (shouldError) {
          throw new Error('测试错误')
        }

        return (
          <div>
            <EvidenceChain
              chains={mockChains}
              evidenceNodes={mockEvidenceNodes}
            />
            <button onClick={() => setShouldError(true)}>
              触发错误
            </button>
          </div>
        )
      }

      render(
        <React.ErrorBoundary
          fallback={
            <div data-testid="error-fallback">发生错误</div>
          }
        >
          <TestComponent />
        </React.ErrorBoundary>
      )

      // 初始状态正常
      expect(screen.getByText('证据链分析')).toBeInTheDocument()

      // 触发错误
      fireEvent.click(screen.getByText('触发错误'))

      // 应该显示错误回退
      expect(screen.getByTestId('error-fallback')).toBeInTheDocument()
    })
  })
})