import { Page, Route, Request } from '@playwright/test';
import {
  SAMPLE_MARKET_DATA,
  SAMPLE_STRATEGY_CONFIGS,
  SAMPLE_BACKTEST_RESULTS,
  ERROR_SCENARIOS,
  TestDataGenerator
} from '../test-data/fixtures';

// API mock responses for testing
export class APIMocks {
  constructor(private page: Page) {}

  // Setup all API mocks
  async setupAllMocks() {
    await this.mockMarketDataAPI();
    await this.mockStrategyAPI();
    await this.mockBacktestAPI();
    await this.mockErrorScenarios();
  }

  // Mock market data API endpoints
  async mockMarketDataAPI() {
    // GET /api/v1/market-data/symbols
    await this.page.route('**/api/v1/market-data/symbols*', async (route) => {
      const url = new URL(route.request().url());
      const sector = url.searchParams.get('sector');

      let filteredData = SAMPLE_MARKET_DATA;
      if (sector) {
        filteredData = SAMPLE_MARKET_DATA.filter(item => item.sector === sector);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: filteredData,
          message: `找到 ${filteredData.length} 支股票`
        })
      });
    });

    // GET /api/v1/market-data/symbol/{symbol}
    await this.page.route('**/api/v1/market-data/symbol/*', async (route) => {
      const symbol = route.request().url().split('/').pop();
      const stockData = SAMPLE_MARKET_DATA.find(item => item.symbol === symbol);

      if (stockData) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: stockData,
            message: '获取股票数据成功'
          })
        });
      } else {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            data: null,
            message: '股票代码不存在'
          })
        });
      }
    });
  }

  // Mock strategy API endpoints
  async mockStrategyAPI() {
    // POST /api/v1/strategies/config
    await this.page.route('**/api/v1/strategies/config', async (route) => {
      const config = await route.request().postDataJSON();

      // Validate strategy configuration
      if (config.shortWindow >= config.longWindow) {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            data: null,
            message: '短期窗口必须小于长期窗口'
          })
        });
        return;
      }

      const newConfig = {
        id: `config_${Date.now()}`,
        ...config,
        createdAt: new Date().toISOString()
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: newConfig,
          message: '策略配置保存成功'
        })
      });
    });

    // GET /api/v1/strategies/configs
    await this.page.route('**/api/v1/strategies/configs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: SAMPLE_STRATEGY_CONFIGS.map((config, index) => ({
            id: `config_${index + 1}`,
            ...config,
            createdAt: '2023-01-01T00:00:00Z'
          })),
          message: '获取策略配置列表成功'
        })
      });
    });
  }

  // Mock backtest API endpoints
  async mockBacktestAPI() {
    // POST /api/v1/strategies/run
    await this.page.route('**/api/v1/strategies/run', async (route) => {
      const strategyConfig = await route.request().postDataJSON();

      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 1000));

      const result = TestDataGenerator.generateBacktestResult(
        strategyConfig.symbol,
        strategyConfig.name || '双均线策略'
      );

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: result,
          message: '回测完成'
        })
      });
    });

    // GET /api/v1/strategies/results/{resultId}
    await this.page.route('**/api/v1/strategies/results/*', async (route) => {
      const resultId = route.request().url().split('/').pop();

      // Find or generate result
      let result = SAMPLE_BACKTEST_RESULTS.find(r => r.id === resultId);
      if (!result) {
        result = TestDataGenerator.generateBacktestResult('000001.SZ', '默认策略');
        result.id = resultId;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: result,
          message: '获取回测结果成功'
        })
      });
    });

    // GET /api/v1/strategies/results
    await this.page.route('**/api/v1/strategies/results*', async (route) => {
      const url = new URL(route.request().url());
      const symbol = url.searchParams.get('symbol');

      let filteredResults = SAMPLE_BACKTEST_RESULTS;
      if (symbol) {
        filteredResults = SAMPLE_BACKTEST_RESULTS.filter(result => result.symbol === symbol);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: filteredResults,
          message: '获取回测结果列表成功'
        })
      });
    });
  }

  // Mock error scenarios
  async mockErrorScenarios() {
    // Network error simulation
    await this.page.route('**/api/v1/network-error', async (route) => {
      await route.abort('failed');
    });

    // Server error simulation
    await this.page.route('**/api/v1/server-error', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          data: null,
          message: '服务器内部错误'
        })
      });
    });

    // Timeout simulation
    await this.page.route('**/api/v1/timeout', async (route) => {
      // Don't fulfill the request to simulate timeout
      await new Promise(resolve => setTimeout(resolve, 60000));
    });

    // Invalid symbol error
    await this.page.route('**/api/v1/market-data/symbol/INVALID.SYMBOL', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          data: null,
          message: '股票代码不存在'
        })
      });
    });
  }

  // Mock slow responses for performance testing
  async mockSlowResponses(delay: number = 2000) {
    await this.page.route('**/api/v1/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, delay));
      await route.continue();
    });
  }

  // Setup mock for specific endpoint
  async mockEndpoint(urlPattern: string, response: any, status: number = 200) {
    await this.page.route(urlPattern, async (route) => {
      await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(response)
      });
    });
  }

  // Remove all mocks
  async removeAllMocks() {
    await this.page.unroute('**/api/v1/**');
  }
}

// Mock data for load testing
export class LoadTestMocks {
  // Generate multiple concurrent requests
  static async simulateConcurrentRequests(page: Page, count: number, endpoint: string) {
    const requests = Array.from({ length: count }, (_, index) =>
      page.evaluate(({ endpoint, index }) => {
        return fetch(`${endpoint}?userId=${index}`)
          .then(response => response.json())
          .catch(error => ({ error: error.message }));
      }, { endpoint, index })
    );

    return Promise.all(requests);
  }

  // Mock cache behavior
  static async setupCacheMocks(page: Page) {
    const cache = new Map();

    await page.route('**/api/v1/cache/*', async (route) => {
      const cacheKey = route.request().url();

      if (cache.has(cacheKey)) {
        const cachedResponse = cache.get(cacheKey);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: cachedResponse,
            cached: true,
            message: '从缓存获取数据'
          })
        });
        return;
      }

      // Simulate cache miss
      const newResponse = TestDataGenerator.generateMarketData(1)[0];
      cache.set(cacheKey, newResponse);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: newResponse,
          cached: false,
          message: '获取新数据'
        })
      });
    });
  }
}