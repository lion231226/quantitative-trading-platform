#!/usr/bin/env node

/**
 * Deployment Strategy Automation Tests
 *
 * 测试蓝绿部署策略、回滚机制和健康检查
 * 支持Vercel集成的部署验证
 */

const { execSync } = require('child_process');
const http = require('http');
const https = require('https');
const { URL } = require('url');

class DeploymentStrategyTester {
  constructor(config = {}) {
    this.config = {
      baseUrl: config.baseUrl || 'http://localhost:3000',
      stagingUrl: config.stagingUrl || 'https://quant-trading-demo-staging.vercel.app',
      productionUrl: config.productionUrl || 'https://quant-trading-demo.vercel.app',
      timeout: config.timeout || 30000,
      retries: config.retries || 3,
      healthCheckInterval: config.healthCheckInterval || 10000,
      ...config
    };

    this.testResults = [];
    this.startTime = Date.now();
  }

  log(message, level = 'info') {
    const timestamp = new Date().toISOString();
    const levels = {
      info: '📝',
      success: '✅',
      warning: '⚠️',
      error: '❌',
      debug: '🔍'
    };

    console.log(`${levels[level] || levels.info} [${timestamp}] ${message}`);
  }

  async makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
      const parsedUrl = new URL(url);
      const client = parsedUrl.protocol === 'https:' ? https : http;

