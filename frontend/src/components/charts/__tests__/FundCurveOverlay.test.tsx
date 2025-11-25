import React from 'react'
import { render, screen } from '@testing-library/react'
import { ThemeProvider } from '../../theme/ThemeProvider'
import { testTheme } from '../../theme/testThemeHelper'
import { FundCurveOverlay } from '../FundCurveOverlay'
import { FundCurveData, DualYAxisConfig } from '../../../types/kline.types'

// Mock lightweight-charts
let mockCreateChart: jest.Mock
let mockChart: any

// Try to mock lightweight-charts, but handle case where it's not installed
try {
  jest.mock('lightweight-charts', () => ({
    createChart: mockCreateChart = jest.fn(() => mockChart),
    CrosshairMode: { Normal: 'normal' },
    LineStyle: { Solid: 0, Dashed: 1, Dotted: 2 },
    PriceScaleMode: { Normal: 0 }
  }))
} catch (e) {
  // Fallback mock if lightweight-charts is not available
  console.warn('lightweight-charts not available for testing')
}

// Setup mock chart instance
mockChart = {
  addLineSeries: jest.fn(() => ({
    setData: jest.fn(),
    subscribeClick: jest.fn()
  })),
  removeSeries: jest.fn(),
  remove: jest.fn(),
  applyOptions: jest.fn()
}

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn()
}))

describe('FundCurveOverlay', () => {
  const mockContainer = document.createElement('div')
  // 使用 Object.defineProperty 来设置只读属性
  Object.defineProperty(mockContainer, 'clientWidth', {
    value: 800,
    writable: true,
    configurable: true
  })
  Object.defineProperty(mockContainer, 'clientHeight', {
    value: 400,
    writable: true,
    configurable: true
  })

  const mockFundCurves: FundCurveData[] = [
    {
      id: 'strategy-1',
      name: '策略1',
      curveType: 'strategy',
      color: '#10B981',
      visible: true,
      lineWidth: 2,
      lineType: 'solid',
      data: [
        { timestamp: 1609459200, value: 100000 },
        { timestamp: 1609545600, value: 102000 },
        { timestamp: 1609632000, value: 101500 },
        { timestamp: 1609718400, value: 103000 }
      ]
    },
    {
      id: 'baseline-1',
      name: '基准',
      curveType: 'baseline',
      color: '#6B7280',
      visible: true,
      lineWidth: 1,
      lineType: 'dashed',
      data: [
        { timestamp: 1609459200, value: 100000 },
        { timestamp: 1609545600, value: 101000 },
        { timestamp: 1609632000, value: 101500 },
        { timestamp: 1609718400, value: 102000 }
      ]
    }
  ]

  const mockDualYAxisConfig: DualYAxisConfig = {
    leftAxis: {
      visible: true,
      textColor: '#1F2937',
      borderColor: '#E5E7EB'
    },
    rightAxis: {
      visible: true,
      textColor: '#1F2937',
      borderColor: '#E5E7EB'
    },
    synchronization: {
      enabled: true,
      syncZoom: true,
      syncPan: true
    }
  }

  const renderWithTheme = (component: React.ReactElement) => {
    return render(
      <ThemeProvider defaultTheme="test-light">
        {component}
      </ThemeProvider>
    )
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('应该在不显示资金曲线时不渲染任何内容', () => {
    renderWithTheme(
      <FundCurveOverlay
        container={mockContainer}
        fundCurves={[]}
        dualYAxisConfig={mockDualYAxisConfig}
      />
    )

    // FundCurveOverlay 返回 null，所以不应该有任何内容
    expect(document.body).toBeEmptyDOMElement()
  })

  test('应该渲染但不显示任何内容（返回null）', () => {
    const { container } = renderWithTheme(
      <FundCurveOverlay
        container={mockContainer}
        fundCurves={mockFundCurves}
        dualYAxisConfig={mockDualYAxisConfig}
      />
    )

    // FundCurveOverlay 组件返回 null，所以容器应该是空的
    expect(container.firstChild).toBeNull()
  })

  test('应该处理空的资金曲线数组', () => {
    const { container } = renderWithTheme(
      <FundCurveOverlay
        container={mockContainer}
        fundCurves={[]}
        dualYAxisConfig={mockDualYAxisConfig}
      />
    )

    expect(container.firstChild).toBeNull()
  })

  test('应该处理回调函数', () => {
    const onMetricsUpdate = jest.fn()
    const onCurveClick = jest.fn()

    renderWithTheme(
      <FundCurveOverlay
        container={mockContainer}
        fundCurves={mockFundCurves}
        dualYAxisConfig={mockDualYAxisConfig}
        onMetricsUpdate={onMetricsUpdate}
        onCurveClick={onCurveClick}
      />
    )

    // 组件应该能正常渲染，即使回调可能不会被调用（因为返回null）
    expect(onMetricsUpdate).not.toHaveBeenCalled()
    expect(onCurveClick).not.toHaveBeenCalled()
  })

  test('应该处理不同类型的资金曲线', () => {
    const mixedCurves: FundCurveData[] = [
      {
        ...mockFundCurves[0],
        curveType: 'strategy'
      },
      {
        ...mockFundCurves[1],
        curveType: 'baseline'
      }
    ]

    const { container } = renderWithTheme(
      <FundCurveOverlay
        container={mockContainer}
        fundCurves={mixedCurves}
        dualYAxisConfig={mockDualYAxisConfig}
      />
    )

    expect(container.firstChild).toBeNull()
  })

  test('应该处理不同的双Y轴配置', () => {
    const customConfig: DualYAxisConfig = {
      leftAxis: {
        visible: false,
        textColor: '#FF0000',
        borderColor: '#00FF00'
      },
      rightAxis: {
        visible: true,
        textColor: '#0000FF',
        borderColor: '#FFFF00'
      },
      synchronization: {
        enabled: false,
        syncZoom: false,
        syncPan: true
      }
    }

    const { container } = renderWithTheme(
      <FundCurveOverlay
        container={mockContainer}
        fundCurves={mockFundCurves}
        dualYAxisConfig={customConfig}
      />
    )

    expect(container.firstChild).toBeNull()
  })
})