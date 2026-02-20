import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import {
  BookOpen,
  Brain,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Info,
  Eye,
  EyeOff,
  TrendingUp,
  Target
} from 'lucide-react';

export interface ExplanationStep {
  step_number: number;
  explanation_type: string;
  title: string;
  description: string;
  evidence: string[];
  confidence: number;
  reasoning?: string;
  assumptions?: string[];
  limitations?: string[];
  timestamp: string;
}

export interface SourceTrace {
  source_id: string;
  source_type: string;
  source_name: string;
  content_snippet: string;
  relevance_score: number;
  confidence_contribution: number;
  verification_status: string;
}

export interface ConfidenceExplanation {
  overall_confidence: number;
  confidence_level: string;
  confidence_description: string;
  confidence_factors: Record<string, number>;
  improvement_suggestions: string[];
}

export interface AlternativeAnswer {
  answer_id: string;
  title: string;
  content: string;
  reasoning_differences: string[];
  confidence_comparison: Record<string, number>;
  scenario_description: string;
  pros?: string[];
  cons?: string[];
}

interface AnswerExplanationProps {
  query: string;
  answer: string;
  explanationSteps?: ExplanationStep[];
  sourceTraces?: SourceTrace[];
  confidenceExplanation?: ConfidenceExplanation;
  alternativeAnswers?: AlternativeAnswer[];
  explanationQualityScore?: number;
  processingMetadata?: {
    total_processing_time: number;
    fusion_enabled: boolean;
    xai_enabled: boolean;
    reasoning_mode: string;
  };
  className?: string;
}

