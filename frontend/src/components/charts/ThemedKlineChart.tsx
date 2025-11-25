'use client'

import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { KlineChartProps, FundCurveData, PerformanceMetrics, DualYAxisConfig } from '../../types/kline.types'
import { createKlineConfigFromTheme } from '../../utils/klineHelpers'
import { useTheme } from '../theme/ThemeProvider'
import { fundCurveService } from '../../services/fundCurveService'
import KlineChart from './KlineChart'
import FundCurveOverlay from './FundCurveOverlay'
import PerformanceMetricsPanel from './PerformanceMetricsPanel'
import BaselineComparison from './BaselineComparison'
import PerformanceMarkers from './PerformanceMarkers'

interface ThemedKlineChartProps extends Omit<KlineChartProps, 'config'> {
  className?: string
  autoApplyTheme?: boolean
  showFundCurves?: boolean
  fundCurves?: FundCurveData[]
  dualYAxisConfig?: Partial<DualYAxisConfig>
  onMetricsUpdate?: (metrics: PerformanceMetrics[]) => void
  onCurveClick?: (curveId: string, point: any) => void
  showBaselineComparison?: boolean
  showPerformanceMarkers?: boolean
  priceData?: Array<{ timestamp: number; price: number }>
}

/**
 * 主题化K线图表组件
 * 自动应用当前主题的颜色配置
 * 支持双Y轴资金曲线显示
 * 性能优化：使用React.memo和精细的依赖管理
 */
