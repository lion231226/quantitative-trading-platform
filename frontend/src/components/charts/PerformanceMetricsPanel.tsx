'use client'

import React, { useMemo } from 'react'
import { PerformanceMetrics } from '../../types/kline.types'
import { useTheme } from '../theme/ThemeProvider'

interface PerformanceMetricsPanelProps {
  metricsData: Array<{
    curveId: string
    curveName: string
    metrics: PerformanceMetrics
  }>
  className?: string
  showDetails?: boolean
  compact?: boolean
}

/**
 * 性能指标面板组件
 * 显示资金曲线的关键性能指标
 */
const PerformanceMetricsPanel: React.FC<PerformanceMetricsPanelProps> = ({
  metricsData,
  className = '',
  showDetails = false,
  compact = false
}) => {
  const { currentTheme } = useTheme()

  // 格式化百分比
  const formatPercent = (value: number, decimals: number = 2): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`
  }

  // 格式化比率
  const formatRatio = (value: number, decimals: number = 3): string => {
    return value.toFixed(decimals)
  }

  // 获取指标颜色
  const getMetricColor = (value: number, isHigherBetter: boolean = true): string => {
    if (value === 0) return currentTheme.colors.text

    if (isHigherBetter) {
      return value > 0 ? currentTheme.colors.bullish : currentTheme.colors.bearish
    } else {
      return value > 0 ? currentTheme.colors.bearish : currentTheme.colors.bullish
    }
  }

  // 主要指标（紧凑模式显示）
  const PrimaryMetrics = ({ metrics }: { metrics: PerformanceMetrics }) => (
    <div className="grid grid-cols-3 gap-4 text-center">
      <div>
        <div className="text-xs text-gray-500 mb-1">收益率</div>
        <div
          className="text-lg font-semibold"
          style={{ color: getMetricColor(metrics.returnRate) }}
        >
          {formatPercent(metrics.returnRate)}
        </div>
      </div>
      <div>
        <div className="text-xs text-gray-500 mb-1">最大回撤</div>
        <div
          className="text-lg font-semibold"
          style={{ color: getMetricColor(metrics.maxDrawdown, false) }}
        >
          {formatPercent(metrics.maxDrawdown)}
        </div>
      </div>
      <div>
        <div className="text-xs text-gray-500 mb-1">夏普比率</div>
        <div
          className="text-lg font-semibold"
          style={{ color: getMetricColor(metrics.sharpeRatio) }}
        >
          {formatRatio(metrics.sharpeRatio)}
        </div>
      </div>
    </div>
  )

  // 详细指标
  const DetailedMetrics = ({ metrics }: { metrics: PerformanceMetrics }) => (
    <div className="space-y-4">
      {/* 收益指标 */}
      <div>
        <h4 className="text-sm font-medium mb-2 text-gray-700">收益指标</h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">总收益率:</span>
            <span style={{ color: getMetricColor(metrics.returnRate) }}>
              {formatPercent(metrics.returnRate)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">年化收益:</span>
            <span style={{ color: getMetricColor(metrics.annualizedReturn) }}>
              {formatPercent(metrics.annualizedReturn)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">总收益:</span>
            <span style={{ color: getMetricColor(metrics.totalReturn) }}>
              {formatPercent(metrics.totalReturn * 100)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">波动率:</span>
            <span style={{ color: currentTheme.colors.text }}>
              {formatPercent(metrics.volatility)}
            </span>
          </div>
        </div>
      </div>

      {/* 风险指标 */}
      <div>
        <h4 className="text-sm font-medium mb-2 text-gray-700">风险指标</h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">最大回撤:</span>
            <span style={{ color: getMetricColor(metrics.maxDrawdown, false) }}>
              {formatPercent(metrics.maxDrawdown)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">夏普比率:</span>
            <span style={{ color: getMetricColor(metrics.sharpeRatio) }}>
              {formatRatio(metrics.sharpeRatio)}
            </span>
          </div>
        </div>
      </div>

      {/* 交易指标（如果有数据） */}
      {(metrics.winRate > 0 || metrics.profitFactor > 0) && (
        <div>
          <h4 className="text-sm font-medium mb-2 text-gray-700">交易指标</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {metrics.winRate > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">胜率:</span>
                <span style={{ color: getMetricColor(metrics.winRate) }}>
                  {formatPercent(metrics.winRate)}
                </span>
              </div>
            )}
            {metrics.profitFactor > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">盈利因子:</span>
                <span style={{ color: getMetricColor(metrics.profitFactor) }}>
                  {formatRatio(metrics.profitFactor)}
                </span>
              </div>
            )}
            {metrics.maxConsecutiveWins > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">最大连胜:</span>
                <span style={{ color: currentTheme.colors.text }}>
                  {metrics.maxConsecutiveWins}
                </span>
              </div>
            )}
            {metrics.maxConsecutiveLosses > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">最大连亏:</span>
                <span style={{ color: currentTheme.colors.text }}>
                  {metrics.maxConsecutiveLosses}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )

  if (metricsData.length === 0) {
    return (
      <div className={`performance-metrics-panel ${className}`}>
        <div className="text-center text-gray-500 py-4">
          暂无资金曲线数据
        </div>
      </div>
    )
  }

  return (
    <div
      className={`performance-metrics-panel ${className}`}
      style={{
        backgroundColor: currentTheme.colors.background,
        borderColor: currentTheme.colors.grid,
        color: currentTheme.colors.text
      }}
    >
      <div className="border-b pb-2 mb-4" style={{ borderColor: currentTheme.colors.grid }}>
        <h3 className="text-lg font-semibold">性能指标</h3>
      </div>

      {/* 多条曲线的指标 */}
      <div className="space-y-6">
        {metricsData.map(({ curveId, curveName, metrics }) => (
          <div key={curveId} className="p-3 rounded-lg border" style={{
            backgroundColor: currentTheme.colors.background,
            borderColor: currentTheme.colors.grid
          }}>
            <h4 className="font-medium mb-3">{curveName}</h4>

            {compact ? (
              <PrimaryMetrics metrics={metrics} />
            ) : (
              <DetailedMetrics metrics={metrics} />
            )}
          </div>
        ))}
      </div>

      {/* 基准比较（如果有多个曲线） */}
      {metricsData.length > 1 && (
        <div className="mt-6 pt-4 border-t" style={{ borderColor: currentTheme.colors.grid }}>
          <h4 className="text-sm font-medium mb-2 text-gray-700">对比分析</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {metricsData.map(({ curveId, curveName, metrics }) => {
              const baselineMetrics = metricsData[0].metrics // 使用第一条曲线作为基准
              const returnDiff = metrics.returnRate - baselineMetrics.returnRate
              const sharpeDiff = metrics.sharpeRatio - baselineMetrics.sharpeRatio

              return (
                <div key={curveId} className="flex justify-between">
                  <span className="text-gray-600">{curveName} vs 基准:</span>
                  <div>
                    <span style={{ color: getMetricColor(returnDiff) }}>
                      收益 {formatPercent(returnDiff)}
                    </span>
                    <span className="mx-1">|</span>
                    <span style={{ color: getMetricColor(sharpeDiff) }}>
                      夏普 {returnDiff > 0 ? '+' : ''}{sharpeDiff.toFixed(3)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export { PerformanceMetricsPanel }
export default PerformanceMetricsPanel