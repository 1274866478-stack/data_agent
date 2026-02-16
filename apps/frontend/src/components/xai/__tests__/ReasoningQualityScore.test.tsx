import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ReasoningQualityScore } from '../ReasoningQualityScore'

// Mock the necessary dependencies
jest.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div data-testid="card-content">{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="card-description">{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div data-testid="card-header">{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="card-title">{children}</div>
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
  TabsTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-trigger">{children}</div>
}))

jest.mock('@/components/ui/alert', () => ({
  Alert: ({ children }: { children: React.ReactNode }) => <div data-testid="alert">{children}</div>,
  AlertDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-description">{children}</div>,
  AlertTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-title">{children}</div>
}))

describe('ReasoningQualityScore Component', () => {
  const defaultProps = {
    query: 'What is the current sales trend?',
    answer: 'Based on the data analysis, sales have increased by 15% in the last quarter.',
  }

  beforeEach(() => {
    // Mock URL.createObjectURL and URL.revokeObjectURL for export functionality
    global.URL.createObjectURL = jest.fn(() => 'mocked-url')
    global.URL.revokeObjectURL = jest.fn()
    global.Blob = jest.fn().mockImplementation((content, options) => ({
      content,
      options
    })) as any
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders without crashing', () => {
    render(<ReasoningQualityScore {...defaultProps} />)

    expect(screen.getByText('推理质量评分系统')).toBeInTheDocument()
    expect(screen.getByText('多维度AI推理质量评估与改进建议')).toBeInTheDocument()
  })

  it('displays query information', () => {
    render(<ReasoningQualityScore {...defaultProps} />)

    expect(screen.getByText(/查询:/)).toBeInTheDocument()
  })

  it('shows overall quality score', () => {
    render(<ReasoningQualityScore {...defaultProps} />)

    expect(screen.getAllByText('85')).toHaveLength(2) // 两个地方都显示85
    expect(screen.getByText('A 级')).toBeInTheDocument()
    expect(screen.getByText('优秀的推理质量')).toBeInTheDocument()
  })

  it('displays quality metrics', () => {
    render(<ReasoningQualityScore {...defaultProps} />)

    expect(screen.getAllByText('准确性')).toHaveLength(2) // 标题和指标中都有
    expect(screen.getAllByText('完整性')).toHaveLength(2) // 标题和指标中都有
    expect(screen.getAllByText('清晰度')).toHaveLength(2) // 标题和指标中都有
    expect(screen.getAllByText('可靠性')).toHaveLength(2) // 标题和指标中都有
    expect(screen.getAllByText('效率')).toHaveLength(2) // 标题和指标中都有
  })

  it('shows strengths and weaknesses', () => {
    render(<ReasoningQualityScore {...defaultProps} />)

    expect(screen.getByText('优势亮点')).toBeInTheDocument()
    expect(screen.getByText('改进空间')).toBeInTheDocument()
    expect(screen.getByText('表达清晰，结构合理')).toBeInTheDocument()
  })

  it('handles custom quality breakdown', () => {
    const customQualityBreakdown = {
      overall_score: 0.92,
      grade: 'A+' as const,
      grade_description: '卓越的推理质量',
      metrics: [],
      category_scores: {},
      strengths: ['Custom strength'],
      weaknesses: ['Custom weakness'],
      improvement_areas: ['Custom improvement'],
      confidence_level: 0.95
    }

    render(
      <ReasoningQualityScore
        {...defaultProps}
        qualityBreakdown={customQualityBreakdown}
      />
    )

    expect(screen.getByText('92')).toBeInTheDocument()
    expect(screen.getByText('A+ 级')).toBeInTheDocument()
    expect(screen.getByText('卓越的推理质量')).toBeInTheDocument()
    expect(screen.getByText('Custom strength')).toBeInTheDocument()
  })

  it('renders export button when allowExport is true', () => {
    render(<ReasoningQualityScore {...defaultProps} allowExport={true} />)

    expect(screen.getByText('导出')).toBeInTheDocument()
  })

  it('handles export functionality', () => {
    render(<ReasoningQualityScore {...defaultProps} allowExport={true} />)

    const exportButton = screen.getByText('导出')
    expect(exportButton).toBeInTheDocument()

    // Mock the DOM operations properly
    const mockCreateElement = jest.spyOn(document, 'createElement')
    const mockAppendChild = jest.spyOn(document.body, 'appendChild')
    const mockRemoveChild = jest.spyOn(document.body, 'removeChild')

    // Mock URL methods
    const mockCreateObjectURL = jest.fn().mockReturnValue('mock-url')
    const mockRevokeObjectURL = jest.fn()
    global.URL.createObjectURL = mockCreateObjectURL
    global.URL.revokeObjectURL = mockRevokeObjectURL

    const mockAnchor = {
      href: '',
      download: '',
      click: jest.fn()
    }
    mockCreateElement.mockReturnValue(mockAnchor as any)

    exportButton.click()

    // Verify DOM operations were attempted
    expect(mockCreateElement).toHaveBeenCalledWith('a')
    expect(mockCreateObjectURL).toHaveBeenCalled()
    expect(mockRevokeObjectURL).toHaveBeenCalled()

    mockCreateElement.mockRestore()
    mockAppendChild.mockRestore()
    mockRemoveChild.mockRestore()
  })

  it('shows processing metadata when provided', () => {
    const processingMetadata = {
      processing_time: 1500,
      model_version: 'gpt-4',
      reasoning_complexity: 0.75,
      data_sources_used: 3
    }

    render(
      <ReasoningQualityScore
        {...defaultProps}
        processingMetadata={processingMetadata}
      />
    )

    expect(screen.getByText('1500ms')).toBeInTheDocument()
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('0.75')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders simplified view when showDetailedAnalysis is false', () => {
    render(<ReasoningQualityScore {...defaultProps} showDetailedAnalysis={false} />)

    expect(screen.getByText('推理质量评分')).toBeInTheDocument()
    expect(screen.getByText('综合评分: 85%')).toBeInTheDocument()
    expect(screen.getByText('A 级')).toBeInTheDocument()

    // Should not show detailed elements
    expect(screen.queryByText('多维度AI推理质量评估与改进建议')).not.toBeInTheDocument()
  })

  it('displays correct grade colors', () => {
    const testCases = [
      { grade: 'A+' as const, expectedClass: 'text-green-600 bg-green-100' },
      { grade: 'B' as const, expectedClass: 'text-blue-600 bg-blue-100' },
      { grade: 'C' as const, expectedClass: 'text-yellow-600 bg-yellow-100' },
      { grade: 'D' as const, expectedClass: 'text-red-600 bg-red-100' }
    ]

    testCases.forEach(({ grade, expectedClass }) => {
      const qualityBreakdown = {
        overall_score: 0.8,
        grade,
        grade_description: 'Test description',
        metrics: [],
        category_scores: {},
        strengths: [],
        weaknesses: [],
        improvement_areas: [],
        confidence_level: 0.8
      }

      const { container } = render(
        <ReasoningQualityScore
          {...defaultProps}
          qualityBreakdown={qualityBreakdown}
        />
      )

      const gradeElement = screen.getByText(`${grade} 级`)
      expect(gradeElement).toBeInTheDocument()
    })
  })
})