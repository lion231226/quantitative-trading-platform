'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  ChartConfig,
  ChartData,
  ChartInteractionConfig,
  ChartLayout,
  ChartTheme,
  ExportFormat,
  ExportPreferences,
  PerformanceConfig,
  TradingSignal,
} from '@/types/chart.types';
import InteractivePriceChart from './InteractivePriceChart'
import TradingSignals from './TradingSignals'
import MovingAverages from './MovingAverages';
import { ChartControls } from './ChartControls';
import { ChartPreferencesManager, ChartPreferencesUtils, ResponsiveChartConfig } from '@/utils/chartPreferences';
import { ChartExporter } from '@/utils/chartExport';

// 响应式断点
const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
  desktop: 1200,
};

// 组件Props
export interface ChartContainerProps {
  data: ChartData
  title?: string
  description?: string
  className?: string
  enableAllFeatures?: boolean
  showTitle?: boolean
  showDescription?: boolean
  enableResponsive?: boolean
  userId?: string
  onSignalClick?: (signal: TradingSignal) => void
  onConfigChange?: (config: ChartConfig) => void
}

export function ChartContainer({
  data,
  title = '交互式数据可视化',
  description = '价格走势与交易信号分析',
  className = '',
  enableAllFeatures = true,
  showTitle = true,
  showDescription = true,
  enableResponsive = true,
  userId,
  onSignalClick,
  onConfigChange,
}: ChartContainerProps) {
  const [screenWidth, setScreenWidth] = useState(1200);
  const [isClient, setIsClient] = useState(false);
  const [activeTab, setActiveTab] = useState<'chart' | 'signals' | 'movingAverages'>('chart');
  const [isExporting, setIsExporting] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);

  // 偏好管理器
  const preferencesManager = useMemo(() => {
    if (isClient) {
      return new ChartPreferencesManager(userId);
    }
    return null;
  }, [isClient, userId]);

  // 当前偏好设置
  const preferences = useMemo(() => {
    return preferencesManager?.getPreferences() || {
      chartConfig: {
        showSignals: true,
        showMovingAverages: true,
        movingAverageType: 'SMA' as const,
        movingAveragePeriod: 20,
        showVolume: false,
        animationDuration: 1000,
      },
      interactionConfig: {
        enableZoom: true,
        enablePan: true,
        zoomMode: 'x' as const,
        panMode: 'x' as const,
        wheelSensitivity: 0.1,
        enableTooltip: true,
        enableCrosshair: false,
        enableDataLabels: false,
      },
      performanceConfig: {
        enableDataSampling: true,
        maxDataPoints: 1000,
        enableAnimation: true,
        animationDuration: 750,
      },
      theme: ChartPreferencesUtils.detectSystemTheme() === 'dark'
        ? { name: 'Dark', colors: { background: '#1f2937', grid: '#374151', text: '#f3f4f6', price: '#60a5fa', buySignal: '#34d399', sellSignal: '#f87171', movingAverage: '#fbbf24', volume: '#9ca3af' }, fonts: { family: 'Inter', size: { title: 16, legend: 12, axis: 11, tooltip: 12 } }, styles: { lineWidth: 2, pointRadius: 4, gridLines: true, animations: true } }
        : { name: 'Light', colors: { background: '#ffffff', grid: '#e5e7eb', text: '#374151', price: '#3b82f6', buySignal: '#22c55e', sellSignal: '#ef4444', movingAverage: '#f59e0b', volume: '#6b7280' }, fonts: { family: 'Inter', size: { title: 16, legend: 12, axis: 11, tooltip: 12 } }, styles: { lineWidth: 2, pointRadius: 4, gridLines: true, animations: true } },
      layout: {
        height: 400,
        padding: { top: 20, right: 20, bottom: 20, left: 20 },
        showControls: true,
        showLegend: true,
        showTooltip: true,
        responsive: true,
      },
      exportPreferences: {
        defaultFormat: 'png' as const,
        defaultFilename: 'chart',
        includeMetadata: true,
        backgroundColor: '#ffffff',
        quality: 0.9,
        dimensions: { width: 1200, height: 600 },
      },
      lastUpdated: new Date().toISOString(),
    };
  }, [preferencesManager]);

  // 响应式配置
  const responsiveConfig = useMemo(() => {
    if (!enableResponsive) return {};
    return ResponsiveChartConfig.getCurrentConfig();
  }, [enableResponsive, screenWidth]);

  // 合并配置
  const mergedConfig = useMemo(() => {
    const chartConfig = {
      ...preferences.chartConfig,
      ...responsiveConfig.chartConfig,
    };

    const interactionConfig = {
      ...preferences.interactionConfig,
      ...responsiveConfig.interactionConfig,
    };

    const performanceConfig = {
      ...preferences.performanceConfig,
      ...responsiveConfig.performanceConfig,
    };

    const layout = {
      ...preferences.layout,
      ...responsiveConfig.layout,
    };

    return {
      chartConfig,
      interactionConfig,
      performanceConfig,
      layout,
      theme: preferences.theme,
      exportPreferences: preferences.exportPreferences,
    };
  }, [preferences, responsiveConfig]);

  // 客户端检测
  useEffect(() => {
    setIsClient(true);
  }, []);

  // 屏幕尺寸监听
  useEffect(() => {
    if (!enableResponsive) return;

    const updateScreenWidth = () => {
      setScreenWidth(window.innerWidth);
    };

    updateScreenWidth();

    const unsubscribe = ResponsiveChartConfig.onScreenSizeChange(() => {
      updateScreenWidth();
    });

    return unsubscribe;
  }, [enableResponsive]);

  // 系统主题监听
  useEffect(() => {
    if (!isClient || !preferencesManager) return;

    const unsubscribe = ChartPreferencesUtils.onSystemThemeChange((theme) => {
      preferencesManager.updateTheme(theme);
    });

    return unsubscribe;
  }, [isClient, preferencesManager]);

  // 应用主题到DOM
  useEffect(() => {
    if (isClient && mergedConfig.theme) {
      ChartPreferencesUtils.applyThemeToDOM(mergedConfig.theme);
    }
  }, [isClient, mergedConfig.theme]);

  // 处理配置变化
  const handleConfigChange = useCallback((config: Partial<ChartConfig>) => {
    const updatedConfig: ChartConfig = {
      showSignals: config.showSignals ?? true,
      showMovingAverages: config.showMovingAverages ?? true,
      movingAverageType: config.movingAverageType ?? 'SMA',
      movingAveragePeriod: config.movingAveragePeriod ?? 20,
      showVolume: config.showVolume ?? false,
      animationDuration: config.animationDuration ?? 1000,
    };
    onConfigChange?.(updatedConfig);

    if (preferencesManager) {
      preferencesManager.updateChartConfig(config);
    }
  }, [mergedConfig.chartConfig, onConfigChange, preferencesManager]);

  // 处理信号点击
  const handleSignalClick = useCallback((signal: TradingSignal) => {
    onSignalClick?.(signal);
  }, [onSignalClick]);

  // 导出功能
  const handleExport = useCallback(async (format: ExportFormat) => {
    if (!isClient) return;

    setIsExporting(true);
    try {
      // 这里需要获取图表实例，暂时使用模拟实现
      // Exporting chart as ${format}

      // 实际实现需要从图表组件获取实例
      // const exporter = new ChartExporter(chartInstance, data)
      // await exporter.exportAndDownload(format, mergedConfig.exportPreferences)

    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  }, [isClient, data, mergedConfig.exportPreferences]);

  // 渲染响应式布局
  const renderResponsiveLayout = () => {
    const isMobile = screenWidth < BREAKPOINTS.mobile;
    const isTablet = screenWidth >= BREAKPOINTS.mobile && screenWidth < BREAKPOINTS.tablet;

    if (isMobile) {
      return (
        <div className="space-y-4">
          {/* 移动端标签导航 */}
          <div className="flex border-b">
            <button
              className={`flex-1 py-2 px-4 text-sm font-medium ${
                activeTab === 'chart'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500'
              }`}
              onClick={() => setActiveTab('chart')}
            >
              图表
            </button>
            <button
              className={`flex-1 py-2 px-4 text-sm font-medium ${
                activeTab === 'signals'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500'
              }`}
              onClick={() => setActiveTab('signals')}
            >
              信号
            </button>
            <button
              className={`flex-1 py-2 px-4 text-sm font-medium ${
                activeTab === 'movingAverages'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500'
              }`}
              onClick={() => setActiveTab('movingAverages')}
            >
              均线
            </button>
          </div>

          {/* 移动端内容区域 */}
          <div className="min-h-[400px]">
            {activeTab === 'chart' && (
              <InteractivePriceChart
                data={data}
                height={mergedConfig.layout.height}
                onSignalClick={handleSignalClick}
                enableInteractions={mergedConfig.interactionConfig.enableZoom}
              />
            )}

            {activeTab === 'signals' && (
              <TradingSignals
                signals={data.signals}
                onSignalClick={handleSignalClick}
                height={mergedConfig.layout.height}
              />
            )}

            {activeTab === 'movingAverages' && (
              <MovingAverages
                priceData={data.prices}
                movingAverages={data.movingAverages}
                height={mergedConfig.layout.height}
                showControls={true}
              />
            )}
          </div>
        </div>
      );
    }

    // 平板和桌面端布局
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主图表区域 */}
        <div className="lg:col-span-2">
          <InteractivePriceChart
            data={data}
            height={mergedConfig.layout.height}
            onSignalClick={handleSignalClick}
            enableInteractions={mergedConfig.interactionConfig.enableZoom}
          />
        </div>

        {/* 侧边栏 */}
        <div className="space-y-6">
          {/* 交易信号 */}
          <TradingSignals
            signals={data.signals}
            onSignalClick={handleSignalClick}
            height={250}
          />

          {/* 移动平均线 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">移动平均线</CardTitle>
            </CardHeader>
            <CardContent>
              <MovingAverages
                priceData={data.prices}
                movingAverages={data.movingAverages}
                height={200}
                showControls={isTablet}
                className="border-0 shadow-none"
              />
            </CardContent>
          </Card>

          {/* 快速操作 */}
          {enableAllFeatures && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">快速操作</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowPreferences(!showPreferences)}
                  >
                    设置
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    );
  };

  // 渲染控制面板
  const renderControls = () => {
    if (!mergedConfig.layout.showControls || screenWidth < BREAKPOINTS.tablet) {
      return null;
    }

    const chartConfigForControls: ChartConfig = {
      showSignals: mergedConfig.chartConfig.showSignals ?? true,
      showMovingAverages: mergedConfig.chartConfig.showMovingAverages ?? true,
      movingAverageType: mergedConfig.chartConfig.movingAverageType ?? 'SMA',
      movingAveragePeriod: mergedConfig.chartConfig.movingAveragePeriod ?? 20,
      showVolume: mergedConfig.chartConfig.showVolume ?? false,
      animationDuration: mergedConfig.chartConfig.animationDuration ?? 1000,
    };

    return (
      <ChartControls
        config={chartConfigForControls}
        onConfigChange={handleConfigChange}
        onReset={() => {
          if (preferencesManager) {
            preferencesManager.resetToDefaults();
          }
        }}
      />
    );
  };

  if (!isClient) {
    // 服务端渲染占位符
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-16">
          <div className="text-center text-gray-500">
            <div className="text-lg font-medium mb-2">图表加载中...</div>
            <div className="text-sm">请稍候</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`chart-container ${className}`}>
      {showTitle && (
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {showDescription && (
            <p className="text-gray-600 mt-2">{description}</p>
          )}
        </div>
      )}

      {renderControls()}

      <Card>
        <CardContent className="p-6">
          {renderResponsiveLayout()}
        </CardContent>
      </Card>

      {/* 偏好设置面板 */}
      {showPreferences && enableAllFeatures && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                图表设置
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPreferences(false)}
                >
                  ×
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* 主题选择 */}
                <div>
                  <h3 className="text-lg font-medium mb-3">主题</h3>
                  <div className="grid grid-cols-3 gap-2">
                    {['light', 'dark', 'professional'].map((theme) => (
                      <Button
                        key={theme}
                        variant={mergedConfig.theme.name.toLowerCase() === theme ? 'default' : 'outline'}
                        onClick={() => {
                          if (preferencesManager) {
                            preferencesManager.updateTheme(theme.charAt(0).toUpperCase() + theme.slice(1));
                          }
                        }}
                      >
                        {theme.charAt(0).toUpperCase() + theme.slice(1)}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* 重置按钮 */}
                <div className="pt-4 border-t">
                  <Button
                    variant="outline"
                    onClick={() => {
                      if (preferencesManager) {
                        preferencesManager.resetToDefaults();
                      }
                    }}
                  >
                    重置为默认设置
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default ChartContainer;
