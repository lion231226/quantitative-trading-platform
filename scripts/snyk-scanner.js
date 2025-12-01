#!/usr/bin/env node

/**
 * Snyk安全漏洞扫描脚本
 *
 * 功能:
 * 1. 集成Snyk进行深度依赖漏洞扫描
 * 2. 生成详细的安全报告
 * 3. 支持持续监控配置
 * 4. 许可证合规检查
 * 5. 实时告警和通知
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class SnykScanner {
  constructor() {
    this.projectRoot = process.cwd();
    this.frontendPath = path.join(this.projectRoot, 'frontend');
    this.reportPath = path.join(this.frontendPath, 'security-reports');
    this.ensureReportDirectory();
    this.snykToken = process.env.SNYK_TOKEN || '';
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
   * 检查Snyk是否已安装
   */
  checkSnykInstallation() {
    try {
      execSync('snyk --version', { stdio: 'pipe' });
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * 安装Snyk CLI
   */
  async installSnyk() {
    try {
      console.log('📦 安装Snyk CLI...');
      execSync('npm install -g snyk', { stdio: 'inherit' });
      console.log('✅ Snyk CLI安装成功');
      return true;
    } catch (error) {
      console.error('❌ Snyk CLI安装失败:', error.message);
      return false;
    }
  }

  /**
   * 配置Snyk认证
   */
  async configureSnyk() {
    if (!this.snykToken) {
      console.log('⚠️  未设置SNYK_TOKEN环境变量');
      console.log('💡 请设置环境变量: export SNYK_TOKEN=your-token');
      return false;
    }

    try {
      console.log('🔐 配置Snyk认证...');
      execSync(`snyk auth ${this.snykToken}`, { stdio: 'pipe' });
      console.log('✅ Snyk认证配置成功');
      return true;
    } catch (error) {
      console.error('❌ Snyk认证配置失败:', error.message);
      return false;
    }
  }

  /**
   * 执行Snyk扫描
   */
  async runSnykTest() {
    try {
      console.log('🔍 执行Snyk安全扫描...');

      const scanOutput = execSync('snyk test --json', {
        cwd: this.frontendPath,
        encoding: 'utf8',
        stdio: 'pipe'
      });

      return JSON.parse(scanOutput);
    } catch (error) {
      // Snyk在发现漏洞时返回非零退出码，但仍然会输出JSON
      if (error.stdout) {
        try {
          return JSON.parse(error.stdout);
        } catch (parseError) {
          console.error('❌ Snyk输出解析失败:', parseError.message);
          return null;
        }
      }
      console.error('❌ Snyk扫描执行失败:', error.message);
      return null;
    }
  }

  /**
   * 执行许可证扫描
   */
  async runLicenseScan() {
    try {
      console.log('📄 执行许可证扫描...');

      const licenseOutput = execSync('snyk license --json', {
        cwd: this.frontendPath,
        encoding: 'utf8',
        stdio: 'pipe'
      });

      return JSON.parse(licenseOutput);
    } catch (error) {
      console.error('❌ 许可证扫描失败:', error.message);
      return null;
    }
  }

  /**
   * 分析Snyk扫描结果
   */
  analyzeSnykResults(scanResults) {
    if (!scanResults) {
      return {
        vulnerabilities: [],
        summary: { critical: 0, high: 0, medium: 0, low: 0, total: 0 },
        compliance: { compliant: false, issues: [] }
      };
    }

    const vulnerabilities = scanResults.vulnerabilities || [];
    const summary = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      total: vulnerabilities.length
    };

    vulnerabilities.forEach(vuln => {
      const severity = vuln.severity;
      if (summary[severity] !== undefined) {
        summary[severity]++;
      }
    });

    return {
      vulnerabilities,
      summary,
      compliance: this.checkCompliance(summary)
    };
  }

  /**
   * 检查合规性
   */
  checkCompliance(summary) {
    const violations = [];

    if (summary.critical > 0) {
      violations.push(`发现 ${summary.critical} 个严重漏洞`);
    }

    if (summary.high > 0) {
      violations.push(`发现 ${summary.high} 个高危漏洞`);
    }

    if (summary.total > 5) {
      violations.push(`总漏洞数量超标: ${summary.total} > 5`);
    }

    return {
      compliant: violations.length === 0,
      violations
    };
  }

  /**
   * 生成控制台报告
   */
  generateConsoleReport(analysis, licenseResults) {
    console.log('\n📊 Snyk安全扫描报告');
    console.log('='.repeat(50));

    const { summary, vulnerabilities, compliance } = analysis;

    // 总览
    console.log(`\n📈 漏洞总览:`);
    console.log(`   总计: ${summary.total}`);
    if (summary.critical > 0) console.log(`   🚨 严重: ${summary.critical}`);
    if (summary.high > 0) console.log(`   ⚠️  高危: ${summary.high}`);
    if (summary.medium > 0) console.log(`   ⚠️ 中危: ${summary.medium}`);
    if (summary.low > 0) console.log(`   ℹ️  低危: ${summary.low}`);

    // 合规性状态
    if (compliance.compliant) {
      console.log('\n✅ 安全合规检查通过');
    } else {
      console.log('\n❌ 安全合规检查未通过:');
      compliance.violations.forEach(violation => {
        console.log(`   • ${violation}`);
      });
    }

    // 高危漏洞详情
    const criticalVulns = vulnerabilities.filter(v => v.severity === 'critical' || v.severity === 'high');
    if (criticalVulns.length > 0) {
      console.log('\n🚨 高危漏洞详情:');
      criticalVulns.forEach((vuln, index) => {
        console.log(`\n${index + 1}. ${vuln.title}`);
        console.log(`   包名: ${vuln.packageName}`);
        console.log(`   严重等级: ${vuln.severity}`);
        console.log(`   当前版本: ${vuln.version}`);
        console.log(`   修复版本: ${vuln.fixedIn}`);
        if (vuln.identifiers) {
          console.log(`   CVE: ${vuln.identifiers.CVE?.join(', ') || 'N/A'}`);
        }
        console.log(`   详情: ${vuln.url}`);
      });
    }

    // 许可证信息
    if (licenseResults && licenseResults.licenses) {
      console.log('\n📄 许可证概览:');
      const licenses = licenseResults.licenses;
      console.log(`   总计: ${licenses.length} 个包`);

      const problematicLicenses = licenses.filter(lic =>
        lic.license && !['MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC'].includes(lic.license)
      );

      if (problematicLicenses.length > 0) {
        console.log(`   ⚠️  需要审查的许可证: ${problematicLicenses.length} 个`);
        problematicLicenses.forEach(lic => {
          console.log(`   • ${lic.name}: ${lic.license}`);
        });
      } else {
        console.log('   ✅ 所有许可证都符合要求');
      }
    }
  }

  /**
   * 生成JSON报告
   */
  generateJsonReport(analysis, licenseResults) {
    const report = {
      timestamp: new Date().toISOString(),
      scanner: 'snyk',
      summary: analysis.summary,
      compliance: analysis.compliance,
      vulnerabilities: analysis.vulnerabilities.map(vuln => ({
        packageName: vuln.packageName,
        title: vuln.title,
        severity: vuln.severity,
        version: vuln.version,
        fixedIn: vuln.fixedIn,
        identifiers: vuln.identifiers,
        url: vuln.url,
        description: vuln.description,
        exploitMaturity: vuln.exploitMaturity
      })),
      licenses: licenseResults?.licenses || [],
      recommendations: this.generateRecommendations(analysis)
    };

    const fileName = `snyk-scan-${new Date().toISOString().split('T')[0]}.json`;
    const filePath = path.join(this.reportPath, fileName);

    fs.writeFileSync(filePath, JSON.stringify(report, null, 2));
    console.log(`\n📄 Snyk报告已保存到: ${filePath}`);

    return filePath;
  }

  /**
   * 生成修复建议
   */
  generateRecommendations(analysis) {
    const recommendations = [];

    const { summary, vulnerabilities } = analysis;

    if (summary.critical > 0 || summary.high > 0) {
      recommendations.push({
        priority: 'immediate',
        action: '立即修复高危和严重漏洞',
        details: '这些漏洞可能被攻击者利用，建议立即更新相关依赖包'
      });
    }

    const fixableVulns = vulnerabilities.filter(v => v.fixedIn && v.fixedIn.length > 0);
    if (fixableVulns.length > 0) {
      recommendations.push({
        priority: 'high',
        action: '更新可修复的依赖包',
        details: `${fixableVulns.length} 个漏洞有可用的修复版本`
      });
    }

    if (summary.medium > 0) {
      recommendations.push({
        priority: 'medium',
        action: '计划修复中危漏洞',
        details: '在下次发布周期中修复这些漏洞'
      });
    }

    recommendations.push({
      priority: 'ongoing',
      action: '启用持续监控',
      details: '使用Snyk持续监控依赖包的新漏洞'
    });

    return recommendations;
  }

  /**
   * 启用Snyk监控
   */
  async enableMonitoring() {
    try {
      console.log('📡 启用Snyk持续监控...');
      execSync('snyk monitor', {
        cwd: this.frontendPath,
        stdio: 'pipe'
      });
      console.log('✅ Snyk监控已启用');
      return true;
    } catch (error) {
      console.error('❌ 启用Snyk监控失败:', error.message);
      return false;
    }
  }

  /**
   * 主执行函数
   */
  async run(options = {}) {
    const {
      installSnyk = false,
      configure = false,
      monitor = false,
      licenseScan = true,
      generateReport = true,
      failOnIssues = true
    } = options;

    try {
      console.log('🔒 Snyk安全扫描开始...');

      // 1. 检查/安装Snyk
      if (!this.checkSnykInstallation()) {
        if (installSnyk) {
          const installed = await this.installSnyk();
          if (!installed) {
            throw new Error('无法安装Snyk CLI');
          }
        } else {
          console.log('❌ Snyk CLI未安装，请运行: npm install -g snyk');
          return { success: false };
        }
      }

      // 2. 配置认证
      if (configure && this.snykToken) {
        await this.configureSnyk();
      }

      // 3. 执行扫描
      const scanResults = await this.runSnykTest();
      if (!scanResults) {
        throw new Error('Snyk扫描失败');
      }

      // 4. 许可证扫描
      let licenseResults = null;
      if (licenseScan) {
        licenseResults = await this.runLicenseScan();
      }

      // 5. 分析结果
      const analysis = this.analyzeSnykResults(scanResults);

      // 6. 生成报告
      this.generateConsoleReport(analysis, licenseResults);
      if (generateReport) {
        this.generateJsonReport(analysis, licenseResults);
      }

      // 7. 启用监控
      if (monitor) {
        await this.enableMonitoring();
      }

      // 8. 检查合规性
      if (failOnIssues && !analysis.compliance.compliant) {
        console.log('\n❌ 由于安全问题，构建被阻止');
        console.log('💡 请修复安全问题后重试，或使用 --no-fail 选项继续');
        process.exit(1);
      }

      return {
        success: true,
        analysis,
        licenseResults
      };
    } catch (error) {
      console.error('❌ Snyk扫描失败:', error.message);
      if (failOnIssues) {
        process.exit(1);
      }
      return { success: false };
    }
  }
}

// CLI接口
if (require.main === module) {
  const scanner = new SnykScanner();

  // 解析命令行参数
  const args = process.argv.slice(2);
  const options = {
    installSnyk: args.includes('--install'),
    configure: args.includes('--configure'),
    monitor: args.includes('--monitor'),
    licenseScan: !args.includes('--no-license'),
    generateReport: !args.includes('--no-report'),
    failOnIssues: !args.includes('--no-fail')
  };

  scanner.run(options);
}

module.exports = SnykScanner;