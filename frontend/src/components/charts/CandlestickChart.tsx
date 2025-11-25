import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import {
  CandlestickData,
  KlineData,
  TimePeriod,
  KlineConfig,
  KlineChartEvent
} from '../../types/kline.types'
import { createLightweightChartConfig, convertToLightweightChartsData, createDefaultKlineConfig } from '../../utils/klineHelpers'
import { KlineDataValidator } from '../../services/klineService'

interface CandlestickChartProps {
  data: CandlestickData[]
  config?: Partial<KlineConfig>
  className?: string
  onCandlestickClick?: (data: CandlestickData, event: any) => void
  onCandlestickHover?: (data: CandlestickData | null, event: any) => void
  onTimeRangeChange?: (start: number, end: number) => void
  height?: number
  width?: number
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  config: userConfig,
  className = '',
  onCandlestickClick,
  onCandlestickHover,
  onTimeRangeChange,
  height = 400,
  width
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const volumeSeriesRef = useRef<any>(null)
  const resizeObserverRef = useRef<ResizeObserver>()

  // 合并配置
  const config = useMemo(() => {
    return createDefaultKlineConfig({
      height,
      width,
      timePeriod: TimePeriod.DAY_1,
      ...userConfig
    })
  }, [userConfig, height, width])

  // 状态管理
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentHover, setCurrentHover] = useState<CandlestickData | null>(null)

  // 验证数据
  const validateData = useCallback((candlestickData: CandlestickData[]) => {
    if (!candlestickData || candlestickData.length === 0) {
      setError('K线数据不能为空')
      return false
    }

    // 检查数据完整性
    const invalidCandles = candlestickData.filter(candle =>
      !candle.timestamp ||
      typeof candle.open !== 'number' ||
      typeof candle.high !== 'number' ||
      typeof candle.low !== 'number' ||
      typeof candle.close !== 'number' ||
      typeof candle.volume !== 'number' ||
      candle.high < candle.low
    )

    if (invalidCandles.length > 0) {
      setError(`发现 ${invalidCandles.length} 条无效K线数据`)
      return false
    }

    setError(null)
    return true
  }, [])

  // 创建成交量序列
  const createVolumeSeries = useCallback(async (chart: any) => {
    if (!config.showVolume) return null

    const volumeSeries = chart.addHistogramSeries({
      color: config.colors.volume,
      priceFormat: {
        type: 'volume'
      },
      priceScaleId: 'volume',
      scaleMargins: {
        top: 0.8,
        bottom: 0
      }
    })

    // 设置成交量数据
    const volumeData = data.map(candle => ({
      time: new Date(candle.timestamp).getTime() / 1000,
      value: candle.volume,
      color: candle.close >= candle.open ? config.colors.bullish : config.colors.bearish
    }))

    volumeSeries.setData(volumeData)
    return volumeSeries
  }, [config.showVolume, config.colors, data])

  // 创建K线图
  const createChart = useCallback(async () => {
    if (!containerRef.current || !validateData(data)) return

    try {
      setIsLoading(true)
      setError(null)

      // 动态导入Lightweight Charts
      const { createChart, IChartApi, ISeriesApi } = await import('lightweight-charts')

      const container = containerRef.current
      const chartWidth = width || container.clientWidth || 800
      const chartHeight = height || 400

      // 创建图表配置
      const chartConfig = createLightweightChartConfig(config, chartWidth, chartHeight)

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

      // 添加成交量序列
      const volumeSeries = await createVolumeSeries(chart)
      volumeSeriesRef.current = volumeSeries

      // 设置K线数据
      const chartData = convertToLightweightChartsData(data)
      candlestickSeries.setData(chartData)

      // 设置时间范围
      chart.timeScale().fitContent()

      // 添加事件监听器
      chart.subscribeCrosshairMove((param: any) => {
        if (param.time && param.seriesData.size > 0) {
          const candlestickData = param.seriesData.get(candlestickSeries)
          if (candlestickData) {
            const originalData = data.find(
              c => new Date(c.timestamp).getTime() / 1000 === param.time
            )
            if (originalData) {
              setCurrentHover(originalData)
              onCandlestickHover?.(originalData, param)
            }
          }
        } else {
          setCurrentHover(null)
          onCandlestickHover?.(null, param)
        }
      })

      // 添加点击事件
      chart.subscribeClick((param: any) => {
        if (param.time && param.seriesData.size > 0) {
          const time = new Date(param.time * 1000).toISOString()
          const clickedCandle = data.find(c => c.timestamp === time)
          if (clickedCandle) {
            onCandlestickClick?.(clickedCandle, param)
          }
        }
      })

      // 监听时间范围变化
      chart.timeScale().subscribeVisibleTimeRangeChange((range: any) => {
        if (range && range.from && range.to) {
          onTimeRangeChange?.(range.from, range.to)
        }
      })

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
    } catch (err) {
      setError('图表创建失败: ' + (err as Error).message)
      setIsLoading(false)
    }
  }, [
    data,
    config,
    width,
    height,
    validateData,
    createVolumeSeries,
    onCandlestickClick,
    onCandlestickHover,
    onTimeRangeChange
  ])

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
    if (!chartRef.current || !candlestickSeriesRef.current || !validateData(data)) return

    try {
      const chartData = convertToLightweightChartsData(data)
      candlestickSeriesRef.current.setData(chartData)

      if (volumeSeriesRef.current && config.showVolume) {
        const volumeData = data.map(candle => ({
          time: new Date(candle.timestamp).getTime() / 1000,
          value: candle.volume,
          color: candle.close >= candle.open ? config.colors.bullish : config.colors.bearish
        }))
        volumeSeriesRef.current.setData(volumeData)
      }

      chartRef.current.timeScale().fitContent()
    } catch (err) {
      setError('数据更新失败: ' + (err as Error).message)
    }
  }, [data, config.showVolume, config.colors, validateData])

  // 处理窗口大小变化
  const handleResize = useCallback(() => {
    if (chartRef.current && containerRef.current) {
      const chartWidth = width || containerRef.current.clientWidth
      const chartHeight = height || 400
      chartRef.current.applyOptions({
        width: chartWidth,
        height: chartHeight
      })
    }
  }, [width, height])

  // 初始化和清理
  useEffect(() => {
    createChart()

    return () => {
      destroyChart()
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect()
      }
    }
  }, [createChart, destroyChart])

  // 数据变化时更新图表
  useEffect(() => {
    if (chartRef.current) {
      updateChart()
    }
  }, [updateChart])

  // 设置ResizeObserver
  useEffect(() => {
    if (containerRef.current && !width) {
      resizeObserverRef.current = new ResizeObserver(handleResize)
      resizeObserverRef.current.observe(containerRef.current)
    }

    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect()
      }
    }
  }, [handleResize, width])

  // 计算当前悬停K线的统计信息
  const hoverStats = useMemo(() => {
    if (!currentHover) return null

    const priceChange = currentHover.close - currentHover.open
    const priceChangePercent = (priceChange / currentHover.open) * 100
    const priceRange = currentHover.high - currentHover.low
    const bodySize = Math.abs(currentHover.close - currentHover.open)

    return {
      ...currentHover,
      priceChange,
      priceChangePercent,
      priceRange,
      bodySize,
      isBullish: currentHover.close >= currentHover.open
    }
  }, [currentHover])

  // 加载状态
  if (isLoading) {
    return (
      <div className={`candlestick-chart-loading ${className}`}>
        <div className="flex items-center justify-center bg-gray-50 rounded-lg" style={{ height }}>
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-600">正在加载K线图...</p>
          </div>
        </div>
      </div>
    )
  }

  // 错误状态
  if (error) {
    return (
      <div className={`candlestick-chart-error ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4" style={{ height }}>
          <div className="flex items-center">
            <svg className="h-5 w-5 text-red-400 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`candlestick-chart-container ${className}`}>
      {/* 悬停信息面板 */}
      {hoverStats && (
        <div className="absolute top-2 right-2 bg-white bg-opacity-95 shadow-lg rounded-lg p-3 z-10 pointer-events-none">
          <div className="text-sm space-y-1">
            <div className="font-semibold text-gray-800">
              {new Date(hoverStats.timestamp).toLocaleString('zh-CN')}
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-600">开盘:</span>
                <span>{hoverStats.open.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">收盘:</span>
                <span className={hoverStats.isBullish ? 'text-green-600' : 'text-red-600'}>
                  {hoverStats.close.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">最高:</span>
                <span className="text-gray-800">{hoverStats.high.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">最低:</span>
                <span className="text-gray-800">{hoverStats.low.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">成交量:</span>
                <span className="text-gray-800">{hoverStats.volume.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">涨跌:</span>
                <span className={hoverStats.isBullish ? 'text-green-600' : 'text-red-600'}>
                  {hoverStats.priceChange >= 0 ? '+' : ''}{hoverStats.priceChange.toFixed(2)}
                  ({hoverStats.priceChangePercent >= 0 ? '+' : ''}{hoverStats.priceChangePercent.toFixed(2)}%)
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 图表容器 */}
      <div
        ref={containerRef}
        className="candlestick-chart"
        style={{
          width: width || '100%',
          height: height || '400px'
        }}
      />

      {/* 数据统计信息 */}
      <div className="mt-2 text-xs text-gray-500 text-center">
        {data.length.toLocaleString()} 条K线数据
        {currentHover && (
          <span className="ml-2">
            当前悬停: {new Date(currentHover.timestamp).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  )
}

export default CandlestickChart