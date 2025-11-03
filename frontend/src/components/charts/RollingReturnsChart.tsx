'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  RollingReturnData,
  PerformanceAnalysisRequest,
  CumulativeReturnData,
  ReturnDataPoint,
} from '@/types/performance.types';
import {
  useCumulativeReturns,
  performanceService,
} from '@/services/performanceService';
import {
  calculateRollingReturns,
  generatePerformanceChartData,
  sampleDataForPerformance,
} from '@/utils/performanceHelpers';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/ui/loading';
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Download,
  Calendar,
  BarChart3,
  Settings,
} from 'lucide-react';

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

// 图表配置常量
const CHART_COLORS = {
  primary: '#10b981', // 绿色
  negative: '#ef4444', // 红色
  secondary: '#6366f1', // 蓝色
  grid: '#e5e7eb', // 灰色
  text: '#374151', // 深灰色
};

const DEFAULT_CHART_OPTIONS: ChartOptions<'line'> = {
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
          const formattedValue = `${(value * 100).toFixed(2)}%`;
          return `${label}: ${formattedValue}`;
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
        color: CHART_COLORS.text,
        maxRotation: 45,
        minRotation: 0,
        autoSkip: true,
        maxTicksLimit: 12,
      },
    },
    y: {
      display: true,
      grid: {
        color: CHART_COLORS.grid,
      },
      ticks: {
        color: CHART_COLORS.text,
        callback: function(value) {
          return `${(Number(value) * 100).toFixed(1)}%`;
        },
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
};

interface RollingReturnsChartProps {
  strategyId: string;
  startDate?: string;
  endDate?: string;
  height?: number;
  width?: number;
  showControls?: boolean;
  showTooltip?: boolean;
  className?: string;
  onDataPointClick?: (point: ReturnDataPoint) => void;
}

interface RollingReturnsChartState {
  selectedWindows: number[];
  isLoadingWindows: boolean;
  selectedPoint: ReturnDataPoint | null;
  isExporting: boolean;
  showSettings: boolean;
  rollingData: RollingReturnData[];
}

const ROLLING_WINDOWS = [20, 60, 120, 252]; // 交易日：1个月、3个月、6个月、1年

const RollingReturnsChartComponent: React.FC<RollingReturnsChartProps> = ({
  strategyId,
  startDate,
  endDate,
  height = 400,
  width,
  showControls = true,
  showTooltip = true,
  className = '',
  onDataPointClick,
}) => {
  const chartRef = useRef<ChartJS<'line'>>(null);
  const [state, setState] = useState<RollingReturnsChartState>({
    selectedWindows: [60], // 默认选择3个月滚动窗口
    isLoadingWindows: false,
    selectedPoint: null,
    isExporting: false,
    showSettings: false,
    rollingData: [],
  });

  // 构建分析请求
  const analysisRequest = useMemo(() => ({
    strategyId,
    returnType: 'simple' as const,
    initialCapital: 100000,
    positionSize: 1,
    riskFreeRate: 0.02,
    includeCosts: true,
    startDate,
    endDate,
  }), [strategyId, startDate, endDate]);

  // 获取基础收益数据
  const {
    data: cumulativeReturns,
    isLoading: isBaseLoading,
    error: baseError,
    refetch: refetchBase,
  } = useCumulativeReturns(analysisRequest, {
    select: (data) => {
      // 直接返回原始数据，在使用时计算收益率
      return data;
    },
  });

  // 计算滚动收益
  useEffect(() => {
    if (!cumulativeReturns?.datasets || cumulativeReturns.datasets.length === 0) {
      setState(prev => ({ ...prev, rollingData: [] }));
      return;
    }

    const cumulativeData = cumulativeReturns.datasets[0].data;
    const labels = cumulativeReturns.labels;

    // 计算收益率数组（从累计收益计算）
    const returns: number[] = [0]; // 第一天收益率为0
    for (let i = 1; i < cumulativeData.length; i++) {
      const dailyReturn = (cumulativeData[i] - cumulativeData[i - 1]) / Math.max(cumulativeData[i - 1], 1);
      returns.push(dailyReturn);
    }

    const rollingData: RollingReturnData[] = state.selectedWindows.map(window => {
      const rollingReturns = calculateRollingReturns(returns, window);
      const rollingLabels = labels.slice(window - 1); // 滚动收益从窗口期后开始

      return {
        window,
        returns: rollingReturns,
        labels: rollingLabels,
      };
    });

    setState(prev => ({ ...prev, rollingData }));
  }, [cumulativeReturns, state.selectedWindows]);

  // 生成图表数据
  const chartData = useMemo(() => {
    if (!state.rollingData.length) return null;

    const datasets = state.rollingData.map((data, index) => {
      const colors = [CHART_COLORS.primary, CHART_COLORS.secondary, CHART_COLORS.negative, '#8b5cf6'];
      const color = colors[index % colors.length];

      return {
        label: `${data.window}日滚动收益`,
        data: data.returns,
        borderColor: color,
        backgroundColor: color + '20',
        fill: false,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
      };
    });

    // 使用最长的标签数组
    const maxLength = Math.max(...state.rollingData.map(data => data.labels.length));
    const labels = state.rollingData.find(data => data.labels.length === maxLength)?.labels || [];

    // 采样数据以提高性能
    const sampledLabels = sampleDataForPerformance(
      labels.map((label, index) => ({ timestamp: label, value: index })),
      500
    ).map(point => point.timestamp);

    const sampledDatasets = datasets.map(dataset => ({
      ...dataset,
      data: sampleDataForPerformance(
        dataset.data.map((value, index) => ({ timestamp: index.toString(), value })),
        500
      ).map(point => point.value),
    }));

    return {
      labels: sampledLabels,
      datasets: sampledDatasets,
    };
  }, [state.rollingData]);

  // 图表选项
  const chartOptions = useMemo(() => {
    const options = { ...DEFAULT_CHART_OPTIONS };

    // 自定义工具提示
    if (showTooltip) {
      options.plugins = {
        ...options.plugins,
        tooltip: {
          ...options.plugins!.tooltip,
          enabled: showTooltip,
        },
      };
    }

    // 添加零线
    (options.plugins as any).annotation = {
      annotations: {
        zeroLine: {
          type: 'line',
          yMin: 0,
          yMax: 0,
          borderColor: CHART_COLORS.grid,
          borderWidth: 1,
          borderDash: [5, 5],
        },
      },
    };

    // 点击事件处理
    options.onClick = (event, elements, chart) => {
      if (elements.length > 0) {
        const element = elements[0];
        const index = element.index;

        if (chartData && chartData.labels) {
          const timestamp = chartData.labels[index];
          const value = chartData.datasets[element.datasetIndex]?.data[index] || 0;

          const point: ReturnDataPoint = {
            timestamp,
            value,
            date: new Date(timestamp),
          };
          setState(prev => ({ ...prev, selectedPoint: point }));
          onDataPointClick?.(point);
        }
      }
    };

    return options;
  }, [showTooltip, chartData, onDataPointClick]);

  // 窗口选择处理
  const handleWindowToggle = useCallback((window: number) => {
    setState(prev => {
      const newWindows = prev.selectedWindows.includes(window)
        ? prev.selectedWindows.filter(w => w !== window)
        : [...prev.selectedWindows, window];

      return { ...prev, selectedWindows: newWindows };
    });
  }, []);

  // 设置面板切换
  const toggleSettings = useCallback(() => {
    setState(prev => ({ ...prev, showSettings: !prev.showSettings }));
  }, []);

  // 刷新数据
  const handleRefresh = useCallback(() => {
    refetchBase();
  }, [refetchBase]);

  // 导出功能
  const handleExport = useCallback(async (format: 'png' | 'csv' | 'json') => {
    if (!chartRef.current || !chartData) return;

    setState(prev => ({ ...prev, isExporting: true }));

    try {
      switch (format) {
        case 'png':
          const canvas = chartRef.current.canvas;
          const url = canvas.toDataURL('image/png');
          const link = document.createElement('a');
          link.download = `rolling-returns-${strategyId}-${new Date().toISOString().split('T')[0]}.png`;
          link.href = url;
          link.click();
          break;

        case 'csv':
          let csvContent = 'Date';
          state.rollingData.forEach(data => {
            csvContent += `,${data.window}日滚动收益`;
          });
          csvContent += '\n';

          const maxLength = Math.max(...state.rollingData.map(data => data.labels.length));
          for (let i = 0; i < maxLength; i++) {
            csvContent += state.rollingData[0]?.labels[i] || '';
            state.rollingData.forEach(data => {
              const value = data.returns[i] || 0;
              csvContent += `,${value}`;
            });
            csvContent += '\n';
          }

          const csvBlob = new Blob([csvContent], { type: 'text/csv' });
          const csvUrl = URL.createObjectURL(csvBlob);
          const csvLink = document.createElement('a');
          csvLink.download = `rolling-returns-${strategyId}-${new Date().toISOString().split('T')[0]}.csv`;
          csvLink.href = csvUrl;
          csvLink.click();
          URL.revokeObjectURL(csvUrl);
          break;

        case 'json':
          const jsonData = {
            strategyId,
            windows: state.selectedWindows,
            rollingData: state.rollingData.map(data => ({
              window: data.window,
              returns: data.returns,
              labels: data.labels,
            })),
            exportDate: new Date().toISOString(),
          };
          const jsonBlob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
          const jsonUrl = URL.createObjectURL(jsonBlob);
          const jsonLink = document.createElement('a');
          jsonLink.download = `rolling-returns-${strategyId}-${new Date().toISOString().split('T')[0]}.json`;
          jsonLink.href = jsonUrl;
          jsonLink.click();
          URL.revokeObjectURL(jsonUrl);
          break;
      }
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setState(prev => ({ ...prev, isExporting: false }));
    }
  }, [chartRef, chartData, strategyId, state]);

  // 渲染控制工具栏
  const renderControls = useCallback(() => {
    if (!showControls) return null;

    return (
      <div className="flex items-center justify-between p-4 bg-gray-50 border-b">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium">滚动窗口:</span>
          <div className="flex flex-wrap gap-2">
            {ROLLING_WINDOWS.map(window => (
              <Button
                key={window}
                variant={state.selectedWindows.includes(window) ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleWindowToggle(window)}
              >
                {window === 252 ? '1年' : `${window / 20}个月`}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleSettings}
            className="h-8 w-8 p-0"
          >
            <Settings className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isBaseLoading}
            className="h-8 w-8 p-0"
          >
            <RefreshCw className={`w-4 h-4 ${isBaseLoading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('png')}
            disabled={state.isExporting}
          >
            <Download className="w-4 h-4 mr-1" />
            PNG
          </Button>
        </div>
      </div>
    );
  }, [
    showControls,
    state.selectedWindows,
    state.isExporting,
    isBaseLoading,
    handleWindowToggle,
    toggleSettings,
    handleRefresh,
    handleExport,
  ]);

  // 渲染设置面板
  const renderSettings = useCallback(() => {
    if (!state.showSettings) return null;

    return (
      <div className="absolute top-16 right-4 bg-white p-4 rounded-lg shadow-lg border z-10 w-80">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-medium">滚动收益设置</h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleSettings}
            className="h-6 w-6 p-0"
          >
            ×
          </Button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium mb-2 block">选择的滚动窗口:</label>
            <div className="text-sm text-gray-600">
              {state.selectedWindows.length === 0 ? (
                <span className="text-red-600">请至少选择一个滚动窗口</span>
              ) : (
                state.selectedWindows.map(window => (
                  <span key={window} className="inline-block mr-2 mb-1 px-2 py-1 bg-blue-100 text-blue-800 rounded">
                    {window === 252 ? '1年' : `${window / 20}个月`}
                  </span>
                ))
              )}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">可用窗口:</label>
            <div className="grid grid-cols-2 gap-2">
              {ROLLING_WINDOWS.map(window => (
                <Button
                  key={window}
                  variant={state.selectedWindows.includes(window) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleWindowToggle(window)}
                  className="text-xs"
                >
                  {window === 252 ? '1年 (252天)' : `${window / 20}个月 (${window}天)`}
                </Button>
              ))}
            </div>
          </div>

          <div className="text-xs text-gray-500 pt-2 border-t">
            滚动收益显示指定时间段内的累计收益率，帮助评估策略在不同时间尺度下的表现。
          </div>
        </div>
      </div>
    );
  }, [state.showSettings, state.selectedWindows, toggleSettings, handleWindowToggle]);

  // 渲染数据点详情
  const renderPointDetails = useCallback(() => {
    if (!state.selectedPoint) return null;

    return (
      <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-lg border z-10">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-medium">滚动收益详情</h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setState(prev => ({ ...prev, selectedPoint: null }))}
            className="h-6 w-6 p-0"
          >
            ×
          </Button>
        </div>
        <div className="text-sm space-y-1">
          <div>日期: {state.selectedPoint.date.toLocaleDateString('zh-CN')}</div>
          <div>滚动收益: {(state.selectedPoint.value * 100).toFixed(2)}%</div>
        </div>
      </div>
    );
  }, [state.selectedPoint]);

  // 加载状态
  if (isBaseLoading && !cumulativeReturns) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center" style={{ height }}>
          <Loading />
          <span className="ml-2 text-gray-600">加载滚动收益数据...</span>
        </CardContent>
      </Card>
    );
  }

  // 错误状态
  if (baseError && !cumulativeReturns) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center" style={{ height }}>
          <div className="text-red-600 mb-2">
            <TrendingDown className="w-8 h-8 mx-auto mb-2" />
            <p className="text-center">加载滚动收益数据失败</p>
            <p className="text-sm text-gray-500 mt-1">
              {baseError instanceof Error ? baseError.message : '未知错误'}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            重试
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center space-x-2">
            <TrendingUp className="w-5 h-5 text-green-500" />
            <span>滚动收益分析</span>
          </CardTitle>

          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSettings}
              className="h-8 w-8 p-0"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* 策略信息 */}
        <div className="text-sm text-gray-600">
          策略ID: {strategyId}
          {startDate && endDate && (
            <span className="ml-2">
              分析期间: {new Date(startDate).toLocaleDateString('zh-CN')} - {new Date(endDate).toLocaleDateString('zh-CN')}
            </span>
          )}
          {state.selectedWindows.length > 0 && (
            <span className="ml-2">
              窗口: {state.selectedWindows.map(w => w === 252 ? '1年' : `${w / 20}个月`).join(', ')}
            </span>
          )}
        </div>
      </CardHeader>

      {renderControls()}

      <CardContent className="p-0 relative">
        {renderSettings()}
        {renderPointDetails()}

        {/* 状态指示器 */}
        <div className="absolute top-2 left-2 flex items-center space-x-2 text-xs text-gray-600">
          {strategyId && (
            <div className="flex items-center space-x-1">
              <BarChart3 className="w-3 h-3" />
              <span>策略: {strategyId}</span>
            </div>
          )}
          {state.selectedWindows.length > 0 && (
            <div className="flex items-center space-x-1">
              <Calendar className="w-3 h-3" />
              <span>{state.selectedWindows.length}个滚动窗口</span>
            </div>
          )}
        </div>

        {/* 图表容器 */}
        <div style={{ height, width }}>
          {chartData && state.selectedWindows.length > 0 ? (
            <Line
              ref={chartRef}
              data={chartData as ChartJSData<'line'>}
              options={chartOptions}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Calendar className="w-8 h-8 mb-2" />
              <p>请选择至少一个滚动窗口</p>
              <Button variant="outline" size="sm" onClick={toggleSettings} className="mt-2">
                打开设置
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

RollingReturnsChartComponent.displayName = 'RollingReturnsChart';

export default RollingReturnsChartComponent;