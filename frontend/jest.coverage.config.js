// Jest 覆盖率配置
const coverageConfig = {
  // 覆盖率收集的文件
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/app/**/layout.tsx',
    '!src/app/**/loading.tsx',
    '!src/app/**/not-found.tsx',
    '!src/app/**/error.tsx',
    '!src/**/__tests__/**',
    '!src/**/__mocks__/**',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/next-env.d.ts',
  ],

  // 覆盖率阈值 - 提升85%以满足验收标准
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
    // 关键目录的更高要求
    './src/services/': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90,
    },
    './src/utils/': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90,
    },
    './src/components/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
  },

  // 覆盖率报告格式
  coverageReporters: ['text', 'text-summary', 'html', 'lcov', 'json'],

  // 覆盖率输出目录
  coverageDirectory: 'coverage',

  // 忽略覆盖率的文件模式
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '<rootDir>/src/__tests__/',
    '<rootDir>/src/__mocks__/',
  ],
};

module.exports = coverageConfig;
