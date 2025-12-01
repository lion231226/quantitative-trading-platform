'use client';

import { useMemo, useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ComparisonTable } from './ComparisonTable';
import { ComparisonCharts } from './ComparisonCharts';
import { ComparisonRankings } from './ComparisonRankings';
import { Loading } from '@/components/ui/loading';
import {
  VarietyComparisonResult,
  VarietyResult,
} from '@/types/comparison.types';
import { cn } from '@/lib/utils';

interface ComparisonResultsProps {
  results?: VarietyComparisonResult;
  loading?: boolean;
  error?: string;
  className?: string;
}

export function ComparisonResults({
  results,
  loading,
  error,
  className,
}: ComparisonResultsProps) {
  const [selectedView, setSelectedView] = useState<
    'overview' | 'charts' | 'table' | 'rankings'
  >('overview');

  // 处理结果数据
  const processedData = useMemo(() => {
    if (!results) return null;

    const successfulResults = results.results.filter((r) => !r.error);
    const failedResults = results.results.filter((r) => r.error);

    return {
      successful: successfulResults,
      failed: failedResults,
      summary: results.summary,
      rankings: results.rankings,
      request: results.request,
    };
  }, [results]);

  if (loading) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center space-y-4">
            <Loading text="正在生成对比分析结果..." />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={cn('border-red-200 bg-red-50', className)}>
        <CardContent className="py-8">
          <div className="text-center text-red-600">
            <div className="font-medium mb-2">结果加载失败</div>
            <div className="text-sm">{error}</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!results || !processedData) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            <div>暂无对比分析结果</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* 结果头部 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>对比分析结果</span>
            <div className="flex gap-2">
              <Badge variant="outline">
                {processedData.successful.length}/
                {processedData.request.symbols.length} 成功
              </Badge>
              <Badge variant="outline">
                {processedData.request.strategy.name} 策略
              </Badge>
            </div>
          </CardTitle>
          <CardDescription>
            基于策略 {processedData.request.strategy.name} 的多品种对比分析结果
          </CardDescription>
        </CardHeader>
      </Card>

      {/* 失败品种提示 */}
      {processedData.failed.length > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader>
            <CardTitle className="text-orange-800">分析失败品种</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {processedData.failed.map((result) => (
                <div
                  key={result.symbol}
                  className="flex items-center justify-between"
                >
                  <div>
                    <span className="font-medium">{result.symbol}</span>
                    <span className="text-sm text-orange-600 ml-2">
                      {result.error}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 结果视图选择 */}
      <Tabs
        value={selectedView}
        onValueChange={(value) => setSelectedView(value as any)}
      >
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="charts">图表分析</TabsTrigger>
          <TabsTrigger value="table">详细表格</TabsTrigger>
          <TabsTrigger value="rankings">排名分析</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <ComparisonOverview data={processedData} />
        </TabsContent>

        <TabsContent value="charts" className="space-y-4">
          <ComparisonCharts results={processedData.successful} />
        </TabsContent>

        <TabsContent value="table" className="space-y-4">
          <ComparisonTable results={processedData.successful} />
        </TabsContent>

        <TabsContent value="rankings" className="space-y-4">
          <ComparisonRankings rankings={processedData.rankings} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// 概览组件
function ComparisonOverview({ data }: { data: any }) {
  const topPerformers = data.successful
    .sort(
      (a: VarietyResult, b: VarietyResult) =>
        b.metrics.totalReturn - a.metrics.totalReturn,
    )
    .slice(0, 3);

  const riskAdjustedTopPerformers = data.successful
    .sort(
      (a: VarietyResult, b: VarietyResult) =>
        b.metrics.sharpeRatio - a.metrics.sharpeRatio,
    )
    .slice(0, 3);

  const lowestRisk = data.successful
    .sort(
      (a: VarietyResult, b: VarietyResult) =>
        a.metrics.maxDrawdown - b.metrics.maxDrawdown,
    )
    .slice(0, 3);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {/* 收益率排名 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">收益率TOP 3</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {topPerformers.map((result: VarietyResult, index: number) => (
              <div
                key={result.symbol}
                className="flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <Badge variant={index === 0 ? 'default' : 'secondary'}>
                    {index + 1}
                  </Badge>
                  <div>
                    <div className="font-medium">{result.symbol}</div>
                    <div className="text-sm text-muted-foreground">
                      {result.name}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium text-green-600">
                    {(result.metrics.totalReturn * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    夏普 {result.metrics.sharpeRatio.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 风险调整收益排名 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">夏普比率TOP 3</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {riskAdjustedTopPerformers.map(
              (result: VarietyResult, index: number) => (
                <div
                  key={result.symbol}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center space-x-3">
                    <Badge variant={index === 0 ? 'default' : 'secondary'}>
                      {index + 1}
                    </Badge>
                    <div>
                      <div className="font-medium">{result.symbol}</div>
                      <div className="text-sm text-muted-foreground">
                        {result.name}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium text-blue-600">
                      {result.metrics.sharpeRatio.toFixed(2)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      收益 {(result.metrics.totalReturn * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              ),
            )}
          </div>
        </CardContent>
      </Card>

      {/* 风险控制排名 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">风险控制TOP 3</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {lowestRisk.map((result: VarietyResult, index: number) => (
              <div
                key={result.symbol}
                className="flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <Badge variant={index === 0 ? 'default' : 'secondary'}>
                    {index + 1}
                  </Badge>
                  <div>
                    <div className="font-medium">{result.symbol}</div>
                    <div className="text-sm text-muted-foreground">
                      {result.name}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium text-red-600">
                    {(result.metrics.maxDrawdown * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    收益 {(result.metrics.totalReturn * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 统计摘要 */}
      <Card className="md:col-span-2 lg:col-span-3">
        <CardHeader>
          <CardTitle>统计摘要</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div className="text-center">
              <div className="text-lg font-bold text-blue-600">
                {(data.summary.averageReturn * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-muted-foreground">平均收益率</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-green-600">
                {data.summary.averageSharpeRatio.toFixed(2)}
              </div>
              <div className="text-sm text-muted-foreground">平均夏普比率</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-red-600">
                {(
                  (data.successful.reduce(
                    (sum: number, r: VarietyResult) =>
                      sum + r.metrics.maxDrawdown,
                    0,
                  ) /
                    data.successful.length) *
                  100
                ).toFixed(1)}
                %
              </div>
              <div className="text-sm text-muted-foreground">平均最大回撤</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-purple-600">
                {(
                  data.successful.reduce(
                    (sum: number, r: VarietyResult) =>
                      sum + r.metrics.totalTrades,
                    0,
                  ) / data.successful.length
                ).toFixed(0)}
              </div>
              <div className="text-sm text-muted-foreground">平均交易次数</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-orange-600">
                {(
                  (data.successful.reduce(
                    (sum: number, r: VarietyResult) => sum + r.metrics.winRate,
                    0,
                  ) /
                    data.successful.length) *
                  100
                ).toFixed(0)}
                %
              </div>
              <div className="text-sm text-muted-foreground">平均胜率</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-600">
                {data.summary.dateRange.tradingDays}
              </div>
              <div className="text-sm text-muted-foreground">交易天数</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
