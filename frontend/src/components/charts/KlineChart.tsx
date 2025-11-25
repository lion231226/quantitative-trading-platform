import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import {
  KlineChartProps,
  KlineConfig,
  TimePeriod,
  CandlestickData,
  KlineData,
  createDefaultKlineConfig,
  KlineChartError
} from '../../types/kline.types'
import {
  createLightweightChartConfig,
  convertToLightweightChartsData,
  convertVolumeData,
  KlineDataSampler,
  debounce,
  throttle,
  createDefaultKlineConfig
} from '../../utils/klineHelpers'
import { KlineDataValidator } from '../../services/klineService'

export const KlineChart: React.FC<KlineChartProps> = ({
  data,
  config: userConfig,
  className = '',
  onSignalClick,
  onTimePeriodChange,
  onDataPointHover,
  onChartReady
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const volumeSeriesRef = useRef<any>(null)
  const resizeObserverRef = useRef<ResizeObserver>()

  // 合并配置
  const config = useMemo(() => {
    return createDefaultKlineConfig(userConfig)
  }, [userConfig])

  // 优化数据
  const optimizedData = useMemo(() => {
    if (!config.performance.enableDataSampling) {
      return data
    }

    const sampledCandlesticks = KlineDataSampler.sample(
      data.candlesticks,
      config.performance.maxDataPoints,
      true // 保持重要数据点
    )

    return {
      ...data,
      candlesticks: sampledCandlesticks
    }
  }, [data, config.performance.enableDataSampling, config.performance.maxDataPoints])

  // 状态管理
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<KlineChartError | null>(null)
  const [dataStats, setDataStats] = useState<any>(null)

  // 数据验证
  const validateData = useCallback((klineData: KlineData) => {
    const validation = KlineDataValidator.validate(klineData)
    if (!validation.isValid) {
      setError({
        type: 'DATA_ERROR',
        message: 'K线数据验证失败',
        details: validation.errors,
        timestamp: new Date().toISOString()
      })
      return false
    }

    if (validation.warnings.length > 0) {
      console.warn('K线数据警告:', validation.warnings)
    }

    // 设置数据统计
    setDataStats({
      dataPoints: validation.dataPoints,
      dateRange: validation.dateRange,
      warnings: validation.warnings.length
    })

    return true
  }, [])

  // 创建图表
  const createChart = useCallback(async () => {
    if (!containerRef.current || !optimizedData) return

    try {
      setIsLoading(true)
      setError(null)

      // 动态导入Lightweight Charts
      const { createChart } = await import('lightweight-charts')

      // 获取容器尺寸
      const container = containerRef.current
      const width = container.clientWidth || config.width || 800
      const height = container.clientHeight || config.height || 400

      // 创建图表配置
      const chartConfig = createLightweightChartConfig(config, width, height)

      // 创建图表实例
      const chart = createChart(container, chartConfig)
      chartRef.current = chart

      // 添加K线序列
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: config.colors.bullish,
        downColor: config.colors.bearish,
        borderVisible: false,
        wickUpColor: config.colors.bullish,
        wickDownColor: config.colors.bearish,
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01
        }
      })

      candlestickSeriesRef.current = candlestickSeries

      // 添加成交量序列（如果启用）
      let volumeSeries = null
      if (config.showVolume) {
        volumeSeries = chart.addHistogramSeries({
          color: config.colors.volume,
          priceFormat: {
            type: 'volume'
          },
          priceScaleId: 'volume'
        })

        volumeSeriesRef.current = volumeSeries

        // 设置成交量刻度
        chart.priceScale('volume').applyOptions({
          scaleMargins: {
            top: 0.8,
            bottom: 0
          }
        })
      }

      // 设置K线数据
      const chartData = convertToLightweightChartsData(optimizedData.candlesticks)
      candlestickSeries.setData(chartData)

      // 设置成交量数据
      if (config.showVolume && volumeSeries) {
        const volumeData = convertVolumeData(optimizedData.candlesticks)
        volumeSeries.setData(volumeData)
      }

      // 设置时间范围
      chart.timeScale().fitContent()

      // 添加事件监听器
      if (onDataPointHover) {
        chart.subscribeCrosshairMove((param: any) => {
          if (param.time && param.seriesData.size > 0) {
            const candlestickData = param.seriesData.get(candlestickSeries)
            if (candlestickData) {
              const originalData = optimizedData.candlesticks.find(
                c => new Date(c.timestamp).getTime() / 1000 === param.time
              )
              if (originalData) {
                onDataPointHover(originalData)
              }
            }
          } else {
            onDataPointHover(null)
          }
        })
      }

      // 添加点击事件
      if (onSignalClick) {
        chart.subscribeClick((param: any) => {
          if (param.time && param.seriesData.size > 0) {
            const time = new Date(param.time * 1000).toISOString()
            const signals = optimizedData.signals?.filter(s => s.timestamp === time)
            if (signals && signals.length > 0) {
              signals.forEach(onSignalClick)
            }
          }
        })
      }

      // 配置交互
      chart.applyOptions({
        handleScroll: {
          vertTouchDrag: true
        },
        handleScale: {
          axisPressedMouseMove: {
            time: true,
            price: false
          },
          mouseWheel: true,
          pinch: true
        }
      })

      setIsLoading(false)
      onChartReady?.()

    } catch (err) {
      setError({
        type: 'RENDER_ERROR',
        message: '图表创建失败',
        details: err,
        timestamp: new Date().toISOString()
      })
      setIsLoading(false)
    }
  }, [optimizedData, config, onDataPointHover, onSignalClick, onChartReady])

  // 销毁图表
  const destroyChart = useCallback(() => {
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      candlestickSeriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, [])

  // 更新图表数据
  const updateChart = useCallback(() => {
    if (!chartRef.current || !candlestickSeriesRef.current || !optimizedData) return

    try {
      const chartData = convertToLightweightChartsData(optimizedData.candlesticks)
      candlestickSeriesRef.current.setData(chartData)

      if (volumeSeriesRef.current && config.showVolume) {
        const volumeData = convertVolumeData(optimizedData.candlesticks)
        volumeSeriesRef.current.setData(volumeData)
      }

      chartRef.current.timeScale().fitContent()
    } catch (err) {
      setError({
        type: 'RENDER_ERROR',
        message: '数据更新失败',
        details: err,
        timestamp: new Date().toISOString()
      })
    }
  }, [optimizedData, config.showVolume])

  // 处理窗口大小变化
  const handleResize = useCallback(
    throttle(() => {
      if (chartRef.current && containerRef.current) {
        const width = containerRef.current.clientWidth
        const height = containerRef.current.clientHeight
        chartRef.current.applyOptions({ width, height })
      }
    }, 100),
    []
  )

  // 初始化和清理
  useEffect(() => {
    if (optimizedData && validateData(optimizedData)) {
      createChart()
    }

    return () => {
      destroyChart()
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect()
      }
    }
  }, [createChart, destroyChart, validateData, optimizedData])

  // 数据变化时更新图表
  useEffect(() => {
    if (chartRef.current && optimizedData) {
      updateChart()
    }
  }, [updateChart, optimizedData])

  // 设置ResizeObserver
  useEffect(() => {
    if (containerRef.current) {
      resizeObserverRef.current = new ResizeObserver(handleResize)
      resizeObserverRef.current.observe(containerRef.current)
    }

    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect()
      }
    }
  }, [handleResize])

  // 性能监控
  useEffect(() => {
    if (dataStats?.dataPoints > 5000) {
      console.log(`大数据集渲染: ${dataStats.dataPoints} 数据点`)
    }
  }, [dataStats])

  // 错误处理
  if (error) {
    return (
      <div className={`kline-chart-error ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">图表加载失败</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error.message}</p>
                {error.details && (
                  <details className="mt-2">
                    <summary className="cursor-pointer">详细错误信息</summary>
                    <pre className="mt-1 text-xs bg-red-50 p-2 rounded overflow-auto">
                      {JSON.stringify(error.details, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // 加载状态
  if (isLoading) {
    return (
      <div className={`kline-chart-loading ${className}`}>
        <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-600">正在加载K线图...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`kline-chart-container ${className}`}>
      {/* 数据统计信息 */}
      {dataStats && (
        <div className="mb-2 flex justify-between text-xs text-gray-500">
          <span>数据点: {dataStats.dataPoints.toLocaleString()}</span>
          <span>日期范围: {dataStats.dateRange.start} 至 {dataStats.dateRange.end}</span>
          {dataStats.warnings > 0 && (
            <span className="text-yellow-600">⚠️ {dataStats.warnings} 个警告</span>
          )}
        </div>
      )}

      {/* 图表容器 */}
      <div
        ref={containerRef}
        className="kline-chart"
        style={{
          width: config.width || '100%',
          height: config.height || '400px'
        }}
      />

      {/* 性能优化提示 */}
      {config.performance.enableDataSampling && (
        <div className="mt-2 text-xs text-gray-500 text-center">
          {optimizedData.candlesticks.length < data.candlesticks.length && (
            <span>
              💡 数据采样优化: {optimizedData.candlesticks.length} / {data.candlesticks.length} 数据点
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default KlineChart