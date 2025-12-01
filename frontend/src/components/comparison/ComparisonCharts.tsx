'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { VarietyResult } from '@/types/comparison.types';
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  RadialLinearScale,
  Title,
  Tooltip,
} from 'chart.js';
import { Bar, Doughnut, Line, Radar } from 'react-chartjs-2';

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale,
  ArcElement,
  Filler,
);

interface ComparisonChartsProps {
  results: VarietyResult[];
  className?: string;
}

export function ComparisonCharts({
  results,
  className,
}: ComparisonChartsProps) {
  // 颜色配置
  const colors = useMemo(
    () => [
      'rgb(59, 130, 246)', // blue-500
      'rgb(16, 185, 129)', // green-500
      'rgb(251, 146, 60)', // orange-400
      'rgb(147, 51, 234)', // purple-600
      'rgb(236, 72, 153)', // pink-500
      'rgb(245, 158, 11)', // amber-500
      'rgb(20, 184, 166)', // teal-500
      'rgb(239, 68, 68)', // red-500
      'rgb(107, 114, 128)', // gray-500
      'rgb(6, 182, 212)', // cyan-500
    ],
    [],
  );

  // 收益率对比数据
  const returnsChartData = useMemo(() => {
    const sortedResults = [...results].sort(
      (a, b) => b.metrics.totalReturn - a.metrics.totalReturn,
    );

    return {
      labels: sortedResults.map((r) => r.symbol),
      datasets: [
        {
          label: '总收益率',
          data: sortedResults.map((r) =>
            (r.metrics.totalReturn * 100).toFixed(2),
          ),
          backgroundColor: sortedResults.map(
            (_, index) => colors[index % colors.length],
          ),
          borderColor: sortedResults.map(
            (_, index) => colors[index % colors.length],
          ),
          borderWidth: 1,
        },
      ],
    };
  }, [results, colors]);

  // 风险指标对比数据
  const riskMetricsChartData = useMemo(() => {
    return {
      labels: results.map((r) => r.symbol),
      datasets: [
        {
          label: '最大回撤',
          data: results.map((r) => Math.abs(r.metrics.maxDrawdown * 100)),
          backgroundColor: 'rgba(239, 68, 68, 0.6)',
          borderColor: 'rgb(239, 68, 68)',
          borderWidth: 1,
        },
        {
          label: '波动率',
          data: results.map((r) => r.metrics.volatility * 100),
          backgroundColor: 'rgba(245, 158, 11, 0.6)',
          borderColor: 'rgb(245, 158, 11)',
          borderWidth: 1,
        },
      ],
    };
  }, [results]);

  // 夏普比率对比数据
  const sharpeRatioChartData = useMemo(() => {
    const sortedResults = [...results].sort(
      (a, b) => b.metrics.sharpeRatio - a.metrics.sharpeRatio,
    );

    return {
      labels: sortedResults.map((r) => r.symbol),
      datasets: [
        {
          label: '夏普比率',
          data: sortedResults.map((r) => r.metrics.sharpeRatio.toFixed(2)),
          backgroundColor: sortedResults.map((_, index) => {
            const value = sortedResults[index].metrics.sharpeRatio;
            if (value > 1.5) return 'rgba(16, 185, 129, 0.6)'; // green
            if (value > 1.0) return 'rgba(251, 146, 60, 0.6)'; // orange
            return 'rgba(239, 68, 68, 0.6)'; // red
          }),
          borderColor: sortedResults.map((_, index) => {
            const value = sortedResults[index].metrics.sharpeRatio;
            if (value > 1.5) return 'rgb(16, 185, 129)';
            if (value > 1.0) return 'rgb(251, 146, 60)';
            return 'rgb(239, 68, 68)';
          }),
          borderWidth: 1,
        },
      ],
    };
  }, [results]);

  // 雷达图数据
  const radarChartData = useMemo(() => {
    // 标准化指标到0-100范围
    const normalizeMetrics = (metrics: any) => {
      const maxReturn = Math.max(...results.map((r) => r.metrics.totalReturn));
      const maxSharpe = Math.max(...results.map((r) => r.metrics.sharpeRatio));
      const maxDrawdown = Math.max(
        ...results.map((r) => Math.abs(r.metrics.maxDrawdown)),
      );
      const maxVolatility = Math.max(
        ...results.map((r) => r.metrics.volatility),
      );
      const maxWinRate = Math.max(...results.map((r) => r.metrics.winRate));

      return [
        ((metrics.totalReturn / maxReturn) * 100).toFixed(1),
        ((metrics.sharpeRatio / maxSharpe) * 100).toFixed(1),
        ((1 - Math.abs(metrics.maxDrawdown) / maxDrawdown) * 100).toFixed(1),
        ((1 - metrics.volatility / maxVolatility) * 100).toFixed(1),
        ((metrics.winRate / maxWinRate) * 100).toFixed(1),
        ((metrics.profitFactor / 5) * 100).toFixed(1), // 假设5为盈亏比上限
      ];
    };

    return {
      labels: ['收益率', '夏普比率', '风险控制', '稳定性', '胜率', '盈亏比'],
      datasets: results.slice(0, 6).map((result, index) => ({
        label: result.symbol,
        data: normalizeMetrics(result.metrics),
        backgroundColor: colors[index % colors.length]
          .replace('rgb', 'rgba')
          .replace(')', ', 0.2)'),
        borderColor: colors[index % colors.length],
        borderWidth: 2,
        pointBackgroundColor: colors[index % colors.length],
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: colors[index % colors.length],
      })),
    };
  }, [results, colors]);

  // 版块分布数据
  const sectorDistributionData = useMemo(() => {
    const sectorCounts = results.reduce(
      (acc, result) => {
        acc[result.sector] = (acc[result.sector] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    return {
      labels: Object.keys(sectorCounts),
      datasets: [
        {
          data: Object.values(sectorCounts),
          backgroundColor: colors,
          borderColor: '#fff',
          borderWidth: 2,
        },
      ],
    };
  }, [results, colors]);

  // 交易统计数据
  const tradingStatsChartData = useMemo(() => {
    return {
      labels: results.map((r) => r.symbol),
      datasets: [
        {
          label: '总交易次数',
          data: results.map((r) => r.metrics.totalTrades),
          backgroundColor: 'rgba(59, 130, 246, 0.6)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 1,
        },
        {
          label: '盈利交易',
          data: results.map((r) => r.metrics.winningTrades),
          backgroundColor: 'rgba(16, 185, 129, 0.6)',
          borderColor: 'rgb(16, 185, 129)',
          borderWidth: 1,
        },
      ],
    };
  }, [results]);

  // 通用图表选项
  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
  };

  const barOptions = {
    ...commonOptions,
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  const radarOptions = {
    ...commonOptions,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: {
          stepSize: 20,
        },
      },
    },
  };

  return (
    <div className={cn('space-y-6', className)}>
      <Tabs defaultValue="returns" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
          <TabsTrigger value="returns">收益率</TabsTrigger>
          <TabsTrigger value="risk">风险指标</TabsTrigger>
          <TabsTrigger value="sharpe">夏普比率</TabsTrigger>
          <TabsTrigger value="radar">雷达图</TabsTrigger>
          <TabsTrigger value="sectors">版块分布</TabsTrigger>
          <TabsTrigger value="trading">交易统计</TabsTrigger>
        </TabsList>

        <TabsContent value="returns" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>收益率对比</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <Bar data={returnsChartData} options={barOptions} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="risk" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>风险指标对比</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <Bar data={riskMetricsChartData} options={barOptions} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sharpe" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>夏普比率对比</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <Bar data={sharpeRatioChartData} options={barOptions} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="radar" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>综合指标雷达图</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96">
                <Radar data={radarChartData} options={radarOptions} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sectors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>版块分布</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80 flex justify-center">
                <div className="w-80">
                  <Doughnut
                    data={sectorDistributionData}
                    options={commonOptions}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trading" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>交易统计对比</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <Bar data={tradingStatsChartData} options={barOptions} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
