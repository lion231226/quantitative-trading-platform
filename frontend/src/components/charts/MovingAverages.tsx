'use client';

import React, { useCallback, useMemo, useState } from 'react';
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
import { MovingAverageLine, PricePoint } from '@/types/chart.types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { calculateEMA, calculateSMA } from '@/utils/chartHelpers';

// 注册 Chart.js 组件
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

// 移动平均线配置接口
export interface MovingAverageConfig {
  type: 'SMA' | 'EMA'
  period: number
  color: string
  lineWidth: number
  showPoints: boolean
  fillArea: boolean
  fillOpacity: number
  animationDuration: number
}

// 默认配置
const DEFAULT_MA_CONFIG: MovingAverageConfig = {
  type: 'SMA',
  period: 20,
  color: 'rgb(239, 68, 68)',
  lineWidth: 2,
  showPoints: false,
  fillArea: false,
  fillOpacity: 0.1,
  animationDuration: 1000,
};

// 组件Props
export interface MovingAveragesProps {
  priceData: PricePoint[]
  movingAverages?: MovingAverageLine[]
  config?: Partial<MovingAverageConfig>
  onConfigChange?: (config: MovingAverageConfig) => void
  onPeriodChange?: (period: number) => void
  onTypeChange?: (type: 'SMA' | 'EMA') => void
  className?: string
  height?: number
  width?: number
  showControls?: boolean
}

// 预设的常用周期
const PRESET_PERIODS = [5, 10, 20, 50, 100, 200];

// 预设颜色方案
const COLOR_SCHEMES = [
  { name: '红色', color: 'rgb(239, 68, 68)' },
  { name: '蓝色', color: 'rgb(59, 130, 246)' },
  { name: '绿色', color: 'rgb(34, 197, 94)' },
  { name: '紫色', color: 'rgb(168, 85, 247)' },
  { name: '橙色', color: 'rgb(251, 146, 60)' },
  { name: '青色', color: 'rgb(6, 182, 212)' },
];

