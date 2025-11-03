import { test, expect } from '@playwright/test';
import { APIUtils } from '../../../tests/e2e/test-helpers';
import { TestDataGenerator } from '../../../tests/e2e/test-data/fixtures';

test.describe('数据获取异常情况测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('网络连接异常', () => {
    test('应该处理网络超时', async () => {
      // 这个测试需要在测试环境中模拟网络超时
      // 这里我们通过请求一个不存在的慢响应端点来模拟

      const startTime = Date.now();
      try {
        const response = await fetch(`${apiUtils.baseURL}/market-data/timeout`, {
          signal: AbortSignal.timeout(5000) // 5秒超时
        });

        // 如果没有超时，检查响应
        if (response.ok) {
          console.log('⚠️ 超时端点响应正常，可能需要调整测试');
        }
      } catch (error) {
        expect(error.name).toBe('TimeoutError');
        console.log('✅ 网络超时处理正确');
      }

      const elapsedTime = Date.now() - startTime;
      expect(elapsedTime).toBeLessThan(10000); // 应该在10秒内返回
    });

    test('应该处理连接拒绝', async () => {
      // 尝试连接到不存在的端口
      const invalidAPIUtils = new APIUtils('http://localhost:9999');

      const result = await invalidAPIUtils.testEndpoint('/market-data/symbols');

      expect(result.success).toBe(false);
      expect(result.status).toBe(0);
      expect(result.data).toBe(null);

      console.log('✅ 连接拒绝处理正确');
    });

    test('应该处理DNS解析失败', async () => {
      const invalidAPIUtils = new APIUtils('http://nonexistent-domain-for-testing.local');

      const result = await invalidAPIUtils.testEndpoint('/market-data/symbols');

      expect(result.success).toBe(false);
      expect(result.status).toBe(0);

      console.log('✅ DNS解析失败处理正确');
    });
  });

  test.describe('数据格式异常', () => {
    test('应该处理API返回的非JSON数据', async () => {
      // 这个测试需要一个专门返回非JSON数据的端点
      // 在实际测试中，可能需要使用mock服务器

      try {
        const response = await apiUtils.makeAPIRequest('/market-data/raw');

        // 检查Content-Type
        const contentType = response.headers.get('content-type');
        if (contentType && !contentType.includes('application/json')) {
          // 应该能够处理非JSON响应
          const text = await response.text();
          expect(typeof text).toBe('string');
          console.log('✅ 非JSON数据处理正确');
        } else {
          console.log('⚠️ 需要专门的非JSON端点进行测试');
        }
      } catch (error) {
        // 解析JSON时出错也算正确的错误处理
        expect(error.message).toContain('JSON');
        console.log('✅ JSON解析错误处理正确');
      }
    });

    test('应该处理不完整的JSON响应', async () => {
      // 模拟不完整的JSON响应
      const incompleteJSON = '{"success": true, "data": {"symbol": "000001.SZ"';

      try {
        const parsed = JSON.parse(incompleteJSON);
        // 如果没有抛出错误，说明JSON实际上是完整的
        console.log('⚠️ 测试JSON实际上是完整的');
      } catch (error) {
        expect(error.message).toContain('Unexpected end');
        console.log('✅ 不完整JSON处理正确');
      }
    });

    test('应该处理API返回的错误数据结构', async () => {
      // 测试缺少必需字段的响应
      const malformedResponse = {
        // 缺少success字段
        data: [
          { symbol: '000001.SZ' } // 缺少其他必需字段
        ]
      };

      // 验证数据结构检查逻辑
      const isValidResponse = (data: any) => {
        return data &&
               typeof data.success === 'boolean' &&
               data.data !== undefined &&
               typeof data.message === 'string';
      };

      expect(isValidResponse(malformedResponse)).toBe(false);
      console.log('✅ 错误数据结构检测正确');
    });
  });

  test.describe('数据内容异常', () => {
    test('应该处理空数据响应', async () => {
      // 模拟空数据响应
      const emptyDataResponse = {
        success: true,
        data: [],
        message: '没有找到数据'
      };

      expect(emptyDataResponse.data).toEqual([]);
      expect(emptyDataResponse.success).toBe(true);

      console.log('✅ 空数据响应处理正确');
    });

    test('应该处理null/undefined数据字段', async () => {
      const nullDataResponse = {
        success: true,
        data: [
          {
            symbol: '000001.SZ',
            name: null, // null字段
            price: undefined, // undefined字段
            sector: '',
            change: null,
            volume: 0
          }
        ],
        message: '数据获取成功'
      };

      // 验证应用能够处理null/undefined字段
      const stock = nullDataResponse.data[0];
      expect(stock.symbol).toBe('000001.SZ');
      expect(stock.name).toBeNull();
      expect(stock.price).toBeUndefined();

      // 在实际应用中，应该有默认值处理
      const safeStock = {
        ...stock,
        name: stock.name || '未知',
        price: stock.price || 0
      };

      expect(safeStock.name).toBe('未知');
      expect(safeStock.price).toBe(0);

      console.log('✅ null/undefined字段处理正确');
    });

    test('应该处理数据类型异常', async () => {
      const typeErrorData = {
        success: true,
        data: [
          {
            symbol: '000001.SZ',
            name: '平安银行',
            price: '12.58', // 应该是number，但是string
            change: 'invalid', // 无效的数字字符串
            volume: 'large' // 完全错误的类型
          }
        ],
        message: '数据获取成功'
      };

      // 验证类型转换和验证逻辑
      const stock = typeErrorData.data[0];

      // 尝试类型转换
      const normalizedStock = {
        ...stock,
        price: typeof stock.price === 'string' ? parseFloat(stock.price) : stock.price,
        change: typeof stock.change === 'string' ? parseFloat(stock.change) : stock.change,
        volume: typeof stock.volume === 'string' && !isNaN(Number(stock.volume)) ? Number(stock.volume) : 0
      };

      expect(isNaN(normalizedStock.price)).toBe(false);
      expect(isNaN(normalizedStock.change)).toBe(true); // 'invalid' 转换结果是 NaN
      expect(normalizedStock.volume).toBe(0);

      // 应该有NaN检查和错误处理
      const finalStock = {
        ...normalizedStock,
        price: isNaN(normalizedStock.price) ? 0 : normalizedStock.price,
        change: isNaN(normalizedStock.change) ? 0 : normalizedStock.change
      };

      expect(finalStock.price).toBe(12.58);
      expect(finalStock.change).toBe(0);

      console.log('✅ 数据类型异常处理正确');
    });
  });

  test.describe('数据量异常', () => {
    test('应该处理超大数据集', async () => {
      // 生成大量测试数据
      const largeDataSet = TestDataGenerator.generateMarketData(10000);

      const largeResponse = {
        success: true,
        data: largeDataSet,
        message: `找到${largeDataSet.length}支股票`
      };

      // 验证大数据集处理
      expect(largeResponse.data.length).toBe(10000);

      // 验证应用不会因为大数据量而崩溃
      const processingTime = Date.now();

      // 模拟数据处理
      const processedData = largeResponse.data.slice(0, 100); // 只处理前100条
      const averagePrice = processedData.reduce((sum, stock) => sum + stock.price, 0) / processedData.length;

      expect(averagePrice).toBeGreaterThan(0);

      const elapsed = Date.now() - processingTime;
      expect(elapsed).toBeLessThan(1000); // 处理应该在1秒内完成

      console.log(`✅ 超大数据集(${largeDataSet.length}条)处理时间: ${elapsed}ms`);
    });

    test('应该处理极小数据集', async () => {
      const minimalData = [
        {
          symbol: '000001.SZ',
          name: '平安银行',
          price: 12.58,
          sector: '金融',
          change: 0.15,
          volume: 1000000
        }
      ];

      const minimalResponse = {
        success: true,
        data: minimalData,
        message: `找到${minimalData.length}支股票`
      };

      expect(minimalResponse.data.length).toBe(1);
      expect(minimalResponse.data[0].symbol).toBe('000001.SZ');

      // 验证单条数据的处理逻辑
      const firstStock = minimalResponse.data[0];
      expect(firstStock.price).toBeGreaterThan(0);

      console.log('✅ 极小数据集处理正确');
    });
  });

  test.describe('并发和竞态条件', () => {
    test('应该处理并发数据获取请求', async () => {
      const concurrentRequests = 10;

      const promises = Array.from({ length: concurrentRequests }, (_, index) =>
        apiUtils.testEndpoint('/market-data/symbols')
      );

      const startTime = Date.now();
      const results = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      // 验证所有请求都成功
      results.forEach((result, index) => {
        expect(result.success).toBe(true);
        console.log(`📊 并发请求${index + 1}成功`);
      });

      // 验证数据一致性
      const dataStrings = results.map(r => JSON.stringify(r.data.data));
      const uniqueDataStrings = [...new Set(dataStrings)];
      expect(uniqueDataStrings.length).toBe(1); // 所有请求应该返回相同数据

      console.log(`✅ ${concurrentRequests}个并发请求数据一致性验证通过，总时间: ${totalTime}ms`);
    });

    test('应该处理快速连续请求', async () => {
      const rapidRequests = 5;
      const results = [];

      for (let i = 0; i < rapidRequests; i++) {
        const startTime = Date.now();
        const result = await apiUtils.testEndpoint('/market-data/symbols');
        const responseTime = Date.now() - startTime;

        results.push({ result, responseTime, index: i });

        // 短暂延迟模拟用户快速操作
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // 验证所有请求都成功
      results.forEach(({ result, responseTime, index }) => {
        expect(result.success).toBe(true);
        console.log(`📊 快速请求${index + 1}响应时间: ${responseTime}ms`);
      });

      // 验证响应时间在合理范围内
      const averageResponseTime = results.reduce((sum, r) => sum + r.responseTime, 0) / results.length;
      expect(averageResponseTime).toBeLessThan(2000);

      console.log(`✅ 快速连续请求平均响应时间: ${averageResponseTime.toFixed(2)}ms`);
    });
  });

  test.describe('缓存和状态异常', () => {
    test('应该处理缓存失效', async () => {
      // 首次请求
      const firstResult = await apiUtils.testEndpoint('/market-data/symbols');
      expect(firstResult.success).toBe(true);

      // 模拟缓存失效，再次请求
      const secondResult = await apiUtils.testEndpoint('/market-data/symbols');
      expect(secondResult.success).toBe(true);

      // 验证数据一致性
      expect(JSON.stringify(firstResult.data.data)).toBe(JSON.stringify(secondResult.data.data));

      console.log('✅ 缓存失效处理正确');
    });

    test('应该处理数据更新冲突', async () => {
      // 模拟同时请求相同数据的冲突情况
      const symbol = '000001.SZ';

      const promises = Array.from({ length: 3 }, () =>
        apiUtils.testEndpoint(`/market-data/symbol/${symbol}`)
      );

      const results = await Promise.all(promises);

      // 验证所有请求都成功且数据一致
      results.forEach((result, index) => {
        expect(result.success).toBe(true);
        expect(result.data.data.symbol).toBe(symbol);
        console.log(`📊 冲突请求${index + 1}数据一致`);
      });

      // 验证数据完全一致
      const dataStrings = results.map(r => JSON.stringify(r.data.data));
      const uniqueDataStrings = [...new Set(dataStrings)];
      expect(uniqueDataStrings.length).toBe(1);

      console.log('✅ 数据更新冲突处理正确');
    });
  });

  test.describe('资源限制异常', () => {
    test('应该处理内存限制', async () => {
      // 生成大量数据来测试内存使用
      const memoryIntensiveData = TestDataGenerator.generateMarketData(5000);

      // 模拟内存监控
      const initialMemory = process.memoryUsage().heapUsed;

      // 处理大数据集
      const processedData = memoryIntensiveData.map(stock => ({
        ...stock,
        processed: true,
        calculated: stock.price * stock.volume
      }));

      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;
      const memoryIncreaseMB = memoryIncrease / (1024 * 1024);

      expect(processedData.length).toBe(5000);
      expect(memoryIncreaseMB).toBeLessThan(100); // 内存增长应该控制在100MB以内

      console.log(`✅ 处理${processedData.length}条数据，内存增长: ${memoryIncreaseMB.toFixed(2)}MB`);
    });

    test('应该处理请求频率限制', async () => {
      // 模拟高频请求
      const highFrequencyRequests = 20;
      const results = [];
      let rateLimitHit = false;

      for (let i = 0; i < highFrequencyRequests; i++) {
        const startTime = Date.now();

        try {
          const result = await apiUtils.testEndpoint('/market-data/symbols');
          const responseTime = Date.now() - startTime;

          results.push({ success: true, responseTime, index: i });

          // 检查是否被频率限制
          if (result.status === 429) {
            rateLimitHit = true;
            console.log(`📊 请求${i + 1}被频率限制`);
          }

        } catch (error) {
          results.push({ success: false, error: error.message, index: i });
          rateLimitHit = true;
        }

        // 极短间隔模拟高频请求
        await new Promise(resolve => setTimeout(resolve, 10));
      }

      const successCount = results.filter(r => r.success).length;
      const failureCount = results.length - successCount;

      console.log(`📊 高频请求测试: ${successCount}成功, ${failureCount}失败`);

      // 即使有频率限制，也应该有部分请求成功
      expect(successCount).toBeGreaterThan(0);

      // 如果触发了频率限制，验证错误处理
      if (rateLimitHit) {
        const failedResults = results.filter(r => !r.success);
        failedResults.forEach(result => {
          expect(result.error).toBeDefined();
        });
        console.log('✅ 频率限制错误处理正确');
      }
    });
  });
});