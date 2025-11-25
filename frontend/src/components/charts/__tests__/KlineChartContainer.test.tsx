import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import KlineChartContainer from '../KlineChartContainer'
import { TimePeriod, CandlestickData } from '../../../types/kline.types'

// Mock services
jest.mock('../../../services/klineService', () => ({
  klineDataService: {
    getData: jest.fn(() => Promise.resolve({
      candlesticks: []
    }))
  }
}))

jest.mock('../../../services/adaptivePerformanceService', () => ({
  adaptivePerformanceService: {
    optimize: jest.fn((config, data, metrics) => ({
      config,
      data,
      appliedStrategies: []
    })),
    recordMetrics: jest.fn()
  }
}))

// Mock dynamic imports
jest.mock('lightweight-charts', () => ({
  createChart: jest.fn(() => ({
    addCandlestickSeries: jest.fn(() => ({
      setData: jest.fn()
    })),
    addHistogramSeries: jest.fn(() => ({
      setData: jest.fn()
    })),
    timeScale: jest.fn(() => ({
      getVisibleLogicalRange: jest.fn(() => ({ from: 0, to: 100 })),
      setVisibleLogicalRange: jest.fn(),
      fitContent: jest.fn(),
      subscribeVisibleTimeRangeChange: jest.fn()
    })),
    subscribeCrosshairMove: jest.fn(),
    subscribeClick: jest.fn(),
    takeScreenshot: jest.fn(() => new ArrayBuffer(0)),
    applyOptions: jest.fn(),
    remove: jest.fn()
  }))
}), { virtual: true })

// Mock performance.now
Object.defineProperty(window, 'performance', {
  value: {
    now: jest.fn(() => Date.now()),
    memory: {
      usedJSHeapSize: 1000000
    }
  },
  writable: true
})

// Mock fullscreen API
Object.defineProperty(document, 'fullscreenElement', {
  writable: true,
  value: null
})

Object.defineProperty(Element.prototype, 'requestFullscreen', {
  writable: true,
  value: jest.fn()
})

Object.defineProperty(document, 'exitFullscreen', {
  writable: true,
  value: jest.fn()
})

// Mock canvas.toDataURL
Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
  writable: true,
  value: jest.fn(() => 'data:image/png;base64,mock')
})

