// 多品种对比分析相关类型定义

export interface VarietyComparisonRequest {
  symbols: string[]
  startDate: string
  endDate: string
  strategy: StrategyConfig
}

export interface VarietyComparisonResult {
  requestId: string
  timestamp: string
  request: VarietyComparisonRequest
  results: VarietyResult[]
  summary: ComparisonSummary
  rankings: VarietyRanking[]
}

export interface VarietyResult {
  symbol: string
  name: string
  sector: string
  exchange: string
  metrics: PerformanceMetrics
  trades: TradeRecord[]
  equity: EquityPoint[]
  signals: SignalPoint[]
  error?: string
}

export interface PerformanceMetrics {
  // 基础收益指标
  totalReturn: number          // 总收益率
  annualizedReturn: number     // 年化收益率
  cagr: number                // 复合年增长率

  // 风险指标
  maxDrawdown: number         // 最大回撤
  volatility: number          // 波动率
  downsideDeviation: number   // 下行标准差

  // 风险调整收益指标
  sharpeRatio: number         // 夏普比率
  sortinoRatio: number        // 索提诺比率
  calmarRatio: number         // 卡玛比率

  // 交易统计
  totalTrades: number         // 总交易次数
  winningTrades: number       // 盈利交易次数
  losingTrades: number        // 亏损交易次数
  winRate: number            // 胜率

  // 盈亏统计
  averageWin: number          // 平均盈利
  averageLoss: number         // 平均亏损
  profitFactor: number       // 盈亏比
  averageTrade: number       // 平均交易盈亏

  // 其他指标
  var95: number               // 95% VaR
  skewness: number           // 偏度
  kurtosis: number           // 峰度
  beta: number               // Beta系数（相对于基准）
  alpha: number              // Alpha系数
}

export interface TradeRecord {
  symbol: string
  date: string
  type: 'BUY' | 'SELL'
  price: number
  quantity: number
  amount: number
  commission: number
  pnl?: number
  equity?: number
}

export interface EquityPoint {
  symbol: string
  date: string
  equity: number
  drawdown: number
  returns: number
  benchmarkReturns?: number
}

export interface SignalPoint {
  symbol: string
  date: string
  signal: 'BUY' | 'SELL' | 'HOLD'
  price: number
  indicator: string
  confidence?: number
}

export interface ComparisonSummary {
  totalVarieties: number
  successfulVarieties: number
  failedVarieties: number
  bestPerformer: string
  worstPerformer: string
  averageReturn: number
  averageSharpeRatio: number
  totalTrades: number
  dateRange: {
    start: string
    end: string
    tradingDays: number
  }
  correlationMatrix?: CorrelationMatrix
}

export interface VarietyRanking {
  rank: number
  symbol: string
  name: string
  sector: string
  score: number
  metrics: {
    returnRank: number
    riskRank: number
    riskAdjustedReturnRank: number
    consistencyRank: number
  }
  highlights: string[]
}

export interface CorrelationMatrix {
  symbols: string[]
  matrix: number[][]
  averageCorrelation: number
  minCorrelation: number
  maxCorrelation: number
}

// 对比分析配置
export interface ComparisonConfig {
  maxVarieties: number
  defaultMetrics: (keyof PerformanceMetrics)[]
  benchmarkSymbol?: string
  riskFreeRate: number
  confidenceLevel: number
  enableStatisticalTests: boolean
  enableMonteCarlo: boolean
  simulationRuns?: number
}

// 组件Props类型
export interface VarietySelectorProps {
  onVarietiesSelect: (varieties: string[]) => void
  selectedVarieties?: string[]
  maxSelection?: number
  className?: string
}

export interface MultiVarietyComparisonProps {
  request?: VarietyComparisonRequest
  onConfigChange?: (config: VarietyComparisonRequest) => void
  className?: string
}

export interface ComparisonResultsProps {
  results?: VarietyComparisonResult
  loading?: boolean
  error?: string
  className?: string
}

export interface ComparisonTableProps {
  results: VarietyResult[]
  sortable?: boolean
  filterable?: boolean
  exportable?: boolean
  className?: string
}

// 服务接口
export interface ComparisonService {
  runComparison(request: VarietyComparisonRequest): Promise<VarietyComparisonResult>
  getComparisonResults(requestId: string): Promise<VarietyComparisonResult>
  cancelComparison(requestId: string): Promise<void>
  getAvailableMetrics(): Promise<string[]>
  getHistoricalComparison(symbols: string[], days: number): Promise<VarietyComparisonResult>
}

// 导出选项
export interface ExportOptions {
  format: 'pdf' | 'excel' | 'csv' | 'json'
  includeCharts: boolean
  includeDetails: boolean
  template?: string
  customFields?: string[]
}

export interface ShareOptions {
  generateLink: boolean
  embedCode: boolean
  password?: string
  expiryDate?: string
  allowDownload: boolean
}

// 错误类型
export interface ComparisonError {
  code: string
  message: string
  details?: any
  symbol?: string
  timestamp: string
}

// 统计检验结果
export interface StatisticalTest {
  testName: string
  nullHypothesis: string
  statistic: number
  pValue: number
  criticalValue: number
  significance: number
  conclusion: 'REJECT' | 'FAIL_TO_REJECT'
  interpretation: string
}

export interface StatisticalAnalysis {
  normalityTest: StatisticalTest
  correlationTest: StatisticalTest
  varianceHomogeneityTest: StatisticalTest
  meanDifferenceTests: {
    [pair: string]: StatisticalTest
  }
}