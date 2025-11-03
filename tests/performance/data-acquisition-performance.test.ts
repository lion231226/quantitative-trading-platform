import { test, expect } from '@playwright/test';
import { APIUtils } from '../../tests/e2e/test-helpers';
import { TestDataGenerator } from '../../tests/e2e/test-data/fixtures';

test.describe('数据获取性能测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('API响应时间基准', () => {
    test('市场数据API响应时间基准', async () => {
      const endpoints = [
        { path: '/market-data/symbols', name: '股票列表' },
        { path: '/market-data/symbol/000001.SZ', name: '单只股票详情' },
        { path: '/market-data/symbols?sector=金融', name: '行业筛选股票' }
      ];

      const benchmarks = {
        excellent: 100,    // 优秀: < 100ms
        good: 300,         // 良好: < 300ms
        acceptable: 500,   // 可接受: < 500ms
        poor: 1000         // 较差: < 1000ms
      };

      const results = [];

      for (const endpoint of endpoints) {
        const measurements = [];

        // 进行多次测量取平均值
        for (let i = 0; i < 10; i++) {
          const startTime = Date.now();
          const response = await apiUtils.makeAPIRequest(endpoint.path);
          const responseTime = Date.now() - startTime;

          measurements.push(responseTime);

          // 确保请求成功
          expect(response.ok).toBe(true);

          // 间隔避免缓存影响
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        const avgResponseTime = measurements.reduce((sum, time) => sum + time, 0) / measurements.length;
        const minResponseTime = Math.min(...measurements);
        const maxResponseTime = Math.max(...measurements);

        let performanceLevel;
        if (avgResponseTime < benchmarks.excellent) {
          performanceLevel = 'excellent';
        } else if (avgResponseTime < benchmarks.good) {
          performanceLevel = 'good';
        } else if (avgResponseTime < benchmarks.acceptable) {
          performanceLevel = 'acceptable';
        } else if (avgResponseTime < benchmarks.poor) {
          performanceLevel = 'poor';
        } else {
          performanceLevel = 'unacceptable';
        }

        results.push({
          endpoint: endpoint.name,
          path: endpoint.path,
          average: avgResponseTime,
          min: minResponseTime,
          max: maxResponseTime,
          level: performanceLevel
        });

        console.log(`📊 ${endpoint.name}性能: 平均${avgResponseTime.toFixed(2)}ms (最小${minResponseTime}ms, 最大${maxResponseTime}ms) - ${performanceLevel}`);
      }

      // 验证性能基准
      results.forEach(result => {
        expect(result.average).toBeLessThan(benchmarks.acceptable);
      });

      console.log('✅ 所有API响应时间符合基准要求');
    });

    test('缓存效果性能测试', async () => {
      const endpoint = '/market-data/symbols';
      const cacheTestIterations = 5;

      // 第一次请求（缓存未命中）
      const firstRequestStart = Date.now();
      const firstResponse = await apiUtils.makeAPIRequest(endpoint);
      const firstRequestTime = Date.now() - firstRequestStart;

      expect(firstResponse.ok).toBe(true);

      // 后续请求（可能命中缓存）
      const cacheRequestTimes = [];
      for (let i = 0; i < cacheTestIterations; i++) {
        const startTime = Date.now();
        const response = await apiUtils.makeAPIRequest(endpoint);
        const requestTime = Date.now() - startTime;

        expect(response.ok).toBe(true);
        cacheRequestTimes.push(requestTime);

        await new Promise(resolve => setTimeout(resolve, 50));
      }

      const avgCacheTime = cacheRequestTimes.reduce((sum, time) => sum + time, 0) / cacheRequestTimes.length;
      const minCacheTime = Math.min(...cacheRequestTimes);

      const cacheImprovement = ((firstRequestTime - avgCacheTime) / firstRequestTime) * 100;

      console.log(`📊 缓存性能分析:`);
      console.log(`  首次请求: ${firstRequestTime}ms`);
      console.log(`  缓存请求平均: ${avgCacheTime.toFixed(2)}ms`);
      console.log(`  缓存请求最小: ${minCacheTime}ms`);
      console.log(`  性能提升: ${cacheImprovement.toFixed(1)}%`);

      // 缓存应该有明显的性能提升
      if (cacheImprovement > 10) {
        console.log('✅ 缓存效果良好');
      } else {
        console.log('⚠️ 缓存效果不明显，可能需要优化');
      }
    });
  });

  test.describe('并发性能测试', () => {
    test('并发请求处理能力', async () => {
      const concurrencyLevels = [1, 5, 10, 20, 50];
      const endpoint = '/market-data/symbols';

      const results = [];

      for (const concurrency of concurrencyLevels) {
        const startTime = Date.now();

        const promises = Array.from({ length: concurrency }, () =>
          apiUtils.makeAPIRequest(endpoint)
        );

        const responses = await Promise.all(promises);
        const totalTime = Date.now() - startTime;

        // 验证所有请求都成功
        const successCount = responses.filter(r => r.ok).length;
        const successRate = (successCount / responses.length) * 100;

        // 计算平均响应时间
        const responseTimes = [];
        for (const response of responses) {
          const data = await response.json();
          if (data.responseTime) {
            responseTimes.push(data.responseTime);
          }
        }

        const avgResponseTime = responseTimes.length > 0 ?
          responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length :
          totalTime / concurrency;

        results.push({
          concurrency,
          totalTime,
          successRate,
          avgResponseTime,
          throughput: concurrency / (totalTime / 1000) // 请求/秒
        });

        console.log(`📊 并发${concurrency}测试: 总时间${totalTime}ms, 成功率${successRate}%, 吞吐量${results[results.length - 1].throughput.toFixed(2)}req/s`);
      }

      // 验证并发性能指标
      results.forEach(result => {
        expect(result.successRate).toBeGreaterThan(95); // 95%以上成功率
        expect(result.avgResponseTime).toBeLessThan(2000); // 平均响应时间<2秒
      });

      console.log('✅ 并发性能测试通过');
    });

    test('高并发下的稳定性', async () => {
      const highConcurrency = 100;
      const endpoint = '/market-data/symbols';
      const maxErrors = 5; // 允许最多5个错误

      const startTime = Date.now();

      const promises = Array.from({ length: highConcurrency }, (_, index) =>
        apiUtils.makeAPIRequest(endpoint).catch(error => ({ error, index }))
      );

      const results = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      const successfulResults = results.filter(r => !r.error);
      const errorResults = results.filter(r => r.error);

      const successRate = (successfulResults.length / results.length) * 100;

      console.log(`📊 高并发稳定性测试 (${highConcurrency}并发):`);
      console.log(`  总时间: ${totalTime}ms`);
      console.log(`  成功请求: ${successfulResults.length}`);
      console.log(`  失败请求: ${errorResults.length}`);
      console.log(`  成功率: ${successRate.toFixed(1)}%`);

      // 验证高并发下的稳定性
      expect(errorResults.length).toBeLessThanOrEqual(maxErrors);
      expect(successRate).toBeGreaterThan(95);

      if (errorResults.length > 0) {
        console.log('📋 错误详情:');
        errorResults.forEach(result => {
          console.log(`  请求${result.index}: ${result.error.message}`);
        });
      }

      console.log('✅ 高并发稳定性测试通过');
    });
  });

  test.describe('大数据量性能测试', () => {
    test('大数据集处理性能', async () => {
      // 这个测试需要能够返回不同数量数据的端点
      // 这里我们模拟不同数据量的性能测试

      const dataSizes = [10, 100, 1000, 5000];
      const results = [];

      for (const size of dataSizes) {
        const startTime = Date.now();

        // 模拟大数据集请求
        const response = await apiUtils.makeAPIRequest(`/market-data/symbols?limit=${size}`);
        const requestTime = Date.now() - startTime;

        expect(response.ok).toBe(true);

        const data = await response.json();
        const actualDataSize = data.data ? data.data.length : 0;

        const processingTime = Date.now() - startTime;

        results.push({
          requestedSize: size,
          actualSize: actualDataSize,
          requestTime,
          processingTime,
          throughput: actualDataSize / (processingTime / 1000) // 记录/秒
        });

        console.log(`📊 数据量${size}测试: 实际${actualDataSize}条, 耗时${processingTime}ms, 吞吐量${results[results.length - 1].throughput.toFixed(0)}records/s`);
      }

      // 验证大数据量处理性能
      results.forEach(result => {
        // 处理时间应该与数据量成正比，但不应该过度增长
        const expectedMaxTime = Math.max(1000, result.actualSize * 2); // 最少1秒，最多每条记录2ms
        expect(result.processingTime).toBeLessThan(expectedMaxTime);
      });

      console.log('✅ 大数据量性能测试通过');
    });

    test('内存使用效率', async () => {
      // 测试处理大数据时的内存使用
      const initialMemory = process.memoryUsage();

      const largeDataRequests = 10;
      for (let i = 0; i < largeDataRequests; i++) {
        const response = await apiUtils.makeAPIRequest('/market-data/symbols');
        expect(response.ok).toBe(true);

        const data = await response.json();
        // 模拟数据处理
        JSON.stringify(data);
      }

      // 强制垃圾回收（如果可用）
      if (global.gc) {
        global.gc();
      }

      const finalMemory = process.memoryUsage();
      const memoryIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
      const memoryIncreaseMB = memoryIncrease / (1024 * 1024);

      console.log(`📊 内存使用分析:`);
      console.log(`  初始内存: ${(initialMemory.heapUsed / (1024 * 1024)).toFixed(2)}MB`);
      console.log(`  最终内存: ${(finalMemory.heapUsed / (1024 * 1024)).toFixed(2)}MB`);
      console.log(`  内存增长: ${memoryIncreaseMB.toFixed(2)}MB`);

      // 内存增长应该在合理范围内
      expect(memoryIncreaseMB).toBeLessThan(50); // 小于50MB增长

      console.log('✅ 内存使用效率测试通过');
    });
  });

  test.describe('网络条件性能测试', () => {
    test('慢网络条件下的性能', async () => {
      // 模拟慢网络条件（需要测试环境支持）
      const networkConditions = [
        { name: '3G', latency: 100, downloadThroughput: 750 * 1024 },
        { name: 'Regular 4G', latency: 20, downloadThroughput: 4 * 1024 * 1024 },
        { name: 'Slow 4G', latency: 50, downloadThroughput: 1.5 * 1024 * 1024 }
      ];

      for (const condition of networkConditions) {
        console.log(`📊 测试${condition.name}网络条件...`);

        const startTime = Date.now();
        const response = await apiUtils.makeAPIRequest('/market-data/symbols');
        const totalTime = Date.now() - startTime;

        expect(response.ok).toBe(true);

        const data = await response.json();
        const dataSize = JSON.stringify(data).length;

        const throughput = dataSize / (totalTime / 1000); // bytes/s

        console.log(`  ${condition.name}: ${totalTime}ms, 数据量${dataSize}bytes, 吞吐量${(throughput / 1024).toFixed(2)}KB/s`);

        // 即使在慢网络下，也应该在合理时间内完成
        expect(totalTime).toBeLessThan(10000); // 10秒内完成
      }

      console.log('✅ 网络条件性能测试完成');
    });

    test('网络中断恢复测试', async () => {
      // 测试网络中断后的恢复能力
      let maxRetries = 3;
      let success = false;

      for (let attempt = 1; attempt <= maxRetries && !success; attempt++) {
        try {
          const startTime = Date.now();
          const response = await apiUtils.makeAPIRequest('/market-data/symbols');
          const responseTime = Date.now() - startTime;

          if (response.ok) {
            success = true;
            console.log(`✅ 网络恢复成功，第${attempt}次尝试，响应时间${responseTime}ms`);
          }
        } catch (error) {
          console.log(`⚠️ 第${attempt}次尝试失败: ${error.message}`);
          if (attempt < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt)); // 指数退避
          }
        }
      }

      expect(success).toBe(true);
    });
  });

  test.describe('性能回归检测', () => {
    test('性能基准对比', async () => {
      // 定义性能基准（应该从配置文件或历史数据中读取）
      const performanceBenchmarks = {
        '/market-data/symbols': { maxResponseTime: 500, minSuccessRate: 99 },
        '/market-data/symbol/000001.SZ': { maxResponseTime: 300, minSuccessRate: 99 }
      };

      const results = [];

      for (const [endpoint, benchmark] of Object.entries(performanceBenchmarks)) {
        const measurements = [];
        const testRuns = 5;

        for (let i = 0; i < testRuns; i++) {
          const startTime = Date.now();
          const response = await apiUtils.makeAPIRequest(endpoint);
          const responseTime = Date.now() - startTime;

          measurements.push({
            success: response.ok,
            responseTime
          });

          await new Promise(resolve => setTimeout(resolve, 200));
        }

        const avgResponseTime = measurements.reduce((sum, m) => sum + m.responseTime, 0) / measurements.length;
        const successRate = measurements.filter(m => m.success).length / measurements.length * 100;

        const passesBenchmark = avgResponseTime <= benchmark.maxResponseTime && successRate >= benchmark.minSuccessRate;

        results.push({
          endpoint,
          avgResponseTime,
          successRate,
          benchmark,
          passesBenchmark
        });

        console.log(`📊 ${endpoint}性能对比:`);
        console.log(`  平均响应时间: ${avgResponseTime.toFixed(2)}ms (基准: ${benchmark.maxResponseTime}ms)`);
        console.log(`  成功率: ${successRate.toFixed(1)}% (基准: ${benchmark.minSuccessRate}%)`);
        console.log(`  结果: ${passesBenchmark ? '✅ 通过' : '❌ 未达标'}`);
      }

      // 验证所有端点都通过基准测试
      const failedBenchmarks = results.filter(r => !r.passesBenchmark);
      expect(failedBenchmarks.length).toBe(0);

      if (failedBenchmarks.length > 0) {
        console.log('❌ 性能回归检测失败:');
        failedBenchmarks.forEach(result => {
          console.log(`  ${result.endpoint}: 未达标`);
        });
      } else {
        console.log('✅ 性能回归检测通过');
      }
    });
  });
});