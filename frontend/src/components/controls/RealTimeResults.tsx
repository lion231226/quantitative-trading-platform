'use client';

import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StrategyResult } from '@/types/parameter.types';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle,
  Clock,
  RefreshCw,
  Shield,
  Target,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

interface RealTimeResultsProps {
  result: StrategyResult | null;
  isLoading?: boolean;
  isUpdating?: boolean;
  error?: string | null;
  lastUpdate?: Date | null;
  onRefresh?: () => void;
  showDetails?: boolean;
  compact?: boolean;
  className?: string;
}

export function RealTimeResults({
  result,
  isLoading = false,
  isUpdating = false,
  error = null,
  lastUpdate = null,
  onRefresh,
  showDetails = true,
  compact = false,
  className = '',
}: RealTimeResultsProps) {
  // 计算性能指标等级
  const performanceGrade = useMemo(() => {
    if (!result) return null;

    const { totalReturn, sharpeRatio, maxDrawdown, winRate } = result;

    // 综合评分算法
    let score = 0;

    // 总收益率评分 (40%)
    if (totalReturn > 20) score += 40;
    else if (totalReturn > 10) score += 30;
    else if (totalReturn > 5) score += 20;
    else if (totalReturn > 0) score += 10;

    // 夏普比率评分 (30%)
    if (sharpeRatio > 2) score += 30;
    else if (sharpeRatio > 1.5) score += 25;
    else if (sharpeRatio > 1) score += 20;
    else if (sharpeRatio > 0.5) score += 15;
    else if (sharpeRatio > 0) score += 10;

    // 最大回撤评分 (20%)
    if (maxDrawdown < 5) score += 20;
    else if (maxDrawdown < 10) score += 15;
    else if (maxDrawdown < 15) score += 10;
    else if (maxDrawdown < 20) score += 5;

    // 胜率评分 (10%)
    if (winRate > 60) score += 10;
    else if (winRate > 50) score += 8;
    else if (winRate > 40) score += 6;
    else if (winRate > 30) score += 4;

    if (score >= 80) return { grade: 'A', color: 'green', label: '优秀' };
    if (score >= 70) return { grade: 'B', color: 'blue', label: '良好' };
    if (score >= 60) return { grade: 'C', color: 'yellow', label: '一般' };
    if (score >= 50) return { grade: 'D', color: 'orange', label: '较差' };
    return { grade: 'F', color: 'red', label: '很差' };
  }, [result]);

  // 格式化百分比
  const formatPercent = (value: number, decimals: number = 2) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  };

  // 格式化数字
  const formatNumber = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };

  if (compact) {
    return (
      <div
        className={`flex items-center space-x-4 p-4 bg-background border rounded-lg ${className}`}
      >
        <div className="flex items-center space-x-2">
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">策略表现</span>
        </div>

        {isLoading && (
          <div className="flex items-center space-x-2 text-blue-600">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span className="text-sm">分析中...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center space-x-2 text-red-600">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm">分析失败</span>
          </div>
        )}

        {result && !isLoading && (
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div
                className={`text-lg font-semibold ${result.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}
              >
                {formatPercent(result.totalReturn)}
              </div>
              <div className="text-xs text-muted-foreground">总收益</div>
            </div>
            {performanceGrade && (
              <div
                className={`px-2 py-1 rounded-full text-xs font-medium bg-${performanceGrade.color}-100 text-${performanceGrade.color}-800`}
              >
                {performanceGrade.grade}
              </div>
            )}
          </div>
        )}

        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading || isUpdating}
            className="ml-auto"
          >
            <RefreshCw
              className={`h-4 w-4 ${isUpdating ? 'animate-spin' : ''}`}
            />
          </Button>
        )}
      </div>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-blue-600" />
            <span>实时策略表现</span>
            {isUpdating && (
              <div className="flex items-center space-x-1 text-sm text-blue-600">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>更新中</span>
              </div>
            )}
          </CardTitle>

          <div className="flex items-center space-x-2">
            {lastUpdate && (
              <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{lastUpdate.toLocaleTimeString()}</span>
              </div>
            )}
            {onRefresh && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                disabled={isLoading || isUpdating}
              >
                <RefreshCw
                  className={`h-4 w-4 mr-1 ${isUpdating ? 'animate-spin' : ''}`}
                />
                刷新
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-8 space-y-3">
            <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
            <div className="text-center">
              <p className="font-medium text-blue-900">正在分析策略表现</p>
              <p className="text-sm text-blue-700">这可能需要几秒钟时间</p>
            </div>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-8 space-y-3">
            <AlertTriangle className="h-8 w-8 text-red-600" />
            <div className="text-center">
              <p className="font-medium text-red-900">策略分析失败</p>
              <p className="text-sm text-red-700">{error}</p>
              {onRefresh && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRefresh}
                  className="mt-3"
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  重试
                </Button>
              )}
            </div>
          </div>
        )}

        {result && !isLoading && !error && (
          <>
            {/* 综合评级 */}
            {performanceGrade && (
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-12 h-12 rounded-full bg-${performanceGrade.color}-100 flex items-center justify-center`}
                  >
                    <span
                      className={`text-xl font-bold text-${performanceGrade.color}-800`}
                    >
                      {performanceGrade.grade}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium">{performanceGrade.label}表现</p>
                    <p className="text-sm text-muted-foreground">
                      综合评分算法
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className={`text-lg font-semibold ${result.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}
                  >
                    {formatPercent(result.totalReturn)}
                  </div>
                  <div className="text-sm text-muted-foreground">总收益率</div>
                </div>
              </div>
            )}

            {/* 关键指标 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium">总收益率</span>
                </div>
                <div
                  className={`text-xl font-bold ${result.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}
                >
                  {formatPercent(result.totalReturn)}
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Activity className="h-4 w-4 text-purple-600" />
                  <span className="text-sm font-medium">夏普比率</span>
                </div>
                <div className="text-xl font-bold text-purple-600">
                  {formatNumber(result.sharpeRatio)}
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Shield className="h-4 w-4 text-orange-600" />
                  <span className="text-sm font-medium">最大回撤</span>
                </div>
                <div className="text-xl font-bold text-orange-600">
                  {formatPercent(result.maxDrawdown)}
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Target className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium">胜率</span>
                </div>
                <div className="text-xl font-bold text-green-600">
                  {formatPercent(result.winRate)}
                </div>
              </Card>
            </div>

            {/* 详细指标 */}
            {showDetails && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium flex items-center space-x-2">
                  <BarChart3 className="h-4 w-4" />
                  <span>详细指标</span>
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-sm text-muted-foreground">
                        总交易次数
                      </span>
                      <span className="font-medium">{result.totalTrades}</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-sm text-muted-foreground">
                        盈利因子
                      </span>
                      <span className="font-medium">
                        {formatNumber(result.profitFactor)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-sm text-muted-foreground">
                        平均交易
                      </span>
                      <span className="font-medium">
                        {result.averageTrade
                          ? formatPercent(result.averageTrade)
                          : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-sm text-muted-foreground">
                        波动率
                      </span>
                      <span className="font-medium">
                        {result.volatility
                          ? formatPercent(result.volatility)
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-sm text-muted-foreground">
                        卡尔玛比率
                      </span>
                      <span className="font-medium">
                        {result.calmarRatio
                          ? formatNumber(result.calmarRatio)
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-sm text-muted-foreground">
                        期望值
                      </span>
                      <span className="font-medium">
                        {result.expectancy
                          ? formatNumber(result.expectancy)
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 风险提示 */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div className="text-sm text-yellow-800">
                  <p className="font-medium mb-1">风险提示</p>
                  <ul className="space-y-1">
                    <li>• 回测结果基于历史数据，不保证未来表现</li>
                    <li>• 市场条件变化可能影响策略效果</li>
                    <li>• 建议结合其他指标进行综合判断</li>
                    <li>• 实际交易可能存在滑点、手续费等额外成本</li>
                  </ul>
                </div>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default RealTimeResults;
