'use client';

import { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { VarietySelector } from './VarietySelector';
import { ComparisonResults } from './ComparisonResults';
import { Loading } from '@/components/ui/loading';
import { useVarietyComparison, useComparisonCache } from '@/services/comparisonService';
import { VarietyComparisonRequest, VarietyComparisonResult } from '@/types/comparison.types';
import { cn } from '@/lib/utils';

interface MultiVarietyComparisonProps {
  className?: string
  initialRequest?: Partial<VarietyComparisonRequest>
  onConfigChange?: (config: VarietyComparisonRequest) => void
}

export function MultiVarietyComparison({
  className,
  initialRequest,
  onConfigChange
}: MultiVarietyComparisonProps) {
  // 状态管理
  const [selectedVarieties, setSelectedVarieties] = useState<string[]>(initialRequest?.symbols || []);
  const [requestConfig, setRequestConfig] = useState<VarietyComparisonRequest>({
    symbols: initialRequest?.symbols || [],
    startDate: initialRequest?.startDate || getDefaultStartDate(),
    endDate: initialRequest?.endDate || getDefaultEndDate(),
    strategy: initialRequest?.strategy || {
      name: 'SMA',
      params: { short_window: 5, long_window: 20 }
    }
  });

  // 对比分析查询
  const {
    data: comparisonResults,
    isLoading: isComparisonLoading,
    error: comparisonError,
    refetch: runComparison
  } = useVarietyComparison(requestConfig);

  // 缓存管理
  const { clearComparisonCache } = useComparisonCache();

  // 处理品种选择变化
  const handleVarietiesSelect = useCallback((varieties: string[]) => {
    setSelectedVarieties(varieties);

    const newConfig = {
      ...requestConfig,
      symbols: varieties
    };

    setRequestConfig(newConfig);
    onConfigChange?.(newConfig);
  }, [requestConfig, onConfigChange]);

  // 处理策略配置变化
  const handleStrategyChange = useCallback((strategy: VarietyComparisonRequest['strategy']) => {
    const newConfig = {
      ...requestConfig,
      strategy
    };

    setRequestConfig(newConfig);
    onConfigChange?.(newConfig);
  }, [requestConfig, onConfigChange]);

  // 处理日期范围变化
  const handleDateRangeChange = useCallback((startDate: string, endDate: string) => {
    const newConfig = {
      ...requestConfig,
      startDate,
      endDate
    };

    setRequestConfig(newConfig);
    onConfigChange?.(newConfig);
  }, [requestConfig, onConfigChange]);

  // 运行对比分析
  const handleRunComparison = useCallback(() => {
    if (selectedVarieties.length < 2) {
      alert('请选择至少2个期货品种进行对比分析');
      return;
    }

    runComparison();
  }, [selectedVarieties, runComparison]);

  // 重置配置
  const handleReset = useCallback(() => {
    const defaultConfig: VarietyComparisonRequest = {
      symbols: [],
      startDate: getDefaultStartDate(),
      endDate: getDefaultEndDate(),
      strategy: {
        name: 'SMA',
        params: { short_window: 5, long_window: 20 }
      }
    };

    setSelectedVarieties([]);
    setRequestConfig(defaultConfig);
    clearComparisonCache();
    onConfigChange?.(defaultConfig);
  }, [clearComparisonCache, onConfigChange]);

  // 计算状态统计
  const stats = useMemo(() => {
    if (!comparisonResults) return null;

    const successful = comparisonResults.results.filter(r => !r.error).length;
    const failed = comparisonResults.results.filter(r => r.error).length;
    const bestPerformer = comparisonResults.results
      .filter(r => !r.error)
      .reduce((best, current) =>
        current.metrics.totalReturn > best.metrics.totalReturn ? current : best
      );

    return {
      total: comparisonResults.results.length,
      successful,
      failed,
      bestPerformer,
      averageReturn: comparisonResults.summary.averageReturn,
      averageSharpe: comparisonResults.summary.averageSharpeRatio
    };
  }, [comparisonResults]);

  return (
    <div className={cn('space-y-6', className)}>
      {/* 头部信息 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>多品种对比分析</span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleReset}
                disabled={isComparisonLoading}
              >
                重置
              </Button>
              <Button
                onClick={handleRunComparison}
                disabled={selectedVarieties.length < 2 || isComparisonLoading}
              >
                {isComparisonLoading ? '分析中...' : '开始分析'}
              </Button>
            </div>
          </CardTitle>
          <CardDescription>
            选择多个期货品种进行策略表现对比分析，获取详细的绩效指标和排名
          </CardDescription>
        </CardHeader>
      </Card>

      {/* 配置区域 */}
      <Tabs defaultValue="varieties" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="varieties">品种选择</TabsTrigger>
          <TabsTrigger value="strategy">策略配置</TabsTrigger>
          <TabsTrigger value="dates">日期范围</TabsTrigger>
        </TabsList>

        <TabsContent value="varieties">
          <VarietySelector
            onVarietiesSelect={handleVarietiesSelect}
            selectedVarieties={selectedVarieties}
            maxSelection={10}
          />
        </TabsContent>

        <TabsContent value="strategy">
          <Card>
            <CardHeader>
              <CardTitle>策略配置</CardTitle>
              <CardDescription>配置用于对比分析的策略参数</CardDescription>
            </CardHeader>
            <CardContent>
              <StrategyConfigPanel
                strategy={requestConfig.strategy}
                onChange={handleStrategyChange}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dates">
          <Card>
            <CardHeader>
              <CardTitle>日期范围</CardTitle>
              <CardDescription>设置对比分析的时间范围</CardDescription>
            </CardHeader>
            <CardContent>
              <DateRangePanel
                startDate={requestConfig.startDate}
                endDate={requestConfig.endDate}
                onChange={handleDateRangeChange}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 加载状态 */}
      {isComparisonLoading && (
        <Card>
          <CardContent className="py-8">
            <div className="flex flex-col items-center space-y-4">
              <Loading text="正在进行多品种对比分析..." />
              <div className="text-sm text-muted-foreground">
                正在分析 {selectedVarieties.length} 个品种的策略表现
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 错误状态 */}
      {comparisonError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-6">
            <div className="text-center">
              <div className="text-red-600 font-medium mb-2">对比分析失败</div>
              <div className="text-sm text-red-500">
                {comparisonError instanceof Error ? comparisonError.message : '未知错误'}
              </div>
              <Button
                variant="outline"
                onClick={() => runComparison()}
                className="mt-4"
              >
                重试
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 统计信息 */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>分析概览</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
                <div className="text-sm text-muted-foreground">总品种数</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.successful}</div>
                <div className="text-sm text-muted-foreground">成功分析</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
                <div className="text-sm text-muted-foreground">分析失败</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {(stats.averageReturn * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-muted-foreground">平均收益率</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {stats.averageSharpe.toFixed(2)}
                </div>
                <div className="text-sm text-muted-foreground">平均夏普比率</div>
              </div>
            </div>

            {stats.bestPerformer && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-green-800">最佳表现品种</div>
                    <div className="text-sm text-green-600">
                      {stats.bestPerformer.symbol} - {stats.bestPerformer.name}
                    </div>
                  </div>
                  <Badge variant="secondary" className="bg-green-100 text-green-800">
                    {(stats.bestPerformer.metrics.totalReturn * 100).toFixed(1)}%
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 对比结果 */}
      {comparisonResults && !isComparisonLoading && (
        <ComparisonResults
          results={comparisonResults}
          loading={false}
          error={undefined}
        />
      )}

      {/* 空状态 */}
      {!comparisonResults && !isComparisonLoading && !comparisonError && (
        <Card>
          <CardContent className="py-12">
            <div className="text-center text-muted-foreground">
              <div className="text-lg font-medium mb-2">开始多品种对比分析</div>
              <div className="text-sm">
                选择至少2个期货品种，配置策略参数，然后点击"开始分析"
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// 策略配置面板组件
function StrategyConfigPanel({
  strategy,
  onChange
}: {
  strategy: VarietyComparisonRequest['strategy'];
  onChange: (strategy: VarietyComparisonRequest['strategy']) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium">策略类型</label>
        <select
          value={strategy.name}
          onChange={(e) => onChange({ ...strategy, name: e.target.value })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        >
          <option value="SMA">单均线策略</option>
          <option value="DMA">双均线策略</option>
          <option value="RSI">RSI策略</option>
          <option value="MACD">MACD策略</option>
        </select>
      </div>

      {strategy.name === 'SMA' && (
        <div className="space-y-2">
          <div>
            <label className="text-sm font-medium">均线周期</label>
            <input
              type="number"
              value={strategy.params.window || 20}
              onChange={(e) => onChange({
                ...strategy,
                params: { ...strategy.params, window: parseInt(e.target.value) }
              })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              min="5"
              max="200"
            />
          </div>
        </div>
      )}

      {strategy.name === 'DMA' && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">短期均线</label>
            <input
              type="number"
              value={strategy.params.short_window || 5}
              onChange={(e) => onChange({
                ...strategy,
                params: { ...strategy.params, short_window: parseInt(e.target.value) }
              })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              min="1"
              max="50"
            />
          </div>
          <div>
            <label className="text-sm font-medium">长期均线</label>
            <input
              type="number"
              value={strategy.params.long_window || 20}
              onChange={(e) => onChange({
                ...strategy,
                params: { ...strategy.params, long_window: parseInt(e.target.value) }
              })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              min="10"
              max="200"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// 日期范围面板组件
function DateRangePanel({
  startDate,
  endDate,
  onChange
}: {
  startDate: string;
  endDate: string;
  onChange: (startDate: string, endDate: string) => void;
}) {
  const presetRanges = [
    { label: '最近1个月', days: 30 },
    { label: '最近3个月', days: 90 },
    { label: '最近6个月', days: 180 },
    { label: '最近1年', days: 365 },
    { label: '今年至今', days: 'ytd' }
  ];

  const handlePresetClick = (days: number | string) => {
    const end = new Date();
    let start: Date;

    if (days === 'ytd') {
      start = new Date(end.getFullYear(), 0, 1);
    } else {
      start = new Date(end.getTime() - (days as number) * 24 * 60 * 60 * 1000);
    }

    onChange(
      start.toISOString().split('T')[0],
      end.toISOString().split('T')[0]
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {presetRanges.map((preset) => (
          <Button
            key={preset.label}
            variant="outline"
            size="sm"
            onClick={() => handlePresetClick(preset.days)}
          >
            {preset.label}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">开始日期</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => onChange(e.target.value, endDate)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
        <div>
          <label className="text-sm font-medium">结束日期</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => onChange(startDate, e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
      </div>
    </div>
  );
}

// 辅助函数
function getDefaultStartDate(): string {
  const date = new Date();
  date.setMonth(date.getMonth() - 3);
  return date.toISOString().split('T')[0];
}

function getDefaultEndDate(): string {
  return new Date().toISOString().split('T')[0];
}