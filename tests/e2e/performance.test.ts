import { test, expect } from './test-helpers';
import { APIMocks } from './mocks/api-mocks';
import { PERFORMANCE_BENCHMARKS, TestDataGenerator } from './test-data/fixtures';

test.describe('性能基准测试', () => {
  let apiMocks: APIMocks;

  test.beforeEach(async ({ page }) => {
    apiMocks = new APIMocks(page);
    await apiMocks.setupAllMocks();
  });

  test.describe('页面加载性能', () => {
    test('首页加载性能测试', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/');

      // 等待页面完全加载
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('[data-testid="market-data-section"]');

      const loadTime = Date.now() - startTime;

      // 验证加载时间符合要求
      expect(loadTime).toBeLessThan(PERFORMANCE_BENCHMARKS.pageLoadTime);

      console.log(`📊 首页加载时间: ${loadTime}ms`);

      // 获取详细的性能指标
      const metrics = await page.evaluate(() => {
        const timing = (window as any).performance.timing;
        return {
          dns: timing.domainLookupEnd - timing.domainLookupStart,
          tcp: timing.connectEnd - timing.connectStart,
          request: timing.responseEnd - timing.requestStart,
          dom: timing.domContentLoadedEventEnd - timing.navigationStart,
          load: timing.loadEventEnd - timing.navigationStart
        };
      });

      console.log('📈 性能指标详情:', metrics);

      // 验证关键性能指标
      expect(metrics.request).toBeLessThan(1000); // 请求时间 < 1秒
      expect(metrics.dom).toBeLessThan(2000); // DOM构建时间 < 2秒
    });

    test('策略页面加载性能测试', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/strategy');

      await page.waitForLoadState('networkidle');
      await page.waitForSelector('[data-testid="strategy-config-form"]');

      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(PERFORMANCE_BENCHMARKS.pageLoadTime);
      console.log(`📊 策略页面加载时间: ${loadTime}ms`);
    });

    test('结果页面加载性能测试', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/results');

      await page.waitForLoadState('networkidle');
      await page.waitForSelector('[data-testid="results-list"]');

      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(PERFORMANCE_BENCHMARKS.pageLoadTime);
      console.log(`📊 结果页面加载时间: ${loadTime}ms`);
    });
  });

  test.describe('API响应性能', () => {
    test('市场数据API响应时间', async ({ page }) => {
      await page.goto('/market-data');

      // 监听API请求
      const apiStartTime = Date.now();
      const responsePromise = page.waitForResponse('**/api/v1/market-data/symbols*');

      await page.click('[data-testid="refresh-data"]');
      const response = await responsePromise;
      const apiResponseTime = Date.now() - apiStartTime;

      // 验证API响应时间
      expect(apiResponseTime).toBeLessThan(PERFORMANCE_BENCHMARKS.apiResponseTime);
      console.log(`📊 市场数据API响应时间: ${apiResponseTime}ms`);

      // 验证响应状态
      expect(response.status()).toBe(200);
    });

    test('策略运行API响应时间', async ({ page }) => {
      await page.goto('/strategy');

      // 配置策略
      await page.selectOption('[data-testid="stock-selector"]', '000001.SZ');
      await page.fill('[data-testid="short-window"]', '5');
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      // 监听策略运行API
      const apiStartTime = Date.now();
      const responsePromise = page.waitForResponse('**/api/v1/strategies/run');

      await page.click('[data-testid="run-strategy"]');
      const response = await responsePromise;
      const apiResponseTime = Date.now() - apiStartTime;

      // 策略运行允许更长的时间
      expect(apiResponseTime).toBeLessThan(PERFORMANCE_BENCHMARKS.strategyCalculationTime);
      console.log(`📊 策略运行API响应时间: ${apiResponseTime}ms`);
    });
  });

  test.describe('并发性能测试', () => {
    test('多用户并发访问测试', async ({ context }) => {
      const userCount = 5;
      const startTime = Date.now();

      // 创建多个页面模拟并发用户
      const pages = await Promise.all(
        Array.from({ length: userCount }, () => context.newPage())
      );

      // 并发访问首页
      const loadPromises = pages.map(async (page, index) => {
        const pageStartTime = Date.now();
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        return {
          pageIndex: index,
          loadTime: Date.now() - pageStartTime
        };
      });

      const results = await Promise.all(loadPromises);
      const totalTime = Date.now() - startTime;

      console.log(`📊 ${userCount}个并发用户总耗时: ${totalTime}ms`);

      // 验证每个用户的加载时间
      results.forEach(result => {
        expect(result.loadTime).toBeLessThan(PERFORMANCE_BENCHMARKS.pageLoadTime);
        console.log(`📈 用户${result.pageIndex}加载时间: ${result.loadTime}ms`);
      });

      // 关闭页面
      await Promise.all(pages.map(page => page.close()));
    });

    test('并发API请求测试', async ({ page }) => {
      await page.goto('/market-data');

      // 同时触发多个API请求
      const startTime = Date.now();

      const promises = [
        page.click('[data-testid="refresh-data"]'),
        page.selectOption('[data-testid="sector-filter"]', '金融'),
        page.click('[data-testid="sort-by-price"]')
      ];

      await Promise.all(promises);
      await page.waitForLoadState('networkidle');

      const totalTime = Date.now() - startTime;

      // 并发请求应该比串行请求快
      expect(totalTime).toBeLessThan(PERFORMANCE_BENCHMARKS.apiResponseTime * 2);
      console.log(`📊 并发API请求总时间: ${totalTime}ms`);
    });
  });

  test.describe('内存和资源使用', () => {
    test('内存泄漏检测', async ({ page }) => {
      await page.goto('/');

      // 获取初始内存使用
      const initialMemory = await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });

      // 执行一系列操作
      for (let i = 0; i < 10; i++) {
        await page.goto('/market-data');
        await page.click('[data-testid="refresh-data"]');
        await page.goto('/strategy');
        await page.goto('/results');
      }

      // 强制垃圾回收
      await page.evaluate(() => {
        if ((window as any).gc) {
          (window as any).gc();
        }
      });

      // 获取最终内存使用
      const finalMemory = await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });

      const memoryIncrease = finalMemory - initialMemory;
      const memoryIncreaseMB = memoryIncrease / (1024 * 1024);

      console.log(`📊 内存增长: ${memoryIncreaseMB.toFixed(2)}MB`);

      // 内存增长应该在合理范围内（小于50MB）
      expect(memoryIncreaseMB).toBeLessThan(50);
    });

    test('DOM节点数量监控', async ({ page }) => {
      await page.goto('/');

      // 获取初始DOM节点数
      const initialNodes = await page.evaluate(() => {
        return document.querySelectorAll('*').length;
      });

      // 执行多个页面导航
      for (let i = 0; i < 5; i++) {
        await page.goto('/market-data');
        await page.waitForSelector('[data-testid="stocks-table"]');
        await page.goto('/strategy');
        await page.waitForSelector('[data-testid="strategy-config-form"]');
      }

      // 获取最终DOM节点数
      const finalNodes = await page.evaluate(() => {
        return document.querySelectorAll('*').length;
      });

      const nodeIncrease = finalNodes - initialNodes;
      console.log(`📊 DOM节点增长: ${nodeIncrease}`);

      // DOM节点增长应该在合理范围内
      expect(nodeIncrease).toBeLessThan(1000);
    });
  });

  test.describe('缓存性能测试', () => {
    test('页面缓存效果测试', async ({ page }) => {
      // 首次访问
      const firstVisitStart = Date.now();
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      const firstVisitTime = Date.now() - firstVisitStart;

      // 二次访问（应该使用缓存）
      const secondVisitStart = Date.now();
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      const secondVisitTime = Date.now() - secondVisitStart;

      const improvement = ((firstVisitTime - secondVisitTime) / firstVisitTime) * 100;

      console.log(`📊 首次访问: ${firstVisitTime}ms`);
      console.log(`📊 二次访问: ${secondVisitTime}ms`);
      console.log(`📈 性能提升: ${improvement.toFixed(1)}%`);

      // 二次访问应该更快（至少提升10%）
      expect(improvement).toBeGreaterThan(10);
    });

    test('API缓存效果测试', async ({ page }) => {
      await page.goto('/market-data');

      // 首次API调用
      const firstAPICallStart = Date.now();
      await page.click('[data-testid="refresh-data"]');
      await page.waitForResponse('**/api/v1/market-data/symbols*');
      const firstAPICallTime = Date.now() - firstAPICallStart;

      // 二次API调用（应该使用缓存）
      const secondAPICallStart = Date.now();
      await page.click('[data-testid="refresh-data"]');
      await page.waitForResponse('**/api/v1/market-data/symbols*');
      const secondAPICallTime = Date.now() - secondAPICallStart;

      const improvement = ((firstAPICallTime - secondAPICallTime) / firstAPICallTime) * 100;

      console.log(`📊 首次API调用: ${firstAPICallTime}ms`);
      console.log(`📊 二次API调用: ${secondAPICallTime}ms`);
      console.log(`📈 缓存性能提升: ${improvement.toFixed(1)}%`);

      // 缓存应该显著提升性能
      expect(improvement).toBeGreaterThan(50);
    });
  });

  test.describe('渲染性能测试', () => {
    test('大数据集渲染性能', async ({ page }) => {
      // 模拟大数据集
      await apiMocks.mockEndpoint('**/api/v1/market-data/symbols*', {
        success: true,
        data: TestDataGenerator.generateMarketData(1000), // 1000条数据
        message: '找到1000支股票'
      });

      const renderStart = Date.now();
      await page.goto('/market-data');
      await page.waitForSelector('[data-testid="stock-row"]');
      const renderTime = Date.now() - renderStart;

      console.log(`📊 1000条数据渲染时间: ${renderTime}ms`);

      // 大数据集渲染应该在合理时间内完成
      expect(renderTime).toBeLessThan(3000);
    });

    test('动画性能测试', async ({ page }) => {
      await page.goto('/');

      // 监控动画性能
      const animationMetrics = await page.evaluate(() => {
        return new Promise((resolve) => {
          let frameCount = 0;
          let startTime = performance.now();

          function countFrames() {
            frameCount++;
            if (performance.now() - startTime < 1000) {
              requestAnimationFrame(countFrames);
            } else {
              resolve({
                frameCount,
                fps: frameCount,
                duration: performance.now() - startTime
              });
            }
          }

          requestAnimationFrame(countFrames);
        });
      });

      console.log(`📊 动画性能: ${animationMetrics.fps} FPS`);

      // 动画应该保持流畅（至少30 FPS）
      expect(animationMetrics.fps).toBeGreaterThan(30);
    });
  });
});