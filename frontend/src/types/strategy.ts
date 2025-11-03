import { StrategyConfig, StrategyResult } from './api';

// 策略类型枚举
export type StrategyType = 'single_ma' | 'dual_ma' | 'rsi' | 'macd'

// 策略类型配置
export interface StrategyTypeConfig {
  id: StrategyType
  name: string
  description: string
  category: 'trend' | 'momentum' | 'volatility' | 'custom'
  status: 'available' | 'coming-soon' | 'experimental'
}

// 单均线策略参数
export interface SingleMovingAverageParams {
  // 基础参数
  ma_period: number
  ma_type: 'SMA' | 'EMA'
  initial_capital: number

  // 信号确认参数
  min_cross_percentage: number
  confirmation_periods: number

  // 风险管理参数
  stop_loss_pct: number
  take_profit_pct: number
  max_position_size: number

  // 信号过滤参数
  max_signals_per_day: number
  signal_cooldown: number
}

// 双均线策略参数（预留）
export interface DualMovingAverageParams {
  // 基础参数
  short_ma_period: number
  long_ma_period: number
  short_ma_type: 'SMA' | 'EMA'
  long_ma_type: 'SMA' | 'EMA'
  initial_capital: number

  // 信号确认参数
  min_cross_percentage: number
  confirmation_periods: number

  // 风险管理参数
  stop_loss_pct: number
  take_profit_pct: number
  max_position_size: number

  // 信号过滤参数
  max_signals_per_day: number
  signal_cooldown: number
}

// RSI策略参数（预留）
export interface RSIStrategyParams {
  // 基础参数
  rsi_period: number
  rsi_overbought: number
  rsi_oversold: number
  initial_capital: number

  // 信号确认参数
  confirmation_periods: number

  // 风险管理参数
  stop_loss_pct: number
  take_profit_pct: number
  max_position_size: number

  // 信号过滤参数
  max_signals_per_day: number
  signal_cooldown: number
}

// MACD策略参数（预留）
export interface MACDStrategyParams {
  // 基础参数
  macd_fast_period: number
  macd_slow_period: number
  macd_signal_period: number
  initial_capital: number

  // 信号确认参数
  confirmation_periods: number

  // 风险管理参数
  stop_loss_pct: number
  take_profit_pct: number
  max_position_size: number

  // 信号过滤参数
  max_signals_per_day: number
  signal_cooldown: number
}

// 联合策略参数类型
export type StrategyParams =
  | SingleMovingAverageParams
  | DualMovingAverageParams
  | RSIStrategyParams
  | MACDStrategyParams

// 向后兼容的别名
export interface MovingAverageStrategyParams extends SingleMovingAverageParams {}

// 策略配置元数据
export interface StrategyParameterMeta {
  type: 'number' | 'select' | 'boolean'
  default: any
  min?: number
  max?: number
  step?: number
  options?: Array<{ value: any; label: string }>
  description: string
  unit?: string
  category: 'basic' | 'signal' | 'risk' | 'filter'
}

// 策略运行状态
export interface StrategyRun {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  result?: StrategyResult
  error?: string
  created_at: string
  completed_at?: string
}

// 表单数据类型
export interface MarketSelectionForm {
  symbol: string
  startDate: string
  endDate: string
}

export interface StrategyConfigForm {
  strategyType: StrategyType
  params: StrategyParams
}

// 完整的策略提交表单
export interface StrategySubmissionForm extends MarketSelectionForm, StrategyConfigForm {}

// 图表数据类型
export interface ChartDataPoint {
  x: string
  y: number
}

export interface StrategyChartData {
  dates: string[]
  prices: number[]
  signals: number[]
  portfolio: number[]
}
