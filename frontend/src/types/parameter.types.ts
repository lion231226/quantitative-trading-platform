// 策略参数配置接口
export interface StrategyParameters {
  movingAveragePeriod: number
  stopLoss: number
  takeProfit: number
}

// 颜色配置接口
export interface ColorConfig {
  bg: string
  border: string
  text: string
  chart: string
}

// 参数组配置（用于对比分析）
export interface ParameterGroup {
  id: string
  name: string
  parameters: StrategyParameters
  color?: ColorConfig | string
  isActive?: boolean
  results?: StrategyResult
}

// 参数验证规则
export interface ParameterValidation {
  min: number
  max: number
  step?: number
  precision?: number
  required?: boolean
}

// 参数预设配置
export interface ParameterPreset {
  id: string
  name: string
  description: string
  parameters: StrategyParameters
  isCustom?: boolean
}

// 参数建议配置
export interface OptimizationSuggestion {
  id: string
  type: 'trend' | 'volatility' | 'risk' | 'performance'
  confidence: number // 0-100
  parameters: StrategyParameters
  reasoning: string
  expectedImprovement?: string
}

// 参数变更事件
export interface ParameterChangeEvent {
  parameter: keyof StrategyParameters
  value: number
  previousValue: number
  groupId?: string
}

// 参数配置验证结果
export interface ParameterValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
}

// 策略结果接口（扩展现有定义）
export interface StrategyResult {
  totalReturn: number
  sharpeRatio: number
  maxDrawdown: number
  winRate: number
  totalTrades: number
  profitFactor: number
  // 新增字段用于详细分析
  volatility?: number
  calmarRatio?: number
  sortinoRatio?: number
  averageTrade?: number
  expectancy?: number
}

// 用户偏好设置
export interface UserPreferences {
  defaultParameters: StrategyParameters
  favoritePresets: string[]
  autoSave: boolean
  showAdvanced: boolean
  chartPreferences: {
    showGrid: boolean
    showVolume: boolean
    animationDuration: number
  }
}

// 参数对比分析配置
export interface ComparisonConfig {
  showDifferences: boolean
  highlightChanges: boolean
  syncParameters: boolean
  maxGroups: number
}

// 参数服务配置
export interface ParameterServiceConfig {
  debounceDelay: number
  cacheTimeout: number
  maxConcurrentRequests: number
  retryAttempts: number
}
