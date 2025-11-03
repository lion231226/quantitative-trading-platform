'use client';

import React, { useCallback, useMemo, useRef, useState } from 'react';
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
  DrawdownChartProps,
  DrawdownData,
  PerformanceAnalysisRequest,
} from '@/types/performance.types';
import {
  useDrawdownData,
  performanceService,
} from '@/services/performanceService';
import {
  generateDrawdownChartData,
  sampleDataForPerformance,
} from '@/utils/performanceHelpers';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/ui/loading';
import {
  TrendingDown,
  TrendingUp,
  Download,
  Calendar,
  AlertTriangle,
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
  drawdown: '#ef4444', // 红色
  fill: 'rgba(239, 68, 68, 0.2)', // 半透明红色
  grid: '#e5e7eb', // 灰色
  text: '#374151', // 深灰色
  warning: '#f59e0b', // 橙色
  critical: '#dc2626', // 深红色
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
          const formattedValue = `${(value * 100).toFixed(2)}%`;
          return `回撤: ${formattedValue}`;
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
      // 反转Y轴，因为回撤是负值
      reverse: false,
    },
  },
  elements: {
    point: {
      radius: 0,
      hoverRadius: 4,
    },
    line: {
      borderWidth: 2,
      tension: 0.1, // 较低的张力，使回撤线更真实
    },
  },
};

interface DrawdownChartState {
  isExporting: boolean;
  selectedPoint: { timestamp: string; value: number } | null;
  maxDrawdown: number;
  maxDrawdownDate: string;
  currentDrawdown: number;
  daysInDrawdown: number;
}

