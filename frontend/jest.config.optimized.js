
module.exports = {
  "projects": [
    {
      "displayName": "Frontend Unit Tests",
      "testMatch": [
        "**/__tests__/**/*.test.{js,jsx,ts,tsx}",
        "**/*.test.{js,jsx,ts,tsx}"
      ],
      "testEnvironment": "jsdom",
      "setupFilesAfterEnv": [
        "<rootDir>/frontend/jest.setup.js"
      ],
      "moduleNameMapping": {
        "^@/(.*)$": "<rootDir>/frontend/src/$1"
      },
      "collectCoverageFrom": [
        "frontend/src/**/*.{js,jsx,ts,tsx}",
        "!frontend/src/**/*.d.ts",
        "!frontend/src/**/*.stories.{js,jsx,ts,tsx}"
      ],
      "coverageThreshold": {
        "global": {
          "branches": 70,
          "functions": 70,
          "lines": 70,
          "statements": 70
        }
      },
      "maxWorkers": 2,
      "testTimeout": 10000,
      "passWithNoTests": true
    },
    {
      "displayName": "Frontend Integration Tests",
      "testMatch": [
        "frontend/**/*.integration.{js,jsx,ts,tsx}"
      ],
      "testEnvironment": "jsdom",
      "setupFilesAfterEnv": [
        "<rootDir>/frontend/jest.integration.setup.js"
      ],
      "maxWorkers": 1,
      "testTimeout": 30000,
      "passWithNoTests": true
    }
  ],
  "maxWorkers": "50%",
  "testTimeout": 10000,
  "passWithNoTests": true,
  "verbose": true
};

// Parallel execution optimization
module.exports.maxWorkers = process.env.CI ? '50%' : 'auto';
module.exports.testTimeout = process.env.CI ? 15000 : 10000;

// CI-specific optimizations
if (process.env.CI) {
  module.exports.collectCoverage = true;
  module.exports.coverageReporters = ['json', 'lcov', 'text', 'clover'];
  module.exports.coverageDirectory = 'coverage';
}

// Development-specific optimizations
if (process.env.NODE_ENV === 'development') {
  module.exports.watchAll = false;
  module.exports.verbose = false;
}
