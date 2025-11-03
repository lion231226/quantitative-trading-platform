import { test, expect } from '@playwright/test';
import { APIUtils } from '../../e2e/test-helpers';

test.describe('市场数据API集成测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('GET /api/v1/market-data/symbols', () => {
    test('应该返回所有股票数据', async () => {
      const result = await apiUtils.testEndpoint('/api/v1/market-data/symbols');

      expect(result.success).toBe(true);
      expect(result.status).toBe(200);
      expect(result.data).toBeDefined();
      expect(Array.isArray(result.data.data)).toBe(true);
      expect(result.data.success).toBe(true);

      // 验证数据结构
      if (result.data.data.length > 0) {
        const stock = result.data.data[0];
        expect(stock).toHaveProperty('symbol');
        expect(stock).toHaveProperty('name');
        expect(stock).toHaveProperty('sector');
        expect(stock).toHaveProperty('price');
        expect(stock).toHaveProperty('change');
        expect(stock).toHaveProperty('changePercent');
        expect(stock).toHaveProperty('volume');
      }
    });

    test('应该支持按行业筛选', async () => {
      const sector = '金融';
      const result = await apiUtils.testEndpoint(`/api/v1/market-data/symbols?sector=${encodeURIComponent(sector)}`);

      expect(result.success).toBe(true);
      expect(result.status).toBe(200);

      // 验证筛选结果
      if (result.data.data.length > 0) {
        result.data.data.forEach((stock: any) => {
          expect(stock.sector).toBe(sector);
        });
      }
    });

    test('应该处理无效的行业参数', async () => {
      const invalidSector = '不存在的行业';
      const result = await apiUtils.testEndpoint(`/api/v1/market-data/symbols?sector=${encodeURIComponent(invalidSector)}`);

      expect(result.success).toBe(true);
      expect(result.status).toBe(200);
      expect(result.data.data).toEqual([]);
    });

    test('应该验证API响应时间', async () => {
      const startTime = Date.now();
      const result = await apiUtils.testEndpoint('/api/v1/market-data/symbols');
      const endTime = Date.now();

      const responseTime = endTime - startTime;
      expect(responseTime).toBeLessThan(5000); // 5秒内响应
      expect(result.success).toBe(true);
    });
  });

  test.describe('GET /api/v1/market-data/symbol/{symbol}', () => {
    test('应该返回指定股票的详细数据', async () => {
      const symbol = '000001.SZ';
      const result = await apiUtils.testEndpoint(`/api/v1/market-data/symbol/${symbol}`);

      expect(result.success).toBe(true);
      expect(result.status).toBe(200);
      expect(result.data).toBeDefined();
      expect(result.data.success).toBe(true);

      if (result.data.data) {
        const stock = result.data.data;
        expect(stock.symbol).toBe(symbol);
        expect(stock).toHaveProperty('name');
        expect(stock).toHaveProperty('sector');
        expect(stock).toHaveProperty('price');
        expect(stock).toHaveProperty('change');
        expect(stock).toHaveProperty('changePercent');
        expect(stock).toHaveProperty('volume');
      }
    });

    test('应该处理不存在的股票代码', async () => {
      const invalidSymbol = 'INVALID.SYMBOL';
      const result = await apiUtils.testEndpoint(`/api/v1/market-data/symbol/${invalidSymbol}`);

      expect(result.success).toBe(false);
      expect(result.status).toBe(404);
      expect(result.data.success).toBe(false);
      expect(result.data.message).toContain('不存在');
    });
  });

  test.describe('缓存机制测试', () => {
    test('应该使用缓存提高响应速度', async () => {
      // 第一次请求
      const startTime1 = Date.now();
      const result1 = await apiUtils.testEndpoint('/api/v1/market-data/symbols');
      const responseTime1 = Date.now() - startTime1;

      // 第二次请求（应该使用缓存）
      const startTime2 = Date.now();
      const result2 = await apiUtils.testEndpoint('/api/v1/market-data/symbols');
      const responseTime2 = Date.now() - startTime2;

      expect(result1.success).toBe(true);
      expect(result2.success).toBe(true);
      expect(result1.data.data).toEqual(result2.data.data);

      // 缓存请求应该更快（至少快20%）
      if (responseTime1 > 1000) {
        expect(responseTime2).toBeLessThan(responseTime1 * 0.8);
      }
    });
  });

  test.describe('错误处理测试', () => {
    test('应该处理网络错误', async () => {
      const apiUtilsBroken = new APIUtils('http://localhost:9999'); // 不存在的服务
      const result = await apiUtilsBroken.testEndpoint('/api/v1/market-data/symbols');

      expect(result.success).toBe(false);
      expect(result.status).toBe(0);
    });

    test('应该处理无效的请求格式', async () => {
      // 测试无效的查询参数
      const result = await apiUtils.testEndpoint('/api/v1/market-data/symbols?invalid_param=test');

      // 应该忽略无效参数并返回正常结果
      expect(result.success).toBe(true);
      expect(result.status).toBe(200);
    });
  });
});