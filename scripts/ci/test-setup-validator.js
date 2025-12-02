#!/usr/bin/env node

/**
 * Test Setup Validator
 *
 * Validates that all CI/CD test configurations are properly set up
 */

const fs = require('fs');
const path = require('path');

class TestSetupValidator {
  constructor() {
    this.projectRoot = process.cwd();
    this.results = {
      jest: { status: 'unknown', details: [] },
      pytest: { status: 'unknown', details: [] },
      coverage: { status: 'unknown', details: [] },
      mocking: { status: 'unknown', details: [] },
      ciIntegration: { status: 'unknown', details: [] }
    };
  }

  validate() {
    console.log('🔍 Validating CI/CD Test Setup...\n');

    this.validateJestSetup();
    this.validatePytestSetup();
    this.validateCoverageSetup();
    this.validateMockingSetup();
    this.validateCIIntegration();

    this.printResults();
    return this.isSetupComplete();
  }

  validateJestSetup() {
    console.log('📋 Validating Jest Setup...');

    // Check Jest configuration files
    const jestConfigPath = path.join(this.projectRoot, 'frontend', 'jest.config.js');
    if (fs.existsSync(jestConfigPath)) {
      this.results.jest.details.push('✅ jest.config.js exists');
    } else {
      this.results.jest.details.push('❌ jest.config.js missing');
    }

    // Check Jest setup file
    const jestSetupPath = path.join(this.projectRoot, 'frontend', 'jest.setup.js');
    if (fs.existsSync(jestSetupPath)) {
      this.results.jest.details.push('✅ jest.setup.js exists');
    } else {
      this.results.jest.details.push('❌ jest.setup.js missing');
    }

    // Check optimized Jest config
    const jestOptimizedPath = path.join(this.projectRoot, 'frontend', 'jest.config.optimized.js');
    if (fs.existsSync(jestOptimizedPath)) {
      this.results.jest.details.push('✅ jest.config.optimized.js exists');
    } else {
      this.results.jest.details.push('⚠️ jest.config.optimized.js missing (optional)');
    }

    // Check test dependencies in package.json
    const packageJsonPath = path.join(this.projectRoot, 'frontend', 'package.json');
    if (fs.existsSync(packageJsonPath)) {
      const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
      const requiredDeps = [
        '@testing-library/jest-dom',
        '@testing-library/react',
        '@testing-library/user-event',
        'jest-axe',
        'msw'
      ];

      const missingDeps = requiredDeps.filter(dep => !packageJson.devDependencies?.[dep]);
      if (missingDeps.length === 0) {
        this.results.jest.details.push('✅ All required test dependencies installed');
      } else {
        this.results.jest.details.push(`❌ Missing dependencies: ${missingDeps.join(', ')}`);
      }
    } else {
      this.results.jest.details.push('❌ package.json not found');
    }

    // Check test directories
    const testDirs = [
      'frontend/src/__tests__',
      'frontend/src/components/__tests__',
      'frontend/src/services/__tests__',
      'frontend/src/utils/__tests__'
    ];

    const existingTestDirs = testDirs.filter(dir => fs.existsSync(path.join(this.projectRoot, dir)));
    if (existingTestDirs.length > 0) {
      this.results.jest.details.push(`✅ Test directories found: ${existingTestDirs.join(', ')}`);
    } else {
      this.results.jest.details.push('⚠️ No test directories found');
    }

    // Check for example test files
    const exampleTestPath = path.join(this.projectRoot, 'frontend/src/__tests__/example.test.tsx');
    if (fs.existsSync(exampleTestPath)) {
      this.results.jest.details.push('✅ Example test file exists');
    }

    // Determine overall Jest status
    const hasErrors = this.results.jest.details.some(detail => detail.startsWith('❌'));
    this.results.jest.status = hasErrors ? 'failed' : 'passed';
  }

  validatePytestSetup() {
    console.log('🐍 Validating Pytest Setup...');

    // Check pytest.ini
    const pytestIniPath = path.join(this.projectRoot, 'backend', 'pytest.ini');
    if (fs.existsSync(pytestIniPath)) {
      this.results.pytest.details.push('✅ pytest.ini exists');
    } else {
      this.results.pytest.details.push('❌ pytest.ini missing');
    }

    // Check test directories
    const backendTestDirs = [
      'backend/tests',
      'backend/tests/unit',
      'backend/tests/integration'
    ];

    const existingBackendTestDirs = backendTestDirs.filter(dir =>
      fs.existsSync(path.join(this.projectRoot, dir))
    );

    if (existingBackendTestDirs.length > 0) {
      this.results.pytest.details.push(`✅ Backend test directories found: ${existingBackendTestDirs.join(', ')}`);
    } else {
      this.results.pytest.details.push('⚠️ No backend test directories found');
    }

    // Check for test dependencies in requirements.txt
    const requirementsPath = path.join(this.projectRoot, 'backend', 'requirements.txt');
    if (fs.existsSync(requirementsPath)) {
      const requirements = fs.readFileSync(requirementsPath, 'utf8');
      const testDeps = ['pytest', 'pytest-cov', 'pytest-asyncio', 'pytest-mock'];
      const missingTestDeps = testDeps.filter(dep => !requirements.includes(dep));

      if (missingTestDeps.length === 0) {
        this.results.pytest.details.push('✅ All pytest dependencies installed');
      } else {
        this.results.pytest.details.push(`❌ Missing pytest dependencies: ${missingTestDeps.join(', ')}`);
      }
    } else {
      this.results.pytest.details.push('❌ requirements.txt not found');
    }

    // Determine overall Pytest status
    const hasErrors = this.results.pytest.details.some(detail => detail.startsWith('❌'));
    this.results.pytest.status = hasErrors ? 'failed' : 'passed';
  }

