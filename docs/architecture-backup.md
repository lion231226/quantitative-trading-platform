# Decision Architecture - 量化交易单均线策略分析平台

## Executive Summary

本架构为量化交易教育平台设计了现代化的全栈解决方案，采用 Next.js + FastAPI 技术栈，结合 Chart.js 数据可视化和 Redis 缓存优化。架构专注于快速开发（2天时间线）和教育导向的用户体验，通过 TypeScript 端到端类型安全和统一的实施模式确保 AI 代理的一致性开发。

## Project Initialization

### 第一实施故事：项目初始化

**使用 NextFastAPI 模板建立基础架构**

```bash
# 1. 通过 GitHub 界面使用模板创建新仓库
# 访问：https://github.com/vintasoftware/nextjs-fastapi-template

# 2. 克隆你的新仓库
git clone https://github.com/your-username/quant-trading-platform.git
cd quant-trading-platform

# 3. 安装必需工具
# - Python 3.12
# - Node.js 18+
# - pnpm: npm install -g pnpm
# - Docker + Docker Compose

# 4. 设置环境变量
# 复制 .env.example 到 .env 并配置
```

**模板提供的架构决策：**
- 语言/TypeScript: 前后端都有 TypeScript 支持 ✅
- 样式解决方案: 预配置的样式系统 ✅
- 测试框架: 包含测试设置 ✅
- 代码规范: 预配置的 linting 和格式化 ✅
- 构建工具: Next.js + FastAPI 标准工具链 ✅
- 项目结构: 分离的前后端结构 ✅

## Decision Summary

| Category | Decision | Version | Affects Epics | Rationale |
| -------- | -------- | ------- | ------------- | --------- |
| 启动模板 | NextFastAPI Template | Latest | 所有史诗 | 现代全栈架构，节省设置时间，端到端类型安全 |
| 数据持久化 | SQLite + Redis | SQLite 3.44+, Redis 7.2+ | Epic 1 | 快速开发，Python 生态集成良好，满足性能要求 |
| 数据可视化 | Chart.js | Chart.js 4.4+ | Epic 2 | 易于快速开发，性能优秀，金融图表支持好 |
| 部署目标 | Vercel | Vercel 平台 | 所有史诗 | Next.js 原生支持，自动 CI/CD，支持全栈部署 |
| API 模式 | REST API | OpenAPI 3.0 | 所有史诗 | 简单易用，文档自动生成，与模板兼容 |
| 错误处理 | 统一错误处理模式 | 自定义标准 | 所有史诗 | 一致的用户体验，便于调试和维护 |

## Project Structure

```
quant-trading-platform/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── frontend/                 # Next.js前端
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   ├── src/
│   │   ├── app/              # App Router页面
│   │   │   ├── page.tsx      # 主页
│   │   │   ├── strategy/     # 策略分析页面
│   │   │   │   ├── page.tsx
│   │   │   │   └── components/
│   │   │   ├── tutorial/     # 教程页面
│   │   │   │   └── page.tsx
│   │   │   └── api/          # API路由
│   │   │       └── strategies/
│   │   ├── components/       # 可复用组件
│   │   │   ├── charts/       # 图表组件
│   │   │   │   ├── StrategyChart.tsx
│   │   │   │   ├── PriceChart.tsx
│   │   │   │   └── PerformanceChart.tsx
│   │   │   ├── forms/        # 表单组件
│   │   │   │   ├── StrategyForm.tsx
│   │   │   │   └── ParameterForm.tsx
│   │   │   └── ui/           # UI组件
│   │   │       ├── Button.tsx
│   │   │       ├── Card.tsx
│   │   │       └── Loading.tsx
│   │   ├── lib/              # 工具函数
│   │   │   ├── api.ts        # API客户端
│   │   │   ├── chart-config.ts # Chart.js配置
│   │   │   └── utils.ts      # 通用工具
│   │   ├── types/            # TypeScript类型定义
│   │   │   ├── strategy.ts   # 策略相关类型
│   │   │   └── api.ts        # API响应类型
│   │   └── hooks/            # React Hooks
│   │       ├── useStrategyData.ts
│   │       └── useMarketData.ts
│   └── public/               # 静态资源
│       ├── images/
│       └── favicon.ico
│
├── backend/                  # FastAPI后端
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── main.py              # FastAPI应用入口
│   ├── app/
│   │   ├── __init__.py
│   │   ├── core/            # 核心配置
│   │   │   ├── config.py    # 应用配置
│   │   │   ├── security.py  # 安全相关
│   │   │   └── database.py  # 数据库连接
│   │   ├── models/          # 数据模型
│   │   │   ├── strategy.py  # 策略模型
│   │   │   └── market_data.py # 市场数据模型
│   │   ├── schemas/         # Pydantic模式
│   │   │   ├── strategy.py  # 策略API模式
│   │   │   └── market_data.py
│   │   ├── api/             # API路由
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── strategies.py  # 策略API
│   │   │   │   │   ├── market_data.py # 数据API
│   │   │   │   │   └── backtest.py    # 回测API
│   │   │   │   └── api.py   # API路由汇总
│   │   │   └── deps.py      # 依赖注入
│   │   ├── services/        # 业务逻辑
│   │   │   ├── akshare_client.py # AKShare客户端
│   │   │   ├── strategy_engine.py  # 策略引擎
│   │   │   ├── backtest_engine.py  # 回测引擎
│   │   │   └── cache_service.py    # 缓存服务
│   │   └── utils/           # 工具函数
│   │       ├── logging.py   # 日志配置
│   │       └── helpers.py   # 辅助函数
│   └── tests/               # 测试文件
│       ├── test_api.py
│       └── test_services.py
│
├── docs/                    # 项目文档
│   ├── api.md               # API文档
│   ├── deployment.md        # 部署指南
│   └── development.md       # 开发指南
│
└── scripts/                 # 部署脚本
    ├── deploy.sh
    └── setup.sh
```

