import { test, expect } from '@playwright/test';
import { APIUtils } from '../../tests/e2e/test-helpers';
import { TestDataGenerator } from '../../tests/e2e/test-data/fixtures';

test.describe('并发负载测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('API负载测试', () => {
    test('市场数据API负载测试', async () => {
      const loadLevels = [
        { users: 1, duration: 10000, name: '单用户基准' },
        { users: 5, duration: 10000, name: '5用户并发' },
        { users: 10, duration: 10000, name: '10用户并发' },
        { users: 20, duration: 10000, name: '20用户并发' },
        { users: 50, duration: 10000, name: '50用户并发' }
      ];

      const endpoint = '/market-data/symbols';

      for (const loadLevel of loadLevels) {
        console.log(`📊 执行${loadLevel.name}负载测试 (${loadLevel.users}用户, ${loadLevel.duration}ms)...`);

        const results = {
          totalRequests: 0,
          successfulRequests: 0,
          failedRequests: 0,
          responseTimes: [],
          errors: []
        };

        const startTime = Date.now();
        const endTime = startTime + loadLevel.duration;

        // 创建并发用户
        const userPromises = Array.from({ length: loadLevel.users }, async (_, userIndex) => {
          let requestCount = 0;

          while (Date.now() < endTime) {
            const requestStart = Date.now();

            try {
              const response = await apiUtils.makeAPIRequest(endpoint);
              const responseTime = Date.now() - requestStart;

              results.totalRequests++;
              requestCount++;

              if (response.ok) {
                results.successfulRequests++;
                results.responseTimes.push(responseTime);
              } else {
                results.failedRequests++;
                results.errors.push(`用户${userIndex}: HTTP ${response.status}`);
              }

            } catch (error) {
              results.totalRequests++;
              results.failedRequests++;
              results.errors.push(`用户${userIndex}: ${error.message}`);
            }

            // 用户间隔时间
            await new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 400));
          }

          return requestCount;
        });

        const userRequestCounts = await Promise.all(userPromises);
        const actualTestDuration = Date.now() - startTime;

        // 计算统计数据
        const successRate = (results.successfulRequests / results.totalRequests) * 100;
        const avgResponseTime = results.responseTimes.length > 0 ?
          results.responseTimes.reduce((sum, time) => sum + time, 0) / results.responseTimes.length : 0;
        const maxResponseTime = results.responseTimes.length > 0 ? Math.max(...results.responseTimes) : 0;
        const minResponseTime = results.responseTimes.length > 0 ? Math.min(...results.responseTimes) : 0;
        const p95ResponseTime = results.responseTimes.length > 0 ?
          results.responseTimes.sort((a, b) => a - b)[Math.floor(results.responseTimes.length * 0.95)] : 0;
        const requestsPerSecond = results.totalRequests / (actualTestDuration / 1000);

        console.log(`📈 ${loadLevel.name}测试结果:`);
        console.log(`  实际测试时间: ${actualTestDuration}ms`);
        console.log(`  总请求数: ${results.totalRequests}`);
        console.log(`  成功请求: ${results.successfulRequests}`);
        console.log(`  失败请求: ${results.failedRequests}`);
        console.log(`  成功率: ${successRate.toFixed(1)}%`);
        console.log(`  平均响应时间: ${avgResponseTime.toFixed(2)}ms`);
        console.log(`  最小响应时间: ${minResponseTime}ms`);
        console.log(`  最大响应时间: ${maxResponseTime}ms`);
        console.log(`  95%响应时间: ${p95ResponseTime}ms`);
        console.log(`  RPS: ${requestsPerSecond.toFixed(2)}`);

        // 每个用户的请求分布
        console.log(`  用户请求分布: ${userRequestCounts.join(', ')}`);

        // 性能基准验证
        expect(successRate).toBeGreaterThan(95); // 成功率>95%
        expect(avgResponseTime).toBeLessThan(2000); // 平均响应时间<2秒
        expect(p95ResponseTime).toBeLessThan(5000); // 95%响应时间<5秒

        if (results.failedRequests > 0) {
          console.log(`  错误详情: ${results.errors.slice(0, 5).join(', ')}${results.errors.length > 5 ? '...' : ''}`);
        }

        console.log(`✅ ${loadLevel.name}负载测试通过`);
      }
    });

    test('策略运行API负载测试', async () => {
      const loadLevels = [
        { users: 1, duration: 15000, name: '单用户策略' },
        { users: 3, duration: 15000, name: '3用户策略' },
        { users: 5, duration: 15000, name: '5用户策略' }
      ];

      for (const loadLevel of loadLevels) {
        console.log(`📊 执行${loadLevel.name}负载测试...`);

        const results = {
          totalRequests: 0,
          successfulRequests: 0,
          failedRequests: 0,
          responseTimes: [],
          totalReturns: [],
          errors: []
        };

        const startTime = Date.now();
        const endTime = startTime + loadLevel.duration;

        // 创建并发策略运行用户
        const userPromises = Array.from({ length: loadLevel.users }, async (_, userIndex) => {
          let requestCount = 0;

          while (Date.now() < endTime) {
            const strategyConfig = TestDataGenerator.generateStrategyConfig();

            const requestStart = Date.now();

            try {
              const response = await apiUtils.makeAPIRequest('/strategies/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(strategyConfig)
              });
              const responseTime = Date.now() - requestStart;

              results.totalRequests++;
              requestCount++;

              if (response.ok) {
                const data = await response.json();
                if (data.success) {
                  results.successfulRequests++;
                  results.responseTimes.push(responseTime);
                  results.totalReturns.push(data.data.totalReturn);
                } else {
                  results.failedRequests++;
                  results.errors.push(`用户${userIndex}: ${data.message}`);
                }
              } else {
                results.failedRequests++;
                results.errors.push(`用户${userIndex}: HTTP ${response.status}`);
              }

            } catch (error) {
              results.totalRequests++;
              results.failedRequests++;
              results.errors.push(`用户${userIndex}: ${error.message}`);
            }

            // 策略运行间隔较长
            await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));
          }

          return requestCount;
        });

        const userRequestCounts = await Promise.all(userPromises);
        const actualTestDuration = Date.now() - startTime;

        // 计算统计数据
        const successRate = (results.successfulRequests / results.totalRequests) * 100;
        const avgResponseTime = results.responseTimes.length > 0 ?
          results.responseTimes.reduce((sum, time) => sum + time, 0) / results.responseTimes.length : 0;
        const maxResponseTime = results.responseTimes.length > 0 ? Math.max(...results.responseTimes) : 0;
        const p95ResponseTime = results.responseTimes.length > 0 ?
          results.responseTimes.sort((a, b) => a - b)[Math.floor(results.responseTimes.length * 0.95)] : 0;
        const avgReturn = results.totalReturns.length > 0 ?
          results.totalReturns.reduce((sum, ret) => sum + ret, 0) / results.totalReturns.length : 0;

        console.log(`📈 ${loadLevel.name}测试结果:`);
        console.log(`  实际测试时间: ${actualTestDuration}ms`);
        console.log(`  总策略数: ${results.totalRequests}`);
        console.log(`  成功策略: ${results.successfulRequests}`);
        console.log(`  失败策略: ${results.failedRequests}`);
        console.log(`  成功率: ${successRate.toFixed(1)}%`);
        console.log(`  平均响应时间: ${avgResponseTime.toFixed(2)}ms`);
        console.log(`  最大响应时间: ${maxResponseTime}ms`);
        console.log(`  95%响应时间: ${p95ResponseTime}ms`);
        console.log(`  平均收益: ${avgReturn.toFixed(2)}%`);
        console.log(`  用户策略分布: ${userRequestCounts.join(', ')}`);

        // 策略运行性能基准
        expect(successRate).toBeGreaterThan(90); // 策略运行成功率>90%
        expect(avgResponseTime).toBeLessThan(30000); // 平均响应时间<30秒
        expect(p95ResponseTime).toBeLessThan(60000); // 95%响应时间<60秒

        console.log(`✅ ${loadLevel.name}负载测试通过`);
      }
    });
  });

  test.describe('压力测试', () => {
    test('极限并发压力测试', async () => {
      const maxConcurrency = 100;
      const testDuration = 30000; // 30秒

      console.log(`📊 执行极限并发压力测试 (${maxConcurrency}并发, ${testDuration}ms)...`);

      const results = {
        totalRequests: 0,
        successfulRequests: 0,
        failedRequests: 0,
        responseTimes: [],
        errors: new Map(),
        timeline: []
      };

      const startTime = Date.now();
      const endTime = startTime + testDuration;

      // 创建大量并发用户
      const userPromises = Array.from({ length: maxConcurrency }, async (_, userIndex) => {
        let requestCount = 0;

        while (Date.now() < endTime) {
          const requestStart = Date.now();

          try {
            // 混合不同类型的请求
            const endpoints = ['/market-data/symbols', '/market-data/symbol/000001.SZ'];
            const endpoint = endpoints[userIndex % endpoints.length];

            const response = await apiUtils.makeAPIRequest(endpoint);
            const responseTime = Date.now() - requestStart;

            results.totalRequests++;
            requestCount++;

            if (response.ok) {
              results.successfulRequests++;
              results.responseTimes.push(responseTime);
            } else {
              results.failedRequests++;
              const errorKey = `HTTP ${response.status}`;
              results.errors.set(errorKey, (results.errors.get(errorKey) || 0) + 1);
            }

          } catch (error) {
            results.totalRequests++;
            results.failedRequests++;
            const errorKey = error.message.substring(0, 50);
            results.errors.set(errorKey, (results.errors.get(errorKey) || 0) + 1);
          }

          // 高频率请求
          await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 150));

          // 记录时间线数据
          if (requestCount % 10 === 0) {
            results.timeline.push({
              timestamp: Date.now() - startTime,
              userIndex,
              requestCount,
              successRate: (results.successfulRequests / results.totalRequests) * 100
            });
          }
        }

        return requestCount;
      });

      const userRequestCounts = await Promise.all(userPromises);
      const actualTestDuration = Date.now() - startTime;

      // 计算统计数据
      const successRate = (results.successfulRequests / results.totalRequests) * 100;
      const avgResponseTime = results.responseTimes.length > 0 ?
        results.responseTimes.reduce((sum, time) => sum + time, 0) / results.responseTimes.length : 0;
      const p95ResponseTime = results.responseTimes.length > 0 ?
        results.responseTimes.sort((a, b) => a - b)[Math.floor(results.responseTimes.length * 0.95)] : 0;
      const requestsPerSecond = results.totalRequests / (actualTestDuration / 1000);

      console.log(`📈 极限压力测试结果:`);
      console.log(`  实际测试时间: ${actualTestDuration}ms`);
      console.log(`  总请求数: ${results.totalRequests}`);
      console.log(`  成功请求: ${results.successfulRequests}`);
      console.log(`  失败请求: ${results.failedRequests}`);
      console.log(`  成功率: ${successRate.toFixed(1)}%`);
      console.log(`  平均响应时间: ${avgResponseTime.toFixed(2)}ms`);
      console.log(`  95%响应时间: ${p95ResponseTime}ms`);
      console.log(`  RPS: ${requestsPerSecond.toFixed(2)}`);

      // 错误分布
      if (results.errors.size > 0) {
        console.log(`  错误分布:`);
        for (const [error, count] of results.errors) {
          console.log(`    ${error}: ${count}次`);
        }
      }

      // 性能分布分析
      const activeUsers = userRequestCounts.filter(count => count > 0).length;
      console.log(`  活跃用户: ${activeUsers}/${maxConcurrency}`);
      console.log(`  用户请求分布: 平均${(userRequestCounts.reduce((a, b) => a + b, 0) / userRequestCounts.length).toFixed(1)}, 最大${Math.max(...userRequestCounts)}, 最小${Math.min(...userRequestCounts)}`);

      // 压力测试验证
      expect(successRate).toBeGreaterThan(80); // 压力下成功率>80%
      expect(avgResponseTime).toBeLessThan(5000); // 平均响应时间<5秒
      expect(activeUsers).toBeGreaterThan(maxConcurrency * 0.8); // 至少80%用户活跃

      console.log('✅ 极限并发压力测试通过');
    });

    test('长时间稳定性测试', async () => {
      const testDuration = 60000; // 1分钟
      const userCount = 10;

      console.log(`📊 执行长时间稳定性测试 (${userCount}用户, ${testDuration}ms)...`);

      const results = {
        timeline: [],
        errors: [],
        performanceMetrics: {
          responseTimes: [],
          successRates: []
        }
      };

      const startTime = Date.now();
      const endTime = startTime + testDuration;

      // 创建持续运行的用户
      const userPromises = Array.from({ length: userCount }, async (_, userIndex) => {
        let requestCount = 0;

        while (Date.now() < endTime) {
          const requestStart = Date.now();

          try {
            const response = await apiUtils.makeAPIRequest('/market-data/symbols');
            const responseTime = Date.now() - requestStart;

            if (response.ok) {
              results.performanceMetrics.responseTimes.push(responseTime);
            }

            requestCount++;

          } catch (error) {
            results.errors.push({
              timestamp: Date.now() - startTime,
              userIndex,
              error: error.message
            });
          }

          // 稳定的请求间隔
          await new Promise(resolve => setTimeout(resolve, 1000));
        }

        return requestCount;
      });

      // 定期记录性能指标
      const metricsInterval = setInterval(() => {
        const currentResponseTimes = results.performanceMetrics.responseTimes.slice(-50); // 最近50个请求
        const recentSuccessRate = currentResponseTimes.length > 0 ? 100 : 0;

        results.timeline.push({
          timestamp: Date.now() - startTime,
          avgResponseTime: currentResponseTimes.length > 0 ?
            currentResponseTimes.reduce((sum, time) => sum + time, 0) / currentResponseTimes.length : 0,
          successRate: recentSuccessRate,
          totalErrors: results.errors.length
        });
      }, 5000);

      const userRequestCounts = await Promise.all(userPromises);
      clearInterval(metricsInterval);
      const actualTestDuration = Date.now() - startTime;

      // 分析性能趋势
      const avgResponseTime = results.performanceMetrics.responseTimes.length > 0 ?
        results.performanceMetrics.responseTimes.reduce((sum, time) => sum + time, 0) / results.performanceMetrics.responseTimes.length : 0;

      console.log(`📈 长时间稳定性测试结果:`);
      console.log(`  实际测试时间: ${actualTestDuration}ms`);
      console.log(`  总请求数: ${results.performanceMetrics.responseTimes.length}`);
      console.log(`  错误数量: ${results.errors.length}`);
      console.log(`  平均响应时间: ${avgResponseTime.toFixed(2)}ms`);
      console.log(`  用户请求分布: ${userRequestCounts.join(', ')}`);

      // 性能趋势分析
      if (results.timeline.length > 2) {
        const firstHalf = results.timeline.slice(0, Math.floor(results.timeline.length / 2));
        const secondHalf = results.timeline.slice(Math.floor(results.timeline.length / 2));

        const firstHalfAvgTime = firstHalf.reduce((sum, point) => sum + point.avgResponseTime, 0) / firstHalf.length;
        const secondHalfAvgTime = secondHalf.reduce((sum, point) => sum + point.avgResponseTime, 0) / secondHalf.length;

        const performanceDegradation = ((secondHalfAvgTime - firstHalfAvgTime) / firstHalfAvgTime) * 100;

        console.log(`  前半段平均响应时间: ${firstHalfAvgTime.toFixed(2)}ms`);
        console.log(`  后半段平均响应时间: ${secondHalfAvgTime.toFixed(2)}ms`);
        console.log(`  性能变化: ${performanceDegradation > 0 ? '+' : ''}${performanceDegradation.toFixed(1)}%`);

        // 验证性能稳定性
        expect(Math.abs(performanceDegradation)).toBeLessThan(50); // 性能变化不超过50%
      }

      // 错误分析
      if (results.errors.length > 0) {
        console.log(`  错误时间分布:`);
        const errorBuckets = {};
        for (const error of results.errors) {
          const bucket = Math.floor(error.timestamp / 10000) * 10; // 10秒为一个bucket
          errorBuckets[bucket] = (errorBuckets[bucket] || 0) + 1;
        }
        Object.entries(errorBuckets).forEach(([bucket, count]) => {
          console.log(`    ${bucket}s: ${count}个错误`);
        });
      }

      // 稳定性验证
      expect(results.errors.length).toBeLessThan(results.performanceMetrics.responseTimes.length * 0.1); // 错误率<10%
      expect(avgResponseTime).toBeLessThan(3000); // 平均响应时间<3秒

      console.log('✅ 长时间稳定性测试通过');
    });
  });

  test.describe('故障恢复测试', () => {
    test('服务中断恢复测试', async () => {
      const userCount = 5;
      const testDuration = 45000; // 45秒

      console.log(`📊 执行服务中断恢复测试 (${userCount}用户, ${testDuration}ms)...`);

      const results = {
        totalRequests: 0,
        successfulRequests: 0,
        failedRequests: 0,
        outagePeriods: [],
        recoveryTimes: []
      };

      const startTime = Date.now();
      const endTime = startTime + testDuration;

      // 模拟用户持续请求
      const userPromises = Array.from({ length: userCount }, async (_, userIndex) => {
        let consecutiveFailures = 0;
        let lastSuccessTime = Date.now();

        while (Date.now() < endTime) {
          const requestStart = Date.now();

          try {
            const response = await apiUtils.makeAPIRequest('/market-data/symbols');
            const requestTime = Date.now() - requestStart;

            results.totalRequests++;

            if (response.ok) {
              results.successfulRequests++;
              consecutiveFailures = 0;
              lastSuccessTime = Date.now();

              // 检测恢复
              if (consecutiveFailures > 0) {
                results.recoveryTimes.push(consecutiveFailures);
                consecutiveFailures = 0;
              }
            } else {
              results.failedRequests++;
              consecutiveFailures++;

              // 检测服务中断
              if (consecutiveFailures === 1) {
                results.outagePeriods.push({
                  startTime: Date.now(),
                  userIndex,
                  duration: 0
                });
              }
            }

          } catch (error) {
            results.totalRequests++;
            results.failedRequests++;
            consecutiveFailures++;

            if (consecutiveFailures === 1) {
              results.outagePeriods.push({
                startTime: Date.now(),
                userIndex,
                duration: 0
              });
            }
          }

          // 更新中断持续时间
          if (results.outagePeriods.length > 0) {
            const lastOutage = results.outagePeriods[results.outagePeriods.length - 1];
            if (lastOutage.duration === 0) {
              lastOutage.duration = Date.now() - lastOutage.startTime;
            }
          }

          await new Promise(resolve => setTimeout(resolve, 2000));
        }

        return { userIndex, consecutiveFailures };
      });

      const userResults = await Promise.all(userPromises);
      const actualTestDuration = Date.now() - startTime;

      // 分析结果
      const successRate = (results.successfulRequests / results.totalRequests) * 100;
      const outageCount = results.outagePeriods.length;
      const avgRecoveryTime = results.recoveryTimes.length > 0 ?
        results.recoveryTimes.reduce((sum, time) => sum + time, 0) / results.recoveryTimes.length : 0;

      console.log(`📈 故障恢复测试结果:`);
      console.log(`  实际测试时间: ${actualTestDuration}ms`);
      console.log(`  总请求数: ${results.totalRequests}`);
      console.log(`  成功请求: ${results.successfulRequests}`);
      console.log(`  失败请求: ${results.failedRequests}`);
      console.log(`  成功率: ${successRate.toFixed(1)}%`);
      console.log(`  检测到中断次数: ${outageCount}`);
      console.log(`  平均恢复时间: ${avgRecoveryTime.toFixed(0)}次尝试`);

      if (outageCount > 0) {
        const outageDurations = results.outagePeriods.map(outage => outage.duration);
        const avgOutageDuration = outageDurations.reduce((sum, duration) => sum + duration, 0) / outageDurations.length;
        console.log(`  平均中断持续时间: ${avgOutageDuration.toFixed(0)}ms`);
      }

      // 验证故障恢复能力
      expect(successRate).toBeGreaterThan(85); // 即使有中断，成功率也应该>85%
      if (outageCount > 0) {
        expect(avgRecoveryTime).toBeLessThan(10); // 平均恢复时间<10次尝试
      }

      console.log('✅ 服务中断恢复测试通过');
    });
  });
});