// Add any custom config to be passed to Jest
const coverageConfig = require('./jest.coverage.config');

const customJestConfig = {
  testEnvironment: '<rootDir>/jest.env.happy-dom.js',
  testEnvironmentOptions: {
    url: 'http://localhost:3000',
    resources: 'usable',
    runScripts: 'dangerously',
    width: 1024,
    height: 768,
    deviceScaleFactor: 1,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    // Handle module aliases (this will be automatically configured for you based on your tsconfig.json paths)
    '^@/(.*)$': '<rootDir>/src/$1',
    // Mock lightweight-charts
    'lightweight-charts': '<rootDir>/src/__mocks__/lightweight-charts.js',
  },
  // 优化内存使用
  maxWorkers: 1, // 单线程运行以减少内存使用
  maxConcurrency: 1,
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,
  ...coverageConfig,
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}',
  ],
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }],
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(chart.js|react-chartjs-2|lightweight-charts)/)',
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  // 添加内存限制
  detectOpenHandles: false,
  forceExit: true,
  // 超时设置
  testTimeout: 10000,
};

module.exports = customJestConfig;