## Epic to Architecture Mapping

| Epic | 架构组件 | 责任范围 |
| ---- | -------- | --------- |
| Epic 1: 项目基础与数据核心 | backend/services/, backend/models/, backend/api/v1/endpoints/market_data.py | 数据获取、策略算法、缓存管理 |
| Epic 2: 用户体验与可视化展示 | frontend/src/components/charts/, frontend/src/app/strategy/, frontend/src/lib/chart-config.ts | 用户界面、数据可视化、交互功能 |

## Technology Stack Details

### Core Technologies

**前端技术栈：**
- **Next.js 14**: React框架，支持SSR和API路由
- **TypeScript**: 端到端类型安全
- **Chart.js 4.4+**: 数据可视化库
- **Tailwind CSS**: 实用优先的CSS框架
- **React Query**: 服务端状态管理

**后端技术栈：**
- **FastAPI**: 现代Python Web框架
- **Pydantic**: 数据验证和序列化
- **SQLite 3.44+**: 轻量级数据库
- **Redis 7.2+**: 内存缓存和会话存储
- **AKShare**: 金融数据获取库

**开发工具：**
- **pnpm**: 包管理器
- **Docker**: 容器化开发环境
- **ESLint + Prettier**: 代码质量和格式化

### Integration Points

**API边界：**
- 前端 API 客户端：`frontend/src/lib/api.ts`
- 后端 API 路由：`backend/api/v1/`
- 数据传输：JSON格式，OpenAPI 3.0规范

**数据流架构：**
```
AKShare API → Redis缓存 → SQLite存储 → 策略引擎计算 → REST API → Chart.js可视化
```

**缓存策略：**
- 市场数据：Redis缓存24小时
- 策略结果：缓存1小时
- 用户会话：Redis存储

## Implementation Patterns

这些模式确保所有AI代理的一致性开发：

### API响应格式标准

```typescript
// 成功响应
{
  "success": true,
  "data": {
    "strategy_id": "string",
    "results": [...]
  },
  "message": "操作成功"
}

// 错误响应
{
  "success": false,
  "error": {
    "type": "VALIDATION_ERROR|API_ERROR|STRATEGY_ERROR",
    "message": "参数验证失败",
    "details": {...}
  }
}
```

### 状态管理模式

```typescript
// 使用React Query进行服务端状态管理
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['strategy', strategyId],
  queryFn: () => strategyAPI.getResults(strategyId),
  staleTime: 5 * 60 * 1000, // 5分钟
});

// 本地状态使用useState
const [parameters, setParameters] = useState<StrategyParams>(defaultParams);
```

### 错误处理模式

```typescript
// 前端错误边界
try {
  const result = await strategyAPI.run(params);
  setData(result.data);
} catch (error) {
  setError({
    type: error.response?.data?.error?.type || 'UNKNOWN_ERROR',
    message: error.response?.data?.error?.message || '操作失败，请重试'
  });
}

// 后端异常处理
try:
    result = await strategy_engine.calculate(params)
except ValidationError as e:
    raise HTTPException(status_code=400, detail={
        "type": "VALIDATION_ERROR",
        "message": str(e),
        "details": {"field": e.field}
    })
```

