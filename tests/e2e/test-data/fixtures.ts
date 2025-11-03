// Test data fixtures for E2E testing

export interface MarketData {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
}

export interface StrategyConfig {
  name: string;
  symbol: string;
  shortWindow: number;
  longWindow: number;
  initialCapital: number;
}

export interface BacktestResult {
  id: string;
  symbol: string;
  strategy: string;
  totalReturn: number;
  annualizedReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  startDate: string;
  endDate: string;
}

// Sample market data
export const SAMPLE_MARKET_DATA: MarketData[] = [
  {
    symbol: '000001.SZ',
    name: '平安银行',
    sector: '金融',
    price: 12.58,
    change: 0.15,
    changePercent: 1.21,
    volume: 12500000
  },
  {
    symbol: '000002.SZ',
    name: '万科A',
    sector: '房地产',
    price: 8.92,
    change: -0.08,
    changePercent: -0.89,
    volume: 8900000
  },
  {
    symbol: '000858.SZ',
    name: '五粮液',
    sector: '消费品',
    price: 168.45,
    change: 2.13,
    changePercent: 1.28,
    volume: 3200000
  },
  {
    symbol: '600036.SH',
    name: '招商银行',
    sector: '金融',
    price: 35.68,
    change: 0.45,
    changePercent: 1.28,
    volume: 15600000
  },
  {
    symbol: '600519.SH',
    name: '贵州茅台',
    sector: '消费品',
    price: 1688.00,
    change: 15.20,
    changePercent: 0.91,
    volume: 450000
  }
];

// Sample strategy configurations
export const SAMPLE_STRATEGY_CONFIGS: StrategyConfig[] = [
  {
    name: '双均线策略',
    symbol: '000001.SZ',
    shortWindow: 5,
    longWindow: 20,
    initialCapital: 100000
  },
  {
    name: '长短期均线策略',
    symbol: '000858.SZ',
    shortWindow: 10,
    longWindow: 30,
    initialCapital: 500000
  },
  {
    name: '保守策略',
    symbol: '600519.SH',
    shortWindow: 20,
    longWindow: 60,
    initialCapital: 1000000
  }
];

// Sample backtest results
export const SAMPLE_BACKTEST_RESULTS: BacktestResult[] = [
  {
    id: 'bt_001',
    symbol: '000001.SZ',
    strategy: '双均线策略',
    totalReturn: 15.68,
    annualizedReturn: 18.45,
    maxDrawdown: -8.92,
    sharpeRatio: 1.24,
    winRate: 0.65,
    startDate: '2023-01-01',
    endDate: '2024-01-01'
  },
  {
    id: 'bt_002',
    symbol: '000858.SZ',
    strategy: '长短期均线策略',
    totalReturn: 22.34,
    annualizedReturn: 24.18,
    maxDrawdown: -12.15,
    sharpeRatio: 1.56,
    winRate: 0.72,
    startDate: '2023-01-01',
    endDate: '2024-01-01'
  },
  {
    id: 'bt_003',
    symbol: '600519.SH',
    strategy: '保守策略',
    totalReturn: 8.92,
    annualizedReturn: 10.24,
    maxDrawdown: -5.68,
    sharpeRatio: 0.98,
    winRate: 0.58,
    startDate: '2023-01-01',
    endDate: '2024-01-01'
  }
];

// Error scenarios for testing
export const ERROR_SCENARIOS = {
  invalidSymbol: 'INVALID.SYMBOL',
  invalidDateRange: {
    startDate: '2024-12-31',
    endDate: '2024-01-01'
  },
  invalidStrategyParams: {
    shortWindow: 50,
    longWindow: 10  // Invalid: short window > long window
  },
  networkError: 'NETWORK_ERROR',
  serverError: 'SERVER_ERROR'
};

// Performance benchmarks
export const PERFORMANCE_BENCHMARKS = {
  apiResponseTime: 500, // ms
  pageLoadTime: 3000,   // ms
  strategyCalculationTime: 10000, // ms
  concurrentUsers: 10,
  testTimeout: 30000    // ms
};

// Test user credentials (if authentication is implemented)
export const TEST_USERS = {
  validUser: {
    username: 'testuser@example.com',
    password: 'testpass123'
  },
  invalidUser: {
    username: 'invalid@example.com',
    password: 'wrongpass'
  }
};

// Utility functions to generate test data
export class TestDataGenerator {
  // Generate random market data
  static generateMarketData(count: number = 10): MarketData[] {
    const sectors = ['金融', '房地产', '消费品', '科技', '医药', '能源'];
    const symbols = ['SZ', 'SH'];

    return Array.from({ length: count }, (_, index) => ({
      symbol: `${String(index + 1).padStart(6, '0')}.${symbols[index % 2]}`,
      name: `测试股票${index + 1}`,
      sector: sectors[index % sectors.length],
      price: Number((Math.random() * 100 + 10).toFixed(2)),
      change: Number((Math.random() * 10 - 5).toFixed(2)),
      changePercent: Number((Math.random() * 10 - 5).toFixed(2)),
      volume: Math.floor(Math.random() * 10000000) + 1000000
    }));
  }

  // Generate random strategy configuration
  static generateStrategyConfig(): StrategyConfig {
    const symbols = SAMPLE_MARKET_DATA.map(data => data.symbol);
    const symbol = symbols[Math.floor(Math.random() * symbols.length)];

    let shortWindow = Math.floor(Math.random() * 20) + 5;
    let longWindow = shortWindow + Math.floor(Math.random() * 30) + 10;

    return {
      name: `测试策略_${Date.now()}`,
      symbol,
      shortWindow,
      longWindow,
      initialCapital: Math.floor(Math.random() * 1000000) + 100000
    };
  }

  // Generate backtest result
  static generateBacktestResult(symbol: string, strategy: string): BacktestResult {
    const totalReturn = Number((Math.random() * 50 - 10).toFixed(2));
    const annualizedReturn = Number((totalReturn * 1.2).toFixed(2));
    const maxDrawdown = Number((-Math.random() * 20).toFixed(2));
    const sharpeRatio = Number((Math.random() * 2 + 0.5).toFixed(2));
    const winRate = Number((Math.random() * 0.4 + 0.5).toFixed(2));

    return {
      id: `bt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      symbol,
      strategy,
      totalReturn,
      annualizedReturn,
      maxDrawdown,
      sharpeRatio,
      winRate,
      startDate: '2023-01-01',
      endDate: '2024-01-01'
    };
  }

  // Generate test data for performance testing
  static generatePerformanceTestData(userCount: number = 10) {
    return Array.from({ length: userCount }, () => ({
      symbol: this.generateStrategyConfig().symbol,
      strategyConfig: this.generateStrategyConfig(),
      requestTimestamp: Date.now() + Math.random() * 1000
    }));
  }
}