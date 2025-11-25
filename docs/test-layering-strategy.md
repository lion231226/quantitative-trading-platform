# 测试分层策略文档

## 概述

本文档定义了项目的测试分层策略，旨在建立清晰的测试职责边界，确保测试覆盖的有效性和可维护性。

## 测试分层架构

### 1. 单元测试 (70%) - 基础层

**职责范围:**
- 组件逻辑测试
- 工具函数测试
- 业务规则验证
- 数据转换函数
- Hook逻辑测试

**实施标准:**
- 使用Jest + React Testing Library
- 隔离测试，不依赖外部服务
- 快速执行，单个测试应在100ms内完成
- 覆盖率要求：90%以上

**测试文件结构:**
```
src/
├── components/
│   └── __tests__/          # 组件单元测试
├── services/
│   └── __tests__/          # 服务单元测试
├── utils/
│   └── __tests__/          # 工具函数单元测试
├── hooks/
│   └── __tests__/          # Hook单元测试
└── types/
    └── __tests__/          # 类型相关测试
```

**示例测试模式:**
```typescript
// 单元测试示例
describe('UserService', () => {
  test('should calculate profit correctly when given valid data', () => {
    // Arrange
    const inputData = { cost: 100, revenue: 150 }

    // Act
    const result = calculateProfit(inputData)

    // Assert
    expect(result).toBe(50)
  })
})
```

### 2. 集成测试 (20%) - 中间层

**职责范围:**
- 组件间交互测试
- API集成测试
- 数据流测试
- 状态管理测试
- 第三方服务集成

**实施标准:**
- 使用Jest + MSW (Mock Service Worker)
- 测试多个组件或服务的协作
- 执行时间应在1-5秒内
- 模拟外部依赖，但保持真实的数据流

**测试文件结构:**
```
src/
├── __tests__/              # 集成测试
│   ├── integration/        # 组件集成测试
│   ├── api/               # API集成测试
│   └── workflows/         # 业务流程测试
```

**示例测试模式:**
```typescript
// 集成测试示例
describe('Strategy Form Integration', () => {
  test('should submit form and update chart data', async () => {
    // 模拟API响应
    server.use(
      rest.post('/api/strategies', (req, res, ctx) => {
        return res(ctx.json({ success: true, data: mockStrategyData }))
      })
    )

    render(<StrategyForm />)

    // 填写表单
    fireEvent.change(screen.getByLabelText('策略名称'), { target: { value: 'Test Strategy' } })
    fireEvent.click(screen.getByText('提交'))

    // 验证图表更新
    await waitFor(() => {
      expect(screen.getByTestId('strategy-chart')).toBeInTheDocument()
    })
  })
})
```

### 3. 端到端测试 (10%) - 顶层

**职责范围:**
- 完整用户流程测试
- 跨页面导航测试
- 关键业务场景验证
- 浏览器兼容性测试
- 性能关键路径测试

**实施标准:**
- 使用Playwright
- 模拟真实用户操作
- 执行时间可在10-30秒内
- 专注核心用户旅程

**测试文件结构:**
```
e2e/
├── auth/                   # 认证流程测试
├── trading/               # 交易流程测试
├── charts/                # 图表交互测试
└── performance/           # 性能测试
```

**示例测试模式:**
```typescript
// E2E测试示例
test('should complete strategy creation workflow', async ({ page }) => {
  await page.goto('/strategies')

  // 创建新策略
  await page.click('[data-testid="create-strategy-btn"]')
  await page.fill('[data-testid="strategy-name"]', 'My Test Strategy')
  await page.fill('[data-testid="initial-capital"]', '10000')

  // 配置策略参数
  await page.click('[data-testid="next-step"]')
  await page.selectOption('[data-testid="chart-type"]', 'candlestick')

  // 提交并验证
  await page.click('[data-testid="submit-strategy"]')
  await expect(page.locator('[data-testid="success-message"]')).toBeVisible()
})
```