## Consistency Rules

### Naming Conventions

**API端点命名：**
- 路径：`/api/v1/strategies` (复数形式)
- 路由参数：`/api/v1/strategies/{strategy_id}` (snake_case)
- 查询参数：`?start_date=2024-01-01&end_date=2024-12-31`

**数据库命名：**
- 表名：`market_data`, `strategy_results` (snake_case, 复数)
- 列名：`strategy_id`, `created_at`, `close_price` (snake_case)
- 外键：`{table}_id` 格式

**前端组件命名：**
- 组件：`StrategyChart`, `MarketDataTable` (PascalCase)
- 文件：`strategy-chart.tsx`, `market-data-table.tsx` (kebab-case)
- Hook：`useStrategyData`, `useMarketData` (camelCase)

### Code Organization

**测试位置：** 与源文件同目录，使用 `.test.ts` 后缀
```
frontend/src/lib/api.test.ts
backend/app/services/strategy_engine.test.py
```

**组件组织：** 按功能分组，不按类型分组
```
frontend/src/components/strategy/
├── StrategyChart.tsx
├── StrategyForm.tsx
└── StrategyResults.tsx
```

### Error Handling

**统一错误响应格式：** 所有API必须遵循标准格式
**错误类型分类：** VALIDATION_ERROR, API_ERROR, STRATEGY_ERROR
**用户友好提示：** 技术错误转换为中文提示信息
**重试机制：** 网络错误自动重试2次，指数退避

### Logging Strategy

```python
# 后端结构化日志
logger.info(
    "策略计算完成",
    extra={
        "strategy_id": strategy_id,
        "symbol": symbol,
        "execution_time_ms": execution_time,
        "result_count": len(results)
    }
)

# 错误日志
logger.error(
    "AKShare API调用失败",
    extra={
        "symbol": symbol,
        "error_type": "API_TIMEOUT",
        "retry_count": retry_count
    }
)
```

## Data Architecture

### 核心数据模型

**市场数据模型：**
```python
class MarketData(BaseModel):
    symbol: str
    date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    created_at: datetime
```

**策略结果模型：**
```python
class StrategyResult(BaseModel):
    strategy_id: str
    symbol: str
    start_date: date
    end_date: date
    parameters: dict
    trades: List[Trade]
    performance: PerformanceMetrics
    created_at: datetime
```

### 数据关系

```
MarketData (1) ←→ (N) StrategyResult
                ↓
         PerformanceMetrics
                ↓
               Trade
```

### 缓存策略

- **市场数据缓存：** Redis，TTL=24小时
- **策略结果缓存：** Redis，TTL=1小时
- **用户参数缓存：** Redis，TTL=30分钟

## API Contracts

### 端点设计

```
GET    /api/v1/market-data/symbols          # 获取可用期货品种
GET    /api/v1/market-data/history          # 获取历史数据
POST   /api/v1/market-data/refresh         # 刷新数据缓存

GET    /api/v1/strategies                   # 获取策略列表
POST   /api/v1/strategies/run               # 运行策略
GET    /api/v1/strategies/{id}/results      # 获取策略结果

POST   /api/v1/backtest                     # 执行回测
GET    /api/v1/backtest/{id}/report         # 获取回测报告
```

### 请求/响应示例

**运行策略请求：**
```json
POST /api/v1/strategies/run
{
  "symbol": "CU2401",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "parameters": {
    "ma_period": 20,
    "initial_capital": 100000
  }
}
```

**策略响应：**
```json
{
  "success": true,
  "data": {
    "strategy_id": "strategy_123456",
    "symbol": "CU2401",
    "performance": {
      "total_return": 0.156,
      "max_drawdown": -0.089,
      "sharpe_ratio": 1.23,
      "win_rate": 0.65
    }
  },
  "message": "策略计算完成"
}
```

## Security Architecture

### 安全策略

**API安全：**
- FastAPI内置CORS配置
- 请求大小限制
- 速率限制（每分钟100次请求）

**数据安全：**
- 敏感信息环境变量存储
- 数据库连接加密
- API密钥安全管理

**前端安全：**
- Next.js安全头部配置
- XSS防护
- 输入验证和清理

### 认证和授权

**项目性质：** 教育演示平台，无需用户认证系统
**访问控制：** 公开访问，无需身份验证
**数据隔离：** 每个用户数据独立存储，避免数据泄露

## Performance Considerations

### 性能优化策略

