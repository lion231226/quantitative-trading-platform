import { test, expect } from './test-helpers';
import { APIMocks } from './mocks/api-mocks';
import { SAMPLE_MARKET_DATA, PERFORMANCE_BENCHMARKS } from './test-data/fixtures';

test.describe('用户完整流程测试', () => {
  let apiMocks: APIMocks;

  test.beforeEach(async ({ page }) => {
    apiMocks = new APIMocks(page);
    await apiMocks.setupAllMocks();
  });

  test.describe('市场数据查看流程', () => {
    test('用户可以查看股票市场数据', async ({ page }) => {
      // 导航到首页
      await page.goto('/');

      // 等待页面加载完成
      await page.waitForSelector('[data-testid="market-data-section"]', {
        timeout: 10000
      });

      // 验证页面标题
      await expect(page.locator('h1')).toContainText('量化交易平台');

      // 验证市场数据表格存在
      await expect(page.locator('[data-testid="stocks-table"]')).toBeVisible();

      // 验证股票数据显示
      const stockRows = page.locator('[data-testid="stock-row"]');
      await expect(stockRows).toHaveCount(SAMPLE_MARKET_DATA.length);

      // 验证第一只股票的信息
      const firstStock = SAMPLE_MARKET_DATA[0];
      await expect(page.locator('[data-testid="stock-symbol-0"]')).toContainText(firstStock.symbol);
      await expect(page.locator('[data-testid="stock-name-0"]')).toContainText(firstStock.name);
      await expect(page.locator('[data-testid="stock-price-0"]')).toContainText(firstStock.price.toString());

      // 测试行业筛选功能
      await page.selectOption('[data-testid="sector-filter"]', '金融');

      // 验证筛选结果
      const filteredStocks = SAMPLE_MARKET_DATA.filter(stock => stock.sector === '金融');
      await expect(page.locator('[data-testid="stock-row"]')).toHaveCount(filteredStocks.length);
    });

    test('用户可以查看单只股票的详细信息', async ({ page }) => {
      // 导航到市场数据页面
      await page.goto('/market-data');

      // 点击第一只股票的查看详情按钮
      await page.click('[data-testid="view-details-0"]');

      // 等待详情页面加载
      await page.waitForSelector('[data-testid="stock-detail-page"]', {
        timeout: 10000
      });

      // 验证股票详情信息
      const firstStock = SAMPLE_MARKET_DATA[0];
      await expect(page.locator('[data-testid="detail-symbol"]')).toContainText(firstStock.symbol);
      await expect(page.locator('[data-testid="detail-name"]')).toContainText(firstStock.name);
      await expect(page.locator('[data-testid="detail-sector"]')).toContainText(firstStock.sector);
      await expect(page.locator('[data-testid="detail-price"]')).toContainText(firstStock.price.toString());

      // 测试返回列表功能
      await page.click('[data-testid="back-to-list"]');
      await expect(page.locator('[data-testid="market-data-section"]')).toBeVisible();
    });
  });

  test.describe('策略配置流程', () => {
    test('用户可以配置和运行策略', async ({ page }) => {
      // 导航到策略页面
      await page.goto('/strategy');

      // 等待策略配置页面加载
      await page.waitForSelector('[data-testid="strategy-config-form"]', {
        timeout: 10000
      });

      // 选择股票
      await page.selectOption('[data-testid="stock-selector"]', SAMPLE_MARKET_DATA[0].symbol);

      // 配置策略参数
      await page.fill('[data-testid="short-window"]', '5');
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      // 验证策略名称自动生成
      await expect(page.locator('[data-testid="strategy-name"]')).toHaveValue('双均线策略');

      // 点击运行策略按钮
      await page.click('[data-testid="run-strategy"]');

      // 等待策略运行完成
      await page.waitForSelector('[data-testid="backtest-results"]', {
        timeout: 15000
      });

      // 验证回测结果显示
      await expect(page.locator('[data-testid="result-total-return"]')).toBeVisible();
      await expect(page.locator('[data-testid="result-sharpe-ratio"]')).toBeVisible();
      await expect(page.locator('[data-testid="result-max-drawdown"]')).toBeVisible();

      // 验证结果数据格式
      const totalReturnElement = page.locator('[data-testid="result-total-return"]');
      const totalReturnText = await totalReturnElement.textContent();
      expect(totalReturnText).toMatch(/\d+\.?\d*%/);
    });

    test('用户可以保存策略配置', async ({ page }) => {
      // 导航到策略页面
      await page.goto('/strategy');

      // 配置策略
      await page.selectOption('[data-testid="stock-selector"]', SAMPLE_MARKET_DATA[1].symbol);
      await page.fill('[data-testid="short-window"]', '10');
      await page.fill('[data-testid="long-window"]', '30');
      await page.fill('[data-testid="initial-capital"]', '500000');

      // 点击保存配置按钮
      await page.click('[data-testid="save-config"]');

      // 等待保存成功提示
      await expect(page.locator('[data-testid="save-success"]')).toBeVisible();

      // 验证配置出现在已保存列表中
      await page.goto('/strategy/saved');
      await expect(page.locator('[data-testid="saved-config-0"]')).toBeVisible();
      await expect(page.locator('[data-testid="saved-config-0"]')).toContainText(SAMPLE_MARKET_DATA[1].symbol);
    });
  });

  test.describe('回测结果查看流程', () => {
    test('用户可以查看回测结果详情', async ({ page }) => {
      // 导航到结果页面
      await page.goto('/results');

      // 等待结果列表加载
      await page.waitForSelector('[data-testid="results-list"]', {
        timeout: 10000
      });

      // 点击查看第一个结果详情
      await page.click('[data-testid="view-result-0"]');

      // 等待详情页面加载
      await page.waitForSelector('[data-testid="result-detail-page"]', {
        timeout: 10000
      });

      // 验证结果显示
      await expect(page.locator('[data-testid="result-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="result-statistics"]')).toBeVisible();
      await expect(page.locator('[data-testid="result-trade-history"]')).toBeVisible();

      // 验证统计数据的准确性
      const statsElements = [
        '[data-testid="stat-total-return"]',
        '[data-testid="stat-annualized-return"]',
        '[data-testid="stat-max-drawdown"]',
        '[data-testid="stat-sharpe-ratio"]',
        '[data-testid="stat-win-rate"]'
      ];

      for (const selector of statsElements) {
        await expect(page.locator(selector)).toBeVisible();
        const text = await page.locator(selector).textContent();
        expect(text).toMatch(/\d+\.?\d*%/);
      }
    });

    test('用户可以导出回测结果', async ({ page }) => {
      // 导航到结果详情页面
      await page.goto('/results/bt_001');

      // 点击导出按钮
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-results"]');

      // 验证文件下载
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/backtest-results.*\.csv/);
    });
  });

  test.describe('完整用户旅程', () => {
    test('新用户完整使用流程', async ({ page }) => {
      // 开始计时 - 性能测试
      const startTime = Date.now();

      // 步骤1: 访问首页
      await page.goto('/');
      await page.waitForSelector('[data-testid="market-data-section"]');

      // 步骤2: 查看市场数据
      await expect(page.locator('[data-testid="stocks-table"]')).toBeVisible();

      // 步骤3: 选择一只股票
      await page.click('[data-testid="view-details-0"]');
      await page.waitForSelector('[data-testid="stock-detail-page"]');

      // 步骤4: 导航到策略配置
      await page.click('[data-testid="create-strategy"]');
      await page.waitForSelector('[data-testid="strategy-config-form"]');

      // 步骤5: 配置策略
      await page.selectOption('[data-testid="stock-selector"]', SAMPLE_MARKET_DATA[0].symbol);
      await page.fill('[data-testid="short-window"]', '5');
      await page.fill('[data-testid="long-window"]', '20');
      await page.fill('[data-testid="initial-capital"]', '100000');

      // 步骤6: 运行策略
      await page.click('[data-testid="run-strategy"]');
      await page.waitForSelector('[data-testid="backtest-results"]', {
        timeout: 15000
      });

      // 步骤7: 查看结果
      await expect(page.locator('[data-testid="result-total-return"]')).toBeVisible();

      // 步骤8: 导航到结果历史
      await page.click('[data-testid="view-all-results"]');
      await page.waitForSelector('[data-testid="results-list"]');

      // 性能验证 - 整个流程应该在合理时间内完成
      const endTime = Date.now();
      const totalTime = endTime - startTime;
      expect(totalTime).toBeLessThan(PERFORMANCE_BENCHMARKS.testTimeout);

      console.log(`✅ 完整用户旅程耗时: ${totalTime}ms`);
    });

    test('返回用户快速操作流程', async ({ page }) => {
      // 模拟返回用户，直接访问策略页面
      await page.goto('/strategy');

      // 使用保存的配置
      await page.click('[data-testid="load-saved-config"]');
      await page.click('[data-testid="saved-config-0"]');

      // 快速运行策略
      await page.click('[data-testid="run-strategy"]');
      await page.waitForSelector('[data-testid="backtest-results"]');

      // 验证结果
      await expect(page.locator('[data-testid="result-total-return"]')).toBeVisible();
    });
  });

  test.describe('响应式设计测试', () => {
    test('移动端适配测试', async ({ page }) => {
      // 设置移动端视口
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto('/');

      // 验证移动端导航
      await expect(page.locator('[data-testid="mobile-menu-button"]')).toBeVisible();

      // 点击移动端菜单
      await page.click('[data-testid="mobile-menu-button"]');
      await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible();

      // 验证移动端表格适配
      await page.goto('/market-data');
      await expect(page.locator('[data-testid="mobile-cards"]')).toBeVisible();
    });

    test('平板端适配测试', async ({ page }) => {
      // 设置平板视口
      await page.setViewportSize({ width: 768, height: 1024 });

      await page.goto('/strategy');

      // 验证平板端布局
      await expect(page.locator('[data-testid="tablet-layout"]')).toBeVisible();
    });
  });
});