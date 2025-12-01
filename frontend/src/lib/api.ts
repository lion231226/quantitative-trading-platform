import axios, { AxiosResponse } from 'axios';
import {
  APIError,
  APIResponse,
  MarketDataPoint,
  MarketDataRequest,
  StrategyConfig,
  StrategyResult,
  StrategyRunRequest,
  Symbol,
} from '@/types/api';

// 创建axios实例
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse<APIResponse<any>>) => {
    return response;
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      // 服务器响应错误
      const apiError: APIError = {
        code: error.response.data?.code || 'UNKNOWN_ERROR',
        message: error.response.data?.message || '请求失败',
        details: error.response.data?.details,
      };
      return Promise.reject(apiError);
    } else if (error.request) {
      // 网络错误
      const apiError: APIError = {
        code: 'NETWORK_ERROR',
        message: '网络连接失败，请检查网络设置',
      };
      return Promise.reject(apiError);
    } else {
      // 其他错误
      const apiError: APIError = {
        code: 'REQUEST_ERROR',
        message: error.message || '请求配置错误',
      };
      return Promise.reject(apiError);
    }
  },
);

// 市场数据API
export const marketDataAPI = {
  // 获取可用期货品种
  getSymbols: async (sector?: string): Promise<Symbol[]> => {
    const response = await apiClient.get('/api/v1/market-data/symbols', {
      params: { sector },
    });
    // 适配后端返回格式：{success: true, data: [...]}
    const rawData = response.data.data || [];
    // 直接使用后端返回的完整数据
    return rawData.map((item: any) => ({
      symbol: item.symbol,
      name: item.name,
      sector: item.sector,
      exchange: item.exchange,
    }));
  },

  // 获取历史数据
  getHistory: async (
    request: MarketDataRequest,
  ): Promise<MarketDataPoint[]> => {
    const response = await apiClient.post<APIResponse<MarketDataPoint[]>>(
      '/market-data/history',
      request,
    );
    return response.data.data;
  },

  // 绩效分析API - 获取绩效指标
  getPerformanceMetrics: async (
    strategyId: string,
    params?: any,
  ): Promise<any> => {
    const response = await apiClient.get<APIResponse<any>>(
      `/performance/metrics/${strategyId}`,
      { params },
    );
    return response.data;
  },

  // 绩效分析API - 计算收益率
  calculateReturns: async (request: any): Promise<any> => {
    const response = await apiClient.post<APIResponse<any>>(
      '/performance/calculate_returns',
      request,
    );
    return response.data;
  },

  // 绩效分析API - 生成绩效报告
  generateReport: async (request: any): Promise<any> => {
    const response = await apiClient.post<APIResponse<any>>(
      '/performance/report',
      request,
    );
    return response.data;
  },
};

// 策略API
export const strategyAPI = {
  // 获取策略列表
  getStrategies: async (): Promise<StrategyConfig[]> => {
    const response = await apiClient.get('/api/v1/strategies/');
    // API返回格式: {"strategies": [...], "total": 1}
    return response.data.strategies || [];
  },

  // 获取策略参数配置
  getStrategyParameters: async (strategyType: string): Promise<any> => {
    const response = await apiClient.get(
      `/strategies/parameters/${strategyType}`,
    );
    return response.data;
  },

  // 配置策略参数
  configureStrategy: async (
    strategyType: string,
    parameters: any,
  ): Promise<any> => {
    const response = await apiClient.post('/strategies/configure', {
      strategy_type: strategyType,
      parameters,
    });
    return response.data;
  },

  // 运行策略
  run: async (request: any): Promise<{ strategy_id: string }> => {
    const response = await apiClient.post<APIResponse<{ strategy_id: string }>>(
      '/api/v1/strategies/run',
      request,
    );
    // 处理可能的响应格式变化
    return response.data.data || response.data;
  },

  // 获取策略结果
  getResults: async (
    strategyId: string,
  ): Promise<StrategyResult & { rawData: any }> => {
    // 首先尝试从任务状态获取结果
    const statusResponse = await apiClient.get(
      `/strategies/task/${strategyId}/status`,
    );

    if (
      statusResponse.data.status === 'completed' &&
      statusResponse.data.result
    ) {
      // 转换后端结果格式为前端期望的格式
      const backendResult = statusResponse.data.result;
      return {
        id: strategyId,
        symbol: backendResult.symbol,
        total_return: backendResult.performance.total_return,
        max_drawdown: backendResult.performance.max_drawdown,
        sharpe_ratio: backendResult.performance.sharpe_ratio,
        win_rate: backendResult.performance.win_rate,
        total_trades: backendResult.performance.total_trades,
        profit_trades: backendResult.performance.winning_trades,
        loss_trades: backendResult.performance.losing_trades,
        average_return:
          backendResult.performance.total_pnl /
          backendResult.performance.total_trades,
        volatility: 0.02, // 可以根据需要计算
        rawData: backendResult, // 保留原始数据用于图表显示
      };
    }

    throw new Error('策略结果不存在或未完成');
  },

  // 获取任务状态
  getTaskStatus: async (taskId: string): Promise<any> => {
    const response = await apiClient.get(
      `/api/v1/strategies/task/${taskId}/status`,
    );
    return response.data;
  },
};

// 通用API方法
export const api = {
  get: async <T>(url: string, params?: any): Promise<T> => {
    const response = await apiClient.get<APIResponse<T>>(url, { params });
    return response.data.data;
  },

  post: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.post<APIResponse<T>>(url, data);
    return response.data.data;
  },

  put: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.put<APIResponse<T>>(url, data);
    return response.data.data;
  },

  delete: async <T>(url: string): Promise<T> => {
    const response = await apiClient.delete<APIResponse<T>>(url);
    return response.data.data;
  },
};

export default apiClient;
