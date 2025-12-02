#!/bin/bash
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
