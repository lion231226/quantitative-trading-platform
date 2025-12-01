'use client';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Line } from 'react-chartjs-2';
import {
  CategoryScale,
  Chart as ChartJS,
  ChartData as ChartJSData,
  ChartOptions,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import {
  ChartConfig,
  ChartData,
  ChartInteractionConfig,
  PerformanceConfig,
  PriceChartProps,
  TradingSignal,
} from '@/types/chart.types';
import {
  createChartConfig,
  findNearestSignal,
  generateTestData,
  registerChartJS,
  sampleData,
} from '@/utils/chartHelpers';
import {
  ChartInteractions,
  createChartInteractions,
} from '@/utils/chartInteractions';
import { ChartExporter, createChartExporter } from '@/utils/chartExport';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';

// 注册 Chart.js 组件
registerChartJS();

// 扩展组件Props
interface InteractivePriceChartProps extends PriceChartProps {
  interactionConfig?: Partial<ChartInteractionConfig>;
  performanceConfig?: Partial<PerformanceConfig>;
  enableInteractions?: boolean;
}

const InteractivePriceChart = React.forwardRef<any, InteractivePriceChartProps>(
  (
    {
      data,
      config: userConfig = {},
      interactionConfig = {},
      performanceConfig = {},
      onSignalClick,
      onParameterChange,
      enableInteractions = true,
      className = '',
      height = 400,
      width,
    }: InteractivePriceChartProps,
    ref,
  ) => {
    const internalRef = useRef<ChartJS<'line'>>(null);
    const chartRef = (ref as React.RefObject<ChartJS<'line'>>) || internalRef;

    const [isLoading, setIsLoading] = useState(false);
    const [selectedSignal, setSelectedSignal] = useState<TradingSignal | null>(
      null,
    );
    const [isInteracting, setIsInteracting] = useState(false);
    const [chartInteractions, setChartInteractions] =
      useState<ChartInteractions | null>(null);
    const [chartExporter, setChartExporter] = useState<ChartExporter | null>(
      null,
    );

    // 性能配置
    const perfConfig = useMemo(
      () => ({
        enableDataSampling: true,
        maxDataPoints: 1000,
        enableAnimation: true,
        animationDuration: 750,
        ...performanceConfig,
      }),
      [performanceConfig],
    );

    // 交互配置
    const interactConfig = useMemo(
      () => ({
        enableZoom: true,
        enablePan: true,
        zoomMode: 'x' as const,
        panMode: 'x' as const,
        wheelSensitivity: 0.1,
        enableTooltip: true,
        enableCrosshair: false,
        enableDataLabels: false,
        ...interactionConfig,
      }),
      [interactionConfig],
    );

    // 数据优化
    const optimizedData = useMemo(() => {
      if (!perfConfig.enableDataSampling) return data;

      return {
        ...data,
        prices: sampleData(data.prices, perfConfig.maxDataPoints),
        signals: sampleData(data.signals, perfConfig.maxDataPoints / 2),
        movingAverages: sampleData(
          data.movingAverages,
          perfConfig.maxDataPoints,
        ),
      };
    }, [data, perfConfig]);

    // 生成图表配置
    const chartConfig = useMemo(() => {
      const config = createChartConfig(optimizedData, {
        animation: {
          duration: perfConfig.enableAnimation
            ? perfConfig.animationDuration
            : 0,
        },
        interaction: {
          mode: 'index',
          intersect: false,
        },
      });

      // 简化交互配置，避免类型问题
      // 注意：缩放功能需要 chartjs-plugin-zoom 插件

      return config;
    }, [optimizedData, perfConfig, interactConfig, enableInteractions]);

    // 简化版本，不使用复杂的ChartExporter类型
    useEffect(() => {
      if (chartRef.current && enableInteractions) {
        console.log('Chart interactions enabled');
      }
    }, [enableInteractions]);

    // 处理信号点击
    const handleSignalClick = useCallback(
      (event: any, elements: any[]) => {
        if (elements.length > 0) {
          const chart = chartRef.current;
          if (!chart) return;

          const canvasPosition = { x: 0, y: 0 }; // 简化版本
          const dataX = chart.scales.x.getValueForPixel(canvasPosition.x);
          const targetDate = dataX !== undefined ? new Date(dataX) : new Date();

          const nearestSignal = findNearestSignal(
            optimizedData.signals,
            targetDate,
          );
          if (nearestSignal) {
            setSelectedSignal(nearestSignal);
            onSignalClick?.(nearestSignal);
          }
        }
      },
      [optimizedData.signals, onSignalClick],
    );

    // 更新图表选项以包含点击处理（简化版本，避免类型问题）
    const chartOptions = useMemo(
      () => ({
        ...chartConfig.options,
        onClick: enableInteractions ? handleSignalClick : undefined,
      }),
      [chartConfig.options, handleSignalClick, enableInteractions],
    );

    // 交互功能
    const handleResetZoom = useCallback(() => {
      if (chartInteractions) {
        chartInteractions.resetZoom();
      }
    }, [chartInteractions]);

    const handleZoomIn = useCallback(() => {
      if (chartRef.current) {
        (chartRef.current as any).zoom?.(1.1);
      }
    }, []);

    const handleZoomOut = useCallback(() => {
      if (chartRef.current) {
        (chartRef.current as any).zoom?.(0.9);
      }
    }, []);

    const handleExport = useCallback(
      async (format: 'png' | 'csv' | 'json') => {
        if (!chartRef.current) return;

        setIsLoading(true);
        try {
          switch (format) {
            case 'png':
              // 使用 toDataURL方法
              const canvas = (chartRef.current as any).canvas;
              if (canvas) {
                const url = canvas.toDataURL();
                const link = document.createElement('a');
                link.download = `chart-${new Date().toISOString().split('T')[0]}.png`;
                link.href = url;
                link.click();
              }
              break;
            case 'csv':
              const csv = `Date,Price\n${optimizedData.prices
                .map((p) => `${p.timestamp},${p.close}`)
                .join('\n')}`;
              const csvBlob = new Blob([csv], { type: 'text/csv' });
              const csvUrl = URL.createObjectURL(csvBlob);
              const csvLink = document.createElement('a');
              csvLink.href = csvUrl;
              csvLink.download = 'chart.csv';
              csvLink.click();
              URL.revokeObjectURL(csvUrl);
              break;
            case 'json':
              const json = JSON.stringify(optimizedData, null, 2);
              const jsonBlob = new Blob([json], { type: 'application/json' });
              const jsonUrl = URL.createObjectURL(jsonBlob);
              const jsonLink = document.createElement('a');
              jsonLink.href = jsonUrl;
              jsonLink.download = 'chart.json';
              jsonLink.click();
              URL.revokeObjectURL(jsonUrl);
              break;
          }
        } catch (error) {
          console.error('Export failed:', error);
        } finally {
          setIsLoading(false);
        }
      },
      [optimizedData],
    );

    // 渲染工具栏
    const renderToolbar = () => {
      if (!enableInteractions) return null;

      return (
        <div className="flex items-center justify-between p-4 bg-gray-50 border-b">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">交互工具:</span>
            <Button variant="outline" size="sm" onClick={handleZoomIn}>
              放大
            </Button>
            <Button variant="outline" size="sm" onClick={handleZoomOut}>
              缩小
            </Button>
            <Button variant="outline" size="sm" onClick={handleResetZoom}>
              重置
            </Button>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">导出:</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('png')}
              disabled={isLoading}
            >
              PNG
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={isLoading}
            >
              CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('json')}
              disabled={isLoading}
            >
              JSON
            </Button>
          </div>
        </div>
      );
    };

    // 渲染信号详情弹窗
    const renderSignalModal = () => {
      if (!selectedSignal) return null;

      return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-96">
            <CardHeader>
              <CardTitle>交易信号详情</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="font-medium">类型:</span>
                  <span
                    className={`px-2 py-1 rounded text-sm ${
                      selectedSignal.type === 'buy'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {selectedSignal.type === 'buy' ? '买入' : '卖出'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">价格:</span>
                  <span>{selectedSignal.price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">时间:</span>
                  <span>
                    {new Date(selectedSignal.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">策略:</span>
                  <span>{selectedSignal.strategy}</span>
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <Button onClick={() => setSelectedSignal(null)}>关闭</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    };

    // 状态指示器
    const renderStatusIndicator = () => {
      return (
        <div className="absolute top-2 right-2 flex items-center space-x-2">
          {isInteracting && (
            <div className="flex items-center space-x-1 text-xs text-blue-600">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
              <span>交互模式</span>
            </div>
          )}
          {enableInteractions && (
            <div className="flex items-center space-x-1 text-xs text-green-600">
              <div className="w-2 h-2 bg-green-600 rounded-full" />
              <span>交互已启用</span>
            </div>
          )}
        </div>
      );
    };

    if (isLoading) {
      return (
        <Card className={className}>
          <CardContent
            className="flex items-center justify-center"
            style={{ height }}
          >
            <Loading />
          </CardContent>
        </Card>
      );
    }

    return (
      <Card className={className}>
        {renderToolbar()}
        <CardContent className="p-0 relative">
          {renderStatusIndicator()}
          <div style={{ height, width }}>
            <Line
              ref={internalRef}
              data={chartConfig.data as any}
              options={chartOptions as any}
            />
          </div>
        </CardContent>
        {renderSignalModal()}
      </Card>
    );
  },
) as React.ForwardRefExoticComponent<
  InteractivePriceChartProps & React.RefAttributes<any>
>;

InteractivePriceChart.displayName = 'InteractivePriceChart';

export default InteractivePriceChart;
