import { test, expect } from '@playwright/test';
import { APIUtils } from '../../../tests/e2e/test-helpers';
import { TestDataGenerator } from '../../../tests/e2e/test-data/fixtures';

test.describe('策略API集成测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('POST /api/v1/strategies/config', () => {
    test('应该成功保存策略配置', async () => {
      const strategyConfig = TestDataGenerator.generateStrategyConfig();

      const response = await apiUtils.makeAPIRequest('/strategies/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });

      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.data).toBeDefined();
      expect(data.data.id).toBeTruthy();
      expect(data.data.symbol).toBe(strategyConfig.symbol);
      expect(data.data.shortWindow).toBe(strategyConfig.shortWindow);
      expect(data.data.longWindow).toBe(strategyConfig.longWindow);
      expect(data.data.initialCapital).toBe(strategyConfig.initialCapital);

      console.log(`✅ 策略配置保存成功: ${data.data.id}`);
    });

    test('应该验证策略参数', async () => {
      const invalidConfig = {
        symbol: '000001.SZ',
        shortWindow: 50, // 错误：短期窗口大于长期窗口
        longWindow: 10,
        initialCapital: 100000
      };

      const response = await apiUtils.makeAPIRequest('/strategies/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(invalidConfig)
      });

      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toContain('短期窗口必须小于长期窗口');
    });

    test('应该验证必需字段', async () => {
      const incompleteConfig = {
        symbol: '000001.SZ',
        // 缺少其他必需字段
      };

      const response = await apiUtils.makeAPIRequest('/strategies/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(incompleteConfig)
      });

      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toContain('必需');
    });

    test('应该处理无效的股票代码', async () => {
      const invalidConfig = {
        symbol: 'INVALID.SYMBOL',
        shortWindow: 5,
        longWindow: 20,
        initialCapital: 100000
      };

      const response = await apiUtils.makeAPIRequest('/strategies/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(invalidConfig)
      });

      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toContain('股票代码');
    });

    test('应该验证参数范围', async () => {
      const testCases = [
        {
          config: {
            symbol: '000001.SZ',
            shortWindow: 0, // 错误：窗口期过小
            longWindow: 20,
            initialCapital: 100000
          },
          expectedError: '窗口期'
        },
        {
          config: {
            symbol: '000001.SZ',
            shortWindow: 5,
            longWindow: 1000, // 错误：窗口期过大
            initialCapital: 100000
          },
          expectedError: '窗口期'
        },
        {
          config: {
            symbol: '000001.SZ',
            shortWindow: 5,
            longWindow: 20,
            initialCapital: 0 // 错误：初始资金过小
          },
          expectedError: '初始资金'
        },
        {
          config: {
            symbol: '000001.SZ',
            shortWindow: 5,
            longWindow: 20,
            initialCapital: -1000 // 错误：负数资金
          },
          expectedError: '初始资金'
        }
      ];

      for (const testCase of testCases) {
        const response = await apiUtils.makeAPIRequest('/strategies/config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(testCase.config)
        });

        const data = await response.json();

        expect(response.status).toBe(400);
        expect(data.success).toBe(false);
        expect(data.message).toContain(testCase.expectedError);

        console.log(`✅ 参数验证通过: ${testCase.expectedError}`);
      }
    });
  });

  test.describe('GET /api/v1/strategies/configs', () => {
    test('应该返回保存的策略配置列表', async () => {
      const response = await apiUtils.makeAPIRequest('/strategies/configs');
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.data).toBeDefined();
      expect(Array.isArray(data.data)).toBe(true);

      // 验证数据结构
      if (data.data.length > 0) {
        const config = data.data[0];
        expect(config).toHaveProperty('id');
        expect(config).toHaveProperty('symbol');
        expect(config).toHaveProperty('shortWindow');
        expect(config).toHaveProperty('longWindow');
        expect(config).toHaveProperty('initialCapital');
        expect(config).toHaveProperty('createdAt');
      }
    });

    test('应该支持分页查询', async () => {
      const response = await apiUtils.makeAPIRequest('/strategies/configs?page=1&limit=5');
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);

      // 如果有数据，验证分页信息
      if (data.data.length > 0) {
        expect(data.data.length).toBeLessThanOrEqual(5);
      }
    });

    test('应该支持按股票代码筛选', async () => {
      const symbol = '000001.SZ';
      const response = await apiUtils.makeAPIRequest(`/strategies/configs?symbol=${symbol}`);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);

      // 验证筛选结果
      if (data.data.length > 0) {
        data.data.forEach((config: any) => {
          expect(config.symbol).toBe(symbol);
        });
      }
    });
  });

  test.describe('POST /api/v1/strategies/run', () => {
    test('应该成功运行策略回测', async () => {
      const strategyConfig = TestDataGenerator.generateStrategyConfig();

      const response = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });

      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.data).toBeDefined();
      expect(data.data.id).toBeTruthy();
      expect(data.data.symbol).toBe(strategyConfig.symbol);
      expect(data.data.strategy).toBeTruthy();
      expect(data.data.totalReturn).toBeDefined();
      expect(data.data.annualizedReturn).toBeDefined();
      expect(data.data.maxDrawdown).toBeDefined();
      expect(data.data.sharpeRatio).toBeDefined();
      expect(data.data.winRate).toBeDefined();
      expect(data.data.startDate).toBeTruthy();
      expect(data.data.endDate).toBeTruthy();

      console.log(`✅ 策略回测成功: ${data.data.id}`);
    });

    test('回测结果数据应该在合理范围内', async () => {
      const strategyConfig = TestDataGenerator.generateStrategyConfig();

      const response = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });

      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);

      const result = data.data;

      // 验证数值范围
      expect(typeof result.totalReturn).toBe('number');
      expect(typeof result.annualizedReturn).toBe('number');
      expect(typeof result.maxDrawdown).toBe('number');
      expect(typeof result.sharpeRatio).toBe('number');
      expect(typeof result.winRate).toBe('number');

      // 验证合理范围
      expect(result.totalReturn).toBeGreaterThan(-100); // 最大损失不超过100%
      expect(result.totalReturn).toBeLessThan(1000); // 收益不超过1000%
      expect(result.maxDrawdown).toBeLessThanOrEqual(0); // 最大回撤应该是负数或0
      expect(result.maxDrawdown).toBeGreaterThanOrEqual(-100); // 不超过-100%
      expect(result.sharpeRatio).toBeGreaterThan(-5); // 夏普比率合理范围
      expect(result.sharpeRatio).toBeLessThan(10);
      expect(result.winRate).toBeGreaterThanOrEqual(0); // 胜率在0-100%之间
      expect(result.winRate).toBeLessThanOrEqual(1);

      console.log(`📊 回测结果验证通过: 总收益=${result.totalReturn}%, 夏普比率=${result.sharpeRatio}`);
    });

    test('应该处理长时间运行的回测', async () => {
      const strategyConfig = {
        ...TestDataGenerator.generateStrategyConfig(),
        // 使用较长的日期范围来模拟长时间运行
        startDate: '2020-01-01',
        endDate: '2024-01-01'
      };

      const startTime = Date.now();
      const response = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });
      const executionTime = Date.now() - startTime;

      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(executionTime).toBeLessThan(30000); // 30秒内完成

      console.log(`📊 长时间回测耗时: ${executionTime}ms`);
    });
  });

  test.describe('GET /api/v1/strategies/results/{resultId}', () => {
    test('应该返回指定的回测结果', async () => {
      // 先运行一个策略来获取结果ID
      const strategyConfig = TestDataGenerator.generateStrategyConfig();
      const runResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });
      const runData = await runResponse.json();
      const resultId = runData.data.id;

      // 查询结果
      const response = await apiUtils.makeAPIRequest(`/strategies/results/${resultId}`);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.data).toBeDefined();
      expect(data.data.id).toBe(resultId);

      console.log(`✅ 回测结果查询成功: ${resultId}`);
    });

    test('应该处理不存在的回测结果ID', async () => {
      const invalidResultId = 'invalid_result_id';
      const response = await apiUtils.makeAPIRequest(`/strategies/results/${invalidResultId}`);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toContain('不存在');
    });
  });

  test.describe('GET /api/v1/strategies/results', () => {
    test('应该返回回测结果列表', async () => {
      const response = await apiUtils.makeAPIRequest('/strategies/results');
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.data).toBeDefined();
      expect(Array.isArray(data.data)).toBe(true);

      // 验证数据结构
      if (data.data.length > 0) {
        const result = data.data[0];
        expect(result).toHaveProperty('id');
        expect(result).toHaveProperty('symbol');
        expect(result).toHaveProperty('strategy');
        expect(result).toHaveProperty('totalReturn');
        expect(result).toHaveProperty('createdAt');
      }
    });

    test('应该支持按股票代码筛选结果', async () => {
      const symbol = '000001.SZ';
      const response = await apiUtils.makeAPIRequest(`/strategies/results?symbol=${symbol}`);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);

      // 验证筛选结果
      if (data.data.length > 0) {
        data.data.forEach((result: any) => {
          expect(result.symbol).toBe(symbol);
        });
      }
    });

    test('应该支持按时间范围筛选', async () => {
      const startDate = '2024-01-01';
      const endDate = '2024-12-31';
      const response = await apiUtils.makeAPIRequest(`/strategies/results?startDate=${startDate}&endDate=${endDate}`);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);

      console.log(`📊 时间范围筛选结果: ${data.data.length}条`);
    });
  });

  test.describe('策略API性能测试', () => {
    test('策略运行API响应时间测试', async () => {
      const strategyConfig = TestDataGenerator.generateStrategyConfig();

      const startTime = Date.now();
      const response = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });
      const responseTime = Date.now() - startTime;

      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(responseTime).toBeLessThan(15000); // 15秒内完成

      console.log(`📊 策略运行API响应时间: ${responseTime}ms`);
    });

    test('并发策略运行测试', async () => {
      const concurrentRequests = 3;
      const strategyConfigs = Array.from({ length: concurrentRequests }, () =>
        TestDataGenerator.generateStrategyConfig()
      );

      const startTime = Date.now();
      const promises = strategyConfigs.map(config =>
        apiUtils.makeAPIRequest('/strategies/run', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(config)
        })
      );

      const responses = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      // 验证所有请求都成功
      responses.forEach(async (response, index) => {
        const data = await response.json();
        expect(response.status).toBe(200);
        expect(data.success).toBe(true);
        console.log(`📊 并发请求${index + 1}完成`);
      });

      console.log(`📊 ${concurrentRequests}个并发策略运行总时间: ${totalTime}ms`);
    });
  });

  test.describe('数据一致性测试', () => {
    test('策略配置和结果的数据一致性', async () => {
      const strategyConfig = TestDataGenerator.generateStrategyConfig();

      // 保存策略配置
      const configResponse = await apiUtils.makeAPIRequest('/strategies/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });
      const configData = await configResponse.json();

      // 运行策略
      const runResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyConfig)
      });
      const runData = await runResponse.json();

      // 验证数据一致性
      expect(configData.data.symbol).toBe(strategyConfig.symbol);
      expect(runData.data.symbol).toBe(strategyConfig.symbol);
      expect(runData.data.strategy).toContain(strategyConfig.symbol);

      console.log(`✅ 数据一致性验证通过: ${strategyConfig.symbol}`);
    });
  });
});