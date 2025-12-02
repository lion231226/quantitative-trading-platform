#!/usr/bin/env node

/**
 * CI/CD Pipeline Performance Analyzer
 *
 * Analyzes current GitHub Actions workflows to identify execution time bottlenecks
 * and establish performance benchmarks for optimization targeting < 10 minute total execution time.
 */

const fs = require('fs');
const path = require('path');

class PipelineAnalyzer {
  constructor() {
    this.workflowsDir = path.join(process.cwd(), '.github', 'workflows');
    this.analysis = {
      workflows: [],
      totalEstimatedTime: 0,
      bottlenecks: [],
      recommendations: []
    };
  }

  /**
   * Parse GitHub Actions workflow file and estimate execution times
   */
  parseWorkflowFile(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const workflowName = this.extractWorkflowName(content);
      const jobs = this.extractJobs(content);

      let estimatedTime = 0;
      const jobDetails = [];

      jobs.forEach(job => {
        const jobTime = this.estimateJobTime(job);
        estimatedTime += jobTime;
        jobDetails.push({
          name: job.name,
          estimatedTime: jobTime,
          steps: job.steps.length,
          runsOn: job.runsOn,
          strategies: job.strategies
        });
      });

      return {
        name: workflowName,
        fileName: path.basename(filePath),
        estimatedTime,
        jobs: jobDetails,
        triggers: this.extractTriggers(content)
      };
    } catch (error) {
      console.warn(`Failed to parse workflow file ${filePath}:`, error.message);
      return null;
    }
  }

  extractWorkflowName(content) {
    const match = content.match(/^name:\s*(.+)$/m);
    return match ? match[1].trim() : 'Unnamed Workflow';
  }

  extractJobs(content) {
    const jobs = [];
    const jobRegex = /(\w+):\s*\n((?:\s{2,}.*\n)*)/g;
    let match;

    while ((match = jobRegex.exec(content)) !== null) {
      const jobName = match[1];
      const jobContent = match[2];

      // Skip if not a job definition
      if (['on', 'env', 'defaults'].includes(jobName)) continue;

      const job = {
        name: jobName,
        steps: this.extractSteps(jobContent),
        runsOn: this.extractRunsOn(jobContent),
        strategies: this.extractStrategies(jobContent)
      };

      jobs.push(job);
    }

    return jobs;
  }

  extractSteps(jobContent) {
    const steps = [];
    const stepRegex = /-\s*name:\s*(.+?)\n(?:\s{6,}uses:\s*(.+?)\n)?(?:\s{6,}run:\s*\n((?:\s{8,}.*\n)*))?/g;
    let match;

    while ((match = stepRegex.exec(jobContent)) !== null) {
      steps.push({
        name: match[1],
        uses: match[2] || null,
        run: match[3] ? match[3].trim() : null
      });
    }

    return steps;
  }

  extractRunsOn(jobContent) {
    const match = jobContent.match(/runs-on:\s*(.+)/);
    return match ? match[1].trim() : 'ubuntu-latest';
  }

  extractStrategies(jobContent) {
    const matrixMatch = jobContent.match(/matrix:\s*\n((?:\s{6,}.*\n)*)/);
    if (!matrixMatch) return null;

    const matrixContent = matrixMatch[1];
    const strategies = {};

    // Extract Python versions
    const pythonMatch = matrixContent.match(/python-version:\s*\[(.*?)\]/);
    if (pythonMatch) {
      strategies.pythonVersions = pythonMatch[1].split(',').map(v => v.trim().replace(/['"]/g, ''));
    }

    // Extract Node versions
    const nodeMatch = matrixContent.match(/node-version:\s*\[(.*?)\]/);
    if (nodeMatch) {
      strategies.nodeVersions = nodeMatch[1].split(',').map(v => v.trim().replace(/['"]/g, ''));
    }

    return strategies;
  }

  extractTriggers(content) {
    const triggers = [];
    const onMatch = content.match(/^on:\s*\n((?:\s{2,}.*\n)*)/m);

    if (onMatch) {
      const onContent = onMatch[1];

      if (onContent.includes('push:')) triggers.push('push');
      if (onContent.includes('pull_request:')) triggers.push('pull_request');
      if (onContent.includes('schedule:')) triggers.push('schedule');
      if (onContent.includes('workflow_dispatch:')) triggers.push('manual');
    }

    return triggers;
  }

  /**
   * Estimate job execution time based on typical GitHub Actions performance
   */
  estimateJobTime(job) {
    let baseTime = 30; // Base setup time (checkout, setup actions)

    job.steps.forEach(step => {
      if (step.uses) {
        baseTime += this.getActionTime(step.uses);
      }

      if (step.run) {
        baseTime += this.getScriptTime(step.run);
      }
    });

    // Matrix strategy multiplies time
    if (job.strategies) {
      const multiplier = this.getMatrixMultiplier(job.strategies);
      baseTime *= multiplier;
    }

    return baseTime;
  }

  getActionTime(action) {
    const actionTimes = {
      'actions/checkout@v4': 10,
      'actions/setup-node@v4': 45,
      'actions/setup-python@v4': 60,
      'actions/cache@v4': 5,
      'codecov/codecov-action@v4': 15,
      'actions/upload-artifact@v4': 10,
      'actions/download-artifact@v4': 10,
      'npm install': 120,
      'pip install': 180,
      'npm test': 90,
      'pytest': 120
    };

    for (const [key, time] of Object.entries(actionTimes)) {
      if (action.toLowerCase().includes(key.toLowerCase())) {
        return time;
      }
    }

    return 30; // Default time for unknown actions
  }

  getScriptTime(script) {
    if (script.includes('npm ci')) return 120;
    if (script.includes('npm install')) return 120;
    if (script.includes('pip install')) return 180;
    if (script.includes('pytest')) return 120;
    if (script.includes('npm test')) return 90;
    if (script.includes('build')) return 90;
    if (script.includes('coverage')) return 60;

    return 30; // Default script time
  }

  getMatrixMultiplier(strategies) {
    let multiplier = 1;

    if (strategies.pythonVersions) {
      multiplier *= strategies.pythonVersions.length;
    }

    if (strategies.nodeVersions) {
      multiplier *= strategies.nodeVersions.length;
    }

    return multiplier;
  }

  /**
   * Analyze all workflow files and identify bottlenecks
   */
  analyze() {
    console.log('🔍 Analyzing CI/CD Pipeline Performance...\n');

    if (!fs.existsSync(this.workflowsDir)) {
      console.error('❌ .github/workflows directory not found');
      return;
    }

    const workflowFiles = fs.readdirSync(this.workflowsDir)
      .filter(file => file.endsWith('.yml') || file.endsWith('.yaml'))
      .filter(file => !file.endsWith('.disabled'));

    console.log(`📁 Found ${workflowFiles.length} active workflow files\n`);

    workflowFiles.forEach(file => {
      const filePath = path.join(this.workflowsDir, file);
      const workflow = this.parseWorkflowFile(filePath);

      if (workflow) {
        this.analysis.workflows.push(workflow);
        this.analysis.totalEstimatedTime += workflow.estimatedTime;

        console.log(`📄 ${workflow.name} (${file})`);
        console.log(`   ⏱️  Estimated Time: ${workflow.estimatedTime}s`);
        console.log(`   📋 Jobs: ${workflow.jobs.length}`);
        console.log(`   🚀 Triggers: ${workflow.triggers.join(', ')}`);
        console.log('');
      }
    });

    this.identifyBottlenecks();
    this.generateRecommendations();
    this.printAnalysis();
  }

  identifyBottlenecks() {
    console.log('🔍 Identifying Performance Bottlenecks...\n');

    this.analysis.workflows.forEach(workflow => {
      workflow.jobs.forEach(job => {
        if (job.estimatedTime > 300) { // 5 minutes
          this.analysis.bottlenecks.push({
            type: 'slow_job',
            workflow: workflow.name,
            job: job.name,
            time: job.estimatedTime,
            severity: job.estimatedTime > 600 ? 'high' : 'medium'
          });
        }

        if (job.steps.length > 15) {
          this.analysis.bottlenecks.push({
            type: 'complex_job',
            workflow: workflow.name,
            job: job.name,
            steps: job.steps.length,
            severity: 'medium'
          });
        }
      });
    });
  }

  generateRecommendations() {
    console.log('💡 Generating Optimization Recommendations...\n');

    // Overall pipeline recommendations
    if (this.analysis.totalEstimatedTime > 600) {
      this.analysis.recommendations.push({
        category: 'pipeline_parallelization',
        priority: 'high',
        title: 'Implement Parallel Job Execution',
        description: 'Jobs can run in parallel to reduce total pipeline time',
        estimatedSavings: `${Math.round(this.analysis.totalEstimatedTime * 0.3)}s`
      });
    }

    // Specific job recommendations
    this.analysis.bottlenecks.forEach(bottleneck => {
      if (bottleneck.type === 'slow_job') {
        this.analysis.recommendations.push({
          category: 'job_optimization',
          priority: bottleneck.severity,
          title: `Optimize ${bottleneck.job} job in ${bottleneck.workflow}`,
          description: `This job takes ${bottleneck.time}s, consider caching or parallelization`,
          estimatedSavings: `${Math.round(bottleneck.time * 0.4)}s`
        });
      }
    });

    // General recommendations
    this.analysis.recommendations.push(
      {
        category: 'dependency_caching',
        priority: 'high',
        title: 'Implement Smart Dependency Caching',
        description: 'Cache npm/pip dependencies based on hash of lock files',
        estimatedSavings: '120s'
      },
      {
        category: 'test_parallelization',
        priority: 'high',
        title: 'Parallel Test Execution',
        description: 'Split test suite and run in parallel across multiple runners',
        estimatedSavings: '180s'
      },
      {
        category: 'conditional_execution',
        priority: 'medium',
        title: 'Implement Conditional Workflow Steps',
        description: 'Skip unnecessary steps based on file changes',
        estimatedSavings: '60s'
      }
    );
  }

  printAnalysis() {
    console.log('📊 CI/CD PIPELINE PERFORMANCE ANALYSIS REPORT');
    console.log('='.repeat(50));

    console.log(`\n📈 SUMMARY:`);
    console.log(`   Total Workflows: ${this.analysis.workflows.length}`);
    console.log(`   Estimated Total Time: ${this.analysis.totalEstimatedTime}s (${Math.round(this.analysis.totalEstimatedTime / 60)} minutes)`);
    console.log(`   Bottlenecks Identified: ${this.analysis.bottlenecks.length}`);
    console.log(`   Recommendations Generated: ${this.analysis.recommendations.length}`);

    if (this.analysis.totalEstimatedTime > 600) {
      console.log(`   ⚠️  CURRENT STATUS: Exceeds 10-minute target by ${Math.round((this.analysis.totalEstimatedTime - 600) / 60)} minutes`);
    } else {
      console.log(`   ✅ CURRENT STATUS: Within 10-minute target`);
    }

    console.log(`\n🚨 BOTTLENECKS:`);
    if (this.analysis.bottlenecks.length === 0) {
      console.log('   No significant bottlenecks identified');
    } else {
      this.analysis.bottlenecks.forEach((bottleneck, index) => {
        const icon = bottleneck.severity === 'high' ? '🔴' : '🟡';
        console.log(`   ${index + 1}. ${icon} ${bottleneck.workflow} → ${bottleneck.job} (${bottleneck.time}s)`);
      });
    }

    console.log(`\n💡 RECOMMENDATIONS:`);
    this.analysis.recommendations.forEach((rec, index) => {
      const icon = rec.priority === 'high' ? '🔥' : rec.priority === 'medium' ? '⚡' : '💡';
      console.log(`   ${index + 1}. ${icon} ${rec.title}`);
      console.log(`      → ${rec.description}`);
      console.log(`      → Estimated Savings: ${rec.estimatedSavings}`);
    });

    console.log(`\n🎯 TARGET BREAKDOWN (< 10 minutes = 600s):`);
    const target = {
      environment_setup: 60,
      code_quality_checks: 120,
      security_scans: 90,
      unit_tests: 180,
      integration_tests: 120,
      build_and_bundle: 90,
      deployment: 60
    };

    Object.entries(target).forEach(([phase, time]) => {
      console.log(`   ${phase.replace(/_/g, ' ').padEnd(25)}: ${time}s`);
    });

    console.log(`   ${''.padEnd(25)}: ${Object.values(target).reduce((a, b) => a + b, 0)}s total`);

    console.log('\n' + '='.repeat(50));
    console.log('✅ Analysis completed. Use this report to guide optimization efforts.');
  }

  /**
   * Export analysis results to JSON file
   */
  exportResults(outputPath = 'ci-analysis-results.json') {
    const results = {
      timestamp: new Date().toISOString(),
      analysis: this.analysis,
      targetExecutionTime: 600, // 10 minutes
      status: this.analysis.totalEstimatedTime <= 600 ? 'within_target' : 'exceeds_target'
    };

    fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
    console.log(`\n💾 Analysis results exported to: ${outputPath}`);
  }
}

// Main execution
if (require.main === module) {
  const analyzer = new PipelineAnalyzer();
  analyzer.analyze();
  analyzer.exportResults();
}

module.exports = PipelineAnalyzer;