  validateCoverageSetup() {
    console.log('📊 Validating Coverage Setup...');

    // Check Jest coverage configuration
    const jestCoverageConfigPath = path.join(this.projectRoot, 'frontend', 'jest.coverage.config.js');
    if (fs.existsSync(jestCoverageConfigPath)) {
      this.results.coverage.details.push('✅ jest.coverage.config.js exists');
    } else {
      this.results.coverage.details.push('❌ jest.coverage.config.js missing');
    }

    // Check if Jest config includes coverage settings
    const jestConfigPath = path.join(this.projectRoot, 'frontend', 'jest.config.js');
    if (fs.existsSync(jestConfigPath)) {
      const jestConfig = fs.readFileSync(jestConfigPath, 'utf8');
      if (jestConfig.includes('coverageThreshold')) {
        this.results.coverage.details.push('✅ Coverage threshold configured');
      } else {
        this.results.coverage.details.push('⚠️ Coverage threshold not configured');
      }

      if (jestConfig.includes('collectCoverageFrom')) {
        this.results.coverage.details.push('✅ Coverage collection configured');
      } else {
        this.results.coverage.details.push('⚠️ Coverage collection not configured');
      }
    }

    // Check if Pytest config includes coverage
    const pytestIniPath = path.join(this.projectRoot, 'backend', 'pytest.ini');
    if (fs.existsSync(pytestIniPath)) {
      const pytestConfig = fs.readFileSync(pytestIniPath, 'utf8');
      if (pytestConfig.includes('--cov')) {
        this.results.coverage.details.push('✅ Pytest coverage configured');
      } else {
        this.results.coverage.details.push('⚠️ Pytest coverage not configured');
      }
    }

    // Determine overall Coverage status
    const hasErrors = this.results.coverage.details.some(detail => detail.startsWith('❌'));
    const hasWarnings = this.results.coverage.details.some(detail => detail.startsWith('⚠️'));

    if (hasErrors) {
      this.results.coverage.status = 'failed';
    } else if (hasWarnings) {
      this.results.coverage.status = 'warning';
    } else {
      this.results.coverage.status = 'passed';
    }
  }

  validateMockingSetup() {
    console.log('🎭 Validating Mocking Setup...');

    // Check Jest mocks directory
    const jestMocksPath = path.join(this.projectRoot, 'frontend/src/__mocks__');
    if (fs.existsSync(jestMocksPath)) {
      this.results.mocking.details.push('✅ Jest mocks directory exists');
    } else {
      this.results.mocking.details.push('⚠️ Jest mocks directory not found');
    }

    // Check Jest setup for mocks
    const jestSetupPath = path.join(this.projectRoot, 'frontend', 'jest.setup.js');
    if (fs.existsSync(jestSetupPath)) {
      const jestSetup = fs.readFileSync(jestSetupPath, 'utf8');
      const mockFeatures = [
        'jest.mock(\'next/router\'',
        'jest.mock(\'next/navigation\'',
        'jest.mock(\'chart.js\'',
        'IntersectionObserver',
        'ResizeObserver'
      ];

      const foundMocks = mockFeatures.filter(mock => jestSetup.includes(mock));
      if (foundMocks.length > 0) {
        this.results.mocking.details.push(`✅ Mocks configured: ${foundMocks.length} features`);
      } else {
        this.results.mocking.details.push('⚠️ No mocks found in setup');
      }
    }

    // Check MSW setup
    const jestSetup = fs.existsSync(jestSetupPath) ? fs.readFileSync(jestSetupPath, 'utf8') : '';
    if (jestSetup.includes('msw') || jestSetup.includes('setupServer')) {
      this.results.mocking.details.push('✅ MSW API mocking configured');
    } else {
      this.results.mocking.details.push('⚠️ MSW API mocking not configured');
    }

    // Determine overall Mocking status
    const hasErrors = this.results.mocking.details.some(detail => detail.startsWith('❌'));
    this.results.mocking.status = hasErrors ? 'failed' : 'passed';
  }

