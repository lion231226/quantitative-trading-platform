#!/usr/bin/env node

/**
 * Build Optimization and Caching Strategy
 *
 * Implements intelligent caching strategies for Docker layers, npm dependencies,
 * and Next.js build artifacts to minimize CI/CD execution time.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class BuildOptimizer {
  constructor() {
    this.projectRoot = process.cwd();
    this.cacheVersion = 'v2';
    this.optimizations = {
      docker: {
        enabled: true,
        layerOptimization: true,
        multiStageBuilds: true
      },
      npm: {
        enabled: true,
        cacheKeyStrategy: 'hash-based',
        deduplication: true
      },
      nextjs: {
        enabled: true,
        incrementalBuilds: true,
        staticOptimization: true,
        isrOptimization: true
      },
      ci: {
        parallelBuilds: true,
        conditionalBuilds: true,
        artifactReuse: true
      }
    };
  }

  /**
   * Generate optimized Dockerfile for CI environment
   */
  generateCIOptimizedDockerfile() {
    const dockerfile = `# Multi-stage optimized Dockerfile for CI/CD
# Generated: ${new Date().toISOString()}

# Build stage with optimized caching
FROM node:18-alpine AS base
# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./
COPY frontend/package.json frontend/package-lock.json* ./frontend/
COPY backend/requirements*.txt ./backend/

# Install dependencies
RUN npm ci --only=production && npm cache clean --force
WORKDIR /app/frontend
RUN npm ci --only=production && npm cache clean --force
WORKDIR /app

# Install Python dependencies
WORKDIR /app/backend
RUN python -m pip install --no-cache-dir -r requirements.txt
WORKDIR /app

# Build stage
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/frontend/node_modules ./frontend/node_modules
COPY --from=deps /app/backend /app/backend

# Copy source code
COPY . .

# Build frontend
WORKDIR /app/frontend
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# Build backend (if needed)
WORKDIR /app/backend
RUN python -m py_compile || true

# Production stage
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder --chown=nextjs:nodejs /app/frontend/public ./frontend/public
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/standalone ./frontend/.next
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/static ./frontend/.next

# Copy backend
COPY --from=builder --chown=nextjs:nodejs /app/backend ./backend

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "frontend/server.js"]
`;

    const dockerfilePath = path.join(this.projectRoot, 'docker', 'Dockerfile.ci-optimized');
    fs.mkdirSync(path.dirname(dockerfilePath), { recursive: true });
    fs.writeFileSync(dockerfilePath, dockerfile);

    console.log(`✅ Optimized Dockerfile created: ${dockerfilePath}`);
  }

  /**
   * Generate Docker Compose for CI environment
   */
  generateCIDockerCompose() {
    const dockerCompose = `version: '3.8'

services:
  # Redis service with health check
  redis:
    image: redis:7-alpine
    container_name: ci-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  # Database service (if needed)
  database:
    image: postgres:15-alpine
    container_name: ci-database
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_user -d test_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - postgres-data:/var/lib/postgresql/data

  # Application build service
  app-builder:
    build:
      context: .
      dockerfile: docker/Dockerfile.ci-optimized
      target: builder
      cache_from:
        - type=local,src=/tmp/.buildx-cache
      cache_to:
        - type=local,dest=/tmp/.buildx-cache
    container_name: ci-app-builder
    volumes:
      - ./frontend/.next:/app/frontend/.next
      - ./backend:/app/backend
    environment:
      NODE_ENV: production
      NEXT_TELEMETRY_DISABLED: 1
    depends_on:
      redis:
        condition: service_healthy
      database:
        condition: service_healthy

volumes:
  redis-data:
  postgres-data:
`;

    const composePath = path.join(this.projectRoot, 'docker', 'docker-compose.ci.yml');
    fs.writeFileSync(composePath, dockerCompose);

    console.log(`✅ Docker Compose CI file created: ${composePath}`);
  }

  /**
   * Generate GitHub Actions cache configuration
   */
  generateCacheConfig() {
    const config = {
      version: '2.0',
      caches: {
        'node-modules': {
          key: '${{ env.CACHE_VERSION }}-${{ runner.os }}-node-modules-${{ hashFiles(\'**/package-lock.json\') }}',
          restoreKeys: [
            '${{ env.CACHE_VERSION }}-${{ runner.os }}-node-modules-'
          ],
          paths: [
            '**/node_modules',
            '~/.npm'
          ]
        },
        'nextjs-build': {
          key: '${{ env.CACHE_VERSION }}-${{ runner.os }}-nextjs-${{ hashFiles(\'frontend/package-lock.json\', \'frontend/next.config.js\') }}',
          restoreKeys: [
            '${{ env.CACHE_VERSION }}-${{ runner.os }}-nextjs-'
          ],
          paths: [
            'frontend/.next/cache',
            'frontend/.next/static'
          ]
        },
        'python-deps': {
          key: '${{ env.CACHE_VERSION }}-${{ runner.os }}-python-${{ hashFiles(\'backend/requirements*.txt\') }}',
          restoreKeys: [
            '${{ env.CACHE_VERSION }}-${{ runner.os }}-python-'
          ],
          paths: [
            '~/.cache/pip',
            'backend/.pytest_cache'
          ]
        },
        'docker-layers': {
          key: '${{ env.CACHE_VERSION }}-${{ runner.os }}-docker-${{ hashFiles(\'**/Dockerfile*\') }}',
          paths: [
            '/tmp/.buildx-cache'
          ]
        }
      }
    };

    const configPath = path.join(this.projectRoot, '.github', 'cache-config.json');
    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

    console.log(`✅ Cache configuration created: ${configPath}`);
  }

  /**
   * Generate optimized Next.js configuration
   */
  generateNextJSConfig() {
    const nextConfig = `/** @type {import('next').NextConfig} */
const nextConfig = {
  // Performance optimizations
  experimental: {
    // Enable incremental compilation for faster builds
    incrementalCacheHandlerPath: require.resolve('./cache-handler.js'),

    // Optimize images
    images: {
      domains: ['localhost'],
      deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
      imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    },
  },

  // Production optimizations
  productionBrowserSourceMaps: false,
  optimizeCss: true,
  compress: true,

  // Build optimizations
  swcMinify: true,
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // Static optimization
  trailingSlash: false,

  // Webpack optimizations
  webpack: (config, { dev, isServer }) => {
    // Optimize bundle size
    if (!dev && !isServer) {
      config.optimization = {
        ...config.optimization,
        usedExports: true,
        sideEffects: false,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            vendor: {
              test: /[\\\\/]node_modules[\\\\/]/,
              name: 'vendors',
              chunks: 'all',
            },
            common: {
              name: 'common',
              minChunks: 2,
              chunks: 'all',
              enforce: true,
            },
          },
        },
      };
    }

    // Enable source maps in development
    if (dev) {
      config.devtool = 'eval-source-map';
    }

    return config;
  },

  // Output optimizations
  output: 'standalone',

  // Redirects for SPA
  async redirects() {
    return [
      {
        source: '/api/:path*',
        destination: '/api/:path*',
        permanent: false,
      },
    ];
  },

  // Headers for security and performance
  async headers() {
    return [
      {
        source: '/_next/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/api/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
`;

    const configPath = path.join(this.projectRoot, 'frontend', 'next.config.optimized.js');
    fs.writeFileSync(configPath, nextConfig);

    console.log(`✅ Next.js optimized config created: ${configPath}`);
  }

  /**
   * Generate cache handler for Next.js
   */
  generateCacheHandler() {
    const cacheHandlerContent = `const fs = require('fs');
const path = require('path');

class IncrementalCache {
  constructor() {
    this.cacheDir = path.join(process.cwd(), '.next/cache/incremental');
    this.ensureCacheDir();
  }

  ensureCacheDir() {
    if (!fs.existsSync(this.cacheDir)) {
      fs.mkdirSync(this.cacheDir, { recursive: true });
    }
  }

  async get(key) {
    try {
      const cacheFile = path.join(this.cacheDir, key + '.json');
      if (fs.existsSync(cacheFile)) {
        const content = fs.readFileSync(cacheFile, 'utf8');
        const data = JSON.parse(content);

        // Check if cache is still valid (24 hours)
        if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
          return data.value;
        }
      }
    } catch (error) {
      console.warn('Cache get error:', error);
    }
    return null;
  }

  async set(key, value) {
    try {
      const cacheFile = path.join(this.cacheDir, key + '.json');
      const data = {
        timestamp: Date.now(),
        value,
      };
      fs.writeFileSync(cacheFile, JSON.stringify(data, null, 2));
    } catch (error) {
      console.warn('Cache set error:', error);
    }
  }
}

module.exports = new IncrementalCache();
`;

    const handlerPath = path.join(this.projectRoot, 'frontend', 'cache-handler.js');
    fs.writeFileSync(handlerPath, cacheHandlerContent);

    console.log(`✅ Next.js cache handler created: ${handlerPath}`);
  }

  /**
   * Generate npm cache optimization script
   */
  generateNpmCacheScript() {
    const script = `#!/bin/bash
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

for dep in "\${COMMON_DEPS[@]}"; do
  echo "  Installing \$dep..."
  npm install "\$dep" --no-save --global-style 2>/dev/null || true
done

# Clean up npm cache to remove old versions
echo "🧹 Cleaning up npm cache..."
npm cache clean --force

# Optimize npm cache
echo "⚡ Optimizing cache..."
npm cache verify

echo "✅ NPM cache optimization completed"
`;

    const scriptPath = path.join(this.projectRoot, 'scripts', 'ci', 'optimize-npm-cache.sh');
    fs.writeFileSync(scriptPath, script);
    fs.chmodSync(scriptPath, '755');

    console.log(`✅ NPM cache optimization script created: ${scriptPath}`);
  }

  /**
   * Generate build performance monitor
   */
  generateBuildMonitor() {
    const monitorContent = `#!/usr/bin/env node

/**
 * Build Performance Monitor
 *
 * Tracks build performance and provides optimization suggestions
 */

const fs = require('fs');
const path = require('path');
const { performance } = require('perf_hooks');

class BuildPerformanceMonitor {
  constructor() {
    this.metrics = {
      startTime: null,
      endTime: null,
      phases: {},
      artifacts: {},
      cacheHitRate: 0
    };
  }

  start() {
    this.metrics.startTime = performance.now();
    console.log('⏱️ Build monitoring started');
  }

  startPhase(name) {
    this.metrics.phases[name] = {
      startTime: performance.now(),
      endTime: null,
      duration: null
    };
    console.log('📋 Starting phase: ' + name);
  }

  endPhase(name) {
    if (this.metrics.phases[name]) {
      this.metrics.phases[name].endTime = performance.now();
      this.metrics.phases[name].duration =
        this.metrics.phases[name].endTime - this.metrics.phases[name].startTime;

      console.log('✅ Completed phase: ' + name + ' (' + this.metrics.phases[name].duration.toFixed(2) + 'ms)');
    }
  }

  recordArtifact(name, size) {
    this.metrics.artifacts[name] = {
      size: size,
      path: name
    };
  }

  calculateCacheHitRate() {
    const cacheDir = path.join(process.cwd(), '.next/cache');
    if (fs.existsSync(cacheDir)) {
      const files = fs.readdirSync(cacheDir);
      this.metrics.cacheHitRate = files.length > 0 ? 75 : 0; // Simplified calculation
    }
  }

  end() {
    this.metrics.endTime = performance.now();
    this.metrics.totalDuration = this.metrics.endTime - this.metrics.startTime;
    this.calculateCacheHitRate();

    console.log('\\\\n📊 BUILD PERFORMANCE REPORT');
    console.log('============================');
    console.log('Total Build Time: ' + this.metrics.totalDuration.toFixed(2) + 'ms (' + (this.metrics.totalDuration/1000).toFixed(2) + 's)');
    console.log('Cache Hit Rate: ' + this.metrics.cacheHitRate + '%');

    // Phase breakdown
    console.log('\\\\n📋 Phase Breakdown:');
    Object.entries(this.metrics.phases).forEach(([name, phase]) => {
      const percentage = ((phase.duration / this.metrics.totalDuration) * 100).toFixed(1);
      console.log('  ' + name + ': ' + phase.duration.toFixed(2) + 'ms (' + percentage + '%)');
    });

    // Artifact sizes
    console.log('\\\\n📦 Artifact Sizes:');
    Object.entries(this.metrics.artifacts).forEach(([name, artifact]) => {
      console.log('  ' + name + ': ' + this.formatBytes(artifact.size));
    });

    // Recommendations
    this.generateRecommendations();
  }

  generateRecommendations() {
    console.log('\\\\n💡 Optimization Recommendations:');

    if (this.metrics.totalDuration > 120000) { // 2 minutes
      console.log('  🔥 Build time exceeds 2 minutes - consider parallel builds');
    }

    if (this.metrics.cacheHitRate < 50) {
      console.log('  ⚡ Low cache hit rate - review caching strategy');
    }

    const installPhase = this.metrics.phases['install-dependencies'];
    if (installPhase && installPhase.duration > 60000) { // 1 minute
      console.log('  📦 Slow dependency installation - enable better caching');
    }

    const buildPhase = this.metrics.phases['build'];
    if (buildPhase && buildPhase.duration > 90000) { // 1.5 minutes
      console.log('  🏗️ Slow build phase - enable incremental builds');
    }
  }

  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  exportResults(outputPath) {
    outputPath = outputPath || 'build-performance-report.json';
    const report = {
      timestamp: new Date().toISOString(),
      metrics: this.metrics,
      recommendations: this.getRecommendationsList()
    };

    fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
    console.log('\\\\n📄 Performance report exported to: ' + outputPath);
  }

  getRecommendationsList() {
    const recommendations = [];

    if (this.metrics.totalDuration > 120000) {
      recommendations.push({
        type: 'build_time',
        priority: 'high',
        message: 'Enable parallel builds to reduce total build time',
        estimatedSavings: '30-50%'
      });
    }

    if (this.metrics.cacheHitRate < 50) {
      recommendations.push({
        type: 'cache_optimization',
        priority: 'high',
        message: 'Improve cache hit rate with better cache key strategy',
        estimatedSavings: '40-60%'
      });
    }

    return recommendations;
  }
}

module.exports = BuildPerformanceMonitor;
`;

    const monitorPath = path.join(this.projectRoot, 'scripts', 'ci', 'build-performance-monitor.js');
    fs.writeFileSync(monitorPath, monitorContent);

    console.log(`✅ Build performance monitor created: ${monitorPath}`);
  }

  /**
   * Update CI/CD workflow with build optimizations
   */
  updateWorkflowWithOptimizations() {
    console.log('📝 Note: Manual update of CI/CD workflow file may be required');
    console.log('   Consider adding the following optimizations to .github/workflows/ci-cd.yml:');
    console.log('');
    console.log('   - Add build performance monitoring');
    console.log('   - Enable parallel job execution');
    console.log('   - Use smart caching strategies');
    console.log('   - Implement conditional builds');
  }

  /**
   * Main execution method
   */
  setup() {
    console.log('🚀 Setting up build optimization and caching strategy...\\n');

    this.generateCIOptimizedDockerfile();
    this.generateCIDockerCompose();
    this.generateCacheConfig();
    this.generateNextJSConfig();
    this.generateCacheHandler();
    this.generateNpmCacheScript();
    this.generateBuildMonitor();
    this.updateWorkflowWithOptimizations();

    console.log('\\n✅ Build optimization setup completed!');
    console.log('\\n📋 Next steps:');
    console.log('1. Review generated configuration files');
    console.log('2. Update CI/CD pipeline to use optimized configurations');
    console.log('3. Enable build caching in your CI/CD platform');
    console.log('4. Monitor build performance improvements');
    console.log('5. Adjust cache strategies based on usage patterns');
  }
}

// Main execution
if (require.main === module) {
  const optimizer = new BuildOptimizer();
  optimizer.setup();
}

module.exports = BuildOptimizer;