# 史诗1技术上下文 - 项目基础与数据核心

**史诗ID:** Epic 1
**史诗名称:** 项目基础与数据核心
**创建日期:** 2025-11-01
**作者:** aTenderLion

---

## 史诗概述

史诗1旨在建立量化交易单均线策略分析平台的核心基础设施。通过8个故事的递进式开发，实现从项目初始化到基础功能集成的完整技术栈，为后续功能开发奠定坚实基础。

**史诗目标:** 建立项目基础设施，实现数据获取和基础策略算法，创建可运行的最小可行性产品
**价值主张:** 为后续功能开发奠定技术基础，提供核心的交易策略功能

---

## 整体技术架构

### 系统架构图
```mermaid
graph TB
    subgraph "前端层 (Next.js)"
        UI[用户界面]
        Forms[表单组件]
        Charts[图表组件]
    end

    subgraph "API层 (FastAPI)"
        API[REST API]
        Auth[认证中间件]
        Validation[数据验证]
    end

    subgraph "业务层"
        Strategy[策略引擎]
        Backtest[回测引擎]
        DataProcessor[数据处理]
    end

    subgraph "数据层"
        Cache[Redis缓存]
        DB[(SQLite数据库)]
        AKShare[AKShare API]
    end

    UI --> API
    Forms --> API
    Charts --> API
    API --> Strategy
    API --> Backtest
    Strategy --> DataProcessor
    Backtest --> DataProcessor
    DataProcessor --> Cache
    DataProcessor --> DB
    DataProcessor --> AKShare
```

### 技术栈配置
- **前端:** Next.js 14+ + TypeScript + Tailwind CSS + Chart.js 4.4+
- **后端:** FastAPI + Python 3.12+ + SQLAlchemy + Pydantic
- **数据库:** SQLite 3.44+ (开发) + Redis 7.2+ (缓存)
- **数据源:** AKShare API (中国期货数据)
- **部署:** Vercel (前端) + Docker (后端)

---

## 故事技术上下文映射

### Story 1.1: 项目初始化和基础架构 ✅
**状态:** ready-for-dev
**上下文文件:** docs/stories/1-1-project-initialization-and-basic-architecture.context.xml

**核心技术组件:**
- 项目目录结构建立
- 开发环境配置
- 代码规范设置
- 错误处理框架

**技术要点:**
- Next.js + FastAPI 双栈架构
- TypeScript strict mode
- 统一的代码规范 (ESLint + Prettier + Black)
- Git 工作流配置

### Story 1.2: 数据获取模块基础 ✅
**状态:** ready-for-dev
**上下文文件:** docs/stories/1-2-data-acquisition-module-basics.context.xml

**核心技术组件:**
- AKShare API 客户端
- Redis 缓存服务
- 多版块数据支持
- 错误处理和重试机制

**技术要点:**
- 支持能源、金属、农产品、化工四大版块
- 24小时数据缓存策略
- 异步API调用优化
- 完整的错误处理机制

### Story 1.3: 数据处理和存储 ✅
**状态:** ready-for-dev
**上下文文件:** docs/stories/1-3-data-processing-and-storage.context.xml

**核心技术组件:**
- SQLite 数据库设计
- 数据清洗和验证
- 批量数据处理
- 增量同步机制

**技术要点:**
- MarketData 数据模型设计
- 数据完整性约束
- 高效查询优化
- 多格式数据导出

### Story 1.4: 单均线策略核心算法
**状态:** ready-for-dev
**上下文文件:** [待创建]

**核心技术组件:**
- 移动平均线计算
- 交易信号生成
- 止损机制
- 策略参数配置

**技术要点:**
- SMA/EMA 均线算法实现
- 金叉/死叉信号逻辑
- 固定百分比止损
- 策略参数可配置化

### Story 1.5: 收益计算引擎
**状态:** ready-for-dev
**上下文文件:** [待创建]

**核心技术组件:**
- 收益率计算
- 风险指标计算
- 绩效统计
- 交易记录分析

**技术要点:**
- 总收益率、累计收益计算
- 最大回撤、回撤期间分析
- 夏普比率、Sortino比率
- 胜率、盈亏比统计

### Story 1.6: 基础API接口
**状态:** ready-for-dev
**上下文文件:** [待创建]

**核心技术组件:**
- RESTful API设计
- 数据查询接口
- 策略执行接口
- 参数配置接口

**技术要点:**
- 统一API响应格式
- 自动API文档生成
- 请求验证和错误处理
- API性能优化

### Story 1.7: 基础前端界面
**状态:** ready-for-dev
**上下文文件:** [待创建]

**核心技术组件:**
- 响应式界面设计
- 期货品种选择
- 参数配置表单
- 结果显示区域

**技术要点:**
- Next.js App Router
- Tailwind CSS 样式
- 表单状态管理
- 错误边界处理

### Story 1.8: 基础功能集成测试
**状态:** ready-for-dev
**上下文文件:** [待创建]

**核心技术组件:**
- 端到端测试
- 性能测试
- 错误处理测试
- 部署脚本

**技术要点:**
- 完整流程测试覆盖
- 性能基准验证
- 错误恢复机制
- CI/CD 流水线

---

