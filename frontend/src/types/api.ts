// API响应类型
export interface APIResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

// 市场数据相关类型
export interface Symbol {
  symbol: string;
  name: string;
  sector: string;
  exchange: string;
}

export interface MarketDataRequest {
  symbol: string;
  start_date: string;
  end_date: string;
}

export interface MarketDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 策略相关类型
export interface StrategyConfig {
  name: string;
  display_name: string;
  description: string;
  parameters: Record<string, any>;
}

export interface StrategyRunRequest {
  symbol: string;
  start_date: string;
  end_date: string;
  config: StrategyConfig;
}

export interface StrategyResult {
  id: string;
  symbol: string;
  total_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_trades: number;
  profit_trades: number;
  loss_trades: number;
  average_return: number;
  volatility: number;
}

// 错误类型
export interface APIError {
  code: string;
  message: string;
  details?: any;
}
