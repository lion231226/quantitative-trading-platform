# 量化交易策略分析平台

一个教育导向的量化交易策略分析平台，专注于量化交易策略的学习和实践。

## 项目概述

本项目旨在通过直观的界面和详细的教程，帮助用户在30分钟内掌握单均线交易策略的核心概念。平台提供真实的市场数据回测功能，让用户能够深入了解策略的运行机制和风险特征。

### 核心特性

- 📊 **实时数据分析**: 基于AKShare获取真实期货市场数据
- 📈 **策略回测**: 单均线策略历史表现分析
- 🎓 **教育导向**: 交互式学习体验和详细教程
- ⚡ **快速响应**: API响应时间 < 500ms
- 🔒 **类型安全**: 端到端TypeScript支持
- 📱 **响应式设计**: 支持桌面和移动设备

## 技术栈

### 前端
- **Next.js 14+**: React全栈框架
- **TypeScript**: 类型安全的JavaScript
- **Tailwind CSS**: 实用优先的CSS框架
- **Chart.js**: 数据可视化库
- **React Query**: 服务端状态管理

### 后端
- **FastAPI**: 现代Python Web框架
- **SQLAlchemy**: Python ORM工具
- **SQLite**: 轻量级数据库
- **Redis**: 内存缓存服务
- **AKShare**: 中国期货数据源

### 开发工具
- **pnpm**: 前端包管理器
- **Black**: Python代码格式化
- **ESLint + Prettier**: 前端代码规范
- **pytest**: 后端测试框架
- **Jest**: 前端测试框架

## 项目结构

```
quant-trading-platform/
├── frontend/                 # Next.js前端
│   ├── src/
│   │   ├── app/             # App Router页面
│   │   ├── components/      # React组件
│   │   ├── lib/             # 工具函数
│   │   ├── types/           # TypeScript类型
│   │   └── hooks/           # React Hooks
│   └── package.json
├── backend/                  # FastAPI后端
│   ├── app/
│   │   ├── api/             # API路由
│   │   ├── core/            # 核心配置
│   │   ├── models/          # 数据模型
│   │   ├── schemas/         # API模式
│   │   ├── services/        # 业务逻辑
│   │   └── utils/           # 工具函数
│   ├── main.py              # 应用入口
│   └── requirements.txt
├── docs/                     # 项目文档
├── data/                     # 数据存储
└── config/                   # 配置文件
```

## 快速开始

### 环境要求

- **Node.js**: 18.0.0+
- **Python**: 3.12+
- **Redis**: 7.2+
- **Git**: 最新版本

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd quant-trading-platform
```

2. **环境配置**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量（可选）
nano .env
```

3. **后端设置**
```bash
cd backend

# 创建Python虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

4. **前端设置**
```bash
cd ../frontend

# 安装依赖
pnpm install
```

5. **启动服务**

启动Redis服务：
```bash
redis-server
```

启动后端服务：
```bash
cd backend
uvicorn main:app --reload --port 8000
```

启动前端服务：
```bash
cd frontend
pnpm dev
```

6. **访问应用**
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/api/v1/docs

## 开发指南

### 代码规范

- **前端**: 使用ESLint + Prettier进行代码格式化
- **后端**: 使用Black进行代码格式化
- **提交**: 遵循Conventional Commits规范

### 测试

运行前端测试：
```bash
cd frontend
pnpm test
pnpm test:coverage
```

运行后端测试：
```bash
cd backend
pytest
pytest --cov=app --cov-report=html
```

### API文档

启动后端服务后，可以通过以下地址访问API文档：
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 策略说明

### 单均线策略

单均线策略是一个简单但有效的趋势跟踪策略：

**买入信号**: 当价格上穿移动平均线时（金叉）
**卖出信号**: 当价格下穿移动平均线时（死叉）
**风险控制**: 固定百分比止损

### 可调参数

- **MA周期**: 移动平均线计算周期（5-200天）
- **初始资金**: 策略启动资金（10,000-10,000,000）
- **止损比例**: 固定止损百分比（1%-20%）

## 性能指标

平台监控以下关键指标：

- **API响应时间**: < 500ms
- **策略计算时间**: < 10秒
- **页面加载时间**: < 3秒
- **数据缓存TTL**: 24小时

## 部署

### 前端部署（Vercel）

```bash
cd frontend
pnpm build
vercel --prod
```

### 后端部署（Docker）

```bash
cd backend
docker build -t quant-trading-backend .
docker run -p 8000:8000 quant-trading-backend
```

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 作者

**aTenderLion** - *项目创始者和主要开发者*

## 鸣谢

- [AKShare](https://github.com/akfamily/akshare) - 提供中国期货数据
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Python Web框架
- [Next.js](https://nextjs.org/) - React全栈框架
- [Chart.js](https://www.chartjs.org/) - 灵活的图表库

## 支持

如果您觉得这个项目有用，请给它一个⭐️！

如有问题或建议，请通过以下方式联系：
- 提交Issue: [GitHub Issues](https://github.com/your-username/quant-trading-platform/issues)
- 邮箱: your-email@example.com

---

**免责声明**: 本平台仅用于教育和研究目的。交易有风险，投资需谨慎。