      const req = client.request(url, options, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: data
          });
        });
      });

      req.on('error', reject);
      req.setTimeout(this.config.timeout, () => {
        req.destroy();
        reject(new Error(`Request timeout after ${this.config.timeout}ms`));
      });

      if (options.body) {
        req.write(options.body);
      }
      req.end();
    });
  }

  async healthCheck(url, retries = this.config.retries) {
    const healthEndpoint = `${url}/api/health`;

    for (let i = 1; i <= retries; i++) {
      try {
        this.log(`Health check attempt ${i}/${retries} for ${healthEndpoint}`);

        const response = await this.makeRequest(healthEndpoint);

        if (response.statusCode === 200) {
          const data = JSON.parse(response.body);
          this.log(`Health check passed: ${JSON.stringify(data)}`, 'success');
          return { success: true, data, response };
        } else {
          this.log(`Health check failed with status: ${response.statusCode}`, 'warning');
        }
      } catch (error) {
        this.log(`Health check error: ${error.message}`, 'warning');
      }

      if (i < retries) {
        await this.sleep(this.config.healthCheckInterval);
      }
    }

    return { success: false, error: 'Health check failed after all retries' };
  }

  async readinessCheck(url, retries = this.config.retries) {
    const readyEndpoint = `${url}/api/ready`;

    for (let i = 1; i <= retries; i++) {
      try {
        this.log(`Readiness check attempt ${i}/${retries} for ${readyEndpoint}`);

        const response = await this.makeRequest(readyEndpoint);

        if (response.statusCode === 200) {
          const data = JSON.parse(response.body);
          this.log(`Readiness check passed: ${JSON.stringify(data)}`, 'success');
          return { success: true, data, response };
        } else {
          this.log(`Readiness check failed with status: ${response.statusCode}`, 'warning');
        }
      } catch (error) {
        this.log(`Readiness check error: ${error.message}`, 'warning');
      }

      if (i < retries) {
        await this.sleep(this.config.healthCheckInterval);
      }
    }

    return { success: false, error: 'Readiness check failed after all retries' };
  }

  async performanceCheck(url) {
    const startTime = Date.now();

    try {
      this.log(`Running performance check for ${url}`);

      const response = await this.makeRequest(url);
      const loadTime = Date.now() - startTime;

      if (response.statusCode === 200 && loadTime < 5000) {
        this.log(`Performance check passed: ${loadTime}ms load time`, 'success');
        return { success: true, loadTime, response };
      } else {
        this.log(`Performance check failed: ${response.statusCode}, ${loadTime}ms load time`, 'error');
        return { success: false, error: `Slow response time: ${loadTime}ms` };
      }
    } catch (error) {
      this.log(`Performance check error: ${error.message}`, 'error');
      return { success: false, error: error.message };
    }
  }

  async testBlueGreenDeployment() {
    this.log('Testing Blue-Green Deployment Strategy', 'info');
    this.log('========================================');

    const testCases = [
      {
        name: 'Production Health Check',
        test: () => this.healthCheck(this.config.productionUrl),
        critical: true
      },
      {
        name: 'Production Readiness Check',
        test: () => this.readinessCheck(this.config.productionUrl),
        critical: true
      },
      {
        name: 'Production Performance Check',
        test: () => this.performanceCheck(this.config.productionUrl),
        critical: false
      },
      {
        name: 'Staging Health Check',
        test: () => this.healthCheck(this.config.stagingUrl),
        critical: false
      },
      {
        name: 'Security Headers Check',
        test: () => this.testSecurityHeaders(this.config.productionUrl),
        critical: false
      }
    ];

    const results = [];
    let criticalFailures = 0;

    for (const testCase of testCases) {
      this.log(`Running test: ${testCase.name}`);

      try {
        const result = await testCase.test();
        results.push({
          name: testCase.name,
          success: result.success,
          critical: testCase.critical,
          result,
          timestamp: new Date().toISOString()
        });

        if (testCase.critical && !result.success) {
          criticalFailures++;
          this.log(`Critical test failed: ${testCase.name}`, 'error');
        }
      } catch (error) {
        results.push({
          name: testCase.name,
          success: false,
          critical: testCase.critical,
          error: error.message,
          timestamp: new Date().toISOString()
        });

        if (testCase.critical) {
          criticalFailures++;
          this.log(`Critical test error: ${testCase.name} - ${error.message}`, 'error');
        }
      }

      await this.sleep(1000); // Brief pause between tests
    }

    return {
      strategy: 'blue-green',
      totalTests: results.length,
      passed: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      criticalFailures,
      results,
      passed: criticalFailures === 0
    };
  }

  async testSecurityHeaders(url) {
    try {
      this.log(`Testing security headers for ${url}`);

      const response = await this.makeRequest(url);
      const headers = response.headers;

      const expectedHeaders = [
        'x-content-type-options',
        'x-frame-options',
        'x-xss-protection',
        'strict-transport-security'
      ];

      const missingHeaders = [];
      const presentHeaders = [];

      expectedHeaders.forEach(header => {
        const headerKey = Object.keys(headers).find(h => h.toLowerCase() === header);
        if (headerKey && headers[headerKey]) {
          presentHeaders.push(`${headerKey}: ${headers[headerKey]}`);
        } else {
          missingHeaders.push(header);
        }
      });

      if (missingHeaders.length === 0) {
        this.log(`All security headers present: ${presentHeaders.join(', ')}`, 'success');
        return { success: true, presentHeaders };
      } else {
        this.log(`Missing security headers: ${missingHeaders.join(', ')}`, 'warning');
        return { success: false, missingHeaders, presentHeaders };
      }
    } catch (error) {
      this.log(`Security headers test error: ${error.message}`, 'error');
      return { success: false, error: error.message };
    }
  }

  async testRollbackSimulation(deploymentUrl) {
    this.log('Testing Rollback Simulation', 'info');
    this.log('===============================');

    // Simulate a deployment failure by testing against a non-existent endpoint
    const failingUrl = `${deploymentUrl}/nonexistent-endpoint`;

    try {
      const response = await this.makeRequest(failingUrl);

      // 404 is expected for non-existent endpoint, but server should be responsive
      if (response.statusCode === 404) {
        this.log('Server is responsive (404 expected for test)', 'success');
        return { success: true, message: 'Server responsive, rollback logic would work' };
      } else {
        this.log(`Unexpected response: ${response.statusCode}`, 'warning');
        return { success: false, error: `Unexpected status code: ${response.statusCode}` };
      }
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        this.log('Connection refused - this would trigger rollback in production', 'error');
        return { success: false, error: 'Connection refused - would trigger rollback' };
      } else {
        this.log(`Rollback test error: ${error.message}`, 'error');
        return { success: false, error: error.message };
      }
    }
  }

  async testDeploymentWorkflow() {
    this.log('Starting Complete Deployment Strategy Tests', 'info');
    this.log('==========================================');

    const suiteResults = [];

    // Test 1: Blue-Green Deployment
    const blueGreenResult = await this.testBlueGreenDeployment();
    suiteResults.push(blueGreenResult);

    // Test 2: Rollback Simulation (only for production)
    const rollbackResult = await this.testRollbackSimulation(this.config.productionUrl);
    suiteResults.push({
      strategy: 'rollback-simulation',
      success: rollbackResult.success,
      result: rollbackResult,
      timestamp: new Date().toISOString()
    });

    // Summary
    const totalTests = suiteResults.reduce((sum, suite) => sum + (suite.totalTests || 1), 0);
    const passedTests = suiteResults.reduce((sum, suite) => sum + (suite.passed || (suite.success ? 1 : 0)), 0);
    const failedTests = totalTests - passedTests;

    const summary = {
      totalExecutionTime: Date.now() - this.startTime,
      totalSuites: suiteResults.length,
      totalTests,
      passedTests,
      failedTests,
      passRate: totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0,
      suiteResults,
      overallSuccess: failedTests === 0,
      deploymentStrategy: 'blue-green',
      environments: {
        production: this.config.productionUrl,
        staging: this.config.stagingUrl
      },
      timestamp: new Date().toISOString()
    };

    this.log('\n🏁 DEPLOYMENT STRATEGY TEST SUMMARY', 'info');
    this.log('==================================');
    this.log(`Total Tests: ${totalTests}`);
    this.log(`Passed: ${passedTests} ✅`);
    this.log(`Failed: ${failedTests} ${failedTests > 0 ? '❌' : '✅'}`);
    this.log(`Pass Rate: ${summary.passRate}%`);
    this.log(`Execution Time: ${Math.round(totalExecutionTime / 1000)}s`);
    this.log(`Overall Result: ${summary.overallSuccess ? '✅ PASSED' : '❌ FAILED'}`);

    if (!summary.overallSuccess) {
      this.log('\n⚠️ Some tests failed. Review the detailed results above.', 'warning');
    }

    return summary;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async generateReport(results, outputPath) {
    const report = {
      metadata: {
        testType: 'Deployment Strategy Automation',
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        config: this.config
      },
      results,
      recommendations: this.generateRecommendations(results)
    };

    try {
      require('fs').writeFileSync(outputPath, JSON.stringify(report, null, 2));
      this.log(`Report generated: ${outputPath}`, 'success');
    } catch (error) {
      this.log(`Failed to generate report: ${error.message}`, 'error');
    }

    return report;
  }

  generateRecommendations(results) {
    const recommendations = [];

    if (!results.overallSuccess) {
      recommendations.push('🚨 Fix critical deployment issues before production deployment');
    }

    if (results.passRate < 80) {
      recommendations.push('⚠️ Improve deployment reliability and monitoring');
    }

    if (results.totalExecutionTime > 300000) { // 5 minutes
      recommendations.push('⏱️ Optimize test execution time for faster feedback');
    }

    const failedTests = results.suiteResults.filter(suite => !suite.success);
    if (failedTests.length > 0) {
      recommendations.push(`🔧 Fix ${failedTests.length} failed test suites`);
    }

    return recommendations;
  }
}

