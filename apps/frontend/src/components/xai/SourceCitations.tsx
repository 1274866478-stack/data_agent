import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import {
  Search,
  Database,
  FileText,
  Globe,
  Link,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Eye,
  ExternalLink,
  Filter,
  Copy,
  Download,
  BarChart3
} from 'lucide-react';

interface SourceTrace {
  source_id: string;
  source_type: string;
  source_name: string;
  content_snippet: string;
  relevance_score: number;
  confidence_contribution: number;
  verification_status: string;
  trace_path?: string[];
  extraction_method?: string;
  metadata?: Record<string, any>;
}

interface SourceStats {
  total_sources: number;
  verified_sources: number;
  average_relevance: number;
  source_type_distribution: Record<string, number>;
  confidence_distribution: {
    high: number;
    medium: number;
    low: number;
  };
}

interface SourceCitationsProps {
  sources?: SourceTrace[];
  answer?: string;
  query?: string;
  showStats?: boolean;
  allowSearch?: boolean;
  className?: string;
}

export const SourceCitations: React.FC<SourceCitationsProps> = ({
  sources = [],
  answer = '',
  query = '',
  showStats = true,
  allowSearch = true,
  className
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSourceType, setSelectedSourceType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'relevance' | 'confidence' | 'type'>('relevance');
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

  const getSourceTypeIcon = (type: string) => {
    switch (type) {
      case 'sql_query':
      case 'sql_results':
        return <Database className="h-4 w-4" />;
      case 'rag_retrieval':
      case 'rag_result':
        return <Search className="h-4 w-4" />;
      case 'document':
      case 'documents':
        return <FileText className="h-4 w-4" />;
      case 'api_response':
      case 'api':
        return <Globe className="h-4 w-4" />;
      default:
        return <Link className="h-4 w-4" />;
    }
  };

  const getSourceTypeColor = (type: string) => {
    switch (type) {
      case 'sql_query':
      case 'sql_results':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'rag_retrieval':
      case 'rag_result':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'document':
      case 'documents':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'api_response':
      case 'api':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getVerificationBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return <Badge className="bg-green-100 text-green-800">已验证</Badge>;
      case 'pending':
        return <Badge variant="secondary">待验证</Badge>;
      case 'failed':
        return <Badge variant="destructive">验证失败</Badge>;
      default:
        return <Badge variant="outline">未知</Badge>;
    }
  };

  // 计算统计信息
  const calculateStats = (): SourceStats => {
    const totalSources = sources.length;
    const verifiedSources = sources.filter(s => s.verification_status === 'verified').length;
    const averageRelevance = sources.length > 0
      ? sources.reduce((sum, s) => sum + s.relevance_score, 0) / sources.length
      : 0;

    const sourceTypeDistribution: Record<string, number> = {};
    sources.forEach(source => {
      sourceTypeDistribution[source.source_type] = (sourceTypeDistribution[source.source_type] || 0) + 1;
    });

    const confidenceDistribution = {
      high: sources.filter(s => s.confidence_contribution >= 0.8).length,
      medium: sources.filter(s => s.confidence_contribution >= 0.6 && s.confidence_contribution < 0.8).length,
      low: sources.filter(s => s.confidence_contribution < 0.6).length
    };

    return {
      total_sources: totalSources,
      verified_sources: verifiedSources,
      average_relevance: averageRelevance,
      source_type_distribution: sourceTypeDistribution,
      confidence_distribution: confidenceDistribution
    };
  };

  // 过滤和排序源数据
  const getFilteredSources = () => {
    let filtered = [...sources];

    // 按搜索词过滤
    if (searchTerm) {
      filtered = filtered.filter(source =>
        source.source_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        source.content_snippet.toLowerCase().includes(searchTerm.toLowerCase()) ||
        source.source_type.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // 按源类型过滤
    if (selectedSourceType !== 'all') {
      filtered = filtered.filter(source => source.source_type === selectedSourceType);
    }

    // 排序
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'relevance':
          return b.relevance_score - a.relevance_score;
        case 'confidence':
          return b.confidence_contribution - a.confidence_contribution;
        case 'type':
          return a.source_type.localeCompare(b.source_type);
        default:
          return 0;
      }
    });

    return filtered;
  };

  const toggleSourceExpansion = (sourceId: string) => {
    setExpandedSources(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sourceId)) {
        newSet.delete(sourceId);
      } else {
        newSet.add(sourceId);
      }
      return newSet;
    });
  };

  const copyCitation = (source: SourceTrace) => {
    const citation = `[${source.source_type}] ${source.source_name}`;
    navigator.clipboard.writeText(citation);
  };

  const stats = calculateStats();
  const filteredSources = getFilteredSources();
  const uniqueSourceTypes = Array.from(new Set(sources.map(s => s.source_type)));

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 头部信息 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Link className="h-5 w-5" />
                数据源引用与溯源
              </CardTitle>
              <CardDescription>
                追踪答案的数据来源，验证信息可靠性
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">
                {sources.length} 个数据源
              </Badge>
              <Badge variant="outline">
                {stats.verified_sources} 已验证
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* 统计信息 */}
          {showStats && sources.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats.total_sources}</div>
                <div className="text-sm text-muted-foreground">总数据源</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.verified_sources}</div>
                <div className="text-sm text-muted-foreground">已验证源</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{(stats.average_relevance * 100).toFixed(0)}%</div>
                <div className="text-sm text-muted-foreground">平均相关性</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{uniqueSourceTypes.length}</div>
                <div className="text-sm text-muted-foreground">源类型</div>
              </div>
            </div>
          )}

          {/* 搜索和过滤控件 */}
          {allowSearch && sources.length > 0 && (
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索数据源..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <select
                value={selectedSourceType}
                onChange={(e) => setSelectedSourceType(e.target.value)}
                className="px-3 py-2 border rounded-md bg-background"
              >
                <option value="all">所有类型</option>
                {uniqueSourceTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-3 py-2 border rounded-md bg-background"
              >
                <option value="relevance">按相关性排序</option>
                <option value="confidence">按置信度排序</option>
                <option value="type">按类型排序</option>
              </select>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 主要内容 */}
      {sources.length > 0 ? (
        <Tabs defaultValue="list" className="w-full">
          <TabsList>
            <TabsTrigger value="list">源列表</TabsTrigger>
            <TabsTrigger value="stats">统计分析</TabsTrigger>
            <TabsTrigger value="trace">溯源路径</TabsTrigger>
          </TabsList>

          {/* 源列表视图 */}
          <TabsContent value="list" className="space-y-4">
            {filteredSources.length > 0 ? (
              filteredSources.map((source) => {
                const isExpanded = expandedSources.has(source.source_id);

                return (
                  <Card key={source.source_id}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getSourceTypeIcon(source.source_type)}
                          <div>
                            <CardTitle className="text-lg">{source.source_name}</CardTitle>
                            <CardDescription>ID: {source.source_id}</CardDescription>
                          </div>
                          <Badge className={getSourceTypeColor(source.source_type)}>
                            {source.source_type}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          {getVerificationBadge(source.verification_status)}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleSourceExpansion(source.source_id)}
                          >
                            {isExpanded ? <Eye className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => copyCitation(source)}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>

                    <CardContent>
                      <div className="space-y-4">
                        {/* 评分信息 */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <span className="text-sm text-muted-foreground">相关性评分:</span>
                            <div className="flex items-center gap-2 mt-1">
                              <div className="flex-1 bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-blue-600 h-2 rounded-full"
                                  style={{ width: `${source.relevance_score * 100}%` }}
                                />
                              </div>
                              <span className={`text-sm font-medium ${getRelevanceColor(source.relevance_score)}`}>
                                {(source.relevance_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          <div>
                            <span className="text-sm text-muted-foreground">置信度贡献:</span>
                            <div className="flex items-center gap-2 mt-1">
                              <div className="flex-1 bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-green-600 h-2 rounded-full"
                                  style={{ width: `${source.confidence_contribution * 100}%` }}
                                />
                              </div>
                              <span className={`text-sm font-medium ${getRelevanceColor(source.confidence_contribution)}`}>
                                {(source.confidence_contribution * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* 内容片段 */}
                        <div>
                          <span className="text-sm text-muted-foreground">内容片段:</span>
                          <p className="mt-1 text-sm bg-muted p-3 rounded border-l-4 border-blue-500">
                            {source.content_snippet}
                          </p>
                        </div>

                        {/* 展开的详细信息 */}
                        {isExpanded && (
                          <div className="space-y-4 border-t pt-4">
                            {source.trace_path && source.trace_path.length > 0 && (
                              <div>
                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                  <Link className="h-4 w-4" />
                                  追踪路径
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                  {source.trace_path.map((path, idx) => (
                                    <Badge key={idx} variant="outline" className="text-xs">
                                      {path}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}

                            {source.extraction_method && (
                              <div>
                                <h4 className="font-medium mb-2">提取方法</h4>
                                <Badge variant="secondary">{source.extraction_method}</Badge>
                              </div>
                            )}

                            {source.metadata && Object.keys(source.metadata).length > 0 && (
                              <div>
                                <h4 className="font-medium mb-2">元数据</h4>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  {Object.entries(source.metadata).map(([key, value]) => (
                                    <div key={key} className="bg-muted p-2 rounded">
                                      <span className="font-medium">{key}:</span>
                                      <span className="ml-1">{String(value)}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            ) : (
              <Alert>
                <Search className="h-4 w-4" />
                <AlertTitle>未找到匹配的数据源</AlertTitle>
                <AlertDescription>
                  尝试调整搜索条件或过滤器设置。
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>

          {/* 统计分析视图 */}
          <TabsContent value="stats" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 源类型分布 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    源类型分布
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(stats.source_type_distribution).map(([type, count]) => (
                      <div key={type} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <div className="flex items-center gap-2">
                            {getSourceTypeIcon(type)}
                            <span>{type}</span>
                          </div>
                          <span>{count}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${(count / stats.total_sources) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 置信度分布 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    置信度分布
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>高置信度 (≥80%)</span>
                        <span className="text-green-600">{stats.confidence_distribution.high}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full"
                          style={{ width: `${(stats.confidence_distribution.high / stats.total_sources) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>中等置信度 (60-80%)</span>
                        <span className="text-yellow-600">{stats.confidence_distribution.medium}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-yellow-600 h-2 rounded-full"
                          style={{ width: `${(stats.confidence_distribution.medium / stats.total_sources) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>低置信度 (&lt;60%)</span>
                        <span className="text-red-600">{stats.confidence_distribution.low}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-red-600 h-2 rounded-full"
                          style={{ width: `${(stats.confidence_distribution.low / stats.total_sources) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* 溯源路径视图 */}
          <TabsContent value="trace" className="space-y-4">
            {sources.map((source) => (
              <Card key={source.source_id}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    {getSourceTypeIcon(source.source_type)}
                    <div>
                      <CardTitle className="text-lg">{source.source_name}</CardTitle>
                      <CardDescription>溯源路径分析</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {source.trace_path && source.trace_path.length > 0 ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Link className="h-4 w-4" />
                        溯源路径:
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {source.trace_path.map((path, idx) => (
                          <div key={idx} className="flex items-center">
                            <Badge variant="outline">{path}</Badge>
                            {idx < source.trace_path!.length - 1 && (
                              <div className="w-4 h-0.5 bg-muted mx-2" />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">该数据源没有详细的溯源路径信息。</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </TabsContent>
        </Tabs>
      ) : (
        <Card>
          <CardContent className="py-8 text-center">
            <Link className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">暂无数据源引用</h3>
            <p className="text-muted-foreground">
              当前答案没有可追溯的数据源信息。
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};