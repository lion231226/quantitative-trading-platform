'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading, LoadingSpinner } from '@/components/ui/loading';
import { strategyAPI } from '@/lib/api';
import { cn, formatPercentage } from '@/lib/utils';
import { StrategyRun } from '@/types/strategy';
import { StrategyResult } from '@/types/api';
import SimpleEquityCurve from '@/components/charts/SimpleEquityCurve';

interface ResultsDisplayProps {
  strategyRun: StrategyRun | null;
  onReset: () => void;
  className?: string;
}

export function ResultsDisplay({ strategyRun, onReset, className }: ResultsDisplayProps) {
  const [result, setResult] = useState<StrategyResult & { rawData?: any } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (strategyRun?.id && strategyRun.status === 'completed') {
      loadResults(strategyRun.id);
    }
  }, [strategyRun]);

  const loadResults = async (strategyId: string) => {
    try {
      setLoading(true);
      const data = await strategyAPI.getResults(strategyId);
      setResult(data);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载策略结果失败');
      console.error('Failed to load results:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!strategyRun) {
    return null;
  }

  if (strategyRun.status === 'running' || strategyRun.status === 'pending') {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>策略运行中</CardTitle>
          <CardDescription>正在执行策略回测，请稍候...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="mt-4 text-muted-foreground">
                {strategyRun?.progress !== undefined ? `进度: ${strategyRun.progress}%` : '正在处理...'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (strategyRun.status === 'failed') {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>策略运行失败</CardTitle>
          <CardDescription>策略执行过程中发生错误</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="text-red-600 mb-4">
              {error || strategyRun?.error || '未知错误'}
            </div>
            <div className="space-x-2">
              <Button onClick={onReset} variant="outline">
                重新配置
              </Button>
              <Button onClick={() => window.location.reload()}>
                刷新页面
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (strategyRun.status === 'completed' && loading) {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>加载结果中</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (strategyRun.status === 'completed' && error) {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>加载失败</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="text-red-600">{error}</div>
            <Button onClick={onReset} className="mt-4">
              重新配置
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (strategyRun.status === 'completed' && result) {
    return (
      <div className="space-y-6">
        {/* 净值曲线图表 */}
        {result.rawData?.equity_curve && (
          <SimpleEquityCurve
            equityCurve={result.rawData.equity_curve}
            title="策略净值曲线"
            height={400}
            className="w-full"
            strategyInfo={
              result.rawData ? {
                symbol: result.rawData.symbol,
                strategyType: result.rawData.strategy_type,
                parameters: result.rawData.parameters,
                startDate: result.rawData.start_date,
                endDate: result.rawData.end_date,
              } : undefined
            }
          />
        )}

        <Card className={cn('', className)}>
          <CardHeader>
            <CardTitle>策略回测结果</CardTitle>
            <CardDescription>基于选定参数的历史回测表现</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {formatPercentage(result.total_return)}
                </div>
                <div className="text-sm text-muted-foreground">总收益率</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {formatPercentage(result.win_rate)}
                </div>
                <div className="text-sm text-muted-foreground">胜率</div>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">
                  {formatPercentage(result.max_drawdown)}
                </div>
                <div className="text-sm text-muted-foreground">最大回撤</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {result.sharpe_ratio.toFixed(2)}
                </div>
                <div className="text-sm text-muted-foreground">夏普比率</div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">交易统计</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span>总交易次数</span>
                    <span className="font-medium">{result.total_trades}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>盈利交易</span>
                    <span className="font-medium text-green-600">{result.profit_trades}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>亏损交易</span>
                    <span className="font-medium text-red-600">{result.loss_trades}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>平均收益</span>
                    <span className="font-medium">{formatPercentage(result.average_return)}</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">风险评估</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span>最大回撤</span>
                    <span className="font-medium text-orange-600">
                      {formatPercentage(result.max_drawdown)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>夏普比率</span>
                    <span className="font-medium">
                      {result.sharpe_ratio > 1 ? (
                        <span className="text-green-600">{result.sharpe_ratio.toFixed(2)}</span>
                      ) : (
                        <span className="text-red-600">{result.sharpe_ratio.toFixed(2)}</span>
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>收益风险比</span>
                    <span className="font-medium">
                      {((result.total_return / Math.abs(result.max_drawdown)) || 0).toFixed(2)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="flex gap-2 justify-center">
              <Button onClick={onReset} variant="outline">
                重新配置策略
              </Button>
              <Button
                onClick={() => window.print()}
                variant="default"
                className="bg-blue-600 hover:bg-blue-700"
              >
                打印报告
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
}