import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  KlineConfig,
  TimePeriod,
  CandlestickData,
  createDefaultKlineConfig
} from '../../types/kline.types'
import { klineDataService } from '../../services/klineService'
import { PerformanceBenchmarkUtil, PerformanceBenchmarkResult } from '../../utils/klineHelpers'

interface PerformanceBenchmarkProps {
  className?: string
  showDetails?: boolean
  autoRun?: boolean
  onComplete?: (results: PerformanceBenchmarkResult[]) => void
}

export const PerformanceBenchmark: React.FC<PerformanceBenchmarkProps> = ({
  className = '',
  showDetails = false,
  autoRun = false,
  onComplete
}) => {
  const [isRunning, setIsRunning] = useState(false)
  const [results, setResults] = useState<PerformanceBenchmarkResult[]>([])
  const [currentTest, setCurrentTest] = useState<string>('')
  const [progress, setProgress] = useState(0)
  const chartRef = useRef<HTMLDivElement>(null)

  // 测试数据点数量配置
  const testSizes = [100, 500, 1000, 5000, 10000]

  // 生成测试数据
  const generateTestData = useCallback(async (size: number): Promise<CandlestickData[]> => {
    const data: CandlestickData[] = []
    const now = new Date()
    let lastClose = 100

    for (let i = size - 1; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * 24 * 60 * 60 * 1000).toISOString()

      const change = (Math.random() - 0.5) * 10
      const open = lastClose + change
      const close = open + (Math.random() - 0.5) * 5
      const high = Math.max(open, close) + Math.random() * 3
      const low = Math.min(open, close) - Math.random() * 3
      const volume = Math.floor(Math.random() * 1000000)

      data.push({
        timestamp,
        open: Math.max(1, open),
        high: Math.max(1, high),
        low: Math.max(1, low),
        close: Math.max(1, close),
        volume
      })

      lastClose = close
    }

    return data
  }, [])

  // 测试Lightweight Charts性能
  const testLightweightCharts = useCallback(async (data: CandlestickData[]): Promise<number> => {
    if (!chartRef.current) return 0

    const benchmark = new PerformanceBenchmarkUtil()
    benchmark.start()

    try {
      // 动态导入Lightweight Charts
      const { createChart, CrosshairMode } = await import('lightweight-charts')

      // 创建图表
      const chart = createChart(chartRef.current, {
        width: chartRef.current.clientWidth,
        height: chartRef.current.clientHeight,
        layout: {
          background: { type: 'solid', color: 'white' },
          textColor: 'black'
        },
        grid: {
          vertLines: { visible: false },
          horzLines: { visible: false }
        }
      })

      // 添加K线序列
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350'
      })

      // 转换数据格式
      const chartData = data.map(candle => ({
        time: new Date(candle.timestamp).getTime() / 1000,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      }))

      // 设置数据
      candlestickSeries.setData(chartData)

      // 强制渲染
      chart.timeScale().fitContent()

      // 等待渲染完成
      await new Promise(resolve => setTimeout(resolve, 100))

      // 清理图表
      chart.remove()

      return benchmark.end()
    } catch (error) {
      console.error('Lightweight Charts测试失败:', error)
      return 0
    }
  }, [])

  // 测试Chart.js性能（对比）
  const testChartJS = useCallback(async (data: CandlestickData[]): Promise<number> => {
    const benchmark = new PerformanceBenchmarkUtil()
    benchmark.start()

    try {
      // 动态导入Chart.js
      const Chart = await import('chart.js/auto')

      // 创建canvas
      const canvas = document.createElement('canvas')
      canvas.width = 800
      canvas.height = 400
      chartRef.current?.appendChild(canvas)

      const ctx = canvas.getContext('2d')
      if (!ctx) return 0

      // 准备Chart.js数据
      const chartData = {
        labels: data.map(d => new Date(d.timestamp).toLocaleDateString()),
        datasets: [{
          label: 'Close Price',
          data: data.map(d => d.close),
          borderColor: '#2196f3',
          backgroundColor: 'transparent',
          borderWidth: 1,
          pointRadius: 0,
          tension: 0
        }]
      }

      // 创建图表
      const chart = new Chart.default(ctx, {
        type: 'line',
        data: chartData,
        options: {
          responsive: false,
          animation: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            x: { display: false },
            y: { display: false }
          }
        }
      })

      // 等待渲染完成
      await new Promise(resolve => setTimeout(resolve, 100))

      // 清理图表
      chart.destroy()
      canvas.remove()

      return benchmark.end()
    } catch (error) {
      console.error('Chart.js测试失败:', error)
      return 0
    }
  }, [])

  // 运行基准测试
  const runBenchmark = useCallback(async () => {
    setIsRunning(true)
    setResults([])
    setProgress(0)

    const newResults: PerformanceBenchmarkResult[] = []

    for (let i = 0; i < testSizes.length; i++) {
      const size = testSizes[i]
      setCurrentTest(`测试数据量: ${size} 点`)
      setProgress((i / testSizes.length) * 100)

      // 生成测试数据
      const testData = await generateTestData(size)

      // 测试Lightweight Charts
      const lwTime = await testLightweightCharts(testData)
      if (lwTime > 0) {
        newResults.push({
          chartLibrary: 'Lightweight Charts',
          dataPoints: size,
          renderTime: lwTime,
          memoryUsage: 0, // 简化处理
          fps: 1000 / lwTime,
          timestamp: new Date().toISOString()
        })
      }

      // 测试Chart.js（仅在小数据量时测试，避免长时间阻塞）
      if (size <= 1000) {
        const chartjsTime = await testChartJS(testData)
        if (chartjsTime > 0) {
          newResults.push({
            chartLibrary: 'Chart.js',
            dataPoints: size,
            renderTime: chartjsTime,
            memoryUsage: 0,
            fps: 1000 / chartjsTime,
            timestamp: new Date().toISOString()
          })
        }
      }

      // 短暂休息，避免浏览器阻塞
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    setResults(newResults)
    setProgress(100)
    setIsRunning(false)
    setCurrentTest('')

    if (onComplete) {
      onComplete(newResults)
    }
  }, [testSizes, generateTestData, testLightweightCharts, testChartJS, onComplete])

  // 计算性能提升倍数
  const getPerformanceImprovement = useCallback((lwTime: number, chartjsTime: number): number => {
    if (chartjsTime === 0) return 0
    return chartjsTime / lwTime
  }, [])

  // 格式化渲染时间
  const formatRenderTime = (time: number): string => {
    if (time < 1) return `${(time * 1000).toFixed(2)}ms`
    return `${time.toFixed(2)}s`
  }

  // 组件挂载时自动运行测试
  useEffect(() => {
    if (autoRun && !isRunning && results.length === 0) {
      runBenchmark()
    }
  }, [autoRun, isRunning, results.length, runBenchmark])

  return (
    <div className={`performance-benchmark ${className}`}>
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">
            图表库性能基准测试
          </h2>
          <button
            onClick={runBenchmark}
            disabled={isRunning}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isRunning ? '测试中...' : '开始测试'}
          </button>
        </div>

        {/* 测试进度 */}
        {isRunning && (
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>{currentTest}</span>
              <span>{progress.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* 测试结果 */}
        {results.length > 0 && (
          <div className="space-y-6">
            {/* 结果概览 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold text-blue-800 mb-2">
                  Lightweight Charts 平均渲染时间
                </h3>
                <p className="text-2xl font-bold text-blue-600">
                  {formatRenderTime(
                    results
                      .filter(r => r.chartLibrary === 'Lightweight Charts')
                      .reduce((sum, r) => sum + r.renderTime, 0) /
                    results.filter(r => r.chartLibrary === 'Lightweight Charts').length
                  )}
                </p>
              </div>

              <div className="bg-green-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold text-green-800 mb-2">
                  性能提升倍数
                </h3>
                <p className="text-2xl font-bold text-green-600">
                  {(() => {
                    const lwResults = results.filter(r => r.chartLibrary === 'Lightweight Charts')
                    const chartjsResults = results.filter(r => r.chartLibrary === 'Chart.js')

                    if (lwResults.length === 0 || chartjsResults.length === 0) return 'N/A'

                    const avgLw = lwResults.reduce((sum, r) => sum + r.renderTime, 0) / lwResults.length
                    const avgChartjs = chartjsResults.reduce((sum, r) => sum + r.renderTime, 0) / chartjsResults.length

                    return `${getPerformanceImprovement(avgLw, avgChartjs).toFixed(1)}x`
                  })()}
                </p>
              </div>

              <div className="bg-purple-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold text-purple-800 mb-2">
                  最大数据量支持
                </h3>
                <p className="text-2xl font-bold text-purple-600">
                  {Math.max(...results.map(r => r.dataPoints)).toLocaleString()} 点
                </p>
              </div>
            </div>

            {/* 详细结果表格 */}
            {showDetails && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        图表库
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        数据点数
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        渲染时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        FPS
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        状态
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {results.map((result, index) => (
                      <tr key={index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {result.chartLibrary}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {result.dataPoints.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatRenderTime(result.renderTime)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {result.fps.toFixed(1)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                              result.fps >= 30
                                ? 'bg-green-100 text-green-800'
                                : result.fps >= 15
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {result.fps >= 30 ? '优秀' : result.fps >= 15 ? '良好' : '需优化'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* 性能对比图表 */}
            <div className="mt-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">性能对比分析</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 渲染时间对比 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-md font-medium text-gray-700 mb-3">渲染时间对比</h4>
                  <div className="space-y-2">
                    {testSizes.map(size => {
                      const lwResult = results.find(r => r.chartLibrary === 'Lightweight Charts' && r.dataPoints === size)
                      const chartjsResult = results.find(r => r.chartLibrary === 'Chart.js' && r.dataPoints === size)

                      return (
                        <div key={size} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">{size} 点:</span>
                          <div className="flex items-center space-x-4">
                            {lwResult && (
                              <span className="text-sm text-blue-600">
                                LW: {formatRenderTime(lwResult.renderTime)}
                              </span>
                            )}
                            {chartjsResult && lwResult && (
                              <span className="text-sm text-green-600 font-medium">
                                {getPerformanceImprovement(lwResult.renderTime, chartjsResult.renderTime).toFixed(1)}x
                              </span>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* 性能评估 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-md font-medium text-gray-700 mb-3">性能评估</h4>
                  <div className="space-y-2">
                    {testSizes.map(size => {
                      const lwResult = results.find(r => r.chartLibrary === 'Lightweight Charts' && r.dataPoints === size)

                      if (!lwResult) return null

                      const performance = lwResult.fps >= 30 ? 'excellent' : lwResult.fps >= 15 ? 'good' : 'poor'
                      const colors = {
                        excellent: 'text-green-600',
                        good: 'text-yellow-600',
                        poor: 'text-red-600'
                      }
                      const labels = {
                        excellent: '优秀',
                        good: '良好',
                        poor: '需优化'
                      }

                      return (
                        <div key={size} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">{size} 点:</span>
                          <span className={`text-sm font-medium ${colors[performance]}`}>
                            {labels[performance]}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 隐藏的测试容器 */}
        <div
          ref={chartRef}
          className="hidden"
          style={{ width: '800px', height: '400px' }}
        />
      </div>
    </div>
  )
}

export default PerformanceBenchmark