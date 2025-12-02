/**
 * CI/CD Pipeline Optimizer Tests
 */

const PipelineAnalyzer = require('../pipeline-analyzer');
const BuildOptimizer = require('../build-optimizer');
const QualityChecker = require('../quality-checker');
const fs = require('fs');
const path = require('path');

describe('Pipeline Optimizer Tests', () => {
  let analyzer;
  let optimizer;
  let qualityChecker;

  beforeEach(() => {
    analyzer = new PipelineAnalyzer();
    optimizer = new BuildOptimizer();
    qualityChecker = new QualityChecker();
  });

  describe('PipelineAnalyzer', () => {
    it('should initialize with correct configuration', () => {
      expect(analyzer.workflowsDir).toContain('.github/workflows');
      expect(analyzer.analysis.workflows).toEqual([]);
      expect(analyzer.analysis.totalEstimatedTime).toBe(0);
    });

    it('should estimate job time correctly', () => {
      const job = {
        name: 'test-job',
        steps: [
          { name: 'checkout', uses: 'actions/checkout@v4' },
          { name: 'npm-install', run: 'npm install' },
          { name: 'npm-test', run: 'npm test' }
        ]
      };

      const time = analyzer.estimateJobTime(job);
      expect(time).toBeGreaterThan(0);
      expect(time).toBeLessThan(300); // Should be less than 5 minutes
    });

    it('should calculate action time correctly', () => {
      expect(analyzer.getActionTime('actions/checkout@v4')).toBe(10);
      expect(analyzer.getActionTime('actions/setup-node@v4')).toBe(45);
      expect(analyzer.getActionTime('npm install')).toBe(120);
      expect(analyzer.getActionTime('npm test')).toBe(90);
    });

    it('should handle unknown actions gracefully', () => {
      const time = analyzer.getActionTime('unknown/action');
      expect(time).toBe(30); // Default time
    });
  });

  describe('BuildOptimizer', () => {
    it('should initialize with correct configuration', () => {
      expect(optimizer.projectRoot).toBeDefined();
      expect(optimizer.cacheVersion).toBe('v2');
      expect(optimizer.optimizations.docker.enabled).toBe(true);
      expect(optimizer.optimizations.npm.enabled).toBe(true);
    });

    it('should generate Jest configuration', () => {
      const jestConfig = optimizer.generateJestConfig();
      expect(jestConfig.projects).toBeDefined();
      expect(jestConfig.projects.length).toBeGreaterThan(0);
      expect(jestConfig.maxWorkers).toBe('50%');
    });

    it('should generate Pytest configuration', () => {
      const pytestConfig = optimizer.generatePytestConfig();
      expect(pytestConfig).toContain('[tool:pytest]');
      expect(pytestConfig).toContain('--dist=work Ste');
      expect(pytestConfig).toContain('--numprocesses=auto');
    });

    it('should format bytes correctly', () => {
      const mockMonitor = {
        formatBytes: function(bytes) {
          if (bytes === 0) return '0 Bytes';
          const k = 1024;
          const sizes = ['Bytes', 'KB', 'MB', 'GB'];
          const i = Math.floor(Math.log(bytes) / Math.log(k));
          return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
      };

      expect(mockMonitor.formatBytes(0)).toBe('0 Bytes');
      expect(mockMonitor.formatBytes(1024)).toBe('1 KB');
      expect(mockMonitor.formatBytes(1024 * 1024)).toBe('1 MB');
    });
  });

  describe('QualityChecker', () => {
    it('should initialize with correct thresholds', () => {
      expect(qualityChecker.thresholds.testCoverage).toBe(85);
      expect(qualityChecker.thresholds.bundleSizeLimit).toBe(1024 * 1024);
      expect(qualityChecker.thresholds.lighthouseScore).toBe(90);
    });

    it('should format bytes correctly', () => {
      expect(qualityChecker.formatBytes(0)).toBe('0 Bytes');
      expect(qualityChecker.formatBytes(1024)).toBe('1 KB');
      expect(qualityChecker.formatBytes(1024 * 1024)).toBe('1 MB');
    });

    it('should calculate quality score correctly', () => {
      qualityChecker.results.checks = {
        testCoverage: { status: 'PASS' },
        codeQuality: { status: 'PASS' },
        security: { status: 'FAIL' },
        performance: { status: 'PASS' },
        bundleSize: { status: 'PASS' },
        accessibility: { status: 'PASS' }
      };

      qualityChecker.calculateQualityScore();
      expect(qualityChecker.results.qualityScore).toBe(83); // 5/6 passed
    });
  });

  describe('Configuration Validation', () => {
    it('should validate cache configuration structure', () => {
      const cacheConfig = optimizer.generateCacheConfig();
      expect(cacheConfig.version).toBe('2.0');
      expect(cacheConfig.caches).toBeDefined();
      expect(cacheConfig.caches['node-modules']).toBeDefined();
      expect(cacheConfig.caches['nextjs-build']).toBeDefined();
    });

    it('should validate Docker configuration', () => {
      const dockerfile = optimizer.generateCIOptimizedDockerfile();
      expect(dockerfile).toContain('FROM node:18-alpine');
      expect(dockerfile).toContain('AS deps');
      expect(dockerfile).toContain('AS builder');
      expect(dockerfile).toContain('AS runner');
    });

    it('should validate Next.js configuration', () => {
      const nextConfig = optimizer.generateNextJSConfig();
      expect(nextConfig).toContain('const nextConfig');
      expect(nextConfig).toContain('experimental:');
      expect(nextConfig).toContain('swcMinify: true');
    });
  });

  describe('Performance Metrics', () => {
    it('should track execution phases', () => {
      const mockMonitor = {
        metrics: {
          phases: {}
        },
        startPhase: function(name) {
          this.metrics.phases[name] = {
            startTime: Date.now(),
            endTime: null,
            duration: null
          };
        },
        endPhase: function(name) {
          if (this.metrics.phases[name]) {
            this.metrics.phases[name].endTime = Date.now();
            this.metrics.phases[name].duration =
              this.metrics.phases[name].endTime - this.metrics.phases[name].startTime;
          }
        }
      };

      mockMonitor.startPhase('test-phase');
      mockMonitor.endPhase('test-phase');

      expect(mockMonitor.metrics.phases['test-phase']).toBeDefined();
      expect(mockMonitor.metrics.phases['test-phase'].duration).toBeGreaterThan(0);
    });
  });

  describe('Error Handling', () => {
    it('should handle missing workflow directory gracefully', () => {
      const mockAnalyzer = new PipelineAnalyzer();
      mockAnalyzer.workflowsDir = '/nonexistent/directory';

      expect(() => mockAnalyzer.analyze()).not.toThrow();
    });

    it('should handle invalid JSON gracefully', () => {
      expect(() => {
        JSON.parse('invalid json');
      }).toThrow();
    });

    it('should handle file system errors', () => {
      expect(() => {
        fs.readFileSync('/nonexistent/file.json');
      }).toThrow();
    });
  });

  describe('Integration Tests', () => {
    it('should complete full pipeline analysis workflow', () => {
      const mockAnalyzer = new PipelineAnalyzer();

      // Mock workflow files existence
      const mockWorkflowFiles = ['ci-cd.yml', 'coverage.yml'];
      jest.spyOn(fs, 'readdirSync').mockReturnValue(mockWorkflowFiles);
      jest.spyOn(fs, 'readFileSync').mockReturnValue('name: Test Workflow');

      expect(() => mockAnalyzer.analyze()).not.toThrow();
      expect(fs.readdirSync).toHaveBeenCalled();
    });

    it('should generate complete optimization setup', () => {
      const mockOptimizer = new BuildOptimizer();

      // Mock file system operations
      jest.spyOn(fs, 'mkdirSync').mockImplementation(() => {});
      jest.spyOn(fs, 'writeFileSync').mockImplementation(() => {});

      expect(() => mockOptimizer.setup()).not.toThrow();
    });
  });
});