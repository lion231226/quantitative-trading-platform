import { test as base, Page, BrowserContext, Browser } from '@playwright/test';

// Define custom fixtures
export interface TestFixtures {
  authenticatedPage: Page;
  backendURL: string;
  frontendURL: string;
}

// Extend base test with custom fixtures
export const test = base.extend<TestFixtures>({
  // Custom authenticated page fixture
  authenticatedPage: async ({ page, context }, use) => {
    // Set up authentication if needed
    // For now, we'll just use the page as-is
    await use(page);
  },

  // Backend URL fixture
  backendURL: async ({}, use) => {
    const backendURL = process.env.BACKEND_URL || 'http://localhost:8000';
    await use(backendURL);
  },

  // Frontend URL fixture
  frontendURL: async ({}, use) => {
    const frontendURL = process.env.FRONTEND_URL || 'http://localhost:3000';
    await use(frontendURL);
  },
});

// Export expect from playwright/test
export { expect } from '@playwright/test';

// Common test utilities
export class TestUtils {
  constructor(private page: Page) {}

  // Wait for API response and return data
  async waitForAPIResponse(urlPattern: string | RegExp): Promise<any> {
    const response = await this.page.waitForResponse(urlPattern);
    return await response.json();
  }

  // Check if element is visible and enabled
  async isElementVisible(selector: string): Promise<boolean> {
    return await this.page.isVisible(selector);
  }

  // Wait for element to be visible
  async waitForElement(selector: string, timeout: number = 10000): Promise<void> {
    await this.page.waitForSelector(selector, {
      state: 'visible',
      timeout
    });
  }

  // Fill form with data
  async fillForm(formData: Record<string, string>): Promise<void> {
    for (const [selector, value] of Object.entries(formData)) {
      await this.page.fill(selector, value);
    }
  }

  // Take screenshot with custom name
  async takeScreenshot(name: string): Promise<void> {
    await this.page.screenshot({
      path: `tests/e2e-results/${name}-${Date.now()}.png`,
      fullPage: true
    });
  }

  // Check for console errors
  async checkConsoleErrors(): Promise<string[]> {
    const errors: string[] = [];
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    return errors;
  }

  // Navigate to URL with timeout
  async navigateTo(url: string, timeout: number = 30000): Promise<void> {
    await this.page.goto(url, { timeout });
  }

  // Wait for network idle
  async waitForNetworkIdle(timeout: number = 5000): Promise<void> {
    await this.page.waitForLoadState('networkidle', { timeout });
  }

  // Check if page has loaded completely
  async isPageLoaded(): Promise<boolean> {
    return await this.page.evaluate(() => {
      return document.readyState === 'complete';
    });
  }
}

// Performance test utilities
export class PerformanceUtils {
  constructor(private page: Page) {}

  // Measure page load time
  async measurePageLoadTime(): Promise<number> {
    const navigationStart = await this.page.evaluate(() => {
      return (window as any).performance.timing.navigationStart;
    });

    const loadComplete = await this.page.evaluate(() => {
      return (window as any).performance.timing.loadEventEnd;
    });

    return loadComplete - navigationStart;
  }

  // Measure API response time
  async measureAPIResponseTime(url: string): Promise<number> {
    const startTime = Date.now();
    await this.page.goto(url);
    const endTime = Date.now();
    return endTime - startTime;
  }

  // Get performance metrics
  async getPerformanceMetrics(): Promise<any> {
    return await this.page.evaluate(() => {
      const timing = (window as any).performance.timing;
      const navigation = (window as any).performance.navigation;

      return {
        dnsLookup: timing.domainLookupEnd - timing.domainLookupStart,
        tcpConnection: timing.connectEnd - timing.connectStart,
        serverResponse: timing.responseEnd - timing.requestStart,
        domLoad: timing.domContentLoadedEventEnd - timing.navigationStart,
        pageLoad: timing.loadEventEnd - timing.navigationStart,
        redirectCount: navigation.redirectCount
      };
    });
  }
}

// API test utilities
export class APIUtils {
  constructor(private baseURL: string) {}

  // Make API request and return response
  async makeAPIRequest(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const url = `${this.baseURL}${endpoint}`;
    return fetch(url, options);
  }

  // Test API endpoint
  async testEndpoint(endpoint: string, expectedStatus: number = 200): Promise<{
    status: number;
    data: any;
    success: boolean;
  }> {
    try {
      const response = await this.makeAPIRequest(endpoint);
      const data = await response.json();

      return {
        status: response.status,
        data,
        success: response.status === expectedStatus
      };
    } catch (error) {
      return {
        status: 0,
        data: null,
        success: false
      };
    }
  }
}