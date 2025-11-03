const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

async function globalSetup(config) {
  console.log('🚀 Starting global setup for E2E tests...');

  // Ensure test results directory exists
  const resultsDir = path.join(__dirname, 'e2e-results');
  if (!fs.existsSync(resultsDir)) {
    fs.mkdirSync(resultsDir, { recursive: true });
  }

  // Wait for services to be ready
  const baseURL = config.webServer?.[0]?.port ?
    `http://localhost:${config.webServer[0].port}` :
    'http://localhost:8000';

  const frontendURL = config.webServer?.[1]?.port ?
    `http://localhost:${config.webServer[1].port}` :
    'http://localhost:3000';

  console.log(`⏳ Waiting for backend at ${baseURL}`);
  console.log(`⏳ Waiting for frontend at ${frontendURL}`);

  // Wait for backend health check
  let backendReady = false;
  let attempts = 0;
  const maxAttempts = 30;

  while (!backendReady && attempts < maxAttempts) {
    try {
      const browser = await chromium.launch();
      const context = await browser.newContext();
      const page = await context.newPage();

      const response = await page.goto(`${baseURL}/health`, { timeout: 5000 });
      if (response && response.status() === 200) {
        backendReady = true;
        console.log('✅ Backend is ready');
      }

      await browser.close();
    } catch (error) {
      attempts++;
      console.log(`⏳ Backend not ready, retrying... (${attempts}/${maxAttempts})`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }

  if (!backendReady) {
    console.warn('⚠️ Backend health check failed, but continuing with tests...');
  }

  // Wait for frontend
  let frontendReady = false;
  attempts = 0;

  while (!frontendReady && attempts < maxAttempts) {
    try {
      const browser = await chromium.launch();
      const context = await browser.newContext();
      const page = await context.newPage();

      const response = await page.goto(frontendURL, { timeout: 5000 });
      if (response && response.status() === 200) {
        frontendReady = true;
        console.log('✅ Frontend is ready');
      }

      await browser.close();
    } catch (error) {
      attempts++;
      console.log(`⏳ Frontend not ready, retrying... (${attempts}/${maxAttempts})`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }

  if (!frontendReady) {
    console.warn('⚠️ Frontend health check failed, but continuing with tests...');
  }

  console.log('✅ Global setup completed');
}

module.exports = globalSetup;