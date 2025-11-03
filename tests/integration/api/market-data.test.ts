import { test, expect } from '@playwright/test';
import { APIUtils } from '../../../tests/e2e/test-helpers';

test.describe('市场数据API集成测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('GET /api/v1/market-data/symbols', () => {
    test('应该返回所有股票数据', async () => {
      const result = await apiUtils.testEndpoint('/market-data/symbols');

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
      const result = await apiUtils.testEndpoint(`/market-data/symbols?sector=${encodeURIComponent(sector)}`);

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
      const result = await apiUtils.testEndpoint(`/market-data/symbols?sector=${encodeURIComponent(invalidSector)}`);

      expect(result.success).toBe(true);
      expect(result.status).toBe(200);
      expect(result.data.data).toEqual([]);
    });
  });

  test.describe('GET /api/v1/market-data/symbol/{symbol}', () => {
    test('应该返回指定股票的详细信息', async () => {
      const symbol = '000001.SZ';
      const result = await apiUtils.testEndpoint(`/market-data/symbol/${symbol}`);

      expect(result.success).toBe(true);
      expect(result.status).toBe(200);
      expect(result.data).toBeDefined();
      expect(result.data.success).toBe(true);

      // 验证数据结构
      const stock = result.data.data;
      expect(stock).toHaveProperty('symbol', symbol);
      expect(stock).toHaveProperty('name');
      expect(stock).toHaveProperty('sector');
      expect(stock).toHaveProperty('price');
      expect(stock).toHaveProperty('change');
      expect(stock).toHaveProperty('changePercent');
      expect(stock).toHaveProperty('volume');
    });

    test('应该处理不存在的股票代码', async () => {
      const invalidSymbol = 'INVALID.SYMBOL';
      const result = await apiUtils.testEndpoint(`/market-data/symbol/${invalidSymbol}`, 404);

      expect(result.success).toBe(false);
      expect(result.status).toBe(404);
      expect(result.data).toBeDefined();
      expect(result.data.success).toBe(false);
      expect(result.data.message).toContain('不存在');
    });

    test('应该处理特殊字符的股票代码', async () => {
      const specialSymbol = 'ST*001.SZ';
      const result = await apiUtils.testEndpoint(`/market-data/symbol/${encodeURIComponent(specialSymbol)}`);

      // 根据API设计，可能返回404或正常响应
      expect([200, 404]).toContain(result.status);
      expect(result.data).toBeDefined();
    });
  });

  test.describe('API响应格式验证', () => {
    test('所有响应都应该遵循统一格式', async () => {
      const endpoints = [
        '/market-data/symbols',
        '/market-data/symbol/000001.SZ'
      ];

      for (const endpoint of endpoints) {
        const response = await apiUtils.makeAPIRequest(endpoint);
        const data = await response.json();

        // 验证统一响应格式
        expect(data).toHaveProperty('success');
        expect(data).toHaveProperty('data');
        expect(data).toHaveProperty('message');

        // 验证数据类型
        expect(typeof data.success).toBe('boolean');
        expect(typeof data.message).toBe('string');

        console.log(`✅ ${endpoint} 响应格式验证通过`);
      }
    });
  });

  test.describe('API性能测试', () => {
    test('API响应时间应该在可接受范围内', async () => {
      const endpoints = [
        '/market-data/symbols',
        '/market-data/symbol/000001.SZ'
      ];

      for (const endpoint of endpoints) {
        const startTime = Date.now();
        const result = await apiUtils.testEndpoint(endpoint);
        const responseTime = Date.now() - startTime;

        expect(result.success).toBe(true);
        expect(responseTime).toBeLessThan(1000); // 1秒内响应

        console.log(`📊 ${endpoint} 响应时间: ${responseTime}ms`);
      }
    });

    test('并发请求处理能力', async () => {
      const endpoint = '/market-data/symbols';
      const concurrentRequests = 10;

      const promises = Array.from({ length: concurrentRequests }, () =>
        apiUtils.testEndpoint(endpoint)
      );

      const startTime = Date.now();
      const results = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      // 验证所有请求都成功
      results.forEach((result, index) => {
        expect(result.success).toBe(true);
        console.log(`📊 并发请求${index + 1}状态: ${result.status}`);
      });

      // 验证总响应时间合理
      expect(totalTime).toBeLessThan(5000); // 5秒内完成所有请求

      console.log(`📊 ${concurrentRequests}个并发请求总时间: ${totalTime}ms`);
    });
  });

  test.describe('错误处理测试', () => {
    test('应该正确处理HTTP错误状态', async () => {
      // 测试不存在的端点
      const result = await apiUtils.testEndpoint('/market-data/nonexistent', 404);
      expect(result.success).toBe(false);
      expect(result.status).toBe(404);
    });

    test('应该处理无效的请求方法', async () => {
      const response = await apiUtils.makeAPIRequest('/market-data/symbols', {
        method: 'POST',
        body: JSON.stringify({})
      });

      // 根据API设计，可能返回405 Method Not Allowed或其他错误
      expect([405, 400, 404]).toContain(response.status);
    });

    test('应该处理无效的请求头', async () => {
      const response = await apiUtils.makeAPIRequest('/market-data/symbols', {
        headers: {
          'Content-Type': 'invalid/content-type'
        }
      });

      // API应该能够处理或忽略无效头
      expect([200, 400, 415]).toContain(response.status);
    });
  });

  test.describe('数据质量验证', () => {
    test('返回的数据应该完整且有效', async () => {
      const result = await apiUtils.testEndpoint('/market-data/symbols');

      expect(result.success).toBe(true);
      expect(result.data.data.length).toBeGreaterThan(0);

      // 验证每条数据的完整性
      result.data.data.forEach((stock: any, index: number) => {
        // 必需字段检查
        expect(stock.symbol).toBeTruthy();
        expect(stock.name).toBeTruthy();
        expect(stock.sector).toBeTruthy();

        // 数值字段检查
        expect(typeof stock.price).toBe('number');
        expect(typeof stock.volume).toBe('number');
        expect(stock.price).toBeGreaterThan(0);
        expect(stock.volume).toBeGreaterThan(0);

        // 百分比字段检查
        expect(typeof stock.changePercent).toBe('number');
        expect(stock.changePercent).toBeGreaterThanOrEqual(-100);
        expect(stock.changePercent).toBeLessThanOrEqual(100);

        console.log(`✅ 股票${index + 1}数据质量验证通过`);
      });
    });

    test('价格数据应该在合理范围内', async () => {
      const result = await apiUtils.testEndpoint('/market-data/symbols');

      if (result.data.data.length > 0) {
        const prices = result.data.data.map((stock: any) => stock.price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);

        // A股价格通常在1-1000元范围内
        expect(minPrice).toBeGreaterThan(0);
        expect(maxPrice).toBeLessThan(10000);

        console.log(`📊 价格范围: ${minPrice} - ${maxPrice}`);
      }
    });
  });

  test.describe('缓存行为测试', () => {
    test('应该支持适当的缓存机制', async () => {
      const endpoint = '/market-data/symbols';

      // 首次请求
      const firstResponse = await apiUtils.makeAPIRequest(endpoint);
      const firstData = await firstResponse.json();

      // 检查缓存头
      const cacheControl = firstResponse.headers.get('cache-control');
      if (cacheControl) {
        console.log(`📊 Cache-Control: ${cacheControl}`);
      }

      const etag = firstResponse.headers.get('etag');
      if (etag) {
        console.log(`📊 ETag: ${etag}`);

        // 使用ETag进行条件请求
        const secondResponse = await apiUtils.makeAPIRequest(endpoint, {
          headers: {
            'If-None-Match': etag
          }
        });

        // 如果数据未变化，应该返回304 Not Modified
        if (secondResponse.status === 304) {
          console.log('✅ 缓存机制正常工作');
        }
      }

      // 验证数据一致性
      const secondResponse = await apiUtils.makeAPIRequest(endpoint);
      const secondData = await secondResponse.json();
      expect(JSON.stringify(firstData)).toBe(JSON.stringify(secondData));
    });
  });
});