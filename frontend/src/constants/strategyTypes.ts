import { StrategyType, StrategyTypeConfig } from '@/types/strategy';

// 策略类型配置
export const STRATEGY_TYPES: StrategyTypeConfig[] = [
  {
    id: 'single_ma',
    name: '单均线策略',
    description: '基于单条移动平均线的简单趋势跟踪策略，适合初学者',
    category: 'trend',
    status: 'available',
  },
  {
    id: 'dual_ma',
    name: '双均线策略',
    description: '使用快慢双均线交叉信号，减少假信号，提高策略稳定性',
    category: 'trend',
    status: 'coming-soon',
  },
  {
    id: 'rsi',
    name: 'RSI超买超卖策略',
    description: '基于相对强弱指数(RSI)的反转策略，适合震荡市场',
    category: 'momentum',
    status: 'coming-soon',
  },
  {
    id: 'macd',
    name: 'MACD动量策略',
    description: '结合MACD指标的趋势和动量分析，捕捉中期趋势变化',
    category: 'momentum',
    status: 'experimental',
  },
];

// 获取可用的策略类型
export const getAvailableStrategies = (): StrategyTypeConfig[] => {
  return STRATEGY_TYPES.filter((strategy) => strategy.status === 'available');
};

// 获取策略类型配置
export const getStrategyConfig = (
  strategyType: StrategyType,
): StrategyTypeConfig | undefined => {
  return STRATEGY_TYPES.find((strategy) => strategy.id === strategyType);
};

// 获取策略分类
export const getStrategiesByCategory = () => {
  const categories = {
    trend: { name: '趋势策略', description: '基于市场趋势的交易策略' },
    momentum: { name: '动量策略', description: '基于价格动量的交易策略' },
    volatility: { name: '波动率策略', description: '基于市场波动率的策略' },
    custom: { name: '自定义策略', description: '用户自定义的高级策略' },
  };

  const categorizedStrategies: Record<string, StrategyTypeConfig[]> = {
    trend: [],
    momentum: [],
    volatility: [],
    custom: [],
  };

  STRATEGY_TYPES.forEach((strategy) => {
    categorizedStrategies[strategy.category].push(strategy);
  });

  return { categories, categorizedStrategies };
};

// 策略状态标签映射
export const STRATEGY_STATUS_LABELS = {
  available: {
    text: '可用',
    color: 'bg-green-100 text-green-800',
    borderColor: 'border-green-200',
  },
  'coming-soon': {
    text: '即将推出',
    color: 'bg-blue-100 text-blue-800',
    borderColor: 'border-blue-200',
  },
  experimental: {
    text: '实验性',
    color: 'bg-orange-100 text-orange-800',
    borderColor: 'border-orange-200',
  },
};

// 策略分类标签映射
export const STRATEGY_CATEGORY_LABELS = {
  trend: { text: '趋势', color: 'bg-purple-100 text-purple-800' },
  momentum: { text: '动量', color: 'bg-indigo-100 text-indigo-800' },
  volatility: { text: '波动率', color: 'bg-pink-100 text-pink-800' },
  custom: { text: '自定义', color: 'bg-gray-100 text-gray-800' },
};
