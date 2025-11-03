import { test, expect } from '@playwright/test';
import { APIUtils } from '../../tests/e2e/test-helpers';
import { TestDataGenerator } from '../../tests/e2e/test-data/fixtures';

test.describe('策略计算性能测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('基础策略计算性能', () => {
    test('标准双均线策略性能基准', async () => {
      const standardConfigs = [
        { shortWindow: 5, longWindow: 20, name: '短期策略' },
        { shortWindow: 10, longWindow: 30, name: '中期策略' },
        { shortWindow: 20, longWindow: 60, name: '长期策略' }
      ];

      const results = [];

      for (const config of standardConfigs) {
        const strategyRequest = {
          symbol: '000001.SZ',
          shortWindow: config.shortWindow,
          longWindow: config.longWindow,
          initialCapital: 100000
        };

        const measurements = [];

        // 进行多次测试取平均值
        for (let i = 0; i < 3; i++) {
          const startTime = Date.now();
          const response = await apiUtils.makeAPIRequest('/strategies/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(strategyRequest)
          });
          const executionTime = Date.now() - startTime;

          expect(response.ok).toBe(true);

          const data = await response.json();
          expect(data.success).toBe(true);

          measurements.push({
            executionTime,
            totalReturn: data.data.totalReturn,
            sharpeRatio: data.data.sharpeRatio
          });

          // 间隔避免资源竞争
          await new Promise(resolve => setTimeout(resolve, 500));
        }

        const avgExecutionTime = measurements.reduce((sum, m) => sum + m.executionTime, 0) / measurements.length;
        const avgTotalReturn = measurements.reduce((sum, m) => sum + m.totalReturn, 0) / measurements.length;
        const avgSharpeRatio = measurements.reduce((sum, m) => sum + m.sharpeRatio, 0) / measurements.length;

        results.push({
          name: config.name,
          shortWindow: config.shortWindow,
          longWindow: config.longWindow,
          avgExecutionTime,
          avgTotalReturn,
          avgSharpeRatio
        });

        console.log(`📊 ${config.name}性能:`);
        console.log(`  平均执行时间: ${avgExecutionTime.toFixed(2)}ms`);
        console.log(`  平均总收益: ${avgTotalReturn.toFixed(2)}%`);
        console.log(`  平均夏普比率: ${avgSharpeRatio.toFixed(2)}`);

        // 性能基准验证
        expect(avgExecutionTime).toBeLessThan(15000); // 15秒内完成
      }

      // 验证策略复杂度与执行时间的关系
      const sortedByComplexity = results.sort((a, b) => (a.shortWindow + a.longWindow) - (b.shortWindow + b.longWindow));
      const executionTimes = sortedByComplexity.map(r => r.avgExecutionTime);

      // 执行时间应该随着复杂度合理增长
      for (let i = 1; i < executionTimes.length; i++) {
        const growthRatio = executionTimes[i] / executionTimes[i - 1];
        expect(growthRatio).toBeLessThan(3); // 增长不超过3倍
      }

      console.log('✅ 标准策略性能基准测试通过');
    });

    test('不同股票的策略计算性能', async () => {
      const stocks = [
        '000001.SZ', // 平安银行
        '000002.SZ', // 万科A
        '000858.SZ', // 五粮液
        '600036.SH', // 招商银行
        '600519.SH'  // 贵州茅台
      ];

      const strategyConfig = {
        shortWindow: 5,
        longWindow: 20,
        initialCapital: 100000
      };

      const results = [];

      for (const symbol of stocks) {
        const request = {
          symbol,
          ...strategyConfig
        };

        const startTime = Date.now();
        const response = await apiUtils.makeAPIRequest('/strategies/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request)
        });
        const executionTime = Date.now() - startTime;

        expect(response.ok).toBe(true);

        const data = await response.json();
        expect(data.success).toBe(true);

        results.push({
          symbol,
          executionTime,
          totalReturn: data.data.totalReturn,
          tradeCount: data.data.tradeCount || 0
        });

        console.log(`📊 ${symbol}策略计算: ${executionTime}ms, 收益${data.data.totalReturn}%`);

        // 性能应该在合理范围内
        expect(executionTime).toBeLessThan(20000); // 20秒内完成
      }

      // 分析不同股票的性能差异
      const avgExecutionTime = results.reduce((sum, r) => sum + r.executionTime, 0) / results.length;
      const maxExecutionTime = Math.max(...results.map(r => r.executionTime));
      const minExecutionTime = Math.min(...results.map(r => r.executionTime));

      console.log(`📈 股票策略性能分析:`);
      console.log(`  平均执行时间: ${avgExecutionTime.toFixed(2)}ms`);
      console.log(`  最大执行时间: ${maxExecutionTime}ms`);
      console.log(`  最小执行时间: ${minExecutionTime}ms`);
      console.log(`  性能差异: ${((maxExecutionTime - minExecutionTime) / minExecutionTime * 100).toFixed(1)}%`);

      // 性能差异不应该过大
      expect((maxExecutionTime - minExecutionTime) / minExecutionTime).toBeLessThan(2); // 差异不超过2倍

      console.log('✅ 不同股票策略计算性能测试通过');
    });
  });

  test.describe('复杂策略性能测试', () => {
    test('长时间窗口策略性能', async () => {
      const longTermConfigs = [
        { shortWindow: 30, longWindow: 90, name: '季度策略' },
        { shortWindow: 60, longWindow: 180, name: '半年策略' },
        { shortWindow: 120, longWindow: 360, name: '年度策略' }
      ];

      for (const config of longTermConfigs) {
        const strategyRequest = {
          symbol: '000001.SZ',
          shortWindow: config.shortWindow,
          longWindow: config.longWindow,
          initialCapital: 100000
        };

        console.log(`📊 测试${config.name} (${config.shortWindow}-${config.longWindow})...`);

        const startTime = Date.now();
        const response = await apiUtils.makeAPIRequest('/strategies/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(strategyRequest)
        });
        const executionTime = Date.now() - startTime;

        expect(response.ok).toBe(true);

        const data = await response.json();
        expect(data.success).toBe(true);

        console.log(`  执行时间: ${executionTime}ms`);
        console.log(`  总收益: ${data.data.totalReturn}%`);
        console.log(`  夏普比率: ${data.data.sharpeRatio}`);

        // 长时间策略允许更长的执行时间，但仍有上限
        const maxAllowedTime = Math.max(30000, config.longWindow * 50); // 至少30秒，每期最多50ms
        expect(executionTime).toBeLessThan(maxAllowedTime);

        // 验证结果的合理性
        expect(data.data.totalReturn).toBeDefined();
        expect(typeof data.data.totalReturn).toBe('number');
        expect(isFinite(data.data.totalReturn)).toBe(true);
      }

      console.log('✅ 长时间窗口策略性能测试通过');
    });

    test('大资金策略计算性能', async () => {
      const capitalSizes = [
        { amount: 100000, name: '10万资金' },
        { amount: 1000000, name: '100万资金' },
        { amount: 10000000, name: '1000万资金' },
        { amount: 100000000, name: '1亿资金' }
      ];

      const baseStrategyConfig = {
        symbol: '000001.SZ',
        shortWindow: 5,
        longWindow: 20
      };

      for (const capital of capitalSizes) {
        const strategyRequest = {
          ...baseStrategyConfig,
          initialCapital: capital.amount
        };

        console.log(`📊 测试${capital.name}...`);

        const startTime = Date.now();
        const response = await apiUtils.makeAPIRequest('/strategies/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(strategyRequest)
        });
        const executionTime = Date.now() - startTime;

        expect(response.ok).toBe(true);

        const data = await response.json();
        expect(data.success).toBe(true);

        console.log(`  执行时间: ${executionTime}ms`);
        console.log(`  总收益: ${data.data.totalReturn}%`);
        console.log(`  绝对收益: ${(data.data.totalReturn * capital.amount / 100).toLocaleString()}元`);

        // 资金大小不应该显著影响计算时间
        expect(executionTime).toBeLessThan(25000); // 25秒内完成

        // 验证大资金计算的精度
        expect(data.data.totalReturn).toBeDefined();
        expect(isFinite(data.data.totalReturn)).toBe(true);
        expect(data.data.totalReturn).toBeGreaterThan(-100); // 最大损失不超过100%
      }

      console.log('✅ 大资金策略计算性能测试通过');
    });
  });

  test.describe('并发策略计算性能', () => {
    test('多策略并发计算性能', async () => {
      const concurrentStrategies = [
        { symbol: '000001.SZ', shortWindow: 5, longWindow: 20 },
        { symbol: '000002.SZ', shortWindow: 10, longWindow: 30 },
        { symbol: '000858.SZ', shortWindow: 8, longWindow: 25 },
        { symbol: '600036.SH', shortWindow: 12, longWindow: 35 },
        { symbol: '600519.SH', shortWindow: 15, longWindow: 45 }
      ];

      const initialCapital = 100000;

      console.log(`📊 测试${concurrentStrategies.length}个策略并发计算...`);

      const startTime = Date.now();

      const promises = concurrentStrategies.map(async (strategy, index) => {
        const strategyRequest = {
          ...strategy,
          initialCapital
        };

        const requestStart = Date.now();
        const response = await apiUtils.makeAPIRequest('/strategies/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(strategyRequest)
        });
        const requestTime = Date.now() - requestStart;

        expect(response.ok).toBe(true);

        const data = await response.json();
        expect(data.success).toBe(true);

        return {
          index,
          symbol: strategy.symbol,
          requestTime,
          totalReturn: data.data.totalReturn,
          sharpeRatio: data.data.sharpeRatio
        };
      });

      const results = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      console.log(`📈 并发计算结果:`);
      console.log(`  总执行时间: ${totalTime}ms`);
      console.log(`  平均每策略: ${(totalTime / results.length).toFixed(2)}ms`);

      results.forEach(result => {
        console.log(`  策略${result.index + 1}(${result.symbol}): ${result.requestTime}ms, 收益${result.totalReturn}%`);
      });

      // 验证并发效率
      const avgIndividualTime = results.reduce((sum, r) => sum + r.requestTime, 0) / results.length;
      const concurrencyEfficiency = avgIndividualTime / (totalTime / results.length);

      console.log(`  并发效率: ${concurrencyEfficiency.toFixed(2)}x`);

      // 所有策略都应该在合理时间内完成
      results.forEach(result => {
        expect(result.requestTime).toBeLessThan(30000); // 30秒内完成
      });

      // 总时间不应该过长
      expect(totalTime).toBeLessThan(60000); // 60秒内完成所有策略

      console.log('✅ 多策略并发计算性能测试通过');
    });

    test('相同策略并发计算一致性', async () => {
      const identicalStrategy = {
        symbol: '000001.SZ',
        shortWindow: 5,
        longWindow: 20,
        initialCapital: 100000
      };

      const concurrentCount = 5;

      console.log(`📊 测试${concurrentCount}个相同策略并发计算一致性...`);

      const promises = Array.from({ length: concurrentCount }, () =>
        apiUtils.makeAPIRequest('/strategies/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(identicalStrategy)
        })
      );

      const responses = await Promise.all(promises);
      const results = await Promise.all(responses.map(r => r.json()));

      // 验证所有请求都成功
      results.forEach((data, index) => {
        expect(data.success).toBe(true);
        console.log(`  策略${index + 1}: 收益${data.data.totalReturn}%, 夏普${data.data.sharpeRatio}`);
      });

      // 验证结果的一致性
      const totalReturns = results.map(r => r.data.totalReturn);
      const sharpeRatios = results.map(r => r.data.sharpeRatio);

      const maxReturnDiff = Math.max(...totalReturns) - Math.min(...totalReturns);
      const maxSharpeDiff = Math.max(...sharpeRatios) - Math.min(...sharpeRatios);

      console.log(`  收益最大差异: ${maxReturnDiff.toFixed(4)}%`);
      console.log(`  夏普比率最大差异: ${maxSharpeDiff.toFixed(4)}`);

      // 结果应该高度一致（差异很小）
      expect(maxReturnDiff).toBeLessThan(0.01); // 收益差异小于0.01%
      expect(maxSharpeDiff).toBeLessThan(0.01); // 夏普比率差异小于0.01

      console.log('✅ 相同策略并发计算一致性测试通过');
    });
  });

  test.describe('性能优化验证', () => {
    test('缓存策略计算结果', async () => {
      const strategyConfig = {
        symbol: '000001.SZ',
        shortWindow: 5,
        longWindow: 20,
        initialCapital: 100000
      };

      // 第一次计算
      console.log('📊 测试策略计算缓存...');
      const firstStart = Date.now();
      const firstResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(strategyConfig)
      });
      const firstTime = Date.now() - firstStart;

      expect(firstResponse.ok).toBe(true);
      const firstData = await firstResponse.json();
      expect(firstData.success).toBe(true);

      // 等待一段时间
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 第二次计算相同策略
      const secondStart = Date.now();
      const secondResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(strategyConfig)
      });
      const secondTime = Date.now() - secondStart;

      expect(secondResponse.ok).toBe(true);
      const secondData = await secondResponse.json();
      expect(secondData.success).toBe(true);

      // 比较结果
      const speedImprovement = ((firstTime - secondTime) / firstTime) * 100;
      const resultsMatch = JSON.stringify(firstData.data) === JSON.stringify(secondData.data);

      console.log(`  首次计算: ${firstTime}ms`);
      console.log(`  二次计算: ${secondTime}ms`);
      console.log(`  性能提升: ${speedImprovement.toFixed(1)}%`);
      console.log(`  结果一致性: ${resultsMatch ? '✅ 一致' : '❌ 不一致'}`);

      // 验证结果一致性
      expect(resultsMatch).toBe(true);

      // 如果有缓存，应该有性能提升
      if (secondTime < firstTime) {
        console.log('✅ 策略计算缓存正常工作');
      } else {
        console.log('ℹ️ 未检测到缓存效果（可能未实现缓存或缓存时间过短）');
      }
    });

    test('增量计算性能', async () => {
      // 测试增量更新的性能（如果有实现）
      const baseStrategy = {
        symbol: '000001.SZ',
        shortWindow: 5,
        longWindow: 20,
        initialCapital: 100000,
        startDate: '2023-01-01',
        endDate: '2023-12-31'
      };

      const extendedStrategy = {
        ...baseStrategy,
        endDate: '2024-01-31' // 延长一个月
      };

      console.log('📊 测试增量计算性能...');

      // 计算基础策略
      const baseStart = Date.now();
      const baseResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(baseStrategy)
      });
      const baseTime = Date.now() - baseStart;

      expect(baseResponse.ok).toBe(true);
      const baseData = await baseResponse.json();
      expect(baseData.success).toBe(true);

      // 计算扩展策略
      const extendedStart = Date.now();
      const extendedResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(extendedStrategy)
      });
      const extendedTime = Date.now() - extendedStart;

      expect(extendedResponse.ok).toBe(true);
      const extendedData = await extendedResponse.json();
      expect(extendedData.success).toBe(true);

      console.log(`  基础计算: ${baseTime}ms`);
      console.log(`  扩展计算: ${extendedTime}ms`);

      // 如果有增量计算，扩展计算应该比完整重新计算快
      if (extendedTime < baseTime) {
        const improvement = ((baseTime - extendedTime) / baseTime) * 100;
        console.log(`  增量计算提升: ${improvement.toFixed(1)}%`);
        console.log('✅ 检测到增量计算优化');
      } else {
        console.log('ℹ️ 未检测到增量计算（可能未实现）');
      }

      // 两种计算都应该在合理时间内完成
      expect(baseTime).toBeLessThan(30000);
      expect(extendedTime).toBeLessThan(30000);
    });
  });

  test.describe('性能监控和报告', () => {
    test('性能指标收集', async () => {
      const strategyConfig = {
        symbol: '000001.SZ',
        shortWindow: 5,
        longWindow: 20,
        initialCapital: 100000
      };

      console.log('📊 收集策略计算性能指标...');

      const startTime = Date.now();
      const response = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(strategyConfig)
      });
      const executionTime = Date.now() - startTime;

      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(data.success).toBe(true);

      // 检查响应中是否包含性能指标
      const performanceMetrics = {
        executionTime,
        serverResponseTime: data.responseTime || executionTime,
        dataPointsProcessed: data.dataPointsCount || 'unknown',
        calculationSteps: data.calculationSteps || 'unknown',
        memoryUsage: data.memoryUsage || 'unknown'
      };

      console.log('📈 性能指标:');
      Object.entries(performanceMetrics).forEach(([key, value]) => {
        console.log(`  ${key}: ${value}`);
      });

      // 验证基本性能指标
      expect(executionTime).toBeGreaterThan(0);
      expect(executionTime).toBeLessThan(30000);

      console.log('✅ 性能指标收集完成');
    });

    test('性能基准对比', async () => {
      // 定义性能基准
      const performanceBenchmarks = {
        simpleStrategy: { maxTime: 10000, name: '简单策略' },
        complexStrategy: { maxTime: 30000, name: '复杂策略' },
        concurrentStrategies: { maxTimePerStrategy: 15000, name: '并发策略' }
      };

      console.log('📊 执行性能基准对比...');

      // 简单策略基准测试
      const simpleStrategy = {
        symbol: '000001.SZ',
        shortWindow: 5,
        longWindow: 20,
        initialCapital: 100000
      };

      const simpleStart = Date.now();
      const simpleResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(simpleStrategy)
      });
      const simpleTime = Date.now() - simpleStart;

      expect(simpleResponse.ok).toBe(true);
      expect(simpleTime).toBeLessThan(performanceBenchmarks.simpleStrategy.maxTime);

      console.log(`✅ ${performanceBenchmarks.simpleStrategy.name}: ${simpleTime}ms < ${performanceBenchmarks.simpleStrategy.maxTime}ms`);

      // 复杂策略基准测试
      const complexStrategy = {
        symbol: '000001.SZ',
        shortWindow: 30,
        longWindow: 120,
        initialCapital: 1000000
      };

      const complexStart = Date.now();
      const complexResponse = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(complexStrategy)
      });
      const complexTime = Date.now() - complexStart;

      expect(complexResponse.ok).toBe(true);
      expect(complexTime).toBeLessThan(performanceBenchmarks.complexStrategy.maxTime);

      console.log(`✅ ${performanceBenchmarks.complexStrategy.name}: ${complexTime}ms < ${performanceBenchmarks.complexStrategy.maxTime}ms`);

      console.log('✅ 所有性能基准测试通过');
    });
  });
});