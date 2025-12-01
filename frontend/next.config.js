/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // !! WARN !!
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    // !! WARN !!
    ignoreBuildErrors: false, // Enable strict type checking for performance optimization
  },
  eslint: {
    ignoreDuringBuilds: false, // Enable ESLint for quality
  },
  images: {
    domains: ['localhost'],
    formats: ['image/webp', 'image/avif'], // Enable modern image formats for better performance
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840], // Responsive image sizes
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384], // Thumbnail sizes
  },
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // Performance optimization configurations
  compress: true, // Enable gzip compression

  // Experimental features for performance
  experimental: {
    optimizeCss: true, // Enable CSS optimization
    scrollRestoration: true, // Enable scroll restoration
  },

  // Build optimizations
  poweredByHeader: false, // Remove powered by header for security
  generateEtags: false, // Disable ETags for better caching

  // Security headers
  headers: async () => [
    {
      source: '/(.*)',
      headers: [
        {
          key: 'X-DNS-Prefetch-Control',
          value: 'on'
        },
        {
          key: 'X-Frame-Options',
          value: 'DENY'
        },
        {
          key: 'X-Content-Type-Options',
          value: 'nosniff'
        },
        {
          key: 'Referrer-Policy',
          value: 'origin-when-cross-origin'
        }
      ]
    }
  ],

  // Bundle analyzer configuration
  webpack: (config, { isDev, isServer, nextRuntime }) => {
    // Enable bundle analyzer in production
    if (!isDev && process.env.ANALYZE === 'true') {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'static',
          openAnalyzer: false,
        })
      );
    }

    // Optimize chunking
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
            },
            charts: {
              test: /[\\/]node_modules[\\/](chart\.js|react-chartjs-2|lightweight-charts)[\\/]/,
              name: 'charts',
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

    return config;
  },
};

module.exports = nextConfig;
