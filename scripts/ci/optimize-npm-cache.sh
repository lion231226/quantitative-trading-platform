#!/bin/bash
# NPM Cache Optimization Script for CI/CD

set -e

echo "🚀 Optimizing NPM cache..."

# Configure npm for optimal caching
npm config set cache ~/.npm
npm config set prefer-online false

# Pre-install frequently used packages for faster subsequent installs
echo "📦 Pre-installing common dependencies..."

COMMON_DEPS=(
  "react@latest"
  "react-dom@latest"
  "next@latest"
  "typescript@latest"
  "@types/react@latest"
  "@types/node@latest"
  "eslint@latest"
  "prettier@latest"
)

for dep in "${COMMON_DEPS[@]}"; do
  echo "  Installing $dep..."
  npm install "$dep" --no-save --global-style 2>/dev/null || true
done

# Clean up npm cache to remove old versions
echo "🧹 Cleaning up npm cache..."
npm cache clean --force

# Optimize npm cache
echo "⚡ Optimizing cache..."
npm cache verify

echo "✅ NPM cache optimization completed"