const ThemedKlineChart: React.FC<ThemedKlineChartProps> = React.memo(({
  data,
  className = '',
  autoApplyTheme = true,
  showFundCurves = false,
  fundCurves = [],
  dualYAxisConfig = {},
  onSignalClick,
  onTimePeriodChange,
  onDataPointHover,
  onChartReady,
  onMetricsUpdate,
  onCurveClick,
  showBaselineComparison = false,
  showPerformanceMarkers = false,
  priceData = [],
  ...rest
}) => {
  const { currentTheme } = useTheme()
  const [isThemeApplied, setIsThemeApplied] = useState(true)
  const [currentMetrics, setCurrentMetrics] = useState<PerformanceMetrics[]>([])
  const [baselineCurve, setBaselineCurve] = useState<FundCurveData | null>(null)
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const overlayContainerRef = useRef<HTMLDivElement>(null)

  // 缓存主题颜色字符串，避免对象引用变化导致的重新计算
  const themeColorsHash = useMemo(() => {
    return JSON.stringify({
      bullish: currentTheme.colors.bullish,
      bearish: currentTheme.colors.bearish,
      background: currentTheme.colors.background,
      grid: currentTheme.colors.grid,
      text: currentTheme.colors.text
    })
  }, [currentTheme.colors])

  // 基于主题创建配置 - 仅在颜色实际变化时重新计算
  const chartConfig = useMemo(() => {
    if (!autoApplyTheme) {
      return undefined
    }

    return createKlineConfigFromTheme(
      currentTheme.colors,
      {
        height: rest.height,
        width: rest.width
      }
    )
  }, [themeColorsHash, autoApplyTheme, rest.height, rest.width])

  // 优化的主题变化处理 - 减少不必要的重新渲染
  const handleThemeChange = useCallback(() => {
    if (autoApplyTheme && !isThemeApplied) {
      setIsThemeApplied(true)
    }
  }, [autoApplyTheme, isThemeApplied])

  // 监听主题变化 - 仅在主题ID或市场模式变化时触发
  useEffect(() => {
    if (autoApplyTheme) {
      // 使用requestAnimationFrame确保在下一帧渲染，避免阻塞
      requestAnimationFrame(() => {
        setIsThemeApplied(false)
        // 使用更短的延迟，提升用户体验
        setTimeout(() => {
          setIsThemeApplied(true)
        }, 16) // ~1帧的时间
      })
    }
  }, [currentTheme.id, currentTheme.marketMode, autoApplyTheme])

  // 默认双Y轴配置
  const defaultDualYAxisConfig: DualYAxisConfig = useMemo(() => ({
    leftAxis: {
      visible: true,
      textColor: currentTheme.colors.text,
      borderColor: currentTheme.colors.grid,
    },
    rightAxis: {
      visible: showFundCurves,
      textColor: currentTheme.colors.text,
      borderColor: currentTheme.colors.grid,
    },
    synchronization: {
      enabled: true,
      syncZoom: true,
      syncPan: true,
    }
  }), [currentTheme, showFundCurves])

  // 合并双Y轴配置
  const mergedDualYAxisConfig: DualYAxisConfig = useMemo(() => ({
    leftAxis: {
      ...defaultDualYAxisConfig.leftAxis,
      ...dualYAxisConfig.leftAxis,
    },
    rightAxis: {
      ...defaultDualYAxisConfig.rightAxis,
      ...dualYAxisConfig.rightAxis,
    },
    synchronization: {
      ...defaultDualYAxisConfig.synchronization,
      ...dualYAxisConfig.synchronization,
    }
  }), [defaultDualYAxisConfig, dualYAxisConfig])

  // 图表就绪回调 - 使用useCallback避免重新创建
  const handleChartReady = useCallback(() => {
    onChartReady?.()
  }, [onChartReady])

  // 处理指标更新
  const handleMetricsUpdate = useCallback((metrics: PerformanceMetrics[]) => {
    setCurrentMetrics(metrics)
    onMetricsUpdate?.(metrics)
  }, [onMetricsUpdate])

  // 处理曲线点击
  const handleCurveClick = useCallback((curveId: string, point: any) => {
    onCurveClick?.(curveId, point)
  }, [onCurveClick])

  // 处理基准更新
  const handleBaselineUpdate = useCallback((baseline: FundCurveData, metrics: PerformanceMetrics) => {
    setBaselineCurve(baseline)
  }, [])

  // 合并所有资金曲线（包括基准）
  const allFundCurves = useMemo(() => {
    const curves = [...fundCurves]
    if (baselineCurve && showBaselineComparison) {
      curves.push(baselineCurve)
    }
    return curves
  }, [fundCurves, baselineCurve, showBaselineComparison])

  // 如果不需要应用主题或主题已应用，直接渲染图表
  if (!autoApplyTheme || isThemeApplied) {
    return (
      <div className={`themed-kline-chart ${className}`}>
        {/* 主图表容器 */}
        <div className="relative">
          {/* K线图 */}
          <div ref={chartContainerRef} className="relative">
            <KlineChart
              data={data}
              config={chartConfig}
              onSignalClick={onSignalClick}
              onTimePeriodChange={onTimePeriodChange}
              onDataPointHover={onDataPointHover}
              onChartReady={handleChartReady}
              {...rest}
            />
          </div>

          {/* 资金曲线覆盖层 */}
          {showFundCurves && allFundCurves.length > 0 && chartContainerRef.current && (
            <div className="absolute inset-0 pointer-events-none">
              <FundCurveOverlay
                container={chartContainerRef.current}
                fundCurves={allFundCurves}
                dualYAxisConfig={mergedDualYAxisConfig}
                onMetricsUpdate={handleMetricsUpdate}
                onCurveClick={handleCurveClick}
              />
            </div>
          )}
        </div>

        {/* 性能指标面板 */}
        {showFundCurves && currentMetrics.length > 0 && (
          <div className="mt-4">
            <PerformanceMetricsPanel
              metricsData={allFundCurves.map((curve, index) => ({
                curveId: curve.id,
                curveName: curve.name,
                metrics: currentMetrics[index] || {
                  returnRate: 0,
                  maxDrawdown: 0,
                  sharpeRatio: 0,
                  totalReturn: 0,
                  annualizedReturn: 0,
                  volatility: 0,
                  winRate: 0,
                  profitFactor: 0,
                  maxConsecutiveWins: 0,
                  maxConsecutiveLosses: 0
                }
              }))}
              className="bg-white border border-gray-200 rounded-lg p-4"
              compact={true}
            />
          </div>
        )}

        {/* 基准比较面板 */}
        {showBaselineComparison && fundCurves.length > 0 && priceData.length > 0 && (
          <div className="mt-4">
            <BaselineComparison
              strategyCurve={fundCurves[0]}
              priceData={priceData}
              onBaselineUpdate={handleBaselineUpdate}
              className="bg-white border border-gray-200 rounded-lg"
            />
          </div>
        )}

        {/* 性能标记面板 */}
        {showPerformanceMarkers && fundCurves.length > 0 && chartContainerRef.current && (
          <div className="mt-4">
            <PerformanceMarkers
              fundCurve={fundCurves[0]}
              container={chartContainerRef.current}
              className="bg-white border border-gray-200 rounded-lg"
            />
          </div>
        )}

        {/* 主题信息显示（开发模式） */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-2 text-xs text-gray-500 bg-gray-50 p-2 rounded">
            <div className="flex items-center justify-between">
              <span>
                主题: {currentTheme.name} ({currentTheme.marketMode}) |
                资金曲线: {showFundCurves ? '启用' : '禁用'} |
                曲线数: {fundCurves.length}
              </span>
              <div className="flex items-center space-x-2">
                <span>涨色:</span>
                <div
                  className="w-3 h-3 rounded border border-gray-300"
                  style={{ backgroundColor: currentTheme.colors.bullish }}
                />
                <span>跌色:</span>
                <div
                  className="w-3 h-3 rounded border border-gray-300"
                  style={{ backgroundColor: currentTheme.colors.bearish }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // 加载状态 - 简化加载UI，减少渲染开销
  return (
    <div className={`themed-kline-chart-loading ${className}`}>
      <div className="flex items-center justify-center h-32 bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-1 text-xs text-gray-500">应用主题中...</p>
        </div>
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  // 自定义比较函数，优化性能
  const keysToCompare: (keyof ThemedKlineChartProps)[] = [
    'className', 'autoApplyTheme', 'height', 'width',
    'showFundCurves', 'showBaselineComparison', 'showPerformanceMarkers'
  ]

  const basicPropsEqual = keysToCompare.every(key => prevProps[key] === nextProps[key])
  const dataEqual = JSON.stringify(prevProps.data) === JSON.stringify(nextProps.data)
  const fundCurvesEqual = JSON.stringify(prevProps.fundCurves) === JSON.stringify(nextProps.fundCurves)
  const priceDataEqual = JSON.stringify(prevProps.priceData) === JSON.stringify(nextProps.priceData)

  return basicPropsEqual && dataEqual && fundCurvesEqual && priceDataEqual
})

export { ThemedKlineChart }
export default ThemedKlineChart