import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 E2E测试全局设置开始...');

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 等待前端服务启动
    const frontendURL = config.webServer?.url || 'http://localhost:3000';
    console.log(`📍 检查前端服务: ${frontendURL}`);

    const maxRetries = 30;
    let retries = 0;

    while (retries < maxRetries) {
      try {
        await page.goto(frontendURL, { timeout: 5000 });
        console.log('✅ 前端服务已就绪');
        break;
      } catch (error) {
        retries++;
        if (retries >= maxRetries) {
          console.log('❌ 前端服务启动失败或超时');
          throw error;
        }
        console.log(`⏳ 等待前端服务启动... (${retries}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }

    // 检查后端服务
    const backendURL = process.env.BACKEND_URL || 'http://localhost:8000';
    console.log(`📍 检查后端服务: ${backendURL}`);

    try {
      const response = await page.goto(`${backendURL}/health`, { timeout: 5000 });
      if (response && response.ok()) {
        console.log('✅ 后端服务已就绪');
      } else {
        console.log('⚠️ 后端服务健康检查失败，但继续测试');
      }
    } catch (error) {
      console.log('⚠️ 后端服务不可用，但继续测试（使用Mock）');
    }

    // 创建测试结果目录
    const fs = require('fs');
    const path = require('path');
    const resultsDir = path.join(__dirname, '../e2e-results');

    if (!fs.existsSync(resultsDir)) {
      fs.mkdirSync(resultsDir, { recursive: true });
      console.log('📁 创建测试结果目录');
    }

  } catch (error) {
    console.error('❌ 全局设置失败:', error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }

  console.log('✅ E2E测试全局设置完成');
}

export default globalSetup;