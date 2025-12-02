#!/bin/bash
# Frontend Test Shard Runner for CI

set -e

SHARD_INDEX=${1:-0}
TOTAL_SHARDS=${2:-2}

echo "🧪 Running Frontend Test Shard $SHARD_INDEX/$TOTAL_SHARDS"

cd frontend

# Calculate which tests to run
TEST_PATTERN=""
case $SHARD_INDEX in
  0)
    TEST_PATTERN="**/__tests__/**/unit/**/*.test.{js,jsx,ts,tsx}"
    ;;
  1)
    TEST_PATTERN="**/__tests__/**/integration/**/*.test.{js,jsx,ts,tsx}"
    ;;
  *)
    echo "❌ Invalid shard index: $SHARD_INDEX"
    exit 1
    ;;
esac

echo "📋 Test pattern: $TEST_PATTERN"

# Run tests with optimized Jest configuration
npm test -- --testPathPattern="$TEST_PATTERN"   --config=jest.config.optimized.js   --maxWorkers=2   --passWithNoTests   --coverage   --coverageReporters=json   --coverageReporters=lcov   --coverageDirectory="coverage-shard-$SHARD_INDEX"   --testTimeout=15000

echo "✅ Frontend shard $SHARD_INDEX completed successfully"
