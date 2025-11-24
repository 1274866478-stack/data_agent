import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { SafeComponentWrapper, useSafeAsyncData } from './SafeComponentWrapper';
import { useErrorHandler } from './ErrorBoundary';
import {
  Star,
  TrendingUp,
  Award,
  Target,
  CheckCircle2,
  AlertTriangle,
  Info,
  BarChart3,
  PieChart,
  LineChart,
  Download,
  RefreshCw,
  Eye,
  EyeOff
} from 'lucide-react';

interface QualityMetric {
  id: string;
  name: string;
  description: string;
  score: number;
  weight: number;
  category: 'accuracy' | 'completeness' | 'clarity' | 'reliability' | 'efficiency';
  status: 'excellent' | 'good' | 'fair' | 'poor';
  feedback?: string;
  improvement_suggestions?: string[];
}

interface QualityBreakdown {
  overall_score: number;
  grade: 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D' | 'F';
  grade_description: string;
  metrics: QualityMetric[];
  category_scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  improvement_areas: string[];
  comparison_with_previous?: {
    score_change: number;
    trend: 'improving' | 'stable' | 'declining';
  };
  confidence_level: number;
}

interface ReasoningQualityScoreProps {
  query: string;
  answer: string;
  qualityBreakdown?: QualityBreakdown;
  processingMetadata?: {
    processing_time: number;
    model_version: string;
    reasoning_complexity: number;
    data_sources_used: number;
  };
  showDetailedAnalysis?: boolean;
  allowExport?: boolean;
  className?: string;
}

