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
  EquityCurveProps,
  CumulativeReturnData,
  ReturnDataPoint,
  PerformanceAnalysisRequest,
} from '@/types/performance.types';
import {
  useCumulativeReturns,
  performanceService,
} from '@/services/performanceService';
import {
  generateCumulativeReturnChartData,
  sampleDataForPerformance,
} from '@/utils/performanceHelpers';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/ui/loading';
import {
  TrendingUp,
  TrendingDown,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  Calendar,
  BarChart3,
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
  benchmark: '#6366f1', // 蓝色
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

interface EquityCurveState {
  isZoomed: boolean;
  showTooltip: boolean;
  selectedPoint: ReturnDataPoint | null;
  isExporting: boolean;
}

const EquityCurveComponent: React.FC<EquityCurveProps> = ({
  strategyId,
  startDate,
  endDate,
  benchmarkId,
  height = 400,
  width,
  showControls = true,
  showTooltip = true,
  enableZoom = true,
  className = '',
  onDataPointClick,
}) => {
  const chartRef = useRef<ChartJS<'line'>>(null);
  const [state, setState] = useState<EquityCurveState>({
    isZoomed: false,
    showTooltip,
    selectedPoint: null,
    isExporting: false,
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
    benchmarkId,
  }), [strategyId, startDate, endDate, benchmarkId]);

  // 获取累计收益数据
  const {
    data: cumulativeReturns,
    isLoading,
    error,
    refetch,
  } = useCumulativeReturns(analysisRequest, {
    select: (data) => {
      // 对大数据集进行采样以提高性能
      if (data.labels.length > 1000) {
        const sampledData = sampleDataForPerformance(
          data.labels.map((label, index) => ({
            timestamp: label,
            value: data.datasets[0]?.data[index] || 0,
          })),
          1000
        );

        return {
          labels: sampledData.map(point => point.timestamp),
          datasets: [{
            ...data.datasets[0],
            data: sampledData.map(point => point.value),
          }],
        };
      }
      return data;
    },
  });

  // 生成图表配置
  const chartData = useMemo(() => {
    if (!cumulativeReturns) return null;

    const baseData = generateCumulativeReturnChartData(
      cumulativeReturns.labels,
      cumulativeReturns.datasets[0]?.data || []
    );

    // 如果有基准数据，添加基准线
    if (benchmarkId && cumulativeReturns.datasets.length > 1) {
      baseData.datasets.push({
        label: '基准',
        data: cumulativeReturns.datasets[1]?.data || [],
        borderColor: CHART_COLORS.benchmark,
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        fill: false,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
      });
    }

    return baseData;
  }, [cumulativeReturns, benchmarkId]);

  // 图表选项
  const chartOptions = useMemo(() => {
    const options = { ...DEFAULT_CHART_OPTIONS };

    // 自定义工具提示
    if (showTooltip) {
      options.plugins = {
        ...options.plugins,
        tooltip: {
          ...options.plugins!.tooltip,
          enabled: state.showTooltip,
        },
      };
    }

    // 缩放功能 - 简化版本，不使用插件
    // 注意：完整的缩放功能需要 chartjs-plugin-zoom 插件
    // 这里我们保留基本的交互功能

    // 点击事件处理
    options.onClick = (event, elements, chart) => {
      if (elements.length > 0) {
        const element = elements[0];
        const datasetIndex = element.datasetIndex;
        const index = element.index;

        if (chartData && chartData.datasets[datasetIndex]) {
          const timestamp = chartData.labels[index];
          const value = chartData.datasets[datasetIndex].data[index];

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
  }, [showTooltip, enableZoom, state.showTooltip, chartData, onDataPointClick]);

  // 缩放控制 - 简化版本
  const handleZoomIn = useCallback(() => {
    // 简化版本：仅设置状态，实际缩放需要插件支持
    setState(prev => ({ ...prev, isZoomed: true }));
  }, []);

  const handleZoomOut = useCallback(() => {
    setState(prev => ({ ...prev, isZoomed: false }));
  }, []);

  const handleResetZoom = useCallback(() => {
    setState(prev => ({ ...prev, isZoomed: false }));
  }, []);

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
          link.download = `equity-curve-${strategyId}-${new Date().toISOString().split('T')[0]}.png`;
          link.href = url;
          link.click();
          break;

        case 'csv':
          const csvContent = 'Date,Value\n' + chartData.labels.map((label, index) => {
            const value = chartData.datasets[0]?.data[index] || 0;
            return `${label},${value}`;
          }).join('\n');
          const csvBlob = new Blob([csvContent], { type: 'text/csv' });
          const csvUrl = URL.createObjectURL(csvBlob);
          const csvLink = document.createElement('a');
          csvLink.download = `equity-curve-${strategyId}-${new Date().toISOString().split('T')[0]}.csv`;
          csvLink.href = csvUrl;
          csvLink.click();
          URL.revokeObjectURL(csvUrl);
          break;

        case 'json':
          const jsonData = {
            strategyId,
            labels: chartData.labels,
            datasets: chartData.datasets.map(dataset => ({
              label: dataset.label,
              data: dataset.data,
            })),
            exportDate: new Date().toISOString(),
          };
          const jsonBlob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
          const jsonUrl = URL.createObjectURL(jsonBlob);
          const jsonLink = document.createElement('a');
          jsonLink.download = `equity-curve-${strategyId}-${new Date().toISOString().split('T')[0]}.json`;
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
  }, [chartRef, chartData, strategyId]);

  // 渲染控制工具栏
  const renderControls = useCallback(() => {
    if (!showControls) return null;

    return (
      <div className="flex items-center justify-between p-4 bg-gray-50 border-b">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">图表控制:</span>
          {enableZoom && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleZoomIn}
                disabled={state.isZoomed}
              >
                <ZoomIn className="w-4 h-4 mr-1" />
                放大
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleZoomOut}
                disabled={!state.isZoomed}
              >
                <ZoomOut className="w-4 h-4 mr-1" />
                缩小
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetZoom}
                disabled={!state.isZoomed}
              >
                <RotateCcw className="w-4 h-4 mr-1" />
                重置
              </Button>
            </>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">导出:</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('png')}
            disabled={state.isExporting}
          >
            <Download className="w-4 h-4 mr-1" />
            PNG
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('csv')}
            disabled={state.isExporting}
          >
            <Download className="w-4 h-4 mr-1" />
            CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('json')}
            disabled={state.isExporting}
          >
            <Download className="w-4 h-4 mr-1" />
            JSON
          </Button>
        </div>
      </div>
    );
  }, [
    showControls,
    enableZoom,
    state.isZoomed,
    state.isExporting,
    handleZoomIn,
    handleZoomOut,
    handleResetZoom,
    handleExport,
  ]);

  // 渲染数据点详情
  const renderPointDetails = useCallback(() => {
    if (!state.selectedPoint) return null;

    return (
      <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-lg border z-10">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-medium">数据点详情</h4>
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
          <div>收益: {(state.selectedPoint.value * 100).toFixed(2)}%</div>
        </div>
      </div>
    );
  }, [state.selectedPoint]);

  // 加载状态
  if (isLoading && !cumulativeReturns) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center" style={{ height }}>
          <Loading />
          <span className="ml-2 text-gray-600">加载收益曲线...</span>
        </CardContent>
      </Card>
    );
  }

  // 错误状态
  if (error && !cumulativeReturns) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center" style={{ height }}>
          <div className="text-red-600 mb-2">
            <TrendingDown className="w-8 h-8 mx-auto mb-2" />
            <p className="text-center">加载收益曲线失败</p>
            <p className="text-sm text-gray-500 mt-1">
              {error instanceof Error ? error.message : '未知错误'}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            重试
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      {renderControls()}

      <CardContent className="p-0 relative">
        {renderPointDetails()}

        {/* 状态指示器 */}
        <div className="absolute top-2 left-2 flex items-center space-x-2 text-xs text-gray-600">
          {strategyId && (
            <div className="flex items-center space-x-1">
              <BarChart3 className="w-3 h-3" />
              <span>策略: {strategyId}</span>
            </div>
          )}
          {startDate && endDate && (
            <div className="flex items-center space-x-1">
              <Calendar className="w-3 h-3" />
              <span>
                {new Date(startDate).toLocaleDateString('zh-CN')} - {new Date(endDate).toLocaleDateString('zh-CN')}
              </span>
            </div>
          )}
          {state.isZoomed && (
            <div className="flex items-center space-x-1 text-blue-600">
              <ZoomIn className="w-3 h-3" />
              <span>已缩放</span>
            </div>
          )}
        </div>

        {/* 图表容器 */}
        <div style={{ height, width }}>
          {chartData ? (
            <Line
              ref={chartRef}
              data={chartData as ChartJSData<'line'>}
              options={chartOptions}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              暂无数据
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

EquityCurveComponent.displayName = 'EquityCurve';

export default EquityCurveComponent;