/**
 * Unit Tests for Deployment Strategy Automation
 *
 * 测试蓝绿部署策略的自动化测试逻辑
 */

const { DeploymentStrategyTester } = require('../test-deployment-strategy');
const { jest } = require('@jest/globals');

// Mock HTTP requests
jest.mock('http');
jest.mock('https');

describe('DeploymentStrategyTester', () => {
  let tester;

  beforeEach(() => {
    tester = new DeploymentStrategyTester({
      baseUrl: 'http://localhost:3000',
      timeout: 5000,
      retries: 2,
      healthCheckInterval: 100
    });

    // Mock console methods to reduce noise in tests
    jest.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Constructor', () => {
    test('should initialize with default configuration', () => {
      const defaultTester = new DeploymentStrategyTester();

      expect(defaultTester.config.baseUrl).toBe('http://localhost:3000');
      expect(defaultTester.config.timeout).toBe(30000);
      expect(defaultTester.config.retries).toBe(3);
    });

    test('should accept custom configuration', () => {
      const customConfig = {
        baseUrl: 'https://custom.example.com',
        timeout: 10000,
        retries: 5
      };

      const customTester = new DeploymentStrategyTester(customConfig);

      expect(customTester.config.baseUrl).toBe(customConfig.baseUrl);
      expect(customTester.config.timeout).toBe(customConfig.timeout);
      expect(customTester.config.retries).toBe(customConfig.retries);
    });
  });

  describe('healthCheck', () => {
    test('should succeed on successful health check', async () => {
      // Mock successful HTTP response
      const mockResponse = {
        statusCode: 200,
        body: JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          services: {
            database: 'connected',
            cache: 'connected',
            api: 'running'
          }
        })
      };

      // Mock the makeRequest method
      jest.spyOn(tester, 'makeRequest').mockResolvedValue(mockResponse);

      const result = await tester.healthCheck('http://localhost:3000');

      expect(result.success).toBe(true);
      expect(result.data.status).toBe('healthy');
      expect(tester.makeRequest).toHaveBeenCalledWith('http://localhost:3000/api/health');
    });

    test('should retry on failed health check', async () => {
      // Mock failed responses followed by success
      const mockFailure = {
        statusCode: 503,
        body: 'Service Unavailable'
      };

      const mockSuccess = {
        statusCode: 200,
        body: JSON.stringify({ status: 'healthy' })
      };

      tester.makeRequest = jest.fn()
        .mockResolvedValueOnce(mockFailure)
        .mockResolvedValueOnce(mockFailure)
        .mockResolvedValueOnce(mockSuccess);

      const result = await tester.healthCheck('http://localhost:3000', 3);

      expect(result.success).toBe(true);
      expect(tester.makeRequest).toHaveBeenCalledTimes(3);
    });

    test('should fail after all retries exhausted', async () => {
      const mockFailure = {
        statusCode: 503,
        body: 'Service Unavailable'
      };

      tester.makeRequest = jest.fn().mockResolvedValue(mockFailure);

      const result = await tester.healthCheck('http://localhost:3000', 2);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Health check failed after all retries');
      expect(tester.makeRequest).toHaveBeenCalledTimes(2);
    });
  });

  describe('readinessCheck', () => {
    test('should succeed on successful readiness check', async () => {
      const mockResponse = {
        statusCode: 200,
        body: JSON.stringify({
          ready: true,
          checks: {
            database: 'ready',
            cache: 'ready',
            external_apis: 'ready'
          }
        })
      };

      jest.spyOn(tester, 'makeRequest').mockResolvedValue(mockResponse);

      const result = await tester.readinessCheck('http://localhost:3000');

      expect(result.success).toBe(true);
      expect(result.data.ready).toBe(true);
      expect(tester.makeRequest).toHaveBeenCalledWith('http://localhost:3000/api/ready');
    });
  });

  describe('performanceCheck', () => {
    test('should pass on fast response', async () => {
      const mockResponse = {
        statusCode: 200,
        body: '<html><body>OK</body></html>'
      };

      jest.spyOn(tester, 'makeRequest').mockImplementation(async (url) => {
        // Simulate fast response
        await new Promise(resolve => setTimeout(resolve, 100));
        return mockResponse;
      });

      const result = await tester.performanceCheck('http://localhost:3000');

      expect(result.success).toBe(true);
      expect(result.loadTime).toBeLessThan(5000);
    });

    test('should fail on slow response', async () => {
      const mockResponse = {
        statusCode: 200,
        body: '<html><body>OK</body></html>'
      };

      jest.spyOn(tester, 'makeRequest').mockImplementation(async (url) => {
        // Simulate slow response
        await new Promise(resolve => setTimeout(resolve, 6000));
        return mockResponse;
      });

      const result = await tester.performanceCheck('http://localhost:3000');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Slow response time');
    });
  });

  describe('testSecurityHeaders', () => {
    test('should pass when all security headers are present', async () => {
      const mockResponse = {
        statusCode: 200,
        headers: {
          'x-content-type-options': 'nosniff',
          'x-frame-options': 'DENY',
          'x-xss-protection': '1; mode=block',
          'strict-transport-security': 'max-age=31536000; includeSubDomains',
          'content-type': 'text/html'
        },
        body: '<html><body>OK</body></html>'
      };

      jest.spyOn(tester, 'makeRequest').mockResolvedValue(mockResponse);

      const result = await tester.testSecurityHeaders('http://localhost:3000');

      expect(result.success).toBe(true);
      expect(result.presentHeaders).toHaveLength(4);
    });

    test('should fail when security headers are missing', async () => {
      const mockResponse = {
        statusCode: 200,
        headers: {
          'content-type': 'text/html'
        },
        body: '<html><body>OK</body></html>'
      };

      jest.spyOn(tester, 'makeRequest').mockResolvedValue(mockResponse);

      const result = await tester.testSecurityHeaders('http://localhost:3000');

      expect(result.success).toBe(false);
      expect(result.missingHeaders).toHaveLength(4);
    });
  });

  describe('testRollbackSimulation', () => {
    test('should indicate server responsiveness on 404', async () => {
      const mockResponse = {
        statusCode: 404,
        body: 'Not Found'
      };

      jest.spyOn(tester, 'makeRequest').mockResolvedValue(mockResponse);

      const result = await tester.testRollbackSimulation('http://localhost:3000');

      expect(result.success).toBe(true);
      expect(result.message).toContain('Server responsive');
    });

    test('should handle connection refused properly', async () => {
      const error = new Error('Connection refused');
      error.code = 'ECONNREFUSED';

      jest.spyOn(tester, 'makeRequest').mockRejectedValue(error);

      const result = await tester.testRollbackSimulation('http://localhost:3000');

      expect(result.success).toBe(false);
      expect(result.error).toContain('would trigger rollback');
    });
  });

  describe('testBlueGreenDeployment', () => {
    test('should run all test cases and return comprehensive results', async () => {
      // Mock all the test methods
      jest.spyOn(tester, 'healthCheck').mockResolvedValue({ success: true, data: { status: 'healthy' } });
      jest.spyOn(tester, 'readinessCheck').mockResolvedValue({ success: true, data: { ready: true } });
      jest.spyOn(tester, 'performanceCheck').mockResolvedValue({ success: true, loadTime: 500 });
      jest.spyOn(tester, 'testSecurityHeaders').mockResolvedValue({ success: true });

      const result = await tester.testBlueGreenDeployment();

      expect(result.strategy).toBe('blue-green');
      expect(result.totalTests).toBe(5);
      expect(result.passed).toBe(5);
      expect(result.failed).toBe(0);
      expect(result.criticalFailures).toBe(0);
      expect(result.passed).toBe(true);
    });

    test('should detect critical test failures', async () => {
      // Mock critical test failures
      jest.spyOn(tester, 'healthCheck').mockResolvedValue({ success: false, error: 'Service down' });
      jest.spyOn(tester, 'readinessCheck').mockResolvedValue({ success: false, error: 'Not ready' });
      jest.spyOn(tester, 'performanceCheck').mockResolvedValue({ success: true, loadTime: 500 });
      jest.spyOn(tester, 'testSecurityHeaders').mockResolvedValue({ success: true });

      const result = await tester.testBlueGreenDeployment();

      expect(result.criticalFailures).toBe(2);
      expect(result.passed).toBe(false);
    });
  });

  describe('testDeploymentWorkflow', () => {
    test('should run complete deployment workflow and generate summary', async () => {
      jest.spyOn(tester, 'testBlueGreenDeployment').mockResolvedValue({
        strategy: 'blue-green',
        totalTests: 5,
        passed: 5,
        failed: 0,
        criticalFailures: 0,
        passed: true
      });

      jest.spyOn(tester, 'testRollbackSimulation').mockResolvedValue({
        success: true,
        message: 'Rollback logic functional'
      });

      const result = await tester.testDeploymentWorkflow();

      expect(result.totalSuites).toBe(2);
      expect(result.overallSuccess).toBe(true);
      expect(result.passRate).toBe(100);
      expect(result.deploymentStrategy).toBe('blue-green');
      expect(result.environments).toBeDefined();
    });
  });

  describe('generateReport', () => {
    test('should generate JSON report with recommendations', async () => {
      const mockResults = {
        overallSuccess: true,
        passRate: 95,
        totalExecutionTime: 120000,
        suiteResults: []
      };

      // Mock fs.writeFileSync
      const mockWriteFileSync = jest.fn();
      jest.doMock('fs', () => ({
        writeFileSync: mockWriteFileSync
      }));

      const report = await tester.generateReport(mockResults, 'test-report.json');

      expect(report.metadata.testType).toBe('Deployment Strategy Automation');
      expect(report.results).toBe(mockResults);
      expect(mockWriteFileSync).toHaveBeenCalledWith('test-report.json', expect.any(String));
    });
  });

  describe('generateRecommendations', () => {
    test('should generate appropriate recommendations for failed tests', () => {
      const failedResults = {
        overallSuccess: false,
        passRate: 60,
        totalExecutionTime: 400000,
        suiteResults: [
          { success: false },
          { success: true }
        ]
      };

      const recommendations = tester.generateRecommendations(failedResults);

      expect(recommendations).toContain('🚨 Fix critical deployment issues before production deployment');
      expect(recommendations).toContain('⚠️ Improve deployment reliability and monitoring');
      expect(recommendations).toContain('⏱️ Optimize test execution time for faster feedback');
    });

    test('should not generate recommendations for successful tests', () => {
      const successfulResults = {
        overallSuccess: true,
        passRate: 100,
        totalExecutionTime: 120000,
        suiteResults: [
          { success: true },
          { success: true }
        ]
      };

      const recommendations = tester.generateRecommendations(successfulResults);

      expect(recommendations).toHaveLength(0);
    });
  });

  describe('Edge Cases', () => {
    test('should handle network timeouts gracefully', async () => {
      jest.spyOn(tester, 'makeRequest').mockRejectedValue(new Error('Request timeout'));

      const result = await tester.healthCheck('http://localhost:3000', 1);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Health check failed after all retries');
    });

    test('should handle malformed JSON responses', async () => {
      const mockResponse = {
        statusCode: 200,
        body: 'invalid json'
      };

      jest.spyOn(tester, 'makeRequest').mockResolvedValue(mockResponse);

      const result = await tester.healthCheck('http://localhost:3000');

      expect(result.success).toBe(false);
    });

    test('should handle empty test suites', async () => {
      const mockResults = {
        overallSuccess: true,
        totalSuites: 0,
        totalTests: 0,
        passedTests: 0,
        failedTests: 0
      };

      const recommendations = tester.generateRecommendations(mockResults);

      expect(recommendations).toHaveLength(0);
    });
  });
});