export const ReasoningQualityScore: React.FC<ReasoningQualityScoreProps> = ({
  query,
  answer,
  qualityBreakdown,
  processingMetadata,
  showDetailedAnalysis = true,
  allowExport = true,
  className
}) => {
  const [expandedMetrics, setExpandedMetrics] = useState<Set<string>>(new Set());
  const [selectedView, setSelectedView] = useState<'overview' | 'detailed' | 'comparison'>('overview');

  // 默认质量分解数据（如果没有传入的话）
  const defaultQualityBreakdown: QualityBreakdown = useMemo(() => {
    if (qualityBreakdown) return qualityBreakdown;

    return {
      overall_score: 0.85,
      grade: 'A',
      grade_description: '优秀的推理质量',
      metrics: [
        {
          id: 'accuracy',
          name: '准确性',
          description: '答案内容的准确性和事实正确性',
          score: 0.88,
          weight: 0.3,
          category: 'accuracy',
          status: 'excellent',
          feedback: '答案内容准确，事实依据充分',
          improvement_suggestions: ['可以进一步验证关键数据点', '考虑更多权威来源']
        },
        {
          id: 'completeness',
          name: '完整性',
          description: '回答的完整性和覆盖范围',
          score: 0.82,
          weight: 0.25,
          category: 'completeness',
          status: 'good',
          feedback: '回答较为全面，覆盖了主要方面',
          improvement_suggestions: ['可以补充更多细节信息', '考虑边缘情况的处理']
        },
        {
          id: 'clarity',
          name: '清晰度',
          description: '表达的清晰度和易理解性',
          score: 0.90,
          weight: 0.2,
          category: 'clarity',
          status: 'excellent',
          feedback: '表达清晰，结构合理',
          improvement_suggestions: ['可以增加更多实例说明']
        },
        {
          id: 'reliability',
          name: '可靠性',
          description: '数据来源的可靠性和验证程度',
          score: 0.78,
          weight: 0.15,
          category: 'reliability',
          status: 'good',
          feedback: '数据来源较为可靠，有基本验证',
          improvement_suggestions: ['增加更多权威来源引用', '提供数据验证方法']
        },
        {
          id: 'efficiency',
          name: '效率',
          description: '推理过程的效率和响应速度',
          score: 0.92,
          weight: 0.1,
          category: 'efficiency',
          status: 'excellent',
          feedback: '推理效率高，响应及时',
          improvement_suggestions: ['可以进一步优化复杂查询的处理']
        }
      ],
      category_scores: {
        accuracy: 0.88,
        completeness: 0.82,
        clarity: 0.90,
        reliability: 0.78,
        efficiency: 0.92
      },
      strengths: [
        '表达清晰，结构合理',
        '推理效率高，响应及时',
        '答案内容准确，事实依据充分'
      ],
      weaknesses: [
        '数据来源验证可以进一步加强',
        '某些细节信息可以补充'
      ],
      improvement_areas: [
        '增加权威来源引用',
        '补充更多细节信息',
        '提供数据验证方法'
      ],
      comparison_with_previous: {
        score_change: 0.05,
        trend: 'improving'
      },
      confidence_level: 0.87
    };
  }, [qualityBreakdown]);

  const quality = defaultQualityBreakdown;

  const getGradeColor = (grade: string) => {
    switch (grade[0]) {
      case 'A': return 'text-green-600 bg-green-100';
      case 'B': return 'text-blue-600 bg-blue-100';
      case 'C': return 'text-yellow-600 bg-yellow-100';
      case 'D': case 'F': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600';
    if (score >= 0.8) return 'text-blue-600';
    if (score >= 0.7) return 'text-yellow-600';
    if (score >= 0.6) return 'text-orange-600';
    return 'text-red-600';
  };

  const getMetricIcon = (category: string) => {
    switch (category) {
      case 'accuracy': return <Target className="h-4 w-4" />;
      case 'completeness': return <CheckCircle2 className="h-4 w-4" />;
      case 'clarity': return <Eye className="h-4 w-4" />;
      case 'reliability': return <Award className="h-4 w-4" />;
      case 'efficiency': return <TrendingUp className="h-4 w-4" />;
      default: return <Info className="h-4 w-4" />;
    }
  };

  const toggleMetricExpansion = (metricId: string) => {
    setExpandedMetrics(prev => {
      const newSet = new Set(prev);
      if (newSet.has(metricId)) {
        newSet.delete(metricId);
      } else {
        newSet.add(metricId);
      }
      return newSet;
    });
  };

  const exportQualityReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      query,
      answer,
      quality_breakdown: quality,
      processing_metadata: processingMetadata
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);

    // 检查是否在测试环境中
    if (typeof window !== 'undefined' && window.document && window.document.body) {
      try {
        const a = document.createElement('a');
        a.href = url;
        a.download = `reasoning-quality-report-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } catch (error) {
        // 如果DOM操作失败，提供备选方案
        console.warn('DOM export failed, using fallback:', error);
        // 在控制台输出报告内容
        console.log('Quality Report:', JSON.stringify(report, null, 2));
        // 尝试打开新窗口
        if (window.open) {
          const newWindow = window.open();
          if (newWindow) {
            newWindow.document.write(`<pre>${JSON.stringify(report, null, 2)}</pre>`);
          }
        }
      }
    } else {
      // 测试环境中的处理
      console.log('Quality Report:', JSON.stringify(report, null, 2));
    }

    URL.revokeObjectURL(url);
  };

  const renderOverview = () => (
    <div className="space-y-6">
      {/* 总体评分 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Star className="h-5 w-5" />
                推理质量评分
              </CardTitle>
              <CardDescription>
                基于准确性、完整性、清晰度、可靠性和效率的综合评估
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={getGradeColor(quality.grade)}>
                {quality.grade} 级
              </Badge>
              {allowExport && (
                <Button variant="outline" size="sm" onClick={exportQualityReport}>
                  <Download className="h-4 w-4 mr-2" />
                  导出报告
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* 总分显示 */}
            <div className="text-center py-6">
              <div className={`text-6xl font-bold ${getScoreColor(quality.overall_score)}`}>
                {(quality.overall_score * 100).toFixed(0)}
              </div>
              <div className="text-lg text-muted-foreground mt-2">
                {quality.grade_description}
              </div>
              <div className="flex items-center justify-center gap-2 mt-4">
                <Progress value={quality.overall_score * 100} className="w-48 h-3" />
                <span className="text-sm text-muted-foreground">
                  置信度: {Math.round(quality.confidence_level * 100)}%
                </span>
              </div>
            </div>

            {/* 趋势指示 */}
            {quality.comparison_with_previous && (
              <div className="flex items-center justify-center gap-2 p-3 bg-muted/50 rounded">
                {quality.comparison_with_previous.trend === 'improving' && (
                  <>
                    <TrendingUp className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-green-600">
                      较上次提升 {Math.round(quality.comparison_with_previous.score_change * 100)}%
                    </span>
                  </>
                )}
                {quality.comparison_with_previous.trend === 'declining' && (
                  <>
                    <TrendingUp className="h-4 w-4 text-red-600 rotate-180" />
                    <span className="text-sm text-red-600">
                      较上次下降 {Math.round(Math.abs(quality.comparison_with_previous.score_change) * 100)}%
                    </span>
                  </>
                )}
                {quality.comparison_with_previous.trend === 'stable' && (
                  <>
                    <Target className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-blue-600">
                      与上次持平
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 优缺点分析 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle2 className="h-5 w-5" />
              优势亮点
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {quality.strengths.map((strength, index) => (
                <li key={index} className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-500" />
                  <span className="text-sm">{strength}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-600">
              <AlertTriangle className="h-5 w-5" />
              改进空间
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {quality.improvement_areas.map((area, index) => (
                <li key={index} className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 mt-0.5 text-orange-500" />
                  <span className="text-sm">{area}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const renderDetailed = () => (
    <div className="space-y-6">
      {/* 分类评分 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="h-5 w-5" />
            分类评分详情
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Object.entries(quality.category_scores).map(([category, score]) => {
              const metric = quality.metrics.find(m => m.category === category);
              return (
                <div key={category} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getMetricIcon(category)}
                      <span className="font-medium">{metric?.name || category}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${getScoreColor(score)}`}>
                        {(score * 100).toFixed(0)}%
                      </span>
                      <Badge variant="outline" className="text-xs">
                        权重 {Math.round((metric?.weight || 0) * 100)}%
                      </Badge>
                    </div>
                  </div>
                  <Progress value={score * 100} className="h-2" />
                  <p className="text-xs text-muted-foreground">
                    {metric?.description}
                  </p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 详细指标分析 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            详细指标分析
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {quality.metrics.map((metric) => {
              const isExpanded = expandedMetrics.has(metric.id);
              return (
                <div key={metric.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {getMetricIcon(metric.category)}
                      <div>
                        <h4 className="font-medium">{metric.name}</h4>
                        <p className="text-sm text-muted-foreground">{metric.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right">
                        <div className={`text-lg font-bold ${getScoreColor(metric.score)}`}>
                          {(metric.score * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-muted-foreground">
                          权重 {Math.round(metric.weight * 100)}%
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleMetricExpansion(metric.id)}
                      >
                        {isExpanded ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>

                  <Progress value={metric.score * 100} className="mb-3" />

                  {isExpanded && (
                    <div className="space-y-3 pt-3 border-t">
                      {metric.feedback && (
                        <div>
                          <h5 className="font-medium text-sm mb-1">评估反馈</h5>
                          <p className="text-sm bg-muted p-2 rounded">{metric.feedback}</p>
                        </div>
                      )}

                      {metric.improvement_suggestions && metric.improvement_suggestions.length > 0 && (
                        <div>
                          <h5 className="font-medium text-sm mb-1">改进建议</h5>
                          <ul className="text-sm space-y-1">
                            {metric.improvement_suggestions.map((suggestion, idx) => (
                              <li key={idx} className="flex items-start gap-2">
                                <TrendingUp className="h-3 w-3 mt-0.5 text-blue-500" />
                                {suggestion}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderComparison = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LineChart className="h-5 w-5" />
            历史对比分析
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {quality.comparison_with_previous ? (
              <div className="text-center py-8">
                <div className="flex items-center justify-center gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-muted-foreground">
                      {(Math.round((quality.overall_score - quality.comparison_with_previous.score_change) * 100))}
                    </div>
                    <div className="text-sm text-muted-foreground">上次评分</div>
                  </div>
                  <div className="flex items-center">
                    {quality.comparison_with_previous.trend === 'improving' && (
                      <TrendingUp className="h-6 w-6 text-green-600" />
                    )}
                    {quality.comparison_with_previous.trend === 'declining' && (
                      <TrendingUp className="h-6 w-6 text-red-600 rotate-180" />
                    )}
                    {quality.comparison_with_previous.trend === 'stable' && (
                      <Target className="h-6 w-6 text-blue-600" />
                    )}
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">
                      {(quality.overall_score * 100).toFixed(0)}
                    </div>
                    <div className="text-sm text-muted-foreground">当前评分</div>
                  </div>
                </div>
                <div className="text-lg">
                  {quality.comparison_with_previous.trend === 'improving' && (
                    <span className="text-green-600">
                      提升 {Math.round(quality.comparison_with_previous.score_change * 100)}%
                    </span>
                  )}
                  {quality.comparison_with_previous.trend === 'declining' && (
                    <span className="text-red-600">
                      下降 {Math.round(Math.abs(quality.comparison_with_previous.score_change) * 100)}%
                    </span>
                  )}
                  {quality.comparison_with_previous.trend === 'stable' && (
                    <span className="text-blue-600">保持稳定</span>
                  )}
                </div>
              </div>
            ) : (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertTitle>暂无历史数据</AlertTitle>
                <AlertDescription>
                  当前还没有历史对比数据。后续会显示评分变化趋势。
                </AlertDescription>
              </Alert>
            )}

            {processingMetadata && (
              <div className="mt-6 p-4 bg-muted/50 rounded">
                <h4 className="font-medium mb-3">处理元数据</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">处理时间:</span>
                    <div className="font-medium">{processingMetadata.processing_time}ms</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">模型版本:</span>
                    <div className="font-medium">{processingMetadata.model_version}</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">推理复杂度:</span>
                    <div className="font-medium">{processingMetadata.reasoning_complexity}</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">数据源数量:</span>
                    <div className="font-medium">{processingMetadata.data_sources_used}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );

  if (!showDetailedAnalysis) {
    return (
      <Card className={className}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Star className="h-5 w-5 text-yellow-500" />
              <div>
                <div className="font-medium">推理质量评分</div>
                <div className="text-sm text-muted-foreground">
                  综合评分: {(quality.overall_score * 100).toFixed(0)}%
                </div>
              </div>
            </div>
            <Badge className={getGradeColor(quality.grade)}>
              {quality.grade} 级
            </Badge>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Award className="h-5 w-5" />
                推理质量评分系统
              </CardTitle>
              <CardDescription>
                多维度AI推理质量评估与改进建议
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">
                查询: {query.slice(0, 20)}{query.length > 20 ? '...' : ''}
              </Badge>
              <Button variant="outline" size="sm" onClick={exportQualityReport}>
                <Download className="h-4 w-4 mr-2" />
                导出
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      <Tabs value={selectedView} onValueChange={(value) => setSelectedView(value as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview">总览</TabsTrigger>
          <TabsTrigger value="detailed">详细分析</TabsTrigger>
          <TabsTrigger value="comparison">历史对比</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {renderOverview()}
        </TabsContent>

        <TabsContent value="detailed" className="space-y-4">
          {renderDetailed()}
        </TabsContent>

        <TabsContent value="comparison" className="space-y-4">
          {renderComparison()}
        </TabsContent>
      </Tabs>
    </div>
  );
};