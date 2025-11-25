'use client'

import React, { useMemo, useCallback } from 'react'
import { FundCurveData, PerformanceMetrics } from '../../types/kline.types'
import { useTheme } from '../theme/ThemeProvider'
import { fundCurveService } from '../../services/fundCurveService'

interface PerformanceMarkersProps {
  fundCurve: FundCurveData
  container: HTMLElement
  className?: string
}

/**
 * 性能可视化标记组件
 * 在图表上显示回撤区域、收益区间等性能标记
 */
const PerformanceMarkers: React.FC<PerformanceMarkersProps> = ({
  fundCurve,
  container,
  className = ''
}) => {
  const { currentTheme } = useTheme()

  // 计算性能指标
  const metrics = useMemo(() => {
    return fundCurveService.calculateMetrics(fundCurve.data)
  }, [fundCurve.data])

  // 识别回撤区域和收益区间
  const performanceZones = useMemo(() => {
    if (fundCurve.data.length < 2) return { drawdowns: [], profitZones: [] }

    const data = fundCurve.data
    let peak = data[0].value
    let peakIndex = 0
    let drawdowns: Array<{ start: number; end: number; depth: number }> = []
    let profitZones: Array<{ start: number; end: number; gain: number }> = []

    let isInDrawdown = false
    let currentDrawdownStart = 0
    let isInProfitZone = false
    let currentProfitStart = 0
    let previousValue = data[0].value

    // 计算收益区间（基于初始投资）
    const initialInvestment = data[0].value
    const profitThreshold = initialInvestment * 1.05 // 5%收益阈值

    for (let i = 1; i < data.length; i++) {
      const currentValue = data[i].value
      const timestamp = data[i].timestamp

      // 更新峰值
      if (currentValue > peak) {
        peak = currentValue
        peakIndex = i
      }

      // 计算当前回撤
      const currentDrawdown = (peak - currentValue) / peak

      // 检测回撤区域开始
      if (!isInDrawdown && currentDrawdown > 0.05) { // 5%回撤阈值
        isInDrawdown = true
        currentDrawdownStart = peakIndex
      }

      // 检测回撤区域结束
      if (isInDrawdown && currentDrawdown < 0.02) { // 2%以下认为回撤结束
        drawdowns.push({
          start: data[currentDrawdownStart].timestamp,
          end: timestamp,
          depth: (data[currentDrawdownStart].value - currentValue) / data[currentDrawdownStart].value
        })
        isInDrawdown = false
      }

      // 检测收益区间
      if (!isInProfitZone && currentValue > profitThreshold) {
        isInProfitZone = true
        currentProfitStart = i - 1
      }

      if (isInProfitZone && currentValue < profitThreshold) {
        profitZones.push({
          start: data[currentProfitStart].timestamp,
          end: timestamp,
          gain: (currentValue - data[currentProfitStart].value) / data[currentProfitStart].value
        })
        isInProfitZone = false
      }

      previousValue = currentValue
    }

    // 处理未结束的区域
    if (isInDrawdown && drawdowns.length === 0) {
      drawdowns.push({
        start: data[currentDrawdownStart].timestamp,
        end: data[data.length - 1].timestamp,
        depth: (peak - data[data.length - 1].value) / peak
      })
    }

    if (isInProfitZone && profitZones.length === 0) {
      profitZones.push({
        start: data[currentProfitStart].timestamp,
        end: data[data.length - 1].timestamp,
        gain: (data[data.length - 1].value - data[currentProfitStart].value) / data[currentProfitStart].value
      })
    }

    return { drawdowns, profitZones }
  }, [fundCurve.data])

  // 渲染性能标记
  const renderMarkers = useCallback(() => {
    if (!container || performanceZones.drawdowns.length === 0 && performanceZones.profitZones.length === 0) {
      return
    }

    // 清除之前的标记
    const existingMarkers = container.querySelectorAll('.performance-marker')
    existingMarkers.forEach(marker => marker.remove())

    // 渲染回撤区域
    performanceZones.drawdowns.forEach((drawdown, index) => {
      const marker = document.createElement('div')
      marker.className = 'performance-marker drawdown-marker'
      marker.style.cssText = `
        position: absolute;
        background: ${currentTheme.colors.bearish}20;
        border-left: 2px solid ${currentTheme.colors.bearish};
        padding: 2px 6px;
        font-size: 10px;
        color: ${currentTheme.colors.bearish};
        pointer-events: none;
        z-index: 100;
      `
      marker.textContent = `回撤 ${(drawdown.depth * 100).toFixed(1)}%`

      // 简单定位（实际应用中需要更精确的时间轴映射）
      marker.style.left = '10px'
      marker.style.top = `${80 + index * 20}px`

      container.appendChild(marker)
    })

    // 渲染收益区间
    performanceZones.profitZones.forEach((zone, index) => {
      const marker = document.createElement('div')
      marker.className = 'performance-marker profit-marker'
      marker.style.cssText = `
        position: absolute;
        background: ${currentTheme.colors.bullish}20;
        border-left: 2px solid ${currentTheme.colors.bullish};
        padding: 2px 6px;
        font-size: 10px;
        color: ${currentTheme.colors.bullish};
        pointer-events: none;
        z-index: 100;
      `
      marker.textContent = `收益 +${(zone.gain * 100).toFixed(1)}%`

      // 简单定位
      marker.style.right = '10px'
      marker.style.top = `${80 + index * 20}px`

      container.appendChild(marker)
    })

  }, [container, performanceZones, currentTheme.colors])

  // 当性能区域变化时重新渲染标记
  React.useEffect(() => {
    renderMarkers()
  }, [renderMarkers])

  // 格式化百分比
  const formatPercent = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
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

  return (
    <div className={`performance-markers ${className}`} style={{
      backgroundColor: currentTheme.colors.background,
      borderColor: currentTheme.colors.grid,
      color: currentTheme.colors.text
    }}>
      <div className="p-3 border-b" style={{ borderColor: currentTheme.colors.grid }}>
        <h4 className="text-sm font-medium">{fundCurve.name} - 性能标记</h4>
      </div>

      {/* 关键指标摘要 */}
      <div className="p-3">
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div className="text-center">
            <div className="text-gray-500 mb-1">总收益</div>
            <div
              className="font-semibold"
              style={{ color: getMetricColor(metrics.returnRate) }}
            >
              {formatPercent(metrics.returnRate)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 mb-1">最大回撤</div>
            <div
              className="font-semibold"
              style={{ color: getMetricColor(metrics.maxDrawdown, false) }}
            >
              {formatPercent(metrics.maxDrawdown)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 mb-1">夏普比率</div>
            <div
              className="font-semibold"
              style={{ color: getMetricColor(metrics.sharpeRatio) }}
            >
              {metrics.sharpeRatio.toFixed(3)}
            </div>
          </div>
        </div>
      </div>

      {/* 性能区域统计 */}
      <div className="p-3 border-t" style={{ borderColor: currentTheme.colors.grid }}>
        <h5 className="text-xs font-medium mb-2">性能区域</h5>
        <div className="space-y-2 text-xs">
          {performanceZones.drawdowns.length > 0 && (
            <div className="flex justify-between">
              <span style={{ color: currentTheme.colors.bearish }}>
                回撤区域:
              </span>
              <span>
                {performanceZones.drawdowns.length} 次,
                平均 {(performanceZones.drawdowns.reduce((sum, d) => sum + d.depth, 0) / performanceZones.drawdowns.length * 100).toFixed(1)}%
              </span>
            </div>
          )}

          {performanceZones.profitZones.length > 0 && (
            <div className="flex justify-between">
              <span style={{ color: currentTheme.colors.bullish }}>
                收益区间:
              </span>
              <span>
                {performanceZones.profitZones.length} 次,
                平均 {(performanceZones.profitZones.reduce((sum, z) => sum + z.gain, 0) / performanceZones.profitZones.length * 100).toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 图例 */}
      <div className="p-3 border-t" style={{ borderColor: currentTheme.colors.grid }}>
        <h5 className="text-xs font-medium mb-2">图例</h5>
        <div className="space-y-1 text-xs">
          <div className="flex items-center space-x-2">
            <div
              className="w-3 h-3 border-l-2"
              style={{
                backgroundColor: currentTheme.colors.bearish + '20',
                borderColor: currentTheme.colors.bearish
              }}
            ></div>
            <span>回撤区域 (&gt;5%)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div
              className="w-3 h-3 border-l-2"
              style={{
                backgroundColor: currentTheme.colors.bullish + '20',
                borderColor: currentTheme.colors.bullish
              }}
            ></div>
            <span>收益区间 (&gt;5%)</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export { PerformanceMarkers }
export default PerformanceMarkers