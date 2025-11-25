import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  KlineChartProps,
  KlineData,
  TimePeriod,
  CandlestickData,
  KlineConfig,
  KlineChartEvent
} from '../../types/kline.types'
import { createDefaultKlineConfig } from '../../utils/klineHelpers'
import { createTimePeriodDataManager } from '../../services/timePeriodDataManager'
import { adaptivePerformanceService } from '../../services/adaptivePerformanceService'
import { klineDataService } from '../../services/klineService'
import { PerformanceMonitor } from './PerformanceMonitor'
import CandlestickChart from './CandlestickChart'
import TimePeriodSelector from './TimePeriodSelector'
import KlineChartControls from './KlineChartControls'

export const KlineChartContainer: React.FC<KlineChartProps> = ({
  data,
  config: userConfig,
  className = '',
  onSignalClick,
  onTimePeriodChange,
  onDataPointHover,
  onChartReady
}) => {
  // 状态管理
  const [config, setConfig] = useState<KlineConfig>(() =>
    createDefaultKlineConfig(userConfig)
  )
  const [currentTimePeriod, setCurrentTimePeriod] = useState<TimePeriod>(
    userConfig?.timePeriod || TimePeriod.DAY_1
  )
  const [showPerformanceMonitor, setShowPerformanceMonitor] = useState(false)
  const [performanceMetrics, setPerformanceMetrics] = useState({
    dataPoints: data.candlesticks.length,
    renderTime: 0,
    fps: 60,
    memoryUsage: 0
  })
  const [chartInstance, setChartInstance] = useState<any>(null)

  // 时间周期数据管理器
  const [dataManager] = useState(() => createTimePeriodDataManager('BTC-USDT'))
  const [currentData, setCurrentData] = useState<KlineData>(data)
  const [isLoading, setIsLoading] = useState(false)

  // 可用时间周期
  const availableTimePeriods: TimePeriod[] = [
    TimePeriod.MINUTE_1,
    TimePeriod.MINUTE_5,
    TimePeriod.MINUTE_15,
    TimePeriod.MINUTE_30,
    TimePeriod.HOUR_1,
    TimePeriod.HOUR_4,
    TimePeriod.DAY_1,
    TimePeriod.DAY_7,
    TimePeriod.MONTH_1
  ]

  // 优化后的数据
  const optimizedData = useMemo(() => {
    if (!config.performance.enableDataSampling) {
      return data
    }

    const metrics = {
      dataPoints: data.candlesticks.length,
      renderTime: performanceMetrics.renderTime,
      fps: performanceMetrics.fps,
      memoryUsage: performanceMetrics.memoryUsage,
      timestamp: Date.now()
    }

    const optimization = adaptivePerformanceService.optimize(
      config,
      data.candlesticks,
      metrics
    )

    // 记录优化结果
    if (optimization.appliedStrategies.length > 0) {
      console.log('🔧 应用自适应优化策略:', optimization.appliedStrategies)
    }

    return {
      ...data,
      candlesticks: optimization.data
    }
  }, [data, config, performanceMetrics])

  // 处理时间周期变化
  const handleTimePeriodChange = useCallback(async (newPeriod: TimePeriod) => {
    if (newPeriod === currentTimePeriod) return

    setCurrentTimePeriod(newPeriod)

    // 获取新周期的数据
    const newData = await klineDataService.getData('BTC-USDT', newPeriod, false)
    if (newData) {
      // 这里应该触发父组件的数据更新
      onTimePeriodChange?.(newPeriod)
    }
  }, [currentTimePeriod, onTimePeriodChange])

  // 图表控制器事件处理
  const handleZoomIn = useCallback(() => {
    if (chartInstance) {
      const timeScale = chartInstance.timeScale()
      const visibleRange = timeScale.getVisibleLogicalRange()
      if (visibleRange) {
        const center = (visibleRange.from + visibleRange.to) / 2
        const newRange = (visibleRange.to - visibleRange.from) * 0.8
        timeScale.setVisibleLogicalRange({
          from: center - newRange / 2,
          to: center + newRange / 2
        })
      }
    }
  }, [chartInstance])

  const handleZoomOut = useCallback(() => {
    if (chartInstance) {
      const timeScale = chartInstance.timeScale()
      const visibleRange = timeScale.getVisibleLogicalRange()
      if (visibleRange) {
        const center = (visibleRange.from + visibleRange.to) / 2
        const newRange = (visibleRange.to - visibleRange.from) * 1.25
        timeScale.setVisibleLogicalRange({
          from: center - newRange / 2,
          to: center + newRange / 2
        })
      }
    }
  }, [chartInstance])

  const handleResetZoom = useCallback(() => {
    if (chartInstance) {
      chartInstance.timeScale().fitContent()
    }
  }, [chartInstance])

  const handleToggleCrosshair = useCallback(() => {
    setConfig(prev => ({
      ...prev,
      showCrosshair: !prev.showCrosshair
    }))
  }, [])

  const handleToggleGrid = useCallback(() => {
    setConfig(prev => ({
      ...prev,
      showGrid: !prev.showGrid
    }))
  }, [])

  const handleExport = useCallback(() => {
    if (chartInstance) {
      // 实现图表导出功能
      const canvas = chartInstance.takeScreenshot()
      const link = document.createElement('a')
      link.download = `kline-chart-${Date.now()}.png`
      link.href = canvas.toDataURL()
      link.click()
    }
  }, [chartInstance])

  const handleFullscreen = useCallback(() => {
    const container = document.querySelector('.kline-chart-container')
    if (container && !document.fullscreenElement) {
      container.requestFullscreen()
    } else if (document.fullscreenElement) {
      document.exitFullscreen()
    }
  }, [])

  // 处理图表准备就绪
  const handleChartReady = useCallback((chart: any) => {
    setChartInstance(chart)
    onChartReady?.()

    // 性能监控：记录渲染时间
    const startTime = performance.now()
    requestAnimationFrame(() => {
      const endTime = performance.now()
      const renderTime = endTime - startTime

      setPerformanceMetrics(prev => ({
        ...prev,
        renderTime,
        fps: 1000 / renderTime
      }))

      // 记录到自适应性能服务
      adaptivePerformanceService.recordMetrics({
        dataPoints: optimizedData.candlesticks.length,
        renderTime,
        fps: 1000 / renderTime,
        memoryUsage: performance.memory?.usedJSHeapSize || 0,
        timestamp: Date.now()
      })
    })
  }, [optimizedData, onChartReady])

  // 处理K线点击事件
  const handleCandlestickClick = useCallback((candleData: CandlestickData, event: any) => {
    // 查找对应的交易信号
    const signals = data.signals?.filter(signal =>
      signal.timestamp === candleData.timestamp
    )

    if (signals && signals.length > 0) {
      signals.forEach(onSignalClick || (() => {}))
    }
  }, [data.signals, onSignalClick])

  // 处理K线悬停事件
  const handleCandlestickHover = useCallback((candleData: CandlestickData | null, event: any) => {
    onDataPointHover?.(candleData)
  }, [onDataPointHover])

  // 监听自适应性能优化事件
  useEffect(() => {
    const handleOptimizationEvent = (event: any) => {
      const { strategy, metrics } = event.detail
      console.log(`🔧 自适应优化触发: ${strategy}`, metrics)

      // 更新性能指标
      setPerformanceMetrics(prev => ({
        ...prev,
        fps: metrics.fps,
        renderTime: 1000 / metrics.fps
      }))

      // 更新配置
      setConfig(prev => ({
        ...prev,
        performance: {
          ...prev.performance,
          enableDataSampling: metrics.dataPoints > 5000
        }
      }))
    }

    window.addEventListener('klinePerformanceOptimization', handleOptimizationEvent)
    return () => {
      window.removeEventListener('klinePerformanceOptimization', handleOptimizationEvent)
    }
  }, [])

  // 监听配置变化
  useEffect(() => {
    setConfig(prev => ({ ...prev, ...userConfig }))
  }, [userConfig])

  // 键盘快捷键处理
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!config.interactions.keyboardShortcuts) return

      switch (event.key) {
        case '+':
        case '=':
          event.preventDefault()
          handleZoomIn()
          break
        case '-':
        case '_':
          event.preventDefault()
          handleZoomOut()
          break
        case 'r':
        case 'R':
          event.preventDefault()
          handleResetZoom()
          break
        case 'c':
        case 'C':
          event.preventDefault()
          handleToggleCrosshair()
          break
        case 'g':
        case 'G':
          event.preventDefault()
          handleToggleGrid()
          break
        case 'e':
        case 'E':
          event.preventDefault()
          handleExport()
          break
        case 'f':
        case 'F':
          event.preventDefault()
          handleFullscreen()
          break
        case 'p':
        case 'P':
          event.preventDefault()
          setShowPerformanceMonitor(prev => !prev)
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [
    config.interactions.keyboardShortcuts,
    handleZoomIn,
    handleZoomOut,
    handleResetZoom,
    handleToggleCrosshair,
    handleToggleGrid,
    handleExport,
    handleFullscreen
  ])

  return (
    <div className={`kline-chart-container ${className}`}>
      {/* 控制面板 */}
      <div className="mb-4">
        <TimePeriodSelector
          currentPeriod={currentTimePeriod}
          availablePeriods={availableTimePeriods}
          onPeriodChange={handleTimePeriodChange}
          className="mb-2"
        />

        <KlineChartControls
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onResetZoom={handleResetZoom}
          onToggleCrosshair={handleToggleCrosshair}
          onToggleGrid={handleToggleGrid}
          onExport={handleExport}
          onFullscreen={handleFullscreen}
          showCrosshair={config.showCrosshair}
          showGrid={config.showGrid}
        />
      </div>

      {/* K线图表 */}
      <div className="relative">
        <CandlestickChart
          data={optimizedData.candlesticks}
          config={config}
          onCandlestickClick={handleCandlestickClick}
          onCandlestickHover={handleCandlestickHover}
          height={config.height || 400}
        />

        {/* 性能监控覆盖层 */}
        {showPerformanceMonitor && (
          <div className="fixed top-4 right-4 z-50">
            <PerformanceMonitor
              dataPoints={performanceMetrics.dataPoints}
              renderTime={performanceMetrics.renderTime}
              fps={performanceMetrics.fps}
              memoryUsage={performanceMetrics.memoryUsage}
              showDetails={true}
            />
          </div>
        )}
      </div>

      {/* 状态栏 */}
      <div className="mt-4 flex justify-between items-center text-xs text-gray-500">
        <div>
          数据点: {optimizedData.candlesticks.length.toLocaleString()}
          {optimizedData.candlesticks.length < data.candlesticks.length && (
            <span className="ml-2 text-yellow-600">
              (优化: {((optimizedData.candlesticks.length / data.candlesticks.length) * 100).toFixed(1)}%)
            </span>
          )}
        </div>

        <div>
          当前周期: {currentTimePeriod}
        </div>

        <div>
          性能: {performanceMetrics.fps.toFixed(1)} FPS
          <span className="mx-2">•</span>
          渲染时间: {performanceMetrics.renderTime.toFixed(1)}ms
        </div>

        <div className="flex items-center gap-2">
          <span>快捷键: </span>
          <button
            onClick={() => setShowPerformanceMonitor(!showPerformanceMonitor)}
            className="text-blue-600 hover:text-blue-800"
            title="显示性能监控 (P)"
          >
            📊 性能
          </button>
          <span className="text-gray-400">| P 键</span>
        </div>
      </div>
    </div>
  )
}

export default KlineChartContainer