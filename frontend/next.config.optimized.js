/** @type {import('next').NextConfig} */
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
              test: /[\\/]node_modules[\\/]/,
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
