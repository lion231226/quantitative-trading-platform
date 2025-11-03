'use client';

import React, { useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import {
  CategoryScale,
  Chart as ChartJS,
  ChartData as ChartJSData,
  ChartOptions,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import { TradingSignal } from '@/types/chart.types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// 注册 Chart.js 组件
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

// 组件Props
export interface TradingSignalsProps {
  signals: TradingSignal[]
  onSignalClick?: (signal: TradingSignal) => void
  className?: string
  height?: number
  width?: number
}

export function TradingSignals({
  signals,
  onSignalClick,
  className = '',
  height = 300,
  width,
}: TradingSignalsProps) {
  // 按类型分组信号
  const { buySignals, sellSignals } = useMemo(() => {
    const buy = signals.filter(s => s.type === 'buy');
    const sell = signals.filter(s => s.type === 'sell');
    return { buySignals: buy, sellSignals: sell };
  }, [signals]);

  // 生成图表数据
  const chartData = useMemo<ChartJSData<'scatter'>>(() => {
    return {
      datasets: [
        {
          label: '买入信号',
          data: buySignals.map(signal => ({
            x: new Date(signal.timestamp).getTime(),
            y: signal.price,
          })),
          backgroundColor: 'rgba(34, 197, 94, 0.8)',
          borderColor: 'rgb(34, 197, 94)',
          pointRadius: 8,
          pointHoverRadius: 10,
          showLine: false,
        },
        {
          label: '卖出信号',
          data: sellSignals.map(signal => ({
            x: new Date(signal.timestamp).getTime(),
            y: signal.price,
          })),
          backgroundColor: 'rgba(239, 68, 68, 0.8)',
          borderColor: 'rgb(239, 68, 68)',
          pointRadius: 8,
          pointHoverRadius: 10,
          showLine: false,
        },
      ],
    };
  }, [buySignals, sellSignals]);

  // 生成图表选项
  const chartOptions = useMemo<ChartOptions<'scatter'>>(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'nearest',
      intersect: true,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
      tooltip: {
        enabled: true,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: '#ddd',
        borderWidth: 1,
        padding: 10,
        displayColors: true,
        callbacks: {
          title: (context) => {
            const signal = context[0];
            const xValue = signal?.parsed?.x;
            return xValue !== null && xValue !== undefined ? new Date(xValue).toLocaleString() : '';
          },
          label: (context) => {
            const datasetIndex = context.datasetIndex;
            const signal = datasetIndex === 0 ? buySignals[context.dataIndex] : sellSignals[context.dataIndex];
            return [
              `类型: ${signal.type === 'buy' ? '买入' : '卖出'}`,
              `价格: ${signal.price.toFixed(2)}`,
              `策略: ${signal.strategy}`,
            ];
          },
        },
      },
    },
    scales: {
      x: {
        type: 'time',
        time: {
          displayFormats: {
            day: 'MM/dd',
            month: 'MM/dd',
          },
        },
        title: {
          display: true,
          text: '时间',
        },
      },
      y: {
        title: {
          display: true,
          text: '价格',
        },
        ticks: {
          callback: (value) => Number(value).toFixed(2),
        },
      },
    },
    onClick: (event, elements) => {
      if (elements.length > 0 && onSignalClick) {
        const element = elements[0];
        const datasetIndex = element.datasetIndex;
        const index = element.index;
        const signal = datasetIndex === 0 ? buySignals[index] : sellSignals[index];
        if (signal) {
          onSignalClick(signal);
        }
      }
    },
  }), [buySignals, sellSignals, onSignalClick]);

  // 渲染统计信息
  const renderStats = () => {
    const totalSignals = signals.length;
    const buyCount = buySignals.length;
    const sellCount = sellSignals.length;
    const recentSignal = signals.length > 0 ? signals[signals.length - 1] : null;

    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 border-b">
        <div className="text-center">
          <div className="text-lg font-semibold">{totalSignals}</div>
          <div className="text-xs text-gray-600">总信号数</div>
        </div>

        <div className="text-center">
          <div className="text-lg font-semibold text-green-600">{buyCount}</div>
          <div className="text-xs text-gray-600">买入信号</div>
        </div>

        <div className="text-center">
          <div className="text-lg font-semibold text-red-600">{sellCount}</div>
          <div className="text-xs text-gray-600">卖出信号</div>
        </div>

        <div className="text-center">
          <div className="text-lg font-semibold">
            {recentSignal ? (
              <span className={recentSignal.type === 'buy' ? 'text-green-600' : 'text-red-600'}>
                {recentSignal.type === 'buy' ? '买入' : '卖出'}
              </span>
            ) : (
              '-'
            )}
          </div>
          <div className="text-xs text-gray-600">最新信号</div>
        </div>
      </div>
    );
  };

  // 渲染信号列表
  const renderSignalList = () => {
    const recentSignals = signals.slice(-10).reverse();

    return (
      <div className="border-t pt-4">
        <h4 className="text-sm font-medium mb-3">最近信号</h4>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {recentSignals.map((signal, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-2 rounded border hover:bg-gray-50 cursor-pointer"
              onClick={() => onSignalClick?.(signal)}
            >
              <div className="flex items-center space-x-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    signal.type === 'buy' ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="text-sm font-medium">
                  {signal.type === 'buy' ? '买入' : '卖出'}
                </span>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium">{signal.price.toFixed(2)}</div>
                <div className="text-xs text-gray-500">
                  {new Date(signal.timestamp).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
          {recentSignals.length === 0 && (
            <div className="text-center text-gray-500 py-4">
              <div className="text-sm">暂无交易信号</div>
            </div>
          )}
        </div>
      </div>
    );
  };

  if (signals.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-center text-gray-500">
            <div className="text-lg font-medium mb-2">暂无交易信号</div>
            <div className="text-sm">请先运行策略以生成交易信号</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">交易信号分析</CardTitle>
        </CardHeader>
        {renderStats()}
        <CardContent className="p-0">
          <div style={{ height, width }}>
            <Line data={chartData as any} options={chartOptions as any} />
          </div>
        </CardContent>
        {renderSignalList()}
      </Card>
    </div>
  );
}

export default TradingSignals;