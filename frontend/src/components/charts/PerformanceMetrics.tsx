'use client';

import React, { useMemo, useCallback, useState } from 'react';
import {
  PerformanceMetrics,
  PerformanceMetricsProps,
  MetricDisplayConfig,
} from '@/types/performance.types';
import {
  usePerformanceMetrics,
  performanceService,
} from '@/services/performanceService';
import {
  formatMetricValue,
  getMetricColorClass,
  validatePerformanceMetrics,
  groupMetricsByImportance,
  groupMetricsByCategory,
  METRIC_DISPLAY_CONFIGS,
  generatePerformanceSummary,
} from '@/utils/performanceHelpers';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loading } from '@/components/ui/loading';
import {
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Info,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Shield,
  Target,
  DollarSign
} from 'lucide-react';

// 组件状态
interface PerformanceMetricsState {
  showDetails: boolean;
  selectedCategory: 'all' | 'returns' | 'risk' | 'efficiency' | 'trading';
  validationErrors: string[];
}

// 图标映射
const CATEGORY_ICONS = {
  returns: TrendingUp,
  risk: Shield,
  efficiency: BarChart3,
  trading: Target,
};

const IMPORTANCE_ICONS = {
  high: '🔥',
  medium: '⚡',
  low: '💡',
};

const PerformanceMetricsComponent: React.FC<PerformanceMetricsProps> = ({
  strategyId,
  startDate,
  endDate,
  benchmarkId,
  className = '',
  onMetricsUpdate,
  showDetails = false,
  compact = false,
}) => {
  const [state, setState] = useState<PerformanceMetricsState>({
    showDetails,
    selectedCategory: 'all',
    validationErrors: [],
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

  // 获取绩效指标
  const {
    data: metrics,
    isLoading,
    error,
    refetch,
    isFetching,
  } = usePerformanceMetrics(analysisRequest);

  // 数据验证和回调
  React.useEffect(() => {
    if (metrics) {
      // 验证数据
      const validation = validatePerformanceMetrics(metrics);
      setState(prev => ({ ...prev, validationErrors: validation.errors }));

      // 调用回调
      onMetricsUpdate?.(metrics);
    }
  }, [metrics, onMetricsUpdate]);

  // 强制刷新
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // 切换详情显示
  const toggleDetails = useCallback(() => {
    setState(prev => ({ ...prev, showDetails: !prev.showDetails }));
  }, []);

  // 切换类别
  const handleCategoryChange = useCallback((category: typeof state.selectedCategory) => {
    setState(prev => ({ ...prev, selectedCategory: category }));
  }, []);

  // 分组指标
  const groupedMetrics = useMemo(() => {
    if (!metrics) return { high: [], medium: [], low: [] };
    return groupMetricsByImportance(metrics);
  }, [metrics]);

  const categorizedMetrics = useMemo(() => {
    if (!metrics) return { returns: [], risk: [], efficiency: [], trading: [] };
    return groupMetricsByCategory(metrics);
  }, [metrics]);

  // 渲染单个指标
  const renderMetric = useCallback((
    config: MetricDisplayConfig,
    value: number | string | undefined,
    showLabel: boolean = true
  ) => {
    const colorClass = getMetricColorClass(
      typeof value === 'number' ? value : undefined,
      config.format
    );
    const formattedValue = formatMetricValue(value, config.format);
    const importanceBadge = IMPORTANCE_ICONS[config.importance];

    return (
      <div
        key={config.key}
        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center space-x-2">
          {importanceBadge && (
            <span className="text-sm" title={`重要性: ${config.importance}`}>
              {importanceBadge}
            </span>
          )}
          {showLabel && (
            <span className="text-sm font-medium text-gray-700">
              {config.label}
            </span>
          )}
        </div>
        <div className={`text-lg font-semibold ${colorClass}`}>
          {formattedValue}
        </div>
      </div>
    );
  }, []);

  // 渲染指标组
  const renderMetricGroup = useCallback((
    title: string,
    configs: MetricDisplayConfig[],
    icon?: React.ReactNode
  ) => {
    if (configs.length === 0) return null;

    return (
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          {icon}
          <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
          <Badge variant="secondary">{configs.length}</Badge>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {configs.map(config => renderMetric(config, metrics?.[config.key]))}
        </div>
      </div>
    );
  }, [metrics, renderMetric]);

  // 渲染类别标签
  const renderCategoryTabs = useCallback(() => {
    const categories = [
      { key: 'all', label: '全部', icon: BarChart3 },
      { key: 'returns', label: '收益', icon: TrendingUp },
      { key: 'risk', label: '风险', icon: Shield },
      { key: 'efficiency', label: '效率', icon: BarChart3 },
      { key: 'trading', label: '交易', icon: Target },
    ] as const;

    return (
      <div className="flex flex-wrap gap-2 mb-4">
        {categories.map(({ key, label, icon: Icon }) => (
          <Button
            key={key}
            variant={state.selectedCategory === key ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleCategoryChange(key)}
            className="flex items-center space-x-1"
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </Button>
        ))}
      </div>
    );
  }, [state.selectedCategory, handleCategoryChange]);

  // 渲染验证错误
  const renderValidationErrors = useCallback(() => {
    if (state.validationErrors.length === 0) return null;

    return (
      <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-start space-x-2">
          <Info className="w-4 h-4 text-yellow-600 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-yellow-800">数据验证警告</h4>
            <ul className="mt-1 text-sm text-yellow-700 list-disc list-inside">
              {state.validationErrors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }, [state.validationErrors]);

  // 渲染紧凑视图
  const renderCompactView = useCallback(() => {
    if (!metrics) return null;

    const importantMetrics = [
      METRIC_DISPLAY_CONFIGS.totalReturn,
      METRIC_DISPLAY_CONFIGS.maxDrawdown,
      METRIC_DISPLAY_CONFIGS.sharpeRatio,
      METRIC_DISPLAY_CONFIGS.winRate,
    ];

    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {importantMetrics.map(config => renderMetric(config, metrics[config.key], false))}
      </div>
    );
  }, [metrics, renderMetric]);

  // 渲染详细视图
  const renderDetailedView = useCallback(() => {
    if (!metrics) return null;

    let configs: MetricDisplayConfig[] = [];

    switch (state.selectedCategory) {
      case 'returns':
        configs = categorizedMetrics.returns;
        break;
      case 'risk':
        configs = categorizedMetrics.risk;
        break;
      case 'efficiency':
        configs = categorizedMetrics.efficiency;
        break;
      case 'trading':
        configs = categorizedMetrics.trading;
        break;
      default:
        configs = [
          ...groupedMetrics.high.slice(0, 4),
          ...groupedMetrics.medium.slice(0, 4),
        ];
    }

    return (
      <div className="space-y-6">
        {renderCategoryTabs()}

        {/* 高重要性指标 */}
        {state.selectedCategory === 'all' && groupedMetrics.high.length > 0 && (
          renderMetricGroup('核心指标', groupedMetrics.high, <DollarSign className="w-5 h-5 text-red-500" />)
        )}

        {/* 选类别指标 */}
        {configs.length > 0 && (
          renderMetricGroup(
            state.selectedCategory === 'all' ? '其他重要指标' :
            CATEGORIES[state.selectedCategory as keyof typeof CATEGORIES]?.label || '指标',
            configs,
            React.createElement(CATEGORY_ICONS[state.selectedCategory as keyof typeof CATEGORY_ICONS] || BarChart3, {
              className: "w-5 h-5 text-blue-500"
            })
          )
        )}
      </div>
    );
  }, [
    metrics,
    state.selectedCategory,
    groupedMetrics,
    categorizedMetrics,
    renderCategoryTabs,
    renderMetricGroup,
  ]);

  // 类别映射
  const CATEGORIES = {
    returns: { label: '收益指标' },
    risk: { label: '风险指标' },
    efficiency: { label: '效率指标' },
    trading: { label: '交易指标' },
  };

  // 加载状态
  if (isLoading && !metrics) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center p-6">
          <Loading />
          <span className="ml-2 text-gray-600">加载绩效指标...</span>
        </CardContent>
      </Card>
    );
  }

  // 错误状态
  if (error && !metrics) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center p-6">
          <div className="text-red-600 mb-2">
            <TrendingDown className="w-8 h-8 mx-auto mb-2" />
            <p className="text-center">加载绩效指标失败</p>
            <p className="text-sm text-gray-500 mt-1">
              {error instanceof Error ? error.message : '未知错误'}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4 mr-1" />
            重试
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`${className} ${isFetching ? 'opacity-75' : ''}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center space-x-2">
            <BarChart3 className="w-5 h-5" />
            <span>绩效指标</span>
            {isFetching && (
              <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
            )}
          </CardTitle>

          <div className="flex items-center space-x-2">
            {!compact && (
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleDetails}
                className="h-8 w-8 p-0"
              >
                {state.showDetails ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </Button>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={isFetching}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* 策略信息 */}
        {metrics && (
          <div className="text-sm text-gray-600">
            策略ID: {metrics.strategyId}
            {metrics.calculationDate && (
              <span className="ml-2">
                更新时间: {new Date(metrics.calculationDate).toLocaleString('zh-CN')}
              </span>
            )}
          </div>
        )}

        {/* 摘要信息 */}
        {metrics && !compact && (
          <div className="text-sm text-gray-700 bg-blue-50 p-2 rounded">
            {generatePerformanceSummary(metrics)}
          </div>
        )}
      </CardHeader>

      <CardContent className="pt-0">
        {renderValidationErrors()}

        {metrics ? (
          <>
            {compact ? renderCompactView() : renderDetailedView()}

            {/* 详细信息切换按钮 */}
            {!compact && !state.showDetails && (
              <div className="mt-4 text-center">
                <Button variant="outline" size="sm" onClick={toggleDetails}>
                  查看详细指标
                  <ChevronDown className="w-4 h-4 ml-1" />
                </Button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center text-gray-500 py-4">
            暂无绩效数据
          </div>
        )}
      </CardContent>
    </Card>
  );
};

PerformanceMetricsComponent.displayName = 'PerformanceMetrics';

export default PerformanceMetricsComponent;