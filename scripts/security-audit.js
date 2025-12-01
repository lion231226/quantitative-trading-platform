#!/usr/bin/env node

/**
 * NPM依赖安全漏洞扫描脚本
 *
 * 功能:
 * 1. 自动扫描npm依赖漏洞
 * 2. 按严重等级分类和统计
 * 3. 在高危漏洞时阻止构建
 * 4. 生成详细的安全报告
 * 5. 支持CI/CD集成
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// 安全阈值配置
const SECURITY_THRESHOLDS = {
  critical: 0,    // 严重漏洞阈值
  high: 0,        // 高危漏洞阈值
  moderate: 2,    // 中危漏洞阈值
  low: 5,         // 低危漏洞阈值
  total: 5        // 总漏洞阈值
};

// 颜色输出函数
const colors = {
  red: (text) => `\x1b[31m${text}\x1b[0m`,
  yellow: (text) => `\x1b[33m${text}\x1b[0m`,
  green: (text) => `\x1b[32m${text}\x1b[0m`,
  blue: (text) => `\x1b[34m${text}\x1b[0m`,
  bold: (text) => `\x1b[1m${text}\x1b[0m`
};

class SecurityAuditor {
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
   * 执行npm audit扫描
   */
  async runAudit() {
    try {
      console.log(colors.blue('🔍 开始扫描依赖漏洞...'));

      const auditOutput = execSync('npm audit --json', {
        encoding: 'utf8',
        stdio: 'pipe'
      });

      return JSON.parse(auditOutput);
    } catch (error) {
      // npm audit在发现漏洞时会返回非零退出码，但仍然会输出JSON
      if (error.stdout) {
        return JSON.parse(error.stdout);
      }
      throw new Error(`安全扫描失败: ${error.message}`);
    }
  }

  /**
   * 分析漏洞报告
   */
  analyzeVulnerabilities(auditReport) {
    const vulnerabilities = auditReport.vulnerabilities || {};
    const metadata = auditReport.metadata || {};

    const analysis = {
      total: metadata.vulnerabilities?.total || 0,
      critical: 0,
      high: 0,
      moderate: 0,
      low: 0,
      info: 0,
      details: []
    };

    // 分析每个漏洞
    Object.values(vulnerabilities).forEach(vuln => {
      const severity = vuln.severity;
      analysis[severity] = (analysis[severity] || 0) + 1;

      analysis.details.push({
        name: vuln.name,
        severity: vuln.severity,
        title: vuln.title || '未知漏洞',
        url: vuln.url || '',
        isDirect: vuln.isDirect,
        fixAvailable: vuln.fixAvailable,
        via: vuln.via || []
      });
    });

    return analysis;
  }

  /**
   * 生成控制台报告
   */
  generateConsoleReport(analysis) {
    console.log('\n' + colors.bold('📊 依赖安全扫描报告'));
    console.log('='.repeat(50));

    // 总览
    console.log(`\n📈 漏洞总览:`);
    console.log(`   总计: ${analysis.total}`);

    if (analysis.critical > 0) {
      console.log(colors.red(`   🚨 严重: ${analysis.critical}`));
    }
    if (analysis.high > 0) {
      console.log(colors.red(`   ⚠️  高危: ${analysis.high}`));
    }
    if (analysis.moderate > 0) {
      console.log(colors.yellow(`   ⚠️ 中危: ${analysis.moderate}`));
    }
    if (analysis.low > 0) {
      console.log(colors.blue(`   ℹ️  低危: ${analysis.low}`));
    }

    // 详细漏洞列表
    if (analysis.details.length > 0) {
      console.log('\n🔍 漏洞详情:');
      analysis.details.forEach((vuln, index) => {
        const severityColor = this.getSeverityColor(vuln.severity);
        console.log(`\n${index + 1}. ${severityColor(vuln.severity.toUpperCase())} - ${vuln.name}`);
        console.log(`   标题: ${vuln.title}`);
        if (vuln.isDirect) {
          console.log(colors.red('   直接依赖'));
        }
        if (vuln.fixAvailable && vuln.fixAvailable.version) {
          console.log(colors.green(`   修复可用: 升级到 ${vuln.fixAvailable.version}`));
        }
        if (vuln.url) {
          console.log(`   详情: ${vuln.url}`);
        }
      });
    }
  }

  /**
   * 生成JSON报告文件
   */
  generateJsonReport(analysis) {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        total: analysis.total,
        critical: analysis.critical,
        high: analysis.high,
        moderate: analysis.moderate,
        low: analysis.low
      },
      thresholds: SECURITY_THRESHOLDS,
      compliance: this.checkCompliance(analysis),
      vulnerabilities: analysis.details
    };

    const fileName = `security-audit-${new Date().toISOString().split('T')[0]}.json`;
    const filePath = path.join(this.reportPath, fileName);

    fs.writeFileSync(filePath, JSON.stringify(report, null, 2));
    console.log(`\n📄 详细报告已保存到: ${filePath}`);

    return filePath;
  }

  /**
   * 检查安全合规性
   */
  checkCompliance(analysis) {
    const violations = [];

    if (analysis.critical > SECURITY_THRESHOLDS.critical) {
      violations.push(`严重漏洞数量超限: ${analysis.critical} > ${SECURITY_THRESHOLDS.critical}`);
    }

    if (analysis.high > SECURITY_THRESHOLDS.high) {
      violations.push(`高危漏洞数量超限: ${analysis.high} > ${SECURITY_THRESHOLDS.high}`);
    }

    if (analysis.moderate > SECURITY_THRESHOLDS.moderate) {
      violations.push(`中危漏洞数量超限: ${analysis.moderate} > ${SECURITY_THRESHOLDS.moderate}`);
    }

    if (analysis.low > SECURITY_THRESHOLDS.low) {
      violations.push(`低危漏洞数量超限: ${analysis.low} > ${SECURITY_THRESHOLDS.low}`);
    }

    if (analysis.total > SECURITY_THRESHOLDS.total) {
      violations.push(`总漏洞数量超限: ${analysis.total} > ${SECURITY_THRESHOLDS.total}`);
    }

    return {
      compliant: violations.length === 0,
      violations
    };
  }

  /**
   * 获取严重等级颜色
   */
  getSeverityColor(severity) {
    switch (severity) {
      case 'critical': return colors.red;
      case 'high': return colors.red;
      case 'moderate': return colors.yellow;
      case 'low': return colors.blue;
      default: return (text) => text;
    }
  }

  /**
   * 执行自动修复（如果可能）
   */
  async runAutoFix() {
    try {
      console.log(colors.blue('\n🔧 尝试自动修复漏洞...'));

      execSync('npm audit fix', { stdio: 'inherit' });

      console.log(colors.green('✅ 自动修复完成'));
      return true;
    } catch (error) {
      console.log(colors.yellow('⚠️  自动修复未能解决所有漏洞'));
      return false;
    }
  }

  /**
   * 主要执行函数
   */
  async run(options = {}) {
    const {
      failOnThreshold = true,
      autoFix = false,
      generateReport = true
    } = options;

    try {
      // 1. 执行扫描
      const auditReport = await this.runAudit();

      // 2. 分析结果
      const analysis = this.analyzeVulnerabilities(auditReport);

      // 3. 生成报告
      this.generateConsoleReport(analysis);

      if (generateReport) {
        this.generateJsonReport(analysis);
      }

      // 4. 自动修复（如果启用）
      if (autoFix && analysis.total > 0) {
        await this.runAutoFix();
      }

      // 5. 检查合规性
      const compliance = this.checkCompliance(analysis);

      if (!compliance.compliant) {
        console.log(colors.red('\n❌ 安全检查未通过合规要求:'));
        compliance.violations.forEach(violation => {
          console.log(colors.red(`   • ${violation}`));
        });

        if (failOnThreshold) {
          console.log(colors.red('\n🚫 由于安全合规问题，构建被阻止'));
          console.log(colors.blue('💡 请运行 npm audit fix 手动修复，或检查依赖更新'));
          process.exit(1);
        }
      } else {
        console.log(colors.green('\n✅ 安全检查通过合规要求'));
      }

      return analysis;
    } catch (error) {
      console.log(colors.red(`\n❌ 安全扫描失败: ${error.message}`));
      if (failOnThreshold) {
        process.exit(1);
      }
    }
  }
}

// CLI接口
if (require.main === module) {
  const auditor = new SecurityAuditor();

  // 解析命令行参数
  const args = process.argv.slice(2);
  const options = {
    failOnThreshold: !args.includes('--no-fail'),
    autoFix: args.includes('--auto-fix'),
    generateReport: !args.includes('--no-report')
  };

  auditor.run(options);
}

module.exports = SecurityAuditor;