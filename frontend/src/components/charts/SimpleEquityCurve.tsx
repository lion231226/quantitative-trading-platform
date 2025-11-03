'use client';

import React, { useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import {
  CategoryScale,
  Chart as ChartJS,
  ChartData,
  ChartOptions,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// 注册 Chart.js 组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface SimpleEquityCurveProps {
  equityCurve: Array<{ date: string; equity: number }>;
  title?: string;
  height?: number;
  className?: string;
  strategyInfo?: {
    symbol: string;
    strategyType: string;
    parameters: {
      ma_period?: number;
      initial_capital?: number;
      [key: string]: any;
    };
    startDate?: string;
    endDate?: string;
  };
}

const SimpleEquityCurve: React.FC<SimpleEquityCurveProps> = ({
  equityCurve,
  title = '策略净值曲线',
  height = 400,
  className = '',
  strategyInfo,
}) => {
  // 生成图表数据
  const chartData = useMemo((): ChartData<'line'> => {
    if (!equityCurve || equityCurve.length === 0) {
      return {
        labels: [],
        datasets: [],
      };
    }

    // 处理数据：采样显示，避免数据点过多
    const maxPoints = 100;
    let sampledData = equityCurve;

    if (equityCurve.length > maxPoints) {
      const step = Math.floor(equityCurve.length / maxPoints);
      sampledData = equityCurve.filter((_, index) => index % step === 0);
    }

    const labels = sampledData.map(point => {
      const date = new Date(point.date);
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    });

    const equityValues = sampledData.map(point => point.equity);

    // 计算初始资金用于计算收益率
    const initialEquity = equityValues[0] || 100000;
    const returns = equityValues.map(equity => ((equity - initialEquity) / initialEquity) * 100);

    return {
      labels,
      datasets: [
        {
          label: '策略净值',
          data: equityValues,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
        {
          label: '收益率 (%)',
          data: returns,
          borderColor: '#3b82f6',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'y1',
        },
      ],
    };
  }, [equityCurve]);

  // 图表配置
  const chartOptions = useMemo((): ChartOptions<'line'> => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          font: {
            size: 12,
          },
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: '#ffffff',
        borderWidth: 1,
        padding: 12,
        displayColors: true,
        callbacks: {
          label: function(context) {
            const value = context.parsed.y;
            if (value === null || value === undefined) return '';

            const label = context.dataset.label || '';
            if (label === '策略净值') {
              return `${label}: ¥${value.toLocaleString()}`;
            } else {
              return `${label}: ${value.toFixed(2)}%`;
            }
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false,
        },
        ticks: {
          color: '#6b7280',
          maxRotation: 45,
          minRotation: 0,
          autoSkip: true,
          maxTicksLimit: 12,
        },
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        grid: {
          color: '#e5e7eb',
        },
        ticks: {
          color: '#6b7280',
          callback: function(value) {
            return '¥' + Number(value).toLocaleString();
          },
        },
        title: {
          display: true,
          text: '策略净值',
          color: '#6b7280',
        },
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        ticks: {
          color: '#6b7280',
          callback: function(value) {
            return value.toFixed(1) + '%';
          },
        },
        title: {
          display: true,
          text: '收益率',
          color: '#6b7280',
        },
      },
    },
    elements: {
      point: {
        radius: 0,
        hoverRadius: 4,
      },
      line: {
        borderWidth: 2,
        tension: 0.4,
      },
    },
  }), []);

  if (!equityCurve || equityCurve.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent style={{ height }}>
          <div className="flex items-center justify-center h-full text-gray-500">
            暂无净值曲线数据
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {strategyInfo && (
          <div className="text-sm text-muted-foreground space-y-1">
            <div className="flex flex-wrap gap-4">
              <span><strong>品种:</strong> {strategyInfo.symbol}</span>
              <span><strong>策略:</strong> {strategyInfo.strategyType === 'single_ma' ? '单均线策略' : strategyInfo.strategyType}</span>
              {strategyInfo.parameters.ma_period && (
                <span><strong>周期:</strong> {strategyInfo.parameters.ma_period}天</span>
              )}
              {strategyInfo.parameters.initial_capital && (
                <span><strong>初始资金:</strong> ¥{strategyInfo.parameters.initial_capital.toLocaleString()}</span>
              )}
            </div>
            {strategyInfo.startDate && strategyInfo.endDate && (
              <div><strong>时间范围:</strong> {strategyInfo.startDate} 至 {strategyInfo.endDate}</div>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent style={{ height }}>
        <Line data={chartData} options={chartOptions} />
      </CardContent>
    </Card>
  );
};

SimpleEquityCurve.displayName = 'SimpleEquityCurve';

export default SimpleEquityCurve;