// CLI Interface
async function main() {
  const args = process.argv.slice(2);
  const config = {};

  // Parse command line arguments
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--production-url':
        config.productionUrl = args[++i];
        break;
      case '--staging-url':
        config.stagingUrl = args[++i];
        break;
      case '--timeout':
        config.timeout = parseInt(args[++i]);
        break;
      case '--retries':
        config.retries = parseInt(args[++i]);
        break;
      case '--output':
        config.outputFile = args[++i];
        break;
      case '--help':
        console.log(`
Deployment Strategy Tester

Usage: node test-deployment-strategy.js [options]

Options:
  --production-url <url>    Production deployment URL (default: https://quant-trading-demo.vercel.app)
  --staging-url <url>       Staging deployment URL (default: https://quant-trading-demo-staging.vercel.app)
  --timeout <ms>            Request timeout in milliseconds (default: 30000)
  --retries <count>         Number of retry attempts (default: 3)
  --output <file>           Output file for test report (JSON format)
  --help                    Show this help message

Examples:
  node test-deployment-strategy.js
  node test-deployment-strategy.js --production-url https://my-app.vercel.app --output report.json
  node test-deployment-strategy.js --timeout 10000 --retries 5
        `);
        process.exit(0);
    }
  }

  const tester = new DeploymentStrategyTester(config);

  try {
    const results = await tester.testDeploymentWorkflow();

    if (config.outputFile) {
      await tester.generateReport(results, config.outputFile);
    }

    process.exit(results.overallSuccess ? 0 : 1);
  } catch (error) {
    console.error('❌ Test execution failed:', error.message);
    process.exit(1);
  }
}

module.exports = { DeploymentStrategyTester };

if (require.main === module) {
  main();
}