## 关键技术规范

### 数据模型标准
```python
class MarketData(BaseModel):
    symbol: str          # 期货代码
    date: datetime       # 交易日期
    open_price: float    # 开盘价
    high_price: float    # 最高价
    low_price: float     # 最低价
    close_price: float   # 收盘价
    volume: int         # 成交量
    created_at: datetime # 创建时间
```

### API响应格式标准
```python
# 成功响应
{
    "success": True,
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "success": False,
    "error": {
        "type": "ERROR_TYPE",
        "message": "错误描述",
        "details": {...}
    }
}
```

### 策略算法标准
```python
def calculate_moving_average(prices: List[float], period: int) -> List[float]
def generate_trading_signals(prices: List[float], ma: List[float]) -> List[Signal]
def calculate_performance_metrics(signals: List[Signal], prices: List[float]) -> PerformanceMetrics
```

---

## 开发约束和规范

### 命名规范
- **API端点:** `/api/v1/{resource}` (复数形式)
- **数据库表:** `{table_name}` (snake_case, 复数)
- **前端组件:** `{ComponentName}` (PascalCase)
- **文件名:** `{file-name}` (kebab-case)

### 代码组织
- **测试文件:** 与源文件同目录，`.test.ts` 后缀
- **组件组织:** 按功能分组，不按类型分组
- **错误处理:** 统一错误响应格式，用户友好提示

### 性能要求
- **API响应时间:** < 500ms
- **策略计算时间:** < 10秒
- **页面加载时间:** < 3秒
- **数据缓存:** 24小时TTL

---

## 测试策略

### 测试层次
1. **单元测试:** (>80%覆盖率)
   - 策略算法计算准确性
   - API端点响应正确性
   - 数据处理逻辑完整性

2. **集成测试:**
   - 完整的数据获取到策略回测流程
   - 前后端API交互
   - 缓存机制有效性

3. **端到端测试:**
   - 用户旅程完整性
   - 错误处理和恢复
   - 性能目标验证

### 测试工具配置
```bash
# 后端测试
pytest backend/tests/ -v --cov=backend/app --cov-report=html

# 前端测试
npm test -- --coverage --watchAll=false
```

---

## 部署和运维

### 环境配置
```bash
# 开发环境
DATABASE_URL=sqlite:///./quant_trading.db
REDIS_URL=redis://localhost:6379
AKSHARE_CACHE_TTL=86400
MAX_RETRY_ATTEMPTS=3

# 生产环境
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://prod-host:6379
SECRET_KEY=your-production-secret
CORS_ORIGINS=https://yourdomain.vercel.app
```

### Docker配置
```dockerfile
# 后端Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 风险缓解策略

### 技术风险
1. **数据获取风险:**
   - 风险: AKShare API限制或不稳定
   - 缓解: 实现重试机制和本地缓存

2. **性能风险:**
   - 风险: 策略计算超时 (>10秒)
   - 缓解: 异步处理、进度反馈

3. **兼容性风险:**
   - 风险: 浏览器兼容性问题
   - 缓解: 使用成熟的Chart.js和Next.js

### 时间风险
1. **开发进度风险:**
   - 风险: 时间不足以完成8个故事
   - 缓解: 并行开发、核心功能优先

2. **学习曲线风险:**
   - 风险: 技术栈学习时间超出预期
   - 缓解: 准备技术文档、示例代码

---

## 质量保证

### 代码质量检查
- **静态分析:** ESLint + Prettier (前端), Black + isort (后端)
- **TypeScript:** strict mode 强制类型检查
- **代码审查:** API设计一致性、错误处理完整性

### 性能监控
- **响应时间监控:** API响应时间追踪
- **错误率监控:** 异常捕获和报告
- **资源使用监控:** 内存和CPU使用情况

---

## 实施建议

### 开发优先级
1. **第一优先级:** Stories 1.1-1.3 (基础设施)
2. **第二优先级:** Stories 1.4-1.5 (核心算法)
3. **第三优先级:** Stories 1.6-1.7 (用户界面)
4. **第四优先级:** Story 1.8 (测试和部署)

### 并行开发策略
- **前端开发:** Story 1.7 可与后端开发并行
- **API设计:** Story 1.6 可在算法完成后开始
- **测试准备:** Story 1.8 可在所有功能完成后集成

### 质量门禁
- 每个故事完成后进行代码审查
- 集成测试通过后进入下一故事
- 性能基准达标后认为完成

---

## 总结

史诗1技术上下文为量化交易单均线策略分析平台提供了完整的技术实施指导。通过标准化的技术栈、清晰的架构设计和详细的实施规范，确保AI代理能够高效一致地完成开发任务。

**关键成功因素:**
1. **快速开发导向:** 选择成熟技术栈，减少学习成本
2. **数据质量保证:** 建立完整的数据处理和验证流程
3. **性能目标明确:** 具体的响应时间和处理能力要求
4. **质量标准统一:** 代码规范和测试覆盖的明确要求

史诗1具备成功实施的所有技术条件，建议立即开始实施阶段，按照故事优先级逐步推进开发工作。

---

*Technical Context generated for BMAD Epic 1*
*Date: 2025-11-01*
*Author: aTenderLion*