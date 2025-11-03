import { MovingAverageStrategyParams, StrategyParameterMeta } from '@/types/strategy'

// 策略参数默认值
export const DEFAULT_STRATEGY_PARAMS: MovingAverageStrategyParams = {
  // 基础参数
  ma_period: 20,
  ma_type: 'SMA',
  initial_capital: 100000,

  // 信号确认参数
  min_cross_percentage: 0.001,
  confirmation_periods: 1,

  // 风险管理参数
  stop_loss_pct: 0.02,
  take_profit_pct: 0.05,
  max_position_size: 1.0,

  // 信号过滤参数
  max_signals_per_day: 10,
  signal_cooldown: 300,
}

// 策略参数元数据配置
export const STRATEGY_PARAMETER_META: Record<keyof MovingAverageStrategyParams, StrategyParameterMeta> = {
  ma_period: {
    type: 'number',
    default: 20,
    min: 5,
    max: 200,
    step: 1,
    description: '移动平均线周期',
    unit: '天',
    category: 'basic'
  },
  ma_type: {
    type: 'select',
    default: 'SMA',
    options: [
      { value: 'SMA', label: '简单移动平均 (SMA)' },
      { value: 'EMA', label: '指数移动平均 (EMA)' }
    ],
    description: '移动平均线类型',
    category: 'basic'
  },
  initial_capital: {
    type: 'number',
    default: 100000,
    min: 1000,
    max: 10000000,
    step: 1000,
    description: '初始资金',
    unit: '元',
    category: 'basic'
  },
  min_cross_percentage: {
    type: 'number',
    default: 0.001,
    min: 0.0001,
    max: 0.01,
    step: 0.0001,
    description: '最小穿越百分比',
    unit: '比例',
    category: 'signal'
  },
  confirmation_periods: {
    type: 'number',
    default: 1,
    min: 1,
    max: 5,
    step: 1,
    description: '信号确认周期数',
    unit: '周期',
    category: 'signal'
  },
  stop_loss_pct: {
    type: 'number',
    default: 0.02,
    min: 0.005,
    max: 0.1,
    step: 0.005,
    description: '止损百分比',
    unit: '比例',
    category: 'risk'
  },
  take_profit_pct: {
    type: 'number',
    default: 0.05,
    min: 0.01,
    max: 0.2,
    step: 0.01,
    description: '止盈百分比',
    unit: '比例',
    category: 'risk'
  },
  max_position_size: {
    type: 'number',
    default: 1.0,
    min: 0.1,
    max: 1.0,
    step: 0.1,
    description: '最大仓位大小',
    unit: '比例',
    category: 'risk'
  },
  max_signals_per_day: {
    type: 'number',
    default: 10,
    min: 1,
    max: 50,
    step: 1,
    description: '每日最大信号数',
    unit: '个',
    category: 'filter'
  },
  signal_cooldown: {
    type: 'number',
    default: 300,
    min: 60,
    max: 3600,
    step: 60,
    description: '信号冷却时间',
    unit: '秒',
    category: 'filter'
  }
}

// 预设策略配置
export const STRATEGY_PRESETS = {
  conservative: {
    name: '保守策略',
    description: '较低风险，稳健收益',
    params: {
      ma_period: 50,
      ma_type: 'SMA' as const,
      initial_capital: 100000,
      min_cross_percentage: 0.002,
      confirmation_periods: 3,
      stop_loss_pct: 0.015,
      take_profit_pct: 0.03,
      max_position_size: 0.5,
      max_signals_per_day: 5,
      signal_cooldown: 600
    } as MovingAverageStrategyParams
  },
  balanced: {
    name: '平衡策略',
    description: '风险与收益平衡',
    params: {
      ma_period: 20,
      ma_type: 'SMA' as const,
      initial_capital: 100000,
      min_cross_percentage: 0.001,
      confirmation_periods: 2,
      stop_loss_pct: 0.02,
      take_profit_pct: 0.05,
      max_position_size: 0.8,
      max_signals_per_day: 10,
      signal_cooldown: 300
    } as MovingAverageStrategyParams
  },
  aggressive: {
    name: '激进策略',
    description: '较高风险，追求高收益',
    params: {
      ma_period: 10,
      ma_type: 'EMA' as const,
      initial_capital: 100000,
      min_cross_percentage: 0.0005,
      confirmation_periods: 1,
      stop_loss_pct: 0.025,
      take_profit_pct: 0.08,
      max_position_size: 1.0,
      max_signals_per_day: 20,
      signal_cooldown: 120
    } as MovingAverageStrategyParams
  }
}