  validateCIIntegration() {
    console.log('🔄 Validating CI Integration...');

    // Check CI scripts
    const ciScripts = [
      'scripts/ci/pipeline-analyzer.js',
      'scripts/ci/test-parallelizer.js',
      'scripts/ci/build-optimizer.js',
      'scripts/ci/quality-checker.js'
    ];

    const existingScripts = ciScripts.filter(script =>
      fs.existsSync(path.join(this.projectRoot, script))
    );

    if (existingScripts.length === ciScripts.length) {
      this.results.ciIntegration.details.push('✅ All CI scripts present');
    } else {
      this.results.ciIntegration.details.push(`⚠️ Missing CI scripts: ${ciScripts.length - existingScripts.length} of ${ciScripts.length}`);
    }

    // Check GitHub Actions workflows
    const workflowsPath = path.join(this.projectRoot, '.github/workflows');
    if (fs.existsSync(workflowsPath)) {
      const workflows = fs.readdirSync(workflowsPath);
      const mainWorkflow = workflows.find(w => w.includes('ci-cd'));

      if (mainWorkflow) {
        this.results.ciIntegration.details.push(`✅ Main CI/CD workflow: ${mainWorkflow}`);
      } else {
        this.results.ciIntegration.details.push('⚠️ No main CI/CD workflow found');
      }

      const qualityWorkflow = workflows.find(w => w.includes('quality') || w.includes('gate'));
      if (qualityWorkflow) {
        this.results.ciIntegration.details.push(`✅ Quality workflow: ${qualityWorkflow}`);
      } else {
        this.results.ciIntegration.details.push('⚠️ No quality gate workflow found');
      }
    } else {
      this.results.ciIntegration.details.push('❌ .github/workflows directory not found');
    }

    // Check Docker configurations
    const dockerConfigs = [
      'docker/Dockerfile.ci-optimized',
      'docker/docker-compose.ci.yml'
    ];

    const existingDockerConfigs = dockerConfigs.filter(config =>
      fs.existsSync(path.join(this.projectRoot, config))
    );

    if (existingDockerConfigs.length > 0) {
      this.results.ciIntegration.details.push(`✅ Docker configs found: ${existingDockerConfigs.length} of ${dockerConfigs.length}`);
    } else {
      this.results.ciIntegration.details.push('⚠️ No Docker configurations found');
    }

    // Determine overall CI Integration status
    const hasErrors = this.results.ciIntegration.details.some(detail => detail.startsWith('❌'));
    const hasWarnings = this.results.ciIntegration.details.some(detail => detail.startsWith('⚠️'));

    if (hasErrors) {
      this.results.ciIntegration.status = 'failed';
    } else if (hasWarnings) {
      this.results.ciIntegration.status = 'warning';
    } else {
      this.results.ciIntegration.status = 'passed';
    }
  }

  isSetupComplete() {
    const statuses = Object.values(this.results).map(result => result.status);
    const hasFailures = statuses.some(status => status === 'failed');
    const hasWarnings = statuses.some(status => status === 'warning');

    if (hasFailures) {
      return false;
    } else if (hasWarnings) {
      return true; // Partial setup is acceptable
    } else {
      return true;
    }
  }

  printResults() {
    console.log('\n📊 TEST SETUP VALIDATION RESULTS');
    console.log('=================================');

    Object.entries(this.results).forEach(([component, result]) => {
      const icon = result.status === 'passed' ? '✅' : result.status === 'failed' ? '❌' : '⚠️';
      console.log(`\n${icon} ${component.toUpperCase()}: ${result.status.toUpperCase()}`);

      result.details.forEach(detail => {
        console.log(`   ${detail}`);
      });
    });

    const isComplete = this.isSetupComplete();
    console.log(`\n${isComplete ? '🎉' : '⚠️'} SETUP STATUS: ${isComplete ? 'COMPLETE' : 'PARTIAL'}`);

    if (isComplete) {
      console.log('\n✅ Test setup is ready for CI/CD pipeline!');
      console.log('📋 Next steps:');
      console.log('1. Run tests locally to verify setup');
      console.log('2. Commit and push changes to trigger CI/CD');
      console.log('3. Monitor test execution and coverage');
    } else {
      console.log('\n⚠️ Setup is incomplete. Address the issues above before proceeding.');
      console.log('📋 Required actions:');
      console.log('1. Fix failed configurations');
      console.log('2. Install missing dependencies');
      console.log('3. Create missing configuration files');
    }
  }

  exportResults(outputPath = 'test-setup-validation-results.json') {
    const validationResults = {
      timestamp: new Date().toISOString(),
      results: this.results,
      isComplete: this.isSetupComplete()
    };

    fs.writeFileSync(outputPath, JSON.stringify(validationResults, null, 2));
    console.log(`\n📄 Validation results exported to: ${outputPath}`);
  }
}

// Main execution
if (require.main === module) {
  const validator = new TestSetupValidator();
  validator.validate();
  validator.exportResults();

  // Exit with appropriate code
  process.exit(validator.isSetupComplete() ? 0 : 1);
}

module.exports = TestSetupValidator;