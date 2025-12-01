#!/usr/bin/env node

/**
 * 依赖更新和补丁管理脚本
 *
 * 功能:
 * 1. 检查过时的依赖包
 * 2. 分类安全更新和功能更新
 * 3. 批量更新依赖包
 * 4. 生成更新报告
 * 5. 支持自动和手动更新模式
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const semver = require('semver');

class DependencyUpdater {
  constructor() {
    this.projectRoot = process.cwd();
    this.packageJsonPath = path.join(this.projectRoot, 'package.json');
    this.reportPath = path.join(this.projectRoot, 'dependency-reports');
    this.ensureReportDirectory();
    this.packages = this.loadPackageJson();
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
   * 加载package.json
   */
  loadPackageJson() {
    if (!fs.existsSync(this.packageJsonPath)) {
      throw new Error('package.json not found');
    }
    return JSON.parse(fs.readFileSync(this.packageJsonPath, 'utf8'));
  }

  /**
   * 检查过时的依赖
   */
  async checkOutdated() {
    try {
      console.log('🔍 检查过时的依赖包...');
      const outdatedOutput = execSync('npm outdated --json', {
        encoding: 'utf8',
        stdio: 'pipe'
      });

      return JSON.parse(outdatedOutput);
    } catch (error) {
      // npm outdated在有过时依赖时会返回非零退出码，但仍然会输出JSON
      if (error.stdout) {
        return JSON.parse(error.stdout);
      }
      return {};
    }
  }

  /**
   * 分类更新类型
   */
  categorizeUpdates(outdated) {
    const categories = {
      security: [],    // 安全更新
      patch: [],       // 补丁更新
      minor: [],       // 次要版本更新
      major: [],       // 主要版本更新
      safe: []         // 安全更新（补丁和次要版本）
    };

    Object.entries(outdated).forEach(([name, info]) => {
      const current = info.current;
      const latest = info.latest;
      const type = info.type;

      const update = {
        name,
        current,
        latest,
        type,
        wanted: info.wanted,
        location: info.location,
        updateAvailable: current !== latest
      };

      // 检查是否为安全更新（根据版本号差异判断）
      if (semver.patch(latest) > semver.patch(current)) {
        categories.patch.push(update);
        categories.safe.push(update);
      } else if (semver.minor(latest) > semver.minor(current)) {
        categories.minor.push(update);
        categories.safe.push(update);
      } else if (semver.major(latest) > semver.major(current)) {
        categories.major.push(update);
      }

      // 检查是否有安全漏洞信息
      if (this.hasSecurityVulnerability(name)) {
        categories.security.push(update);
      }
    });

    return categories;
  }

  /**
   * 检查包是否有安全漏洞（简化版本）
   */
  hasSecurityVulnerability(packageName) {
    try {
      const auditOutput = execSync(`npm audit --json`, {
        encoding: 'utf8',
        stdio: 'pipe'
      });
      const auditReport = JSON.parse(auditOutput);
      const vulnerabilities = auditReport.vulnerabilities || {};

      return Object.keys(vulnerabilities).includes(packageName);
    } catch (error) {
      return false;
    }
  }

  /**
   * 生成控制台报告
   */
  generateConsoleReport(categories) {
    console.log('\n📊 依赖更新报告');
    console.log('='.repeat(50));

    const totalUpdates = Object.values(categories).reduce((sum, cat) => sum + cat.length, 0);
    console.log(`\n📈 更新总览: ${totalUpdates} 个包需要更新`);

    // 安全更新
    if (categories.security.length > 0) {
      console.log(`\n🚨 安全更新 (${categories.security.length}):`);
      categories.security.forEach(pkg => {
        console.log(`   🔒 ${pkg.name}: ${pkg.current} → ${pkg.latest}`);
      });
    }

    // 补丁更新
    if (categories.patch.length > 0) {
      console.log(`\n🔧 补丁更新 (${categories.patch.length}):`);
      categories.patch.forEach(pkg => {
        console.log(`   📦 ${pkg.name}: ${pkg.current} → ${pkg.latest}`);
      });
    }

    // 次要版本更新
    if (categories.minor.length > 0) {
      console.log(`\n✨ 次要版本更新 (${categories.minor.length}):`);
      categories.minor.forEach(pkg => {
        console.log(`   📦 ${pkg.name}: ${pkg.current} → ${pkg.latest}`);
      });
    }

    // 主要版本更新
    if (categories.major.length > 0) {
      console.log(`\n🚀 主要版本更新 (${categories.major.length}):`);
      categories.major.forEach(pkg => {
        console.log(`   ⚠️  ${pkg.name}: ${pkg.current} → ${pkg.latest} (可能包含破坏性变更)`);
      });
    }

    // 安全更新建议
    console.log(`\n💡 安全更新建议:`);
    console.log(`   🔒 立即应用: ${categories.security.length} 个安全更新`);
    console.log(`   🔧 建议应用: ${categories.patch.length} 个补丁更新`);
    console.log(`   ✨ 可选更新: ${categories.minor.length} 个次要版本更新`);
    console.log(`   ⚠️  谨慎测试: ${categories.major.length} 个主要版本更新`);
  }

  /**
   * 执行安全更新
   */
  async applySecurityUpdates(categories, autoConfirm = false) {
    const securityPackages = categories.security.map(pkg => pkg.name);
    const patchPackages = categories.patch.map(pkg => pkg.name);

    const safeUpdates = [...securityPackages, ...patchPackages];

    if (safeUpdates.length === 0) {
      console.log('✅ 没有需要立即应用的安全更新');
      return { success: true, updated: [] };
    }

    if (!autoConfirm) {
      console.log(`\n🔒 准备应用安全更新: ${safeUpdates.join(', ')}`);
      console.log('这些更新将提高应用的安全性。');
      // 在实际应用中，这里可以添加用户确认逻辑
    }

    try {
      console.log('🔧 应用安全更新...');

      // 更新安全相关的包
      for (const pkg of safeUpdates) {
        try {
          console.log(`   更新 ${pkg}...`);
          execSync(`npm update ${pkg}`, { stdio: 'pipe' });
          console.log(`   ✅ ${pkg} 更新成功`);
        } catch (error) {
          console.log(`   ❌ ${pkg} 更新失败: ${error.message}`);
        }
      }

      return { success: true, updated: safeUpdates };
    } catch (error) {
      console.error('❌ 安全更新失败:', error.message);
      return { success: false, updated: [] };
    }
  }

  /**
   * 生成更新计划文件
   */
  generateUpdatePlan(categories) {
    const plan = {
      timestamp: new Date().toISOString(),
      summary: {
        totalUpdates: Object.values(categories).reduce((sum, cat) => sum + cat.length, 0),
        security: categories.security.length,
        patch: categories.patch.length,
        minor: categories.minor.length,
        major: categories.major.length
      },
      recommendations: {
        immediate: categories.security.map(pkg => pkg.name),
        weekly: categories.patch.map(pkg => pkg.name),
        monthly: categories.minor.map(pkg => pkg.name),
        research: categories.major.map(pkg => pkg.name)
      },
      details: categories
    };

    const fileName = `dependency-update-plan-${new Date().toISOString().split('T')[0]}.json`;
    const filePath = path.join(this.reportPath, fileName);

    fs.writeFileSync(filePath, JSON.stringify(plan, null, 2));
    console.log(`\n📄 更新计划已保存到: ${filePath}`);

    return filePath;
  }

  /**
   * 主要执行函数
   */
  async run(options = {}) {
    const {
      autoFix = false,
      generateReport = true,
      updateSecurity = false
    } = options;

    try {
      // 1. 检查过时的依赖
      const outdated = await this.checkOutdated();

      if (Object.keys(outdated).length === 0) {
        console.log('✅ 所有依赖都是最新的');
        return { success: true, updated: [], outdated: {} };
      }

      // 2. 分类更新
      const categories = this.categorizeUpdates(outdated);

      // 3. 生成报告
      this.generateConsoleReport(categories);

      if (generateReport) {
        this.generateUpdatePlan(categories);
      }

      // 4. 应用安全更新
      let updateResult = { success: true, updated: [] };
      if (updateSecurity) {
        updateResult = await this.applySecurityUpdates(categories, autoFix);
      }

      return {
        success: updateResult.success,
        updated: updateResult.updated,
        outdated,
        categories
      };
    } catch (error) {
      console.error('❌ 依赖更新检查失败:', error.message);
      return { success: false, updated: [], outdated: {} };
    }
  }
}

// CLI接口
if (require.main === module) {
  const updater = new DependencyUpdater();

  // 解析命令行参数
  const args = process.argv.slice(2);
  const options = {
    autoFix: args.includes('--auto-fix'),
    generateReport: !args.includes('--no-report'),
    updateSecurity: args.includes('--update-security')
  };

  updater.run(options);
}

module.exports = DependencyUpdater;