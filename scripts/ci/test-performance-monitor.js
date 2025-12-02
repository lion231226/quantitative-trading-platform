#!/usr/bin/env node

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

    console.log(`📊 ${name}: ${duration.toFixed(2)}ms`);
    return result;
  }

  end() {
    const totalTime = performance.now() - this.startTime;
    console.log(`\n⏱️ Total test time: ${totalTime.toFixed(2)}ms (${(totalTime/1000).toFixed(2)}s)`);

    // Analyze performance
    const avgTime = this.measurements.reduce((sum, m) => sum + m.duration, 0) / this.measurements.length;
    console.log(`📈 Average test time: ${avgTime.toFixed(2)}ms`);

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
        estimatedSavings: `${Math.round(totalTime * 0.4)}ms`
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