export function MovingAverages({
  priceData,
  movingAverages = [],
  config: userConfig = {},
  onConfigChange,
  onPeriodChange,
  onTypeChange,
  className = '',
  height = 300,
  width,
  showControls = true,
}: MovingAveragesProps) {
  const [config, setConfig] = useState<MovingAverageConfig>({ ...DEFAULT_MA_CONFIG, ...userConfig });
  const [isCalculating, setIsCalculating] = useState(false);

  // 计算移动平均线数据
  const calculateMovingAverageData = useCallback(
    (prices: number[], type: 'SMA' | 'EMA', period: number): number[] => {
      if (prices.length < period) return [];

      return type === 'SMA' ? calculateSMA(prices, period) : calculateEMA(prices, period);
    },
    [],
  );

  // 处理配置变化
  const handleConfigChange = useCallback(
    (newConfig: Partial<MovingAverageConfig>) => {
      const updatedConfig = { ...config, ...newConfig };
      setConfig(updatedConfig);
      onConfigChange?.(updatedConfig);

      // 分别调用特定的回调
      if (newConfig.period !== undefined) {
        onPeriodChange?.(newConfig.period);
      }
      if (newConfig.type !== undefined) {
        onTypeChange?.(newConfig.type);
      }
    },
    [config, onConfigChange, onPeriodChange, onTypeChange],
  );

  // 获取价格数据
  const priceValues = useMemo(() => priceData.map(p => p.close), [priceData]);
  const priceLabels = useMemo(() => priceData.map(p => p.timestamp), [priceData]);

  // 计算移动平均线
  const maData = useMemo(() => {
    if (priceValues.length === 0) return [];

    setIsCalculating(true);
    const result = calculateMovingAverageData(priceValues, config.type, config.period);
    setIsCalculating(false);

    return result;
  }, [priceValues, config.type, config.period, calculateMovingAverageData]);

  // 生成图表数据
  const chartData = useMemo<ChartJSData<'line'>>(() => {
    // 价格线
    const datasets: ChartJSData<'line'>['datasets'] = [
      {
        label: '价格',
        data: priceValues,
        borderColor: 'rgb(156, 163, 175)',
        backgroundColor: 'rgba(156, 163, 175, 0.1)',
        borderWidth: 1,
        pointRadius: 0,
        pointHoverRadius: 2,
        tension: 0.1,
      },
    ];

    // 移动平均线
    if (maData.length > 0) {
      const startIndex = priceValues.length - maData.length;
      const alignedLabels = priceLabels.slice(startIndex);

      datasets.push({
        label: `${config.type}(${config.period})`,
        data: maData,
        borderColor: config.color,
        backgroundColor: config.fillArea
          ? config.color.replace('rgb', 'rgba').replace(')', `, ${config.fillOpacity})`)
          : 'transparent',
        borderWidth: config.lineWidth,
        pointRadius: config.showPoints ? 2 : 0,
        pointHoverRadius: config.showPoints ? 4 : 2,
        tension: 0.1,
        fill: config.fillArea,
      });
    }

    return {
      labels: priceLabels,
      datasets,
    };
  }, [priceValues, priceLabels, maData, config]);

  // 生成图表选项
  const chartOptions = useMemo<ChartOptions<'line'>>(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: config.animationDuration,
    },
    interaction: {
      mode: 'index',
      intersect: false,
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
          title(context) {
            return context[0].label;
          },
          label(context) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            if (value === null) return `${label}: --`;
            return `${label}: ${value.toFixed(2)}`;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'category',
        display: true,
        title: {
          display: true,
          text: '时间',
        },
        ticks: {
          maxTicksLimit: 8,
        },
      },
      y: {
        type: 'linear',
        display: true,
        title: {
          display: true,
          text: '价格',
        },
        ticks: {
          callback(value) {
            return Number(value).toFixed(2);
          },
        },
      },
    },
  }), [config]);

  // 渲染控制面板
  const renderControls = () => {
    if (!showControls) return null;

    return (
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-lg">移动平均线设置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* 类型选择 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">均线类型</label>
              <div className="flex space-x-2">
                {(['SMA', 'EMA'] as const).map((type) => (
                  <Button
                    key={type}
                    variant={config.type === type ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleConfigChange({ type })}
                  >
                    {type}
                  </Button>
                ))}
              </div>
            </div>

            {/* 周期选择 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">周期</label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  value={config.period}
                  onChange={(e) => handleConfigChange({ period: parseInt(e.target.value) || 20 })}
                  min="2"
                  max="500"
                  className="border rounded px-2 py-1 w-20"
                />
                <div className="flex flex-wrap gap-1">
                  {PRESET_PERIODS.slice(0, 4).map((period) => (
                    <Button
                      key={period}
                      variant={config.period === period ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleConfigChange({ period })}
                    >
                      {period}
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            {/* 颜色选择 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">颜色</label>
              <div className="flex items-center space-x-2">
                <input
                  type="color"
                  value={config.color}
                  onChange={(e) => handleConfigChange({ color: e.target.value })}
                  className="w-8 h-8 border rounded"
                />
                <div className="flex space-x-1">
                  {COLOR_SCHEMES.slice(0, 4).map((scheme) => (
                    <Button
                      key={scheme.name}
                      variant="outline"
                      size="sm"
                      className="w-8 h-8 p-0"
                      style={{ backgroundColor: scheme.color }}
                      onClick={() => handleConfigChange({ color: scheme.color })}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* 线宽 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">线宽: {config.lineWidth}px</label>
              <input
                type="range"
                min="1"
                max="5"
                value={config.lineWidth}
                onChange={(e) => handleConfigChange({ lineWidth: parseInt(e.target.value) })}
                className="w-full"
              />
            </div>

            {/* 显示点 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">显示数据点</label>
              <input
                type="checkbox"
                checked={config.showPoints}
                onChange={(e) => handleConfigChange({ showPoints: e.target.checked })}
                className="rounded"
              />
            </div>

            {/* 填充区域 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">填充区域</label>
              <input
                type="checkbox"
                checked={config.fillArea}
                onChange={(e) => handleConfigChange({ fillArea: e.target.checked })}
                className="rounded"
              />
              {config.fillArea && (
                <div className="flex items-center space-x-2">
                  <label className="text-xs">透明度:</label>
                  <input
                    type="range"
                    min="0.1"
                    max="0.5"
                    step="0.1"
                    value={config.fillOpacity}
                    onChange={(e) => handleConfigChange({ fillOpacity: parseFloat(e.target.value) })}
                    className="w-20"
                  />
                </div>
              )}
            </div>
          </div>

          {/* 更多预设周期 */}
          <div className="mt-4 pt-4 border-t">
            <div className="text-sm font-medium mb-2">更多周期</div>
            <div className="flex flex-wrap gap-2">
              {PRESET_PERIODS.slice(4).map((period) => (
                <Button
                  key={period}
                  variant={config.period === period ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleConfigChange({ period })}
                >
                  {period}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  // 渲染统计信息
  const renderStats = () => {
    if (maData.length === 0) return null;

    const currentMA = maData[maData.length - 1];
    const currentPrice = priceValues[priceValues.length - 1];
    const previousMA = maData.length > 1 ? maData[maData.length - 2] : currentMA;
    const maTrend = currentMA > previousMA ? 'up' : currentMA < previousMA ? 'down' : 'flat';
    const priceVsMA = currentPrice > currentMA ? 'above' : 'below';

    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 border-b">
        <div className="text-center">
          <div className="text-lg font-semibold">
            {currentMA.toFixed(2)}
          </div>
          <div className="text-xs text-gray-600">当前 {config.type}({config.period})</div>
        </div>

        <div className="text-center">
          <div className={`text-lg font-semibold ${
            maTrend === 'up' ? 'text-green-600' : maTrend === 'down' ? 'text-red-600' : 'text-gray-600'
          }`}>
            {maTrend === 'up' ? '↑ 上升' : maTrend === 'down' ? '↓ 下降' : '→ 平稳'}
          </div>
          <div className="text-xs text-gray-600">均线趋势</div>
        </div>

        <div className="text-center">
          <div className={`text-lg font-semibold ${
            priceVsMA === 'above' ? 'text-green-600' : 'text-red-600'
          }`}>
            {priceVsMA === 'above' ? '上方' : '下方'}
          </div>
          <div className="text-xs text-gray-600">价格相对位置</div>
        </div>

        <div className="text-center">
          <div className="text-lg font-semibold">
            {Math.abs(currentPrice - currentMA).toFixed(2)}
          </div>
          <div className="text-xs text-gray-600">偏离距离</div>
        </div>
      </div>
    );
  };

  if (priceData.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-center text-gray-500">
            <div className="text-lg font-medium mb-2">暂无价格数据</div>
            <div className="text-sm">请先加载价格数据以计算移动平均线</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={className}>
      {renderControls()}
      <Card>
        {renderStats()}
        <CardContent className="p-0">
          <div style={{ height, width }}>
            {isCalculating ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-gray-500">计算中...</div>
              </div>
            ) : (
              <Line data={chartData} options={chartOptions} />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default MovingAverages;
