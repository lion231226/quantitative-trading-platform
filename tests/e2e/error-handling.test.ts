import { test, expect } from './test-helpers';
import { APIMocks } from './mocks/api-mocks';
import { ERROR_SCENARIOS } from './test-data/fixtures';

test.describe('错误处理和边界条件测试', () => {
  let apiMocks: APIMocks;

  test.beforeEach(async ({ page }) => {
    apiMocks = new APIMocks(page);
  });

  test.describe('网络错误处理', () => {
    test('网络连接失败时的错误处理', async ({ page }) => {
      // 设置网络错误模拟
      await apiMocks.mockEndpoint('**/api/v1/market-data/symbols*', {
        success: false,
        data: null,
        message: '网络连接失败'
      }, 500);

      await page.goto('/market-data');

      // 验证错误提示显示
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-message"]')).toContainText('网络连接失败');

      // 验证重试按钮存在
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();

      // 验证错误状态下的UI友好性
      await expect(page.locator('[data-testid="error-icon"]')).toBeVisible();
    });

    test('API超时处理', async ({ page }) => {
      // 设置超时模拟
      await page.route('**/api/v1/**', async (route) => {
        // 不响应，模拟超时
        await new Promise(resolve => setTimeout(resolve, 35000));
      });

      await page.goto('/market-data');

      // 验证超时错误提示
      await expect(page.locator('[data-testid="timeout-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="timeout-message"]')).toContainText('请求超时');
    });

    test('服务器错误处理', async ({ page }) => {
      // 设置服务器错误模拟
      await apiMocks.mockEndpoint('**/api/v1/strategies/run', {
        success: false,
        data: null,
        message: '服务器内部错误'
      }, 500);

      await page.goto('/strategy');

      // 配置并运行策略
      await page.selectOption('[data-testid="stock-selector"]', '000001.SZ');
      await page.fill('[data-testid="short-window"]', '5');
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      await page.click('[data-testid="run-strategy"]');

      // 验证服务器错误处理
      await expect(page.locator('[data-testid="server-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="server-error"]')).toContainText('服务器内部错误');

      // 验证错误恢复机制
      await expect(page.locator('[data-testid="error-recovery"]')).toBeVisible();
    });
  });

  test.describe('数据验证错误', () => {
    test('无效股票代码处理', async ({ page }) => {
      await apiMocks.setupAllMocks();

      await page.goto('/market-data');

      // 尝试访问无效股票代码
      await page.goto('/market-data/INVALID.SYMBOL');

      // 验证404错误页面
      await expect(page.locator('[data-testid="not-found"]')).toBeVisible();
      await expect(page.locator('[data-testid="not-found"]')).toContainText('股票代码不存在');

      // 验证返回按钮
      await expect(page.locator('[data-testid="back-home"]')).toBeVisible();
    });

    test('策略参数验证', async ({ page }) => {
      await apiMocks.setupAllMocks();

      await page.goto('/strategy');

      // 测试无效参数组合
      await page.selectOption('[data-testid="stock-selector"]', '000001.SZ');
      await page.fill('[data-testid="short-window"]', '50'); // 错误：短期窗口 > 长期窗口
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      await page.click('[data-testid="run-strategy"]');

      // 验证参数验证错误
      await expect(page.locator('[data-testid="validation-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="validation-error"]')).toContainText('短期窗口必须小于长期窗口');

      // 验证错误高亮
      await expect(page.locator('[data-testid="short-window"]')).toHaveClass(/error/);
      await expect(page.locator('[data-testid="long-window"]')).toHaveClass(/error/);
    });

    test('输入边界值测试', async ({ page }) => {
      await apiMocks.setupAllMocks();

      await page.goto('/strategy');

      // 测试极小值
      await page.fill('[data-testid="short-window"]', '1');
      await page.fill('[data-testid="long-window"]', '2');
      await page.fill('[data-testid="initial-capital"]', '1'); // 最小资本

      await page.click('[data-testid="run-strategy"]');

      // 验证可以处理最小值
      await expect(page.locator('[data-testid="backtest-results"]')).toBeVisible();

      // 测试极大值
      await page.fill('[data-testid="short-window"]', '100');
      await page.fill('[data-testid="long-window"]', '200');
      await page.fill('[data-testid="initial-capital"]', '999999999');

      await page.click('[data-testid="run-strategy"]');

      // 验证可以处理最大值
      await expect(page.locator('[data-testid="backtest-results"]')).toBeVisible();
    });
  });

  test.describe('用户交互错误', () => {
    test('重复提交防护', async ({ page }) => {
      await apiMocks.setupAllMocks();

      await page.goto('/strategy');

      // 配置策略
      await page.selectOption('[data-testid="stock-selector"]', '000001.SZ');
      await page.fill('[data-testid="short-window"]', '5');
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      // 快速双击运行按钮
      await page.click('[data-testid="run-strategy"]');
      await page.click('[data-testid="run-strategy"]'); // 第二次点击应该被忽略

      // 验证按钮被禁用
      await expect(page.locator('[data-testid="run-strategy"]')).toBeDisabled();

      // 验证加载状态
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();

      // 等待完成
      await page.waitForSelector('[data-testid="backtest-results"]');

      // 验证只有一个结果
      const results = page.locator('[data-testid="result-item"]');
      await expect(results).toHaveCount(1);
    });

    test('表单数据丢失保护', async ({ page }) => {
      await page.goto('/strategy');

      // 填写表单数据
      await page.selectOption('[data-testid="stock-selector"]', '000001.SZ');
      await page.fill('[data-testid="short-window"]', '5');
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      // 导航到其他页面
      await page.goto('/market-data');

      // 返回策略页面
      await page.goBack();

      // 验证数据是否保持（或提示用户）
      const shortWindow = page.locator('[data-testid="short-window"]');
      const value = await shortWindow.inputValue();

      if (value !== '5') {
        // 如果数据丢失，应该有提示
        await expect(page.locator('[data-testid="data-loss-warning"]')).toBeVisible();
      }
    });
  });

  test.describe('并发和竞态条件', () => {
    test('并发请求处理', async ({ page }) => {
      await apiMocks.setupAllMocks();

      await page.goto('/market-data');

      // 同时触发多个请求
      const promises = [
        page.click('[data-testid="refresh-data"]'),
        page.click('[data-testid="filter-by-sector"]'),
        page.click('[data-testid="sort-by-price"]')
      ];

      await Promise.all(promises);

      // 验证最终状态一致性
      await page.waitForSelector('[data-testid="stocks-table"]');
      await expect(page.locator('[data-testid="stock-row"]')).toHaveCountGreaterThan(0);
    });

    test('组件卸载时的请求取消', async ({ page }) => {
      await page.goto('/strategy');

      // 启动长时间运行的任务
      await page.selectOption('[data-testid="stock-selector"]', '000001.SZ');
      await page.fill('[data-testid="short-window"]', '5');
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      await page.click('[data-testid="run-strategy"]');

      // 立即导航离开
      await page.goto('/market-data');

      // 验证没有错误产生
      await expect(page.locator('[data-testid="error-message"]')).not.toBeVisible();
    });
  });

  test.describe('资源加载错误', () => {
    test('图片加载失败处理', async ({ page }) => {
      // 设置图片加载失败
      await page.route('**/images/**', route => route.abort());

      await page.goto('/');

      // 验证图片加载失败的占位符
      await expect(page.locator('[data-testid="image-placeholder"]')).toBeVisible();
    });

    test('CSS加载失败处理', async ({ page }) => {
      // 阻止CSS加载
      await page.route('**/*.css', route => route.abort());

      await page.goto('/');

      // 验证页面仍然可用（虽然样式缺失）
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('[data-testid="no-styles-warning"]')).toBeVisible();
    });

    test('JavaScript加载失败处理', async ({ page }) => {
      // 这个测试比较复杂，需要模拟部分JS加载失败
      // 在实际项目中，应该有适当的fallback机制

      await page.goto('/');

      // 验证核心功能仍然可用
      await expect(page.locator('[data-testid="fallback-content"]')).toBeVisible();
    });
  });

  test.describe('浏览器兼容性错误', () => {
    test('旧版浏览器兼容性', async ({ page }) => {
      // 模拟旧版浏览器
      await page.addInitScript(() => {
        // 模拟不支持某些API
        (window as any).IntersectionObserver = undefined;
        (window as any).fetch = undefined;
      });

      await page.goto('/');

      // 验证降级方案
      await expect(page.locator('[data-testid="legacy-browser-notice"]')).toBeVisible();
      await expect(page.locator('[data-testid="fallback-implementation"]')).toBeVisible();
    });

    test('禁用JavaScript的处理', async ({ page }) => {
      // 这个测试需要在Playwright配置中设置JavaScript禁用
      // 这里只是示例结构

      await page.goto('/', { javaScriptEnabled: false });

      // 验证noscript内容
      await expect(page.locator('noscript')).toBeVisible();
    });
  });
});