export const AnswerExplanation: React.FC<AnswerExplanationProps> = ({
  query,
  answer,
  explanationSteps = [],
  sourceTraces = [],
  confidenceExplanation,
  alternativeAnswers = [],
  explanationQualityScore = 0,
  processingMetadata,
  className
}) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [showDetailedReasoning, setShowDetailedReasoning] = useState(false);
  const [selectedAlternative, setSelectedAlternative] = useState<string | null>(null);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceBadgeVariant = (confidence: number): 'default' | 'secondary' | 'destructive' | 'outline' => {
    if (confidence >= 0.8) return 'default';
    if (confidence >= 0.6) return 'secondary';
    return 'destructive';
  };

  const getExplanationTypeIcon = (type: string) => {
    switch (type) {
      case 'data_source': return <BookOpen className="h-4 w-4" />;
      case 'reasoning_process': return <Brain className="h-4 w-4" />;
      case 'confidence': return <Target className="h-4 w-4" />;
      case 'alternative': return <TrendingUp className="h-4 w-4" />;
      default: return <Info className="h-4 w-4" />;
    }
  };

  const formatProcessingTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const toggleStepExpansion = (stepNumber: number) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stepNumber)) {
        newSet.delete(stepNumber);
      } else {
        newSet.add(stepNumber);
      }
      return newSet;
    });
  };

  const overallConfidence = confidenceExplanation?.overall_confidence || 0;
  const qualityGrade = explanationQualityScore >= 0.8 ? '优秀' :
                       explanationQualityScore >= 0.6 ? '良好' :
                       explanationQualityScore >= 0.4 ? '一般' : '需要改进';

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 头部信息 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5" />
                答案解释与分析
              </CardTitle>
              <CardDescription>
                深入了解答案的生成过程、数据来源和置信度评估
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={getConfidenceBadgeVariant(overallConfidence)}>
                置信度: {(overallConfidence * 100).toFixed(0)}%
              </Badge>
              <Badge variant="outline">
                质量: {qualityGrade}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {processingMetadata && (
              <>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    处理时间: {formatProcessingTime(processingMetadata.total_processing_time || 0)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    数据融合: {processingMetadata.fusion_enabled ? '启用' : '禁用'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Eye className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    XAI解释: {processingMetadata.xai_enabled ? '启用' : '禁用'}
                  </span>
                </div>
              </>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>综合质量分数</span>
              <span className={getConfidenceColor(explanationQualityScore)}>
                {(explanationQualityScore * 100).toFixed(0)}%
              </span>
            </div>
            <Progress value={explanationQualityScore * 100} className="h-2" />
          </div>
        </CardContent>
      </Card>

      {/* 主要内容标签页 */}
      <Tabs defaultValue="reasoning" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="reasoning">推理过程</TabsTrigger>
          <TabsTrigger value="confidence">置信度分析</TabsTrigger>
          <TabsTrigger value="sources">数据溯源</TabsTrigger>
          <TabsTrigger value="alternatives">替代答案</TabsTrigger>
        </TabsList>

        {/* 推理过程标签页 */}
        <TabsContent value="reasoning" className="space-y-4">
          {explanationSteps.length > 0 ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">详细推理步骤</h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDetailedReasoning(!showDetailedReasoning)}
                >
                  {showDetailedReasoning ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
                  {showDetailedReasoning ? '简化视图' : '详细视图'}
                </Button>
              </div>

              {explanationSteps.map((step) => (
                <Card key={step.step_number}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline">步骤 {step.step_number}</Badge>
                        <div className="flex items-center gap-1">
                          {getExplanationTypeIcon(step.explanation_type)}
                          <span className="font-medium">{step.title}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${getConfidenceColor(step.confidence)}`}>
                          {(step.confidence * 100).toFixed(0)}%
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleStepExpansion(step.step_number)}
                        >
                          {expandedSteps.has(step.step_number) ? '收起' : '展开'}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">{step.description}</p>

                    {expandedSteps.has(step.step_number) && showDetailedReasoning && (
                      <div className="space-y-4 mt-4">
                        {step.reasoning && (
                          <div>
                            <h4 className="font-medium mb-2">推理逻辑</h4>
                            <p className="text-sm bg-muted p-3 rounded">{step.reasoning}</p>
                          </div>
                        )}

                        {step.evidence && step.evidence.length > 0 && (
                          <div>
                            <h4 className="font-medium mb-2">支持证据</h4>
                            <ul className="text-sm space-y-1">
                              {step.evidence.map((evidence, idx) => (
                                <li key={idx} className="flex items-start gap-2">
                                  <CheckCircle2 className="h-3 w-3 mt-0.5 text-green-500" />
                                  {evidence}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {step.assumptions && step.assumptions.length > 0 && (
                          <div>
                            <h4 className="font-medium mb-2">假设条件</h4>
                            <ul className="text-sm space-y-1">
                              {step.assumptions.map((assumption, idx) => (
                                <li key={idx} className="flex items-start gap-2">
                                  <AlertTriangle className="h-3 w-3 mt-0.5 text-yellow-500" />
                                  {assumption}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {step.limitations && step.limitations.length > 0 && (
                          <Alert>
                            <AlertTriangle className="h-4 w-4" />
                            <AlertTitle>限制因素</AlertTitle>
                            <ul className="text-sm mt-2 space-y-1">
                              {step.limitations.map((limitation, idx) => (
                                <li key={idx}>{limitation}</li>
                              ))}
                            </ul>
                          </Alert>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>暂无推理步骤</AlertTitle>
              <AlertDescription>
                当前答案没有详细的推理步骤记录。
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        {/* 置信度分析标签页 */}
        <TabsContent value="confidence" className="space-y-4">
          {confidenceExplanation ? (
            <div className="space-y-6">
              {/* 总体置信度 */}
              <Card>
                <CardHeader>
                  <CardTitle>总体置信度分析</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-medium">置信度等级</span>
                      <Badge variant={getConfidenceBadgeVariant(overallConfidence)}>
                        {confidenceExplanation.confidence_level}
                      </Badge>
                    </div>
                    <Progress value={overallConfidence * 100} className="h-3" />
                    <p className="text-sm text-muted-foreground">
                      {confidenceExplanation.confidence_description}
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* 置信度因子 */}
              <Card>
                <CardHeader>
                  <CardTitle>置信度组成因子</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(confidenceExplanation.confidence_factors).map(([factor, score]) => (
                      <div key={factor} className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>{factor}</span>
                          <span className={getConfidenceColor(score)}>{(score * 100).toFixed(0)}%</span>
                        </div>
                        <Progress value={score * 100} className="h-2" />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 改进建议 */}
              {confidenceExplanation.improvement_suggestions && confidenceExplanation.improvement_suggestions.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>置信度改进建议</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {confidenceExplanation.improvement_suggestions.map((suggestion, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <TrendingUp className="h-4 w-4 mt-0.5 text-blue-500" />
                          <span className="text-sm">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>暂无置信度分析</AlertTitle>
              <AlertDescription>
                当前答案没有详细的置信度分析数据。
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        {/* 数据溯源标签页 */}
        <TabsContent value="sources" className="space-y-4">
          {sourceTraces.length > 0 ? (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">数据来源追溯</h3>
              {sourceTraces.map((trace) => (
                <Card key={trace.source_id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline">{trace.source_type}</Badge>
                        <span className="font-medium">{trace.source_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={trace.verification_status === 'verified' ? 'default' : 'secondary'}
                        >
                          {trace.verification_status === 'verified' ? '已验证' : '未验证'}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">相关性评分:</span>
                          <span className={`ml-2 font-medium ${getConfidenceColor(trace.relevance_score)}`}>
                            {(trace.relevance_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">置信度贡献:</span>
                          <span className={`ml-2 font-medium ${getConfidenceColor(trace.confidence_contribution)}`}>
                            {(trace.confidence_contribution * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <div>
                        <span className="text-sm text-muted-foreground">内容片段:</span>
                        <p className="mt-1 text-sm bg-muted p-3 rounded border-l-4 border-blue-500">
                          {trace.content_snippet}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>暂无数据溯源信息</AlertTitle>
              <AlertDescription>
                当前答案没有具体的数据来源追溯记录。
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        {/* 替代答案标签页 */}
        <TabsContent value="alternatives" className="space-y-4">
          {alternativeAnswers.length > 0 ? (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">替代答案方案</h3>
              {alternativeAnswers.map((alternative) => (
                <Card key={alternative.answer_id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Button
                          variant={selectedAlternative === alternative.answer_id ? "default" : "outline"}
                          size="sm"
                          onClick={() => setSelectedAlternative(
                            selectedAlternative === alternative.answer_id ? null : alternative.answer_id
                          )}
                        >
                          {alternative.title}
                        </Button>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {alternative.scenario_description}
                      </div>
                    </div>
                  </CardHeader>
                  {selectedAlternative === alternative.answer_id && (
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-medium mb-2">替代答案内容</h4>
                          <p className="text-sm bg-muted p-3 rounded">{alternative.content}</p>
                        </div>

                        <div>
                          <h4 className="font-medium mb-2">推理差异</h4>
                          <ul className="text-sm space-y-1">
                            {alternative.reasoning_differences.map((diff, idx) => (
                              <li key={idx} className="flex items-start gap-2">
                                <TrendingUp className="h-3 w-3 mt-0.5 text-blue-500" />
                                {diff}
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <h4 className="font-medium mb-2">置信度对比</h4>
                            <div className="space-y-2">
                              {Object.entries(alternative.confidence_comparison).map(([key, value]) => (
                                <div key={key} className="space-y-1">
                                  <div className="flex justify-between text-sm">
                                    <span>{key}</span>
                                    <span>{(value * 100).toFixed(0)}%</span>
                                  </div>
                                  <Progress value={value * 100} className="h-1" />
                                </div>
                              ))}
                            </div>
                          </div>

                          {(alternative.pros || alternative.cons) && (
                            <div>
                              <h4 className="font-medium mb-2">优缺点分析</h4>
                              <div className="space-y-2">
                                {alternative.pros && alternative.pros.length > 0 && (
                                  <div>
                                    <span className="text-sm font-medium text-green-600">优点:</span>
                                    <ul className="text-sm mt-1 space-y-1">
                                      {alternative.pros.map((pro, idx) => (
                                        <li key={idx} className="flex items-start gap-1">
                                          <CheckCircle2 className="h-3 w-3 mt-0.5 text-green-500" />
                                          {pro}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {alternative.cons && alternative.cons.length > 0 && (
                                  <div>
                                    <span className="text-sm font-medium text-red-600">缺点:</span>
                                    <ul className="text-sm mt-1 space-y-1">
                                      {alternative.cons.map((con, idx) => (
                                        <li key={idx} className="flex items-start gap-1">
                                          <AlertTriangle className="h-3 w-3 mt-0.5 text-red-500" />
                                          {con}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          ) : (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>暂无替代答案</AlertTitle>
              <AlertDescription>
                当前查询没有生成替代答案方案。
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};