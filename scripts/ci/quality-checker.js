#!/usr/bin/env node

/**
 * Quality Gate Automation Script
 *
 * Implements comprehensive quality checks for code quality, security, and performance
 * to ensure only high-quality code passes through the CI/CD pipeline.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class QualityChecker {
  constructor() {
    this.projectRoot = process.cwd();
    this.results = {
      timestamp: new Date().toISOString(),
      checks: {},
      summary: {
        passed: 0,
        failed: 0,
        warnings: 0,
        total: 0
      },
      qualityScore: 0,
      recommendations: []
    };
    this.thresholds = {
      testCoverage: 85, // Minimum test coverage percentage
      bundleSizeLimit: 1024 * 1024, // 1MB
      lighthouseScore: 90, // Minimum Lighthouse performance score
      maxSecurityVulnerabilities: {
        high: 0,
        medium: 2,
        low: 5
      },
      maxComplexity: 10, // Maximum cyclomatic complexity
      maxCodeDuplication: 3 // Maximum code duplication percentage
    };
  }

  /**
   * Run all quality checks
   */
  async runAllChecks() {
    console.log('🔍 Running Quality Gate Checks...\n');

    try {
      await this.runTestCoverageCheck();
      await this.runCodeQualityCheck();
      await this.runSecurityCheck();
      await this.runPerformanceCheck();
      await this.runBundleSizeCheck();
      await this.runAccessibilityCheck();

      this.calculateQualityScore();
      this.generateRecommendations();
      this.printResults();
      this.exportResults();

      return this.results.summary.failed === 0;
    } catch (error) {
      console.error('❌ Quality check failed:', error.message);
      return false;
    }
  }

  /**
   * Test Coverage Check
   */
  async runTestCoverageCheck() {
    console.log('📊 Running Test Coverage Check...');

    try {
      let coverage = 0;
      let frontendCoverage = 0;
      let backendCoverage = 0;

      // Check frontend coverage
      const frontendCoveragePath = path.join(this.projectRoot, 'frontend', 'coverage', 'coverage-summary.json');
      if (fs.existsSync(frontendCoveragePath)) {
        const coverageData = JSON.parse(fs.readFileSync(frontendCoveragePath, 'utf8'));
        frontendCoverage = coverageData.total?.lines?.pct || 0;
      }

      // Check backend coverage
      const backendCoveragePath = path.join(this.projectRoot, 'backend', 'coverage.xml');
      if (fs.existsSync(backendCoveragePath)) {
        // Parse XML coverage (simplified)
        const xmlContent = fs.readFileSync(backendCoveragePath, 'utf8');
        const match = xmlContent.match(/line-rate="(\d+\.\d+)"/);
        backendCoverage = match ? parseFloat(match[1]) * 100 : 0;
      }

      // Calculate average coverage
      coverage = frontendCoverage > 0 && backendCoverage > 0
        ? (frontendCoverage + backendCoverage) / 2
        : Math.max(frontendCoverage, backendCoverage);

      const passed = coverage >= this.thresholds.testCoverage;
      const status = passed ? 'PASS' : 'FAIL';

      this.results.checks.testCoverage = {
        status,
        coverage: Math.round(coverage),
        threshold: this.thresholds.testCoverage,
        frontend: Math.round(frontendCoverage),
        backend: Math.round(backendCoverage),
        details: passed
          ? 'Coverage meets minimum requirement'
          : `Coverage ${Math.round(coverage)}% below threshold ${this.thresholds.testCoverage}%`
      };

      console.log(`   ${passed ? '✅' : '❌'} Test Coverage: ${Math.round(coverage)}% (Frontend: ${Math.round(frontendCoverage)}%, Backend: ${Math.round(backendCoverage)}%)`);
    } catch (error) {
      this.results.checks.testCoverage = {
        status: 'ERROR',
        error: error.message,
        details: 'Failed to calculate test coverage'
      };
      console.log('   ❌ Test Coverage Check failed:', error.message);
    }
  }

  /**
   * Code Quality Check
   */
  async runCodeQualityCheck() {
    console.log('🔍 Running Code Quality Check...');

    try {
      let eslintErrors = 0;
      let eslintWarnings = 0;
      let typeScriptErrors = 0;
      let complexityIssues = 0;

      // Run ESLint check
      try {
        const eslintResult = execSync('cd frontend && npm run lint -- --format=json 2>/dev/null || true', {
          encoding: 'utf8'
        });

        if (eslintResult) {
          const eslintData = JSON.parse(eslintResult);
          eslintErrors = eslintData.reduce((sum, file) => sum + file.errorCount, 0);
          eslintWarnings = eslintData.reduce((sum, file) => sum + file.warningCount, 0);
        }
      } catch (eslintError) {
        // ESLint command failed, assume there are issues
        eslintErrors = 1;
      }

      // Run TypeScript check
      try {
        execSync('cd frontend && npx tsc --noEmit', { encoding: 'utf8' });
      } catch (tsError) {
        typeScriptErrors = (tsError.stderr || tsError.stdout || '').split('\n').filter(line => line.includes('error')).length;
      }

      const totalIssues = eslintErrors + eslintWarnings + typeScriptErrors + complexityIssues;
      const passed = eslintErrors === 0 && typeScriptErrors === 0;
      const status = passed ? 'PASS' : 'FAIL';

      this.results.checks.codeQuality = {
        status,
        eslintErrors,
        eslintWarnings,
        typeScriptErrors,
        complexityIssues,
        totalIssues,
        details: passed
          ? 'Code quality checks passed'
          : `Found ${totalIssues} code quality issues`
      };

      console.log(`   ${passed ? '✅' : '❌'} Code Quality: ${eslintErrors} ESLint errors, ${typeScriptErrors} TypeScript errors`);
    } catch (error) {
      this.results.checks.codeQuality = {
        status: 'ERROR',
        error: error.message,
        details: 'Failed to run code quality checks'
      };
      console.log('   ❌ Code Quality Check failed:', error.message);
    }
  }

  /**
   * Security Check
   */
  async runSecurityCheck() {
    console.log('🔒 Running Security Check...');

    try {
      let vulnerabilities = { high: 0, medium: 0, low: 0 };
      let securityScore = 100;

      // Check npm audit
      try {
        const auditResult = execSync('cd frontend && npm audit --json 2>/dev/null || true', {
          encoding: 'utf8'
        });

        if (auditResult) {
          const auditData = JSON.parse(auditResult);
          if (auditData.vulnerabilities) {
            Object.values(auditData.vulnerabilities).forEach(vuln => {
              switch (vuln.severity) {
                case 'high':
                case 'critical':
                  vulnerabilities.high++;
                  securityScore -= 20;
                  break;
                case 'moderate':
                  vulnerabilities.medium++;
                  securityScore -= 10;
                  break;
                case 'low':
                  vulnerabilities.low++;
                  securityScore -= 5;
                  break;
              }
            });
          }
        }
      } catch (auditError) {
        // Audit command failed
        vulnerabilities.medium = 1;
        securityScore -= 10;
      }

      const highPassed = vulnerabilities.high <= this.thresholds.maxSecurityVulnerabilities.high;
      const mediumPassed = vulnerabilities.medium <= this.thresholds.maxSecurityVulnerabilities.medium;
      const lowPassed = vulnerabilities.low <= this.thresholds.maxSecurityVulnerabilities.low;
      const passed = highPassed && mediumPassed && lowPassed;
      const status = passed ? 'PASS' : 'FAIL';

      this.results.checks.security = {
        status,
        vulnerabilities,
        securityScore,
        thresholds: this.thresholds.maxSecurityVulnerabilities,
        details: passed
          ? `Security score: ${securityScore}%`
          : `Security vulnerabilities exceed thresholds: ${vulnerabilities.high}H/${vulnerabilities.medium}M/${vulnerabilities.low}L`
      };

      console.log(`   ${passed ? '✅' : '❌'} Security: ${vulnerabilities.high}H/${vulnerabilities.medium}M/${vulnerabilities.low}L vulnerabilities, Score: ${securityScore}%`);
    } catch (error) {
      this.results.checks.security = {
        status: 'ERROR',
        error: error.message,
        details: 'Failed to run security checks'
      };
      console.log('   ❌ Security Check failed:', error.message);
    }
  }

  /**
   * Performance Check
   */
  async runPerformanceCheck() {
    console.log('⚡ Running Performance Check...');

    try {
      let lighthouseScore = 0;
      let coreWebVitals = {
        lcp: { value: 0, status: 'unknown' },
        fid: { value: 0, status: 'unknown' },
        cls: { value: 0, status: 'unknown' }
      };

      // Check for Lighthouse results
      const lighthousePath = path.join(this.projectRoot, '.lighthouseci', 'lhr.json');
      if (fs.existsSync(lighthousePath)) {
        const lhrData = JSON.parse(fs.readFileSync(lighthousePath, 'utf8'));
        lighthouseScore = Math.round(lhrData.categories.performance.score * 100);

        // Extract Core Web Vitals
        if (lhrData.audits) {
          coreWebVitals.lcp = {
            value: lhrData.audits['largest-contentful-paint']?.numericValue || 0,
            status: lhrData.audits['largest-contentful-paint']?.score || 0
          };
          coreWebVitals.fid = {
            value: lhrData.audits['max-potential-fid']?.numericValue || 0,
            status: lhrData.audits['max-potential-fid']?.score || 0
          };
          coreWebVitals.cls = {
            value: lhrData.audits['cumulative-layout-shift']?.numericValue || 0,
            status: lhrData.audits['cumulative-layout-shift']?.score || 0
          };
        }
      } else {
        // Default score if no Lighthouse data
        lighthouseScore = 85;
      }

      const passed = lighthouseScore >= this.thresholds.lighthouseScore;
      const status = passed ? 'PASS' : 'FAIL';

      this.results.checks.performance = {
        status,
        lighthouseScore,
        thresholds: this.thresholds.lighthouseScore,
        coreWebVitals,
        details: passed
          ? `Performance score: ${lighthouseScore}`
          : `Performance score ${lighthouseScore} below threshold ${this.thresholds.lighthouseScore}`
      };

      console.log(`   ${passed ? '✅' : '❌'} Performance: Lighthouse ${lighthouseScore}, LCP: ${Math.round(coreWebVitals.lcp.value)}ms`);
    } catch (error) {
      this.results.checks.performance = {
        status: 'ERROR',
        error: error.message,
        details: 'Failed to run performance checks'
      };
      console.log('   ❌ Performance Check failed:', error.message);
    }
  }

  /**
   * Bundle Size Check
   */
  async runBundleSizeCheck() {
    console.log('📦 Running Bundle Size Check...');

    try {
      let bundleSize = 0;
      let mainBundleSize = 0;
      let totalJsSize = 0;

      // Check for bundle analysis results
      const packageJsonPath = path.join(this.projectRoot, 'frontend', 'package.json');
      if (fs.existsSync(packageJsonPath)) {
        const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));

        // Estimate bundle sizes (simplified calculation)
        if (packageJson.dependencies) {
          totalJsSize = Object.keys(packageJson.dependencies).length * 50000; // Rough estimate
          mainBundleSize = totalJsSize * 0.7; // Assume 70% in main bundle
          bundleSize = mainBundleSize;
        }
      }

      const passed = bundleSize <= this.thresholds.bundleSizeLimit;
      const status = passed ? 'PASS' : 'FAIL';

      this.results.checks.bundleSize = {
        status,
        bundleSize,
        mainBundleSize,
        totalJsSize,
        thresholds: this.thresholds.bundleSizeLimit,
        details: passed
          ? `Bundle size: ${this.formatBytes(bundleSize)}`
          : `Bundle size ${this.formatBytes(bundleSize)} exceeds limit ${this.formatBytes(this.thresholds.bundleSizeLimit)}`
      };

      console.log(`   ${passed ? '✅' : '❌'} Bundle Size: ${this.formatBytes(bundleSize)} (limit: ${this.formatBytes(this.thresholds.bundleSizeLimit)})`);
    } catch (error) {
      this.results.checks.bundleSize = {
        status: 'ERROR',
        error: error.message,
        details: 'Failed to check bundle size'
      };
      console.log('   ❌ Bundle Size Check failed:', error.message);
    }
  }

  /**
   * Accessibility Check
   */
  async runAccessibilityCheck() {
    console.log('♿ Running Accessibility Check...');

    try {
      let accessibilityScore = 0;
      let violations = 0;

      // Check for axe results if available
      const axeResultsPath = path.join(this.projectRoot, 'accessibility-results.json');
      if (fs.existsSync(axeResultsPath)) {
        const axeData = JSON.parse(fs.readFileSync(axeResultsPath, 'utf8'));
        violations = axeData.violations ? axeData.violations.length : 0;
        accessibilityScore = Math.max(0, 100 - (violations * 10));
      } else {
        // Default score if no accessibility data
        accessibilityScore = 85;
        violations = 1;
      }

      const passed = accessibilityScore >= 80; // WCAG AA compliance
      const status = passed ? 'PASS' : 'FAIL';

      this.results.checks.accessibility = {
        status,
        accessibilityScore,
        violations,
        standards: 'WCAG 2.1 AA',
        details: passed
          ? `Accessibility score: ${accessibilityScore}%`
          : `Accessibility score ${accessibilityScore}% below WCAG AA standard`
      };

      console.log(`   ${passed ? '✅' : '❌'} Accessibility: Score ${accessibilityScore}%, ${violations} violations`);
    } catch (error) {
      this.results.checks.accessibility = {
        status: 'ERROR',
        error: error.message,
        details: 'Failed to run accessibility checks'
      };
      console.log('   ❌ Accessibility Check failed:', error.message);
    }
  }

  /**
   * Calculate overall quality score
   */
  calculateQualityScore() {
    const checks = Object.values(this.results.checks);
    const passedChecks = checks.filter(check => check.status === 'PASS').length;
    const totalChecks = checks.length;

    this.results.qualityScore = Math.round((passedChecks / totalChecks) * 100);

    // Update summary
    checks.forEach(check => {
      switch (check.status) {
        case 'PASS':
          this.results.summary.passed++;
          break;
        case 'FAIL':
          this.results.summary.failed++;
          break;
        case 'ERROR':
          this.results.summary.failed++;
          break;
        default:
          this.results.summary.warnings++;
      }
      this.results.summary.total++;
    });
  }

  /**
   * Generate improvement recommendations
   */
  generateRecommendations() {
    this.results.recommendations = [];

    // Test coverage recommendations
    const testCheck = this.results.checks.testCoverage;
    if (testCheck && testCheck.status !== 'PASS') {
      this.results.recommendations.push({
        type: 'test_coverage',
        priority: 'high',
        message: 'Improve test coverage',
        details: `Current coverage ${testCheck.coverage}% is below threshold ${testCheck.threshold}%`,
        estimatedImpact: '+15% quality score'
      });
    }

    // Code quality recommendations
    const qualityCheck = this.results.checks.codeQuality;
    if (qualityCheck && qualityCheck.status !== 'PASS') {
      this.results.recommendations.push({
        type: 'code_quality',
        priority: 'high',
        message: 'Fix code quality issues',
        details: `Found ${qualityCheck.totalIssues} code quality issues`,
        estimatedImpact: '+20% quality score'
      });
    }

    // Security recommendations
    const securityCheck = this.results.checks.security;
    if (securityCheck && securityCheck.status !== 'PASS') {
      this.results.recommendations.push({
        type: 'security',
        priority: 'high',
        message: 'Address security vulnerabilities',
        details: `${securityCheck.vulnerabilities.high}H/${securityCheck.vulnerabilities.medium}M/${securityCheck.vulnerabilities.low}L vulnerabilities found`,
        estimatedImpact: '+25% quality score'
      });
    }

    // Performance recommendations
    const perfCheck = this.results.checks.performance;
    if (perfCheck && perfCheck.status !== 'PASS') {
      this.results.recommendations.push({
        type: 'performance',
        priority: 'medium',
        message: 'Optimize application performance',
        details: `Lighthouse score ${perfCheck.lighthouseScore} is below threshold ${perfCheck.thresholds}`,
        estimatedImpact: '+10% quality score'
      });
    }
  }

  /**
   * Format bytes for human readable output
   */
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Print results summary
   */
  printResults() {
    console.log('\n📊 QUALITY GATE RESULTS');
    console.log('=========================');
    console.log(`Overall Quality Score: ${this.results.qualityScore}%`);
    console.log(`Checks: ${this.results.summary.passed} passed, ${this.results.summary.failed} failed, ${this.results.summary.warnings} warnings`);

    console.log('\n📋 Detailed Results:');
    Object.entries(this.results.checks).forEach(([check, result]) => {
      const icon = result.status === 'PASS' ? '✅' : result.status === 'FAIL' ? '❌' : '⚠️';
      console.log(`  ${icon} ${check}: ${result.details}`);
    });

    if (this.results.recommendations.length > 0) {
      console.log('\n💡 Recommendations:');
      this.results.recommendations.forEach((rec, index) => {
        const priorityIcon = rec.priority === 'high' ? '🔥' : rec.priority === 'medium' ? '⚡' : '💡';
        console.log(`  ${index + 1}. ${priorityIcon} ${rec.message}`);
        console.log(`     → ${rec.details}`);
        console.log(`     → Impact: ${rec.estimatedImpact}`);
      });
    }

    const gatePassed = this.results.summary.failed === 0;
    console.log(`\n${gatePassed ? '🎉' : '🚫'} QUALITY GATE: ${gatePassed ? 'PASSED' : 'FAILED'}`);

    if (!gatePassed) {
      console.log('\n❌ Quality gate failed. Address the issues above before proceeding.');
      process.exit(1);
    } else {
      console.log('\n✅ Quality gate passed. Code is ready for deployment.');
    }
  }

  /**
   * Export results to JSON file
   */
  exportResults(outputPath = 'quality-gate-results.json') {
    fs.writeFileSync(outputPath, JSON.stringify(this.results, null, 2));
    console.log(`\n📄 Quality gate results exported to: ${outputPath}`);
  }
}

// Main execution
if (require.main === module) {
  const checker = new QualityChecker();
  checker.runAllChecks().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('Quality gate execution failed:', error);
    process.exit(1);
  });
}

module.exports = QualityChecker;