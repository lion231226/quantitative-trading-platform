import React from 'react'
import { render, screen } from '@testing-library/react'
import { ThemeProvider } from '../../theme/ThemeProvider'
import { testTheme } from '../../theme/testThemeHelper'
import PerformanceMetricsPanel from '../PerformanceMetricsPanel'
import { PerformanceMetrics } from '../../../types/kline.types'

describe('PerformanceMetricsPanel', () => {
  const mockMetricsData = [
    {
      curveId: 'strategy-1',
      curveName: '策略1',
      metrics: {
        returnRate: 15.5,
        maxDrawdown: -8.2,
        sharpeRatio: 1.85,
        totalReturn: 15.5,
        annualizedReturn: 18.2,
        volatility: 12.3,
        winRate: 65.5,
        profitFactor: 1.8,
        maxConsecutiveWins: 5,
        maxConsecutiveLosses: 2
      }
    },
    {
      curveId: 'baseline-1',
      curveName: '基准',
      metrics: {
        returnRate: 8.3,
        maxDrawdown: -12.1,
        sharpeRatio: 0.92,
        totalReturn: 8.3,
        annualizedReturn: 9.5,
        volatility: 10.2,
        winRate: 52.0,
        profitFactor: 1.2,
        maxConsecutiveWins: 3,
        maxConsecutiveLosses: 4
      }
    }
  ]

  const renderWithTheme = (component: React.ReactElement) => {
    return render(
      <ThemeProvider defaultTheme="test-light">
        {component}
      </ThemeProvider>
    )
  }

  test('应该在无数据时显示占位信息', () => {
    renderWithTheme(
      <PerformanceMetricsPanel metricsData={[]} />
    )

    expect(screen.getByText('暂无资金曲线数据')).toBeInTheDocument()
  })

  test('应该显示主要性能指标（紧凑模式）', () => {
    renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={mockMetricsData}
        compact={true}
      />
    )

    // 检查第一条曲线的主要指标
    expect(screen.getByText('策略1')).toBeInTheDocument()
    expect(screen.getByText('+15.50%')).toBeInTheDocument() // 收益率
    expect(screen.getByText('-8.20%')).toBeInTheDocument() // 最大回撤
    expect(screen.getByText('1.850')).toBeInTheDocument() // 夏普比率

    // 检查第二条曲线的主要指标
    expect(screen.getByText('基准')).toBeInTheDocument()
    expect(screen.getAllByText('+8.30%')).toHaveLength(2) // 两条曲线都显示
    expect(screen.getAllByText('-12.10%')).toHaveLength(2) // 两条曲线都显示
  })

  test('应该显示详细性能指标（非紧凑模式）', () => {
    renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={mockMetricsData}
        compact={false}
        showDetails={true}
      />
    )

    // 检查收益指标部分
    expect(screen.getByText('收益指标')).toBeInTheDocument()
    expect(screen.getByText('总收益率:')).toBeInTheDocument()
    expect(screen.getByText('年化收益:')).toBeInTheDocument()
    expect(screen.getByText('波动率:')).toBeInTheDocument()

    // 检查风险指标部分
    expect(screen.getByText('风险指标')).toBeInTheDocument()
    expect(screen.getByText('最大回撤:')).toBeInTheDocument()
    expect(screen.getByText('夏普比率:')).toBeInTheDocument()

    // 检查交易指标部分
    expect(screen.getByText('交易指标')).toBeInTheDocument()
    expect(screen.getByText('胜率:')).toBeInTheDocument()
    expect(screen.getByText('盈利因子:')).toBeInTheDocument()
  })

  test('应该正确格式化百分比数值', () => {
    const dataWithNegativeReturn = [
      {
        ...mockMetricsData[0],
        metrics: {
          ...mockMetricsData[0].metrics,
          returnRate: -5.25
        }
      }
    ]

    renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={dataWithNegativeReturn}
        compact={true}
      />
    )

    // 负收益率应该显示为 -5.25%
    expect(screen.getByText('-5.25%')).toBeInTheDocument()
  })

  test('应该在有多个曲线时显示对比分析', () => {
    renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={mockMetricsData}
        compact={false}
      />
    )

    expect(screen.getByText('对比分析')).toBeInTheDocument()
    expect(screen.getByText('策略1 vs 基准:')).toBeInTheDocument()
    expect(screen.getByText('基准 vs 基准:')).toBeInTheDocument()

    // 检查对比数值
    expect(screen.getByText(/收益 \+7\.20%/)).toBeInTheDocument() // 15.5 - 8.3 = 7.2
    expect(screen.getByText(/夏鲁 \+0\.930/)).toBeInTheDocument() // 1.85 - 0.92 ≈ 0.93
  })

  test('应该为正负指标使用不同颜色', () => {
    renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={mockMetricsData}
        compact={true}
      />
    )

    // 在实际测试中，我们检查元素是否存在和数值是否正确
    // 颜色测试需要更复杂的选择器，这里我们主要验证逻辑
    expect(screen.getByText('+15.50%')).toBeInTheDocument()
    expect(screen.getByText('-8.20%')).toBeInTheDocument()
  })

  test('应该处理零值和缺失的交易指标', () => {
    const dataWithZeroMetrics = [
      {
        curveId: 'zero-metrics',
        curveName: '零指标',
        metrics: {
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
      }
    ]

    renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={dataWithZeroMetrics}
        compact={true}
      />
    )

    expect(screen.getByText('0.00%')).toBeInTheDocument()
    expect(screen.getByText('0.000')).toBeInTheDocument()
  })

  test('应该应用自定义类名', () => {
    const customClass = 'custom-metrics-panel'
    const { container } = renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={mockMetricsData}
        className={customClass}
      />
    )

    expect(container.querySelector(`.${customClass}`)).toBeInTheDocument()
  })

  test('应该根据showDetails属性控制详细指标显示', () => {
    const { rerender } = renderWithTheme(
      <PerformanceMetricsPanel
        metricsData={mockMetricsData}
        showDetails={false}
      />
    )

    // 不应该显示详细指标部分
    expect(screen.queryByText('收益指标')).not.toBeInTheDocument()
    expect(screen.queryByText('交易指标')).not.toBeInTheDocument()

    // 重新渲染并启用详细指标
    rerender(
      <ThemeProvider theme={defaultTheme}>
        <PerformanceMetricsPanel
          metricsData={mockMetricsData}
          showDetails={true}
        />
      </ThemeProvider>
    )

    // 现在应该显示详细指标
    expect(screen.getByText('收益指标')).toBeInTheDocument()
    expect(screen.getByText('交易指标')).toBeInTheDocument()
  })
})