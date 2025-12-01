#!/usr/bin/env node

/**
 * 简化的CI/CD安全扫描脚本
 *
 * 功能:
 * 1. 基本的npm依赖扫描
 * 2. 生成简化的安全报告
 * 3. CI/CD友好的输出格式
 */

const fs = require('fs');
const path = require('path');

class CICDSecurityScanner {
  constructor() {
    this.projectRoot = process.cwd();
    this.reportPath = path.join(this.projectRoot, 'security-reports');
    this.ensureReportDirectory();
  }

  /**
   * 确保报告目录存在
   */
  ensureReportDirectory() {
    if (!fs.existsSync(this.reportPath)) {
      fs.mkdirSync(this.reportPath, { recursive: true });
    }
  }

  /**
   * 执行基本的安全检查
   */
  async runBasicSecurityCheck() {
    console.log('🔍 Starting basic security scan...');

    try {
      // 检查package.json是否存在
      const packageJsonPath = path.join(this.projectRoot, 'package.json');
      if (!fs.existsSync(packageJsonPath)) {
        console.log('❌ package.json not found');
        return { success: false, issues: ['package.json not found'] };
      }

      const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
      const dependencies = packageJson.dependencies || {};
      const devDependencies = packageJson.devDependencies || {};

      // 基本的安全检查
      const securityIssues = [];

      // 检查是否有已知的不安全包（简化版）
      const knownInsecurePackages = [
        'lodash@<4.17.21',
        'request@<2.88.2',
        'axios@<0.21.1',
        'node-forge@<1.3.0'
      ];

      for (const [pkg, version] of Object.entries({...dependencies, ...devDependencies})) {
        for (const insecurePkg of knownInsecurePackages) {
          const [insecureName, insecureVersion] = insecurePkg.split('@');
          if (pkg === insecureName && this.compareVersions(version, insecureVersion) < 0) {
            securityIssues.push(`${pkg}@${version} - Known vulnerable version, should upgrade to ${insecureVersion}`);
          }
        }
      }

      // 生成报告
      const report = {
        timestamp: new Date().toISOString(),
        summary: {
          totalDependencies: Object.keys(dependencies).length + Object.keys(devDependencies).length,
          securityIssues: securityIssues.length,
          status: securityIssues.length === 0 ? 'PASS' : 'FAIL'
        },
        issues: securityIssues
      };

      // 保存报告
      const reportPath = path.join(this.reportPath, 'security-scan-report.json');
      fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

      console.log(`📄 Security report saved to: ${reportPath}`);
      console.log(`📊 Dependencies scanned: ${report.summary.totalDependencies}`);
      console.log(`🔍 Security issues found: ${report.summary.securityIssues}`);

      if (securityIssues.length > 0) {
        console.log('\n❌ Security Issues:');
        securityIssues.forEach(issue => console.log(`  • ${issue}`));
      } else {
        console.log('\n✅ No obvious security issues detected');
      }

      return report;
    } catch (error) {
      console.error('❌ Security scan failed:', error.message);
      return { success: false, error: error.message };
    }
  }

  /**
   * 简单的版本比较
   */
  compareVersions(version1, version2) {
    const v1parts = version1.replace(/^[\^~]/, '').split('.').map(Number);
    const v2parts = version2.split('.').map(Number);

    for (let i = 0; i < Math.max(v1parts.length, v2parts.length); i++) {
      const v1part = v1parts[i] || 0;
      const v2part = v2parts[i] || 0;

      if (v1part > v2part) return 1;
      if (v1part < v2part) return -1;
    }
    return 0;
  }

  /**
   * 生成markdown报告
   */
  generateMarkdownReport(report) {
    const markdown = `# 📊 Security Scan Report

**Generated:** ${new Date().toISOString()}

## Summary

- **Total Dependencies:** ${report.summary.totalDependencies}
- **Security Issues Found:** ${report.summary.securityIssues}
- **Status:** ${report.summary.status === 'PASS' ? '✅ PASS' : '❌ FAIL'}

## Security Issues

${report.issues.length > 0 ?
  report.issues.map(issue => `- ❌ ${issue}`).join('\n') :
  '✅ No security issues detected'
}

## Recommendations

${report.summary.securityIssues > 0 ?
  '1. Update vulnerable dependencies immediately\n2. Review alternative packages if available\n3. Test thoroughly after updates' :
  'Continue monitoring dependencies regularly'
}
`;

    const markdownPath = path.join(this.reportPath, 'security-summary.md');
    fs.writeFileSync(markdownPath, markdown);
    return markdownPath;
  }
}

// 主执行逻辑
if (require.main === module) {
  const scanner = new CICDSecurityScanner();
  scanner.runBasicSecurityCheck()
    .then(report => {
      if (report.summary && report.summary.status === 'FAIL') {
        console.log('\n❌ Security scan failed - critical issues found');
        process.exit(1);
      } else {
        console.log('\n✅ Security scan completed successfully');
        // 生成markdown报告
        scanner.generateMarkdownReport(report);
      }
    })
    .catch(error => {
      console.error('❌ Security scan error:', error);
      process.exit(1);
    });
}

module.exports = CICDSecurityScanner;