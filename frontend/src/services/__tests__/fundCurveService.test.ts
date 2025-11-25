import { fundCurveService } from '../fundCurveService'
import { TradingSignal } from '../../types/chart.types'

describe('FundCurveService', () => {
  const mockSignals: TradingSignal[] = [
    {
      id: 'signal-1',
      timestamp: 1609459200, // 2021-01-01
      price: 100,
      signalType: 'buy',
      strategyId: 'strategy-1',
      confidence: 0.8,
      volume: 1000
    },
    {
      id: 'signal-2',
      timestamp: 1609545600, // 2021-01-02
      price: 105,
      signalType: 'sell',
      strategyId: 'strategy-1',
      confidence: 0.7,
      volume: 1000
    },
    {
      id: 'signal-3',
      timestamp: 1609632000, // 2021-01-03
      price: 95,
      signalType: 'buy',
      strategyId: 'strategy-1',
      confidence: 0.9,
      volume: 1000
    },
    {
      id: 'signal-4',
      timestamp: 1609718400, // 2021-01-04
      price: 110,
      signalType: 'sell',
      strategyId: 'strategy-1',
      confidence: 0.6,
      volume: 1000
    }
  ]

  beforeEach(() => {
    fundCurveService.clearCache()
  })

  describe('calculateFundCurve', () => {
    test('应该根据交易信号正确计算资金曲线', () => {
      const initialCapital = 10000

      const result = fundCurveService.calculateFundCurve(
        mockSignals,
        initialCapital,
        1.0
      )

      expect(result).toHaveLength(mockSignals.length)

      // 第一个数据点（买入前）
      expect(result[0]).toEqual({
        timestamp: 1609459200,
        value: 10000
      })

      // 最后一个数据点应该是正收益
      expect(result[result.length - 1].value).toBeGreaterThan(initialCapital)
    })

    test('应该使用默认初始资金和仓位大小', () => {
      const signalsWithBuy: TradingSignal[] = [
        {
          id: 'buy-signal',
          timestamp: Date.now(),
          price: 100,
          signalType: 'buy',
          strategyId: 'test',
          confidence: 0.8,
          volume: 1000
        }
      ]

      const result = fundCurveService.calculateFundCurve(signalsWithBuy)

      expect(result[0].value).toBe(100000) // 默认初始资金
    })

    test('应该处理空的信号数组', () => {
      const result = fundCurveService.calculateFundCurve([])

      expect(result).toEqual([])
    })

    test('应该正确处理多笔交易', () => {
      const multiTradeSignals: TradingSignal[] = [
        { id: '1', timestamp: 1000, price: 100, signalType: 'buy', strategyId: 'test', confidence: 0.8, volume: 1000 },
        { id: '2', timestamp: 2000, price: 90, signalType: 'sell', strategyId: 'test', confidence: 0.8, volume: 1000 }, // 亏损交易
        { id: '3', timestamp: 3000, price: 100, signalType: 'buy', strategyId: 'test', confidence: 0.8, volume: 1000 },
        { id: '4', timestamp: 4000, price: 120, signalType: 'sell', strategyId: 'test', confidence: 0.8, volume: 1000 }, // 盈利交易
      ]

      const result = fundCurveService.calculateFundCurve(multiTradeSignals, 10000)

      // 应该有4个数据点对应4个信号
      expect(result).toHaveLength(4)

      // 最终结果应该有收益（最后一笔交易盈利更多）
      expect(result[3].value).toBeGreaterThan(10000)
    })

    test('应该按时间戳排序信号', () => {
      const unsortedSignals: TradingSignal[] = [
        { id: '3', timestamp: 3000, price: 100, signalType: 'sell', strategyId: 'test', confidence: 0.8, volume: 1000 },
        { id: '1', timestamp: 1000, price: 100, signalType: 'buy', strategyId: 'test', confidence: 0.8, volume: 1000 },
        { id: '2', timestamp: 2000, price: 90, signalType: 'buy', strategyId: 'test', confidence: 0.8, volume: 1000 },
      ]

      const result = fundCurveService.calculateFundCurve(unsortedSignals, 10000)

      // 应该按时间戳顺序处理
      expect(result[0].timestamp).toBe(1000)
      expect(result[1].timestamp).toBe(2000)
      expect(result[2].timestamp).toBe(3000)
    })
  })

  describe('calculateBuyAndHoldBaseline', () => {
    test('应该正确计算买入持有基准曲线', () => {
      const initialPrice = 100
      const initialCapital = 10000
      const prices = [
        { timestamp: 1000, price: 100 },
        { timestamp: 2000, price: 105 },
        { timestamp: 3000, price: 95 },
        { timestamp: 4000, price: 110 }
      ]

      const result = fundCurveService.calculateBuyAndHoldBaseline(
        initialPrice,
        prices,
        initialCapital
      )

      expect(result).toHaveLength(prices.length)

      // 检查股数计算（10000 / 100 = 100股）
      expect(result[0].value).toBe(10000)
      expect(result[1].value).toBe(10500) // 100 * 105
      expect(result[2].value).toBe(9500)  // 100 * 95
      expect(result[3].value).toBe(11000) // 100 * 110
    })

    test('应该处理空的价格数组', () => {
      const result = fundCurveService.calculateBuyAndHoldBaseline(100, [], 10000)

      expect(result).toEqual([])
    })
  })

  describe('calculateMetrics', () => {
    test('应该正确计算性能指标', () => {
      const dataPoints = [
        { timestamp: 1000, value: 100000 },
        { timestamp: 2000, value: 105000 },
        { timestamp: 3000, value: 95000 },
        { timestamp: 4000, value: 115000 }
      ]

      const metrics = fundCurveService.calculateMetrics(dataPoints)

      expect(metrics.returnRate).toBe(15) // (115000 - 100000) / 100000 * 100
      expect(metrics.totalReturn).toBe(15)
      expect(metrics.maxDrawdown).toBeGreaterThan(0) // 从105000降到95000的回撤
      expect(metrics.sharpeRatio).toBeDefined()
      expect(metrics.volatility).toBeGreaterThan(0)
      expect(metrics.annualizedReturn).toBeGreaterThan(0)
    })

    test('应该处理数据点不足的情况', () => {
      const singlePoint = [{ timestamp: 1000, value: 100000 }]

      const metrics = fundCurveService.calculateMetrics(singlePoint)

      // 所有指标应该是0或空值
      expect(metrics.returnRate).toBe(0)
      expect(metrics.maxDrawdown).toBe(0)
      expect(metrics.sharpeRatio).toBe(0)
      expect(metrics.totalReturn).toBe(0)
      expect(metrics.annualizedReturn).toBe(0)
      expect(metrics.volatility).toBe(0)
    })

    test('应该正确计算最大回撤', () => {
      const dataPoints = [
        { timestamp: 1000, value: 100000 },
        { timestamp: 2000, value: 120000 }, // 高点
        { timestamp: 3000, value: 90000 },  // 最大回撤点
        { timestamp: 4000, value: 110000 }
      ]

      const metrics = fundCurveService.calculateMetrics(dataPoints)

      // 最大回撤：(120000 - 90000) / 120000 = 25%
      expect(metrics.maxDrawdown).toBeCloseTo(25, 1)
    })
  })

  describe('calculateRelativeMetrics', () => {
    test('应该正确计算相对性能指标', () => {
      const strategyMetrics = {
        returnRate: 15,
        maxDrawdown: 8,
        sharpeRatio: 1.5,
        totalReturn: 15,
        annualizedReturn: 18,
        volatility: 12,
        winRate: 60,
        profitFactor: 1.8,
        maxConsecutiveWins: 5,
        maxConsecutiveLosses: 2
      }

      const baselineMetrics = {
        returnRate: 10,
        maxDrawdown: 12,
        sharpeRatio: 1.0,
        totalReturn: 10,
        annualizedReturn: 12,
        volatility: 10,
        winRate: 55,
        profitFactor: 1.5,
        maxConsecutiveWins: 3,
        maxConsecutiveLosses: 3
      }

      const relative = fundCurveService.calculateRelativeMetrics(
        strategyMetrics,
        baselineMetrics
      )

      expect(relative.alpha).toBe(5) // 15 - 10
      expect(relative.beta).toBe(1.2) // 12 / 10
      expect(relative.informationRatio).toBeGreaterThan(0)
      expect(relative.trackingError).toBe(2) // |12 - 10|
    })
  })

  describe('缓存功能', () => {
    test('应该正确缓存和获取资金曲线数据', () => {
      const fundCurve = {
        id: 'test-curve',
        name: '测试曲线',
        curveType: 'strategy' as const,
        color: '#10B981',
        visible: true,
        data: [{ timestamp: 1000, value: 100000 }]
      }

      const key = 'test-key'

      fundCurveService.cacheFundCurve(key, fundCurve)

      const cached = fundCurveService.getCachedFundCurve(key)

      expect(cached).toEqual(fundCurve)
    })

    test('应该在缓存不存在时返回null', () => {
      const cached = fundCurveService.getCachedFundCurve('non-existent-key')

      expect(cached).toBeNull()
    })

    test('应该生成正确的缓存键', () => {
      const key = fundCurveService.generateCacheKey(mockSignals, 10000, 1.0)

      expect(key).toBeDefined()
      expect(typeof key).toBe('string')
      expect(key.length).toBeGreaterThan(10) // 至少应该有一定长度

      // 相同的信号和参数应该生成相同的键
      const key2 = fundCurveService.generateCacheKey(mockSignals, 10000, 1.0)
      expect(key).toBe(key2)

      // 不同的参数应该生成不同的键
      const key3 = fundCurveService.generateCacheKey(mockSignals, 20000, 1.0)
      expect(key).not.toBe(key3)
    })
  })

  describe('createFundCurveData', () => {
    test('应该创建标准化的资金曲线数据', () => {
      const dataPoints = [
        { timestamp: 1000, value: 100000 },
        { timestamp: 2000, value: 105000 }
      ]

      const result = fundCurveService.createFundCurveData(
        'test-id',
        '测试曲线',
        dataPoints,
        '#10B981',
        'strategy'
      )

      expect(result).toEqual({
        id: 'test-id',
        name: '测试曲线',
        data: dataPoints,
        color: '#10B981',
        curveType: 'strategy',
        visible: true,
        lineWidth: 2,
        lineType: 'solid'
      })
    })

    test('应该为基线类型设置默认样式', () => {
      const dataPoints = [{ timestamp: 1000, value: 100000 }]

      const result = fundCurveService.createFundCurveData(
        'baseline-id',
        '基准曲线',
        dataPoints,
        '#6B7280',
        'baseline'
      )

      expect(result.lineWidth).toBe(1)
      expect(result.lineType).toBe('dashed')
    })
  })

  describe('alignDataPoints', () => {
    test('应该正确对齐多个资金曲线的数据点', () => {
      const curves = [
        {
          id: 'curve-1',
          name: '曲线1',
          curveType: 'strategy' as const,
          color: '#10B981',
          visible: true,
          data: [
            { timestamp: 1000, value: 100000 },
            { timestamp: 3000, value: 110000 }
          ]
        },
        {
          id: 'curve-2',
          name: '曲线2',
          curveType: 'baseline' as const,
          color: '#6B7280',
          visible: true,
          data: [
            { timestamp: 2000, value: 105000 },
            { timestamp: 3000, value: 108000 }
          ]
        }
      ]

      const result = fundCurveService.alignDataPoints(curves)

      expect(result).toHaveLength(3) // 三个时间戳：1000, 2000, 3000

      // 验证时间戳排序
      expect(result[0].timestamp).toBe(1000)
      expect(result[1].timestamp).toBe(2000)
      expect(result[2].timestamp).toBe(3000)

      // 验证数据对齐
      expect(result[0].values).toEqual({
        'curve-1': 100000
      })

      expect(result[1].values).toEqual({
        'curve-2': 105000
      })

      expect(result[2].values).toEqual({
        'curve-1': 110000,
        'curve-2': 108000
      })
    })

    test('应该处理空曲线数组', () => {
      const result = fundCurveService.alignDataPoints([])

      expect(result).toEqual([])
    })
  })
})