## 测试执行策略

### CI/CD 集成

**GitHub Actions 配置:**
```yaml
name: Test Pipeline
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm run test:unit -- --coverage

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm run test:integration

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm run build
      - run: npm run test:e2e
```

### 本地开发工作流

**命令配置:**
```json
{
  "scripts": {
    "test": "jest",
    "test:unit": "jest --testPathPattern=__tests__",
    "test:integration": "jest --testPathPattern=integration",
    "test:e2e": "playwright test",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:ci": "jest --ci --coverage --watchAll=false"
  }
}
```

## 质量标准

### 覆盖率要求

| 测试类型 | 覆盖率目标 | 执行时间要求 |
|---------|-----------|-------------|
| 单元测试 | 90%+ | < 100ms/test |
| 集成测试 | 80%+ | < 5s/test |
| E2E测试 | 核心路径100% | < 30s/test |

### 性能基准

- **总测试套件执行时间**: < 5分钟
- **单元测试套件**: < 2分钟
- **集成测试套件**: < 3分钟
- **E2E测试套件**: < 10分钟

## 测试数据策略

### 测试数据管理

**单元测试:**
- 使用工厂函数生成测试数据
- 内存数据，无需持久化
- 每个测试独立数据

**集成测试:**
- 使用MSW模拟API响应
- 标准化的测试数据集
- 数据库事务回滚

**E2E测试:**
- 使用专用的测试数据库
- 种子数据管理
- 测试间数据隔离

### Mock策略

**Mock原则:**
- 单元测试：完全隔离，Mock所有外部依赖
- 集成测试：Mock外部服务，保持内部逻辑真实
- E2E测试：最小化Mock，使用真实服务

## 最佳实践

### 1. 测试命名规范

```typescript
// 推荐：使用 "should [期望结果] when [条件]" 模式
test('should calculate profit correctly when given valid input')
test('should display error message when API call fails')
test('should navigate to strategy page when form is submitted')
```

### 2. 测试组织结构

```typescript
describe('ComponentName', () => {
  describe('Rendering', () => {
    // 渲染相关测试
  })

  describe('User Interactions', () => {
    // 用户交互测试
  })

  describe('Data Handling', () => {
    // 数据处理测试
  })
})
```

### 3. 错误处理测试

```typescript
test('should handle network errors gracefully', async () => {
  // 模拟网络错误
  server.use(
    rest.get('/api/data', (req, res, ctx) => {
      return res.networkError('Network connection failed')
    })
  )

  render(<Component />)

  // 验证错误状态
  await waitFor(() => {
    expect(screen.getByText('网络连接失败')).toBeInTheDocument()
  })
})
```

## 工具和配置

### Jest 配置优化

```javascript
// jest.config.js
module.exports = {
  projects: [
    {
      displayName: 'unit',
      testMatch: ['<rootDir>/src/**/__tests__/**/*.test.{js,ts,tsx}'],
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testTimeout: 10000
    },
    {
      displayName: 'integration',
      testMatch: ['<rootDir>/src/__tests__/integration/**/*.test.{js,ts,tsx}'],
      setupFilesAfterEnv: ['<rootDir>/jest.integration.setup.js'],
      testTimeout: 30000
    }
  ]
}
```

### 覆盖率配置

```javascript
// jest.coverage.config.js
module.exports = {
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    },
    './src/services/': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90
    }
  }
}
```

## 监控和报告

### 测试报告

- **覆盖率报告**: HTML + LCOV格式
- **测试执行报告**: JUnit XML格式
- **性能报告**: 测试执行时间统计
- **失败分析**: 自动分类失败原因

### 持续改进

- 定期审查测试覆盖率
- 分析测试执行时间趋势
- 识别和消除不稳定的测试
- 重构重复的测试代码

---

本文档为测试团队提供了清晰的指导原则，确保测试策略与项目目标和质量标准保持一致。