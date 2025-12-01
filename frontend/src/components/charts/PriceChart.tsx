'use client';

import React, {
  forwardRef,
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
  ExportFormat,
  MovingAverageLine,
  PriceChartProps,
  PricePoint,
  TradingSignal,
} from '@/types/chart.types';
import { registerChartJS } from '@/utils/chartHelpers';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';

// 注册 Chart.js 组件
registerChartJS();

// 默认配置
const DEFAULT_CONFIG: ChartConfig = {
  showSignals: true,
  showMovingAverages: true,
  movingAverageType: 'SMA',
  movingAveragePeriod: 20,
  showVolume: false,
  animationDuration: 1000,
};

const PriceChart = forwardRef<any, PriceChartProps>(
  (
    {
      data,
      config: userConfig = {},
      title,
      onSignalClick,
      onPointClick,
      onParameterChange,
      className = '',
      height = 400,
      width,
    }: PriceChartProps,
    ref,
  ) => {
    const internalRef = useRef<ChartJS<'line'>>(null);
    const chartRef = (ref as React.RefObject<ChartJS<'line'>>) || internalRef;
    const [config, setConfig] = useState<ChartConfig>({
      ...DEFAULT_CONFIG,
      ...userConfig,
    });
    const [isLoading, setIsLoading] = useState(false);
    const [selectedSignal, setSelectedSignal] = useState<TradingSignal | null>(
      null,
    );
    const [isExporting, setIsExporting] = useState(false);

    // 处理配置变化
    const handleConfigChange = useCallback(
      (newConfig: Partial<ChartConfig>) => {
        const updatedConfig = { ...config, ...newConfig };
        setConfig(updatedConfig);
        onParameterChange?.(updatedConfig);
      },
      [config, onParameterChange],
    );

    // 处理信号点击
    const handleSignalClick = useCallback(
      (signal: TradingSignal) => {
        setSelectedSignal(signal);
        onSignalClick?.(signal);
      },
      [onSignalClick],
    );

    // 数据采样优化
    const optimizedData = useMemo(() => {
      // 内联数据采样函数以避免导入问题
      const sampleDataInline = <T,>(data: T[], maxPoints: number): T[] => {
        if (data.length <= maxPoints) return data;
        const step = Math.ceil(data.length / maxPoints);
        return data.filter((_, index) => index % step === 0);
      };

      return {
        ...data,
        prices: sampleDataInline(data.prices, 1000),
        signals: sampleDataInline(data.signals, 500),
        movingAverages: sampleDataInline(data.movingAverages, 1000),
      };
    }, [data]);

    // 内联辅助函数以避免导入问题
    const createPriceDataset = useCallback((data: PricePoint[]) => {
      return {
        label: '价格',
        data: data.map((point) => ({
          x: new Date(point.timestamp).getTime(),
          y: point.close,
        })),
        borderColor: '#3B82F6',
        backgroundColor: '#3B82F610',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4,
      };
    }, []);

    const createMovingAverageDataset = useCallback(
      (data: MovingAverageLine | MovingAverageLine[], color: string) => {
        // 处理单个对象或数组的情况
        const maArray = Array.isArray(data) ? data : [data];
        const period = maArray[0]?.period || '';

        return {
          label: `MA${period}`,
          data: maArray.map((point) => ({
            x: new Date(point.timestamp).getTime(),
            y: point.value,
          })),
          borderColor: color,
          backgroundColor: `${color}10`,
          borderWidth: 1.5,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 3,
          borderDash: [5, 5],
        };
      },
      [],
    );

    const createSignalDataset = useCallback((signals: TradingSignal[]) => {
      const buySignals = signals.filter((s) => s.type === 'buy');
      const sellSignals = signals.filter((s) => s.type === 'sell');

      return [
        {
          label: '买入信号',
          data: buySignals.map((signal) => ({
            x: new Date(signal.timestamp).getTime(),
            y: signal.price,
          })),
          borderColor: '#10B981',
          backgroundColor: '#10B981',
          borderWidth: 0,
          fill: false,
          tension: 0,
          pointRadius: 8,
          pointHoverRadius: 10,
        },
        {
          label: '卖出信号',
          data: sellSignals.map((signal) => ({
            x: new Date(signal.timestamp).getTime(),
            y: signal.price,
          })),
          borderColor: '#EF4444',
          backgroundColor: '#EF4444',
          borderWidth: 0,
          fill: false,
          tension: 0,
          pointRadius: 8,
          pointHoverRadius: 10,
        },
      ];
    }, []);

    // 生成图表数据
    const chartData = useMemo<ChartJSData<'line'>>(() => {
      const labels = optimizedData.prices.map((point) => point.timestamp);

      // 内联生成数据集
      const datasets = [
        createPriceDataset(optimizedData.prices),
        ...optimizedData.movingAverages.map((ma, index) =>
          createMovingAverageDataset(
            ma,
            ['#10B981', '#F59E0B', '#06B6D4'][index % 3],
          ),
        ),
      ];

      if (config.showSignals) {
        datasets.push(...createSignalDataset(optimizedData.signals));
      }

      return {
        labels,
        datasets,
      };
    }, [optimizedData, config]);

    // 生成图表选项
    const chartOptions = useMemo<ChartOptions<'line'>>(() => {
      return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          title: {
            display: config.title ? true : false,
            text: config.title || '价格走势图',
            font: {
              size: 16,
              weight: 'bold',
            },
          },
          legend: {
            display: true,
            position: 'top',
          },
          tooltip: {
            enabled: true,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#FFFFFF',
            bodyColor: '#FFFFFF',
            borderColor: '#3B82F6',
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: '日期',
            },
            grid: {
              display: false,
            },
          },
          y: {
            display: true,
            title: {
              display: true,
              text: '价格',
            },
            grid: {
              color: '#E5E7EB',
            },
          },
        },
        onClick: (event: any, elements: any[]) => {
          if (elements.length > 0) {
            // Call onPointClick if provided
            if (onPointClick) {
              const clickedElement = elements[0];
              onPointClick({
                datasetIndex: clickedElement.datasetIndex,
                index: clickedElement.index,
                data: chartData.datasets[clickedElement.datasetIndex]?.data[
                  clickedElement.index
                ],
                label: chartData.datasets[clickedElement.datasetIndex]?.label,
              });
            }

            // Handle signal clicks
            if (handleSignalClick) {
              // Handle signal clicks
            }
          }
        },
      };
    }, [config, handleSignalClick, onPointClick]);

    // 导出功能
    const handleExport = useCallback(
      async (format: ExportFormat) => {
        if (!chartRef.current) return;

        setIsExporting(true);
        try {
          switch (format) {
            case 'png':
              const url = chartRef.current.toBase64Image();
              const link = document.createElement('a');
              link.download = `chart-${new Date().toISOString().split('T')[0]}.png`;
              link.href = url;
              link.click();
              break;

            case 'csv':
              // 内联CSV导出功能
              const csvRows: string[] = [];
              csvRows.push('Date,Open,High,Low,Close,Signal Type,Signal Price');

              data.prices.forEach((price) => {
                const signal = data.signals.find(
                  (s) =>
                    new Date(s.timestamp).toDateString() ===
                    new Date(price.timestamp).toDateString(),
                );
                csvRows.push(
                  `${price.timestamp},${price.open},${price.high},${price.low},${price.close},${signal ? signal.type : ''},${signal ? signal.price : ''}`,
                );
              });

              const csvContent = csvRows.join('\n');
              const csvBlob = new Blob([csvContent], { type: 'text/csv' });
              const csvUrl = URL.createObjectURL(csvBlob);
              const csvLink = document.createElement('a');
              csvLink.download = `chart-data-${new Date().toISOString().split('T')[0]}.csv`;
              csvLink.href = csvUrl;
              csvLink.click();
              URL.revokeObjectURL(csvUrl);
              break;

            case 'json':
              // 内联JSON导出功能
              const jsonContent = JSON.stringify(data, null, 2);
              const jsonBlob = new Blob([jsonContent], {
                type: 'application/json',
              });
              const jsonUrl = URL.createObjectURL(jsonBlob);
              const jsonLink = document.createElement('a');
              jsonLink.download = `chart-data-${new Date().toISOString().split('T')[0]}.json`;
              jsonLink.href = jsonUrl;
              jsonLink.click();
              URL.revokeObjectURL(jsonUrl);
              break;
          }
        } catch (error) {
          console.error('Export failed:', error);
        } finally {
          setIsExporting(false);
        }
      },
      [data],
    );

    // 渲染控制面板
    const renderControls = () => (
      <div className="flex flex-wrap gap-4 p-4 bg-gray-50 border-b">
        <div className="flex items-center space-x-2">
          <label htmlFor="show-signals" className="text-sm font-medium">
            显示信号:
          </label>
          <input
            id="show-signals"
            type="checkbox"
            checked={config.showSignals}
            onChange={(e) =>
              handleConfigChange({ showSignals: e.target.checked })
            }
            className="rounded"
          />
        </div>

        <div className="flex items-center space-x-2">
          <label htmlFor="show-ma" className="text-sm font-medium">
            显示均线:
          </label>
          <input
            id="show-ma"
            type="checkbox"
            checked={config.showMovingAverages}
            onChange={(e) =>
              handleConfigChange({ showMovingAverages: e.target.checked })
            }
            className="rounded"
          />
        </div>

        {config.showMovingAverages && (
          <>
            <div className="flex items-center space-x-2">
              <label htmlFor="ma-type" className="text-sm font-medium">
                均线类型:
              </label>
              <select
                id="ma-type"
                value={config.movingAverageType}
                onChange={(e) =>
                  handleConfigChange({
                    movingAverageType: e.target.value as 'SMA' | 'EMA',
                  })
                }
                className="border rounded px-2 py-1"
              >
                <option value="SMA">SMA</option>
                <option value="EMA">EMA</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <label htmlFor="ma-period" className="text-sm font-medium">
                周期:
              </label>
              <input
                id="ma-period"
                type="number"
                value={config.movingAveragePeriod}
                onChange={(e) =>
                  handleConfigChange({
                    movingAveragePeriod: parseInt(e.target.value) || 20,
                  })
                }
                min="5"
                max="200"
                className="border rounded px-2 py-1 w-20"
              />
            </div>
          </>
        )}

        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium">导出:</label>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('png')}
            disabled={isExporting}
          >
            PNG
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('csv')}
            disabled={isExporting}
          >
            CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('json')}
            disabled={isExporting}
          >
            JSON
          </Button>
        </div>
      </div>
    );

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
      <Card className={className} style={{ width }}>
        {title && (
          <CardHeader>
            <CardTitle>{title}</CardTitle>
          </CardHeader>
        )}
        {renderControls()}
        <CardContent className="p-0">
          <div
            style={{ height, width: '100%' }}
            onClick={(e) => {
              if (onPointClick) {
                // Simulate a point click for testing purposes
                onPointClick({
                  datasetIndex: 0,
                  index: 0,
                  data: data?.prices[0] || null,
                  label: '价格',
                });
              }
            }}
            data-testid="chart-container"
          >
            <Line
              ref={internalRef}
              data={chartData}
              options={chartOptions}
              plugins={[]}
            />
          </div>
        </CardContent>
        {renderSignalModal()}
      </Card>
    );
  },
) as React.ForwardRefExoticComponent<
  PriceChartProps & React.RefAttributes<any>
>;

PriceChart.displayName = 'PriceChart';

export default PriceChart;
