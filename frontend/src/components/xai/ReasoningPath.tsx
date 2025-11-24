import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Button } from '../ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../ui/collapsible';
import {
  ArrowRight,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  Brain,
  Search,
  FileText,
  Database,
  GitBranch,
  Clock,
  Target,
  Info
} from 'lucide-react';

interface ReasoningStep {
  step_number: number;
  title: string;
  description: string;
  reasoning?: string;
  evidence?: string[];
  confidence: number;
  step_type: string;
  decision_factors?: Record<string, any>;
  assumptions?: string[];
  limitations?: string[];
  supporting_data?: any;
  child_step_ids?: string[];
  timestamp: string;
}

interface VisualizationNode {
  id: string;
  type: string;
  title: string;
  content: string;
  confidence: number;
  children: string[];
  parent?: string;
}

interface ReasoningPathProps {
  reasoningSteps?: ReasoningStep[];
  decisionTree?: Record<string, VisualizationNode>;
  processingTime?: number;
  showVisualization?: boolean;
  className?: string;
}

export const ReasoningPath: React.FC<ReasoningPathProps> = ({
  reasoningSteps = [],
  decisionTree = {},
  processingTime = 0,
  showVisualization = true,
  className
}) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set([1]));
  const [viewMode, setViewMode] = useState<'timeline' | 'tree' | 'detailed'>('timeline');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const getStepTypeIcon = (type: string) => {
    switch (type) {
      case 'analysis': return <Search className="h-4 w-4" />;
      case 'synthesis': return <GitBranch className="h-4 w-4" />;
      case 'validation': return <CheckCircle2 className="h-4 w-4" />;
      case 'evidence': return <FileText className="h-4 w-4" />;
      case 'data': return <Database className="h-4 w-4" />;
      default: return <Brain className="h-4 w-4" />;
    }
  };

  const getStepTypeColor = (type: string) => {
    switch (type) {
      case 'analysis': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'synthesis': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'validation': return 'bg-green-100 text-green-800 border-green-200';
      case 'evidence': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'data': return 'bg-orange-100 text-orange-800 border-orange-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString('zh-CN');
    } catch {
      return timestamp;
    }
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

  const renderStepConnector = (isLast: boolean) => {
    if (isLast) return null;

    return (
      <div className="flex justify-center">
        <ArrowRight className="h-5 w-5 text-muted-foreground" />
      </div>
    );
  };

  const renderTimeline = () => (
    <div className="space-y-4">
      {reasoningSteps.map((step, index) => {
        const isExpanded = expandedSteps.has(step.step_number);
        const isLast = index === reasoningSteps.length - 1;

        return (
          <div key={step.step_number} className="relative">
            {/* 连接线 */}
            {!isLast && (
              <div className="absolute left-6 top-12 w-0.5 h-8 bg-border" />
            )}

            {/* 步骤内容 */}
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${getStepTypeColor(step.step_type)} border`}>
                  {getStepTypeIcon(step.step_type)}
                </div>
                <Badge variant="outline" className="mt-2 text-xs">
                  步骤 {step.step_number}
                </Badge>
              </div>

              <div className="flex-1 min-w-0">
                <Card>
                  <Collapsible
                    open={isExpanded}
                    onOpenChange={() => toggleStepExpansion(step.step_number)}
                  >
                    <CollapsibleTrigger asChild>
                      <CardHeader className="pb-3 cursor-pointer hover:bg-muted/50 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="space-y-1">
                            <CardTitle className="text-lg">{step.title}</CardTitle>
                            <CardDescription>{step.description}</CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="text-right">
                              <div className={`text-sm font-medium ${getConfidenceColor(step.confidence)}`}>
                                置信度: {(step.confidence * 100).toFixed(0)}%
                              </div>
                              <Progress value={step.confidence * 100} className="w-16 h-1 mt-1" />
                            </div>
                            <Button variant="ghost" size="sm">
                              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </Button>
                          </div>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <CardContent className="pt-0">
                        <div className="space-y-4">
                          {/* 推理逻辑 */}
                          {step.reasoning && (
                            <div>
                              <h4 className="font-medium mb-2 flex items-center gap-2">
                                <Brain className="h-4 w-4" />
                                推理逻辑
                              </h4>
                              <p className="text-sm bg-muted p-3 rounded">{step.reasoning}</p>
                            </div>
                          )}

                          {/* 支持证据 */}
                          {step.evidence && step.evidence.length > 0 && (
                            <div>
                              <h4 className="font-medium mb-2 flex items-center gap-2">
                                <CheckCircle2 className="h-4 w-4" />
                                支持证据
                              </h4>
                              <ul className="text-sm space-y-2">
                                {step.evidence.map((evidence, idx) => (
                                  <li key={idx} className="flex items-start gap-2 bg-green-50 p-2 rounded border-l-4 border-green-500">
                                    <CheckCircle2 className="h-3 w-3 mt-0.5 text-green-600" />
                                    {evidence}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* 决策因素 */}
                          {step.decision_factors && Object.keys(step.decision_factors).length > 0 && (
                            <div>
                              <h4 className="font-medium mb-2 flex items-center gap-2">
                                <Target className="h-4 w-4" />
                                决策因素
                              </h4>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                                {Object.entries(step.decision_factors).map(([key, value]) => (
                                  <div key={key} className="bg-muted p-2 rounded">
                                    <span className="font-medium">{key}:</span>
                                    <span className="ml-1">{String(value)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* 假设和限制 */}
                          {(step.assumptions || step.limitations) && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {step.assumptions && step.assumptions.length > 0 && (
                                <div>
                                  <h4 className="font-medium mb-2 text-blue-600">假设条件</h4>
                                  <ul className="text-sm space-y-1">
                                    {step.assumptions.map((assumption, idx) => (
                                      <li key={idx} className="flex items-start gap-2">
                                        <AlertTriangle className="h-3 w-3 mt-0.5 text-blue-500" />
                                        {assumption}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {step.limitations && step.limitations.length > 0 && (
                                <div>
                                  <h4 className="font-medium mb-2 text-orange-600">限制因素</h4>
                                  <ul className="text-sm space-y-1">
                                    {step.limitations.map((limitation, idx) => (
                                      <li key={idx} className="flex items-start gap-2">
                                        <AlertTriangle className="h-3 w-3 mt-0.5 text-orange-500" />
                                        {limitation}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}

                          {/* 时间戳 */}
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {formatTimestamp(step.timestamp)}
                          </div>
                        </div>
                      </CardContent>
                    </CollapsibleContent>
                  </Collapsible>
                </Card>
              </div>
            </div>

            {/* 连接器 */}
            {renderStepConnector(isLast)}
          </div>
        );
      })}
    </div>
  );

  const renderTreeView = () => {
    if (!decisionTree || Object.keys(decisionTree).length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          没有决策树数据可显示
        </div>
      );
    }

    const TreeNode: React.FC<{ nodeId: string; level: number }> = ({ nodeId, level }) => {
      const node = decisionTree[nodeId];
      if (!node) return null;

      const isSelected = selectedNode === nodeId;
      const hasChildren = node.children && node.children.length > 0;

      return (
        <div className={`ml-${level * 4}`}>
          <div className={`p-3 border rounded-lg mb-2 cursor-pointer transition-colors ${
            isSelected ? 'bg-primary/10 border-primary' : 'hover:bg-muted'
          }`} onClick={() => setSelectedNode(isSelected ? null : nodeId)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getStepTypeIcon(node.type)}
                <span className="font-medium">{node.title}</span>
              </div>
              <Badge variant="outline">
                {(node.confidence * 100).toFixed(0)}%
              </Badge>
            </div>
            {isSelected && (
              <p className="text-sm text-muted-foreground mt-2">{node.content}</p>
            )}
          </div>

          {hasChildren && (
            <div className="ml-4 border-l-2 border-muted pl-2">
              {node.children.map((childId) => (
                <TreeNode key={childId} nodeId={childId} level={level + 1} />
              ))}
            </div>
          )}
        </div>
      );
    };

    const rootNode = Object.values(decisionTree).find(node => !node.parent);

    return (
      <div className="p-4 border rounded-lg bg-muted/50">
        <TreeNode nodeId={rootNode?.id || ''} level={0} />
      </div>
    );
  };

  const renderDetailedView = () => (
    <div className="space-y-6">
      {reasoningSteps.map((step) => (
        <Card key={step.step_number}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${getStepTypeColor(step.step_type)} border`}>
                  {getStepTypeIcon(step.step_type)}
                </div>
                <div>
                  <CardTitle className="text-lg">{step.title}</CardTitle>
                  <CardDescription>步骤 {step.step_number} - {step.step_type}</CardDescription>
                </div>
              </div>
              <Badge variant="outline">
                {(step.confidence * 100).toFixed(0)}%
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">描述</h4>
                  <p className="text-sm">{step.description}</p>
                </div>

                {step.reasoning && (
                  <div>
                    <h4 className="font-medium mb-2">推理逻辑</h4>
                    <p className="text-sm bg-muted p-3 rounded">{step.reasoning}</p>
                  </div>
                )}

                {step.supporting_data && (
                  <div>
                    <h4 className="font-medium mb-2">支持数据</h4>
                    <pre className="text-xs bg-muted p-3 rounded overflow-auto">
                      {JSON.stringify(step.supporting_data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                {step.evidence && step.evidence.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">支持证据</h4>
                    <ul className="text-sm space-y-1">
                      {step.evidence.map((evidence, idx) => (
                        <li key={idx} className="bg-green-50 p-2 rounded border-l-4 border-green-500">
                          {evidence}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {step.decision_factors && Object.keys(step.decision_factors).length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">决策因素</h4>
                    <div className="space-y-1 text-sm">
                      {Object.entries(step.decision_factors).map(([key, value]) => (
                        <div key={key} className="bg-muted p-2 rounded flex justify-between">
                          <span>{key}:</span>
                          <span>{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {formatTimestamp(step.timestamp)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 头部信息 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                推理路径分析
              </CardTitle>
              <CardDescription>
                详细展示AI系统的推理过程和决策逻辑
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">
                {reasoningSteps.length} 个步骤
              </Badge>
              {processingTime > 0 && (
                <Badge variant="outline">
                  {(processingTime / 1000).toFixed(1)}s
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {showVisualization && reasoningSteps.length > 1 && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium">整体推理路径:</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {reasoningSteps.map((step, index) => (
                  <div key={step.step_number} className="flex items-center">
                    <Badge
                      variant="outline"
                      className={`${getStepTypeColor(step.step_type)}`}
                    >
                      <Brain className="h-3 w-3 mr-1" />
                      {step.title}
                    </Badge>
                    {index < reasoningSteps.length - 1 && (
                      <ArrowRight className="h-3 w-3 mx-1 text-muted-foreground" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 视图切换 */}
          {reasoningSteps.length > 0 && (
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'timeline' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('timeline')}
              >
                时间线视图
              </Button>
              <Button
                variant={viewMode === 'tree' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('tree')}
              >
                决策树视图
              </Button>
              <Button
                variant={viewMode === 'detailed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('detailed')}
              >
                详细视图
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 主要内容 */}
      {reasoningSteps.length > 0 ? (
        <>
          {viewMode === 'timeline' && renderTimeline()}
          {viewMode === 'tree' && renderTreeView()}
          {viewMode === 'detailed' && renderDetailedView()}
        </>
      ) : (
        <Card>
          <CardContent className="py-8 text-center">
            <Info className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">暂无推理路径</h3>
            <p className="text-muted-foreground">
              当前答案没有详细的推理路径记录。
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};