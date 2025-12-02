#!/bin/bash
# Backend Test Shard Runner for CI

set -e

SHARD_INDEX=${1:-0}
TOTAL_SHARDS=${2:-2}

echo "🧪 Running Backend Test Shard $SHARD_INDEX/$TOTAL_SHARDS"

cd backend

# Calculate which tests to run
TEST_PATH=""
MARKERS=""

case $SHARD_INDEX in
  0)
    TEST_PATH="tests/unit"
    MARKERS="unit or not integration"
    ;;
  1)
    TEST_PATH="tests/integration"
    MARKERS="integration"
    ;;
  *)
    echo "❌ Invalid shard index: $SHARD_INDEX"
    exit 1
    ;;
esac

echo "📋 Test path: $TEST_PATH"
echo "🏷️ Markers: $MARKERS"

# Set up test environment
export TESTING=true
export DATABASE_URL=sqlite:///./test_$SHARD_INDEX.db
export REDIS_URL=redis://localhost:6379/$SHARD_INDEX

# Run tests with pytest-xdist for parallel execution
pytest $TEST_PATH \
  --dist=work Ste \
  --numprocesses=auto \
  --maxprocesses=2 \
  --markers="$MARKERS" \
  --cov=app \
  --cov-report=json \
  --cov-report=xml \
  --cov-report=html \
  --cov-report=html:htmlcov-shard-$SHARD_INDEX \
  --junit-xml=junit-shard-$SHARD_INDEX.xml \
  --tb=short \
  -v

echo "✅ Backend shard $SHARD_INDEX completed successfully"
