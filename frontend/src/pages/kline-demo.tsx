import React, { useState, useEffect } from 'react'
import { KlineChartContainer } from '../components/charts/KlineChartContainer'
import { TimePeriod, CandlestickData } from '../types/kline.types'
import { createTimePeriodDataManager } from '../services/timePeriodDataManager'

// 生成模拟数据
const generateMockData = (count: number): CandlestickData[] => {
  const data: CandlestickData[] = []
  const now = new Date()
  let lastClose = 100

  for (let i = count - 1; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)

    const change = (Math.random() - 0.5) * 10
    const open = lastClose + change
    const close = open + (Math.random() - 0.5) * 5
    const high = Math.max(open, close) + Math.random() * 3
    const low = Math.min(open, close) - Math.random() * 3
    const volume = Math.floor(Math.random() * 1000000)

    data.push({
      timestamp: timestamp.toISOString(),
      open: Math.max(1, open),
      high: Math.max(1, high),
      low: Math.max(1, low),
      close: Math.max(1, close),
      volume
    })

    lastClose = close
  }

  return data
}

export default function KlineDemo() {
  const [data, setData] = useState(() => ({
    candlesticks: generateMockData(500),
    signals: []
  }))

  const [currentPeriod, setCurrentPeriod] = useState<TimePeriod>(TimePeriod.DAY_1)
  const [isLoading, setIsLoading] = useState(false)

  // 模拟时间周期切换
  const handleTimePeriodChange = async (period: TimePeriod) => {
    setIsLoading(true)
    setCurrentPeriod(period)

    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 500))

    // 根据时间周期生成不同数量的数据
    let dataCount = 500
    switch (period) {
      case TimePeriod.MINUTE_1:
        dataCount = 1440 // 1天
        break
      case TimePeriod.MINUTE_5:
        dataCount = 288 // 1天
        break
      case TimePeriod.MINUTE_15:
        dataCount = 96 // 1天
        break
      case TimePeriod.MINUTE_30:
        dataCount = 48 // 1天
        break
      case TimePeriod.HOUR_1:
        dataCount = 168 // 1周
        break
      case TimePeriod.HOUR_4:
        dataCount = 42 // 1周
        break
      case TimePeriod.DAY_1:
        dataCount = 365 // 1年
        break
      case TimePeriod.DAY_7:
        dataCount = 52 // 1年
        break
      case TimePeriod.MONTH_1:
        dataCount = 24 // 2年
        break
    }

    setData({
      candlesticks: generateMockData(dataCount),
      signals: []
    })

    setIsLoading(false)
  }

  // 处理K线点击事件
  const handleCandlestickClick = (signal: any) => {
    console.log('K线点击:', signal)
  }

  // 处理数据点悬停事件
  const handleDataPointHover = (data: any) => {
    if (data) {
      console.log('悬停数据:', data)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          高性能K线图表演示
        </h1>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              功能特性
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                Lightweight Charts 5.0+ 高性能渲染
              </div>
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                专业K线图显示 (OHLC)
              </div>
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                多时间周期切换
              </div>
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                交互式图表控制
              </div>
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                键盘快捷键支持
              </div>
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                性能监控和优化
              </div>
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                大数据集智能采样
              </div>
              <div className="flex items-center">
                <span className="text-green-500 mr-2">✓</span>
                响应式设计
              </div>
            </div>
          </div>

          <div className="mb-4">
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              快捷键说明
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <h3 className="font-medium text-gray-700 mb-1">缩放控制</h3>
                <ul className="space-y-1 text-gray-600">
                  <li><kbd className="px-2 py-1 bg-gray-100 rounded text-xs">+/-</kbd> 放大/缩小</li>
                  <li><kbd className="px-2 py-1 bg-gray-100 rounded text-xs">R</kbd> 重置缩放</li>
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-700 mb-1">时间周期</h3>
                <ul className="space-y-1 text-gray-600">
                  <li><kbd className="px-2 py-1 bg-gray-100 rounded text-xs">K</kbd> 下一个周期</li>
                  <li><kbd className="px-2 py-1 bg-gray-100 rounded text-xs">Shift+K</kbd> 上一个周期</li>
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-700 mb-1">显示控制</h3>
                <ul className="space-y-1 text-gray-600">
                  <li><kbd className="px-2 py-1 bg-gray-100 rounded text-xs">C</kbd> 十字线</li>
                  <li><kbd className="px-2 py-1 bg-gray-100 rounded text-xs">G</kbd> 网格</li>
                  <li><kbd className="px-2 py-1 bg-gray-100 rounded text-xs">P</kbd> 性能监控</li>
                </ul>
              </div>
            </div>
          </div>

          {/* 当前状态显示 */}
          <div className="mb-4 p-4 bg-blue-50 rounded-lg">
            <div className="flex justify-between items-center">
              <div>
                <span className="text-sm font-medium text-blue-800">当前时间周期:</span>
                <span className="ml-2 text-blue-600 font-bold">{currentPeriod}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-blue-800">数据点数:</span>
                <span className="ml-2 text-blue-600 font-bold">
                  {data.candlesticks.length.toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-sm font-medium text-blue-800">状态:</span>
                <span className="ml-2 text-blue-600 font-bold">
                  {isLoading ? '加载中...' : '就绪'}
                </span>
              </div>
            </div>
          </div>

          {/* K线图容器 */}
          <KlineChartContainer
            data={data}
            onSignalClick={handleCandlestickClick}
            onTimePeriodChange={handleTimePeriodChange}
            onDataPointHover={handleDataPointHover}
            config={{
              timePeriod: currentPeriod,
              height: 500,
              showVolume: true,
              showCrosshair: false,
              showGrid: true,
              performance: {
                enableDataSampling: true,
                maxDataPoints: 1000,
                enableAnimation: true,
                animationDuration: 300
              },
              interactions: {
                enableZoom: true,
                enablePan: true,
                wheelSensitivity: 1,
                keyboardShortcuts: true
              }
            }}
          />

          {/* 使用说明 */}
          <div className="mt-8 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">使用说明</h3>
            <div className="space-y-2 text-sm text-gray-600">
              <p>• 使用鼠标滚轮或 +/- 键进行缩放</p>
              <p>• 拖拽图表进行平移查看更多数据</p>
              <p>• 点击时间周期按钮切换不同的时间粒度</p>
              <p>• 按快捷键 P 显示/隐藏性能监控面板</p>
              <p>• 点击导出按钮保存图表为图片</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}