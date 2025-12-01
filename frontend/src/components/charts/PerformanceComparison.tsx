'use client';

import React, { useCallback, useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import {
  Activity,
  AlertCircle,
  Award,
  BarChart3,
  Download,
  Plus,
  RefreshCw,
  Target,
  TrendingDown,
  TrendingUp,
  X,
} from 'lucide-react';
import {
  PerformanceComparisonProps,
  PerformanceMetrics,
} from '@/types/performance.types';
import { usePerformanceComparison } from '@/services/performanceService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loading } from '@/components/ui/loading';

// 注册 Chart.js 组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

// 策略颜色配置
const STRATEGY_COLORS = [
  {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-700',
    chart: '#3B82F6',
  },
  {
    bg: 'bg-green-50',
    border: 'border-green-200',
    text: 'text-green-700',
    chart: '#10B981',
  },
  {
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    text: 'text-purple-700',
    chart: '#8B5CF6',
  },
  {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    text: 'text-orange-700',
    chart: '#F97316',
  },
  {
    bg: 'bg-pink-50',
    border: 'border-pink-200',
    text: 'text-pink-700',
    chart: '#EC4899',
  },
  {
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    text: 'text-indigo-700',
    chart: '#6366F1',
  },
];

interface StrategyResult {
  id: string;
  name: string;
  metrics: PerformanceMetrics;
  color: string;
}

const METRIC_LABELS: Record<string, string> = {
  totalReturn: '总收益率',
  annualizedReturn: '年化收益率',
  maxDrawdown: '最大回撤',
  sharpeRatio: '夏普比率',
  sortinoRatio: 'Sortino比率',
  winRate: '胜率',
  profitLossRatio: '盈亏比',
  volatility: '波动率',
};

const formatMetricValue = (value: number, metricKey: string): string => {
  if (metricKey.includes('Rate') || metricKey.includes('Ratio')) {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (metricKey === 'maxDrawdown') {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (metricKey === 'totalReturn' || metricKey === 'annualizedReturn') {
    return `${(value * 100).toFixed(2)}%`;
  }
  return value.toFixed(2);
};

export const PerformanceComparison: React.FC<PerformanceComparisonProps> = ({
  strategyIds,
  benchmarkId,
  startDate,
  endDate,
  comparisonType = 'both',
  height = 400,
  className = '',
}) => {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    'totalReturn',
    'sharpeRatio',
    'maxDrawdown',
  ]);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);

  const {
    data: comparisonData,
    isLoading,
    error,
    refetch,
  } = usePerformanceComparison(strategyIds, benchmarkId);

  // 转换数据为图表格式
  const chartData = useMemo(() => {
    if (!comparisonData?.strategies?.length) {
      return null;
    }

    const labels = comparisonData.strategies.map((s) => s.name);

    // 根据选择的策略获取数据
    const strategiesToShow =
      selectedStrategies.length > 0
        ? comparisonData.strategies.filter((s) =>
            selectedStrategies.includes(s.id),
          )
        : comparisonData.strategies;

    const datasets = selectedMetrics.map((metricKey, index) => {
      const color = STRATEGY_COLORS[index % STRATEGY_COLORS.length];

      return {
        label: METRIC_LABELS[metricKey] || metricKey,
        data: strategiesToShow.map(
          (s) => s.metrics[metricKey as keyof PerformanceMetrics] as number,
        ),
        backgroundColor: `${color.chart}20`,
        borderColor: color.chart,
        borderWidth: 2,
        fill: true,
      };
    });

    return {
      labels,
      datasets,
    };
  }, [comparisonData, selectedMetrics, selectedStrategies]);

  // 关键指标对比数据
  const keyMetricsComparison = useMemo(() => {
    if (!comparisonData?.strategies?.length) {
      return [];
    }

    const metricsToShow = [
      { key: 'totalReturn', label: '总收益率', important: true },
      { key: 'sharpeRatio', label: '夏普比率', important: true },
      { key: 'maxDrawdown', label: '最大回撤', important: true },
      { key: 'winRate', label: '胜率', important: false },
      { key: 'profitLossRatio', label: '盈亏比', important: false },
      { key: 'volatility', label: '波动率', important: false },
    ];

    return metricsToShow.map((metric) => {
      const values = comparisonData.strategies.map((strategy) => ({
        strategyId: strategy.id,
        strategyName: strategy.name,
        value: strategy.metrics[
          metric.key as keyof PerformanceMetrics
        ] as number,
      }));

      // 找出最优值（最大或最小，取决于指标类型）
      let bestValue: number;
      if (metric.key === 'maxDrawdown' || metric.key === 'volatility') {
        bestValue = Math.min(...values.map((v) => v.value));
      } else {
        bestValue = Math.max(...values.map((v) => v.value));
      }

      return {
        metricKey: metric.key,
        label: metric.label,
        important: metric.important,
        values: values.map((v) => ({ ...v, isBest: v.value === bestValue })),
      };
    });
  }, [comparisonData]);

  // 图表配置
  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top' as const,
          labels: {
            font: {
              size: 12,
            },
          },
        },
        title: {
          display: true,
          text: '绩效指标对比',
          font: {
            size: 16,
            weight: 'bold' as const,
          },
        },
        tooltip: {
          callbacks: {
            label: (context: any) => {
              const metricKey = context.dataset.label;
              const value = context.parsed.y;
              return `${metricKey}: ${formatMetricValue(value, metricKey)}`;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback(value: any) {
              return typeof value === 'number' ? value.toFixed(2) : value;
            },
          },
        },
      },
    }),
    [],
  );

  const toggleMetric = useCallback((metricKey: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(metricKey)
        ? prev.filter((m) => m !== metricKey)
        : [...prev, metricKey],
    );
  }, []);

  const toggleStrategy = useCallback((strategyId: string) => {
    setSelectedStrategies((prev) =>
      prev.includes(strategyId)
        ? prev.filter((id) => id !== strategyId)
        : [...prev, strategyId],
    );
  }, []);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <Loading />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center text-red-600">
            <AlertCircle className="mr-2 h-5 w-5" />
            <span>加载绩效对比数据失败</span>
          </div>
          <Button onClick={() => refetch()} variant="outline" className="mt-4">
            <RefreshCw className="mr-2 h-4 w-4" />
            重试
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!comparisonData?.strategies?.length) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            <BarChart3 className="mx-auto h-12 w-12 mb-4 text-gray-300" />
            <p>暂无绩效对比数据</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 策略选择器 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Target className="mr-2 h-5 w-5" />
            对比策略选择
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {comparisonData.strategies.map((strategy, index) => {
              const color = STRATEGY_COLORS[index % STRATEGY_COLORS.length];
              const isSelected =
                !selectedStrategies.length ||
                selectedStrategies.includes(strategy.id);

              return (
                <Badge
                  key={strategy.id}
                  variant={isSelected ? 'default' : 'outline'}
                  className={`cursor-pointer transition-all ${isSelected ? `${color.bg} ${color.border}` : ''}`}
                  onClick={() => toggleStrategy(strategy.id)}
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: color.chart }}
                    />
                    {strategy.name}
                  </div>
                </Badge>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 指标选择器 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Activity className="mr-2 h-5 w-5" />
            选择对比指标
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {Object.entries(METRIC_LABELS).map(([key, label]) => (
              <Badge
                key={key}
                variant={selectedMetrics.includes(key) ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => toggleMetric(key)}
              >
                {label}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 对比图表 */}
      {(comparisonType === 'charts' || comparisonType === 'both') &&
        chartData && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <TrendingUp className="mr-2 h-5 w-5" />
                绩效指标对比图表
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div style={{ height: `${height}px` }}>
                <Line data={chartData} options={chartOptions} />
              </div>
            </CardContent>
          </Card>
        )}

      {/* 关键指标对比表格 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Award className="mr-2 h-5 w-5" />
            关键指标对比
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">指标</th>
                  {comparisonData.strategies.map((strategy, index) => {
                    const color =
                      STRATEGY_COLORS[index % STRATEGY_COLORS.length];
                    return (
                      <th key={strategy.id} className="text-left p-2">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: color.chart }}
                          />
                          {strategy.name}
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {keyMetricsComparison.map((metric) => (
                  <tr
                    key={metric.metricKey}
                    className="border-b hover:bg-gray-50"
                  >
                    <td
                      className={`p-2 font-medium ${metric.important ? 'text-blue-700' : ''}`}
                    >
                      {metric.label}
                    </td>
                    {metric.values.map((value, idx) => (
                      <td
                        key={value.strategyId}
                        className={`p-2 ${
                          value.isBest ? 'font-bold text-green-600' : ''
                        }`}
                      >
                        {formatMetricValue(value.value, metric.metricKey)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 text-sm text-gray-500 flex items-center gap-2">
            <span>🟢 绿色表示最优值</span>
            <span>•</span>
            <span>粗体表示该指标的最佳表现</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PerformanceComparison;