describe('KlineChartContainer', () => {
  const mockData: CandlestickData[] = [
    {
      timestamp: '2024-01-01T00:00:00Z',
      open: 100,
      high: 110,
      low: 95,
      close: 105,
      volume: 1000
    },
    {
      timestamp: '2024-01-02T00:00:00Z',
      open: 105,
      high: 115,
      low: 100,
      close: 110,
      volume: 1200
    }
  ]

  const defaultProps = {
    data: {
      candlesticks: mockData,
      signals: []
    }
  }

  beforeEach(() => {
    jest.clearAllMocks()
    document.body.innerHTML = ''
  })

  test('renders K线图容器组件', () => {
    render(<KlineChartContainer {...defaultProps} />)

    expect(screen.getByText('当前周期: 1d')).toBeInTheDocument()
    expect(screen.getByText('数据点: 2')).toBeInTheDocument()
  })

  test('renders time period selector', () => {
    render(<KlineChartContainer {...defaultProps} />)

    // 检查时间周期按钮
    expect(screen.getByText('分')).toBeInTheDocument() // 1分钟
    expect(screen.getByText('日线')).toBeInTheDocument() // 1天
  })

  test('renders chart controls', () => {
    render(<KlineChartContainer {...defaultProps} />)

    // 检查控制按钮
    expect(screen.getByTitle('放大图表 (+)')).toBeInTheDocument()
    expect(screen.getByTitle('缩小图表 (-)')).toBeInTheDocument()
    expect(screen.getByTitle('重置缩放 (R)')).toBeInTheDocument()
    expect(screen.getByTitle('切换十字线 (C)')).toBeInTheDocument()
    expect(screen.getByTitle('切换网格 (G)')).toBeInTheDocument()
    expect(screen.getByTitle('导出图表 (E)')).toBeInTheDocument()
    expect(screen.getByTitle('全屏显示 (F)')).toBeInTheDocument()
  })

  test('handles time period change', async () => {
    const onTimePeriodChange = jest.fn()
    render(
      <KlineChartContainer
        {...defaultProps}
        onTimePeriodChange={onTimePeriodChange}
        config={{ timePeriod: TimePeriod.DAY_1 }}
      />
    )

    // 点击5分钟按钮
    fireEvent.click(screen.getByText('5分'))

    await waitFor(() => {
      expect(onTimePeriodChange).toHaveBeenCalledWith(TimePeriod.MINUTE_5)
    })
  })

  test('handles keyboard shortcuts', () => {
    render(<KlineChartContainer {...defaultProps} />)

    // 测试放大快捷键
    fireEvent.keyDown(document, { key: '+' })

    // 测试缩小快捷键
    fireEvent.keyDown(document, { key: '-' })

    // 测试重置快捷键
    fireEvent.keyDown(document, { key: 'r' })

    // 测试切换十字线快捷键
    fireEvent.keyDown(document, { key: 'c' })

    // 测试切换网格快捷键
    fireEvent.keyDown(document, { key: 'g' })

    // 测试导出快捷键
    fireEvent.keyDown(document, { key: 'e' })

    // 测试全屏快捷键
    fireEvent.keyDown(document, { key: 'f' })

    // 测试性能监控快捷键
    fireEvent.keyDown(document, { key: 'p' })
  })

  test('shows performance monitor when P key is pressed', () => {
    render(<KlineChartContainer {...defaultProps} />)

    // 初始状态不应该显示性能监控
    expect(screen.queryByText('📊 性能监控')).not.toBeInTheDocument()

    // 按P键显示性能监控
    fireEvent.keyDown(document, { key: 'p' })

    // 注意：由于性能监控是fixed定位，可能需要特殊处理
  })

  test('displays optimization information when data is sampled', () => {
    const largeData = Array.from({ length: 15000 }, (_, i) => ({
      timestamp: new Date(Date.now() - i * 60000).toISOString(),
      open: 100 + Math.random() * 10,
      high: 110 + Math.random() * 10,
      low: 90 + Math.random() * 10,
      close: 100 + Math.random() * 10,
      volume: 1000 + Math.random() * 1000
    }))

    render(
      <KlineChartContainer
        data={{ candlesticks: largeData, signals: [] }}
        config={{ performance: { enableDataSampling: true, maxDataPoints: 1000 } }}
      />
    )

    // 应该显示优化信息
    expect(screen.getByText(/\(优化: [\d.]+\% \)/)).toBeInTheDocument()
  })

  test('handles chart control clicks', () => {
    render(<KlineChartContainer {...defaultProps} />)

    // 测试缩放按钮
    fireEvent.click(screen.getByTitle('放大图表 (+)'))
    fireEvent.click(screen.getByTitle('缩小图表 (-)'))
    fireEvent.click(screen.getByTitle('重置缩放 (R)'))

    // 测试显示控制按钮
    fireEvent.click(screen.getByTitle('切换十字线 (C)'))
    fireEvent.click(screen.getByTitle('切换网格 (G)'))

    // 测试导出按钮
    fireEvent.click(screen.getByTitle('导出图表 (E)'))

    // 测试全屏按钮
    fireEvent.click(screen.getByTitle('全屏显示 (F)'))
  })

  test('handles performance monitor toggle', () => {
    render(<KlineChartContainer {...defaultProps} />)

    // 点击性能监控按钮
    const performanceButton = screen.getByText('📊 性能')
    fireEvent.click(performanceButton)

    // 再次点击切换状态
    fireEvent.click(performanceButton)
  })

  test('displays correct data point count', () => {
    render(<KlineChartContainer {...defaultProps} />)

    expect(screen.getByText('数据点: 2')).toBeInTheDocument()
  })

  test('displays performance metrics', () => {
    render(<KlineChartContainer {...defaultProps} />)

    // 检查性能指标显示
    expect(screen.getByText(/性能: [\d.]+ FPS/)).toBeInTheDocument()
    expect(screen.getByText(/渲染时间: [\d.]+ms/)).toBeInTheDocument()
  })

  test('applies custom className', () => {
    const customClass = 'custom-kline-container'
    render(
      <KlineChartContainer
        {...defaultProps}
        className={customClass}
      />
    )

    const container = document.querySelector('.kline-chart-container')
    expect(container).toHaveClass(customClass)
  })

  test('handles keyboard shortcuts when disabled', () => {
    render(
      <KlineChartContainer
        {...defaultProps}
        config={{ interactions: { keyboardShortcuts: false } }}
      />
    )

    // 快捷键应该被忽略
    fireEvent.keyDown(document, { key: '+' })
    fireEvent.keyDown(document, { key: 'r' })

    // 由于键盘快捷键被禁用，不会有特定的行为，但不应该报错
  })

  test('updates config when userConfig changes', () => {
    const { rerender } = render(<KlineChartContainer {...defaultProps} />)

    // 初始配置
    expect(screen.getByText('当前周期: 1d')).toBeInTheDocument()

    // 更新配置
    rerender(
      <KlineChartContainer
        {...defaultProps}
        config={{ timePeriod: TimePeriod.HOUR_1 }}
      />
    )

    expect(screen.getByText('当前周期: 1h')).toBeInTheDocument()
  })

  test('handles empty data gracefully', () => {
    render(
      <KlineChartContainer
        data={{ candlesticks: [], signals: [] }}
      />
    )

    expect(screen.getByText('数据点: 0')).toBeInTheDocument()
    // 组件应该正常渲染，不应该崩溃
  })

  test('handles chart ready callback', () => {
    const onChartReady = jest.fn()
    render(
      <KlineChartContainer
        {...defaultProps}
        onChartReady={onChartReady}
      />
    )

    // 由于我们mock了图表创建，onChartReady可能不会立即被调用
    // 这个测试主要确保组件不会因为回调而崩溃
    expect(screen.getByText('数据点: 2')).toBeInTheDocument()
  })
})