// 参数验证函数
export const validateStrategyParams = (params: MovingAverageStrategyParams): { isValid: boolean; errors: string[] } => {
  const errors: string[] = []

  // 验证基础参数
  if (params.ma_period < 5 || params.ma_period > 200) {
    errors.push('移动平均线周期必须在5-200天之间')
  }

  if (params.initial_capital < 1000 || params.initial_capital > 10000000) {
    errors.push('初始资金必须在1,000-10,000,000元之间')
  }

  // 验证信号确认参数
  if (params.min_cross_percentage < 0.0001 || params.min_cross_percentage > 0.01) {
    errors.push('最小穿越百分比必须在0.01%-1%之间')
  }

  if (params.confirmation_periods < 1 || params.confirmation_periods > 5) {
    errors.push('信号确认周期数必须在1-5之间')
  }

  // 验证风险管理参数
  if (params.stop_loss_pct < 0.005 || params.stop_loss_pct > 0.1) {
    errors.push('止损百分比必须在0.5%-10%之间')
  }

  if (params.take_profit_pct < 0.01 || params.take_profit_pct > 0.2) {
    errors.push('止盈百分比必须在1%-20%之间')
  }

  if (params.max_position_size < 0.1 || params.max_position_size > 1.0) {
    errors.push('最大仓位大小必须在10%-100%之间')
  }

  // 验证信号过滤参数
  if (params.max_signals_per_day < 1 || params.max_signals_per_day > 50) {
    errors.push('每日最大信号数必须在1-50之间')
  }

  if (params.signal_cooldown < 60 || params.signal_cooldown > 3600) {
    errors.push('信号冷却时间必须在60-3600秒之间')
  }

  return {
    isValid: errors.length === 0,
    errors
  }
}

// 安全获取参数值
export const safeGetValue = (params: Partial<MovingAverageStrategyParams>, key: keyof MovingAverageStrategyParams, defaultValue: any): any => {
  return params[key] !== undefined ? params[key] : defaultValue
}

// 格式化参数值用于显示
export const formatParamValue = (key: keyof MovingAverageStrategyParams, value: number | string | undefined): string => {
  if (value === undefined || value === null) {
    return safeGetValue(DEFAULT_STRATEGY_PARAMS, key, 0).toString()
  }

  const numValue = typeof value === 'string' ? parseFloat(value) : value

  if (isNaN(numValue)) {
    return safeGetValue(DEFAULT_STRATEGY_PARAMS, key, 0).toString()
  }

  switch (key) {
    case 'ma_period':
    case 'confirmation_periods':
    case 'max_signals_per_day':
    case 'signal_cooldown':
      return numValue.toString()

    case 'initial_capital':
      return `¥${numValue.toLocaleString()}`

    case 'min_cross_percentage':
    case 'stop_loss_pct':
    case 'take_profit_pct':
    case 'max_position_size':
      return `${(numValue * 100).toFixed(2)}%`

    case 'ma_type':
      return String(value)

    default:
      return numValue.toString()
  }
}

// 获取参数配置分类
export const getParametersByCategory = () => {
  const categories = {
    basic: { name: '基础参数', description: '策略的基本配置参数' },
    signal: { name: '信号确认', description: '交易信号的确认和过滤参数' },
    risk: { name: '风险管理', description: '风险控制和仓位管理参数' },
    filter: { name: '信号过滤', description: '信号频率和过滤限制参数' }
  }

  const categorizedParams: Record<string, Array<{ key: keyof MovingAverageStrategyParams; meta: StrategyParameterMeta }>> = {
    basic: [],
    signal: [],
    risk: [],
    filter: []
  }

  Object.entries(STRATEGY_PARAMETER_META).forEach(([key, meta]) => {
    categorizedParams[meta.category].push({
      key: key as keyof MovingAverageStrategyParams,
      meta
    })
  })

  return { categories, categorizedParams }
}