const DrawdownChartComponent: React.FC<DrawdownChartProps> = ({
  strategyId,
  startDate,
  endDate,
  height = 300,
  width,
  showControls = true,
  showTooltip = true,
  className = '',
  onDrawdownClick,
}) => {
  const chartRef = useRef<ChartJS<'line'>>(null);
  const [state, setState] = useState<DrawdownChartState>({
    isExporting: false,
    selectedPoint: null,
    maxDrawdown: 0,
    maxDrawdownDate: '',
    currentDrawdown: 0,
    daysInDrawdown: 0,
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

  // 获取回撤数据
  const {
    data: drawdownData,
    isLoading,
    error,
    refetch,
  } = useDrawdownData(analysisRequest, {
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

  // 计算回撤统计
  React.useEffect(() => {
    if (drawdownData && drawdownData.datasets[0]?.data) {
      const drawdownValues = drawdownData.datasets[0].data;
      const labels = drawdownData.labels;

      // 计算最大回撤
      const maxDrawdown = Math.max(...drawdownValues);
      const maxDrawdownIndex = drawdownValues.indexOf(maxDrawdown);
      const maxDrawdownDate = labels[maxDrawdownIndex] || '';

      // 计算当前回撤
      const currentDrawdown = drawdownValues[drawdownValues.length - 1] || 0;

      // 计算回撤天数
      let daysInDrawdown = 0;
      let inDrawdown = false;
      for (let i = drawdownValues.length - 1; i >= 0; i--) {
        if (drawdownValues[i] > 0.001) { // 大于0.1%认为是回撤
          if (!inDrawdown) {
            inDrawdown = true;
          }
          daysInDrawdown++;
        } else if (inDrawdown) {
          break;
        }
      }

      setState(prev => ({
        ...prev,
        maxDrawdown,
        maxDrawdownDate,
        currentDrawdown,
        daysInDrawdown,
      }));
    }
  }, [drawdownData]);

  // 生成图表配置
  const chartData = useMemo(() => {
    if (!drawdownData) return null;

    return generateDrawdownChartData(
      drawdownData.labels,
      drawdownData.datasets[0]?.data || []
    );
  }, [drawdownData]);

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

    // 添加水平线标记重要回撤水平
    if (state.maxDrawdown > 0) {
      (options.plugins as any).annotation = {
        annotations: {
          maxDrawdownLine: {
            type: 'line',
            yMin: state.maxDrawdown,
            yMax: state.maxDrawdown,
            borderColor: CHART_COLORS.critical,
            borderWidth: 2,
            borderDash: [5, 5],
            label: {
              content: `最大回撤: ${(state.maxDrawdown * 100).toFixed(2)}%`,
              enabled: true,
              position: 'end',
              backgroundColor: CHART_COLORS.critical,
              color: '#ffffff',
            },
          },
        },
      };
    }

    // 点击事件处理
    options.onClick = (event, elements, chart) => {
      if (elements.length > 0) {
        const element = elements[0];
        const index = element.index;

        if (chartData && chartData.datasets[0]) {
          const timestamp = chartData.labels[index];
          const value = chartData.datasets[0].data[index];

          const point = { timestamp, value };
          setState(prev => ({ ...prev, selectedPoint: point }));
          onDrawdownClick?.(point);
        }
      }
    };

    return options;
  }, [showTooltip, state.maxDrawdown, chartData, onDrawdownClick]);

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
          link.download = `drawdown-chart-${strategyId}-${new Date().toISOString().split('T')[0]}.png`;
          link.href = url;
          link.click();
          break;

        case 'csv':
          const csvContent = 'Date,Drawdown\n' + chartData.labels.map((label, index) => {
            const value = chartData.datasets[0]?.data[index] || 0;
            return `${label},${value}`;
          }).join('\n');
          const csvBlob = new Blob([csvContent], { type: 'text/csv' });
          const csvUrl = URL.createObjectURL(csvBlob);
          const csvLink = document.createElement('a');
          csvLink.download = `drawdown-chart-${strategyId}-${new Date().toISOString().split('T')[0]}.csv`;
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
            statistics: {
              maxDrawdown: state.maxDrawdown,
              maxDrawdownDate: state.maxDrawdownDate,
              currentDrawdown: state.currentDrawdown,
              daysInDrawdown: state.daysInDrawdown,
            },
            exportDate: new Date().toISOString(),
          };
          const jsonBlob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
          const jsonUrl = URL.createObjectURL(jsonBlob);
          const jsonLink = document.createElement('a');
          jsonLink.download = `drawdown-chart-${strategyId}-${new Date().toISOString().split('T')[0]}.json`;
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
          <span className="text-sm font-medium">回撤统计:</span>
          <div className="flex items-center space-x-4 text-sm">
            <div className="flex items-center space-x-1">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span>最大回撤: {(state.maxDrawdown * 100).toFixed(2)}%</span>
            </div>
            <div className="flex items-center space-x-1">
              <TrendingDown className="w-4 h-4 text-orange-500" />
              <span>当前回撤: {(state.currentDrawdown * 100).toFixed(2)}%</span>
            </div>
            {state.daysInDrawdown > 0 && (
              <div className="flex items-center space-x-1">
                <Calendar className="w-4 h-4 text-blue-500" />
                <span>回撤天数: {state.daysInDrawdown}</span>
              </div>
            )}
          </div>
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
    state,
    handleExport,
  ]);

  // 渲染数据点详情
  const renderPointDetails = useCallback(() => {
    if (!state.selectedPoint) return null;

    return (
      <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-lg border z-10">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-medium">回撤详情</h4>
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
          <div>日期: {new Date(state.selectedPoint.timestamp).toLocaleDateString('zh-CN')}</div>
          <div>回撤: {(state.selectedPoint.value * 100).toFixed(2)}%</div>
        </div>
      </div>
    );
  }, [state.selectedPoint]);

  // 渲染风险警告
  const renderRiskWarning = useCallback(() => {
    if (state.maxDrawdown < 0.1) return null; // 最大回撤小于10%不显示警告

    const getRiskLevel = (drawdown: number) => {
      if (drawdown >= 0.3) return { level: '极高风险', color: 'text-red-600', icon: AlertTriangle };
      if (drawdown >= 0.2) return { level: '高风险', color: 'text-orange-600', icon: TrendingDown };
      if (drawdown >= 0.1) return { level: '中等风险', color: 'text-yellow-600', icon: AlertTriangle };
      return { level: '低风险', color: 'text-green-600', icon: TrendingUp };
    };

    const risk = getRiskLevel(state.maxDrawdown);
    const Icon = risk.icon;

    return (
      <div className={`flex items-center space-x-2 p-3 bg-gray-50 rounded-lg ${risk.color}`}>
        <Icon className="w-5 h-5" />
        <div>
          <div className="font-medium">{risk.level}</div>
          <div className="text-sm">最大回撤 {(state.maxDrawdown * 100).toFixed(2)}%</div>
        </div>
      </div>
    );
  }, [state.maxDrawdown]);

  // 加载状态
  if (isLoading && !drawdownData) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center" style={{ height }}>
          <Loading />
          <span className="ml-2 text-gray-600">加载回撤数据...</span>
        </CardContent>
      </Card>
    );
  }

  // 错误状态
  if (error && !drawdownData) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center" style={{ height }}>
          <div className="text-red-600 mb-2">
            <TrendingDown className="w-8 h-8 mx-auto mb-2" />
            <p className="text-center">加载回撤数据失败</p>
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
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center space-x-2">
            <TrendingDown className="w-5 h-5 text-red-500" />
            <span>回撤分析</span>
          </CardTitle>

          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
              className="h-8 w-8 p-0"
            >
              <TrendingDown className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
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
        </div>

        {/* 风险警告 */}
        {renderRiskWarning()}
      </CardHeader>

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
              暂无回撤数据
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

DrawdownChartComponent.displayName = 'DrawdownChart';

export default DrawdownChartComponent;