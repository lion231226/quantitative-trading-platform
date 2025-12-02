#!/usr/bin/env node

/**
 * Test Parallelizer Configuration
 *
 * Optimizes test execution by splitting test suites into shards
 * and running them in parallel for maximum CI/CD performance.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class TestParallelizer {
  constructor() {
    this.projectRoot = process.cwd();
    this.config = {
      frontend: {
        testDir: path.join(this.projectRoot, 'frontend'),
        testPatterns: ['**/__tests__/**/*.test.{js,jsx,ts,tsx}', '**/*.test.{js,jsx,ts,tsx}'],
        maxWorkers: 2,
        shardCount: 2
      },
      backend: {
        testDir: path.join(this.projectRoot, 'backend'),
        testPatterns: ['tests/**/*.py', '**/test_*.py'],
        maxWorkers: 'auto',
        shardCount: 2
      }
    };
  }

  /**
   * Generate Jest parallel configuration
   */
  generateJestConfig() {
    const jestConfig = {
      projects: [
        {
          displayName: 'Frontend Unit Tests',
          testMatch: this.config.frontend.testPatterns,
          testEnvironment: 'jsdom',
          setupFilesAfterEnv: ['<rootDir>/frontend/jest.setup.js'],
          moduleNameMapping: {
            '^@/(.*)$': '<rootDir>/frontend/src/$1'
          },
          collectCoverageFrom: [
            'frontend/src/**/*.{js,jsx,ts,tsx}',
            '!frontend/src/**/*.d.ts',
            '!frontend/src/**/*.stories.{js,jsx,ts,tsx}'
          ],
          coverageThreshold: {
            global: {
              branches: 70,
              functions: 70,
              lines: 70,
              statements: 70
            }
          },
          maxWorkers: this.config.frontend.maxWorkers,
          testTimeout: 10000,
          passWithNoTests: true
        },
        {
          displayName: 'Frontend Integration Tests',
          testMatch: ['frontend/**/*.integration.{js,jsx,ts,tsx}'],
          testEnvironment: 'jsdom',
          setupFilesAfterEnv: ['<rootDir>/frontend/jest.integration.setup.js'],
          maxWorkers: 1,
          testTimeout: 30000,
          passWithNoTests: true
        }
      ],
      maxWorkers: '50%', // Use 50% of available CPUs
      testTimeout: 10000,
      passWithNoTests: true,
      verbose: true
    };

    return jestConfig;
  }

  /**
   * Generate Pytest configuration with parallel execution
   */
  generatePytestConfig() {
    const pytestConfig = `
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --tb=short
    --dist=work Ste
    --numprocesses=auto
    --maxprocesses=4
    --tx=popen
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    e2e: marks tests as end-to-end tests
    parallel: marks tests safe for parallel execution
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
asyncio_mode = auto
`;

    return pytestConfig;
  }

  /**
   * Create optimized Jest configuration file
   */
  createJestConfig() {
    const jestConfigPath = path.join(this.projectRoot, 'frontend', 'jest.config.optimized.js');
    const config = this.generateJestConfig();

    const configContent = `
module.exports = ${JSON.stringify(config, null, 2)};

// Parallel execution optimization
module.exports.maxWorkers = process.env.CI ? '50%' : 'auto';
module.exports.testTimeout = process.env.CI ? 15000 : 10000;

// CI-specific optimizations
if (process.env.CI) {
  module.exports.collectCoverage = true;
  module.exports.coverageReporters = ['json', 'lcov', 'text', 'clover'];
  module.exports.coverageDirectory = 'coverage';
}

// Development-specific optimizations
if (process.env.NODE_ENV === 'development') {
  module.exports.watchAll = false;
  module.exports.verbose = false;
}
`;

    fs.writeFileSync(jestConfigPath, configContent);
    console.log(`✅ Jest config created: ${jestConfigPath}`);
  }

  /**
   * Create optimized Pytest configuration file
   */
  createPytestConfig() {
    const pytestConfigPath = path.join(this.projectRoot, 'backend', 'pytest.ini');
    const config = this.generatePytestConfig();

    fs.writeFileSync(pytestConfigPath, config);
    console.log(`✅ Pytest config created: ${pytestConfigPath}`);
  }

  /**
   * Generate test shard scripts for CI
   */
  generateShardScripts() {
    const scriptsDir = path.join(this.projectRoot, 'scripts', 'ci');
    if (!fs.existsSync(scriptsDir)) {
      fs.mkdirSync(scriptsDir, { recursive: true });
    }

    // Frontend test shard script
    const frontendShardScript = `#!/bin/bash
# Frontend Test Shard Runner for CI

set -e

SHARD_INDEX=\${1:-0}
TOTAL_SHARDS=\${2:-2}

echo "🧪 Running Frontend Test Shard \$SHARD_INDEX/\$TOTAL_SHARDS"

cd frontend

# Calculate which tests to run
TEST_PATTERN=""
case \$SHARD_INDEX in
  0)
    TEST_PATTERN="**/__tests__/**/unit/**/*.test.{js,jsx,ts,tsx}"
    ;;
  1)
    TEST_PATTERN="**/__tests__/**/integration/**/*.test.{js,jsx,ts,tsx}"
    ;;
  *)
    echo "❌ Invalid shard index: \$SHARD_INDEX"
    exit 1
    ;;
esac

echo "📋 Test pattern: \$TEST_PATTERN"

# Run tests with optimized Jest configuration
npm test -- --testPathPattern="\$TEST_PATTERN" \
  --config=jest.config.optimized.js \
  --maxWorkers=2 \
  --passWithNoTests \
  --coverage \
  --coverageReporters=json \
  --coverageReporters=lcov \
  --coverageDirectory="coverage-shard-\$SHARD_INDEX" \
  --testTimeout=15000

echo "✅ Frontend shard \$SHARD_INDEX completed successfully"
`;

    // Backend test shard script
    const backendShardScript = `#!/bin/bash
# Backend Test Shard Runner for CI

set -e

SHARD_INDEX=\${1:-0}
TOTAL_SHARDS=\${2:-2}

echo "🧪 Running Backend Test Shard \$SHARD_INDEX/\$TOTAL_SHARDS"

cd backend

# Calculate which tests to run
TEST_PATH=""
MARKERS=""

case \$SHARD_INDEX in
  0)
    TEST_PATH="tests/unit"
    MARKERS="unit or not integration"
    ;;
  1)
    TEST_PATH="tests/integration"
    MARKERS="integration"
    ;;
  *)
    echo "❌ Invalid shard index: \$SHARD_INDEX"
    exit 1
    ;;
esac

echo "📋 Test path: \$TEST_PATH"
echo "🏷️ Markers: \$MARKERS"

# Set up test environment
export TESTING=true
export DATABASE_URL=sqlite:///./test_\$SHARD_INDEX.db
export REDIS_URL=redis://localhost:6379/\$SHARD_INDEX

# Run tests with pytest-xdist for parallel execution
pytest \$TEST_PATH \\
  --dist=work Ste \\
  --numprocesses=auto \\
  --maxprocesses=2 \\
  --markers="\$MARKERS" \\
  --cov=app \\
  --cov-report=json \\
  --cov-report=xml \\
  --cov-report=html \\
  --cov-report=html:htmlcov-shard-\$SHARD_INDEX \\
  --junit-xml=junit-shard-\$SHARD_INDEX.xml \\
  --tb=short \\
  -v

echo "✅ Backend shard \$SHARD_INDEX completed successfully"
`;

    // Write shard scripts
    fs.writeFileSync(path.join(scriptsDir, 'run-frontend-shard.sh'), frontendShardScript);
    fs.writeFileSync(path.join(scriptsDir, 'run-backend-shard.sh'), backendShardScript);

    // Make scripts executable
    fs.chmodSync(path.join(scriptsDir, 'run-frontend-shard.sh'), '755');
    fs.chmodSync(path.join(scriptsDir, 'run-backend-shard.sh'), '755');

    console.log('✅ Test shard scripts created');
  }

  /**
   * Create test merge script for combining shard results
   */
  createMergeScript() {
    const scriptsDir = path.join(this.projectRoot, 'scripts', 'ci');
    const mergeScript = `#!/bin/bash
# Test Results Merger for CI

set -e

echo "🔧 Merging test results from shards..."

cd frontend

# Merge coverage reports
if [ -d "coverage-shard-0" ] && [ -d "coverage-shard-1" ]; then
  echo "📊 Merging coverage reports..."

  # Install coverage merge tool
  npm install -g @jest/coverage-merge

  # Merge JSON coverage reports
  @jest/coverage-merge coverage-shard-0/coverage.json coverage-shard-1/coverage.json -o coverage/coverage.json

  # Generate HTML report
  npx nyc report --reporter=html --reporter=text

  echo "✅ Coverage reports merged"
fi

cd ../backend

# Merge backend coverage reports
if [ -f "coverage-shard-0.json" ] && [ -f "coverage-shard-1.json" ]; then
  echo "📊 Merging backend coverage reports..."

  # Install coverage tools if needed
  pip install coverage coverage-merge

  # Merge coverage data
  coverage combine coverage-shard-0.json coverage-shard-1.json
  coverage xml
  coverage html

  echo "✅ Backend coverage reports merged"
fi

echo "🎉 All test results merged successfully"
`;

    fs.writeFileSync(path.join(scriptsDir, 'merge-test-results.sh'), mergeScript);
    fs.chmodSync(path.join(scriptsDir, 'merge-test-results.sh'), '755');

    console.log('✅ Test merge script created');
  }

  /**
   * Update package.json scripts for parallel execution
   */
  updatePackageJson() {
    const packageJsonPath = path.join(this.projectRoot, 'frontend', 'package.json');

    if (!fs.existsSync(packageJsonPath)) {
      console.log('⚠️ frontend/package.json not found, skipping script updates');
      return;
    }

    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));

    // Add optimized test scripts
    packageJson.scripts = {
      ...packageJson.scripts,
      'test:parallel': 'jest --config=jest.config.optimized.js --maxWorkers=2',
      'test:shard': 'bash ../scripts/ci/run-frontend-shard.sh',
      'test:coverage:parallel': 'jest --config=jest.config.optimized.js --coverage --maxWorkers=2',
      'test:ci': 'npm run test:coverage:parallel -- --passWithNoTests',
      'merge-coverage': 'bash ../scripts/ci/merge-test-results.sh'
    };

    fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));
    console.log('✅ Frontend package.json updated with parallel test scripts');
  }

  /**
   * Analyze current test performance and suggest optimizations
   */
  analyzeTestPerformance() {
    console.log('📊 Analyzing test performance...');

    // Frontend analysis
    const frontendDir = this.config.frontend.testDir;
    if (fs.existsSync(frontendDir)) {
      const testFiles = this.findTestFiles(frontendDir, this.config.frontend.testPatterns);
      console.log(`📁 Found ${testFiles.length} frontend test files`);

      if (testFiles.length > 10) {
        console.log('💡 Recommendation: Enable parallel test execution');
        console.log(`   - Suggested shard count: ${this.config.frontend.shardCount}`);
        console.log(`   - Estimated time savings: ${Math.round(testFiles.length * 0.3)}s`);
      }
    }

    // Backend analysis
    const backendDir = this.config.backend.testDir;
    if (fs.existsSync(backendDir)) {
      const testFiles = this.findTestFiles(backendDir, this.config.backend.testPatterns);
      console.log(`📁 Found ${testFiles.length} backend test files`);

      if (testFiles.length > 5) {
        console.log('💡 Recommendation: Enable pytest-xdist parallel execution');
        console.log(`   - Suggested process count: auto (up to 4)`);
        console.log(`   - Estimated time savings: ${Math.round(testFiles.length * 0.4)}s`);
      }
    }
  }

  /**
   * Find test files matching patterns
   */
  findTestFiles(dir, patterns) {
    let testFiles = [];

    if (!fs.existsSync(dir)) {
      return testFiles;
    }

    patterns.forEach(pattern => {
      try {
        const { execSync } = require('child_process');
        const files = execSync(`find "${dir}" -name "${pattern}"`, { encoding: 'utf8' });
        testFiles = testFiles.concat(files.trim().split('\\n').filter(Boolean));
      } catch (error) {
        // Silently handle find command errors
      }
    });

    return [...new Set(testFiles)]; // Remove duplicates
  }

  /**
   * Create performance monitoring configuration
   */
  createPerformanceMonitor() {
    const monitorScript = `#!/usr/bin/env node

/**
 * Test Performance Monitor
 *
 * Tracks test execution time and provides optimization suggestions
 */

const { performance } = require('perf_hooks');
const { execSync } = require('child_process');

class TestPerformanceMonitor {
  constructor() {
    this.startTime = null;
    this.measurements = [];
  }

  start() {
    this.startTime = performance.now();
    console.log('⏱️ Test performance monitoring started');
  }

  measure(name, fn) {
    const start = performance.now();
    const result = fn();
    const end = performance.now();

    const duration = end - start;
    this.measurements.push({ name, duration });

    console.log(\`📊 \${name}: \${duration.toFixed(2)}ms\`);
    return result;
  }

  end() {
    const totalTime = performance.now() - this.startTime;
    console.log(\`\\n⏱️ Total test time: \${totalTime.toFixed(2)}ms (\${(totalTime/1000).toFixed(2)}s)\`);

    // Analyze performance
    const avgTime = this.measurements.reduce((sum, m) => sum + m.duration, 0) / this.measurements.length;
    console.log(\`📈 Average test time: \${avgTime.toFixed(2)}ms\`);

    // Provide suggestions
    if (totalTime > 30000) { // 30 seconds
      console.log('💡 Suggestion: Consider parallel test execution');
    }

    if (avgTime > 5000) { // 5 seconds per test
      console.log('💡 Suggestion: Some tests may be too slow, consider optimization');
    }

    return {
      totalTime,
      measurements: this.measurements,
      suggestions: this.generateSuggestions(totalTime, avgTime)
    };
  }

  generateSuggestions(totalTime, avgTime) {
    const suggestions = [];

    if (totalTime > 30000) {
      suggestions.push({
        type: 'parallelization',
        message: 'Enable parallel test execution to reduce total time',
        estimatedSavings: \`\${Math.round(totalTime * 0.4)}ms\`
      });
    }

    if (avgTime > 5000) {
      suggestions.push({
        type: 'optimization',
        message: 'Optimize slow individual tests',
        details: 'Consider mocking, better test data, or test splitting'
      });
    }

    return suggestions;
  }
}

module.exports = TestPerformanceMonitor;
`;

    const monitorPath = path.join(this.projectRoot, 'scripts', 'ci', 'test-performance-monitor.js');
    fs.writeFileSync(monitorPath, monitorScript);
    console.log('✅ Test performance monitor created');
  }

  /**
   * Main execution method
   */
  setup() {
    console.log('🚀 Setting up test parallelization configuration...\n');

    this.analyzeTestPerformance();
    console.log('');

    this.createJestConfig();
    this.createPytestConfig();
    this.generateShardScripts();
    this.createMergeScript();
    this.updatePackageJson();
    this.createPerformanceMonitor();

    console.log('\n✅ Test parallelization setup completed!');
    console.log('\n📋 Next steps:');
    console.log('1. Review generated configuration files');
    console.log('2. Update CI/CD pipeline to use shard scripts');
    console.log('3. Run tests with parallel execution');
    console.log('4. Monitor performance improvements');
  }
}

// Main execution
if (require.main === module) {
  const parallelizer = new TestParallelizer();
  parallelizer.setup();
}

module.exports = TestParallelizer;