**前端优化：**
- Next.js静态生成和SSR
- Chart.js数据点限制（最大1000个点）
- 图片懒加载和压缩
- 代码分割和动态导入

**后端优化：**
- 异步数据库查询
- Redis缓存热点数据
- 数据库索引优化
- 连接池管理

**API性能：**
- 响应压缩（gzip）
- 缓存头设置
- 异步任务队列
- 超时控制（10秒）

### 性能指标

**目标性能（来自NFR）：**
- 页面加载时间：< 3秒
- 策略回测响应：< 10秒
- API响应时间：< 500ms
- 并发用户支持：50+

**监控指标：**
- API响应时间分布
- 缓存命中率
- 错误率统计
- 用户行为分析

## Deployment Architecture

### 部署策略

**目标平台：** Vercel（推荐）
**部署方式：** 自动CI/CD
**环境配置：** 开发/测试/生产环境分离

### Vercel部署配置

```json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/.next",
  "installCommand": "cd frontend && npm install",
  "framework": "nextjs",
  "functions": {
    "backend/api/*.py": {
      "runtime": "python3.9"
    }
  }
}
```

### 环境变量管理

**生产环境变量：**
```bash
# 数据库
DATABASE_URL=sqlite:///./quant_trading.db
REDIS_URL=redis://localhost:6379

# API配置
AKSHARE_CACHE_TTL=86400
MAX_RETRY_ATTEMPTS=3

# 安全
SECRET_KEY=your-secret-key
CORS_ORIGINS=https://yourdomain.vercel.app
```

### 备份和恢复

**数据备份：**
- SQLite数据库定期备份到云存储
- Redis数据持久化配置
- 配置文件版本控制

**灾难恢复：**
- 多区域部署选项
- 自动故障转移
- 数据恢复流程

## Development Environment

### Prerequisites

**必需工具：**
- Python 3.12+
- Node.js 18+
- pnpm (包管理器)
- Docker + Docker Compose
- Git

**推荐工具：**
- VS Code + 相关扩展
- Postman (API测试)
- Redis Desktop Manager

### Setup Commands

```bash
# 1. 克隆项目
git clone https://github.com/your-username/quant-trading-platform.git
cd quant-trading-platform

# 2. 设置后端环境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 设置前端环境
cd ../frontend
pnpm install

# 4. 启动开发服务
# 终端1: 启动后端
cd backend && uvicorn main:app --reload --port 8000

# 终端2: 启动前端
cd frontend && pnpm dev

# 终端3: 启动Redis
docker run -d -p 6379:6379 redis:7-alpine

# 5. 访问应用
# 前端: http://localhost:3000
# 后端API: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 开发工作流

**代码提交前检查：**
- 运行测试套件
- 代码格式检查（prettier, eslint）
- TypeScript类型检查
- API文档更新

**调试和测试：**
- 单元测试覆盖率 > 80%
- 集成测试关键API
- 性能测试和优化

## Architecture Decision Records (ADRs)

### ADR-001: 技术栈选择

**决策：** 采用 Next.js + FastAPI + SQLite + Redis 技术栈
**状态：** 已接受
**理由：**
- 快速开发需求（2天时间线）
- 端到端类型安全
- 教育导向的复杂度平衡
- 部署和维护简单

**替代方案考虑：**
- T3 App：过于复杂，学习成本高
- 纯前端方案：无法处理复杂策略计算
- Django + React：设置时间过长

### ADR-002: 数据可视化选择

**决策：** 使用 Chart.js 而非 D3.js
**状态：** 已接受
**理由：**
- 学习曲线平缓，符合时间约束
- 金融图表支持良好
- 性能优秀，满足响应要求
- 社区活跃，问题解决容易

### ADR-003: 缓存策略设计

**决策：** Redis + SQLite 分层缓存
**状态：** 已接受
**理由：**
- AKShare API调用优化
- 响应时间要求（< 10秒）
- 成本效益平衡
- 扩展性考虑

### ADR-004: 部署平台选择

**决策：** Vercel 而非自建服务器
**状态：** 已接受
**理由：**
- Next.js原生支持
- 自动CI/CD
- 免费额度充足
- 运维成本低

### ADR-005: 错误处理标准化

**决策：** 统一错误响应格式和用户友好提示
**状态：** 已接受
**理由：**
- 教育平台用户体验优先
- AI代理开发一致性要求
- 调试和维护便利性
- 国际化支持需求

---

*Generated by BMAD Decision Architecture Workflow v1.3.2*
*Date: 2025-11-01*
*For: aTenderLion*